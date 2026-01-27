"""
Discord Command Handlers for CursorBot
Provides Discord-specific command implementations
"""

from typing import Optional

try:
    import discord
    from discord import app_commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    discord = None

from .base import MessageContext, ButtonRow, Button
from .discord_channel import DiscordChannel
from ..cursor.background_agent import get_background_agent, get_task_tracker
from ..core import get_memory_manager, get_skill_manager, get_context_manager
from ..utils.config import settings
from ..utils.logger import logger


# Store user repos (shared state)
_discord_user_repos: dict[str, str] = {}


def get_discord_user_repo(user_id: str) -> str:
    """Get user's current repo."""
    return _discord_user_repos.get(user_id, settings.cursor_github_repo)


def set_discord_user_repo(user_id: str, repo_url: str) -> None:
    """Set user's current repo."""
    _discord_user_repos[user_id] = repo_url


def _create_task_buttons(task_id: str, status: str = "running") -> list[ButtonRow]:
    """Create task action buttons."""
    row1 = ButtonRow()
    row1.add("🔗 在 Cursor 開啟", url=f"https://cursor.com/agents/{task_id}")

    row2 = ButtonRow()
    if status in ["running", "pending", "created"]:
        row2.add("🔄 重新整理", callback_data=f"task_refresh:{task_id[:8]}")
        row2.add("❌ 取消", callback_data=f"task_cancel:{task_id[:8]}", style="danger")
    else:
        row2.add("🔄 重新整理", callback_data=f"task_refresh:{task_id[:8]}")

    return [row1, row2]


async def handle_start(ctx: MessageContext, interaction=None) -> None:
    """Handle /start command."""
    from ..cursor.cli_agent import is_cli_available
    
    user = ctx.user
    
    # Check various status
    status_items = []
    
    # CLI status
    if is_cli_available():
        status_items.append("🟢 Cursor CLI")
    else:
        status_items.append("⚪ Cursor CLI")
    
    # Background Agent status
    if settings.background_agent_enabled and settings.cursor_api_key:
        status_items.append("🟢 Background Agent")
    else:
        status_items.append("⚪ Background Agent")
    
    status_items.append("🟢 Discord Bot")
    
    status = " | ".join(status_items)

    content = f"""**👋 歡迎使用 CursorBot!**

您好, {user.display_name}!

CursorBot 是一個多平台 AI 編程助手，支援 **Telegram**、**Discord**、**Line** 等平台，讓你遠端控制 Cursor AI。

**📡 狀態:** {status}

**🚀 快速開始:**
1️⃣ 使用 `/model` 選擇 AI 模型
2️⃣ 使用 `/mode` 選擇對話模式 (CLI/Agent)
3️⃣ 直接發送問題開始對話

**✨ 核心功能:**
• **Cursor CLI** - 使用官方 CLI 直接對話
• **Agent Loop** - 自主代理執行複雜任務
• **多模型支援** - OpenAI/Claude/Gemini/GLM
• **Session 管理** - 對話上下文與記憶
• **記憶系統** - `/memory` 儲存常用資訊
• **技能系統** - `/skills` 查看可用技能

**📋 常用指令:**
`/help` - 完整指令說明
`/model` - 切換 AI 模型
`/mode` - 切換對話模式
`/session` - Session 管理
`/new` - 開始新對話
`/status` - 狀態總覽
"""

    buttons = [
        ButtonRow().add("⚡ 模式", callback_data="mode_menu")
                   .add("🤖 模型", callback_data="model_menu"),
        ButtonRow().add("💬 Session", callback_data="session_menu")
                   .add("🧠 記憶", callback_data="memory_list"),
        ButtonRow().add("🎯 技能", callback_data="skills_list")
                   .add("🔧 工具", callback_data="tools_menu"),
        ButtonRow().add("📊 狀態", callback_data="status")
                   .add("❓ 幫助", callback_data="help"),
    ]

    if interaction:
        await interaction.followup.send(content, view=_create_view(buttons, ctx.channel))
    else:
        await ctx.reply(content, buttons=buttons)


