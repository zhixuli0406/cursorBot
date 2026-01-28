"""
MCP (Model Context Protocol) Integration for CursorBot

Implements Anthropic's Model Context Protocol for connecting AI models
with external tools, resources, and data sources.

Reference: https://modelcontextprotocol.io/

Features:
- MCP Server discovery and connection
- Tool invocation via MCP
- Resource access (files, databases, APIs)
- Prompt templates from MCP servers
- Sampling requests handling

Usage:
    from src.core.mcp import get_mcp_manager, MCPConfig
    
    mcp = get_mcp_manager()
    
    # Connect to MCP server
    await mcp.connect_server("filesystem", "npx -y @anthropic/mcp-server-filesystem /path")
    
    # List available tools
    tools = await mcp.list_tools()
    
    # Call a tool
    result = await mcp.call_tool("read_file", {"path": "/path/to/file"})
    
    # List resources
    resources = await mcp.list_resources()
    
    # Read a resource
    content = await mcp.read_resource("file:///path/to/file")
"""

import asyncio
import json
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Union
from pathlib import Path

from ..utils.logger import logger


# ============================================
# MCP Protocol Types
# ============================================

class MCPMessageType(Enum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MCPMethod(Enum):
    """MCP standard methods."""
    # Lifecycle
    INITIALIZE = "initialize"
    INITIALIZED = "notifications/initialized"
    SHUTDOWN = "shutdown"
    
    # Tools
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    
    # Resources
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"
    
    # Prompts
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    
    # Sampling (server -> client)
    SAMPLING_CREATE = "sampling/createMessage"
    
    # Logging
    LOGGING_SET_LEVEL = "logging/setLevel"


@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class MCPResource:
    """Represents an MCP resource."""
    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"
    
    def to_dict(self) -> dict:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class MCPPrompt:
    """Represents an MCP prompt template."""
    name: str
    description: str = ""
    arguments: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
        }


@dataclass
class MCPServerInfo:
    """Information about an MCP server."""
    name: str
    version: str
    capabilities: dict = field(default_factory=dict)


@dataclass
class MCPConfig:
    """Configuration for MCP manager."""
    # Server discovery
    config_path: str = "~/.cursor/mcp.json"
    
    # Connection settings
    connection_timeout: int = 30
    request_timeout: int = 60
    
    # Auto-connect on startup
    auto_connect: bool = True
    
    # Logging
    log_messages: bool = False


# ============================================
# MCP Transport Layer
# ============================================

class MCPTransport(ABC):
    """Base class for MCP transport implementations."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""
        pass
    
    @abstractmethod
    async def send(self, message: dict) -> None:
        """Send a message."""
        pass
    
    @abstractmethod
    async def receive(self) -> dict:
        """Receive a message."""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        pass


class StdioTransport(MCPTransport):
    """
    Stdio-based MCP transport.
    Communicates with MCP server via stdin/stdout.
    """
    
    def __init__(self, command: str, args: list[str] = None, env: dict = None):
        self.command = command
        self.args = args or []
        self.env = env
        self._process: Optional[asyncio.subprocess.Process] = None
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
    
    @property
    def is_connected(self) -> bool:
        return self._process is not None and self._process.returncode is None
    
    async def connect(self) -> None:
        """Start the MCP server process."""
        # Prepare environment
        process_env = os.environ.copy()
        if self.env:
            process_env.update(self.env)
        
        # Parse command
        if " " in self.command and not self.args:
            # Command with arguments as string
            parts = self.command.split()
            cmd = parts[0]
            args = parts[1:] + self.args
        else:
            cmd = self.command
            args = self.args
        
        try:
            self._process = await asyncio.create_subprocess_exec(
                cmd,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
            )
            logger.info(f"MCP server process started: {cmd}")
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Stop the MCP server process."""
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
            finally:
                self._process = None
                logger.info("MCP server process stopped")
    
    async def send(self, message: dict) -> None:
        """Send a JSON-RPC message via stdin."""
        if not self.is_connected:
            raise ConnectionError("Not connected to MCP server")
        
        async with self._write_lock:
            # JSON-RPC over stdio uses newline-delimited JSON
            data = json.dumps(message) + "\n"
            self._process.stdin.write(data.encode())
            await self._process.stdin.drain()
    
    async def receive(self) -> dict:
        """Receive a JSON-RPC message from stdout."""
        if not self.is_connected:
            raise ConnectionError("Not connected to MCP server")
        
        async with self._read_lock:
            line = await self._process.stdout.readline()
            if not line:
                raise ConnectionError("MCP server closed connection")
            
            return json.loads(line.decode())


