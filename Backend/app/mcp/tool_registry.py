"""Tool Registry — dynamic discovery and OpenAI function-calling format conversion.

On startup, queries the MCP server for available tools and caches their metadata.
Provides helpers to convert tool schemas into OpenAI-compatible function definitions
for LLM consumption.
"""
from __future__ import annotations

import logging
from typing import Any

from app.mcp.mcp_client import get_mcp_client, MCPClientError

logger = logging.getLogger("mcp.registry")


class ToolRegistry:
    """Manages discovered MCP tools and converts schemas for LLM function calling."""

    def __init__(self):
        self._tools: list[dict[str, Any]] = []
        self._tools_by_name: dict[str, dict[str, Any]] = {}
        self._initialized: bool = False

    async def initialize(self) -> None:
        """Discover tools from MCP server and cache them."""
        logger.info("Tool registry: discovering tools from MCP server...")
        client = get_mcp_client()
        try:
            self._tools = await client.list_tools()
            self._tools_by_name = {t["name"]: t for t in self._tools}
            self._initialized = True
            logger.info(f"Tool registry initialized: {len(self._tools)} tools registered.")
            for t in self._tools:
                logger.info(f"  ├── {t['name']}: {t.get('description', '')[:60]}")
        except MCPClientError as e:
            logger.error(f"Tool registry initialization failed: {e}")
            self._tools = []
            self._tools_by_name = {}
            self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Return all registered tool descriptors."""
        return list(self._tools)

    def get_tool_by_name(self, name: str) -> dict[str, Any] | None:
        """Return a single tool's metadata by name."""
        return self._tools_by_name.get(name)

    def get_tool_names(self) -> list[str]:
        """Return list of all registered tool names."""
        return list(self._tools_by_name.keys())

    def to_openai_functions(self) -> list[dict[str, Any]]:
        """Convert all registered tools to OpenAI function-calling format.

        Returns a list suitable for the `functions` parameter of an OpenAI chat completion.
        """
        functions = []
        for tool in self._tools:
            fn_def = self._tool_to_openai_function(tool)
            if fn_def:
                functions.append(fn_def)
        return functions

    def to_openai_tools(self) -> list[dict[str, Any]]:
        """Convert all registered tools to OpenAI tools format (newer API).

        Returns a list suitable for the `tools` parameter of an OpenAI chat completion.
        """
        tools = []
        for tool in self._tools:
            fn_def = self._tool_to_openai_function(tool)
            if fn_def:
                tools.append({"type": "function", "function": fn_def})
        return tools

    def _tool_to_openai_function(self, tool: dict[str, Any]) -> dict[str, Any] | None:
        """Convert a single MCP tool descriptor to an OpenAI function definition."""
        name = tool.get("name")
        if not name:
            return None

        description = tool.get("description", "")
        input_schema = tool.get("input_schema", {})

        # Build parameters schema from input_schema
        parameters = self._normalize_schema(input_schema)

        return {
            "name": name,
            "description": description,
            "parameters": parameters,
        }

    def _normalize_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Normalize an MCP input schema to a valid JSON Schema for OpenAI."""
        if not schema:
            return {"type": "object", "properties": {}, "required": []}

        # If it's already a proper JSON schema, return as-is
        if "type" in schema and schema["type"] == "object":
            return schema

        # Wrap raw properties into a proper schema
        if "properties" in schema:
            return {
                "type": "object",
                "properties": schema["properties"],
                "required": schema.get("required", []),
            }

        return {"type": "object", "properties": {}, "required": []}


# Singleton registry
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the singleton tool registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


async def initialize_tool_registry() -> ToolRegistry:
    """Initialize the tool registry. Called during app startup after MCP client connects."""
    registry = get_tool_registry()
    if not registry.is_initialized:
        await registry.initialize()
    return registry
