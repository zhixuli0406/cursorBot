"""
Telegram Bot command and message handlers
Defines all user interaction endpoints
"""

import asyncio
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..cursor.agent import CursorAgent
from ..cursor.background_agent import (
    CursorBackgroundAgent,
    get_background_agent,
    get_task_tracker,
)
from ..utils.auth import authorized_only
from ..utils.config import settings
from ..utils.logger import logger

# Global Workspace Agent instance
workspace_agent: CursorAgent = None
background_agent: Optional[CursorBackgroundAgent] = None


def get_cursor_agent() -> CursorAgent:
    """Get or create the global Workspace Agent instance."""
    global workspace_agent
    if workspace_agent is None:
        workspace_agent = CursorAgent()
    return workspace_agent


def is_background_agent_enabled() -> bool:
    """Check if Background Agent is enabled and configured."""
    return (
        settings.background_agent_enabled
        and bool(settings.cursor_api_key)
    )


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
    # Check mode for different help text
    mode_info = ""
    if is_background_agent_enabled():
        mode_info = """
<b>🤖 目前模式: Background Agent (自動)</b>
問題會自動由雲端 Agent 處理，無需開啟 IDE！
"""
    else:
        mode_info = """
<b>📡 目前模式: MCP Server (手動)</b>
需要在 Cursor IDE 中處理問題。
💡 設定 CURSOR_SESSION_TOKEN 啟用自動模式！
"""

    help_text = f"""
<b>📖 CursorBot 指令說明</b>
{mode_info}
<b>🔹 基礎指令</b>
• /start - 啟動並顯示歡迎訊息
• /help - 顯示此說明
• /status - 查看系統狀態

<b>🔹 AI 對話 (Background Agent)</b>
• /ask &lt;問題&gt; - 發送問題給 AI Agent
• /repo &lt;owner/repo&gt; - 切換 GitHub 倉庫
• /repos - 查看我的倉庫
• /tasks - 查看我的任務列表
• /result &lt;ID&gt; - 查看任務結果
• /cancel_task &lt;ID&gt; - 取消執行中的任務

<b>🔹 MCP 模式 (需 IDE)</b>
• /check - 檢查 Cursor IDE 的回覆
• /pending - 查看待處理問題

<b>🔹 檔案操作</b>
• /file read &lt;路徑&gt; - 讀取檔案內容
• /file list &lt;目錄&gt; - 列出目錄檔案
• /write &lt;路徑&gt; - 建立/覆寫檔案
• /edit &lt;檔案&gt; &lt;舊&gt; -&gt; &lt;新&gt; - 編輯檔案
• /delete &lt;路徑&gt; - 刪除檔案
• /undo - 復原上一次編輯

<b>🔹 終端機操作</b>
• /run &lt;命令&gt; - 執行命令並等待結果
• /run_bg &lt;命令&gt; - 背景執行命令
• /jobs - 查看執行中的命令
• /kill &lt;ID&gt; - 停止執行中的命令

<b>🔹 工作區管理</b>
• /workspace - 顯示目前工作區資訊
• /workspace list - 列出所有可用工作區
• /cd &lt;名稱&gt; - 快速切換工作區
• /search &lt;關鍵字&gt; - 搜尋程式碼

<b>💡 提示:</b>
直接發送訊息也可以與 AI Agent 對話!
"""
    await update.message.reply_text(help_text, parse_mode="HTML")


@authorized_only
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /status command.
    Display system and MCP status.
    """
    # Check pending questions (MCP mode)
    from ..cursor.mcp_server import get_pending_questions, get_new_answers
    pending = get_pending_questions()
    answers = get_new_answers()

    # Get workspace info
    agent = get_cursor_agent()
    ws_info = await agent.get_workspace_info()

    # Check Background Agent status
    if is_background_agent_enabled():
        bg_status = "🟢 Background Agent 已啟用"
        tracker = get_task_tracker()
        running_tasks = tracker.get_pending_tasks()
        bg_tasks_info = f"🔄 <b>執行中任務:</b> {len(running_tasks)}"
        
        # Show repo info
        if settings.cursor_github_repo:
            repo_name = settings.cursor_github_repo.split("/")[-1]
            bg_status += f"\n📁 倉庫: {repo_name}"
        else:
            bg_status += "\n⚠️ 未設定 GitHub 倉庫"
        
        # Test connection
        try:
            bg_agent = get_background_agent(settings.cursor_api_key)
            test_result = await bg_agent.test_connection()
            if test_result.get("success"):
                bg_status += f"\n✅ API 連線正常"
            else:
                bg_status += f"\n❌ API 連線失敗"
        except Exception as e:
            bg_status += f"\n❌ 錯誤: {str(e)[:30]}"
    else:
        bg_status = "⚪ Background Agent 未啟用"
        bg_tasks_info = ""

    mcp_status = "🟢 MCP Server 已啟用"

    message = f"""
