"""
Skills/Plugin System for CursorBot
Inspired by Clawd Bot's skills and plugin architecture

Provides extensible skill system for:
- Custom commands
- Tool integrations
- Automation scripts
- AI enhancements
- Agent Skills (for /agent and /ask)
"""

import importlib
import importlib.util
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from telegram import Update
from telegram.ext import ContextTypes

from ..utils.logger import logger

SKILLS_DIR = Path("skills")
AGENT_SKILLS_DIR = Path("skills/agent")


@dataclass
class SkillInfo:
    """Skill metadata."""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "unknown"
    enabled: bool = True
    commands: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    config: dict = field(default_factory=dict)


class Skill(ABC):
    """
    Base class for all skills.

    Implement this to create custom skills:

    class MySkill(Skill):
        @property
        def info(self) -> SkillInfo:
            return SkillInfo(
                name="my_skill",
                description="My custom skill",
                commands=["mycommand"],
            )

        async def execute(self, update, context, command, args):
            await update.message.reply_text("Hello from my skill!")
    """

    @property
    @abstractmethod
    def info(self) -> SkillInfo:
        """Return skill metadata."""
        pass

    @abstractmethod
    async def execute(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        command: str,
        args: list[str],
    ) -> Any:
        """Execute the skill."""
        pass

    async def on_load(self) -> None:
        """Called when skill is loaded."""
        pass

    async def on_unload(self) -> None:
        """Called when skill is unloaded."""
        pass

    def matches_trigger(self, text: str) -> bool:
        """Check if text matches any skill triggers."""
        text_lower = text.lower()
        for trigger in self.info.triggers:
            if trigger.lower() in text_lower:
                return True
        return False


# ============================================
# Agent Skills (for /agent and /ask)
# ============================================


@dataclass
class AgentSkillInfo:
    """Agent Skill metadata."""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "unknown"
    enabled: bool = True
    # Parameters the skill accepts
    parameters: dict = field(default_factory=dict)
    # Example usage
    examples: list[str] = field(default_factory=list)
    # Categories for organization
    categories: list[str] = field(default_factory=list)


