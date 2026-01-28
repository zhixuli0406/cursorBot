"""
Social Platform Webhook Handlers for CursorBot

Provides unified webhook endpoints for:
- LINE
- Slack
- WhatsApp (Cloud API)
- Microsoft Teams
- Google Chat
"""

import base64
import hashlib
import hmac
import re
from typing import Optional

from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRouter

from ..core.unified_commands import CommandContext, execute_command
from ..core.llm_providers import get_llm_manager
from ..utils.config import settings
from ..utils.logger import logger

router = APIRouter(prefix="/webhook", tags=["webhooks"])


# ============================================
# Unified Message Handler
# ============================================

async def handle_platform_message(
    user_id: str,
    text: str,
    platform: str,
    user_name: str = "",
    allowed_users: str = "",
) -> str:
    """
    Unified message handler for all platforms.
    
    Args:
        user_id: Platform-specific user ID
        text: Message text
        platform: Platform name (line, slack, whatsapp, teams, google_chat)
        user_name: Optional user display name
        allowed_users: Comma-separated list of allowed user IDs
        
    Returns:
        Response text
    """
    # Check authorization if allowed_users is set
    if allowed_users:
        allowed_list = [u.strip() for u in allowed_users.split(",") if u.strip()]
        if user_id not in allowed_list:
            return "⚠️ 您沒有使用此機器人的權限。"
    
    text = text.strip()
    
    # Check if it's a command
    if text.startswith("/"):
        parts = text[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []
        
        # Create command context
        ctx = CommandContext(
            user_id=user_id,
            user_name=user_name or f"{platform.title()} User",
            platform=platform,
            args=args,
            raw_text=text,
            is_admin=False,
        )
        
        # Execute command
        result = await execute_command(command, ctx)
        
        if result:
            # Strip HTML tags for platforms that don't support them
            response = result.message
            response = re.sub(r'<[^>]+>', '', response)
            response = response.replace('**', '')
            return response
        else:
            return f"❓ 未知指令: /{command}\n\n使用 /help 查看可用指令"
    
    # Not a command - handle as chat
    try:
        manager = get_llm_manager()
        response = await manager.chat(
            message=text,
            user_id=user_id,
            system_prompt="你是 CursorBot，一個多平台 AI 編程助手。請用繁體中文回答，簡潔且有幫助。",
        )
        return response
    except Exception as e:
        logger.error(f"{platform} chat error: {e}")
        return f"❌ 處理訊息時發生錯誤: {str(e)[:100]}"


def split_long_message(text: str, max_chars: int = 4000) -> list[str]:
    """Split long message into chunks."""
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for line in text.split("\n"):
        if len(current_chunk) + len(line) + 1 <= max_chars:
            current_chunk += line + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = line + "\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


# ============================================
# LINE Webhook
# ============================================

@router.post("/line")
async def line_webhook(request: Request):
    """LINE Messaging API webhook endpoint."""
    try:
        # Get signature header
        signature = request.headers.get("X-Line-Signature", "")
        body = await request.body()
        
        # Verify signature
        channel_secret = settings.line_channel_secret
        if not channel_secret:
            logger.error("LINE_CHANNEL_SECRET not configured")
            raise HTTPException(status_code=500, detail="LINE not configured")
        
        # Calculate expected signature
        hash_value = hmac.new(
            channel_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).digest()
        expected_signature = base64.b64encode(hash_value).decode('utf-8')
        
        # Constant-time comparison
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Invalid LINE webhook signature")
            raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Parse events
        data = await request.json()
        events = data.get("events", [])
        
        for event in events:
            event_type = event.get("type")
            
            if event_type == "message":
                message = event.get("message", {})
                message_type = message.get("type")
                
                if message_type == "text":
                    text = message.get("text", "").strip()
                    reply_token = event.get("replyToken")
                    user_id = event.get("source", {}).get("userId", "")
                    
                    logger.info(f"LINE message from {user_id}: {text[:50]}...")
                    
                    if reply_token:
                        response = await handle_platform_message(
                            user_id=user_id,
                            text=text,
                            platform="line",
                            allowed_users=settings.line_allowed_users,
                        )
                        await _send_line_reply(reply_token, response)
            
            elif event_type == "follow":
                user_id = event.get("source", {}).get("userId", "")
                reply_token = event.get("replyToken")
                logger.info(f"New LINE follower: {user_id}")
                
                if reply_token:
                    await _send_line_reply(
                        reply_token,
                        "歡迎使用 CursorBot！\n\n發送任何訊息開始對話，或使用 /help 查看指令。"
                    )
            
            elif event_type == "unfollow":
                user_id = event.get("source", {}).get("userId", "")
                logger.info(f"LINE user unfollowed: {user_id}")
        
        return Response(status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LINE webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _send_line_reply(reply_token: str, text: str) -> bool:
    """Send LINE reply message."""
    import httpx
    
    access_token = settings.line_channel_access_token
    if not access_token:
        logger.error("LINE_CHANNEL_ACCESS_TOKEN not configured")
        return False
    
    # Split into multiple messages if needed (LINE limit: 5000 chars, max 5 messages)
    chunks = split_long_message(text, 4900)[:5]
    messages = [{"type": "text", "text": chunk} for chunk in chunks]
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.line.me/v2/bot/message/reply",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "replyToken": reply_token,
                    "messages": messages,
                },
                timeout=10.0,
            )
            
            if response.status_code != 200:
                logger.error(f"LINE reply failed: {response.text}")
                return False
                
            return True
            
    except Exception as e:
        logger.error(f"LINE reply error: {e}")
        return False


