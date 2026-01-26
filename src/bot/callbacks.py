"""
Callback query handlers for Telegram Bot
Handles button clicks and inline keyboard interactions
"""

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes, CallbackQueryHandler

from ..cursor.background_agent import get_background_agent, get_task_tracker
from ..utils.auth import authorized_only
from ..utils.config import settings
from ..utils.logger import logger
from .keyboards import (
    get_task_keyboard,
    get_task_list_keyboard,
    get_repo_keyboard,
    get_status_keyboard,
    get_help_keyboard,
)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# Store user's current repo selection (shared with handlers.py)
_user_repos: dict[int, str] = {}


def get_user_repo(user_id: int) -> str:
    """Get user's current repo, fallback to settings."""
    return _user_repos.get(user_id, settings.cursor_github_repo)


def set_user_repo(user_id: int, repo_url: str) -> None:
    """Set user's current repo."""
    _user_repos[user_id] = repo_url


@authorized_only
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle all callback queries from inline keyboards.
    """
    query = update.callback_query
    await query.answer()  # Acknowledge the callback

    data = query.data
    user_id = update.effective_user.id
    logger.info(f"Callback from user {user_id}: {data}")

    # Parse callback data
    if ":" in data:
        action, param = data.split(":", 1)
    else:
        action = data
        param = ""

    # Route to appropriate handler
    try:
        if action == "close":
            await query.message.delete()

        elif action == "task_refresh":
            await handle_task_refresh(query, param)

        elif action == "task_cancel":
            await handle_task_cancel(query, param, user_id)

        elif action == "task_view":
            await handle_task_view(query, param, user_id)

        elif action == "task_followup":
            await handle_task_followup(query, param, user_id)

        elif action == "task_copy":
            await handle_task_copy(query, param, user_id)

        elif action == "tasks_list" or action == "tasks_refresh":
            await handle_tasks_list(query, user_id)

        elif action == "repo_select":
            await handle_repo_select(query, param, user_id)

        elif action == "repos_list" or action == "repos_refresh":
            await handle_repos_list(query, user_id)

        elif action == "status" or action == "status_refresh":
            await handle_status(query, user_id)

        elif action == "help":
            await handle_help(query)

        elif action == "help_quickstart":
            await handle_help_quickstart(query)

        elif action == "help_commands":
            await handle_help_commands(query)

        elif action == "ask_new":
            await query.message.reply_text(
                "💬 <b>發送任務</b>\n\n"
                "直接輸入你的問題或指令，我會發送到 Cursor Agent。\n\n"
                "範例:\n"
                "• <code>幫我實作一個快速排序函數</code>\n"
                "• <code>修正這個 bug: ...</code>\n"
                "• <code>新增 dark mode 支援</code>",
                parse_mode="HTML",
            )

        elif action == "memory_list":
            await handle_memory_list(query, user_id)

        elif action == "skills_list":
            await handle_skills_list(query)

        # === Agent & Tools Menu ===
        elif action == "agent_menu":
            await handle_agent_menu(query)

        elif action == "tools_menu":
            await handle_tools_menu(query)

        elif action == "back_main":
            await handle_back_main(query)

        elif action == "agent_loop":
            await handle_agent_loop(query)

        elif action == "scheduler_list":
            await handle_scheduler_list(query)

        elif action == "scheduler_add":
            await handle_scheduler_add(query)

        elif action == "webhook_list":
            await handle_webhook_list(query)

        elif action == "browser_tool":
            await handle_browser_tool(query)

        elif action == "browser_navigate":
            await handle_browser_navigate(query)

        elif action == "browser_screenshot":
            await handle_browser_screenshot(query)

        elif action == "file_tool":
            await handle_file_tool(query)

        elif action == "terminal_tool":
            await handle_terminal_tool(query)

        else:
            logger.warning(f"Unknown callback action: {action}")

    except BadRequest as e:
        # Handle "message not modified" error silently
        if "message is not modified" in str(e).lower():
            await query.answer("內容沒有變化", show_alert=False)
        else:
            logger.error(f"Callback BadRequest: {e}")
            await query.answer(f"錯誤: {str(e)[:50]}", show_alert=True)

    except Exception as e:
        logger.error(f"Callback error: {e}")
        await query.answer(f"發生錯誤: {str(e)[:50]}", show_alert=True)


async def handle_task_refresh(query, task_id_prefix: str) -> None:
    """Refresh task status."""
    tracker = get_task_tracker()
    user_id = query.from_user.id

    # Find task
    user_tasks = tracker.get_user_tasks(user_id)
    matching_task = None
    for t in user_tasks:
        if t['composer_id'].startswith(task_id_prefix):
            matching_task = t
            break

    if not matching_task:
        await query.message.edit_text(f"❌ 找不到任務: {task_id_prefix}")
        return

    # Get fresh status from API
    try:
        bg_agent = get_background_agent(settings.cursor_api_key)
        result = await bg_agent.get_task_details(matching_task['composer_id'])

        if result.get("success"):
            status = result.get("status", matching_task.get("status", "unknown"))
            output = result.get("output", "")

            # Update tracker
            tracker.update_task(matching_task['composer_id'], status, output)
            matching_task["status"] = status
            matching_task["output"] = output

    except Exception as e:
        logger.error(f"Error refreshing task: {e}")

    # Format response
    status = matching_task.get("status", "unknown")
    status_emoji = {
        "running": "🔄",
        "pending": "⏳",
        "created": "🆕",
        "completed": "✅",
        "failed": "❌",
    }.get(status, "❓")

    output = matching_task.get("output", "（尚無輸出）")
    if len(output) > 2000:
        output = output[:2000] + "\n\n... (內容過長已截斷)"

    prompt = matching_task.get("prompt", "")[:150]
    if len(matching_task.get("prompt", "")) > 150:
        prompt += "..."

    await query.message.edit_text(
        f"<b>📋 任務狀態</b>\n\n"
        f"🆔 ID: <code>{matching_task['composer_id'][:8]}</code>\n"
        f"{status_emoji} 狀態: {_escape_html(status)}\n\n"
        f"<b>❓ 問題:</b>\n{_escape_html(prompt)}\n\n"
        f"<b>📝 結果:</b>\n{_escape_html(output)}",
        parse_mode="HTML",
        reply_markup=get_task_keyboard(matching_task['composer_id'], status),
    )


async def handle_task_cancel(query, task_id_prefix: str, user_id: int) -> None:
    """Cancel a task."""
    tracker = get_task_tracker()

    # Find task
    user_tasks = tracker.get_user_tasks(user_id)
    matching_task = None
    for t in user_tasks:
        if t['composer_id'].startswith(task_id_prefix):
            matching_task = t
            break

    if not matching_task:
        await query.message.edit_text(f"❌ 找不到任務: {task_id_prefix}")
        return

    try:
        bg_agent = get_background_agent(settings.cursor_api_key)
        result = await bg_agent.cancel_task(matching_task['composer_id'])

        if result.get("success"):
            tracker.update_task(matching_task['composer_id'], "cancelled")
            await query.message.edit_text(
                f"🚫 <b>任務已取消</b>\n\n"
                f"🆔 ID: <code>{matching_task['composer_id'][:8]}</code>",
                parse_mode="HTML",
            )
        else:
            await query.message.edit_text(
                f"❌ 取消失敗: {result.get('message', 'Unknown')}"
            )

    except Exception as e:
        await query.message.edit_text(f"❌ 錯誤: {str(e)[:100]}")


async def handle_task_view(query, task_id_prefix: str, user_id: int) -> None:
    """View task details."""
    await handle_task_refresh(query, task_id_prefix)


async def handle_task_followup(query, task_id_prefix: str, user_id: int) -> None:
    """Send follow-up to a task."""
    await query.message.reply_text(
        f"💬 <b>追問任務</b>\n\n"
        f"回覆這則訊息，輸入你的追問內容。\n\n"
        f"任務 ID: <code>{task_id_prefix}</code>",
        parse_mode="HTML",
    )
    # Store context for follow-up handling
    # This would require conversation state management


async def handle_task_copy(query, task_id_prefix: str, user_id: int) -> None:
    """Copy task result."""
    tracker = get_task_tracker()

    user_tasks = tracker.get_user_tasks(user_id)
    matching_task = None
    for t in user_tasks:
        if t['composer_id'].startswith(task_id_prefix):
            matching_task = t
            break

    if not matching_task:
        await query.answer("找不到任務", show_alert=True)
        return

    output = matching_task.get("output", "")
    if output:
        # Send as a separate message for easy copying
        await query.message.reply_text(
            f"<pre>{_escape_html(output[:4000])}</pre>",
            parse_mode="HTML",
        )
    else:
        await query.answer("任務尚無輸出", show_alert=True)


async def handle_tasks_list(query, user_id: int) -> None:
    """Show task list."""
    tracker = get_task_tracker()
    all_tasks = tracker.get_user_tasks(user_id)

    if not all_tasks:
        await query.message.edit_text(
            "📋 <b>沒有任務記錄</b>\n\n"
            "直接發送訊息來建立新任務！",
            parse_mode="HTML",
        )
        return

    # Get recent tasks
    recent_tasks = all_tasks[:8]

    # Count by status
    running = len([t for t in all_tasks if t.get("status") in ["running", "pending", "created"]])
    completed = len([t for t in all_tasks if t.get("status") == "completed"])
    failed = len([t for t in all_tasks if t.get("status") in ["failed", "error"]])

    await query.message.edit_text(
        f"<b>📋 我的任務</b>\n\n"
        f"🔄 執行中: {running}\n"
        f"✅ 已完成: {completed}\n"
        f"❌ 失敗: {failed}\n\n"
        f"點擊查看詳情:",
        parse_mode="HTML",
        reply_markup=get_task_list_keyboard(recent_tasks),
    )


async def handle_repo_select(query, full_name: str, user_id: int) -> None:
    """Select a repository."""
    repo_url = f"https://github.com/{full_name}"
    set_user_repo(user_id, repo_url)

    repo_name = full_name.split("/")[-1]

    await query.message.edit_text(
        f"✅ <b>已選擇倉庫</b>\n\n"
        f"📁 {full_name}\n\n"
        f"現在可以發送任務到此倉庫。\n"
        f"直接輸入問題或使用 /ask 指令。",
        parse_mode="HTML",
    )


async def handle_repos_list(query, user_id: int) -> None:
    """Show repository list."""
    if not settings.cursor_api_key:
        await query.message.edit_text(
            "⚠️ <b>未設定 API Key</b>\n\n"
            "請設定 CURSOR_API_KEY 來使用此功能。",
            parse_mode="HTML",
        )
        return

    try:
        bg_agent = get_background_agent(settings.cursor_api_key)
        result = await bg_agent.list_repositories()

        if result.get("success") and result.get("repositories"):
            repos = result.get("repositories", [])
            current_repo = get_user_repo(user_id)

            await query.message.edit_text(
                f"<b>📁 選擇倉庫</b>\n\n"
                f"找到 {len(repos)} 個倉庫:",
                parse_mode="HTML",
                reply_markup=get_repo_keyboard(repos, current_repo),
            )
        else:
            await query.message.edit_text(
                f"⚠️ 無法取得倉庫列表\n\n"
                f"請使用 /repo 手動設定:\n"
                f"<code>/repo owner/repo-name</code>",
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Error listing repos: {e}")
        await query.message.edit_text(f"❌ 錯誤: {str(e)[:100]}")


async def handle_status(query, user_id: int) -> None:
    """Show status."""
    current_repo = get_user_repo(user_id)
    tracker = get_task_tracker()
    running_tasks = len(tracker.get_pending_tasks())

    if settings.cursor_api_key:
        api_status = "🟢 已連線"
    else:
        api_status = "🔴 未設定"

    repo_display = current_repo.split("/")[-1] if current_repo else "未設定"

    await query.message.edit_text(
        f"<b>📊 系統狀態</b>\n\n"
        f"<b>Background Agent:</b> {api_status}\n"
        f"<b>目前倉庫:</b> {repo_display}\n"
        f"<b>執行中任務:</b> {running_tasks}\n",
        parse_mode="HTML",
        reply_markup=get_status_keyboard(),
    )


async def handle_help(query) -> None:
    """Show help."""
    await query.message.edit_text(
        "<b>❓ 幫助</b>\n\n"
        "CursorBot 讓你透過 Telegram 遠端控制 Cursor AI。\n\n"
        "選擇一個主題了解更多:",
        parse_mode="HTML",
        reply_markup=get_help_keyboard(),
    )


async def handle_help_quickstart(query) -> None:
    """Show quickstart guide."""
    await query.message.edit_text(
        "<b>🚀 快速開始</b>\n\n"
        "<b>1. 選擇倉庫</b>\n"
        "使用 /repo 或點擊「選擇倉庫」按鈕\n\n"
        "<b>2. 發送任務</b>\n"
        "直接輸入問題，例如:\n"
        "<code>幫我實作一個登入功能</code>\n\n"
        "<b>3. 查看結果</b>\n"
        "任務完成後會自動通知，或使用 /tasks 查看",
        parse_mode="HTML",
        reply_markup=get_help_keyboard(),
    )


async def handle_help_commands(query) -> None:
    """Show commands help."""
    await query.message.edit_text(
        "<b>📖 指令說明</b>\n\n"
        "<b>基本指令:</b>\n"
        "/start - 歡迎訊息\n"
        "/help - 顯示幫助\n"
        "/status - 系統狀態\n"
        "/stats - 使用統計\n\n"
        "<b>任務管理:</b>\n"
        "/ask - 發送問題\n"
        "/tasks - 我的任務\n"
        "/result - 查看結果\n\n"
        "<b>記憶與技能:</b>\n"
        "/memory - 記憶管理\n"
        "/skills - 可用技能\n"
        "/remind - 設定提醒\n\n"
        "<b>💡 提示:</b>\n"
        "直接發送訊息也可以建立任務！",
        parse_mode="HTML",
        reply_markup=get_help_keyboard(),
    )


async def handle_memory_list(query, user_id: int) -> None:
    """Show user's memory list."""
    from ..core import get_memory_manager

    memory = get_memory_manager()
    memories = await memory.list_memories(user_id, limit=10)

    if not memories:
        await query.message.edit_text(
            "🧠 <b>我的記憶</b>\n\n"
            "目前沒有儲存任何記憶。\n\n"
            "<b>用法:</b>\n"
            "<code>/memory add key value</code> - 新增記憶\n"
            "<code>/memory get key</code> - 取得記憶\n\n"
            "<b>範例:</b>\n"
            "<code>/memory add lang Python</code>",
            parse_mode="HTML",
        )
        return

    text = "🧠 <b>我的記憶</b>\n\n"
    for m in memories:
        value = m['value'][:40] + "..." if len(str(m['value'])) > 40 else m['value']
        text += f"• <code>{m['key']}</code>: {_escape_html(str(value))}\n"

    text += "\n使用 /memory 管理記憶"

    await query.message.edit_text(text, parse_mode="HTML")


