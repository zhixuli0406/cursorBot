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
from ..cursor.agent import CursorAgent
from ..utils.config import settings
from ..utils.logger import logger


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    telegram_bot: bool
    cursor_agent: bool


class AskRequest(BaseModel):
    """Request model for ask endpoint."""

    question: str
    user_id: Optional[int] = None


class CodeRequest(BaseModel):
    """Request model for code endpoint."""

    instruction: str
    file_path: Optional[str] = None


class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    query: str
    scope: Optional[str] = None


# Global instances
cursor_agent: Optional[CursorAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    global cursor_agent

    # Startup
    logger.info("Starting CursorBot API Server...")

    # Ensure directories exist
    settings.ensure_directories()

    # Initialize Cursor Agent
    cursor_agent = CursorAgent()
    await cursor_agent.connect()

    logger.info(f"API Server ready at http://{settings.server_host}:{settings.server_port}")

    yield

    # Shutdown
    logger.info("Shutting down CursorBot API Server...")

    if cursor_agent:
        await cursor_agent.disconnect()

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
        allow_origins=["*"],  # Configure appropriately for production
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
        """
        Health check endpoint.
        Returns status of all services.
        """
        tg_bot_status = False
        cursor_status = False

        try:
            bot = get_telegram_bot()
            tg_bot_status = bot._running if bot else False
        except Exception:
            pass

        if cursor_agent:
            status = await cursor_agent.get_status()
            cursor_status = status.get("connected", False)

        return HealthResponse(
            status="healthy" if (tg_bot_status or cursor_status) else "degraded",
            version="0.1.0",
            telegram_bot=tg_bot_status,
            cursor_agent=cursor_status,
        )

    @app.get("/status")
    async def get_status():
        """Get detailed system status."""
        if not cursor_agent:
            raise HTTPException(status_code=503, detail="Cursor Agent not initialized")

        return await cursor_agent.get_status()

    @app.post("/api/ask")
    async def ask_agent(request: AskRequest):
        """
        Ask a question to Cursor Agent.

        Args:
            request: Question request body

        Returns:
            Agent's response
        """
        if not cursor_agent:
            raise HTTPException(status_code=503, detail="Cursor Agent not available")

        response = await cursor_agent.ask(request.question)
        return {"response": response}

    @app.post("/api/code")
    async def execute_code(request: CodeRequest):
        """
        Execute a code instruction.

        Args:
            request: Code instruction request

        Returns:
            Execution result
        """
        if not cursor_agent:
            raise HTTPException(status_code=503, detail="Cursor Agent not available")

        result = await cursor_agent.execute_code_instruction(request.instruction)
        return {"result": result}

    @app.post("/api/search")
    async def search_code(request: SearchRequest):
        """
        Search code in workspace.

        Args:
            request: Search request

        Returns:
            Search results
        """
        if not cursor_agent:
            raise HTTPException(status_code=503, detail="Cursor Agent not available")

        results = await cursor_agent.search_code(request.query)
        return {"results": results}

    @app.get("/api/files")
    async def list_files(path: str = "."):
        """
        List files in directory.

        Args:
            path: Directory path

        Returns:
            List of files
        """
        if not cursor_agent:
            raise HTTPException(status_code=503, detail="Cursor Agent not available")

        files = await cursor_agent.list_files(path)
        return {"files": files}

    @app.get("/api/files/{file_path:path}")
    async def read_file(file_path: str):
        """
        Read file content.

        Args:
            file_path: Path to file

        Returns:
            File content
        """
        if not cursor_agent:
            raise HTTPException(status_code=503, detail="Cursor Agent not available")

        content = await cursor_agent.read_file(file_path)
        return {"content": content}

    @app.post("/webhook/telegram")
    async def telegram_webhook(request: Request):
        """
        Telegram webhook endpoint.
        Receives updates from Telegram servers.
        """
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
