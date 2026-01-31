"""
Telegram Bot command and message handlers
Defines all user interaction endpoints
"""

import asyncio
import os
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..utils.auth import authorized_only
from ..utils.config import settings
from ..utils.logger import logger

# Import shared cursor agent instance from handlers_extended
# This ensures all modules use the same workspace state
from .handlers_extended import get_cursor_agent

# User chat mode settings (cli vs agent vs assistant)
# Key: user_id, Value: "cli", "agent", "assistant", or "auto"
_user_chat_modes: dict[int, str] = {}

# Default chat mode (auto = use priority: cli -> agent)
DEFAULT_CHAT_MODE = "auto"  # "auto", "cli", "agent", or "assistant"

# Valid chat modes
VALID_CHAT_MODES = ["auto", "cli", "agent", "assistant"]


def get_user_chat_mode(user_id: int) -> str:
    """Get user's chat mode preference."""
    return _user_chat_modes.get(user_id, DEFAULT_CHAT_MODE)


def set_user_chat_mode(user_id: int, mode: str) -> bool:
    """Set user's chat mode preference."""
    if mode not in VALID_CHAT_MODES:
        return False
    _user_chat_modes[user_id] = mode
    return True


async def store_conversation_to_rag(
    user_id: int,
    username: str,
    question: str,
    answer: str,
    source: str = "agent",
    metadata: dict = None,
) -> bool:
    """
    Store a conversation (question + answer) into RAG for future retrieval.
    
    Args:
        user_id: User ID
        username: Username
        question: User's question/prompt
        answer: AI's response
        source: Source type ("agent", "ask", "cli")
        metadata: Additional metadata
        
    Returns:
        True if stored successfully
    """
    try:
        from ..core.rag import get_rag_manager
        from datetime import datetime
        
        rag = get_rag_manager()
        
        # Format conversation for storage
        timestamp = datetime.now().isoformat()
        conversation_text = f"""## 對話記錄
時間: {timestamp}
使用者: {username} (ID: {user_id})
來源: {source}

### 問題
{question}

### 回答
{answer}
"""
        
        # Build metadata
        doc_metadata = {
            "source": source,
            "type": "conversation",
            "user_id": str(user_id),
            "username": username,
            "timestamp": timestamp,
        }
        if metadata:
            doc_metadata.update(metadata)
        
        # Index the conversation
        doc_id = f"conv_{user_id}_{int(datetime.now().timestamp())}"
        chunks = await rag.index_text(
            text=conversation_text,
            doc_id=doc_id,
            metadata=doc_metadata,
        )
        
        logger.debug(f"Stored conversation to RAG: {doc_id} ({chunks} chunks)")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to store conversation to RAG: {e}")
        return False


def set_user_chat_mode(user_id: int, mode: str) -> None:
    """Set user's chat mode preference."""
    if mode in ("auto", "cli", "agent", "cursor"):
        _user_chat_modes[user_id] = mode


def get_best_available_mode() -> str:
    """
    Get the best available mode based on priority.
    Priority: CLI -> Agent
    All modes use async execution by default.
    """
    from ..cursor.cli_agent import is_cli_available
    
    # Prefer CLI if available
    if is_cli_available():
        return "cli"
    
    # Fallback to Agent
    return "agent"


# Note: get_cursor_agent is imported from handlers_extended to share the same instance


