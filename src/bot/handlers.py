"""
Telegram Bot command and message handlers
Defines all user interaction endpoints
"""

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..cursor.agent import CursorAgent
from ..utils.auth import authorized_only
from ..utils.logger import logger

# Global Cursor Agent instance
cursor_agent: CursorAgent = None


def get_cursor_agent() -> CursorAgent:
    """Get or create the global Cursor Agent instance."""
    global cursor_agent
    if cursor_agent is None:
        from ..utils.config import settings
        cursor_agent = CursorAgent(use_mock=settings.debug)
    return cursor_agent


# ============================================
# Command Handlers
# ============================================


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command.
    Welcome message and basic instructions.
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")

    welcome_text = f"""
👋 <b>歡迎使用 CursorBot!</b>

您好, {user.first_name}! 我是您的 Cursor Agent 遠端控制助手。

<b>📋 可用指令:</b>
• /help - 顯示所有指令
• /status - 查看連線狀態
• /ask &lt;問題&gt; - 詢問 Cursor Agent
• /code &lt;指令&gt; - 執行程式碼操作
• /file &lt;路徑&gt; - 檔案操作
• /search &lt;關鍵字&gt; - 搜尋程式碼

<b>🔐 您的使用者 ID:</b> <code>{user.id}</code>

使用 /help 查看詳細說明。
"""
    await update.message.reply_text(welcome_text, parse_mode="HTML")


@authorized_only
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command.
    Display detailed help information.
    """
    help_text = """
<b>📖 CursorBot 指令說明</b>

<b>🔹 基礎指令</b>
• /start - 啟動並顯示歡迎訊息
• /help - 顯示此說明
• /status - 查看 Cursor Agent 連線狀態

<b>🔹 Cursor AI 對話</b>
• /ask &lt;問題&gt; - 詢問 Cursor Agent
• /repo &lt;url&gt; - 設定 GitHub 倉庫
• /agents - 列出所有 Agents
• /agent &lt;id&gt; - 查看 Agent 狀態
• 直接發送訊息也可以對話！

<b>🔹 檔案操作</b>
• /file read &lt;路徑&gt; - 讀取檔案內容
• /file list &lt;目錄&gt; - 列出目錄檔案
• /write &lt;路徑&gt; - 建立/覆寫檔案
• /edit &lt;檔案&gt; &lt;舊&gt; -&gt; &lt;新&gt; - 編輯檔案
• /delete &lt;路徑&gt; - 刪除檔案
• /undo - 復原上一次編輯
• /history - 顯示編輯歷史

<b>🔹 終端機操作</b>
• /run &lt;命令&gt; - 執行命令並等待結果
• /run_bg &lt;命令&gt; - 背景執行命令
• /jobs - 查看執行中的命令
• /kill &lt;ID&gt; - 停止執行中的命令

<b>🔹 任務管理</b>
• /tasks - 查看您的任務列表
• /cancel &lt;ID&gt; - 取消任務
• /queue - 查看任務佇列狀態

<b>🔹 工作區管理</b>
• /workspace - 顯示目前工作區資訊
• /workspace list - 列出所有可用工作區
• /cd &lt;名稱&gt; - 快速切換工作區
• /pwd - 顯示目前路徑

<b>🔹 搜尋與專案</b>
• /search &lt;關鍵字&gt; - 搜尋程式碼庫
• /project list - 列出專案
• /project switch &lt;名稱&gt; - 切換專案

<b>💡 提示:</b>
直接發送訊息也可以與 Cursor Agent 對話!
"""
    await update.message.reply_text(help_text, parse_mode="HTML")


@authorized_only
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /status command.
    Display Cursor Agent connection status.
    """
    agent = get_cursor_agent()
    status = await agent.get_status()

    if status["connected"]:
        status_emoji = "🟢"
        status_text = "已連線"
    else:
        status_emoji = "🔴"
        status_text = "未連線"

    message = f"""
<b>📊 系統狀態</b>

{status_emoji} <b>Cursor Agent:</b> {status_text}
📂 <b>工作目錄:</b> <code>{status.get('workspace', 'N/A')}</code>
⏱ <b>回應時間:</b> {status.get('latency', 'N/A')}ms

<b>📈 統計資訊</b>
• 已執行指令: {status.get('commands_executed', 0)}
• 上次活動: {status.get('last_activity', 'N/A')}
"""
    await update.message.reply_text(message, parse_mode="HTML")


@authorized_only
async def ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /ask command.
    Send a question to Cursor Cloud Agent.
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 請提供問題!\n\n"
            "用法: /ask <問題>\n"
            "例: /ask 如何實作快速排序?\n\n"
            "💡 需要先用 /repo 設定 GitHub 倉庫"
        )
        return

    question = " ".join(context.args)
    user_id = update.effective_user.id
    logger.info(f"User {user_id} asking: {question}")

    # Send typing indicator and status
    await update.message.chat.send_action("typing")
    status_msg = await update.message.reply_text(
        "🤔 <b>正在啟動 Cursor Agent...</b>\n\n"
        f"問題: {question[:100]}{'...' if len(question) > 100 else ''}",
        parse_mode="HTML",
    )

    # Get response from Cursor Cloud Agent
    from ..cursor.cursor_api import get_cursor_ai
    cursor = get_cursor_ai()
    response = await cursor.ask(user_id, question)

    # Truncate if too long for Telegram
    if len(response) > 4000:
        response = response[:4000] + "\n\n... (回覆過長已截斷)"

    await status_msg.edit_text(
        f"🤖 <b>Cursor Agent 回覆</b>\n\n{response}",
        parse_mode="HTML",
    )


