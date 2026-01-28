# CursorBot API Reference

Complete API documentation for CursorBot v0.4.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Health & Status](#health--status)
- [Webhook Endpoints](#webhook-endpoints)
- [Bot Commands](#bot-commands)
- [Error Handling](#error-handling)

---

## Overview

CursorBot exposes a RESTful API for health monitoring, webhook handling, and bot management.

**Base URL**: `http://localhost:8000` (default)

**Content-Type**: `application/json`

---

## Authentication

### API Endpoints
Most API endpoints are public (health checks) or protected by platform-specific authentication (webhooks).

### Webhook Authentication
Each platform uses its own authentication mechanism:

| Platform | Method |
|----------|--------|
| LINE | X-Line-Signature header |
| Slack | Signing Secret verification |
| WhatsApp | Hub verification token |
| Teams | Bot Framework authentication |
| Google Chat | Bearer token |
| Telegram | Webhook secret path |

---

## Health & Status

### GET /

Root endpoint with basic information.

**Response:**
```json
{
  "name": "CursorBot",
  "version": "0.4.0",
  "status": "running"
}
```

---

### GET /health

Basic health check for load balancers.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T10:00:00Z",
  "version": "0.4.0"
}
```

**Status Codes:**
- `200` - Healthy
- `503` - Unhealthy

---

### GET /health/detailed

Detailed health check with all system information.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T10:00:00Z",
  "version": "0.4.0",
  "components": {
    "telegram": {
      "status": "healthy",
      "latency_ms": 50
    },
    "discord": {
      "status": "healthy",
      "latency_ms": 30
    },
    "llm": {
      "status": "healthy",
      "providers": ["openai", "anthropic", "google"]
    },
    "database": {
      "status": "healthy"
    }
  },
  "system": {
    "cpu_percent": 25.5,
    "memory_percent": 45.2,
    "disk_percent": 60.0
  }
}
```

---

### GET /status

Get workspace status.

**Response:**
```json
{
  "workspace": "/path/to/workspace",
  "active_sessions": 5,
  "pending_tasks": 2
}
```

---

## Webhook Endpoints

All webhook endpoints are under `/webhook/` prefix.

### POST /webhook/telegram

Telegram Bot webhook endpoint.

**Headers:**
- `Content-Type: application/json`

**Request Body:** Telegram Update object

**Response:**
```json
{
  "ok": true
}
```

---

### POST /webhook/line

LINE Messaging API webhook endpoint.

**Headers:**
- `Content-Type: application/json`
- `X-Line-Signature: {signature}` - HMAC-SHA256 signature

**Request Body:**
```json
{
  "events": [
    {
      "type": "message",
      "replyToken": "xxx",
      "source": {
        "userId": "U123456",
        "type": "user"
      },
      "message": {
        "type": "text",
        "text": "/help"
      }
    }
  ]
}
```

**Response:**
```json
{
  "status": "ok"
}
```

**Error Response:**
```json
{
  "detail": "Invalid signature"
}
```

---

### POST /webhook/slack

Slack Events API webhook endpoint.

**Headers:**
- `Content-Type: application/json`
- `X-Slack-Signature: v0={signature}`
- `X-Slack-Request-Timestamp: {timestamp}`

**Request Body (URL Verification):**
```json
{
  "type": "url_verification",
  "challenge": "xxx"
}
```

**Request Body (Event):**
```json
{
  "type": "event_callback",
  "event": {
    "type": "message",
    "user": "U123456",
    "text": "/help",
    "channel": "C123456"
  }
}
```

**Response:**
```json
{
  "ok": true
}
```

---

### POST /webhook/slack/commands

Slack slash command endpoint.

**Headers:**
- `Content-Type: application/x-www-form-urlencoded`

**Request Body:**
```
command=/cursorbot&text=help&user_id=U123456&channel_id=C123456
```

**Response:**
```json
{
  "response_type": "in_channel",
  "text": "CursorBot help message..."
}
```

---

### POST /webhook/whatsapp

WhatsApp Cloud API webhook endpoint.

**Headers:**
- `Content-Type: application/json`

**Request Body:**
```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "changes": [
        {
          "value": {
            "messages": [
              {
                "from": "1234567890",
                "type": "text",
                "text": {
                  "body": "/help"
                }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

**Response:**
```json
{
  "status": "ok"
}
```

---

### GET /webhook/whatsapp

WhatsApp webhook verification.

**Query Parameters:**
- `hub.mode` - Should be `subscribe`
- `hub.verify_token` - Your verification token
- `hub.challenge` - Challenge string to return

**Response:** Returns `hub.challenge` value

---

### POST /webhook/teams

Microsoft Teams Bot Framework webhook endpoint.

**Headers:**
- `Content-Type: application/json`
- `Authorization: Bearer {token}`

**Request Body:**
```json
{
  "type": "message",
  "from": {
    "id": "user123",
    "name": "User Name"
  },
  "text": "/help",
  "conversation": {
    "id": "conv123"
  }
}
```

**Response:**
```json
{
  "status": "ok"
}
```

---

### POST /webhook/google-chat

Google Chat webhook endpoint.

**Headers:**
- `Content-Type: application/json`
- `Authorization: Bearer {token}`

**Request Body:**
```json
{
  "type": "MESSAGE",
  "message": {
    "sender": {
      "name": "users/123456",
      "displayName": "User Name"
    },
    "text": "/help"
  },
  "space": {
    "name": "spaces/xxx"
  }
}
```

**Response:**
```json
{
  "text": "Response message..."
}
```

---

## API Endpoints

### GET /api/usage

Get LLM usage statistics.

**Response:**
```json
{
  "total_requests": 1000,
  "total_tokens": 500000,
  "by_provider": {
    "openai": {
      "requests": 500,
      "tokens": 250000
    },
    "anthropic": {
      "requests": 300,
      "tokens": 150000
    }
  },
  "by_user": {
    "user123": {
      "requests": 100,
      "tokens": 50000
    }
  }
}
```

---

### POST /api/broadcast

Broadcast a message to users.

**Request Body:**
```json
{
  "message": "System maintenance in 1 hour",
  "user_ids": ["user1", "user2"],
  "platforms": ["telegram", "discord"]
}
```

**Response:**
```json
{
  "sent": 2,
  "failed": 0
}
```

---

### POST /api/search

Search code in workspace.

**Request Body:**
```json
{
  "query": "function",
  "path": "src/",
  "max_results": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "file": "src/main.py",
      "line": 10,
      "content": "def function():"
    }
  ],
  "total": 1
}
```

---

### GET /api/files

List files in directory.

**Query Parameters:**
- `path` - Directory path (default: ".")

**Response:**
```json
{
  "files": [
    {
      "name": "main.py",
      "type": "file",
      "size": 1024
    },
    {
      "name": "src",
      "type": "directory"
    }
  ]
}
```

---

### GET /api/files/{file_path}

Read file content.

**Path Parameters:**
- `file_path` - Path to the file

**Response:**
```json
{
  "content": "file content here...",
  "encoding": "utf-8"
}
```

---

### GET /api/workspaces

List available workspaces.

**Response:**
```json
{
  "workspaces": [
    {
      "name": "project1",
      "path": "/path/to/project1"
    },
    {
      "name": "project2",
      "path": "/path/to/project2"
    }
  ],
  "current": "project1"
}
```

---

## Bot Commands

All platforms support the same command set via unified command handling.

### Basic Commands

| Command | Description |
|---------|-------------|
| `/start` | Start bot and show welcome |
| `/help` | Show command help |
| `/status` | System status |
| `/doctor` | System diagnostics |

### Mode Commands

| Command | Description |
|---------|-------------|
| `/mode` | Show current mode |
| `/mode cli` | Switch to CLI mode (async) |
| `/mode agent` | Switch to Agent mode (async) |
| `/mode auto` | Auto-select best mode |

### AI Model Commands

| Command | Description |
|---------|-------------|
| `/model` | Show Agent model |
| `/model set <id>` | Switch Agent model |
| `/climodel` | Show CLI model |
| `/climodel list` | List all CLI models |
| `/climodel set <id>` | Switch CLI model |

### Task Commands

| Command | Description |
|---------|-------------|
| `/tasks` | View pending tasks |
| `/cancel <id>` | Cancel a task |
| `/task_status <id>` | Task details |

### Memory & RAG

| Command | Description |
|---------|-------------|
| `/memory` | Memory management |
| `/rag <question>` | RAG query |
| `/index <file>` | Index file |
| `/clear` | Clear context |

### v0.4 Commands

| Command | Description |
|---------|-------------|
| `/verbose` | Verbose output mode |
| `/elevated` | Permission elevation |
| `/think` | AI thinking mode |
| `/health` | Health check |
| `/alias` | Command aliases |

---

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `400` | Bad Request |
| `401` | Unauthorized |
| `403` | Forbidden |
| `404` | Not Found |
| `429` | Rate Limited |
| `500` | Internal Error |
| `503` | Service Unavailable |

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid request body",
    "details": {
      "field": "message",
      "reason": "required"
    }
  }
}
```

### Rate Limiting

API endpoints are rate limited. When exceeded:

**Response Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1706439600
Retry-After: 60
```

**Response Body:**
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests",
    "retry_after": 60
  }
}
```

---

## WebSocket Endpoints

### WS /ws/canvas

Live Canvas real-time connection.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/canvas?token=xxx');
```

**Messages:**
```json
{
  "type": "update",
  "component": {
    "id": "comp1",
    "type": "text",
    "content": "Hello"
  }
}
```

---

## Environment Variables

Required environment variables for API:

| Variable | Description | Required |
|----------|-------------|----------|
| `API_SERVER_PORT` | API server port | No (default: 8000) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | For Telegram |
| `LINE_CHANNEL_SECRET` | LINE channel secret | For LINE |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE access token | For LINE |
| `SLACK_BOT_TOKEN` | Slack bot token | For Slack |
| `SLACK_SIGNING_SECRET` | Slack signing secret | For Slack |
| `WHATSAPP_TOKEN` | WhatsApp token | For WhatsApp |
| `WHATSAPP_VERIFY_TOKEN` | WhatsApp verify token | For WhatsApp |
| `TEAMS_APP_ID` | Teams app ID | For Teams |
| `TEAMS_APP_PASSWORD` | Teams app password | For Teams |

---

## SDK Examples

### Python

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Search code
response = requests.post(
    "http://localhost:8000/api/search",
    json={"query": "function", "path": "src/"}
)
print(response.json())
```

### JavaScript

```javascript
// Health check
const response = await fetch('http://localhost:8000/health');
const data = await response.json();
console.log(data);

// Search code
const searchResponse = await fetch('http://localhost:8000/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'function', path: 'src/' })
});
console.log(await searchResponse.json());
```

### cURL

```bash
# Health check
curl http://localhost:8000/health

# Search code
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "function", "path": "src/"}'
```

---

## Changelog

- **v0.4.0** - Added health endpoints, webhook unification, async execution
- **v0.3.0** - Added multi-platform webhooks, CLI model selection
- **v0.2.0** - Added RAG, Agent Loop, Memory system
- **v0.1.0** - Initial release with Telegram support
