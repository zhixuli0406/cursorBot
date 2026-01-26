"""
LLM Provider System for CursorBot

Supports multiple AI providers:
- OpenAI (GPT-4, GPT-3.5, etc.)
- Google (Gemini)
- Anthropic (Claude)
- OpenRouter (proxy to multiple models)
- Ollama (local models)
- Custom OpenAI-compatible endpoints

Configuration is done via environment variables.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class ProviderType(Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class ModelInfo:
    """Information about an AI model."""
    provider: ProviderType
    model_id: str
    display_name: str
    description: str = ""
    max_tokens: int = 4096
    supports_vision: bool = False
    supports_functions: bool = False
    is_free: bool = False


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    provider_type: ProviderType
    api_key: str = ""
    api_base: str = ""
    model: str = ""
    enabled: bool = False
    timeout: int = 120
    max_tokens: int = 4096
    temperature: float = 0.7
    extra: dict = field(default_factory=dict)


class LLMProvider(ABC):
    """Base class for LLM providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type."""
        pass
    
    @abstractmethod
    async def generate(self, messages: list[dict], **kwargs) -> str:
        """Generate a response from the LLM."""
        pass
    
    def is_available(self) -> bool:
        """Check if this provider is properly configured."""
        return bool(self.config.api_key) and self.config.enabled


# ============================================
# OpenAI Provider
# ============================================

class OpenAIProvider(LLMProvider):
    """OpenAI GPT models provider."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI
    
    async def generate(self, messages: list[dict], **kwargs) -> str:
        import httpx
        
        api_key = self.config.api_key
        api_base = self.config.api_base or "https://api.openai.com/v1"
        model = kwargs.get("model") or self.config.model or "gpt-4o-mini"
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                        "temperature": kwargs.get("temperature", self.config.temperature),
                    },
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    raise ValueError(f"OpenAI API error: {response.status_code}")
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except httpx.TimeoutException:
            raise ValueError("OpenAI API timeout")
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


# ============================================
# Google Gemini Provider
# ============================================

