"""Tests for MCP integration — server, client, tool registry, and API endpoints."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# MCP Server tests
# ---------------------------------------------------------------------------

class TestMCPServer:
    """Test that the MCP server registers all tools correctly."""

    def test_server_instance_exists(self):
        from app.mcp.mcp_server import mcp_server
        assert mcp_server is not None

    @pytest.mark.asyncio
    async def test_server_has_tools_registered(self):
        from app.mcp.mcp_server import mcp_server
        tools = await mcp_server.list_tools()
        assert len(tools) == 8

    @pytest.mark.asyncio
    async def test_server_tool_names(self):
        from app.mcp.mcp_server import mcp_server
        tools = await mcp_server.list_tools()
        tool_names = {t.name for t in tools}
        expected = {
            "arxiv_search",
            "rag_query",
            "sql_query",
            "sheets_query",
            "tic_tac_toe_move",
            "generate_image",
            "memory_retrieve",
            "chat_history",
        }
        assert tool_names == expected


# ---------------------------------------------------------------------------
# MCP Client tests
# ---------------------------------------------------------------------------

class TestMCPClient:
    """Test the MCP client connection and tool calling."""

    @pytest.mark.asyncio
    async def test_client_connect_disconnect(self):
        from app.mcp.mcp_client import MCPClient
        client = MCPClient()
        assert not client.is_connected
        await client.connect()
        assert client.is_connected
        await client.disconnect()
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_client_list_tools(self):
        from app.mcp.mcp_client import MCPClient
        client = MCPClient()
        await client.connect()
        tools = await client.list_tools()
        assert isinstance(tools, list)
        assert len(tools) == 8
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_client_call_nonexistent_tool(self):
        from app.mcp.mcp_client import MCPClient
        client = MCPClient()
        await client.connect()
        result = await client.call_tool("nonexistent_tool", {})
        assert result["success"] is False
        assert "not registered" in result["error"]
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_client_not_connected_error(self):
        from app.mcp.mcp_client import MCPClient, MCPClientError
        client = MCPClient()
        with pytest.raises(MCPClientError, match="not connected"):
            await client.list_tools()


# ---------------------------------------------------------------------------
# Tool Registry tests
# ---------------------------------------------------------------------------

class TestToolRegistry:
    """Test tool registry initialization and schema conversion."""

    @pytest.mark.asyncio
    async def test_registry_initialization(self):
        from app.mcp.mcp_client import MCPClient
        from app.mcp.tool_registry import ToolRegistry

        # Need client connected for registry to work
        client = MCPClient()
        await client.connect()

        registry = ToolRegistry()
        with patch("app.mcp.tool_registry.get_mcp_client", return_value=client):
            await registry.initialize()

        assert registry.is_initialized
        assert registry.tool_count == 8
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_registry_get_tool_by_name(self):
        from app.mcp.mcp_client import MCPClient
        from app.mcp.tool_registry import ToolRegistry

        client = MCPClient()
        await client.connect()

        registry = ToolRegistry()
        with patch("app.mcp.tool_registry.get_mcp_client", return_value=client):
            await registry.initialize()

        tool = registry.get_tool_by_name("arxiv_search")
        assert tool is not None
        assert tool["name"] == "arxiv_search"

        missing = registry.get_tool_by_name("nonexistent")
        assert missing is None
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_registry_openai_format(self):
        from app.mcp.mcp_client import MCPClient
        from app.mcp.tool_registry import ToolRegistry

        client = MCPClient()
        await client.connect()

        registry = ToolRegistry()
        with patch("app.mcp.tool_registry.get_mcp_client", return_value=client):
            await registry.initialize()

        functions = registry.to_openai_functions()
        assert isinstance(functions, list)
        assert len(functions) == 8
        for fn in functions:
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn

        tools = registry.to_openai_tools()
        assert isinstance(tools, list)
        for t in tools:
            assert t["type"] == "function"
            assert "function" in t

        await client.disconnect()


# ---------------------------------------------------------------------------
# Tool wrapper tests
# ---------------------------------------------------------------------------

class TestToolWrappers:
    """Test individual tool wrappers with validation."""

    @pytest.mark.asyncio
    async def test_arxiv_empty_query(self):
        from app.tools.arxiv_tool import execute_arxiv_search
        result = await execute_arxiv_search("")
        assert result["success"] is False
        assert "empty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rag_empty_query(self):
        from app.tools.rag_tool import execute_rag_query
        result = await execute_rag_query("", "user-123")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_rag_empty_user_id(self):
        from app.tools.rag_tool import execute_rag_query
        result = await execute_rag_query("test query", "")
        assert result["success"] is False
        assert "user_id" in result["error"]

    @pytest.mark.asyncio
    async def test_sql_empty_question(self):
        from app.tools.sql_tool import execute_sql_query
        result = await execute_sql_query("")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_game_invalid_board(self):
        from app.tools.game_tool import execute_game_move
        result = await execute_game_move([[""]], "hard")
        assert result["success"] is False
        assert "3x3" in result["error"]

    @pytest.mark.asyncio
    async def test_game_invalid_difficulty(self):
        from app.tools.game_tool import execute_game_move
        board = [["", "", ""], ["", "", ""], ["", "", ""]]
        result = await execute_game_move(board, "impossible")
        assert result["success"] is False
        assert "difficulty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_game_invalid_cell_value(self):
        from app.tools.game_tool import execute_game_move
        board = [["Z", "", ""], ["", "", ""], ["", "", ""]]
        result = await execute_game_move(board, "hard")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_image_empty_prompt(self):
        from app.tools.image_tool import execute_image_generation
        result = await execute_image_generation("")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_image_short_prompt(self):
        from app.tools.image_tool import execute_image_generation
        result = await execute_image_generation("hi")
        assert result["success"] is False
        assert "10 characters" in result["error"]

    def test_memory_invalid_history(self):
        from app.tools.memory_tool import execute_memory_retrieve
        result = execute_memory_retrieve("not a list")
        assert result["success"] is False

    def test_memory_valid(self):
        from app.tools.memory_tool import execute_memory_retrieve
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = execute_memory_retrieve(history, window_size=5)
        assert result["success"] is True
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_chat_history_invalid_uuid(self):
        from app.tools.chat_history_tool import execute_chat_history
        result = await execute_chat_history("not-a-uuid", "also-not-uuid")
        assert result["success"] is False
        assert "UUID" in result["error"]

    @pytest.mark.asyncio
    async def test_sheets_invalid_source_type(self):
        from app.tools.sheets_tool import execute_sheets_query
        result = await execute_sheets_query("test", "invalid_type")
        assert result["success"] is False
        assert "source_type" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_sheets_missing_url(self):
        from app.tools.sheets_tool import execute_sheets_query
        result = await execute_sheets_query("test", "google_sheet")
        assert result["success"] is False
        assert "sheet_url" in result["error"]
