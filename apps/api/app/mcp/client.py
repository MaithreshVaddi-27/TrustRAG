"""
TRUSTRAG — Internal Model Context Protocol (MCP) Client Dispatcher.

Allows internal pipeline components (e.g. LangGraph Agent) to invoke
registered MCP tools via standardized JSON-RPC interface.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger
from app.mcp.server import handle_tool_call

logger = get_logger(__name__)


async def execute_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """
    Execute a registered MCP tool through the unified MCP dispatcher.
    Returns the parsed JSON response content.
    """
    logger.debug("Executing MCP tool", tool_name=tool_name, arguments=arguments)
    try:
        response = await handle_tool_call(tool_name, arguments)
        content_items = response.get("content", [])
        if not content_items:
            return None

        first_text = content_items[0].get("text", "")
        try:
            return json.loads(first_text)
        except Exception:
            return first_text

    except Exception as exc:
        logger.error("MCP tool execution failed", tool_name=tool_name, error=str(exc))
        raise
