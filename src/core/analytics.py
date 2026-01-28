"""
Analytics Module for CursorBot

Provides usage analytics, statistics, and insights.

Features:
- Message and command tracking
- User activity analytics
- LLM usage statistics
- Performance metrics
- Cost estimation
- Export capabilities

Usage:
    from src.core.analytics import get_analytics, track_event, EventType
    
    analytics = get_analytics()
    
    # Track events
    analytics.track(EventType.MESSAGE, user_id="123", data={"text": "hello"})
    analytics.track(EventType.COMMAND, user_id="123", data={"command": "/help"})
    
    # Get statistics
    stats = analytics.get_user_stats("123")
    daily_stats = analytics.get_daily_stats()
    
    # Export data
    analytics.export_to_json("analytics.json")
"""

import json
import os
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union
import asyncio

from ..utils.logger import logger


# ============================================
# Event Types
# ============================================

class EventType(Enum):
    """Types of trackable events."""
    # User interactions
    MESSAGE = "message"
    COMMAND = "command"
    CALLBACK = "callback"
    VOICE = "voice"
    IMAGE = "image"
    FILE = "file"
    
    # AI interactions
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    RAG_QUERY = "rag_query"
    AGENT_RUN = "agent_run"
    
    # System events
    ERROR = "error"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    
    # Workflow events
    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"
    
    # MCP events
    MCP_TOOL_CALL = "mcp_tool_call"
    MCP_RESOURCE_READ = "mcp_resource_read"


@dataclass
class Event:
    """Represents an analytics event."""
    id: str
    type: EventType
    timestamp: datetime
    user_id: Optional[str] = None
    chat_id: Optional[str] = None
    platform: Optional[str] = None
    data: dict = field(default_factory=dict)
    
    # Metrics
    duration_ms: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "platform": self.platform,
            "data": self.data,
            "duration_ms": self.duration_ms,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost": self.cost,
        }


@dataclass
class UserStats:
    """Statistics for a single user."""
    user_id: str
    total_messages: int = 0
    total_commands: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    favorite_commands: dict = field(default_factory=dict)
    platforms_used: set = field(default_factory=set)
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "total_messages": self.total_messages,
            "total_commands": self.total_commands,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "favorite_commands": self.favorite_commands,
            "platforms_used": list(self.platforms_used),
        }


@dataclass
class DailyStats:
    """Daily aggregate statistics."""
    date: str
    total_events: int = 0
    total_messages: int = 0
    total_commands: int = 0
    total_llm_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    unique_users: int = 0
    avg_response_time_ms: float = 0.0
    errors: int = 0
    
    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "total_events": self.total_events,
            "total_messages": self.total_messages,
            "total_commands": self.total_commands,
            "total_llm_requests": self.total_llm_requests,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "unique_users": self.unique_users,
            "avg_response_time_ms": self.avg_response_time_ms,
            "errors": self.errors,
        }


# ============================================
# Cost Estimation
# ============================================