async def handle_skills_list(query) -> None:
    """Show available skills."""
    from ..core import get_skill_manager

    skills = get_skill_manager()

    # Load built-in skills if not loaded
    if not skills.list_skills():
        await skills.load_builtin_skills()

    skill_list = skills.list_skills()

    if not skill_list:
        await query.message.edit_text(
            "🎯 <b>技能系統</b>\n\n"
            "目前沒有可用的技能。",
            parse_mode="HTML",
        )
        return

    text = "🎯 <b>可用技能</b>\n\n"

    for skill in skill_list:
        status = "✅" if skill.enabled else "❌"
        commands = ", ".join([f"/{c}" for c in skill.commands[:2]])
        text += f"{status} <b>{skill.name}</b>\n"
        text += f"   {skill.description}\n"
        text += f"   {commands}\n\n"

    await query.message.edit_text(text, parse_mode="HTML")


# ============================================
# Agent & Tools Menu Handlers
# ============================================


async def handle_agent_menu(query) -> None:
    """Show Agent menu."""
    from .keyboards import get_agent_menu_keyboard

    text = """🤖 <b>Agent 功能</b>

選擇要使用的功能:

• <b>Agent Loop</b> - 自主代理執行循環
• <b>排程任務</b> - 定時執行任務
• <b>Webhook</b> - 外部事件觸發
"""
    await query.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_agent_menu_keyboard(),
    )


