"""
Tests for Cursor Agent functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestCursorCommands:
    """Tests for Cursor command utilities."""

    def test_ask_command(self):
        """Test ask command creation."""
        from src.cursor.commands import ask, CommandType

        cmd = ask("What is Python?")
        assert cmd.type == CommandType.ASK
        assert cmd.content == "What is Python?"

    def test_chat_command(self):
        """Test chat command creation."""
        from src.cursor.commands import chat, CommandType

        cmd = chat("Hello!")
        assert cmd.type == CommandType.CHAT
        assert cmd.content == "Hello!"

    def test_code_command(self):
        """Test code command creation."""
        from src.cursor.commands import code, CommandType

        cmd = code("Create a function", "test.py")
        assert cmd.type == CommandType.CODE
        assert cmd.content == "Create a function"
        assert cmd.file_path == "test.py"

    def test_search_command(self):
        """Test search command creation."""
        from src.cursor.commands import search, CommandType

        cmd = search("def main", "src/")
        assert cmd.type == CommandType.SEARCH
        assert cmd.content == "def main"
        assert cmd.options["scope"] == "src/"

    def test_command_to_dict(self):
        """Test command serialization."""
        from src.cursor.commands import ask

        cmd = ask("test question")
        data = cmd.to_dict()

        assert data["type"] == "ask"
        assert data["content"] == "test question"


class TestCommandResult:
    """Tests for command result handling."""

    def test_from_response_success(self):
        """Test creating result from successful response."""
        from src.cursor.commands import CommandResult

        response = {"content": "Success!", "metadata": {"key": "value"}}
        result = CommandResult.from_response(response)

        assert result.success is True
        assert result.content == "Success!"
        assert result.error is None
        assert result.metadata == {"key": "value"}

    def test_from_response_error(self):
        """Test creating result from error response."""
        from src.cursor.commands import CommandResult

        response = {"error": "Something went wrong"}
        result = CommandResult.from_response(response)

        assert result.success is False
        assert result.error == "Something went wrong"


class TestCommandBuilder:
    """Tests for command builder."""

    def test_builder_chain(self):
        """Test builder method chaining."""
        from src.cursor.commands import CommandBuilder, CommandType

        cmd = (
            CommandBuilder(CommandType.EDIT)
            .content("Edit this")
            .file("test.py")
            .option("mode", "append")
            .build()
        )

        assert cmd.type == CommandType.EDIT
        assert cmd.content == "Edit this"
        assert cmd.file_path == "test.py"
        assert cmd.options["mode"] == "append"


@pytest.mark.asyncio
class TestMCPClient:
    """Tests for MCP client."""

    async def test_mock_client_connect(self):
        """Test mock client connection."""
        from src.cursor.mcp_client import MockMCPClient

        client = MockMCPClient()
        result = await client.connect()

        assert result is True
        assert client._connected is True

    async def test_mock_client_ping(self):
        """Test mock client ping."""
        from src.cursor.mcp_client import MockMCPClient

        client = MockMCPClient()
        await client.connect()

        result = await client.ping()
        assert result is True

    async def test_mock_client_ask(self):
        """Test mock client ask message."""
        from src.cursor.mcp_client import MockMCPClient

        client = MockMCPClient()
        await client.connect()

        response = await client.send_message({
            "type": "ask",
            "content": "What is 1+1?",
        })

        assert "content" in response
        assert "Mock Response" in response["content"]

    async def test_mock_client_disconnect(self):
        """Test mock client disconnection."""
        from src.cursor.mcp_client import MockMCPClient

        client = MockMCPClient()
        await client.connect()
        await client.disconnect()

        assert client._connected is False


@pytest.mark.asyncio
class TestCursorAgent:
    """Tests for Cursor Agent."""

    async def test_get_status_disconnected(self):
        """Test status when disconnected."""
        from src.cursor.agent import CursorAgent

        with patch("src.cursor.agent.settings") as mock_settings:
            mock_settings.cursor_workspace_path = "/tmp/test"
            mock_settings.cursor_mcp_port = 3000

            agent = CursorAgent()
            status = await agent.get_status()

            assert status["connected"] is False
            assert "workspace" in status

    async def test_list_projects(self):
        """Test project listing."""
        import tempfile
        from pathlib import Path
        from src.cursor.agent import CursorAgent

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test projects
            (Path(tmpdir) / "project1").mkdir()
            (Path(tmpdir) / "project2").mkdir()
            (Path(tmpdir) / ".hidden").mkdir()  # Should be excluded

            with patch("src.cursor.agent.settings") as mock_settings:
                mock_settings.cursor_workspace_path = tmpdir
                mock_settings.cursor_mcp_port = 3000

                agent = CursorAgent()
                result = await agent.list_projects()

                assert "project1" in result
                assert "project2" in result
                assert ".hidden" not in result
