"""
Media handlers for Telegram Bot
Handles voice messages, images, and other media types
"""

import base64
import io
import os
import tempfile
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, PhotoSize
from telegram.ext import ContextTypes, MessageHandler, filters

from ..utils.auth import authorized_only
from ..utils.config import settings
from ..utils.logger import logger
from .keyboards import get_media_received_keyboard

# Media cache: user_id -> list of media data
_media_cache: dict[int, list[dict]] = {}
_cache_expiry: dict[int, datetime] = {}
CACHE_TTL_MINUTES = 3


def _cleanup_expired_cache():
    """Remove expired media cache entries."""
    now = datetime.now()
    expired_users = [
        user_id for user_id, expiry in _cache_expiry.items()
        if now > expiry
    ]
    for user_id in expired_users:
        _media_cache.pop(user_id, None)
        _cache_expiry.pop(user_id, None)


def add_to_cache(user_id: int, media_data: dict):
    """Add media to user's cache."""
    _cleanup_expired_cache()

    if user_id not in _media_cache:
        _media_cache[user_id] = []

    _media_cache[user_id].append(media_data)
    _cache_expiry[user_id] = datetime.now() + timedelta(minutes=CACHE_TTL_MINUTES)


def get_cached_media(user_id: int) -> list[dict]:
    """Get user's cached media."""
    _cleanup_expired_cache()
    return _media_cache.get(user_id, [])


def clear_cache(user_id: int):
    """Clear user's media cache."""
    _media_cache.pop(user_id, None)
    _cache_expiry.pop(user_id, None)


def get_cache_count(user_id: int) -> int:
    """Get count of cached media for user."""
    return len(get_cached_media(user_id))


# ============================================
# Voice Message Handling
# ============================================


async def transcribe_voice_google(audio_data: bytes) -> Optional[str]:
    """
    Transcribe voice using Google Gemini API.

    Args:
        audio_data: Audio file bytes

    Returns:
        Transcribed text or None
    """
    if not settings.google_ai_api_key:
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.google_ai_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Create audio part
        audio_part = {
            "mime_type": "audio/ogg",
            "data": base64.b64encode(audio_data).decode()
        }

        response = model.generate_content([
            "Please transcribe this audio message accurately. Return only the transcription, no additional text.",
            audio_part
        ])

        return response.text.strip()

    except ImportError:
        logger.warning("google-generativeai not installed")
        return None
    except Exception as e:
        logger.error(f"Google transcription error: {e}")
        return None


async def transcribe_voice_openrouter(audio_data: bytes) -> Optional[str]:
    """
    Transcribe voice using OpenRouter API with Whisper.

    Args:
        audio_data: Audio file bytes

    Returns:
        Transcribed text or None
    """
    if not settings.openrouter_api_key:
        return None

    try:
        import httpx

        # OpenRouter doesn't directly support audio, use OpenAI Whisper
        # This is a placeholder - would need actual Whisper API integration
        logger.warning("OpenRouter voice transcription not implemented")
        return None

    except Exception as e:
        logger.error(f"OpenRouter transcription error: {e}")
        return None


