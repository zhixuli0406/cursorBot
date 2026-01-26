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
    from .keyboards import get_welcome_keyboard

    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")

    # Check status
    if is_background_agent_enabled():
        status = "🟢 Background Agent 已連線"
    else:
        status = "⚠️ 請設定 API Key"

    welcome_text = f"""
👋 <b>歡迎使用 CursorBot!</b>

您好, {user.first_name}!

CursorBot 讓你透過 Telegram 遠端控制 Cursor AI Agent，完全無需開啟 IDE。

<b>狀態:</b> {status}

<b>🚀 快速開始:</b>
1. 使用 /repo 選擇 GitHub 倉庫
2. 直接發送問題或指令
3. AI Agent 會自動執行任務

<b>✨ 主要功能:</b>
• <b>AI 任務</b> - 發送問題讓 AI 自動編程
• <b>語音/圖片</b> - 支援語音轉錄和圖片附件
• <b>記憶系統</b> - /memory 儲存常用資訊
• <b>技能系統</b> - /skills 查看可用技能
• <b>排程任務</b> - /remind 設定提醒

<b>📋 常用指令:</b>
/help - 完整指令說明
/status - 系統狀態
/repo - 設定倉庫
/tasks - 我的任務

使用下方按鈕開始，或直接發送訊息！
"""
    await update.message.reply_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_welcome_keyboard(),
    )


@authorized_only
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command.
    Display detailed help information.
    """
    # Check if Background Agent is configured
    if is_background_agent_enabled():
        status_info = "🟢 Background Agent 已啟用"
    else:
        status_info = "⚠️ 請設定 CURSOR_API_KEY 和 BACKGROUND_AGENT_ENABLED"

    help_text = f"""
<b>📖 CursorBot 指令說明</b>

<b>{status_info}</b>

<b>🔹 基礎指令</b>
• /start - 啟動並顯示歡迎訊息
• /help - 顯示此說明
• /status - 查看系統狀態
• /stats - 使用統計
• /settings - 用戶設定

<b>🔹 AI 對話</b>
• /ask &lt;問題&gt; - 發送問題給 AI Agent
• /repo &lt;owner/repo&gt; - 切換 GitHub 倉庫
• /repos - 查看帳號中的倉庫
• /tasks - 查看我的任務列表
• /result &lt;ID&gt; - 查看任務結果
• /cancel_task &lt;ID&gt; - 取消執行中的任務

<b>🔹 記憶系統</b>
• /memory - 查看我的記憶
• /memory add &lt;key&gt; &lt;value&gt; - 新增記憶
• /memory get &lt;key&gt; - 取得記憶
• /memory del &lt;key&gt; - 刪除記憶
• /memory search &lt;query&gt; - 搜尋記憶
• /clear - 清除對話上下文

<b>🔹 技能系統</b>
• /skills - 查看可用技能
• /translate &lt;lang&gt; &lt;text&gt; - 翻譯文字
• /calc &lt;expression&gt; - 計算表達式
• /remind &lt;time&gt; &lt;msg&gt; - 設定提醒
• /schedule - 查看排程任務

<b>🔹 檔案操作</b>
• /file read &lt;路徑&gt; - 讀取檔案
• /file list &lt;目錄&gt; - 列出檔案
• /write &lt;路徑&gt; - 建立檔案
• /edit &lt;檔案&gt; - 編輯檔案
• /delete &lt;路徑&gt; - 刪除檔案

<b>🔹 終端機操作</b>
• /run &lt;命令&gt; - 執行命令
• /run_bg &lt;命令&gt; - 背景執行
• /jobs - 查看執行中命令
• /kill &lt;ID&gt; - 停止命令

<b>🔹 工作區管理</b>
• /workspace - 顯示工作區
• /cd &lt;名稱&gt; - 切換工作區
• /search &lt;關鍵字&gt; - 搜尋程式碼

