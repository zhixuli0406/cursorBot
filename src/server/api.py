"""
FastAPI server for CursorBot
Provides REST API and webhook endpoints
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List

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
    uptime_seconds: float
    telegram_bot: bool
    discord_bot: bool
    llm_providers: List[str]
    memory_usage_mb: float


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""
    
    status: str
    version: str
    timestamp: str
    uptime_seconds: float
    
    # Services
    services: dict
    
    # LLM Providers
    llm: dict
    
    # System
    system: dict


class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    query: str


class BroadcastRequest(BaseModel):
    """Request model for broadcast endpoint."""
    
    message: str
    user_ids: Optional[List[int]] = None  # If None, broadcast to all allowed users
    parse_mode: Optional[str] = "HTML"


class UsageStatsResponse(BaseModel):
    """Usage statistics response model."""
    
    total_requests: int
    successful_requests: int
    failed_requests: int
    failover_requests: int
    total_input_chars: int
    total_output_chars: int
    total_time_seconds: float
    by_provider: dict


# Track server start time
_server_start_time: Optional[datetime] = None


# Global instances
workspace_agent: Optional[WorkspaceAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    global workspace_agent, _server_start_time

    # Startup
    logger.info("Starting CursorBot API Server...")
    _server_start_time = datetime.now()

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
    
    # Register web interfaces
    try:
        from ..web import create_dashboard_router, create_webchat_router, create_control_router
        application.include_router(create_dashboard_router())
        application.include_router(create_webchat_router())
        application.include_router(create_control_router())
        logger.info("Web interfaces registered: /dashboard, /chat, /control")
    except ImportError as e:
        logger.warning(f"Web interfaces not available: {e}")

    # Register social platform webhooks
    try:
        from .social_webhooks import router as social_router
        application.include_router(social_router)
        logger.info("Social webhooks registered: /webhook/line, /webhook/slack, /webhook/teams, /webhook/whatsapp, /webhook/google-chat")
    except ImportError as e:
        logger.warning(f"Social webhooks not available: {e}")

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
        import psutil
        
        tg_bot_status = False
        discord_bot_status = False
        bg_agent_status = False
        llm_providers = []
        active_tasks = 0
        
        # Check Telegram bot
        try:
            bot = get_telegram_bot()
            tg_bot_status = bot._running if bot else False
        except Exception:
            pass
        
        # Check Discord bot
        try:
            from ..channels.discord_channel import get_discord_bot
            discord_bot = get_discord_bot()
            discord_bot_status = discord_bot.is_ready() if discord_bot else False
        except Exception:
            pass
        
        # Check LLM providers
        try:
            from ..core.llm_providers import get_llm_manager
            manager = get_llm_manager()
            llm_providers = manager.list_available_providers()
        except Exception:
            pass
        
        # Get memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Calculate uptime
        uptime = 0.0
        if _server_start_time:
            uptime = (datetime.now() - _server_start_time).total_seconds()
        
        # Determine overall status
        status = "healthy"
        if not tg_bot_status and not discord_bot_status:
            status = "degraded"
        if not llm_providers:
            status = "degraded"

        return HealthResponse(
            status=status,
            version="0.2.0",
            uptime_seconds=round(uptime, 2),
            telegram_bot=tg_bot_status,
            discord_bot=discord_bot_status,
            llm_providers=llm_providers,
            memory_usage_mb=round(memory_mb, 2),
        )
    
    @app.get("/health/detailed", response_model=DetailedHealthResponse)
    async def detailed_health_check():
        """Detailed health check with all system information."""
        import psutil
        import platform
        
        # Get basic health info
        health = await health_check()
        
        # LLM provider details
        llm_info = {"providers": [], "usage_stats": {}}
        try:
            from ..core.llm_providers import get_llm_manager
            manager = get_llm_manager()
            llm_info["providers"] = manager.list_available_providers()
            llm_info["usage_stats"] = manager.get_usage_stats()
            status = manager.get_current_status()
            llm_info["current_provider"] = status.get("current_provider")
            llm_info["current_model"] = status.get("current_model")
        except Exception as e:
            llm_info["error"] = str(e)
        
        # System info
        process = psutil.Process()
        system_info = {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "process_memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "process_threads": process.num_threads(),
        }
        
        return DetailedHealthResponse(
            status=health.status,
            version="0.2.0",
            timestamp=datetime.now().isoformat(),
            uptime_seconds=health.uptime_seconds,
            services={
                "telegram_bot": health.telegram_bot,
                "discord_bot": health.discord_bot,
                "api_server": True,
            },
            llm=llm_info,
            system=system_info,
        )
    
    @app.get("/api/usage", response_model=UsageStatsResponse)
    async def get_usage_stats():
        """Get LLM usage statistics."""
        try:
            from ..core.llm_providers import get_llm_manager
            manager = get_llm_manager()
            stats = manager.get_usage_stats()
            return UsageStatsResponse(**stats)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/broadcast")
    async def broadcast_message(request: BroadcastRequest):
        """
        Broadcast a message to users.
        Requires admin API key.
        """
        try:
            bot = get_telegram_bot()
            if not bot or not bot.app:
                raise HTTPException(status_code=503, detail="Telegram bot not available")
            
            # Get target users
            target_users = request.user_ids
            if not target_users:
                # Broadcast to all allowed users
                target_users = settings.telegram_allowed_users
            
            if not target_users:
                raise HTTPException(status_code=400, detail="No target users specified")
            
            # Send messages
            sent_count = 0
            failed_count = 0
            
            for user_id in target_users:
                try:
                    await bot.bot.send_message(
                        chat_id=user_id,
                        text=request.message,
                        parse_mode=request.parse_mode,
                    )
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send broadcast to {user_id}: {e}")
                    failed_count += 1
            
            return {
                "success": True,
                "sent": sent_count,
                "failed": failed_count,
                "total": len(target_users),
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

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