@authorized_only
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle voice messages.
    Transcribes the voice and processes as a task request.
    """
    user_id = update.effective_user.id
    voice = update.message.voice

    logger.info(f"Voice message from user {user_id}, duration: {voice.duration}s")

    # Check if transcription is available
    if not settings.google_ai_api_key:
        await update.message.reply_text(
            "⚠️ <b>語音轉錄未啟用</b>\n\n"
            "請設定 GOOGLE_GENERATIVE_AI_API_KEY 來啟用語音功能。",
            parse_mode="HTML",
        )
        return

    # Download voice file
    status_msg = await update.message.reply_text("🎤 正在轉錄語音訊息...")

    try:
        voice_file = await context.bot.get_file(voice.file_id)
        voice_bytes = await voice_file.download_as_bytearray()

        # Transcribe
        transcription = await transcribe_voice_google(bytes(voice_bytes))

        if transcription:
            await status_msg.edit_text(
                f"🎤 <b>語音轉錄</b>\n\n"
                f"<i>{transcription}</i>\n\n"
                f"正在處理任務...",
                parse_mode="HTML",
            )

            # Process as a task request
            from .handlers import _handle_background_agent_ask
            chat_id = update.effective_chat.id
            username = update.effective_user.username or update.effective_user.first_name

            await _handle_background_agent_ask(
                update, transcription, user_id, username, chat_id
            )

        else:
            await status_msg.edit_text(
                "❌ <b>轉錄失敗</b>\n\n"
                "無法識別語音內容，請重試或直接輸入文字。",
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Voice handling error: {e}")
        await status_msg.edit_text(f"❌ 處理語音時發生錯誤: {str(e)[:100]}")


# ============================================
# Image Handling
# ============================================


async def process_image(photo: PhotoSize, context) -> dict:
    """
    Process and cache an image.

    Args:
        photo: Telegram PhotoSize object
        context: Bot context

    Returns:
        Image data dictionary
    """
    try:
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        # Encode as base64
        base64_data = base64.b64encode(bytes(image_bytes)).decode()

        return {
            "type": "image",
            "file_id": photo.file_id,
            "base64": base64_data,
            "mime_type": "image/jpeg",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return None


@authorized_only
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle photo messages.
    Caches the image for inclusion in task requests.
    """
    user_id = update.effective_user.id
    photo = update.message.photo[-1]  # Get highest resolution

    logger.info(f"Photo from user {user_id}, file_id: {photo.file_id}")

    # Process and cache image
    image_data = await process_image(photo, context)

    if image_data:
        add_to_cache(user_id, image_data)
        cache_count = get_cache_count(user_id)

        await update.message.reply_text(
            f"📸 <b>圖片已儲存</b>\n\n"
            f"已快取 {cache_count} 張圖片（{CACHE_TTL_MINUTES} 分鐘內有效）\n\n"
            f"發送文字訊息來建立包含圖片的任務。",
            parse_mode="HTML",
            reply_markup=get_media_received_keyboard(),
        )
    else:
        await update.message.reply_text(
            "❌ 圖片處理失敗，請重試。",
            parse_mode="HTML",
        )


# ============================================
# Document Handling
# ============================================


@authorized_only
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle document/file uploads.
    """
    user_id = update.effective_user.id
    document = update.message.document

    logger.info(f"Document from user {user_id}: {document.file_name}")

    # Check if it's an image
    if document.mime_type and document.mime_type.startswith("image/"):
        # Process as image
        try:
            file = await context.bot.get_file(document.file_id)
            file_bytes = await file.download_as_bytearray()

            base64_data = base64.b64encode(bytes(file_bytes)).decode()

            image_data = {
                "type": "image",
                "file_id": document.file_id,
                "file_name": document.file_name,
                "base64": base64_data,
                "mime_type": document.mime_type,
                "timestamp": datetime.now().isoformat(),
            }

            add_to_cache(user_id, image_data)
            cache_count = get_cache_count(user_id)

            await update.message.reply_text(
                f"📸 <b>圖片已儲存</b>\n\n"
                f"檔案: {document.file_name}\n"
                f"已快取 {cache_count} 張圖片\n\n"
                f"發送文字訊息來建立任務。",
                parse_mode="HTML",
            )

        except Exception as e:
            logger.error(f"Document processing error: {e}")
            await update.message.reply_text(f"❌ 處理檔案時發生錯誤")

    else:
        await update.message.reply_text(
            "ℹ️ 目前僅支援圖片檔案。\n\n"
            "支援格式: JPG, PNG, GIF, WEBP"
        )


def setup_media_handlers(app) -> None:
    """
    Setup media message handlers.

    Args:
        app: Telegram Application instance
    """
    # Voice message handler
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))

    # Photo handler
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # Document handler
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))

    logger.info("Media handlers configured")


__all__ = [
    "voice_handler",
    "photo_handler",
    "document_handler",
    "setup_media_handlers",
    "get_cached_media",
    "clear_cache",
    "get_cache_count",
]
