"""
FastAPI server for CursorBot
Provides REST API and webhook endpoints
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..bot.telegram_bot import get_telegram_bot
from ..cursor.agent import WorkspaceAgent
from ..utils.config import settings
from ..utils.logger import logger


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    telegram_bot: bool


class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    query: str


# Global instances
workspace_agent: Optional[WorkspaceAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    global workspace_agent

    # Startup
    logger.info("Starting CursorBot API Server...")

    # Ensure directories exist
    settings.ensure_directories()

    # Initialize Workspace Agent
    workspace_agent = WorkspaceAgent()

    logger.info(f"API Server ready at http://{settings.server_host}:{settings.server_port}")

    yield

    # Shutdown
    logger.info("Shutting down CursorBot API Server...")
    logger.info("Server shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI instance
    """
    application = FastAPI(
        title="CursorBot API",
        description="Remote control API for Cursor Agent via Telegram",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    register_routes(application)

    return application


def register_routes(app: FastAPI) -> None:
    """Register all API routes."""

    @app.get("/", response_model=dict)
    async def root():
        """Root endpoint with basic info."""
        return {
            "name": "CursorBot API",
            "version": "0.1.0",
            "docs": "/docs",
        }

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint."""
        tg_bot_status = False

        try:
            bot = get_telegram_bot()
            tg_bot_status = bot._running if bot else False
        except Exception:
            pass

        return HealthResponse(
            status="healthy" if tg_bot_status else "degraded",
            version="0.1.0",
            telegram_bot=tg_bot_status,
        )

    @app.get("/status")
    async def get_status():
        """Get workspace status."""
        if not workspace_agent:
            raise HTTPException(status_code=503, detail="Workspace Agent not initialized")

        info = await workspace_agent.get_workspace_info()
        return {
            "workspace": info["name"],
            "path": info["path"],
            "total_files": info["total_files"],
        }

    @app.post("/api/search")
    async def search_code(request: SearchRequest):
        """Search code in workspace."""
        if not workspace_agent:
            raise HTTPException(status_code=503, detail="Workspace Agent not available")

        results = await workspace_agent.search_code(request.query)
        return {"results": results}

    @app.get("/api/files")
    async def list_files(path: str = "."):
        """List files in directory."""
        if not workspace_agent:
            raise HTTPException(status_code=503, detail="Workspace Agent not available")

        files = await workspace_agent.list_files(path)
        return {"files": files}

    @app.get("/api/files/{file_path:path}")
    async def read_file(file_path: str):
        """Read file content."""
        if not workspace_agent:
            raise HTTPException(status_code=503, detail="Workspace Agent not available")

        content = await workspace_agent.read_file(file_path)
        return {"content": content}

    @app.get("/api/workspaces")
    async def list_workspaces():
        """List available workspaces."""
        if not workspace_agent:
            raise HTTPException(status_code=503, detail="Workspace Agent not available")

        workspaces = await workspace_agent.list_workspaces()
        return {"workspaces": workspaces}

    @app.post("/webhook/telegram")
    async def telegram_webhook(request: Request):
        """Telegram webhook endpoint."""
        try:
            data = await request.json()
            bot = get_telegram_bot()

            if bot and bot.app:
                from telegram import Update
                update = Update.de_json(data, bot.bot)
                await bot.app.process_update(update)

            return Response(status_code=200)
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler."""
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )


# Create default app instance
app = create_app()

__all__ = ["app", "create_app"]
