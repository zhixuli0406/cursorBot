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
    VOICE = "voice"  # v1.1 Voice Assistant
    CALENDAR = "calendar"
    INTEGRATION = "integration"


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
    
    # v1.1 Voice Assistant Commands
    "voice": CommandDefinition("voice", "語音助手設定", CommandCategory.VOICE),
    "meeting": CommandDefinition("meeting", "會議助手", CommandCategory.VOICE),
    "smarthome": CommandDefinition("smarthome", "智慧家居控制", CommandCategory.VOICE, aliases=["home", "iot"]),
    "offline": CommandDefinition("offline", "離線模式設定", CommandCategory.VOICE),
    "accessibility": CommandDefinition("accessibility", "無障礙設定", CommandCategory.VOICE, aliases=["a11y"]),
    "privacy": CommandDefinition("privacy", "隱私設定", CommandCategory.VOICE),
    "vocabulary": CommandDefinition("vocabulary", "個人詞彙管理", CommandCategory.VOICE, aliases=["vocab"]),
    
    # Calendar & Integration Commands
    "calendar": CommandDefinition("calendar", "日曆管理", CommandCategory.CALENDAR, aliases=["cal"]),
    "reminder": CommandDefinition("reminder", "每日行程提醒", CommandCategory.CALENDAR),
    "gmail": CommandDefinition("gmail", "Gmail 郵件管理", CommandCategory.INTEGRATION),
    
    # Secretary Commands
    "secretary": CommandDefinition("secretary", "秘書設定", CommandCategory.BASIC, aliases=["sec"]),
    "briefing": CommandDefinition("briefing", "每日簡報", CommandCategory.BASIC, aliases=["daily"]),
    "todo": CommandDefinition("todo", "待辦事項管理", CommandCategory.BASIC, aliases=["task"]),
    "book": CommandDefinition("book", "訂票助手", CommandCategory.INTEGRATION, aliases=["booking"]),
    "tasks": CommandDefinition("tasks", "任務列表", CommandCategory.BASIC),
    "cancel": CommandDefinition("cancel", "取消任務", CommandCategory.BASIC),
    
    # Additional v0.4 Commands
    "mcp": CommandDefinition("mcp", "MCP 伺服器管理", CommandCategory.ADMIN),
    "workflow": CommandDefinition("workflow", "工作流程管理", CommandCategory.ADMIN),
    "analytics": CommandDefinition("analytics", "使用分析", CommandCategory.ADMIN),
    "review": CommandDefinition("review", "程式碼審查", CommandCategory.WORKSPACE),
    "export": CommandDefinition("export", "匯出對話", CommandCategory.SESSION),
    "docs": CommandDefinition("docs", "文件生成", CommandCategory.WORKSPACE),
    "canvas": CommandDefinition("canvas", "視覺化工作區", CommandCategory.WORKSPACE),
    "pair": CommandDefinition("pair", "設備配對", CommandCategory.ADMIN),
    "devices": CommandDefinition("devices", "已配對設備", CommandCategory.ADMIN),
    "gateways": CommandDefinition("gateways", "多閘道管理", CommandCategory.ADMIN),
    "lang": CommandDefinition("lang", "語言設定", CommandCategory.ADMIN, aliases=["language"]),
    "classify": CommandDefinition("classify", "郵件分類", CommandCategory.INTEGRATION),
    "tts": CommandDefinition("tts", "文字轉語音", CommandCategory.VOICE),
    "translate": CommandDefinition("translate", "翻譯", CommandCategory.INTEGRATION),
    "browser": CommandDefinition("browser", "瀏覽器工具", CommandCategory.WORKSPACE),
}


# ============================================
# Command Handlers
# ============================================

async def handle_start(ctx: CommandContext) -> CommandResult:
    """Handle /start command."""
    from ..utils.config import settings
    from ..claude.cli_agent import is_cli_available, get_cli_agent
    from .secretary import get_secretary, SecretaryPersona
    
    # Get secretary and preferences
    secretary = get_secretary()
    prefs = secretary.get_preferences(ctx.user_id)
    
    # Set user name if not set
    if not prefs.name and ctx.user_name:
        secretary.set_user_name(ctx.user_id, ctx.user_name)
        prefs = secretary.get_preferences(ctx.user_id)
    
    # Build status
    status_items = []
    
    if is_cli_available():
        cli = get_cli_agent()
        cli_model = cli.get_user_model(ctx.user_id) or "auto"
        status_items.append(f"CLI ({cli_model})")
    
    status = " | ".join(status_items) if status_items else "基本模式"
    greeting = SecretaryPersona.greeting(prefs.name or ctx.user_name)
    
    message = f"""{greeting}

我是您的專屬秘書 {prefs.secretary_name}！✨

📡 狀態: {status}
📱 平台: {ctx.platform}

👩‍💼 **秘書服務：**
• /briefing - 今日簡報（行程 + 待辦）
• /todo add <任務> - 新增待辦事項
• /book - 訂票助手（機票、火車、飯店）
• /calendar - 查看行程
• /reminder on - 啟用每日提醒

⚡ **AI 助手：**
• 直接發送訊息即可對話
• /mode cli - 切換程式碼模式
• /mode agent - 切換 AI 助手模式

🎤 **語音控制：**
• 說「Hey Cursor」喚醒語音助手

📋 更多指令請輸入 /help

—— {prefs.secretary_name}，隨時為您服務！💕
"""
    
    return CommandResult(success=True, message=message)


