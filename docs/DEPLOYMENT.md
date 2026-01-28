# CursorBot Deployment Guide

Complete guide for deploying CursorBot to various platforms.

## Table of Contents

- [Quick Start](#quick-start)
- [Railway](#railway)
- [Render](#render)
- [Fly.io](#flyio)
- [Docker](#docker)
- [Manual Deployment](#manual-deployment)
- [Post-Deployment](#post-deployment)

---

## Quick Start

### One-Click Deploy

| Platform | Deploy Button |
|----------|--------------|
| Railway | [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/cursorbot) |
| Render | [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/your-repo/cursorbot) |

### Minimum Requirements

- **RAM**: 512MB
- **CPU**: 1 vCPU (shared)
- **Storage**: 1GB
- **Network**: Public HTTPS endpoint

### Required Environment Variables

```bash
# Essential
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ALLOWED_USERS=123456789

# AI Provider (at least one)
OPENAI_API_KEY=sk-xxx
# or
ANTHROPIC_API_KEY=sk-ant-xxx
# or
OPENROUTER_API_KEY=sk-or-xxx
```

---

## Railway

### Method 1: One-Click Deploy

1. Click the Railway deploy button above
2. Connect GitHub account
3. Configure environment variables
4. Deploy

### Method 2: CLI Deploy

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Link to repository
railway link

# Set secrets
railway secrets set TELEGRAM_BOT_TOKEN=xxx
railway secrets set TELEGRAM_ALLOWED_USERS=xxx
railway secrets set OPENAI_API_KEY=xxx

# Deploy
railway up
```

### Method 3: GitHub Integration

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **New Project** > **Deploy from GitHub repo**
3. Select your fork of CursorBot
4. Configure environment variables
5. Auto-deploy enabled on push

### Railway Configuration

The `railway.json` file is pre-configured:

```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "python -m src.main",
    "healthcheckPath": "/health",
    "numReplicas": 1
  }
}
```

### Railway Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Yes |
| `TELEGRAM_ALLOWED_USERS` | Allowed user IDs | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `OPENROUTER_API_KEY` | OpenRouter API key | Optional |
| `GOOGLE_GENERATIVE_AI_API_KEY` | Gemini API key | Optional |
| `DISCORD_ENABLED` | Enable Discord | Optional |
| `DISCORD_BOT_TOKEN` | Discord bot token | If Discord enabled |

### Railway Custom Domain

1. Go to project settings
2. Click **Add Custom Domain**
3. Configure DNS CNAME record
4. Update webhook URLs

---

## Render

### Method 1: Blueprint Deploy

1. Fork the repository
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click **New** > **Blueprint**
4. Connect your fork
5. Render reads `render.yaml` automatically

### Method 2: Manual Service

1. Go to Render Dashboard
2. Click **New** > **Web Service**
3. Connect repository
4. Configure:
   - **Runtime**: Docker
   - **Region**: Oregon (or nearest)
   - **Plan**: Starter ($7/month) or Free
5. Add environment variables
6. Deploy

### Render Configuration

The `render.yaml` blueprint:

```yaml
services:
  - type: web
    name: cursorbot
    runtime: docker
    dockerfilePath: ./Dockerfile
    plan: starter
    healthCheckPath: /health
    envVars:
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: TELEGRAM_ALLOWED_USERS
        sync: false
      - key: OPENAI_API_KEY
        sync: false
```

### Render Free Tier Limitations

- Spins down after 15 minutes of inactivity
- Cold start takes ~30 seconds
- Consider upgrade to Starter for always-on

### Keep Alive (Free Tier)

Use external ping service:
- [UptimeRobot](https://uptimerobot.com/) - Free
- [Cron-job.org](https://cron-job.org/) - Free

Ping `/health` endpoint every 14 minutes.

---

## Fly.io

### Method 1: CLI Deploy

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch (first time)
fly launch

# Or deploy (subsequent)
fly deploy

# Set secrets
fly secrets set TELEGRAM_BOT_TOKEN=xxx
fly secrets set TELEGRAM_ALLOWED_USERS=xxx
fly secrets set OPENAI_API_KEY=xxx
```

### Method 2: GitHub Actions

Create `.github/workflows/fly.yml`:

```yaml
name: Deploy to Fly.io

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

### Fly.io Configuration

The `fly.toml` is pre-configured:

```toml
app = "cursorbot"
primary_region = "nrt"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8000
  force_https = true
  min_machines_running = 1

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512

[checks.health]
  path = "/health"
  interval = "30s"
```

### Fly.io Regions

| Region | Location |
|--------|----------|
| `nrt` | Tokyo (default) |
| `sin` | Singapore |
| `hkg` | Hong Kong |
| `lax` | Los Angeles |
| `ord` | Chicago |
| `lhr` | London |
| `fra` | Frankfurt |

Change region:
```bash
fly regions set sin
```

### Fly.io Scaling

```bash
# Scale memory
fly scale memory 1024

# Scale CPU
fly scale vm shared-cpu-1x

# Scale instances
fly scale count 2
```

---

## Docker

### Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/your-repo/cursorbot.git
cd cursorbot

# Copy environment file
cp env.example .env
# Edit .env with your credentials

# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Docker Run

```bash
# Build
docker build -t cursorbot .

# Run
docker run -d \
  --name cursorbot \
  -p 8000:8000 \
  -e TELEGRAM_BOT_TOKEN=xxx \
  -e TELEGRAM_ALLOWED_USERS=xxx \
  -e OPENAI_API_KEY=xxx \
  cursorbot
```

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  cursorbot:
    build: .
    container_name: cursorbot
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_ALLOWED_USERS=${TELEGRAM_ALLOWED_USERS}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Docker with Reverse Proxy

Using Nginx:

```nginx
server {
    listen 443 ssl;
    server_name cursorbot.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/cursorbot.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cursorbot.yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Manual Deployment

### Requirements

- Python 3.11+
- pip
- git

### Steps

```bash
# Clone
git clone https://github.com/your-repo/cursorbot.git
cd cursorbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure
cp env.example .env
nano .env  # Edit configuration

# Run
python -m src.main

# Or use start script
./start.sh
```

### Systemd Service (Linux)

Create `/etc/systemd/system/cursorbot.service`:

```ini
[Unit]
Description=CursorBot AI Assistant
After=network.target

[Service]
Type=simple
User=cursorbot
WorkingDirectory=/opt/cursorbot
Environment="PATH=/opt/cursorbot/venv/bin"
ExecStart=/opt/cursorbot/venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable cursorbot
sudo systemctl start cursorbot
sudo systemctl status cursorbot
```

### PM2 (Node.js Process Manager)

```bash
# Install PM2
npm install -g pm2

# Start
pm2 start "python -m src.main" --name cursorbot

# Save configuration
pm2 save

# Auto-start on boot
pm2 startup
```

---

## Post-Deployment

### 1. Verify Health

```bash
curl https://your-domain.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.4.0"
}
```

### 2. Set Webhook (Telegram)

If using webhook mode:
```bash
curl "https://api.telegram.org/bot{TOKEN}/setWebhook?url=https://your-domain.com/webhook/telegram"
```

### 3. Test Bot

Send `/start` to your Telegram bot.

### 4. Configure Other Platforms

See [Platform Setup Guide](PLATFORM_SETUP.md) for:
- LINE webhook setup
- Slack app configuration
- Discord bot invite
- WhatsApp business setup

### 5. Monitor

#### Logs
```bash
# Railway
railway logs

# Render
# View in dashboard

# Fly.io
fly logs

# Docker
docker logs -f cursorbot
```

#### Health Monitoring

Set up external monitoring:
- [UptimeRobot](https://uptimerobot.com/)
- [Better Uptime](https://betteruptime.com/)
- [Pingdom](https://www.pingdom.com/)

### 6. Backups

For persistent data:
```bash
# Backup data directory
tar -czf cursorbot-backup.tar.gz data/

# Restore
tar -xzf cursorbot-backup.tar.gz
```

---

## Troubleshooting

### Common Issues

#### Bot Not Responding

1. Check logs for errors
2. Verify `TELEGRAM_BOT_TOKEN` is correct
3. Verify `TELEGRAM_ALLOWED_USERS` includes your ID
4. Check `/health` endpoint

#### Webhook Errors

1. Verify HTTPS is working
2. Check SSL certificate validity
3. Confirm webhook URL is correct
4. Check platform-specific requirements

#### Memory Issues

Increase memory:
```bash
# Fly.io
fly scale memory 1024

# Railway
# Upgrade plan in dashboard

# Docker
docker update --memory 1g cursorbot
```

#### Cold Start (Free Tiers)

- Use keep-alive ping service
- Upgrade to paid tier
- Accept initial delay

### Getting Help

1. Check [FAQ](FAQ.md)
2. Review [API docs](API.md)
3. Open GitHub issue
4. Community Discord

---

## Cost Comparison

| Platform | Free Tier | Paid |
|----------|-----------|------|
| Railway | $5 credit/month | $5+/month |
| Render | 750 hours/month (spins down) | $7/month |
| Fly.io | 3 shared VMs | ~$3/month |
| DigitalOcean | None | $4/month |
| Heroku | None | $7/month |

**Recommendation**: Fly.io for cost-effectiveness, Railway for ease of use.
