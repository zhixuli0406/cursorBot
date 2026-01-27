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

# User chat mode settings (agent vs cursor)
# Key: user_id, Value: "agent" or "cursor"
_user_chat_modes: dict[int, str] = {}

# Default chat mode
DEFAULT_CHAT_MODE = "cursor"  # "agent" or "cursor"


def get_user_chat_mode(user_id: int) -> str:
    """Get user's chat mode preference."""
    return _user_chat_modes.get(user_id, DEFAULT_CHAT_MODE)


def set_user_chat_mode(user_id: int, mode: str) -> None:
    """Set user's chat mode preference."""
    if mode in ("agent", "cursor"):
        _user_chat_modes[user_id] = mode


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
    status_items = []
    if is_background_agent_enabled():
        status_items.append("🟢 Background Agent")
    else:
        status_items.append("⚪ Background Agent (未設定)")

    # Check AI model status
    try:
        from ..core.llm_providers import get_llm_manager
        manager = get_llm_manager()
        available = manager.list_available_providers()
        if available:
            current = manager.get_user_model(str(user.id))
            model_name = f"{current[0]}/{current[1]}" if current else "未設定"
            status_items.append(f"🤖 {model_name}")
        else:
            status_items.append("⚪ AI 模型 (未設定)")
    except Exception:
        status_items.append("⚪ AI 模型")

    # Check Discord status
    if settings.discord_enabled and settings.discord_bot_token:
        status_items.append("🟢 Discord")
    
    status_text = " | ".join(status_items) if status_items else "⚠️ 請設定 API Key"

    welcome_text = f"""
👋 <b>歡迎使用 CursorBot!</b>

您好, {user.first_name}!

CursorBot 是一個多平台 AI 編程助手，支援 <b>Telegram</b> 和 <b>Discord</b>，讓你遠端控制 Cursor AI Agent，完全無需開啟 IDE。

<b>📡 狀態:</b>
{status_text}

<b>🚀 快速開始:</b>
1️⃣ 使用 /model 選擇 AI 模型
2️⃣ 使用 /repo 選擇 GitHub 倉庫
3️⃣ 直接發送問題或使用 /agent 指令

<b>✨ v0.3 新功能:</b>
• 📱 Line - 亞洲市場訊息平台
• 🧠 GLM 智譜 - 中國 ChatGLM AI
• 🖥️ Menu Bar - macOS 選單列應用
• 💬 iMessage - macOS 訊息整合
• 🌐 Chrome Extension - 瀏覽器整合
• 🌙 Moonshot AI - 中國月之暗面

<b>✨ 核心功能:</b>
• <b>多模型 AI</b> - OpenAI/Claude/Gemini/GLM
• <b>Agent Loop</b> - 自主任務執行與 Skills
• <b>AI 編程</b> - Cursor Background Agent
• <b>多媒體支援</b> - 語音轉錄、圖片附件
• <b>多平台</b> - TG/DC/WhatsApp/Teams/Line
• <b>記憶系統</b> - 儲存常用資訊和偏好

<b>📋 常用指令:</b>
/help - 完整指令說明
/model - 切換 AI 模型
/agent - AI Agent 對話
/skills - 可用技能
/repo - 設定 GitHub 倉庫
/ask - Cursor Background Agent

點擊下方按鈕或直接發送訊息開始！
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
    # Check status
    status_parts = []
    if is_background_agent_enabled():
        status_parts.append("🟢 Background Agent")
    else:
        status_parts.append("⚪ Background Agent")
    
    # Check AI model status
    try:
        from ..core.llm_providers import get_llm_manager
        manager = get_llm_manager()
        available = manager.list_available_providers()
        if available:
            status_parts.append(f"🤖 AI ({len(available)} 提供者)")
    except Exception:
        pass
    
    if settings.discord_enabled:
        status_parts.append("🟢 Discord")
    
    status_info = " | ".join(status_parts)

    help_text = f"""
<b>📖 CursorBot 完整指令說明</b>

<b>狀態:</b> {status_info}

━━━━━━━━━━━━━━━━━━━━━━
<b>🔹 基礎指令</b>
━━━━━━━━━━━━━━━━━━━━━━
/start - 啟動並顯示歡迎訊息
/help - 顯示此說明
/status - 查看系統狀態
/stats - 使用統計
/settings - 用戶設定