class AgentSkill(ABC):
    """
    Base class for Agent Skills.
    
    Agent Skills are tools that can be used by the AI agent during
    /agent and /ask commands to perform specific tasks.
    
    Example:
        class WebSearchSkill(AgentSkill):
            @property
            def info(self) -> AgentSkillInfo:
                return AgentSkillInfo(
                    name="web_search",
                    description="Search the web for information",
                    parameters={"query": "Search query string"},
                    examples=["Search for Python tutorials"],
                )
            
            async def execute(self, **kwargs) -> dict:
                query = kwargs.get("query", "")
                # Perform web search
                return {"results": [...]}
    """
    
    @property
    @abstractmethod
    def info(self) -> AgentSkillInfo:
        """Return skill metadata."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """
        Execute the skill.
        
        Args:
            **kwargs: Skill-specific parameters
            
        Returns:
            dict with results
        """
        pass
    
    def get_tool_description(self) -> str:
        """Get description for AI tool calling."""
        info = self.info
        desc = f"{info.name}: {info.description}"
        if info.parameters:
            params = ", ".join(f"{k}={v}" for k, v in info.parameters.items())
            desc += f" Parameters: {params}"
        return desc
    
    async def on_load(self) -> None:
        """Called when skill is loaded."""
        pass
    
    async def on_unload(self) -> None:
        """Called when skill is unloaded."""
        pass


# ============================================
# Built-in Agent Skills
# ============================================


class WebSearchAgentSkill(AgentSkill):
    """Search the web for information."""
    
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="web_search",
            description="Search the web for current information",
            parameters={"query": "Search query"},
            examples=["Search for latest Python news", "Find React tutorials"],
            categories=["search", "web"],
        )
    
    async def execute(self, **kwargs) -> dict:
        query = kwargs.get("query", "")
        if not query:
            return {"error": "No query provided"}
        
        try:
            import httpx
            
            # Use DuckDuckGo instant answer API (no key needed)
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1}
                )
                data = response.json()
                
                results = []
                if data.get("Abstract"):
                    results.append({
                        "title": data.get("Heading", ""),
                        "content": data.get("Abstract"),
                        "url": data.get("AbstractURL", ""),
                    })
                
                for topic in data.get("RelatedTopics", [])[:5]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "title": topic.get("Text", "")[:50],
                            "content": topic.get("Text"),
                            "url": topic.get("FirstURL", ""),
                        })
                
                return {"query": query, "results": results}
                
        except Exception as e:
            return {"error": str(e)}


class CodeAnalysisAgentSkill(AgentSkill):
    """Analyze code for issues and suggestions."""
    
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="code_analysis",
            description="Analyze code for potential issues, complexity, and suggestions",
            parameters={"code": "Code to analyze", "language": "Programming language"},
            examples=["Analyze this Python function for bugs"],
            categories=["code", "analysis"],
        )
    
    async def execute(self, **kwargs) -> dict:
        code = kwargs.get("code", "")
        language = kwargs.get("language", "python")
        
        if not code:
            return {"error": "No code provided"}
        
        analysis = {
            "language": language,
            "lines": len(code.split("\n")),
            "characters": len(code),
            "suggestions": [],
        }
        
        # Basic analysis
        if language.lower() == "python":
            if "import *" in code:
                analysis["suggestions"].append("Avoid 'import *' - use explicit imports")
            if "except:" in code and "except Exception" not in code:
                analysis["suggestions"].append("Avoid bare 'except:' - catch specific exceptions")
            if "global " in code:
                analysis["suggestions"].append("Consider avoiding global variables")
            if len(code.split("\n")) > 50:
                analysis["suggestions"].append("Function is long - consider splitting")
        
        return analysis


class FileOperationAgentSkill(AgentSkill):
    """Read and analyze files."""
    
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="file_read",
            description="Read file contents from workspace",
            parameters={"path": "File path to read"},
            examples=["Read README.md", "Show contents of src/main.py"],
            categories=["file", "read"],
        )
    
    async def execute(self, **kwargs) -> dict:
        path = kwargs.get("path", "")
        if not path:
            return {"error": "No path provided"}
        
        try:
            from ..utils.config import settings
            
            # Get workspace path
            workspace = settings.effective_workspace_path
            if not workspace:
                workspace = os.getcwd()
            
            # Resolve path
            file_path = Path(workspace) / path
            if not file_path.exists():
                return {"error": f"File not found: {path}"}
            
            # Security check
            try:
                file_path.resolve().relative_to(Path(workspace).resolve())
            except ValueError:
                return {"error": "Access denied: path outside workspace"}
            
            # Read file
            content = file_path.read_text(encoding="utf-8", errors="replace")
            
            # Truncate if too long
            if len(content) > 10000:
                content = content[:10000] + "\n... (truncated)"
            
            return {
                "path": str(path),
                "content": content,
                "size": file_path.stat().st_size,
            }
            
        except Exception as e:
            return {"error": str(e)}


class CommandExecuteAgentSkill(AgentSkill):
    """Execute shell commands."""
    
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="execute_command",
            description="Execute shell command in workspace",
            parameters={"command": "Command to execute"},
            examples=["Run npm install", "Execute python script.py"],
            categories=["shell", "execute"],
        )
    
    async def execute(self, **kwargs) -> dict:
        command = kwargs.get("command", "")
        if not command:
            return {"error": "No command provided"}
        
        # Security: block dangerous commands
        dangerous = ["rm -rf /", "rm -rf /*", "dd if=", "mkfs", ":(){"]
        for d in dangerous:
            if d in command:
                return {"error": "Command blocked for security"}
        
        try:
            import asyncio
            from ..utils.config import settings
            
            workspace = settings.effective_workspace_path or os.getcwd()
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60,
            )
            
            return {
                "command": command,
                "exit_code": process.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:5000],
                "stderr": stderr.decode("utf-8", errors="replace")[:1000],
            }
            
        except asyncio.TimeoutError:
            return {"error": "Command timed out"}
        except Exception as e:
            return {"error": str(e)}


class UrlFetchAgentSkill(AgentSkill):
    """Fetch content from URLs."""
    
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="url_fetch",
            description="Fetch and extract content from a URL",
            parameters={"url": "URL to fetch"},
            examples=["Fetch https://example.com", "Get content from API"],
            categories=["web", "fetch"],
        )
    
    async def execute(self, **kwargs) -> dict:
        url = kwargs.get("url", "")
        if not url:
            return {"error": "No URL provided"}
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url)
                
                content_type = response.headers.get("content-type", "")
                
                if "application/json" in content_type:
                    return {
                        "url": url,
                        "status": response.status_code,
                        "type": "json",
                        "content": response.json(),
                    }
                else:
                    text = response.text[:10000]
                    # Try to extract main content (simple approach)
                    if "<body" in text.lower():
                        import re
                        # Remove scripts and styles
                        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
                        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
                        # Remove HTML tags
                        text = re.sub(r"<[^>]+>", " ", text)
                        # Clean whitespace
                        text = " ".join(text.split())
                    
                    return {
                        "url": url,
                        "status": response.status_code,
                        "type": "text",
                        "content": text[:5000],
                    }
                    
        except Exception as e:
            return {"error": str(e)}


# ============================================
# Built-in Skills (Telegram Commands)
# ============================================


class TranslateSkill(Skill):
    """Skill for text translation."""

    @property
    def info(self) -> SkillInfo:
        return SkillInfo(
            name="translate",
            description="Translate text between languages",
            commands=["translate", "tr"],
            triggers=["translate", "翻譯"],
        )

    async def execute(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        command: str,
        args: list[str],
    ) -> Any:
        if not args:
            await update.message.reply_text(
                "💬 <b>翻譯技能</b>\n\n"
                "用法: /translate [目標語言] [文字]\n"
                "範例: /translate en 你好世界",
                parse_mode="HTML",
            )
            return

        # Parse target language and text
        target_lang = args[0] if len(args) > 1 else "en"
        text = " ".join(args[1:]) if len(args) > 1 else args[0]

        # This would integrate with translation API
        await update.message.reply_text(
            f"🌐 翻譯功能需要設定翻譯 API\n"
            f"目標語言: {target_lang}\n"
            f"原文: {text}",
            parse_mode="HTML",
        )


class SummarizeSkill(Skill):
    """Skill for text summarization."""

    @property
    def info(self) -> SkillInfo:
        return SkillInfo(
            name="summarize",
            description="Summarize long text or URLs",
            commands=["summarize", "sum"],
            triggers=["summarize", "摘要"],
        )

    async def execute(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        command: str,
        args: list[str],
    ) -> Any:
        if not args:
            await update.message.reply_text(
                "📝 <b>摘要技能</b>\n\n"
                "用法: /summarize [文字或URL]\n"
                "範例: /summarize https://example.com/article",
                parse_mode="HTML",
            )
            return

        text = " ".join(args)

        await update.message.reply_text(
            f"📝 摘要功能需要整合 AI API\n"
            f"輸入: {text[:100]}...",
            parse_mode="HTML",
        )


class CalculatorSkill(Skill):
    """Skill for calculations."""

    @property
    def info(self) -> SkillInfo:
        return SkillInfo(
            name="calculator",
            description="Perform calculations",
            commands=["calc", "calculate"],
            triggers=["calculate", "計算"],
        )

    async def execute(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        command: str,
        args: list[str],
    ) -> Any:
        if not args:
            await update.message.reply_text(
                "🔢 <b>計算機技能</b>\n\n"
                "用法: /calc [表達式]\n"
                "範例: /calc 2 + 2 * 3",
                parse_mode="HTML",
            )
            return

        expression = " ".join(args)

        try:
            # Safe eval using ast
            import ast
            import operator

            operators = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }

            def eval_expr(node):
                if isinstance(node, ast.Constant):
                    return node.value
                elif isinstance(node, ast.BinOp):
                    return operators[type(node.op)](
                        eval_expr(node.left),
                        eval_expr(node.right)
                    )
                elif isinstance(node, ast.UnaryOp):
                    return operators[type(node.op)](eval_expr(node.operand))
                else:
                    raise TypeError(f"Unsupported type: {type(node)}")

            tree = ast.parse(expression, mode='eval')
            result = eval_expr(tree.body)

            await update.message.reply_text(
                f"🔢 <b>計算結果</b>\n\n"
                f"<code>{expression}</code> = <b>{result}</b>",
                parse_mode="HTML",
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ 計算錯誤: {str(e)[:100]}"
            )


class ReminderSkill(Skill):
    """Skill for setting reminders."""

    @property
    def info(self) -> SkillInfo:
        return SkillInfo(
            name="reminder",
            description="Set reminders",
            commands=["remind", "reminder"],
            triggers=["remind me", "提醒我"],
        )

    async def execute(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        command: str,
        args: list[str],
    ) -> Any:
        if not args:
            await update.message.reply_text(
                "⏰ <b>提醒技能</b>\n\n"
                "用法: /remind [時間] [內容]\n"
                "範例: /remind 5m 檢查代碼\n"
                "時間格式: 5s, 5m, 5h, 5d",
                parse_mode="HTML",
            )
            return

        # Parse time and message
        time_str = args[0]
        message = " ".join(args[1:]) if len(args) > 1 else "提醒"

        # Parse time
        import re
        match = re.match(r"(\d+)([smhd])", time_str)
        if not match:
            await update.message.reply_text("❌ 無效的時間格式")
            return

        amount = int(match.group(1))
        unit = match.group(2)
        seconds = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
        }.get(unit, 60) * amount

        # Schedule reminder
        import asyncio

        async def send_reminder():
            await asyncio.sleep(seconds)
            await update.effective_chat.send_message(
                f"⏰ <b>提醒</b>\n\n{message}",
                parse_mode="HTML",
            )

        asyncio.create_task(send_reminder())

        await update.message.reply_text(
            f"✅ 已設定提醒\n"
            f"時間: {time_str}\n"
            f"內容: {message}",
        )


# ============================================
# Skill Manager
# ============================================


class SkillManager:
    """
    Manages skill loading, registration, and execution.
    Supports both Telegram command skills and Agent skills.
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._command_map: dict[str, str] = {}  # command -> skill_name
        self._agent_skills: dict[str, AgentSkill] = {}

    async def load_builtin_skills(self) -> None:
        """Load built-in skills."""
        # Telegram command skills
        builtin_skills = [
            TranslateSkill(),
            SummarizeSkill(),
            CalculatorSkill(),
            ReminderSkill(),
        ]

        for skill in builtin_skills:
            await self.register_skill(skill)

        logger.info(f"Loaded {len(builtin_skills)} built-in command skills")
        
        # Agent skills
        await self.load_builtin_agent_skills()
    
    async def load_builtin_agent_skills(self) -> None:
        """Load built-in agent skills."""
        builtin_agent_skills = [
            WebSearchAgentSkill(),
            CodeAnalysisAgentSkill(),
            FileOperationAgentSkill(),
            CommandExecuteAgentSkill(),
            UrlFetchAgentSkill(),
        ]
        
        for skill in builtin_agent_skills:
            await self.register_agent_skill(skill)
        
        logger.info(f"Loaded {len(builtin_agent_skills)} built-in agent skills")
        
        # Load external agent skills from skills/agent directory
        external_count = await self.load_external_agent_skills(AGENT_SKILLS_DIR)
        if external_count > 0:
            logger.info(f"Loaded {external_count} external agent skills")
    
    # ============================================
    # Agent Skill Management
    # ============================================
    
    async def register_agent_skill(self, skill: AgentSkill) -> bool:
        """Register an agent skill."""
        info = skill.info
        
        if info.name in self._agent_skills:
            logger.warning(f"Agent skill {info.name} already registered")
            return False
        
        self._agent_skills[info.name] = skill
        await skill.on_load()
        logger.info(f"Registered agent skill: {info.name}")
        return True
    
    async def unregister_agent_skill(self, name: str) -> bool:
        """Unregister an agent skill."""
        skill = self._agent_skills.pop(name, None)
        if not skill:
            return False
        
        await skill.on_unload()
        logger.info(f"Unregistered agent skill: {name}")
        return True
    
    def get_agent_skill(self, name: str) -> Optional[AgentSkill]:
        """Get an agent skill by name."""
        return self._agent_skills.get(name)
    
    def list_agent_skills(self) -> list[AgentSkillInfo]:
        """List all registered agent skills."""
        return [skill.info for skill in self._agent_skills.values()]
    
    def get_agent_tools(self) -> dict[str, Callable]:
        """
        Get all agent skills as callable tools.
        For use with AgentLoop.
        """
        tools = {}
        for name, skill in self._agent_skills.items():
            if skill.info.enabled:
                tools[name] = skill.execute
        return tools
    
    def get_agent_tools_description(self) -> str:
        """Get description of all agent tools for AI prompting."""
        descriptions = []
        for skill in self._agent_skills.values():
            if skill.info.enabled:
                descriptions.append(skill.get_tool_description())
        return "\n".join(descriptions)
    
    async def execute_agent_skill(self, name: str, **kwargs) -> dict:
        """Execute an agent skill."""
        skill = self._agent_skills.get(name)
        if not skill or not skill.info.enabled:
            return {"error": f"Agent skill not found: {name}"}
        
        try:
            return await skill.execute(**kwargs)
        except Exception as e:
            logger.error(f"Agent skill {name} error: {e}")
            return {"error": str(e)}
    
    async def load_external_agent_skills(self, skills_dir: Path = AGENT_SKILLS_DIR) -> int:
        """
        Load external agent skill modules from directory.
        
        Supports multiple formats:
        1. Python files with AgentSkill subclasses
        2. JSON skill definition files (*.skill.json)
        3. YAML skill definition files (*.skill.yaml, *.skill.yml)
        4. Subdirectories with skill.json/skill.yaml config
        5. Auto-wrapping of Python scripts as skills
        
        The loader recursively scans the directory and automatically
        detects and loads skills in any supported format.
        """
        if not skills_dir.exists():
            skills_dir.mkdir(parents=True, exist_ok=True)
            return 0
        
        loaded = 0
        
        # 1. Load Python files with AgentSkill classes
        loaded += await self._load_python_skills(skills_dir)
        
        # 2. Load JSON/YAML skill definitions
        loaded += await self._load_config_skills(skills_dir)
        
        # 3. Scan subdirectories for skill packages
        loaded += await self._load_skill_packages(skills_dir)
        
        return loaded
    
    async def _load_python_skills(self, skills_dir: Path) -> int:
        """Load Python files containing AgentSkill subclasses."""
        loaded = 0
        
        for skill_file in skills_dir.glob("*.py"):
            if skill_file.name.startswith("_"):
                continue
            
            try:
                loaded += await self._load_python_skill_file(skill_file)
            except Exception as e:
                logger.error(f"Failed to load Python skill {skill_file}: {e}")
        
        return loaded
    
    async def _load_python_skill_file(self, skill_file: Path) -> int:
        """Load a single Python skill file."""
        loaded = 0
        
        try:
            spec = importlib.util.spec_from_file_location(
                skill_file.stem, skill_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for AgentSkill subclasses
            found_skill = False
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, AgentSkill)
                    and attr is not AgentSkill
                ):
                    skill = attr()
                    if await self.register_agent_skill(skill):
                        loaded += 1
                        found_skill = True
            
            # If no AgentSkill class found, try to auto-wrap as a simple skill
            if not found_skill:
                loaded += await self._auto_wrap_python_module(module, skill_file)
                
        except Exception as e:
            logger.error(f"Error loading {skill_file}: {e}")
        
        return loaded
    
    async def _auto_wrap_python_module(self, module, skill_file: Path) -> int:
        """
        Auto-wrap a Python module as an AgentSkill.
        
        Looks for:
        - SKILL_INFO dict with metadata
        - execute() or run() or main() async function
        """
        loaded = 0
        
        # Check for SKILL_INFO metadata
        skill_info = getattr(module, "SKILL_INFO", None)
        if not skill_info or not isinstance(skill_info, dict):
            return 0
        
        # Look for execute function
        execute_func = None
        for func_name in ["execute", "run", "main"]:
            func = getattr(module, func_name, None)
            if callable(func):
                execute_func = func
                break
        
        if not execute_func:
            return 0
        
        # Create dynamic AgentSkill
        skill = self._create_dynamic_skill(skill_info, execute_func, skill_file.stem)
        if skill and await self.register_agent_skill(skill):
            loaded += 1
            logger.info(f"Auto-wrapped skill from {skill_file.name}")
        
        return loaded
    
    def _create_dynamic_skill(self, info: dict, execute_func: Callable, default_name: str) -> Optional[AgentSkill]:
        """Create a dynamic AgentSkill from metadata and function."""
        
        class DynamicAgentSkill(AgentSkill):
            def __init__(self, skill_info: dict, exec_func: Callable, name: str):
                self._info = AgentSkillInfo(
                    name=skill_info.get("name", name),
                    description=skill_info.get("description", f"Skill from {name}"),
                    version=skill_info.get("version", "1.0.0"),
                    author=skill_info.get("author", "unknown"),
                    enabled=skill_info.get("enabled", True),
                    parameters=skill_info.get("parameters", {}),
                    examples=skill_info.get("examples", []),
                    categories=skill_info.get("categories", []),
                )
                self._execute_func = exec_func
            
            @property
            def info(self) -> AgentSkillInfo:
                return self._info
            
            async def execute(self, **kwargs) -> dict:
                import asyncio
                import inspect
                
                try:
                    if inspect.iscoroutinefunction(self._execute_func):
                        return await self._execute_func(**kwargs)
                    else:
                        # Run sync function in executor
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(
                            None, lambda: self._execute_func(**kwargs)
                        )
                except Exception as e:
                    return {"error": str(e)}
        
        return DynamicAgentSkill(info, execute_func, default_name)
    
    async def _load_config_skills(self, skills_dir: Path) -> int:
        """Load skills from JSON/YAML configuration files."""
        loaded = 0
        
        # Load *.skill.json files
        for config_file in skills_dir.glob("*.skill.json"):
            try:
                loaded += await self._load_json_skill(config_file)
            except Exception as e:
                logger.error(f"Failed to load JSON skill {config_file}: {e}")
        
        # Load *.skill.yaml and *.skill.yml files
        for pattern in ["*.skill.yaml", "*.skill.yml"]:
            for config_file in skills_dir.glob(pattern):
                try:
                    loaded += await self._load_yaml_skill(config_file)
                except Exception as e:
                    logger.error(f"Failed to load YAML skill {config_file}: {e}")
        
        return loaded
    
    async def _load_json_skill(self, config_file: Path) -> int:
        """Load a skill from JSON configuration."""
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        return await self._load_skill_from_config(config, config_file)
    
    async def _load_yaml_skill(self, config_file: Path) -> int:
        """Load a skill from YAML configuration."""
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed, skipping YAML skills")
            return 0
        
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        return await self._load_skill_from_config(config, config_file)
    
    async def _load_skill_from_config(self, config: dict, config_file: Path) -> int:
        """Create and register a skill from configuration dict."""
        if not config:
            return 0
        
        skill_type = config.get("type", "script")
        
        if skill_type == "script":
            return await self._create_script_skill(config, config_file)
        elif skill_type == "http":
            return await self._create_http_skill(config, config_file)
        elif skill_type == "command":
            return await self._create_command_skill(config, config_file)
        else:
            logger.warning(f"Unknown skill type: {skill_type} in {config_file}")
            return 0
    
    async def _create_script_skill(self, config: dict, config_file: Path) -> int:
        """Create a skill that executes a script."""
        script = config.get("script")
        if not script:
            return 0
        
        # Resolve script path relative to config file
        script_path = config_file.parent / script
        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            return 0
        
        class ScriptAgentSkill(AgentSkill):
            def __init__(self, cfg: dict, script_file: Path):
                self._config = cfg
                self._script_path = script_file
                self._info = AgentSkillInfo(
                    name=cfg.get("name", script_file.stem),
                    description=cfg.get("description", f"Execute {script_file.name}"),
                    version=cfg.get("version", "1.0.0"),
                    author=cfg.get("author", "unknown"),
                    enabled=cfg.get("enabled", True),
                    parameters=cfg.get("parameters", {}),
                    examples=cfg.get("examples", []),
                    categories=cfg.get("categories", []),
                )
            
            @property
            def info(self) -> AgentSkillInfo:
                return self._info
            
            async def execute(self, **kwargs) -> dict:
                import asyncio
                import shlex
                
                # Build command
                interpreter = self._config.get("interpreter", "python3")
                cmd = f"{interpreter} {shlex.quote(str(self._script_path))}"
                
                # Add arguments
                for key, value in kwargs.items():
                    if value is not None:
                        cmd += f" --{key}={shlex.quote(str(value))}"
                
                try:
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=str(self._script_path.parent),
                    )
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self._config.get("timeout", 60),
                    )
                    
                    return {
                        "exit_code": process.returncode,
                        "stdout": stdout.decode("utf-8", errors="replace"),
                        "stderr": stderr.decode("utf-8", errors="replace"),
                    }
                except asyncio.TimeoutError:
                    return {"error": "Script execution timed out"}
                except Exception as e:
                    return {"error": str(e)}
        
        skill = ScriptAgentSkill(config, script_path)
        if await self.register_agent_skill(skill):
            return 1
        return 0
    
    async def _create_http_skill(self, config: dict, config_file: Path) -> int:
        """Create a skill that calls an HTTP endpoint."""
        url = config.get("url")
        if not url:
            return 0
        
        class HttpAgentSkill(AgentSkill):
            def __init__(self, cfg: dict):
                self._config = cfg
                self._info = AgentSkillInfo(
                    name=cfg.get("name", "http_skill"),
                    description=cfg.get("description", f"Call {cfg.get('url')}"),
                    version=cfg.get("version", "1.0.0"),
                    author=cfg.get("author", "unknown"),
                    enabled=cfg.get("enabled", True),
                    parameters=cfg.get("parameters", {}),
                    examples=cfg.get("examples", []),
                    categories=cfg.get("categories", ["http"]),
                )
            
            @property
            def info(self) -> AgentSkillInfo:
                return self._info
            
            async def execute(self, **kwargs) -> dict:
                import httpx
                
                url = self._config.get("url")
                method = self._config.get("method", "POST").upper()
                headers = self._config.get("headers", {})
                timeout = self._config.get("timeout", 30)
                
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        if method == "GET":
                            response = await client.get(url, params=kwargs, headers=headers)
                        else:
                            response = await client.post(url, json=kwargs, headers=headers)
                        
                        return {
                            "status_code": response.status_code,
                            "response": response.json() if "application/json" in response.headers.get("content-type", "") else response.text,
                        }
                except Exception as e:
                    return {"error": str(e)}
        
        skill = HttpAgentSkill(config)
        if await self.register_agent_skill(skill):
            return 1
        return 0
    
    async def _create_command_skill(self, config: dict, config_file: Path) -> int:
        """Create a skill that executes a shell command."""
        command = config.get("command")
        if not command:
            return 0
        
        class CommandAgentSkill(AgentSkill):
            def __init__(self, cfg: dict):
                self._config = cfg
                self._info = AgentSkillInfo(
                    name=cfg.get("name", "command_skill"),
                    description=cfg.get("description", f"Execute: {cfg.get('command')}"),
                    version=cfg.get("version", "1.0.0"),
                    author=cfg.get("author", "unknown"),
                    enabled=cfg.get("enabled", True),
                    parameters=cfg.get("parameters", {}),
                    examples=cfg.get("examples", []),
                    categories=cfg.get("categories", ["shell"]),
                )
            
            @property
            def info(self) -> AgentSkillInfo:
                return self._info
            
            async def execute(self, **kwargs) -> dict:
                import asyncio
                
                command = self._config.get("command")
                
                # Replace placeholders in command
                for key, value in kwargs.items():
                    command = command.replace(f"{{{key}}}", str(value))
                    command = command.replace(f"${key}", str(value))
                
                try:
                    process = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self._config.get("timeout", 60),
                    )
                    
                    return {
                        "exit_code": process.returncode,
                        "stdout": stdout.decode("utf-8", errors="replace"),
                        "stderr": stderr.decode("utf-8", errors="replace"),
                    }
                except asyncio.TimeoutError:
                    return {"error": "Command execution timed out"}
                except Exception as e:
                    return {"error": str(e)}
        
        skill = CommandAgentSkill(config)
        if await self.register_agent_skill(skill):
            return 1
        return 0
    
    async def _load_skill_packages(self, skills_dir: Path) -> int:
        """Load skill packages from subdirectories."""
        loaded = 0
        
        for subdir in skills_dir.iterdir():
            if not subdir.is_dir():
                continue
            if subdir.name.startswith("_") or subdir.name.startswith("."):
                continue
            
            # Check for skill.json or skill.yaml
            config_file = None
            for config_name in ["skill.json", "skill.yaml", "skill.yml"]:
                potential = subdir / config_name
                if potential.exists():
                    config_file = potential
                    break
            
            if config_file:
                try:
                    if config_file.suffix == ".json":
                        loaded += await self._load_json_skill(config_file)
                    else:
                        loaded += await self._load_yaml_skill(config_file)
                except Exception as e:
                    logger.error(f"Failed to load skill package {subdir}: {e}")
            else:
                # Recursively scan subdirectory for Python skills
                loaded += await self._load_python_skills(subdir)
        
        return loaded

    async def register_skill(self, skill: Skill) -> bool:
        """
        Register a skill.

        Args:
            skill: Skill instance

        Returns:
            True if registered successfully
        """
        info = skill.info

        if info.name in self._skills:
            logger.warning(f"Skill {info.name} already registered")
            return False

        self._skills[info.name] = skill

        # Map commands to skill
        for cmd in info.commands:
            self._command_map[cmd] = info.name

        await skill.on_load()
        logger.info(f"Registered skill: {info.name}")
        return True

    async def unregister_skill(self, name: str) -> bool:
        """
        Unregister a skill.

        Args:
            name: Skill name

        Returns:
            True if unregistered successfully
        """
        skill = self._skills.pop(name, None)
        if not skill:
            return False

        # Remove command mappings
        info = skill.info
        for cmd in info.commands:
            self._command_map.pop(cmd, None)

        await skill.on_unload()
        logger.info(f"Unregistered skill: {name}")
        return True

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self._skills.get(name)

    def get_skill_by_command(self, command: str) -> Optional[Skill]:
        """Get a skill by command."""
        skill_name = self._command_map.get(command)
        if skill_name:
            return self._skills.get(skill_name)
        return None

    def find_skill_by_trigger(self, text: str) -> Optional[Skill]:
        """Find a skill that matches the text trigger."""
        for skill in self._skills.values():
            if skill.info.enabled and skill.matches_trigger(text):
                return skill
        return None

    async def execute_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        command: str,
        args: list[str],
    ) -> bool:
        """
        Execute a skill command.

        Returns:
            True if a skill handled the command
        """
        skill = self.get_skill_by_command(command)
        if not skill or not skill.info.enabled:
            return False

        try:
            await skill.execute(update, context, command, args)
            return True
        except Exception as e:
            logger.error(f"Skill {skill.info.name} error: {e}")
            await update.message.reply_text(f"❌ 技能執行錯誤: {str(e)[:100]}")
            return True

    def list_skills(self) -> list[SkillInfo]:
        """List all registered skills."""
        return [skill.info for skill in self._skills.values()]

    def list_commands(self) -> dict[str, str]:
        """List all skill commands with descriptions."""
        result = {}
        for skill in self._skills.values():
            if skill.info.enabled:
                for cmd in skill.info.commands:
                    result[cmd] = skill.info.description
        return result

    async def load_external_skills(self, skills_dir: Path = SKILLS_DIR) -> int:
        """
        Load external skill modules from directory.

        Args:
            skills_dir: Directory containing skill modules

        Returns:
            Number of skills loaded
        """
        if not skills_dir.exists():
            skills_dir.mkdir(parents=True, exist_ok=True)
            return 0

        loaded = 0

        for skill_file in skills_dir.glob("*.py"):
            if skill_file.name.startswith("_"):
                continue

            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(
                    skill_file.stem, skill_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find Skill subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Skill)
                        and attr is not Skill
                    ):
                        skill = attr()
                        if await self.register_skill(skill):
                            loaded += 1

            except Exception as e:
                logger.error(f"Failed to load skill {skill_file}: {e}")

        return loaded


# Global instance
_skill_manager: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    """Get the global SkillManager instance."""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager


__all__ = [
    # Base classes
    "Skill",
    "SkillInfo",
    "AgentSkill",
    "AgentSkillInfo",
    # Manager
    "SkillManager",
    "get_skill_manager",
    # Built-in command skills
    "TranslateSkill",
    "SummarizeSkill",
    "CalculatorSkill",
    "ReminderSkill",
    # Built-in agent skills
    "WebSearchAgentSkill",
    "CodeAnalysisAgentSkill",
    "FileOperationAgentSkill",
    "CommandExecuteAgentSkill",
    "UrlFetchAgentSkill",
]