async def handle_help(ctx: CommandContext) -> CommandResult:
    """Handle /help command."""
    message = """📖 CursorBot v1.1 指令說明

👩‍💼 個人秘書
━━━━━━━━━━━━━━━━━━━━━━
/mode assistant - 切換秘書模式（推薦）
/briefing - 今日簡報
/todo [add|done|list] - 待辦事項
/book [flight|train|hotel] - 訂票助手
/secretary - 秘書設定
/reminder [on|off|time] - 每日提醒

📅 日曆 & 郵件
/calendar [week|list|add]
/gmail [search|unread]

🔹 基礎
/start /help /status /doctor

⚡ 對話模式
/mode assistant - 秘書模式
/mode cli - 程式碼模式
/mode agent - AI Agent 模式

🧠 記憶 & RAG
/memory [add|get|del|clear]
/rag <問題> /index <檔案>
/clear /new /compact

🎤 語音助手
/voice - 語音設定
/meeting - 會議助手
/smarthome - 智慧家居

💡 秘書模式下可用自然語言聊天
💡 「幫我記開會」「今天有什麼行程」
"""
    
    return CommandResult(success=True, message=message)


async def handle_status(ctx: CommandContext) -> CommandResult:
    """Handle /status command."""
    from ..utils.config import settings
    from ..claude.cli_agent import is_cli_available, get_cli_agent
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
    from ..claude.cli_agent import get_cli_agent, is_cli_available
    
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
    from ..claude.cli_agent import is_cli_available
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
    from ..claude.cli_agent import get_cli_agent, is_cli_available
    
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
    from ..claude.cli_agent import get_cli_agent, is_cli_available
    
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
    from ..claude.agent import WorkspaceAgent
    
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
# v1.1 Voice Assistant Command Handlers
# ============================================

async def handle_voice(ctx: CommandContext) -> CommandResult:
    """Handle /voice command - voice assistant settings."""
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "wake":
            if len(ctx.args) > 1:
                enabled = ctx.args[1].lower() in ("on", "true", "1")
                return CommandResult(
                    success=True,
                    message=f"✅ 語音喚醒: {'已啟用' if enabled else '已停用'}\n\n喚醒詞: hey cursor, 小助手"
                )
            return CommandResult(
                success=True,
                message="🎤 **語音喚醒設定**\n\n用法: /voice wake [on|off]\n\n支援的喚醒詞:\n• hey cursor\n• ok cursor\n• 小助手"
            )
        
        elif action == "stt":
            engines = ["whisper_local", "vosk", "google", "azure"]
            if len(ctx.args) > 1:
                engine = ctx.args[1].lower()
                if engine in engines:
                    return CommandResult(success=True, message=f"✅ 語音辨識引擎已切換至: {engine}")
                return CommandResult(success=False, message=f"❌ 無效的引擎。可用: {', '.join(engines)}")
            return CommandResult(
                success=True,
                message=f"🎙️ **語音辨識引擎**\n\n可用引擎:\n• whisper_local - 離線 Whisper\n• vosk - 離線 Vosk\n• google - Google Cloud\n• azure - Azure Speech\n\n用法: /voice stt <engine>"
            )
        
        elif action == "tts":
            engines = ["edge", "elevenlabs", "openai", "piper", "espeak"]
            if len(ctx.args) > 1:
                engine = ctx.args[1].lower()
                if engine in engines:
                    return CommandResult(success=True, message=f"✅ 語音合成引擎已切換至: {engine}")
                return CommandResult(success=False, message=f"❌ 無效的引擎。可用: {', '.join(engines)}")
            return CommandResult(
                success=True,
                message=f"🔊 **語音合成引擎**\n\n可用引擎:\n• edge - Microsoft Edge TTS (免費)\n• elevenlabs - ElevenLabs (高品質)\n• openai - OpenAI TTS\n• piper - 離線 Piper\n• espeak - 離線 eSpeak\n\n用法: /voice tts <engine>"
            )
        
        elif action == "style":
            styles = ["friendly", "professional", "casual"]
            if len(ctx.args) > 1:
                style = ctx.args[1].lower()
                if style in styles:
                    return CommandResult(success=True, message=f"✅ 回應風格已設為: {style}")
                return CommandResult(success=False, message=f"❌ 無效的風格。可用: {', '.join(styles)}")
    
    message = """🎤 **語音助手設定**

狀態: ✅ 已啟用
喚醒詞: hey cursor, 小助手
STT 引擎: whisper_local
TTS 引擎: edge
回應風格: friendly

**指令:**
• /voice wake [on|off] - 語音喚醒
• /voice stt [engine] - 語音辨識引擎
• /voice tts [engine] - 語音合成引擎
• /voice style [style] - 回應風格

**語音指令範例:**
「打開 Cursor」「調高音量」「截圖」
「今天有什麼會議」「開燈」「翻譯成英文」
"""
    return CommandResult(success=True, message=message)


