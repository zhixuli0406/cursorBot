"""
Web interfaces for CursorBot

Provides:
- Dashboard: Admin control panel
- WebChat: Browser-based chat interface
- Control UI: Configuration management
"""

from .dashboard import create_dashboard_router, DashboardStats, DASHBOARD_HTML
from .webchat import create_webchat_router, WebChatManager, get_webchat_manager
from .control_ui import create_control_router, CONTROL_UI_HTML

__all__ = [
    # Dashboard
    "create_dashboard_router",
    "DashboardStats",
    "DASHBOARD_HTML",
    # WebChat
    "create_webchat_router",
    "WebChatManager",
    "get_webchat_manager",
    # Control UI
    "create_control_router",
    "CONTROL_UI_HTML",
]
