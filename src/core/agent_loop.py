"""
Agent Loop System for CursorBot
Inspired by ClawdBot's agent runtime

Provides:
- Autonomous agent execution
- Multi-step task handling
- Tool orchestration
- Conversation management
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class AgentState(Enum):
    """Agent execution state."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


class ActionType(Enum):
    """Types of agent actions."""
    THINK = "think"
    TOOL_CALL = "tool_call"
    RESPOND = "respond"
    DELEGATE = "delegate"
    WAIT = "wait"
    COMPLETE = "complete"


@dataclass
class AgentAction:
    """Represents an action in the agent loop."""
    action_type: ActionType
    content: str = ""
    tool_name: Optional[str] = None
    tool_args: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentStep:
    """A single step in agent execution."""
    step_number: int
    action: AgentAction
    result: Any = None
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class AgentContext:
    """Context for agent execution."""
    user_id: str
    session_id: str
    initial_prompt: str
    
    # State
    state: AgentState = AgentState.IDLE
    steps: list[AgentStep] = field(default_factory=list)
    
    # Configuration
    max_steps: int = 20
    timeout_seconds: int = 300
    
    # Memory and context
    memory: dict = field(default_factory=dict)
    conversation: list[dict] = field(default_factory=list)
    
    # Results
    final_response: Optional[str] = None
    error: Optional[str] = None

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def add_step(self, action: AgentAction, result: Any = None, error: str = None, duration_ms: int = 0) -> AgentStep:
        step = AgentStep(
            step_number=self.step_count + 1,
            action=action,
            result=result,
            error=error,
            duration_ms=duration_ms,
        )
        self.steps.append(step)
        return step


