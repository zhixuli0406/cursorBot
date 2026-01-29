"""
Voice LLM Integration for CursorBot v1.1

Integrates voice assistant with LLM for:
- Natural conversation
- Context-aware responses
- Smart response generation
- Conversation flow management
- Multi-turn dialogue

Usage:
    from src.core.voice_llm import get_voice_llm
    
    llm = get_voice_llm()
    response = await llm.generate_response(utterance, context)
"""

import os
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..utils.logger import logger
from .voice_assistant import (
    VoiceAssistant, VoiceAssistantConfig, Utterance, Intent, 
    IntentCategory, AssistantResponse
)
from .voice_context import ContextEngine, FullContext, get_context_engine
from .voice_commands import CommandExecutor, CommandResult, get_command_executor
from .llm_providers import LLMProviderManager, get_llm_manager


# ============================================
# Enums
# ============================================

class ResponseStyle(Enum):
    """Response generation styles."""
    CONCISE = "concise"       # Short, direct
    FRIENDLY = "friendly"     # Warm, conversational
    PROFESSIONAL = "professional"  # Formal
    CASUAL = "casual"         # Relaxed
    ENTHUSIASTIC = "enthusiastic"  # Energetic


class ResponseType(Enum):
    """Types of responses."""
    ANSWER = "answer"         # Direct answer
    CONFIRMATION = "confirmation"  # Confirm action
    CLARIFICATION = "clarification"  # Ask for more info
    SUGGESTION = "suggestion"  # Offer suggestions
    ERROR = "error"           # Error response
    GREETING = "greeting"     # Greeting


# ============================================
# Data Classes
# ============================================

@dataclass
class VoiceLLMConfig:
    """Voice LLM configuration."""
    # Response settings
    default_style: ResponseStyle = ResponseStyle.FRIENDLY
    max_response_length: int = 200  # Characters for TTS
    language: str = "zh-TW"
    
    # System prompt
    assistant_name: str = "小助手"
    personality: str = "friendly and helpful"
    
    # Context settings
    include_time_context: bool = True
    include_location_context: bool = True
    include_activity_context: bool = True
    
    # Conversation settings
    max_history_turns: int = 10
    conversation_timeout: int = 300  # Seconds


@dataclass
class LLMResponse:
    """Response from LLM."""
    text: str
    response_type: ResponseType
    style: ResponseStyle
    suggestions: List[str] = field(default_factory=list)
    action_required: bool = False
    confidence: float = 1.0


# ============================================
# Voice LLM Integration
# ============================================

