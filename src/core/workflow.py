"""
Workflow Engine for CursorBot

Provides workflow automation capabilities for multi-step task orchestration.

Features:
- Declarative workflow definition (YAML/JSON)
- Step-based execution with conditions
- Parallel and sequential execution
- Error handling and retries
- Variable interpolation
- Webhook triggers
- Scheduled workflows

Usage:
    from src.core.workflow import get_workflow_engine, Workflow, WorkflowStep
    
    engine = get_workflow_engine()
    
    # Define workflow
    workflow = Workflow(
        name="code-review",
        steps=[
            WorkflowStep(name="lint", action="run_command", params={"cmd": "npm run lint"}),
            WorkflowStep(name="test", action="run_command", params={"cmd": "npm test"}),
            WorkflowStep(name="notify", action="send_message", params={"text": "Review complete"}),
        ]
    )
    
    # Run workflow
    result = await engine.run(workflow, context={"branch": "main"})
"""

import asyncio
import json
import os
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Union

from ..utils.logger import logger


# ============================================
# Workflow Types
# ============================================

class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(Enum):
    """Step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(Enum):
    """Types of workflow steps."""
    ACTION = "action"           # Execute an action
    CONDITION = "condition"     # Conditional branching
    PARALLEL = "parallel"       # Run steps in parallel
    LOOP = "loop"              # Loop over items
    WAIT = "wait"              # Wait for event/time
    SUBPROCESS = "subprocess"   # Run sub-workflow


@dataclass
class StepResult:
    """Result of a workflow step execution."""
    step_name: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    action: str
    params: dict = field(default_factory=dict)
    
    # Control flow
    condition: Optional[str] = None  # Expression to evaluate
    depends_on: list[str] = field(default_factory=list)
    
    # Error handling
    retry_count: int = 0
    retry_delay: float = 1.0
    continue_on_error: bool = False
    timeout: float = 300.0
    
    # Output
    output_var: Optional[str] = None  # Variable to store result
    
    # Metadata
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class Workflow:
    """Workflow definition."""
    name: str
    steps: list[WorkflowStep] = field(default_factory=list)
    
    # Workflow metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    version: str = "1.0.0"
    
    # Triggers
    triggers: list[dict] = field(default_factory=list)
    
    # Variables
    variables: dict = field(default_factory=dict)
    
    # Settings
    max_parallel: int = 5
    timeout: float = 3600.0  # 1 hour
    
    @classmethod
    def from_dict(cls, data: dict) -> "Workflow":
        """Create workflow from dictionary."""
        steps = [
            WorkflowStep(**step) if isinstance(step, dict) else step
            for step in data.get("steps", [])
        ]
        
        return cls(
            name=data["name"],
            steps=steps,
            id=data.get("id", str(uuid.uuid4())[:8]),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            triggers=data.get("triggers", []),
            variables=data.get("variables", {}),
            max_parallel=data.get("max_parallel", 5),
            timeout=data.get("timeout", 3600.0),
        )
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Workflow":
        """Create workflow from YAML content."""
        try:
            import yaml
            data = yaml.safe_load(yaml_content)
            return cls.from_dict(data)
        except ImportError:
            raise ImportError("PyYAML not installed. Run: pip install pyyaml")
    
    @classmethod
    def from_file(cls, path: str) -> "Workflow":
        """Load workflow from file (YAML or JSON)."""
        path = Path(path)
        content = path.read_text()
        
        if path.suffix in (".yaml", ".yml"):
            return cls.from_yaml(content)
        else:
            return cls.from_dict(json.loads(content))
    
    def to_dict(self) -> dict:
        """Convert workflow to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [
                {
                    "name": s.name,
                    "action": s.action,
                    "params": s.params,
                    "condition": s.condition,
                    "depends_on": s.depends_on,
                    "retry_count": s.retry_count,
                    "continue_on_error": s.continue_on_error,
                    "timeout": s.timeout,
                    "output_var": s.output_var,
                }
                for s in self.steps
            ],
            "triggers": self.triggers,
            "variables": self.variables,
            "max_parallel": self.max_parallel,
            "timeout": self.timeout,
        }


@dataclass
class WorkflowRun:
    """A workflow execution instance."""
    id: str
    workflow: Workflow
    status: WorkflowStatus = WorkflowStatus.PENDING
    
    # Context and variables
    context: dict = field(default_factory=dict)
    variables: dict = field(default_factory=dict)
    
    # Results
    step_results: list[StepResult] = field(default_factory=list)
    output: Any = None
    error: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def duration_ms(self) -> int:
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return 0