class AgentLoop:
    """
    Agent execution loop.
    
    Manages the autonomous execution of AI agent tasks with:
    - Multi-step reasoning
    - Tool invocation
    - Context management
    - Error handling
    
    Usage:
        agent = AgentLoop(
            llm_provider=my_llm_function,
            tools=my_tools_dict,
        )
        
        result = await agent.run(
            prompt="Help me refactor this code",
            user_id="123",
        )
    """

    def __init__(
        self,
        llm_provider: Callable = None,
        tools: dict[str, Callable] = None,
        system_prompt: str = None,
    ):
        self.llm_provider = llm_provider
        self.tools = tools or {}
        self.system_prompt = system_prompt or self._default_system_prompt()
        
        # Event hooks
        self._on_step: list[Callable] = []
        self._on_tool_call: list[Callable] = []
        self._on_complete: list[Callable] = []

    def _default_system_prompt(self) -> str:
        return """You are CursorBot, an AI assistant that helps with coding tasks.

You have access to various tools to help complete tasks:
- read_file: Read file contents
- write_file: Write to files
- execute_command: Run shell commands
- fetch_url: Fetch web content
- github: GitHub operations

When given a task:
1. Think about what needs to be done
2. Use appropriate tools to gather information or make changes
3. Verify your work
4. Provide a clear response

Always explain your reasoning and actions.
"""

    def on_step(self, handler: Callable) -> Callable:
        """Register step handler."""
        self._on_step.append(handler)
        return handler

    def on_tool_call(self, handler: Callable) -> Callable:
        """Register tool call handler."""
        self._on_tool_call.append(handler)
        return handler

    def on_complete(self, handler: Callable) -> Callable:
        """Register completion handler."""
        self._on_complete.append(handler)
        return handler

    async def _emit_step(self, ctx: AgentContext, step: AgentStep) -> None:
        for handler in self._on_step:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(ctx, step)
                else:
                    handler(ctx, step)
            except Exception as e:
                logger.error(f"Step handler error: {e}")

    async def _emit_tool_call(self, ctx: AgentContext, tool_name: str, args: dict, result: Any) -> None:
        for handler in self._on_tool_call:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(ctx, tool_name, args, result)
                else:
                    handler(ctx, tool_name, args, result)
            except Exception as e:
                logger.error(f"Tool call handler error: {e}")

    async def _emit_complete(self, ctx: AgentContext) -> None:
        for handler in self._on_complete:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(ctx)
                else:
                    handler(ctx)
            except Exception as e:
                logger.error(f"Complete handler error: {e}")

    async def run(
        self,
        prompt: str,
        user_id: str,
        session_id: str = None,
        context: dict = None,
        max_steps: int = 20,
        timeout: int = 300,
    ) -> AgentContext:
        """
        Run the agent loop.
        
        Args:
            prompt: User's initial prompt
            user_id: User identifier
            session_id: Session identifier
            context: Additional context
            max_steps: Maximum execution steps
            timeout: Timeout in seconds
            
        Returns:
            AgentContext with results
        """
        import uuid

        ctx = AgentContext(
            user_id=user_id,
            session_id=session_id or str(uuid.uuid4()),
            initial_prompt=prompt,
            max_steps=max_steps,
            timeout_seconds=timeout,
        )

        if context:
            ctx.memory.update(context)

        ctx.state = AgentState.THINKING
        start_time = datetime.now()

        try:
            # Add initial message to conversation
            ctx.conversation.append({
                "role": "system",
                "content": self.system_prompt,
            })
            ctx.conversation.append({
                "role": "user",
                "content": prompt,
            })

            # Main agent loop
            while ctx.step_count < ctx.max_steps:
                # Check timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > ctx.timeout_seconds:
                    ctx.state = AgentState.ERROR
                    ctx.error = "Execution timeout"
                    break

                # Get next action from LLM
                action = await self._get_next_action(ctx)

                if action is None:
                    ctx.state = AgentState.ERROR
                    ctx.error = "Failed to determine next action"
                    break

                # Execute action
                step_start = datetime.now()
                result, error = await self._execute_action(ctx, action)
                duration = int((datetime.now() - step_start).total_seconds() * 1000)

                # Record step
                step = ctx.add_step(action, result, error, duration)
                await self._emit_step(ctx, step)

                # Check if complete
                if action.action_type == ActionType.COMPLETE:
                    ctx.state = AgentState.COMPLETED
                    ctx.final_response = action.content
                    break

                if action.action_type == ActionType.RESPOND:
                    ctx.state = AgentState.COMPLETED
                    ctx.final_response = action.content
                    break

                # Add result to conversation
                if result:
                    ctx.conversation.append({
                        "role": "assistant",
                        "content": f"Tool result: {str(result)[:500]}",
                    })

            # Emit completion
            await self._emit_complete(ctx)

        except Exception as e:
            logger.error(f"Agent loop error: {e}")
            ctx.state = AgentState.ERROR
            ctx.error = str(e)

        return ctx

    async def _get_next_action(self, ctx: AgentContext) -> Optional[AgentAction]:
        """
        Get the next action from the LLM.
        
        This is a simplified implementation. In production, you would
        use function calling or a more sophisticated prompting strategy.
        """
        if not self.llm_provider:
            # Without LLM, just respond with the prompt
            return AgentAction(
                action_type=ActionType.RESPOND,
                content=f"Received: {ctx.initial_prompt}",
            )

        try:
            # Call LLM to determine next action
            response = await self.llm_provider(ctx.conversation)

            # Parse response to determine action
            # This would typically use function calling or structured output
            return AgentAction(
                action_type=ActionType.RESPOND,
                content=response,
            )

        except Exception as e:
            logger.error(f"LLM call error: {e}")
            return None

    async def _execute_action(self, ctx: AgentContext, action: AgentAction) -> tuple[Any, Optional[str]]:
        """Execute an agent action."""
        ctx.state = AgentState.EXECUTING

        try:
            if action.action_type == ActionType.TOOL_CALL:
                # Execute tool
                tool = self.tools.get(action.tool_name)
                if not tool:
                    return None, f"Tool not found: {action.tool_name}"

                if asyncio.iscoroutinefunction(tool):
                    result = await tool(**action.tool_args)
                else:
                    result = tool(**action.tool_args)

                await self._emit_tool_call(ctx, action.tool_name, action.tool_args, result)
                return result, None

            elif action.action_type == ActionType.THINK:
                # Just record the thought
                return {"thought": action.content}, None

            elif action.action_type in [ActionType.RESPOND, ActionType.COMPLETE]:
                return {"response": action.content}, None

            elif action.action_type == ActionType.WAIT:
                # Wait for external input
                ctx.state = AgentState.WAITING
                return {"waiting": True}, None

            else:
                return None, f"Unknown action type: {action.action_type}"

        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return None, str(e)

    def register_tool(self, name: str, func: Callable) -> None:
        """Register a tool function."""
        self.tools[name] = func

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self.tools:
            del self.tools[name]
            return True
        return False


