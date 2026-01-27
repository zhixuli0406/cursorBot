"""
Agent Send System for CursorBot

Provides:
- Inter-agent communication
- Message routing between agents
- Agent-to-user messaging
- Broadcast capabilities
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class AgentMessageType(Enum):
    """Types of agent messages."""
    TASK = "task"
    RESULT = "result"
    STATUS = "status"
    NOTIFICATION = "notification"
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    BROADCAST = "broadcast"


@dataclass
class AgentMessage:
    """Message sent between agents."""
    id: str
    sender_agent: str
    receiver_agent: str
    message_type: AgentMessageType
    payload: Any
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Optional metadata
    correlation_id: Optional[str] = None  # For request/response pairing
    priority: int = 0
    ttl_seconds: int = 300  # Time to live
    requires_ack: bool = False
    
    def is_expired(self) -> bool:
        """Check if message has expired."""
        from datetime import timedelta
        return (datetime.now() - self.timestamp) > timedelta(seconds=self.ttl_seconds)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender_agent,
            "receiver": self.receiver_agent,
            "type": self.message_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "priority": self.priority,
        }


@dataclass
class Agent:
    """Represents a registered agent."""
    agent_id: str
    name: str = ""
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    handler: Optional[Callable] = None
    online: bool = True
    last_heartbeat: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "online": self.online,
        }


class AgentSendManager:
    """
    Manages inter-agent communication.
    """
    
    def __init__(self):
        self._agents: dict[str, Agent] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._pending_responses: dict[str, asyncio.Future] = {}
        self._message_handlers: dict[str, list[Callable]] = {}
        self._running: bool = False
        self._stats = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
        }
    
    # ============================================
    # Agent Registration
    # ============================================
    
    def register_agent(
        self,
        agent_id: str,
        name: str = "",
        description: str = "",
        capabilities: list[str] = None,
        handler: Callable = None,
    ) -> Agent:
        """
        Register a new agent.
        
        Args:
            agent_id: Unique agent identifier
            name: Human-readable name
            description: Agent description
            capabilities: List of capabilities
            handler: Message handler function
        
        Returns:
            Registered Agent
        """
        agent = Agent(
            agent_id=agent_id,
            name=name or agent_id,
            description=description,
            capabilities=capabilities or [],
            handler=handler,
        )
        self._agents[agent_id] = agent
        logger.info(f"Agent registered: {agent_id}")
        return agent
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")
            return True
        return False
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)
    
    def list_agents(self, online_only: bool = False) -> list[Agent]:
        """List all registered agents."""
        agents = list(self._agents.values())
        if online_only:
            agents = [a for a in agents if a.online]
        return agents
    
    def find_agents_by_capability(self, capability: str) -> list[Agent]:
        """Find agents with a specific capability."""
        return [
            agent for agent in self._agents.values()
            if capability in agent.capabilities and agent.online
        ]
    
    # ============================================
    # Messaging
    # ============================================
    
    async def send(
        self,
        sender: str,
        receiver: str,
        message_type: AgentMessageType,
        payload: Any,
        **kwargs,
    ) -> str:
        """
        Send a message to another agent.
        
        Args:
            sender: Sender agent ID
            receiver: Receiver agent ID
            message_type: Type of message
            payload: Message payload
            **kwargs: Additional message options
        
        Returns:
            Message ID
        """
        import uuid
        
        message_id = str(uuid.uuid4())[:8]
        
        message = AgentMessage(
            id=message_id,
            sender_agent=sender,
            receiver_agent=receiver,
            message_type=message_type,
            payload=payload,
            correlation_id=kwargs.get("correlation_id"),
            priority=kwargs.get("priority", 0),
            ttl_seconds=kwargs.get("ttl_seconds", 300),
            requires_ack=kwargs.get("requires_ack", False),
        )
        
        await self._deliver(message)
        self._stats["messages_sent"] += 1
        
        return message_id
    
    async def send_task(
        self,
        sender: str,
        receiver: str,
        task: dict,
        **kwargs,
    ) -> str:
        """Send a task to another agent."""
        return await self.send(sender, receiver, AgentMessageType.TASK, task, **kwargs)
    
    async def send_result(
        self,
        sender: str,
        receiver: str,
        result: Any,
        correlation_id: str = None,
        **kwargs,
    ) -> str:
        """Send a result back to an agent."""
        return await self.send(
            sender, receiver, AgentMessageType.RESULT, result,
            correlation_id=correlation_id, **kwargs
        )
    
    async def request(
        self,
        sender: str,
        receiver: str,
        payload: Any,
        timeout: float = 30.0,
    ) -> Any:
        """
        Send a request and wait for response.
        
        Args:
            sender: Sender agent ID
            receiver: Receiver agent ID
            payload: Request payload
            timeout: Response timeout in seconds
        
        Returns:
            Response payload
        """
        import uuid
        
        correlation_id = str(uuid.uuid4())[:8]
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending_responses[correlation_id] = future
        
        try:
            # Send request
            await self.send(
                sender, receiver, AgentMessageType.REQUEST, payload,
                correlation_id=correlation_id,
            )
            
            # Wait for response
            return await asyncio.wait_for(future, timeout)
            
        except asyncio.TimeoutError:
            raise TimeoutError(f"No response from {receiver} within {timeout}s")
        finally:
            self._pending_responses.pop(correlation_id, None)
    
    async def broadcast(
        self,
        sender: str,
        payload: Any,
        exclude: list[str] = None,
    ) -> int:
        """
        Broadcast a message to all agents.
        
        Args:
            sender: Sender agent ID
            payload: Broadcast payload
            exclude: Agent IDs to exclude
        
        Returns:
            Number of agents notified
        """
        exclude = exclude or []
        count = 0
        
        for agent_id in self._agents.keys():
            if agent_id != sender and agent_id not in exclude:
                await self.send(sender, agent_id, AgentMessageType.BROADCAST, payload)
                count += 1
        
        return count
    
    # ============================================
    # Message Delivery
    # ============================================
    
    async def _deliver(self, message: AgentMessage) -> bool:
        """Deliver a message to the receiver."""
        receiver = self._agents.get(message.receiver_agent)
        
        if not receiver:
            logger.warning(f"Agent not found: {message.receiver_agent}")
            self._stats["messages_failed"] += 1
            return False
        
        if not receiver.online:
            logger.warning(f"Agent offline: {message.receiver_agent}")
            self._stats["messages_failed"] += 1
            return False
        
        try:
            # Handle response messages
            if message.message_type == AgentMessageType.RESPONSE:
                if message.correlation_id in self._pending_responses:
                    self._pending_responses[message.correlation_id].set_result(message.payload)
                    self._stats["messages_delivered"] += 1
                    return True
            
            # Call agent handler
            if receiver.handler:
                if asyncio.iscoroutinefunction(receiver.handler):
                    await receiver.handler(message)
                else:
                    receiver.handler(message)
            
            # Call registered handlers
            for handler in self._message_handlers.get(message.receiver_agent, []):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    logger.error(f"Handler error: {e}")
            
            self._stats["messages_delivered"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Delivery error: {e}")
            self._stats["messages_failed"] += 1
            return False
    
    # ============================================
    # Handlers
    # ============================================
    
    def on_message(self, agent_id: str, handler: Callable) -> None:
        """Register a message handler for an agent."""
        if agent_id not in self._message_handlers:
            self._message_handlers[agent_id] = []
        self._message_handlers[agent_id].append(handler)
    
    def off_message(self, agent_id: str, handler: Callable = None) -> None:
        """Unregister message handlers."""
        if handler:
            if agent_id in self._message_handlers:
                self._message_handlers[agent_id] = [
                    h for h in self._message_handlers[agent_id] if h != handler
                ]
        else:
            self._message_handlers.pop(agent_id, None)
    
    # ============================================
    # Agent Status
    # ============================================
    
    def heartbeat(self, agent_id: str) -> None:
        """Update agent heartbeat."""
        agent = self._agents.get(agent_id)
        if agent:
            agent.last_heartbeat = datetime.now()
            agent.online = True
    
    def set_online(self, agent_id: str, online: bool = True) -> None:
        """Set agent online status."""
        agent = self._agents.get(agent_id)
        if agent:
            agent.online = online
    
    # ============================================
    # Statistics
    # ============================================
    
    def get_stats(self) -> dict:
        """Get messaging statistics."""
        return {
            **self._stats,
            "registered_agents": len(self._agents),
            "online_agents": len([a for a in self._agents.values() if a.online]),
            "pending_responses": len(self._pending_responses),
        }


# ============================================
# Global Instance
# ============================================

_agent_send_manager: Optional[AgentSendManager] = None


def get_agent_send_manager() -> AgentSendManager:
    """Get the global agent send manager instance."""
    global _agent_send_manager
    if _agent_send_manager is None:
        _agent_send_manager = AgentSendManager()
    return _agent_send_manager


__all__ = [
    "AgentMessageType",
    "AgentMessage",
    "Agent",
    "AgentSendManager",
    "get_agent_send_manager",
]