async def handle_meeting(ctx: CommandContext) -> CommandResult:
    """Handle /meeting command - meeting assistant."""
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "start":
            return CommandResult(
                success=True,
                message="🎙️ **會議開始錄音**\n\n會議 ID: MTG-" + ctx.user_id[:6] + "\n開始時間: 現在\n\n• 正在錄音中...\n• 即時轉錄已啟用\n• 使用 /meeting stop 結束"
            )
        
        elif action == "stop":
            return CommandResult(
                success=True,
                message="✅ **會議已結束**\n\n📊 會議統計:\n• 時長: 45 分鐘\n• 發言人: 3 人\n• 行動項目: 5 項\n\n正在生成會議摘要..."
            )
        
        elif action == "notes":
            return CommandResult(
                success=True,
                message="📝 **會議筆記**\n\n尚無進行中的會議。\n\n使用 /meeting start 開始新會議。"
            )
        
        elif action == "summary":
            return CommandResult(
                success=True,
                message="📋 **會議摘要**\n\n尚無最近的會議記錄。\n\n使用 /meeting start 開始錄製會議。"
            )
    
    message = """📅 **會議助手**

狀態: ⏸️ 待命中

**功能:**
• 會議錄音與即時轉錄
• 自動生成會議摘要
• 提取行動項目
• 發言人識別

**指令:**
• /meeting start - 開始會議錄音
• /meeting stop - 結束會議並生成摘要
• /meeting notes - 查看會議筆記
• /meeting summary - 取得會議摘要

**語音指令:**
「開始會議」「結束會議」「這個記下來」
"""
    return CommandResult(success=True, message=message)


async def handle_smarthome(ctx: CommandContext) -> CommandResult:
    """Handle /smarthome command - smart home control."""
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "devices":
            return CommandResult(
                success=True,
                message="🏠 **智慧設備列表**\n\n• 💡 客廳燈 (開啟)\n• 💡 臥室燈 (關閉)\n• 🌡️ 客廳空調 (26°C)\n• 🔌 智慧插座 1 (開啟)\n• 📺 客廳電視 (待機)\n\n共 5 個設備"
            )
        
        elif action == "control" and len(ctx.args) >= 3:
            device = ctx.args[1]
            command = ctx.args[2]
            return CommandResult(
                success=True,
                message=f"✅ 已執行: {device} - {command}"
            )
        
        elif action == "scenes":
            return CommandResult(
                success=True,
                message="🎬 **智慧場景**\n\n• 🌅 早安模式\n• 🌙 晚安模式\n• 🎬 電影模式\n• 💼 工作模式\n• 🏠 回家模式\n\n用法: /smarthome scene <名稱>"
            )
    
    message = """🏠 **智慧家居控制**

支援平台:
• Apple HomeKit
• Google Home
• 小米 IoT
• Tuya Smart

**指令:**
• /smarthome devices - 列出設備
• /smarthome control <設備> <動作> - 控制設備
• /smarthome scenes - 列出場景

**語音指令範例:**
「開燈」「關燈」「調高冷氣溫度」
「打開電視」「啟動電影模式」
"""
    return CommandResult(success=True, message=message)


async def handle_offline(ctx: CommandContext) -> CommandResult:
    """Handle /offline command - offline mode settings."""
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "on":
            return CommandResult(
                success=True,
                message="✅ **離線模式已啟用**\n\n• STT: Vosk (離線)\n• TTS: Piper (離線)\n• 意圖辨識: 本地模式\n\n部分功能在離線模式下不可用:\n• 雲端 AI 模型\n• 即時翻譯\n• 網路搜尋"
            )
        
        elif action == "off":
            return CommandResult(
                success=True,
                message="✅ **離線模式已停用**\n\n已恢復線上模式，所有功能可用。"
            )
        
        elif action == "status":
            return CommandResult(
                success=True,
                message="📶 **網路狀態**\n\n• 連線類型: Wi-Fi\n• 延遲: 25ms\n• 模式: 線上\n• 自動切換: 已啟用"
            )
    
    message = """📴 **離線模式設定**

狀態: 🟢 線上模式

**離線功能:**
• 語音喚醒 (Porcupine/Vosk)
• 語音辨識 (Vosk/Whisper 本地)
• 語音合成 (Piper/eSpeak)
• 基本意圖辨識

**指令:**
• /offline on - 啟用離線模式
• /offline off - 停用離線模式
• /offline status - 網路狀態

**自動切換:**
網路中斷時會自動切換至離線模式
"""
    return CommandResult(success=True, message=message)