<b>📊 系統狀態</b>

<b>🤖 Background Agent</b>
{bg_status}
{bg_tasks_info}

<b>📡 MCP Server</b>
{mcp_status}
📝 待處理問題: {len(pending)}
💬 新回覆: {len(answers)}

<b>📂 工作區</b>
• 名稱: {ws_info['name']}
• 檔案數: {ws_info['total_files']}
• 路徑: <code>{ws_info['path']}</code>

<b>💡 使用方式</b>
{"• /ask 發送問題 → 自動執行" if is_background_agent_enabled() else "• /ask 發送問題 → Cursor IDE 處理"}
• /tasks 查看任務狀態
• /check 檢查回覆
"""
    await update.message.reply_text(message, parse_mode="HTML")


@authorized_only
async def ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /ask command.
    Send a question to Cursor Background Agent or MCP.
    """
    if not context.args:
        mode = "Background Agent 自動處理" if is_background_agent_enabled() else "Cursor IDE 手動處理"
        await update.message.reply_text(
            f"⚠️ 請提供問題!\n\n"
            f"用法: /ask <問題>\n"
            f"例: /ask 如何實作快速排序?\n\n"
            f"💡 目前模式: {mode}"
        )
        return

    question = " ".join(context.args)
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat_id = update.effective_chat.id
    logger.info(f"User {user_id} asking: {question}")

    # Check if Background Agent is enabled
    if is_background_agent_enabled():
        await _handle_background_agent_ask(update, question, user_id, username, chat_id)
    else:
        await _handle_mcp_ask(update, question, user_id, username)


async def _handle_background_agent_ask(
    update: Update,
    question: str,
    user_id: int,
    username: str,
    chat_id: int,
) -> None:
    """Handle ask command using Background Agent."""
    # Get user's current repo
    repo_url = get_user_repo(user_id)
    
    # Check if GitHub repo is configured
    if not repo_url:
        await update.message.reply_text(
            "⚠️ <b>未設定 GitHub 倉庫</b>\n\n"
            "Background Agent 需要指定 GitHub 倉庫才能運作。\n\n"
            "<b>設定方式:</b>\n"
            "1. 使用 <code>/repo owner/repo-name</code> 指定倉庫\n"
            "2. 或在 .env 設定 CURSOR_GITHUB_REPO\n\n"
            "<b>範例:</b>\n"
            "<code>/repo lizhixu/cursorBot</code>",
            parse_mode="HTML",
        )
        return

    repo_name = repo_url.split("/")[-1]
    
    # Send initial response
    status_msg = await update.message.reply_text(
        f"🚀 <b>正在啟動 Background Agent...</b>\n\n"
        f"📁 倉庫: <code>{repo_name}</code>\n"
        f"❓ 問題: {question[:80]}{'...' if len(question) > 80 else ''}",
        parse_mode="HTML",
    )

    try:
        # Create background agent task
        bg_agent = get_background_agent(settings.cursor_api_key)
        result = await bg_agent.create_task(
            prompt=question,
            repo_url=repo_url,
        )

        if not result.get("success"):
            error_msg = result.get('message', 'Unknown error')
            
            # Provide specific guidance based on error
            if "repository" in error_msg.lower():
                hint = "請確認 CURSOR_GITHUB_REPO 設定正確"
            elif "401" in error_msg or "auth" in error_msg.lower():
                hint = "API Key 無效或已過期"
            elif "403" in error_msg:
                hint = "沒有權限存取此倉庫"
            else:
                hint = "請檢查 API Key 和倉庫設定"
            
            await status_msg.edit_text(
                f"❌ <b>建立任務失敗</b>\n\n"
                f"原因: {error_msg[:150]}\n\n"
                f"💡 {hint}",
                parse_mode="HTML",
            )
            return

        composer_id = result.get("composer_id")
        
        # Track the task
        tracker = get_task_tracker()
        tracker.add_task(user_id, composer_id, question, chat_id)

        await status_msg.edit_text(
            f"✅ <b>任務已建立</b>\n\n"
            f"🆔 任務 ID: <code>{composer_id}</code>\n"
            f"❓ 問題: {question[:80]}{'...' if len(question) > 80 else ''}\n\n"
            f"⏳ 正在執行中...\n"
            f"使用 /tasks 查看狀態\n"
            f"使用 /result {composer_id[:8]} 查看結果",
            parse_mode="HTML",
        )

        # Start background polling for this task
        asyncio.create_task(
            _poll_task_completion(update, composer_id, status_msg)
        )

    except Exception as e:
        logger.error(f"Background Agent error: {e}")
        await status_msg.edit_text(
            f"❌ <b>執行錯誤</b>\n\n"
            f"<code>{str(e)[:200]}</code>",
            parse_mode="HTML",
        )