# ============================================
# Action Handlers
# ============================================

class ActionHandler(ABC):
    """Base class for workflow action handlers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Action name."""
        pass
    
    @abstractmethod
    async def execute(self, params: dict, context: dict) -> Any:
        """Execute the action."""
        pass


class RunCommandAction(ActionHandler):
    """Execute shell command."""
    
    @property
    def name(self) -> str:
        return "run_command"
    
    async def execute(self, params: dict, context: dict) -> Any:
        cmd = params.get("cmd", "")
        cwd = params.get("cwd")
        timeout = params.get("timeout", 60)
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "success": process.returncode == 0,
            }
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"Command timed out: {cmd}")


class SendMessageAction(ActionHandler):
    """Send a message to user."""
    
    @property
    def name(self) -> str:
        return "send_message"
    
    async def execute(self, params: dict, context: dict) -> Any:
        text = params.get("text", "")
        channel = params.get("channel")
        user_id = context.get("user_id")
        
        # Use the gateway to send message
        try:
            from .gateway import get_gateway
            gateway = get_gateway()
            
            await gateway.send_message(
                platform=channel or context.get("platform", "telegram"),
                chat_id=user_id or context.get("chat_id"),
                text=text,
            )
            return {"sent": True, "text": text}
        except Exception as e:
            logger.warning(f"Failed to send message: {e}")
            return {"sent": False, "error": str(e)}


class HttpRequestAction(ActionHandler):
    """Make HTTP request."""
    
    @property
    def name(self) -> str:
        return "http_request"
    
    async def execute(self, params: dict, context: dict) -> Any:
        import httpx
        
        url = params.get("url")
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        body = params.get("body")
        timeout = params.get("timeout", 30)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if isinstance(body, dict) else None,
                content=body if isinstance(body, str) else None,
            )
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text,
                "json": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
            }


class SetVariableAction(ActionHandler):
    """Set a workflow variable."""
    
    @property
    def name(self) -> str:
        return "set_variable"
    
    async def execute(self, params: dict, context: dict) -> Any:
        name = params.get("name")
        value = params.get("value")
        
        # Variable will be set by the engine
        return {"name": name, "value": value}


class WaitAction(ActionHandler):
    """Wait for specified duration."""
    
    @property
    def name(self) -> str:
        return "wait"
    
    async def execute(self, params: dict, context: dict) -> Any:
        seconds = params.get("seconds", 0)
        await asyncio.sleep(seconds)
        return {"waited": seconds}


class LLMAction(ActionHandler):
    """Call LLM for generation."""
    
    @property
    def name(self) -> str:
        return "llm"
    
    async def execute(self, params: dict, context: dict) -> Any:
        prompt = params.get("prompt", "")
        system = params.get("system", "")
        model = params.get("model")
        
        try:
            from .llm_providers import get_llm_manager
            manager = get_llm_manager()
            
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            response = await manager.generate(messages, model=model)
            return {"response": response}
        except Exception as e:
            return {"error": str(e)}


class RAGQueryAction(ActionHandler):
    """Query RAG system."""
    
    @property
    def name(self) -> str:
        return "rag_query"
    
    async def execute(self, params: dict, context: dict) -> Any:
        question = params.get("question", "")
        top_k = params.get("top_k", 5)
        
        try:
            from .rag import get_rag_manager
            rag = get_rag_manager()
            
            response = await rag.query(question, top_k=top_k)
            return {
                "answer": response.answer,
                "sources": [
                    {"content": s.document.content[:200], "score": s.score}
                    for s in response.sources
                ],
            }
        except Exception as e:
            return {"error": str(e)}


class FileOperationAction(ActionHandler):
    """File operations (read/write)."""
    
    @property
    def name(self) -> str:
        return "file"
    
    async def execute(self, params: dict, context: dict) -> Any:
        operation = params.get("operation", "read")
        path = params.get("path")
        content = params.get("content")
        
        if operation == "read":
            try:
                with open(path, "r") as f:
                    return {"content": f.read()}
            except Exception as e:
                return {"error": str(e)}
        
        elif operation == "write":
            try:
                with open(path, "w") as f:
                    f.write(content)
                return {"written": True, "path": path}
            except Exception as e:
                return {"error": str(e)}
        
        elif operation == "exists":
            return {"exists": os.path.exists(path)}
        
        else:
            return {"error": f"Unknown operation: {operation}"}