class GoogleProvider(LLMProvider):
    """Google Gemini models provider."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GOOGLE
    
    async def generate(self, messages: list[dict], **kwargs) -> str:
        api_key = self.config.api_key
        model_name = kwargs.get("model") or self.config.model or "gemini-2.0-flash"
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=api_key)
            
            # Try specified model first, then fallbacks
            model_names = [model_name, "gemini-2.0-flash", "gemini-1.5-pro", "gemini-pro"]
            model = None
            
            for name in model_names:
                try:
                    model = genai.GenerativeModel(name)
                    if name != model_name:
                        logger.info(f"Using fallback Gemini model: {name}")
                    break
                except Exception:
                    continue
            
            if model is None:
                raise ValueError("No available Gemini model found")
            
            # Convert to Gemini format
            prompt_parts = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    prompt_parts.append(f"[System Instructions]\n{content}\n")
                elif role == "user":
                    prompt_parts.append(f"[User]\n{content}\n")
                elif role == "assistant":
                    prompt_parts.append(f"[Assistant]\n{content}\n")
            
            prompt_parts.append("[Assistant]\n")
            full_prompt = "\n".join(prompt_parts)
            
            # Run sync API in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(full_prompt)
            )
            
            return response.text
            
        except ImportError:
            raise ValueError("google-generativeai package not installed. Run: pip install google-generativeai")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise


# ============================================
# Anthropic Claude Provider
# ============================================

class AnthropicProvider(LLMProvider):
    """Anthropic Claude models provider."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC
    
    async def generate(self, messages: list[dict], **kwargs) -> str:
        import httpx
        
        api_key = self.config.api_key
        api_base = self.config.api_base or "https://api.anthropic.com/v1"
        model = kwargs.get("model") or self.config.model or "claude-3-5-sonnet-20241022"
        
        # Extract system message
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_content += msg.get("content", "") + "\n"
            else:
                chat_messages.append(msg)
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                payload = {
                    "model": model,
                    "messages": chat_messages,
                    "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                }
                if system_content:
                    payload["system"] = system_content.strip()
                
                response = await client.post(
                    f"{api_base}/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                
                if response.status_code != 200:
                    logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
                    raise ValueError(f"Anthropic API error: {response.status_code}")
                
                result = response.json()
                return result["content"][0]["text"]
                
        except httpx.TimeoutException:
            raise ValueError("Anthropic API timeout")
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


# ============================================
# OpenRouter Provider
# ============================================

class OpenRouterProvider(LLMProvider):
    """OpenRouter proxy provider (access to multiple models)."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENROUTER
    
    async def generate(self, messages: list[dict], **kwargs) -> str:
        import httpx
        
        api_key = self.config.api_key
        model = kwargs.get("model") or self.config.model or "google/gemini-2.0-flash-exp:free"
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/cursorbot",
                        "X-Title": "CursorBot",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                        "temperature": kwargs.get("temperature", self.config.temperature),
                    },
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                    raise ValueError(f"OpenRouter API error: {response.status_code}")
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except httpx.TimeoutException:
            raise ValueError("OpenRouter API timeout")
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            raise


# ============================================
# Ollama Provider (Local Models)
# ============================================

class OllamaProvider(LLMProvider):
    """Ollama local models provider."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA
    
    async def generate(self, messages: list[dict], **kwargs) -> str:
        import httpx
        
        api_base = self.config.api_base or "http://localhost:11434"
        model = kwargs.get("model") or self.config.model or "llama3.2"
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{api_base}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": kwargs.get("temperature", self.config.temperature),
                        },
                    },
                )
                
                if response.status_code != 200:
                    logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                    raise ValueError(f"Ollama API error: {response.status_code}")
                
                result = response.json()
                return result["message"]["content"]
                
        except httpx.ConnectError:
            raise ValueError(f"Cannot connect to Ollama at {api_base}. Is Ollama running?")
        except httpx.TimeoutException:
            raise ValueError("Ollama API timeout")
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise


# ============================================
# Custom OpenAI-Compatible Provider
# ============================================

