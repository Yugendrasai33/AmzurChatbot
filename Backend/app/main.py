from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.game import router as game_router
from app.api.rag import router as rag_router
from app.api.research import router as research_router
from app.api.sheets import router as sheets_router
from app.api.sql import router as sql_router
from app.api.threads import router as threads_router
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
app.include_router(rag_router)
app.include_router(research_router)
app.include_router(sheets_router)
app.include_router(sql_router)
app.include_router(threads_router)


@app.on_event("startup")
async def on_startup() -> None:
    if engine is not None:
        await ensure_tables(engine)
    else:
        print("Warning: Database engine not initialized. Database features unavailable.")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
