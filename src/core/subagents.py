"""
Subagent System for CursorBot

Provides:
- Task decomposition and delegation
- Specialized agent spawning
- Inter-agent communication
- Result aggregation
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class SubagentType(Enum):
    """Types of specialized subagents."""
    RESEARCHER = "researcher"  # Information gathering
    CODER = "coder"  # Code generation
    REVIEWER = "reviewer"  # Code review
    PLANNER = "planner"  # Task planning
    EXECUTOR = "executor"  # Task execution
    ANALYST = "analyst"  # Data analysis
    WRITER = "writer"  # Content writing
    CUSTOM = "custom"  # Custom agent


class SubagentStatus(Enum):
    """Subagent execution status."""
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


@dataclass
class SubagentTask:
    """Task assigned to a subagent."""
    id: str
    description: str
    context: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)  # Task IDs this depends on
    result: Any = None
    error: Optional[str] = None
    status: SubagentStatus = SubagentStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class SubagentConfig:
    """Configuration for a subagent."""
    type: SubagentType = SubagentType.CUSTOM
    name: str = ""
    system_prompt: str = ""
    model: Optional[str] = None
    max_iterations: int = 10
    timeout: float = 300.0  # seconds
    tools: list[str] = field(default_factory=list)


class Subagent(ABC):
    """
    Base class for specialized subagents.
    """
    
    def __init__(self, config: SubagentConfig):
        self.config = config
        self.id = str(uuid.uuid4())[:8]
        self.status = SubagentStatus.IDLE
        self._current_task: Optional[SubagentTask] = None
    
    @property
    def name(self) -> str:
        return self.config.name or f"{self.config.type.value}_{self.id}"
    
    @abstractmethod
    async def execute(self, task: SubagentTask) -> Any:
        """
        Execute a task and return the result.
        
        Args:
            task: Task to execute
        
        Returns:
            Task result
        """
        pass
    
    def get_status(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.config.type.value,
            "status": self.status.value,
            "current_task": self._current_task.id if self._current_task else None,
        }


class LLMSubagent(Subagent):
    """
    LLM-powered subagent that uses language model for task execution.
    """
    
    async def execute(self, task: SubagentTask) -> Any:
        from .llm_providers import get_llm_manager
        
        self.status = SubagentStatus.WORKING
        self._current_task = task
        task.status = SubagentStatus.WORKING
        
        try:
            manager = get_llm_manager()
            
            # Build prompt with context
            context_str = "\n".join([
                f"- {k}: {v}" for k, v in task.context.items()
            ]) if task.context else "No additional context."
            
            messages = [
                {
                    "role": "system",
                    "content": self.config.system_prompt or self._get_default_prompt()
                },
                {
                    "role": "user",
                    "content": f"""Task: {task.description}

Context:
{context_str}