━━━━━━━━━━━━━━━━━━━━━━
<b>🤖 AI 模型管理</b>
━━━━━━━━━━━━━━━━━━━━━━
/model - 查看目前 AI 模型
/model list - 列出所有可用模型
/model set &lt;provider&gt; [model] - 切換模型
/model reset - 恢復預設模型

<b>支援的提供者:</b>
• OpenAI (GPT-4o, GPT-4o-mini)
• Anthropic (Claude 3.5 + Thinking Mode)
• Google (Gemini 2.0 Flash)
• OpenRouter (多種模型)
• Ollama (本地模型)

━━━━━━━━━━━━━━━━━━━━━━
<b>🤖 Agent Loop &amp; Skills</b>
━━━━━━━━━━━━━━━━━━━━━━
/agent &lt;任務&gt; - 啟動 AI Agent 執行任務
/skills - 查看所有可用技能
/skills agent - 查看 Agent 專用技能

<b>內建 Agent Skills:</b>
• 網路搜尋、程式碼分析
• 檔案讀取、指令執行
• UI/UX 設計系統生成

━━━━━━━━━━━━━━━━━━━━━━
<b>📋 Cursor Background Agent</b>
━━━━━━━━━━━━━━━━━━━━━━
/ask &lt;問題&gt; - 發送問題給 Cursor Agent
/repo &lt;owner/repo&gt; - 切換 GitHub 倉庫
/repos - 查看帳號中的倉庫
/tasks - 查看我的任務列表
/result &lt;ID&gt; - 查看任務結果
/cancel_task &lt;ID&gt; - 取消執行中的任務

<i>💡 也可以直接發送訊息、語音或圖片</i>

━━━━━━━━━━━━━━━━━━━━━━
<b>🧠 記憶系統</b>
━━━━━━━━━━━━━━━━━━━━━━
/memory - 查看我的記憶
/memory add &lt;key&gt; &lt;value&gt; - 新增記憶
/memory get &lt;key&gt; - 取得記憶
/memory del &lt;key&gt; - 刪除記憶
/clear - 清除對話上下文

━━━━━━━━━━━━━━━━━━━━━━
<b>🎯 指令技能</b>
━━━━━━━━━━━━━━━━━━━━━━
/translate &lt;lang&gt; &lt;text&gt; - 翻譯文字
/calc &lt;expression&gt; - 計算表達式
/remind &lt;time&gt; &lt;msg&gt; - 設定提醒
/schedule - 查看排程任務

━━━━━━━━━━━━━━━━━━━━━━
<b>📁 檔案 &amp; 終端機</b>
━━━━━━━━━━━━━━━━━━━━━━
/file read &lt;路徑&gt; - 讀取檔案
/file list &lt;目錄&gt; - 列出檔案
/run &lt;命令&gt; - 執行命令
/run_bg &lt;命令&gt; - 背景執行
/jobs - 查看執行中命令

━━━━━━━━━━━━━━━━━━━━━━
<b>📂 工作區管理</b>
━━━━━━━━━━━━━━━━━━━━━━
/workspace - 顯示工作區
/cd &lt;名稱&gt; - 切換工作區
/search &lt;關鍵字&gt; - 搜尋程式碼

━━━━━━━━━━━━━━━━━━━━━━
<b>🌐 Browser 工具</b>
━━━━━━━━━━━━━━━━━━━━━━
/browser navigate &lt;URL&gt; - 開啟網頁
/browser screenshot - 網頁截圖
/browser text &lt;selector&gt; - 取得文字

━━━━━━━━━━━━━━━━━━━━━━
<b>🌐 多平台支援</b>
━━━━━━━━━━━━━━━━━━━━━━
• <b>Telegram</b> - 你正在使用
• <b>Discord</b> - 相同功能，斜線指令
• <b>WhatsApp</b> - 透過 whatsapp-web.js
• <b>MS Teams</b> - Bot Framework 整合
• <b>Slack</b> - 企業工作區整合

━━━━━━━━━━━━━━━━━━━━━━
<b>✨ v0.3 新功能指令</b>
━━━━━━━━━━━━━━━━━━━━━━
/doctor - 系統診斷
/sessions - 會話管理
/tts &lt;文字&gt; - 文字轉語音
/lock - 閘道鎖定控制
/presence - 在線狀態
/gateway - 統一閘道
/agents - 代理管理
/whatsapp - WhatsApp 狀態
/teams - MS Teams 狀態
/tailscale - Tailscale VPN 狀態
/imessage - iMessage 狀態 (macOS)
/line - Line Bot 狀態
/menubar - macOS Menu Bar 說明
/control - 系統控制面板
/mode - 切換對話模式 (Agent/Cursor)

