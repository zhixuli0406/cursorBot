"""
Remote Gateway for CursorBot

Provides:
- Remote bot control via secure tunnel
- Gateway registration and discovery
- Secure message relay
- Multi-node deployment support
"""

import asyncio
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class GatewayStatus(Enum):
    """Gateway connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class GatewayNode:
    """Represents a gateway node."""
    node_id: str
    name: str = ""
    host: str = ""
    port: int = 8080
    status: GatewayStatus = GatewayStatus.DISCONNECTED
    last_heartbeat: datetime = field(default_factory=datetime.now)
    capabilities: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    def is_healthy(self, timeout_seconds: int = 60) -> bool:
        """Check if node is healthy."""
        if self.status != GatewayStatus.CONNECTED:
            return False
        return (datetime.now() - self.last_heartbeat).seconds < timeout_seconds
    
    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "capabilities": self.capabilities,
        }


@dataclass
class GatewayConfig:
    """Remote gateway configuration."""
    node_id: str = ""
    node_name: str = "CursorBot"
    
    # Server mode
    listen_host: str = "0.0.0.0"
    listen_port: int = 8765
    
    # Client mode
    remote_host: str = ""
    remote_port: int = 8765
    
    # Security
    secret_key: str = ""
    allowed_nodes: list[str] = field(default_factory=list)
    
    # Timeouts
    heartbeat_interval: int = 30
    connection_timeout: int = 60


class RemoteGateway:
    """
    Remote gateway for distributed bot deployment.
    """
    
    def __init__(self, config: GatewayConfig = None):
        self.config = config or GatewayConfig()
        
        # Generate node ID if not set
        if not self.config.node_id:
            self.config.node_id = secrets.token_hex(8)
        
        self._nodes: dict[str, GatewayNode] = {}
        self._server = None
        self._connections: dict[str, Any] = {}
        self._message_handlers: list[Callable] = []
        self._running = False
        self._heartbeat_task = None
    
    # ============================================
    # Server Mode
    # ============================================
    
    async def start_server(self) -> bool:
        """
        Start as gateway server.
        
        Returns:
            True if started successfully
        """
        try:
            import websockets
            
            self._server = await websockets.serve(
                self._handle_connection,
                self.config.listen_host,
                self.config.listen_port,
            )
            
            self._running = True
            self._start_heartbeat()
            
            logger.info(f"Gateway server started on {self.config.listen_host}:{self.config.listen_port}")
            return True
            
        except ImportError:
            logger.error("websockets not installed. Run: pip install websockets")
            return False
        except Exception as e:
            logger.error(f"Gateway server start error: {e}")
            return False
    
    async def _handle_connection(self, websocket, path):
        """Handle incoming WebSocket connection."""
        node_id = None
        
        try:
            # Authenticate
            auth_msg = await asyncio.wait_for(
                websocket.recv(),
                timeout=10,
            )
            
            import json
            auth_data = json.loads(auth_msg)
            
            if not self._verify_auth(auth_data):
                await websocket.close(4001, "Authentication failed")
                return
            
            node_id = auth_data.get("node_id")
            
            # Register node
            node = GatewayNode(
                node_id=node_id,
                name=auth_data.get("name", ""),
                host=websocket.remote_address[0],
                port=websocket.remote_address[1],
                status=GatewayStatus.CONNECTED,
                capabilities=auth_data.get("capabilities", []),
            )
            
            self._nodes[node_id] = node
            self._connections[node_id] = websocket
            
            logger.info(f"Node connected: {node_id}")
            
            # Send acknowledgment
            await websocket.send(json.dumps({
                "type": "connected",
                "node_id": self.config.node_id,
            }))
            
            # Message loop
            async for message in websocket:
                await self._process_message(node_id, message)
                
        except asyncio.TimeoutError:
            logger.warning("Connection authentication timeout")
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            if node_id:
                self._disconnect_node(node_id)
    
    # ============================================
    # Client Mode
    # ============================================
    
    async def connect_to_server(self) -> bool:
        """
        Connect to a remote gateway server.
        
        Returns:
            True if connected successfully
        """
        if not self.config.remote_host:
            logger.warning("No remote host configured")
            return False
        
        try:
            import websockets
            import json
            
            uri = f"ws://{self.config.remote_host}:{self.config.remote_port}"
            
            websocket = await websockets.connect(uri)
            
            # Authenticate
            auth_msg = json.dumps({
                "type": "auth",
                "node_id": self.config.node_id,
                "name": self.config.node_name,
                "secret": self._generate_auth_token(),
                "capabilities": ["chat", "agent"],
            })
            
            await websocket.send(auth_msg)
            
            # Wait for acknowledgment
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            response_data = json.loads(response)
            
            if response_data.get("type") != "connected":
                await websocket.close()
                return False
            
            # Store connection
            server_node_id = response_data.get("node_id")
            self._connections["server"] = websocket
            self._nodes["server"] = GatewayNode(
                node_id=server_node_id,
                host=self.config.remote_host,
                port=self.config.remote_port,
                status=GatewayStatus.CONNECTED,
            )
            
            self._running = True
            self._start_heartbeat()
            
            # Start receive loop
            asyncio.create_task(self._receive_loop(websocket))
            
            logger.info(f"Connected to gateway server at {uri}")
            return True
            
        except ImportError:
            logger.error("websockets not installed. Run: pip install websockets")
            return False
        except Exception as e:
            logger.error(f"Gateway connection error: {e}")
            return False
    
    async def _receive_loop(self, websocket):
        """Receive messages from server."""
        try:
            async for message in websocket:
                await self._process_message("server", message)
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
        finally:
            self._disconnect_node("server")
    
    # ============================================
    # Messaging
    # ============================================
    
    async def send_to_node(self, node_id: str, message: dict) -> bool:
        """
        Send message to a specific node.
        
        Args:
            node_id: Target node ID
            message: Message to send
        
        Returns:
            True if sent successfully
        """
        import json
        
        websocket = self._connections.get(node_id)
        if not websocket:
            return False
        
        try:
            await websocket.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Send error to {node_id}: {e}")
            return False
    
    async def broadcast(self, message: dict, exclude: list[str] = None) -> int:
        """
        Broadcast message to all connected nodes.
        
        Args:
            message: Message to broadcast
            exclude: Node IDs to exclude
        
        Returns:
            Number of nodes reached
        """
        exclude = exclude or []
        count = 0
        
        for node_id in list(self._connections.keys()):
            if node_id not in exclude:
                if await self.send_to_node(node_id, message):
                    count += 1
        
        return count
    
    async def _process_message(self, sender_id: str, raw_message: str) -> None:
        """Process incoming message."""
        import json
        
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type")
            
            # Handle heartbeat
            if msg_type == "heartbeat":
                if sender_id in self._nodes:
                    self._nodes[sender_id].last_heartbeat = datetime.now()
                return
            
            # Call handlers
            for handler in self._message_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(sender_id, message)
                    else:
                        handler(sender_id, message)
                except Exception as e:
                    logger.error(f"Message handler error: {e}")
                    
        except json.JSONDecodeError:
            logger.warning(f"Invalid message from {sender_id}")
    
    # ============================================
    # Security
    # ============================================
    
    def _verify_auth(self, auth_data: dict) -> bool:
        """Verify authentication data."""
        node_id = auth_data.get("node_id")
        secret = auth_data.get("secret")
        
        # Check allowed nodes
        if self.config.allowed_nodes:
            if node_id not in self.config.allowed_nodes:
                return False
        
        # Verify secret
        if self.config.secret_key:
            expected = self._generate_auth_token(node_id)
            if secret != expected:
                return False
        
        return True
    
    def _generate_auth_token(self, node_id: str = None) -> str:
        """Generate authentication token."""
        node_id = node_id or self.config.node_id
        data = f"{node_id}:{self.config.secret_key}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    # ============================================
    # Heartbeat
    # ============================================
    
    def _start_heartbeat(self) -> None:
        """Start heartbeat task."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        while self._running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                
                heartbeat = {
                    "type": "heartbeat",
                    "node_id": self.config.node_id,
                    "timestamp": datetime.now().isoformat(),
                }
                
                await self.broadcast(heartbeat)
                
                # Check for stale connections
                await self._check_connections()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
    
    async def _check_connections(self) -> None:
        """Check for stale connections."""
        timeout = self.config.connection_timeout
        
        for node_id, node in list(self._nodes.items()):
            if not node.is_healthy(timeout):
                logger.warning(f"Node {node_id} heartbeat timeout")
                self._disconnect_node(node_id)
    
    def _disconnect_node(self, node_id: str) -> None:
        """Disconnect a node."""
        if node_id in self._nodes:
            self._nodes[node_id].status = GatewayStatus.DISCONNECTED
            del self._nodes[node_id]
        
        if node_id in self._connections:
            del self._connections[node_id]
        
        logger.info(f"Node disconnected: {node_id}")
    
    # ============================================
    # Handlers
    # ============================================
    
    def on_message(self, handler: Callable) -> None:
        """Register a message handler."""
        self._message_handlers.append(handler)
    
    # ============================================
    # Status
    # ============================================
    
    async def stop(self) -> None:
        """Stop the gateway."""
        self._running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        # Close all connections
        for websocket in self._connections.values():
            await websocket.close()
        
        self._connections.clear()
        self._nodes.clear()
        
        logger.info("Gateway stopped")
    
    def get_nodes(self) -> list[GatewayNode]:
        """Get all connected nodes."""
        return list(self._nodes.values())
    
    def get_stats(self) -> dict:
        """Get gateway statistics."""
        return {
            "node_id": self.config.node_id,
            "running": self._running,
            "connected_nodes": len(self._nodes),
            "is_server": self._server is not None,
            "nodes": [n.to_dict() for n in self._nodes.values()],
        }


# ============================================
# Global Instance
# ============================================

_remote_gateway: Optional[RemoteGateway] = None


def get_remote_gateway() -> RemoteGateway:
    """Get the global remote gateway instance."""
    global _remote_gateway
    if _remote_gateway is None:
        _remote_gateway = RemoteGateway()
    return _remote_gateway


__all__ = [
    "GatewayStatus",
    "GatewayNode",
    "GatewayConfig",
    "RemoteGateway",
    "get_remote_gateway",
]