class SSETransport(MCPTransport):
    """
    Server-Sent Events (SSE) based MCP transport.
    For HTTP-based MCP servers.
    """
    
    def __init__(self, url: str, headers: dict = None):
        self.url = url
        self.headers = headers or {}
        self._client = None
        self._connected = False
        self._message_queue: asyncio.Queue = asyncio.Queue()
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def connect(self) -> None:
        """Connect to SSE endpoint."""
        import httpx
        
        self._client = httpx.AsyncClient(timeout=None)
        self._connected = True
        logger.info(f"Connected to MCP SSE server: {self.url}")
    
    async def disconnect(self) -> None:
        """Disconnect from SSE endpoint."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
    
    async def send(self, message: dict) -> None:
        """Send message via HTTP POST."""
        if not self._client:
            raise ConnectionError("Not connected")
        
        response = await self._client.post(
            self.url,
            json=message,
            headers=self.headers,
        )
        response.raise_for_status()
    
    async def receive(self) -> dict:
        """Receive message from SSE stream."""
        return await self._message_queue.get()


# ============================================
# MCP Client
# ============================================

class MCPClient:
    """
    MCP client for communicating with a single MCP server.
    Handles JSON-RPC protocol and message routing.
    """
    
    def __init__(self, name: str, transport: MCPTransport):
        self.name = name
        self.transport = transport
        self.server_info: Optional[MCPServerInfo] = None
        
        # Request tracking
        self._request_id = 0
        self._pending_requests: dict[int, asyncio.Future] = {}
        
        # Capabilities cache
        self._tools: list[MCPTool] = []
        self._resources: list[MCPResource] = []
        self._prompts: list[MCPPrompt] = []
        
        # Message handler task
        self._handler_task: Optional[asyncio.Task] = None
        
        # Notification handlers
        self._notification_handlers: dict[str, Callable] = {}
    
    @property
    def is_connected(self) -> bool:
        return self.transport.is_connected
    
    async def connect(self) -> MCPServerInfo:
        """Connect to MCP server and perform initialization."""
        await self.transport.connect()
        
        # Start message handler
        self._handler_task = asyncio.create_task(self._handle_messages())
        
        # Send initialize request
        result = await self._request(MCPMethod.INITIALIZE.value, {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
            },
            "clientInfo": {
                "name": "CursorBot",
                "version": "0.4.0",
            },
        })
        
        self.server_info = MCPServerInfo(
            name=result.get("serverInfo", {}).get("name", "unknown"),
            version=result.get("serverInfo", {}).get("version", "unknown"),
            capabilities=result.get("capabilities", {}),
        )
        
        # Send initialized notification
        await self._notify(MCPMethod.INITIALIZED.value, {})
        
        logger.info(f"MCP client '{self.name}' connected to {self.server_info.name}")
        return self.server_info
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self._handler_task:
            self._handler_task.cancel()
            try:
                await self._handler_task
            except asyncio.CancelledError:
                pass
        
        # Send shutdown if connected
        if self.is_connected:
            try:
                await self._request(MCPMethod.SHUTDOWN.value, {}, timeout=5.0)
            except Exception:
                pass
        
        await self.transport.disconnect()
        logger.info(f"MCP client '{self.name}' disconnected")
    
    async def _handle_messages(self) -> None:
        """Background task to handle incoming messages."""
        while self.is_connected:
            try:
                message = await self.transport.receive()
                await self._process_message(message)
            except ConnectionError:
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error handling MCP message: {e}")
    
    async def _process_message(self, message: dict) -> None:
        """Process an incoming JSON-RPC message."""
        # Check if it's a response
        if "id" in message and "result" in message or "error" in message:
            request_id = message["id"]
            if request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                if "error" in message:
                    future.set_exception(Exception(message["error"].get("message", "Unknown error")))
                else:
                    future.set_result(message.get("result"))
        
        # Check if it's a notification
        elif "method" in message and "id" not in message:
            method = message["method"]
            params = message.get("params", {})
            
            if method in self._notification_handlers:
                try:
                    await self._notification_handlers[method](params)
                except Exception as e:
                    logger.error(f"Notification handler error: {e}")
        
        # Check if it's a request from server (e.g., sampling)
        elif "method" in message and "id" in message:
            await self._handle_server_request(message)
    
    async def _handle_server_request(self, message: dict) -> None:
        """Handle requests from MCP server (e.g., sampling)."""
        method = message["method"]
        request_id = message["id"]
        params = message.get("params", {})
        
        if method == MCPMethod.SAMPLING_CREATE.value:
            # Handle sampling request - this requires LLM integration
            # For now, return an error
            await self._send_response(request_id, error={
                "code": -32601,
                "message": "Sampling not implemented",
            })
        else:
            await self._send_response(request_id, error={
                "code": -32601,
                "message": f"Method not found: {method}",
            })
    
    async def _request(self, method: str, params: dict, timeout: float = 60.0) -> Any:
        """Send a JSON-RPC request and wait for response."""
        self._request_id += 1
        request_id = self._request_id
        
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future
        
        try:
            await self.transport.send(message)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"MCP request timeout: {method}")
    
    async def _notify(self, method: str, params: dict) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        await self.transport.send(message)
    
    async def _send_response(self, request_id: int, result: Any = None, error: dict = None) -> None:
        """Send a JSON-RPC response."""
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
        }
        
        if error:
            message["error"] = error
        else:
            message["result"] = result
        
        await self.transport.send(message)
    
    # ============================================
    # MCP Methods
    # ============================================
    
    async def list_tools(self) -> list[MCPTool]:
        """List available tools from the server."""
        if not self.server_info or "tools" not in self.server_info.capabilities:
            return []
        
        result = await self._request(MCPMethod.TOOLS_LIST.value, {})
        self._tools = [
            MCPTool(
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in result.get("tools", [])
        ]
        return self._tools
    
    async def call_tool(self, name: str, arguments: dict = None) -> Any:
        """Call a tool on the server."""
        result = await self._request(MCPMethod.TOOLS_CALL.value, {
            "name": name,
            "arguments": arguments or {},
        })
        return result
    
    async def list_resources(self) -> list[MCPResource]:
        """List available resources from the server."""
        if not self.server_info or "resources" not in self.server_info.capabilities:
            return []
        
        result = await self._request(MCPMethod.RESOURCES_LIST.value, {})
        self._resources = [
            MCPResource(
                uri=r["uri"],
                name=r["name"],
                description=r.get("description", ""),
                mime_type=r.get("mimeType", "text/plain"),
            )
            for r in result.get("resources", [])
        ]
        return self._resources
    
    async def read_resource(self, uri: str) -> dict:
        """Read a resource from the server."""
        result = await self._request(MCPMethod.RESOURCES_READ.value, {
            "uri": uri,
        })
        return result
    
    async def list_prompts(self) -> list[MCPPrompt]:
        """List available prompt templates from the server."""
        if not self.server_info or "prompts" not in self.server_info.capabilities:
            return []
        
        result = await self._request(MCPMethod.PROMPTS_LIST.value, {})
        self._prompts = [
            MCPPrompt(
                name=p["name"],
                description=p.get("description", ""),
                arguments=p.get("arguments", []),
            )
            for p in result.get("prompts", [])
        ]
        return self._prompts
    
    async def get_prompt(self, name: str, arguments: dict = None) -> dict:
        """Get a prompt template with arguments filled in."""
        result = await self._request(MCPMethod.PROMPTS_GET.value, {
            "name": name,
            "arguments": arguments or {},
        })
        return result
    
    def on_notification(self, method: str, handler: Callable) -> None:
        """Register a notification handler."""
        self._notification_handlers[method] = handler


# ============================================
# MCP Manager
# ============================================

class MCPManager:
    """
    Manages multiple MCP server connections.
    Provides a unified interface for tool/resource access.
    """
    
    def __init__(self, config: MCPConfig = None):
        self.config = config or MCPConfig()
        self._clients: dict[str, MCPClient] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize MCP manager and auto-connect to configured servers."""
        if self._initialized:
            return
        
        # Load server configurations
        config_path = Path(self.config.config_path).expanduser()
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config_data = json.load(f)
                
                servers = config_data.get("mcpServers", {})
                for name, server_config in servers.items():
                    if self.config.auto_connect:
                        try:
                            await self.connect_server(
                                name=name,
                                command=server_config.get("command"),
                                args=server_config.get("args", []),
                                env=server_config.get("env"),
                            )
                        except Exception as e:
                            logger.warning(f"Failed to auto-connect MCP server '{name}': {e}")
                
            except Exception as e:
                logger.warning(f"Failed to load MCP config from {config_path}: {e}")
        
        self._initialized = True
        logger.info(f"MCP manager initialized with {len(self._clients)} servers")
    
    async def connect_server(
        self,
        name: str,
        command: str = None,
        args: list[str] = None,
        env: dict = None,
        url: str = None,
    ) -> MCPServerInfo:
        """
        Connect to an MCP server.
        
        Args:
            name: Unique name for this server connection
            command: Command to start stdio-based server
            args: Command arguments
            env: Environment variables
            url: URL for SSE-based server
            
        Returns:
            Server information
        """
        if name in self._clients:
            raise ValueError(f"MCP server '{name}' already connected")
        
        # Create transport
        if command:
            transport = StdioTransport(command, args, env)
        elif url:
            transport = SSETransport(url)
        else:
            raise ValueError("Either 'command' or 'url' must be provided")
        
        # Create and connect client
        client = MCPClient(name, transport)
        server_info = await client.connect()
        
        self._clients[name] = client
        return server_info
    
    async def disconnect_server(self, name: str) -> None:
        """Disconnect from an MCP server."""
        if name not in self._clients:
            raise ValueError(f"MCP server '{name}' not found")
        
        client = self._clients.pop(name)
        await client.disconnect()
    
    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for name in list(self._clients.keys()):
            await self.disconnect_server(name)
    
    def get_client(self, name: str) -> Optional[MCPClient]:
        """Get a specific MCP client."""
        return self._clients.get(name)
    
    def list_servers(self) -> list[str]:
        """List connected server names."""
        return list(self._clients.keys())
    
    # ============================================
    # Unified Tool/Resource Access
    # ============================================
    
    async def list_all_tools(self) -> dict[str, list[MCPTool]]:
        """List tools from all connected servers."""
        result = {}
        for name, client in self._clients.items():
            try:
                tools = await client.list_tools()
                result[name] = tools
            except Exception as e:
                logger.warning(f"Failed to list tools from '{name}': {e}")
                result[name] = []
        return result
    
    async def call_tool(self, server: str, tool_name: str, arguments: dict = None) -> Any:
        """Call a tool on a specific server."""
        client = self._clients.get(server)
        if not client:
            raise ValueError(f"MCP server '{server}' not found")
        
        return await client.call_tool(tool_name, arguments)
    
    async def list_all_resources(self) -> dict[str, list[MCPResource]]:
        """List resources from all connected servers."""
        result = {}
        for name, client in self._clients.items():
            try:
                resources = await client.list_resources()
                result[name] = resources
            except Exception as e:
                logger.warning(f"Failed to list resources from '{name}': {e}")
                result[name] = []
        return result
    
    async def read_resource(self, server: str, uri: str) -> dict:
        """Read a resource from a specific server."""
        client = self._clients.get(server)
        if not client:
            raise ValueError(f"MCP server '{server}' not found")
        
        return await client.read_resource(uri)
    
    async def list_all_prompts(self) -> dict[str, list[MCPPrompt]]:
        """List prompts from all connected servers."""
        result = {}
        for name, client in self._clients.items():
            try:
                prompts = await client.list_prompts()
                result[name] = prompts
            except Exception as e:
                logger.warning(f"Failed to list prompts from '{name}': {e}")
                result[name] = []
        return result
    
    async def get_prompt(self, server: str, name: str, arguments: dict = None) -> dict:
        """Get a prompt from a specific server."""
        client = self._clients.get(server)
        if not client:
            raise ValueError(f"MCP server '{server}' not found")
        
        return await client.get_prompt(name, arguments)
    
    def get_tools_for_llm(self) -> list[dict]:
        """
        Get all tools in a format suitable for LLM function calling.
        Returns tools in OpenAI/Anthropic compatible format.
        """
        tools = []
        for server_name, client in self._clients.items():
            for tool in client._tools:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": f"{server_name}__{tool.name}",
                        "description": f"[{server_name}] {tool.description}",
                        "parameters": tool.input_schema,
                    },
                })
        return tools
    
    async def execute_tool_call(self, tool_name: str, arguments: dict) -> Any:
        """
        Execute a tool call from LLM response.
        Tool name format: server__tool_name
        """
        if "__" not in tool_name:
            raise ValueError(f"Invalid tool name format: {tool_name}")
        
        server, name = tool_name.split("__", 1)
        return await self.call_tool(server, name, arguments)
    
    def get_stats(self) -> dict:
        """Get MCP manager statistics."""
        stats = {
            "connected_servers": len(self._clients),
            "servers": {},
        }
        
        for name, client in self._clients.items():
            stats["servers"][name] = {
                "connected": client.is_connected,
                "server_info": {
                    "name": client.server_info.name if client.server_info else None,
                    "version": client.server_info.version if client.server_info else None,
                } if client.server_info else None,
                "tools_count": len(client._tools),
                "resources_count": len(client._resources),
                "prompts_count": len(client._prompts),
            }
        
        return stats


