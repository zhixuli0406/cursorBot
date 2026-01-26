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
