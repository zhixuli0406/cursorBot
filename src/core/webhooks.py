"""
Webhook System for CursorBot
Inspired by Clawd Bot's webhook automation

Provides:
- Webhook endpoint registration
- External trigger handling
- GitHub/GitLab webhook support
- Custom webhook handlers
"""

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from fastapi import Request, HTTPException

from ..utils.logger import logger


class WebhookType(Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    GENERIC = "generic"
    CUSTOM = "custom"


@dataclass
class WebhookEndpoint:
    """Represents a webhook endpoint configuration."""
    webhook_id: str
    name: str
    webhook_type: WebhookType
    callback: Callable
    user_id: Optional[int] = None
    chat_id: Optional[int] = None
    secret: Optional[str] = None
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    filters: dict = field(default_factory=dict)  # Event filters

    @property
    def endpoint_url(self) -> str:
        """Get the webhook endpoint URL path."""
        return f"/webhooks/{self.webhook_id}"

    def to_dict(self) -> dict:
        return {
            "webhook_id": self.webhook_id,
            "name": self.name,
            "type": self.webhook_type.value,
            "enabled": self.enabled,
            "endpoint": self.endpoint_url,
            "created_at": self.created_at.isoformat(),
            "trigger_count": self.trigger_count,
        }


class WebhookManager:
    """
    Manages webhook endpoints and handlers.

    Usage:
        manager = get_webhook_manager()

        # Register a webhook
        webhook = manager.register_webhook(
            name="github_push",
            webhook_type=WebhookType.GITHUB,
            callback=handle_github_push,
            user_id=12345,
            secret="mysecret",
        )

        # In FastAPI route:
        @app.post("/webhooks/{webhook_id}")
        async def webhook_handler(webhook_id: str, request: Request):
            return await manager.handle_webhook(webhook_id, request)
    """

    def __init__(self):
        self._webhooks: dict[str, WebhookEndpoint] = {}

    def _generate_id(self) -> str:
        """Generate a unique webhook ID."""
        return uuid.uuid4().hex[:16]

    def _generate_secret(self) -> str:
        """Generate a webhook secret."""
        return uuid.uuid4().hex

    def register_webhook(
        self,
        name: str,
        webhook_type: WebhookType,
        callback: Callable,
        user_id: int = None,
        chat_id: int = None,
        secret: str = None,
        filters: dict = None,
    ) -> WebhookEndpoint:
        """
        Register a new webhook endpoint.

        Args:
            name: Webhook name
            webhook_type: Type of webhook
            callback: Function to call when triggered
            user_id: Associated user ID
            chat_id: Associated chat ID for notifications
            secret: Webhook secret for verification
            filters: Event filters (e.g., {"events": ["push", "pull_request"]})

        Returns:
            WebhookEndpoint instance
        """
        webhook_id = self._generate_id()

        webhook = WebhookEndpoint(
            webhook_id=webhook_id,
            name=name,
            webhook_type=webhook_type,
            callback=callback,
            user_id=user_id,
            chat_id=chat_id,
            secret=secret or self._generate_secret(),
            filters=filters or {},
        )

        self._webhooks[webhook_id] = webhook
        logger.info(f"Registered webhook: {name} ({webhook_id})")
        return webhook

    def unregister_webhook(self, webhook_id: str) -> bool:
        """Unregister a webhook."""
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            logger.info(f"Unregistered webhook: {webhook_id}")
            return True
        return False

    def get_webhook(self, webhook_id: str) -> Optional[WebhookEndpoint]:
        """Get a webhook by ID."""
        return self._webhooks.get(webhook_id)

    def list_webhooks(self, user_id: int = None) -> list[WebhookEndpoint]:
        """List all webhooks, optionally filtered by user."""
        webhooks = list(self._webhooks.values())
        if user_id:
            webhooks = [w for w in webhooks if w.user_id == user_id]
        return webhooks

    def verify_github_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """Verify GitHub webhook signature."""
        if not signature or not signature.startswith("sha256="):
            return False

        expected_sig = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected_sig}", signature)

    def verify_gitlab_token(self, token: str, secret: str) -> bool:
        """Verify GitLab webhook token."""
        return token == secret

    async def handle_webhook(
        self,
        webhook_id: str,
        request: Request,
    ) -> dict:
        """
        Handle an incoming webhook request.

        Args:
            webhook_id: Webhook ID
            request: FastAPI request object

        Returns:
            Response dictionary
        """
        webhook = self._webhooks.get(webhook_id)

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        if not webhook.enabled:
            raise HTTPException(status_code=403, detail="Webhook disabled")

        # Get request body
        try:
            body = await request.body()
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {}

        # Verify signature based on type
        if webhook.webhook_type == WebhookType.GITHUB:
            signature = request.headers.get("X-Hub-Signature-256", "")
            if webhook.secret and not self.verify_github_signature(body, signature, webhook.secret):
                raise HTTPException(status_code=401, detail="Invalid signature")

            # Get event type
            event_type = request.headers.get("X-GitHub-Event", "unknown")
            payload["_event_type"] = event_type

        elif webhook.webhook_type == WebhookType.GITLAB:
            token = request.headers.get("X-Gitlab-Token", "")
            if webhook.secret and not self.verify_gitlab_token(token, webhook.secret):
                raise HTTPException(status_code=401, detail="Invalid token")

            # Get event type
            event_type = request.headers.get("X-Gitlab-Event", "unknown")
            payload["_event_type"] = event_type

        # Check event filters
        if webhook.filters.get("events"):
            event_type = payload.get("_event_type", "")
            if event_type not in webhook.filters["events"]:
                return {"status": "ignored", "reason": "event filtered"}

        # Update webhook stats
        webhook.last_triggered = datetime.now()
        webhook.trigger_count += 1

        # Execute callback
        try:
            if asyncio.iscoroutinefunction(webhook.callback):
                import asyncio
                result = await webhook.callback(payload, webhook)
            else:
                result = webhook.callback(payload, webhook)

            logger.info(f"Webhook {webhook_id} triggered successfully")
            return {"status": "success", "result": result}

        except Exception as e:
            logger.error(f"Webhook {webhook_id} error: {e}")
            return {"status": "error", "message": str(e)}


