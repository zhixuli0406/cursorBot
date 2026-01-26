"""
Skills/Plugin System for CursorBot
Inspired by Clawd Bot's skills and plugin architecture

Provides extensible skill system for:
- Custom commands
- Tool integrations
- Automation scripts
- AI enhancements
"""

import importlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from telegram import Update
from telegram.ext import ContextTypes

from ..utils.logger import logger

SKILLS_DIR = Path("skills")


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
# Built-in Skills
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
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._command_map: dict[str, str] = {}  # command -> skill_name

    async def load_builtin_skills(self) -> None:
        """Load built-in skills."""
        builtin_skills = [
            TranslateSkill(),
            SummarizeSkill(),
            CalculatorSkill(),
            ReminderSkill(),
        ]

        for skill in builtin_skills:
            await self.register_skill(skill)

        logger.info(f"Loaded {len(builtin_skills)} built-in skills")

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
    "Skill",
    "SkillInfo",
    "SkillManager",
    "get_skill_manager",
    # Built-in skills
    "TranslateSkill",
    "SummarizeSkill",
    "CalculatorSkill",
    "ReminderSkill",
]
