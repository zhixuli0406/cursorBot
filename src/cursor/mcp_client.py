"""
MCP (Model Context Protocol) client for Cursor communication
Handles low-level WebSocket communication with Cursor
"""

import asyncio
import json
from typing import Any, Optional
from uuid import uuid4

import websockets
from websockets.client import WebSocketClientProtocol

from ..utils.logger import logger


class MCPClient:
    """
    MCP Protocol client for communicating with Cursor Agent.
    Uses WebSocket for bidirectional communication.
    """

    def __init__(self, host: str = "localhost", port: int = 3000):
        """
        Initialize MCP client.

        Args:
            host: Server host address
            port: Server port number
        """
        self.host = host
        self.port = port
        self.ws: Optional[WebSocketClientProtocol] = None
        self._connected = False
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._receive_task: Optional[asyncio.Task] = None

    @property
    def uri(self) -> str:
        """Get WebSocket URI."""
        return f"ws://{self.host}:{self.port}"

    async def connect(self) -> bool:
        """
        Establish WebSocket connection.

        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to MCP server at {self.uri}")

            self.ws = await websockets.connect(
                self.uri,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10,
            )

            self._connected = True

            # Start message receiver task
            self._receive_task = asyncio.create_task(self._receive_messages())

            logger.info("MCP connection established")
            return True

        except Exception as e:
            logger.error(f"MCP connection failed: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._connected = False

        # Cancel receive task
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket
        if self.ws:
            await self.ws.close()
            self.ws = None

        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        logger.info("MCP connection closed")

    async def _receive_messages(self) -> None:
        """Background task to receive and route messages."""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message[:100]}")
        except websockets.ConnectionClosed:
            logger.info("MCP connection closed by server")
            self._connected = False
        except Exception as e:
            logger.error(f"Error in message receiver: {e}")
            self._connected = False

    async def _handle_message(self, data: dict) -> None:
        """
        Handle incoming message.

        Args:
            data: Parsed message data
        """
        request_id = data.get("id")

        if request_id and request_id in self._pending_requests:
            # Response to a pending request
            future = self._pending_requests.pop(request_id)
            if not future.done():
                if "error" in data:
                    future.set_exception(Exception(data["error"]))
                else:
                    future.set_result(data.get("result", data))
        else:
            # Unsolicited message (notification, etc.)
            logger.debug(f"Received notification: {data.get('type', 'unknown')}")

    async def send_message(
        self,
        message: dict[str, Any],
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        """
        Send a message and wait for response.

        Args:
            message: Message to send
            timeout: Response timeout in seconds

        Returns:
            Response data

        Raises:
            ConnectionError: If not connected
            TimeoutError: If response timeout
        """
        if not self._connected or not self.ws:
            raise ConnectionError("Not connected to MCP server")

        # Generate request ID
        request_id = str(uuid4())
        message["id"] = request_id

        # Create future for response
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[request_id] = future

        try:
            # Send message
            await self.ws.send(json.dumps(message))
            logger.debug(f"Sent message: {message.get('type', 'unknown')}")

            # Wait for response
            return await asyncio.wait_for(future, timeout=timeout)

        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"Request timeout after {timeout}s")
        except Exception as e:
            self._pending_requests.pop(request_id, None)
            raise

    async def ping(self) -> bool:
        """
        Send ping to verify connection.

        Returns:
            True if ping successful
        """
        try:
            response = await self.send_message({"type": "ping"}, timeout=5.0)
            return response.get("type") == "pong"
        except Exception:
            return False

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        message = {
            "type": "tool_call",
            "tool": tool_name,
            "arguments": arguments or {},
        }
        return await self.send_message(message)

    async def list_tools(self) -> list[dict]:
        """
        List available tools on the MCP server.

        Returns:
            List of available tools
        """
        response = await self.send_message({"type": "list_tools"})
        return response.get("tools", [])


class MockMCPClient(MCPClient):
    """
    Mock MCP client for testing without actual Cursor connection.
    Returns simulated responses.
    """

    async def connect(self) -> bool:
        """Simulate connection."""
        logger.info("MockMCPClient: Simulating connection")
        self._connected = True
        return True

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._connected = False
        logger.info("MockMCPClient: Disconnected")

    async def send_message(
        self,
        message: dict[str, Any],
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        """Return mock responses."""
        msg_type = message.get("type")

        if msg_type == "ping":
            return {"type": "pong"}

        if msg_type == "ask":
            return {
                "content": f"[Mock Response] 這是對「{message.get('content', '')}」的模擬回答。"
            }

        if msg_type == "chat":
            return {
                "content": f"[Mock Chat] 收到您的訊息：{message.get('content', '')}"
            }

        if msg_type == "code":
            return {
                "result": f"[Mock] 執行指令：{message.get('instruction', '')}\n// Generated code here"
            }

        if msg_type == "search":
            return {
                "results": [
                    {"file": "example.py", "line": 10, "content": "# Mock search result"},
                ]
            }

        return {"status": "ok"}

    async def ping(self) -> bool:
        """Always succeed."""
        return True


__all__ = ["MCPClient", "MockMCPClient"]