# Global instance
_agent_loop: Optional[AgentLoop] = None


def _get_llm_provider():
    """
    Get the LLM provider function using the new LLMProviderManager.
    Supports multiple providers: OpenAI, Google, Anthropic, OpenRouter, Ollama, Custom.
    """
    try:
        from .llm_providers import get_llm_manager
        
        manager = get_llm_manager()
        provider_func = manager.get_llm_provider_function()
        
        if provider_func:
            available = manager.list_available_providers()
            logger.info(f"LLM providers loaded: {available}")
            return provider_func
        
        logger.warning(
            "No LLM provider configured. Set one of: "
            "OPENAI_API_KEY, GOOGLE_GENERATIVE_AI_API_KEY, "
            "ANTHROPIC_API_KEY, OPENROUTER_API_KEY, or OLLAMA_ENABLED=true"
        )
        return None
        
    except Exception as e:
        logger.error(f"Failed to initialize LLM provider: {e}")
        return None


def _get_agent_tools() -> dict:
    """Get tools from skill manager."""
    try:
        from .skills import get_skill_manager
        manager = get_skill_manager()
        return manager.get_agent_tools()
    except Exception as e:
        logger.error(f"Failed to get agent tools: {e}")
        return {}


def _get_tools_description() -> str:
    """Get tools description for system prompt."""
    try:
        from .skills import get_skill_manager
        manager = get_skill_manager()
        return manager.get_agent_tools_description()
    except Exception:
        return ""


def get_agent_loop() -> AgentLoop:
    """Get the global AgentLoop instance with configured LLM provider and skills."""
    global _agent_loop
    if _agent_loop is None:
        # Get tools from skill manager
        tools = _get_agent_tools()
        tools_desc = _get_tools_description()
        
        system_prompt = f"""You are CursorBot, an intelligent AI assistant that helps with various tasks.

You have access to the following tools/skills:
{tools_desc if tools_desc else "No tools available"}

When given a task:
1. Analyze the request carefully
2. If you need to use a tool, specify which tool and parameters
3. Break down complex tasks into steps
4. Provide detailed, helpful responses
5. Use code examples when appropriate
6. Be concise but thorough

To use a tool, respond with:
[TOOL: tool_name]
{{parameters as JSON}}
[/TOOL]

Always respond in the same language as the user's input.
If the user writes in Chinese, respond in Chinese.
If the user writes in Traditional Chinese, respond in Traditional Chinese.
"""
        
        _agent_loop = AgentLoop(
            llm_provider=_get_llm_provider(),
            tools=tools,
            system_prompt=system_prompt,
        )
        
        if tools:
            logger.info(f"Agent Loop initialized with {len(tools)} tools: {list(tools.keys())}")
    
    return _agent_loop


def reset_agent_loop() -> None:
    """Reset the agent loop instance (useful after adding new skills)."""
    global _agent_loop
    _agent_loop = None
    logger.info("Agent Loop reset")


__all__ = [
    "AgentLoop",
    "AgentContext",
    "AgentAction",
    "AgentStep",
    "AgentState",
    "ActionType",
    "get_agent_loop",
]
