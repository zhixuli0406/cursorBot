"""
Approval System for CursorBot
Inspired by Clawd Bot's approval workflows

Provides approval workflows for:
- Sensitive operations
- Destructive actions (delete, reset)
- High-cost operations
- Permission elevation
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ..utils.logger import logger


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalType(Enum):
    DESTRUCTIVE = "destructive"  # Delete, reset operations
    COSTLY = "costly"  # High token/API cost operations
    SENSITIVE = "sensitive"  # Security-related
    ELEVATED = "elevated"  # Requires elevated permissions
    CUSTOM = "custom"  # Custom approval type


class PendingApproval:
    """Represents a pending approval request."""

    def __init__(
        self,
        approval_id: str,
        user_id: int,
        approval_type: ApprovalType,
        action: str,
        description: str,
        callback: Optional[Callable] = None,
        callback_args: Optional[tuple] = None,
        callback_kwargs: Optional[dict] = None,
        expires_in: int = 300,  # 5 minutes default
        metadata: Optional[dict] = None,
    ):
        self.approval_id = approval_id
        self.user_id = user_id
        self.approval_type = approval_type
        self.action = action
        self.description = description
        self.callback = callback
        self.callback_args = callback_args or ()
        self.callback_kwargs = callback_kwargs or {}
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=expires_in)
        self.status = ApprovalStatus.PENDING
        self.metadata = metadata or {}
        self.result: Any = None

    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "approval_id": self.approval_id,
            "user_id": self.user_id,
            "type": self.approval_type.value,
            "action": self.action,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


class ApprovalManager:
    """
    Manages approval workflows for sensitive operations.

    Usage:
        manager = get_approval_manager()

        # Request approval
        approval = await manager.request_approval(
            update=update,
            user_id=user_id,
            approval_type=ApprovalType.DESTRUCTIVE,
            action="delete_repo",
            description="Delete repository xyz",
            callback=delete_repo_func,
            callback_args=(repo_id,),
        )

        # Approval is handled via callback when user clicks button
    """

    def __init__(self):
        self._pending: dict[str, PendingApproval] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def _generate_id(self) -> str:
        """Generate a short approval ID."""
        return uuid.uuid4().hex[:8]

    async def _cleanup_expired(self) -> None:
        """Cleanup expired approvals periodically."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            expired = [
                aid for aid, approval in self._pending.items()
                if approval.is_expired
            ]
            for aid in expired:
                approval = self._pending.pop(aid, None)
                if approval:
                    approval.status = ApprovalStatus.EXPIRED
                    logger.debug(f"Approval {aid} expired")

    def start_cleanup(self) -> None:
        """Start the cleanup background task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())

    async def request_approval(
        self,
        update: Update,
        user_id: int,
        approval_type: ApprovalType,
        action: str,
        description: str,
        callback: Optional[Callable] = None,
        callback_args: Optional[tuple] = None,
        callback_kwargs: Optional[dict] = None,
        expires_in: int = 300,
        metadata: Optional[dict] = None,
    ) -> PendingApproval:
        """
        Request user approval for an action.

        Args:
            update: Telegram update object
            user_id: User ID requesting approval
            approval_type: Type of approval
            action: Action identifier
            description: Human-readable description
            callback: Function to call if approved
            callback_args: Args for callback
            callback_kwargs: Kwargs for callback
            expires_in: Seconds until expiration
            metadata: Additional metadata

        Returns:
            PendingApproval object
        """
        approval_id = self._generate_id()

        approval = PendingApproval(
            approval_id=approval_id,
            user_id=user_id,
            approval_type=approval_type,
            action=action,
            description=description,
            callback=callback,
            callback_args=callback_args,
            callback_kwargs=callback_kwargs,
            expires_in=expires_in,
            metadata=metadata,
        )

        self._pending[approval_id] = approval

        # Send approval request message
        type_emoji = {
            ApprovalType.DESTRUCTIVE: "⚠️",
            ApprovalType.COSTLY: "💰",
            ApprovalType.SENSITIVE: "🔐",
            ApprovalType.ELEVATED: "🔑",
            ApprovalType.CUSTOM: "❓",
        }

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ 批准", callback_data=f"approve:{approval_id}"),
                InlineKeyboardButton("❌ 拒絕", callback_data=f"reject:{approval_id}"),
            ],
            [InlineKeyboardButton("ℹ️ 詳情", callback_data=f"approval_info:{approval_id}")],
        ])

        emoji = type_emoji.get(approval_type, "❓")
        expires_str = approval.expires_at.strftime("%H:%M:%S")

        await update.effective_chat.send_message(
            f"{emoji} <b>需要確認</b>\n\n"
            f"<b>操作:</b> {action}\n"
            f"<b>說明:</b> {description}\n"
            f"<b>類型:</b> {approval_type.value}\n"
            f"<b>有效期至:</b> {expires_str}\n\n"
            f"請確認是否執行此操作。",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

        logger.info(f"Approval requested: {approval_id} - {action}")
        return approval

    async def handle_approval_response(
        self,
        approval_id: str,
        approved: bool,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> dict:
        """
        Handle user's response to approval request.

        Args:
            approval_id: Approval ID
            approved: Whether approved or rejected
            update: Telegram update
            context: Telegram context

        Returns:
            Result dictionary
        """
        approval = self._pending.get(approval_id)

        if not approval:
            return {"success": False, "message": "Approval not found or expired"}

        if approval.is_expired:
            approval.status = ApprovalStatus.EXPIRED
            self._pending.pop(approval_id, None)
            return {"success": False, "message": "Approval has expired"}

        # Check user authorization
        if update.effective_user.id != approval.user_id:
            return {"success": False, "message": "Unauthorized"}

        result = {"success": True}

        if approved:
            approval.status = ApprovalStatus.APPROVED
            logger.info(f"Approval {approval_id} approved")

            # Execute callback if provided
            if approval.callback:
                try:
                    if asyncio.iscoroutinefunction(approval.callback):
                        approval.result = await approval.callback(
                            *approval.callback_args,
                            **approval.callback_kwargs
                        )
                    else:
                        approval.result = approval.callback(
                            *approval.callback_args,
                            **approval.callback_kwargs
                        )
                    result["callback_result"] = approval.result
                except Exception as e:
                    logger.error(f"Approval callback error: {e}")
                    result["callback_error"] = str(e)

            # Update message
            await update.callback_query.edit_message_text(
                f"✅ <b>已批准</b>\n\n"
                f"<b>操作:</b> {approval.action}\n"
                f"<b>狀態:</b> 已執行",
                parse_mode="HTML",
            )
        else:
            approval.status = ApprovalStatus.REJECTED
            logger.info(f"Approval {approval_id} rejected")

            await update.callback_query.edit_message_text(
                f"❌ <b>已拒絕</b>\n\n"
                f"<b>操作:</b> {approval.action}\n"
                f"<b>狀態:</b> 已取消",
                parse_mode="HTML",
            )

        # Remove from pending
        self._pending.pop(approval_id, None)

        return result

    async def get_approval_info(self, approval_id: str) -> Optional[dict]:
        """Get approval details."""
        approval = self._pending.get(approval_id)
        if approval:
            return approval.to_dict()
        return None

    def get_pending_approvals(self, user_id: int) -> list[PendingApproval]:
        """Get all pending approvals for a user."""
        return [
            a for a in self._pending.values()
            if a.user_id == user_id and not a.is_expired
        ]

    async def cancel_approval(self, approval_id: str) -> bool:
        """Cancel a pending approval."""
        approval = self._pending.pop(approval_id, None)
        if approval:
            approval.status = ApprovalStatus.CANCELLED
            return True
        return False


# Global instance
_approval_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    """Get the global ApprovalManager instance."""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
        _approval_manager.start_cleanup()
    return _approval_manager


# Decorator for requiring approval
def requires_approval(
    approval_type: ApprovalType = ApprovalType.CUSTOM,
    action: str = "custom_action",
    description: str = "This action requires approval",
):
    """
    Decorator to require approval before executing a handler.

    Usage:
        @requires_approval(
            approval_type=ApprovalType.DESTRUCTIVE,
            action="delete_task",
            description="Delete all tasks"
        )
        async def delete_all_tasks(update, context):
            # This will only run if approved
            pass
    """
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            manager = get_approval_manager()

            # Create approval with callback to original function
            await manager.request_approval(
                update=update,
                user_id=update.effective_user.id,
                approval_type=approval_type,
                action=action,
                description=description,
                callback=func,
                callback_args=(update, context) + args,
                callback_kwargs=kwargs,
            )

        return wrapper
    return decorator


__all__ = [
    "ApprovalManager",
    "ApprovalStatus",
    "ApprovalType",
    "PendingApproval",
    "get_approval_manager",
    "requires_approval",
]