class CostEstimator:
    """Estimate costs for LLM usage."""
    
    # Pricing per 1M tokens (approximate, as of 2024)
    PRICING = {
        # OpenAI
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        
        # Anthropic
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-3.5-sonnet": {"input": 3.0, "output": 15.0},
        
        # Google
        "gemini-pro": {"input": 0.5, "output": 1.5},
        "gemini-1.5-pro": {"input": 3.5, "output": 10.5},
        "gemini-1.5-flash": {"input": 0.35, "output": 1.05},
        
        # Default (free/local)
        "default": {"input": 0.0, "output": 0.0},
    }
    
    @classmethod
    def estimate(cls, model: str, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost for token usage."""
        # Find matching pricing
        pricing = cls.PRICING.get("default")
        for model_name, model_pricing in cls.PRICING.items():
            if model_name in model.lower():
                pricing = model_pricing
                break
        
        cost_in = (tokens_in / 1_000_000) * pricing["input"]
        cost_out = (tokens_out / 1_000_000) * pricing["output"]
        
        return round(cost_in + cost_out, 6)


# ============================================
# Analytics Storage
# ============================================

class AnalyticsStorage:
    """SQLite-based storage for analytics data."""
    
    def __init__(self, db_path: str = "data/analytics.db"):
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                chat_id TEXT,
                platform TEXT,
                data TEXT,
                duration_ms INTEGER,
                tokens_in INTEGER,
                tokens_out INTEGER,
                cost REAL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)")
        
        conn.commit()
        conn.close()
    
    def save_event(self, event: Event) -> None:
        """Save an event to storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO events (id, type, timestamp, user_id, chat_id, platform, data, 
                               duration_ms, tokens_in, tokens_out, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.id,
            event.type.value,
            event.timestamp.isoformat(),
            event.user_id,
            event.chat_id,
            event.platform,
            json.dumps(event.data),
            event.duration_ms,
            event.tokens_in,
            event.tokens_out,
            event.cost,
        ))
        
        conn.commit()
        conn.close()
    
    def get_events(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        event_type: EventType = None,
        user_id: str = None,
        limit: int = 1000,
    ) -> list[Event]:
        """Query events from storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        if event_type:
            query += " AND type = ?"
            params.append(event_type.value)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        events = []
        for row in rows:
            events.append(Event(
                id=row[0],
                type=EventType(row[1]),
                timestamp=datetime.fromisoformat(row[2]),
                user_id=row[3],
                chat_id=row[4],
                platform=row[5],
                data=json.loads(row[6]) if row[6] else {},
                duration_ms=row[7],
                tokens_in=row[8],
                tokens_out=row[9],
                cost=row[10],
            ))
        
        return events
    
    def get_daily_aggregates(self, days: int = 30) -> list[dict]:
        """Get daily aggregated statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT 
                date(timestamp) as date,
                COUNT(*) as total_events,
                COUNT(CASE WHEN type = 'message' THEN 1 END) as messages,
                COUNT(CASE WHEN type = 'command' THEN 1 END) as commands,
                COUNT(CASE WHEN type = 'llm_request' THEN 1 END) as llm_requests,
                SUM(COALESCE(tokens_in, 0) + COALESCE(tokens_out, 0)) as total_tokens,
                SUM(COALESCE(cost, 0)) as total_cost,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(duration_ms) as avg_duration,
                COUNT(CASE WHEN type = 'error' THEN 1 END) as errors
            FROM events
            WHERE timestamp >= ?
            GROUP BY date(timestamp)
            ORDER BY date DESC
        """, (start_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "date": row[0],
                "total_events": row[1],
                "messages": row[2],
                "commands": row[3],
                "llm_requests": row[4],
                "total_tokens": row[5] or 0,
                "total_cost": row[6] or 0.0,
                "unique_users": row[7],
                "avg_duration_ms": row[8] or 0.0,
                "errors": row[9],
            }
            for row in rows
        ]
    
    def get_user_aggregates(self, limit: int = 100) -> list[dict]:
        """Get per-user aggregated statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                user_id,
                COUNT(*) as total_events,
                COUNT(CASE WHEN type = 'message' THEN 1 END) as messages,
                COUNT(CASE WHEN type = 'command' THEN 1 END) as commands,
                SUM(COALESCE(tokens_in, 0) + COALESCE(tokens_out, 0)) as total_tokens,
                SUM(COALESCE(cost, 0)) as total_cost,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM events
            WHERE user_id IS NOT NULL
            GROUP BY user_id
            ORDER BY total_events DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "user_id": row[0],
                "total_events": row[1],
                "messages": row[2],
                "commands": row[3],
                "total_tokens": row[4] or 0,
                "total_cost": row[5] or 0.0,
                "first_seen": row[6],
                "last_seen": row[7],
            }
            for row in rows
        ]


# ============================================
# Analytics Manager
# ============================================