# ============================================
# Slack Webhook
# ============================================

@router.post("/slack")
async def slack_webhook(request: Request):
    """Slack Events API webhook endpoint."""
    try:
        body = await request.body()
        data = await request.json()
        
        # Handle URL verification challenge
        if data.get("type") == "url_verification":
            return {"challenge": data.get("challenge")}
        
        # Verify signature
        signing_secret = settings.slack_signing_secret
        if signing_secret:
            timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
            slack_signature = request.headers.get("X-Slack-Signature", "")
            
            # Check timestamp to prevent replay attacks
            import time
            if abs(time.time() - float(timestamp)) > 60 * 5:
                raise HTTPException(status_code=403, detail="Request too old")
            
            # Calculate signature
            sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
            expected_sig = "v0=" + hmac.new(
                signing_secret.encode('utf-8'),
                sig_basestring.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(slack_signature, expected_sig):
                logger.warning("Invalid Slack signature")
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Process events
        event = data.get("event", {})
        event_type = event.get("type")
        
        if event_type == "message" and not event.get("bot_id"):
            # Ignore bot messages to prevent loops
            text = event.get("text", "").strip()
            user_id = event.get("user", "")
            channel = event.get("channel", "")
            
            logger.info(f"Slack message from {user_id} in {channel}: {text[:50]}...")
            
            response = await handle_platform_message(
                user_id=user_id,
                text=text,
                platform="slack",
                allowed_users=settings.slack_allowed_users,
            )
            
            # Send reply
            await _send_slack_message(channel, response, event.get("ts"))
        
        return Response(status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Slack webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/slack/commands")
async def slack_slash_command(request: Request):
    """Slack slash command endpoint."""
    try:
        form_data = await request.form()
        
        command = form_data.get("command", "").lstrip("/")
        text = form_data.get("text", "")
        user_id = form_data.get("user_id", "")
        user_name = form_data.get("user_name", "")
        channel_id = form_data.get("channel_id", "")
        response_url = form_data.get("response_url", "")
        
        logger.info(f"Slack command from {user_id}: /{command} {text}")
        
        # Handle command
        full_command = f"/{command} {text}".strip() if text else f"/{command}"
        response = await handle_platform_message(
            user_id=user_id,
            text=full_command,
            platform="slack",
            user_name=user_name,
            allowed_users=settings.slack_allowed_users,
        )
        
        return {"response_type": "in_channel", "text": response}
        
    except Exception as e:
        logger.error(f"Slack command error: {e}")
        return {"response_type": "ephemeral", "text": f"Error: {str(e)[:100]}"}


async def _send_slack_message(channel: str, text: str, thread_ts: Optional[str] = None) -> bool:
    """Send Slack message."""
    import httpx
    
    bot_token = settings.slack_bot_token
    if not bot_token:
        logger.error("SLACK_BOT_TOKEN not configured")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "channel": channel,
                "text": text,
            }
            if thread_ts:
                payload["thread_ts"] = thread_ts
            
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {bot_token}",
                },
                json=payload,
                timeout=10.0,
            )
            
            result = response.json()
            if not result.get("ok"):
                logger.error(f"Slack message failed: {result.get('error')}")
                return False
                
            return True
            
    except Exception as e:
        logger.error(f"Slack message error: {e}")
        return False


# ============================================
# Microsoft Teams Webhook
# ============================================

