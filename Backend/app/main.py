from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging so MCP lifecycle logs are visible in the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-14s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
# Set MCP loggers to DEBUG for detailed tool execution logs
logging.getLogger("mcp").setLevel(logging.DEBUG)

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.game import router as game_router
from app.api.mcp import router as mcp_router
from app.api.rag import router as rag_router
from app.api.research import router as research_router
from app.api.sheets import router as sheets_router
from app.api.sql import router as sql_router
from app.api.threads import router as threads_router
from app.api.tickets import router as tickets_router
from app.db.bootstrap import ensure_tables
from app.db.session import engine

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(game_router)
app.include_router(mcp_router)
app.include_router(rag_router)
app.include_router(research_router)
app.include_router(sheets_router)
app.include_router(sql_router)
app.include_router(threads_router)
app.include_router(tickets_router)


@app.on_event("startup")
async def on_startup() -> None:
    if engine is not None:
        await ensure_tables(engine)
    else:
        print("Warning: Database engine not initialized. Database features unavailable.")

    # Initialize MCP server, client, and tool registry
    try:
        from app.mcp.mcp_client import initialize_mcp_client
        from app.mcp.tool_registry import initialize_tool_registry

        logger = logging.getLogger("mcp")
        logger.info("MCP lifecycle: startup initiated")
        await initialize_mcp_client()
        await initialize_tool_registry()
        logger.info("MCP lifecycle: startup complete — all systems operational")
    except Exception as e:
        logging.getLogger("mcp").error(f"MCP lifecycle: startup FAILED — {e}", exc_info=True)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    try:
        from app.mcp.mcp_client import shutdown_mcp_client
        logger = logging.getLogger("mcp")
        logger.info("MCP lifecycle: shutdown initiated")
        await shutdown_mcp_client()
        logger.info("MCP lifecycle: shutdown complete")
    except Exception as e:
        logging.getLogger("mcp").error(f"MCP lifecycle: shutdown error — {e}")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
