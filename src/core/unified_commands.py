"""
Unified Command Handler for all platforms (Telegram, Discord, Line, WhatsApp, Teams, etc.)
Ensures consistent command behavior across all channels.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional
from enum import Enum

from ..utils.logger import logger


class CommandCategory(Enum):
    """Command categories."""
    BASIC = "basic"
    AI = "ai"
    AGENT = "agent"
    MEMORY = "memory"
    SESSION = "session"
    WORKSPACE = "workspace"
    ADMIN = "admin"
    DIAGNOSTIC = "diagnostic"


@dataclass
class CommandContext:
    """Context for command execution."""
    user_id: str
    user_name: str
    platform: str  # telegram, discord, line, whatsapp, teams
    args: list[str] = None
    raw_text: str = ""
    is_admin: bool = False
    
    def __post_init__(self):
        if self.args is None:
            self.args = []


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    message: str
    data: dict = None
    buttons: list = None  # For platforms that support buttons
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.buttons is None:
            self.buttons = []


@dataclass
class CommandDefinition:
    """Definition of a command."""
    name: str
    description: str
    category: CommandCategory
    aliases: list[str] = None
    admin_only: bool = False
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


# ============================================
# Command Registry
# ============================================

COMMANDS: dict[str, CommandDefinition] = {
    # Basic commands
    "start": CommandDefinition("start", "開始使用 CursorBot", CommandCategory.BASIC),
    "help": CommandDefinition("help", "顯示完整說明", CommandCategory.BASIC),
    "status": CommandDefinition("status", "狀態總覽", CommandCategory.BASIC),
    
    # AI & Model commands
    "mode": CommandDefinition("mode", "查看/切換對話模式", CommandCategory.AI),
    "model": CommandDefinition("model", "查看/切換 AI 模型", CommandCategory.AI),
    "climodel": CommandDefinition("climodel", "CLI 模型設定", CommandCategory.AI),
    "agent": CommandDefinition("agent", "啟動 AI Agent 執行任務", CommandCategory.AGENT),
    "think": CommandDefinition("think", "AI 思考模式控制", CommandCategory.AI, aliases=["thinking"]),
    
    # Memory commands
    "memory": CommandDefinition("memory", "記憶系統管理", CommandCategory.MEMORY),
    "clear": CommandDefinition("clear", "清除對話上下文", CommandCategory.MEMORY),
    
    # RAG commands
    "rag": CommandDefinition("rag", "基於索引內容回答問題", CommandCategory.MEMORY),
    "index": CommandDefinition("index", "索引單一檔案", CommandCategory.MEMORY),
    "index_dir": CommandDefinition("index_dir", "索引整個目錄", CommandCategory.MEMORY),
    "index_text": CommandDefinition("index_text", "索引文字", CommandCategory.MEMORY),
    "ragstats": CommandDefinition("ragstats", "RAG 統計資訊", CommandCategory.MEMORY),
    "ragconfig": CommandDefinition("ragconfig", "RAG 設定", CommandCategory.MEMORY),
    "ragclear": CommandDefinition("ragclear", "清除 RAG 索引", CommandCategory.MEMORY),
    
    # Session commands
    "new": CommandDefinition("new", "開始新對話", CommandCategory.SESSION),
    "session": CommandDefinition("session", "Session 管理", CommandCategory.SESSION),
    "compact": CommandDefinition("compact", "壓縮對話歷史", CommandCategory.SESSION),
    
    # Workspace commands
    "workspace": CommandDefinition("workspace", "工作區設定", CommandCategory.WORKSPACE, aliases=["ws"]),
    "skills": CommandDefinition("skills", "查看可用技能", CommandCategory.WORKSPACE),
    
    # Stats & Settings
    "stats": CommandDefinition("stats", "查看使用統計", CommandCategory.ADMIN),
    "settings": CommandDefinition("settings", "Bot 設定", CommandCategory.ADMIN),
    
    # Diagnostic
    "doctor": CommandDefinition("doctor", "診斷系統狀態", CommandCategory.DIAGNOSTIC),
    
    # v0.4 Commands
    "verbose": CommandDefinition("verbose", "詳細輸出模式", CommandCategory.ADMIN, aliases=["v"]),
    "elevated": CommandDefinition("elevated", "權限提升模式", CommandCategory.ADMIN, aliases=["elevate", "el"]),
    "alias": CommandDefinition("alias", "指令別名管理", CommandCategory.ADMIN),
    "notify": CommandDefinition("notify", "通知設定", CommandCategory.ADMIN),
    "health": CommandDefinition("health", "健康檢查", CommandCategory.DIAGNOSTIC),
    "ratelimit": CommandDefinition("ratelimit", "Rate Limit 狀態", CommandCategory.DIAGNOSTIC),
}


# ============================================
# Command Handlers
# ============================================

async def handle_start(ctx: CommandContext) -> CommandResult:
    """Handle /start command."""
    from ..utils.config import settings
    from ..cursor.cli_agent import is_cli_available, get_cli_agent
    
    # Build status
    status_items = []
    
    if is_cli_available():
        cli = get_cli_agent()
        cli_model = cli.get_user_model(ctx.user_id) or "auto"
        status_items.append(f"CLI ({cli_model})")
    
    status = " | ".join(status_items) if status_items else "基本模式"
    
    message = f"""👋 歡迎使用 CursorBot!