━━━━━━━━━━━━━━━━━━━━━━
<b>🛠️ v0.3 功能特色</b>
━━━━━━━━━━━━━━━━━━━━━━
• <b>Line</b> - 亞洲市場訊息平台
• <b>GLM (智譜)</b> - 中國 AI ChatGLM
• <b>Menu Bar</b> - macOS 選單列應用
• <b>iMessage</b> - macOS 訊息整合
• <b>Chrome Extension</b> - 瀏覽器擴展
• <b>Moonshot AI</b> - 中國月之暗面

━━━━━━━━━━━━━━━━━━━━━━
<b>💡 使用提示</b>
━━━━━━━━━━━━━━━━━━━━━━
• /model set glm 使用智譜 AI
• /line setup 查看 Line 設定
• /menubar 查看 Menu Bar 說明
• Chrome Extension 安裝見文件
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
    """
    Poll for task completion and send result.
    
    Continuously polls until the task is completed or failed.
    Sends periodic status updates to the user.
    """
    try:
        bg_agent = get_background_agent(settings.cursor_api_key)
        tracker = get_task_tracker()
        last_status_msg_update = asyncio.get_event_loop().time()
        
        # Status update callback - updates the status message periodically
        async def status_callback(
            task_id: str, 
            status: str, 
            result: dict, 
            elapsed: float,
            periodic: bool = False
        ):
            nonlocal last_status_msg_update
            
            current_time = asyncio.get_event_loop().time()
            
            # Update status message every 30 seconds or on status change
            if not periodic and (current_time - last_status_msg_update) < 30:
                return
            
            try:
                # Format elapsed time
                if elapsed < 60:
                    time_str = f"{elapsed:.0f}秒"
                elif elapsed < 3600:
                    minutes = int(elapsed // 60)
                    seconds = int(elapsed % 60)
                    time_str = f"{minutes}分{seconds}秒"
                else:
                    hours = int(elapsed // 3600)
                    minutes = int((elapsed % 3600) // 60)
                    time_str = f"{hours}小時{minutes}分"
                
                status_emoji = {
                    "running": "🔄",
                    "pending": "⏳",
                    "processing": "⚙️",
                    "queued": "📋",
                }.get(status, "🔄")
                
                await status_msg.edit_text(
                    f"{status_emoji} <b>任務執行中...</b>\n\n"
                    f"🆔 <code>{_escape_html(task_id[:8])}</code>\n"
                    f"📊 狀態: {_escape_html(status)}\n"
                    f"⏱️ 已執行: {time_str}\n\n"
                    f"<i>任務仍在執行，請耐心等候...</i>",
                    parse_mode="HTML",
                )
                last_status_msg_update = current_time
            except Exception as e:
                # Message might have been deleted, ignore
                logger.debug(f"Could not update status message: {e}")
        
        # Poll with no timeout (0 = infinite), continuous polling
        result = await bg_agent.wait_for_completion(
            composer_id,
            timeout=0,  # No timeout - poll indefinitely
            poll_interval=settings.background_agent_poll_interval,
            callback=status_callback,
            status_update_interval=60,  # Send callback every 60 seconds
        )

        # Update tracker
        tracker.update_task(
            composer_id,
            result.get("status", "unknown"),
            result.get("output", ""),
        )

        from .keyboards import get_task_keyboard
        
        # Format elapsed time for final message
        elapsed = result.get("elapsed", 0)
        if elapsed < 60:
            time_str = f"{elapsed:.0f}秒"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            time_str = f"{minutes}分{seconds}秒"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            time_str = f"{hours}小時{minutes}分"

        if result.get("success"):
            output = result.get("output", "（無輸出）")
            if len(output) > 2500:
                output = output[:2500] + "\n\n... (內容過長已截斷)"
            output = _escape_html(output)

            await update.effective_chat.send_message(
                f"✅ <b>任務完成</b>\n\n"
                f"🆔 <code>{_escape_html(composer_id[:8])}</code>\n"
                f"⏱️ 執行時間: {time_str}\n\n"
                f"📝 <b>結果:</b>\n{output}",
                parse_mode="HTML",
                reply_markup=get_task_keyboard(composer_id, "completed"),
            )
            
            # Delete the status message
            try:
                await status_msg.delete()
            except Exception:
                pass
        else:
            status = _escape_html(result.get('status', 'unknown'))
            message = _escape_html(result.get('message', 'Unknown'))
            await update.effective_chat.send_message(
                f"❌ <b>任務失敗</b>\n\n"
                f"🆔 <code>{_escape_html(composer_id[:8])}</code>\n"
                f"⏱️ 執行時間: {time_str}\n"
                f"📊 狀態: {status}\n"
                f"❗ 原因: {message}",
                parse_mode="HTML",
                reply_markup=get_task_keyboard(composer_id, "failed"),
            )
            
            # Delete the status message
            try:
                await status_msg.delete()
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Poll error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Notify user of polling error
        try:
            await update.effective_chat.send_message(
                f"⚠️ <b>輪詢錯誤</b>\n\n"
                f"🆔 <code>{_escape_html(composer_id[:8])}</code>\n"
                f"錯誤: {_escape_html(str(e)[:200])}\n\n"
                f"使用 /result {composer_id[:8]} 手動檢查任務狀態",
                parse_mode="HTML",
            )
        except Exception:
            pass


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
    Show all repositories from Cursor account with pagination.
    """
    from .keyboards import get_repo_keyboard
    
    user_id = update.effective_user.id
    current_repo = get_user_repo(user_id)

    # Fetch repositories from Cursor API if Background Agent is enabled
    if not is_background_agent_enabled():
        await update.message.reply_text(
            "💡 <b>未啟用 Background Agent</b>\n\n"
            "請設定 CURSOR_API_KEY 以查看帳號中的所有倉庫。\n\n"
            "<b>手動切換倉庫:</b>\n"
            "<code>/repo owner/repo-name</code>",
            parse_mode="HTML",
        )
        return

    # Send loading message
    loading_msg = await update.message.reply_text(
        "🔄 <b>正在獲取倉庫列表...</b>",
        parse_mode="HTML",
    )
    
    try:
        bg_agent = get_background_agent(settings.cursor_api_key)
        result = await bg_agent.list_repositories()
        
        if result.get("success") and result.get("repositories"):
            repos = result.get("repositories", [])
            
            # Cache repos in context for pagination
            context.user_data["repos_cache"] = repos
            
            # Build text
            text = f"<b>📁 選擇倉庫</b>\n\n"
            text += f"共 {len(repos)} 個倉庫（第 1/{max(1, (len(repos) + 7) // 8)} 頁）\n"
            text += "點擊按鈕切換倉庫：\n"
            
            if current_repo:
                repo_name = current_repo.split("/")[-1]
                text += f"\n目前使用: <code>{repo_name}</code>"
            
            await loading_msg.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_repo_keyboard(repos, current_repo, page=0),
            )
        elif result.get("message"):
            await loading_msg.edit_text(
                f"⚠️ <b>無法取得倉庫列表</b>\n\n"
                f"{result.get('message', '')[:100]}\n\n"
                f"<b>手動切換倉庫:</b>\n"
                f"<code>/repo owner/repo-name</code>",
                parse_mode="HTML",
            )
        else:
            await loading_msg.edit_text(
                "📭 <b>帳號中沒有找到任何倉庫</b>\n\n"
                "<b>手動切換倉庫:</b>\n"
                "<code>/repo owner/repo-name</code>",
                parse_mode="HTML",
            )
            
    except Exception as e:
        logger.error(f"Error fetching repositories: {e}")
        await loading_msg.edit_text(
            f"❌ <b>取得倉庫時發生錯誤</b>\n\n"
            f"<code>{str(e)[:100]}</code>",
            parse_mode="HTML",
        )


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


def _should_respond_in_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[bool, str]:
    """
    Check if bot should respond in a group chat.
    
    Returns:
        tuple of (should_respond, cleaned_message)
    """
    message_text = update.message.text or ""
    chat_type = update.effective_chat.type
    
    # Always respond in private chats
    if chat_type == "private":
        return True, message_text
    
    # In groups, check for @mention
    bot_username = context.bot.username
    if not bot_username:
        return False, message_text
    
    # Check for @mention patterns
    mention_patterns = [
        f"@{bot_username}",
        f"@{bot_username.lower()}",
    ]
    
    # Check if message starts with or contains @bot mention
    cleaned_message = message_text
    found_mention = False
    
    for pattern in mention_patterns:
        if pattern in message_text.lower():
            found_mention = True
            # Remove the mention from message
            cleaned_message = message_text.replace(pattern, "").replace(pattern.lower(), "").strip()
            break
    
    # Also check message entities for mention
    if not found_mention and update.message.entities:
        for entity in update.message.entities:
            if entity.type == "mention":
                mention_text = message_text[entity.offset:entity.offset + entity.length]
                if mention_text.lower() == f"@{bot_username.lower()}":
                    found_mention = True
                    cleaned_message = message_text[:entity.offset] + message_text[entity.offset + entity.length:]
                    cleaned_message = cleaned_message.strip()
                    break
    
    # Check if it's a reply to bot's message
    if not found_mention and update.message.reply_to_message:
        reply_user = update.message.reply_to_message.from_user
        if reply_user and reply_user.is_bot and reply_user.username == bot_username:
            found_mention = True
    
    return found_mention, cleaned_message


def _get_session_key(update: Update) -> str:
    """
    Get a unique session key for the chat.
    Different chats/groups have different sessions.
    """
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if chat_type == "private":
        # Private chat: use user_id
        return f"user_{update.effective_user.id}"
    else:
        # Group chat: use chat_id
        return f"group_{chat_id}"


@authorized_only
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle regular text messages.
    Supports @mention in groups and session isolation.
    Routes to Agent Loop or Cursor Background Agent based on user mode.
    """
    # Check if we should respond (handles group @mention)
    should_respond, message_text = _should_respond_in_group(update, context)
    
    if not should_respond:
        # In group but not mentioned, ignore
        return
    
    if not message_text.strip():
        # Empty message after removing mention
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat_id = update.effective_chat.id
    session_key = _get_session_key(update)
    chat_type = update.effective_chat.type
    
    logger.info(f"User {user_id} message in {chat_type} (session: {session_key}): {message_text[:50]}...")
    
    # Show typing indicator
    await update.effective_chat.send_action("typing")

    # Get user's chat mode preference
    chat_mode = get_user_chat_mode(user_id)
    
    if chat_mode == "agent":
        # Use Agent Loop mode
        await _handle_agent_mode(update, message_text, user_id, username, chat_id)
    else:
        # Use Cursor Background Agent mode (default)
        if is_background_agent_enabled():
            await _handle_background_agent_ask(update, message_text, user_id, username, chat_id)
        else:
            # Fallback to Agent mode if Cursor not configured
            await _handle_agent_mode(update, message_text, user_id, username, chat_id)


async def _handle_agent_mode(
    update: Update,
    message_text: str,
    user_id: int,
    username: str,
    chat_id: int,
) -> None:
    """Handle message using Agent Loop mode."""
    from ..core import get_agent_loop
    from ..core.llm_providers import get_llm_manager
    
    try:
        # Get user's model settings
        manager = get_llm_manager()
        user_provider = manager.get_llm_provider_function_for_user(str(user_id))
        current_model = manager.get_user_model(str(user_id))
        
        # Get agent loop
        agent = get_agent_loop()
        
        # Use user's provider if set
        original_provider = agent.llm_provider
        if user_provider:
            agent.llm_provider = user_provider
        
        try:
            # Run agent
            result = await agent.run(
                task=message_text,
                context={
                    "user_id": str(user_id),
                    "username": username,
                    "chat_id": str(chat_id),
                    "platform": "telegram",
                }
            )
            
            # Format response
            if result.success:
                response = result.result or "任務完成"
            else:
                response = f"❌ Agent 錯誤: {result.error or '未知錯誤'}"
            
            # Send response (handle long messages)
            if len(response) > 4000:
                # Split into chunks
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk, parse_mode="HTML")
            else:
                await update.message.reply_text(response, parse_mode="HTML")
                
        finally:
            # Restore original provider
            agent.llm_provider = original_provider
            
    except Exception as e:
        logger.error(f"Agent mode error: {e}")
        await update.message.reply_text(
            f"❌ <b>Agent 錯誤</b>\n\n<code>{str(e)[:500]}</code>",
            parse_mode="HTML"
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
