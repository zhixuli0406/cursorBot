"""
Custom keyboard layouts for Telegram Bot
Provides interactive inline and reply keyboards for CursorBot

Features inspired by cursor-telegram-bot and ClawBot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Get the main menu reply keyboard.
    Shows common actions for quick access.
    """
    keyboard = [
        ["📊 狀態", "❓ 幫助"],
        ["📋 任務", "📁 倉庫"],
        ["🔍 搜尋", "⚙️ 設定"],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


# ============================================
# Task Management Keyboards
# ============================================


def get_task_keyboard(task_id: str, status: str = "running") -> InlineKeyboardMarkup:
    """
    Get task action keyboard with buttons.

    Args:
        task_id: The task/composer ID
        status: Current task status
    """
    keyboard = []

    # Open in Cursor button (external link)
    cursor_url = f"https://cursor.com/agents/{task_id}"
    keyboard.append([
        InlineKeyboardButton("🔗 在 Cursor 開啟", url=cursor_url)
    ])

    # Action buttons based on status
    if status in ["running", "pending", "created"]:
        keyboard.append([
            InlineKeyboardButton("🔄 重新整理", callback_data=f"task_refresh:{task_id[:8]}"),
            InlineKeyboardButton("❌ 取消任務", callback_data=f"task_cancel:{task_id[:8]}"),
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🔄 重新整理", callback_data=f"task_refresh:{task_id[:8]}"),
            InlineKeyboardButton("📋 複製結果", callback_data=f"task_copy:{task_id[:8]}"),
        ])

    # Follow-up button
    keyboard.append([
        InlineKeyboardButton("💬 追問", callback_data=f"task_followup:{task_id[:8]}")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_task_list_keyboard(tasks: list[dict]) -> InlineKeyboardMarkup:
    """
    Get task list selection keyboard.

    Args:
        tasks: List of task dictionaries
    """
    keyboard = []

    for task in tasks[:8]:  # Limit to 8 tasks
        task_id = task.get("composer_id", "")[:8]
        status = task.get("status", "unknown")
        prompt = task.get("prompt", "")[:20] + "..." if len(task.get("prompt", "")) > 20 else task.get("prompt", "")

        # Status emoji
        emoji = {
            "running": "🔄",
            "pending": "⏳",
            "created": "🆕",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "🚫",
        }.get(status, "❓")

        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {task_id}: {prompt}",
                callback_data=f"task_view:{task_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🔄 重新整理", callback_data="tasks_refresh"),
        InlineKeyboardButton("❌ 關閉", callback_data="close"),
    ])

    return InlineKeyboardMarkup(keyboard)


def get_task_created_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """
    Get keyboard shown when task is created.

    Args:
        task_id: The task/composer ID
    """
    cursor_url = f"https://cursor.com/agents/{task_id}"
    keyboard = [
        [InlineKeyboardButton("🔗 在 Cursor 開啟", url=cursor_url)],
        [
            InlineKeyboardButton("🔄 查看狀態", callback_data=f"task_refresh:{task_id[:8]}"),
            InlineKeyboardButton("❌ 取消", callback_data=f"task_cancel:{task_id[:8]}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================
# Repository Keyboards
# ============================================


def get_repo_keyboard(
    repos: list[dict], 
    current_repo: str = "",
    page: int = 0,
    page_size: int = 8,
) -> InlineKeyboardMarkup:
    """
    Get paginated repository selection keyboard.

    Args:
        repos: List of repository dictionaries
        current_repo: Currently selected repo URL
        page: Current page number (0-indexed)
        page_size: Number of repos per page
    """
    keyboard = []
    
    total = len(repos)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    
    start = page * page_size
    end = min(start + page_size, total)
    page_repos = repos[start:end]

    for repo in page_repos:
        name = repo.get("name", "")
        full_name = repo.get("full_name", "")
        owner = repo.get("owner", "")
        private = repo.get("private", False)

        # Fallback: construct full_name if empty
        if not full_name:
            if owner and name:
                full_name = f"{owner}/{name}"
            elif name:
                full_name = name
            else:
                # Skip repos without proper identification
                continue

        # Mark current repo
        is_current = current_repo and full_name in current_repo
        prefix = "✓ " if is_current else ""
        lock = "🔒 " if private else ""

        keyboard.append([
            InlineKeyboardButton(
                f"{lock}{prefix}{name or full_name.split('/')[-1]}",
                callback_data=f"repo_select:{full_name}"
            )
        ])

    # Navigation row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ 上一頁", callback_data=f"repos_page:{page - 1}"))
    
    nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="repos_noop"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("下一頁 ▶️", callback_data=f"repos_page:{page + 1}"))
    
    keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton("🔄 重新整理", callback_data="repos_refresh"),
        InlineKeyboardButton("❌ 關閉", callback_data="close"),
    ])

    return InlineKeyboardMarkup(keyboard)