async def _poll_task_completion(
    update: Update,
    composer_id: str,
    status_msg,
) -> None:
    """Poll for task completion and send result."""
    try:
        bg_agent = get_background_agent(settings.cursor_api_key)
        tracker = get_task_tracker()

        result = await bg_agent.wait_for_completion(
            composer_id,
            timeout=settings.background_agent_timeout,
            poll_interval=settings.background_agent_poll_interval,
        )

        # Update tracker
        tracker.update_task(
            composer_id,
            result.get("status", "unknown"),
            result.get("output", ""),
        )

        if result.get("success"):
            output = result.get("output", "（無輸出）")
            if len(output) > 3500:
                output = output[:3500] + "\n\n... (內容過長已截斷)"

            await update.effective_chat.send_message(
                f"✅ <b>任務完成</b>\n\n"
                f"🆔 <code>{composer_id[:8]}</code>\n\n"
                f"📝 <b>結果:</b>\n{output}",
                parse_mode="HTML",
            )
        else:
            await update.effective_chat.send_message(
                f"❌ <b>任務失敗</b>\n\n"
                f"🆔 <code>{composer_id[:8]}</code>\n"
                f"狀態: {result.get('status', 'unknown')}\n"
                f"原因: {result.get('message', 'Unknown')}",
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Poll error: {e}")


async def _handle_mcp_ask(
    update: Update,
    question: str,
    user_id: int,
    username: str,
) -> None:
    """Handle ask command using MCP (fallback mode)."""
    from ..cursor.mcp_server import add_question
    import uuid

    question_id = str(uuid.uuid4())[:8]
    add_question(question_id, user_id, username, question)

    await update.message.reply_text(
        f"✅ <b>問題已發送到 Cursor IDE</b>\n\n"
        f"📝 ID: <code>{question_id}</code>\n"
        f"❓ 問題: {question[:100]}{'...' if len(question) > 100 else ''}\n\n"
        f"<b>下一步：</b>\n"
        f"1. 在 Cursor IDE 中呼叫 <code>get_telegram_questions</code> 工具\n"
        f"2. 或使用 /check 檢查是否有回覆\n\n"
        f"💡 提示: 設定 CURSOR_API_KEY 啟用自動模式",
        parse_mode="HTML",
    )


@authorized_only
async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /code command.
    Send code instruction to Cursor IDE via MCP.
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 請提供程式碼指令!\n\n"
            "用法: /code <指令>\n"
            "例: /code 建立一個 hello world 函數\n\n"
            "💡 指令會發送到 Cursor IDE"
        )
        return

    instruction = " ".join(context.args)
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"User {user_id} code instruction: {instruction}")

    # Add as a question for Cursor IDE (with code prefix)
    from ..cursor.mcp_server import add_question
    import uuid
    
    question_id = str(uuid.uuid4())[:8]
    code_prompt = f"[程式碼指令] {instruction}"
    add_question(question_id, user_id, username, code_prompt)

    await update.message.reply_text(
        f"✅ <b>程式碼指令已發送到 Cursor IDE</b>\n\n"
        f"📝 ID: <code>{question_id}</code>\n"
        f"⚙️ 指令: {instruction[:80]}{'...' if len(instruction) > 80 else ''}\n\n"
        f"使用 /check 檢查回覆",
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
async def check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /check command.
    Check for answers from Cursor IDE.
    """
    from ..cursor.mcp_server import get_new_answers, get_pending_questions

    answers = get_new_answers()
    
    if answers:
        for ans in answers:
            response = ans.get("answer", "")
            if len(response) > 4000:
                response = response[:4000] + "\n\n... (回覆過長已截斷)"
            
            await update.message.reply_text(
                f"🤖 <b>Cursor 回覆</b>\n\n{response}",
                parse_mode="HTML",
            )
    else:
        pending = get_pending_questions()
        if pending:
            await update.message.reply_text(
                f"⏳ 尚無新回覆\n\n"
                f"還有 {len(pending)} 個問題待處理\n\n"
                f"請在 Cursor IDE 中處理問題"
            )
        else:
            await update.message.reply_text(
                "✅ 沒有待處理的問題\n\n"
                "使用 /ask <問題> 發送新問題"
            )


@authorized_only
async def pending_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /pending command.
    Show pending questions.
    """
    from ..cursor.mcp_server import get_pending_questions

    pending = get_pending_questions()
    
    if not pending:
        await update.message.reply_text(
            "✅ 沒有待處理的問題\n\n"
            "使用 /ask <問題> 發送新問題"
        )
        return

    lines = [f"<b>📋 待處理問題 ({len(pending)})</b>\n"]
    
    for q in pending[:10]:
        question_preview = q['question'][:50] + '...' if len(q['question']) > 50 else q['question']
        lines.append(
            f"• <code>{q['id']}</code>: {question_preview}\n"
            f"  👤 {q['username']} | ⏰ {q['created_at'][:16]}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


@authorized_only
async def tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tasks command.
    Show Background Agent tasks for current user.
    """
    if not is_background_agent_enabled():
        await update.message.reply_text(
            "⚪ Background Agent 未啟用\n\n"
            "請設定:\n"
            "1. CURSOR_API_KEY=你的API金鑰\n"
            "2. BACKGROUND_AGENT_ENABLED=true\n\n"
            "API Key 從 cursor.com/dashboard 取得"
        )
        return

    user_id = update.effective_user.id
    tracker = get_task_tracker()
    
    # Get all tasks for this user
    all_tasks = tracker.get_user_tasks(user_id)
    
    if not all_tasks:
        await update.message.reply_text(
            "📋 <b>沒有任務記錄</b>\n\n"
            "使用 /ask <問題> 建立新任務",
            parse_mode="HTML",
        )
        return

    # Separate by status
    running = [t for t in all_tasks if t.get("status") in ["running", "pending", "created"]]
    completed = [t for t in all_tasks if t.get("status") == "completed"][:5]
    failed = [t for t in all_tasks if t.get("status") in ["failed", "error", "timeout"]][:3]

    lines = ["<b>📋 我的任務</b>\n"]

    if running:
        lines.append(f"\n<b>🔄 執行中 ({len(running)})</b>")
        for t in running[:5]:
            prompt_preview = t['prompt'][:40] + '...' if len(t['prompt']) > 40 else t['prompt']
            lines.append(
                f"• <code>{t['composer_id'][:8]}</code>\n"
                f"  {prompt_preview}"
            )

    if completed:
        lines.append(f"\n<b>✅ 已完成 ({len(completed)})</b>")
        for t in completed:
            prompt_preview = t['prompt'][:40] + '...' if len(t['prompt']) > 40 else t['prompt']
            lines.append(
                f"• <code>{t['composer_id'][:8]}</code>: {prompt_preview}"
            )

    if failed:
        lines.append(f"\n<b>❌ 失敗 ({len(failed)})</b>")
        for t in failed:
            prompt_preview = t['prompt'][:40] + '...' if len(t['prompt']) > 40 else t['prompt']
            lines.append(
                f"• <code>{t['composer_id'][:8]}</code>: {prompt_preview}"
            )

    lines.append("\n💡 使用 /result <ID> 查看詳細結果")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


@authorized_only
async def result_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /result command.
    Show result of a specific Background Agent task.
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 請提供任務 ID!\n\n"
            "用法: /result <任務ID>\n"
            "例: /result abc12345\n\n"
            "使用 /tasks 查看任務列表"
        )
        return

    task_id_prefix = context.args[0]
    tracker = get_task_tracker()
    
    # Find task by ID prefix
    user_id = update.effective_user.id
    user_tasks = tracker.get_user_tasks(user_id)
    
    matching_task = None
    for t in user_tasks:
        if t['composer_id'].startswith(task_id_prefix):
            matching_task = t
            break

    if not matching_task:
        await update.message.reply_text(
            f"❌ 找不到任務: {task_id_prefix}\n\n"
            "使用 /tasks 查看任務列表"
        )
        return

    # Get fresh status from API if running
    if matching_task.get("status") in ["running", "pending", "created"]:
        try:
            bg_agent = get_background_agent(settings.cursor_api_key)
            result = await bg_agent.get_task_details(matching_task['composer_id'])
            if result.get("success"):
                matching_task["status"] = result.get("status", matching_task["status"])
                if result.get("output"):
                    matching_task["output"] = result.get("output")
        except Exception:
            pass

    # Format output
    status_emoji = {
        "running": "🔄",
        "pending": "⏳",
        "created": "🆕",
        "completed": "✅",
        "failed": "❌",
        "error": "❌",
        "timeout": "⏰",
    }.get(matching_task.get("status", ""), "❓")

    output = matching_task.get("output", "（尚無輸出）")
    if len(output) > 3500:
        output = output[:3500] + "\n\n... (內容過長已截斷)"

    prompt = matching_task.get("prompt", "")
    if len(prompt) > 200:
        prompt = prompt[:200] + "..."

    await update.message.reply_text(
        f"<b>📋 任務詳情</b>\n\n"
        f"🆔 ID: <code>{matching_task['composer_id']}</code>\n"
        f"{status_emoji} 狀態: {matching_task.get('status', 'unknown')}\n"
        f"⏰ 建立: {matching_task.get('created_at', '')[:16]}\n\n"
        f"<b>❓ 問題:</b>\n{prompt}\n\n"
        f"<b>📝 結果:</b>\n{output}",
        parse_mode="HTML",
    )


# Store user's current repo selection
_user_repos: dict[int, str] = {}


def get_user_repo(user_id: int) -> str:
    """Get user's current repo, fallback to settings."""
    return _user_repos.get(user_id, settings.cursor_github_repo)


def set_user_repo(user_id: int, repo_url: str) -> None:
    """Set user's current repo."""
    _user_repos[user_id] = repo_url


@authorized_only
async def repo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /repo command.
    Set or show current GitHub repository.
    """
    user_id = update.effective_user.id

    if not context.args:
        # Show current repo
        current_repo = get_user_repo(user_id)
        if current_repo:
            repo_name = current_repo.split("/")[-1]
            owner = current_repo.split("/")[-2] if "/" in current_repo else ""
            await update.message.reply_text(
                f"📁 <b>目前倉庫</b>\n\n"
                f"• 名稱: <code>{repo_name}</code>\n"
                f"• 擁有者: <code>{owner}</code>\n"
                f"• URL: {current_repo}\n\n"
                f"<b>切換倉庫:</b>\n"
                f"<code>/repo owner/repo-name</code>\n"
                f"<code>/repo https://github.com/owner/repo</code>",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                "⚠️ <b>未設定倉庫</b>\n\n"
                "請使用以下格式設定:\n"
                "<code>/repo owner/repo-name</code>\n"
                "<code>/repo https://github.com/owner/repo</code>",
                parse_mode="HTML",
            )
        return

    # Set new repo
    repo_input = " ".join(context.args)
    
    # Normalize repo URL
    if repo_input.startswith("https://github.com/"):
        repo_url = repo_input.rstrip("/")
    elif "/" in repo_input and not repo_input.startswith("http"):
        # Format: owner/repo
        repo_url = f"https://github.com/{repo_input}"
    else:
        await update.message.reply_text(
            "❌ <b>格式錯誤</b>\n\n"
            "請使用以下格式:\n"
            "<code>/repo owner/repo-name</code>\n"
            "<code>/repo https://github.com/owner/repo</code>",
            parse_mode="HTML",
        )
        return

    # Validate format
    parts = repo_url.replace("https://github.com/", "").split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        await update.message.reply_text(
            "❌ <b>無效的倉庫格式</b>\n\n"
            "請確保格式為: owner/repo-name",
            parse_mode="HTML",
        )
        return

    owner = parts[0]
    repo_name = parts[1]
    set_user_repo(user_id, repo_url)

    await update.message.reply_text(
        f"✅ <b>已切換倉庫</b>\n\n"
        f"📁 {owner}/<b>{repo_name}</b>\n"
        f"🔗 {repo_url}\n\n"
        f"現在可以使用 /ask 發送任務到此倉庫",
        parse_mode="HTML",
    )


@authorized_only
async def repos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /repos command.
    Show recently used repositories.
    """
    user_id = update.effective_user.id
    current_repo = get_user_repo(user_id)
    default_repo = settings.cursor_github_repo

    lines = ["<b>📁 我的倉庫</b>\n"]

    if current_repo:
        repo_name = current_repo.split("/")[-1]
        lines.append(f"<b>目前:</b> {repo_name} ✓")
        lines.append(f"  └ {current_repo}")

    if default_repo and default_repo != current_repo:
        repo_name = default_repo.split("/")[-1]
        lines.append(f"\n<b>預設:</b> {repo_name}")
        lines.append(f"  └ {default_repo}")

    lines.append("\n<b>切換倉庫:</b>")
    lines.append("<code>/repo owner/repo-name</code>")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


@authorized_only
async def cancel_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /cancel_task command.
    Cancel a running Background Agent task.
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 請提供任務 ID!\n\n"
            "用法: /cancel_task <任務ID>"
        )
        return

    if not is_background_agent_enabled():
        await update.message.reply_text("⚪ Background Agent 未啟用")
        return

    task_id_prefix = context.args[0]
    tracker = get_task_tracker()
    user_id = update.effective_user.id
    user_tasks = tracker.get_user_tasks(user_id)

    matching_task = None
    for t in user_tasks:
        if t['composer_id'].startswith(task_id_prefix):
            matching_task = t
            break

    if not matching_task:
        await update.message.reply_text(f"❌ 找不到任務: {task_id_prefix}")
        return

    try:
        bg_agent = get_background_agent(settings.cursor_api_key)
        result = await bg_agent.cancel_task(matching_task['composer_id'])

        if result.get("success"):
            tracker.update_task(matching_task['composer_id'], "cancelled")
            await update.message.reply_text(
                f"✅ 任務已取消: <code>{matching_task['composer_id'][:8]}</code>",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                f"❌ 取消失敗: {result.get('message', 'Unknown')}"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ 錯誤: {str(e)[:200]}")


@authorized_only
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle regular text messages.
    Send to Background Agent or Cursor IDE as a question.
    """
    message_text = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat_id = update.effective_chat.id
    logger.info(f"User {user_id} message: {message_text[:50]}...")

    # Use Background Agent if enabled
    if is_background_agent_enabled():
        await _handle_background_agent_ask(update, message_text, user_id, username, chat_id)
    else:
        # Fallback to MCP mode
        from ..cursor.mcp_server import add_question
        import uuid
        
        question_id = str(uuid.uuid4())[:8]
        add_question(question_id, user_id, username, message_text)

        await update.message.reply_text(
            f"📝 已發送到 Cursor IDE\n\n"
            f"ID: <code>{question_id}</code>\n"
            f"使用 /check 檢查回覆",
            parse_mode="HTML",
        )


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
    app.add_handler(CommandHandler("check", check_handler))
    app.add_handler(CommandHandler("pending", pending_handler))
    app.add_handler(CommandHandler("code", code_handler))
    app.add_handler(CommandHandler("file", file_handler))
    app.add_handler(CommandHandler("search", search_handler))
    app.add_handler(CommandHandler("project", project_handler))

    # Background Agent handlers
    app.add_handler(CommandHandler("tasks", tasks_handler))
    app.add_handler(CommandHandler("result", result_handler))
    app.add_handler(CommandHandler("cancel_task", cancel_task_handler))
    app.add_handler(CommandHandler("repo", repo_handler))
    app.add_handler(CommandHandler("repos", repos_handler))

    # Message handler for regular text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Error handler
    app.add_error_handler(error_handler)

    # Setup extended handlers (file editing, terminal, task management)
    from .handlers_extended import setup_extended_handlers
    setup_extended_handlers(app)

    # Log Background Agent status
    if is_background_agent_enabled():
        logger.info("Background Agent integration enabled")
    else:
        logger.info("Background Agent disabled (MCP mode)")

    logger.info("Bot handlers configured successfully")


__all__ = ["setup_handlers"]
