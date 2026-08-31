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
]


async def handle_tool_call(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute an MCP tool call and return structured tool content."""
    from app.services.search_service import duckduckgo_search, execute_web_search, tavily_search

    if tool_name == "tavily_search":
        count = arguments.get("max_results", 5)
        res = await tavily_search(arguments["query"], max_results=count)
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    elif tool_name == "duckduckgo_search":
        count = arguments.get("max_results", 5)
        res = await duckduckgo_search(arguments["query"], max_results=count)
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    elif tool_name == "hybrid_web_search":
        count = arguments.get("max_results", 5)
        res = await execute_web_search(
            arguments["query"],
            provider=arguments.get("provider", "both"),
            max_results=count,
        )
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
    if tool_name == "trustrag_search":
        kb_id = arguments["kb_id"]
        query = arguments["query"]
        top_k = arguments.get("top_k", 5)
        candidates = await retrieve_hybrid_chunks(query=query, kb_id=kb_id, top_k=top_k)
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
        claims = arguments["claims"]
        evidence_texts = arguments["evidence_texts"]
        fake_chunks = [
            {"chunk_id": f"ev_{idx}", "text": text}
            for idx, text in enumerate(evidence_texts)
        ]
        verdicts = await batch_verify_claims_nli(claims=claims, chunks=fake_chunks)
        return {"content": [{"type": "text", "text": json.dumps(verdicts, indent=2)}]}

    elif tool_name == "trustrag_list_kbs":
        coll = get_collection(Collections.KNOWLEDGE_BASES)
        cursor = coll.find({}, {"name": 1, "description": 1, "document_count": 1})
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