# ============================================
# Built-in MCP Servers
# ============================================

class BuiltInMCPServers:
    """
    Factory for common MCP server configurations.
    """
    
    @staticmethod
    def filesystem(paths: list[str]) -> dict:
        """Filesystem access server."""
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"] + paths,
        }
    
    @staticmethod
    def github(token: str = None) -> dict:
        """GitHub integration server."""
        env = {}
        if token:
            env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": env,
        }
    
    @staticmethod
    def postgres(connection_string: str) -> dict:
        """PostgreSQL database server."""
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres", connection_string],
        }
    
    @staticmethod
    def sqlite(db_path: str) -> dict:
        """SQLite database server."""
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sqlite", db_path],
        }
    
    @staticmethod
    def brave_search(api_key: str) -> dict:
        """Brave search server."""
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": api_key},
        }
    
    @staticmethod
    def puppeteer() -> dict:
        """Puppeteer browser automation server."""
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        }
    
    @staticmethod
    def memory() -> dict:
        """Knowledge graph memory server."""
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
        }


# ============================================
# Global Instance
# ============================================

_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager(config: MCPConfig = None) -> MCPManager:
    """Get the global MCP manager instance."""
    global _mcp_manager
    
    if _mcp_manager is None:
        _mcp_manager = MCPManager(config)
    
    return _mcp_manager


async def initialize_mcp() -> MCPManager:
    """Initialize and return the MCP manager."""
    manager = get_mcp_manager()
    await manager.initialize()
    return manager


def reset_mcp_manager() -> None:
    """Reset the MCP manager instance."""
    global _mcp_manager
    if _mcp_manager:
        asyncio.create_task(_mcp_manager.disconnect_all())
    _mcp_manager = None


__all__ = [
    # Types
    "MCPMessageType",
    "MCPMethod",
    "MCPTool",
    "MCPResource",
    "MCPPrompt",
    "MCPServerInfo",
    "MCPConfig",
    # Transport
    "MCPTransport",
    "StdioTransport",
    "SSETransport",
    # Client
    "MCPClient",
    # Manager
    "MCPManager",
    "get_mcp_manager",
    "initialize_mcp",
    "reset_mcp_manager",
    # Built-in servers
    "BuiltInMCPServers",
]
