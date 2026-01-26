"""
Cursor Cloud Agents API Integration
Uses Cursor's official API for AI responses
Documentation: https://cursor.com/cn/docs/cloud-agent/api/endpoints
"""

import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import httpx

from ..utils.config import settings
from ..utils.logger import logger


@dataclass
class CursorAgent:
    """Represents a Cursor Cloud Agent."""

    id: str
    name: str
    status: str  # PENDING, RUNNING, FINISHED, FAILED
    source_repo: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class ConversationMessage:
    """A message in the agent conversation."""

    id: str
    type: str  # user_message, assistant_message
    text: str


class CursorCloudAPI:
    """
    Cursor Cloud Agents API Client.
    
    Requires API key from https://cursor.com/settings
    Uses Basic Authentication.
    """

    BASE_URL = "https://api.cursor.com"

    def __init__(self, api_key: str):
        """
        Initialize Cursor API client.

        Args:
            api_key: Cursor API key from settings
        """
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    def _get_auth_header(self) -> dict:
        """Get Basic Auth header."""
        # Basic auth with api_key as username, empty password
        credentials = base64.b64encode(f"{self.api_key}:".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=self._get_auth_header(),
                timeout=120.0,
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_me(self) -> dict:
        """
        Get API key information.
        
        Returns:
            Dict with apiKeyName, createdAt, userEmail
        """
        client = await self._get_client()
        response = await client.get("/v0/me")
        response.raise_for_status()
        return response.json()

    async def list_models(self) -> list[str]:
        """
        List available models for Cloud Agents.
        
        Returns:
            List of model names
        """
        client = await self._get_client()
        response = await client.get("/v0/models")
        response.raise_for_status()
        return response.json().get("models", [])

    async def list_repositories(self) -> list[dict]:
        """
        List accessible GitHub repositories.
        Note: This endpoint has strict rate limits (1/min, 30/hour).
        
        Returns:
            List of repository info
        """
        client = await self._get_client()
        response = await client.get("/v0/repositories")
        response.raise_for_status()
        return response.json().get("repositories", [])

    async def list_agents(
        self,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> tuple[list[CursorAgent], Optional[str]]:
        """
        List all Cloud Agents.
        
        Args:
            limit: Number of agents to return (max 100)
            cursor: Pagination cursor
            
        Returns:
            Tuple of (agents list, next cursor)
        """
        client = await self._get_client()
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        response = await client.get("/v0/agents", params=params)
        response.raise_for_status()
        data = response.json()

        agents = []
        for a in data.get("agents", []):
            agents.append(CursorAgent(
                id=a["id"],
                name=a.get("name", ""),
                status=a.get("status", "UNKNOWN"),
                source_repo=a.get("source", {}).get("repository"),
                summary=a.get("summary"),
                created_at=a.get("createdAt"),
            ))

        return agents, data.get("nextCursor")

    async def create_agent(
        self,
        prompt: str,
        repository: str,
        ref: str = "main",
        name: Optional[str] = None,
        model: Optional[str] = None,
        auto_create_pr: bool = False,
    ) -> CursorAgent:
        """
        Create a new Cloud Agent.
        
        Args:
            prompt: The task/question for the agent
            repository: GitHub repository URL
            ref: Git ref (branch/tag)
            name: Optional agent name
            model: Optional model name (defaults to auto)
            auto_create_pr: Whether to auto-create PR
            
        Returns:
            Created CursorAgent
        """
        client = await self._get_client()

        payload = {
            "prompt": {"text": prompt},
            "source": {
                "repository": repository,
                "ref": ref,
            },
            "target": {
                "autoCreatePr": auto_create_pr,
            },
        }

        if name:
            payload["name"] = name
        if model:
            payload["model"] = model

        response = await client.post("/v0/agents", json=payload)
        response.raise_for_status()
        data = response.json()

        return CursorAgent(
            id=data["id"],
            name=data.get("name", ""),
            status=data.get("status", "PENDING"),
            source_repo=repository,
            created_at=data.get("createdAt"),
        )

    async def get_agent(self, agent_id: str) -> CursorAgent:
        """
        Get agent status and details.
        
        Args:
            agent_id: Agent ID (e.g., bc_abc123)
            
        Returns:
            CursorAgent with current status
        """
        client = await self._get_client()
        response = await client.get(f"/v0/agents/{agent_id}")
        response.raise_for_status()
        data = response.json()

        return CursorAgent(
            id=data["id"],
            name=data.get("name", ""),
            status=data.get("status", "UNKNOWN"),
            source_repo=data.get("source", {}).get("repository"),
            summary=data.get("summary"),
            created_at=data.get("createdAt"),
        )

    async def get_conversation(self, agent_id: str) -> list[ConversationMessage]:
        """
        Get agent conversation history.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of conversation messages
        """
        client = await self._get_client()
        response = await client.get(f"/v0/agents/{agent_id}/conversation")
        response.raise_for_status()
        data = response.json()

        messages = []
        for m in data.get("messages", []):
            messages.append(ConversationMessage(
                id=m.get("id", ""),
                type=m.get("type", ""),
                text=m.get("text", ""),
            ))

        return messages

    async def send_followup(self, agent_id: str, prompt: str) -> str:
        """
        Send a follow-up message to an agent.
        
        Args:
            agent_id: Agent ID
            prompt: Follow-up prompt text
            
        Returns:
            Agent ID
        """
        client = await self._get_client()
        response = await client.post(
            f"/v0/agents/{agent_id}/followup",
            json={"prompt": {"text": prompt}},
        )
        response.raise_for_status()
        return response.json().get("id", agent_id)

    async def stop_agent(self, agent_id: str) -> str:
        """
        Stop a running agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent ID
        """
        client = await self._get_client()
        response = await client.post(f"/v0/agents/{agent_id}/stop")
        response.raise_for_status()
        return response.json().get("id", agent_id)

    async def delete_agent(self, agent_id: str) -> str:
        """
        Delete an agent permanently.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent ID
        """
        client = await self._get_client()
        response = await client.delete(f"/v0/agents/{agent_id}")
        response.raise_for_status()
        return response.json().get("id", agent_id)

    async def wait_for_completion(
        self,
        agent_id: str,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> CursorAgent:
        """
        Wait for an agent to complete.
        
        Args:
            agent_id: Agent ID
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Final agent state
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            agent = await self.get_agent(agent_id)

            if agent.status in ("FINISHED", "FAILED", "STOPPED"):
                return agent

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(f"Agent {agent_id} did not complete within {timeout}s")

            await asyncio.sleep(poll_interval)


class CursorAIManager:
    """
    Manages AI interactions using Cursor Cloud Agents API.
    """

    def __init__(self):
        self._api: Optional[CursorCloudAPI] = None
        self._active_agents: dict[int, str] = {}  # user_id -> agent_id
        self._default_repo: Optional[str] = None

    def _get_api(self) -> CursorCloudAPI:
        """Get or create API client."""
        if self._api is None:
            api_key = getattr(settings, 'cursor_api_key', '') or ''
            if not api_key:
                raise ValueError(
                    "CURSOR_API_KEY is required.\n"
                    "Get it from: https://cursor.com/settings"
                )
            self._api = CursorCloudAPI(api_key)
        return self._api

    @property
    def is_configured(self) -> bool:
        """Check if Cursor API is configured."""
        api_key = getattr(settings, 'cursor_api_key', '') or ''
        return bool(api_key)

    async def verify_api_key(self) -> dict:
        """
        Verify API key and get account info.
        
        Returns:
            Account info dict
        """
        api = self._get_api()
        return await api.get_me()

    async def list_models(self) -> list[str]:
        """List available models."""
        api = self._get_api()
        return await api.list_models()

    async def ask(
        self,
        user_id: int,
        question: str,
        repository: Optional[str] = None,
        wait_for_response: bool = True,
    ) -> str:
        """
        Ask a question using Cursor Cloud Agent.
        
        Args:
            user_id: Telegram user ID
            question: The question to ask
            repository: GitHub repository (optional)
            wait_for_response: Whether to wait for completion
            
        Returns:
            AI response or status message
        """
        if not self.is_configured:
            return (
                "❌ Cursor API 未設定\n\n"
                "請在 .env 中設定 CURSOR_API_KEY\n"
                "從 https://cursor.com/settings 獲取 API Key"
            )

        api = self._get_api()

        # Use default repo or require one
        repo = repository or self._default_repo
        if not repo:
            return (
                "❌ 需要指定 GitHub 倉庫\n\n"
                "請使用 /repo <url> 設定預設倉庫\n"
                "或使用 /ask <問題> -r <repo_url>"
            )

        try:
            # Check if user has an active agent
            if user_id in self._active_agents:
                agent_id = self._active_agents[user_id]
                try:
                    agent = await api.get_agent(agent_id)
                    if agent.status == "RUNNING":
                        # Send as follow-up
                        await api.send_followup(agent_id, question)
                        
                        if wait_for_response:
                            agent = await api.wait_for_completion(agent_id, timeout=120)
                            messages = await api.get_conversation(agent_id)
                            if messages:
                                return messages[-1].text
                        
                        return f"✅ 已發送後續問題到 Agent {agent_id}"
                except Exception:
                    # Agent not available, create new one
                    pass

            # Create new agent
            logger.info(f"Creating Cursor agent for user {user_id}")
            agent = await api.create_agent(
                prompt=question,
                repository=repo,
                name=f"TG-{user_id}-{datetime.now().strftime('%H%M%S')}",
            )

            self._active_agents[user_id] = agent.id
            logger.info(f"Created agent {agent.id} for user {user_id}")

            if wait_for_response:
                # Wait for completion
                agent = await api.wait_for_completion(agent.id, timeout=180)
                
                if agent.status == "FINISHED":
                    # Get the response
                    messages = await api.get_conversation(agent.id)
                    
                    # Find last assistant message
                    for msg in reversed(messages):
                        if msg.type == "assistant_message":
                            return msg.text
                    
                    return agent.summary or "（Agent 完成但無回覆）"
                else:
                    return f"❌ Agent 狀態: {agent.status}"
            else:
                return (
                    f"✅ Agent 已創建\n\n"
                    f"ID: <code>{agent.id}</code>\n"
                    f"狀態: {agent.status}\n\n"
                    f"使用 /agent {agent.id} 查看結果"
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"Cursor API error: {e}")
            if e.response.status_code == 401:
                return "❌ API Key 無效，請檢查 CURSOR_API_KEY"
            elif e.response.status_code == 429:
                return "❌ 請求過於頻繁，請稍後再試"
            else:
                return f"❌ API 錯誤: {e.response.status_code}"
        except TimeoutError:
            return "⏱️ Agent 執行超時，請使用 /agent 查看狀態"
        except Exception as e:
            logger.error(f"Cursor ask error: {e}")
            return f"❌ 錯誤: {str(e)}"

    async def get_agent_status(self, agent_id: str) -> str:
        """Get agent status formatted for Telegram."""
        api = self._get_api()
        
        try:
            agent = await api.get_agent(agent_id)
            
            status_emoji = {
                "PENDING": "⏳",
                "RUNNING": "🔄",
                "FINISHED": "✅",
                "FAILED": "❌",
                "STOPPED": "⏹️",
            }.get(agent.status, "❓")

            result = (
                f"<b>🤖 Agent 狀態</b>\n\n"
                f"ID: <code>{agent.id}</code>\n"
                f"名稱: {agent.name}\n"
                f"{status_emoji} 狀態: {agent.status}\n"
            )

            if agent.summary:
                result += f"\n<b>摘要:</b>\n{agent.summary[:500]}"

            if agent.status == "FINISHED":
                messages = await api.get_conversation(agent_id)
                if messages:
                    last_msg = messages[-1]
                    if last_msg.type == "assistant_message":
                        text = last_msg.text
                        if len(text) > 2000:
                            text = text[:2000] + "..."
                        result += f"\n\n<b>回覆:</b>\n{text}"

            return result

        except Exception as e:
            return f"❌ 無法獲取 Agent 狀態: {str(e)}"

    async def list_user_agents(self, user_id: int) -> str:
        """List agents (for info, not filtered by user)."""
        api = self._get_api()
        
        try:
            agents, _ = await api.list_agents(limit=10)
            
            if not agents:
                return "📋 沒有任何 Agent"

            lines = ["<b>📋 最近的 Agents</b>\n"]
            
            for agent in agents[:10]:
                status_emoji = {
                    "PENDING": "⏳",
                    "RUNNING": "🔄",
                    "FINISHED": "✅",
                    "FAILED": "❌",
                }.get(agent.status, "❓")
                
                lines.append(
                    f"{status_emoji} <code>{agent.id}</code>\n"
                    f"   {agent.name or '(無名稱)'}"
                )

            return "\n".join(lines)

        except Exception as e:
            return f"❌ 無法列出 Agents: {str(e)}"

    def set_default_repo(self, repo_url: str):
        """Set default repository for agents."""
        self._default_repo = repo_url
        logger.info(f"Set default repo: {repo_url}")

    def clear_user_agent(self, user_id: int):
        """Clear user's active agent."""
        self._active_agents.pop(user_id, None)


# Global instance
_cursor_ai: Optional[CursorAIManager] = None


def get_cursor_ai() -> CursorAIManager:
    """Get or create Cursor AI manager."""
    global _cursor_ai
    if _cursor_ai is None:
        _cursor_ai = CursorAIManager()
    return _cursor_ai


__all__ = [
    "CursorCloudAPI",
    "CursorAIManager",
    "CursorAgent",
    "get_cursor_ai",
]
