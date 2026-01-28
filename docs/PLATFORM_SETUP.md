# Platform Setup Guide

Complete guide for setting up CursorBot on different messaging platforms.

## Table of Contents

- [Telegram](#telegram)
- [Discord](#discord)
- [LINE](#line)
- [Slack](#slack)
- [WhatsApp](#whatsapp)
- [Microsoft Teams](#microsoft-teams)
- [Google Chat](#google-chat)

---

## Telegram

### Step 1: Create Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow prompts to set bot name and username
4. Copy the **Bot Token** (e.g., `123456789:ABCdefGHI...`)

### Step 2: Configure Environment

```bash
# .env file
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALLOWED_USERS=123456789,987654321  # Comma-separated user IDs
```

### Step 3: Get Your User ID

1. Search for `@userinfobot` on Telegram
2. Send any message
3. Copy your user ID

### Step 4: Start Bot

```bash
./cursorbot start
```

### Optional: Webhook Mode

For production, use webhook instead of polling:

```bash
# .env file
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram
```

---

## Discord

### Step 1: Create Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application**
3. Name your application and create

### Step 2: Create Bot

1. Go to **Bot** section
2. Click **Add Bot**
3. Copy the **Bot Token**
4. Enable **Message Content Intent** under Privileged Gateway Intents

### Step 3: Invite Bot

1. Go to **OAuth2** > **URL Generator**
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - Send Messages
   - Read Message History
   - Use Slash Commands
   - Attach Files
   - Embed Links
4. Copy generated URL and open in browser
5. Select server and authorize

### Step 4: Configure Environment

```bash
# .env file
DISCORD_ENABLED=true
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_ALLOWED_USERS=123456789012345678  # Discord user IDs
```

### Step 5: Start Bot

```bash
./cursorbot start
```

---

## LINE

### Step 1: Create LINE Messaging API Channel

1. Go to [LINE Developers Console](https://developers.line.biz/console/)
2. Create a new Provider (or use existing)
3. Create a new **Messaging API** channel
4. Fill in required information

### Step 2: Get Credentials

1. Go to **Basic settings** tab
2. Copy **Channel secret**
3. Go to **Messaging API** tab
4. Issue and copy **Channel access token (long-lived)**

### Step 3: Configure Webhook

1. In **Messaging API** tab
2. Set **Webhook URL**: `https://your-domain.com/webhook/line`
3. Enable **Use webhook**
4. Disable **Auto-reply messages**
5. Disable **Greeting messages**

### Step 4: Configure Environment

```bash
# .env file
LINE_CHANNEL_SECRET=your_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_access_token
LINE_ALLOWED_USERS=U722f9b179e0f56f500adb3d11dae6e99  # LINE user IDs
```

### Step 5: Get User ID

When a user messages the bot, their ID appears in logs:
```
LINE message from U722f9b179e0f56f500adb3d11dae6e99: hello
```

### Step 6: Verify Webhook

1. Click **Verify** button in LINE console
2. Should return `200 OK`

---

## Slack

### Step 1: Create Slack App

1. Go to [Slack API](https://api.slack.com/apps)
2. Click **Create New App**
3. Choose **From scratch**
4. Name your app and select workspace

### Step 2: Configure Bot

1. Go to **OAuth & Permissions**
2. Add Bot Token Scopes:
   - `chat:write`
   - `commands`
   - `app_mentions:read`
   - `im:history`
   - `im:read`
   - `im:write`
3. Install to workspace
4. Copy **Bot User OAuth Token**

### Step 3: Configure Slash Commands

1. Go to **Slash Commands**
2. Create new command:
   - Command: `/cursorbot`
   - Request URL: `https://your-domain.com/webhook/slack/commands`
   - Description: CursorBot AI assistant

### Step 4: Configure Event Subscriptions

1. Go to **Event Subscriptions**
2. Enable Events
3. Request URL: `https://your-domain.com/webhook/slack`
4. Subscribe to bot events:
   - `message.im`
   - `app_mention`

### Step 5: Get Signing Secret

1. Go to **Basic Information**
2. Copy **Signing Secret**

### Step 6: Configure Environment

```bash
# .env file
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your_signing_secret
SLACK_ALLOWED_USERS=U12345678  # Slack user IDs
```

---

## WhatsApp

### Step 1: Create Meta App

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create new app
3. Select **Business** type
4. Add **WhatsApp** product

### Step 2: Configure WhatsApp

1. Go to **WhatsApp** > **Getting Started**
2. Add phone number or use test number
3. Generate **Temporary access token**
4. Note the **Phone number ID**

### Step 3: Configure Webhook

1. Go to **Configuration**
2. Add callback URL: `https://your-domain.com/webhook/whatsapp`
3. Create a **Verify token** (any string)
4. Subscribe to `messages` webhook field

### Step 4: Configure Environment

```bash
# .env file
WHATSAPP_TOKEN=your_access_token
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_ALLOWED_USERS=1234567890  # Phone numbers
```

### Step 5: Production Access

For production:
1. Complete Business Verification
2. Request permissions for `whatsapp_business_messaging`
3. Get permanent access token

---

## Microsoft Teams

### Step 1: Create Azure Bot

1. Go to [Azure Portal](https://portal.azure.com/)
2. Create **Azure Bot** resource
3. Choose **Multi Tenant**
4. Create new **Microsoft App ID**

### Step 2: Get Credentials

1. Go to bot resource
2. Click **Configuration**
3. Copy **Microsoft App ID**
4. Click **Manage** > **Certificates & secrets**
5. Create new client secret
6. Copy secret value

### Step 3: Configure Messaging Endpoint

1. In Azure Bot **Configuration**
2. Set **Messaging endpoint**: `https://your-domain.com/webhook/teams`

### Step 4: Add Teams Channel

1. Go to **Channels**
2. Click **Microsoft Teams**
3. Accept terms and save

### Step 5: Configure Environment

```bash
# .env file
TEAMS_APP_ID=your_app_id
TEAMS_APP_PASSWORD=your_client_secret
TEAMS_ALLOWED_USERS=user@domain.com  # Teams user emails or IDs
```

### Step 6: Install in Teams

1. Go to Teams Admin Center
2. Upload custom app or
3. Create Teams app package with manifest

---

## Google Chat

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable **Google Chat API**

### Step 2: Configure OAuth

1. Go to **APIs & Services** > **Credentials**
2. Create **OAuth 2.0 Client ID**
3. Configure consent screen
4. Download credentials JSON

### Step 3: Configure Chat App

1. Go to [Google Chat API Configuration](https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat)
2. Configure app:
   - App name: CursorBot
   - Avatar URL: (optional)
   - Description: AI coding assistant
   - Functionality: Receive 1:1 messages, Join spaces
   - Connection settings: HTTP endpoint URL
   - HTTP endpoint URL: `https://your-domain.com/webhook/google-chat`

### Step 4: Configure Environment

```bash
# .env file
GOOGLE_CHAT_CREDENTIALS=/path/to/credentials.json
GOOGLE_CHAT_ALLOWED_USERS=users/123456789  # Google Chat user IDs
```

### Step 5: Publish App

1. For workspace use: Publish to your organization
2. For public: Submit for verification

---

## Common Configuration

### SSL/HTTPS Requirements

Most platforms require HTTPS for webhooks. Options:

1. **ngrok** (Development)
   ```bash
   ngrok http 8000
   # Use ngrok URL for webhooks
   ```

2. **Cloudflare Tunnel** (Free)
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

3. **Let's Encrypt** (Production)
   ```bash
   certbot certonly --standalone -d your-domain.com
   ```

### API Server Configuration

```bash
# .env file
API_SERVER_HOST=0.0.0.0
API_SERVER_PORT=8000
```

### Starting the Server

```bash
# Start with all platforms
./cursorbot start

# Or use Docker
docker-compose up -d
```

### Verifying Setup

Check platform status:
```
/status
```

Detailed diagnostics:
```
/doctor
```

---

## Troubleshooting

### Common Issues

#### Webhook Not Receiving Messages

1. Check webhook URL is publicly accessible
2. Verify SSL certificate is valid
3. Check firewall allows incoming connections
4. Review logs: `tail -f logs/cursorbot.log`

#### Authentication Errors

1. Verify tokens and secrets are correct
2. Check for whitespace in environment variables
3. Regenerate tokens if expired

#### Rate Limiting

1. Check platform rate limits
2. Enable rate limiting in CursorBot
3. Add delays between messages

### Platform-Specific Issues

#### LINE: 502 Bad Gateway
- Ensure API server is running
- Check `API_SERVER_PORT` configuration
- Verify webhook URL is correct

#### Slack: Request Timeout
- Respond within 3 seconds
- Use async processing for long tasks
- Return acknowledgment immediately

#### Teams: 401 Unauthorized
- Verify App ID and Password
- Check tenant configuration
- Regenerate client secret

### Getting Help

1. Check [FAQ](FAQ.md)
2. Review [API Documentation](API.md)
3. Open GitHub issue
4. Join community Discord

---

## Security Best Practices

1. **Use Environment Variables**
   - Never commit tokens to git
   - Use `.env` file (gitignored)

2. **Restrict User Access**
   - Configure `*_ALLOWED_USERS` for each platform
   - Use user IDs, not usernames

3. **Enable Rate Limiting**
   ```bash
   RATE_LIMIT_ENABLED=true
   RATE_LIMIT_REQUESTS=100
   RATE_LIMIT_WINDOW=60
   ```

4. **Use HTTPS**
   - Required for production webhooks
   - Verify SSL certificates

5. **Monitor Logs**
   - Check for unauthorized access attempts
   - Review error patterns

---

## Quick Reference

| Platform | Webhook URL | Auth Header |
|----------|-------------|-------------|
| Telegram | `/webhook/telegram` | (in URL) |
| LINE | `/webhook/line` | X-Line-Signature |
| Slack | `/webhook/slack` | X-Slack-Signature |
| WhatsApp | `/webhook/whatsapp` | (verify token) |
| Teams | `/webhook/teams` | Authorization |
| Google Chat | `/webhook/google-chat` | Authorization |

| Platform | User ID Format | Example |
|----------|----------------|---------|
| Telegram | Numeric | `123456789` |
| Discord | Snowflake | `123456789012345678` |
| LINE | String | `U722f9b179e0f56...` |
| Slack | String | `U12345678` |
| WhatsApp | Phone | `1234567890` |
| Teams | Email/ID | `user@domain.com` |
| Google Chat | String | `users/123456789` |
