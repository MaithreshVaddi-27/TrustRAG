"""
TRUSTRAG — Model Context Protocol (MCP) Server.

Exposes TrustRAG as standardized MCP tools:
  - `search_knowledge_base`: Hybrid RAG retrieval with dense/sparse RRF fusion
  - `verify_claim`: NLI assertion auditor against retrieved citations
  - `list_knowledge_bases`: List collections and point counts

Compatible with Claude Desktop, Cursor, Antigravity IDE, and any MCP client.
Run via:
    python -m app.mcp.server
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from app.core.exceptions import RetrievalOutageError
from app.core.logging import get_logger
from app.db.mongodb import Collections, connect_db, get_collection
from app.retrieval.retriever import retrieve_hybrid_chunks
from app.verification.verifier import batch_verify_claims_nli

logger = get_logger(__name__)

# Standard MCP Tool Definitions
MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "trustrag_search",
        "description": (
            "Retrieve grounded evidence chunks from a TrustRAG Knowledge Base "
            "using hybrid dense+sparse search with RRF."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_id": {"type": "string", "description": "Knowledge Base ObjectId"},
                "query": {"type": "string", "description": "Search query text"},
                "top_k": {
                    "type": "integer",
                    "description": "Number of chunks to retrieve (default: 5)",
                },
            },
            "required": ["kb_id", "query"],
        },
    },
    {
        "name": "trustrag_verify_claim",
        "description": (
            "Audit and verify factual assertions against evidence chunks "
            "(Supported, Contradicted, or Neutral)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "claims": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of atomic assertions to audit",
                },
                "evidence_texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Reference evidence chunk texts",
                },
            },
            "required": ["claims", "evidence_texts"],
        },
    },
    {
        "name": "trustrag_list_kbs",
        "description": "List all active TrustRAG knowledge bases and their collection schemas.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "tavily_search",
        "description": "AI-native web search using Tavily for clean snippets and source URLs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 5)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "duckduckgo_search",
        "description": "100% free web search using DuckDuckGo (zero API key needed).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 5)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "hybrid_web_search",
        "description": "Concurrent search across Tavily and DuckDuckGo with deduplication.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 5)",
                },
                "provider": {
                    "type": "string",
                    "description": "Search provider: 'tavily', 'duckduckgo', or 'both'",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "local_llm_chat",
        "description": (
            "Invoke local LLM (Ollama or llama.cpp) for grounded reasoning, summarization, or chat."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Prompt text for the local LLM"},
                "provider": {
                    "type": "string",
                    "description": "Provider: 'ollama' or 'llama_cpp' (default: 'ollama')",
                },
                "model": {
                    "type": "string",
                    "description": (
                        "Model identifier (e.g. 'granite4.2:3b-q4_K_M' or "
                        "'occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M')"
                    ),
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "local_llm_status",
        "description": (
            "Query status and available models for local LLM engines (Ollama and llama.cpp)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "description": "'ollama', 'llama_cpp', or 'both'",
                },
            },
        },
    },
]


async def handle_tool_call(
    tool_name: str, arguments: dict[str, Any], *, _internal: bool = False
) -> dict[str, Any]:
    """Execute an MCP tool call and return structured tool content.

    Args:
        _internal: In-process pipeline calls (graph.py web grounding) run
            inside the already-authenticated API process — no bearer token.
            External stdio clients must supply service_token. Never exposed
            over stdio: run_stdio_mcp_server() does not accept this flag.
    """
    from app.core.exceptions import AuthenticationError
    from app.core.security import decode_service_token
    from app.services.search_service import duckduckgo_search, execute_web_search, tavily_search

    def _clamp_results(value: Any, default: int = 5) -> int:
        try:
            return max(1, min(int(value), 10))
        except (TypeError, ValueError):
            return default

    def _require_service_token(arguments: dict[str, Any]) -> dict[str, Any]:
        """Extract and validate service token from arguments (returns payload)."""
        if _internal:
            return {"sub": "internal-pipeline"}
        token = arguments.get("service_token")
        if not token:
            raise AuthenticationError(
                "Service token required", detail="MCP tool requires service_token parameter"
            )
        try:
            payload = decode_service_token(token)
            if not isinstance(payload, dict):
                raise AuthenticationError("Invalid service token", detail="malformed payload")
            return payload
        except AuthenticationError as exc:
            raise AuthenticationError("Invalid service token", detail=str(exc)) from exc

    async def _enforce_kb_tenant(payload: dict[str, Any], kb_id: str) -> None:
        """Cross-tenant guard: a service token bound to a KB/user reads only that scope.

        Mirrors the M-2 checks on internal_ingest_document. Unbound (service-level)
        tokens keep full access; bound tokens are confined. Ownership failures map
        to AuthenticationError so bound callers can't probe KB existence.
        """
        from app.core.exceptions import AuthorizationError, NotFoundError
        from app.services.kb_service import get_kb

        bound_kb = payload.get("bound_kb_id")
        if bound_kb and str(bound_kb) != str(kb_id):
            raise AuthenticationError(
                "Service token not authorized for this knowledge base",
                detail="token is bound to a different KB",
            )
        bound_user = payload.get("bound_user_id")
        if bound_user:
            try:
                await get_kb(str(kb_id), str(bound_user))
            except (NotFoundError, AuthorizationError) as exc:
                raise AuthenticationError(
                    "Service token not authorized for this knowledge base",
                    detail="token is bound to a different user",
                ) from exc

    if tool_name == "tavily_search":
        _require_service_token(arguments)
        count = _clamp_results(arguments.get("max_results", 5))
        res = await tavily_search(arguments["query"], max_results=count)
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    elif tool_name == "duckduckgo_search":
        _require_service_token(arguments)
        count = _clamp_results(arguments.get("max_results", 5))
        res = await duckduckgo_search(arguments["query"], max_results=count)
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    elif tool_name == "hybrid_web_search":
        _require_service_token(arguments)
        count = _clamp_results(arguments.get("max_results", 5))
        res = await execute_web_search(
            arguments["query"],
            provider=arguments.get("provider", "both"),
            max_results=count,
        )
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
    if tool_name == "trustrag_search":
        _payload = _require_service_token(arguments)
        kb_id = arguments["kb_id"]
        await _enforce_kb_tenant(_payload, kb_id)
        query = arguments["query"]
        # Clamp client-supplied depth: retrieve_hybrid_chunks fans out to
        # dense+sparse searches plus rerank, so unbounded top_k is a DoS vector.
        try:
            top_k = int(arguments.get("top_k", 5))
        except (TypeError, ValueError):
            top_k = 5
        top_k = max(1, min(top_k, 50))
        try:
            candidates = await retrieve_hybrid_chunks(
                query=query, kb_id=kb_id, top_k_override=top_k
            )
        except RetrievalOutageError as exc:
            logger.error("trustrag_search outage", error=str(exc))
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"trustrag_search unavailable (retrieval outage): {exc}",
                    }
                ]
            }
        results = [
            {
                "chunk_id": str(c.get("chunk_id")),
                "text": c.get("text", ""),
                "score": round(float(c.get("rerank_score") or c.get("rrf_score", 0.0)), 4),
                "zone": c.get("zone", "body"),
                "document_id": str(c.get("document_id") or ""),
            }
            for c in candidates
        ]
        return {"content": [{"type": "text", "text": json.dumps(results, indent=2)}]}

    elif tool_name == "trustrag_verify_claim":
        _require_service_token(arguments)
        claims = arguments["claims"][:20]
        evidence_texts = [t[:4000] for t in arguments["evidence_texts"][:20]]
        fake_chunks = [
            {"chunk_id": f"ev_{idx}", "text": text} for idx, text in enumerate(evidence_texts)
        ]
        verdicts = await batch_verify_claims_nli(claims=claims, chunks=fake_chunks)
        return {"content": [{"type": "text", "text": json.dumps(verdicts, indent=2)}]}

    elif tool_name == "trustrag_list_kbs":
        _payload = _require_service_token(arguments)
        coll = get_collection(Collections.KNOWLEDGE_BASES)
        # Bound tokens enumerate only their tenant's KBs; unbound service
        # tokens keep the full listing.
        _filter: dict[str, Any] = {}
        bound_user = _payload.get("bound_user_id")
        if bound_user:
            from bson import ObjectId

            if not ObjectId.is_valid(str(bound_user)):
                raise AuthenticationError(
                    "Service token not authorized", detail="invalid bound user"
                )
            _filter = {"user_id": ObjectId(str(bound_user))}
        cursor = coll.find(_filter, {"name": 1, "description": 1, "document_count": 1})
        kbs = []
        async for doc in cursor:
            kbs.append(
                {
                    "id": str(doc["_id"]),
                    "name": doc.get("name", "Untitled"),
                    "description": doc.get("description", ""),
                    "document_count": doc.get("document_count", 0),
                }
            )
        return {"content": [{"type": "text", "text": json.dumps(kbs, indent=2)}]}

    elif tool_name == "local_llm_chat":
        _require_service_token(arguments)
        from app.core.local_llm import LOCAL_LLM_PROVIDERS
        from app.core.model_registry import get_llm

        # Local-only tool: never route a service-token call to metered cloud
        # providers (a leaked token must not become a spend vector).
        provider = str(arguments.get("provider", "ollama") or "ollama").strip().lower()
        if provider not in LOCAL_LLM_PROVIDERS:
            raise ValueError(
                f"local_llm_chat supports local providers only "
                f"({sorted(LOCAL_LLM_PROVIDERS)}), got '{provider}'"
            )
        model = arguments.get("model")
        prompt = str(arguments["prompt"])[:8000]
        llm = get_llm(provider=provider, model=model)
        res = await llm.ainvoke(prompt)
        text = res.content if hasattr(res, "content") else str(res)
        return {"content": [{"type": "text", "text": text}]}

    elif tool_name == "local_llm_status":
        _require_service_token(arguments)
        from app.core.config import get_settings
        from app.core.local_llm import check_llamacpp_status, check_ollama_status

        settings = get_settings()
        prov = arguments.get("provider", "both")
        status_res: dict[str, Any] = {}
        if prov in ("ollama", "both"):
            try:
                status_res["ollama"] = await check_ollama_status(settings.ollama_base_url)
            except Exception as exc:
                status_res["ollama"] = {"connected": False, "error": str(exc)[:200]}
        if prov in ("llama_cpp", "both"):
            try:
                status_res["llama_cpp"] = await check_llamacpp_status(settings.llamacpp_base_url)
            except Exception as exc:
                status_res["llama_cpp"] = {"connected": False, "error": str(exc)[:200]}
        return {"content": [{"type": "text", "text": json.dumps(status_res, indent=2)}]}

    raise ValueError(f"Unknown MCP tool: {tool_name}")


async def run_stdio_mcp_server() -> None:
    """Standard JSON-RPC 2.0 stdio loop for Model Context Protocol."""
    await connect_db()
    logger.info("TrustRAG MCP Server listening on stdio")

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break
        try:
            req = json.loads(line.decode("utf-8").strip())
            req_id = req.get("id")
            method = req.get("method")

            if method == "tools/list":
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}
            elif method == "tools/call":
                params = req.get("params", {})
                tool_result = await handle_tool_call(
                    params.get("name"), params.get("arguments", {})
                )
                resp = {"jsonrpc": "2.0", "id": req_id, "result": tool_result}
            else:
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": req.get("id") if "req" in locals() else None,
                "error": {"code": -32603, "message": str(exc)},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(run_stdio_mcp_server())
