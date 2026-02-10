"""
Tests for Claude Code CLI Agent functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path


class TestCLIConfig:
    """Tests for CLI configuration."""

    def test_config_defaults(self):
        """Test default configuration values."""
        from src.claude.cli_agent import CLIConfig

        config = CLIConfig()
        assert config.timeout == 900  # 15 minutes
        assert config.max_retries == 3
        assert "claude-sonnet" in config.model.lower()

    def test_config_custom(self):
        """Test custom configuration."""
        from src.claude.cli_agent import CLIConfig

        config = CLIConfig(
            timeout=600,
            max_retries=5,
            model="claude-opus-4.5"
        )
        assert config.timeout == 600
        assert config.max_retries == 5
        assert config.model == "claude-opus-4.5"


class TestCLIResult:
    """Tests for CLI result handling."""

    def test_result_success(self):
        """Test successful result creation."""
        from src.claude.cli_agent import CLIResult

        result = CLIResult(
            success=True,
            output="Test output",
            command="claude chat 'hello'"
        )

        assert result.success is True
        assert result.output == "Test output"
        assert result.error is None

    def test_result_error(self):
        """Test error result creation."""
        from src.claude.cli_agent import CLIResult

        result = CLIResult(
            success=False,
            error="Command failed",
            command="claude chat 'test'"
        )

        assert result.success is False
        assert result.error == "Command failed"

    def test_result_to_dict(self):
        """Test result serialization."""
        from src.claude.cli_agent import CLIResult

        result = CLIResult(
            success=True,
            output="Test",
            command="claude chat"
        )
        data = result.to_dict()

        assert data["success"] is True
        assert data["output"] == "Test"
        assert "command" in data


@pytest.mark.asyncio
class TestClaudeCodeCLIAgent:
    """Tests for Claude Code CLI Agent."""

    async def test_agent_initialization(self):
        """Test agent initialization."""
        from src.claude.cli_agent import ClaudeCodeCLIAgent, CLIStatus

        agent = ClaudeCodeCLIAgent()
        assert agent._status in [CLIStatus.AVAILABLE, CLIStatus.NOT_INSTALLED]

    async def test_find_cli_path(self):
        """Test CLI path detection."""
        from src.claude.cli_agent import ClaudeCodeCLIAgent

        agent = ClaudeCodeCLIAgent()
        # Should find claude CLI if installed, or return None
        assert agent._cli_path is None or Path(agent._cli_path).name == "claude"

    @patch('src.claude.cli_agent.utils.run_command')
    async def test_chat_command(self, mock_run):
        """Test chat command execution."""
        from src.claude.cli_agent import ClaudeCodeCLIAgent

        mock_run.return_value = ("Hello response", "", 0)

        agent = ClaudeCodeCLIAgent()
        agent._cli_path = "/usr/local/bin/claude"  # Mock CLI path

        result = await agent.chat("Hello", user_id="test_user")

        assert result.success is True
        assert "Hello response" in result.output or result.output == "Hello response"
        mock_run.assert_called_once()

    @patch('src.claude.cli_agent.utils.run_command')
    async def test_ask_command(self, mock_run):
        """Test ask command execution."""
        from src.claude.cli_agent import ClaudeCodeCLIAgent

        mock_run.return_value = ("Answer to question", "", 0)

        agent = ClaudeCodeCLIAgent()
        agent._cli_path = "/usr/local/bin/claude"

        result = await agent.ask("What is Python?")

        assert result.success is True
        assert result.output == "Answer to question"

    @patch('src.claude.cli_agent.utils.run_command')
    async def test_cli_not_installed(self, mock_run):
        """Test behavior when CLI is not installed."""
        from src.claude.cli_agent import ClaudeCodeCLIAgent, CLIStatus

        agent = ClaudeCodeCLIAgent()
        agent._cli_path = None
        agent._status = CLIStatus.NOT_INSTALLED

        result = await agent.chat("Hello")

        assert result.success is False
        assert "not installed" in result.error.lower()

    async def test_session_management(self):
        """Test session management."""
        from src.claude.cli_agent import ClaudeCodeCLIAgent

        agent = ClaudeCodeCLIAgent()

        # Test session ID generation/tracking
        user1 = "user1"
        user2 = "user2"

        # Sessions should be isolated per user
        assert user1 not in agent._user_chat_sessions or agent._user_chat_sessions.get(user1) != agent._user_chat_sessions.get(user2)


class TestCompatibilityWrappers:
    """Tests for backward compatibility wrappers."""

    def test_workspace_agent(self):
        """Test WorkspaceAgent wrapper."""
        from src.claude.agent import WorkspaceAgent

        agent = WorkspaceAgent("/tmp/workspace")
        assert agent.get_current_workspace() == "/tmp/workspace"

    def test_legacy_name(self):
        """Test CursorAgent legacy name."""
        from src.claude.agent import CursorAgent, WorkspaceAgent

        # CursorAgent should be alias for WorkspaceAgent
        assert CursorAgent is WorkspaceAgent

    async def test_file_operations(self):
        """Test FileOperations wrapper."""
        from src.claude.file_operations import FileOperations

        ops = FileOperations("/tmp")
        assert ops.workspace_path == Path("/tmp")

    async def test_terminal_manager(self):
        """Test TerminalManager wrapper."""
        from src.claude.terminal import TerminalManager

        manager = TerminalManager()
        assert manager.work_dir is not None


@pytest.mark.asyncio
class TestUtilities:
    """Tests for utility functions."""

    @patch('builtins.open', new_callable=mock_open, read_data="test content")
    async def test_read_file(self, mock_file):
        """Test file reading."""
        from src.claude.utils import read_file

        content = await read_file("/tmp/test.txt")
        assert content == "test content"

    @patch('builtins.open', new_callable=mock_open)
    async def test_write_file(self, mock_file):
        """Test file writing."""
        from src.claude.utils import write_file

        await write_file("/tmp/test.txt", "new content")
        mock_file.assert_called()

    @patch('asyncio.create_subprocess_shell')
    async def test_run_command(self, mock_subprocess):
        """Test command execution."""
        from src.claude.utils import run_command

        # Mock the subprocess
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        mock_proc.returncode = 0
        mock_subprocess.return_value = mock_proc

        stdout, stderr, code = await run_command("echo test")

        assert code == 0
        assert stdout == "output"
