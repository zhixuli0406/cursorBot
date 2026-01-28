"""
Agent to Agent Communication for CursorBot

Provides:
- Cross-session collaboration between agents
- Session discovery and messaging
- Task delegation and result sharing
- Multi-agent workflows

Usage:
    from src.core.agent_to_agent import get_a2a_manager
    
    a2a = get_a2a_manager()
    
    # List active sessions
    sessions = await a2a.list_sessions()
    
    # Send message to another session
    await a2a.send_message(target_session_id, "Complete this task...")
    
    # Delegate task
    result = await a2a.delegate_task(target_session_id, task_prompt)
"""

import os
import json
import asyncio
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
from dataclasses import dataclass, field

from ..utils.logger import logger


class SessionStatus(Enum):
    """Agent session status."""
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class MessageType(Enum):
    """Inter-agent message types."""
    TEXT = "text"
    TASK = "task"
    RESULT = "result"
    QUERY = "query"
    BROADCAST = "broadcast"
    SYNC = "sync"


@dataclass
class AgentSession:
    """Represents an agent session."""
    id: str
    name: str = ""
    user_id: str = ""
    platform: str = ""  # telegram, discord, etc.
    status: SessionStatus = SessionStatus.IDLE
    capabilities: list[str] = field(default_factory=list)
    current_task: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def is_active(self) -> bool:
        return self.status in [SessionStatus.ACTIVE, SessionStatus.IDLE]
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "platform": self.platform,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "current_task": self.current_task,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentSession":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            user_id=data.get("user_id", ""),
            platform=data.get("platform", ""),
            status=SessionStatus(data.get("status", "idle")),
            capabilities=data.get("capabilities", []),
            current_task=data.get("current_task", ""),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            last_activity=datetime.fromisoformat(data.get("last_activity", datetime.now().isoformat())),
            metadata=data.get("metadata", {}),
        )


@dataclass
class A2AMessage:
    """Inter-agent message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.TEXT
    sender_id: str = ""
    recipient_id: str = ""
    content: str = ""
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: str = ""
    expires_at: datetime = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "content": self.content,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "A2AMessage":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=MessageType(data.get("type", "text")),
            sender_id=data.get("sender_id", ""),
            recipient_id=data.get("recipient_id", ""),
            content=data.get("content", ""),
            payload=data.get("payload", {}),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            reply_to=data.get("reply_to", ""),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )


@dataclass
class DelegatedTask:
    """A task delegated to another agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str = ""
    delegated_to: str = ""
    delegated_by: str = ""
    status: str = "pending"  # pending, running, completed, failed
    result: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = None
    timeout: int = 300  # seconds
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "delegated_to": self.delegated_to,
            "delegated_by": self.delegated_by,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "timeout": self.timeout,
        }