# ============================================
# Expression Evaluator
# ============================================

class ExpressionEvaluator:
    """
    Evaluates expressions in workflow conditions and variable interpolation.
    Supports a safe subset of Python expressions.
    """
    
    SAFE_BUILTINS = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
        "round": round,
        "sorted": sorted,
        "reversed": reversed,
        "enumerate": enumerate,
        "zip": zip,
        "range": range,
        "True": True,
        "False": False,
        "None": None,
    }
    
    def __init__(self):
        pass
    
    def evaluate(self, expression: str, context: dict) -> Any:
        """
        Evaluate an expression with given context.
        
        Examples:
            "steps.lint.output.success" -> True
            "variables.count > 5" -> True/False
            "context.branch == 'main'" -> True/False
        """
        try:
            # Create safe namespace
            namespace = {
                **self.SAFE_BUILTINS,
                **context,
            }
            
            # Evaluate expression
            return eval(expression, {"__builtins__": {}}, namespace)
        except Exception as e:
            logger.warning(f"Expression evaluation error: {expression} -> {e}")
            return None
    
    def interpolate(self, template: str, context: dict) -> str:
        """
        Interpolate variables in a template string.
        
        Supports ${var} and ${{expression}} syntax.
        """
        # Simple variable interpolation: ${var}
        def replace_simple(match):
            var_name = match.group(1)
            value = self._get_nested(context, var_name.split("."))
            return str(value) if value is not None else match.group(0)
        
        result = re.sub(r"\$\{([^}]+)\}", replace_simple, template)
        
        # Expression interpolation: ${{expression}}
        def replace_expr(match):
            expr = match.group(1)
            value = self.evaluate(expr, context)
            return str(value) if value is not None else match.group(0)
        
        result = re.sub(r"\$\{\{([^}]+)\}\}", replace_expr, result)
        
        return result
    
    def _get_nested(self, obj: dict, keys: list[str]) -> Any:
        """Get nested value from dict."""
        for key in keys:
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                return None
        return obj


# ============================================
# Workflow Engine
# ============================================

