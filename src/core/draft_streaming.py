"""
Draft Streaming for CursorBot

Provides:
- Telegram-style draft message streaming
- Progressive message updates
- Efficient edit batching
- Rate-limited updates
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class StreamState(Enum):
    """Streaming states."""
    IDLE = "idle"
    STREAMING = "streaming"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StreamConfig:
    """Draft streaming configuration."""
    # Update frequency
    min_update_interval: float = 0.3  # Minimum seconds between updates
    batch_chars: int = 20  # Minimum chars to trigger update
    
    # Display
    show_cursor: bool = True
    cursor_char: str = "▌"
    typing_indicator: bool = True
    
    # Rate limiting
    max_updates_per_second: float = 3.0
    debounce_ms: int = 100


@dataclass
class DraftMessage:
    """Represents a draft message being streamed."""
    message_id: Any  # Platform message ID
    chat_id: Any
    content: str = ""
    state: StreamState = StreamState.IDLE
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    update_count: int = 0
    
    # Buffering
    _buffer: str = field(default="", repr=False)
    _pending_update: bool = field(default=False, repr=False)


class DraftStreamer:
    """
    Handles draft-style message streaming for Telegram.
    """
    
    def __init__(self, config: StreamConfig = None):
        self.config = config or StreamConfig()
        self._drafts: dict[str, DraftMessage] = {}
        self._update_callback: Optional[Callable] = None
        self._complete_callback: Optional[Callable] = None
        self._update_tasks: dict[str, asyncio.Task] = {}
    
    # ============================================
    # Stream Lifecycle
    # ============================================
    
    async def start_stream(
        self,
        chat_id: Any,
        message_id: Any,
        initial_content: str = "",
    ) -> DraftMessage:
        """
        Start a new draft stream.
        
        Args:
            chat_id: Chat ID
            message_id: Initial message ID
            initial_content: Starting content
        
        Returns:
            DraftMessage instance
        """
        key = self._make_key(chat_id, message_id)
        
        draft = DraftMessage(
            message_id=message_id,
            chat_id=chat_id,
            content=initial_content,
            state=StreamState.STREAMING,
        )
        
        self._drafts[key] = draft
        
        logger.debug(f"Draft stream started: {key}")
        return draft
    
    async def append(
        self,
        chat_id: Any,
        message_id: Any,
        text: str,
    ) -> None:
        """
        Append text to a draft stream.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID
            text: Text to append
        """
        key = self._make_key(chat_id, message_id)
        draft = self._drafts.get(key)
        
        if not draft:
            return
        
        if draft.state != StreamState.STREAMING:
            return
        
        # Add to buffer
        draft._buffer += text
        
        # Check if we should update
        if self._should_update(draft):
            await self._schedule_update(key, draft)
    
    async def complete(
        self,
        chat_id: Any,
        message_id: Any,
        final_content: str = None,
    ) -> None:
        """
        Complete a draft stream.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID
            final_content: Optional final content
        """
        key = self._make_key(chat_id, message_id)
        draft = self._drafts.get(key)
        
        if not draft:
            return
        
        # Flush remaining buffer
        if draft._buffer:
            draft.content += draft._buffer
            draft._buffer = ""
        
        if final_content:
            draft.content = final_content
        
        draft.state = StreamState.COMPLETED
        
        # Final update
        await self._send_update(draft, final=True)
        
        # Call completion callback
        if self._complete_callback:
            try:
                if asyncio.iscoroutinefunction(self._complete_callback):
                    await self._complete_callback(draft)
                else:
                    self._complete_callback(draft)
            except Exception as e:
                logger.error(f"Complete callback error: {e}")
        
        # Clean up
        self._cleanup(key)
        
        logger.debug(f"Draft stream completed: {key}")
    
    async def cancel(self, chat_id: Any, message_id: Any) -> None:
        """Cancel a draft stream."""
        key = self._make_key(chat_id, message_id)
        draft = self._drafts.get(key)
        
        if draft:
            draft.state = StreamState.IDLE
            self._cleanup(key)
    
    # ============================================
    # Update Management
    # ============================================
    
    def _should_update(self, draft: DraftMessage) -> bool:
        """Check if we should send an update."""
        # Check buffer size
        if len(draft._buffer) >= self.config.batch_chars:
            return True
        
        # Check time since last update
        elapsed = (datetime.now() - draft.last_update).total_seconds()
        if elapsed >= self.config.min_update_interval:
            return True
        
        return False
    
    async def _schedule_update(self, key: str, draft: DraftMessage) -> None:
        """Schedule a debounced update."""
        # Cancel existing task
        if key in self._update_tasks:
            self._update_tasks[key].cancel()
        
        # Schedule new task
        async def delayed_update():
            await asyncio.sleep(self.config.debounce_ms / 1000)
            await self._flush_and_update(key, draft)
        
        self._update_tasks[key] = asyncio.create_task(delayed_update())
    
    async def _flush_and_update(self, key: str, draft: DraftMessage) -> None:
        """Flush buffer and send update."""
        if not draft._buffer:
            return
        
        # Move buffer to content
        draft.content += draft._buffer
        draft._buffer = ""
        
        # Send update
        await self._send_update(draft)
    
    async def _send_update(self, draft: DraftMessage, final: bool = False) -> None:
        """Send update to platform."""
        # Prepare content with cursor
        content = draft.content
        if not final and self.config.show_cursor:
            content += self.config.cursor_char
        
        # Update tracking
        draft.last_update = datetime.now()
        draft.update_count += 1
        
        # Call update callback
        if self._update_callback:
            try:
                if asyncio.iscoroutinefunction(self._update_callback):
                    await self._update_callback(draft, content, final)
                else:
                    self._update_callback(draft, content, final)
            except Exception as e:
                logger.error(f"Update callback error: {e}")
                draft.state = StreamState.ERROR
    
    # ============================================
    # Helpers
    # ============================================
    
    def _make_key(self, chat_id: Any, message_id: Any) -> str:
        """Generate unique key for draft."""
        return f"{chat_id}:{message_id}"
    
    def _cleanup(self, key: str) -> None:
        """Clean up resources for a draft."""
        self._drafts.pop(key, None)
        
        if key in self._update_tasks:
            self._update_tasks[key].cancel()
            del self._update_tasks[key]
    
    # ============================================
    # Callbacks
    # ============================================
    
    def on_update(self, callback: Callable) -> None:
        """
        Set update callback.
        
        Callback signature: (draft: DraftMessage, content: str, final: bool) -> None
        """
        self._update_callback = callback
    
    def on_complete(self, callback: Callable) -> None:
        """
        Set completion callback.
        
        Callback signature: (draft: DraftMessage) -> None
        """
        self._complete_callback = callback
    
    # ============================================
    # Status
    # ============================================
    
    def get_active_streams(self) -> list[DraftMessage]:
        """Get all active draft streams."""
        return [
            d for d in self._drafts.values()
            if d.state == StreamState.STREAMING
        ]
    
    def get_stats(self) -> dict:
        """Get streaming statistics."""
        states = {}
        for draft in self._drafts.values():
            state = draft.state.value
            states[state] = states.get(state, 0) + 1
        
        return {
            "total_drafts": len(self._drafts),
            "active_streams": len(self.get_active_streams()),
            "by_state": states,
        }


# ============================================
# Telegram Integration Helper
# ============================================

class TelegramDraftStreamer(DraftStreamer):
    """
    Draft streamer with Telegram-specific integration.
    """
    
    def __init__(self, bot, config: StreamConfig = None):
        super().__init__(config)
        self._bot = bot
        
        # Set up callbacks
        self.on_update(self._telegram_update)
    
    async def _telegram_update(
        self,
        draft: DraftMessage,
        content: str,
        final: bool,
    ) -> None:
        """Handle Telegram message update."""
        try:
            await self._bot.edit_message_text(
                chat_id=draft.chat_id,
                message_id=draft.message_id,
                text=content,
                parse_mode="HTML" if final else None,
            )
        except Exception as e:
            # Rate limit or message not found
            if "message is not modified" not in str(e).lower():
                logger.warning(f"Telegram edit error: {e}")


# ============================================
# Global Instance
# ============================================

_draft_streamer: Optional[DraftStreamer] = None


def get_draft_streamer() -> DraftStreamer:
    """Get the global draft streamer instance."""
    global _draft_streamer
    if _draft_streamer is None:
        _draft_streamer = DraftStreamer()
    return _draft_streamer


__all__ = [
    "StreamState",
    "StreamConfig",
    "DraftMessage",
    "DraftStreamer",
    "TelegramDraftStreamer",
    "get_draft_streamer",
]