async def handle_help(ctx: MessageContext, interaction=None) -> None:
    """Handle /help command."""
    content = """**📖 CursorBot 完整指令說明**

━━━━━━━━━━━━━━━━━━━━━━
**🔹 基礎指令**
━━━━━━━━━━━━━━━━━━━━━━
• `/start` - 啟動並顯示歡迎訊息
• `/help` - 顯示此說明
• `/status` - 狀態總覽

━━━━━━━━━━━━━━━━━━━━━━
**⚡ 對話模式**
━━━━━━━━━━━━━━━━━━━━━━
• `/mode` - 查看/切換對話模式
• `/mode auto` - 自動選擇最佳模式
• `/mode cli` - Cursor CLI 模式
• `/mode agent` - Agent Loop 模式

━━━━━━━━━━━━━━━━━━━━━━
**🤖 AI 模型管理**
━━━━━━━━━━━━━━━━━━━━━━
• `/model` - 查看目前 Agent 模型
• `/model list` - 列出所有可用模型
• `/model set <provider> [model]` - 切換 Agent 模型
• `/climodel` - CLI 模型設定
• `/climodel list` - 列出 CLI 可用模型
• `/climodel set <model>` - 切換 CLI 模型

**Agent 支援:** OpenAI, Claude, Gemini, GLM, Ollama
**CLI 支援:** GPT-5.2, Claude 4.5, Gemini 3, Grok

━━━━━━━━━━━━━━━━━━━━━━
**💬 Session 管理** (ClawdBot-style)
━━━━━━━━━━━━━━━━━━━━━━
• `/session` - 查看目前 session
• `/session list` - 列出所有 sessions
• `/session stats` - 統計資訊
• `/new` - 開始新對話 (重置上下文)
• `/compact` - 壓縮對話歷史

━━━━━━━━━━━━━━━━━━━━━━
**🤖 Agent Loop**
━━━━━━━━━━━━━━━━━━━━━━
• `/agent <任務>` - 自主代理執行
自動分解任務、多步驟推理

━━━━━━━━━━━━━━━━━━━━━━
**🧠 記憶系統**
━━━━━━━━━━━━━━━━━━━━━━
• `/memory` - 查看記憶
• `/memory add <key> <value>` - 新增
• `/memory get <key>` - 取得
• `/memory del <key>` - 刪除

━━━━━━━━━━━━━━━━━━━━━━
**🎯 技能系統**
━━━━━━━━━━━━━━━━━━━━━━
• `/skills` - 查看技能
• `/skills agent` - Agent 技能

━━━━━━━━━━━━━━━━━━━━━━
**📁 檔案/工作區**
━━━━━━━━━━━━━━━━━━━━━━
• `/workspace` - 工作區資訊
• `/workspace list` - 列出工作區
• `/file read <路徑>` - 讀取檔案
• `/run <命令>` - 執行命令

━━━━━━━━━━━━━━━━━━━━━━
**⏰ 排程系統**
━━━━━━━━━━━━━━━━━━━━━━
• `/schedule` - 查看排程
• `/remind <時間> <訊息>` - 設定提醒

━━━━━━━━━━━━━━━━━━━━━━
**💡 使用提示**
━━━━━━━━━━━━━━━━━━━━━━
• `/new` 開始全新對話
• `/status` 查看目前狀態
• `/compact` 壓縮過長的對話
• 直接發送訊息與 AI 對話
"""

    if interaction:
        await interaction.followup.send(content)
    else:
        await ctx.reply(content)


