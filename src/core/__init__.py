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
from .voice_assistant import (
    VoiceAssistant, VoiceAssistantConfig, AssistantState,
    WakeEngine, STTEngine, TTSEngine, IntentCategory,
    Utterance, Intent, AssistantResponse,
    get_voice_assistant, reset_voice_assistant,
)
from .voice_commands import (
    CommandExecutor, CommandResult, CommandStatus, CommandCategory,
    get_command_executor,
)
from .voice_context import (
    ContextEngine, FullContext, TimeContext, LocationContext,
    ActivityContext, DeviceContext, UserContext, ConversationContext,
    TimeOfDay, DayType, LocationType, ActivityType, DeviceType,
    get_context_engine,
)
from .voice_llm import (
    VoiceLLM, VoiceLLMConfig, LLMResponse, ResponseStyle, ResponseType,
    IntegratedVoiceAssistant, get_voice_llm, get_integrated_assistant,
)
from .voice_learning import (
    VoiceLearningEngine, UserProfile, InteractionRecord, LearnedPattern,
    AdaptiveResponseSystem, get_learning_engine,
)
from .voice_slots import (
    SlotFillingManager, SlotDefinition, SlotValue, SlotFillingResult,
    SlotType, SlotStatus, EntityExtractor, get_slot_manager,
)
from .voice_integrations import (
    FileOperationHandler, ClipboardHandler, WeatherHandler,
    CalendarVoiceHandler, TranslationHandler, VoiceSearchHandler,
    ConfirmationHandler, get_confirmation_handler,
)
from .voice_advanced import (
    VoicePrintManager, VoicePrint, VoicePrintConfig, get_voice_print_manager,
    EmotionTTS, EmotionTTSConfig, Emotion,
    VoiceInterruptionHandler, InterruptionConfig, InterruptionType,
    MeetingAssistant, MeetingNote, MeetingSummary, get_meeting_assistant,
    VoiceNavigator, NavigationCommand, NavigationTarget, get_voice_navigator,
    OfflineTTS, MultiLanguageResponder,
    SmartHomeHandler, SmartDevice, SmartHomeProtocol, get_smart_home_handler,
)
from .voice_dialogue import (
    DialogueManager, ContextResolver, DialogueCorrector, ConversationSummarizer,
    MultiLanguageIntent, get_dialogue_manager,
)
from .voice_privacy import (
    PrivacyManager, VocabularyManager, ConsentManager,
    PrivacySettings, DataCategory, RetentionPeriod,
    get_privacy_manager, get_vocabulary_manager, get_consent_manager,
)
from .voice_accessibility import (
    AccessibilityManager, AccessibilitySettings, AccessibilityMode,
    ScreenReaderBridge, VoiceNavigation, AudioFeedback, HapticFeedback,
    get_accessibility_manager,
)
from .voice_offline import (
    OfflineModeManager, NetworkMonitor, OfflineIntentRecognizer,
    NetworkStatus, OfflineIntent, get_offline_manager, get_network_monitor,
)
from .voice_shortcuts import (
    ShortcutsManager, MacOSShortcutsManager, AppleScriptRunner,
    AndroidIntentHandler, NotificationInteraction,
    get_shortcuts_manager,
)
from .calendar_reminder import (
    CalendarReminderService, ReminderSettings, ReminderPlatform,
    CalendarEventSummary, get_reminder_service,
)
from .secretary import (
    PersonalSecretary, SecretaryPersona, Task, TaskPriority,
    UserPreferences, AssistantIntent, AssistantNLU, AssistantMode,
    get_secretary, get_assistant_mode,
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
from .async_tasks import (
    AsyncTaskManager, AsyncTask, TaskType, TaskStatus, TaskProgress,
    NotificationSender, get_task_manager, reset_task_manager,
)
# v0.4 modules
from .mcp import (
    MCPMessageType, MCPMethod, MCPTool, MCPResource, MCPPrompt,
    MCPServerInfo, MCPConfig, MCPTransport, StdioTransport, SSETransport,
    MCPClient, MCPManager, get_mcp_manager, initialize_mcp, reset_mcp_manager,
    BuiltInMCPServers,
)
from .workflow import (
    WorkflowStatus, StepStatus, StepType, StepResult,
    WorkflowStep, Workflow, WorkflowRun,
    ActionHandler, RunCommandAction, SendMessageAction, HttpRequestAction,
    SetVariableAction, WaitAction, LLMAction, RAGQueryAction, FileOperationAction,
    WorkflowEngine, get_workflow_engine, reset_workflow_engine,
    ExpressionEvaluator, create_code_review_workflow, create_deploy_workflow,
)
from .analytics import (
    EventType, Event, UserStats, DailyStats,
    CostEstimator, AnalyticsStorage, AnalyticsManager,
    get_analytics, track_event, reset_analytics,
)
from .code_review import (
    ReviewSeverity, ReviewCategory, ReviewFinding, ReviewResult, ReviewConfig,
    StaticAnalyzer, PylintAnalyzer, RuffAnalyzer, ESLintAnalyzer,
    AICodeReviewer, SecurityScanner, CodeReviewManager,
    get_code_reviewer, reset_code_reviewer,
)
from .conversation_export import (
    ExportFormat, ExportMessage, ExportConfig, ExportResult,
    PrivacyRedactor, BaseExporter, JSONExporter, MarkdownExporter,
    HTMLExporter, TxtExporter, CSVExporter, ConversationExporter,
    get_exporter, reset_exporter,
)
from .auto_docs import (
    DocFormat, DocType, DocParameter, DocReturn, DocElement, ModuleDoc, DocConfig,
    CodeParser, MarkdownGenerator, HTMLGenerator, AutoDocGenerator,
    get_doc_generator, reset_doc_generator,
)
# v0.4 core feature modules
from .verbose import (
    VerbosityLevel, VerboseConfig, VerboseManager,
    get_verbose_manager, reset_verbose_manager,
)
from .elevated import (
    ElevationReason, ElevationRequest, ElevatedAction, ElevatedManager,
    ELEVATED_ACTIONS, get_elevated_manager, reset_elevated_manager,
    require_elevation,
)
from .thinking import (
    ThinkingLevel, ThinkingConfig, ThinkingManager,
    THINKING_BUDGETS, LEVEL_NAMES, NAME_TO_LEVEL,
    get_thinking_manager, reset_thinking_manager,
)
from .notifications import (
    NotificationPriority, NotificationCategory, Notification,
    NotificationSettings, NotificationManager,
    get_notification_manager, reset_notification_manager,
)
from .command_alias import (
    CommandAlias, AliasManager, SYSTEM_ALIASES, RESERVED_COMMANDS,
    get_alias_manager, reset_alias_manager,
)
from .rate_limit import (
    RateLimitType, RateLimitRule, RateLimitBucket, RateLimitResult,
    RateLimiter, RateLimitExceeded, rate_limit, DEFAULT_RULES,
    get_rate_limiter, reset_rate_limiter,
)
from .input_validation import (
    ValidationResult, InputValidator, SENSITIVE_PATTERNS,
    validate_input, sanitize_for_log, validated_input,
    get_input_validator, reset_input_validator,
)
from .env_validation import (
    EnvVarType, EnvVarSeverity, EnvVarSpec,
    ValidationError as EnvValidationError, ValidationReport as EnvValidationReport,
    EnvironmentValidator, ENV_SPECS,
    validate_environment, require_env_var,
    get_env_validator, reset_env_validator,
)
from .health import (
    HealthStatus, ComponentType, ComponentHealth, HealthReport,
    HealthManager, get_health_manager, reset_health_manager,
    register_default_checks,
)
from .errors import (
    ErrorCode, ERROR_MESSAGES, ErrorContext, CursorBotError,
    ValidationError, AuthenticationError, PermissionError,
    ElevationRequiredError, NotFoundError, RateLimitError,
    LLMError, CommandError, ErrorHandler,
    get_error_handler, reset_error_handler,
)
from .permissions_minimal import (
    Platform as MinimalPlatform, PermissionScope,
    PlatformPermissions, PermissionAudit,
    MinimalPermissionsManager, PLATFORM_PERMISSIONS,
    get_minimal_permissions_manager, reset_minimal_permissions_manager,
)
# v0.4 advanced feature modules
from .multi_gateway import (
    GatewayState, LoadBalanceStrategy, GatewayInstance, GatewayCluster,
    MultiGatewayManager, get_multi_gateway_manager, reset_multi_gateway_manager,
)
from .dm_pairing import (
    DeviceType, PairingStatus, PairingCode, PairedDevice,
    DMPairingManager, get_dm_pairing_manager, reset_dm_pairing_manager,
)
from .i18n import (
    Language, TRANSLATIONS, UserLanguagePreference,
    I18nManager, get_i18n_manager, reset_i18n_manager, t,
)
from .live_canvas import (
    ComponentType, ChartType, AlertType, Position,
    CanvasComponent, CanvasSession, LiveCanvasManager,
    get_live_canvas_manager, reset_live_canvas_manager,
)
from .email_classifier import (
    EmailCategory, EmailPriority, EmailMessage,
    ClassificationResult, ClassificationRule, DEFAULT_RULES as EMAIL_DEFAULT_RULES,
    EmailClassifier, get_email_classifier, reset_email_classifier,
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
    # Async Tasks
    "AsyncTaskManager",
    "AsyncTask",
    "TaskType",
    "TaskStatus",
    "TaskProgress",
    "NotificationSender",
    "get_task_manager",
    "reset_task_manager",
    # MCP (v0.4)
    "MCPMessageType",
    "MCPMethod",
    "MCPTool",
    "MCPResource",
    "MCPPrompt",
    "MCPServerInfo",
    "MCPConfig",
    "MCPTransport",
    "StdioTransport",
    "SSETransport",
    "MCPClient",
    "MCPManager",
    "get_mcp_manager",
    "initialize_mcp",
    "reset_mcp_manager",
    "BuiltInMCPServers",
    # Workflow (v0.4)
    "WorkflowStatus",
    "StepStatus",
    "StepType",
    "StepResult",
    "WorkflowStep",
    "Workflow",
    "WorkflowRun",
    "ActionHandler",
    "RunCommandAction",
    "SendMessageAction",
    "HttpRequestAction",
    "SetVariableAction",
    "WaitAction",
    "LLMAction",
    "RAGQueryAction",
    "FileOperationAction",
    "WorkflowEngine",
    "get_workflow_engine",
    "reset_workflow_engine",
    "ExpressionEvaluator",
    "create_code_review_workflow",
    "create_deploy_workflow",
    # Analytics (v0.4)
    "EventType",
    "Event",
    "UserStats",
    "DailyStats",
    "CostEstimator",
    "AnalyticsStorage",
    "AnalyticsManager",
    "get_analytics",
    "track_event",
    "reset_analytics",
    # Code Review (v0.4)
    "ReviewSeverity",
    "ReviewCategory",
    "ReviewFinding",
    "ReviewResult",
    "ReviewConfig",
    "StaticAnalyzer",
    "PylintAnalyzer",
    "RuffAnalyzer",
    "ESLintAnalyzer",
    "AICodeReviewer",
    "SecurityScanner",
    "CodeReviewManager",
    "get_code_reviewer",
    "reset_code_reviewer",
    # Conversation Export (v0.4)
    "ExportFormat",
    "ExportMessage",
    "ExportConfig",
    "ExportResult",
    "PrivacyRedactor",
    "BaseExporter",
    "JSONExporter",
    "MarkdownExporter",
    "HTMLExporter",
    "TxtExporter",
    "CSVExporter",
    "ConversationExporter",
    "get_exporter",
    "reset_exporter",
    # Auto-Documentation (v0.4)
    "DocFormat",
    "DocType",
    "DocParameter",
    "DocReturn",
    "DocElement",
    "ModuleDoc",
    "DocConfig",
    "CodeParser",
    "MarkdownGenerator",
    "HTMLGenerator",
    "AutoDocGenerator",
    "get_doc_generator",
    "reset_doc_generator",
    # Verbose Mode (v0.4)
    "VerbosityLevel",
    "VerboseConfig",
    "VerboseManager",
    "get_verbose_manager",
    "reset_verbose_manager",
    # Elevated Mode (v0.4)
    "ElevationReason",
    "ElevationRequest",
    "ElevatedAction",
    "ElevatedManager",
    "ELEVATED_ACTIONS",
    "get_elevated_manager",
    "reset_elevated_manager",
    "require_elevation",
    # Thinking Mode (v0.4)
    "ThinkingLevel",
    "ThinkingConfig",
    "ThinkingManager",
    "THINKING_BUDGETS",
    "LEVEL_NAMES",
    "NAME_TO_LEVEL",
    "get_thinking_manager",
    "reset_thinking_manager",
    # Notifications (v0.4)
    "NotificationPriority",
    "NotificationCategory",
    "Notification",
    "NotificationSettings",
    "NotificationManager",
    "get_notification_manager",
    "reset_notification_manager",
    # Command Alias (v0.4)
    "CommandAlias",
    "AliasManager",
    "SYSTEM_ALIASES",
    "RESERVED_COMMANDS",
    "get_alias_manager",
    "reset_alias_manager",
    # Rate Limiting (v0.4)
    "RateLimitType",
    "RateLimitRule",
    "RateLimitBucket",
    "RateLimitResult",
    "RateLimiter",
    "RateLimitExceeded",
    "rate_limit",
    "DEFAULT_RULES",
    "get_rate_limiter",
    "reset_rate_limiter",
    # Input Validation (v0.4)
    "ValidationResult",
    "InputValidator",
    "SENSITIVE_PATTERNS",
    "validate_input",
    "sanitize_for_log",
    "validated_input",
    "get_input_validator",
    "reset_input_validator",
    # Environment Validation (v0.4)
    "EnvVarType",
    "EnvVarSeverity",
    "EnvVarSpec",
    "EnvValidationError",
    "EnvValidationReport",
    "EnvironmentValidator",
    "ENV_SPECS",
    "validate_environment",
    "require_env_var",
    "get_env_validator",
    "reset_env_validator",
    # Health Check (v0.4)
    "HealthStatus",
    "ComponentType",
    "ComponentHealth",
    "HealthReport",
    "HealthManager",
    "get_health_manager",
    "reset_health_manager",
    "register_default_checks",
    # Error Handling (v0.4)
    "ErrorCode",
    "ERROR_MESSAGES",
    "ErrorContext",
    "CursorBotError",
    "ValidationError",
    "AuthenticationError",
    "PermissionError",
    "ElevationRequiredError",
    "NotFoundError",
    "RateLimitError",
    "LLMError",
    "CommandError",
    "ErrorHandler",
    "get_error_handler",
    "reset_error_handler",
    # Minimal Permissions (v0.4)
    "MinimalPlatform",
    "PermissionScope",
    "PlatformPermissions",
    "PermissionAudit",
    "MinimalPermissionsManager",
    "PLATFORM_PERMISSIONS",
    "get_minimal_permissions_manager",
    "reset_minimal_permissions_manager",
    # Multi-Gateway (v0.4 Advanced)
    "GatewayState",
    "LoadBalanceStrategy",
    "GatewayInstance",
    "GatewayCluster",
    "MultiGatewayManager",
    "get_multi_gateway_manager",
    "reset_multi_gateway_manager",
    # DM Pairing (v0.4 Advanced)
    "DeviceType",
    "PairingStatus",
    "PairingCode",
    "PairedDevice",
    "DMPairingManager",
    "get_dm_pairing_manager",
    "reset_dm_pairing_manager",
    # i18n (v0.4 Advanced)
    "Language",
    "TRANSLATIONS",
    "UserLanguagePreference",
    "I18nManager",
    "get_i18n_manager",
    "reset_i18n_manager",
    "t",
    # Live Canvas (v0.4 Advanced)
    "ComponentType",
    "ChartType",
    "AlertType",
    "Position",
    "CanvasComponent",
    "CanvasSession",
    "LiveCanvasManager",
    "get_live_canvas_manager",
    "reset_live_canvas_manager",
    # Email Classifier (v0.4 Optional)
    "EmailCategory",
    "EmailPriority",
    "EmailMessage",
    "ClassificationResult",
    "ClassificationRule",
    "EMAIL_DEFAULT_RULES",
    "EmailClassifier",
    "get_email_classifier",
    "reset_email_classifier",
]
