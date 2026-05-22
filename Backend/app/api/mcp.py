"""MCP API router — exposes tool discovery, execution, and health endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.services.auth_service import AuthenticatedUser

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ToolExecuteRequest(BaseModel):
    tool: str = Field(..., description="Name of the MCP tool to execute")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolExecuteResponse(BaseModel):
    success: bool
    tool: str
    result: Any = None
    error: str | None = None


class MCPHealthResponse(BaseModel):
    status: str
    tools_registered: int
    tool_names: list[str]


class ToolInfo(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health", response_model=MCPHealthResponse)
async def mcp_health():
    """Check MCP server health and registered tool count."""
    from app.mcp.tool_registry import get_tool_registry

    registry = get_tool_registry()
    return MCPHealthResponse(
        status="ok" if registry.is_initialized else "degraded",
        tools_registered=registry.tool_count,
        tool_names=registry.get_tool_names(),
    )


@router.get("/tools", response_model=list[ToolInfo])
async def list_mcp_tools(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List all available MCP tools with metadata. Requires authentication."""
    from app.mcp.tool_registry import get_tool_registry

    registry = get_tool_registry()
    if not registry.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP tool registry not initialized",
        )

    tools = registry.get_available_tools()
    return [
        ToolInfo(
            name=t["name"],
            description=t.get("description", ""),
            input_schema=t.get("input_schema", {}),
        )
        for t in tools
    ]


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_mcp_tool(
    request: ToolExecuteRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Execute an MCP tool by name with the given arguments. Requires authentication."""
    from app.mcp.mcp_client import get_mcp_client, MCPClientError
    from app.mcp.tool_registry import get_tool_registry

    registry = get_tool_registry()
    if not registry.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP tool registry not initialized",
        )

    # Verify the tool exists
    tool_meta = registry.get_tool_by_name(request.tool)
    if tool_meta is None:
        return ToolExecuteResponse(
            success=False,
            tool=request.tool,
            error=f"Tool '{request.tool}' not registered",
        )

    # Execute via MCP client
    client = get_mcp_client()
    try:
        result = await client.call_tool(request.tool, request.arguments)
        return ToolExecuteResponse(
            success=result.get("success", False),
            tool=request.tool,
            result=result.get("result"),
            error=result.get("error"),
        )
    except MCPClientError as e:
        return ToolExecuteResponse(
            success=False,
            tool=request.tool,
            error=str(e),
        )


@router.get("/functions", response_model=list[dict[str, Any]])
async def get_openai_functions(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get tools in OpenAI function-calling format for LLM integration."""
    from app.mcp.tool_registry import get_tool_registry

    registry = get_tool_registry()
    if not registry.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP tool registry not initialized",
        )

    return registry.to_openai_tools()