async def handle_tools_menu(query) -> None:
    """Show Tools menu."""
    from .keyboards import get_tools_menu_keyboard

    text = """🔧 <b>工具箱</b>

選擇要使用的工具:

• <b>Browser</b> - 網頁自動化、截圖
• <b>檔案操作</b> - 讀寫檔案
• <b>終端機</b> - 執行命令
"""
    await query.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_tools_menu_keyboard(),
    )


async def handle_back_main(query) -> None:
    """Back to main menu."""
    from .keyboards import get_welcome_keyboard

    text = """👋 <b>CursorBot 主選單</b>

選擇要使用的功能:
"""
    await query.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_welcome_keyboard(),
    )


async def handle_agent_loop(query) -> None:
    """Show Agent Loop info."""
    text = """🤖 <b>Agent Loop</b>

Agent Loop 是一個自主代理執行系統，可以:

• 自動分解複雜任務
• 多步驟推理和執行
• 自動調用工具完成任務
• 追蹤執行狀態

<b>使用方式:</b>
直接發送訊息，系統會自動判斷是否需要啟動 Agent Loop。

<b>或使用指令:</b>
<code>/agent &lt;任務描述&gt;</code>
"""
    await query.message.edit_text(text, parse_mode="HTML")


async def handle_scheduler_list(query) -> None:
    """Show scheduler jobs."""
    from ..core import get_scheduler
    from .keyboards import get_scheduler_keyboard

    scheduler = get_scheduler()
    jobs = scheduler.list_jobs()

    if not jobs:
        text = """⏰ <b>排程任務</b>

目前沒有排程任務。

<b>建立排程:</b>
• <code>/remind 10m 提醒我開會</code> - 10分鐘後提醒
• <code>/schedule daily 09:00 早安</code> - 每天早上9點
"""
    else:
        text = f"⏰ <b>排程任務</b> ({len(jobs)} 個)\n\n"
        for job in jobs[:5]:
            status = "🟢" if job.enabled else "⚪"
            text += f"{status} {job.name}\n"

    await query.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_scheduler_keyboard(jobs if jobs else None),
    )


