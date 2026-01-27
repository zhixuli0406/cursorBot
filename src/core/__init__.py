"""
Core modules for CursorBot
Includes memory, approvals, skills, context, scheduler, webhooks, tools, browser, agent loop, LLM providers, and heartbeat

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
from .llm_providers import (
    LLMProviderManager, get_llm_manager, reset_llm_manager,
    ProviderType, LLMProvider,
)
from .heartbeat import (
    HeartbeatMonitor, HeartbeatConfig, ServiceStatus, ServiceHealth,
    RetryHandler, RetryConfig, with_retry,
    get_heartbeat_monitor, get_retry_handler,
)
from .queue import (
    TaskQueue, TaskStatus, TaskPriority, Task, QueueConfig,
    QueueManager, get_queue_manager, get_task_queue,
)
from .tts import (
    TTSManager, TTSConfig, TTSResult, TTSProvider,
    get_tts_manager, text_to_speech,
)
from .subagents import (
    SubagentOrchestrator, Subagent, SubagentType, SubagentStatus,
    SubagentTask, SubagentConfig, TaskPlan,
    get_subagent_orchestrator,
)
from .sandbox import (
    SandboxManager, SandboxConfig, SandboxType, ExecutionResult,
    ExecutionStatus, get_sandbox_manager, execute_code,
)
from .oauth import (
    OAuthManager, OAuthConfig, OAuthProvider, OAuthToken, OAuthUser,
    APITokenManager, APIToken,
    get_oauth_manager, get_api_token_manager,
)
from .doctor import (
    Doctor, DiagnosticResult, DiagnosticReport, DiagnosticLevel,
    get_doctor, run_diagnostics,
)
from .reactions import (
    ReactionManager, Reaction, ReactionType,
    react_to_message, react_status, get_reaction_manager,
)
from .patch import (
    PatchManager, Patch, PatchResult, PatchStatus,
    create_simple_patch, get_patch_manager,
)
from .chunking import (
    MessageChunker, ChunkConfig,
    chunk_message, iter_chunks,
)
from .tool_policy import (
    ToolPolicyManager, ToolPolicy, PolicyCheckResult,
    PermissionLevel, PolicyAction, RateLimit,
    policy_check, get_tool_policy_manager,
)
from .permissions import (
    PermissionManager, Role, Permission,
    UserPermissions, GroupSettings,
    get_permission_manager, require_permission,
)
from .llm_task import (
    LLMTaskManager, TaskType, TaskTemplate, TaskResult,
    get_llm_task_manager,
)
from .channel_routing import (
    ChannelRouter, ChannelConfig, ChannelType, RouteRule,
    get_channel_router,
)
from .websocket import (
    WebSocketManager, WSMessage, WSClient, WSMessageType,
    get_websocket_manager,
)
from .location import (
    LocationManager, Location, LocationShare,
    get_location_manager,
)
from .gateway_lock import (
    GatewayLock, LockInfo, LockReason,
    get_gateway_lock,
)
from .gateway import (
    Gateway, Platform, MessageType, UnifiedMessage, UnifiedUser,
    OutgoingMessage, PlatformAdapter, get_gateway,
)
from .presence import (
    PresenceManager, PresenceStatus, UserPresence,
    get_presence_manager,
)
from .agent_send import (
    AgentSendManager, AgentMessage, AgentMessageType, Agent,
    get_agent_send_manager,
)
from .voice_wake import (
    VoiceWakeManager, WakeConfig, WakeEvent, WakeWordEngine, ListeningState,
    get_voice_wake_manager,
)
from .remote_gateway import (
    RemoteGateway, GatewayConfig, GatewayNode, GatewayStatus,
    get_remote_gateway,
)
from .draft_streaming import (
    DraftStreamer, StreamConfig, DraftMessage, StreamState,
    TelegramDraftStreamer, get_draft_streamer,
)
from .tailscale import (
    TailscaleManager, TailscaleConfig, TailscaleDevice, TailscaleNetwork,
    TailscaleStatus, get_tailscale_manager,
)
from .rag import (
    RAGManager, RAGConfig, RAGResponse,
    Document, SearchResult,
    ChunkingStrategy, EmbeddingProvider,
    TextChunker, DocumentLoader,
    VectorStore, InMemoryVectorStore, ChromaVectorStore,
    OpenAIEmbedding, GoogleEmbedding, OllamaEmbedding,
    get_rag_manager, reset_rag_manager,
)

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
    # LLM Providers
    "LLMProviderManager",
    "get_llm_manager",
    "reset_llm_manager",
    "ProviderType",
    "LLMProvider",
    # Heartbeat & Retry
    "HeartbeatMonitor",
    "HeartbeatConfig",
    "ServiceStatus",
    "ServiceHealth",
    "RetryHandler",
    "RetryConfig",
    "with_retry",
    "get_heartbeat_monitor",
    "get_retry_handler",
    # Task Queue
    "TaskQueue",
    "TaskStatus",
    "TaskPriority",
    "Task",
    "QueueConfig",
    "QueueManager",
    "get_queue_manager",
    "get_task_queue",
    # TTS
    "TTSManager",
    "TTSConfig",
    "TTSResult",
    "TTSProvider",
    "get_tts_manager",
    "text_to_speech",
    # Subagents
    "SubagentOrchestrator",
    "Subagent",
    "SubagentType",
    "SubagentStatus",
    "SubagentTask",
    "SubagentConfig",
    "TaskPlan",
    "get_subagent_orchestrator",
    # Sandbox
    "SandboxManager",
    "SandboxConfig",
    "SandboxType",
    "ExecutionResult",
    "ExecutionStatus",
    "get_sandbox_manager",
    "execute_code",
    # OAuth
    "OAuthManager",
    "OAuthConfig",
    "OAuthProvider",
    "OAuthToken",
    "OAuthUser",
    "APITokenManager",
    "APIToken",
    "get_oauth_manager",
    "get_api_token_manager",
    # Doctor
    "Doctor",
    "DiagnosticResult",
    "DiagnosticReport",
    "DiagnosticLevel",
    "get_doctor",
    "run_diagnostics",
    # Reactions
    "ReactionManager",
    "Reaction",
    "ReactionType",
    "react_to_message",
    "react_status",
    "get_reaction_manager",
    # Patch
    "PatchManager",
    "Patch",
    "PatchResult",
    "PatchStatus",
    "create_simple_patch",
    "get_patch_manager",
    # Chunking
    "MessageChunker",
    "ChunkConfig",
    "chunk_message",
    "iter_chunks",
    # Tool Policy
    "ToolPolicyManager",
    "ToolPolicy",
    "PolicyCheckResult",
    "PermissionLevel",
    "PolicyAction",
    "RateLimit",
    "policy_check",
    "get_tool_policy_manager",
    # Permissions
    "PermissionManager",
    "Role",
    "Permission",
    "UserPermissions",
    "GroupSettings",
    "get_permission_manager",
    "require_permission",
    # LLM Task
    "LLMTaskManager",
    "TaskType",
    "TaskTemplate",
    "TaskResult",
    "get_llm_task_manager",
    # Channel Routing
    "ChannelRouter",
    "ChannelConfig",
    "ChannelType",
    "RouteRule",
    "get_channel_router",
    # WebSocket
    "WebSocketManager",
    "WSMessage",
    "WSClient",
    "WSMessageType",
    "get_websocket_manager",
    # Location
    "LocationManager",
    "Location",
    "LocationShare",
    "get_location_manager",
    # Gateway Lock
    "GatewayLock",
    "LockInfo",
    "LockReason",
    "get_gateway_lock",
    # Unified Gateway
    "Gateway",
    "Platform",
    "MessageType",
    "UnifiedMessage",
    "UnifiedUser",
    "OutgoingMessage",
    "PlatformAdapter",
    "get_gateway",
    # Presence
    "PresenceManager",
    "PresenceStatus",
    "UserPresence",
    "get_presence_manager",
    # Agent Send
    "AgentSendManager",
    "AgentMessage",
    "AgentMessageType",
    "Agent",
    "get_agent_send_manager",
    # Voice Wake
    "VoiceWakeManager",
    "WakeConfig",
    "WakeEvent",
    "WakeWordEngine",
    "ListeningState",
    "get_voice_wake_manager",
    # Remote Gateway
    "RemoteGateway",
    "GatewayConfig",
    "GatewayNode",
    "GatewayStatus",
    "get_remote_gateway",
    # Draft Streaming
    "DraftStreamer",
    "StreamConfig",
    "DraftMessage",
    "StreamState",
    "TelegramDraftStreamer",
    "get_draft_streamer",
    # Tailscale
    "TailscaleManager",
    "TailscaleConfig",
    "TailscaleDevice",
    "TailscaleNetwork",
    "TailscaleStatus",
    "get_tailscale_manager",
    # RAG
    "RAGManager",
    "RAGConfig",
    "RAGResponse",
    "Document",
    "SearchResult",
    "ChunkingStrategy",
    "EmbeddingProvider",
    "TextChunker",
    "DocumentLoader",
    "VectorStore",
    "InMemoryVectorStore",
    "ChromaVectorStore",
    "OpenAIEmbedding",
    "GoogleEmbedding",
    "OllamaEmbedding",
    "get_rag_manager",
    "reset_rag_manager",
]