class WorkflowEngine:
    """
    Main workflow execution engine.
    Handles workflow parsing, execution, and monitoring.
    """
    
    def __init__(self):
        self._actions: dict[str, ActionHandler] = {}
        self._runs: dict[str, WorkflowRun] = {}
        self._workflows: dict[str, Workflow] = {}
        self._evaluator = ExpressionEvaluator()
        
        # Register built-in actions
        self._register_builtin_actions()
    
    def _register_builtin_actions(self) -> None:
        """Register built-in action handlers."""
        builtin_actions = [
            RunCommandAction(),
            SendMessageAction(),
            HttpRequestAction(),
            SetVariableAction(),
            WaitAction(),
            LLMAction(),
            RAGQueryAction(),
            FileOperationAction(),
        ]
        
        for action in builtin_actions:
            self._actions[action.name] = action
    
    def register_action(self, handler: ActionHandler) -> None:
        """Register a custom action handler."""
        self._actions[handler.name] = handler
    
    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow for later execution."""
        self._workflows[workflow.name] = workflow
    
    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a registered workflow by name."""
        return self._workflows.get(name)
    
    def list_workflows(self) -> list[str]:
        """List registered workflow names."""
        return list(self._workflows.keys())
    
    async def run(
        self,
        workflow: Union[str, Workflow],
        context: dict = None,
        wait: bool = True,
    ) -> WorkflowRun:
        """
        Run a workflow.
        
        Args:
            workflow: Workflow name or Workflow object
            context: Initial context variables
            wait: Whether to wait for completion
            
        Returns:
            WorkflowRun instance
        """
        # Resolve workflow
        if isinstance(workflow, str):
            wf = self._workflows.get(workflow)
            if not wf:
                raise ValueError(f"Workflow not found: {workflow}")
        else:
            wf = workflow
        
        # Create run instance
        run = WorkflowRun(
            id=str(uuid.uuid4())[:8],
            workflow=wf,
            context=context or {},
            variables={**wf.variables},
        )
        
        self._runs[run.id] = run
        
        if wait:
            await self._execute(run)
        else:
            asyncio.create_task(self._execute(run))
        
        return run
    
    async def _execute(self, run: WorkflowRun) -> None:
        """Execute a workflow run."""
        run.status = WorkflowStatus.RUNNING
        run.started_at = datetime.now()
        
        logger.info(f"Starting workflow '{run.workflow.name}' (run: {run.id})")
        
        try:
            # Build execution context
            exec_context = {
                "context": run.context,
                "variables": run.variables,
                "steps": {},
            }
            
            # Execute steps in order (respecting dependencies)
            completed_steps = set()
            pending_steps = list(run.workflow.steps)
            
            while pending_steps:
                # Find steps that can be executed
                ready_steps = [
                    step for step in pending_steps
                    if all(dep in completed_steps for dep in step.depends_on)
                ]
                
                if not ready_steps:
                    if pending_steps:
                        raise RuntimeError("Circular dependency detected in workflow")
                    break
                
                # Execute ready steps (potentially in parallel)
                tasks = []
                for step in ready_steps[:run.workflow.max_parallel]:
                    task = asyncio.create_task(
                        self._execute_step(step, exec_context, run)
                    )
                    tasks.append((step, task))
                
                # Wait for batch completion
                for step, task in tasks:
                    try:
                        result = await task
                        exec_context["steps"][step.name] = {
                            "output": result.output,
                            "status": result.status.value,
                        }
                        completed_steps.add(step.name)
                        pending_steps.remove(step)
                        
                        # Check if step failed and should stop
                        if result.status == StepStatus.FAILED and not step.continue_on_error:
                            raise RuntimeError(f"Step '{step.name}' failed: {result.error}")
                        
                    except Exception as e:
                        if not step.continue_on_error:
                            raise
                        logger.warning(f"Step '{step.name}' failed but continuing: {e}")
                        completed_steps.add(step.name)
                        pending_steps.remove(step)
            
            # Workflow completed successfully
            run.status = WorkflowStatus.COMPLETED
            run.output = exec_context
            
        except Exception as e:
            run.status = WorkflowStatus.FAILED
            run.error = str(e)
            logger.error(f"Workflow '{run.workflow.name}' failed: {e}")
        
        finally:
            run.completed_at = datetime.now()
            logger.info(
                f"Workflow '{run.workflow.name}' {run.status.value} "
                f"(duration: {run.duration_ms}ms)"
            )
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        exec_context: dict,
        run: WorkflowRun,
    ) -> StepResult:
        """Execute a single workflow step."""
        result = StepResult(
            step_name=step.name,
            status=StepStatus.PENDING,
            started_at=datetime.now(),
        )
        
        logger.debug(f"Executing step '{step.name}'")
        
        try:
            # Check condition
            if step.condition:
                condition_result = self._evaluator.evaluate(step.condition, exec_context)
                if not condition_result:
                    result.status = StepStatus.SKIPPED
                    result.completed_at = datetime.now()
                    run.step_results.append(result)
                    return result
            
            # Get action handler
            handler = self._actions.get(step.action)
            if not handler:
                raise ValueError(f"Unknown action: {step.action}")
            
            # Interpolate parameters
            params = self._interpolate_params(step.params, exec_context)
            
            # Execute with retry
            result.status = StepStatus.RUNNING
            attempt = 0
            last_error = None
            
            while attempt <= step.retry_count:
                try:
                    output = await asyncio.wait_for(
                        handler.execute(params, run.context),
                        timeout=step.timeout,
                    )
                    
                    result.output = output
                    result.status = StepStatus.COMPLETED
                    
                    # Set output variable
                    if step.output_var:
                        run.variables[step.output_var] = output
                    
                    break
                    
                except Exception as e:
                    last_error = e
                    attempt += 1
                    if attempt <= step.retry_count:
                        logger.warning(f"Step '{step.name}' failed, retrying ({attempt}/{step.retry_count})")
                        await asyncio.sleep(step.retry_delay)
            
            if result.status != StepStatus.COMPLETED:
                result.status = StepStatus.FAILED
                result.error = str(last_error)
        
        except Exception as e:
            result.status = StepStatus.FAILED
            result.error = str(e)
        
        finally:
            result.completed_at = datetime.now()
            result.duration_ms = int(
                (result.completed_at - result.started_at).total_seconds() * 1000
            )
            run.step_results.append(result)
        
        return result
    
    def _interpolate_params(self, params: dict, context: dict) -> dict:
        """Interpolate variables in parameters."""
        result = {}
        for key, value in params.items():
            if isinstance(value, str):
                result[key] = self._evaluator.interpolate(value, context)
            elif isinstance(value, dict):
                result[key] = self._interpolate_params(value, context)
            elif isinstance(value, list):
                result[key] = [
                    self._evaluator.interpolate(v, context) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                result[key] = value
        return result
    
    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        """Get a workflow run by ID."""
        return self._runs.get(run_id)
    
    def list_runs(self, workflow_name: str = None) -> list[WorkflowRun]:
        """List workflow runs."""
        runs = list(self._runs.values())
        if workflow_name:
            runs = [r for r in runs if r.workflow.name == workflow_name]
        return runs
    
    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a running workflow."""
        run = self._runs.get(run_id)
        if not run or run.status != WorkflowStatus.RUNNING:
            return False
        
        run.status = WorkflowStatus.CANCELLED
        run.completed_at = datetime.now()
        return True
    
    def get_stats(self) -> dict:
        """Get engine statistics."""
        runs = list(self._runs.values())
        return {
            "registered_workflows": len(self._workflows),
            "registered_actions": len(self._actions),
            "total_runs": len(runs),
            "runs_by_status": {
                status.value: len([r for r in runs if r.status == status])
                for status in WorkflowStatus
            },
        }


# ============================================
# Predefined Workflows
# ============================================

def create_code_review_workflow() -> Workflow:
    """Create a code review workflow."""
    return Workflow(
        name="code-review",
        description="Automated code review workflow",
        steps=[
            WorkflowStep(
                name="lint",
                action="run_command",
                params={"cmd": "npm run lint || echo 'No lint script'"},
                continue_on_error=True,
            ),
            WorkflowStep(
                name="test",
                action="run_command",
                params={"cmd": "npm test || echo 'No test script'"},
                continue_on_error=True,
            ),
            WorkflowStep(
                name="analyze",
                action="llm",
                params={
                    "system": "You are a code reviewer. Analyze the lint and test results.",
                    "prompt": "Lint result: ${steps.lint.output.stdout}\nTest result: ${steps.test.output.stdout}\n\nProvide a summary and recommendations.",
                },
            ),
            WorkflowStep(
                name="notify",
                action="send_message",
                params={"text": "Code review complete:\n${steps.analyze.output.response}"},
            ),
        ],
    )


def create_deploy_workflow() -> Workflow:
    """Create a deployment workflow."""
    return Workflow(
        name="deploy",
        description="Deployment workflow",
        steps=[
            WorkflowStep(
                name="build",
                action="run_command",
                params={"cmd": "npm run build"},
                timeout=300,
            ),
            WorkflowStep(
                name="test",
                action="run_command",
                params={"cmd": "npm test"},
                depends_on=["build"],
            ),
            WorkflowStep(
                name="deploy",
                action="run_command",
                params={"cmd": "npm run deploy"},
                depends_on=["test"],
            ),
            WorkflowStep(
                name="notify",
                action="send_message",
                params={"text": "Deployment ${variables.version} complete!"},
                depends_on=["deploy"],
            ),
        ],
    )


# ============================================
# Global Instance
# ============================================

_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get the global workflow engine instance."""
    global _workflow_engine
    
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
        
        # Register predefined workflows
        _workflow_engine.register_workflow(create_code_review_workflow())
        _workflow_engine.register_workflow(create_deploy_workflow())
    
    return _workflow_engine


def reset_workflow_engine() -> None:
    """Reset the workflow engine instance."""
    global _workflow_engine
    _workflow_engine = None


__all__ = [
    # Types
    "WorkflowStatus",
    "StepStatus",
    "StepType",
    "StepResult",
    "WorkflowStep",
    "Workflow",
    "WorkflowRun",
    # Actions
    "ActionHandler",
    "RunCommandAction",
    "SendMessageAction",
    "HttpRequestAction",
    "SetVariableAction",
    "WaitAction",
    "LLMAction",
    "RAGQueryAction",
    "FileOperationAction",
    # Engine
    "WorkflowEngine",
    "get_workflow_engine",
    "reset_workflow_engine",
    # Utilities
    "ExpressionEvaluator",
    # Predefined workflows
    "create_code_review_workflow",
    "create_deploy_workflow",
]