async def handle_scheduler_add(query) -> None:
    """Show how to add scheduler."""
    text = """➕ <b>新增排程任務</b>

<b>一次性提醒:</b>
<code>/remind 10m 提醒內容</code>
<code>/remind 2h 提醒內容</code>

<b>重複排程:</b>
<code>/schedule interval 1h 每小時執行</code>
<code>/schedule daily 09:00 每天執行</code>
<code>/schedule cron "0 9 * * *" cron格式</code>

<b>時間格式:</b>
• <code>10m</code> - 10 分鐘
• <code>2h</code> - 2 小時
• <code>1d</code> - 1 天
"""
    await query.message.edit_text(text, parse_mode="HTML")


async def handle_webhook_list(query) -> None:
    """Show webhook endpoints."""
    from ..core import get_webhook_manager

    webhooks = get_webhook_manager()
    endpoints = webhooks.list_endpoints()

    if not endpoints:
        text = """🔔 <b>Webhook 端點</b>

目前沒有設定 Webhook。

Webhook 可以接收外部事件觸發任務，例如:
• GitHub push 事件
• GitLab CI 完成
• 自訂 HTTP 請求

<b>設定方式:</b>
請在程式碼中使用 <code>WebhookManager</code> 註冊端點。
"""
    else:
        text = f"🔔 <b>Webhook 端點</b> ({len(endpoints)} 個)\n\n"
        for ep in endpoints:
            text += f"• <code>{ep.path}</code> - {ep.description}\n"

    await query.message.edit_text(text, parse_mode="HTML")


