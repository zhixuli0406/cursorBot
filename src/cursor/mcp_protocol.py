"""
MCP (Model Context Protocol) implementation
Implements the official MCP protocol for Cursor communication
Based on MCP specification: JSON-RPC 2.0 over stdio/HTTP
"""

import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

from ..utils.logger import logger


class MCPMessageType(Enum):
    """MCP message types."""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPRequest:
    """MCP JSON-RPC request."""

    method: str
    params: Optional[dict[str, Any]] = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-RPC format."""
        data = {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": self.method,
        }
        if self.params:
            data["params"] = self.params
        return data

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class MCPResponse:
    """MCP JSON-RPC response."""

    id: str
    result: Optional[Any] = None
    error: Optional[dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "MCPResponse":
        """Parse from JSON-RPC format."""
        return cls(
            id=data.get("id", ""),
            result=data.get("result"),
            error=data.get("error"),
        )

    @property
    def is_error(self) -> bool:
        """Check if response is an error."""
        return self.error is not None


@dataclass
class MCPNotification:
    """MCP JSON-RPC notification (no response expected)."""

    method: str
    params: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-RPC format."""
        data = {
            "jsonrpc": "2.0",
            "method": self.method,
        }
        if self.params:
            data["params"] = self.params
        return data


class MCPError(Exception):
    """MCP protocol error."""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP Error {code}: {message}")


# Standard JSON-RPC error codes
class MCPErrorCode:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class StdioTransport:
    """
    Stdio transport layer for MCP protocol.
    Communicates with MCP server via stdin/stdout.
    """

    def __init__(self, command: list[str], env: Optional[dict] = None):
        """
        Initialize stdio transport.

        Args:
            command: Command to start MCP server
            env: Environment variables for the subprocess
        """
        self.command = command
        self.env = env or os.environ.copy()
        self.process: Optional[subprocess.Popen] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._notification_handlers: list[Callable] = []
        self._connected = False
        self._read_buffer = ""

    async def connect(self) -> bool:
        """
        Start MCP server process and establish connection.

        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Starting MCP server: {' '.join(self.command)}")

            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env,
                bufsize=0,
            )

            self._connected = True

            # Start reader task
            self._reader_task = asyncio.create_task(self._read_loop())

            # Initialize MCP connection
            await self._initialize()

            logger.info("MCP stdio transport connected")
            return True

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False

    async def _initialize(self) -> None:
        """Send MCP initialize request."""
        response = await self.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "prompts": {},
                    "resources": {},
                },
                "clientInfo": {
                    "name": "CursorBot",
                    "version": "0.1.0",
                },
            },
        )

        if response.is_error:
            raise MCPError(
                response.error.get("code", -1),
                response.error.get("message", "Initialize failed"),
            )

        # Send initialized notification
        await self.send_notification("notifications/initialized")
        logger.info(f"MCP initialized: {response.result}")

    async def disconnect(self) -> None:
        """Stop MCP server and close connection."""
        self._connected = False

        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        logger.info("MCP stdio transport disconnected")

    async def _read_loop(self) -> None:
        """Read messages from stdout."""
        try:
            loop = asyncio.get_event_loop()

            while self._connected and self.process:
                # Read line from stdout
                line = await loop.run_in_executor(
                    None,
                    self.process.stdout.readline,
                )

                if not line:
                    break

                try:
                    line_str = line.decode("utf-8").strip()
                    if not line_str:
                        continue

                    data = json.loads(line_str)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from MCP: {e}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"MCP reader error: {e}")
        finally:
            self._connected = False

    async def _handle_message(self, data: dict) -> None:
        """Handle incoming message."""
        # Check if it's a response
        if "id" in data and ("result" in data or "error" in data):
            request_id = data["id"]
            if request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                if not future.done():
                    future.set_result(MCPResponse.from_dict(data))
            return

        # Check if it's a notification
        if "method" in data and "id" not in data:
            for handler in self._notification_handlers:
                try:
                    await handler(data["method"], data.get("params"))
                except Exception as e:
                    logger.error(f"Notification handler error: {e}")

    async def send_request(
        self,
        method: str,
        params: Optional[dict] = None,
        timeout: float = 60.0,
    ) -> MCPResponse:
        """
        Send request and wait for response.

        Args:
            method: RPC method name
            params: Method parameters
            timeout: Response timeout

        Returns:
            MCPResponse object
        """
        if not self._connected or not self.process:
            raise ConnectionError("Not connected to MCP server")

        request = MCPRequest(method=method, params=params)
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[request.id] = future

        try:
            # Write to stdin
            message = request.to_json() + "\n"
            self.process.stdin.write(message.encode("utf-8"))
            self.process.stdin.flush()

            logger.debug(f"Sent MCP request: {method}")

            # Wait for response
            return await asyncio.wait_for(future, timeout=timeout)

        except asyncio.TimeoutError:
            self._pending_requests.pop(request.id, None)
            raise TimeoutError(f"MCP request timeout: {method}")

    async def send_notification(
        self,
        method: str,
        params: Optional[dict] = None,
    ) -> None:
        """Send notification (no response expected)."""
        if not self._connected or not self.process:
            raise ConnectionError("Not connected to MCP server")

        notification = MCPNotification(method=method, params=params)
        message = json.dumps(notification.to_dict()) + "\n"
        self.process.stdin.write(message.encode("utf-8"))
        self.process.stdin.flush()

    def add_notification_handler(self, handler: Callable) -> None:
        """Add handler for incoming notifications."""
        self._notification_handlers.append(handler)


class HTTPTransport:
    """
    HTTP/SSE transport layer for MCP protocol.
    Communicates with MCP server via HTTP endpoints.
    """

    def __init__(self, base_url: str):
        """
        Initialize HTTP transport.

        Args:
            base_url: Base URL of MCP server
        """
        self.base_url = base_url.rstrip("/")
        self._session = None
        self._connected = False
        self._pending_requests: dict[str, asyncio.Future] = {}

    async def connect(self) -> bool:
        """Establish HTTP connection."""
        try:
            import httpx

            self._session = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
            )

            # Test connection
            response = await self._session.get("/health")
            if response.status_code == 200:
                self._connected = True
                logger.info(f"MCP HTTP transport connected to {self.base_url}")
                return True

            return False

        except Exception as e:
            logger.error(f"HTTP transport connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Close HTTP connection."""
        if self._session:
            await self._session.aclose()
            self._session = None
        self._connected = False

    async def send_request(
        self,
        method: str,
        params: Optional[dict] = None,
        timeout: float = 60.0,
    ) -> MCPResponse:
        """Send JSON-RPC request via HTTP POST."""
        if not self._session:
            raise ConnectionError("Not connected")

        request = MCPRequest(method=method, params=params)

        response = await self._session.post(
            "/rpc",
            json=request.to_dict(),
            timeout=timeout,
        )

        data = response.json()
        return MCPResponse.from_dict(data)


