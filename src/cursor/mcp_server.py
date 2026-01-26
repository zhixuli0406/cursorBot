"""
Simple MCP Server for bridging Telegram commands to local operations
This server can run independently and handle requests from CursorBot
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Optional

import websockets
from websockets.server import WebSocketServerProtocol

from ..utils.config import settings
from ..utils.logger import logger


class MCPServer:
    """
    Simple MCP-compatible WebSocket server.
    Handles requests from CursorBot and executes local operations.
    """

    def __init__(self, host: str = "localhost", port: int = 3000):
        self.host = host
        self.port = port
        self.workspace_path = Path(settings.cursor_workspace_path)
        self._clients: set[WebSocketServerProtocol] = set()

    async def handle_client(self, websocket: WebSocketServerProtocol) -> None:
        """Handle a client connection."""
        self._clients.add(websocket)
        client_info = f"{websocket.remote_address}"
        logger.info(f"MCP client connected: {client_info}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    response = await self.handle_message(data)
                    await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "error": "Invalid JSON"
                    }))
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    await websocket.send(json.dumps({
                        "id": data.get("id"),
                        "error": str(e)
                    }))

        except websockets.ConnectionClosed:
            logger.info(f"MCP client disconnected: {client_info}")
        finally:
            self._clients.discard(websocket)

    async def handle_message(self, data: dict) -> dict:
        """
        Handle incoming MCP message.

        Args:
            data: Parsed message data

        Returns:
            Response dictionary
        """
        msg_id = data.get("id")
        msg_type = data.get("type")

        logger.debug(f"Received message type: {msg_type}")

        if msg_type == "ping":
            return {"id": msg_id, "type": "pong"}

        if msg_type == "ask":
            return await self._handle_ask(msg_id, data)

        if msg_type == "chat":
            return await self._handle_chat(msg_id, data)

        if msg_type == "code":
            return await self._handle_code(msg_id, data)

        if msg_type == "search":
            return await self._handle_search(msg_id, data)

        return {
            "id": msg_id,
            "error": f"Unknown message type: {msg_type}"
        }

    async def _handle_ask(self, msg_id: str, data: dict) -> dict:
        """Handle ask message - forward to AI or return placeholder."""
        content = data.get("content", "")

        # In a real implementation, you would call an AI API here
        # For now, return a helpful placeholder
        response_content = (
            f"收到您的問題：「{content[:100]}」\n\n"
            "（此為本地 MCP Server 回應。如需 AI 功能，請整合 OpenAI/Claude API）"
        )

        return {
            "id": msg_id,
            "content": response_content
        }

    async def _handle_chat(self, msg_id: str, data: dict) -> dict:
        """Handle chat message."""
        content = data.get("content", "")

        return {
            "id": msg_id,
            "content": f"[MCP Server] 收到訊息：{content[:100]}"
        }

    async def _handle_code(self, msg_id: str, data: dict) -> dict:
        """Handle code instruction."""
        instruction = data.get("instruction", "")

        return {
            "id": msg_id,
            "result": (
                f"指令：{instruction[:100]}\n\n"
                "（程式碼生成功能需整合 AI API）"
            )
        }

    async def _handle_search(self, msg_id: str, data: dict) -> dict:
        """Handle search request - perform local grep."""
        query = data.get("query", "")

        if not query:
            return {"id": msg_id, "results": []}

        results = []

        try:
            # Use grep for searching
            process = await asyncio.create_subprocess_exec(
                "grep",
                "-rn",
                "--include=*.py",
                "--include=*.js",
                "--include=*.ts",
                "--include=*.tsx",
                "--include=*.jsx",
                query,
                str(self.workspace_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=10.0
            )

            for line in stdout.decode("utf-8", errors="replace").split("\n")[:20]:
                if not line:
                    continue

                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_path = parts[0]
                    try:
                        rel_path = Path(file_path).relative_to(self.workspace_path)
                    except ValueError:
                        rel_path = file_path

                    results.append({
                        "file": str(rel_path),
                        "line": int(parts[1]) if parts[1].isdigit() else 0,
                        "content": parts[2][:100] if len(parts) > 2 else ""
                    })

        except asyncio.TimeoutError:
            logger.warning("Search timed out")
        except Exception as e:
            logger.error(f"Search error: {e}")

        return {"id": msg_id, "results": results}

    async def start(self) -> None:
        """Start the MCP server."""
        logger.info(f"Starting MCP Server on ws://{self.host}:{self.port}")

        async with websockets.serve(
            self.handle_client,
            self.host,
            self.port,
        ):
            logger.info(f"MCP Server running at ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever

    async def stop(self) -> None:
        """Stop the server and disconnect all clients."""
        for client in self._clients:
            await client.close()
        self._clients.clear()


async def run_mcp_server():
    """Run the MCP server as standalone."""
    server = MCPServer(
        host="localhost",
        port=settings.cursor_mcp_port,
    )
    await server.start()


if __name__ == "__main__":
    asyncio.run(run_mcp_server())


__all__ = ["MCPServer", "run_mcp_server"]