<b>💡 提示:</b>
• 直接發送訊息即可與 AI 對話
• 發送語音會自動轉錄
• 發送圖片會加入任務
"""
    await update.message.reply_text(help_text, parse_mode="HTML")


@authorized_only
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /status command.
    Display system status.
    """
    # Get workspace info
    agent = get_cursor_agent()
    ws_info = await agent.get_workspace_info()

    # Check Background Agent status
    if is_background_agent_enabled():
        bg_status = "🟢 Background Agent 已啟用"
        tracker = get_task_tracker()
        running_tasks = tracker.get_pending_tasks()
        bg_tasks_info = f"🔄 <b>執行中任務:</b> {len(running_tasks)}"
        
        # Show current repo
        user_id = update.effective_user.id
        current_repo = get_user_repo(user_id)
        if current_repo:
            repo_name = current_repo.split("/")[-1]
            bg_status += f"\n📁 目前倉庫: {repo_name}"
        else:
            bg_status += "\n⚠️ 未設定 GitHub 倉庫 (使用 /repo 設定)"
        
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
        bg_status = "⚪ Background Agent 未啟用\n\n請設定:\n• CURSOR_API_KEY\n• BACKGROUND_AGENT_ENABLED=true"
        bg_tasks_info = ""

    message = f"""
<b>📊 系統狀態</b>

<b>🤖 Background Agent</b>
{bg_status}
{bg_tasks_info}

<b>📂 工作區</b>
• 名稱: {ws_info['name']}
• 檔案數: {ws_info['total_files']}
• 路徑: <code>{ws_info['path']}</code>

<b>💡 使用方式</b>
• /repo 設定 GitHub 倉庫
• /ask 發送問題給 AI
• /tasks 查看任務狀態
"""
    await update.message.reply_text(message, parse_mode="HTML")


@authorized_only
async def ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /ask command.
    Send a question to Cursor Background Agent.
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 請提供問題!\n\n"
            "用法: /ask <問題>\n"
            "例: /ask 如何實作快速排序?"
        )
        return

    # Check if Background Agent is enabled
    if not is_background_agent_enabled():
        await update.message.reply_text(
            "⚠️ <b>Background Agent 未啟用</b>\n\n"
            "請在 .env 中設定:\n"
            "<code>CURSOR_API_KEY=你的API金鑰</code>\n"
            "<code>BACKGROUND_AGENT_ENABLED=true</code>\n\n"
            "API Key 從 cursor.com/dashboard 取得",
            parse_mode="HTML",
        )
        return

    question = " ".join(context.args)
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat_id = update.effective_chat.id
    logger.info(f"User {user_id} asking: {question}")

    await _handle_background_agent_ask(update, question, user_id, username, chat_id)


