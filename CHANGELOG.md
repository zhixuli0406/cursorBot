# Changelog

All notable changes to CursorBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **v0.4 Telegram Command Handlers** - All v0.4 core commands now have full Telegram handlers
  - `/verbose` - Detailed output mode (off/low/medium/high)
  - `/think` - AI thinking depth control (off/low/medium/high/xhigh)
  - `/alias` - User-defined command aliases
  - `/notify` - System notification settings
- **Updated /start command** - Shows v0.4 version and new features
- **Updated /help command** - Complete v0.4 command reference
- **Live Canvas (A2UI)** - Agent-driven visual workspace
- **macOS App 完整版** (apps/macos) - SwiftUI native app
  - Talk Mode with Speech Recognition & TTS
  - Debug Tools (Logs, Network Inspector)
  - Remote Gateway connection
  - Menu Bar integration
  - Global Hotkeys
  - Voice Wake support
- **iOS Node** (apps/ios) - SwiftUI native app
  - Live Canvas support
  - Voice Wake
  - Talk Mode
  - Camera integration with AI analysis
  - Device Pairing (QR Code)
- **Android Node** (apps/android) - Kotlin/Compose native app
  - Live Canvas support
  - Talk Mode
  - CameraX integration
  - Screen Recording (MediaProjection)
  - Device Pairing

### Changed
- **Async execution is now default** - All modes (CLI/Agent) use background execution
  - Messages are processed in background, results pushed when complete
  - Users can continue chatting without waiting
  - Use `/tasks` to view pending tasks, `/cancel <id>` to cancel
  - Removed separate `/agent_async` and `/cli_async` commands (now default behavior)

### Documentation
- Updated FEATURE_ROADMAP.md with v0.4 completion status (92% complete)
- Updated README.md version to v0.4.0
- Complete API documentation (docs/API.md)
- Platform setup guide (docs/PLATFORM_SETUP.md)
- Deployment guide (docs/DEPLOYMENT.md)

---

## [0.4.0] - 2026-01-28

### Added

#### Core Commands
- `/verbose` - Detailed output mode with multiple verbosity levels (off/low/medium/high)
  - Show tokens usage
  - Show response timing
  - Show model information
  - Show raw response (high level)
- `/elevated` - Permission elevation for sensitive operations
  - Time-limited elevated privileges (default: 15 minutes, max: 60 minutes)
  - Protected actions: file_delete, system_exec, config_write, rag_clear, memory_clear, broadcast
  - Auto-grant for admin users
- `/think` - AI thinking mode control
  - Thinking levels: off/low/medium/high/xhigh
  - Adjustable thinking budget (1K to 25K tokens)
  - Show thinking process option
  - Auto-adjust based on task complexity
- System notifications
  - Desktop notifications (macOS, Windows, Linux)
  - Notification categories: task_complete, task_failed, message_received, system_alert, approval_required, reminder
  - Quiet hours support
  - Sound control
- Command alias system
  - Built-in system aliases (h=help, s=status, m=mode, etc.)
  - User-defined aliases (up to 50 per user)
  - Alias with default arguments support

#### Security
- Rate limiting system
  - Per-user and global rate limits
  - Token bucket algorithm
  - Multiple limit types: requests, tokens, commands, uploads, websocket
  - User blocking capability
- Input validation
  - Command injection prevention
  - SQL injection prevention
  - Path traversal detection
  - XSS prevention
- Log sanitization
  - Automatic masking of sensitive data (API keys, tokens, passwords, emails, etc.)
  - Safe logging for production environments

#### Operations
- Environment variable validation
  - Startup validation of required configuration
  - Pattern matching for API keys and tokens
  - Feature availability detection
- Health check endpoints
  - `GET /health` - Basic health check for load balancers
  - `GET /ready` - Kubernetes readiness check
  - `GET /health/detail` - Detailed component status
  - Memory and disk usage monitoring
- Graceful shutdown
  - Signal handling (SIGTERM, SIGINT)
  - Shutdown handler registration
  - Timeout support for cleanup operations

#### Infrastructure
- MCP (Model Context Protocol) support
  - Stdio and SSE transports
  - Built-in MCP server integrations
- Workflow engine
  - Multi-step workflow execution
  - Condition-based branching
  - Variable interpolation
  - Pre-built workflows (code review, deploy)
- Analytics system
  - Event tracking
  - Usage statistics
  - Cost estimation

### Changed
- Improved error messages with consistent formatting
- Enhanced session management with better cleanup
- Updated LLM provider integration for new model versions