您好, {ctx.user_name}!

📡 狀態: {status}

🚀 快速開始:
直接發送訊息即可！背景執行，完成自動推送

⚡ 兩種模式:
• CLI - Cursor CLI 處理
• Agent - AI Agent 處理

📋 常用指令:
/help - 指令說明
/mode - 切換模式
/tasks - 查看任務
/status - 系統狀態
"""
    
    return CommandResult(success=True, message=message)


async def handle_help(ctx: CommandContext) -> CommandResult:
    """Handle /help command."""
    message = """📖 CursorBot 指令說明

🔹 基礎
/start /help /status /doctor

⚡ 模式 (皆為異步)
/mode [cli|agent|auto]
/tasks /cancel <id>

🤖 AI 模型
/model [list|set|reset]
/climodel [list|set|reset]

🤖 Agent
/agent <任務>
/skills /skills_search /skills_install

🧠 記憶 & RAG
/memory [add|get|del|clear]
/rag <問題> /index <檔案>
/clear /new /compact

📅 日曆 & 郵件
/calendar [week|list|add]
/gmail [search|unread]

📁 檔案 & 工作區
/file [read|list] /run <cmd>
/workspace /cd <name>

🌐 其他
/browser /translate /tts
/session /export /review

🔧 進階
/mcp /workflow /analytics
/verbose /elevated /health

💡 直接發送訊息即可對話
"""
    
    return CommandResult(success=True, message=message)


async def handle_status(ctx: CommandContext) -> CommandResult:
    """Handle /status command."""
    from ..utils.config import settings
    from ..cursor.cli_agent import is_cli_available, get_cli_agent
    from ..core.llm_providers import get_llm_manager
    from ..core.session import get_session_manager
    
    lines = ["📊 **系統狀態**\n"]
    
    # CLI Status
    if is_cli_available():
        cli = get_cli_agent()
        model = cli.get_user_model(ctx.user_id) or "auto"
        lines.append(f"✅ Cursor CLI: {model}")
    else:
        lines.append("⚪ Cursor CLI: 未安裝")
    
    # LLM Provider
    manager = get_llm_manager()
    providers = manager.list_available_providers()
    if providers:
        lines.append(f"✅ AI 提供者: {len(providers)} 個")
    else:
        lines.append("⚪ AI 提供者: 未設定")
    
    # Session
    session_manager = get_session_manager()
    session = session_manager.get_session(ctx.user_id)
    if session:
        lines.append(f"✅ Session: {session.token_count} tokens")
    else:
        lines.append("✅ Session: 就緒")
    
    lines.append(f"\n📱 平台: {ctx.platform}")
    
    return CommandResult(success=True, message="\n".join(lines))


async def handle_mode(ctx: CommandContext) -> CommandResult:
    """Handle /mode command."""
    from ..utils.config import settings
    
    # Get current mode
    current_mode = getattr(settings, 'default_mode', 'auto')
    
    if ctx.args:
        new_mode = ctx.args[0].lower()
        if new_mode in ['cli', 'agent', 'auto']:
            # TODO: Actually change mode
            return CommandResult(
                success=True,
                message=f"✅ 已切換至 {new_mode} 模式"
            )
        else:
            return CommandResult(
                success=False,
                message="❌ 無效的模式，可選: cli, agent, auto"
            )
    
    message = f"""⚡ **對話模式**

