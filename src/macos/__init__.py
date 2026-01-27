"""
macOS specific features for CursorBot

Includes:
- Menu Bar application
- Launch Agent management
"""

from .menubar import (
    CursorBotMenuBar,
    run_menubar,
    create_launch_agent,
    IS_MACOS,
    RUMPS_AVAILABLE,
)

__all__ = [
    "CursorBotMenuBar",
    "run_menubar",
    "create_launch_agent",
    "IS_MACOS",
    "RUMPS_AVAILABLE",
]