def get_repo_info_keyboard(repo_url: str) -> InlineKeyboardMarkup:
    """
    Get keyboard for repo info display.

    Args:
        repo_url: GitHub repository URL
    """
    keyboard = [
        [InlineKeyboardButton("🔗 在 GitHub 開啟", url=repo_url)],
        [
            InlineKeyboardButton("💬 發送任務", callback_data="ask_new"),
            InlineKeyboardButton("🔄 切換倉庫", callback_data="repos_list"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


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
        [InlineKeyboardButton("📝 自訂提示詞", callback_data="settings_prompt")],
        [InlineKeyboardButton("🤖 AI 設定", callback_data="settings_ai")],
        [InlineKeyboardButton("❌ 關閉", callback_data="close")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================
# Quick Action Keyboards
# ============================================


def get_welcome_keyboard() -> InlineKeyboardMarkup:
    """Get welcome message keyboard with quick actions."""
    keyboard = [
        [
            InlineKeyboardButton("📁 選擇倉庫", callback_data="repos_list"),
            InlineKeyboardButton("📋 我的任務", callback_data="tasks_list"),
        ],
        [
            InlineKeyboardButton("🧠 記憶", callback_data="memory_list"),
            InlineKeyboardButton("🎯 技能", callback_data="skills_list"),
        ],
        [
            InlineKeyboardButton("🤖 Agent", callback_data="agent_menu"),
            InlineKeyboardButton("🔧 工具", callback_data="tools_menu"),
        ],
        [
            InlineKeyboardButton("📊 狀態", callback_data="status"),
            InlineKeyboardButton("❓ 幫助", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_agent_menu_keyboard() -> InlineKeyboardMarkup:
    """Get Agent Loop menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("🤖 Agent Loop", callback_data="agent_loop")],
        [InlineKeyboardButton("⏰ 排程任務", callback_data="scheduler_list")],
        [InlineKeyboardButton("🔔 Webhook", callback_data="webhook_list")],
        [InlineKeyboardButton("⬅️ 返回", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tools_menu_keyboard() -> InlineKeyboardMarkup:
    """Get Tools menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("🌐 Browser 工具", callback_data="browser_tool")],
        [InlineKeyboardButton("📁 檔案操作", callback_data="file_tool")],
        [InlineKeyboardButton("💻 終端機", callback_data="terminal_tool")],
        [InlineKeyboardButton("⬅️ 返回", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_scheduler_keyboard(jobs: list = None) -> InlineKeyboardMarkup:
    """Get scheduler jobs keyboard."""
    keyboard = []
    
    if jobs:
        for job in jobs[:5]:
            job_id = job.get("id", "")[:8]
            name = job.get("name", "未命名")[:15]
            status = "🟢" if job.get("enabled") else "⚪"
            keyboard.append([
                InlineKeyboardButton(f"{status} {name}", callback_data=f"job_view:{job_id}")
            ])
    
    keyboard.append([
        InlineKeyboardButton("➕ 新增排程", callback_data="scheduler_add"),
        InlineKeyboardButton("🔄 重整", callback_data="scheduler_refresh"),
    ])
    keyboard.append([InlineKeyboardButton("⬅️ 返回", callback_data="agent_menu")])
    
    return InlineKeyboardMarkup(keyboard)


def get_browser_keyboard() -> InlineKeyboardMarkup:
    """Get browser tool keyboard."""
    keyboard = [
        [InlineKeyboardButton("🌐 開啟網頁", callback_data="browser_navigate")],
        [InlineKeyboardButton("📸 截圖", callback_data="browser_screenshot")],
        [InlineKeyboardButton("📝 取得內容", callback_data="browser_content")],
        [InlineKeyboardButton("⬅️ 返回", callback_data="tools_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_status_keyboard() -> InlineKeyboardMarkup:
    """Get status page keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📁 我的倉庫", callback_data="repos_list"),
            InlineKeyboardButton("📋 我的任務", callback_data="tasks_list"),
        ],
        [
            InlineKeyboardButton("🔄 重新整理", callback_data="status_refresh"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Get help page keyboard."""
    keyboard = [
        [InlineKeyboardButton("🚀 快速開始", callback_data="help_quickstart")],
        [InlineKeyboardButton("📖 指令說明", callback_data="help_commands")],
        [InlineKeyboardButton("❓ 常見問題", callback_data="help_faq")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_error_keyboard() -> InlineKeyboardMarkup:
    """Get error message keyboard with retry option."""
    keyboard = [
        [
            InlineKeyboardButton("🔄 重試", callback_data="retry_last"),
            InlineKeyboardButton("❓ 取得幫助", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================
# Image/Voice Keyboards
# ============================================


def get_media_received_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard shown when media (image/voice) is received."""
    keyboard = [
        [InlineKeyboardButton("💬 建立任務", callback_data="create_task_with_media")],
        [
            InlineKeyboardButton("🗑️ 清除快取", callback_data="clear_media_cache"),
            InlineKeyboardButton("❌ 取消", callback_data="cancel_media"),
        ],
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
    # Task keyboards
    "get_task_keyboard",
    "get_task_list_keyboard",
    "get_task_created_keyboard",
    # Repo keyboards
    "get_repo_keyboard",
    "get_repo_info_keyboard",
    # Quick action keyboards
    "get_welcome_keyboard",
    "get_status_keyboard",
    "get_help_keyboard",
    "get_error_keyboard",
    # Media keyboards
    "get_media_received_keyboard",
    # Agent & Tools menus
    "get_agent_menu_keyboard",
    "get_tools_menu_keyboard",
    "get_scheduler_keyboard",
    "get_browser_keyboard",
]
