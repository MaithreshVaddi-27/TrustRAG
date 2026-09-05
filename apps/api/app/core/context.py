"""
TRUSTRAG — Conversation Context Management.

Implements sliding window and summarization strategies for managing
long conversation histories within LLM context limits.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_model_config
from app.core.logging import get_logger
from app.core.model_registry import get_llm

logger = get_logger(__name__)


# ─── Data Structures ──────────────────────────────────────────────────────────


@dataclass
class Message:
    """A single conversation message."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
    token_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "token_count": self.token_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"])
            if isinstance(data["timestamp"], str)
            else data["timestamp"],
            metadata=data.get("metadata", {}),
            token_count=data.get("token_count"),
        )


@dataclass
class ConversationSummary:
    """A summary of a conversation segment."""

    summary: str
    start_index: int  # Index of first message in original conversation
    end_index: int  # Index of last message (inclusive)
    message_count: int
    token_count: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "message_count": self.message_count,
            "token_count": self.token_count,
            "created_at": self.created_at.isoformat(),
        }


# ─── Token Estimation ─────────────────────────────────────────────────────────


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation (≈4 chars per token for English).
    For production, use tiktoken or model-specific tokenizer.
    """
    return max(1, len(text) // 4)


def estimate_message_tokens(message: Message) -> int:
    """Estimate tokens for a message including role overhead."""
    return estimate_tokens(message.content) + 4  # Role overhead


# ─── Sliding Window Manager ───────────────────────────────────────────────────


class SlidingWindowManager:
    """
    Manages conversation history with sliding window strategy.

    Keeps the most recent N messages or up to max_tokens.
    Older messages are dropped (not summarized).
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        max_messages: int = 50,
        system_message: str | None = None,
    ):
        self.max_tokens = max_tokens
        self.max_messages = max_messages
        self.system_message = system_message
        self.messages: deque[Message] = deque(maxlen=max_messages)

    def add_message(self, message: Message) -> None:
        """Add a message to the conversation."""
        if message.token_count is None:
            message.token_count = estimate_message_tokens(message)
        self.messages.append(message)

    def add_messages(self, messages: list[Message]) -> None:
        """Add multiple messages."""
        for msg in messages:
            self.add_message(msg)

    def get_context(self, reserve_tokens: int = 0) -> list[Message]:
        """
        Get messages that fit within token budget.

        Args:
            reserve_tokens: Tokens to reserve for response generation

        Returns:
            List of messages (most recent first) that fit in context
        """
        available_tokens = self.max_tokens - reserve_tokens
        if self.system_message:
            available_tokens -= estimate_tokens(self.system_message)

        result = []
        total_tokens = 0

        # Iterate from most recent
        for msg in reversed(self.messages):
            msg_tokens = msg.token_count or estimate_message_tokens(msg)
            if total_tokens + msg_tokens > available_tokens:
                break
            result.insert(0, msg)
            total_tokens += msg_tokens

        return result

    def get_context_as_list(self, reserve_tokens: int = 0) -> list[dict[str, str]]:
        """Get context formatted for LLM API (role/content dicts)."""
        msgs = self.get_context(reserve_tokens)
        result = []
        if self.system_message:
            result.append({"role": "system", "content": self.system_message})
        result.extend([{"role": m.role, "content": m.content} for m in msgs])
        return result

    def total_tokens(self) -> int:
        """Get total token count of all messages."""
        return sum(m.token_count or estimate_message_tokens(m) for m in self.messages)

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def __len__(self) -> int:
        return len(self.messages)

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "max_messages": self.max_messages,
            "system_message": self.system_message,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlidingWindowManager:
        mgr = cls(
            max_tokens=data.get("max_tokens", 8000),
            max_messages=data.get("max_messages", 50),
            system_message=data.get("system_message"),
        )
        mgr.messages = deque(
            [Message.from_dict(m) for m in data.get("messages", [])],
            maxlen=mgr.max_messages,
        )
        return mgr


# ─── Summarization Manager ────────────────────────────────────────────────────


