"""
LLM Task System for CursorBot

Provides:
- Structured LLM task execution
- Task templates and prompts
- Task chaining and composition
- Result formatting
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class TaskType(Enum):
    """Types of LLM tasks."""
    COMPLETION = "completion"
    CHAT = "chat"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    ANALYZE = "analyze"
    EXTRACT = "extract"
    GENERATE = "generate"
    TRANSFORM = "transform"


@dataclass
class TaskTemplate:
    """Template for LLM tasks."""
    name: str
    task_type: TaskType
    system_prompt: str
    user_prompt_template: str
    output_format: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    
    def render_prompt(self, **kwargs) -> str:
        """Render the user prompt with variables."""
        return self.user_prompt_template.format(**kwargs)


@dataclass
class TaskResult:
    """Result from an LLM task."""
    success: bool
    task_type: TaskType
    output: str
    metadata: dict = field(default_factory=dict)
    error: Optional[str] = None
    tokens_used: int = 0
    execution_time: float = 0
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "task_type": self.task_type.value,
            "output": self.output,
            "metadata": self.metadata,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "execution_time": self.execution_time,
        }


# ============================================
# Built-in Task Templates
# ============================================

BUILTIN_TEMPLATES = {
    "summarize": TaskTemplate(
        name="summarize",
        task_type=TaskType.SUMMARIZE,
        system_prompt="You are a professional summarizer. Create concise, accurate summaries.",
        user_prompt_template="Please summarize the following text:\n\n{text}\n\nProvide a summary in {length} sentences.",
        max_tokens=500,
        temperature=0.3,
    ),
    "translate": TaskTemplate(
        name="translate",
        task_type=TaskType.TRANSLATE,
        system_prompt="You are a professional translator. Translate accurately while preserving meaning and tone.",
        user_prompt_template="Translate the following text to {target_language}:\n\n{text}",
        max_tokens=2000,
        temperature=0.2,
    ),
    "analyze_code": TaskTemplate(
        name="analyze_code",
        task_type=TaskType.ANALYZE,
        system_prompt="You are a senior software engineer. Analyze code for quality, bugs, and improvements.",
        user_prompt_template="Analyze the following {language} code:\n\n```{language}\n{code}\n```\n\nProvide:\n1. Code quality assessment\n2. Potential bugs\n3. Improvement suggestions",
        max_tokens=1500,
        temperature=0.5,
    ),
    "extract_entities": TaskTemplate(
        name="extract_entities",
        task_type=TaskType.EXTRACT,
        system_prompt="You are an entity extraction expert. Extract structured information from text.",
        user_prompt_template="Extract the following entities from the text: {entity_types}\n\nText:\n{text}\n\nReturn as JSON.",
        output_format="json",
        max_tokens=1000,
        temperature=0.1,
    ),
    "generate_docstring": TaskTemplate(
        name="generate_docstring",
        task_type=TaskType.GENERATE,
        system_prompt="You are a documentation expert. Generate clear, comprehensive docstrings.",
        user_prompt_template="Generate a docstring for the following {language} function:\n\n```{language}\n{code}\n```\n\nUse {style} style.",
        max_tokens=500,
        temperature=0.3,
    ),
    "rewrite": TaskTemplate(
        name="rewrite",
        task_type=TaskType.TRANSFORM,
        system_prompt="You are a professional writer. Rewrite text while preserving meaning.",
        user_prompt_template="Rewrite the following text in a {tone} tone:\n\n{text}",
        max_tokens=1000,
        temperature=0.7,
    ),
    "explain": TaskTemplate(
        name="explain",
        task_type=TaskType.COMPLETION,
        system_prompt="You are an expert teacher. Explain concepts clearly and thoroughly.",
        user_prompt_template="Explain {topic} in simple terms. Target audience: {audience}.",
        max_tokens=1500,
        temperature=0.5,
    ),
}


class LLMTaskManager:
    """
    Manages LLM task execution.
    """
    
    def __init__(self):
        self._templates: dict[str, TaskTemplate] = BUILTIN_TEMPLATES.copy()
        self._task_history: list[TaskResult] = []
        self._hooks: dict[str, list[Callable]] = {
            "before_task": [],
            "after_task": [],
        }
    
    def register_template(self, template: TaskTemplate) -> None:
        """Register a custom task template."""
        self._templates[template.name] = template
        logger.info(f"Registered LLM task template: {template.name}")
    
    def get_template(self, name: str) -> Optional[TaskTemplate]:
        """Get a template by name."""
        return self._templates.get(name)
    
    def list_templates(self) -> list[str]:
        """List all available templates."""
        return list(self._templates.keys())
    
    async def execute_task(
        self,
        template_name: str,
        user_id: int = 0,
        **kwargs,
    ) -> TaskResult:
        """
        Execute an LLM task using a template.
        
        Args:
            template_name: Name of the template to use
            user_id: User ID for tracking
            **kwargs: Variables to fill in the template
        
        Returns:
            TaskResult
        """
        template = self.get_template(template_name)
        if not template:
            return TaskResult(
                success=False,
                task_type=TaskType.COMPLETION,
                output="",
                error=f"Template not found: {template_name}",
            )
        
        start_time = datetime.now()
        
        # Run before hooks
        for hook in self._hooks["before_task"]:
            try:
                await hook(template_name, kwargs)
            except Exception as e:
                logger.warning(f"Before task hook error: {e}")
        
        try:
            # Render prompt
            user_prompt = template.render_prompt(**kwargs)
            
            # Get LLM manager and execute
            from .llm_providers import get_llm_manager
            manager = get_llm_manager()
            
            messages = [
                {"role": "system", "content": template.system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            
            response = await manager.generate(
                messages=messages,
                user_id=user_id,
                max_tokens=template.max_tokens,
                temperature=template.temperature,
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = TaskResult(
                success=True,
                task_type=template.task_type,
                output=response,
                metadata={
                    "template": template_name,
                    "user_id": user_id,
                },
                execution_time=execution_time,
            )
            
        except Exception as e:
            logger.error(f"LLM task error: {e}")
            result = TaskResult(
                success=False,
                task_type=template.task_type,
                output="",
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds(),
            )
        
        # Run after hooks
        for hook in self._hooks["after_task"]:
            try:
                await hook(template_name, result)
            except Exception as e:
                logger.warning(f"After task hook error: {e}")
        
        # Store in history
        self._task_history.append(result)
        if len(self._task_history) > 100:
            self._task_history = self._task_history[-100:]
        
        return result
    
    async def execute_chain(
        self,
        tasks: list[tuple[str, dict]],
        user_id: int = 0,
    ) -> list[TaskResult]:
        """
        Execute a chain of LLM tasks.
        
        Args:
            tasks: List of (template_name, kwargs) tuples
            user_id: User ID
        
        Returns:
            List of TaskResults
        """
        results = []
        previous_output = None
        
        for template_name, kwargs in tasks:
            # Allow using previous output in chain
            if previous_output and "{previous_output}" in str(kwargs):
                for key, value in kwargs.items():
                    if isinstance(value, str) and "{previous_output}" in value:
                        kwargs[key] = value.replace("{previous_output}", previous_output)
            
            result = await self.execute_task(template_name, user_id, **kwargs)
            results.append(result)
            
            if result.success:
                previous_output = result.output
            else:
                break  # Stop chain on failure
        
        return results
    
    async def summarize(self, text: str, length: int = 3, user_id: int = 0) -> TaskResult:
        """Summarize text."""
        return await self.execute_task("summarize", user_id, text=text, length=length)
    
    async def translate(self, text: str, target_language: str, user_id: int = 0) -> TaskResult:
        """Translate text."""
        return await self.execute_task("translate", user_id, text=text, target_language=target_language)
    
    async def analyze_code(self, code: str, language: str = "python", user_id: int = 0) -> TaskResult:
        """Analyze code."""
        return await self.execute_task("analyze_code", user_id, code=code, language=language)
    
    async def explain(self, topic: str, audience: str = "beginners", user_id: int = 0) -> TaskResult:
        """Explain a topic."""
        return await self.execute_task("explain", user_id, topic=topic, audience=audience)
    
    def add_hook(self, event: str, hook: Callable) -> None:
        """Add a hook for task events."""
        if event in self._hooks:
            self._hooks[event].append(hook)
    
    def get_history(self, limit: int = 20) -> list[dict]:
        """Get task execution history."""
        return [r.to_dict() for r in self._task_history[-limit:]]
    
    def get_stats(self) -> dict:
        """Get task statistics."""
        total = len(self._task_history)
        success = sum(1 for r in self._task_history if r.success)
        
        by_type = {}
        for r in self._task_history:
            t = r.task_type.value
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            "total_tasks": total,
            "success_count": success,
            "failure_count": total - success,
            "success_rate": success / total if total > 0 else 0,
            "by_type": by_type,
            "available_templates": len(self._templates),
        }


# ============================================
# Global Instance
# ============================================

_task_manager: Optional[LLMTaskManager] = None


def get_llm_task_manager() -> LLMTaskManager:
    """Get the global LLM task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = LLMTaskManager()
    return _task_manager


__all__ = [
    "TaskType",
    "TaskTemplate",
    "TaskResult",
    "LLMTaskManager",
    "get_llm_task_manager",
]
