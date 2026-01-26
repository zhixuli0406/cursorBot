"""
CursorBot Main Entry Point
Starts both Telegram Bot and API Server
"""

import asyncio
import signal
import sys
from typing import Optional

import uvicorn

from .bot.telegram_bot import CursorTelegramBot, get_telegram_bot
from .server.api import app
from .utils.config import settings
from .utils.logger import logger
from .utils.task_queue import get_task_queue


class CursorBotApp:
    """
    Main application class that coordinates all services.
    Manages Telegram Bot and API Server lifecycle.
    """

    def __init__(self):
        self.telegram_bot: Optional[CursorTelegramBot] = None
        self.server_task: Optional[asyncio.Task] = None
        self.bot_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def start_telegram_bot(self) -> None:
        """Start the Telegram bot."""
        try:
            self.telegram_bot = get_telegram_bot()
            await self.telegram_bot.start()
        except Exception as e:
            logger.error(f"Telegram bot error: {e}")
            raise

    async def start_api_server(self) -> None:
        """Start the FastAPI server."""
        config = uvicorn.Config(
            app=app,
            host=settings.server_host,
            port=settings.server_port,
            log_level="info" if settings.debug else "warning",
        )
        server = uvicorn.Server(config)

        try:
            await server.serve()
        except Exception as e:
            logger.error(f"API server error: {e}")
            raise

    async def run(self) -> None:
        """
        Run all services concurrently.
        """
        logger.info("=" * 50)
        logger.info("Starting CursorBot")
        logger.info("=" * 50)

        # Setup signal handlers
        self._setup_signal_handlers()

        # Ensure directories exist
        settings.ensure_directories()

        try:
            # Initialize and start task queue
            task_queue = get_task_queue()
            await task_queue.start()
            logger.info("Task queue started")

            # Start services concurrently
            self.bot_task = asyncio.create_task(
                self.start_telegram_bot(),
                name="telegram_bot",
            )
            self.server_task = asyncio.create_task(
                self.start_api_server(),
                name="api_server",
            )

            # Wait for shutdown signal or task completion
            done, pending = await asyncio.wait(
                [self.bot_task, self.server_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Check for errors
            for task in done:
                if task.exception():
                    logger.error(f"Task {task.get_name()} failed: {task.exception()}")

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except asyncio.CancelledError:
            logger.info("Application cancelled")
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully shutdown all services."""
        logger.info("Shutting down CursorBot...")

        # Stop task queue
        task_queue = get_task_queue()
        await task_queue.stop()

        # Stop Telegram bot
        if self.telegram_bot:
            await self.telegram_bot.stop()

        # Cancel tasks
        for task in [self.bot_task, self.server_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("CursorBot shutdown complete")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self._handle_signal()),
            )

    async def _handle_signal(self) -> None:
        """Handle shutdown signal."""
        logger.info("Received shutdown signal")
        self._shutdown_event.set()

        # Cancel running tasks
        if self.bot_task:
            self.bot_task.cancel()
        if self.server_task:
            self.server_task.cancel()


def main() -> None:
    """Main entry point."""
    # Print startup banner
    print("""
    ╔═══════════════════════════════════════════════╗
    ║                                               ║
    ║   🤖 CursorBot - Telegram Remote Control      ║
    ║                                               ║
    ║   Control Cursor Agent from anywhere!         ║
    ║                                               ║
    ╚═══════════════════════════════════════════════╝
    """)

    # Validate configuration
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is required!")
        logger.info("Please set it in your .env file or environment variables")
        sys.exit(1)

    if not settings.allowed_user_ids:
        logger.warning("No TELEGRAM_ALLOWED_USERS configured. Bot will reject all users.")

    # Run application
    app_instance = CursorBotApp()

    try:
        asyncio.run(app_instance.run())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