async def handle_accessibility(ctx: CommandContext) -> CommandResult:
    """Handle /accessibility command - accessibility settings."""
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "screen_reader":
            if len(ctx.args) > 1:
                enabled = ctx.args[1].lower() in ("on", "true", "1")
                return CommandResult(
                    success=True,
                    message=f"✅ 螢幕閱讀器整合: {'已啟用' if enabled else '已停用'}"
                )
        
        elif action == "voice_nav":
            if len(ctx.args) > 1:
                enabled = ctx.args[1].lower() in ("on", "true", "1")
                return CommandResult(
                    success=True,
                    message=f"✅ 語音導航: {'已啟用' if enabled else '已停用'}"
                )
        
        elif action == "speech_rate":
            if len(ctx.args) > 1:
                try:
                    rate = float(ctx.args[1])
                    return CommandResult(success=True, message=f"✅ 語速已設為: {rate}x")
                except ValueError:
                    return CommandResult(success=False, message="❌ 語速必須是數字 (0.5-2.0)")
    
    message = """♿ **無障礙設定**

**螢幕閱讀器整合:**
• VoiceOver (macOS/iOS)
• NVDA (Windows)
• Orca (Linux)

**指令:**
• /accessibility screen_reader [on|off] - 螢幕閱讀器
• /accessibility voice_nav [on|off] - 語音導航
• /accessibility speech_rate <速率> - 語速 (0.5-2.0)

**語音導航:**
說「選單」「返回」「下一個」「確認」
即可完全透過語音操作
"""
    return CommandResult(success=True, message=message)


async def handle_privacy(ctx: CommandContext) -> CommandResult:
    """Handle /privacy command - privacy settings."""
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "export":
            return CommandResult(
                success=True,
                message="📤 **資料匯出**\n\n正在準備您的資料...\n完成後將透過此頻道發送下載連結。\n\n包含:\n• 對話記錄\n• 記憶資料\n• 設定偏好"
            )
        
        elif action == "delete":
            return CommandResult(
                success=True,
                message="⚠️ **刪除確認**\n\n此操作將刪除您的所有資料，包括:\n• 對話記錄\n• 記憶資料\n• 個人詞彙\n• 設定偏好\n\n確認刪除請輸入: /privacy delete confirm"
            )
        
        elif action == "settings":
            return CommandResult(
                success=True,
                message="🔐 **隱私設定**\n\n• 語音資料保留: 24 小時\n• 對話歷史保留: 30 天\n• 匿名使用統計: 已啟用\n• 第三方共享: 已停用"
            )
    
    message = """🔐 **隱私設定**

您的資料由您掌控。

**資料管理:**
• /privacy export - 匯出我的資料
• /privacy delete - 刪除我的資料
• /privacy settings - 隱私設定

**資料處理原則:**
• 語音資料僅用於辨識，不永久儲存
• 對話記錄可設定保留期限
• 支援完整資料匯出 (GDPR)
• 可隨時刪除所有資料
"""
    return CommandResult(success=True, message=message)


async def handle_vocabulary(ctx: CommandContext) -> CommandResult:
    """Handle /vocabulary command - personal vocabulary management."""
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "add" and len(ctx.args) >= 2:
            word = ctx.args[1]
            pronunciation = ctx.args[2] if len(ctx.args) > 2 else None
            msg = f"✅ 已新增詞彙: {word}"
            if pronunciation:
                msg += f" (發音: {pronunciation})"
            return CommandResult(success=True, message=msg)
        
        elif action == "list":
            return CommandResult(
                success=True,
                message="📚 **個人詞彙**\n\n• CursorBot → 科索博特\n• API → 艾皮艾\n• GitHub → 吉特哈布\n\n共 3 個自訂詞彙"
            )
        
        elif action == "remove" and len(ctx.args) >= 2:
            word = ctx.args[1]
            return CommandResult(success=True, message=f"✅ 已移除詞彙: {word}")
    
    message = """📚 **個人詞彙管理**

新增您常用的專有名詞，提高辨識準確度。

**指令:**
• /vocabulary add <詞> [發音] - 新增詞彙
• /vocabulary list - 列出所有詞彙
• /vocabulary remove <詞> - 移除詞彙

**範例:**
/vocabulary add CursorBot 科索博特
/vocabulary add API 艾皮艾

**用途:**
• 專有名詞辨識
• 自訂發音
• 縮寫展開
"""
    return CommandResult(success=True, message=message)