async def handle_browser_tool(query) -> None:
    """Show browser tool menu."""
    from .keyboards import get_browser_keyboard
    from ..core import PLAYWRIGHT_AVAILABLE

    if not PLAYWRIGHT_AVAILABLE:
        text = """🌐 <b>Browser 工具</b>

⚠️ Playwright 未安裝

請執行以下指令安裝:
<code>pip install playwright</code>
<code>playwright install</code>
"""
    else:
        text = """🌐 <b>Browser 工具</b>

Browser 工具提供網頁自動化功能:

• <b>開啟網頁</b> - 導航到指定 URL
• <b>截圖</b> - 擷取網頁畫面
• <b>取得內容</b> - 抓取網頁文字

<b>指令方式:</b>
<code>/browser navigate https://example.com</code>
<code>/browser screenshot</code>
<code>/browser text h1</code>
"""
    await query.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_browser_keyboard() if PLAYWRIGHT_AVAILABLE else None,
    )


async def handle_browser_navigate(query) -> None:
    """Browser navigate prompt."""
    text = """🌐 <b>開啟網頁</b>

請輸入要開啟的網址:

<code>/browser navigate https://example.com</code>

或直接發送網址:
<code>https://github.com</code>
"""
    await query.message.edit_text(text, parse_mode="HTML")