# ============================================
# Command Handlers
# ============================================


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command.
    Welcome message and basic instructions with secretary persona.
    """
    from .keyboards import get_welcome_keyboard
    from ..core.secretary import get_secretary, SecretaryPersona

    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")

    # Get or create secretary preferences
    secretary = get_secretary()
    prefs = secretary.get_preferences(str(user.id))
    
    # Set user name if not set
    user_name = user.first_name or "用戶"
    if not prefs.name:
        secretary.set_user_name(str(user.id), user_name)
        prefs = secretary.get_preferences(str(user.id))

    # Check status
    status_items = []
    
    # Check Cursor CLI status
    try:
        from ..cursor.cli_agent import is_cli_available, get_cli_agent
        if is_cli_available():
            cli = get_cli_agent()
            cli_model = cli.get_user_model(str(user.id)) or "auto"
            # Escape HTML special characters
            cli_model_safe = _escape_html(str(cli_model))
            status_items.append(f"🟢 CLI ({cli_model_safe})")
        else:
            status_items.append("⚪ CLI (未安裝)")
    except Exception:
        status_items.append("⚪ CLI")

    # Check AI model status
    try:
        from ..core.llm_providers import get_llm_manager
        manager = get_llm_manager()
        available = manager.list_available_providers()
        if available:
            current = manager.get_user_model(str(user.id))
            model_name = f"{current[0]}/{current[1]}" if current else "預設"
            # Escape HTML special characters
            model_name_safe = _escape_html(str(model_name))
            status_items.append(f"🤖 {model_name_safe}")
        else:
            status_items.append("⚪ AI 模型")
    except Exception:
        status_items.append("⚪ AI 模型")

    # Check Discord status
    if settings.discord_enabled and settings.discord_bot_token:
        status_items.append("🟢 Discord")
    
    status_text = " | ".join(status_items) if status_items else "⚠️ 請設定 API Key"
    
    # Escape user's name for HTML
    user_name_safe = _escape_html(prefs.name or user_name)
    secretary_name_safe = _escape_html(prefs.secretary_name)
    
    # Get time-based greeting
    greeting = SecretaryPersona.greeting(prefs.name or user_name)
    greeting_safe = _escape_html(greeting)

    welcome_text = f"""{greeting_safe}

我是您的專屬秘書 <b>{secretary_name_safe}</b>！✨

<b>📡 狀態:</b> {status_text}

<b>👩‍💼 秘書服務：</b>
• /briefing - 今日簡報（行程 + 待辦）
• /todo add &lt;任務&gt; - 新增待辦事項
• /book - 訂票助手（機票、火車、飯店）
• /calendar - 查看行程
• /reminder on - 啟用每日提醒

<b>⚡ AI 助手：</b>
• 直接發送訊息即可對話
• /mode cli - 切換程式碼模式
• /mode agent - 切換 AI 助手模式

<b>🎤 語音控制：</b>
• 說「Hey Cursor」喚醒語音助手

📋 更多指令請輸入 /help

—— {secretary_name_safe}，隨時為您服務！💕
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
    Display detailed help information with secretary persona.
    """
    from ..core.secretary import get_secretary
    
    user = update.effective_user
    secretary = get_secretary()
    prefs = secretary.get_preferences(str(user.id))
    secretary_name_safe = _escape_html(prefs.secretary_name)
    
    # Check status
    status_parts = []
    
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

    help_text = f"""<b>📖 CursorBot v1.1 指令說明</b>
{status_info}

<b>👩‍💼 個人秘書</b>
━━━━━━━━━━━━━━━━━━━━━━
/mode assistant - 切換秘書模式 👈
/briefing - 今日簡報
/todo [add|done|list] - 待辦事項
/book [flight|train|hotel] - 訂票助手
/secretary - 秘書設定

<b>📅 日曆 &amp; 郵件</b>
/calendar [week|list|add]
/reminder [on|off] - 每日提醒
/gmail [search|unread]

<b>⚡ 對話模式</b>
/mode assistant - 秘書模式（推薦）
/mode cli - 程式碼模式
/mode agent - AI Agent 模式

<b>🧠 記憶 &amp; RAG</b>
/memory [add|get|del|clear]
/rag &lt;問題&gt; /index &lt;檔案&gt;

<b>🎤 語音助手</b>
/voice - 語音設定
/meeting - 會議助手

<b>💡 秘書模式可用自然語言：</b>
• 「幫我記開會」
• 「今天有什麼行程」
• 「訂機票去東京」