@authorized_only
async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /code command.
    Execute code-related operations.
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 請提供程式碼指令!\n\n用法: /code <指令>\n例: /code 建立 hello world"
        )
        return

    instruction = " ".join(context.args)
    logger.info(f"User {update.effective_user.id} code instruction: {instruction}")

    await update.message.chat.send_action("typing")

    agent = get_cursor_agent()
    result = await agent.execute_code_instruction(instruction)

    await update.message.reply_text(
        f"⚙️ <b>執行結果:</b>\n\n<pre>{result}</pre>",
        parse_mode="HTML",
    )


@authorized_only
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /file command.
    File operations (read, list, etc.)
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 請提供檔案操作!\n\n"
            "用法:\n"
            "• /file read <路徑> - 讀取檔案\n"
            "• /file list <目錄> - 列出檔案"
        )
        return

    operation = context.args[0].lower()
    path = " ".join(context.args[1:]) if len(context.args) > 1 else "."

    agent = get_cursor_agent()

    if operation == "read":
        content = await agent.read_file(path)
        if len(content) > 4000:
            content = content[:4000] + "\n... (內容過長已截斷)"
        await update.message.reply_text(
            f"📄 <b>{path}</b>\n\n<pre>{content}</pre>",
            parse_mode="HTML",
        )
    elif operation == "list":
        files = await agent.list_files(path)
        await update.message.reply_text(
            f"📂 <b>{path}</b>\n\n{files}",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(f"❌ 未知操作: {operation}")


@authorized_only
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /search command.
    Search code in workspace.
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 請提供搜尋關鍵字!\n\n用法: /search <關鍵字>"
        )
        return

    query = " ".join(context.args)
    logger.info(f"User {update.effective_user.id} searching: {query}")

    await update.message.chat.send_action("typing")

    agent = get_cursor_agent()
    results = await agent.search_code(query)

    await update.message.reply_text(
        f"🔍 <b>搜尋結果: {query}</b>\n\n{results}",
        parse_mode="HTML",
    )


@authorized_only
async def project_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /project command.
    Project management operations.
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 請提供專案操作!\n\n"
            "用法:\n"
            "• /project list - 列出專案\n"
            "• /project switch <名稱> - 切換專案"
        )
        return

    operation = context.args[0].lower()
    agent = get_cursor_agent()

    if operation == "list":
        projects = await agent.list_projects()
        await update.message.reply_text(
            f"📁 <b>專案列表:</b>\n\n{projects}",
            parse_mode="HTML",
        )
    elif operation == "switch" and len(context.args) > 1:
        project_name = " ".join(context.args[1:])
        result = await agent.switch_project(project_name)
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("❌ 未知操作或缺少參數")


@authorized_only
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle regular text messages.
    Forward to Cursor Cloud Agent.
    """
    message_text = update.message.text
    user_id = update.effective_user.id
    logger.info(f"User {user_id} message: {message_text[:50]}...")

    await update.message.chat.send_action("typing")

    # Use Cursor Cloud Agent
    from ..cursor.cursor_api import get_cursor_ai
    cursor = get_cursor_ai()
    
    if not cursor.is_configured:
        await update.message.reply_text(
            "❌ Cursor API 未設定\n\n"
            "請在 .env 中設定：\n"
            "<code>CURSOR_API_KEY=your_api_key</code>\n\n"
            "從 https://cursor.com/settings 獲取 API Key"
        , parse_mode="HTML")
        return

    response = await cursor.ask(user_id, message_text)

    # Truncate if too long
    if len(response) > 4000:
        response = response[:4000] + "\n\n... (回覆過長已截斷)"

    await update.message.reply_text(response, parse_mode="HTML")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error {context.error}")

    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ 發生錯誤,請稍後重試。\n\n"
            f"<code>{str(context.error)[:200]}</code>",
            parse_mode="HTML",
        )


def setup_handlers(app: Application) -> None:
    """
    Setup all command and message handlers for the application.

    Args:
        app: Telegram Application instance
    """
    # Command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("ask", ask_handler))
    app.add_handler(CommandHandler("code", code_handler))
    app.add_handler(CommandHandler("file", file_handler))
    app.add_handler(CommandHandler("search", search_handler))
    app.add_handler(CommandHandler("project", project_handler))

    # Message handler for regular text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Error handler
    app.add_error_handler(error_handler)

    # Setup extended handlers (file editing, terminal, task management)
    from .handlers_extended import setup_extended_handlers
    setup_extended_handlers(app)

    logger.info("Bot handlers configured successfully")


__all__ = ["setup_handlers"]