async def handle_status(ctx: MessageContext, interaction=None) -> None:
    """Handle /status command."""
    from ..cursor.cli_agent import is_cli_available, get_cli_agent
    from ..core.session import get_session_manager, ChatType
    
    user_id = str(ctx.user.id)
    
    # Get session info
    session_mgr = get_session_manager()
    session = session_mgr.get_session(
        user_id=user_id,
        chat_id=user_id,
        chat_type=ChatType.DM,
        channel="discord",
    )
    
    # Check CLI status
    cli_status = "❌ 未安裝"
    if is_cli_available():
        cli = get_cli_agent()
        cli_chat = cli.get_user_chat_id(user_id)
        if cli_chat:
            cli_status = f"✅ 連線中 ({cli_chat[:8]}...)"
        else:
            cli_status = "✅ 可用"

    # Check Background Agent
    if settings.background_agent_enabled and settings.cursor_api_key:
        bg_status = "✅ 已啟用"
    else:
        bg_status = "⚪ 未啟用"

    # Calculate context usage
    context_tokens = session.context_tokens if session else 0
    max_tokens = 8000
    context_pct = min(100, int(context_tokens / max_tokens * 100))
    context_bar = "█" * (context_pct // 10) + "░" * (10 - context_pct // 10)

    content = f"""**📊 狀態總覽**

━━━━━━━━━━━━━━━━━━━━━━
**對話模式**
━━━━━━━━━━━━━━━━━━━━━━
⌨️ CLI: {cli_status}
💻 Background Agent: {bg_status}

━━━━━━━━━━━━━━━━━━━━━━
**Session 狀態**
━━━━━━━━━━━━━━━━━━━━━━
🆔 {session.session_id[:12] if session else 'N/A'}...
📨 訊息: {session.message_count if session else 0}
🎫 Token: {session.total_tokens if session else 0:,}

━━━━━━━━━━━━━━━━━━━━━━
**上下文使用量**
━━━━━━━━━━━━━━━━━━━━━━
[{context_bar}] {context_pct}%
約 {context_tokens:,} / {max_tokens:,} tokens

━━━━━━━━━━━━━━━━━━━━━━
**快捷指令**
━━━━━━━━━━━━━━━━━━━━━━
`/new` - 開始新對話
`/compact` - 壓縮上下文
`/mode` - 切換模式
`/model` - 切換模型
"""

    buttons = [
        ButtonRow().add("🆕 新對話", callback_data="new_chat")
                   .add("📦 壓縮", callback_data="compact"),
        ButtonRow().add("⚡ 模式", callback_data="mode_menu")
                   .add("🤖 模型", callback_data="model_menu"),
    ]

    if interaction:
        await interaction.followup.send(content, view=_create_view(buttons, ctx.channel))
    else:
        await ctx.reply(content, buttons=buttons)


async def handle_ask(ctx: MessageContext, question: str, interaction=None) -> None:
    """Handle /ask command."""
    user_id = ctx.user.id

    # Check if Background Agent is enabled
    if not settings.background_agent_enabled or not settings.cursor_api_key:
        content = "⚠️ **Background Agent 未啟用**\n\n請設定 `CURSOR_API_KEY`"
        if interaction:
            await interaction.followup.send(content)
        else:
            await ctx.reply(content)
        return

    # Get repo
    repo_url = get_discord_user_repo(user_id)
    if not repo_url:
        content = """⚠️ **未設定 GitHub 倉庫**

使用 `/repo owner/repo-name` 設定倉庫
或點擊下方按鈕選擇倉庫
"""
        buttons = [ButtonRow().add("📁 選擇倉庫", callback_data="repos_list")]
        if interaction:
            await interaction.followup.send(content, view=_create_view(buttons, ctx.channel))
        else:
            await ctx.reply(content, buttons=buttons)
        return

    repo_name = repo_url.split("/")[-1]

    # Send initial message
    content = f"🚀 **正在啟動 Background Agent...**\n\n📁 倉庫: `{repo_name}`\n❓ 問題: {question[:80]}..."

    if interaction:
        status_msg = await interaction.followup.send(content)
    else:
        status_msg = await ctx.reply(content)

    # Create task
    try:
        bg_agent = get_background_agent(settings.cursor_api_key)
        result = await bg_agent.create_task(prompt=question, repo_url=repo_url)

        if result.get("success"):
            composer_id = result.get("composer_id", "")
            
            # Track task
            tracker = get_task_tracker()
            tracker.add_task(
                composer_id=composer_id,
                user_id=int(user_id),
                prompt=question,
                repo_url=repo_url,
            )

            buttons = _create_task_buttons(composer_id, "running")
            content = f"""✅ **任務已建立**

🆔 任務 ID: `{composer_id[:8]}`
📁 倉庫: `{repo_name}`
❓ 問題: {question[:60]}...

⏳ 正在執行中...
"""
            # Edit message
            if hasattr(status_msg, 'edit'):
                await status_msg.edit(content=content, view=_create_view(buttons, ctx.channel))

        else:
            content = f"❌ 建立任務失敗: {result.get('message', 'Unknown error')}"
            if hasattr(status_msg, 'edit'):
                await status_msg.edit(content=content)

    except Exception as e:
        logger.error(f"Ask error: {e}")
        content = f"❌ 錯誤: {str(e)[:200]}"
        if hasattr(status_msg, 'edit'):
            await status_msg.edit(content=content)


async def handle_tasks(ctx: MessageContext, interaction=None) -> None:
    """Handle /tasks command."""
    user_id = ctx.user.id
    tracker = get_task_tracker()
    all_tasks = tracker.get_user_tasks(int(user_id))

    if not all_tasks:
        content = "📋 **沒有任務記錄**\n\n直接發送訊息來建立新任務！"
        if interaction:
            await interaction.followup.send(content)
        else:
            await ctx.reply(content)
        return

    # Count by status
    running = len([t for t in all_tasks if t.get("status") in ["running", "pending", "created"]])
    completed = len([t for t in all_tasks if t.get("status") == "completed"])
    failed = len([t for t in all_tasks if t.get("status") in ["failed", "error"]])

    content = f"""**📋 我的任務**

🔄 執行中: {running}
✅ 已完成: {completed}
❌ 失敗: {failed}

**最近任務:**
"""

    for task in all_tasks[:5]:
        task_id = task.get("composer_id", "")[:8]
        status = task.get("status", "unknown")
        prompt = task.get("prompt", "")[:30] + "..."

        emoji = {
            "running": "🔄",
            "pending": "⏳",
            "completed": "✅",
            "failed": "❌",
        }.get(status, "❓")

        content += f"\n{emoji} `{task_id}`: {prompt}"

    if interaction:
        await interaction.followup.send(content)
    else:
        await ctx.reply(content)


async def handle_repo(ctx: MessageContext, repo: str = None, interaction=None) -> None:
    """Handle /repo command."""
    user_id = ctx.user.id

    if not repo:
        # Show current repo
        current = get_discord_user_repo(user_id)
        if current:
            repo_name = current.split("/")[-1]
            content = f"📁 **目前倉庫:** {repo_name}\n\n使用 `/repo owner/repo-name` 切換倉庫"
        else:
            content = "📁 **未設定倉庫**\n\n使用 `/repo owner/repo-name` 設定倉庫"

        buttons = [ButtonRow().add("📁 選擇倉庫", callback_data="repos_list")]
        if interaction:
            await interaction.followup.send(content, view=_create_view(buttons, ctx.channel))
        else:
            await ctx.reply(content, buttons=buttons)
        return

    # Set repo
    if "/" in repo and not repo.startswith("http"):
        repo_url = f"https://github.com/{repo}"
    elif repo.startswith("http"):
        repo_url = repo
    else:
        content = "❌ 無效的倉庫格式\n\n使用: `/repo owner/repo-name`"
        if interaction:
            await interaction.followup.send(content)
        else:
            await ctx.reply(content)
        return

    set_discord_user_repo(user_id, repo_url)
    repo_name = repo_url.split("/")[-1]

    content = f"✅ **已切換倉庫**\n\n📁 {repo_name}\n\n現在可以發送任務到此倉庫。"

    buttons = [
        ButtonRow().add("🔗 在 GitHub 開啟", url=repo_url)
                   .add("💬 發送任務", callback_data="ask_new"),
    ]

    if interaction:
        await interaction.followup.send(content, view=_create_view(buttons, ctx.channel))
    else:
        await ctx.reply(content, buttons=buttons)


async def handle_memory(ctx: MessageContext, action: str = None, key: str = None, value: str = None, interaction=None) -> None:
    """Handle /memory command."""
    user_id = int(ctx.user.id)
    memory = get_memory_manager()

    if not action:
        # List memories
        memories = await memory.list_memories(user_id, limit=10)

        if not memories:
            content = """🧠 **我的記憶**

目前沒有儲存任何記憶。

**用法:**
`/memory add <key> <value>` - 新增記憶
`/memory get <key>` - 取得記憶
`/memory del <key>` - 刪除記憶
"""
        else:
            content = "🧠 **我的記憶**\n\n"
            for m in memories:
                v = str(m['value'])[:40] + "..." if len(str(m['value'])) > 40 else m['value']
                content += f"• `{m['key']}`: {v}\n"

        if interaction:
            await interaction.followup.send(content)
        else:
            await ctx.reply(content)

    elif action == "add" and key and value:
        await memory.remember(user_id, key, value)
        content = f"✅ 已記住: `{key}`"
        if interaction:
            await interaction.followup.send(content)
        else:
            await ctx.reply(content)

    elif action == "get" and key:
        v = await memory.recall(user_id, key)
        if v:
            content = f"🧠 `{key}`: {v}"
        else:
            content = f"❌ 找不到記憶: {key}"
        if interaction:
            await interaction.followup.send(content)
        else:
            await ctx.reply(content)

    elif action == "del" and key:
        deleted = await memory.forget(user_id, key)
        content = f"✅ 已刪除: {key}" if deleted else f"❌ 找不到記憶: {key}"
        if interaction:
            await interaction.followup.send(content)
        else:
            await ctx.reply(content)


async def handle_skills(ctx: MessageContext, interaction=None) -> None:
    """Handle /skills command."""
    skills = get_skill_manager()

    if not skills.list_skills():
        await skills.load_builtin_skills()

    skill_list = skills.list_skills()

    if not skill_list:
        content = "🎯 **技能系統**\n\n目前沒有可用的技能。"
    else:
        content = "🎯 **可用技能**\n\n"
        for skill in skill_list:
            status = "✅" if skill.enabled else "❌"
            commands = ", ".join([f"`/{c}`" for c in skill.commands[:2]])
            content += f"{status} **{skill.name}**\n   {skill.description}\n   {commands}\n\n"

    if interaction:
        await interaction.followup.send(content)
    else:
        await ctx.reply(content)


async def handle_new(ctx: MessageContext, interaction=None) -> None:
    """Handle /new command - start fresh session."""
    from ..core.session import get_session_manager, ChatType
    from ..cursor.cli_agent import get_cli_agent, is_cli_available
    
    user_id = str(ctx.user.id)
    session_mgr = get_session_manager()
    
    # Reset session
    session = session_mgr.reset_session(
        user_id=user_id,
        chat_id=user_id,
        chat_type=ChatType.DM,
        channel="discord",
    )
    
    # Clear CLI chat if available
    if is_cli_available():
        cli = get_cli_agent()
        cli.clear_user_chat(user_id)
    
    # Clear conversation context
    ctx_mgr = get_context_manager()
    user_ctx = ctx_mgr.get_context(int(user_id), int(user_id), "private")
    user_ctx.clear()
    
    content = f"""🆕 **新對話已開始**

Session ID: `{session.session_id[:12]}...`
所有對話上下文已清除。

💡 現在可以開始全新的對話了！"""
    
    if interaction:
        await interaction.followup.send(content)
    else:
        await ctx.reply(content)


async def handle_session(ctx: MessageContext, interaction=None) -> None:
    """Handle /session command."""
    from ..core.session import get_session_manager, ChatType
    from datetime import datetime
    
    user_id = str(ctx.user.id)
    session_mgr = get_session_manager()
    
    session = session_mgr.get_session(
        user_id=user_id,
        chat_id=user_id,
        chat_type=ChatType.DM,
        channel="discord",
    )
    
    status = session_mgr.get_session_status(session.session_key)
    
    # Format duration
    age_seconds = (datetime.now() - session.created_at).total_seconds()
    if age_seconds < 60:
        age_str = f"{int(age_seconds)}秒"
    elif age_seconds < 3600:
        age_str = f"{int(age_seconds / 60)}分鐘"
    elif age_seconds < 86400:
        age_str = f"{int(age_seconds / 3600)}小時"
    else:
        age_str = f"{int(age_seconds / 86400)}天"
    
    cli_info = ""
    if session.cli_chat_id:
        cli_info = f"\n🔗 CLI 對話: `{session.cli_chat_id[:12]}...`"
    
    content = f"""**💬 目前對話 Session**

━━━━━━━━━━━━━━━━━━━━━━
**基本資訊**
━━━━━━━━━━━━━━━━━━━━━━
🆔 Session ID: `{session.session_id[:12]}...`
📅 建立時間: {session.created_at.strftime('%Y-%m-%d %H:%M')}
⏱️ Session 年齡: {age_str}
📨 訊息數量: {session.message_count}
🔄 壓縮次數: {session.compaction_count}{cli_info}

━━━━━━━━━━━━━━━━━━━━━━
**Token 使用量**
━━━━━━━━━━━━━━━━━━━━━━
📥 輸入: {status['input_tokens']:,}
📤 輸出: {status['output_tokens']:,}
📊 總計: {status['total_tokens']:,}

━━━━━━━━━━━━━━━━━━━━━━
**指令**
━━━━━━━━━━━━━━━━━━━━━━
`/new` - 開始新對話
`/compact` - 壓縮對話歷史
"""

    buttons = [
        ButtonRow().add("🆕 新對話", callback_data="new_chat")
                   .add("📦 壓縮", callback_data="compact"),
    ]
    
    if interaction:
        await interaction.followup.send(content, view=_create_view(buttons, ctx.channel))
    else:
        await ctx.reply(content, buttons=buttons)


async def handle_compact(ctx: MessageContext, interaction=None) -> None:
    """Handle /compact command."""
    user_id = int(ctx.user.id)
    ctx_mgr = get_context_manager()
    user_ctx = ctx_mgr.get_context(user_id, user_id, "private")
    
    before_tokens = user_ctx.estimate_tokens()
    before_messages = len(user_ctx.messages)
    
    if before_messages < 5:
        content = "ℹ️ 對話歷史太短，不需要壓縮。\n" + f"目前只有 {before_messages} 條訊息。"
        if interaction:
            await interaction.followup.send(content)
        else:
            await ctx.reply(content)
        return
    
    # Perform compaction
    await user_ctx.compact(force=True)
    
    after_tokens = user_ctx.estimate_tokens()
    saved_tokens = before_tokens - after_tokens
    saved_messages = before_messages - len(user_ctx.messages)
    
    content = f"""✅ **對話已壓縮**

📉 訊息: {before_messages} → {len(user_ctx.messages)} (-{saved_messages})
🎫 Token: {before_tokens:,} → {after_tokens:,} (-{saved_tokens:,})
📊 節省: {int(saved_tokens / max(before_tokens, 1) * 100)}%

壓縮摘要已保存在上下文中。"""
    
    if interaction:
        await interaction.followup.send(content)
    else:
        await ctx.reply(content)


async def handle_mode(ctx: MessageContext, interaction=None) -> None:
    """Handle /mode command."""
    from ..cursor.cli_agent import is_cli_available, get_cli_agent
    
    cli_available = is_cli_available()
    bg_available = settings.background_agent_enabled and settings.cursor_api_key
    
    # Get CLI info
    cli_info = ""
    if cli_available:
        cli = get_cli_agent()
        info = await cli.check_installation()
        cli_info = f"版本: {info.get('version', 'unknown')}"
    
    content = f"""**⚡ 對話模式設定**

━━━━━━━━━━━━━━━━━━━━━━
**可用模式** (優先順序: CLI → Agent → Cursor)
━━━━━━━━━━━━━━━━━━━━━━

⌨️ **Cursor CLI** (`/mode cli`)
   使用官方 Cursor CLI (agent 指令)
   直接與 Cursor AI 互動
   ✨ 對話記憶功能
   {f'✅ 可用 ({cli_info})' if cli_available else '⚠️ 未安裝'}

🤖 **Agent Loop** (`/mode agent`)
   使用內建 AI Agent 處理對話
   支援多種 AI 模型 (OpenAI/Claude/Gemini/GLM)
   ✅ 可用

💻 **Background Agent** (`/mode cursor`)
   使用 Cursor IDE 的 Background Agent API
   {'✅ 可用' if bg_available else '⚠️ 未設定'}

━━━━━━━━━━━━━━━━━━━━━━
**使用方式**
━━━━━━━━━━━━━━━━━━━━━━
直接發送訊息即可使用選定模式。
"""

    buttons = [
        ButtonRow().add("⌨️ CLI", callback_data="set_mode_cli")
                   .add("🤖 Agent", callback_data="set_mode_agent"),
    ]
    
    if interaction:
        await interaction.followup.send(content, view=_create_view(buttons, ctx.channel))
    else:
        await ctx.reply(content, buttons=buttons)


async def handle_model(ctx: MessageContext, interaction=None) -> None:
    """Handle /model command."""
    from ..core.llm_providers import get_llm_manager
    
    user_id = str(ctx.user.id)
    manager = get_llm_manager()
    
    # Get current model for user
    current_model = manager.get_user_model(user_id) or "預設"
    
    # Get available providers
    providers = manager.list_available_providers()
    
    content = f"""**🤖 AI 模型管理**

━━━━━━━━━━━━━━━━━━━━━━
**目前模型**
━━━━━━━━━━━━━━━━━━━━━━
🎯 {current_model}

━━━━━━━━━━━━━━━━━━━━━━
**可用提供者**
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    for p in providers:
        status = "✅" if p.get('available', False) else "⚪"
        content += f"{status} **{p['name']}** - {p.get('model', 'default')}\n"
    
    content += """
━━━━━━━━━━━━━━━━━━━━━━
**使用方式**
━━━━━━━━━━━━━━━━━━━━━━
`/model list` - 列出所有可用模型
`/model set <provider>` - 切換模型
`/model reset` - 恢復預設

範例: `/model set openai gpt-4o`
"""
    
    buttons = [
        ButtonRow().add("📋 模型列表", callback_data="model_list")
                   .add("🔄 重置", callback_data="model_reset"),
    ]
    
    if interaction:
        await interaction.followup.send(content, view=_create_view(buttons, ctx.channel))
    else:
        await ctx.reply(content, buttons=buttons)


def _create_view(buttons: list[ButtonRow], channel: DiscordChannel):
    """Create Discord view from buttons."""
    if not DISCORD_AVAILABLE:
        return None
    from .discord_channel import DiscordButtonView
    return DiscordButtonView(buttons, channel._button_callback if hasattr(channel, '_button_callback') else None)


def setup_discord_handlers(channel: DiscordChannel) -> None:
    """
    Setup Discord command handlers.
    
    Args:
        channel: DiscordChannel instance
    """
    if not DISCORD_AVAILABLE:
        logger.warning("Discord not available, skipping handler setup")
        return

    # Register slash commands
    channel.add_slash_command("start", "開始使用 CursorBot", 
        lambda ctx, i: handle_start(ctx, i))
    channel.add_slash_command("help", "顯示說明", 
        lambda ctx, i: handle_help(ctx, i))
    channel.add_slash_command("status", "狀態總覽", 
        lambda ctx, i: handle_status(ctx, i))
    channel.add_slash_command("tasks", "查看我的任務", 
        lambda ctx, i: handle_tasks(ctx, i))
    channel.add_slash_command("skills", "查看可用技能", 
        lambda ctx, i: handle_skills(ctx, i))
    
    # New commands for session management
    channel.add_slash_command("new", "開始新對話 (重置上下文)",
        lambda ctx, i: handle_new(ctx, i))
    channel.add_slash_command("session", "Session 管理",
        lambda ctx, i: handle_session(ctx, i))
    channel.add_slash_command("compact", "壓縮對話歷史",
        lambda ctx, i: handle_compact(ctx, i))
    channel.add_slash_command("mode", "查看/切換對話模式",
        lambda ctx, i: handle_mode(ctx, i))
    channel.add_slash_command("model", "查看/切換 AI 模型",
        lambda ctx, i: handle_model(ctx, i))

    # Register message handler for non-command messages
    @channel.on_message
    async def on_message(ctx: MessageContext):
        # Skip commands
        if ctx.message.is_command:
            return

        # Handle as ask
        if settings.background_agent_enabled and settings.cursor_api_key:
            await handle_ask(ctx, ctx.message.content)

    # Register button handler
    @channel.on_button
    async def on_button(callback_data: str, ctx: MessageContext):
        # Get interaction from context (stored by _button_callback)
        interaction = getattr(ctx, 'interaction', None)
        
        async def send_response(content: str, ephemeral: bool = False):
            """Helper to send response via interaction or ctx."""
            if interaction:
                await interaction.followup.send(content, ephemeral=ephemeral)
            else:
                await ctx.reply(content)
        
        try:
            if callback_data == "repos_list":
                await send_response("使用 `/repo owner/repo-name` 設定倉庫\n\n例如: `/repo microsoft/vscode`")
            
            elif callback_data == "tasks_list":
                await _handle_button_tasks(ctx, interaction)
            
            elif callback_data == "status":
                await _handle_button_status(ctx, interaction)
            
            elif callback_data == "help":
                await _handle_button_help(ctx, interaction)
            
            elif callback_data.startswith("task_refresh:"):
                task_id = callback_data.split(":")[1]
                await send_response(f"🔄 正在刷新任務 `{task_id}`...")

            elif callback_data == "memory_list":
                await _handle_button_memory(ctx, interaction)

            elif callback_data == "agent_menu":
                await send_response(
                    "**🤖 Agent 功能**\n\n"
                    "• **Agent Loop** - 自主代理執行\n"
                    "• **排程任務** - `/remind`, `/schedule`\n"
                    "• **Webhook** - 外部事件觸發\n\n"
                    "使用 `/agent <任務>` 啟動 Agent Loop"
                )

            elif callback_data == "tools_menu":
                await send_response(
                    "**🔧 工具箱**\n\n"
                    "• **Browser** - `/browser navigate <URL>`\n"
                    "• **檔案操作** - `/file read <路徑>`\n"
                    "• **終端機** - `/run <命令>`"
                )
            
            elif callback_data == "mode_menu":
                from ..cursor.cli_agent import is_cli_available
                cli_available = is_cli_available()
                bg_available = settings.background_agent_enabled and settings.cursor_api_key
                
                await send_response(
                    "**⚡ 對話模式**\n\n"
                    f"⌨️ **Cursor CLI** - {'✅ 可用' if cli_available else '⚠️ 未安裝'}\n"
                    "   使用官方 CLI，支援對話記憶\n\n"
                    "🤖 **Agent Loop** - ✅ 可用\n"
                    "   使用內建 AI Agent\n\n"
                    f"💻 **Background Agent** - {'✅ 可用' if bg_available else '⚠️ 未設定'}\n"
                    "   使用 Cursor Background Agent API\n\n"
                    "使用 `/mode <mode>` 切換模式"
                )
            
            elif callback_data == "model_menu":
                await send_response(
                    "**🤖 AI 模型選擇**\n\n"
                    "**支援的提供者:**\n"
                    "• **OpenAI** - GPT-4o, GPT-4o-mini\n"
                    "• **Claude** - claude-3-5-sonnet\n"
                    "• **Gemini** - gemini-2.0-flash\n"
                    "• **GLM** - glm-4-flash\n"
                    "• **Ollama** - 本地模型\n\n"
                    "使用 `/model list` 查看所有模型\n"
                    "使用 `/model set <provider>` 切換"
                )
            
            elif callback_data == "session_menu":
                from ..core.session import get_session_manager, ChatType
                session_mgr = get_session_manager()
                user_id = str(ctx.user.id)
                session = session_mgr.get_session(
                    user_id=user_id,
                    chat_id=user_id,
                    chat_type=ChatType.DM,
                    channel="discord",
                )
                
                await send_response(
                    f"**💬 Session 管理**\n\n"
                    f"🆔 Session ID: `{session.session_id[:12]}...`\n"
                    f"📨 訊息數量: {session.message_count}\n"
                    f"🎫 Token 使用: {session.total_tokens:,}\n\n"
                    "**指令:**\n"
                    "• `/session` - 詳細資訊\n"
                    "• `/session list` - 所有 sessions\n"
                    "• `/new` - 開始新對話\n"
                    "• `/compact` - 壓縮歷史"
                )
            
            elif callback_data == "new_chat":
                from ..core.session import get_session_manager, ChatType
                from ..cursor.cli_agent import get_cli_agent, is_cli_available
                
                user_id = str(ctx.user.id)
                session_mgr = get_session_manager()
                
                # Reset session
                session = session_mgr.reset_session(
                    user_id=user_id,
                    chat_id=user_id,
                    chat_type=ChatType.DM,
                    channel="discord",
                )
                
                # Clear CLI chat
                if is_cli_available():
                    cli = get_cli_agent()
                    cli.clear_user_chat(user_id)
                
                # Clear context
                ctx_mgr = get_context_manager()
                user_ctx = ctx_mgr.get_context(int(user_id), int(user_id), "private")
                user_ctx.clear()
                
                await send_response(
                    f"🆕 **新對話已開始**\n\n"
                    f"Session ID: `{session.session_id[:12]}...`\n"
                    f"所有對話上下文已清除。"
                )
            
            elif callback_data == "compact":
                ctx_mgr = get_context_manager()
                user_id = int(ctx.user.id)
                user_ctx = ctx_mgr.get_context(user_id, user_id, "private")
                
                before_tokens = user_ctx.estimate_tokens()
                before_messages = len(user_ctx.messages)
                
                if before_messages < 5:
                    await send_response("ℹ️ 對話歷史太短，不需要壓縮。")
                    return
                
                await user_ctx.compact(force=True)
                
                after_tokens = user_ctx.estimate_tokens()
                saved = before_tokens - after_tokens
                
                await send_response(
                    f"✅ **對話已壓縮**\n\n"
                    f"📉 Token: {before_tokens:,} → {after_tokens:,} (-{saved:,})\n"
                    f"📊 節省: {int(saved / max(before_tokens, 1) * 100)}%"
                )
            
            elif callback_data == "skills_list":
                await _handle_button_skills(ctx, interaction)
            
            elif callback_data == "set_mode_cli":
                from ..cursor.cli_agent import is_cli_available
                if is_cli_available():
                    await send_response(
                        "⌨️ **已切換到 Cursor CLI 模式**\n\n"
                        "現在直接發送訊息將由 Cursor CLI 處理。\n"
                        "CLI 支援對話記憶功能。"
                    )
                else:
                    await send_response(
                        "⚠️ **Cursor CLI 未安裝**\n\n"
                        "安裝: `curl https://cursor.com/install -fsS | bash`"
                    )
            
            elif callback_data == "set_mode_agent":
                await send_response(
                    "🤖 **已切換到 Agent Loop 模式**\n\n"
                    "現在直接發送訊息將由 AI Agent 處理。\n"
                    "使用 `/model` 切換 AI 模型。"
                )
            
            elif callback_data == "model_list":
                from ..core.llm_providers import get_llm_manager
                manager = get_llm_manager()
                providers = manager.list_available_providers()
                
                content = "**📋 可用模型**\n\n"
                for p in providers:
                    status = "✅" if p.get('available', False) else "⚪"
                    content += f"{status} **{p['name']}** - {p.get('model', 'default')}\n"
                
                content += "\n使用 `/model set <provider>` 切換"
                await send_response(content)
            
            elif callback_data == "model_reset":
                from ..core.llm_providers import get_llm_manager
                user_id = str(ctx.user.id)
                manager = get_llm_manager()
                manager.clear_user_model(user_id)
                await send_response("🔄 **已恢復預設模型**")
            
            else:
                await send_response(f"未知操作: {callback_data}", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Button handler error: {e}")
            await send_response(f"❌ 處理失敗: {str(e)[:100]}", ephemeral=True)

    logger.info("Discord handlers configured")


async def _handle_button_tasks(ctx: MessageContext, interaction) -> None:
    """Handle tasks button click."""
    user_id = ctx.user.id
    tracker = get_task_tracker()
    all_tasks = tracker.get_user_tasks(int(user_id))

    if not all_tasks:
        content = "📋 **沒有任務記錄**\n\n直接發送訊息來建立新任務！"
    else:
        running = len([t for t in all_tasks if t.get("status") in ["running", "pending", "created"]])
        completed = len([t for t in all_tasks if t.get("status") == "completed"])
        failed = len([t for t in all_tasks if t.get("status") in ["failed", "error"]])

        content = f"**📋 我的任務**\n\n🔄 執行中: {running}\n✅ 已完成: {completed}\n❌ 失敗: {failed}\n\n**最近任務:**\n"

        for task in all_tasks[:5]:
            task_id = task.get("composer_id", "")[:8]
            status = task.get("status", "unknown")
            prompt = task.get("prompt", "")[:30] + "..."
            emoji = {"running": "🔄", "pending": "⏳", "completed": "✅", "failed": "❌"}.get(status, "❓")
            content += f"\n{emoji} `{task_id}`: {prompt}"

    if interaction:
        await interaction.followup.send(content)
    else:
        await ctx.reply(content)


async def _handle_button_status(ctx: MessageContext, interaction) -> None:
    """Handle status button click."""
    user_id = ctx.user.id
    
    if settings.background_agent_enabled and settings.cursor_api_key:
        bg_status = "🟢 已啟用"
        tracker = get_task_tracker()
        running = len(tracker.get_pending_tasks())
    else:
        bg_status = "⚪ 未啟用"
        running = 0

    current_repo = get_discord_user_repo(user_id)
    repo_display = current_repo.split("/")[-1] if current_repo else "未設定"

    content = f"**📊 系統狀態**\n\n**Background Agent:** {bg_status}\n**目前倉庫:** {repo_display}\n**執行中任務:** {running}\n**平台:** Discord"

    if interaction:
        await interaction.followup.send(content)
    else:
        await ctx.reply(content)


async def _handle_button_help(ctx: MessageContext, interaction) -> None:
    """Handle help button click."""
    content = """**📖 快速指令說明**

**⚡ 對話模式**
`/mode` - 查看/切換模式
`/mode cli` - CLI 模式
`/mode agent` - Agent 模式

**🤖 AI 模型**
`/model` - 查看目前模型
`/model list` - 列出所有模型

**💬 Session**
`/session` - Session 資訊
`/new` - 開始新對話
`/compact` - 壓縮對話

使用 `/help` 查看完整說明"""

    if interaction:
        await interaction.followup.send(content, ephemeral=True)
    else:
        await ctx.reply(content)


async def _handle_button_skills(ctx: MessageContext, interaction) -> None:
    """Handle skills button click."""
    skills = get_skill_manager()
    
    # Load built-in skills if not loaded
    if not skills.list_skills():
        await skills.load_builtin_skills()
    
    skill_list = skills.list_skills()
    agent_skills = skills.list_agent_skills()
    
    content = "**🎯 可用技能**\n\n"
    
    if skill_list:
        content += "**📋 指令技能:**\n"
        for skill in skill_list[:5]:
            status = "✅" if skill.enabled else "❌"
            content += f"{status} `/{skill.name}` - {skill.description[:30]}...\n"
        if len(skill_list) > 5:
            content += f"...還有 {len(skill_list) - 5} 個技能\n"
    
    if agent_skills:
        content += "\n**🤖 Agent 技能:**\n"
        for skill in agent_skills[:3]:
            status = "✅" if skill.enabled else "❌"
            content += f"{status} **{skill.name}** - {skill.description[:30]}...\n"
        if len(agent_skills) > 3:
            content += f"...還有 {len(agent_skills) - 3} 個技能\n"
    
    content += "\n使用 `/skills` 查看完整列表"
    
    if interaction:
        await interaction.followup.send(content)
    else:
        await ctx.reply(content)


async def _handle_button_memory(ctx: MessageContext, interaction) -> None:
    """Handle memory button click."""
    user_id = int(ctx.user.id)
    
    try:
        from ..core import get_memory_manager
        memory = get_memory_manager()
        memories = await memory.list_memories(user_id, limit=10)

        if not memories:
            content = """**🧠 我的記憶**

目前沒有儲存任何記憶。

**用法:**
`/memory add <key> <value>` - 新增記憶
`/memory get <key>` - 取得記憶
`/memory del <key>` - 刪除記憶"""
        else:
            content = "**🧠 我的記憶**\n\n"
            for m in memories:
                v = str(m['value'])[:30] + "..." if len(str(m['value'])) > 30 else m['value']
                content += f"• `{m['key']}`: {v}\n"

        if interaction:
            await interaction.followup.send(content)
        else:
            await ctx.reply(content)
    except Exception as e:
        logger.error(f"Memory list error: {e}")
        if interaction:
            await interaction.followup.send(f"❌ 讀取記憶失敗: {str(e)[:50]}", ephemeral=True)


__all__ = [
    "setup_discord_handlers",
    "handle_start",
    "handle_help",
    "handle_status",
    "handle_ask",
    "handle_tasks",
    "handle_repo",
    "handle_memory",
    "handle_skills",
]