—— {secretary_name_safe}
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
    
    # Check CLI status
    cli_status = "⚪ CLI 未安裝"
    try:
        from ..cursor.cli_agent import is_cli_available, get_cli_agent
        if is_cli_available():
            cli = get_cli_agent()
            user_id = str(update.effective_user.id)
            cli_model = cli.get_user_model(user_id) or "auto"
            # Escape HTML special characters in model name
            cli_model_safe = _escape_html(str(cli_model))
            cli_status = f"🟢 CLI ({cli_model_safe})"
    except Exception:
        pass
    
    # Check AI providers
    ai_status = "⚪ AI 未設定"
    try:
        from ..core.llm_providers import get_llm_manager
        manager = get_llm_manager()
        providers = manager.list_available_providers()
        if providers:
            ai_status = f"🟢 AI ({len(providers)} 提供者)"
    except Exception:
        pass

    # Check v0.4 modules
    v04_status = []
    
    # Check MCP
    try:
        from ..core.mcp import get_mcp_manager
        mcp = get_mcp_manager()
        connected = len(mcp.list_servers())
        v04_status.append(f"🔌 MCP ({connected} 伺服器)")
    except Exception:
        v04_status.append("⚪ MCP")
    
    # Check Workflow
    try:
        from ..core.workflow import get_workflow_engine
        engine = get_workflow_engine()
        workflows = len(engine.list_workflows())
        v04_status.append(f"⚙️ Workflow ({workflows} 工作流)")
    except Exception:
        v04_status.append("⚪ Workflow")
    
    # Check Analytics
    try:
        from ..core.analytics import get_analytics_manager
        analytics = get_analytics_manager()
        v04_status.append("📊 Analytics")
    except Exception:
        v04_status.append("⚪ Analytics")
    
    # Check Async Tasks
    try:
        from ..core.async_tasks import get_task_manager
        tm = get_task_manager()
        stats = await tm.get_stats()
        pending = stats.get("pending_tasks", 0)
        v04_status.append(f"⏳ Tasks ({pending} 待處理)")
    except Exception:
        v04_status.append("⚪ Tasks")
    
    # Check RAG
    try:
        from ..core.rag import get_rag_manager
        rag = get_rag_manager()
        v04_status.append("📚 RAG")
    except Exception:
        v04_status.append("⚪ RAG")
    
    v04_text = " | ".join(v04_status)

    message = f"""
<b>📊 系統狀態 (v0.4)</b>

<b>🤖 Cursor CLI</b>
{cli_status}

<b>🧠 AI 提供者</b>
{ai_status}

<b>📂 工作區</b>
• 名稱: {ws_info['name']}
• 檔案數: {ws_info['total_files']}
• 路徑: <code>{ws_info['path']}</code>

<b>🆕 v0.4 模組</b>
{v04_text}

<b>💡 使用方式</b>
• /mode 切換對話模式
• /model 切換 AI 模型
• /cli_async 背景執行 CLI
• /review 程式碼審查
• /analytics 使用分析
"""
    await update.message.reply_text(message, parse_mode="HTML")


