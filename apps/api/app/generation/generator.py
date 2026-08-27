"""
TRUSTRAG — grounded answer generation using Google Gemini.

Formulates prompts protecting against instructions injection and enforces
abstention rules when context is insufficient.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.core.model_registry import get_llm

logger = get_logger(__name__)

GROUNDING_SYSTEM_PROMPT = """You are a highly reliable question-answering assistant.
Your task is to answer the user query based ONLY on the provided text segments
in the Context section below.

Strict Constraints:
1. Grounding: Every assertion you make in the answer MUST be directly supported
   by a segment in the Context. Do not assume or extrapolate.
2. Insufficient Information: If the provided context does not contain enough
   information to answer the query, you MUST respond with the exact word:
   "ABSTAIN". Do not write any other text.
3. No External Knowledge: Do not use any training data knowledge to answer
   this question. Rely strictly on the Context segments.
4. Format: Do not include markdown headers or greetings in your output.
   Just return the factual answer or "ABSTAIN".
"""


def format_context(chunks: list[dict[str, Any]]) -> str:
    """Format evidence segments into a clear structured block."""
    if not chunks:
        return "No context segments available."

    formatted = []
    for i, c in enumerate(chunks, start=1):
        filename = c.get("filename") or "unknown_doc"
        page = c.get("page") or 1
        text = c.get("text", "").strip()
        formatted.append(f"--- Segment {i} [Source: {filename}, Page {page}] ---\n{text}")

    return "\n\n".join(formatted)


async def generate_grounded_answer(query: str, chunks: list[dict[str, Any]]) -> str:
    """
    Invoke Gemini model to generate a grounded answer based on candidate evidence chunks.

    If chunks list is empty, returns 'ABSTAIN' immediately without LLM invocation
    to save token costs.
    """
    if not chunks:
        logger.info("Empty context provided, abstaining immediately to save tokens")
        return "ABSTAIN"

    try:
        # Load primary LLM (cached)
        llm = get_llm()

        # Prepare context text
        context_str = format_context(chunks)

        # Build prompt messages
        messages = [
            SystemMessage(content=GROUNDING_SYSTEM_PROMPT),
            HumanMessage(content=f"[CONTEXT]\n{context_str}\n\n[QUERY]\n{query}"),
        ]

        logger.info("Invoking Gemini for grounded generation", chunk_count=len(chunks))

        response = await llm.ainvoke(messages)

        # Standardize result
        answer = response.content
        if isinstance(answer, bytes):
            answer = answer.decode("utf-8")

        answer = answer.strip()

        logger.info(
            "Grounded generation completed", answer_len=len(answer), abstained=(answer == "ABSTAIN")
        )
        return answer

    except Exception as exc:
        logger.error("Grounded generation failed", error=str(exc))
        # Default to ABSTAIN on runtime exception to ensure reliability
        return "ABSTAIN"