class AgentToAgentManager:
    """
    Manages agent-to-agent communication.
    
    Provides:
    - Session registry and discovery
    - Message routing between sessions
    - Task delegation and result collection
    - Multi-agent workflows
    """
    
    def __init__(self, session_id: str = None):
        """
        Initialize A2A manager.
        
        Args:
            session_id: This session's ID (auto-generated if not provided)
        """
        self.session_id = session_id or str(uuid.uuid4())
        
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "a2a"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.sessions_file = self.data_dir / "sessions.json"
        self.messages_dir = self.data_dir / "messages"
        self.messages_dir.mkdir(exist_ok=True)
        
        self._session: Optional[AgentSession] = None
        self._message_handlers: list[Callable] = []
        self._task_handlers: list[Callable] = []
        self._pending_tasks: dict[str, DelegatedTask] = {}
        
        self._running = False
        self._poll_task = None
    
    # ============================================
    # Lifecycle
    # ============================================
    
    async def start(
        self,
        name: str = "",
        user_id: str = "",
        platform: str = "",
        capabilities: list[str] = None,
    ) -> bool:
        """
        Start the A2A manager and register this session.
        
        Args:
            name: Session display name
            user_id: Associated user ID
            platform: Platform (telegram, discord, etc.)
            capabilities: List of capabilities this session provides
            
        Returns:
            True if started successfully
        """
        try:
            # Create session
            self._session = AgentSession(
                id=self.session_id,
                name=name or f"Session-{self.session_id[:8]}",
                user_id=user_id,
                platform=platform,
                status=SessionStatus.ACTIVE,
                capabilities=capabilities or [],
            )
            
            # Register session
            await self._register_session()
            
            # Start message polling
            self._running = True
            self._poll_task = asyncio.create_task(self._poll_messages())
            
            logger.info(f"A2A started: {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"A2A start error: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the A2A manager."""
        self._running = False
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        
        # Update status
        if self._session:
            self._session.status = SessionStatus.OFFLINE
            await self._update_session()
        
        logger.info("A2A stopped")
    
    # ============================================
    # Session Management
    # ============================================
    
    async def _register_session(self) -> None:
        """Register this session in the registry."""
        sessions = await self._load_sessions()
        sessions[self.session_id] = self._session.to_dict()
        await self._save_sessions(sessions)
    
    async def _update_session(self) -> None:
        """Update this session in the registry."""
        if not self._session:
            return
        
        self._session.last_activity = datetime.now()
        
        sessions = await self._load_sessions()
        sessions[self.session_id] = self._session.to_dict()
        await self._save_sessions(sessions)
    
    async def _load_sessions(self) -> dict:
        """Load sessions from file."""
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    async def _save_sessions(self, sessions: dict) -> None:
        """Save sessions to file."""
        with open(self.sessions_file, "w") as f:
            json.dump(sessions, f, indent=2)
    
    async def list_sessions(
        self,
        active_only: bool = True,
        platform: str = None,
    ) -> list[AgentSession]:
        """
        List available sessions.
        
        Args:
            active_only: Only return active sessions
            platform: Filter by platform
            
        Returns:
            List of sessions
        """
        sessions_data = await self._load_sessions()
        sessions = []
        
        for session_data in sessions_data.values():
            session = AgentSession.from_dict(session_data)
            
            # Skip own session
            if session.id == self.session_id:
                continue
            
            # Filter by status
            if active_only and not session.is_active():
                # Check if session is stale (no activity for 5 minutes)
                if (datetime.now() - session.last_activity).total_seconds() > 300:
                    continue
            
            # Filter by platform
            if platform and session.platform != platform:
                continue
            
            sessions.append(session)
        
        return sessions
    
    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get a specific session by ID."""
        sessions_data = await self._load_sessions()
        
        if session_id in sessions_data:
            return AgentSession.from_dict(sessions_data[session_id])
        
        return None
    
    async def find_sessions_by_capability(
        self,
        capability: str,
    ) -> list[AgentSession]:
        """Find sessions that have a specific capability."""
        sessions = await self.list_sessions(active_only=True)
        return [s for s in sessions if capability in s.capabilities]
    
    # ============================================
    # Messaging
    # ============================================
    
    async def send_message(
        self,
        recipient_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        payload: dict = None,
        reply_to: str = None,
    ) -> Optional[str]:
        """
        Send a message to another session.
        
        Args:
            recipient_id: Target session ID
            content: Message content
            message_type: Type of message
            payload: Additional data
            reply_to: ID of message being replied to
            
        Returns:
            Message ID or None
        """
        message = A2AMessage(
            type=message_type,
            sender_id=self.session_id,
            recipient_id=recipient_id,
            content=content,
            payload=payload or {},
            reply_to=reply_to or "",
        )
        
        # Save to recipient's inbox
        inbox_file = self.messages_dir / f"{recipient_id}.json"
        
        messages = []
        if inbox_file.exists():
            try:
                with open(inbox_file) as f:
                    messages = json.load(f)
            except Exception:
                pass
        
        messages.append(message.to_dict())
        
        with open(inbox_file, "w") as f:
            json.dump(messages, f, indent=2)
        
        logger.debug(f"A2A message sent: {self.session_id} -> {recipient_id}")
        return message.id
    
    async def broadcast(
        self,
        content: str,
        payload: dict = None,
        platform: str = None,
    ) -> list[str]:
        """
        Broadcast a message to all active sessions.
        
        Args:
            content: Message content
            payload: Additional data
            platform: Only broadcast to specific platform
            
        Returns:
            List of message IDs
        """
        sessions = await self.list_sessions(active_only=True, platform=platform)
        message_ids = []
        
        for session in sessions:
            msg_id = await self.send_message(
                recipient_id=session.id,
                content=content,
                message_type=MessageType.BROADCAST,
                payload=payload,
            )
            if msg_id:
                message_ids.append(msg_id)
        
        return message_ids
    
    async def _poll_messages(self) -> None:
        """Poll for incoming messages."""
        while self._running:
            try:
                inbox_file = self.messages_dir / f"{self.session_id}.json"
                
                if inbox_file.exists():
                    with open(inbox_file) as f:
                        messages = json.load(f)
                    
                    # Process messages
                    for msg_data in messages:
                        message = A2AMessage.from_dict(msg_data)
                        await self._handle_message(message)
                    
                    # Clear inbox
                    with open(inbox_file, "w") as f:
                        json.dump([], f)
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"A2A poll error: {e}")
                await asyncio.sleep(5)
    
    async def _handle_message(self, message: A2AMessage) -> None:
        """Handle an incoming message."""
        logger.debug(f"A2A received: {message.type.value} from {message.sender_id}")
        
        # Handle task messages
        if message.type == MessageType.TASK:
            await self._handle_task_message(message)
        elif message.type == MessageType.RESULT:
            await self._handle_result_message(message)
        
        # Notify handlers
        for handler in self._message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Message handler error: {e}")
    
    def on_message(self, handler: Callable) -> None:
        """Register a message handler."""
        self._message_handlers.append(handler)
    
    # ============================================
    # Task Delegation
    # ============================================
    
    async def delegate_task(
        self,
        target_session_id: str,
        prompt: str,
        timeout: int = 300,
        wait: bool = True,
    ) -> Optional[str]:
        """
        Delegate a task to another session.
        
        Args:
            target_session_id: Session to delegate to
            prompt: Task prompt/description
            timeout: Timeout in seconds
            wait: Whether to wait for result
            
        Returns:
            Task result if wait=True, task ID otherwise
        """
        task = DelegatedTask(
            prompt=prompt,
            delegated_to=target_session_id,
            delegated_by=self.session_id,
            timeout=timeout,
        )
        
        # Store pending task
        self._pending_tasks[task.id] = task
        
        # Send task message
        await self.send_message(
            recipient_id=target_session_id,
            content=prompt,
            message_type=MessageType.TASK,
            payload={"task_id": task.id, "timeout": timeout},
        )
        
        if not wait:
            return task.id
        
        # Wait for result
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout:
            if task.status == "completed":
                return task.result
            elif task.status == "failed":
                return None
            
            await asyncio.sleep(1)
        
        # Timeout
        task.status = "failed"
        return None
    
    async def _handle_task_message(self, message: A2AMessage) -> None:
        """Handle an incoming task."""
        task_id = message.payload.get("task_id")
        prompt = message.content
        
        # Update session status
        if self._session:
            self._session.status = SessionStatus.BUSY
            self._session.current_task = prompt[:50]
            await self._update_session()
        
        # Execute task via handlers
        result = None
        for handler in self._task_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(prompt, message.sender_id)
                else:
                    result = handler(prompt, message.sender_id)
                
                if result:
                    break
            except Exception as e:
                logger.error(f"Task handler error: {e}")
        
        # Send result
        await self.send_message(
            recipient_id=message.sender_id,
            content=result or "Task completed",
            message_type=MessageType.RESULT,
            payload={"task_id": task_id, "success": bool(result)},
            reply_to=message.id,
        )
        
        # Update session status
        if self._session:
            self._session.status = SessionStatus.ACTIVE
            self._session.current_task = ""
            await self._update_session()
    
    async def _handle_result_message(self, message: A2AMessage) -> None:
        """Handle a task result."""
        task_id = message.payload.get("task_id")
        
        if task_id in self._pending_tasks:
            task = self._pending_tasks[task_id]
            task.status = "completed" if message.payload.get("success") else "failed"
            task.result = message.content
            task.completed_at = datetime.now()
    
    def on_task(self, handler: Callable) -> None:
        """Register a task handler."""
        self._task_handlers.append(handler)
    
    async def get_task_status(self, task_id: str) -> Optional[DelegatedTask]:
        """Get status of a delegated task."""
        return self._pending_tasks.get(task_id)
    
    # ============================================
    # Multi-Agent Workflows
    # ============================================
    
    async def coordinate_workflow(
        self,
        steps: list[dict],
        parallel: bool = False,
    ) -> list[dict]:
        """
        Coordinate a multi-step workflow across agents.
        
        Args:
            steps: List of workflow steps, each with:
                   - session_id: Target session (or capability)
                   - prompt: Task prompt
                   - timeout: Step timeout
            parallel: Run steps in parallel if True
            
        Returns:
            List of step results
        """
        results = []
        
        if parallel:
            # Run all steps concurrently
            tasks = []
            for step in steps:
                session_id = step.get("session_id")
                
                # Find session by capability if needed
                if not session_id and step.get("capability"):
                    sessions = await self.find_sessions_by_capability(step["capability"])
                    if sessions:
                        session_id = sessions[0].id
                
                if session_id:
                    task = asyncio.create_task(
                        self.delegate_task(
                            target_session_id=session_id,
                            prompt=step.get("prompt", ""),
                            timeout=step.get("timeout", 300),
                        )
                    )
                    tasks.append((step, task))
            
            # Gather results
            for step, task in tasks:
                try:
                    result = await task
                    results.append({
                        "step": step,
                        "success": result is not None,
                        "result": result,
                    })
                except Exception as e:
                    results.append({
                        "step": step,
                        "success": False,
                        "error": str(e),
                    })
        
        else:
            # Run steps sequentially
            context = {}
            
            for step in steps:
                session_id = step.get("session_id")
                
                # Find session by capability if needed
                if not session_id and step.get("capability"):
                    sessions = await self.find_sessions_by_capability(step["capability"])
                    if sessions:
                        session_id = sessions[0].id
                
                if not session_id:
                    results.append({
                        "step": step,
                        "success": False,
                        "error": "No suitable session found",
                    })
                    continue
                
                # Interpolate context into prompt
                prompt = step.get("prompt", "")
                for key, value in context.items():
                    prompt = prompt.replace(f"{{{{result.{key}}}}}", str(value))
                
                try:
                    result = await self.delegate_task(
                        target_session_id=session_id,
                        prompt=prompt,
                        timeout=step.get("timeout", 300),
                    )
                    
                    # Store result in context
                    step_name = step.get("name", f"step_{len(results)}")
                    context[step_name] = result
                    
                    results.append({
                        "step": step,
                        "success": result is not None,
                        "result": result,
                    })
                    
                except Exception as e:
                    results.append({
                        "step": step,
                        "success": False,
                        "error": str(e),
                    })
                    
                    # Stop on failure if required
                    if step.get("required", True):
                        break
        
        return results
    
    # ============================================
    # Status
    # ============================================
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def get_stats(self) -> dict:
        """Get A2A statistics."""
        return {
            "session_id": self.session_id,
            "running": self._running,
            "status": self._session.status.value if self._session else "offline",
            "pending_tasks": len(self._pending_tasks),
            "message_handlers": len(self._message_handlers),
            "task_handlers": len(self._task_handlers),
        }


# ============================================
# Global Instance
# ============================================

_a2a_manager: Optional[AgentToAgentManager] = None


def get_a2a_manager() -> AgentToAgentManager:
    """Get the global A2A manager instance."""
    global _a2a_manager
    if _a2a_manager is None:
        _a2a_manager = AgentToAgentManager()
    return _a2a_manager


__all__ = [
    "SessionStatus",
    "MessageType",
    "AgentSession",
    "A2AMessage",
    "DelegatedTask",
    "AgentToAgentManager",
    "get_a2a_manager",
]
