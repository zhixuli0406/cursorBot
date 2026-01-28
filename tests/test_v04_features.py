"""
Tests for v0.4 Features

Tests cover:
- MCP (Model Context Protocol)
- Workflow Engine
- Analytics
- Code Review
- Conversation Export
- Auto-Documentation
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import tempfile
import os


# ============================================
# MCP Tests
# ============================================

class TestMCP:
    """Test MCP module."""
    
    def test_mcp_imports(self):
        """Test MCP module imports correctly."""
        from src.core.mcp import (
            MCPManager, MCPConfig, MCPTool, MCPResource,
            get_mcp_manager, reset_mcp_manager,
        )
        assert MCPManager is not None
        assert MCPConfig is not None
    
    def test_mcp_manager_creation(self):
        """Test MCP manager can be created."""
        from src.core.mcp import get_mcp_manager, reset_mcp_manager
        
        reset_mcp_manager()
        manager = get_mcp_manager()
        assert manager is not None
    
    def test_mcp_tool_dataclass(self):
        """Test MCPTool dataclass."""
        from src.core.mcp import MCPTool
        
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"},
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        
        data = tool.to_dict()
        assert data["name"] == "test_tool"


# ============================================
# Workflow Tests
# ============================================

class TestWorkflow:
    """Test Workflow Engine module."""
    
    def test_workflow_imports(self):
        """Test Workflow module imports correctly."""
        from src.core.workflow import (
            WorkflowEngine, Workflow, WorkflowStep,
            WorkflowStatus, StepStatus,
            get_workflow_engine,
        )
        assert WorkflowEngine is not None
        assert Workflow is not None
    
    def test_workflow_step_creation(self):
        """Test WorkflowStep creation."""
        from src.core.workflow import WorkflowStep
        
        step = WorkflowStep(
            name="test_step",
            action="run_command",
            params={"cmd": "echo hello"},
        )
        
        assert step.name == "test_step"
        assert step.action == "run_command"
    
    def test_workflow_creation(self):
        """Test Workflow creation."""
        from src.core.workflow import Workflow, WorkflowStep
        
        steps = [
            WorkflowStep(name="step1", action="run_command", params={"cmd": "echo 1"}),
            WorkflowStep(name="step2", action="run_command", params={"cmd": "echo 2"}),
        ]
        
        workflow = Workflow(
            name="test_workflow",
            description="A test workflow",
            steps=steps,
        )
        
        assert workflow.name == "test_workflow"
        assert len(workflow.steps) == 2
    
    def test_expression_evaluator(self):
        """Test ExpressionEvaluator."""
        from src.core.workflow import ExpressionEvaluator
        
        evaluator = ExpressionEvaluator()
        
        # Test variable interpolation
        result = evaluator.interpolate(
            "Hello ${name}!",
            {"name": "World"}
        )
        assert result == "Hello World!"
        
        # Test condition evaluation
        assert evaluator.evaluate_condition("1 == 1", {}) == True
        assert evaluator.evaluate_condition("${x} > 5", {"x": 10}) == True


# ============================================
# Analytics Tests
# ============================================

class TestAnalytics:
    """Test Analytics module."""
    
    def test_analytics_imports(self):
        """Test Analytics module imports correctly."""
        from src.core.analytics import (
            AnalyticsManager, EventType, Event,
            get_analytics, track_event,
        )
        assert AnalyticsManager is not None
        assert EventType is not None
    
    def test_event_types(self):
        """Test EventType enum."""
        from src.core.analytics import EventType
        
        assert EventType.MESSAGE.value == "message"
        assert EventType.COMMAND.value == "command"
        assert EventType.LLM_REQUEST.value == "llm_request"
    
    def test_event_creation(self):
        """Test Event creation."""
        from src.core.analytics import Event, EventType
        import uuid
        
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.MESSAGE,
            timestamp=datetime.now(),
            user_id="user123",
            data={"text": "hello"},
        )
        
        assert event.user_id == "user123"
        assert event.type == EventType.MESSAGE
        
        data = event.to_dict()
        assert data["user_id"] == "user123"
    
    def test_cost_estimator(self):
        """Test CostEstimator."""
        from src.core.analytics import CostEstimator
        
        estimator = CostEstimator()
        
        # Test cost calculation
        cost = estimator.estimate_cost(
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500,
        )
        
        assert cost >= 0


# ============================================
# Code Review Tests
# ============================================

class TestCodeReview:
    """Test Code Review module."""
    
    def test_code_review_imports(self):
        """Test Code Review module imports correctly."""
        from src.core.code_review import (
            CodeReviewManager, ReviewConfig, ReviewResult,
            ReviewSeverity, ReviewCategory,
            get_code_reviewer,
        )
        assert CodeReviewManager is not None
        assert ReviewConfig is not None
    
    def test_review_severity_enum(self):
        """Test ReviewSeverity enum."""
        from src.core.code_review import ReviewSeverity
        
        assert ReviewSeverity.INFO.value == "info"
        assert ReviewSeverity.WARNING.value == "warning"
        assert ReviewSeverity.ERROR.value == "error"
        assert ReviewSeverity.CRITICAL.value == "critical"
    
    def test_review_finding_creation(self):
        """Test ReviewFinding creation."""
        from src.core.code_review import ReviewFinding, ReviewSeverity, ReviewCategory
        
        finding = ReviewFinding(
            message="Unused variable",
            severity=ReviewSeverity.WARNING,
            category=ReviewCategory.QUALITY,
            file_path="test.py",
            line_start=10,
        )
        
        assert finding.message == "Unused variable"
        assert finding.severity == ReviewSeverity.WARNING
        
        data = finding.to_dict()
        assert data["severity"] == "warning"
    
    def test_security_scanner(self):
        """Test SecurityScanner."""
        from src.core.code_review import SecurityScanner
        
        scanner = SecurityScanner()
        
        # Test detection of eval()
        code = "result = eval(user_input)"
        
        loop = asyncio.new_event_loop()
        findings = loop.run_until_complete(scanner.scan(code, "python"))
        loop.close()
        
        assert len(findings) > 0
        assert any("eval" in f.message.lower() for f in findings)


# ============================================
# Conversation Export Tests
# ============================================

class TestConversationExport:
    """Test Conversation Export module."""
    
    def test_export_imports(self):
        """Test Export module imports correctly."""
        from src.core.conversation_export import (
            ConversationExporter, ExportFormat, ExportConfig,
            get_exporter,
        )
        assert ConversationExporter is not None
        assert ExportFormat is not None
    
    def test_export_formats(self):
        """Test ExportFormat enum."""
        from src.core.conversation_export import ExportFormat
        
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.MARKDOWN.value == "markdown"
        assert ExportFormat.HTML.value == "html"
    
    def test_export_message_creation(self):
        """Test ExportMessage creation."""
        from src.core.conversation_export import ExportMessage
        
        msg = ExportMessage(
            id="msg1",
            role="user",
            content="Hello!",
            timestamp=datetime.now(),
            user_name="TestUser",
        )
        
        assert msg.role == "user"
        assert msg.content == "Hello!"
        
        data = msg.to_dict()
        assert data["role"] == "user"
    
    def test_privacy_redactor(self):
        """Test PrivacyRedactor."""
        from src.core.conversation_export import PrivacyRedactor, ExportConfig
        
        redactor = PrivacyRedactor()
        config = ExportConfig(
            redact_emails=True,
            redact_api_keys=True,
        )
        
        # Test email redaction
        text = "Contact me at test@example.com"
        result = redactor.redact(text, config)
        assert "[EMAIL]" in result
        assert "test@example.com" not in result
    
    def test_markdown_exporter(self):
        """Test MarkdownExporter."""
        from src.core.conversation_export import MarkdownExporter, ExportMessage, ExportConfig
        
        config = ExportConfig()
        exporter = MarkdownExporter(config)
        
        messages = [
            ExportMessage(
                id="1",
                role="user",
                content="Hello!",
                timestamp=datetime.now(),
            ),
            ExportMessage(
                id="2",
                role="assistant",
                content="Hi there!",
                timestamp=datetime.now(),
            ),
        ]
        
        result = exporter.export(messages)
        
        assert "# Conversation Export" in result
        assert "Hello!" in result
        assert "Hi there!" in result


# ============================================
# Auto-Documentation Tests
# ============================================

class TestAutoDocs:
    """Test Auto-Documentation module."""
    
    def test_autodocs_imports(self):
        """Test Auto-Docs module imports correctly."""
        from src.core.auto_docs import (
            AutoDocGenerator, DocConfig, DocFormat,
            CodeParser, MarkdownGenerator,
            get_doc_generator,
        )
        assert AutoDocGenerator is not None
        assert CodeParser is not None
    
    def test_doc_formats(self):
        """Test DocFormat enum."""
        from src.core.auto_docs import DocFormat
        
        assert DocFormat.MARKDOWN.value == "markdown"
        assert DocFormat.HTML.value == "html"
    
    def test_code_parser(self):
        """Test CodeParser."""
        from src.core.auto_docs import CodeParser, DocConfig
        
        config = DocConfig()
        parser = CodeParser(config)
        
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
"""Test module docstring."""

def hello(name: str) -> str:
    """Say hello to someone.
    
    Args:
        name: The person's name
        
    Returns:
        A greeting message
    """
    return f"Hello, {name}!"

class Calculator:
    """A simple calculator."""
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
''')
            temp_path = f.name
        
        try:
            module_doc = parser.parse_file(temp_path)
            
            assert module_doc.docstring == "Test module docstring."
            assert len(module_doc.elements) >= 2  # function + class
            
            # Check function
            func = next((e for e in module_doc.elements if e.name == "hello"), None)
            assert func is not None
            assert len(func.parameters) == 1
            assert func.parameters[0].name == "name"
            
        finally:
            os.unlink(temp_path)


# ============================================
# Integration Tests
# ============================================

class TestV04Integration:
    """Integration tests for v0.4 features."""
    
    def test_all_modules_in_core_init(self):
        """Test all v0.4 modules are exported from core."""
        from src.core import (
            # MCP
            MCPManager, get_mcp_manager,
            # Workflow
            WorkflowEngine, get_workflow_engine,
            # Analytics
            AnalyticsManager, get_analytics,
            # Code Review
            CodeReviewManager, get_code_reviewer,
            # Conversation Export
            ConversationExporter, get_exporter,
            # Auto-Docs
            AutoDocGenerator, get_doc_generator,
        )
        
        assert MCPManager is not None
        assert WorkflowEngine is not None
        assert AnalyticsManager is not None
        assert CodeReviewManager is not None
        assert ConversationExporter is not None
        assert AutoDocGenerator is not None
    
    def test_handlers_registered(self):
        """Test v0.4 handlers can be imported."""
        from src.bot.v04_handlers import (
            mcp_command,
            workflow_command,
            analytics_command,
            review_command,
            export_command,
            docs_command,
            register_v04_handlers,
        )
        
        assert mcp_command is not None
        assert workflow_command is not None
        assert register_v04_handlers is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
