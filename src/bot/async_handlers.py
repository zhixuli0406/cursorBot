"""
Async Handlers for Non-blocking Agent and CLI Execution

Provides handlers that submit tasks in background and push results when complete.
Users don't need to wait - they receive a notification when the task finishes.

Usage:
    # In your bot setup:
    from src.bot.async_handlers import register_async_handlers
    register_async_handlers(application)
    
    # Users can then use:
    # /agent_async <prompt>  - Run agent in background
    # /cli_async <prompt>    - Run CLI in background
    # /tasks                 - View pending tasks
    # /cancel <task_id>      - Cancel a task
"""

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..core.async_tasks import (
    get_task_manager,
    TaskType,
    TaskStatus,
    AsyncTask,
)
from ..utils.logger import logger
from ..utils.auth import is_authorized


def _escape_html(text: str) -> str:
    """Escape HTML special characters to prevent parsing errors."""
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ============================================
# Async Agent Handler
# ============================================

async def agent_async_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /agent_async command - Run agent in background.
    
    Usage:
        /agent_async <prompt>
        /agent_bg <prompt>
        
    The task runs in background and pushes result when complete.
    """
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "<b>Async Agent</b>\n\n"
            "Usage: <code>/agent_async &lt;prompt&gt;</code>\n\n"
            "The task runs in background. You'll receive a message when it completes.\n\n"
            "Example:\n"
            "<code>/agent_async Help me write a Python function to sort a list</code>\n\n"
            "Related commands:\n"
            "- <code>/tasks</code> - View your pending tasks\n"
            "- <code>/cancel &lt;task_id&gt;</code> - Cancel a task",
            parse_mode="HTML"
        )
        return
    
    prompt = " ".join(context.args)
    
    # Default timeout: 10 minutes for Agent tasks
    timeout = 600.0
    
    # Get task manager
    manager = get_task_manager()
    
    # Submit task
    task_id = await manager.submit_agent_task(
        user_id=user_id,
        chat_id=chat_id,
        platform="telegram",
        prompt=prompt,
        timeout=timeout,
    )
    
    # Send confirmation with task ID
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("View Status", callback_data=f"task_status:{task_id}"),
            InlineKeyboardButton("Cancel", callback_data=f"task_cancel:{task_id}"),
        ]
    ])
    
    await update.message.reply_text(
        f"🚀 <b>Task Submitted</b>\n\n"
        f"Task ID: <code>{_escape_html(task_id)}</code>\n"
        f"Type: Agent\n"
        f"Timeout: {int(timeout/60)} minutes\n\n"
        f"Your task is running in the background.\n"
        f"You'll receive a message when it completes.",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ============================================
# Async CLI Handler
# ============================================

async def cli_async_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /cli_async command - Run CLI in background.
    
    Usage:
        /cli_async <prompt>
        /cli_bg <prompt>
        
    The task runs in background and pushes result when complete.
    """
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "<b>Async CLI</b>\n\n"
            "Usage: <code>/cli_async &lt;prompt&gt;</code>\n\n"
            "The task runs in background. You'll receive a message when it completes.\n\n"
            "Example:\n"
            "<code>/cli_async Refactor the main function in src/main.py</code>\n\n"
            "Related commands:\n"
            "- <code>/tasks</code> - View your pending tasks\n"
            "- <code>/cancel &lt;task_id&gt;</code> - Cancel a task",
            parse_mode="HTML"
        )
        return
    
    prompt = " ".join(context.args)
    working_dir = os.getenv("CURSOR_WORKSPACE_PATH", os.getcwd())
    
    # Default timeout: 15 minutes for CLI tasks
    timeout = 900.0
    
    # Get task manager
    manager = get_task_manager()
    
    # Submit task
    task_id = await manager.submit_cli_task(
        user_id=user_id,
        chat_id=chat_id,
        platform="telegram",
        prompt=prompt,
        working_directory=working_dir,
        timeout=timeout,
    )
    
    # Send confirmation
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("View Status", callback_data=f"task_status:{task_id}"),
            InlineKeyboardButton("Cancel", callback_data=f"task_cancel:{task_id}"),
        ]
    ])
    
    await update.message.reply_text(
        f"🚀 <b>Task Submitted</b>\n\n"
        f"Task ID: <code>{_escape_html(task_id)}</code>\n"
        f"Type: Cursor CLI\n"
        f"Working Dir: <code>{_escape_html(os.path.basename(working_dir))}</code>\n"
        f"Timeout: {int(timeout/60)} minutes\n\n"
        f"Your task is running in the background.\n"
        f"You'll receive a message when it completes.",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ============================================
# Async RAG Handler
# ============================================

async def rag_async_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /rag_async command - Run RAG query in background.
    """
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Async RAG Query**\n\n"
            "Usage: `/rag_async <question>`\n\n"
            "Example:\n"
            "`/rag_async What is the main purpose of this project?`",
            parse_mode="HTML"
        )
        return
    
    question = " ".join(context.args)
    
    manager = get_task_manager()
    
    task_id = await manager.submit_rag_task(
        user_id=user_id,
        chat_id=chat_id,
        platform="telegram",
        question=question,
        timeout=120.0,
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("View Status", callback_data=f"task_status:{task_id}"),
            InlineKeyboardButton("Cancel", callback_data=f"task_cancel:{task_id}"),
        ]
    ])
    
    await update.message.reply_text(
        f"🔍 **RAG Query Submitted**\n\n"
        f"Task ID: `{task_id}`\n\n"
        f"Searching knowledge base in background...",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ============================================
# Task Management Commands
# ============================================

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tasks command - View user's tasks.
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    manager = get_task_manager()
    tasks = manager.get_user_tasks(user_id)
    
    if not tasks:
        await update.message.reply_text(
            "📋 **Your Tasks**\n\n"
            "No tasks found.\n\n"
            "Submit a task with:\n"
            "- `/agent_async <prompt>`\n"
            "- `/cli_async <prompt>`\n"
            "- `/rag_async <question>`",
            parse_mode="HTML"
        )
        return
    
    # Format task list
    lines = ["📋 **Your Tasks**\n"]
    
    for task in tasks[:10]:  # Show last 10 tasks
        status_emoji = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "🚫",
            TaskStatus.TIMEOUT: "⏱️",
        }.get(task.status, "❓")
        
        prompt_preview = task.input_data.get("prompt", "")[:30]
        if len(task.input_data.get("prompt", "")) > 30:
            prompt_preview += "..."
        
        lines.append(
            f"{status_emoji} `{task.id}` - {task.type.value}\n"
            f"   {prompt_preview}\n"
            f"   Status: {task.status.value}"
        )
        
        if task.duration_seconds > 0:
            lines[-1] += f" ({task.duration_seconds:.1f}s)"
        
        lines.append("")
    
    # Add buttons for active tasks
    buttons = []
    active_tasks = [t for t in tasks if t.is_active]
    
    if active_tasks:
        for task in active_tasks[:3]:
            buttons.append([
                InlineKeyboardButton(f"Cancel {task.id}", callback_data=f"task_cancel:{task.id}")
            ])
    
    keyboard = InlineKeyboardMarkup(buttons) if buttons else None
    
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def cancel_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /cancel command - Cancel a task.
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Cancel Task**\n\n"
            "Usage: `/cancel <task_id>`\n\n"
            "Example: `/cancel abc12345`\n\n"
            "Use `/tasks` to see your task IDs.",
            parse_mode="HTML"
        )
        return
    
    task_id = context.args[0]
    
    manager = get_task_manager()
    task = manager.get_task(task_id)
    
    if not task:
        await update.message.reply_text(f"Task `{task_id}` not found.", parse_mode="HTML")
        return
    
    if task.user_id != user_id:
        await update.message.reply_text("You can only cancel your own tasks.")
        return
    
    if not task.is_active:
        await update.message.reply_text(
            f"Task `{task_id}` is already {task.status.value}.",
            parse_mode="HTML"
        )
        return
    
    success = await manager.cancel_task(task_id)
    
    if success:
        await update.message.reply_text(f"🚫 Task `{task_id}` cancelled.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"Failed to cancel task `{task_id}`.", parse_mode="HTML")


async def task_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /task_status command - View task details.
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Task Status**\n\n"
            "Usage: `/task_status <task_id>`",
            parse_mode="HTML"
        )
        return
    
    task_id = context.args[0]
    manager = get_task_manager()
    task = manager.get_task(task_id)
    
    if not task:
        await update.message.reply_text(f"Task `{task_id}` not found.", parse_mode="HTML")
        return
    
    status_emoji = {
        TaskStatus.PENDING: "⏳",
        TaskStatus.RUNNING: "🔄",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
        TaskStatus.CANCELLED: "🚫",
        TaskStatus.TIMEOUT: "⏱️",
    }.get(task.status, "❓")
    
    prompt = task.input_data.get("prompt", task.input_data.get("question", "N/A"))
    
    text = (
        f"{status_emoji} **Task Details**\n\n"
        f"**ID:** `{task.id}`\n"
        f"**Type:** {task.type.value}\n"
        f"**Status:** {task.status.value}\n"
        f"**Duration:** {task.duration_seconds:.1f}s\n\n"
        f"**Input:**\n```\n{prompt[:500]}{'...' if len(prompt) > 500 else ''}\n```"
    )
    
    if task.error:
        text += f"\n\n**Error:**\n```\n{task.error[:300]}\n```"
    
    if task.result and task.status == TaskStatus.COMPLETED:
        result_preview = str(task.result)[:500]
        if len(str(task.result)) > 500:
            result_preview += "..."
        text += f"\n\n**Result:**\n```\n{result_preview}\n```"
    
    # Add cancel button if active
    keyboard = None
    if task.is_active:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel Task", callback_data=f"task_cancel:{task.id}")]
        ])
    
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


# ============================================
# Callback Handlers
# ============================================

async def task_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle task-related callback queries."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = query.data
    
    if not is_authorized(user_id):
        await query.edit_message_text("Unauthorized")
        return
    
    manager = get_task_manager()
    
    if data.startswith("task_status:"):
        task_id = data.split(":", 1)[1]
        task = manager.get_task(task_id)
        
        if not task:
            await query.edit_message_text(f"Task `{task_id}` not found.", parse_mode="HTML")
            return
        
        status_emoji = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "🚫",
            TaskStatus.TIMEOUT: "⏱️",
        }.get(task.status, "❓")
        
        text = (
            f"{status_emoji} **Task Status**\n\n"
            f"**ID:** `{task.id}`\n"
            f"**Type:** {task.type.value}\n"
            f"**Status:** {task.status.value}\n"
            f"**Duration:** {task.duration_seconds:.1f}s\n"
        )
        
        if task.progress.message:
            text += f"\n**Progress:** {task.progress.message}"
        
        buttons = []
        if task.is_active:
            buttons.append([
                InlineKeyboardButton("Refresh", callback_data=f"task_status:{task.id}"),
                InlineKeyboardButton("Cancel", callback_data=f"task_cancel:{task.id}"),
            ])
        
        keyboard = InlineKeyboardMarkup(buttons) if buttons else None
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    
    elif data.startswith("task_cancel:"):
        task_id = data.split(":", 1)[1]
        task = manager.get_task(task_id)
        
        if not task:
            await query.edit_message_text(f"Task `{task_id}` not found.", parse_mode="HTML")
            return
        
        if task.user_id != user_id:
            await query.edit_message_text("You can only cancel your own tasks.")
            return
        
        if not task.is_active:
            await query.edit_message_text(
                f"Task `{task_id}` is already {task.status.value}.",
                parse_mode="HTML"
            )
            return
        
        success = await manager.cancel_task(task_id)
        
        if success:
            await query.edit_message_text(
                f"🚫 Task `{task_id}` cancelled.",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                f"Failed to cancel task `{task_id}`.",
                parse_mode="HTML"
            )


# ============================================
# Task Stats Command (Admin)
# ============================================

async def task_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /task_stats command - View task manager statistics.
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    manager = get_task_manager()
    stats = manager.get_stats()
    
    text = (
        "📊 **Task Manager Statistics**\n\n"
        f"**Total Tasks:** {stats['total_tasks']}\n"
        f"**Active Tasks:** {stats['active_tasks']}\n"
        f"**Max Concurrent:** {stats['max_concurrent']}\n"
        f"**Avg Duration:** {stats['avg_duration_seconds']}s\n\n"
        "**By Status:**\n"
    )
    
    for status, count in stats['by_status'].items():
        text += f"  - {status}: {count}\n"
    
    text += "\n**By Type:**\n"
    for task_type, count in stats['by_type'].items():
        text += f"  - {task_type}: {count}\n"
    
    await update.message.reply_text(text, parse_mode="HTML")


# ============================================
# Handler Registration
# ============================================

def register_async_handlers(application) -> None:
    """Register async task handlers with the application."""
    # Async execution commands
    application.add_handler(CommandHandler("agent_async", agent_async_command))
    application.add_handler(CommandHandler("agent_bg", agent_async_command))
    application.add_handler(CommandHandler("cli_async", cli_async_command))
    application.add_handler(CommandHandler("cli_bg", cli_async_command))
    application.add_handler(CommandHandler("rag_async", rag_async_command))
    
    # Task management commands
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("cancel", cancel_task_command))
    application.add_handler(CommandHandler("task_status", task_status_command))
    application.add_handler(CommandHandler("task_stats", task_stats_command))
    
    # Callback handler for buttons
    application.add_handler(CallbackQueryHandler(task_callback_handler, pattern=r"^task_"))
    
    logger.info("Async task handlers registered")


__all__ = [
    "agent_async_command",
    "cli_async_command",
    "rag_async_command",
    "tasks_command",
    "cancel_task_command",
    "task_status_command",
    "task_stats_command",
    "task_callback_handler",
    "register_async_handlers",
]