class SummarizationManager:
    """
    Manages conversation history with summarization strategy.

    Older messages are compressed into summaries to preserve
    semantic information while reducing token usage.
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        summary_trigger_tokens: int = 6000,
        summary_ratio: float = 0.3,  # Target summary size as fraction of original
        system_message: str | None = None,
        summarization_model: str | None = None,
    ):
        self.max_tokens = max_tokens
        self.summary_trigger_tokens = summary_trigger_tokens
        self.summary_ratio = summary_ratio
        self.system_message = system_message
        self.summarization_model = summarization_model

        # Active messages (recent, not summarized)
        self.messages: deque[Message] = deque()
        # Historical summaries
        self.summaries: list[ConversationSummary] = []

    def add_message(self, message: Message) -> None:
        """Add a message and check if summarization is needed."""
        if message.token_count is None:
            message.token_count = estimate_message_tokens(message)
        self.messages.append(message)

        # Check if we need to summarize
        if self._should_summarize():
            self._summarize_oldest()

    def _should_summarize(self) -> bool:
        """Check if summarization should be triggered."""
        total = self._count_active_tokens()
        return total > self.summary_trigger_tokens

    def _count_active_tokens(self) -> int:
        """Count tokens in active messages + summaries."""
        msg_tokens = sum(m.token_count or estimate_message_tokens(m) for m in self.messages)
        summary_tokens = sum(s.token_count for s in self.summaries)
        if self.system_message:
            summary_tokens += estimate_tokens(self.system_message)
        return msg_tokens + summary_tokens

    async def _summarize_oldest(self) -> None:
        """Summarize the oldest messages to free up context space."""
        if len(self.messages) < 3:
            return  # Not enough to summarize

        # Determine how many messages to summarize (keep at least 2 recent)
        messages_to_summarize = len(self.messages) - 2
        if messages_to_summarize < 2:
            return

        # Extract messages to summarize
        to_summarize = []
        for _ in range(messages_to_summarize):
            if self.messages:
                to_summarize.append(self.messages.popleft())

        if not to_summarize:
            return

        # Generate summary using LLM
        summary_text = await self._generate_summary(to_summarize)

        # Create summary object
        summary = ConversationSummary(
            summary=summary_text,
            start_index=0,  # Will be relative to current state
            end_index=len(to_summarize) - 1,
            message_count=len(to_summarize),
            token_count=estimate_tokens(summary_text),
        )

        self.summaries.append(summary)
        logger.info(
            "Conversation summarized",
            original_messages=len(to_summarize),
            summary_tokens=summary.token_count,
        )

    async def _generate_summary(self, messages: list[Message]) -> str:
        """Generate a summary of messages using LLM."""
        # Format messages for summarization
        conversation = "\n".join(f"{m.role.upper()}: {m.content}" for m in messages)

        prompt = f"""Summarize the following conversation concisely, preserving key facts, decisions, and context needed for future turns:

{conversation}

