"""
Memory System for CursorBot
Inspired by Clawd Bot's memory management

Provides persistent memory storage for:
- User preferences
- Conversation history
- Task history
- Custom facts/knowledge
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from ..utils.logger import logger

# Default data directory
DATA_DIR = Path("data")
MEMORY_DB = DATA_DIR / "memory.db"


class MemoryManager:
    """
    Manages persistent memory for users and conversations.

    Features:
    - User preferences (language, default repo, notifications)
    - Conversation history
    - Facts/knowledge base
    - Task statistics
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or MEMORY_DB
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database schema."""
        if self._initialized:
            return

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            # User preferences table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    language TEXT DEFAULT 'zh-TW',
                    default_repo TEXT,
                    notifications_enabled INTEGER DEFAULT 1,
                    custom_prompt TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # Memory/Facts table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    importance INTEGER DEFAULT 0,
                    created_at TEXT,
                    expires_at TEXT,
                    UNIQUE(user_id, key)
                )
            """)

            # Conversation history table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    chat_id INTEGER,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT
                )
            """)

            # Task statistics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS task_stats (
                    user_id INTEGER PRIMARY KEY,
                    total_tasks INTEGER DEFAULT 0,
                    completed_tasks INTEGER DEFAULT 0,
                    failed_tasks INTEGER DEFAULT 0,
                    total_tokens_used INTEGER DEFAULT 0,
                    last_task_at TEXT
                )
            """)

            await db.commit()

        self._initialized = True
        logger.info("Memory system initialized")

    # ============================================
    # User Preferences
    # ============================================

    async def get_user_preferences(self, user_id: int) -> dict:
        """Get user preferences."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()

            if row:
                return dict(row)
            return {
                "user_id": user_id,
                "language": "zh-TW",
                "default_repo": "",
                "notifications_enabled": True,
                "custom_prompt": "",
            }

    async def set_user_preference(
        self,
        user_id: int,
        key: str,
        value: Any,
        username: str = None
    ) -> None:
        """Set a user preference."""
        await self.initialize()

        now = datetime.now().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            # Check if user exists
            cursor = await db.execute(
                "SELECT user_id FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )
            exists = await cursor.fetchone()

            if exists:
                await db.execute(
                    f"UPDATE user_preferences SET {key} = ?, updated_at = ? WHERE user_id = ?",
                    (value, now, user_id)
                )
            else:
                await db.execute(
                    """INSERT INTO user_preferences 
                       (user_id, username, created_at, updated_at) 
                       VALUES (?, ?, ?, ?)""",
                    (user_id, username, now, now)
                )
                await db.execute(
                    f"UPDATE user_preferences SET {key} = ? WHERE user_id = ?",
                    (value, user_id)
                )

            await db.commit()

    async def get_default_repo(self, user_id: int) -> str:
        """Get user's default repository."""
        prefs = await self.get_user_preferences(user_id)
        return prefs.get("default_repo", "")

    async def set_default_repo(self, user_id: int, repo_url: str) -> None:
        """Set user's default repository."""
        await self.set_user_preference(user_id, "default_repo", repo_url)

    # ============================================
    # Memory/Facts
    # ============================================

    async def remember(
        self,
        user_id: int,
        key: str,
        value: Any,
        category: str = "general",
        importance: int = 0,
        expires_at: Optional[datetime] = None
    ) -> None:
        """
        Store a memory/fact for a user.

        Args:
            user_id: User ID
            key: Memory key (e.g., "favorite_language", "project_structure")
            value: Memory value (will be JSON serialized if not string)
            category: Category for organization
            importance: 0-10, higher = more important
            expires_at: Optional expiration datetime
        """
        await self.initialize()

        if not isinstance(value, str):
            value = json.dumps(value)

        now = datetime.now().isoformat()
        expires = expires_at.isoformat() if expires_at else None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO memories 
                   (user_id, key, value, category, importance, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, key, value, category, importance, now, expires)
            )
            await db.commit()

        logger.debug(f"Remembered [{key}] for user {user_id}")

    async def recall(
        self,
        user_id: int,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Recall a memory/fact for a user.

        Args:
            user_id: User ID
            key: Memory key
            default: Default value if not found

        Returns:
            The remembered value or default
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT value FROM memories 
                   WHERE user_id = ? AND key = ?
                   AND (expires_at IS NULL OR expires_at > ?)""",
                (user_id, key, datetime.now().isoformat())
            )
            row = await cursor.fetchone()

            if row:
                value = row[0]
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value

            return default

    async def forget(self, user_id: int, key: str) -> bool:
        """
        Forget a memory.

        Returns:
            True if memory was deleted, False if not found
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM memories WHERE user_id = ? AND key = ?",
                (user_id, key)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def list_memories(
        self,
        user_id: int,
        category: Optional[str] = None,
        limit: int = 50
    ) -> list[dict]:
        """List all memories for a user."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if category:
                cursor = await db.execute(
                    """SELECT key, value, category, importance, created_at 
                       FROM memories WHERE user_id = ? AND category = ?
                       ORDER BY importance DESC, created_at DESC LIMIT ?""",
                    (user_id, category, limit)
                )
            else:
                cursor = await db.execute(
                    """SELECT key, value, category, importance, created_at 
                       FROM memories WHERE user_id = ?
                       ORDER BY importance DESC, created_at DESC LIMIT ?""",
                    (user_id, limit)
                )

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def search_memories(
        self,
        user_id: int,
        query: str,
        limit: int = 10
    ) -> list[dict]:
        """Search memories by key or value."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT key, value, category, importance, created_at 
                   FROM memories WHERE user_id = ? 
                   AND (key LIKE ? OR value LIKE ?)
                   ORDER BY importance DESC LIMIT ?""",
                (user_id, f"%{query}%", f"%{query}%", limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ============================================
    # Conversation History
    # ============================================

    async def add_message(
        self,
        user_id: int,
        chat_id: int,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> None:
        """Add a message to conversation history."""
        await self.initialize()

        now = datetime.now().isoformat()
        meta_json = json.dumps(metadata) if metadata else None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO conversation_history 
                   (user_id, chat_id, role, content, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, chat_id, role, content, meta_json, now)
            )
            await db.commit()

    async def get_conversation_history(
        self,
        user_id: int,
        chat_id: int,
        limit: int = 20
    ) -> list[dict]:
        """Get recent conversation history."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT role, content, metadata, created_at 
                   FROM conversation_history 
                   WHERE user_id = ? AND chat_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (user_id, chat_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in reversed(rows)]

    async def clear_conversation_history(
        self,
        user_id: int,
        chat_id: int
    ) -> int:
        """Clear conversation history for a chat."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM conversation_history WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
            await db.commit()
            return cursor.rowcount

    # ============================================
    # Task Statistics
    # ============================================

    async def record_task(
        self,
        user_id: int,
        success: bool,
        tokens_used: int = 0
    ) -> None:
        """Record a task completion."""
        await self.initialize()

        now = datetime.now().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            # Check if user stats exist
            cursor = await db.execute(
                "SELECT user_id FROM task_stats WHERE user_id = ?",
                (user_id,)
            )
            exists = await cursor.fetchone()

            if exists:
                if success:
                    await db.execute(
                        """UPDATE task_stats SET 
                           total_tasks = total_tasks + 1,
                           completed_tasks = completed_tasks + 1,
                           total_tokens_used = total_tokens_used + ?,
                           last_task_at = ?
                           WHERE user_id = ?""",
                        (tokens_used, now, user_id)
                    )
                else:
                    await db.execute(
                        """UPDATE task_stats SET 
                           total_tasks = total_tasks + 1,
                           failed_tasks = failed_tasks + 1,
                           last_task_at = ?
                           WHERE user_id = ?""",
                        (now, user_id)
                    )
            else:
                await db.execute(
                    """INSERT INTO task_stats 
                       (user_id, total_tasks, completed_tasks, failed_tasks, 
                        total_tokens_used, last_task_at)
                       VALUES (?, 1, ?, ?, ?, ?)""",
                    (user_id, 1 if success else 0, 0 if success else 1, tokens_used, now)
                )

            await db.commit()

    async def get_task_stats(self, user_id: int) -> dict:
        """Get task statistics for a user."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM task_stats WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()

            if row:
                return dict(row)
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "total_tokens_used": 0,
                "last_task_at": None,
            }


# Global instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get the global MemoryManager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


__all__ = ["MemoryManager", "get_memory_manager"]
