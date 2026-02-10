"""
Core feature handlers for Telegram Bot
Integrates memory, skills, approvals, and other core features
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..core import (
    get_memory_manager,
    get_skill_manager,
    get_context_manager,
    get_scheduler,
    get_approval_manager,
    ApprovalType,
)
from ..core.session import (
    get_session_manager,
    ChatType,
    DMScope,
    ResetMode,
)
from ..utils.auth import authorized_only
from ..utils.logger import logger


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
# Session Commands (Inspired by ClawdBot)
# Reference: https://docs.clawd.bot/concepts/session
# ============================================


@authorized_only
async def session_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /session command.
    View and manage chat sessions with context memory.
    
    Usage:
        /session - Show current session info
        /session list - List all your sessions
        /session stats - Show session statistics
        /session reset - Reset current session
        /session config - Show session configuration
    """
    from html import escape
    
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    chat_type_raw = update.effective_chat.type
    
    # Map telegram chat type to our ChatType
    if chat_type_raw == "private":
        chat_type = ChatType.DM
    elif chat_type_raw in ("group", "supergroup"):
        chat_type = ChatType.GROUP
    else:
        chat_type = ChatType.CHANNEL
    
    session_mgr = get_session_manager()
    args = context.args or []
    
    if not args:
        # Show current session info
        session = session_mgr.get_session(
            user_id=user_id,
            chat_id=chat_id,
            chat_type=chat_type,
            channel="telegram",
        )
        
        status = session_mgr.get_session_status(session.session_key)
        
        # Format duration
        from datetime import datetime
        age_seconds = (datetime.now() - session.created_at).total_seconds()
        if age_seconds < 60:
            age_str = f"{int(age_seconds)}秒"
        elif age_seconds < 3600:
            age_str = f"{int(age_seconds / 60)}分鐘"
        elif age_seconds < 86400:
            age_str = f"{int(age_seconds / 3600)}小時"
        else:
            age_str = f"{int(age_seconds / 86400)}天"
        
        # Check CLI chat context
        cli_info = ""
        if session.cli_chat_id:
            cli_info = f"\n🔗 CLI 對話: <code>{session.cli_chat_id[:12]}...</code>"
        
        text = f"""💬 <b>目前對話 Session</b>

━━━━━━━━━━━━━━━━━━━━━━
<b>基本資訊</b>
━━━━━━━━━━━━━━━━━━━━━━
🆔 Session ID: <code>{session.session_id[:12]}...</code>
🔑 Session Key: <code>{escape(session.session_key[:30])}...</code>
📅 建立時間: {session.created_at.strftime('%Y-%m-%d %H:%M')}
⏱️ Session 年齡: {age_str}
📨 訊息數量: {session.message_count}
🔄 壓縮次數: {session.compaction_count}{cli_info}

━━━━━━━━━━━━━━━━━━━━━━
<b>Token 使用量</b>
━━━━━━━━━━━━━━━━━━━━━━
📥 輸入: {status['input_tokens']:,}
📤 輸出: {status['output_tokens']:,}
📊 總計: {status['total_tokens']:,}
🧠 上下文: {status['context_tokens']:,}

━━━━━━━━━━━━━━━━━━━━━━
<b>重置策略</b>
━━━━━━━━━━━━━━━━━━━━━━
模式: {status['reset_policy']['mode']}
{'每日重置時間: ' + str(status['reset_policy']['at_hour']) + ':00' if status['reset_policy']['mode'] == 'daily' else ''}
{'閒置分鐘: ' + str(status['reset_policy']['idle_minutes']) if status['reset_policy']['mode'] == 'idle' else ''}
狀態: {'⚠️ 已過期' if status['is_stale'] else '✅ 活躍'}

━━━━━━━━━━━━━━━━━━━━━━
<b>指令</b>
━━━━━━━━━━━━━━━━━━━━━━
<code>/session list</code> - 所有 sessions
<code>/session stats</code> - 統計資訊
<code>/session reset</code> - 重置此 session
<code>/new</code> - 開始新對話
<code>/compact</code> - 壓縮對話歷史
"""
        await update.message.reply_text(text, parse_mode="HTML")
    
    elif args[0] == "list":
        # List user's sessions
        sessions = session_mgr.list_user_sessions(user_id)
        
        if not sessions:
            await update.message.reply_text("📭 目前沒有任何 session")
            return
        
        text = f"📋 <b>我的 Sessions</b> ({len(sessions)} 個)\n\n"
        
        for i, s in enumerate(sessions[:10], 1):
            age_seconds = (datetime.now() - s.updated_at).total_seconds()
            if age_seconds < 60:
                age_str = f"{int(age_seconds)}秒前"
            elif age_seconds < 3600:
                age_str = f"{int(age_seconds / 60)}分前"
            elif age_seconds < 86400:
                age_str = f"{int(age_seconds / 3600)}時前"
            else:
                age_str = f"{int(age_seconds / 86400)}天前"
            
            channel_icon = {
                "telegram": "📱",
                "line": "💚",
                "webchat": "🌐",
                "discord": "🎮",
            }.get(s.channel, "💬")
            
            type_label = {
                ChatType.DM: "私訊",
                ChatType.GROUP: "群組",
                ChatType.THREAD: "討論串",
                ChatType.CHANNEL: "頻道",
            }.get(s.chat_type, "其他")
            
            display = s.display_name or s.subject or s.session_key[:20]
            
            text += f"{i}. {channel_icon} <b>{escape(display)}</b>\n"
            text += f"   {type_label} | {age_str} | {s.message_count} 訊息\n"
        
        if len(sessions) > 10:
            text += f"\n...還有 {len(sessions) - 10} 個 sessions"
        
        await update.message.reply_text(text, parse_mode="HTML")
    
    elif args[0] == "stats":
        # Show statistics
        stats = session_mgr.get_stats()
        
        channel_text = "\n".join(
            f"   • {ch}: {count}" 
            for ch, count in stats['by_channel'].items()
        ) or "   （無）"
        
        type_text = "\n".join(
            f"   • {t}: {count}" 
            for t, count in stats['by_type'].items()
        ) or "   （無）"
        
        text = f"""📊 <b>Session 統計</b>

━━━━━━━━━━━━━━━━━━━━━━
<b>總覽</b>
━━━━━━━━━━━━━━━━━━━━━━
📦 Sessions 數量: {stats['total_sessions']}
📨 總訊息數: {stats['total_messages']:,}
🎫 總 Token 數: {stats['total_tokens']:,}

━━━━━━━━━━━━━━━━━━━━━━
<b>依頻道</b>
━━━━━━━━━━━━━━━━━━━━━━
{channel_text}

━━━━━━━━━━━━━━━━━━━━━━
<b>依類型</b>
━━━━━━━━━━━━━━━━━━━━━━
{type_text}

📁 存儲路徑: <code>{stats['store_path']}</code>
"""
        await update.message.reply_text(text, parse_mode="HTML")
    
    elif args[0] == "reset":
        # Reset current session
        session = session_mgr.reset_session(
            user_id=user_id,
            chat_id=chat_id,
            chat_type=chat_type,
            channel="telegram",
        )
        
        await update.message.reply_text(
            f"🔄 <b>Session 已重置</b>\n\n"
            f"新 Session ID: <code>{session.session_id[:12]}...</code>\n\n"
            f"對話上下文已清除，開始新對話。",
            parse_mode="HTML"
        )
    
    elif args[0] == "config":
        # Show session configuration
        config = session_mgr.config
        
        dm_scope_names = {
            DMScope.MAIN: "main (所有 DM 共用)",
            DMScope.PER_PEER: "per-peer (每人獨立)",
            DMScope.PER_CHANNEL_PEER: "per-channel-peer (每頻道每人獨立)",
        }
        
        reset_mode_names = {
            ResetMode.DAILY: "daily (每日重置)",
            ResetMode.IDLE: "idle (閒置重置)",
            ResetMode.MANUAL: "manual (手動重置)",
            ResetMode.NEVER: "never (永不重置)",
        }
        
        identity_text = ""
        if config.identity_links:
            identity_text = "\n<b>身份連結:</b>\n"
            for canonical, links in list(config.identity_links.items())[:3]:
                identity_text += f"   • {canonical}: {len(links)} 個連結\n"
        
        text = f"""⚙️ <b>Session 設定</b>

━━━━━━━━━━━━━━━━━━━━━━
<b>DM 範圍</b>
━━━━━━━━━━━━━━━━━━━━━━
{dm_scope_names.get(config.dm_scope, str(config.dm_scope))}
Main Key: {config.main_key}

━━━━━━━━━━━━━━━━━━━━━━
<b>預設重置策略</b>
━━━━━━━━━━━━━━━━━━━━━━
模式: {reset_mode_names.get(config.default_reset.mode, str(config.default_reset.mode))}
每日時間: {config.default_reset.at_hour}:00
閒置分鐘: {config.default_reset.idle_minutes}

━━━━━━━━━━━━━━━━━━━━━━
<b>重置觸發器</b>
━━━━━━━━━━━━━━━━━━━━━━
{', '.join(config.reset_triggers)}
{identity_text}
━━━━━━━━━━━━━━━━━━━━━━
<b>環境變數設定</b>
━━━━━━━━━━━━━━━━━━━━━━
<code>SESSION_DM_SCOPE</code> - DM 範圍模式
<code>SESSION_RESET_MODE</code> - 重置模式
<code>SESSION_RESET_HOUR</code> - 每日重置時間
<code>SESSION_IDLE_MINUTES</code> - 閒置分鐘數
"""
        await update.message.reply_text(text, parse_mode="HTML")
    
    elif args[0] == "cleanup":
        # Cleanup stale sessions (admin only)
        count = session_mgr.cleanup_stale_sessions()
        await update.message.reply_text(f"🧹 已清理 {count} 個過期 sessions")
    
    else:
        await update.message.reply_text(
            "❌ 無效的 session 指令。使用 /session 查看用法。"
        )