@router.post("/teams")
async def teams_webhook(request: Request):
    """Microsoft Teams Bot Framework webhook endpoint."""
    try:
        data = await request.json()
        
        activity_type = data.get("type")
        
        if activity_type == "message":
            text = data.get("text", "").strip()
            user_id = data.get("from", {}).get("id", "")
            user_name = data.get("from", {}).get("name", "")
            conversation_id = data.get("conversation", {}).get("id", "")
            service_url = data.get("serviceUrl", "")
            
            # Remove bot mention if present
            text = re.sub(r'<at>.*?</at>\s*', '', text).strip()
            
            logger.info(f"Teams message from {user_name}: {text[:50]}...")
            
            response = await handle_platform_message(
                user_id=user_id,
                text=text,
                platform="teams",
                user_name=user_name,
                allowed_users=settings.teams_allowed_users,
            )
            
            # Send reply
            await _send_teams_reply(
                service_url=service_url,
                conversation_id=conversation_id,
                activity_id=data.get("id"),
                text=response,
            )
        
        elif activity_type == "conversationUpdate":
            # Handle member added/removed
            members_added = data.get("membersAdded", [])
            for member in members_added:
                if member.get("id") != data.get("recipient", {}).get("id"):
                    logger.info(f"Teams: New member added: {member.get('name')}")
        
        return Response(status_code=200)
        
    except Exception as e:
        logger.error(f"Teams webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _send_teams_reply(
    service_url: str,
    conversation_id: str,
    activity_id: str,
    text: str,
) -> bool:
    """Send Teams reply using Bot Framework."""
    import httpx
    
    app_id = settings.teams_app_id
    app_password = settings.teams_app_password
    
    if not app_id or not app_password:
        logger.error("TEAMS_APP_ID and TEAMS_APP_PASSWORD not configured")
        return False
    
    try:
        # Get access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": app_id,
                    "client_secret": app_password,
                    "scope": "https://api.botframework.com/.default",
                },
                timeout=10.0,
            )
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                logger.error(f"Teams token error: {token_data}")
                return False
            
            # Send reply
            reply_url = f"{service_url}v3/conversations/{conversation_id}/activities/{activity_id}"
            
            response = await client.post(
                reply_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "type": "message",
                    "text": text,
                },
                timeout=10.0,
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Teams reply failed: {response.text}")
                return False
                
            return True
            
    except Exception as e:
        logger.error(f"Teams reply error: {e}")
        return False


# ============================================
# Google Chat Webhook
# ============================================

@router.post("/google-chat")
async def google_chat_webhook(request: Request):
    """Google Chat webhook endpoint."""
    try:
        data = await request.json()
        
        event_type = data.get("type")
        
        if event_type == "MESSAGE":
            message = data.get("message", {})
            text = message.get("text", "").strip()
            user = data.get("user", {})
            user_id = user.get("name", "")
            user_name = user.get("displayName", "")
            space = data.get("space", {})
            space_name = space.get("name", "")
            
            # Remove bot mention if present
            text = re.sub(r'@\w+\s*', '', text).strip()
            
            logger.info(f"Google Chat message from {user_name}: {text[:50]}...")
            
            response = await handle_platform_message(
                user_id=user_id,
                text=text,
                platform="google_chat",
                user_name=user_name,
                allowed_users=settings.google_chat_allowed_users,
            )
            
            return {"text": response}
        
        elif event_type == "ADDED_TO_SPACE":
            space = data.get("space", {})
            space_type = space.get("type")
            
            if space_type == "DM":
                return {"text": "歡迎使用 CursorBot！發送 /help 查看可用指令。"}
            else:
                return {"text": "感謝添加！提及我並發送訊息即可開始對話。"}
        
        elif event_type == "REMOVED_FROM_SPACE":
            logger.info("Google Chat: Removed from space")
        
        return Response(status_code=200)
        
    except Exception as e:
        logger.error(f"Google Chat webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# WhatsApp Cloud API Webhook
# ============================================

@router.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """WhatsApp webhook verification (GET request)."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    verify_token = settings.whatsapp_verify_token
    
    if mode == "subscribe" and token == verify_token:
        logger.info("WhatsApp webhook verified")
        return Response(content=challenge, media_type="text/plain")
    
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """WhatsApp Cloud API webhook endpoint."""
    try:
        data = await request.json()
        
        # Process messages
        entry = data.get("entry", [])
        for e in entry:
            changes = e.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                
                for message in messages:
                    msg_type = message.get("type")
                    
                    if msg_type == "text":
                        text = message.get("text", {}).get("body", "").strip()
                        from_number = message.get("from", "")
                        phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
                        
                        logger.info(f"WhatsApp message from {from_number}: {text[:50]}...")
                        
                        response = await handle_platform_message(
                            user_id=from_number,
                            text=text,
                            platform="whatsapp",
                            allowed_users=settings.whatsapp_allowed_numbers,
                        )
                        
                        # Send reply
                        await _send_whatsapp_message(phone_number_id, from_number, response)
        
        return Response(status_code=200)
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _send_whatsapp_message(phone_number_id: str, to: str, text: str) -> bool:
    """Send WhatsApp message via Cloud API."""
    import httpx
    
    access_token = settings.whatsapp_access_token
    if not access_token:
        logger.error("WHATSAPP_ACCESS_TOKEN not configured")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.facebook.com/v18.0/{phone_number_id}/messages",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to,
                    "type": "text",
                    "text": {"body": text[:4096]},  # WhatsApp limit
                },
                timeout=10.0,
            )
            
            if response.status_code != 200:
                logger.error(f"WhatsApp message failed: {response.text}")
                return False
                
            return True
            
    except Exception as e:
        logger.error(f"WhatsApp message error: {e}")
        return False


__all__ = ["router"]