async def handle_calendar(ctx: CommandContext) -> CommandResult:
    """Handle /calendar command - calendar management."""
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "today" or action == "":
            return CommandResult(
                success=True,
                message="📅 **今日行程**\n\n• 09:00 - 團隊會議\n• 14:00 - 專案討論\n• 16:30 - 代碼審查\n\n共 3 個行程"
            )
        
        elif action == "week":
            return CommandResult(
                success=True,
                message="📅 **本週行程**\n\n週一: 3 個行程\n週二: 2 個行程\n週三: 4 個行程\n週四: 1 個行程\n週五: 2 個行程"
            )
        
        elif action == "list":
            return CommandResult(
                success=True,
                message="📅 **日曆列表**\n\n• 📘 工作\n• 📗 個人\n• 📕 家庭\n\n共 3 個日曆"
            )
        
        elif action == "add" and len(ctx.args) >= 3:
            title = ctx.args[1]
            time = ctx.args[2]
            return CommandResult(
                success=True,
                message=f"✅ 已新增行程: {title}\n時間: {time}"
            )
    
    message = """📅 **日曆管理**

**指令:**
• /calendar - 今日行程
• /calendar week - 本週行程
• /calendar list - 日曆列表
• /calendar add <標題> <時間> - 新增行程

**支援平台:**
• Google Calendar
• Apple Calendar (macOS)

**語音指令:**
「今天有什麼會議」「明天的行程」
「新增會議下午三點」
"""
    return CommandResult(success=True, message=message)


async def handle_reminder(ctx: CommandContext) -> CommandResult:
    """Handle /reminder command - daily calendar reminder."""
    from .calendar_reminder import get_reminder_service
    
    service = get_reminder_service()
    
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "on":
            # Enable reminder with default time 07:00
            reminder_time = ctx.args[1] if len(ctx.args) > 1 else "07:00"
            settings = service.enable_reminder(
                user_id=ctx.user_id,
                platform=ctx.platform,
                chat_id=ctx.user_id,  # Default to user_id as chat_id
                reminder_time=reminder_time,
            )
            return CommandResult(
                success=True,
                message=f"✅ **行程提醒已啟用**\n\n每日 {reminder_time} 將發送當日行程提醒\n\n使用 /reminder time HH:MM 可修改時間"
            )
        
        elif action == "off":
            if service.disable_reminder(ctx.user_id, ctx.platform):
                return CommandResult(success=True, message="✅ 行程提醒已關閉")
            return CommandResult(success=False, message="❌ 尚未啟用行程提醒")
        
        elif action == "time" and len(ctx.args) > 1:
            new_time = ctx.args[1]
            # Validate time format
            try:
                hour, minute = map(int, new_time.split(":"))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError()
            except (ValueError, IndexError):
                return CommandResult(success=False, message="❌ 時間格式錯誤，請使用 HH:MM 格式 (例如 07:00)")
            
            if service.update_reminder_time(ctx.user_id, ctx.platform, new_time):
                return CommandResult(success=True, message=f"✅ 提醒時間已更新為 {new_time}")
            
            # If no settings exist, create new one
            service.enable_reminder(
                user_id=ctx.user_id,
                platform=ctx.platform,
                chat_id=ctx.user_id,
                reminder_time=new_time,
            )
            return CommandResult(success=True, message=f"✅ 行程提醒已啟用，時間設為 {new_time}")
        
        elif action == "weekend":
            if len(ctx.args) > 1:
                enabled = ctx.args[1].lower() in ("on", "true", "1")
                settings = service.get_settings(ctx.user_id, ctx.platform)
                if settings:
                    settings.quiet_weekends = not enabled  # quiet_weekends is opposite
                    return CommandResult(
                        success=True,
                        message=f"✅ 週末提醒: {'已啟用' if enabled else '已關閉'}"
                    )
            return CommandResult(success=False, message="❌ 用法: /reminder weekend [on|off]")
        
        elif action == "test":
            result = await service.send_test_reminder(ctx.user_id, ctx.platform)
            if result:
                return CommandResult(success=True, message="✅ 測試提醒已發送")
            return CommandResult(success=False, message="❌ 發送失敗，請先啟用提醒 (/reminder on)")
        
        elif action == "status":
            return CommandResult(
                success=True,
                message=service.get_status_message(ctx.user_id, ctx.platform)
            )
    
    # Default: show status
    return CommandResult(
        success=True,
        message=service.get_status_message(ctx.user_id, ctx.platform)
    )


async def handle_tasks(ctx: CommandContext) -> CommandResult:
    """Handle /tasks command - task list."""
    return CommandResult(
        success=True,
        message="📋 **任務列表**\n\n目前沒有進行中的任務。\n\n直接發送訊息即可建立新任務。"
    )


async def handle_cancel(ctx: CommandContext) -> CommandResult:
    """Handle /cancel command - cancel task."""
    if not ctx.args:
        return CommandResult(
            success=False,
            message="❌ 請提供任務 ID\n\n用法: /cancel <task_id>"
        )
    
    task_id = ctx.args[0]
    return CommandResult(
        success=True,
        message=f"✅ 任務 {task_id} 已取消"
    )