@authorized_only
async def new_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /new command.
    Start a fresh session (reset trigger).
    
    Usage:
        /new - Start new session
        /new <model> - Start new session with specific model
    """
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    chat_type_raw = update.effective_chat.type
    
    # Map chat type
    if chat_type_raw == "private":
        chat_type = ChatType.DM
    elif chat_type_raw in ("group", "supergroup"):
        chat_type = ChatType.GROUP
    else:
        chat_type = ChatType.CHANNEL
    
    session_mgr = get_session_manager()
    args = context.args or []
    
    # Reset session
    session = session_mgr.reset_session(
        user_id=user_id,
        chat_id=chat_id,
        chat_type=chat_type,
        channel="telegram",
    )
    
    # Also clear CLI chat context
    from ..claude.cli_agent import get_cli_agent, is_cli_available
    if is_cli_available():
        cli = get_cli_agent()
        cli.clear_user_chat(user_id)
    
    # Also clear conversation context
    context_mgr = get_context_manager()
    ctx = context_mgr.get_context(
        user_id=int(user_id),
        chat_id=int(chat_id),
        chat_type=chat_type_raw,
    )
    ctx.clear()
    
    # Handle model switch if specified
    model_msg = ""
    if args:
        model_name = args[0]
        from .handlers import set_user_chat_mode
        from ..core.llm_providers import get_llm_manager
        
        # Try to set model
        try:
            llm_mgr = get_llm_manager()
            available = llm_mgr.list_available_providers()
            
            # Check if it's a provider name
            provider_match = next(
                (p for p in available if p['name'].lower() == model_name.lower()),
                None
            )
            if provider_match:
                llm_mgr.set_user_model(user_id, provider_match['name'])
                model_msg = f"\n🤖 模型已切換為: {provider_match['name']}"
        except Exception as e:
            logger.warning(f"Failed to set model: {e}")
    
    await update.message.reply_text(
        f"🆕 <b>新對話已開始</b>\n\n"
        f"Session ID: <code>{session.session_id[:12]}...</code>\n"
        f"所有對話上下文已清除。{model_msg}\n\n"
        f"💡 現在可以開始全新的對話了！",
        parse_mode="HTML"
    )


@authorized_only
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /status command.
    Show current session status and system info.
    
    Similar to ClawdBot's /status command.
    """
    from datetime import datetime
    from html import escape
    
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    chat_type_raw = update.effective_chat.type
    
    # Map chat type
    if chat_type_raw == "private":
        chat_type = ChatType.DM
    elif chat_type_raw in ("group", "supergroup"):
        chat_type = ChatType.GROUP
    else:
        chat_type = ChatType.CHANNEL
    
    session_mgr = get_session_manager()
    
    # Get current session
    session = session_mgr.get_session(
        user_id=user_id,
        chat_id=chat_id,
        chat_type=chat_type,
        channel="telegram",
    )
    
    # Get current mode and model
    from .handlers import get_user_chat_mode
    from ..core.llm_providers import get_llm_manager
    
    current_mode = get_user_chat_mode(int(user_id))
    
    mode_names = {
        "auto": "🔄 自動選擇",
        "cli": "⌨️ Cursor CLI",
        "agent": "🤖 Agent Loop",
        "assistant": "👩‍💼 秘書模式",
        "cursor": "💻 Background Agent",
    }
    
    # Get model info
    llm_mgr = get_llm_manager()
    model_info = llm_mgr.get_user_model(user_id)
    
    # Get context info
    context_mgr = get_context_manager()
    ctx = context_mgr.get_context(
        user_id=int(user_id),
        chat_id=int(chat_id),
        chat_type=chat_type_raw,
    )
    
    # Calculate context usage
    context_tokens = ctx.estimate_tokens()
    max_tokens = 8000  # Approximate max context
    context_pct = min(100, int(context_tokens / max_tokens * 100))
    context_bar = "█" * (context_pct // 10) + "░" * (10 - context_pct // 10)
    
    # Check CLI status
    cli_status = "❌ 未安裝"
    from ..claude.cli_agent import is_cli_available, get_cli_agent
    if is_cli_available():
        cli = get_cli_agent()
        cli_chat = cli.get_user_chat_id(user_id)
        if cli_chat:
            cli_status = f"✅ 連線中 ({cli_chat[:8]}...)"
        else:
            cli_status = "✅ 可用"
    
    text = f"""📊 <b>狀態總覽</b>

━━━━━━━━━━━━━━━━━━━━━━
<b>對話模式</b>
━━━━━━━━━━━━━━━━━━━━━━
{mode_names.get(current_mode, current_mode)}
🤖 模型: {model_info or '預設'}
⌨️ CLI: {cli_status}

━━━━━━━━━━━━━━━━━━━━━━
<b>Session 狀態</b>
━━━━━━━━━━━━━━━━━━━━━━
🆔 {session.session_id[:12]}...
📨 訊息: {session.message_count}
🎫 Token: {session.total_tokens:,}

━━━━━━━━━━━━━━━━━━━━━━
<b>上下文使用量</b>
━━━━━━━━━━━━━━━━━━━━━━
[{context_bar}] {context_pct}%
約 {context_tokens:,} / {max_tokens:,} tokens
{f'⚠️ 建議使用 /compact 壓縮' if context_pct > 70 else ''}

━━━━━━━━━━━━━━━━━━━━━━
<b>快捷指令</b>
━━━━━━━━━━━━━━━━━━━━━━
/new - 開始新對話
/compact - 壓縮上下文
/mode - 切換模式
/model - 切換模型
"""
    await update.message.reply_text(text, parse_mode="HTML")


@authorized_only
async def compact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /compact command.
    Compress conversation context to free up space.
    
    Usage:
        /compact - Auto compress
        /compact <instructions> - Compress with specific focus
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    args = context.args or []
    
    # Get context
    context_mgr = get_context_manager()
    ctx = context_mgr.get_context(
        user_id=user_id,
        chat_id=chat_id,
        chat_type=chat_type,
    )
    
    # Check if compaction is needed
    before_tokens = ctx.estimate_tokens()
    before_messages = len(ctx.messages)
    
    if before_messages < 5:
        await update.message.reply_text(
            "ℹ️ 對話歷史太短，不需要壓縮。\n"
            f"目前只有 {before_messages} 條訊息。"
        )
        return
    
    # Send processing message
    status_msg = await update.message.reply_text("🔄 正在壓縮對話歷史...")
    
    try:
        # Perform compaction
        instructions = " ".join(args) if args else None
        
        # Use custom summarizer if instructions provided
        if instructions:
            async def custom_summarizer(messages):
                from ..core.llm_providers import get_llm_manager
                manager = get_llm_manager()
                
                conversation_text = "\n".join([
                    f"{m['role'].upper()}: {m['content'][:500]}"
                    for m in messages
                ])
                
                prompt = [
                    {
                        "role": "system",
                        "content": (
                            f"Summarize this conversation focusing on: {instructions}\n"
                            "Keep key decisions, code snippets, and important context."
                        )
                    },
                    {
                        "role": "user",
                        "content": conversation_text
                    }
                ]
                
                return await manager.generate(prompt, max_tokens=500)
            
            compacted = await ctx.compact(summarizer=custom_summarizer, force=True)
        else:
            compacted = await ctx.compact(force=True)
        
        after_tokens = ctx.estimate_tokens()
        after_messages = len(ctx.messages)
        
        # Update session stats
        session_mgr = get_session_manager()
        session_key = f"agent:default:telegram:dm:{user_id}" if chat_type == "private" else f"agent:default:telegram:group:{chat_id}"
        session = session_mgr.get_session_by_key(session_key)
        if session:
            session.compaction_count += 1
            session.context_tokens = after_tokens
        
        saved_tokens = before_tokens - after_tokens
        saved_messages = before_messages - after_messages
        
        await status_msg.edit_text(
            f"✅ <b>對話已壓縮</b>\n\n"
            f"📉 訊息: {before_messages} → {after_messages} (-{saved_messages})\n"
            f"🎫 Token: {before_tokens:,} → {after_tokens:,} (-{saved_tokens:,})\n"
            f"📊 節省: {int(saved_tokens / max(before_tokens, 1) * 100)}%\n\n"
            f"壓縮摘要已保存在上下文中。",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Compaction error: {e}")
        await status_msg.edit_text(f"❌ 壓縮失敗: {str(e)[:100]}")


# ============================================
# Skills Commands
# ============================================


@authorized_only
async def skills_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /skills command.
    List available skills (both command and agent skills).
    """
    skills = get_skill_manager()

    # Load built-in skills if not loaded
    if not skills.list_skills():
        await skills.load_builtin_skills()

    args = context.args if context.args else []
    
    # /skills agent - show agent skills
    if args and args[0] == "agent":
        agent_skills = skills.list_agent_skills()
        
        if not agent_skills:
            await update.message.reply_text("❌ 沒有可用的 Agent 技能")
            return
        
        text = "🤖 <b>Agent 技能</b>\n\n"
        text += "這些技能可在 /agent 指令中使用:\n\n"
        
        for skill in agent_skills:
            status = "✅" if skill.enabled else "❌"
            text += f"{status} <b>{skill.name}</b>\n"
            text += f"   {skill.description}\n"
            if skill.categories:
                text += f"   分類: {', '.join(skill.categories)}\n"
            if skill.examples:
                text += f"   範例: {skill.examples[0]}\n"
            text += "\n"
        
        await update.message.reply_text(text, parse_mode="HTML")
        return
    
    # Default: show command skills
    skill_list = skills.list_skills()
    agent_skills = skills.list_agent_skills()

    text = "🎯 <b>可用技能</b>\n\n"
    
    # Command skills
    if skill_list:
        text += "<b>📋 指令技能:</b>\n"
        for skill in skill_list:
            status = "✅" if skill.enabled else "❌"
            commands = ", ".join([f"/{c}" for c in skill.commands])
            text += f"{status} <b>{skill.name}</b>: {commands}\n"
        text += "\n"
    
    # Agent skills summary
    if agent_skills:
        text += f"<b>🤖 Agent 技能:</b> {len(agent_skills)} 個可用\n"
        text += "使用 <code>/skills agent</code> 查看詳情\n\n"
    
    text += "<b>使用說明:</b>\n"
    text += "• 指令技能: 直接使用 /指令 執行\n"
    text += "• Agent 技能: 透過 /agent 指令使用\n"

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


@authorized_only
async def agent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /agent command - Run Agent Loop for complex tasks.
    
    Usage: /agent <task description>
    """
    if not context.args:
        await update.message.reply_text(
            "🤖 <b>Agent Loop</b>\n\n"
            "使用方式: <code>/agent &lt;任務描述&gt;</code>\n\n"
            "範例:\n"
            "• <code>/agent 幫我分析這段程式碼的效能問題</code>\n"
            "• <code>/agent 建立一個完整的登入系統</code>\n"
            "• <code>/agent 重構這個模組並加入測試</code>\n\n"
            "切換模型: <code>/model set &lt;provider&gt;</code>",
            parse_mode="HTML",
        )
        return
    
    task = " ".join(context.args)
    user_id = str(update.effective_user.id)
    
    # Get current model info
    from ..core.llm_providers import get_llm_manager
    manager = get_llm_manager()
    current_model = manager.get_user_model(user_id)
    model_info = f"{current_model[0]}/{current_model[1]}" if current_model else "未設定"
    
    status_msg = await update.message.reply_text(
        f"🤖 <b>Agent Loop 啟動中...</b>\n\n"
        f"任務: {task[:100]}{'...' if len(task) > 100 else ''}\n"
        f"模型: <code>{model_info}</code>\n\n"
        f"⏳ Agent 正在分析任務...",
        parse_mode="HTML",
    )
    
    try:
        from ..core import get_agent_loop, AgentLoop
        from ..core.llm_providers import get_llm_manager
        import uuid
        
        # Get user's selected provider function
        manager = get_llm_manager()
        user_provider = manager.get_llm_provider_function_for_user(user_id)
        
        # Create agent with user's provider
        agent = get_agent_loop()
        
        # Temporarily use user's provider if set
        original_provider = agent.llm_provider
        if user_provider:
            agent.llm_provider = user_provider
        
        # Run the agent loop
        result = await agent.run(
            prompt=task,
            user_id=user_id,
            session_id=str(uuid.uuid4()),
            context={"source": "telegram", "command": "agent"},
        )
        
        # Restore original provider
        agent.llm_provider = original_provider
        
        # Format response based on AgentContext result
        if result.error:
            await status_msg.edit_text(
                f"❌ <b>Agent 執行失敗</b>\n\n{_escape_html(result.error)}",
                parse_mode="HTML",
            )
        elif result.final_response:
            response = _escape_html(result.final_response[:4000])
            await status_msg.edit_text(
                f"✅ <b>Agent 完成</b>\n\n"
                f"執行了 {result.step_count} 個步驟\n\n"
                f"{response}",
                parse_mode="HTML",
            )
        else:
            await status_msg.edit_text(
                f"✅ <b>Agent 完成</b>\n\n"
                f"執行了 {result.step_count} 個步驟",
                parse_mode="HTML",
            )
            
    except Exception as e:
        logger.error(f"Agent handler error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await status_msg.edit_text(
            f"❌ Agent 執行錯誤: {_escape_html(str(e)[:200])}",
            parse_mode="HTML",
        )


# ============================================
# Model Selection Commands
# ============================================

# Provider display names and emojis
_PROVIDER_NAMES = {
    "openai": "OpenAI",
    "google": "Google Gemini",
    "anthropic": "Anthropic Claude",
    "openrouter": "OpenRouter",
    "ollama": "Ollama (本地)",
    "custom": "自訂端點",
}

_PROVIDER_EMOJIS = {
    "openai": "🤖",
    "google": "🔷",
    "anthropic": "🟠",
    "openrouter": "🌐",
    "ollama": "🦙",
    "custom": "⚙️",
}


def _create_model_provider_view(
    models: dict,
    providers: list,
    current_provider: str = None,
    current_model: str = None,
) -> tuple[str, InlineKeyboardMarkup]:
    """Create provider selection view with model counts."""
    text = "📋 <b>選擇 AI 模型提供者</b>\n\n"
    text += "點擊下方按鈕選擇提供者，然後選擇模型。\n\n"
    
    total_models = 0
    for provider in providers:
        name = _PROVIDER_NAMES.get(provider, provider)
        emoji = _PROVIDER_EMOJIS.get(provider, "•")
        model_list = models.get(provider, [])
        count = len(model_list)
        total_models += count
        
        is_current = provider == current_provider
        marker = " ✓" if is_current else ""
        text += f"{emoji} <b>{name}</b>{marker} ({count} 個模型)\n"
    
    text += f"\n<b>共 {total_models} 個模型可用</b>\n"
    
    if current_provider and current_model:
        text += f"\n目前使用: <code>{current_provider}/{current_model}</code>"
    
    # Create provider buttons
    keyboard = []
    row = []
    for i, provider in enumerate(providers):
        emoji = _PROVIDER_EMOJIS.get(provider, "•")
        name = _PROVIDER_NAMES.get(provider, provider)
        is_current = provider == current_provider
        
        # Shorten name for button
        short_name = name.split()[0] if len(name) > 10 else name
        label = f"{emoji} {short_name}" + (" ✓" if is_current else "")
        
        row.append(InlineKeyboardButton(label, callback_data=f"model_provider:{provider}"))
        
        # 2 buttons per row
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Add refresh and close buttons
    keyboard.append([
        InlineKeyboardButton("🔄 重新整理", callback_data="model_refresh"),
        InlineKeyboardButton("❌ 關閉", callback_data="model_close"),
    ])
    
    return text, InlineKeyboardMarkup(keyboard)


def _create_model_list_view(
    provider: str,
    models: list,
    page: int = 0,
    page_size: int = 8,
    current_provider: str = None,
    current_model: str = None,
) -> tuple[str, InlineKeyboardMarkup]:
    """Create paginated model list view for a specific provider."""
    name = _PROVIDER_NAMES.get(provider, provider)
    emoji = _PROVIDER_EMOJIS.get(provider, "•")
    
    total = len(models)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    
    start = page * page_size
    end = min(start + page_size, total)
    page_models = models[start:end]
    
    text = f"{emoji} <b>{name} 模型</b>\n\n"
    text += f"共 {total} 個模型（第 {page + 1}/{total_pages} 頁）\n"
    text += "點擊按鈕切換模型：\n\n"
    
    # Create model buttons
    keyboard = []
    for model in page_models:
        is_current = provider == current_provider and model == current_model
        # Truncate long model names
        display_name = model if len(model) <= 35 else model[:32] + "..."
        label = f"{'✓ ' if is_current else ''}{display_name}"
        
        # Encode model in callback data (URL-safe)
        callback_data = f"model_set:{provider}:{model}"
        
        # Telegram callback_data limit is 64 bytes
        if len(callback_data.encode('utf-8')) > 64:
            # Use index instead
            callback_data = f"model_idx:{provider}:{page}:{page_models.index(model)}"
        
        keyboard.append([InlineKeyboardButton(label, callback_data=callback_data)])
    
    # Navigation buttons
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ 上一頁", callback_data=f"model_page:{provider}:{page - 1}"))
    
    nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="model_noop"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("下一頁 ▶️", callback_data=f"model_page:{provider}:{page + 1}"))
    
    keyboard.append(nav_row)
    
    # Back and close buttons
    keyboard.append([
        InlineKeyboardButton("⬅️ 返回提供者", callback_data="model_back"),
        InlineKeyboardButton("❌ 關閉", callback_data="model_close"),
    ])
    
    return text, InlineKeyboardMarkup(keyboard)


@authorized_only
async def model_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /model command.
    List available models and switch between them.
    
    Usage:
        /model - Show current model and available options
        /model list - List all available providers and models
        /model set <provider> [model] - Set model for this user
        /model reset - Reset to default model
    """
    from ..core.llm_providers import get_llm_manager
    
    user_id = str(update.effective_user.id)
    args = context.args or []
    manager = get_llm_manager()
    
    if not args or args[0] == "status":
        # Show current status
        status = manager.get_current_status(user_id)
        
        if not status["available_providers"]:
            await update.message.reply_text(
                "❌ <b>沒有可用的 AI 模型</b>\n\n"
                "請在 .env 中設定至少一個提供者的 API Key：\n"
                "• OPENAI_API_KEY\n"
                "• GOOGLE_GENERATIVE_AI_API_KEY\n"
                "• ANTHROPIC_API_KEY\n"
                "• OPENROUTER_API_KEY\n"
                "• OLLAMA_ENABLED=true",
                parse_mode="HTML",
            )
            return
        
        # Build status message
        current = f"{status['current_provider']}/{status['current_model']}" if status["current_provider"] else "未設定"
        selection_type = "（自選）" if status["is_user_selection"] else "（預設）"
        
        text = f"🤖 <b>AI 模型狀態</b>\n\n"
        text += f"<b>目前使用：</b> <code>{current}</code> {selection_type}\n\n"
        text += f"<b>可用提供者：</b>\n"
        
        provider_icons = {
            "openai": "🟢",
            "google": "🔵",
            "anthropic": "🟠",
            "openrouter": "🟣",
            "ollama": "⚪",
            "custom": "⚙️",
        }
        
        for provider in status["available_providers"]:
            icon = provider_icons.get(provider, "•")
            models = status["available_models"].get(provider, [])
            model_preview = ", ".join(models[:3])
            if len(models) > 3:
                model_preview += f" (+{len(models)-3})"
            text += f"{icon} <b>{provider}</b>: {model_preview}\n"
        
        text += "\n<b>指令：</b>\n"
        text += "• <code>/model list</code> - 顯示所有模型\n"
        text += "• <code>/model set &lt;provider&gt; [model]</code> - 切換模型\n"
        text += "• <code>/model reset</code> - 恢復預設\n"
        
        await update.message.reply_text(text, parse_mode="HTML")
        return
    
    elif args[0] == "list":
        # List all models with interactive buttons
        status = manager.get_current_status(user_id)
        
        if not status["available_providers"]:
            await update.message.reply_text("❌ 沒有可用的 AI 模型")
            return
        
        # Send loading message
        loading_msg = await update.message.reply_text(
            "🔄 <b>正在從各提供者獲取可用模型...</b>",
            parse_mode="HTML",
        )
        
        # Fetch models from APIs
        try:
            fetched_models = await manager.fetch_all_models(max_per_provider=50)
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            fetched_models = status["available_models"]
        
        # Cache the fetched models in context for pagination
        context.user_data["model_list_cache"] = fetched_models
        context.user_data["model_list_providers"] = status["available_providers"]
        
        # Show provider selection first
        text, keyboard = _create_model_provider_view(
            fetched_models, 
            status["available_providers"],
            status.get("current_provider"),
            status.get("current_model"),
        )
        
        await loading_msg.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    elif args[0] == "set" and len(args) >= 2:
        # Set model
        provider = args[1].lower()
        model = args[2] if len(args) >= 3 else None
        
        if manager.set_user_model(user_id, provider, model):
            current = manager.get_user_model(user_id)
            if current:
                await update.message.reply_text(
                    f"✅ <b>已切換 AI 模型</b>\n\n"
                    f"提供者：<code>{current[0]}</code>\n"
                    f"模型：<code>{current[1]}</code>",
                    parse_mode="HTML",
                )
            else:
                await update.message.reply_text("✅ 模型已設定")
        else:
            available = manager.list_available_providers()
            await update.message.reply_text(
                f"❌ 無效的提供者：<code>{provider}</code>\n\n"
                f"可用的提供者：{', '.join(available)}",
                parse_mode="HTML",
            )
        return
    
    elif args[0] == "reset":
        # Reset to default
        manager.clear_user_model(user_id)
        status = manager.get_current_status(user_id)
        
        current = f"{status['current_provider']}/{status['current_model']}" if status["current_provider"] else "未設定"
        
        await update.message.reply_text(
            f"🔄 <b>已恢復預設模型</b>\n\n"
            f"目前使用：<code>{current}</code>",
            parse_mode="HTML",
        )
        return
    
    else:
        await update.message.reply_text(
            "❓ <b>模型指令用法</b>\n\n"
            "• <code>/model</code> - 查看目前狀態\n"
            "• <code>/model list</code> - 列出所有模型\n"
            "• <code>/model set &lt;provider&gt; [model]</code> - 切換模型\n"
            "• <code>/model reset</code> - 恢復預設\n\n"
            "<b>範例：</b>\n"
            "<code>/model set openai gpt-4o</code>\n"
            "<code>/model set anthropic</code>\n"
            "<code>/model set ollama llama3.2</code>",
            parse_mode="HTML",
        )


@authorized_only
async def model_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle model selection callbacks from inline keyboard.
    """
    from ..core.llm_providers import get_llm_manager
    
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    manager = get_llm_manager()
    
    # Get cached models from context
    cached_models = context.user_data.get("model_list_cache", {})
    providers = context.user_data.get("model_list_providers", [])
    
    # Get current selection
    status = manager.get_current_status(user_id)
    current_provider = status.get("current_provider")
    current_model = status.get("current_model")
    
    if data == "model_close":
        await query.message.delete()
        return
    
    elif data == "model_noop":
        # Do nothing (page indicator button)
        return
    
    elif data == "model_refresh":
        # Refresh model list
        await query.message.edit_text(
            "🔄 <b>正在重新獲取模型列表...</b>",
            parse_mode="HTML",
        )
        
        try:
            fetched_models = await manager.fetch_all_models(max_per_provider=50)
            context.user_data["model_list_cache"] = fetched_models
            providers = manager.list_available_providers()
            context.user_data["model_list_providers"] = providers
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            fetched_models = manager.list_available_models()
            context.user_data["model_list_cache"] = fetched_models
        
        status = manager.get_current_status(user_id)
        text, keyboard = _create_model_provider_view(
            fetched_models,
            providers,
            status.get("current_provider"),
            status.get("current_model"),
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    elif data == "model_back":
        # Go back to provider view
        if not cached_models:
            cached_models = manager.list_available_models()
        if not providers:
            providers = manager.list_available_providers()
        
        text, keyboard = _create_model_provider_view(
            cached_models,
            providers,
            current_provider,
            current_model,
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    elif data.startswith("model_provider:"):
        # Show models for selected provider
        provider = data.split(":", 1)[1]
        
        if not cached_models:
            # Fetch if not cached
            await query.message.edit_text(
                "🔄 <b>正在獲取模型列表...</b>",
                parse_mode="HTML",
            )
            try:
                cached_models = await manager.fetch_all_models(max_per_provider=50)
                context.user_data["model_list_cache"] = cached_models
            except Exception:
                cached_models = manager.list_available_models()
        
        models = cached_models.get(provider, [])
        
        if not models:
            await query.answer("此提供者沒有可用模型", show_alert=True)
            return
        
        text, keyboard = _create_model_list_view(
            provider,
            models,
            page=0,
            current_provider=current_provider,
            current_model=current_model,
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    elif data.startswith("model_page:"):
        # Handle pagination
        parts = data.split(":")
        provider = parts[1]
        page = int(parts[2])
        
        models = cached_models.get(provider, [])
        
        text, keyboard = _create_model_list_view(
            provider,
            models,
            page=page,
            current_provider=current_provider,
            current_model=current_model,
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    elif data.startswith("model_set:"):
        # Set model directly
        parts = data.split(":", 2)
        provider = parts[1]
        model = parts[2] if len(parts) > 2 else None
        
        if manager.set_user_model(user_id, provider, model):
            current = manager.get_user_model(user_id)
            status = manager.get_current_status(user_id)
            
            # Update the view to show new selection
            models = cached_models.get(provider, [])
            page = 0
            
            # Find current page
            if model and model in models:
                idx = models.index(model)
                page = idx // 8
            
            text, keyboard = _create_model_list_view(
                provider,
                models,
                page=page,
                current_provider=status.get("current_provider"),
                current_model=status.get("current_model"),
            )
            
            # Add success message
            success_text = f"✅ 已切換至 <code>{provider}/{model}</code>\n\n" + text
            
            try:
                await query.message.edit_text(success_text, parse_mode="HTML", reply_markup=keyboard)
            except BadRequest as e:
                if "message is not modified" in str(e).lower():
                    pass  # Ignore - content unchanged
                else:
                    raise
            await query.answer("✅ 模型已切換")
        else:
            await query.answer("❌ 切換失敗", show_alert=True)
        return
    
    elif data.startswith("model_idx:"):
        # Set model by index (for long model names)
        parts = data.split(":")
        provider = parts[1]
        page = int(parts[2])
        idx = int(parts[3])
        
        models = cached_models.get(provider, [])
        page_size = 8
        model_idx = page * page_size + idx
        
        if 0 <= model_idx < len(models):
            model = models[model_idx]
            
            if manager.set_user_model(user_id, provider, model):
                status = manager.get_current_status(user_id)
                
                text, keyboard = _create_model_list_view(
                    provider,
                    models,
                    page=page,
                    current_provider=status.get("current_provider"),
                    current_model=status.get("current_model"),
                )
                
                success_text = f"✅ 已切換至 <code>{provider}/{model}</code>\n\n" + text
                await query.message.edit_text(success_text, parse_mode="HTML", reply_markup=keyboard)
                await query.answer("✅ 模型已切換")
            else:
                await query.answer("❌ 切換失敗", show_alert=True)
        return
    
    else:
        logger.warning(f"Unknown model callback: {data}")


# ============================================
# CLI Model Management
# ============================================


@authorized_only
async def climodel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /climodel command.
    Manage Cursor CLI model selection.
    
    Usage:
        /climodel - Show current CLI model and available options
        /climodel list - List all available CLI models
        /climodel set <model_id> - Set CLI model for this user
        /climodel reset - Reset to CLI default model
    """
    from ..claude.cli_agent import get_cli_agent, is_cli_available
    
    if not is_cli_available():
        await update.message.reply_text(
            "❌ <b>Cursor CLI 未安裝</b>\n\n"
            "請先安裝 Cursor CLI：\n"
            "<code>curl https://cursor.com/install -fsS | bash</code>",
            parse_mode="HTML",
        )
        return
    
    user_id = str(update.effective_user.id)
    args = context.args or []
    cli = get_cli_agent()
    
    if not args or args[0] == "status":
        # Show current status
        current_model = cli.get_user_model(user_id) or "auto (預設)"
        
        # Fetch models if not cached
        if not cli._models_fetched:
            loading_msg = await update.message.reply_text("🔄 正在獲取 CLI 模型列表...")
            models = await cli.list_models()
            await loading_msg.delete()
        else:
            models = cli._available_models
        
        text = "🖥️ <b>Cursor CLI 模型設定</b>\n\n"
        text += f"<b>目前使用：</b> <code>{current_model}</code>\n\n"
        
        if models:
            # Find current/default model
            current_default = [m for m in models if m.get("current") or m.get("default")]
            if current_default:
                text += f"<b>CLI 預設：</b> <code>{current_default[0]['id']}</code>\n\n"
            
            text += f"<b>可用模型：</b> {len(models)} 個\n"
            
            # Show top models
            top_models = models[:8]
            for m in top_models:
                flags = []
                if m.get("current"):
                    flags.append("當前")
                if m.get("default"):
                    flags.append("預設")
                flag_str = f" ({', '.join(flags)})" if flags else ""
                text += f"• <code>{m['id']}</code> - {m['name']}{flag_str}\n"
            
            if len(models) > 8:
                text += f"... 還有 {len(models) - 8} 個模型\n"
        
        text += "\n<b>指令：</b>\n"
        text += "• <code>/climodel list</code> - 顯示所有模型\n"
        text += "• <code>/climodel set &lt;model_id&gt;</code> - 切換模型\n"
        text += "• <code>/climodel reset</code> - 恢復預設\n"
        
        # Build keyboard
        keyboard = []
        if models:
            # Add quick model buttons (top 6)
            row = []
            for m in models[:6]:
                row.append(InlineKeyboardButton(
                    f"{'✓ ' if m['id'] == cli.get_user_model(user_id) else ''}{m['id'][:12]}",
                    callback_data=f"climodel_set:{m['id']}"
                ))
                if len(row) >= 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("📋 所有模型", callback_data="climodel_list:0"),
            InlineKeyboardButton("🔄 重置", callback_data="climodel_reset"),
        ])
        
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return
    
    elif args[0] == "list":
        # List all models
        loading_msg = await update.message.reply_text("🔄 正在獲取 CLI 模型列表...")
        models = await cli.list_models(force_refresh=True)
        await loading_msg.delete()
        
        if not models:
            await update.message.reply_text("❌ 無法獲取 CLI 模型列表")
            return
        
        # Store in context for pagination
        context.user_data["climodel_list"] = models
        
        text, keyboard = _create_climodel_list_view(models, 0, cli.get_user_model(user_id))
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    elif args[0] == "set":
        if len(args) < 2:
            await update.message.reply_text(
                "❌ 請指定模型 ID\n\n"
                "用法: <code>/climodel set &lt;model_id&gt;</code>\n"
                "例如: <code>/climodel set sonnet-4.5</code>",
                parse_mode="HTML",
            )
            return
        
        model_id = args[1].lower()
        
        # Verify model exists
        models = await cli.list_models()
        valid_ids = [m['id'].lower() for m in models]
        
        # Try exact match first, then prefix match
        matched_model = None
        for m in models:
            if m['id'].lower() == model_id:
                matched_model = m['id']
                break
        
        if not matched_model:
            # Try prefix match
            for m in models:
                if m['id'].lower().startswith(model_id):
                    matched_model = m['id']
                    break
        
        if not matched_model:
            await update.message.reply_text(
                f"❌ 找不到模型: <code>{model_id}</code>\n\n"
                f"使用 <code>/climodel list</code> 查看可用模型",
                parse_mode="HTML",
            )
            return
        
        cli.set_user_model(user_id, matched_model)
        
        await update.message.reply_text(
            f"✅ <b>CLI 模型已切換</b>\n\n"
            f"<code>{matched_model}</code>\n\n"
            f"下次 CLI 對話將使用此模型。",
            parse_mode="HTML",
        )
        return
    
    elif args[0] == "reset":
        if cli.clear_user_model(user_id):
            await update.message.reply_text(
                "✅ <b>已恢復 CLI 預設模型</b>\n\n"
                "將使用 Cursor CLI 的預設模型設定。",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text("ℹ️ 目前已經是使用預設模型")
        return
    
    else:
        await update.message.reply_text(
            "❌ 未知指令\n\n"
            "使用 <code>/climodel</code> 查看說明",
            parse_mode="HTML",
        )


def _create_climodel_list_view(
    models: list[dict],
    page: int,
    current_model: str = None,
) -> tuple[str, InlineKeyboardMarkup]:
    """Create CLI model list view with pagination."""
    page_size = 10
    total_pages = max(1, (len(models) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    
    start = page * page_size
    end = min(start + page_size, len(models))
    page_models = models[start:end]
    
    text = f"🖥️ <b>Cursor CLI 可用模型</b> ({page + 1}/{total_pages})\n\n"
    
    for m in page_models:
        flags = []
        if m.get("current"):
            flags.append("🔵當前")
        if m.get("default"):
            flags.append("⭐預設")
        if current_model and m['id'] == current_model:
            flags.append("✓選中")
        
        flag_str = f" ({', '.join(flags)})" if flags else ""
        text += f"• <code>{m['id']}</code> - {m['name']}{flag_str}\n"
    
    # Build keyboard with model selection buttons
    keyboard = []
    row = []
    for i, m in enumerate(page_models):
        prefix = "✓ " if current_model and m['id'] == current_model else ""
        row.append(InlineKeyboardButton(
            f"{prefix}{m['id'][:12]}",
            callback_data=f"climodel_set:{m['id']}"
        ))
        if len(row) >= 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Navigation buttons
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ 上一頁", callback_data=f"climodel_list:{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("➡️ 下一頁", callback_data=f"climodel_list:{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([
        InlineKeyboardButton("🔄 重置", callback_data="climodel_reset"),
        InlineKeyboardButton("❌ 關閉", callback_data="climodel_close"),
    ])
    
    return text, InlineKeyboardMarkup(keyboard)


@authorized_only
async def climodel_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle CLI model callback queries."""
    from ..claude.cli_agent import get_cli_agent
    
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    cli = get_cli_agent()
    
    if data.startswith("climodel_set:"):
        model_id = data.split(":", 1)[1]
        cli.set_user_model(user_id, model_id)
        
        # Refresh view
        models = cli._available_models or await cli.list_models()
        page = context.user_data.get("climodel_page", 0)
        text, keyboard = _create_climodel_list_view(models, page, model_id)
        
        success_text = f"✅ 已切換至 <code>{model_id}</code>\n\n" + text
        try:
            await query.message.edit_text(success_text, parse_mode="HTML", reply_markup=keyboard)
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
    
    elif data.startswith("climodel_list:"):
        page = int(data.split(":")[1])
        context.user_data["climodel_page"] = page
        
        models = context.user_data.get("climodel_list") or cli._available_models
        if not models:
            models = await cli.list_models()
            context.user_data["climodel_list"] = models
        
        text, keyboard = _create_climodel_list_view(models, page, cli.get_user_model(user_id))
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    
    elif data == "climodel_reset":
        cli.clear_user_model(user_id)
        
        models = cli._available_models or await cli.list_models()
        page = context.user_data.get("climodel_page", 0)
        text, keyboard = _create_climodel_list_view(models, page, None)
        
        success_text = "✅ 已恢復預設模型\n\n" + text
        await query.message.edit_text(success_text, parse_mode="HTML", reply_markup=keyboard)
    
    elif data == "climodel_close":
        await query.message.delete()


# ============================================
# Doctor - System Diagnostics
# ============================================


@authorized_only
async def doctor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /doctor command.
    Run system diagnostics.
    
    Usage:
        /doctor - Run full diagnostics
        /doctor quick - Quick health check
    """
    args = context.args or []
    
    await update.message.reply_text("🩺 正在執行系統診斷...")
    
    try:
        from ..core.doctor import get_doctor
        doctor = get_doctor()
        
        if args and args[0] == "quick":
            # Quick check
            results = []
            for name in ["python_version", "telegram_config", "llm_providers"]:
                result = await doctor.run_check(name)
                if result:
                    icon = {"ok": "✅", "warning": "⚠️", "error": "❌", "critical": "☠️", "info": "ℹ️"}
                    results.append(f"{icon.get(result.level.value, '•')} {result.name}: {result.message}")
            
            text = "🩺 <b>快速診斷結果</b>\n\n" + "\n".join(results)
        else:
            # Full diagnostics
            report = await doctor.run_all_checks()
            
            # Format report
            lines = [
                f"🩺 <b>系統診斷報告</b>",
                f"📅 {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                f"📊 整體狀態: <b>{report.overall_status.value.upper()}</b>",
                "",
            ]
            
            # Group by level
            for level_name, icon in [("critical", "☠️"), ("error", "❌"), ("warning", "⚠️"), ("ok", "✅")]:
                level_results = [r for r in report.results if r.level.value == level_name]
                if level_results:
                    for r in level_results[:5]:  # Limit to 5 per level
                        lines.append(f"{icon} <b>{r.name}</b>: {r.message}")
                        if r.recommendation:
                            lines.append(f"   → {r.recommendation}")
            
            # Summary
            lines.append("")
            lines.append(f"📈 <b>統計</b>: {report.summary.get('ok', 0)} 通過 / "
                        f"{report.summary.get('warnings', 0)} 警告 / "
                        f"{report.summary.get('errors', 0)} 錯誤")
            
            text = "\n".join(lines)
        
        await update.message.reply_text(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Doctor error: {e}")
        await update.message.reply_text(f"❌ 診斷失敗: {e}")


# ============================================
# Sessions - Session Management
# ============================================


@authorized_only
async def sessions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /sessions command.
    Manage conversation sessions.
    
    Usage:
        /sessions - Show session stats
        /sessions list - List active sessions
        /sessions prune - Clean expired sessions
        /sessions clear - Clear all sessions
    """
    args = context.args or []
    ctx_manager = get_context_manager()
    
    if not args or args[0] == "stats":
        # Show stats
        stats = ctx_manager.get_session_stats()
        
        text = f"""📊 <b>會話統計</b>

• 總會話數: <b>{stats['total_sessions']}</b>
• 總訊息數: <b>{stats['total_messages']}</b>
• 平均訊息/會話: <b>{stats['avg_messages_per_session']:.1f}</b>

<b>按類型:</b>
"""
        for ct, count in stats.get("by_chat_type", {}).items():
            text += f"  • {ct}: {count}\n"
        
        text += "\n<b>按狀態:</b>\n"
        for status, count in stats.get("by_status", {}).items():
            text += f"  • {status}: {count}\n"
        
        if stats.get("oldest_session"):
            text += f"\n🕐 最舊會話: {stats['oldest_session']['age_minutes']:.0f} 分鐘前"
        
        await update.message.reply_text(text, parse_mode="HTML")
        
    elif args[0] == "list":
        # List sessions
        contexts = list(ctx_manager._contexts.items())[:10]
        
        if not contexts:
            await update.message.reply_text("📭 目前沒有活躍會話")
            return
        
        lines = ["📋 <b>活躍會話</b> (前 10 個)\n"]
        for key, ctx in contexts:
            status = "🔴 過期" if ctx.is_expired else "🟢 活躍"
            lines.append(f"• <code>{key}</code> {status}")
            lines.append(f"  訊息: {len(ctx.messages)} | 類型: {ctx.chat_type}")
        
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
    elif args[0] == "prune":
        # Prune expired sessions
        result = ctx_manager.prune_expired_sessions()
        
        await update.message.reply_text(
            f"🧹 <b>會話清理完成</b>\n\n"
            f"• 已清理: <b>{result['pruned_count']}</b> 個會話\n"
            f"• 剩餘: <b>{result['remaining_count']}</b> 個會話",
            parse_mode="HTML"
        )
        
    elif args[0] == "clear":
        # Clear all sessions (admin only)
        ctx_manager._contexts.clear()
        await update.message.reply_text("🗑️ 已清除所有會話")
        
    else:
        await update.message.reply_text(
            "📖 <b>會話管理</b>\n\n"
            "<code>/sessions</code> - 顯示統計\n"
            "<code>/sessions list</code> - 列出會話\n"
            "<code>/sessions prune</code> - 清理過期\n"
            "<code>/sessions clear</code> - 清除全部",
            parse_mode="HTML"
        )


# ============================================
# Patch - Git Patch Management
# ============================================


@authorized_only
async def patch_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /patch command.
    Manage Git patches.
    
    Usage:
        /patch - Show patch help
        /patch create - Create patch from changes
        /patch list - List patch history
        /patch apply <content> - Apply a patch
    """
    args = context.args or []
    
    try:
        from ..core.patch import get_patch_manager
        pm = get_patch_manager()
        
        if not args:
            await update.message.reply_text(
                "📝 <b>補丁管理</b>\n\n"
                "<code>/patch create</code> - 從當前變更建立補丁\n"
                "<code>/patch create --staged</code> - 從暫存區建立\n"
                "<code>/patch list</code> - 顯示補丁歷史\n"
                "<code>/patch stats</code> - 顯示統計\n"
                "<code>/patch check</code> - 檢查補丁（回覆補丁內容）",
                parse_mode="HTML"
            )
            return
        
        if args[0] == "create":
            staged = "--staged" in args
            patch_content = await pm.create_patch(staged=staged)
            
            if patch_content:
                # Truncate if too long
                if len(patch_content) > 3500:
                    patch_content = patch_content[:3500] + "\n... (已截斷)"
                
                await update.message.reply_text(
                    f"📝 <b>已建立補丁</b>\n\n<pre>{patch_content}</pre>",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("📭 沒有變更可建立補丁")
        
        elif args[0] == "list":
            history = pm.get_history(limit=10)
            
            if not history:
                await update.message.reply_text("📭 沒有補丁歷史")
                return
            
            lines = ["📋 <b>補丁歷史</b>\n"]
            for p in history:
                status_icon = {"applied": "✅", "failed": "❌", "reverted": "↩️", "pending": "⏳"}
                lines.append(f"• <code>{p['id']}</code> {status_icon.get(p['status'], '•')} {p['status']}")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif args[0] == "stats":
            stats = pm.get_stats()
            await update.message.reply_text(
                f"📊 <b>補丁統計</b>\n\n"
                f"• 總數: {stats['total_patches']}\n"
                f"• 已套用: {stats['applied']}\n"
                f"• 失敗: {stats['failed']}\n"
                f"• 已還原: {stats['reverted']}",
                parse_mode="HTML"
            )
        
        elif args[0] == "check":
            # Check if replying to a message with patch content
            if update.message.reply_to_message:
                patch_content = update.message.reply_to_message.text
                result = await pm.check_patch(patch_content)
                
                if result.success:
                    await update.message.reply_text(
                        f"✅ 補丁可套用\n\n"
                        f"影響檔案: {len(result.affected_files)}\n"
                        f"新增: +{result.diff_stats.get('additions', 0)}\n"
                        f"刪除: -{result.diff_stats.get('deletions', 0)}"
                    )
                else:
                    await update.message.reply_text(f"❌ 補丁無法套用: {result.error}")
            else:
                await update.message.reply_text("請回覆包含補丁內容的訊息")
        
        else:
            await update.message.reply_text("❓ 未知的子命令，使用 /patch 查看說明")
            
    except Exception as e:
        logger.error(f"Patch error: {e}")
        await update.message.reply_text(f"❌ 補丁操作失敗: {e}")


# ============================================
# Policy - Tool Policy Management
# ============================================


@authorized_only
async def policy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /policy command.
    Manage tool access policies.
    
    Usage:
        /policy - Show policy status
        /policy list - List all policies
        /policy audit - Show audit log
        /policy set <tool> <on|off> - Enable/disable tool
    """
    args = context.args or []
    
    try:
        from ..core.tool_policy import get_tool_policy_manager
        pm = get_tool_policy_manager()
        
        if not args or args[0] == "status":
            stats = pm.get_stats()
            
            await update.message.reply_text(
                f"🔒 <b>工具策略狀態</b>\n\n"
                f"• 全域啟用: {'✅ 是' if stats['global_enabled'] else '❌ 否'}\n"
                f"• 策略總數: {stats['total_policies']}\n"
                f"• 已啟用: {stats['enabled_policies']}\n"
                f"• 管理員數: {stats['admin_users']}\n"
                f"• 審計記錄: {stats['audit_log_entries']}",
                parse_mode="HTML"
            )
        
        elif args[0] == "list":
            policies = pm.get_all_policies()
            
            if not policies:
                await update.message.reply_text("📭 沒有設定任何策略")
                return
            
            lines = ["📋 <b>工具策略清單</b>\n"]
            for p in policies:
                status = "✅" if p['enabled'] else "❌"
                lines.append(f"• {status} <code>{p['tool_name']}</code> [{p['permission_level']}]")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif args[0] == "audit":
            entries = pm.get_audit_log(limit=10)
            
            if not entries:
                await update.message.reply_text("📭 沒有審計記錄")
                return
            
            lines = ["📋 <b>審計日誌</b> (最近 10 筆)\n"]
            for e in entries:
                icon = "✅" if e['allowed'] else "❌"
                lines.append(f"• {icon} {e['tool_name']} - {e['action']} (用戶 {e['user_id']})")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif args[0] == "set" and len(args) >= 3:
            tool_name = args[1]
            action = args[2].lower()
            
            from ..core.tool_policy import ToolPolicy
            
            if action in ("on", "enable", "1"):
                policy = pm.get_policy(tool_name) or ToolPolicy(tool_name=tool_name)
                policy.enabled = True
                pm.set_policy(policy)
                await update.message.reply_text(f"✅ 已啟用工具: {tool_name}")
            elif action in ("off", "disable", "0"):
                policy = pm.get_policy(tool_name) or ToolPolicy(tool_name=tool_name)
                policy.enabled = False
                pm.set_policy(policy)
                await update.message.reply_text(f"❌ 已停用工具: {tool_name}")
            else:
                await update.message.reply_text("❓ 請使用 on 或 off")
        
        else:
            await update.message.reply_text(
                "🔒 <b>工具策略管理</b>\n\n"
                "<code>/policy</code> - 顯示狀態\n"
                "<code>/policy list</code> - 列出策略\n"
                "<code>/policy audit</code> - 審計日誌\n"
                "<code>/policy set &lt;tool&gt; on|off</code> - 啟用/停用",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Policy error: {e}")
        await update.message.reply_text(f"❌ 策略操作失敗: {e}")


# ============================================
# TTS - Text to Speech
# ============================================


@authorized_only
async def tts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tts command.
    Convert text to speech.
    
    Usage:
        /tts <text> - Convert text to speech
        /tts providers - List available providers
    """
    args = context.args or []
    
    if not args:
        await update.message.reply_text(
            "🔊 <b>語音合成</b>\n\n"
            "<code>/tts &lt;文字&gt;</code> - 將文字轉為語音\n"
            "<code>/tts providers</code> - 查看可用服務\n\n"
            "或直接回覆訊息使用 /tts",
            parse_mode="HTML"
        )
        return
    
    if args[0] == "providers":
        from ..core.tts import TTSProvider
        providers = [p.value for p in TTSProvider]
        await update.message.reply_text(
            f"🔊 <b>可用 TTS 服務</b>\n\n" +
            "\n".join(f"• {p}" for p in providers),
            parse_mode="HTML"
        )
        return
    
    # Get text to convert
    text = " ".join(args)
    if not text and update.message.reply_to_message:
        text = update.message.reply_to_message.text
    
    if not text:
        await update.message.reply_text("請提供要轉換的文字")
        return
    
    try:
        from ..core.tts import text_to_speech
        
        await update.message.reply_text("🔊 正在合成語音...")
        
        result = await text_to_speech(text)
        
        if result.success and result.audio_data:
            from io import BytesIO
            audio_file = BytesIO(result.audio_data)
            audio_file.name = "speech.mp3"
            
            await update.message.reply_voice(
                voice=audio_file,
                caption=f"🔊 TTS ({result.provider})"
            )
        else:
            await update.message.reply_text(f"❌ 語音合成失敗: {result.error}")
            
    except Exception as e:
        logger.error(f"TTS error: {e}")
        await update.message.reply_text(f"❌ TTS 錯誤: {e}")


# ============================================
# Broadcast - Send message to all users
# ============================================


@authorized_only
async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /broadcast command.
    Send message to all allowed users.
    
    Usage:
        /broadcast <message> - Send message to all users
    """
    args = context.args or []
    
    if not args:
        await update.message.reply_text(
            "📢 <b>廣播訊息</b>\n\n"
            "<code>/broadcast &lt;訊息&gt;</code> - 發送訊息給所有用戶",
            parse_mode="HTML"
        )
        return
    
    message = " ".join(args)
    
    try:
        from ..utils.config import settings
        
        allowed_users = settings.telegram_allowed_users
        if not allowed_users:
            await update.message.reply_text("❌ 沒有設定允許的用戶")
            return
        
        await update.message.reply_text(f"📢 正在廣播訊息給 {len(allowed_users)} 位用戶...")
        
        success_count = 0
        failed_count = 0
        
        for user_id in allowed_users:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 <b>系統廣播</b>\n\n{message}",
                    parse_mode="HTML"
                )
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to send broadcast to {user_id}: {e}")
                failed_count += 1
        
        await update.message.reply_text(
            f"📢 <b>廣播完成</b>\n\n"
            f"✅ 成功: {success_count}\n"
            f"❌ 失敗: {failed_count}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await update.message.reply_text(f"❌ 廣播失敗: {e}")


# ============================================
# Usage - Show usage statistics
# ============================================


@authorized_only
async def usage_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /usage command.
    Show usage statistics.
    
    Usage:
        /usage - Show usage stats
        /usage me - Show my usage
    """
    args = context.args or []
    user_id = update.effective_user.id
    
    try:
        from ..core.llm_providers import get_llm_manager
        manager = get_llm_manager()
        stats = manager.get_usage_stats()
        
        if args and args[0] == "me":
            # Show user's usage
            user_calls = stats.get("by_user", {}).get(user_id, 0)
            await update.message.reply_text(
                f"📊 <b>我的使用統計</b>\n\n"
                f"API 呼叫次數: <b>{user_calls}</b>",
                parse_mode="HTML"
            )
        else:
            # Show overall stats
            text = f"""📊 <b>使用統計</b>

總 API 呼叫: <b>{stats.get('total_calls', 0)}</b>

<b>按提供者:</b>
"""
            for provider, count in stats.get('by_provider', {}).items():
                text += f"  • {provider}: {count}\n"
            
            text += "\n<b>前 5 名用戶:</b>\n"
            sorted_users = sorted(
                stats.get('by_user', {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            for uid, count in sorted_users:
                text += f"  • 用戶 {uid}: {count}\n"
            
            await update.message.reply_text(text, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Usage error: {e}")
        await update.message.reply_text(f"❌ 無法取得使用統計: {e}")


# ============================================
# Permissions - Manage permissions
# ============================================


@authorized_only
async def permissions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /permissions command.
    Manage user and group permissions.
    
    Usage:
        /permissions - Show permission status
        /permissions user <id> - Show user permissions
        /permissions group - Show group settings
        /permissions admin add <id> - Add group admin
        /permissions whitelist add <id> - Add to whitelist
    """
    args = context.args or []
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    try:
        from ..core.permissions import get_permission_manager, Role
        pm = get_permission_manager()
        
        if not args:
            # Show overall stats
            stats = pm.get_stats()
            await update.message.reply_text(
                f"🔐 <b>權限系統狀態</b>\n\n"
                f"• 全域管理員: {stats['global_admins']}\n"
                f"• 全域黑名單: {stats['global_blacklist']}\n"
                f"• 已設定用戶: {stats['users_with_permissions']}\n"
                f"• 已設定群組: {stats['groups_configured']}\n"
                f"• 提升中用戶: {stats['elevated_users']}",
                parse_mode="HTML"
            )
            return
        
        if args[0] == "user" and len(args) >= 2:
            # Show user permissions
            target_id = int(args[1])
            perms = pm.get_user_permissions(target_id)
            
            await update.message.reply_text(
                f"👤 <b>用戶權限</b> ({target_id})\n\n"
                f"• 角色: {perms.role.value}\n"
                f"• 全域管理員: {'是' if pm.is_global_admin(target_id) else '否'}\n"
                f"• 提升中: {'是' if pm.is_elevated(target_id) else '否'}\n"
                f"• 自訂權限: {len(perms.custom_permissions)}\n"
                f"• 拒絕權限: {len(perms.denied_permissions)}",
                parse_mode="HTML"
            )
            return
        
        if args[0] == "group":
            # Show group settings
            if chat_type == "private":
                await update.message.reply_text("此指令僅限群組使用")
                return
            
            group = pm.get_group_settings(chat_id)
            await update.message.reply_text(
                f"👥 <b>群組設定</b>\n\n"
                f"• 已啟用: {'是' if group.enabled else '否'}\n"
                f"• 白名單模式: {'是' if group.whitelist_mode else '否'}\n"
                f"• 管理員數: {len(group.admins)}\n"
                f"• 版主數: {len(group.moderators)}\n"
                f"• 白名單: {len(group.whitelist)}\n"
                f"• 黑名單: {len(group.blacklist)}\n"
                f"• 停用指令: {len(group.disabled_commands)}",
                parse_mode="HTML"
            )
            return
        
        if args[0] == "admin" and len(args) >= 3:
            action = args[1]
            target_id = int(args[2])
            
            if chat_type == "private":
                await update.message.reply_text("此指令僅限群組使用")
                return
            
            if action == "add":
                pm.add_group_admin(chat_id, target_id)
                await update.message.reply_text(f"✅ 已將用戶 {target_id} 設為群組管理員")
            elif action == "remove":
                pm.remove_group_admin(chat_id, target_id)
                await update.message.reply_text(f"✅ 已移除用戶 {target_id} 的管理員權限")
            return
        
        if args[0] == "whitelist" and len(args) >= 3:
            action = args[1]
            target_id = int(args[2])
            
            if chat_type == "private":
                await update.message.reply_text("此指令僅限群組使用")
                return
            
            if action == "add":
                pm.add_to_whitelist(chat_id, target_id)
                await update.message.reply_text(f"✅ 已將用戶 {target_id} 加入白名單")
            elif action == "remove":
                group = pm.get_group_settings(chat_id)
                group.whitelist.discard(target_id)
                await update.message.reply_text(f"✅ 已將用戶 {target_id} 從白名單移除")
            return
        
        if args[0] == "blacklist" and len(args) >= 3:
            action = args[1]
            target_id = int(args[2])
            
            if action == "add":
                if chat_type == "private":
                    pm.add_to_global_blacklist(target_id)
                    await update.message.reply_text(f"✅ 已將用戶 {target_id} 加入全域黑名單")
                else:
                    pm.add_to_blacklist(chat_id, target_id)
                    await update.message.reply_text(f"✅ 已將用戶 {target_id} 加入群組黑名單")
            elif action == "remove":
                if chat_type == "private":
                    pm.remove_from_global_blacklist(target_id)
                    await update.message.reply_text(f"✅ 已將用戶 {target_id} 從全域黑名單移除")
            return
        
        # Show help
        await update.message.reply_text(
            "🔐 <b>權限管理</b>\n\n"
            "<code>/permissions</code> - 顯示狀態\n"
            "<code>/permissions user &lt;id&gt;</code> - 查看用戶\n"
            "<code>/permissions group</code> - 群組設定\n"
            "<code>/permissions admin add|remove &lt;id&gt;</code>\n"
            "<code>/permissions whitelist add|remove &lt;id&gt;</code>\n"
            "<code>/permissions blacklist add|remove &lt;id&gt;</code>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Permissions error: {e}")
        await update.message.reply_text(f"❌ 權限操作失敗: {e}")


# ============================================
# Elevate - Temporary elevated permissions
# ============================================


@authorized_only
async def elevate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /elevate command.
    Grant or check elevated permissions.
    
    Usage:
        /elevate - Check elevation status
        /elevate <minutes> - Request elevation
        /elevate revoke - Revoke elevation
    """
    args = context.args or []
    user_id = update.effective_user.id
    
    try:
        from ..core.permissions import get_permission_manager
        pm = get_permission_manager()
        
        if not args:
            # Check status
            is_elevated = pm.is_elevated(user_id)
            perms = pm.get_user_permissions(user_id)
            
            if is_elevated:
                remaining = (perms.elevated_until - datetime.now()).total_seconds() / 60
                await update.message.reply_text(
                    f"⬆️ <b>提升狀態</b>\n\n"
                    f"狀態: 🟢 已提升\n"
                    f"剩餘時間: {remaining:.0f} 分鐘",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text(
                    f"⬆️ <b>提升狀態</b>\n\n"
                    f"狀態: ⚪ 未提升\n\n"
                    f"使用 <code>/elevate &lt;分鐘&gt;</code> 請求提升",
                    parse_mode="HTML"
                )
            return
        
        if args[0] == "revoke":
            pm.revoke_elevation(user_id)
            await update.message.reply_text("✅ 已撤銷提升權限")
            return
        
        # Request elevation
        try:
            minutes = int(args[0])
            if minutes < 1 or minutes > 120:
                await update.message.reply_text("⚠️ 提升時間需在 1-120 分鐘之間")
                return
            
            # Check if user is allowed to self-elevate
            if not pm.is_global_admin(user_id):
                await update.message.reply_text("❌ 只有全域管理員可以自行提升權限")
                return
            
            pm.elevate_user(user_id, minutes)
            await update.message.reply_text(
                f"⬆️ <b>權限已提升</b>\n\n"
                f"持續時間: {minutes} 分鐘\n"
                f"您現在擁有提升權限",
                parse_mode="HTML"
            )
            
        except ValueError:
            await update.message.reply_text("❌ 請輸入有效的分鐘數")
            
    except Exception as e:
        logger.error(f"Elevate error: {e}")
        await update.message.reply_text(f"❌ 提升操作失敗: {e}")


# Need to import datetime for elevate handler
from datetime import datetime


# ============================================
# Lock - Gateway Lock Management
# ============================================


@authorized_only
async def lock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /lock command.
    Control gateway locking.
    
    Usage:
        /lock - Show lock status
        /lock on [message] - Lock the bot
        /lock off - Unlock the bot
        /lock maintenance [minutes] - Enter maintenance mode
        /lock user <id> - Lock a user
        /lock group - Lock current group
    """
    args = context.args or []
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        from ..core.gateway_lock import get_gateway_lock, LockReason
        gl = get_gateway_lock()
        
        if not args:
            # Show status
            info = gl.get_lock_info()
            stats = gl.get_stats()
            
            status = "🔒 已鎖定" if info.is_active() else "🔓 未鎖定"
            
            text = f"""🔐 <b>閘道鎖定狀態</b>

狀態: {status}
"""
            if info.is_active():
                text += f"原因: {info.reason.value}\n"
                text += f"訊息: {info.message or '(無)'}\n"
                remaining = info.time_remaining()
                if remaining:
                    text += f"剩餘: {remaining.seconds // 60} 分鐘\n"
            
            text += f"""
<b>統計:</b>
• 鎖定用戶: {stats['locked_users']}
• 鎖定群組: {stats['locked_groups']}
• IP 黑名單: {stats['blacklisted_ips']}
"""
            await update.message.reply_text(text, parse_mode="HTML")
            return
        
        action = args[0].lower()
        
        if action in ("on", "lock"):
            message = " ".join(args[1:]) if len(args) > 1 else "Bot is locked"
            gl.lock(LockReason.MANUAL, message, locked_by=user_id)
            await update.message.reply_text("🔒 閘道已鎖定")
        
        elif action in ("off", "unlock"):
            if gl.unlock(user_id):
                await update.message.reply_text("🔓 閘道已解鎖")
            else:
                await update.message.reply_text("閘道未處於鎖定狀態")
        
        elif action == "maintenance":
            minutes = int(args[1]) if len(args) > 1 else 30
            gl.maintenance_mode(minutes, locked_by=user_id)
            await update.message.reply_text(f"🔧 已進入維護模式 ({minutes} 分鐘)")
        
        elif action == "emergency":
            gl.emergency_lockdown(user_id)
            await update.message.reply_text("🚨 緊急鎖定已啟動")
        
        elif action == "user" and len(args) >= 2:
            target_id = int(args[1])
            minutes = int(args[2]) if len(args) > 2 else None
            gl.lock_user(target_id, duration_minutes=minutes)
            await update.message.reply_text(f"🔒 已鎖定用戶 {target_id}")
        
        elif action == "group":
            minutes = int(args[1]) if len(args) > 1 else None
            gl.lock_group(chat_id, duration_minutes=minutes)
            await update.message.reply_text("🔒 已鎖定此群組")
        
        elif action == "history":
            history = gl.get_history(10)
            if not history:
                await update.message.reply_text("📜 沒有鎖定歷史")
                return
            
            lines = ["📜 <b>鎖定歷史</b>\n"]
            for h in history:
                lines.append(f"• {h['action']} {h['target']} ({h['reason'] or '-'})")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        else:
            await update.message.reply_text(
                "🔐 <b>閘道鎖定</b>\n\n"
                "<code>/lock</code> - 顯示狀態\n"
                "<code>/lock on [訊息]</code> - 鎖定\n"
                "<code>/lock off</code> - 解鎖\n"
                "<code>/lock maintenance [分鐘]</code> - 維護模式\n"
                "<code>/lock emergency</code> - 緊急鎖定\n"
                "<code>/lock user &lt;id&gt; [分鐘]</code> - 鎖定用戶\n"
                "<code>/lock group [分鐘]</code> - 鎖定群組\n"
                "<code>/lock history</code> - 查看歷史",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Lock error: {e}")
        await update.message.reply_text(f"❌ 鎖定操作失敗: {e}")


# ============================================
# Location - Location Sharing
# ============================================


@authorized_only
async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /location command.
    Manage location sharing.
    
    Usage:
        /location - Show location help
        /location share - Share current location
        /location get <id> - Get shared location
        /location stop - Stop sharing
    """
    args = context.args or []
    user_id = update.effective_user.id
    
    try:
        from ..core.location import get_location_manager
        lm = get_location_manager()
        
        if not args:
            stats = lm.get_stats()
            await update.message.reply_text(
                f"📍 <b>位置服務</b>\n\n"
                f"• 用戶位置: {stats['users_with_location']}\n"
                f"• 活躍分享: {stats['active_shares']}\n"
                f"• 即時分享: {stats['live_shares']}\n\n"
                f"<b>指令:</b>\n"
                f"<code>/location share</code> - 分享位置\n"
                f"<code>/location get &lt;id&gt;</code> - 取得分享\n"
                f"<code>/location stop</code> - 停止分享\n"
                f"<code>/location my</code> - 我的位置\n\n"
                f"<i>提示: 直接發送位置訊息即可分享</i>",
                parse_mode="HTML"
            )
            return
        
        action = args[0].lower()
        
        if action == "share":
            # User needs to send a location message
            await update.message.reply_text(
                "📍 請發送位置訊息來分享您的位置\n\n"
                "點擊附件圖示 📎 -> 位置 -> 發送位置"
            )
        
        elif action == "get" and len(args) >= 2:
            share_id = args[1]
            share = lm.get_shared_location(share_id)
            
            if not share:
                await update.message.reply_text("❌ 找不到此位置分享或已過期")
                return
            
            loc = share.location
            await update.message.reply_location(
                latitude=loc.latitude,
                longitude=loc.longitude,
            )
            
            await update.message.reply_text(
                f"📍 <b>位置資訊</b>\n\n"
                f"座標: {loc.latitude:.6f}, {loc.longitude:.6f}\n"
                f"地址: {loc.address or '(未知)'}\n"
                f"🔗 {loc.to_google_maps_url()}",
                parse_mode="HTML"
            )
        
        elif action == "stop":
            lm.stop_live_sharing(user_id)
            lm.clear_user_location(user_id)
            await update.message.reply_text("✅ 已停止位置分享")
        
        elif action == "my":
            loc = lm.get_user_location(user_id)
            if not loc:
                await update.message.reply_text("❌ 沒有您的位置記錄")
                return
            
            await update.message.reply_text(
                f"📍 <b>我的位置</b>\n\n"
                f"座標: {loc.latitude:.6f}, {loc.longitude:.6f}\n"
                f"更新: {loc.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
                f"🔗 {loc.to_google_maps_url()}",
                parse_mode="HTML"
            )
        
        else:
            await update.message.reply_text("❓ 未知的子指令")
            
    except Exception as e:
        logger.error(f"Location error: {e}")
        await update.message.reply_text(f"❌ 位置操作失敗: {e}")


# ============================================
# Route - Channel Routing
# ============================================


@authorized_only
async def route_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /route command.
    Manage channel routing.
    
    Usage:
        /route - Show routing stats
        /route list - List channels
        /route add <channel_id> <agent> - Add route
        /route remove <channel_id> - Remove route
    """
    args = context.args or []
    
    try:
        from ..core.channel_routing import get_channel_router
        router = get_channel_router()
        
        if not args:
            stats = router.get_stats()
            await update.message.reply_text(
                f"🔀 <b>頻道路由</b>\n\n"
                f"• 總頻道數: {stats['total_channels']}\n"
                f"• 活躍規則: {stats['active_rules']}\n"
                f"• 處理器: {stats['registered_handlers']}\n"
                f"• 轉發: {'啟用' if stats['forwarding_enabled'] else '停用'}\n"
                f"• 已路由訊息: {stats['total_messages_routed']}",
                parse_mode="HTML"
            )
            return
        
        action = args[0].lower()
        
        if action == "list":
            channels = router.list_channels()
            if not channels:
                await update.message.reply_text("📭 沒有已註冊的頻道")
                return
            
            lines = ["📋 <b>已註冊頻道</b>\n"]
            for ch in channels[:10]:
                status = "✅" if ch.enabled else "❌"
                lines.append(f"• {status} <code>{ch.channel_id}</code>")
                lines.append(f"  類型: {ch.channel_type.value}")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif action == "enable":
            router.enable_forwarding()
            await update.message.reply_text("✅ 已啟用訊息轉發")
        
        elif action == "disable":
            router.disable_forwarding()
            await update.message.reply_text("❌ 已停用訊息轉發")
        
        else:
            await update.message.reply_text(
                "🔀 <b>頻道路由</b>\n\n"
                "<code>/route</code> - 顯示統計\n"
                "<code>/route list</code> - 列出頻道\n"
                "<code>/route enable</code> - 啟用轉發\n"
                "<code>/route disable</code> - 停用轉發",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Route error: {e}")
        await update.message.reply_text(f"❌ 路由操作失敗: {e}")


# ============================================
# Presence - Online Status
# ============================================


@authorized_only
async def presence_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /presence command.
    Manage user online status.
    
    Usage:
        /presence - Show status
        /presence online - Set online
        /presence away - Set away
        /presence busy [text] - Set busy
        /presence offline - Set offline
    """
    args = context.args or []
    user_id = update.effective_user.id
    
    try:
        from ..core.presence import get_presence_manager, PresenceStatus
        pm = get_presence_manager()
        
        if not args:
            presence = pm.get_presence(user_id)
            stats = pm.get_stats()
            
            status = presence.status.value if presence else "offline"
            status_emoji = {
                "online": "🟢",
                "away": "🟡",
                "busy": "🔴",
                "offline": "⚫",
                "invisible": "👻",
            }.get(status, "⚪")
            
            text = f"""👤 <b>在線狀態</b>

您的狀態: {status_emoji} {status}
"""
            if presence and presence.status_text:
                text += f"狀態訊息: {presence.status_text}\n"
            
            text += f"""
<b>全域統計:</b>
• 在線用戶: {stats['online']}
• 5分鐘內活躍: {stats['active_5min']}
• 總追蹤: {stats['total_tracked']}
"""
            await update.message.reply_text(text, parse_mode="HTML")
            return
        
        action = args[0].lower()
        
        if action == "online":
            pm.set_online(user_id, "telegram")
            await update.message.reply_text("🟢 已設為在線")
        
        elif action == "away":
            pm.set_away(user_id)
            await update.message.reply_text("🟡 已設為離開")
        
        elif action == "busy":
            status_text = " ".join(args[1:]) if len(args) > 1 else ""
            pm.set_busy(user_id, status_text)
            await update.message.reply_text("🔴 已設為忙碌")
        
        elif action == "offline":
            pm.set_offline(user_id)
            await update.message.reply_text("⚫ 已設為離線")
        
        elif action == "invisible":
            pm.set_invisible(user_id)
            await update.message.reply_text("👻 已設為隱身")
        
        else:
            await update.message.reply_text(
                "👤 <b>在線狀態</b>\n\n"
                "<code>/presence</code> - 顯示狀態\n"
                "<code>/presence online</code> - 設為在線\n"
                "<code>/presence away</code> - 設為離開\n"
                "<code>/presence busy [訊息]</code> - 設為忙碌\n"
                "<code>/presence offline</code> - 設為離線\n"
                "<code>/presence invisible</code> - 設為隱身",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Presence error: {e}")
        await update.message.reply_text(f"❌ 狀態操作失敗: {e}")


# ============================================
# Gateway - Unified Gateway Info
# ============================================


@authorized_only
async def gateway_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /gateway command.
    Show unified gateway information.
    
    Usage:
        /gateway - Show gateway status
    """
    try:
        from ..core.gateway import get_gateway
        gw = get_gateway()
        stats = gw.get_stats()
        
        adapters = ", ".join(stats.get("adapters", [])) or "(無)"
        
        text = f"""🌐 <b>統一閘道</b>

狀態: {'🟢 運行中' if stats.get('running') else '⚫ 停止'}
已註冊適配器: {adapters}

<b>統計:</b>
• 已接收訊息: {stats.get('messages_received', 0)}
• 已發送訊息: {stats.get('messages_sent', 0)}
• 錯誤: {stats.get('errors', 0)}
• 處理器: {stats.get('handlers', 0)}
• 中介軟體: {stats.get('middleware', 0)}
"""
        await update.message.reply_text(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Gateway error: {e}")
        await update.message.reply_text(f"❌ 閘道查詢失敗: {e}")


# ============================================
# Agents - Agent Management
# ============================================


@authorized_only
async def agents_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /agents command.
    Manage registered agents.
    
    Usage:
        /agents - List agents
        /agents stats - Show statistics
    """
    args = context.args or []
    
    try:
        from ..core.agent_send import get_agent_send_manager
        asm = get_agent_send_manager()
        
        if not args or args[0] == "list":
            agents = asm.list_agents()
            
            if not agents:
                await update.message.reply_text("🤖 沒有已註冊的代理")
                return
            
            lines = ["🤖 <b>已註冊代理</b>\n"]
            for agent in agents:
                status = "🟢" if agent.online else "⚫"
                lines.append(f"• {status} <b>{agent.name}</b> (<code>{agent.agent_id}</code>)")
                if agent.capabilities:
                    lines.append(f"  能力: {', '.join(agent.capabilities[:3])}")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif args[0] == "stats":
            stats = asm.get_stats()
            
            text = f"""🤖 <b>代理統計</b>

• 已註冊: {stats['registered_agents']}
• 在線: {stats['online_agents']}
• 已發送訊息: {stats['messages_sent']}
• 已送達: {stats['messages_delivered']}
• 失敗: {stats['messages_failed']}
• 待處理回應: {stats['pending_responses']}
"""
            await update.message.reply_text(text, parse_mode="HTML")
        
        else:
            await update.message.reply_text(
                "🤖 <b>代理管理</b>\n\n"
                "<code>/agents</code> - 列出代理\n"
                "<code>/agents stats</code> - 顯示統計",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Agents error: {e}")
        await update.message.reply_text(f"❌ 代理查詢失敗: {e}")


# ============================================
# WhatsApp - WhatsApp Integration
# ============================================


@authorized_only
async def whatsapp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /whatsapp command.
    Manage WhatsApp integration.
    
    Usage:
        /whatsapp - Show status
        /whatsapp qr - Show QR code for login
        /whatsapp chats - List chats
    """
    args = context.args or []
    
    try:
        from ..platforms.whatsapp_bot import WhatsAppBot, WhatsAppStatus
        import os
        
        # Check if WhatsApp is enabled
        if not os.getenv("WHATSAPP_ENABLED", "").lower() == "true":
            await update.message.reply_text(
                "📱 <b>WhatsApp 整合</b>\n\n"
                "❌ WhatsApp 未啟用\n\n"
                "<b>啟用方式:</b>\n"
                "1. 設定 <code>WHATSAPP_ENABLED=true</code>\n"
                "2. 安裝 Node.js 並執行 WhatsApp Bridge\n"
                "3. 使用 <code>/whatsapp qr</code> 掃描登入",
                parse_mode="HTML"
            )
            return
        
        if not args or args[0] == "status":
            # Show status
            text = """📱 <b>WhatsApp 整合狀態</b>

• 狀態: 🟡 等待連線
• 需要掃描 QR Code 登入

<b>指令:</b>
• <code>/whatsapp qr</code> - 顯示登入 QR Code
• <code>/whatsapp chats</code> - 列出聊天室

<b>設定:</b>
• Bridge 端口: {port}
• 允許號碼: {allowed}
""".format(
                port=os.getenv("WHATSAPP_BRIDGE_PORT", "3000"),
                allowed=os.getenv("WHATSAPP_ALLOWED_NUMBERS", "全部") or "全部"
            )
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "qr":
            await update.message.reply_text(
                "📱 <b>WhatsApp 登入</b>\n\n"
                "請訪問以下網址掃描 QR Code:\n"
                f"<code>http://localhost:{os.getenv('WHATSAPP_BRIDGE_PORT', '3000')}/qr</code>\n\n"
                "或使用 WhatsApp > 設定 > 已連結的裝置 > 連結裝置",
                parse_mode="HTML"
            )
        
        elif args[0] == "chats":
            await update.message.reply_text(
                "📱 請先確保 WhatsApp Bridge 正在運行並已登入"
            )
        
        else:
            await update.message.reply_text(
                "📱 <b>WhatsApp 指令</b>\n\n"
                "<code>/whatsapp</code> - 狀態\n"
                "<code>/whatsapp qr</code> - 登入 QR Code\n"
                "<code>/whatsapp chats</code> - 聊天列表",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"WhatsApp error: {e}")
        await update.message.reply_text(f"❌ WhatsApp 錯誤: {e}")


# ============================================
# MS Teams - Teams Integration
# ============================================


@authorized_only
async def teams_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /teams command.
    Manage MS Teams integration.
    
    Usage:
        /teams - Show status
        /teams setup - Setup instructions
    """
    args = context.args or []
    
    try:
        import os
        
        app_id = os.getenv("TEAMS_APP_ID", "")
        
        if not args or args[0] == "status":
            if app_id:
                status = "🟢 已設定"
                app_info = f"App ID: <code>{app_id[:8]}...</code>"
            else:
                status = "⚪ 未設定"
                app_info = "需要 Azure AD 設定"
            
            text = f"""💼 <b>MS Teams 整合狀態</b>

• 狀態: {status}
• {app_info}
• 端口: {os.getenv('TEAMS_PORT', '3978')}

<b>指令:</b>
• <code>/teams setup</code> - 設定說明

<b>功能:</b>
• 直接訊息與頻道訊息
• Adaptive Cards 支援
• Bot Framework 整合
"""
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "setup":
            text = """💼 <b>MS Teams 設定指南</b>

<b>步驟 1: Azure AD 設定</b>
1. 前往 Azure Portal
2. 建立 App Registration
3. 取得 App ID 和 Password

<b>步驟 2: Bot Framework</b>
1. 前往 Bot Framework Portal
2. 建立 Bot Channel Registration
3. 設定 Messaging Endpoint

<b>步驟 3: 環境變數</b>
<code>TEAMS_ENABLED=true
TEAMS_APP_ID=your-app-id
TEAMS_APP_PASSWORD=your-password</code>

<b>步驟 4: Teams App</b>
1. 建立 Teams App manifest
2. 上傳至 Teams

詳細文件: https://docs.microsoft.com/azure/bot-service/
"""
            await update.message.reply_text(text, parse_mode="HTML")
        
        else:
            await update.message.reply_text(
                "💼 <b>MS Teams 指令</b>\n\n"
                "<code>/teams</code> - 狀態\n"
                "<code>/teams setup</code> - 設定說明",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Teams error: {e}")
        await update.message.reply_text(f"❌ Teams 錯誤: {e}")


# ============================================
# Tailscale - VPN Integration
# ============================================


@authorized_only
async def tailscale_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tailscale command.
    Manage Tailscale VPN integration.
    
    Usage:
        /tailscale - Show status
        /tailscale devices - List devices
        /tailscale ping <device> - Ping device
        /tailscale ip - Show Tailscale IP
    """
    args = context.args or []
    
    try:
        from ..core.tailscale import get_tailscale_manager, TailscaleStatus
        
        ts = get_tailscale_manager()
        
        if not args or args[0] == "status":
            status = await ts.get_status()
            self_device = await ts.get_self()
            
            status_emoji = {
                TailscaleStatus.RUNNING: "🟢",
                TailscaleStatus.STOPPED: "⚪",
                TailscaleStatus.NEEDS_LOGIN: "🟡",
                TailscaleStatus.ERROR: "🔴",
                TailscaleStatus.NOT_INSTALLED: "❌",
            }.get(status, "❓")
            
            text = f"""🔐 <b>Tailscale VPN 狀態</b>

• 狀態: {status_emoji} {status.value}
"""
            if self_device:
                text += f"""• 主機名: {self_device.hostname}
• IP: {', '.join(self_device.ip_addresses[:2])}
• 系統: {self_device.os}
"""
            
            text += """
<b>指令:</b>
• <code>/tailscale devices</code> - 列出裝置
• <code>/tailscale ping &lt;device&gt;</code> - Ping 裝置
• <code>/tailscale ip</code> - 顯示 IP
"""
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "devices":
            devices = await ts.get_devices()
            
            if not devices:
                await update.message.reply_text("🔐 沒有找到 Tailscale 裝置")
                return
            
            lines = ["🔐 <b>Tailscale 裝置</b>\n"]
            for device in devices:
                status = "🟢" if device.online else "⚫"
                lines.append(f"• {status} <b>{device.name}</b>")
                lines.append(f"  {', '.join(device.ip_addresses[:1])}")
                if device.is_self:
                    lines.append("  (本機)")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif args[0] == "ping" and len(args) >= 2:
            target = args[1]
            await update.message.reply_text(f"🔐 正在 Ping {target}...")
            
            latency = await ts.ping(target, count=3)
            
            if latency is not None:
                await update.message.reply_text(f"🔐 Ping {target}: {latency:.1f}ms")
            else:
                await update.message.reply_text(f"❌ 無法 Ping {target}")
        
        elif args[0] == "ip":
            ip = await ts.get_ip()
            if ip:
                await update.message.reply_text(f"🔐 Tailscale IP: <code>{ip}</code>", parse_mode="HTML")
            else:
                await update.message.reply_text("❌ 無法取得 Tailscale IP")
        
        else:
            await update.message.reply_text(
                "🔐 <b>Tailscale 指令</b>\n\n"
                "<code>/tailscale</code> - 狀態\n"
                "<code>/tailscale devices</code> - 裝置列表\n"
                "<code>/tailscale ping &lt;device&gt;</code> - Ping\n"
                "<code>/tailscale ip</code> - IP 地址",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Tailscale error: {e}")
        await update.message.reply_text(f"❌ Tailscale 錯誤: {e}")


# ============================================
# iMessage - iMessage Integration (macOS)
# ============================================


@authorized_only
async def imessage_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /imessage command.
    Manage iMessage integration (macOS only).
    
    Usage:
        /imessage - Show status
        /imessage chats - List recent chats
        /imessage send <recipient> <message> - Send message
    """
    args = context.args or []
    
    try:
        import platform
        
        # Check if macOS
        if platform.system() != "Darwin":
            await update.message.reply_text(
                "💬 <b>iMessage 整合</b>\n\n"
                "❌ iMessage 僅支援 macOS\n\n"
                "你目前的系統: " + platform.system(),
                parse_mode="HTML"
            )
            return
        
        from ..platforms.imessage_bot import IMessageBot, IMessageStatus
        
        bot = IMessageBot()
        
        if not args or args[0] == "status":
            # Show status
            is_macos = bot.is_macos()
            has_access = bot.has_db_access()
            
            status_text = "🟢 可用" if (is_macos and has_access) else "⚪ 未設定"
            access_text = "✅ 已授權" if has_access else "❌ 需要授權"
            
            text = f"""💬 <b>iMessage 整合狀態</b>

• 系統: macOS ✅
• 狀態: {status_text}
• 資料庫存取: {access_text}

<b>指令:</b>
• <code>/imessage chats</code> - 列出聊天
• <code>/imessage send &lt;號碼&gt; &lt;訊息&gt;</code> - 發送

<b>設定:</b>
需要在系統偏好設定 > 安全性與隱私 > 完整磁碟存取權 中授權
"""
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "chats":
            if not bot.has_db_access():
                await update.message.reply_text(
                    "❌ 無法存取 Messages 資料庫\n"
                    "請在系統偏好設定中授權"
                )
                return
            
            chats = await bot.get_recent_chats(limit=10)
            
            if not chats:
                await update.message.reply_text("💬 沒有找到聊天記錄")
                return
            
            lines = ["💬 <b>最近聊天</b>\n"]
            for chat in chats:
                emoji = "👥" if chat.is_group else "👤"
                lines.append(f"• {emoji} {chat.name}")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif args[0] == "send" and len(args) >= 3:
            recipient = args[1]
            message = " ".join(args[2:])
            
            success = await bot.send_message(recipient, message)
            
            if success:
                await update.message.reply_text(f"✅ 已發送訊息給 {recipient}")
            else:
                await update.message.reply_text(f"❌ 發送失敗")
        
        else:
            await update.message.reply_text(
                "💬 <b>iMessage 指令</b>\n\n"
                "<code>/imessage</code> - 狀態\n"
                "<code>/imessage chats</code> - 聊天列表\n"
                "<code>/imessage send &lt;號碼&gt; &lt;訊息&gt;</code> - 發送訊息",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"iMessage error: {e}")
        await update.message.reply_text(f"❌ iMessage 錯誤: {e}")


# ============================================
# Line - Line Bot Integration
# ============================================


@authorized_only
async def line_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /line command.
    Manage Line bot integration.
    
    Usage:
        /line - Show status
        /line setup - Setup instructions
    """
    args = context.args or []
    
    try:
        import os
        
        token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        
        if not args or args[0] == "status":
            if token:
                status = "🟢 已設定"
                token_info = f"Token: <code>{token[:10]}...</code>"
            else:
                status = "⚪ 未設定"
                token_info = "需要 Line Developer 設定"
            
            text = f"""📱 <b>Line Bot 整合狀態</b>

• 狀態: {status}
• {token_info}
• Webhook: /webhook/line (使用 API Server port)

<b>指令:</b>
• <code>/line setup</code> - 設定說明

<b>支援功能:</b>
• 文字訊息
• Quick Reply
• Flex Message
• Rich Menu
"""
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "setup":
            text = """📱 <b>Line Bot 設定指南</b>

<b>步驟 1: Line Developer Console</b>
1. 前往 https://developers.line.biz/
2. 建立 Provider 和 Channel
3. 選擇 Messaging API

<b>步驟 2: 取得憑證</b>
1. Channel Access Token (長期)
2. Channel Secret

<b>步驟 3: 環境變數</b>
<code>LINE_ENABLED=true
LINE_CHANNEL_ACCESS_TOKEN=your-token
LINE_CHANNEL_SECRET=your-secret</code>

<b>步驟 4: Webhook 設定</b>
1. 設定 Webhook URL
2. 格式: https://your-domain/webhook/line
3. 開啟 Use webhook

<b>特點:</b>
• 日本、台灣、泰國等亞洲市場
• 豐富的 Flex Message 格式
• Quick Reply 按鈕
"""
            await update.message.reply_text(text, parse_mode="HTML")
        
        else:
            await update.message.reply_text(
                "📱 <b>Line 指令</b>\n\n"
                "<code>/line</code> - 狀態\n"
                "<code>/line setup</code> - 設定說明",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Line error: {e}")
        await update.message.reply_text(f"❌ Line 錯誤: {e}")


# ============================================
# Menu Bar - macOS Menu Bar App
# ============================================


@authorized_only
async def menubar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /menubar command.
    Information about macOS Menu Bar app.
    
    Usage:
        /menubar - Show info and installation
    """
    import platform
    
    is_macos = platform.system() == "Darwin"
    
    text = f"""🖥️ <b>macOS Menu Bar 應用</b>

• 系統: {'macOS ✅' if is_macos else platform.system() + ' ❌'}

<b>功能:</b>
• 狀態列快速存取
• 即時聊天視窗
• 伺服器狀態顯示
• 最近對話

<b>安裝:</b>
<code>pip install rumps</code>

<b>執行:</b>
<code>python -m src.macos.menubar</code>

<b>自動啟動:</b>
<code>python -m src.macos.menubar --install</code>

<b>環境變數:</b>
<code>CURSORBOT_SERVER_URL=http://localhost:8000</code>

注意: 僅支援 macOS
"""
    await update.message.reply_text(text, parse_mode="HTML")


# ============================================
# Control Panel - System Control
# ============================================


@authorized_only
async def control_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /control command.
    System control panel and quick actions.
    
    Usage:
        /control - Show control panel
        /control status - System status
        /control restart - Restart bot (admin only)
        /control providers - List AI providers
        /control url - Show Web UI URL
    """
    import os
    args = context.args or []
    
    try:
        # Get server URL
        server_url = os.getenv("CURSORBOT_SERVER_URL", "http://localhost:8000")
        api_port = os.getenv("API_PORT", "8000")
        
        if not args or args[0] == "status":
            # Get system status
            import psutil
            import platform
            
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            
            # Get provider status
            from ..core import LLMProviderManager
            manager = LLMProviderManager()
            providers = list(manager.list_providers().keys())
            provider_count = len(providers)
            
            text = f"""⚙️ <b>CursorBot 控制面板</b>

━━━━━━━━━━━━━━━━━━━━━━
<b>📊 系統狀態</b>
━━━━━━━━━━━━━━━━━━━━━━
• CPU: {cpu}%
• 記憶體: {mem.percent}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)
• 系統: {platform.system()} {platform.release()}
• Python: {platform.python_version()}

━━━━━━━━━━━━━━━━━━━━━━
<b>🤖 Bot 狀態</b>
━━━━━━━━━━━━━━━━━━━━━━
• AI 提供者: {provider_count} 個已設定
• 已載入: {', '.join(providers[:3])}{'...' if len(providers) > 3 else ''}

━━━━━━━━━━━━━━━━━━━━━━
<b>🌐 Web 介面</b>
━━━━━━━━━━━━━━━━━━━━━━
• Dashboard: {server_url}/dashboard
• WebChat: {server_url}/chat
• Control UI: {server_url}/control

━━━━━━━━━━━━━━━━━━━━━━
<b>📋 可用指令</b>
━━━━━━━━━━━━━━━━━━━━━━
<code>/control status</code> - 系統狀態
<code>/control providers</code> - AI 提供者列表
<code>/control url</code> - Web 介面網址
<code>/control restart</code> - 重啟 Bot
"""
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "providers":
            from ..core import LLMProviderManager
            manager = LLMProviderManager()
            providers_info = manager.list_providers()
            
            lines = ["⚙️ <b>AI 提供者狀態</b>\n"]
            
            for name, info in providers_info.items():
                status = "🟢" if info.get("available", False) else "⚪"
                model = info.get("model", "N/A")
                lines.append(f"{status} <b>{name}</b>: {model}")
            
            if not providers_info:
                lines.append("尚未設定任何 AI 提供者")
            
            lines.append("\n使用 <code>/model</code> 切換模型")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif args[0] == "url":
            text = f"""🌐 <b>Web 介面網址</b>

• <b>Dashboard</b>
  {server_url}/dashboard
  系統監控和統計

• <b>WebChat</b>
  {server_url}/chat
  網頁版聊天介面

• <b>Control Panel</b>
  {server_url}/control
  設定和管理

• <b>API Docs</b>
  {server_url}/docs
  API 文件 (Swagger)

伺服器埠: {api_port}
"""
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "restart":
            # Check if user is admin
            admin_ids = os.getenv("ADMIN_USER_IDS", "").split(",")
            user_id = str(update.effective_user.id)
            
            if user_id not in admin_ids and admin_ids[0] != "":
                await update.message.reply_text("❌ 僅管理員可執行重啟操作")
                return
            
            await update.message.reply_text(
                "⚠️ <b>確認重啟</b>\n\n"
                "這將重啟 CursorBot 服務。\n"
                "請透過 Web Control Panel 執行:\n"
                f"{server_url}/control",
                parse_mode="HTML"
            )
        
        else:
            await update.message.reply_text(
                "⚙️ <b>Control 指令</b>\n\n"
                "<code>/control</code> - 控制面板\n"
                "<code>/control status</code> - 系統狀態\n"
                "<code>/control providers</code> - AI 提供者\n"
                "<code>/control url</code> - Web 介面網址\n"
                "<code>/control restart</code> - 重啟 Bot",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Control error: {e}")
        await update.message.reply_text(f"❌ 控制面板錯誤: {e}")


# ============================================
# Mode - Switch Chat Mode (Agent vs Cursor)
# ============================================


@authorized_only
async def mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /mode command.
    Switch between Assistant, Agent and Cursor CLI (both use async execution).
    
    Usage:
        /mode - Show current mode
        /mode assistant - Personal secretary mode (natural language)
        /mode auto - Auto select best mode (CLI -> Agent)
        /mode cli - Use Cursor CLI for chat
        /mode agent - Use Agent Loop for chat
    """
    from . import handlers as handlers_module
    from .handlers import get_user_chat_mode, set_user_chat_mode, get_best_available_mode
    from ..claude.cli_agent import is_cli_available, get_cli_agent
    from ..core.secretary import get_secretary
    
    logger.info(f"mode_handler called with args: {context.args}")
    logger.info(f"Current _user_chat_modes before change: {handlers_module._user_chat_modes}")
    
    user_id = update.effective_user.id
    args = context.args or []
    
    current_mode = get_user_chat_mode(user_id)
    
    # Get secretary info
    secretary = get_secretary()
    prefs = secretary.get_preferences(str(user_id))
    
    if not args:
        # Show current mode and options
        mode_icons = {"auto": "🔄", "cli": "⌨️", "agent": "🤖", "assistant": "👩‍💼"}
        mode_names = {
            "auto": "自動選擇",
            "cli": "Cursor CLI",
            "agent": "Agent Loop",
            "assistant": f"秘書模式 ({prefs.secretary_name})",
        }
        mode_icon = mode_icons.get(current_mode, "🔄")
        mode_name = mode_names.get(current_mode, "自動選擇")
        
        # Check availability
        cli_available = is_cli_available()
        
        # Get effective mode if auto
        effective_mode = ""
        if current_mode == "auto":
            best = get_best_available_mode()
            effective_mode = f"\n   實際使用: {mode_names.get(best, best)}"
        
        # Get CLI info
        cli_info = ""
        if cli_available:
            cli = get_cli_agent()
            info = await cli.check_installation()
            cli_info = f"版本: {info.get('version', 'unknown')}"
        
        text = f"""⚡ <b>對話模式設定</b>

━━━━━━━━━━━━━━━━━━━━━━
<b>目前模式</b>
━━━━━━━━━━━━━━━━━━━━━━
{mode_icon} <b>{mode_name}</b>{effective_mode}

━━━━━━━━━━━━━━━━━━━━━━
<b>可用模式</b>
━━━━━━━━━━━━━━━━━━━━━━
👩‍💼 <b>秘書模式</b> (<code>/mode assistant</code>) ✅ 推薦
   專屬秘書 {prefs.secretary_name} 為您服務
   用自然語言聊天和下指令
   「幫我記開會」「今天有什麼行程」

🔄 <b>自動選擇</b> (<code>/mode auto</code>)
   自動選擇最佳可用模式
   優先順序: CLI → Agent

⌨️ <b>Cursor CLI</b> (<code>/mode cli</code>) {f'✅' if cli_available else '⚠️'}
   程式碼生成、檔案編輯
   {f'({cli_info})' if cli_available else '未安裝'}

🤖 <b>Agent Loop</b> (<code>/mode agent</code>) ✅
   AI Agent 多步驟推理
   執行複雜任務、使用工具

━━━━━━━━━━━━━━━━━━━━━━
<b>切換指令</b>
━━━━━━━━━━━━━━━━━━━━━━
<code>/mode assistant</code> - 秘書模式 👩‍💼
<code>/mode auto</code> - 自動選擇
<code>/mode cli</code> - Cursor CLI 模式
<code>/mode agent</code> - Agent Loop 模式

直接發送訊息即可使用選定模式。
"""
        await update.message.reply_text(text, parse_mode="HTML")
    
    elif args[0].lower() in ["assistant", "secretary", "秘書"]:
        result = set_user_chat_mode(user_id, "assistant")
        logger.info(f"set_user_chat_mode({user_id}, 'assistant') returned: {result}")
        logger.info(f"_user_chat_modes after change: {handlers_module._user_chat_modes}")
        
        await update.message.reply_text(
            f"👩‍💼 <b>已切換到秘書模式</b>\n\n"
            f"您的專屬秘書 <b>{prefs.secretary_name}</b> 為您服務！\n\n"
            "💬 現在可以用自然語言與我互動：\n"
            "• 「幫我記明天要開會」\n"
            "• 「今天有什麼行程」\n"
            "• 「訂機票去東京」\n"
            "• 「待辦清單」\n\n"
            "或是直接跟我聊天也可以喔～✨\n\n"
            f"—— {prefs.secretary_name}",
            parse_mode="HTML"
        )
    
    elif args[0].lower() == "auto":
        set_user_chat_mode(user_id, "auto")
        
        # Get best mode
        best = get_best_available_mode()
        mode_names = {"cli": "Cursor CLI", "agent": "Agent Loop", "assistant": "秘書模式"}
        
        await update.message.reply_text(
            "🔄 <b>已切換到自動選擇模式</b>\n\n"
            f"目前最佳模式: <b>{mode_names.get(best, best)}</b>\n\n"
            "🚀 所有模式皆為異步執行\n"
            "任務完成後自動推送結果",
            parse_mode="HTML"
        )
    
    elif args[0].lower() == "agent":
        set_user_chat_mode(user_id, "agent")
        
        # Get current model info
        from ..core.llm_providers import get_llm_manager
        manager = get_llm_manager()
        current_model = manager.get_user_model(str(user_id))
        model_info = f"{current_model[0]}/{current_model[1]}" if current_model else "預設模型"
        
        await update.message.reply_text(
            "🤖 <b>已切換到 Agent Loop 模式</b>\n\n"
            f"模型: <code>{model_info}</code>\n\n"
            "🚀 異步執行，任務背景處理\n"
            "完成後自動推送結果\n\n"
            "Agent 可以:\n"
            "• 回答問題和對話\n"
            "• 執行複雜任務\n"
            "• 使用已載入的技能\n"
            "• 呼叫各種工具\n\n"
            "💡 <code>/model</code> 切換 AI 模型\n"
            "💡 <code>/tasks</code> 查看任務",
            parse_mode="HTML"
        )
    
    elif args[0].lower() == "cli":
        if not is_cli_available():
            await update.message.reply_text(
                "⚠️ <b>Cursor CLI 未安裝</b>\n\n"
                "安裝指令:\n"
                "<code>curl https://cursor.com/install -fsS | bash</code>\n\n"
                "安裝後重新執行 <code>/mode cli</code>",
                parse_mode="HTML"
            )
            return
        
        set_user_chat_mode(user_id, "cli")
        
        # Get CLI info
        cli = get_cli_agent()
        info = await cli.check_installation()
        
        await update.message.reply_text(
            "⌨️ <b>已切換到 Cursor CLI 模式</b>\n\n"
            f"路徑: <code>{info.get('path', 'agent')}</code>\n"
            f"版本: <code>{info.get('version', 'unknown')}</code>\n\n"
            "🚀 異步執行，任務背景處理\n"
            "完成後自動推送結果\n\n"
            "CLI 可以:\n"
            "• 程式碼生成和編輯\n"
            "• 檔案操作\n"
            "• 專案分析\n"
            "• 執行終端指令\n\n"
            "💡 <code>/workspace</code> 設定工作目錄\n"
            "💡 <code>/tasks</code> 查看任務",
            parse_mode="HTML"
        )
    
    else:
        await update.message.reply_text(
            "⚡ <b>Mode 指令</b>\n\n"
            "<code>/mode</code> - 查看目前模式\n"
            "<code>/mode assistant</code> - 👩‍💼 秘書模式（推薦）\n"
            "<code>/mode auto</code> - 自動選擇\n"
            "<code>/mode cli</code> - Cursor CLI 模式\n"
            "<code>/mode agent</code> - Agent Loop 模式\n\n"
            "💡 秘書模式可用自然語言互動",
            parse_mode="HTML"
        )


# ============================================
# New Chat - Clear CLI Context
# ============================================


@authorized_only
async def newchat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /newchat command.
    Start a fresh CLI conversation without previous context.
    
    Usage:
        /newchat - Clear current chat context and start fresh
    """
    from ..claude.cli_agent import get_cli_agent, is_cli_available
    from .handlers import get_user_chat_mode
    
    user_id = update.effective_user.id
    
    if not is_cli_available():
        await update.message.reply_text(
            "⚠️ <b>Cursor CLI 未安裝</b>\n\n"
            "此指令僅適用於 CLI 模式。\n"
            "安裝: <code>curl https://cursor.com/install -fsS | bash</code>",
            parse_mode="HTML"
        )
        return
    
    cli = get_cli_agent()
    
    # Check if user has an active chat
    old_chat_id = cli.get_user_chat_id(str(user_id))
    
    if old_chat_id:
        # Clear the chat session
        cli.clear_user_chat(str(user_id))
        
        await update.message.reply_text(
            "🔄 <b>對話已重置</b>\n\n"
            f"已清除對話: <code>{old_chat_id[:8]}...</code>\n\n"
            "下次對話將開始全新的上下文。\n"
            "之前的對話記憶已清除。",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "ℹ️ <b>無活躍對話</b>\n\n"
            "您目前沒有活躍的對話上下文。\n"
            "直接發送訊息即可開始新對話。",
            parse_mode="HTML"
        )


@authorized_only
async def chatinfo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /chatinfo command.
    Show current CLI chat session info.
    
    Usage:
        /chatinfo - Show current chat context info
    """
    from ..claude.cli_agent import get_cli_agent, is_cli_available
    from .handlers import get_user_chat_mode
    
    user_id = update.effective_user.id
    current_mode = get_user_chat_mode(user_id)
    
    if not is_cli_available():
        await update.message.reply_text(
            "⚠️ <b>Cursor CLI 未安裝</b>\n\n"
            "此指令僅適用於 CLI 模式。",
            parse_mode="HTML"
        )
        return
    
    cli = get_cli_agent()
    chat_id = cli.get_user_chat_id(str(user_id))
    
    if chat_id:
        mode_text = "CLI 模式" if current_mode == "cli" else f"{current_mode} 模式 (CLI 有對話記錄)"
        await update.message.reply_text(
            f"💬 <b>對話上下文資訊</b>\n\n"
            f"🆔 對話 ID: <code>{chat_id}</code>\n"
            f"⚡ 目前模式: {mode_text}\n\n"
            f"<b>說明:</b>\n"
            f"• 對話具有記憶功能，可延續上下文\n"
            f"• 使用 <code>/newchat</code> 清除記憶\n"
            f"• 對話記錄儲存在 Cursor 伺服器",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "💬 <b>對話上下文資訊</b>\n\n"
            "🔹 目前沒有活躍的對話\n\n"
            "發送訊息後將自動建立新對話，\n"
            "並開始記錄上下文。",
            parse_mode="HTML"
        )


# ============================================
# v0.4 Feature Commands
# ============================================


@authorized_only
async def verbose_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /verbose command - Detailed output control.
    
    Usage:
        /verbose - Show status
        /verbose on - Enable verbose mode
        /verbose off - Disable verbose mode
        /verbose level <0-3> - Set verbosity level
        /verbose tokens on|off - Toggle token display
    """
    from ..core.verbose import get_verbose_manager, VerbosityLevel
    
    user_id = str(update.effective_user.id)
    args = context.args or []
    manager = get_verbose_manager()
    
    if not args:
        # Show status
        config = manager.get_config(user_id)
        status_icon = "✅" if config.enabled else "⬜"
        level_names = ["OFF", "LOW", "MEDIUM", "HIGH"]
        level_name = level_names[config.level.value]
        
        text = (
            "🔍 <b>Verbose Mode</b>\n\n"
            f"狀態: {status_icon} {'啟用' if config.enabled else '停用'}\n"
            f"等級: <b>{level_name}</b> ({config.level.value}/3)\n\n"
            "<b>選項:</b>\n"
            f"• 顯示 Token: {'✓' if config.show_tokens else '✗'}\n"
            f"• 顯示時間: {'✓' if config.show_timing else '✗'}\n"
            f"• 顯示模型: {'✓' if config.show_model_info else '✗'}\n\n"
            "<b>指令:</b>\n"
            "<code>/verbose on</code> - 啟用\n"
            "<code>/verbose off</code> - 停用\n"
            "<code>/verbose level &lt;0-3&gt;</code> - 設定等級\n"
            "<code>/verbose tokens on|off</code> - 切換 Token 顯示"
        )
        await update.message.reply_text(text, parse_mode="HTML")
        return
    
    action = args[0].lower()
    
    if action == "on":
        manager.set_enabled(user_id, True)
        await update.message.reply_text("✅ Verbose 模式已<b>啟用</b>", parse_mode="HTML")
    
    elif action == "off":
        manager.set_enabled(user_id, False)
        await update.message.reply_text("⬜ Verbose 模式已<b>停用</b>", parse_mode="HTML")
    
    elif action == "level" and len(args) >= 2:
        try:
            level = int(args[1])
            config = manager.set_level(user_id, level)
            level_names = ["OFF", "LOW", "MEDIUM", "HIGH"]
            await update.message.reply_text(
                f"✅ Verbose 等級設為 <b>{level_names[config.level.value]}</b> ({level})",
                parse_mode="HTML"
            )
        except (ValueError, IndexError):
            await update.message.reply_text("❌ 無效等級。請使用 0-3")
    
    elif action == "tokens" and len(args) >= 2:
        show = args[1].lower() in ("on", "true", "yes", "1")
        manager.set_option(user_id, "show_tokens", show)
        await update.message.reply_text(
            f"✅ Token 顯示已{'啟用' if show else '停用'}",
            parse_mode="HTML"
        )
    
    else:
        await update.message.reply_text(
            "用法:\n"
            "<code>/verbose on|off</code>\n"
            "<code>/verbose level &lt;0-3&gt;</code>\n"
            "<code>/verbose tokens on|off</code>",
            parse_mode="HTML"
        )


@authorized_only
async def think_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /think command - AI thinking mode control.
    
    Usage:
        /think - Show status
        /think off - Disable thinking
        /think low|medium|high|xhigh - Set thinking level
        /think show on|off - Toggle thinking display
    """
    from ..core.thinking import get_thinking_manager, ThinkingLevel, LEVEL_NAMES
    
    user_id = str(update.effective_user.id)
    args = context.args or []
    manager = get_thinking_manager()
    
    if not args:
        # Show status
        config = manager.get_config(user_id)
        status_icon = "✅" if config.is_enabled else "⬜"
        
        text = (
            "🧠 <b>Thinking Mode</b>\n\n"
            f"狀態: {status_icon} {'啟用' if config.is_enabled else '停用'}\n"
            f"等級: <b>{config.level_name}</b> ({config.level.value}/4)\n"
            f"Token 預算: {config.budget:,}\n\n"
            "<b>選項:</b>\n"
            f"• 顯示思考過程: {'✓' if config.show_thinking else '✗'}\n"
            f"• 自動調整: {'✓' if config.auto_adjust else '✗'}\n\n"
            "<b>等級說明:</b>\n"
            "• off - 不使用深度思考\n"
            "• low - 輕度推理 (~1K tokens)\n"
            "• medium - 標準推理 (~5K tokens)\n"
            "• high - 深度推理 (~10K tokens)\n"
            "• xhigh - 最大推理 (~25K tokens)\n\n"
            "<b>指令:</b>\n"
            "<code>/think &lt;level&gt;</code> - 設定等級\n"
            "<code>/think show on|off</code> - 顯示思考過程"
        )
        await update.message.reply_text(text, parse_mode="HTML")
        return
    
    action = args[0].lower()
    
    # Check if it's a level name
    valid_levels = ["off", "low", "medium", "high", "xhigh"]
    if action in valid_levels:
        success, config = manager.set_level_by_name(user_id, action)
        if success:
            await update.message.reply_text(
                f"✅ Thinking 等級設為 <b>{config.level_name}</b> (預算: {config.budget:,} tokens)",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("❌ 設定失敗")
    
    elif action == "show" and len(args) >= 2:
        show = args[1].lower() in ("on", "true", "yes", "1")
        manager.set_show_thinking(user_id, show)
        await update.message.reply_text(
            f"✅ 思考過程顯示已{'啟用' if show else '停用'}",
            parse_mode="HTML"
        )
    
    elif action == "auto" and len(args) >= 2:
        auto = args[1].lower() in ("on", "true", "yes", "1")
        config = manager.get_config(user_id)
        config.auto_adjust = auto
        await update.message.reply_text(
            f"✅ 自動調整已{'啟用' if auto else '停用'}",
            parse_mode="HTML"
        )
    
    else:
        await update.message.reply_text(
            "用法:\n"
            "<code>/think off|low|medium|high|xhigh</code>\n"
            "<code>/think show on|off</code>\n"
            "<code>/think auto on|off</code>",
            parse_mode="HTML"
        )


@authorized_only
async def alias_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /alias command - Command alias management.
    
    Usage:
        /alias - List aliases
        /alias add <name> <command> - Create alias
        /alias remove <name> - Remove alias
        /alias clear - Clear all aliases
    """
    from ..core.command_alias import get_alias_manager
    
    user_id = str(update.effective_user.id)
    args = context.args or []
    manager = get_alias_manager()
    
    if not args:
        # List aliases
        all_aliases = manager.get_all_aliases(user_id)
        user_aliases = [a for a in all_aliases if a["type"] == "user"]
        system_aliases = [a for a in all_aliases if a["type"] == "system"]
        
        text = "📎 <b>指令別名</b>\n\n"
        
        # System aliases
        if system_aliases:
            text += "<b>系統別名:</b>\n"
            for a in system_aliases[:8]:
                text += f"• <code>/{a['name']}</code> → /{a['command']}\n"
            if len(system_aliases) > 8:
                text += f"  ... 還有 {len(system_aliases) - 8} 個\n"
            text += "\n"
        
        # User aliases
        if user_aliases:
            text += f"<b>自訂別名 ({len(user_aliases)}/50):</b>\n"
            for a in user_aliases[:10]:
                text += f"• <code>/{a['name']}</code> → /{a['command']}\n"
        else:
            text += "尚未定義自訂別名。\n"
        
        text += (
            "\n<b>指令:</b>\n"
            "<code>/alias add &lt;名稱&gt; &lt;指令&gt;</code>\n"
            "<code>/alias remove &lt;名稱&gt;</code>\n"
            "<code>/alias clear</code>"
        )
        await update.message.reply_text(text, parse_mode="HTML")
        return
    
    action = args[0].lower()
    
    if action == "add" and len(args) >= 3:
        name = args[1]
        command = " ".join(args[2:])
        success, message = manager.add_alias(user_id, name, command)
        
        if success:
            await update.message.reply_text(f"✅ {_escape_html(message)}", parse_mode="HTML")
        else:
            await update.message.reply_text(f"❌ {_escape_html(message)}", parse_mode="HTML")
    
    elif action == "remove" and len(args) >= 2:
        name = args[1]
        success, message = manager.remove_alias(user_id, name)
        
        if success:
            await update.message.reply_text(f"✅ {_escape_html(message)}", parse_mode="HTML")
        else:
            await update.message.reply_text(f"❌ {_escape_html(message)}", parse_mode="HTML")
    
    elif action == "clear":
        count = manager.clear_aliases(user_id)
        await update.message.reply_text(f"✅ 已清除 {count} 個別名")
    
    else:
        await update.message.reply_text(
            "用法:\n"
            "<code>/alias add &lt;名稱&gt; &lt;指令&gt;</code>\n"
            "<code>/alias remove &lt;名稱&gt;</code>\n"
            "<code>/alias clear</code>\n\n"
            "範例:\n"
            "<code>/alias add gpt model set openai gpt-4o</code>",
            parse_mode="HTML"
        )


@authorized_only
async def notify_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /notify command - Notification settings.
    
    Usage:
        /notify - Show status
        /notify on|off - Enable/disable notifications
        /notify sound on|off - Toggle sound
        /notify quiet <start> <end> - Set quiet hours
    """
    from ..core.notifications import get_notification_manager
    
    user_id = str(update.effective_user.id)
    args = context.args or []
    manager = get_notification_manager()
    
    if not args:
        # Show status
        settings = manager.get_settings(user_id)
        status_icon = "✅" if settings.enabled else "⬜"
        
        text = (
            "🔔 <b>通知設定</b>\n\n"
            f"狀態: {status_icon} {'啟用' if settings.enabled else '停用'}\n"
            f"聲音: {'✓' if settings.sound_enabled else '✗'}\n"
            f"桌面通知: {'✓' if settings.desktop_enabled else '✗'}\n"
        )
        
        if settings.quiet_hours_start is not None:
            text += f"勿擾時段: {settings.quiet_hours_start}:00 - {settings.quiet_hours_end}:00\n"
        
        text += (
            "\n<b>指令:</b>\n"
            "<code>/notify on|off</code> - 啟用/停用\n"
            "<code>/notify sound on|off</code> - 切換聲音\n"
            "<code>/notify quiet &lt;開始&gt; &lt;結束&gt;</code> - 設定勿擾時段"
        )
        await update.message.reply_text(text, parse_mode="HTML")
        return
    
    action = args[0].lower()
    
    if action == "on":
        manager.set_enabled(user_id, True)
        await update.message.reply_text("✅ 通知已<b>啟用</b>", parse_mode="HTML")
    
    elif action == "off":
        manager.set_enabled(user_id, False)
        await update.message.reply_text("⬜ 通知已<b>停用</b>", parse_mode="HTML")
    
    elif action == "sound" and len(args) >= 2:
        enabled = args[1].lower() in ("on", "true", "yes", "1")
        manager.set_sound_enabled(user_id, enabled)
        await update.message.reply_text(
            f"✅ 通知聲音已{'啟用' if enabled else '停用'}",
            parse_mode="HTML"
        )
    
    elif action == "quiet" and len(args) >= 3:
        try:
            start = int(args[1])
            end = int(args[2])
            manager.set_quiet_hours(user_id, start, end)
            await update.message.reply_text(
                f"✅ 勿擾時段設為 {start}:00 - {end}:00",
                parse_mode="HTML"
            )
        except ValueError:
            await update.message.reply_text("❌ 請輸入有效的小時數 (0-23)")
    
    else:
        await update.message.reply_text(
            "用法:\n"
            "<code>/notify on|off</code>\n"
            "<code>/notify sound on|off</code>\n"
            "<code>/notify quiet &lt;開始小時&gt; &lt;結束小時&gt;</code>",
            parse_mode="HTML"
        )


# ============================================
# v1.1 Personal Secretary Handlers
# ============================================

@authorized_only
async def secretary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /secretary command - secretary settings."""
    from ..core.unified_commands import handle_secretary, CommandContext
    
    user = update.effective_user
    ctx = CommandContext(
        user_id=str(user.id),
        user_name=user.first_name or user.username or "用戶",
        platform="telegram",
        args=context.args or [],
    )
    
    result = await handle_secretary(ctx)
    await update.message.reply_text(result.message)


@authorized_only
async def briefing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /briefing command - daily briefing."""
    from ..core.unified_commands import handle_briefing, CommandContext
    
    user = update.effective_user
    ctx = CommandContext(
        user_id=str(user.id),
        user_name=user.first_name or user.username or "用戶",
        platform="telegram",
        args=context.args or [],
    )
    
    result = await handle_briefing(ctx)
    await update.message.reply_text(result.message)


@authorized_only
async def todo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /todo command - task management."""
    from ..core.unified_commands import handle_todo, CommandContext
    
    user = update.effective_user
    ctx = CommandContext(
        user_id=str(user.id),
        user_name=user.first_name or user.username or "用戶",
        platform="telegram",
        args=context.args or [],
    )
    
    result = await handle_todo(ctx)
    await update.message.reply_text(result.message)


@authorized_only
async def book_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /book command - booking assistant."""
    from ..core.unified_commands import handle_book, CommandContext
    
    user = update.effective_user
    ctx = CommandContext(
        user_id=str(user.id),
        user_name=user.first_name or user.username or "用戶",
        platform="telegram",
        args=context.args or [],
    )
    
    result = await handle_book(ctx)
    await update.message.reply_text(result.message)


def setup_core_handlers(app) -> None:
    """
    Setup core feature handlers.

    Args:
        app: Telegram Application instance
    """
    # Mode switching command
    app.add_handler(CommandHandler("mode", mode_handler))
    
    # Chat context management (CLI)
    app.add_handler(CommandHandler("newchat", newchat_handler))
    app.add_handler(CommandHandler("chatinfo", chatinfo_handler))
    
    # Agent command
    app.add_handler(CommandHandler("agent", agent_handler))
    
    # Model selection command
    app.add_handler(CommandHandler("model", model_handler))
    
    # Model selection callback handler
    app.add_handler(CallbackQueryHandler(
        model_callback_handler,
        pattern=r"^model_"
    ))
    
    # CLI Model selection command
    app.add_handler(CommandHandler("climodel", climodel_handler))
    
    # CLI Model selection callback handler
    app.add_handler(CallbackQueryHandler(
        climodel_callback_handler,
        pattern=r"^climodel_"
    ))
    
    # Memory commands
    app.add_handler(CommandHandler("memory", memory_handler))
    
    # Session management commands (ClawdBot-style)
    app.add_handler(CommandHandler("session", session_handler))
    app.add_handler(CommandHandler("new", new_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("compact", compact_handler))

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
    
    # v0.3 New feature commands
    app.add_handler(CommandHandler("doctor", doctor_handler))
    app.add_handler(CommandHandler("sessions", sessions_handler))
    app.add_handler(CommandHandler("patch", patch_handler))
    app.add_handler(CommandHandler("policy", policy_handler))
    app.add_handler(CommandHandler("tts", tts_handler))
    
    # v0.3 Additional commands
    app.add_handler(CommandHandler("broadcast", broadcast_handler))
    app.add_handler(CommandHandler("usage", usage_handler))
    app.add_handler(CommandHandler("permissions", permissions_handler))
    app.add_handler(CommandHandler("perm", permissions_handler))  # Alias
    app.add_handler(CommandHandler("elevate", elevate_handler))
    
    # v0.3 Extended commands
    app.add_handler(CommandHandler("lock", lock_handler))
    app.add_handler(CommandHandler("location", location_handler))
    app.add_handler(CommandHandler("loc", location_handler))  # Alias
    app.add_handler(CommandHandler("route", route_handler))
    
    # v0.3 New commands
    app.add_handler(CommandHandler("presence", presence_handler))
    app.add_handler(CommandHandler("gateway", gateway_handler))
    app.add_handler(CommandHandler("agents", agents_handler))
    
    # v0.3 Platform integration commands
    app.add_handler(CommandHandler("whatsapp", whatsapp_handler))
    app.add_handler(CommandHandler("wa", whatsapp_handler))  # Alias
    app.add_handler(CommandHandler("teams", teams_handler))
    app.add_handler(CommandHandler("tailscale", tailscale_handler))
    app.add_handler(CommandHandler("ts", tailscale_handler))  # Alias
    app.add_handler(CommandHandler("imessage", imessage_handler))
    app.add_handler(CommandHandler("imsg", imessage_handler))  # Alias
    app.add_handler(CommandHandler("line", line_handler))
    app.add_handler(CommandHandler("menubar", menubar_handler))
    app.add_handler(CommandHandler("control", control_handler))
    app.add_handler(CommandHandler("ctrl", control_handler))  # Alias
    
    # v0.4 Feature commands
    app.add_handler(CommandHandler("verbose", verbose_handler))
    app.add_handler(CommandHandler("v", verbose_handler))  # Alias
    app.add_handler(CommandHandler("think", think_handler))
    app.add_handler(CommandHandler("th", think_handler))  # Alias
    app.add_handler(CommandHandler("alias", alias_handler))
    app.add_handler(CommandHandler("notify", notify_handler))
    app.add_handler(CommandHandler("notif", notify_handler))  # Alias
    
    # v1.1 Personal Secretary commands
    app.add_handler(CommandHandler("secretary", secretary_handler))
    app.add_handler(CommandHandler("sec", secretary_handler))  # Alias
    app.add_handler(CommandHandler("briefing", briefing_handler))
    app.add_handler(CommandHandler("daily", briefing_handler))  # Alias
    app.add_handler(CommandHandler("todo", todo_handler))
    app.add_handler(CommandHandler("task", todo_handler))  # Alias
    app.add_handler(CommandHandler("book", book_handler))
    app.add_handler(CommandHandler("booking", book_handler))  # Alias

    logger.info("Core handlers configured")


__all__ = [
    "agent_handler",
    "model_handler",
    "model_callback_handler",
    "memory_handler",
    "skills_handler",
    "schedule_handler",
    "clear_context_handler",
    "stats_handler",
    "settings_handler",
    "doctor_handler",
    "sessions_handler",
    "patch_handler",
    "policy_handler",
    "tts_handler",
    "broadcast_handler",
    "usage_handler",
    "permissions_handler",
    "elevate_handler",
    "lock_handler",
    "location_handler",
    "route_handler",
    "presence_handler",
    "gateway_handler",
    "agents_handler",
    "whatsapp_handler",
    "teams_handler",
    "tailscale_handler",
    "imessage_handler",
    "line_handler",
    "menubar_handler",
    "control_handler",
    "mode_handler",
    # v0.4 handlers
    "verbose_handler",
    "think_handler",
    # v1.1 secretary handlers
    "secretary_handler",
    "briefing_handler",
    "todo_handler",
    "book_handler",
    "alias_handler",
    "notify_handler",
    "setup_core_handlers",
]