# ============================================
# Common Webhook Handlers
# ============================================


async def github_push_handler(payload: dict, webhook: WebhookEndpoint) -> dict:
    """
    Handle GitHub push events.

    Creates a task to review the pushed commits.
    """
    ref = payload.get("ref", "")
    commits = payload.get("commits", [])
    repository = payload.get("repository", {})
    repo_name = repository.get("full_name", "unknown")

    # Get commit messages
    commit_msgs = [c.get("message", "")[:50] for c in commits[:5]]

    return {
        "event": "push",
        "ref": ref,
        "repo": repo_name,
        "commits": len(commits),
        "messages": commit_msgs,
    }


async def github_pr_handler(payload: dict, webhook: WebhookEndpoint) -> dict:
    """
    Handle GitHub pull request events.
    """
    action = payload.get("action", "")
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number", 0)
    pr_title = pr.get("title", "")
    repository = payload.get("repository", {})
    repo_name = repository.get("full_name", "unknown")

    return {
        "event": "pull_request",
        "action": action,
        "repo": repo_name,
        "pr_number": pr_number,
        "pr_title": pr_title,
    }


async def github_issue_handler(payload: dict, webhook: WebhookEndpoint) -> dict:
    """
    Handle GitHub issue events.
    """
    action = payload.get("action", "")
    issue = payload.get("issue", {})
    issue_number = issue.get("number", 0)
    issue_title = issue.get("title", "")
    repository = payload.get("repository", {})
    repo_name = repository.get("full_name", "unknown")

    return {
        "event": "issue",
        "action": action,
        "repo": repo_name,
        "issue_number": issue_number,
        "issue_title": issue_title,
    }


# Need asyncio for iscoroutinefunction check
import asyncio

# Global instance
_webhook_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """Get the global WebhookManager instance."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager


__all__ = [
    "WebhookManager",
    "WebhookEndpoint",
    "WebhookType",
    "get_webhook_manager",
    # Handlers
    "github_push_handler",
    "github_pr_handler",
    "github_issue_handler",
]