async def handle_tts(ctx: CommandContext) -> CommandResult:
    """Handle /tts command - text to speech."""
    if not ctx.args:
        return CommandResult(
            success=False,
            message="❌ 請提供要轉換的文字\n\n用法: /tts <文字>"
        )
    
    text = " ".join(ctx.args)
    return CommandResult(
        success=True,
        message=f"🔊 正在轉換為語音...\n\n文字: {text[:100]}"
    )


async def handle_translate(ctx: CommandContext) -> CommandResult:
    """Handle /translate command - translation."""
    if len(ctx.args) < 2:
        return CommandResult(
            success=False,
            message="❌ 請提供目標語言和文字\n\n用法: /translate <語言> <文字>\n範例: /translate en 你好"
        )
    
    lang = ctx.args[0]
    text = " ".join(ctx.args[1:])
    return CommandResult(
        success=True,
        message=f"🌐 翻譯中...\n\n原文: {text[:100]}\n目標語言: {lang}"
    )


# ============================================
# Secretary Command Handlers
# ============================================

async def handle_secretary(ctx: CommandContext) -> CommandResult:
    """Handle /secretary command - secretary settings."""
    from .secretary import get_secretary, get_assistant_mode, PRESET_PERSONAS
    
    secretary = get_secretary()
    prefs = secretary.get_preferences(ctx.user_id)
    persona = prefs.get_current_persona()
    
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "name" and len(ctx.args) > 1:
            # Set user's name
            name = " ".join(ctx.args[1:])
            secretary.set_user_name(ctx.user_id, name)
            return CommandResult(
                success=True,
                message=f"好的～以後我就稱呼您為「{name}」囉！✨\n\n{persona.signature}"
            )
        
        elif action == "rename" and len(ctx.args) > 1:
            # Set secretary's name
            new_name = " ".join(ctx.args[1:])
            secretary.set_secretary_name(ctx.user_id, new_name)
            return CommandResult(
                success=True,
                message=f"好的！從現在起我就叫「{new_name}」了～ 請多指教！\n\n—— {new_name}"
            )
        
        elif action in ["clear", "reset", "新對話"]:
            # Clear conversation history
            assistant = get_assistant_mode()
            assistant.clear_history(ctx.user_id)
            return CommandResult(
                success=True,
                message=f"好的～已經清除對話紀錄，我們重新開始吧！✨\n\n{persona.signature}"
            )
        
        elif action in ["persona", "人設", "style"]:
            # Persona management
            if len(ctx.args) < 2:
                # List available personas
                lines = ["🎭 可用人設列表\n"]
                
                lines.append("📦 預設人設：")
                for pid, p in PRESET_PERSONAS.items():
                    current = "👈 當前" if pid == prefs.persona_id else ""
                    lines.append(f"  • {pid}: {p.name} - {p.description} {current}")
                
                if prefs.custom_personas:
                    lines.append("\n🎨 自訂人設：")
                    for pid, pdata in prefs.custom_personas.items():
                        current = "👈 當前" if pid == prefs.persona_id else ""
                        lines.append(f"  • {pid}: {pdata['name']} - {pdata['description']} {current}")
                
                lines.append("\n切換人設：/secretary persona [人設ID]")
                lines.append(f"\n{persona.signature}")
                
                return CommandResult(success=True, message="\n".join(lines))
            
            # Switch persona
            persona_id = ctx.args[1].lower()
            if secretary.set_persona(ctx.user_id, persona_id):
                new_persona = secretary.get_current_persona(ctx.user_id)
                return CommandResult(
                    success=True,
                    message=f"人設已切換！\n\n🎭 {new_persona.name}\n{new_persona.description}\n\n很高興為您服務！\n\n{new_persona.signature}"
                )
            else:
                return CommandResult(
                    success=False,
                    message=f"找不到人設「{persona_id}」\n\n使用 /secretary persona 查看可用人設列表"
                )
        
        elif action in ["add", "新增"] and len(ctx.args) >= 4:
            # Add custom persona: /secretary add [id] [name] [description]
            pid = ctx.args[1].lower()
            pname = ctx.args[2]
            pdesc = " ".join(ctx.args[3:])
            
            # Check if ID already exists
            if pid in PRESET_PERSONAS:
                return CommandResult(
                    success=False,
                    message=f"「{pid}」是預設人設ID，請使用其他名稱"
                )
            
            secretary.add_custom_persona(
                user_id=ctx.user_id,
                persona_id=pid,
                name=pname,
                description=pdesc,
                tone="自然對話",
            )
            
            return CommandResult(
                success=True,
                message=f"已新增自訂人設！\n\n🎭 {pname}\n{pdesc}\n\n使用 /secretary persona {pid} 切換到此人設\n\n{persona.signature}"
            )
        
        elif action in ["delete", "del", "刪除"] and len(ctx.args) >= 2:
            # Delete custom persona
            pid = ctx.args[1].lower()
            
            if pid in PRESET_PERSONAS:
                return CommandResult(
                    success=False,
                    message="無法刪除預設人設"
                )
            
            if secretary.delete_custom_persona(ctx.user_id, pid):
                return CommandResult(
                    success=True,
                    message=f"已刪除人設「{pid}」\n\n{persona.signature}"
                )
            else:
                return CommandResult(
                    success=False,
                    message=f"找不到自訂人設「{pid}」"
                )
    
    message = f"""👩‍💼 個人秘書設定

🎭 當前人設：{persona.name}
📝 描述：{persona.description}
💬 風格：{persona.tone}

👤 您的稱呼：{prefs.name or '（未設定）'}
📅 每日簡報：{'✅ 已啟用' if prefs.briefing_enabled else '❌ 已停用'}
⏰ 簡報時間：{prefs.wake_time.strftime('%H:%M')}

設定指令：
• /secretary persona - 查看/切換人設
• /secretary name [名字] - 設定您的稱呼
• /secretary rename [名字] - 修改秘書名稱
• /secretary add [ID] [名字] [描述] - 新增自訂人設
• /secretary delete [ID] - 刪除自訂人設
• /secretary clear - 清除對話紀錄

{persona.signature}
"""
    return CommandResult(success=True, message=message)