class VoiceLLM:
    """
    Integrates voice assistant with LLM.
    
    Provides:
    - Natural language understanding
    - Context-aware response generation
    - Multi-turn conversation management
    - Smart action execution
    """
    
    SYSTEM_PROMPT_TEMPLATE = """你是 {assistant_name}，一個{personality}的語音助手。

回應規則：
1. 回應要簡潔，適合語音朗讀（最多{max_length}字）
2. 使用{language}回應
3. 保持{style}的語氣
4. 如果需要執行動作，先確認再執行
5. 如果不確定用戶的意圖，禮貌地詢問

{context}

對話歷史：
{history}

用戶說：{user_input}

請直接回應用戶，不要包含任何標記或前綴。"""

    INTENT_PROMPT = """分析用戶的語音輸入，判斷意圖。

用戶說：{text}

請以 JSON 格式回應：
{{
  "intent": "question|command|control|search|reminder|calendar|code|chat",
  "action": "具體動作（如有）",
  "entities": {{}},
  "confidence": 0.0-1.0
}}"""

    def __init__(self, config: VoiceLLMConfig = None):
        self.config = config or VoiceLLMConfig()
        
        self._llm: Optional[LLMProviderManager] = None
        self._context_engine: Optional[ContextEngine] = None
        self._command_executor: Optional[CommandExecutor] = None
        
        # Conversation history
        self._history: List[Dict[str, str]] = []
    
    async def start(self) -> bool:
        """Initialize the Voice LLM."""
        try:
            self._llm = get_llm_manager()
            self._context_engine = get_context_engine()
            self._command_executor = get_command_executor()
            
            logger.info("Voice LLM initialized")
            return True
            
        except Exception as e:
            logger.error(f"Voice LLM init error: {e}")
            return False
    
    async def generate_response(
        self,
        utterance: Utterance,
        intent: Optional[Intent] = None,
        context: Optional[FullContext] = None
    ) -> LLMResponse:
        """
        Generate a response for the user's utterance.
        
        Args:
            utterance: User's spoken input
            intent: Recognized intent (optional, will be determined if not provided)
            context: Current context (optional, will be gathered if not provided)
            
        Returns:
            LLMResponse
        """
        if not self._llm:
            return LLMResponse(
                text="抱歉，我現在無法處理請求。",
                response_type=ResponseType.ERROR,
                style=self.config.default_style
            )
        
        # Get context if not provided
        if context is None and self._context_engine:
            context = await self._context_engine.get_current_context()
        
        # Determine intent if not provided
        if intent is None:
            intent = await self._analyze_intent(utterance.text)
        
        # Handle different intent types
        if intent and intent.category in [
            IntentCategory.COMMAND,
            IntentCategory.CONTROL,
            IntentCategory.CODE
        ]:
            # Execute command and generate confirmation
            result = await self._execute_command(intent)
            if result.response_text:
                response_text = result.response_text
            else:
                response_text = await self._generate_llm_response(
                    utterance.text, context, f"動作結果：{result.message}"
                )
        else:
            # Generate conversational response
            response_text = await self._generate_llm_response(
                utterance.text, context
            )
        
        # Update conversation history
        self._history.append({"role": "user", "content": utterance.text})
        self._history.append({"role": "assistant", "content": response_text})
        
        # Trim history
        if len(self._history) > self.config.max_history_turns * 2:
            self._history = self._history[-self.config.max_history_turns * 2:]
        
        # Update context engine
        if self._context_engine:
            self._context_engine.update_conversation(
                topic=utterance.text[:50],
                intent=intent.category.value if intent else None
            )
        
        # Get suggestions
        suggestions = []
        if self._context_engine and context:
            suggestions = self._context_engine.get_suggestions(context)
        
        return LLMResponse(
            text=response_text,
            response_type=self._determine_response_type(response_text, intent),
            style=self.config.default_style,
            suggestions=suggestions
        )
    
    async def _analyze_intent(self, text: str) -> Intent:
        """Analyze intent using LLM."""
        try:
            prompt = self.INTENT_PROMPT.format(text=text)
            
            result = await self._llm.generate(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3
            )
            
            import json
            data = json.loads(result)
            
            # Map string to IntentCategory
            intent_map = {
                "question": IntentCategory.QUESTION,
                "command": IntentCategory.COMMAND,
                "control": IntentCategory.CONTROL,
                "search": IntentCategory.SEARCH,
                "reminder": IntentCategory.REMINDER,
                "calendar": IntentCategory.CALENDAR,
                "code": IntentCategory.CODE,
                "chat": IntentCategory.CHAT,
            }
            
            return Intent(
                category=intent_map.get(data.get("intent", "chat"), IntentCategory.CHAT),
                action=data.get("action", ""),
                entities=data.get("entities", {}),
                confidence=data.get("confidence", 0.5),
                raw_text=text
            )
            
        except Exception as e:
            logger.debug(f"Intent analysis fallback: {e}")
            # Fallback to simple pattern matching
            from .voice_assistant import IntentRecognizer
            recognizer = IntentRecognizer(VoiceAssistantConfig())
            return await recognizer.recognize(text)
    
    async def _execute_command(self, intent: Intent) -> CommandResult:
        """Execute a command based on intent."""
        if not self._command_executor:
            return CommandResult(
                status=None,
                message="Command executor not available"
            )
        
        return await self._command_executor.execute(intent)
    
    async def _generate_llm_response(
        self,
        user_input: str,
        context: Optional[FullContext],
        extra_context: str = ""
    ) -> str:
        """Generate response using LLM."""
        # Build context string
        context_str = ""
        if context:
            context_parts = []
            
            if self.config.include_time_context:
                time_desc = self._format_time_context(context)
                if time_desc:
                    context_parts.append(time_desc)
            
            if self.config.include_activity_context and context.activity.current_app:
                context_parts.append(f"用戶正在使用 {context.activity.current_app}")
            
            if extra_context:
                context_parts.append(extra_context)
            
            context_str = "\n".join(context_parts)
        
        # Build history string
        history_str = ""
        for msg in self._history[-6:]:  # Last 3 turns
            role = "用戶" if msg["role"] == "user" else self.config.assistant_name
            history_str += f"{role}：{msg['content']}\n"
        
        # Build prompt
        prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
            assistant_name=self.config.assistant_name,
            personality=self.config.personality,
            max_length=self.config.max_response_length,
            language=self.config.language,
            style=self.config.default_style.value,
            context=context_str,
            history=history_str or "（這是對話開始）",
            user_input=user_input
        )
        
        try:
            response = await self._llm.generate(
                prompt=prompt,
                max_tokens=300,
                temperature=0.7
            )
            
            # Clean up response
            response = response.strip()
            
            # Ensure it's not too long for TTS
            if len(response) > self.config.max_response_length * 1.5:
                # Truncate at sentence boundary
                sentences = response.split("。")
                truncated = ""
                for sentence in sentences:
                    if len(truncated) + len(sentence) < self.config.max_response_length:
                        truncated += sentence + "。"
                    else:
                        break
                response = truncated or sentences[0] + "。"
            
            return response
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "抱歉，我遇到了一些問題，請再說一次。"
    
    def _format_time_context(self, context: FullContext) -> str:
        """Format time context for prompt."""
        time_ctx = context.time
        
        time_of_day_map = {
            "early_morning": "清晨",
            "morning": "上午",
            "afternoon": "下午",
            "evening": "傍晚",
            "night": "晚上",
            "late_night": "深夜",
        }
        
        day_map = {
            "weekday": "平日",
            "weekend": "週末",
        }
        
        tod = time_of_day_map.get(time_ctx.time_of_day.value, "")
        day = day_map.get(time_ctx.day_type.value, "")
        
        return f"現在是{day}{tod}"
    
    def _determine_response_type(
        self,
        response: str,
        intent: Optional[Intent]
    ) -> ResponseType:
        """Determine the type of response."""
        if intent:
            if intent.category in [IntentCategory.COMMAND, IntentCategory.CONTROL]:
                return ResponseType.CONFIRMATION
            elif intent.category == IntentCategory.QUESTION:
                return ResponseType.ANSWER
        
        # Check response content
        if any(q in response for q in ["嗎？", "呢？", "?", "請問", "是否"]):
            return ResponseType.CLARIFICATION
        elif any(s in response for s in ["建議", "可以試試", "或許"]):
            return ResponseType.SUGGESTION
        elif any(e in response for e in ["抱歉", "無法", "錯誤"]):
            return ResponseType.ERROR
        elif any(g in response for g in ["早安", "午安", "晚安", "你好"]):
            return ResponseType.GREETING
        
        return ResponseType.ANSWER
    
    # ============================================
    # Conversation Management
    # ============================================
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self._history.clear()
        if self._context_engine:
            self._context_engine.clear_conversation()
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self._history.copy()
    
    # ============================================
    # Special Responses
    # ============================================
    
    async def get_greeting(self) -> str:
        """Get a contextual greeting."""
        if self._context_engine:
            context = await self._context_engine.get_current_context()
            return self._context_engine.get_greeting(context)
        return "你好！"
    
    async def get_help_response(self) -> str:
        """Get help information."""
        commands = []
        if self._command_executor:
            commands = self._command_executor.get_available_commands()
        
        help_text = f"""我是{self.config.assistant_name}，我可以幫你：

{chr(10).join('• ' + cmd for cmd in commands)}

還有任何問題我都可以回答哦！"""
        
        return help_text
    
    async def get_status_response(self) -> str:
        """Get status information."""
        if self._context_engine:
            context = await self._context_engine.get_current_context()
            
            status_parts = [
                f"現在是{context.time.date.strftime('%H:%M')}",
            ]
            
            if context.device.battery_level:
                status_parts.append(f"電量{context.device.battery_level}%")
            
            if context.location.type.value != "unknown":
                status_parts.append(f"位置：{context.location.type.value}")
            
            return "，".join(status_parts) + "。"
        
        return "系統運作正常。"


