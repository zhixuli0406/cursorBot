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
import os
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
    BEDROCK = "bedrock"
    MOONSHOT = "moonshot"
    GLM = "glm"


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
    
    async def fetch_models(self) -> list[str]:
        """
        Fetch available models from the provider API.
        Override in subclasses to implement provider-specific logic.
        
        Returns:
            List of model IDs
        """
        return []
    
    async def generate_stream(self, messages: list[dict], **kwargs):
        """
        Generate a streaming response from the LLM.
        Yields chunks of text as they arrive.
        
        Override in subclasses to implement provider-specific streaming.
        Default implementation falls back to non-streaming.
        
        Yields:
            str: Text chunks
        """
        # Default: fall back to non-streaming
        result = await self.generate(messages, **kwargs)
        yield result


# ============================================
# OpenAI Provider
# ============================================

class OpenAIProvider(LLMProvider):
    """OpenAI GPT models provider."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI
    
    async def fetch_models(self) -> list[str]:
        """Fetch available models from OpenAI API."""
        import httpx
        
        api_key = self.config.api_key
        api_base = self.config.api_base or "https://api.openai.com/v1"
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{api_base}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                
                if response.status_code != 200:
                    logger.warning(f"OpenAI models fetch error: {response.status_code}")
                    return []
                
                result = response.json()
                # Filter for chat models only
                chat_models = []
                for model in result.get("data", []):
                    model_id = model.get("id", "")
                    # Include GPT models and o1 models
                    if any(x in model_id for x in ["gpt-4", "gpt-3.5", "o1-", "chatgpt"]):
                        chat_models.append(model_id)
                
                # Sort by name
                chat_models.sort(key=lambda x: (
                    0 if "gpt-4o" in x else 
                    1 if "gpt-4" in x else 
                    2 if "o1" in x else 
                    3 if "gpt-3.5" in x else 4
                ))
                return chat_models
                
        except Exception as e:
            logger.warning(f"Failed to fetch OpenAI models: {e}")
            return []
    
    async def generate_stream(self, messages: list[dict], **kwargs):
        """Generate streaming response from OpenAI."""
        import httpx
        
        api_key = self.config.api_key
        api_base = self.config.api_base or "https://api.openai.com/v1"
        model = kwargs.get("model") or self.config.model or "gpt-4o-mini"
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                async with client.stream(
                    "POST",
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
                        "stream": True,
                    },
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise ValueError(f"OpenAI API error: {response.status_code} - {error_text}")
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                import json
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                                
        except httpx.TimeoutException:
            raise ValueError("OpenAI API timeout")
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
    
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
    
    async def fetch_models(self) -> list[str]:
        """Fetch available models from Google Gemini API."""
        api_key = self.config.api_key
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=api_key)
            
            # Run in executor since list_models is sync
            loop = asyncio.get_event_loop()
            models = await loop.run_in_executor(None, lambda: list(genai.list_models()))
            
            # Filter for generative models
            gemini_models = []
            for model in models:
                name = model.name.replace("models/", "")
                # Only include gemini models that support generateContent
                if "gemini" in name and "generateContent" in [m.name for m in model.supported_generation_methods]:
                    gemini_models.append(name)
            
            # Sort by version (newer first)
            gemini_models.sort(key=lambda x: (
                0 if "2.0" in x else
                1 if "1.5-pro" in x else
                2 if "1.5-flash" in x else
                3 if "1.5" in x else
                4 if "pro" in x else 5
            ))
            return gemini_models
            
        except ImportError:
            logger.warning("google-generativeai not installed")
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch Google models: {e}")
            return []
    
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
    """Anthropic Claude models provider with Extended Thinking support."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC
    
    async def fetch_models(self) -> list[str]:
        """
        Return available Anthropic Claude models.
        Note: Anthropic doesn't have a public models list API,
        so we return a predefined list of known models.
        """
        # Predefined list of Claude models (Anthropic has no list API)
        return [
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]
    
    async def generate(
        self, 
        messages: list[dict], 
        thinking: bool = False,
        thinking_budget: int = 10000,
        **kwargs
    ) -> str:
        """
        Generate response from Anthropic Claude.
        
        Args:
            messages: Conversation messages
            thinking: Enable Extended Thinking mode (Claude 3.5+ only)
            thinking_budget: Max tokens for thinking (1024-100000)
            **kwargs: Additional arguments
        
        Returns:
            Generated response (includes thinking if enabled)
        """
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
                # Build payload
                max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
                
                payload = {
                    "model": model,
                    "messages": chat_messages,
                    "max_tokens": max_tokens,
                }
                
                if system_content:
                    payload["system"] = system_content.strip()
                
                # Add thinking configuration if enabled
                if thinking:
                    # Thinking requires specific budget configuration
                    thinking_budget = max(1024, min(thinking_budget, 100000))
                    payload["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": thinking_budget
                    }
                    # When thinking is enabled, temperature must be 1
                    payload["temperature"] = 1
                    logger.info(f"Extended Thinking enabled with budget: {thinking_budget}")
                
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                }
                
                # Use beta header for thinking feature
                if thinking:
                    headers["anthropic-beta"] = "interleaved-thinking-2025-05-14"
                
                response = await client.post(
                    f"{api_base}/messages",
                    headers=headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
                    raise ValueError(f"Anthropic API error: {response.status_code}")
                
                result = response.json()
                
                # Process response content
                content_blocks = result.get("content", [])
                text_parts = []
                thinking_parts = []
                
                for block in content_blocks:
                    if block.get("type") == "thinking":
                        thinking_parts.append(block.get("thinking", ""))
                    elif block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                
                # Combine response
                response_text = "\n".join(text_parts)
                
                # Optionally include thinking in response
                if thinking and thinking_parts and kwargs.get("include_thinking", False):
                    thinking_text = "\n".join(thinking_parts)
                    response_text = f"<thinking>\n{thinking_text}\n</thinking>\n\n{response_text}"
                
                return response_text
                
        except httpx.TimeoutException:
            raise ValueError("Anthropic API timeout")
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def generate_with_thinking(
        self,
        messages: list[dict],
        thinking_budget: int = 10000,
        include_thinking: bool = False,
        **kwargs
    ) -> dict:
        """
        Generate response with Extended Thinking and return structured result.
        
        Args:
            messages: Conversation messages
            thinking_budget: Max tokens for thinking
            include_thinking: Include thinking in result
            **kwargs: Additional arguments
        
        Returns:
            dict with 'response', 'thinking', and 'usage' keys
        """
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
                thinking_budget = max(1024, min(thinking_budget, 100000))
                
                payload = {
                    "model": model,
                    "messages": chat_messages,
                    "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                    "thinking": {
                        "type": "enabled",
                        "budget_tokens": thinking_budget
                    },
                    "temperature": 1,  # Required for thinking
                }
                
                if system_content:
                    payload["system"] = system_content.strip()
                
                response = await client.post(
                    f"{api_base}/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "anthropic-beta": "interleaved-thinking-2025-05-14",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                
                if response.status_code != 200:
                    raise ValueError(f"Anthropic API error: {response.status_code}")
                
                result = response.json()
                
                # Parse content blocks
                content_blocks = result.get("content", [])
                text_parts = []
                thinking_parts = []
                
                for block in content_blocks:
                    if block.get("type") == "thinking":
                        thinking_parts.append(block.get("thinking", ""))
                    elif block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                
                return {
                    "response": "\n".join(text_parts),
                    "thinking": "\n".join(thinking_parts) if include_thinking else None,
                    "usage": result.get("usage", {}),
                    "model": result.get("model", model),
                    "stop_reason": result.get("stop_reason"),
                }
                
        except Exception as e:
            logger.error(f"Anthropic thinking error: {e}")
            raise


# ============================================
# OpenRouter Provider
# ============================================

class OpenRouterProvider(LLMProvider):
    """OpenRouter proxy provider (access to multiple models)."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENROUTER
    
    async def fetch_models(self) -> list[str]:
        """Fetch available models from OpenRouter API."""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "HTTP-Referer": "https://github.com/cursorbot",
                    },
                )
                
                if response.status_code != 200:
                    logger.warning(f"OpenRouter models fetch error: {response.status_code}")
                    return []
                
                result = response.json()
                models = []
                
                for model in result.get("data", []):
                    model_id = model.get("id", "")
                    # Add free indicator
                    pricing = model.get("pricing", {})
                    is_free = (
                        pricing.get("prompt") == "0" or 
                        pricing.get("prompt") == 0 or
                        ":free" in model_id
                    )
                    models.append({
                        "id": model_id,
                        "name": model.get("name", model_id),
                        "is_free": is_free,
                        "context_length": model.get("context_length", 0),
                    })
                
                # Sort: free models first, then by context length
                models.sort(key=lambda x: (
                    0 if x["is_free"] else 1,
                    -x["context_length"]
                ))
                
                return [m["id"] for m in models]
                
        except Exception as e:
            logger.warning(f"Failed to fetch OpenRouter models: {e}")
            return []
    
    async def generate_stream(self, messages: list[dict], **kwargs):
        """Generate streaming response from OpenRouter."""
        import httpx
        
        api_key = self.config.api_key
        model = kwargs.get("model") or self.config.model or "google/gemini-2.0-flash-exp:free"
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                async with client.stream(
                    "POST",
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
                        "stream": True,
                    },
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise ValueError(f"OpenRouter API error: {response.status_code} - {error_text}")
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                import json
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                                
        except httpx.TimeoutException:
            raise ValueError("OpenRouter API timeout")
        except Exception as e:
            logger.error(f"OpenRouter streaming error: {e}")
            raise
    
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
    
    def is_available(self) -> bool:
        """Ollama doesn't require API key, just needs to be enabled."""
        return self.config.enabled
    
    async def fetch_models(self) -> list[str]:
        """Fetch available models from Ollama local API."""
        import httpx
        
        api_base = self.config.api_base or "http://localhost:11434"
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{api_base}/api/tags")
                
                if response.status_code != 200:
                    logger.warning(f"Ollama models fetch error: {response.status_code}")
                    return []
                
                result = response.json()
                models = []
                
                for model in result.get("models", []):
                    name = model.get("name", "")
                    # Remove tag if it's 'latest'
                    if name.endswith(":latest"):
                        name = name.replace(":latest", "")
                    models.append(name)
                
                return sorted(models)
                
        except httpx.ConnectError:
            logger.warning(f"Cannot connect to Ollama at {api_base}")
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch Ollama models: {e}")
            return []
    
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
# AWS Bedrock Provider
# ============================================

class BedrockProvider(LLMProvider):
    """AWS Bedrock provider for Claude and other models."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.BEDROCK
    
    def is_available(self) -> bool:
        """Check if Bedrock is configured."""
        return self.config.enabled and bool(self.config.extra.get("region"))
    
    async def fetch_models(self) -> list[str]:
        """Fetch available models from AWS Bedrock."""
        try:
            import boto3
            
            region = self.config.extra.get("region", "us-east-1")
            
            bedrock = boto3.client(
                service_name="bedrock",
                region_name=region,
            )
            
            response = bedrock.list_foundation_models()
            
            models = []
            for model in response.get("modelSummaries", []):
                model_id = model.get("modelId", "")
                # Filter for text generation models
                if "TEXT" in model.get("outputModalities", []):
                    models.append(model_id)
            
            # Sort by provider
            models.sort(key=lambda x: (
                0 if "anthropic" in x else
                1 if "amazon" in x else
                2 if "meta" in x else
                3 if "cohere" in x else 4
            ))
            
            return models
            
        except ImportError:
            logger.warning("boto3 not installed for Bedrock")
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch Bedrock models: {e}")
            return [
                "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "anthropic.claude-3-5-haiku-20241022-v1:0",
                "anthropic.claude-3-opus-20240229-v1:0",
                "amazon.titan-text-express-v1",
                "meta.llama3-2-90b-instruct-v1:0",
            ]
    
    async def generate(self, messages: list[dict], **kwargs) -> str:
        """Generate response using AWS Bedrock."""
        try:
            import boto3
            import json
            
            region = self.config.extra.get("region", "us-east-1")
            model_id = kwargs.get("model") or self.config.model or "anthropic.claude-3-5-sonnet-20241022-v2:0"
            
            bedrock_runtime = boto3.client(
                service_name="bedrock-runtime",
                region_name=region,
            )
            
            # Format messages for different model types
            if "anthropic" in model_id:
                # Claude format
                system_prompt = kwargs.get("system_prompt", "")
                
                # Extract system message if present
                formatted_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system_prompt = msg["content"]
                    else:
                        formatted_messages.append({
                            "role": msg["role"],
                            "content": msg["content"],
                        })
                
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                    "messages": formatted_messages,
                }
                
                if system_prompt:
                    body["system"] = system_prompt
                    
            elif "amazon" in model_id:
                # Titan format
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                body = {
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": kwargs.get("max_tokens", self.config.max_tokens),
                        "temperature": kwargs.get("temperature", self.config.temperature),
                    }
                }
                
            elif "meta" in model_id:
                # Llama format
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                body = {
                    "prompt": prompt,
                    "max_gen_len": kwargs.get("max_tokens", self.config.max_tokens),
                    "temperature": kwargs.get("temperature", self.config.temperature),
                }
                
            else:
                # Generic format
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                body = {"prompt": prompt}
            
            # Run in executor since boto3 is synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: bedrock_runtime.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )
            )
            
            response_body = json.loads(response["body"].read())
            
            # Extract response based on model type
            if "anthropic" in model_id:
                return response_body.get("content", [{}])[0].get("text", "")
            elif "amazon" in model_id:
                return response_body.get("results", [{}])[0].get("outputText", "")
            elif "meta" in model_id:
                return response_body.get("generation", "")
            else:
                return str(response_body.get("completion", response_body))
                
        except ImportError:
            raise ValueError("boto3 not installed. Run: pip install boto3")
        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
            raise ValueError(f"Bedrock API error: {e}")


# ============================================
# Moonshot AI Provider (月之暗面)
# ============================================

class MoonshotProvider(LLMProvider):
    """Moonshot AI (月之暗面) provider for Chinese market."""
    
    API_BASE = "https://api.moonshot.cn/v1"
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.MOONSHOT
    
    def is_available(self) -> bool:
        """Check if Moonshot API key is configured."""
        return bool(self.config.api_key) and self.config.enabled
    
    async def fetch_models(self) -> list[str]:
        """Return available Moonshot models."""
        return [
            "moonshot-v1-8k",      # 8K context
            "moonshot-v1-32k",     # 32K context
            "moonshot-v1-128k",    # 128K context (long context)
        ]
    
    async def generate(self, messages: list[dict], **kwargs) -> str:
        """Generate response using Moonshot API (OpenAI compatible)."""
        import httpx
        
        if not self.is_available():
            raise ValueError("Moonshot API key not configured")
        
        model = kwargs.get("model") or self.config.model or "moonshot-v1-8k"
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
        temperature = kwargs.get("temperature", self.config.temperature)
        
        # Moonshot uses OpenAI-compatible API
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.API_BASE}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    raise ValueError(f"Moonshot API error: {response.status_code} - {error_text}")
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
        except httpx.HTTPError as e:
            raise ValueError(f"Moonshot HTTP error: {e}")
        except Exception as e:
            raise ValueError(f"Moonshot error: {e}")


# ============================================
# GLM (智譜) Provider
# ============================================

class GLMProvider(LLMProvider):
    """GLM (智譜 ChatGLM) provider for Chinese market."""
    
    API_BASE = "https://open.bigmodel.cn/api/paas/v4"
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GLM
    
    def is_available(self) -> bool:
        """Check if GLM API key is configured."""
        return bool(self.config.api_key) and self.config.enabled
    
    async def fetch_models(self) -> list[str]:
        """Return available GLM models."""
        return [
            "glm-4-plus",       # Most powerful
            "glm-4",            # Standard
            "glm-4-long",       # Long context (1M tokens)
            "glm-4-flash",      # Fast and cheap
            "glm-4v-plus",      # Vision model
            "glm-4-alltools",   # With tool calling
        ]
    
    async def generate(self, messages: list[dict], **kwargs) -> str:
        """Generate response using GLM API."""
        import httpx
        import time
        import jwt
        
        if not self.is_available():
            raise ValueError("GLM API key not configured")
        
        model = kwargs.get("model") or self.config.model or "glm-4-flash"
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
        temperature = kwargs.get("temperature", self.config.temperature)
        
        # Generate JWT token for authentication
        token = self._generate_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.API_BASE}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    raise ValueError(f"GLM API error: {response.status_code} - {error_text}")
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
        except httpx.HTTPError as e:
            raise ValueError(f"GLM HTTP error: {e}")
        except Exception as e:
            raise ValueError(f"GLM error: {e}")
    
    def _generate_token(self) -> str:
        """Generate JWT token for GLM API authentication."""
        import time
        
        try:
            import jwt
        except ImportError:
            # Fallback: use API key directly if jwt not available
            return self.config.api_key
        
        # API key format: {id}.{secret}
        api_key = self.config.api_key
        if "." not in api_key:
            return api_key
        
        key_id, secret = api_key.split(".", 1)
        
        now = int(time.time() * 1000)
        
        payload = {
            "api_key": key_id,
            "exp": now + 3600 * 1000,  # 1 hour
            "timestamp": now,
        }
        
        return jwt.encode(
            payload,
            secret,
            algorithm="HS256",
            headers={"alg": "HS256", "sign_type": "SIGN"},
        )


# ============================================
# Custom OpenAI-Compatible Provider
# ============================================

class CustomProvider(LLMProvider):
    """Custom OpenAI-compatible endpoint provider."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.CUSTOM
    
    def is_available(self) -> bool:
        """Custom provider needs api_base to be set."""
        return bool(self.config.api_base) and self.config.enabled
    
    async def fetch_models(self) -> list[str]:
        """Try to fetch models from custom OpenAI-compatible endpoint."""
        import httpx
        
        api_base = self.config.api_base
        api_key = self.config.api_key
        
        if not api_base:
            return []
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{api_base}/models",
                    headers=headers,
                )
                
                if response.status_code != 200:
                    logger.warning(f"Custom endpoint models fetch error: {response.status_code}")
                    return []
                
                result = response.json()
                models = []
                
                # OpenAI format
                for model in result.get("data", []):
                    models.append(model.get("id", ""))
                
                return sorted(filter(None, models))
                
        except Exception as e:
            logger.warning(f"Failed to fetch models from custom endpoint: {e}")
            return []
    
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
        ProviderType.BEDROCK: BedrockProvider,
        ProviderType.MOONSHOT: MoonshotProvider,
        ProviderType.GLM: GLMProvider,
    }
    
    # Default models for each provider
    DEFAULT_MODELS = {
        ProviderType.OPENAI: "gpt-4o-mini",
        ProviderType.GOOGLE: "gemini-2.0-flash",
        ProviderType.ANTHROPIC: "claude-3-5-sonnet-20241022",
        ProviderType.OPENROUTER: "google/gemini-2.0-flash-exp:free",
        ProviderType.OLLAMA: "llama3.2",
        ProviderType.CUSTOM: "default",
        ProviderType.BEDROCK: "anthropic.claude-3-5-sonnet-20241022-v2:0",
        ProviderType.MOONSHOT: "moonshot-v1-8k",
        ProviderType.GLM: "glm-4-flash",
    }
    
    def __init__(self):
        self._providers: dict[ProviderType, LLMProvider] = {}
        self._default_provider: Optional[ProviderType] = None
        self._default_model: Optional[str] = None
        # User-specific model selections (user_id -> (provider, model))
        self._user_selections: dict[str, tuple[ProviderType, str]] = {}
        # Usage tracking history
        self._usage_history: list[dict] = []
    
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
        
        # Moonshot (月之暗面)
        moonshot_key = getattr(settings, 'moonshot_api_key', None) or os.getenv("MOONSHOT_API_KEY")
        if moonshot_key:
            moonshot_model = getattr(settings, 'moonshot_model', None) or os.getenv("MOONSHOT_MODEL", "moonshot-v1-8k")
            config = ProviderConfig(
                provider_type=ProviderType.MOONSHOT,
                api_key=moonshot_key,
                model=moonshot_model,
                enabled=True,
            )
            self._providers[ProviderType.MOONSHOT] = MoonshotProvider(config)
            logger.info(f"Loaded Moonshot provider with model: {moonshot_model}")
        
        # GLM (智譜)
        glm_key = getattr(settings, 'glm_api_key', None) or os.getenv("GLM_API_KEY")
        if glm_key:
            glm_model = getattr(settings, 'glm_model', None) or os.getenv("GLM_MODEL", "glm-4-flash")
            config = ProviderConfig(
                provider_type=ProviderType.GLM,
                api_key=glm_key,
                model=glm_model,
                enabled=True,
            )
            self._providers[ProviderType.GLM] = GLMProvider(config)
            logger.info(f"Loaded GLM provider with model: {glm_model}")
        
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
        """
        List available models for each provider (fallback/cached).
        Use fetch_all_models() for live API fetch.
        """
        models = {}
        
        # Predefined popular models as fallback
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
    
    async def fetch_all_models(self, max_per_provider: int = 20) -> dict[str, list[str]]:
        """
        Fetch available models from all configured providers via API.
        
        Args:
            max_per_provider: Maximum number of models to return per provider
        
        Returns:
            dict mapping provider name to list of model IDs
        """
        models = {}
        fallback = self.list_available_models()
        
        # Create tasks for all providers
        tasks = {}
        for provider_type, provider in self._providers.items():
            tasks[provider_type] = provider.fetch_models()
        
        # Execute all fetches concurrently
        for provider_type, task in tasks.items():
            try:
                result = await task
                if result:
                    # Limit results and add to dict
                    models[provider_type.value] = result[:max_per_provider]
                else:
                    # Use fallback if fetch returns empty
                    models[provider_type.value] = fallback.get(provider_type.value, [])
            except Exception as e:
                logger.warning(f"Error fetching models for {provider_type.value}: {e}")
                # Use fallback on error
                models[provider_type.value] = fallback.get(provider_type.value, [])
        
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
        enable_failover: bool = True,
        **kwargs
    ) -> str:
        """
        Generate a response using the specified or default provider.
        Supports automatic failover to backup providers on failure.
        
        Args:
            messages: Conversation messages in OpenAI format
            provider: Optional provider name (openai, google, anthropic, etc.)
            model: Optional model name (overrides provider default)
            enable_failover: Whether to try other providers on failure
            **kwargs: Additional arguments for the provider
        
        Returns:
            Generated response text
        """
        import time
        
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
        
        # Build failover order
        failover_providers = []
        if enable_failover:
            # Priority order for failover
            priority = [
                ProviderType.OPENROUTER,
                ProviderType.OPENAI,
                ProviderType.ANTHROPIC,
                ProviderType.GOOGLE,
                ProviderType.OLLAMA,
                ProviderType.CUSTOM,
            ]
            
            primary_type = llm_provider.provider_type
            for pt in priority:
                if pt != primary_type and pt in self._providers:
                    failover_providers.append(self._providers[pt])
        
        # Try primary provider first
        start_time = time.time()
        errors = []
        
        try:
            result = await llm_provider.generate(messages, model=model, **kwargs)
            
            # Track usage
            elapsed = time.time() - start_time
            self._track_usage(llm_provider.provider_type.value, model, len(str(messages)), len(result), elapsed, True)
            
            return result
            
        except Exception as e:
            errors.append(f"{llm_provider.provider_type.value}: {str(e)}")
            logger.warning(f"Primary provider {llm_provider.provider_type.value} failed: {e}")
            
            # Track failed usage
            elapsed = time.time() - start_time
            self._track_usage(llm_provider.provider_type.value, model, len(str(messages)), 0, elapsed, False)
        
        # Try failover providers
        for backup_provider in failover_providers:
            start_time = time.time()
            backup_model = backup_provider.config.model
            
            try:
                logger.info(f"Failing over to {backup_provider.provider_type.value}")
                result = await backup_provider.generate(messages, model=backup_model, **kwargs)
                
                # Track usage
                elapsed = time.time() - start_time
                self._track_usage(backup_provider.provider_type.value, backup_model, len(str(messages)), len(result), elapsed, True, failover=True)
                
                return result
                
            except Exception as e:
                errors.append(f"{backup_provider.provider_type.value}: {str(e)}")
                logger.warning(f"Failover provider {backup_provider.provider_type.value} failed: {e}")
                
                # Track failed usage
                elapsed = time.time() - start_time
                self._track_usage(backup_provider.provider_type.value, backup_model, len(str(messages)), 0, elapsed, False, failover=True)
                continue
        
        # All providers failed
        raise ValueError(f"All LLM providers failed:\n" + "\n".join(errors))
    
    def _track_usage(
        self, 
        provider: str, 
        model: str, 
        input_chars: int, 
        output_chars: int, 
        elapsed: float, 
        success: bool,
        failover: bool = False
    ) -> None:
        """Track API usage for analytics."""
        usage_entry = {
            "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0,
            "provider": provider,
            "model": model or "default",
            "input_chars": input_chars,
            "output_chars": output_chars,
            "elapsed_seconds": round(elapsed, 2),
            "success": success,
            "failover": failover,
        }
        
        self._usage_history.append(usage_entry)
        
        # Keep only last 1000 entries
        if len(self._usage_history) > 1000:
            self._usage_history = self._usage_history[-1000:]
        
        logger.debug(f"Usage tracked: {provider}/{model} - {output_chars} chars in {elapsed:.2f}s")
    
    def get_usage_stats(self, user_id: Optional[str] = None) -> dict:
        """
        Get usage statistics.
        
        Returns:
            dict with usage statistics
        """
        if not self._usage_history:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "failover_requests": 0,
                "total_input_chars": 0,
                "total_output_chars": 0,
                "total_time_seconds": 0,
                "by_provider": {},
            }
        
        stats = {
            "total_requests": len(self._usage_history),
            "successful_requests": sum(1 for u in self._usage_history if u["success"]),
            "failed_requests": sum(1 for u in self._usage_history if not u["success"]),
            "failover_requests": sum(1 for u in self._usage_history if u.get("failover")),
            "total_input_chars": sum(u["input_chars"] for u in self._usage_history),
            "total_output_chars": sum(u["output_chars"] for u in self._usage_history),
            "total_time_seconds": round(sum(u["elapsed_seconds"] for u in self._usage_history), 2),
            "by_provider": {},
        }
        
        # Group by provider
        for entry in self._usage_history:
            provider = entry["provider"]
            if provider not in stats["by_provider"]:
                stats["by_provider"][provider] = {
                    "requests": 0,
                    "successful": 0,
                    "failed": 0,
                    "output_chars": 0,
                    "time_seconds": 0,
                }
            
            stats["by_provider"][provider]["requests"] += 1
            if entry["success"]:
                stats["by_provider"][provider]["successful"] += 1
            else:
                stats["by_provider"][provider]["failed"] += 1
            stats["by_provider"][provider]["output_chars"] += entry["output_chars"]
            stats["by_provider"][provider]["time_seconds"] += entry["elapsed_seconds"]
        
        return stats
    
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
    
    async def generate_stream(
        self,
        messages: list[dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        """
        Generate a streaming response.
        
        Yields:
            str: Text chunks as they arrive
        """
        llm_provider = self.get_provider(provider)
        
        if not llm_provider:
            raise ValueError("No LLM provider available")
        
        if not model and self._default_model:
            model = self._default_model
        
        async for chunk in llm_provider.generate_stream(messages, model=model, **kwargs):
            yield chunk
    
    async def generate_stream_for_user(
        self,
        user_id: str,
        messages: list[dict],
        **kwargs
    ):
        """
        Generate a streaming response using the user's selected model.
        
        Yields:
            str: Text chunks as they arrive
        """
        provider = None
        model = None
        
        if user_id in self._user_selections:
            provider_type, model = self._user_selections[user_id]
            provider = provider_type.value
            if not model:
                p = self._providers.get(provider_type)
                model = p.config.model if p else None
        
        async for chunk in self.generate_stream(messages, provider=provider, model=model, **kwargs):
            yield chunk


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