### Fixed
- Memory leaks in long-running sessions
- Rate limiting edge cases
- Signal handling on Windows

---

## [0.3.0] - 2026-01-15

### Added

#### Platforms
- WhatsApp Cloud API integration
- Microsoft Teams Bot Framework integration
- Slack Events API integration
- iMessage support (macOS via AppleScript)
- LINE Messaging API integration
- Signal integration (via signal-cli)
- Google Chat integration

#### AI Providers
- AWS Bedrock support
- Moonshot AI (Chinese market)
- GLM/ChatGLM (Chinese market)
- GitHub Copilot / GitHub Models

#### Features
- RAG (Retrieval-Augmented Generation) system
  - Document indexing (PDF, MD, code, JSON)
  - Vector search with ChromaDB
  - Multiple embedding providers
  - Auto-save conversations to RAG
- Voice Wake (always-on voice activation)
- Talk Mode (continuous conversation)
- TTS (Text-to-Speech) output
  - OpenAI TTS
  - Edge TTS (free)
  - ElevenLabs
- Agent to Agent collaboration
- Gmail integration (read/send/search)
- Google Calendar integration
- Skills Registry (SkillsMP.com integration)
- Chrome Extension
- macOS Menu Bar app
- Sandbox execution (Docker/Subprocess)
- Subagents system
- Thinking Mode (Claude Extended Thinking)
- Compaction (conversation compression)
- OAuth 2.0 authentication
- Heartbeat monitoring
- Retry mechanism
- Task queue
- Web Dashboard
- TUI (Terminal UI)
- Tailscale VPN integration

#### Commands
- `/rag` - RAG knowledge base queries
- `/index` - Document indexing
- `/tts` - Text-to-speech
- `/gmail` - Gmail operations
- `/calendar` - Google Calendar
- `/skills_search` - Search skills marketplace
- `/skills_install` - Install skills
- `/session` - Session management
- `/compact` - Conversation compression

### Changed
- Unified webhook system for all platforms
- Improved streaming response handling
- Better error recovery with retry logic

### Fixed
- Session isolation issues in group chats
- Memory usage in long conversations
- Webhook verification for various platforms

---

## [0.2.0] - 2025-12-01

### Added
- Model failover (automatic backup model switching)
- Usage tracking (token usage per user)
- @mention trigger in groups
- Session management enhancements
- Group session isolation
- Multi-Agent routing
- Broadcast messages
- Streaming responses
- Typing indicator
- Health check improvements

### Changed
- Improved context management
- Better error handling
- Enhanced logging

### Fixed
- Race conditions in concurrent requests
- Memory leaks in browser tool
- Timeout issues with long tasks

---

## [0.1.0] - 2025-11-01

### Added
- Initial release
- Telegram Bot support
- Discord Bot support
- Basic AI conversation
- Agent Loop
- Memory system
- Skills system
- Context management
- Scheduler
- Webhooks
- Browser tool (Playwright)
- File operations
- Terminal execution

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 0.4.0 | 2026-01-28 | v0.4 Core: verbose, elevated, think, notifications, aliases, rate limiting, health checks |
| 0.3.0 | 2026-01-15 | Multi-platform (WhatsApp, Teams, Slack, Line), RAG, Voice, TTS, Gmail, Calendar |
| 0.2.0 | 2025-12-01 | Model failover, usage tracking, streaming, groups |
| 0.1.0 | 2025-11-01 | Initial release with Telegram, Discord, Agent Loop |

---

## Migration Guide

### From 0.3.x to 0.4.0

1. **New Environment Variables** (optional):
   - No new required variables
   - `SECRET_KEY` is now recommended (32+ chars)

2. **New Features to Configure**:
   - Rate limiting is enabled by default
   - Health endpoints are available at `/health` and `/ready`
   - Graceful shutdown is automatic

3. **Breaking Changes**:
   - None

### From 0.2.x to 0.3.0

1. **New Environment Variables**:
   - Platform-specific tokens (LINE, Slack, WhatsApp, Teams)
   - RAG configuration variables
   - TTS provider settings

2. **Database Migration**:
   - Run `python -m src.migrations.v030` to upgrade database

---

## Links

- [GitHub Repository](https://github.com/your-repo/cursorBot)
- [Documentation](https://github.com/your-repo/cursorBot/wiki)
- [Issue Tracker](https://github.com/your-repo/cursorBot/issues)
- [Feature Roadmap](docs/FEATURE_ROADMAP.md)