Please complete this task and provide a clear response."""
                }
            ]
            
            # Execute with timeout
            result = await asyncio.wait_for(
                manager.generate(
                    messages,
                    model=self.config.model,
                    max_tokens=4096
                ),
                timeout=self.config.timeout
            )
            
            task.result = result
            task.status = SubagentStatus.COMPLETED
            task.completed_at = datetime.now()
            self.status = SubagentStatus.COMPLETED
            
            return result
            
        except asyncio.TimeoutError:
            task.error = f"Task timed out after {self.config.timeout}s"
            task.status = SubagentStatus.FAILED
            self.status = SubagentStatus.FAILED
            raise
            
        except Exception as e:
            task.error = str(e)
            task.status = SubagentStatus.FAILED
            self.status = SubagentStatus.FAILED
            raise
        
        finally:
            self._current_task = None
    
    def _get_default_prompt(self) -> str:
        """Get default system prompt based on agent type."""
        prompts = {
            SubagentType.RESEARCHER: (
                "You are a research assistant specialized in gathering and synthesizing information. "
                "Provide well-organized, factual responses with sources when possible."
            ),
            SubagentType.CODER: (
                "You are an expert programmer. Write clean, efficient, well-documented code. "
                "Follow best practices and include error handling."
            ),
            SubagentType.REVIEWER: (
                "You are a code reviewer. Analyze code for bugs, security issues, and improvements. "
                "Provide constructive feedback with specific suggestions."
            ),
            SubagentType.PLANNER: (
                "You are a project planner. Break down complex tasks into manageable steps. "
                "Consider dependencies and provide realistic estimates."
            ),
            SubagentType.EXECUTOR: (
                "You are a task executor. Follow instructions precisely and report results clearly. "
                "Handle errors gracefully and provide status updates."
            ),
            SubagentType.ANALYST: (
                "You are a data analyst. Analyze data and provide insights. "
                "Use clear visualizations and statistical methods when appropriate."
            ),
            SubagentType.WRITER: (
                "You are a content writer. Create clear, engaging, and well-structured content. "
                "Adapt your style to the target audience."
            ),
        }
        return prompts.get(self.config.type, "You are a helpful assistant.")


# ============================================
# Subagent Orchestrator
# ============================================

@dataclass
class TaskPlan:
    """A plan for executing a complex task with subagents."""
    id: str
    goal: str
    tasks: list[SubagentTask] = field(default_factory=list)
    status: SubagentStatus = SubagentStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    final_result: Any = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status.value,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class SubagentOrchestrator:
    """
    Orchestrates multiple subagents to complete complex tasks.
    """
    
    def __init__(self):
        self._agents: dict[str, Subagent] = {}
        self._plans: dict[str, TaskPlan] = {}
        self._results_cache: dict[str, Any] = {}
    
    def create_agent(
        self,
        agent_type: SubagentType,
        name: str = None,
        system_prompt: str = None,
        model: str = None,
    ) -> Subagent:
        """
        Create a new subagent.
        
        Args:
            agent_type: Type of agent to create
            name: Optional agent name
            system_prompt: Optional custom system prompt
            model: Optional LLM model to use
        
        Returns:
            Created subagent
        """
        config = SubagentConfig(
            type=agent_type,
            name=name or f"{agent_type.value}",
            system_prompt=system_prompt or "",
            model=model,
        )
        
        agent = LLMSubagent(config)
        self._agents[agent.id] = agent
        
        logger.info(f"Created subagent: {agent.name} ({agent.id})")
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Subagent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> list[dict]:
        """List all agents."""
        return [a.get_status() for a in self._agents.values()]
    
    async def plan_task(
        self,
        goal: str,
        context: dict = None,
    ) -> TaskPlan:
        """
        Create a task plan by decomposing a goal into subtasks.
        
        Args:
            goal: The goal to achieve
            context: Additional context
        
        Returns:
            TaskPlan with decomposed tasks
        """
        from .llm_providers import get_llm_manager
        
        plan_id = str(uuid.uuid4())[:8]
        
        # Use LLM to decompose the task
        manager = get_llm_manager()
        
        messages = [
            {
                "role": "system",
                "content": """You are a task planner. Break down complex tasks into smaller, manageable subtasks.
