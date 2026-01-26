"""
Logging configuration for CursorBot
Uses loguru for structured and colorful logging
"""

import sys
from pathlib import Path

from loguru import logger

from .config import settings


def setup_logger() -> None:
    """
    Configure the logger with appropriate handlers and formats.
    Sets up both console and file logging.
    """
    # Remove default handler
    logger.remove()

    # Console handler with colors
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=settings.log_level,
        colorize=True,
    )

    # File handler with rotation
    log_path = Path(settings.log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        settings.log_file_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=settings.log_level,
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="7 days",  # Keep logs for 7 days
        compression="zip",  # Compress rotated logs
        encoding="utf-8",
    )

    logger.info(f"Logger initialized with level: {settings.log_level}")


# Initialize logger on module import
setup_logger()

__all__ = ["logger"]