async def _handle_background_agent_ask(
    update: Update,
    question: str,
    user_id: int,
    username: str,
    chat_id: int,
) -> None:
    """Handle ask command using Background Agent."""
    from .keyboards import get_repo_keyboard
    from .media_handlers import get_cached_media, clear_cache, get_cache_count

    # Get user's current repo
    repo_url = get_user_repo(user_id)

    # Check if GitHub repo is configured
    if not repo_url:
        await update.message.reply_text(
            "⚠️ <b>未設定 GitHub 倉庫</b>\n\n"
            "Background Agent 需要指定 GitHub 倉庫才能運作。\n\n"
            "<b>設定方式:</b>\n"
            "1. 使用 <code>/repo owner/repo-name</code> 指定倉庫\n"
            "2. 或點擊下方按鈕選擇倉庫\n\n"
            "<b>範例:</b>\n"
            "<code>/repo lizhixu/cursorBot</code>",
            parse_mode="HTML",
        )
        return

    repo_name = repo_url.split("/")[-1]

    # Check for cached media (images)
    cached_media = get_cached_media(user_id)
    media_count = len(cached_media)
    media_info = f"\n📎 附件: {media_count} 張圖片" if media_count > 0 else ""

    # Add custom prompt if configured
    if settings.custom_prompt:
        question = f"{settings.custom_prompt}\n\n{question}"

    # Send initial response
    status_msg = await update.message.reply_text(
        f"🚀 <b>正在啟動 Background Agent...</b>\n\n"
        f"📁 倉庫: <code>{repo_name}</code>\n"
        f"❓ 問題: {question[:80]}{'...' if len(question) > 80 else ''}{media_info}",
        parse_mode="HTML",
    )

    # Clear media cache after task creation
    if media_count > 0:
        clear_cache(user_id)

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

        from .keyboards import get_task_created_keyboard

        await status_msg.edit_text(
            f"✅ <b>任務已建立</b>\n\n"
            f"🆔 任務 ID: <code>{composer_id}</code>\n"
            f"📁 倉庫: <code>{repo_name}</code>\n"
            f"❓ 問題: {question[:60]}{'...' if len(question) > 60 else ''}\n\n"
            f"⏳ 正在執行中...",
            parse_mode="HTML",
            reply_markup=get_task_created_keyboard(composer_id),
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

        from .keyboards import get_task_keyboard

        if result.get("success"):
            output = result.get("output", "（無輸出）")
            if len(output) > 2500:
                output = output[:2500] + "\n\n... (內容過長已截斷)"
            output = _escape_html(output)

            await update.effective_chat.send_message(
                f"✅ <b>任務完成</b>\n\n"
                f"🆔 <code>{_escape_html(composer_id[:8])}</code>\n\n"
                f"📝 <b>結果:</b>\n{output}",
                parse_mode="HTML",
                reply_markup=get_task_keyboard(composer_id, "completed"),
            )
        else:
            status = _escape_html(result.get('status', 'unknown'))
            message = _escape_html(result.get('message', 'Unknown'))
            await update.effective_chat.send_message(
                f"❌ <b>任務失敗</b>\n\n"
                f"🆔 <code>{_escape_html(composer_id[:8])}</code>\n"
                f"狀態: {status}\n"
                f"原因: {message}",
                parse_mode="HTML",
                reply_markup=get_task_keyboard(composer_id, "failed"),
            )

    except Exception as e:
        logger.error(f"Poll error: {e}")


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


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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
            "使用 /ask 問題 建立新任務",
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
            prompt_text = t.get('prompt', '')[:40]
            prompt_preview = _escape_html(prompt_text) + ('...' if len(t.get('prompt', '')) > 40 else '')
            task_id = _escape_html(t.get('composer_id', '')[:8])
            lines.append(
                f"• <code>{task_id}</code>\n"
                f"  {prompt_preview}"
            )

    if completed:
        lines.append(f"\n<b>✅ 已完成 ({len(completed)})</b>")
        for t in completed:
            prompt_text = t.get('prompt', '')[:40]
            prompt_preview = _escape_html(prompt_text) + ('...' if len(t.get('prompt', '')) > 40 else '')
            task_id = _escape_html(t.get('composer_id', '')[:8])
            lines.append(
                f"• <code>{task_id}</code>: {prompt_preview}"
            )

    if failed:
        lines.append(f"\n<b>❌ 失敗 ({len(failed)})</b>")
        for t in failed:
            prompt_text = t.get('prompt', '')[:40]
            prompt_preview = _escape_html(prompt_text) + ('...' if len(t.get('prompt', '')) > 40 else '')
            task_id = _escape_html(t.get('composer_id', '')[:8])
            lines.append(
                f"• <code>{task_id}</code>: {prompt_preview}"
            )

    lines.append("\n💡 使用 /result ID 查看詳細結果")

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

    # Escape HTML special characters
    prompt = _escape_html(prompt)
    output = _escape_html(output)
    task_id = _escape_html(matching_task.get('composer_id', ''))
    status = _escape_html(matching_task.get('status', 'unknown'))
    created_at = _escape_html(matching_task.get('created_at', '')[:16])

    await update.message.reply_text(
        f"<b>📋 任務詳情</b>\n\n"
        f"🆔 ID: <code>{task_id}</code>\n"
        f"{status_emoji} 狀態: {status}\n"
        f"⏰ 建立: {created_at}\n\n"
        f"<b>❓ 問題:</b>\n{prompt}\n\n"
        f"<b>📝 結果:</b>\n{output}",
        parse_mode="HTML",
    )


# Import user repo functions from callbacks module (shared state)
from .callbacks import get_user_repo, set_user_repo


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
    Show all repositories from Cursor account and recently used ones.
    """
    user_id = update.effective_user.id
    current_repo = get_user_repo(user_id)
    default_repo = settings.cursor_github_repo

    lines = ["<b>📁 我的倉庫</b>\n"]

    # Show current and default repos
    if current_repo:
        repo_name = current_repo.split("/")[-1]
        lines.append(f"<b>目前:</b> {repo_name} ✓")
        lines.append(f"  └ {current_repo}")

    if default_repo and default_repo != current_repo:
        repo_name = default_repo.split("/")[-1]
        lines.append(f"\n<b>預設:</b> {repo_name}")
        lines.append(f"  └ {default_repo}")

    # Fetch repositories from Cursor API if Background Agent is enabled
    if is_background_agent_enabled():
        await update.message.chat.send_action("typing")
        
        try:
            bg_agent = get_background_agent(settings.cursor_api_key)
            result = await bg_agent.list_repositories()
            
            if result.get("success") and result.get("repositories"):
                repos = result.get("repositories", [])
                lines.append(f"\n<b>📦 帳號倉庫 ({len(repos)}):</b>")
                
                for repo in repos[:15]:  # Limit to 15 repos
                    name = repo.get("name", "")
                    owner = repo.get("owner", "")
                    full_name = repo.get("full_name", f"{owner}/{name}")
                    description = repo.get("description", "")
                    private = repo.get("private", False)
                    
                    # Mark if this is the current repo
                    is_current = current_repo and full_name in current_repo
                    current_mark = " ✓" if is_current else ""
                    private_mark = "🔒" if private else "📂"
                    
                    lines.append(f"\n{private_mark} <b>{name}</b>{current_mark}")
                    lines.append(f"  └ <code>{full_name}</code>")
                    if description:
                        desc_preview = description[:50] + "..." if len(description) > 50 else description
                        lines.append(f"  └ {desc_preview}")
                
                if len(repos) > 15:
                    lines.append(f"\n... 還有 {len(repos) - 15} 個倉庫")
            elif result.get("message"):
                lines.append(f"\n⚠️ 無法取得帳號倉庫: {result.get('message', '')[:100]}")
            else:
                lines.append("\n📭 帳號中沒有找到任何倉庫")
                
        except Exception as e:
            logger.error(f"Error fetching repositories: {e}")
            lines.append(f"\n⚠️ 取得倉庫時發生錯誤")
    else:
        lines.append("\n💡 啟用 Background Agent 以查看帳號中的所有倉庫")

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
    Send to Background Agent as a question.
    """
    message_text = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat_id = update.effective_chat.id
    logger.info(f"User {user_id} message: {message_text[:50]}...")

    # Check if Background Agent is enabled
    if is_background_agent_enabled():
        await _handle_background_agent_ask(update, message_text, user_id, username, chat_id)
    else:
        await update.message.reply_text(
            "⚠️ <b>Background Agent 未啟用</b>\n\n"
            "請設定 CURSOR_API_KEY 和 BACKGROUND_AGENT_ENABLED=true\n\n"
            "或使用 /help 查看其他可用指令",
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
    # Basic command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("status", status_handler))

    # Background Agent handlers
    app.add_handler(CommandHandler("ask", ask_handler))
    app.add_handler(CommandHandler("repo", repo_handler))
    app.add_handler(CommandHandler("repos", repos_handler))
    app.add_handler(CommandHandler("tasks", tasks_handler))
    app.add_handler(CommandHandler("result", result_handler))
    app.add_handler(CommandHandler("cancel_task", cancel_task_handler))

    # Workspace handlers
    app.add_handler(CommandHandler("file", file_handler))
    app.add_handler(CommandHandler("search", search_handler))
    app.add_handler(CommandHandler("project", project_handler))

    # Setup callback handlers for inline keyboards
    from .callbacks import setup_callback_handlers
    setup_callback_handlers(app)

    # Setup media handlers (voice, photo, document)
    from .media_handlers import setup_media_handlers
    setup_media_handlers(app)

    # Setup core feature handlers (memory, skills, scheduler, etc.)
    from .core_handlers import setup_core_handlers
    setup_core_handlers(app)

    # Message handler for regular text (should be added last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Error handler
    app.add_error_handler(error_handler)

    # Setup extended handlers (file editing, terminal, task management)
    from .handlers_extended import setup_extended_handlers
    setup_extended_handlers(app)

    # Log Background Agent status
    if is_background_agent_enabled():
        logger.info("Background Agent enabled")
    else:
        logger.warning("Background Agent NOT configured - set CURSOR_API_KEY")

    logger.info("Bot handlers configured successfully")


__all__ = ["setup_handlers"]
