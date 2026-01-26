"""
Core modules for CursorBot
Includes memory, approvals, skills, context, scheduler, webhooks, tools, browser, and agent loop

Inspired by ClawdBot's architecture
"""

from .memory import MemoryManager, get_memory_manager
from .approvals import ApprovalManager, ApprovalType, get_approval_manager, requires_approval
from .skills import (
    Skill, SkillInfo, SkillManager, get_skill_manager,
    AgentSkill, AgentSkillInfo,
)
from .context import ContextManager, ConversationContext, get_context_manager
from .scheduler import Scheduler, ScheduledJob, get_scheduler
from .webhooks import WebhookManager, WebhookType, get_webhook_manager
from .tools import Tool, ToolResult, ToolRegistry, get_tool_registry
from .browser import BrowserTool, BrowserResult, get_browser_tool, PLAYWRIGHT_AVAILABLE
from .agent_loop import AgentLoop, AgentContext, AgentState, get_agent_loop, reset_agent_loop

__all__ = [
    # Memory
    "MemoryManager",
    "get_memory_manager",
    # Approvals
    "ApprovalManager",
    "ApprovalType",
    "get_approval_manager",
    "requires_approval",
    # Skills (Command)
    "Skill",
    "SkillInfo",
    "SkillManager",
    "get_skill_manager",
    # Skills (Agent)
    "AgentSkill",
    "AgentSkillInfo",
    # Context
    "ContextManager",
    "ConversationContext",
    "get_context_manager",
    # Scheduler
    "Scheduler",
    "ScheduledJob",
    "get_scheduler",
    # Webhooks
    "WebhookManager",
    "WebhookType",
    "get_webhook_manager",
    # Tools
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "get_tool_registry",
    # Browser
    "BrowserTool",
    "BrowserResult",
    "get_browser_tool",
    "PLAYWRIGHT_AVAILABLE",
    # Agent Loop
    "AgentLoop",
    "AgentContext",
    "AgentState",
    "get_agent_loop",
    "reset_agent_loop",
]
