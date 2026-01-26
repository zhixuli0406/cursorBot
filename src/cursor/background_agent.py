"""
Cursor Background Agent API Client
Enables programmatic access to Cursor Background Composer

This module allows CursorBot to create and monitor background agent tasks
without requiring manual IDE interaction.

API Documentation: https://docs.cursor.com/background-agent/api
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx

from ..utils.logger import logger


class CursorBackgroundAgent:
    """
    Client for Cursor Background Agent API.
    
    Provides methods to:
    - Create background composer tasks
    - List and monitor task status
    - Get task results
    
    API Endpoint: https://api.cursor.com/v0/agents
    Authentication: Bearer token (API Key from Cursor Dashboard)
    """
    
    BASE_URL = "https://api.cursor.com"
    API_VERSION = "v0"
    
    def __init__(self, api_key: str):
        """
        Initialize the Background Agent client.
        
        Args:
            api_key: Cursor API key from https://cursor.com/dashboard?tab=background-agents
        """
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper headers."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                timeout=60.0,
                follow_redirects=True,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def test_connection(self) -> dict:
        """
        Test if the API key is valid by listing agents.
        
        Returns:
            dict with status and info
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/{self.API_VERSION}/agents")
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "user": "API Key Valid",
                    "message": "Connection successful",
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Invalid API Key",
                }
            else:
                return {
                    "success": False,
                    "message": f"API error: {response.status_code}",
                }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "message": str(e),
            }
    
    async def create_task(
        self,
        prompt: str,
        repo_url: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> dict:
        """
        Create a new background agent task.
        
        Args:
            prompt: The task description/prompt for the agent
            repo_url: Optional GitHub repository URL (e.g., https://github.com/user/repo)
            branch: Optional git branch name (default: main)
            
        Returns:
            dict with task info including agent_id
        """
        try:
            client = await self._get_client()
            
            # Build request payload according to Cursor API spec
            payload = {
                "prompt": {
                    "text": prompt,
                },
            }
            
            # Add repository source if provided
            if repo_url:
                payload["source"] = {
                    "repository": repo_url,
                    "ref": branch or "main",
                }
            
            logger.info(f"Creating background agent task: {prompt[:50]}...")
            
            response = await client.post(
                f"/{self.API_VERSION}/agents",
                json=payload,
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                agent_id = data.get("id") or data.get("agentId") or data.get("composerId")
                
                logger.info(f"Task created: {agent_id}")
                
                return {
                    "success": True,
                    "composer_id": agent_id,
                    "status": data.get("status", "created"),
                    "message": "Task created successfully",
                    "data": data,
                }
            else:
                error_text = response.text
                logger.error(f"Failed to create task: {response.status_code} - {error_text}")
                return {
                    "success": False,
                    "message": f"Failed: {response.status_code} - {error_text[:200]}",
                }
                
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return {
                "success": False,
                "message": str(e),
            }
    
    async def list_tasks(self, limit: int = 20) -> dict:
        """
        List background agent tasks.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            dict with list of tasks
        """
        try:
            client = await self._get_client()
            
            response = await client.get(
                f"/{self.API_VERSION}/agents",
                params={"limit": limit},
            )
            
            if response.status_code == 200:
                data = response.json()
                # Handle different response formats
                if isinstance(data, list):
                    tasks = data
                else:
                    tasks = data.get("agents", data.get("composers", data.get("tasks", [])))
                
                return {
                    "success": True,
                    "tasks": tasks,
                    "count": len(tasks),
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed: {response.status_code}",
                    "tasks": [],
                }
                
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return {
                "success": False,
                "message": str(e),
                "tasks": [],
            }
    
    async def get_task_details(self, agent_id: str) -> dict:
        """
        Get detailed information about a specific task.
        
        Args:
            agent_id: The agent/task ID
            
        Returns:
            dict with task details including status and output
        """
        try:
            client = await self._get_client()
            
            response = await client.get(
                f"/{self.API_VERSION}/agents/{agent_id}",
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse status and output from response
                status = data.get("status", "unknown")
                output = data.get("output", data.get("response", data.get("result", "")))
                
                # Check for completion indicators
                if status in ["completed", "finished", "done", "success"]:
                    status = "completed"
                elif status in ["running", "in_progress", "processing"]:
                    status = "running"
                elif status in ["failed", "error"]:
                    status = "failed"
                
                return {
                    "success": True,
                    "composer_id": agent_id,
                    "status": status,
                    "output": output,
                    "data": data,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed: {response.status_code}",
                }
                
        except Exception as e:
            logger.error(f"Error getting task details: {e}")
            return {
                "success": False,
                "message": str(e),
            }
    
    async def wait_for_completion(
        self,
        composer_id: str,
        timeout: int = 0,  # 0 = no timeout (infinite polling)
        poll_interval: int = 5,
        callback: Optional[callable] = None,
        status_update_interval: int = 60,  # Send status update every N seconds
    ) -> dict:
        """
        Wait for a task to complete with polling.
        
        Continuously polls until the task is completed or failed.
        No timeout by default - will keep polling until task finishes.
        
        Args:
            composer_id: The task/composer ID
            timeout: Maximum time to wait (0 = infinite, keep polling)
            poll_interval: Time between status checks
            callback: Optional async callback for status updates
            status_update_interval: Send periodic status updates every N seconds
            
        Returns:
            dict with final task status and output
        """
        start_time = asyncio.get_event_loop().time()
        last_status = None
        last_update_time = start_time
        poll_count = 0
        
        logger.info(f"Starting to poll task {composer_id} (timeout={timeout}, interval={poll_interval})")
        
        while True:
            poll_count += 1
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - start_time
            
            # Only apply timeout if explicitly set (> 0)
            if timeout > 0 and elapsed > timeout:
                logger.warning(f"Task {composer_id} timed out after {elapsed:.0f}s")
                return {
                    "success": False,
                    "composer_id": composer_id,
                    "status": "timeout",
                    "message": f"Task timed out after {timeout}s (still polling possible via /result)",
                    "elapsed": elapsed,
                }
            
            try:
                result = await self.get_task_details(composer_id)
            except Exception as e:
                logger.error(f"Error getting task details: {e}")
                # Don't fail immediately, retry on next poll
                await asyncio.sleep(poll_interval)
                continue
            
            if not result.get("success"):
                # API error - log but continue polling
                logger.warning(f"Task {composer_id} status check failed: {result.get('message')}")
                await asyncio.sleep(poll_interval)
                continue
            
            status = result.get("status", "unknown")
            
            # Notify callback of status change
            if callback and status != last_status:
                try:
                    await callback(composer_id, status, result, elapsed)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
            
            # Periodic status update callback (even if status hasn't changed)
            if callback and (current_time - last_update_time) >= status_update_interval:
                try:
                    await callback(composer_id, status, result, elapsed, periodic=True)
                except Exception as e:
                    logger.error(f"Periodic callback error: {e}")
                last_update_time = current_time
            
            last_status = status
            
            # Check if completed
            if status in ["completed", "finished", "done", "success"]:
                logger.info(f"Task {composer_id} completed after {elapsed:.0f}s ({poll_count} polls)")
                return {
                    "success": True,
                    "composer_id": composer_id,
                    "status": "completed",
                    "output": result.get("output", ""),
                    "data": result.get("data", {}),
                    "elapsed": elapsed,
                    "poll_count": poll_count,
                }
            
            # Check if failed
            if status in ["failed", "error", "cancelled"]:
                logger.info(f"Task {composer_id} failed with status {status} after {elapsed:.0f}s")
                return {
                    "success": False,
                    "composer_id": composer_id,
                    "status": status,
                    "message": result.get("output", "Task failed"),
                    "elapsed": elapsed,
                    "poll_count": poll_count,
                }
            
            # Log progress periodically
            if poll_count % 12 == 0:  # Every minute at 5s interval
                logger.info(f"Task {composer_id} still running: {status} (elapsed: {elapsed:.0f}s)")
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
    
    async def cancel_task(self, composer_id: str) -> dict:
        """
        Cancel a running task.
        
        Args:
            composer_id: The task/composer ID
            
        Returns:
            dict with cancellation result
        """
        try:
            client = await self._get_client()
            
            response = await client.post(
                f"/api/background-composer/{composer_id}/cancel",
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Task cancelled",
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed: {response.status_code}",
                }
                
        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return {
                "success": False,
                "message": str(e),
            }
    
    def _format_repo_info(self, repo: dict) -> dict:
        """
        Format repository information with consistent structure.
        
        Args:
            repo: Raw repository data from API
            
        Returns:
            Formatted repository info dict
        """
        # Extract owner from different possible formats
        owner = ""
        if isinstance(repo.get("owner"), dict):
            owner = repo.get("owner", {}).get("login", "")
        else:
            owner = repo.get("owner", "")
        
        # Extract name
        name = repo.get("name", "")
        
        # Construct full_name if not provided
        full_name = repo.get("full_name", "")
        if not full_name and owner and name:
            full_name = f"{owner}/{name}"
        elif not full_name and name:
            # Try to extract from URL if available
            url = repo.get("html_url", repo.get("url", ""))
            if "github.com/" in url:
                parts = url.split("github.com/")[-1].strip("/").split("/")
                if len(parts) >= 2:
                    full_name = f"{parts[0]}/{parts[1]}"
            if not full_name:
                full_name = name
        
        # If name is empty, extract from full_name
        if not name and full_name:
            name = full_name.split("/")[-1]
        
        # If owner is empty, extract from full_name
        if not owner and full_name and "/" in full_name:
            owner = full_name.split("/")[0]
        
        return {
            "id": repo.get("id", ""),
            "name": name,
            "full_name": full_name,
            "owner": owner,
            "url": repo.get("html_url", repo.get("url", "")),
            "description": repo.get("description", ""),
            "private": repo.get("private", False),
            "default_branch": repo.get("default_branch", "main"),
        }

    async def list_repositories(self) -> dict:
        """
        List all GitHub repositories connected to the Cursor account.
        
        Returns:
            dict with list of repositories
        """
        try:
            client = await self._get_client()
            
            # Try the repositories endpoint
            response = await client.get(f"/{self.API_VERSION}/repositories")
            
            if response.status_code == 200:
                data = response.json()
                # Handle different response formats
                if isinstance(data, list):
                    repos = data
                else:
                    repos = data.get("repositories", data.get("repos", []))
                
                # Format repository information using helper method
                formatted_repos = [self._format_repo_info(repo) for repo in repos]
                
                logger.info(f"Found {len(formatted_repos)} repositories")
                
                return {
                    "success": True,
                    "repositories": formatted_repos,
                    "count": len(formatted_repos),
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "API Key invalid or expired",
                    "repositories": [],
                }
            elif response.status_code == 404:
                # Try alternative endpoint
                return await self._list_repositories_alternative()
            else:
                return {
                    "success": False,
                    "message": f"Failed: {response.status_code} - {response.text[:200]}",
                    "repositories": [],
                }
                
        except Exception as e:
            logger.error(f"Error listing repositories: {e}")
            return {
                "success": False,
                "message": str(e),
                "repositories": [],
            }
    
    async def _list_repositories_alternative(self) -> dict:
        """
        Alternative method to get repositories using different API endpoints.
        
        Returns:
            dict with list of repositories
        """
        try:
            client = await self._get_client()
            
            # Try fetching from github integrations endpoint
            response = await client.get(f"/{self.API_VERSION}/github/repositories")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    repos = data
                else:
                    repos = data.get("repositories", data.get("repos", []))
                
                formatted_repos = []
                for repo in repos:
                    formatted_repos.append(self._format_repo_info(repo))
                
                return {
                    "success": True,
                    "repositories": formatted_repos,
                    "count": len(formatted_repos),
                }
            else:
                # If this also fails, try user endpoint
                response = await client.get(f"/{self.API_VERSION}/user/repos")
                
                if response.status_code == 200:
                    data = response.json()
                    repos = data if isinstance(data, list) else data.get("repos", [])
                    
                    formatted_repos = []
                    for repo in repos:
                        formatted_repos.append(self._format_repo_info(repo))
                    
                    return {
                        "success": True,
                        "repositories": formatted_repos,
                        "count": len(formatted_repos),
                    }
                
                return {
                    "success": False,
                    "message": "Unable to fetch repositories from API",
                    "repositories": [],
                }
                
        except Exception as e:
            logger.error(f"Error in alternative repositories fetch: {e}")
            return {
                "success": False,
                "message": str(e),
                "repositories": [],
            }


# Task tracking for Telegram integration
class TaskTracker:
    """
    Track background agent tasks for Telegram users.
    Maps Telegram user IDs to their active tasks.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the task tracker."""
        self.data_dir = data_dir or Path(__file__).parent.parent.parent / "data"
        self.tasks_file = self.data_dir / "background_tasks.json"
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.tasks_file.exists():
            self.tasks_file.write_text("{}")
    
    def _load_tasks(self) -> dict:
        """Load tasks from file."""
        try:
            return json.loads(self.tasks_file.read_text())
        except Exception:
            return {}
    
    def _save_tasks(self, tasks: dict):
        """Save tasks to file."""
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))
    
    def add_task(
        self,
        user_id: int,
        composer_id: str,
        prompt: str,
        chat_id: int,
    ) -> dict:
        """
        Add a new task for tracking.
        
        Args:
            user_id: Telegram user ID
            composer_id: Cursor composer/task ID
            prompt: The original prompt
            chat_id: Telegram chat ID for sending updates
            
        Returns:
            Task info dict
        """
        tasks = self._load_tasks()
        
        task_info = {
            "composer_id": composer_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "prompt": prompt,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        # Store by composer_id
        tasks[composer_id] = task_info
        self._save_tasks(tasks)
        
        return task_info
    
    def update_task(self, composer_id: str, status: str, output: str = "") -> bool:
        """
        Update task status.
        
        Args:
            composer_id: Task ID
            status: New status
            output: Task output/result
            
        Returns:
            True if updated successfully
        """
        tasks = self._load_tasks()
        
        if composer_id not in tasks:
            return False
        
        tasks[composer_id]["status"] = status
        tasks[composer_id]["updated_at"] = datetime.now().isoformat()
        
        if output:
            tasks[composer_id]["output"] = output
        
        self._save_tasks(tasks)
        return True
    
    def get_task(self, composer_id: str) -> Optional[dict]:
        """Get task by composer ID."""
        tasks = self._load_tasks()
        return tasks.get(composer_id)
    
    def get_user_tasks(self, user_id: int, status: Optional[str] = None) -> list:
        """
        Get all tasks for a user.
        
        Args:
            user_id: Telegram user ID
            status: Optional filter by status
            
        Returns:
            List of task dicts
        """
        tasks = self._load_tasks()
        user_tasks = [
            t for t in tasks.values()
            if t.get("user_id") == user_id
        ]
        
        if status:
            user_tasks = [t for t in user_tasks if t.get("status") == status]
        
        # Sort by created_at descending
        user_tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return user_tasks
    
    def get_pending_tasks(self) -> list:
        """Get all running/pending tasks."""
        tasks = self._load_tasks()
        return [
            t for t in tasks.values()
            if t.get("status") in ["running", "pending", "created"]
        ]
    
    def remove_task(self, composer_id: str) -> bool:
        """Remove a task from tracking."""
        tasks = self._load_tasks()
        if composer_id in tasks:
            del tasks[composer_id]
            self._save_tasks(tasks)
            return True
        return False


# Global instances
_agent_instance: Optional[CursorBackgroundAgent] = None
_tracker_instance: Optional[TaskTracker] = None


def get_background_agent(session_token: str) -> CursorBackgroundAgent:
    """Get or create the global Background Agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CursorBackgroundAgent(session_token)
    return _agent_instance


def get_task_tracker() -> TaskTracker:
    """Get or create the global Task Tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = TaskTracker()
    return _tracker_instance


__all__ = [
    "CursorBackgroundAgent",
    "TaskTracker",
    "get_background_agent",
    "get_task_tracker",
]
