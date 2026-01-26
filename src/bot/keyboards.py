"""
Custom keyboard layouts for Telegram Bot
Provides interactive inline and reply keyboards
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Get the main menu reply keyboard.
    Shows common actions for quick access.
    """
    keyboard = [
        ["📊 狀態", "❓ 幫助"],
        ["💬 詢問", "📁 檔案"],
        ["🔍 搜尋", "📂 專案"],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_file_operations_keyboard(path: str = ".") -> InlineKeyboardMarkup:
    """
    Get inline keyboard for file operations.

    Args:
        path: Current directory path
    """
    keyboard = [
        [
            InlineKeyboardButton("📄 讀取", callback_data=f"file_read:{path}"),
            InlineKeyboardButton("📂 列出", callback_data=f"file_list:{path}"),
        ],
        [
            InlineKeyboardButton("⬆️ 上層目錄", callback_data="file_up"),
            InlineKeyboardButton("🔄 重整", callback_data=f"file_refresh:{path}"),
        ],
        [InlineKeyboardButton("❌ 關閉", callback_data="close")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    Get confirmation dialog keyboard.

    Args:
        action: Action identifier for callback
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ 確認", callback_data=f"confirm:{action}"),
            InlineKeyboardButton("❌ 取消", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_project_list_keyboard(projects: list[str]) -> InlineKeyboardMarkup:
    """
    Get project selection keyboard.

    Args:
        projects: List of project names
    """
    keyboard = [
        [InlineKeyboardButton(f"📁 {project}", callback_data=f"project_switch:{project}")]
        for project in projects[:10]  # Limit to 10 projects
    ]
    keyboard.append([InlineKeyboardButton("❌ 關閉", callback_data="close")])
    return InlineKeyboardMarkup(keyboard)


def get_search_results_keyboard(results: list[dict]) -> InlineKeyboardMarkup:
    """
    Get search results navigation keyboard.

    Args:
        results: List of search result items
    """
    keyboard = []

    for i, result in enumerate(results[:5]):  # Limit to 5 results
        file_path = result.get("path", "unknown")
        line_num = result.get("line", 0)
        display = f"{file_path}:{line_num}"
        if len(display) > 30:
            display = "..." + display[-27:]
        keyboard.append([
            InlineKeyboardButton(
                f"📄 {display}",
                callback_data=f"open_file:{file_path}:{line_num}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton("⬅️ 上一頁", callback_data="search_prev"),
        InlineKeyboardButton("➡️ 下一頁", callback_data="search_next"),
    ])
    keyboard.append([InlineKeyboardButton("❌ 關閉", callback_data="close")])

    return InlineKeyboardMarkup(keyboard)


def get_code_action_keyboard() -> InlineKeyboardMarkup:
    """Get code action selection keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🔨 執行", callback_data="code_run"),
            InlineKeyboardButton("📝 編輯", callback_data="code_edit"),
        ],
        [
            InlineKeyboardButton("📋 複製", callback_data="code_copy"),
            InlineKeyboardButton("💾 儲存", callback_data="code_save"),
        ],
        [InlineKeyboardButton("❌ 關閉", callback_data="close")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Get settings menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("🔔 通知設定", callback_data="settings_notifications")],
        [InlineKeyboardButton("🎨 顯示設定", callback_data="settings_display")],
        [InlineKeyboardButton("🔐 安全設定", callback_data="settings_security")],
        [InlineKeyboardButton("❌ 關閉", callback_data="close")],
    ]
    return InlineKeyboardMarkup(keyboard)


__all__ = [
    "get_main_menu_keyboard",
    "get_file_operations_keyboard",
    "get_confirmation_keyboard",
    "get_project_list_keyboard",
    "get_search_results_keyboard",
    "get_code_action_keyboard",
    "get_settings_keyboard",
]