class AnalyticsManager:
    """
    Main analytics manager.
    Handles event tracking, statistics, and reporting.
    """
    
    def __init__(self, db_path: str = "data/analytics.db"):
        self._storage = AnalyticsStorage(db_path)
        self._event_counter = 0
        
        # In-memory cache for real-time stats
        self._cache = {
            "today_events": 0,
            "today_tokens": 0,
            "today_cost": 0.0,
            "active_users": set(),
        }
        self._cache_date = datetime.now().date()
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        self._event_counter += 1
        return f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._event_counter:06d}"
    
    def _reset_cache_if_needed(self) -> None:
        """Reset daily cache if date changed."""
        today = datetime.now().date()
        if today != self._cache_date:
            self._cache = {
                "today_events": 0,
                "today_tokens": 0,
                "today_cost": 0.0,
                "active_users": set(),
            }
            self._cache_date = today
    
    def track(
        self,
        event_type: EventType,
        user_id: str = None,
        chat_id: str = None,
        platform: str = None,
        data: dict = None,
        duration_ms: int = None,
        tokens_in: int = None,
        tokens_out: int = None,
        model: str = None,
    ) -> Event:
        """
        Track an analytics event.
        
        Args:
            event_type: Type of event
            user_id: User identifier
            chat_id: Chat/channel identifier
            platform: Platform (telegram, discord, etc.)
            data: Additional event data
            duration_ms: Duration in milliseconds
            tokens_in: Input tokens (for LLM events)
            tokens_out: Output tokens (for LLM events)
            model: Model name (for cost estimation)
            
        Returns:
            Created Event object
        """
        self._reset_cache_if_needed()
        
        # Calculate cost if tokens provided
        cost = None
        if tokens_in is not None and tokens_out is not None and model:
            cost = CostEstimator.estimate(model, tokens_in, tokens_out)
        
        # Create event
        event = Event(
            id=self._generate_event_id(),
            type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            chat_id=chat_id,
            platform=platform,
            data=data or {},
            duration_ms=duration_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
        )
        
        # Save to storage
        try:
            self._storage.save_event(event)
        except Exception as e:
            logger.error(f"Failed to save analytics event: {e}")
        
        # Update cache
        self._cache["today_events"] += 1
        if tokens_in:
            self._cache["today_tokens"] += tokens_in
        if tokens_out:
            self._cache["today_tokens"] += tokens_out
        if cost:
            self._cache["today_cost"] += cost
        if user_id:
            self._cache["active_users"].add(user_id)
        
        return event
    
    def track_llm_request(
        self,
        user_id: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        duration_ms: int,
        platform: str = None,
        prompt: str = None,
    ) -> Event:
        """Convenience method for tracking LLM requests."""
        return self.track(
            event_type=EventType.LLM_REQUEST,
            user_id=user_id,
            platform=platform,
            data={
                "model": model,
                "prompt_preview": prompt[:100] if prompt else None,
            },
            duration_ms=duration_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=model,
        )
    
    def track_command(
        self,
        user_id: str,
        command: str,
        platform: str = None,
        args: list = None,
    ) -> Event:
        """Convenience method for tracking commands."""
        return self.track(
            event_type=EventType.COMMAND,
            user_id=user_id,
            platform=platform,
            data={
                "command": command,
                "args": args,
            },
        )
    
    def track_error(
        self,
        error: str,
        user_id: str = None,
        platform: str = None,
        context: dict = None,
    ) -> Event:
        """Convenience method for tracking errors."""
        return self.track(
            event_type=EventType.ERROR,
            user_id=user_id,
            platform=platform,
            data={
                "error": error,
                "context": context,
            },
        )
    
    # ============================================
    # Statistics Methods
    # ============================================
    
    def get_today_stats(self) -> dict:
        """Get real-time today's statistics."""
        self._reset_cache_if_needed()
        return {
            "date": str(self._cache_date),
            "events": self._cache["today_events"],
            "tokens": self._cache["today_tokens"],
            "cost": round(self._cache["today_cost"], 4),
            "active_users": len(self._cache["active_users"]),
        }
    
    def get_daily_stats(self, days: int = 30) -> list[DailyStats]:
        """Get daily statistics for the past N days."""
        aggregates = self._storage.get_daily_aggregates(days)
        return [
            DailyStats(
                date=agg["date"],
                total_events=agg["total_events"],
                total_messages=agg["messages"],
                total_commands=agg["commands"],
                total_llm_requests=agg["llm_requests"],
                total_tokens=agg["total_tokens"],
                total_cost=agg["total_cost"],
                unique_users=agg["unique_users"],
                avg_response_time_ms=agg["avg_duration_ms"],
                errors=agg["errors"],
            )
            for agg in aggregates
        ]
    
    def get_user_stats(self, user_id: str) -> Optional[UserStats]:
        """Get statistics for a specific user."""
        events = self._storage.get_events(user_id=user_id, limit=10000)
        
        if not events:
            return None
        
        stats = UserStats(user_id=user_id)
        command_counts = defaultdict(int)
        
        for event in events:
            if event.type == EventType.MESSAGE:
                stats.total_messages += 1
            elif event.type == EventType.COMMAND:
                stats.total_commands += 1
                cmd = event.data.get("command", "unknown")
                command_counts[cmd] += 1
            
            if event.tokens_in:
                stats.total_tokens += event.tokens_in
            if event.tokens_out:
                stats.total_tokens += event.tokens_out
            if event.cost:
                stats.total_cost += event.cost
            if event.platform:
                stats.platforms_used.add(event.platform)
            
            if stats.first_seen is None or event.timestamp < stats.first_seen:
                stats.first_seen = event.timestamp
            if stats.last_seen is None or event.timestamp > stats.last_seen:
                stats.last_seen = event.timestamp
        
        stats.favorite_commands = dict(
            sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        return stats
    
    def get_top_users(self, limit: int = 10) -> list[dict]:
        """Get top users by activity."""
        return self._storage.get_user_aggregates(limit)
    
    def get_events(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        event_type: EventType = None,
        user_id: str = None,
        limit: int = 100,
    ) -> list[Event]:
        """Query events with filters."""
        return self._storage.get_events(
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            user_id=user_id,
            limit=limit,
        )
    
    def get_summary(self) -> dict:
        """Get overall analytics summary."""
        today = self.get_today_stats()
        daily = self.get_daily_stats(30)
        
        # Calculate totals
        total_events = sum(d.total_events for d in daily)
        total_tokens = sum(d.total_tokens for d in daily)
        total_cost = sum(d.total_cost for d in daily)
        total_users = len(set(
            u["user_id"] for u in self._storage.get_user_aggregates(1000)
        ))
        
        return {
            "today": today,
            "last_30_days": {
                "total_events": total_events,
                "total_tokens": total_tokens,
                "total_cost": round(total_cost, 4),
                "total_users": total_users,
                "avg_daily_events": total_events / 30 if daily else 0,
            },
            "top_users": self.get_top_users(5),
        }
    
    # ============================================
    # Export Methods
    # ============================================
    
    def export_to_json(
        self,
        output_path: str,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> str:
        """Export analytics data to JSON file."""
        events = self._storage.get_events(
            start_date=start_date,
            end_date=end_date,
            limit=100000,
        )
        
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_events": len(events),
            "events": [e.to_dict() for e in events],
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def export_to_csv(
        self,
        output_path: str,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> str:
        """Export analytics data to CSV file."""
        import csv
        
        events = self._storage.get_events(
            start_date=start_date,
            end_date=end_date,
            limit=100000,
        )
        
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "type", "timestamp", "user_id", "chat_id", "platform",
                "duration_ms", "tokens_in", "tokens_out", "cost"
            ])
            
            for event in events:
                writer.writerow([
                    event.id,
                    event.type.value,
                    event.timestamp.isoformat(),
                    event.user_id,
                    event.chat_id,
                    event.platform,
                    event.duration_ms,
                    event.tokens_in,
                    event.tokens_out,
                    event.cost,
                ])
        
        return output_path


# ============================================
# Global Instance
# ============================================

_analytics: Optional[AnalyticsManager] = None


def get_analytics(db_path: str = None) -> AnalyticsManager:
    """Get the global analytics manager instance."""
    global _analytics
    
    if _analytics is None:
        path = db_path or os.getenv("ANALYTICS_DB_PATH", "data/analytics.db")
        _analytics = AnalyticsManager(path)
    
    return _analytics


def track_event(
    event_type: EventType,
    user_id: str = None,
    **kwargs
) -> Event:
    """Convenience function to track an event."""
    return get_analytics().track(event_type, user_id=user_id, **kwargs)


def reset_analytics() -> None:
    """Reset the analytics manager instance."""
    global _analytics
    _analytics = None


__all__ = [
    # Types
    "EventType",
    "Event",
    "UserStats",
    "DailyStats",
    # Cost estimation
    "CostEstimator",
    # Storage
    "AnalyticsStorage",
    # Manager
    "AnalyticsManager",
    "get_analytics",
    "track_event",
    "reset_analytics",
]