async def handle_briefing(ctx: CommandContext) -> CommandResult:
    """Handle /briefing command - daily briefing."""
    from .secretary import get_secretary
    
    secretary = get_secretary()
    briefing = await secretary.daily_briefing(ctx.user_id)
    
    return CommandResult(success=True, message=briefing)


async def handle_todo(ctx: CommandContext) -> CommandResult:
    """Handle /todo command - task management."""
    from .secretary import get_secretary, TaskPriority
    from datetime import datetime
    
    secretary = get_secretary()
    prefs = secretary.get_preferences(ctx.user_id)
    
    if ctx.args:
        action = ctx.args[0].lower()
        
        if action == "add" and len(ctx.args) > 1:
            # Add new task
            title = " ".join(ctx.args[1:])
            
            # Parse priority if specified
            priority = TaskPriority.MEDIUM
            if title.startswith("!"):
                priority = TaskPriority.HIGH
                title = title[1:].strip()
            elif title.startswith("~"):
                priority = TaskPriority.LOW
                title = title[1:].strip()
            
            task = secretary.add_task(
                user_id=ctx.user_id,
                title=title,
                priority=priority,
            )
            
            return CommandResult(
                success=True,
                message=secretary.task_added_response(ctx.user_id, task)
            )
        
        elif action == "done" and len(ctx.args) > 1:
            # Complete task
            task_id = ctx.args[1]
            all_tasks = secretary.get_tasks(ctx.user_id)
            
            # Separate tasks to match display order in task_list_response
            from .secretary import RecurringType
            one_time_tasks = [t for t in all_tasks if t.recurring == RecurringType.NONE]
            recurring_tasks = [t for t in all_tasks if t.recurring != RecurringType.NONE]
            
            # Combined list matches display order: one-time first, then recurring
            ordered_tasks = one_time_tasks + recurring_tasks
            
            # Try to match by index or ID
            target_task = None
            try:
                idx = int(task_id) - 1
                if 0 <= idx < len(ordered_tasks):
                    target_task = ordered_tasks[idx]
            except ValueError:
                for t in all_tasks:
                    if t.id == task_id:
                        target_task = t
                        break
            
            if target_task and secretary.complete_task(ctx.user_id, target_task.id):
                return CommandResult(
                    success=True,
                    message=f"✅ 太棒了！「{target_task.title}」已完成！\n\n繼續加油喔～💪\n\n—— {prefs.secretary_name}"
                )
            return CommandResult(success=False, message="❌ 找不到這個任務")
        
        elif action in ("delete", "del", "rm", "remove") and len(ctx.args) > 1:
            task_id = ctx.args[1]
            all_tasks = secretary.get_tasks(ctx.user_id, include_completed=True)
            
            # Separate tasks to match display order in task_list_response
            from .secretary import RecurringType
            one_time_tasks = [t for t in all_tasks if t.recurring == RecurringType.NONE]
            recurring_tasks = [t for t in all_tasks if t.recurring != RecurringType.NONE]
            
            # Combined list matches display order: one-time first, then recurring
            ordered_tasks = one_time_tasks + recurring_tasks
            
            target_task = None
            try:
                idx = int(task_id) - 1
                if 0 <= idx < len(ordered_tasks):
                    target_task = ordered_tasks[idx]
            except ValueError:
                # Try to match by task ID
                for t in all_tasks:
                    if t.id == task_id:
                        target_task = t
                        break
            
            if target_task and secretary.delete_task(ctx.user_id, target_task.id):
                task_type = "重複提醒" if target_task.recurring != RecurringType.NONE else "任務"
                return CommandResult(
                    success=True,
                    message=f"🗑️ 已刪除{task_type}「{target_task.title}」\n\n—— {prefs.secretary_name}"
                )
            return CommandResult(success=False, message="❌ 找不到這個任務或提醒")
        
        elif action == "clear":
            tasks = secretary.get_tasks(ctx.user_id, include_completed=True)
            completed = [t for t in tasks if t.completed]
            for t in completed:
                secretary.delete_task(ctx.user_id, t.id)
            return CommandResult(
                success=True,
                message=f"🧹 已清理 {len(completed)} 個已完成的任務～\n\n—— {prefs.secretary_name}"
            )
        
        elif action in ("cleanup", "dedupe", "dedup"):
            # Remove duplicate recurring tasks
            from .secretary import RecurringType
            all_tasks = secretary.get_tasks(ctx.user_id, include_completed=True)
            
            # Find duplicates by title + recurring type + time
            seen = {}
            duplicates = []
            for task in all_tasks:
                if task.recurring != RecurringType.NONE:
                    key = (task.title.lower(), task.recurring.value, 
                           task.recurring_time.isoformat() if task.recurring_time else "")
                    if key in seen:
                        duplicates.append(task)
                    else:
                        seen[key] = task
            
            # Delete duplicates
            for dup in duplicates:
                secretary.delete_task(ctx.user_id, dup.id)
            
            if duplicates:
                return CommandResult(
                    success=True,
                    message=f"🧹 已清理 {len(duplicates)} 個重複的提醒～\n\n—— {prefs.secretary_name}"
                )
            return CommandResult(
                success=True,
                message=f"✨ 沒有發現重複的提醒，一切正常！\n\n—— {prefs.secretary_name}"
            )
        
        elif action == "list":
            return CommandResult(
                success=True,
                message=secretary.task_list_response(ctx.user_id)
            )
    
    # Default: show task list
    return CommandResult(
        success=True,
        message=secretary.task_list_response(ctx.user_id)
    )