async def handle_browser_screenshot(query) -> None:
    """Take browser screenshot."""
    from ..core import get_browser_tool, PLAYWRIGHT_AVAILABLE

    if not PLAYWRIGHT_AVAILABLE:
        await query.message.edit_text("⚠️ Playwright 未安裝")
        return

    browser = get_browser_tool()
    if not browser or not browser.is_running:
        await query.message.edit_text(
            "⚠️ Browser 未啟動\n\n請先使用 <code>/browser navigate URL</code> 開啟網頁",
            parse_mode="HTML",
        )
        return

    await query.message.edit_text("📸 正在截圖...")

    result = await browser.screenshot()
    if result.success and result.screenshot:
        await query.message.reply_photo(
            result.screenshot,
            caption="📸 網頁截圖",
        )
    else:
        await query.message.edit_text(f"❌ 截圖失敗: {result.error}")


async def handle_file_tool(query) -> None:
    """Show file tool info."""
    text = """📁 <b>檔案操作</b>

可用指令:

<b>讀取檔案:</b>
<code>/file read path/to/file</code>

<b>列出目錄:</b>
<code>/file list .</code>

<b>建立檔案:</b>
<code>/write path/to/file</code>
然後輸入內容

<b>刪除檔案:</b>
<code>/delete path/to/file</code>
"""
    await query.message.edit_text(text, parse_mode="HTML")


async def handle_terminal_tool(query) -> None:
    """Show terminal tool info."""
    text = """💻 <b>終端機</b>

可用指令:

<b>執行命令:</b>
<code>/run ls -la</code>
<code>/run git status</code>

<b>背景執行:</b>
<code>/run_bg npm start</code>

<b>查看執行中:</b>
<code>/jobs</code>

<b>停止命令:</b>
<code>/kill &lt;ID&gt;</code>

⚠️ 請小心使用，命令會在伺服器上執行。
"""
    await query.message.edit_text(text, parse_mode="HTML")


def setup_callback_handlers(app) -> None:
    """
    Setup callback query handlers.

    Args:
        app: Telegram Application instance
    """
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("Callback handlers configured")


__all__ = [
    "callback_handler",
    "setup_callback_handlers",
    "get_user_repo",
    "set_user_repo",
]