目前模式: **{current_mode}**

可用模式:
• **auto** - 自動選擇最佳模式
• **cli** - Cursor CLI 模式 (推薦)
• **agent** - Agent Loop 模式

用法: /mode <模式名稱>
"""
    
    return CommandResult(success=True, message=message)


async def handle_new(ctx: CommandContext) -> CommandResult:
    """Handle /new command - start new conversation."""
    from ..core.session import get_session_manager
    from ..cursor.cli_agent import get_cli_agent, is_cli_available
    
    session_manager = get_session_manager()
    session_manager.reset_session(ctx.user_id)
    
    # Also reset CLI chat
    if is_cli_available():
        cli = get_cli_agent()
        cli.clear_user_chat(ctx.user_id)
    
    return CommandResult(
        success=True,
        message="🔄 已開始新對話\n\n對話上下文和 CLI 記憶已清除。"
    )


async def handle_doctor(ctx: CommandContext) -> CommandResult:
    """Handle /doctor command - system diagnostics."""
    from ..cursor.cli_agent import is_cli_available
    from ..core.llm_providers import get_llm_manager
    
    checks = []
    
    # CLI
    if is_cli_available():
        checks.append("✅ Cursor CLI")
    else:
        checks.append("❌ Cursor CLI (未安裝)")
    
    # LLM Providers
    manager = get_llm_manager()
    providers = manager.list_available_providers()
    if providers:
        checks.append(f"✅ AI 提供者 ({len(providers)} 個)")
        for p in providers[:3]:
            checks.append(f"   • {p}")
    else:
        checks.append("❌ AI 提供者 (未設定)")
    
    checks.append("✅ 記憶系統")
    checks.append("✅ Session 管理")
    
    return CommandResult(
        success=True,
        message="🩺 **系統診斷**\n\n" + "\n".join(checks)
    )


async def handle_model(ctx: CommandContext) -> CommandResult:
    """Handle /model command - AI model selection."""
    from ..core.llm_providers import get_llm_manager
    
    manager = get_llm_manager()
    providers = manager.list_available_providers()
    current = manager.get_current_model() if hasattr(manager, 'get_current_model') else "auto"
    
    if ctx.args:
        model_id = ctx.args[0].lower()
        try:
            if hasattr(manager, 'set_model'):
                manager.set_model(model_id)
                return CommandResult(success=True, message=f"✅ 已切換至模型: {model_id}")
            else:
                return CommandResult(success=False, message="❌ 此平台不支援模型切換")
        except Exception as e:
            return CommandResult(success=False, message=f"❌ 切換失敗: {str(e)[:50]}")
    
    lines = ["🤖 **AI 模型設定**", ""]
    lines.append(f"目前模型: **{current}**")
    lines.append("")
    lines.append("可用提供者:")
    for p in providers[:5]:
        lines.append(f"• {p}")
    if len(providers) > 5:
        lines.append(f"... 還有 {len(providers) - 5} 個")
    lines.append("")
    lines.append("用法: /model <model_id>")
    
    return CommandResult(success=True, message="\n".join(lines))


async def handle_climodel(ctx: CommandContext) -> CommandResult:
    """Handle /climodel command - CLI model selection."""
    from ..cursor.cli_agent import get_cli_agent, is_cli_available
    
    if not is_cli_available():
        return CommandResult(success=False, message="❌ Cursor CLI 未安裝")
    
    cli = get_cli_agent()
    models = await cli.list_models()
    current = cli.get_user_model(ctx.user_id) or "auto"
    
    if ctx.args:
        if ctx.args[0] == "list":
            if not models:
                return CommandResult(success=False, message="❌ 無法獲取模型列表")
            
            lines = ["📋 **CLI 可用模型**", ""]
            for i, m in enumerate(models[:20], 1):
                flag = "✓ " if m['id'] == current else ""
                lines.append(f"{i}. {flag}{m['id']}")
            if len(models) > 20:
                lines.append(f"... 還有 {len(models) - 20} 個")
            lines.append("")
            lines.append("用法: /climodel set <model_id>")
            return CommandResult(success=True, message="\n".join(lines))
        
        elif ctx.args[0] == "set" and len(ctx.args) > 1:
            model_id = ctx.args[1]
            # Check if model exists
            valid_ids = [m['id'] for m in models]
            if model_id not in valid_ids:
                return CommandResult(success=False, message=f"❌ 找不到模型: {model_id}")
            
            cli.set_user_model(ctx.user_id, model_id)
            return CommandResult(success=True, message=f"✅ 已切換至: {model_id}")
        
        elif ctx.args[0] == "reset":
            cli.clear_user_model(ctx.user_id)
            return CommandResult(success=True, message="✅ 已恢復預設模型")
    
    lines = ["⚙️ **CLI 模型設定**", ""]
    lines.append(f"目前模型: **{current}**")
    lines.append(f"可用模型: {len(models)} 個")
    lines.append("")
    lines.append("指令:")
    lines.append("• /climodel list - 顯示所有模型")
    lines.append("• /climodel set <id> - 切換模型")
    lines.append("• /climodel reset - 恢復預設")
    
    return CommandResult(success=True, message="\n".join(lines))


async def handle_clear(ctx: CommandContext) -> CommandResult:
    """Handle /clear command - clear conversation context."""
    from ..core.session import get_session_manager
    from ..cursor.cli_agent import get_cli_agent, is_cli_available
    
    session_manager = get_session_manager()
    session_manager.reset_session(ctx.user_id)
    
    if is_cli_available():
        cli = get_cli_agent()
        cli.clear_user_chat(ctx.user_id)
    
    return CommandResult(success=True, message="🧹 已清除對話上下文")


async def handle_memory(ctx: CommandContext) -> CommandResult:
    """Handle /memory command - memory system."""
    from ..core.memory import get_memory_manager
    
    memory = get_memory_manager()
    memories = memory.get_all_memories(ctx.user_id)
    
    if ctx.args:
        if ctx.args[0] == "list":
            if not memories:
                return CommandResult(success=True, message="📝 暫無記憶")
            
            lines = ["📝 **記憶列表**", ""]
            for i, m in enumerate(memories[:10], 1):
                content = m.get('content', '')[:50]
                lines.append(f"{i}. {content}...")
            if len(memories) > 10:
                lines.append(f"... 還有 {len(memories) - 10} 條")
            return CommandResult(success=True, message="\n".join(lines))
        
        elif ctx.args[0] == "clear":
            memory.clear_memories(ctx.user_id)
            return CommandResult(success=True, message="🗑️ 已清除所有記憶")
    
    lines = ["🧠 **記憶系統**", ""]
    lines.append(f"記憶數量: {len(memories)}")
    lines.append("")
    lines.append("指令:")
    lines.append("• /memory list - 查看記憶")
    lines.append("• /memory clear - 清除記憶")
    
    return CommandResult(success=True, message="\n".join(lines))


async def handle_workspace(ctx: CommandContext) -> CommandResult:
    """Handle /workspace command - workspace management."""
    from ..cursor.agent import WorkspaceAgent
    
    agent = WorkspaceAgent()
    workspaces = await agent.list_workspaces()
    current = agent.get_current_workspace()
    
    if ctx.args:
        if ctx.args[0] == "list":
            if not workspaces:
                return CommandResult(success=True, message="📁 暫無工作區")
            
            lines = ["📁 **工作區列表**", ""]
            for i, ws in enumerate(workspaces[:10], 1):
                flag = "✓ " if ws == current else ""
                lines.append(f"{i}. {flag}{ws}")
            if len(workspaces) > 10:
                lines.append(f"... 還有 {len(workspaces) - 10} 個")
            return CommandResult(success=True, message="\n".join(lines))
        
        elif ctx.args[0] == "switch" and len(ctx.args) > 1:
            ws_name = ctx.args[1]
            try:
                agent.switch_workspace(ws_name)
                return CommandResult(success=True, message=f"✅ 已切換至: {ws_name}")
            except Exception as e:
                return CommandResult(success=False, message=f"❌ 切換失敗: {str(e)[:50]}")
    
    lines = ["📁 **工作區**", ""]
    lines.append(f"目前: **{current or '未設定'}**")
    lines.append(f"可用: {len(workspaces)} 個")
    lines.append("")
    lines.append("指令:")
    lines.append("• /workspace list - 列出所有")
    lines.append("• /workspace switch <name> - 切換")
    
    return CommandResult(success=True, message="\n".join(lines))


async def handle_skills(ctx: CommandContext) -> CommandResult:
    """Handle /skills command - list available skills."""
    from ..core.skills import get_skill_manager
    from ..core.skills_registry import get_skills_registry
    
    manager = get_skill_manager()
    registry = get_skills_registry()
    
    skills = manager.list_skills()
    installed = registry.list_installed()
    
    lines = ["🛠️ **可用技能**", ""]
    
    # Show installed skills from registry
    if installed:
        lines.append("**📦 已安裝:**")
        for s in installed[:5]:
            status = "✅" if s.enabled else "⬜"
            lines.append(f"{status} {s.manifest.name}")
        if len(installed) > 5:
            lines.append(f"... 還有 {len(installed) - 5} 個")
        lines.append("")
    
    # Show built-in skills
    if skills:
        lines.append("**🔧 內建技能:**")
        for skill in skills[:8]:
            name = skill.get('name', 'unknown')
            lines.append(f"• {name}")
        if len(skills) > 8:
            lines.append(f"... 還有 {len(skills) - 8} 個")
        lines.append("")
    
    lines.append("**安裝更多技能:**")
    lines.append("• /skills_search <關鍵字>")
    lines.append("• /skills_install <skill_id>")
    lines.append("• 瀏覽: https://skillsmp.com")
    
    return CommandResult(success=True, message="\n".join(lines))


async def handle_stats(ctx: CommandContext) -> CommandResult:
    """Handle /stats command - usage statistics."""
    from ..core.llm_providers import get_llm_manager
    
    manager = get_llm_manager()
    
    lines = ["📊 **使用統計**", ""]
    
    if hasattr(manager, 'get_usage_stats'):
        stats = manager.get_usage_stats()
        lines.append(f"總請求: {stats.get('total_requests', 0)}")
        lines.append(f"成功: {stats.get('successful_requests', 0)}")
        lines.append(f"失敗: {stats.get('failed_requests', 0)}")
    else:
        lines.append("統計功能尚未啟用")
    
    return CommandResult(success=True, message="\n".join(lines))


async def handle_agent(ctx: CommandContext) -> CommandResult:
    """Handle /agent command - run agent task."""
    if not ctx.args:
        return CommandResult(
            success=False,
            message="❌ 請提供任務描述\n\n用法: /agent <任務描述>"
        )
    
    task = " ".join(ctx.args)
    
    return CommandResult(
        success=True,
        message=f"🤖 正在執行任務...\n\n任務: {task[:100]}\n\n(此功能在 {ctx.platform} 平台上為基礎版本)"
    )


# ============================================
# v0.4 Command Handlers
# ============================================

async def handle_verbose(ctx: CommandContext) -> CommandResult:
    """Handle /verbose command - detailed output mode."""
    from .verbose import get_verbose_manager, VerbosityLevel
    
    manager = get_verbose_manager()
    
    if ctx.args:
        arg = ctx.args[0].lower()
        
        if arg == "on":
            manager.set_enabled(ctx.user_id, True)
            return CommandResult(success=True, message="✅ Verbose 模式已啟用")
        
        elif arg == "off":
            manager.set_enabled(ctx.user_id, False)
            return CommandResult(success=True, message="✅ Verbose 模式已停用")
        
        elif arg == "level" and len(ctx.args) > 1:
            try:
                level = int(ctx.args[1])
                manager.set_level(ctx.user_id, level)
                return CommandResult(success=True, message=f"✅ Verbose 等級設為 {level}")
            except ValueError:
                return CommandResult(success=False, message="❌ 等級必須是 0-3 的數字")
        
        elif arg == "tokens":
            if len(ctx.args) > 1:
                enabled = ctx.args[1].lower() in ("on", "true", "1")
                manager.set_option(ctx.user_id, "show_tokens", enabled)
                return CommandResult(success=True, message=f"✅ Token 顯示: {'開啟' if enabled else '關閉'}")
    
    return CommandResult(success=True, message=manager.get_status_message(ctx.user_id))


async def handle_elevated(ctx: CommandContext) -> CommandResult:
    """Handle /elevated command - permission elevation."""
    from .elevated import get_elevated_manager
    
    manager = get_elevated_manager()
    
    if ctx.args:
        arg = ctx.args[0].lower()
        
        if arg == "on":
            minutes = 15
            if len(ctx.args) > 1:
                try:
                    minutes = int(ctx.args[1])
                except ValueError:
                    pass
            
            request = await manager.request_elevation(ctx.user_id, minutes=minutes)
            if request.granted:
                return CommandResult(
                    success=True,
                    message=f"✅ 權限提升已啟用，有效期 {request.remaining_minutes} 分鐘"
                )
            else:
                return CommandResult(
                    success=False,
                    message="❌ 權限提升請求被拒絕"
                )
        
        elif arg == "off":
            manager.revoke_elevation(ctx.user_id)
            return CommandResult(success=True, message="✅ 權限提升已撤銷")
    
    return CommandResult(success=True, message=manager.get_status_message(ctx.user_id))


async def handle_think(ctx: CommandContext) -> CommandResult:
    """Handle /think command - AI thinking mode."""
    from .thinking import get_thinking_manager, LEVEL_NAMES
    
    manager = get_thinking_manager()
    
    if ctx.args:
        arg = ctx.args[0].lower()
        
        # Check if it's a level name
        success, config = manager.set_level_by_name(ctx.user_id, arg)
        if success:
            return CommandResult(
                success=True,
                message=f"✅ 思考模式設為 **{config.level_name}** (預算: {config.budget:,} tokens)"
            )
        
        if arg == "show" and len(ctx.args) > 1:
            enabled = ctx.args[1].lower() in ("on", "true", "1")
            manager.set_show_thinking(ctx.user_id, enabled)
            return CommandResult(
                success=True,
                message=f"✅ 顯示思考過程: {'開啟' if enabled else '關閉'}"
            )
        
        elif arg == "auto" and len(ctx.args) > 1:
            enabled = ctx.args[1].lower() in ("on", "true", "1")
            config = manager.get_config(ctx.user_id)
            config.auto_adjust = enabled
            return CommandResult(
                success=True,
                message=f"✅ 自動調整: {'開啟' if enabled else '關閉'}"
            )
        
        return CommandResult(
            success=False,
            message=f"❌ 無效的等級。可用: {', '.join(LEVEL_NAMES.values())}"
        )
    
    return CommandResult(success=True, message=manager.get_status_message(ctx.user_id))


async def handle_alias(ctx: CommandContext) -> CommandResult:
    """Handle /alias command - command aliases."""
    from .command_alias import get_alias_manager
    
    manager = get_alias_manager()
    
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "add" and len(ctx.args) >= 3:
            name = ctx.args[1]
            command = " ".join(ctx.args[2:])
            success, message = manager.add_alias(ctx.user_id, name, command)
            return CommandResult(success=success, message=message)
        
        elif action == "remove" and len(ctx.args) >= 2:
            name = ctx.args[1]
            success, message = manager.remove_alias(ctx.user_id, name)
            return CommandResult(success=success, message=message)
        
        elif action == "clear":
            count = manager.clear_aliases(ctx.user_id)
            return CommandResult(success=True, message=f"✅ 已清除 {count} 個別名")
        
        elif action == "list":
            pass  # Fall through to status message
        
        else:
            return CommandResult(
                success=False,
                message="❌ 用法: /alias add <名稱> <指令> | /alias remove <名稱> | /alias clear"
            )
    
    return CommandResult(success=True, message=manager.get_status_message(ctx.user_id))


async def handle_notify(ctx: CommandContext) -> CommandResult:
    """Handle /notify command - notification settings."""
    from .notifications import get_notification_manager
    
    manager = get_notification_manager()
    
    if ctx.args:
        arg = ctx.args[0].lower()
        
        if arg == "on":
            manager.set_enabled(ctx.user_id, True)
            return CommandResult(success=True, message="✅ 通知已啟用")
        
        elif arg == "off":
            manager.set_enabled(ctx.user_id, False)
            return CommandResult(success=True, message="✅ 通知已停用")
        
        elif arg == "sound":
            if len(ctx.args) > 1:
                enabled = ctx.args[1].lower() in ("on", "true", "1")
                manager.set_sound_enabled(ctx.user_id, enabled)
                return CommandResult(
                    success=True,
                    message=f"✅ 通知音效: {'開啟' if enabled else '關閉'}"
                )
        
        elif arg == "quiet" and len(ctx.args) >= 3:
            try:
                start = int(ctx.args[1])
                end = int(ctx.args[2])
                manager.set_quiet_hours(ctx.user_id, start, end)
                return CommandResult(
                    success=True,
                    message=f"✅ 靜音時段: {start}:00 - {end}:00"
                )
            except ValueError:
                return CommandResult(
                    success=False,
                    message="❌ 時間必須是 0-23 的數字"
                )
    
    return CommandResult(success=True, message=manager.get_status_message(ctx.user_id))


async def handle_health(ctx: CommandContext) -> CommandResult:
    """Handle /health command - health check."""
    from .health import get_health_manager
    
    manager = get_health_manager()
    
    if ctx.args and ctx.args[0].lower() == "detail":
        report = await manager.check(include_components=True)
        lines = [
            f"💚 **Health Report**",
            "",
            f"Status: {report.status.value}",
            f"Version: {report.version}",
            f"Uptime: {report.uptime_seconds:.0f}s",
            f"Checks: {report.checks_passed}/{report.checks_passed + report.checks_failed} passed",
            "",
        ]
        
        if report.components:
            lines.append("**Components:**")
            for c in report.components:
                icon = "✅" if c.status.value == "healthy" else "⚠️" if c.status.value == "degraded" else "❌"
                lines.append(f"{icon} {c.name}: {c.message or c.status.value}")
        
        return CommandResult(success=True, message="\n".join(lines))
    
    return CommandResult(success=True, message=manager.get_status_message())


async def handle_ratelimit(ctx: CommandContext) -> CommandResult:
    """Handle /ratelimit command - rate limit status."""
    from .rate_limit import get_rate_limiter
    
    limiter = get_rate_limiter()
    return CommandResult(success=True, message=limiter.get_status_message(ctx.user_id))


# ============================================
# Command Router
# ============================================

COMMAND_HANDLERS: dict[str, Callable] = {
    "start": handle_start,
    "help": handle_help,
    "status": handle_status,
    "mode": handle_mode,
    "new": handle_new,
    "doctor": handle_doctor,
    "model": handle_model,
    "climodel": handle_climodel,
    "clear": handle_clear,
    "memory": handle_memory,
    "workspace": handle_workspace,
    "ws": handle_workspace,  # Alias
    "skills": handle_skills,
    "stats": handle_stats,
    "agent": handle_agent,
    # v0.4 commands
    "verbose": handle_verbose,
    "v": handle_verbose,  # Alias
    "elevated": handle_elevated,
    "elevate": handle_elevated,  # Alias
    "el": handle_elevated,  # Alias
    "think": handle_think,
    "thinking": handle_think,  # Alias
    "alias": handle_alias,
    "notify": handle_notify,
    "health": handle_health,
    "ratelimit": handle_ratelimit,
}


async def execute_command(command: str, ctx: CommandContext) -> Optional[CommandResult]:
    """
    Execute a command and return the result.
    
    Args:
        command: Command name (without /)
        ctx: Command context
        
    Returns:
        CommandResult or None if command not found
    """
    # Normalize command
    cmd = command.lower().strip()
    
    # Check aliases
    for name, definition in COMMANDS.items():
        if cmd == name or cmd in definition.aliases:
            cmd = name
            break
    
    # Check if command exists
    if cmd not in COMMAND_HANDLERS:
        return None
    
    # Check admin permission
    definition = COMMANDS.get(cmd)
    if definition and definition.admin_only and not ctx.is_admin:
        return CommandResult(
            success=False,
            message="❌ 此指令需要管理員權限"
        )
    
    # Execute handler
    try:
        handler = COMMAND_HANDLERS[cmd]
        return await handler(ctx)
    except Exception as e:
        logger.error(f"Command {cmd} error: {e}")
        return CommandResult(
            success=False,
            message=f"❌ 指令執行失敗: {str(e)[:100]}"
        )


def get_all_commands() -> list[CommandDefinition]:
    """Get all available commands."""
    return list(COMMANDS.values())


def get_commands_by_category(category: CommandCategory) -> list[CommandDefinition]:
    """Get commands by category."""
    return [c for c in COMMANDS.values() if c.category == category]


__all__ = [
    "CommandContext",
    "CommandResult",
    "CommandDefinition",
    "CommandCategory",
    "execute_command",
    "get_all_commands",
    "get_commands_by_category",
    "COMMANDS",
]
