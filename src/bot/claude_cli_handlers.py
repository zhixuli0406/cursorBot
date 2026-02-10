"""
Claude Code CLI notification handlers for Telegram
"""

from telegram import Update
from telegram.ext import ContextTypes

from ...integrations.claude_cli_notifier import get_claude_cli_notifier
from ...integrations.claude_cli_monitor import get_claude_cli_monitor
from ...utils.logger import logger


async def cmd_claude_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    啟用 Claude Code CLI 任務完成通知

    Usage: /claude_notify [on|off|status]
    """
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)

    # 解析參數
    args = context.args
    action = args[0].lower() if args else "on"

    notifier = get_claude_cli_notifier()

    if action == "on":
        # 啟用通知
        notifier.register_user(user_id, "telegram", chat_id)
        await update.message.reply_text(
            "✅ **Claude Code CLI 通知已啟用**\n\n"
            "當您在電腦端執行的 Claude Code CLI 任務完成時，"
            "我會自動發送通知到這個聊天。\n\n"
            "監控目錄: `~/.claude/`"
        )
        logger.info(f"User {user_id} enabled Claude CLI notifications")

    elif action == "off":
        # 停用通知（從映射中移除）
        if user_id in notifier.user_platform_map:
            del notifier.user_platform_map[user_id]
            del notifier.user_chat_map[user_id]
        await update.message.reply_text("❌ Claude Code CLI 通知已停用")
        logger.info(f"User {user_id} disabled Claude CLI notifications")

    elif action == "status":
        # 查看狀態
        monitor = get_claude_cli_monitor()
        is_enabled = user_id in notifier.user_platform_map

        running_tasks = monitor.list_tasks(status="running")
        completed_tasks = monitor.list_tasks(status="completed")

        status_msg = (
            f"📊 **Claude CLI 通知狀態**\n\n"
            f"通知狀態: {'✅ 已啟用' if is_enabled else '❌ 未啟用'}\n"
            f"監控目錄: `~/.claude/`\n"
            f"運行中任務: {len(running_tasks)}\n"
            f"已完成任務: {len(completed_tasks)}\n"
        )

        if running_tasks:
            status_msg += "\n**運行中的任務:**\n"
            for task in running_tasks[:5]:  # 最多顯示5個
                status_msg += f"• `{task.task_id}` (已運行 {int(task.duration or 0)}秒)\n"

        await update.message.reply_text(status_msg, parse_mode="Markdown")

    else:
        await update.message.reply_text(
            "用法: `/claude_notify [on|off|status]`\n\n"
            "• `on` - 啟用通知\n"
            "• `off` - 停用通知\n"
            "• `status` - 查看狀態"
        )


async def cmd_claude_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    查看 Claude Code CLI 任務列表

    Usage: /claude_tasks [running|completed|all]
    """
    args = context.args
    filter_status = args[0].lower() if args else "all"

    monitor = get_claude_cli_monitor()

    if filter_status == "running":
        tasks = monitor.list_tasks(status="running")
        title = "🏃 **運行中的任務**"
    elif filter_status == "completed":
        tasks = monitor.list_tasks(status="completed")
        title = "✅ **已完成的任務**"
    else:
        tasks = monitor.list_tasks()
        title = "📋 **所有任務**"

    if not tasks:
        await update.message.reply_text(f"{title}\n\n暫無任務")
        return

    # 構建任務列表消息
    message = f"{title}\n\n"

    for i, task in enumerate(tasks[:10], 1):  # 最多顯示10個
        status_emoji = {
            "running": "🏃",
            "completed": "✅",
            "failed": "❌",
        }.get(task.status, "❓")

        duration = f"{int(task.duration)}秒" if task.duration else "進行中"

        message += (
            f"{i}. {status_emoji} `{task.task_id}`\n"
            f"   狀態: {task.status} | 時長: {duration}\n"
        )

        if task.error:
            message += f"   ⚠️ 錯誤: {task.error[:50]}...\n"

        message += "\n"

    if len(tasks) > 10:
        message += f"\n... 還有 {len(tasks) - 10} 個任務"

    await update.message.reply_text(message, parse_mode="Markdown")


async def cmd_claude_task_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    查看任務詳情

    Usage: /claude_task <task_id>
    """
    if not context.args:
        await update.message.reply_text(
            "請提供任務ID\n\n"
            "用法: `/claude_task <task_id>`"
        )
        return

    task_id = context.args[0]
    monitor = get_claude_cli_monitor()
    task = monitor.get_task(task_id)

    if not task:
        await update.message.reply_text(f"❌ 找不到任務: `{task_id}`")
        return

    # 構建詳情消息
    status_emoji = {
        "running": "🏃",
        "completed": "✅",
        "failed": "❌",
    }.get(task.status, "❓")

    duration = f"{task.duration:.1f}秒" if task.duration else "進行中"

    message = f"{status_emoji} **任務詳情**\n\n"
    message += f"**ID**: `{task.task_id}`\n"
    message += f"**狀態**: {task.status}\n"
    message += f"**執行時長**: {duration}\n"

    if task.user_id:
        message += f"**用戶**: {task.user_id}\n"

    if task.metadata:
        message += f"\n**元數據**:\n"
        for key, value in task.metadata.items():
            message += f"• {key}: `{value}`\n"

    if task.output:
        output_preview = task.output[:300]
        if len(task.output) > 300:
            output_preview += "..."
        message += f"\n**輸出**:\n```\n{output_preview}\n```"

    if task.error:
        message += f"\n**錯誤**:\n```\n{task.error}\n```"

    await update.message.reply_text(message, parse_mode="Markdown")