# ============================================
# Integrated Voice Assistant
# ============================================

class IntegratedVoiceAssistant:
    """
    Fully integrated voice assistant.
    
    Combines:
    - VoiceAssistant (audio processing)
    - VoiceLLM (response generation)
    - ContextEngine (context awareness)
    - CommandExecutor (action execution)
    """
    
    def __init__(
        self,
        assistant_config: VoiceAssistantConfig = None,
        llm_config: VoiceLLMConfig = None
    ):
        self._assistant = VoiceAssistant(assistant_config)
        self._llm = VoiceLLM(llm_config)
        self._running = False
    
    async def start(self) -> bool:
        """Start the integrated assistant."""
        # Override the response generation
        original_generate = self._assistant._generate_response
        
        async def enhanced_generate(utterance: Utterance, intent: Optional[Intent]) -> str:
            response = await self._llm.generate_response(utterance, intent)
            return response.text
        
        self._assistant._generate_response = enhanced_generate
        
        # Start components
        if not await self._llm.start():
            logger.warning("LLM not available, using basic responses")
        
        if not await self._assistant.start():
            return False
        
        self._running = True
        return True
    
    async def stop(self) -> None:
        """Stop the integrated assistant."""
        await self._assistant.stop()
        self._running = False
    
    async def process_audio(self, audio: bytes) -> Optional[AssistantResponse]:
        """Process audio through the full pipeline."""
        return await self._assistant.process_audio(audio)
    
    def on_wake(self, handler) -> None:
        """Register wake event handler."""
        self._assistant.on_wake(handler)
    
    def on_response(self, handler) -> None:
        """Register response handler."""
        self._assistant.on_response(handler)
    
    @property
    def is_listening(self) -> bool:
        return self._assistant.is_listening
    
    @property
    def state(self):
        return self._assistant.state
    
    def get_stats(self) -> Dict[str, Any]:
        stats = self._assistant.get_stats()
        stats["llm_history_length"] = len(self._llm._history)
        return stats


# ============================================
# Global Instances
# ============================================

_voice_llm: Optional[VoiceLLM] = None
_integrated_assistant: Optional[IntegratedVoiceAssistant] = None


def get_voice_llm() -> VoiceLLM:
    """Get or create the global Voice LLM."""
    global _voice_llm
    if _voice_llm is None:
        _voice_llm = VoiceLLM()
    return _voice_llm


def get_integrated_assistant(
    assistant_config: VoiceAssistantConfig = None,
    llm_config: VoiceLLMConfig = None
) -> IntegratedVoiceAssistant:
    """Get or create the global integrated assistant."""
    global _integrated_assistant
    if _integrated_assistant is None:
        _integrated_assistant = IntegratedVoiceAssistant(
            assistant_config, llm_config
        )
    return _integrated_assistant


__all__ = [
    "ResponseStyle",
    "ResponseType",
    "VoiceLLMConfig",
    "LLMResponse",
    "VoiceLLM",
    "IntegratedVoiceAssistant",
    "get_voice_llm",
    "get_integrated_assistant",
]
