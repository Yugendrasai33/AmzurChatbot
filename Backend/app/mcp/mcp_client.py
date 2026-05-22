"""MCP Client — connects to the in-process MCP server for tool discovery and execution.

Provides an async interface for:
- Listing available tools (with metadata)
- Calling tools by name with arguments
- Handling timeouts and errors gracefully
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from app.mcp.mcp_server import mcp_server

logger = logging.getLogger("mcp.client")


class MCPClientError(Exception):
    """Raised when the MCP client encounters an error."""
    pass


class MCPClient:
    """In-process MCP client that communicates directly with the FastMCP server instance."""

    def __init__(self, timeout: float = 30.0):
        self._timeout = timeout
        self._connected = False
        self._tools_cache: list[dict[str, Any]] | None = None

    async def connect(self) -> None:
        """Initialize connection to the MCP server."""
        logger.info("MCP Client connecting to in-process server...")
        self._connected = True
        # Pre-cache tool list on connect
        self._tools_cache = None
        logger.info("MCP Client connected successfully.")

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        logger.info("MCP Client disconnecting...")
        self._connected = False
        self._tools_cache = None
        logger.info("MCP Client disconnected.")

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools with their metadata.

        Returns a list of tool descriptors with name, description, and input schema.
        """
        if not self._connected:
            raise MCPClientError("Client is not connected. Call connect() first.")

        if self._tools_cache is not None:
            return self._tools_cache

        try:
            logger.debug("Discovering tools from MCP server...")
            tools = await mcp_server.list_tools()
            tool_list = []
            for tool in tools:
                tool_info = {
                    "name": tool.name if hasattr(tool, "name") else str(tool),
                    "description": tool.description if hasattr(tool, "description") else "",
                    "input_schema": tool.parameters if hasattr(tool, "parameters") else {},
                }
                tool_list.append(tool_info)
            self._tools_cache = tool_list
            logger.info(f"Tool discovery complete: {len(tool_list)} tools found.")
            return tool_list
        except Exception as e:
            logger.error(f"Tool discovery failed: {e}")
            raise MCPClientError(f"Failed to list tools: {e}") from e

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a tool by name with the given arguments.

        Returns a dict with keys: success, result (or error).
        Enforces a timeout to prevent hung tool calls.
        """
        if not self._connected:
            raise MCPClientError("Client is not connected. Call connect() first.")

        arguments = arguments or {}
        logger.info(f"Calling tool '{name}' with arguments: {list(arguments.keys())}")
        start = time.perf_counter()

        try:
            result = await asyncio.wait_for(
                self._execute_tool(name, arguments),
                timeout=self._timeout,
            )
            elapsed = time.perf_counter() - start
            logger.info(f"Tool '{name}' executed successfully in {elapsed:.3f}s")
            return {"success": True, "result": result, "tool": name}
        except asyncio.TimeoutError:
            elapsed = time.perf_counter() - start
            logger.warning(f"Tool '{name}' timed out after {elapsed:.3f}s (limit: {self._timeout}s)")
            return {"success": False, "error": f"Tool '{name}' execution timed out after {self._timeout}s", "tool": name}
        except MCPClientError as e:
            elapsed = time.perf_counter() - start
            logger.error(f"Tool '{name}' client error after {elapsed:.3f}s: {e}")
            return {"success": False, "error": str(e), "tool": name}
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.error(f"Tool '{name}' unexpected error after {elapsed:.3f}s: {e}")
            return {"success": False, "error": f"Tool execution failed: {e}", "tool": name}

    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Internal: look up and invoke the tool on the MCP server."""
        # Get the tool function from the server
        tools = await mcp_server.list_tools()
        tool_fn = None

        for tool in tools:
            tool_name = tool.name if hasattr(tool, "name") else str(tool)
            if tool_name == name:
                tool_fn = tool
                break

        if tool_fn is None:
            raise MCPClientError(f"Tool '{name}' not registered on MCP server")

        # Call the tool through the server's call mechanism
        result = await mcp_server.call_tool(name, arguments)

        # Parse JSON result if it's a string
        if isinstance(result, str):
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return result

        # Handle fastmcp result objects
        if hasattr(result, "content"):
            # Extract text content from MCP result
            content_parts = result.content if isinstance(result.content, list) else [result.content]
            text_parts = []
            for part in content_parts:
                if hasattr(part, "text"):
                    text_parts.append(part.text)
                elif isinstance(part, str):
                    text_parts.append(part)
            combined = "\n".join(text_parts)
            try:
                return json.loads(combined)
            except (json.JSONDecodeError, TypeError):
                return combined

        return result


# Singleton client instance
_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    """Get the singleton MCP client instance."""
    global _client
    if _client is None:
        _client = MCPClient()
    return _client


async def initialize_mcp_client() -> MCPClient:
    """Initialize and connect the MCP client. Called during app startup."""
    logger.info("Initializing MCP client...")
    client = get_mcp_client()
    if not client.is_connected:
        await client.connect()
    logger.info("MCP client initialization complete.")
    return client


async def shutdown_mcp_client() -> None:
    """Disconnect the MCP client. Called during app shutdown."""
    global _client
    logger.info("Shutting down MCP client...")
    if _client and _client.is_connected:
        await _client.disconnect()
    _client = None
    logger.info("MCP client shutdown complete.")