Summary:"""

        try:
            llm = get_llm(model=self.summarization_model)
            response = await llm.ainvoke(prompt)
            return (
                response.content.strip() if hasattr(response, "content") else str(response).strip()
            )
        except Exception as exc:
            logger.error("Summarization failed, using fallback", error=str(exc))
            # Fallback: simple concatenation of key points
            return self._fallback_summary(messages)

    def _fallback_summary(self, messages: list[Message]) -> str:
        """Fallback summary when LLM fails."""
        key_points = []
        for m in messages:
            # Take first 100 chars of each message as fallback
            truncated = m.content[:100] + "..." if len(m.content) > 100 else m.content
            key_points.append(f"{m.role}: {truncated}")
        return " | ".join(key_points)

    def get_context(self, reserve_tokens: int = 0) -> list[dict[str, str]]:
        """
        Get context with summaries + recent messages.

        Returns formatted messages for LLM API.
        """
        available_tokens = self.max_tokens - reserve_tokens
        if self.system_message:
            available_tokens -= estimate_tokens(self.system_message)

        result = []
        if self.system_message:
            result.append({"role": "system", "content": self.system_message})

        # Add summaries first (oldest first)
        summary_tokens = 0
        for summary in self.summaries:
            summary_content = f"[Summary of {summary.message_count} messages]: {summary.summary}"
            st = estimate_tokens(summary_content)
            if summary_tokens + st > available_tokens:
                break
            result.append({"role": "system", "content": summary_content})
            summary_tokens += st

        # Add recent messages (most recent last)
        remaining_tokens = available_tokens - summary_tokens
        msg_tokens = 0
        recent_messages = []

        for msg in reversed(self.messages):
            mt = msg.token_count or estimate_message_tokens(msg)
            if msg_tokens + mt > remaining_tokens:
                break
            recent_messages.insert(0, msg)
            msg_tokens += mt

        for msg in recent_messages:
            result.append({"role": msg.role, "content": msg.content})

        return result

    def total_tokens(self) -> int:
        """Get total token count including summaries."""
        return self._count_active_tokens()

    def clear(self) -> None:
        """Clear all messages and summaries."""
        self.messages.clear()
        self.summaries.clear()

    def __len__(self) -> int:
        return len(self.messages) + sum(s.message_count for s in self.summaries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "summary_trigger_tokens": self.summary_trigger_tokens,
            "summary_ratio": self.summary_ratio,
            "system_message": self.system_message,
            "summarization_model": self.summarization_model,
            "messages": [m.to_dict() for m in self.messages],
            "summaries": [s.to_dict() for s in self.summaries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SummarizationManager:
        mgr = cls(
            max_tokens=data.get("max_tokens", 8000),
            summary_trigger_tokens=data.get("summary_trigger_tokens", 6000),
            summary_ratio=data.get("summary_ratio", 0.3),
            system_message=data.get("system_message"),
            summarization_model=data.get("summarization_model"),
        )
        mgr.messages = deque([Message.from_dict(m) for m in data.get("messages", [])])
        mgr.summaries = [
            ConversationSummary(
                summary=s["summary"],
                start_index=s["start_index"],
                end_index=s["end_index"],
                message_count=s["message_count"],
                token_count=s["token_count"],
                created_at=datetime.fromisoformat(s["created_at"])
                if isinstance(s["created_at"], str)
                else s["created_at"],
            )
            for s in data.get("summaries", [])
        ]
        return mgr


# ─── Unified Context Manager ──────────────────────────────────────────────────


class ContextManager:
    """
    Unified context manager supporting multiple strategies.

    Strategies:
    - "sliding_window": Drop oldest messages when limit reached
    - "summarization": Compress oldest messages into summaries
    - "hybrid": Use sliding window for recent, summarization for older
    """

    def __init__(
        self,
        strategy: str = "hybrid",
        max_tokens: int = 8000,
        system_message: str | None = None,
        **kwargs,
    ):
        self.strategy = strategy
        self.max_tokens = max_tokens
        self.system_message = system_message

        if strategy == "sliding_window":
            self.manager = SlidingWindowManager(
                max_tokens=max_tokens,
                system_message=system_message,
                **kwargs,
            )
        elif strategy == "summarization":
            self.manager = SummarizationManager(
                max_tokens=max_tokens,
                system_message=system_message,
                **kwargs,
            )
        elif strategy == "hybrid":
            # Use sliding window for very recent, summarization for older
            self.window_manager = SlidingWindowManager(
                max_tokens=max_tokens // 2,
                system_message=system_message,
                **kwargs,
            )
            self.summary_manager = SummarizationManager(
                max_tokens=max_tokens // 2,
                system_message=None,  # System message in window manager
                **kwargs,
            )
            self.manager = None  # Use both
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def add_message(self, message: Message) -> None:
        """Add a message to the context."""
        if self.manager:
            self.manager.add_message(message)
        else:
            # Hybrid: add to window manager, it will handle summarization internally
            self.window_manager.add_message(message)
            # If window manager is full, move oldest to summarization
            if len(self.window_manager.messages) >= self.window_manager.max_messages:
                oldest = self.window_manager.messages.popleft()
                self.summary_manager.messages.append(oldest)
                if self.summary_manager._should_summarize():
                    import asyncio

                    asyncio.create_task(self.summary_manager._summarize_oldest())

    async def get_context(self, reserve_tokens: int = 0) -> list[dict[str, str]]:
        """Get formatted context for LLM."""
        if self.manager:
            return self.manager.get_context_as_list(reserve_tokens)

        # Hybrid: combine window + summaries
        window_msgs = self.window_manager.get_context(reserve_tokens)
        summary_context = self.summary_manager.get_context(reserve_tokens)

        # Combine: system + summaries + window messages
        result = []
        if self.system_message:
            result.append({"role": "system", "content": self.system_message})

        # Add summaries from summary manager
        for msg in summary_context:
            if msg.role == "system" and msg.content.startswith("[Summary"):
                result.append(msg)

        # Add window messages
        for msg in window_msgs:
            if not (msg.role == "system" and self.system_message):
                result.append(msg)

        return result

    def total_tokens(self) -> int:
        """Get total token count."""
        if self.manager:
            return self.manager.total_tokens()
        return self.window_manager.total_tokens() + self.summary_manager.total_tokens()

    def clear(self) -> None:
        """Clear all context."""
        if self.manager:
            self.manager.clear()
        else:
            self.window_manager.clear()
            self.summary_manager.clear()

    def __len__(self) -> int:
        if self.manager:
            return len(self.manager)
        return len(self.window_manager) + len(self.summary_manager)


# ─── Context Persistence ──────────────────────────────────────────────────────


class ContextStore:
    """Persists conversation context to database."""

    def __init__(self):
        self._cache: dict[str, ContextManager] = {}

    def _get_collection(self):
        from app.db.mongodb import Collections, get_collection

        return get_collection(Collections.CONVERSATION_CONTEXTS)

    async def save(self, conversation_id: str, context: ContextManager) -> None:
        """Save context to database."""
        coll = self._get_collection()
        data = {
            "conversation_id": conversation_id,
            "strategy": context.strategy,
            "data": context.to_dict()
            if hasattr(context, "to_dict")
            else context.manager.to_dict()
            if context.manager
            else {
                "window": context.window_manager.to_dict(),
                "summary": context.summary_manager.to_dict(),
            },
            "updated_at": datetime.now(UTC),
        }
        await coll.update_one(
            {"conversation_id": conversation_id},
            {"$set": data},
            upsert=True,
        )
        self._cache[conversation_id] = context

    async def load(self, conversation_id: str, **kwargs) -> ContextManager:
        """Load context from database."""
        if conversation_id in self._cache:
            return self._cache[conversation_id]

        coll = self._get_collection()
        doc = await coll.find_one({"conversation_id": conversation_id})

        if not doc:
            # Create new context
            context = ContextManager(**kwargs)
            self._cache[conversation_id] = context
            return context

        # Reconstruct context
        data = doc["data"]
        if "window" in data and "summary" in data:
            # Hybrid format
            context = ContextManager(
                strategy="hybrid",
                max_tokens=kwargs.get("max_tokens", 8000),
                system_message=kwargs.get("system_message"),
            )
            context.window_manager = SlidingWindowManager.from_dict(data["window"])
            context.summary_manager = SummarizationManager.from_dict(data["summary"])
        else:
            # Single manager format
            context = ContextManager(
                strategy=doc.get("strategy", "hybrid"),
                max_tokens=kwargs.get("max_tokens", 8000),
                system_message=kwargs.get("system_message"),
            )
            if context.manager:
                if isinstance(context.manager, SlidingWindowManager):
                    context.manager = SlidingWindowManager.from_dict(data)
                else:
                    context.manager = SummarizationManager.from_dict(data)

        self._cache[conversation_id] = context
        return context

    async def delete(self, conversation_id: str) -> None:
        """Delete context from database and cache."""
        coll = self._get_collection()
        await coll.delete_one({"conversation_id": conversation_id})
        self._cache.pop(conversation_id, None)


# Global context store
_context_store: ContextStore | None = None


def get_context_store() -> ContextStore:
    """Get the global context store."""
    global _context_store
    if _context_store is None:
        _context_store = ContextStore()
    return _context_store


# ─── Integration with Agent Graph ─────────────────────────────────────────────


async def manage_agent_context(
    analysis_id: str,
    user_id: str,
    new_messages: list[Message],
    strategy: str = "hybrid",
    max_tokens: int = 8000,
    system_message: str | None = None,
) -> list[dict[str, str]]:
    """
    Manage context for agent execution.

    Loads existing context, adds new messages, returns formatted context.
    """
    store = get_context_store()
    conversation_id = f"{user_id}:{analysis_id}"

    context = await store.load(
        conversation_id,
        strategy=strategy,
        max_tokens=max_tokens,
        system_message=system_message,
    )

    for msg in new_messages:
        context.add_message(msg)

    await store.save(conversation_id, context)

    return await context.get_context()


def get_context_config() -> dict[str, Any]:
    """Get context management configuration from models.yaml."""
    cfg = get_model_config()
    return {
        "strategy": getattr(cfg, "context_strategy", "hybrid"),
        "max_tokens": cfg.max_input_tokens,
        "summary_trigger_tokens": getattr(cfg, "summary_trigger_tokens", 6000),
        "summary_ratio": getattr(cfg, "summary_ratio", 0.3),
    }
