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
    user = ctx.user
    
    # Check Background Agent status
    status_items = []
    if settings.background_agent_enabled and settings.cursor_api_key:
        status_items.append("🟢 Background Agent")
    else:
        status_items.append("⚪ Background Agent")
    status_items.append("🟢 Discord Bot")
    
    status = " | ".join(status_items)

    content = f"""**👋 歡迎使用 CursorBot!**

您好, {user.display_name}!

CursorBot 是一個多平台 AI 編程助手，支援 **Telegram** 和 **Discord**，讓你遠端控制 Cursor AI Agent。

**📡 狀態:** {status}

**🚀 快速開始:**
1️⃣ 使用 `/repo` 選擇 GitHub 倉庫
2️⃣ 直接發送問題或使用 `/ask`
3️⃣ AI Agent 會自動執行任務並回報結果

**✨ 核心功能:**
• **AI 編程** - 發送問題讓 AI 自動編程
• **多平台** - Telegram + Discord 同步
• **記憶系統** - `/memory` 儲存常用資訊
• **技能系統** - `/skills` 查看可用技能
• **瀏覽器工具** - 網頁自動化
• **Agent Loop** - 自主任務執行

**📋 常用指令:**
`/help` - 完整指令說明
`/status` - 系統狀態
`/repo` - 設定倉庫
`/tasks` - 我的任務
`/memory` - 記憶管理
"""

    buttons = [
        ButtonRow().add("📁 選擇倉庫", callback_data="repos_list")
                   .add("📋 我的任務", callback_data="tasks_list"),
        ButtonRow().add("🧠 記憶", callback_data="memory_list")
                   .add("🎯 技能", callback_data="skills_list"),
        ButtonRow().add("🤖 Agent", callback_data="agent_menu")
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
• `/status` - 查看系統狀態
• `/stats` - 使用統計

━━━━━━━━━━━━━━━━━━━━━━
**🤖 AI 任務（Background Agent）**
━━━━━━━━━━━━━━━━━━━━━━
• `/ask <問題>` - 發送問題給 AI Agent
• `/repo <owner/repo>` - 切換 GitHub 倉庫
• `/repos` - 查看帳號中的倉庫
• `/tasks` - 查看我的任務列表
• `/result <ID>` - 查看任務結果

*💡 直接發送訊息也可以與 AI 對話*

━━━━━━━━━━━━━━━━━━━━━━
**🧠 記憶系統**
━━━━━━━━━━━━━━━━━━━━━━
• `/memory` - 查看我的記憶
• `/memory add <key> <value>` - 新增記憶
• `/memory get <key>` - 取得記憶
• `/memory del <key>` - 刪除記憶
• `/clear` - 清除對話上下文

━━━━━━━━━━━━━━━━━━━━━━
**🎯 技能系統**
━━━━━━━━━━━━━━━━━━━━━━
• `/skills` - 查看可用技能
• `/calc <expression>` - 計算表達式
• `/remind <time> <msg>` - 設定提醒
• `/translate <lang> <text>` - 翻譯文字

━━━━━━━━━━━━━━━━━━━━━━
**🌐 多平台支援**
━━━━━━━━━━━━━━━━━━━━━━
• **Discord** - 你正在使用
• **Telegram** - 相同功能

━━━━━━━━━━━━━━━━━━━━━━
**💡 使用提示**
━━━━━━━━━━━━━━━━━━━━━━
• 直接發送訊息即可與 AI 對話
• 使用按鈕可以快速操作
• Telegram 和 Discord 功能同步
"""

    if interaction:
        await interaction.followup.send(content)
    else:
        await ctx.reply(content)


async def handle_status(ctx: MessageContext, interaction=None) -> None:
    """Handle /status command."""
    user_id = ctx.user.id

    # Check Background Agent
    if settings.background_agent_enabled and settings.cursor_api_key:
        bg_status = "🟢 已啟用"
        tracker = get_task_tracker()
        running = len(tracker.get_pending_tasks())
    else:
        bg_status = "⚪ 未啟用"
        running = 0

    # Get current repo
    current_repo = get_discord_user_repo(user_id)
    repo_display = current_repo.split("/")[-1] if current_repo else "未設定"

    content = f"""**📊 系統狀態**

**Background Agent:** {bg_status}
**目前倉庫:** {repo_display}
**執行中任務:** {running}
**平台:** Discord
"""

    buttons = [
        ButtonRow().add("📁 我的倉庫", callback_data="repos_list")
                   .add("📋 我的任務", callback_data="tasks_list"),
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
    channel.add_slash_command("status", "查看系統狀態", 
        lambda ctx, i: handle_status(ctx, i))
    channel.add_slash_command("tasks", "查看我的任務", 
        lambda ctx, i: handle_tasks(ctx, i))
    channel.add_slash_command("skills", "查看可用技能", 
        lambda ctx, i: handle_skills(ctx, i))

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

**🤖 AI 任務**
`/ask <問題>` - 發送問題給 AI
`/repo <owner/repo>` - 設定倉庫
`/tasks` - 查看任務

**🧠 記憶系統**
`/memory` - 查看記憶
`/memory add <key> <value>` - 新增

**🎯 技能**
`/skills` - 查看技能
`/calc <expr>` - 計算

使用 `/help` 查看完整說明"""

    if interaction:
        await interaction.followup.send(content, ephemeral=True)
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