@authorized_only
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /file command.
    File operations (read, list, etc.) with path traversal protection.
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
    
    # Path traversal protection
    from ..utils.security import sanitize_path
    from ..utils.config import settings
    
    # Get workspace as base directory
    base_dir = settings.effective_workspace_path or os.getcwd()
    
    # Validate and sanitize path
    is_valid, safe_path, error = sanitize_path(path, base_directory=base_dir)
    if not is_valid:
        await update.message.reply_text(
            f"❌ <b>路徑錯誤</b>\n\n{_escape_html(error)}\n\n"
            f"路徑必須在工作區內: <code>{_escape_html(base_dir)}</code>",
            parse_mode="HTML",
        )
        return

    agent = get_cursor_agent()

    if operation == "read":
        try:
            content = await agent.read_file(safe_path)
            if len(content) > 4000:
                content = content[:4000] + "\n... (內容過長已截斷)"
            # Escape HTML in content
            content = _escape_html(content)
            display_path = _escape_html(path)
            await update.message.reply_text(
                f"📄 <b>{display_path}</b>\n\n<pre>{content}</pre>",
                parse_mode="HTML",
            )
        except FileNotFoundError:
            await update.message.reply_text(f"❌ 檔案不存在: {_escape_html(path)}", parse_mode="HTML")
        except PermissionError:
            await update.message.reply_text(f"❌ 沒有權限讀取: {_escape_html(path)}", parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ 讀取錯誤: {_escape_html(str(e)[:100])}", parse_mode="HTML")
    elif operation == "list":
        try:
            files = await agent.list_files(safe_path)
            display_path = _escape_html(path)
            files = _escape_html(files)
            await update.message.reply_text(
                f"📂 <b>{display_path}</b>\n\n{files}",
                parse_mode="HTML",
            )
        except FileNotFoundError:
            await update.message.reply_text(f"❌ 目錄不存在: {_escape_html(path)}", parse_mode="HTML")
        except PermissionError:
            await update.message.reply_text(f"❌ 沒有權限存取: {_escape_html(path)}", parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ 列出錯誤: {_escape_html(str(e)[:100])}", parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ 未知操作: {_escape_html(operation)}", parse_mode="HTML")


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


async def _handle_media_task_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_text: str,
    user_id: int,
    username: str,
    chat_id: int,
) -> None:
    """
    Handle user input for media task description.
    Creates an actual async task with the media and description.
    Uses user's current mode (CLI or Agent).
    """
    from ..core.async_tasks import get_task_manager
    from .media_handlers import get_cached_media, clear_cache
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # Check for cancel
    if message_text.lower() in ["/cancel", "cancel", "取消"]:
        context.user_data["waiting_for_media_task"] = False
        clear_cache(user_id)
        await update.message.reply_text("❌ 已取消任務建立")
        return
    
    # Clear waiting state
    context.user_data["waiting_for_media_task"] = False
    
    # Get cached media
    cached_media = get_cached_media(user_id)
    
    if not cached_media:
        await update.message.reply_text("❌ 媒體快取已過期，請重新發送媒體檔案")
        return
    
    # Build prompt with media info
    media_parts = []
    for media in cached_media:
        media_type = media.get("type", "unknown")
        if media_type == "photo":
            media_parts.append("[附加圖片]")
        elif media_type == "voice":
            transcription = media.get("transcription", "")
            if transcription:
                media_parts.append(f"[語音轉錄: {transcription}]")
            else:
                media_parts.append("[附加語音]")
        elif media_type == "document":
            media_parts.append(f"[附加檔案: {media.get('file_name', 'unknown')}]")
    
    media_info = "\n".join(media_parts)
    full_prompt = f"{message_text}\n\n---\n附加媒體:\n{media_info}"
    
    # Show typing
    await update.effective_chat.send_action("typing")
    
    # Get user's current mode
    chat_mode = get_user_chat_mode(user_id)
    if chat_mode == "auto":
        chat_mode = get_best_available_mode()
    
    try:
        manager = get_task_manager()
        
        # Submit task based on user's mode
        if chat_mode == "cli":
            from ..cursor.cli_agent import is_cli_available
            if is_cli_available():
                task_id = await manager.submit_cli_task(
                    user_id=str(user_id),
                    chat_id=str(chat_id),
                    platform="telegram",
                    prompt=full_prompt,
                    timeout=None,  # No timeout, use CLI's own setting
                    metadata={
                        "username": username,
                        "source": "media_task",
                        "media_count": len(cached_media),
                        "media_types": [m.get("type") for m in cached_media],
                    },
                )
                mode_name = "CLI"
            else:
                # Fallback to Agent if CLI not available
                task_id = await manager.submit_agent_task(
                    user_id=str(user_id),
                    chat_id=str(chat_id),
                    platform="telegram",
                    prompt=full_prompt,
                    timeout=600.0,
                    metadata={
                        "username": username,
                        "source": "media_task",
                        "media_count": len(cached_media),
                        "media_types": [m.get("type") for m in cached_media],
                    },
                )
                mode_name = "Agent (CLI 不可用)"
        else:
            # Agent mode
            task_id = await manager.submit_agent_task(
                user_id=str(user_id),
                chat_id=str(chat_id),
                platform="telegram",
                prompt=full_prompt,
                timeout=600.0,  # 10 minutes for Agent
                metadata={
                    "username": username,
                    "source": "media_task",
                    "media_count": len(cached_media),
                    "media_types": [m.get("type") for m in cached_media],
                },
            )
            mode_name = "Agent"
        
        # Clear media cache after task creation
        clear_cache(user_id)
        
        # Send confirmation
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("查看狀態", callback_data=f"task_status:{task_id}"),
                InlineKeyboardButton("取消", callback_data=f"task_cancel:{task_id}"),
            ]
        ])
        
        preview = message_text[:50] + "..." if len(message_text) > 50 else message_text
        safe_preview = _escape_html(preview)
        
        await update.message.reply_text(
            f"🤖 <b>媒體任務已建立</b> ({mode_name})\n\n"
            f"📝 <code>{safe_preview}</code>\n"
            f"📎 包含 {len(cached_media)} 個媒體檔案\n\n"
            f"🆔 <code>{task_id}</code>\n\n"
            f"⏳ 背景執行中，完成後自動通知\n\n"
            f"💡 <code>/tasks</code> 查看所有任務",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        
        logger.info(f"Media task {task_id} ({mode_name}) created for user {user_id} with {len(cached_media)} media files")
        
    except Exception as e:
        logger.error(f"Failed to create media task: {e}")
        await update.message.reply_text(f"❌ 建立任務失敗: {str(e)[:100]}")


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
    
    # Check if waiting for media task description
    if context.user_data.get("waiting_for_media_task"):
        await _handle_media_task_input(update, context, message_text, user_id, username, chat_id)
        return
    
    logger.info(f"User {user_id} message in {chat_type} (session: {session_key}): {message_text[:50]}...")
    
    # Show typing indicator
    await update.effective_chat.send_action("typing")

    # Get user's chat mode preference
    chat_mode = get_user_chat_mode(user_id)
    
    # Handle auto mode - use priority: CLI -> Agent
    if chat_mode == "auto":
        chat_mode = get_best_available_mode()
    
    # Route based on mode
    if chat_mode == "assistant":
        # Use Assistant Mode (personal secretary)
        await _handle_assistant_mode(update, message_text, user_id, username, chat_id)
    elif chat_mode == "cli":
        # Use Cursor CLI mode (async)
        from ..cursor.cli_agent import is_cli_available
        if is_cli_available():
            await _handle_async_cli_mode(update, message_text, user_id, username, chat_id)
        else:
            # Fallback to Agent (async)
            await _handle_async_agent_mode(update, message_text, user_id, username, chat_id)
    else:
        # Use Agent Loop mode (async)
        await _handle_async_agent_mode(update, message_text, user_id, username, chat_id)


async def _handle_assistant_mode(
    update: Update,
    message_text: str,
    user_id: int,
    username: str,
    chat_id: int,
) -> None:
    """
    Handle message using Assistant Mode (personal secretary).
    
    Uses natural language understanding to process commands
    and respond with a friendly secretary persona.
    """
    from ..core.secretary import get_assistant_mode
    
    try:
        assistant = get_assistant_mode()
        
        # Process message with assistant
        response = await assistant.process_message(str(user_id), message_text)
        
        # Send response
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Assistant mode error: {e}")
        
        # Friendly error response
        from ..core.secretary import get_secretary
        secretary = get_secretary()
        prefs = secretary.get_preferences(str(user_id))
        
        await update.message.reply_text(
            f"抱歉，我遇到了一點問題呢～\n"
            f"請稍後再試，或使用 /help 查看可用指令。\n\n"
            f"—— {prefs.secretary_name}"
        )


async def _handle_async_agent_mode(
    update: Update,
    message_text: str,
    user_id: int,
    username: str,
    chat_id: int,
) -> None:
    """
    Handle message using Async Agent mode (non-blocking).
    
    Submits task to background and pushes result when complete.
    User receives immediate confirmation and can continue chatting.
    """
    from ..core.async_tasks import get_task_manager
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    try:
        manager = get_task_manager()
        
        # Submit task to background
        task_id = await manager.submit_agent_task(
            user_id=str(user_id),
            chat_id=str(chat_id),
            platform="telegram",
            prompt=message_text,
            timeout=300.0,
            metadata={
                "username": username,
                "source": "message",
            },
        )
        
        # Send confirmation with task ID
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("查看狀態", callback_data=f"task_status:{task_id}"),
                InlineKeyboardButton("取消", callback_data=f"task_cancel:{task_id}"),
            ]
        ])
        
        # Truncate message for display
        preview = message_text[:50] + "..." if len(message_text) > 50 else message_text
        safe_preview = _escape_html(preview)
        
        await update.message.reply_text(
            f"🤖 <b>Agent 任務已提交</b>\n\n"
            f"📝 <code>{safe_preview}</code>\n\n"
            f"🆔 <code>{task_id}</code>\n\n"
            f"⏳ 背景執行中，完成後自動通知\n\n"
            f"💡 <code>/tasks</code> 查看所有任務",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        
    except Exception as e:
        logger.error(f"Async agent mode error: {e}")
        await update.message.reply_text(
            f"❌ <b>任務提交失敗</b>\n\n"
            f"錯誤: {_escape_html(str(e)[:200])}",
            parse_mode="HTML"
        )


async def _handle_async_cli_mode(
    update: Update,
    message_text: str,
    user_id: int,
    username: str,
    chat_id: int,
) -> None:
    """
    Handle message using Async CLI mode (non-blocking).
    
    Submits CLI task to background and pushes result when complete.
    """
    from ..core.async_tasks import get_task_manager
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    try:
        manager = get_task_manager()
        
        # Get current workspace
        workspace_agent = get_cursor_agent()
        working_dir = workspace_agent.get_current_workspace()
        
        # Submit CLI task to background
        task_id = await manager.submit_cli_task(
            user_id=str(user_id),
            chat_id=str(chat_id),
            platform="telegram",
            prompt=message_text,
            working_directory=working_dir,
            timeout=None,  # No timeout, use CLI's own setting
            metadata={
                "username": username,
                "source": "message",
                "workspace": working_dir,
            },
        )
        
        # Send confirmation with task ID
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("查看狀態", callback_data=f"task_status:{task_id}"),
                InlineKeyboardButton("取消", callback_data=f"task_cancel:{task_id}"),
            ]
        ])
        
        # Truncate message for display
        preview = message_text[:50] + "..." if len(message_text) > 50 else message_text
        safe_preview = _escape_html(preview)
        workspace_name = _escape_html(workspace_agent.get_current_workspace_name())
        
        await update.message.reply_text(
            f"⌨️ <b>CLI 任務已提交</b>\n\n"
            f"📝 <code>{safe_preview}</code>\n"
            f"📂 <code>{workspace_name}</code>\n\n"
            f"🆔 <code>{task_id}</code>\n\n"
            f"⏳ 背景執行中，完成後自動通知\n\n"
            f"💡 <code>/tasks</code> 查看所有任務",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        
    except Exception as e:
        logger.error(f"Async CLI mode error: {e}")
        await update.message.reply_text(
            f"❌ <b>任務提交失敗</b>\n\n"
            f"錯誤: {_escape_html(str(e)[:200])}",
            parse_mode="HTML"
        )


async def _handle_cli_mode(
    update: Update,
    message_text: str,
    user_id: int,
    username: str,
    chat_id: int,
) -> None:
    """Handle message using Cursor CLI mode."""
    from ..cursor.cli_agent import get_cli_agent
    
    try:
        cli = get_cli_agent()
        
        if not cli.is_available:
            await update.message.reply_text(
                "⚠️ <b>Cursor CLI 未安裝</b>\n\n"
                "安裝指令:\n"
                "<code>curl https://cursor.com/install -fsS | bash</code>\n\n"
                "使用 <code>/mode agent</code> 切換到 Agent 模式",
                parse_mode="HTML"
            )
            return
        
        # Check if authenticated
        api_key = os.getenv("CURSOR_API_KEY", "")
        if not api_key:
            # Check if logged in by trying a simple command
            check_result = await cli.check_installation()
            if "login" in str(check_result).lower():
                await update.message.reply_text(
                    "⚠️ <b>Cursor CLI 需要認證</b>\n\n"
                    "請執行以下其中一種方式:\n\n"
                    "<b>方法 1: 互動式登入</b>\n"
                    "<code>agent login</code>\n\n"
                    "<b>方法 2: 設定 API Key</b>\n"
                    "在 .env 中設定:\n"
                    "<code>CURSOR_API_KEY=your-key</code>\n\n"
                    "或使用 <code>/mode agent</code> 切換模式",
                    parse_mode="HTML"
                )
                return
        
        # Get current workspace from workspace agent
        workspace_agent = get_cursor_agent()
        current_workspace = workspace_agent.get_current_workspace()
        
        # Send processing message (escape user input)
        safe_workspace = _escape_html(workspace_agent.get_current_workspace_name())
        safe_message = _escape_html(message_text[:100])
        status_msg = await update.message.reply_text(
            "💻 <b>Cursor CLI 處理中...</b>\n\n"
            f"📂 工作區: <code>{safe_workspace}</code>\n"
            f"<code>{safe_message}{'...' if len(message_text) > 100 else ''}</code>",
            parse_mode="HTML"
        )
        
        # Run CLI with current workspace directory and user context
        # Pass user_id to enable conversation memory (--resume)
        logger.info(f"Sending to CLI: {message_text[:80]}... (user: {user_id})")
        
        result = await cli.run(
            prompt=message_text,
            working_directory=current_workspace,
            user_id=str(user_id),
        )
        
        # Log result for debugging
        logger.info(f"CLI result: success={result.success}, output_len={len(result.output or '')}")
        if result.output:
            logger.debug(f"CLI output preview: {result.output[:150]}...")
        
        if result.success:
            # Escape HTML in output to prevent parsing errors
            output_text = _escape_html(result.output) if result.output else "任務完成"
            response = output_text
            
            # Add file modification info if any
            if result.files_modified:
                files_info = "\n".join(f"• {_escape_html(f)}" for f in result.files_modified[:5])
                response += f"\n\n📁 <b>修改的檔案:</b>\n{files_info}"
            
            # Add duration
            response += f"\n\n⏱️ 耗時: {result.duration:.1f}s"
            
            # Store successful conversation to RAG
            asyncio.create_task(
                store_conversation_to_rag(
                    user_id=user_id,
                    username=username,
                    question=message_text,
                    answer=result.output or "任務完成",
                    source="cli",
                    metadata={
                        "workspace": current_workspace,
                        "duration": result.duration,
                        "files_modified": result.files_modified,
                    },
                )
            )
        else:
            # Escape HTML in error message
            error_text = _escape_html(result.error[:500]) if result.error else "未知錯誤"
            response = f"❌ <b>CLI 錯誤</b>\n\n<code>{error_text}</code>"
        
        # Delete status message
        await status_msg.delete()
        
        # Send response (handle long messages)
        if len(response) > 4000:
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode="HTML")
        else:
            await update.message.reply_text(response, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"CLI mode error: {e}")
        safe_error = _escape_html(str(e)[:500])
        await update.message.reply_text(
            f"❌ <b>Cursor CLI 錯誤</b>\n\n<code>{safe_error}</code>",
            parse_mode="HTML"
        )


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
            
            # Format response (escape HTML to prevent parsing errors)
            if result.success:
                response = _escape_html(result.result) if result.result else "任務完成"
                
                # Store successful conversation to RAG
                asyncio.create_task(
                    store_conversation_to_rag(
                        user_id=user_id,
                        username=username,
                        question=message_text,
                        answer=result.result or "任務完成",
                        source="agent",
                        metadata={"model": current_model} if current_model else None,
                    )
                )
            else:
                error_msg = _escape_html(result.error) if result.error else "未知錯誤"
                response = f"❌ Agent 錯誤: {error_msg}"
            
            # Send response (handle long messages)
            if len(response) > 4000:
                # Split into chunks
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)  # No HTML parse mode for escaped content
            else:
                await update.message.reply_text(response)  # No HTML parse mode for escaped content
                
        finally:
            # Restore original provider
            agent.llm_provider = original_provider
            
    except Exception as e:
        logger.error(f"Agent mode error: {e}")
        safe_error = _escape_html(str(e)[:500])
        await update.message.reply_text(
            f"❌ <b>Agent 錯誤</b>\n\n<code>{safe_error}</code>",
            parse_mode="HTML"
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error {context.error}")

    if update and update.effective_message:
        safe_error = _escape_html(str(context.error)[:200])
        await update.effective_message.reply_text(
            "❌ 發生錯誤,請稍後重試。\n\n"
            f"<code>{safe_error}</code>",
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

    # Workspace handlers
    app.add_handler(CommandHandler("file", file_handler))
    app.add_handler(CommandHandler("search", search_handler))
    app.add_handler(CommandHandler("project", project_handler))

    # Setup async task handlers FIRST (non-blocking agent/cli execution)
    # This must be before setup_callback_handlers to ensure task_ callbacks are handled
    from .async_handlers import register_async_handlers
    register_async_handlers(app)

    # Setup callback handlers for inline keyboards
    # Note: task_ callbacks are excluded by pattern and handled by async_handlers
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

    # Setup Google and Skills Registry handlers
    from .google_handlers import setup_google_handlers
    setup_google_handlers(app)

    # Setup v0.4 feature handlers (MCP, Workflow, Analytics, Code Review, etc.)
    from .v04_handlers import register_v04_handlers
    register_v04_handlers(app)
    
    # Setup v0.4 advanced feature handlers (Gateway, Pairing, Canvas, i18n, etc.)
    from .v04_advanced_handlers import register_v04_advanced_handlers
    register_v04_advanced_handlers(app)
    
    # Setup personal assistant handlers (Todo, Reminder, Book, Secretary)
    from .assistant_handlers import setup_assistant_handlers
    setup_assistant_handlers(app)

    logger.info("Bot handlers configured successfully")


__all__ = ["setup_handlers"]