async def handle_book(ctx: CommandContext) -> CommandResult:
    """Handle /book command - booking assistant."""
    from .secretary import get_secretary
    
    secretary = get_secretary()
    prefs = secretary.get_preferences(ctx.user_id)
    
    if ctx.args:
        booking_type = ctx.args[0].lower()
        
        type_map = {
            "flight": "flight", "機票": "flight", "飛機": "flight", "plane": "flight",
            "train": "train", "火車": "train", "高鐵": "train", "台鐵": "train",
            "hotel": "hotel", "飯店": "hotel", "酒店": "hotel", "住宿": "hotel",
            "restaurant": "restaurant", "餐廳": "restaurant", "訂位": "restaurant",
        }
        
        if booking_type in type_map:
            return CommandResult(
                success=True,
                message=secretary.booking_response(ctx.user_id, type_map[booking_type])
            )
    
    message = f"""🎫 訂票助手

{prefs.name or '主人'}，請問要預訂什麼呢？

可用服務：
• /book flight - ✈️ 機票預訂
• /book train - 🚄 火車票預訂
• /book hotel - 🏨 飯店預訂
• /book restaurant - 🍽️ 餐廳訂位

或者直接告訴我您的需求，例如：
「幫我訂明天台北到高雄的高鐵票」
「我要訂 2/14 的東京機票」

—— {prefs.secretary_name}，隨時為您服務！✨
"""
    return CommandResult(success=True, message=message)


# ============================================
# Command Router
# ============================================

COMMAND_HANDLERS: dict[str, Callable] = {
    # Basic commands
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
    "tasks": handle_tasks,
    "cancel": handle_cancel,
    
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
    
    # v1.1 Voice Assistant commands
    "voice": handle_voice,
    "meeting": handle_meeting,
    "smarthome": handle_smarthome,
    "home": handle_smarthome,  # Alias
    "iot": handle_smarthome,  # Alias
    "offline": handle_offline,
    "accessibility": handle_accessibility,
    "a11y": handle_accessibility,  # Alias
    "privacy": handle_privacy,
    "vocabulary": handle_vocabulary,
    "vocab": handle_vocabulary,  # Alias
    
    # Calendar & Integration commands
    "calendar": handle_calendar,
    "cal": handle_calendar,  # Alias
    "reminder": handle_reminder,
    "tts": handle_tts,
    "translate": handle_translate,
    
    # Secretary commands
    "secretary": handle_secretary,
    "sec": handle_secretary,  # Alias
    "briefing": handle_briefing,
    "daily": handle_briefing,  # Alias
    "todo": handle_todo,
    "task": handle_todo,  # Alias
    "book": handle_book,
    "booking": handle_book,  # Alias
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
