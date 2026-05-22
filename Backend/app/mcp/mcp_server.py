"""MCP Server — registers all tools and exposes them via the FastMCP protocol.

Uses fastmcp to create an in-process MCP server. Each tool delegates to existing
service/chain implementations without modifying them.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastmcp import FastMCP

from app.core.config import settings

logger = logging.getLogger("mcp.server")

# Create the MCP server instance
mcp_server = FastMCP(
    name=settings.MCP_SERVER_NAME if hasattr(settings, "MCP_SERVER_NAME") else "amzur-ai-tools",
)

logger.info(f"MCP Server '{mcp_server.name}' instance created.")


# ---------------------------------------------------------------------------
# Tool 1: arXiv Search
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="arxiv_search",
    description="Search arXiv academic papers by query. Returns a list of papers with title, authors, year, URL, and summary.",
)
async def arxiv_search(query: str) -> str:
    """Search arXiv for papers matching the query."""
    logger.debug(f"Tool 'arxiv_search' invoked with query='{query[:50]}...'")
    from app.tools.arxiv_tool import execute_arxiv_search
    result = await execute_arxiv_search(query)
    logger.debug(f"Tool 'arxiv_search' completed: success={result.get('success')}")
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 2: RAG Query
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="rag_query",
    description="Query uploaded PDF/document content using RAG (Retrieval Augmented Generation). Returns relevant text chunks from user's documents.",
)
async def rag_query(query: str, user_id: str, k: int = 4, attachment_ids: str = "") -> str:
    """Retrieve context from user's uploaded documents."""
    logger.debug(f"Tool 'rag_query' invoked: query='{query[:50]}', user_id='{user_id[:8]}...'")
    from app.tools.rag_tool import execute_rag_query
    ids = [aid.strip() for aid in attachment_ids.split(",") if aid.strip()] if attachment_ids else None
    result = await execute_rag_query(query, user_id, k, ids)
    logger.debug(f"Tool 'rag_query' completed: success={result.get('success')}")
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 3: SQL Query
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="sql_query",
    description="Execute a read-only SQL query against the PostgreSQL database. Input is a natural language question that gets converted to SQL.",
)
async def sql_query(question: str, user_email: str = "system") -> str:
    """Generate and execute SQL from a natural language question."""
    logger.debug(f"Tool 'sql_query' invoked: question='{question[:50]}'")
    from app.tools.sql_tool import execute_sql_query
    result = await execute_sql_query(question, user_email)
    logger.debug(f"Tool 'sql_query' completed: success={result.get('success')}")
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 4: Sheets/CSV/Excel Query
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="sheets_query",
    description="Query data from Google Sheets, CSV files, or Excel files using natural language. Requires source_type and either sheet_url or attachment_id.",
)
async def sheets_query(
    question: str,
    source_type: str,
    user_email: str = "system",
    sheet_url: str = "",
    attachment_id: str = "",
) -> str:
    """Query spreadsheet data with natural language."""
    logger.debug(f"Tool 'sheets_query' invoked: source_type='{source_type}', question='{question[:50]}'")
    from app.tools.sheets_tool import execute_sheets_query
    result = await execute_sheets_query(
        question=question,
        source_type=source_type,
        user_email=user_email,
        sheet_url=sheet_url or None,
        attachment_id=attachment_id or None,
    )
    logger.debug(f"Tool 'sheets_query' completed: success={result.get('success')}")
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 5: Tic Tac Toe Move
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="tic_tac_toe_move",
    description="Generate an AI move for Tic Tac Toe. Takes a 3x3 board state and difficulty level. Returns row, col, and reason.",
)
async def tic_tac_toe_move(board: str, difficulty: str = "hard") -> str:
    """Get the AI's next move for Tic Tac Toe."""
    logger.debug(f"Tool 'tic_tac_toe_move' invoked: difficulty='{difficulty}'")
    from app.tools.game_tool import execute_game_move
    board_list = json.loads(board) if isinstance(board, str) else board
    result = await execute_game_move(board_list, difficulty)
    logger.debug(f"Tool 'tic_tac_toe_move' completed: success={result.get('success')}")
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 6: Image Generation
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="generate_image",
    description="Generate an image from a text prompt using AI image generation models.",
)
async def generate_image(prompt: str, user_email: str = "system") -> str:
    """Generate an image from a text prompt."""
    logger.debug(f"Tool 'generate_image' invoked: prompt='{prompt[:50]}'")
    from app.tools.image_tool import execute_image_generation
    result = await execute_image_generation(prompt, user_email)
    logger.debug(f"Tool 'generate_image' completed: success={result.get('success')}")
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 7: Memory Retrieval
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="memory_retrieve",
    description="Retrieve recent conversation memory/history trimmed to the configured window size.",
)
async def memory_retrieve(history: str, window_size: int = 5) -> str:
    """Trim and retrieve conversation memory."""
    logger.debug(f"Tool 'memory_retrieve' invoked: window_size={window_size}")
    from app.tools.memory_tool import execute_memory_retrieve
    history_list = json.loads(history) if isinstance(history, str) else history
    result = execute_memory_retrieve(history_list, window_size)
    logger.debug(f"Tool 'memory_retrieve' completed: success={result.get('success')}")
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 8: Chat History Retrieval
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="chat_history",
    description="Retrieve chat message history for a specific thread. Returns messages with role and content.",
)
async def chat_history(thread_id: str, user_id: str, limit: int = 50) -> str:
    """Retrieve chat history for a thread."""
    logger.debug(f"Tool 'chat_history' invoked: thread_id='{thread_id[:8]}...', limit={limit}")
    from app.tools.chat_history_tool import execute_chat_history
    result = await execute_chat_history(thread_id, user_id, limit)
    logger.debug(f"Tool 'chat_history' completed: success={result.get('success')}")
    return json.dumps(result, ensure_ascii=False)