Output format (JSON array):
[
  {"description": "task description", "type": "researcher|coder|reviewer|planner|executor|analyst|writer", "dependencies": []},
  {"description": "another task", "type": "coder", "dependencies": ["0"]},
  ...
]
Dependencies are indices of tasks that must complete first."""
            },
            {
                "role": "user",
                "content": f"Goal: {goal}\n\nContext: {context or 'None'}\n\nPlease decompose this into subtasks."
            }
        ]
        
        response = await manager.generate(messages, max_tokens=2000)
        
        # Parse response
        import json
        import re
        
        # Extract JSON from response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            try:
                task_defs = json.loads(json_match.group())
            except json.JSONDecodeError:
                task_defs = [{"description": goal, "type": "executor", "dependencies": []}]
        else:
            task_defs = [{"description": goal, "type": "executor", "dependencies": []}]
        
        # Create tasks
        tasks = []
        for i, task_def in enumerate(task_defs):
            task_id = f"{plan_id}_{i}"
            dependencies = [f"{plan_id}_{d}" for d in task_def.get("dependencies", [])]
            
            task = SubagentTask(
                id=task_id,
                description=task_def.get("description", ""),
                context=context or {},
                dependencies=dependencies,
            )
            tasks.append(task)
        
        plan = TaskPlan(
            id=plan_id,
            goal=goal,
            tasks=tasks,
        )
        
        self._plans[plan_id] = plan
        logger.info(f"Created task plan {plan_id} with {len(tasks)} subtasks")
        
        return plan
    
    async def execute_plan(
        self,
        plan: TaskPlan,
        callback: Callable = None,
    ) -> Any:
        """
        Execute a task plan.
        
        Args:
            plan: Task plan to execute
            callback: Optional callback for progress updates
        
        Returns:
            Final aggregated result
        """
        plan.status = SubagentStatus.WORKING
        results = {}
        
        try:
            # Build dependency graph
            pending = {t.id: t for t in plan.tasks}
            completed = set()
            
            while pending:
                # Find tasks ready to execute (dependencies satisfied)
                ready = [
                    t for t in pending.values()
                    if all(dep in completed for dep in t.dependencies)
                ]
                
                if not ready:
                    # Deadlock or all tasks have unmet dependencies
                    logger.warning(f"No ready tasks, remaining: {list(pending.keys())}")
                    break
                
                # Execute ready tasks in parallel
                async def execute_task(task: SubagentTask):
                    # Add results from dependencies to context
                    for dep_id in task.dependencies:
                        if dep_id in results:
                            task.context[f"result_{dep_id}"] = results[dep_id]
                    
                    # Select appropriate agent
                    agent_type = self._infer_agent_type(task.description)
                    agent = self.create_agent(agent_type)
                    
                    try:
                        result = await agent.execute(task)
                        results[task.id] = result
                        return task.id, result
                    except Exception as e:
                        logger.error(f"Task {task.id} failed: {e}")
                        results[task.id] = None
                        return task.id, None
                
                # Run ready tasks
                tasks_coros = [execute_task(t) for t in ready]
                completed_results = await asyncio.gather(*tasks_coros, return_exceptions=True)
                
                # Update state
                for t in ready:
                    del pending[t.id]
                    completed.add(t.id)
                
                # Callback for progress
                if callback:
                    progress = len(completed) / len(plan.tasks)
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(plan, progress, completed_results)
                        else:
                            callback(plan, progress, completed_results)
                    except Exception:
                        pass
            
            # Aggregate results
            plan.status = SubagentStatus.COMPLETED
            plan.completed_at = datetime.now()
            
            # Create final summary
            plan.final_result = await self._aggregate_results(plan.goal, results)
            
            return plan.final_result
            
        except Exception as e:
            plan.status = SubagentStatus.FAILED
            logger.error(f"Plan execution failed: {e}")
            raise
    
    def _infer_agent_type(self, task_description: str) -> SubagentType:
        """Infer the appropriate agent type from task description."""
        desc_lower = task_description.lower()
        
        if any(w in desc_lower for w in ["research", "find", "search", "gather", "investigate"]):
            return SubagentType.RESEARCHER
        elif any(w in desc_lower for w in ["code", "implement", "write code", "program", "develop"]):
            return SubagentType.CODER
        elif any(w in desc_lower for w in ["review", "check", "audit", "validate"]):
            return SubagentType.REVIEWER
        elif any(w in desc_lower for w in ["plan", "design", "architect", "outline"]):
            return SubagentType.PLANNER
        elif any(w in desc_lower for w in ["analyze", "examine", "evaluate", "assess"]):
            return SubagentType.ANALYST
        elif any(w in desc_lower for w in ["write", "document", "compose", "draft"]):
            return SubagentType.WRITER
        else:
            return SubagentType.EXECUTOR
    
    async def _aggregate_results(self, goal: str, results: dict) -> str:
        """Aggregate results from all subtasks into a final response."""
        from .llm_providers import get_llm_manager
        
        if not results:
            return "No results to aggregate."
        
        manager = get_llm_manager()
        
        results_text = "\n\n".join([
            f"[Task {tid}]\n{result or 'Failed'}"
            for tid, result in results.items()
        ])
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert at synthesizing information. Combine the results from multiple subtasks into a coherent final response."
            },
            {
                "role": "user",
                "content": f"""Original Goal: {goal}

Subtask Results:
{results_text}

Please synthesize these results into a comprehensive final response."""
            }
        ]
        
        return await manager.generate(messages, max_tokens=4096)
    
    def get_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)
    
    def get_stats(self) -> dict:
        """Get orchestrator statistics."""
        return {
            "total_agents": len(self._agents),
            "total_plans": len(self._plans),
            "active_agents": sum(1 for a in self._agents.values() if a.status == SubagentStatus.WORKING),
            "completed_plans": sum(1 for p in self._plans.values() if p.status == SubagentStatus.COMPLETED),
        }


# ============================================
# Global Instance
# ============================================

_orchestrator: Optional[SubagentOrchestrator] = None


def get_subagent_orchestrator() -> SubagentOrchestrator:
    """Get the global subagent orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SubagentOrchestrator()
    return _orchestrator


__all__ = [
    "SubagentType",
    "SubagentStatus",
    "SubagentTask",
    "SubagentConfig",
    "Subagent",
    "LLMSubagent",
    "TaskPlan",
    "SubagentOrchestrator",
    "get_subagent_orchestrator",
]