class CustomProvider(LLMProvider):
    """Custom OpenAI-compatible endpoint provider."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.CUSTOM
    
    async def generate(self, messages: list[dict], **kwargs) -> str:
        import httpx
        
        api_key = self.config.api_key
        api_base = self.config.api_base
        model = kwargs.get("model") or self.config.model
        
        if not api_base:
            raise ValueError("CUSTOM_API_BASE not configured")
        
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{api_base}/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                        "temperature": kwargs.get("temperature", self.config.temperature),
                    },
                )
                
                if response.status_code != 200:
                    logger.error(f"Custom API error: {response.status_code} - {response.text}")
                    raise ValueError(f"Custom API error: {response.status_code}")
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except httpx.TimeoutException:
            raise ValueError("Custom API timeout")
        except Exception as e:
            logger.error(f"Custom API error: {e}")
            raise


# ============================================
# LLM Provider Manager
# ============================================

class LLMProviderManager:
    """
    Manages multiple LLM providers and handles model selection.
    
    Usage:
        manager = LLMProviderManager()
        manager.load_from_settings()
        
        # Use default provider
        response = await manager.generate(messages)
        
        # Use specific provider
        response = await manager.generate(messages, provider="openai")
        
        # Use specific model
        response = await manager.generate(messages, model="gpt-4o")
    """
    
    # Provider class mapping
    PROVIDER_CLASSES = {
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.GOOGLE: GoogleProvider,
        ProviderType.ANTHROPIC: AnthropicProvider,
        ProviderType.OPENROUTER: OpenRouterProvider,
        ProviderType.OLLAMA: OllamaProvider,
        ProviderType.CUSTOM: CustomProvider,
    }
    
    # Default models for each provider
    DEFAULT_MODELS = {
        ProviderType.OPENAI: "gpt-4o-mini",
        ProviderType.GOOGLE: "gemini-2.0-flash",
        ProviderType.ANTHROPIC: "claude-3-5-sonnet-20241022",
        ProviderType.OPENROUTER: "google/gemini-2.0-flash-exp:free",
        ProviderType.OLLAMA: "llama3.2",
        ProviderType.CUSTOM: "default",
    }
    
    def __init__(self):
        self._providers: dict[ProviderType, LLMProvider] = {}
        self._default_provider: Optional[ProviderType] = None
        self._default_model: Optional[str] = None
        # User-specific model selections (user_id -> (provider, model))
        self._user_selections: dict[str, tuple[ProviderType, str]] = {}
    
    def load_from_settings(self) -> None:
        """Load provider configurations from settings."""
        from ..utils.config import settings
        
        # OpenAI
        if settings.openai_api_key:
            config = ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key=settings.openai_api_key,
                api_base=settings.openai_api_base,
                model=settings.openai_model,
                enabled=True,
            )
            self._providers[ProviderType.OPENAI] = OpenAIProvider(config)
            logger.info(f"Loaded OpenAI provider with model: {settings.openai_model}")
        
        # Google Gemini
        if settings.google_generative_ai_api_key:
            config = ProviderConfig(
                provider_type=ProviderType.GOOGLE,
                api_key=settings.google_generative_ai_api_key,
                model=settings.google_model,
                enabled=True,
            )
            self._providers[ProviderType.GOOGLE] = GoogleProvider(config)
            logger.info(f"Loaded Google Gemini provider with model: {settings.google_model}")
        
        # Anthropic Claude
        if settings.anthropic_api_key:
            config = ProviderConfig(
                provider_type=ProviderType.ANTHROPIC,
                api_key=settings.anthropic_api_key,
                api_base=settings.anthropic_api_base,
                model=settings.anthropic_model,
                enabled=True,
            )
            self._providers[ProviderType.ANTHROPIC] = AnthropicProvider(config)
            logger.info(f"Loaded Anthropic provider with model: {settings.anthropic_model}")
        
        # OpenRouter
        if settings.openrouter_api_key:
            config = ProviderConfig(
                provider_type=ProviderType.OPENROUTER,
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
                enabled=True,
            )
            self._providers[ProviderType.OPENROUTER] = OpenRouterProvider(config)
            logger.info(f"Loaded OpenRouter provider with model: {settings.openrouter_model}")
        
        # Ollama
        if settings.ollama_enabled:
            config = ProviderConfig(
                provider_type=ProviderType.OLLAMA,
                api_base=settings.ollama_api_base,
                model=settings.ollama_model,
                enabled=True,
                timeout=180,  # Local models may be slower
            )
            self._providers[ProviderType.OLLAMA] = OllamaProvider(config)
            logger.info(f"Loaded Ollama provider with model: {settings.ollama_model}")
        
        # Custom
        if settings.custom_api_base:
            config = ProviderConfig(
                provider_type=ProviderType.CUSTOM,
                api_key=settings.custom_api_key,
                api_base=settings.custom_api_base,
                model=settings.custom_model,
                enabled=True,
            )
            self._providers[ProviderType.CUSTOM] = CustomProvider(config)
            logger.info(f"Loaded Custom provider: {settings.custom_api_base}")
        
        # Set default provider based on priority
        self._set_default_provider(settings)
    
    def _set_default_provider(self, settings) -> None:
        """Set default provider based on configuration priority."""
        # Check explicit default setting first
        default_provider_str = settings.default_llm_provider
        if default_provider_str:
            try:
                provider_type = ProviderType(default_provider_str.lower())
                if provider_type in self._providers:
                    self._default_provider = provider_type
                    self._default_model = settings.default_llm_model
                    logger.info(f"Default LLM provider set to: {provider_type.value}")
                    return
            except ValueError:
                logger.warning(f"Invalid default provider: {default_provider_str}")
        
        # Auto-select based on priority: OpenRouter > OpenAI > Anthropic > Google > Ollama > Custom
        priority = [
            ProviderType.OPENROUTER,
            ProviderType.OPENAI,
            ProviderType.ANTHROPIC,
            ProviderType.GOOGLE,
            ProviderType.OLLAMA,
            ProviderType.CUSTOM,
        ]
        
        for provider_type in priority:
            if provider_type in self._providers:
                self._default_provider = provider_type
                logger.info(f"Auto-selected default LLM provider: {provider_type.value}")
                return
        
        logger.warning("No LLM provider configured")
    
    def get_provider(self, provider: Optional[str] = None) -> Optional[LLMProvider]:
        """Get a specific provider or the default one."""
        if provider:
            try:
                provider_type = ProviderType(provider.lower())
                return self._providers.get(provider_type)
            except ValueError:
                logger.warning(f"Unknown provider: {provider}")
                return None
        
        if self._default_provider:
            return self._providers.get(self._default_provider)
        
        return None
    
    def list_available_providers(self) -> list[str]:
        """List all available (configured) providers."""
        return [p.value for p in self._providers.keys()]
    
    def list_available_models(self) -> dict[str, list[str]]:
        """List available models for each provider."""
        models = {}
        
        # Predefined popular models
        model_lists = {
            ProviderType.OPENAI: [
                "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
                "o1-preview", "o1-mini",
            ],
            ProviderType.GOOGLE: [
                "gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-pro",
                "gemini-1.5-flash", "gemini-pro",
            ],
            ProviderType.ANTHROPIC: [
                "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307",
            ],
            ProviderType.OPENROUTER: [
                "google/gemini-2.0-flash-exp:free", "meta-llama/llama-3.2-3b-instruct:free",
                "anthropic/claude-3.5-sonnet", "openai/gpt-4o", "google/gemini-pro-1.5",
            ],
            ProviderType.OLLAMA: [
                "llama3.2", "llama3.1", "mistral", "codellama", "phi3",
                "qwen2.5", "deepseek-coder-v2",
            ],
            ProviderType.CUSTOM: ["default"],
        }
        
        for provider_type in self._providers.keys():
            models[provider_type.value] = model_lists.get(provider_type, [])
        
        return models
    
    # ============================================
    # Model Selection Methods
    # ============================================
    
    def set_user_model(self, user_id: str, provider: str, model: Optional[str] = None) -> bool:
        """
        Set a specific model for a user.
        
        Args:
            user_id: User identifier
            provider: Provider name (openai, google, etc.)
            model: Optional model name (uses provider default if not specified)
        
        Returns:
            True if set successfully
        """
        try:
            provider_type = ProviderType(provider.lower())
            if provider_type not in self._providers:
                return False
            
            self._user_selections[user_id] = (provider_type, model or "")
            logger.info(f"User {user_id} selected model: {provider}/{model}")
            return True
        except ValueError:
            return False
    
    def get_user_model(self, user_id: str) -> Optional[tuple[str, str]]:
        """
        Get the current model selection for a user.
        
        Returns:
            Tuple of (provider, model) or None if using default
        """
        if user_id in self._user_selections:
            provider_type, model = self._user_selections[user_id]
            if model:
                return (provider_type.value, model)
            # Get provider's configured model
            provider = self._providers.get(provider_type)
            if provider:
                return (provider_type.value, provider.config.model)
        
        # Return default
        if self._default_provider:
            provider = self._providers.get(self._default_provider)
            model = self._default_model or (provider.config.model if provider else "")
            return (self._default_provider.value, model)
        
        return None
    
    def clear_user_model(self, user_id: str) -> bool:
        """Clear user's model selection, reverting to default."""
        if user_id in self._user_selections:
            del self._user_selections[user_id]
            logger.info(f"User {user_id} cleared model selection")
            return True
        return False
    
    def get_current_status(self, user_id: Optional[str] = None) -> dict:
        """
        Get current LLM status including available providers and current selection.
        
        Args:
            user_id: Optional user ID to check user-specific selection
        
        Returns:
            dict with status information
        """
        available = self.list_available_providers()
        models = self.list_available_models()
        
        # Get current selection
        current_provider = None
        current_model = None
        is_user_selection = False
        
        if user_id and user_id in self._user_selections:
            provider_type, model = self._user_selections[user_id]
            current_provider = provider_type.value
            provider = self._providers.get(provider_type)
            current_model = model or (provider.config.model if provider else "")
            is_user_selection = True
        elif self._default_provider:
            current_provider = self._default_provider.value
            provider = self._providers.get(self._default_provider)
            current_model = self._default_model or (provider.config.model if provider else "")
        
        return {
            "available_providers": available,
            "available_models": models,
            "current_provider": current_provider,
            "current_model": current_model,
            "is_user_selection": is_user_selection,
        }
    
    async def generate_for_user(
        self,
        user_id: str,
        messages: list[dict],
        **kwargs
    ) -> str:
        """
        Generate a response using the user's selected model.
        
        Args:
            user_id: User identifier
            messages: Conversation messages
            **kwargs: Additional arguments
        
        Returns:
            Generated response text
        """
        provider = None
        model = None
        
        if user_id in self._user_selections:
            provider_type, model = self._user_selections[user_id]
            provider = provider_type.value
            if not model:
                p = self._providers.get(provider_type)
                model = p.config.model if p else None
        
        return await self.generate(messages, provider=provider, model=model, **kwargs)
    
    def get_llm_provider_function_for_user(self, user_id: str) -> Optional[Callable]:
        """
        Get a callable function for a specific user's model selection.
        """
        async def provider_func(conversation: list[dict]) -> str:
            return await self.generate_for_user(user_id, conversation)
        
        return provider_func
    
    async def generate(
        self,
        messages: list[dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a response using the specified or default provider.
        
        Args:
            messages: Conversation messages in OpenAI format
            provider: Optional provider name (openai, google, anthropic, etc.)
            model: Optional model name (overrides provider default)
            **kwargs: Additional arguments for the provider
        
        Returns:
            Generated response text
        """
        llm_provider = self.get_provider(provider)
        
        if not llm_provider:
            available = self.list_available_providers()
            if available:
                raise ValueError(f"Provider '{provider}' not available. Available: {available}")
            else:
                raise ValueError(
                    "No LLM provider configured. Set one of: "
                    "OPENAI_API_KEY, GOOGLE_GENERATIVE_AI_API_KEY, "
                    "ANTHROPIC_API_KEY, OPENROUTER_API_KEY, or OLLAMA_ENABLED=true"
                )
        
        # Use specified model or default
        if not model and self._default_model:
            model = self._default_model
        
        return await llm_provider.generate(messages, model=model, **kwargs)
    
    def get_llm_provider_function(self) -> Optional[Callable]:
        """
        Get a callable function for AgentLoop compatibility.
        Returns an async function that matches the old provider signature.
        """
        if not self._default_provider:
            return None
        
        async def provider_func(conversation: list[dict]) -> str:
            return await self.generate(conversation)
        
        return provider_func


# Global instance
_llm_manager: Optional[LLMProviderManager] = None


def get_llm_manager() -> LLMProviderManager:
    """Get the global LLM Provider Manager instance."""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMProviderManager()
        _llm_manager.load_from_settings()
    return _llm_manager


def reset_llm_manager() -> None:
    """Reset the LLM manager (useful after config changes)."""
    global _llm_manager
    _llm_manager = None


__all__ = [
    "ProviderType",
    "ModelInfo",
    "ProviderConfig",
    "LLMProvider",
    "OpenAIProvider",
    "GoogleProvider",
    "AnthropicProvider",
    "OpenRouterProvider",
    "OllamaProvider",
    "CustomProvider",
    "LLMProviderManager",
    "get_llm_manager",
    "reset_llm_manager",
]
