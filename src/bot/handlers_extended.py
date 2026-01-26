"""
Extended Telegram Bot handlers for CursorBot
Includes file editing, terminal, task management, and workspace commands
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from ..cursor.agent import CursorAgent
from ..cursor.file_operations import FileOperations
from ..cursor.terminal import TerminalManager
from ..utils.auth import authorized_only
from ..utils.config import settings
from ..utils.logger import logger
from ..utils.task_queue import TaskPriority, TaskQueue, get_task_queue

# Global instances
file_ops: FileOperations = None
terminal: TerminalManager = None
cursor_agent: CursorAgent = None


def get_cursor_agent() -> CursorAgent:
    """Get or create cursor agent instance."""
    global cursor_agent
    if cursor_agent is None:
        cursor_agent = CursorAgent(use_mock=settings.debug)
    return cursor_agent


def get_file_operations() -> FileOperations:
    """Get or create file operations instance."""
    global file_ops
    agent = get_cursor_agent()
    if file_ops is None or str(file_ops.workspace_path) != agent.get_current_workspace():
        file_ops = FileOperations(agent.get_current_workspace())
    return file_ops


def get_terminal() -> TerminalManager:
    """Get or create terminal manager instance."""
    global terminal
    agent = get_cursor_agent()
    if terminal is None or str(terminal.workspace_path) != agent.get_current_workspace():
        terminal = TerminalManager(agent.get_current_workspace())
    return terminal


def update_workspace_instances():
    """Update file_ops and terminal to use current workspace."""
    global file_ops, terminal
    agent = get_cursor_agent()
    current_ws = agent.get_current_workspace()

    file_ops = FileOperations(current_ws)
    terminal = TerminalManager(current_ws)


# ============================================
# File Editing Handlers
# ============================================


@authorized_only
async def edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /edit command for file editing.

    Usage:
        /edit <file> <old_text> -> <new_text>
        /edit <file> insert <line_number> <text>
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ 用法:\n"
            "• /edit <檔案> <舊文字> -> <新文字>\n"
            "• /edit <檔案> insert <行號> <文字>\n\n"
            "範例:\n"
            "<code>/edit main.py print(\"old\") -> print(\"new\")</code>",
            parse_mode="HTML",
        )
        return

    file_path = context.args[0]
    rest = " ".join(context.args[1:])

    ops = get_file_operations()

    # Check for insert operation
    if context.args[1].lower() == "insert" and len(context.args) >= 4:
        try:
            line_num = int(context.args[2])
            text = " ".join(context.args[3:])

            result = ops.insert_at_line(file_path, line_num, text)
        except ValueError:
            await update.message.reply_text("❌ 無效的行號")
            return
    else:
        # Replace operation
        if " -> " not in rest:
            await update.message.reply_text(
                "❌ 請使用 ' -> ' 分隔舊文字和新文字"
            )
            return

        parts = rest.split(" -> ", 1)
        old_text = parts[0]
        new_text = parts[1] if len(parts) > 1 else ""

        result = ops.edit_file(file_path, old_text, new_text)

    # Send result
    message = result.message
    if result.diff and len(result.diff) < 2000:
        message += f"\n\n<b>變更:</b>\n<pre>{result.diff[:1500]}</pre>"

    await update.message.reply_text(message, parse_mode="HTML")


@authorized_only
async def write_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /write command for creating/overwriting files.

    Usage:
        /write <file>
        <content>
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 用法:\n"
            "/write <檔案路徑>\n"
            "<檔案內容>\n\n"
            "範例:\n"
            "<code>/write hello.py\n"
            "print(\"Hello World\")</code>",
            parse_mode="HTML",
        )
        return

    # Get file path and content
    lines = update.message.text.split("\n")
    first_line_parts = lines[0].split(maxsplit=1)

    if len(first_line_parts) < 2:
        await update.message.reply_text("❌ 請提供檔案路徑")
        return

    file_path = first_line_parts[1]
    content = "\n".join(lines[1:]) if len(lines) > 1 else ""

    if not content:
        await update.message.reply_text("❌ 請提供檔案內容")
        return

    ops = get_file_operations()
    result = ops.write_file(file_path, content)

    await update.message.reply_text(result.message, parse_mode="HTML")


@authorized_only
async def delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /delete command for deleting files.

    Usage:
        /delete <file>
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 用法: /delete <檔案路徑>"
        )
        return

    file_path = " ".join(context.args)

    # Confirmation for safety
    # TODO: Add confirmation dialog

    ops = get_file_operations()
    result = ops.delete_file(file_path)

    await update.message.reply_text(result.message, parse_mode="HTML")


@authorized_only
async def undo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /undo command to undo last file change.
    """
    ops = get_file_operations()
    result = ops.undo_last_change()

    await update.message.reply_text(result.message, parse_mode="HTML")


