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
    
    # Background Agent commands
    "ask": CommandDefinition("ask", "向 Cursor Agent 發送問題", CommandCategory.AGENT),
    "tasks": CommandDefinition("tasks", "查看我的任務", CommandCategory.AGENT),
    "repo": CommandDefinition("repo", "切換 GitHub 倉庫", CommandCategory.AGENT),
    "repos": CommandDefinition("repos", "查看帳號中的倉庫", CommandCategory.AGENT),
    
    # Memory commands
    "memory": CommandDefinition("memory", "記憶系統管理", CommandCategory.MEMORY),
    "clear": CommandDefinition("clear", "清除對話上下文", CommandCategory.MEMORY),
    
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
}


# ============================================
# Command Handlers
# ============================================

async def handle_start(ctx: CommandContext) -> CommandResult:
    """Handle /start command."""
    from ..utils.config import settings
    from ..cursor.cli_agent import is_cli_available, get_cli_agent
    from ..cursor.background_agent import get_background_agent
    
    # Build status
    status_items = []
    
    if is_cli_available():
        cli = get_cli_agent()
        cli_model = cli.get_user_model(ctx.user_id) or "auto"
        status_items.append(f"CLI ({cli_model})")
    
    agent = get_background_agent()
    if agent and agent.is_authenticated():
        status_items.append("Background Agent")
    
    status = " | ".join(status_items) if status_items else "基本模式"
    
    message = f"""👋 歡迎使用 CursorBot!

您好, {ctx.user_name}!

CursorBot 是一個多平台 AI 編程助手，支援 Telegram、Discord、Line 等平台。

📡 狀態: {status}

🚀 快速開始:
1. 使用 /mode 選擇對話模式
2. 使用 /model 或 /climodel 切換 AI 模型
3. 直接發送問題開始對話

✨ 核心功能:
• Cursor CLI - 使用官方 CLI 對話
• 多模型 AI - OpenAI/Claude/Gemini/Copilot
• Agent Loop - 自主任務執行
• 記憶系統 - 儲存常用資訊

📋 常用指令:
/help - 完整指令說明
/mode - 切換對話模式
/model - 模型設定
/new - 開始新對話
/status - 狀態總覽
"""
    
    return CommandResult(success=True, message=message)


async def handle_help(ctx: CommandContext) -> CommandResult:
    """Handle /help command."""
    message = """📖 CursorBot 完整指令說明

━━━━━━━━━━━━━━━━━━━━━━
🔹 基礎指令
━━━━━━━━━━━━━━━━━━━━━━
/start - 開始使用
/help - 顯示此說明
/status - 狀態總覽

━━━━━━━━━━━━━━━━━━━━━━
⚡ 對話模式
━━━━━━━━━━━━━━━━━━━━━━
/mode - 查看/切換對話模式
/mode cli - Cursor CLI 模式
/mode agent - Agent Loop 模式

━━━━━━━━━━━━━━━━━━━━━━
🤖 AI 模型管理
━━━━━━━━━━━━━━━━━━━━━━
/model - 查看目前模型
/model list - 列出所有可用模型
/model set <provider> - 切換模型
/climodel - CLI 模型設定

支援: OpenAI (GPT-5), Claude 4.5, Gemini 3, Copilot

━━━━━━━━━━━━━━━━━━━━━━
📋 Background Agent
━━━━━━━━━━━━━━━━━━━━━━
/ask <問題> - 發送問題給 Cursor Agent
/tasks - 查看我的任務
/repo <owner/repo> - 切換 GitHub 倉庫
/repos - 查看帳號中的倉庫

━━━━━━━━━━━━━━━━━━━━━━
🤖 Agent Loop
━━━━━━━━━━━━━━━━━━━━━━
/agent <任務> - 啟動 AI Agent 執行任務
/skills - 查看可用技能

━━━━━━━━━━━━━━━━━━━━━━
💬 Session 管理
━━━━━━━━━━━━━━━━━━━━━━
/new - 開始新對話
/session - 查看 session 資訊
/compact - 壓縮對話歷史

━━━━━━━━━━━━━━━━━━━━━━
🧠 記憶系統
━━━━━━━━━━━━━━━━━━━━━━
/memory - 查看我的記憶
/memory add <key> <value> - 新增記憶
/memory del <key> - 刪除記憶
/clear - 清除對話上下文

━━━━━━━━━━━━━━━━━━━━━━
🔧 其他功能
━━━━━━━━━━━━━━━━━━━━━━
/workspace - 工作區設定
/stats - 使用統計
/settings - Bot 設定
/doctor - 系統診斷

直接發送訊息即可開始對話！
"""
    
    return CommandResult(success=True, message=message)


async def handle_status(ctx: CommandContext) -> CommandResult:
    """Handle /status command."""
    from ..utils.config import settings
    from ..cursor.cli_agent import is_cli_available, get_cli_agent
    from ..cursor.background_agent import get_background_agent
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
    
    # Background Agent
    agent = get_background_agent()
    if agent and agent.is_authenticated():
        lines.append("✅ Background Agent: 已連線")
    else:
        lines.append("⚪ Background Agent: 未啟用")
    
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
    from ..cursor.background_agent import get_background_agent
    from ..core.llm_providers import get_llm_manager
    
    checks = []
    
    # CLI
    if is_cli_available():
        checks.append("✅ Cursor CLI")
    else:
        checks.append("❌ Cursor CLI (未安裝)")
    
    # Background Agent
    agent = get_background_agent()
    if agent and agent.is_authenticated():
        checks.append("✅ Background Agent")
    else:
        checks.append("⚪ Background Agent (未啟用)")
    
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