class MCPProtocolClient:
    """
    High-level MCP protocol client.
    Provides convenient methods for MCP operations.
    """

    def __init__(self, transport: StdioTransport | HTTPTransport):
        """
        Initialize MCP client.

        Args:
            transport: Transport layer to use
        """
        self.transport = transport
        self._tools_cache: Optional[list[dict]] = None

    async def connect(self) -> bool:
        """Connect to MCP server."""
        return await self.transport.connect()

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        await self.transport.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self.transport._connected

    async def list_tools(self) -> list[dict]:
        """
        List available tools.

        Returns:
            List of tool definitions
        """
        if self._tools_cache:
            return self._tools_cache

        response = await self.transport.send_request("tools/list")

        if response.is_error:
            raise MCPError(
                response.error.get("code", -1),
                response.error.get("message", "Failed to list tools"),
            )

        self._tools_cache = response.result.get("tools", [])
        return self._tools_cache

    async def call_tool(
        self,
        name: str,
        arguments: Optional[dict] = None,
    ) -> Any:
        """
        Call a tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        response = await self.transport.send_request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments or {},
            },
        )

        if response.is_error:
            raise MCPError(
                response.error.get("code", -1),
                response.error.get("message", f"Tool call failed: {name}"),
                response.error.get("data"),
            )

        return response.result

    async def list_prompts(self) -> list[dict]:
        """List available prompts."""
        response = await self.transport.send_request("prompts/list")

        if response.is_error:
            return []

        return response.result.get("prompts", [])

    async def get_prompt(
        self,
        name: str,
        arguments: Optional[dict] = None,
    ) -> dict:
        """Get a prompt template."""
        response = await self.transport.send_request(
            "prompts/get",
            {
                "name": name,
                "arguments": arguments or {},
            },
        )

        if response.is_error:
            raise MCPError(
                response.error.get("code", -1),
                response.error.get("message", f"Failed to get prompt: {name}"),
            )

        return response.result

    async def list_resources(self) -> list[dict]:
        """List available resources."""
        response = await self.transport.send_request("resources/list")

        if response.is_error:
            return []

        return response.result.get("resources", [])

    async def read_resource(self, uri: str) -> dict:
        """Read a resource."""
        response = await self.transport.send_request(
            "resources/read",
            {"uri": uri},
        )

        if response.is_error:
            raise MCPError(
                response.error.get("code", -1),
                response.error.get("message", f"Failed to read resource: {uri}"),
            )

        return response.result

    async def ping(self) -> bool:
        """Ping the server."""
        try:
            response = await self.transport.send_request("ping", timeout=5.0)
            return not response.is_error
        except Exception:
            return False


__all__ = [
    "MCPRequest",
    "MCPResponse",
    "MCPNotification",
    "MCPError",
    "MCPErrorCode",
    "StdioTransport",
    "HTTPTransport",
    "MCPProtocolClient",
]
