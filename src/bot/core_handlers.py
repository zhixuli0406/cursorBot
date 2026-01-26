"""
Core feature handlers for Telegram Bot
Integrates memory, skills, approvals, and other core features
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

from ..core import (
    get_memory_manager,
    get_skill_manager,
    get_context_manager,
    get_scheduler,
    get_approval_manager,
    ApprovalType,
)
from ..utils.auth import authorized_only
from ..utils.logger import logger


# ============================================
# Memory Commands
# ============================================


@authorized_only
async def memory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /memory command.
    List, add, or search memories.

    Usage:
        /memory - List memories
        /memory add <key> <value> - Add memory
        /memory get <key> - Get memory
        /memory del <key> - Delete memory
        /memory search <query> - Search memories
    """
    user_id = update.effective_user.id
    args = context.args or []
    memory = get_memory_manager()

    if not args:
        # List memories
        memories = await memory.list_memories(user_id, limit=10)

        if not memories:
            await update.message.reply_text(
                "🧠 <b>記憶系統</b>\n\n"
                "目前沒有儲存任何記憶。\n\n"
                "<b>用法:</b>\n"
                "• <code>/memory add key value</code> - 新增記憶\n"
                "• <code>/memory get key</code> - 取得記憶\n"
                "• <code>/memory del key</code> - 刪除記憶\n"
                "• <code>/memory search query</code> - 搜尋",
                parse_mode="HTML",
            )
            return

        text = "🧠 <b>我的記憶</b>\n\n"
        for m in memories:
            value = m['value'][:50] + "..." if len(m['value']) > 50 else m['value']
            text += f"• <code>{m['key']}</code>: {value}\n"

        await update.message.reply_text(text, parse_mode="HTML")

    elif args[0] == "add" and len(args) >= 3:
        key = args[1]
        value = " ".join(args[2:])
        await memory.remember(user_id, key, value)
        await update.message.reply_text(
            f"✅ 已記住: <code>{key}</code>",
            parse_mode="HTML",
        )

    elif args[0] == "get" and len(args) >= 2:
        key = args[1]
        value = await memory.recall(user_id, key)
        if value:
            await update.message.reply_text(
                f"🧠 <code>{key}</code>:\n{value}",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(f"❌ 找不到記憶: {key}")

    elif args[0] == "del" and len(args) >= 2:
        key = args[1]
        deleted = await memory.forget(user_id, key)
        if deleted:
            await update.message.reply_text(f"✅ 已刪除: {key}")
        else:
            await update.message.reply_text(f"❌ 找不到記憶: {key}")

    elif args[0] == "search" and len(args) >= 2:
        query = " ".join(args[1:])
        results = await memory.search_memories(user_id, query)

        if not results:
            await update.message.reply_text(f"❌ 找不到符合的記憶: {query}")
            return

        text = f"🔍 <b>搜尋結果:</b> {query}\n\n"
        for m in results:
            value = m['value'][:50] + "..." if len(m['value']) > 50 else m['value']
            text += f"• <code>{m['key']}</code>: {value}\n"

        await update.message.reply_text(text, parse_mode="HTML")

    else:
        await update.message.reply_text(
            "❌ 無效的記憶指令。使用 /memory 查看用法。"
        )


# ============================================
# Skills Commands
# ============================================


@authorized_only
async def skills_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /skills command.
    List available skills.
    """
    skills = get_skill_manager()

    # Load built-in skills if not loaded
    if not skills.list_skills():
        await skills.load_builtin_skills()

    skill_list = skills.list_skills()

    if not skill_list:
        await update.message.reply_text("❌ 沒有可用的技能")
        return

    text = "🎯 <b>可用技能</b>\n\n"

    for skill in skill_list:
        status = "✅" if skill.enabled else "❌"
        commands = ", ".join([f"/{c}" for c in skill.commands])
        text += f"{status} <b>{skill.name}</b>\n"
        text += f"   {skill.description}\n"
        text += f"   指令: {commands}\n\n"

    await update.message.reply_text(text, parse_mode="HTML")


@authorized_only
async def skill_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle skill commands.
    Routes to appropriate skill based on command.
    """
    message = update.message.text
    if not message.startswith("/"):
        return

    # Extract command and args
    parts = message.split()
    command = parts[0][1:]  # Remove /
    args = parts[1:] if len(parts) > 1 else []

    skills = get_skill_manager()

    # Load built-in skills if not loaded
    if not skills.list_skills():
        await skills.load_builtin_skills()

    # Try to execute skill command
    handled = await skills.execute_command(update, context, command, args)

    if not handled:
        # Not a skill command, let other handlers process it
        pass


# ============================================
# Scheduler Commands
# ============================================


@authorized_only
async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /schedule command.
    List or manage scheduled jobs.

    Usage:
        /schedule - List jobs
        /schedule cancel <job_id> - Cancel job
    """
    user_id = update.effective_user.id
    args = context.args or []
    scheduler = get_scheduler()

    if not args:
        # List jobs
        jobs = scheduler.list_jobs(user_id)

        if not jobs:
            await update.message.reply_text(
                "⏰ <b>排程系統</b>\n\n"
                "目前沒有排程任務。\n\n"
                "使用 /remind 設定提醒，或透過技能建立排程任務。",
                parse_mode="HTML",
            )
            return

        text = "⏰ <b>我的排程</b>\n\n"
        for job in jobs:
            status_emoji = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
            }.get(job.status.value, "❓")

            next_run = job.next_run.strftime("%H:%M:%S") if job.next_run else "N/A"
            text += f"{status_emoji} <code>{job.job_id[:8]}</code>: {job.name}\n"
            text += f"   下次執行: {next_run}\n\n"

        await update.message.reply_text(text, parse_mode="HTML")

    elif args[0] == "cancel" and len(args) >= 2:
        job_id = args[1]

        # Find job by prefix
        jobs = scheduler.list_jobs(user_id)
        matching = [j for j in jobs if j.job_id.startswith(job_id)]

        if not matching:
            await update.message.reply_text(f"❌ 找不到排程: {job_id}")
            return

        scheduler.cancel_job(matching[0].job_id)
        await update.message.reply_text(f"✅ 已取消排程: {matching[0].name}")

    else:
        await update.message.reply_text(
            "❌ 無效的排程指令。使用 /schedule 查看用法。"
        )


# ============================================
# Context Commands
# ============================================


@authorized_only
async def clear_context_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /clear command.
    Clear conversation context.
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    ctx_manager = get_context_manager()

    ctx_manager.clear_context(user_id, chat_id)

    await update.message.reply_text(
        "🗑️ <b>已清除對話上下文</b>\n\n"
        "Bot 將不會記住之前的對話內容。",
        parse_mode="HTML",
    )


# ============================================
# Stats Commands
# ============================================


@authorized_only
async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /stats command.
    Show user statistics.
    """
    user_id = update.effective_user.id
    memory = get_memory_manager()
    ctx_manager = get_context_manager()
    scheduler = get_scheduler()

    # Get task stats
    task_stats = await memory.get_task_stats(user_id)

    # Get context stats
    ctx_stats = ctx_manager.get_stats()

    # Get scheduler stats
    sched_stats = scheduler.get_stats()

    text = "📊 <b>使用統計</b>\n\n"

    text += "<b>任務統計:</b>\n"
    text += f"• 總任務數: {task_stats['total_tasks']}\n"
    text += f"• 完成任務: {task_stats['completed_tasks']}\n"
    text += f"• 失敗任務: {task_stats['failed_tasks']}\n"

    success_rate = (
        task_stats['completed_tasks'] / task_stats['total_tasks'] * 100
        if task_stats['total_tasks'] > 0 else 0
    )
    text += f"• 成功率: {success_rate:.1f}%\n\n"

    text += "<b>系統狀態:</b>\n"
    text += f"• 活躍對話: {ctx_stats['active_contexts']}\n"
    text += f"• 排程任務: {sched_stats['pending']}\n"
    text += f"• 排程器: {'運行中' if sched_stats['scheduler_running'] else '已停止'}\n"

    await update.message.reply_text(text, parse_mode="HTML")


# ============================================
# Settings Commands
# ============================================


@authorized_only
async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /settings command.
    Show and manage user settings.
    """
    user_id = update.effective_user.id
    args = context.args or []
    memory = get_memory_manager()

    prefs = await memory.get_user_preferences(user_id)

    if not args:
        # Show settings
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 通知", callback_data="settings_notifications")],
            [InlineKeyboardButton("📝 自訂提示詞", callback_data="settings_prompt")],
            [InlineKeyboardButton("📁 預設倉庫", callback_data="settings_repo")],
        ])

        text = "⚙️ <b>設定</b>\n\n"
        text += f"<b>通知:</b> {'開啟' if prefs.get('notifications_enabled') else '關閉'}\n"
        text += f"<b>預設倉庫:</b> {prefs.get('default_repo') or '未設定'}\n"
        text += f"<b>自訂提示詞:</b> {'已設定' if prefs.get('custom_prompt') else '未設定'}\n"

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    elif args[0] == "notifications":
        current = prefs.get('notifications_enabled', True)
        new_value = not current
        await memory.set_user_preference(user_id, 'notifications_enabled', int(new_value))
        await update.message.reply_text(
            f"✅ 通知已{'開啟' if new_value else '關閉'}"
        )

    elif args[0] == "prompt" and len(args) >= 2:
        prompt = " ".join(args[1:])
        await memory.set_user_preference(user_id, 'custom_prompt', prompt)
        await update.message.reply_text(
            f"✅ 自訂提示詞已設定:\n{prompt[:100]}..."
        )

    else:
        await update.message.reply_text(
            "❌ 無效的設定指令。使用 /settings 查看設定。"
        )


def setup_core_handlers(app) -> None:
    """
    Setup core feature handlers.

    Args:
        app: Telegram Application instance
    """
    # Memory commands
    app.add_handler(CommandHandler("memory", memory_handler))

    # Skills commands
    app.add_handler(CommandHandler("skills", skills_handler))

    # Scheduler commands
    app.add_handler(CommandHandler("schedule", schedule_handler))

    # Context commands
    app.add_handler(CommandHandler("clear", clear_context_handler))

    # Stats commands
    app.add_handler(CommandHandler("stats", stats_handler))

    # Settings commands
    app.add_handler(CommandHandler("settings", settings_handler))

    # Built-in skill commands
    skill_commands = ["translate", "tr", "summarize", "sum", "calc", "calculate", "remind", "reminder"]
    for cmd in skill_commands:
        app.add_handler(CommandHandler(cmd, skill_command_handler))

    logger.info("Core handlers configured")


__all__ = [
    "memory_handler",
    "skills_handler",
    "schedule_handler",
    "clear_context_handler",
    "stats_handler",
    "settings_handler",
    "setup_core_handlers",
]