@authorized_only
async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /history command to show file change history.
    """
    ops = get_file_operations()
    history = ops.get_history(limit=10)

    if not history:
        await update.message.reply_text("📝 尚無編輯歷史")
        return

    lines = ["<b>📝 最近編輯歷史:</b>\n"]
    for h in history:
        emoji = {"create": "✨", "update": "📝", "delete": "🗑️"}.get(h["operation"], "•")
        lines.append(f"{emoji} <code>{h['path']}</code> - {h['timestamp'][:19]}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ============================================
# Terminal Handlers
# ============================================


@authorized_only
async def run_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /run command for executing terminal commands.

    Usage:
        /run <command>
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 用法: /run <命令>\n\n"
            "範例:\n"
            "• /run ls -la\n"
            "• /run python --version\n"
            "• /run npm install"
        )
        return

    command = " ".join(context.args)
    user_id = update.effective_user.id

    await update.message.chat.send_action("typing")

    # Submit as task for queuing
    queue = get_task_queue()

    try:
        term = get_terminal()

        async def execute_command():
            return await term.execute(command, timeout=60)

        task = await queue.submit(
            user_id=user_id,
            name=f"run: {command[:30]}",
            func=execute_command,
            priority=TaskPriority.NORMAL,
        )

        # Wait for task to complete (with timeout)
        import asyncio

        for _ in range(120):  # 2 minutes max
            await asyncio.sleep(1)
            if task.status.value in ("completed", "failed", "timeout", "cancelled"):
                break

        if task.status.value == "completed" and task.result:
            result = task.result
            output = result.stdout or result.stderr or "(無輸出)"
            if len(output) > 3500:
                output = output[:3500] + "\n... (輸出過長已截斷)"

            status_emoji = "✅" if result.success else "❌"
            await update.message.reply_text(
                f"{status_emoji} <b>執行結果</b> (exit={result.exit_code})\n\n"
                f"<pre>{output}</pre>",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                f"❌ 任務狀態: {task.status.value}\n"
                f"錯誤: {task.error or '未知'}"
            )

    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")
    except Exception as e:
        logger.error(f"Run command error: {e}")
        await update.message.reply_text(f"❌ 執行錯誤: {str(e)}")


@authorized_only
async def run_bg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /run_bg command for background execution.

    Usage:
        /run_bg <command>
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 用法: /run_bg <命令>\n"
            "命令將在背景執行"
        )
        return

    command = " ".join(context.args)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    term = get_terminal()

    async def output_callback(cmd_id: str, line: str):
        # Send output to user (throttled)
        pass  # Implement if needed

    try:
        cmd_id = await term.start_background(
            command,
            output_callback=output_callback,
        )

        await update.message.reply_text(
            f"🚀 背景執行中\n"
            f"命令: <code>{command[:50]}</code>\n"
            f"ID: <code>{cmd_id}</code>\n\n"
            f"使用 /jobs 查看狀態\n"
            f"使用 /kill {cmd_id} 停止",
            parse_mode="HTML",
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")


@authorized_only
async def jobs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /jobs command to list running commands.
    """
    term = get_terminal()
    running = term.list_running()

    if not running:
        await update.message.reply_text("📋 目前沒有執行中的命令")
        return

    lines = ["<b>🔄 執行中的命令:</b>\n"]
    for job in running:
        lines.append(
            f"• <code>{job['id']}</code>: {job['command']}\n"
            f"  運行時間: {job['duration_s']}s"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


@authorized_only
async def kill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /kill command to stop a running command.

    Usage:
        /kill <command_id>
    """
    if not context.args:
        await update.message.reply_text("⚠️ 用法: /kill <命令ID>")
        return

    cmd_id = context.args[0]
    term = get_terminal()

    if await term.cancel_command(cmd_id):
        await update.message.reply_text(f"✅ 已停止命令: {cmd_id}")
    else:
        await update.message.reply_text(f"❌ 找不到命令或無法停止: {cmd_id}")


# ============================================
# Task Queue Handlers
# ============================================


@authorized_only
async def tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tasks command to list user's tasks.
    """
    user_id = update.effective_user.id
    queue = get_task_queue()

    tasks = queue.get_user_tasks(user_id, limit=10)

    if not tasks:
        await update.message.reply_text("📋 您沒有任何任務")
        return

    lines = ["<b>📋 您的任務:</b>\n"]
    for task in tasks:
        status_emoji = {
            "pending": "⏳",
            "queued": "📥",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "🚫",
            "timeout": "⏱️",
        }.get(task.status.value, "•")

        duration = f" ({task.duration_ms}ms)" if task.duration_ms else ""
        lines.append(
            f"{status_emoji} <code>{task.id}</code>: {task.name}{duration}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


@authorized_only
async def cancel_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /cancel command to cancel a task.

    Usage:
        /cancel <task_id>
    """
    if not context.args:
        await update.message.reply_text("⚠️ 用法: /cancel <任務ID>")
        return

    task_id = context.args[0]
    user_id = update.effective_user.id
    queue = get_task_queue()

    if await queue.cancel_task(task_id, user_id):
        await update.message.reply_text(f"✅ 已取消任務: {task_id}")
    else:
        await update.message.reply_text(
            f"❌ 無法取消任務: {task_id}\n"
            "可能任務不存在、已完成或不屬於您"
        )


@authorized_only
async def queue_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /queue command to show queue statistics.
    """
    queue = get_task_queue()
    stats = queue.get_queue_stats()

    lines = [
        "<b>📊 任務佇列狀態:</b>\n",
        f"• 佇列大小: {stats['queue_size']}/{stats['max_queue_size']}",
        f"• 工作執行緒: {stats['workers']}",
        f"• 狀態: {'運行中' if stats['running'] else '已停止'}",
        "\n<b>任務統計:</b>",
    ]

    for status, count in stats["tasks_by_status"].items():
        if count > 0:
            lines.append(f"• {status}: {count}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ============================================
# Workspace Handlers
# ============================================


@authorized_only
async def workspace_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /workspace command for workspace management.

    Usage:
        /workspace - Show current workspace info
        /workspace list - List all available workspaces
        /workspace switch <name> - Switch to a workspace
    """
    try:
        agent = get_cursor_agent()
        root_path = agent.get_root_workspace()

        logger.info(f"Workspace handler called, root: {root_path}")

        # Check if root workspace exists
        if not root_path.exists():
            await update.message.reply_text(
                f"❌ 工作區根目錄不存在\n\n"
                f"請確認 .env 中的 CURSOR_WORKSPACE_PATH 設定正確：\n"
                f"<code>{root_path}</code>",
                parse_mode="HTML",
            )
            return

        if not context.args:
            # Show current workspace info
            info = await agent.get_workspace_info()

            # Format file types
            types_str = ", ".join(
                f"{ext}: {count}" for ext, count in info["top_file_types"]
            ) or "（無）"

            # Format features
            features = []
            if info["has_git"]:
                features.append("📦 Git")
            if info["has_package_json"]:
                features.append("🟢 Node.js")
            if info["has_requirements"]:
                features.append("🐍 Python")
            if info["has_readme"]:
                features.append("📖 README")

            message = (
                f"<b>📂 目前工作區</b>\n\n"
                f"<b>名稱:</b> {info['name']}\n"
                f"<b>路徑:</b> <code>{info['path']}</code>\n"
                f"<b>檔案數:</b> {info['total_files']}\n"
                f"<b>主要類型:</b> {types_str}\n"
                f"<b>特性:</b> {' '.join(features) or '（無）'}\n\n"
                f"使用 /workspace list 查看所有工作區"
            )
            await update.message.reply_text(message, parse_mode="HTML")
            return

        subcommand = context.args[0].lower()

        if subcommand == "list":
            logger.info("Listing workspaces...")

            # List all workspaces with inline keyboard
            workspaces = await agent.list_workspaces()

            logger.info(f"Found {len(workspaces)} workspaces")

            if not workspaces:
                await update.message.reply_text(
                    f"❌ 找不到任何工作區\n\n"
                    f"根目錄: <code>{root_path}</code>",
                    parse_mode="HTML",
                )
                return

            # Create inline keyboard
            keyboard = []
            for ws in workspaces[:15]:  # Limit to 15
                current_mark = " ✓" if ws["is_current"] else ""
                button_text = f"{ws['type']} {ws['name']}{current_mark}"
                keyboard.append([
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"ws_switch:{ws['name']}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton("❌ 關閉", callback_data="ws_close")
            ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            # Also show as text
            formatted = await agent.list_workspaces_formatted()

            await update.message.reply_text(
                f"<b>📂 可用工作區</b>\n\n{formatted}\n\n"
                f"點擊下方按鈕切換工作區：",
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

        elif subcommand == "switch":
            if len(context.args) < 2:
                await update.message.reply_text(
                    "⚠️ 請提供工作區名稱\n\n"
                    "用法: /workspace switch <名稱>"
                )
                return

            workspace_name = " ".join(context.args[1:])
            result = await agent.switch_workspace(workspace_name)

            # Update file_ops and terminal to use new workspace
            if "✅" in result:
                update_workspace_instances()

            await update.message.reply_text(result, parse_mode="HTML")

        else:
            await update.message.reply_text(
                "⚠️ 未知的子指令\n\n"
                "可用指令:\n"
                "• /workspace - 顯示目前工作區\n"
                "• /workspace list - 列出所有工作區\n"
                "• /workspace switch <名稱> - 切換工作區"
            )

    except Exception as e:
        logger.error(f"Workspace handler error: {e}")
        await update.message.reply_text(
            f"❌ 發生錯誤: {str(e)}\n\n"
            f"請確認 CURSOR_WORKSPACE_PATH 設定正確",
            parse_mode="HTML",
        )


@authorized_only
async def ws_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Short alias for /workspace command.
    """
    await workspace_handler(update, context)


async def workspace_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle workspace inline keyboard callbacks.
    """
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "ws_close":
        await query.message.delete()
        return

    if data.startswith("ws_switch:"):
        workspace_name = data.split(":", 1)[1]

        # Check authorization
        user = update.effective_user
        from ..utils.auth import is_user_authorized
        if not is_user_authorized(user.id):
            await query.message.reply_text("⛔ 未授權的操作")
            return

        agent = get_cursor_agent()
        result = await agent.switch_workspace(workspace_name)

        # Update instances
        if "✅" in result:
            update_workspace_instances()

        # Update the message
        await query.message.edit_text(
            result,
            parse_mode="HTML",
        )


@authorized_only
async def pwd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /pwd command to show current working directory.
    """
    agent = get_cursor_agent()
    current = agent.get_current_workspace()
    name = agent.get_current_workspace_name()

    await update.message.reply_text(
        f"📂 <b>目前工作區:</b> {name}\n"
        f"📍 <code>{current}</code>",
        parse_mode="HTML",
    )


@authorized_only
async def cd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /cd command to quickly switch workspace.

    Usage:
        /cd <workspace_name>
    """
    if not context.args:
        # Show workspace list like /workspace list
        context.args = ["list"]
        await workspace_handler(update, context)
        return

    workspace_name = " ".join(context.args)
    agent = get_cursor_agent()
    result = await agent.switch_workspace(workspace_name)

    if "✅" in result:
        update_workspace_instances()

    await update.message.reply_text(result, parse_mode="HTML")


# ============================================
# Cursor Cloud Agent Handlers
# ============================================


@authorized_only
async def repo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /repo command to set default GitHub repository.
    
    Usage:
        /repo <github_url>
        /repo - Show current repo
    """
    from ..cursor.cursor_api import get_cursor_ai
    cursor = get_cursor_ai()

    if not context.args:
        # Show current repo
        repo = cursor._default_repo
        if repo:
            await update.message.reply_text(
                f"📦 <b>目前預設倉庫</b>\n\n"
                f"<code>{repo}</code>\n\n"
                f"使用 /repo <url> 更改",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                "❌ 尚未設定預設倉庫\n\n"
                "用法: /repo <github_url>\n"
                "例: /repo https://github.com/user/repo"
            )
        return

    repo_url = context.args[0]
    
    # Validate URL
    if not repo_url.startswith("https://github.com/"):
        await update.message.reply_text(
            "❌ 請提供有效的 GitHub 倉庫 URL\n\n"
            "例: https://github.com/username/repository"
        )
        return

    cursor.set_default_repo(repo_url)

    await update.message.reply_text(
        f"✅ 已設定預設倉庫\n\n"
        f"<code>{repo_url}</code>\n\n"
        f"現在可以使用 /ask 發問了！",
        parse_mode="HTML",
    )


@authorized_only
async def agents_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /agents command to list all agents.
    """
    from ..cursor.cursor_api import get_cursor_ai
    cursor = get_cursor_ai()

    if not cursor.is_configured:
        await update.message.reply_text(
            "❌ Cursor API 未設定\n\n"
            "請在 .env 設定 CURSOR_API_KEY"
        )
        return

    await update.message.chat.send_action("typing")
    
    user_id = update.effective_user.id
    result = await cursor.list_user_agents(user_id)
    
    await update.message.reply_text(result, parse_mode="HTML")


@authorized_only
async def agent_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /agent command to check agent status.
    
    Usage:
        /agent <agent_id>
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 用法: /agent <agent_id>\n\n"
            "例: /agent bc_abc123"
        )
        return

    agent_id = context.args[0]

    from ..cursor.cursor_api import get_cursor_ai
    cursor = get_cursor_ai()

    if not cursor.is_configured:
        await update.message.reply_text("❌ Cursor API 未設定")
        return

    await update.message.chat.send_action("typing")
    
    result = await cursor.get_agent_status(agent_id)
    await update.message.reply_text(result, parse_mode="HTML")


@authorized_only
async def models_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /models command to list available Cursor models.
    """
    from ..cursor.cursor_api import get_cursor_ai
    cursor = get_cursor_ai()

    if not cursor.is_configured:
        await update.message.reply_text("❌ Cursor API 未設定")
        return

    await update.message.chat.send_action("typing")

    try:
        models = await cursor.list_models()
        
        if models:
            models_text = "\n".join(f"• {m}" for m in models)
            await update.message.reply_text(
                f"<b>🧠 可用模型</b>\n\n{models_text}",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text("📋 無可用模型資訊")
    except Exception as e:
        await update.message.reply_text(f"❌ 錯誤: {str(e)}")


@authorized_only
async def cursor_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /cursor command to show Cursor API status.
    """
    from ..cursor.cursor_api import get_cursor_ai
    cursor = get_cursor_ai()

    if not cursor.is_configured:
        await update.message.reply_text(
            "<b>🔧 Cursor Cloud Agent 設定</b>\n\n"
            "❌ API Key 未設定\n\n"
            "<b>設定步驟:</b>\n"
            "1. 前往 https://cursor.com/settings\n"
            "2. 複製 API Key\n"
            "3. 在 .env 中設定:\n"
            "<code>CURSOR_API_KEY=your_key</code>\n\n"
            "<b>也需要設定 GitHub 倉庫:</b>\n"
            "/repo https://github.com/user/repo",
            parse_mode="HTML",
        )
        return

    await update.message.chat.send_action("typing")

    try:
        info = await cursor.verify_api_key()
        repo = cursor._default_repo or "（未設定）"

        await update.message.reply_text(
            f"<b>🤖 Cursor Cloud Agent</b>\n\n"
            f"✅ <b>狀態:</b> 已連接\n"
            f"👤 <b>帳號:</b> {info.get('userEmail', 'N/A')}\n"
            f"🔑 <b>Key 名稱:</b> {info.get('apiKeyName', 'N/A')}\n"
            f"📦 <b>預設倉庫:</b> {repo}\n\n"
            f"<b>指令:</b>\n"
            f"• /ask - 詢問 Cursor Agent\n"
            f"• /repo - 設定 GitHub 倉庫\n"
            f"• /agents - 列出 Agents\n"
            f"• /models - 列出可用模型",
            parse_mode="HTML",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ API 錯誤: {str(e)}")


def setup_extended_handlers(app) -> None:
    """
    Setup extended command handlers.

    Args:
        app: Telegram Application instance
    """
    from telegram.ext import CommandHandler

    # File operations
    app.add_handler(CommandHandler("edit", edit_handler))
    app.add_handler(CommandHandler("write", write_handler))
    app.add_handler(CommandHandler("delete", delete_handler))
    app.add_handler(CommandHandler("undo", undo_handler))
    app.add_handler(CommandHandler("history", history_handler))

    # Terminal operations
    app.add_handler(CommandHandler("run", run_handler))
    app.add_handler(CommandHandler("run_bg", run_bg_handler))
    app.add_handler(CommandHandler("jobs", jobs_handler))
    app.add_handler(CommandHandler("kill", kill_handler))

    # Task management
    app.add_handler(CommandHandler("tasks", tasks_handler))
    app.add_handler(CommandHandler("cancel", cancel_task_handler))
    app.add_handler(CommandHandler("queue", queue_stats_handler))

    # Workspace management
    app.add_handler(CommandHandler("workspace", workspace_handler))
    app.add_handler(CommandHandler("ws", ws_handler))
    app.add_handler(CommandHandler("pwd", pwd_handler))
    app.add_handler(CommandHandler("cd", cd_handler))

    # Cursor Cloud Agent handlers
    app.add_handler(CommandHandler("repo", repo_handler))
    app.add_handler(CommandHandler("agents", agents_handler))
    app.add_handler(CommandHandler("agent", agent_status_handler))
    app.add_handler(CommandHandler("models", models_handler))
    app.add_handler(CommandHandler("cursor", cursor_info_handler))

    # Callback handlers for inline keyboards
    app.add_handler(CallbackQueryHandler(
        workspace_callback_handler,
        pattern=r"^ws_"
    ))

    logger.info("Extended handlers configured")


__all__ = ["setup_extended_handlers"]
