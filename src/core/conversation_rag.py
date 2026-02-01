"""
Conversation RAG Module for CursorBot

Provides conversation memory with RAG (Retrieval-Augmented Generation)
to enable contextual, continuous conversations that improve over time.

Features:
- Store conversation history with embeddings
- Retrieve relevant past conversations for context
- Learn user preferences and patterns
- PostgreSQL + pgvector for production-grade storage

Usage:
    from src.core.conversation_rag import get_conversation_rag
    
    rag = get_conversation_rag()
    
    # Store a conversation turn
    await rag.store_message(user_id, "user", "查詢機票")
    await rag.store_message(user_id, "assistant", "好的，請問...")
    
    # Retrieve relevant context for new message
    context = await rag.get_relevant_context(user_id, "繼續查詢")
    
    # Learn from feedback
    await rag.learn_pattern(user_id, "booking", "機票", "flight booking intent")
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from ..utils.logger import logger


class PatternType(Enum):
    """Types of learned patterns."""
    INTENT = "intent"           # User intent patterns
    PREFERENCE = "preference"   # User preferences
    CORRECTION = "correction"   # User corrections
    FEEDBACK = "feedback"       # Positive/negative feedback
    TOPIC = "topic"            # Conversation topics


@dataclass
class ConversationMessage:
    """Represents a single conversation message."""
    user_id: str
    role: str  # "user", "assistant", "system"
    content: str
    session_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RelevantContext:
    """Context retrieved from conversation history."""
    messages: list[ConversationMessage]
    patterns: list[dict]
    summary: str
    total_found: int


@dataclass
class ConversationRAGConfig:
    """Configuration for Conversation RAG."""
    # Storage settings
    use_postgres: bool = True
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "cursorbot"
    postgres_user: str = "cursorbot"
    postgres_password: str = "cursorbot_secret"
    
    # Embedding settings
    embedding_provider: str = "openai"  # "openai", "google", "ollama"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    
    # Retrieval settings
    max_context_messages: int = 10
    similarity_threshold: float = 0.6
    recency_weight: float = 0.3  # Weight for recent messages
    
    # Memory management
    max_messages_per_user: int = 1000
    message_retention_days: int = 90


class ConversationRAG:
    """
    Conversation RAG manager.
    
    Handles storing, retrieving, and learning from conversations
    to provide contextual, improving responses.
    """
    
    def __init__(self, config: ConversationRAGConfig = None):
        self.config = config or ConversationRAGConfig()
        self._embedding_provider = None
        self._pg_pool = None
        self._initialized = False
        
        # In-memory cache for recent conversations (fallback)
        self._memory_cache: dict[str, list[ConversationMessage]] = {}
        self._max_cache_size = 50
    
    async def initialize(self) -> bool:
        """Initialize the RAG system."""
        if self._initialized:
            return True
        
        try:
            # Try to connect to PostgreSQL
            if self.config.use_postgres:
                await self._init_postgres()
            
            # Initialize embedding provider
            await self._init_embedding_provider()
            
            self._initialized = True
            logger.info("ConversationRAG initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ConversationRAG: {e}")
            logger.info("Falling back to in-memory storage")
            self._initialized = True  # Allow fallback mode
            return False
    
    async def _init_postgres(self):
        """Initialize PostgreSQL connection pool."""
        try:
            import asyncpg
            
            host = os.getenv("POSTGRES_HOST", self.config.postgres_host)
            port = int(os.getenv("POSTGRES_PORT", self.config.postgres_port))
            db = os.getenv("POSTGRES_DB", self.config.postgres_db)
            user = os.getenv("POSTGRES_USER", self.config.postgres_user)
            password = os.getenv("POSTGRES_PASSWORD", self.config.postgres_password)
            
            self._pg_pool = await asyncpg.create_pool(
                host=host,
                port=port,
                database=db,
                user=user,
                password=password,
                min_size=2,
                max_size=10,
            )
            logger.info(f"PostgreSQL pool connected: {host}:{port}/{db}")
            
        except ImportError:
            logger.warning("asyncpg not installed, using in-memory storage")
            self._pg_pool = None
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed: {e}, using in-memory storage")
            self._pg_pool = None
    
    async def _init_embedding_provider(self):
        """Initialize embedding provider."""
        try:
            from .rag import OpenAIEmbedding, GoogleEmbedding, OllamaEmbedding
            from ..utils.config import settings
            
            provider = os.getenv("RAG_EMBEDDING_PROVIDER", self.config.embedding_provider)
            model = os.getenv("RAG_EMBEDDING_MODEL", self.config.embedding_model)
            
            if provider == "openai":
                # Get API key from settings (properly loaded from .env)
                api_key = getattr(settings, 'openai_api_key', None) or os.getenv("OPENAI_API_KEY")
                self._embedding_provider = OpenAIEmbedding(api_key=api_key, model=model)
            elif provider == "google":
                api_key = getattr(settings, 'google_generative_ai_api_key', None) or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
                self._embedding_provider = GoogleEmbedding(api_key=api_key, model=model)
            elif provider == "ollama":
                self._embedding_provider = OllamaEmbedding(model=model)
            else:
                api_key = getattr(settings, 'openai_api_key', None) or os.getenv("OPENAI_API_KEY")
                self._embedding_provider = OpenAIEmbedding(api_key=api_key, model=model)
            
            logger.info(f"Embedding provider initialized: {provider}/{model}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize embedding provider: {e}")
            self._embedding_provider = None
    
    async def _get_embedding(self, text: str) -> Optional[list[float]]:
        """Get embedding for text."""
        if not self._embedding_provider:
            return None
        
        try:
            embeddings = await self._embedding_provider.embed([text])
            return embeddings[0] if embeddings else None
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return None
    
    async def store_message(
        self,
        user_id: str,
        role: str,
        content: str,
        session_id: str = None,
        metadata: dict = None,
    ) -> bool:
        """
        Store a conversation message.
        
        Args:
            user_id: User identifier
            role: Message role ("user", "assistant", "system")
            content: Message content
            session_id: Optional session identifier
            metadata: Additional metadata
            
        Returns:
            True if stored successfully
        """
        await self.initialize()
        
        # Get embedding
        embedding = await self._get_embedding(content)
        
        message = ConversationMessage(
            user_id=user_id,
            role=role,
            content=content,
            session_id=session_id,
            metadata=metadata or {},
            embedding=embedding,
        )
        
        # Store in PostgreSQL if available
        if self._pg_pool:
            try:
                async with self._pg_pool.acquire() as conn:
                    embedding_str = None
                    if embedding:
                        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                    
                    await conn.execute(
                        """
                        INSERT INTO cursorbot.conversations 
                        (user_id, session_id, role, content, embedding, metadata)
                        VALUES ($1, $2, $3, $4, $5::vector, $6::jsonb)
                        """,
                        user_id,
                        session_id,
                        role,
                        content,
                        embedding_str,
                        json.dumps(metadata or {}, ensure_ascii=False),
                    )
                    logger.debug(f"Stored message for user {user_id}: {role}")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to store message in PostgreSQL: {e}")
        
        # Fallback to in-memory cache
        if user_id not in self._memory_cache:
            self._memory_cache[user_id] = []
        
        self._memory_cache[user_id].append(message)
        
        # Limit cache size
        if len(self._memory_cache[user_id]) > self._max_cache_size:
            self._memory_cache[user_id] = self._memory_cache[user_id][-self._max_cache_size:]
        
        return True
    
    async def get_relevant_context(
        self,
        user_id: str,
        query: str,
        max_messages: int = None,
        include_patterns: bool = True,
    ) -> RelevantContext:
        """
        Retrieve relevant conversation context for a query.
        
        Uses semantic similarity to find relevant past conversations
        and combines with recent messages for context.
        
        Args:
            user_id: User identifier
            query: Current query to find context for
            max_messages: Maximum messages to return
            include_patterns: Whether to include learned patterns
            
        Returns:
            RelevantContext with messages and patterns
        """
        await self.initialize()
        
        max_messages = max_messages or self.config.max_context_messages
        messages = []
        patterns = []
        total_found = 0
        
        # Get query embedding for semantic search
        query_embedding = await self._get_embedding(query)
        
        if self._pg_pool and query_embedding:
            try:
                async with self._pg_pool.acquire() as conn:
                    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
                    
                    # Semantic search for similar conversations
                    rows = await conn.fetch(
                        """
                        SELECT id, role, content, metadata, created_at,
                               1 - (embedding <=> $1::vector) as similarity
                        FROM cursorbot.conversations
                        WHERE user_id = $2 
                          AND embedding IS NOT NULL
                          AND created_at > NOW() - INTERVAL '30 days'
                        ORDER BY embedding <=> $1::vector
                        LIMIT $3
                        """,
                        embedding_str,
                        user_id,
                        max_messages,
                    )
                    
                    for row in rows:
                        if row["similarity"] >= self.config.similarity_threshold:
                            msg = ConversationMessage(
                                user_id=user_id,
                                role=row["role"],
                                content=row["content"],
                                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                                created_at=row["created_at"],
                            )
                            messages.append(msg)
                    
                    total_found = len(rows)
                    
                    # Get recent messages for immediate context
                    recent_rows = await conn.fetch(
                        """
                        SELECT role, content, metadata, created_at
                        FROM cursorbot.conversations
                        WHERE user_id = $1
                        ORDER BY created_at DESC
                        LIMIT 5
                        """,
                        user_id,
                    )
                    
                    # Add recent messages not already in semantic results
                    existing_contents = {m.content for m in messages}
                    for row in reversed(recent_rows):  # Reverse to get chronological order
                        if row["content"] not in existing_contents:
                            msg = ConversationMessage(
                                user_id=user_id,
                                role=row["role"],
                                content=row["content"],
                                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                                created_at=row["created_at"],
                            )
                            messages.insert(0, msg)  # Add to beginning for recency
                    
                    # Get learned patterns if requested
                    if include_patterns:
                        pattern_rows = await conn.fetch(
                            """
                            SELECT pattern_type, trigger_text, response_pattern, confidence
                            FROM cursorbot.learned_patterns
                            WHERE (user_id = $1 OR user_id IS NULL)
                              AND embedding IS NOT NULL
                            ORDER BY embedding <=> $2::vector
                            LIMIT 3
                            """,
                            user_id,
                            embedding_str,
                        )
                        
                        for row in pattern_rows:
                            patterns.append({
                                "type": row["pattern_type"],
                                "trigger": row["trigger_text"],
                                "response": row["response_pattern"],
                                "confidence": row["confidence"],
                            })
                    
            except Exception as e:
                logger.error(f"Failed to retrieve context from PostgreSQL: {e}")
        
        # Fallback to in-memory cache
        if not messages and user_id in self._memory_cache:
            messages = self._memory_cache[user_id][-max_messages:]
            total_found = len(self._memory_cache[user_id])
        
        # Build summary
        summary = self._build_context_summary(messages, patterns)
        
        return RelevantContext(
            messages=messages,
            patterns=patterns,
            summary=summary,
            total_found=total_found,
        )
    
    def _build_context_summary(
        self,
        messages: list[ConversationMessage],
        patterns: list[dict],
    ) -> str:
        """Build a summary of the retrieved context."""
        if not messages and not patterns:
            return ""
        
        parts = []
        
        if messages:
            # Group messages by topic/session
            recent = messages[-5:] if len(messages) > 5 else messages
            
            parts.append("## 最近對話記錄")
            for msg in recent:
                role_label = "用戶" if msg.role == "user" else "秘書"
                content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                parts.append(f"- {role_label}: {content_preview}")
        
        if patterns:
            parts.append("\n## 已學習的偏好")
            for p in patterns:
                parts.append(f"- {p['type']}: {p.get('trigger', '')} -> {p.get('response', '')[:50]}")
        
        return "\n".join(parts)
    
    async def learn_pattern(
        self,
        user_id: str,
        pattern_type: str,
        trigger_text: str,
        response_pattern: str,
        confidence: float = 0.5,
        metadata: dict = None,
    ) -> bool:
        """
        Learn a new pattern from user interaction.
        
        Args:
            user_id: User identifier (None for global patterns)
            pattern_type: Type of pattern (intent, preference, correction, feedback)
            trigger_text: Text that triggers this pattern
            response_pattern: Associated response or action
            confidence: Initial confidence score (0-1)
            metadata: Additional metadata
            
        Returns:
            True if pattern stored successfully
        """
        await self.initialize()
        
        if not self._pg_pool:
            logger.warning("Pattern learning requires PostgreSQL")
            return False
        
        # Get embedding for trigger text
        embedding = await self._get_embedding(trigger_text)
        
        try:
            async with self._pg_pool.acquire() as conn:
                embedding_str = None
                if embedding:
                    embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                
                await conn.execute(
                    """
                    INSERT INTO cursorbot.learned_patterns 
                    (user_id, pattern_type, trigger_text, response_pattern, embedding, confidence, metadata)
                    VALUES ($1, $2, $3, $4, $5::vector, $6, $7::jsonb)
                    """,
                    user_id,
                    pattern_type,
                    trigger_text,
                    response_pattern,
                    embedding_str,
                    confidence,
                    json.dumps(metadata or {}, ensure_ascii=False),
                )
                
                logger.info(f"Learned pattern for user {user_id}: {pattern_type}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store pattern: {e}")
            return False
    
    async def update_pattern_confidence(
        self,
        pattern_id: int,
        delta: float,
    ) -> bool:
        """Update pattern confidence based on feedback."""
        if not self._pg_pool:
            return False
        
        try:
            async with self._pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE cursorbot.learned_patterns
                    SET confidence = GREATEST(0, LEAST(1, confidence + $1)),
                        usage_count = usage_count + 1,
                        last_used_at = NOW()
                    WHERE id = $2
                    """,
                    delta,
                    pattern_id,
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update pattern confidence: {e}")
            return False
    
    async def get_user_stats(self, user_id: str) -> dict:
        """Get conversation statistics for a user."""
        await self.initialize()
        
        stats = {
            "total_messages": 0,
            "user_messages": 0,
            "assistant_messages": 0,
            "learned_patterns": 0,
            "first_message": None,
            "last_message": None,
        }
        
        if self._pg_pool:
            try:
                async with self._pg_pool.acquire() as conn:
                    # Message counts
                    row = await conn.fetchrow(
                        """
                        SELECT 
                            COUNT(*) as total,
                            SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_count,
                            SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_count,
                            MIN(created_at) as first_message,
                            MAX(created_at) as last_message
                        FROM cursorbot.conversations
                        WHERE user_id = $1
                        """,
                        user_id,
                    )
                    
                    if row:
                        stats["total_messages"] = row["total"] or 0
                        stats["user_messages"] = row["user_count"] or 0
                        stats["assistant_messages"] = row["assistant_count"] or 0
                        stats["first_message"] = row["first_message"]
                        stats["last_message"] = row["last_message"]
                    
                    # Pattern counts
                    pattern_row = await conn.fetchrow(
                        """
                        SELECT COUNT(*) as count
                        FROM cursorbot.learned_patterns
                        WHERE user_id = $1 OR user_id IS NULL
                        """,
                        user_id,
                    )
                    stats["learned_patterns"] = pattern_row["count"] if pattern_row else 0
                    
            except Exception as e:
                logger.error(f"Failed to get user stats: {e}")
        
        # Fallback to memory cache
        if stats["total_messages"] == 0 and user_id in self._memory_cache:
            messages = self._memory_cache[user_id]
            stats["total_messages"] = len(messages)
            stats["user_messages"] = sum(1 for m in messages if m.role == "user")
            stats["assistant_messages"] = sum(1 for m in messages if m.role == "assistant")
        
        return stats
    
    async def cleanup_old_messages(self, days: int = None) -> int:
        """Remove old messages beyond retention period."""
        days = days or self.config.message_retention_days
        
        if not self._pg_pool:
            return 0
        
        try:
            async with self._pg_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM cursorbot.conversations
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    """,
                    days,
                )
                
                # Extract deleted count
                deleted = int(result.split()[-1]) if result else 0
                logger.info(f"Cleaned up {deleted} old messages")
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to cleanup messages: {e}")
            return 0
    
    async def close(self):
        """Close connections and cleanup."""
        if self._pg_pool:
            await self._pg_pool.close()
            self._pg_pool = None
        self._initialized = False


# Global instance
_conversation_rag: Optional[ConversationRAG] = None


def get_conversation_rag(config: ConversationRAGConfig = None) -> ConversationRAG:
    """Get the global ConversationRAG instance."""
    global _conversation_rag
    
    if _conversation_rag is None:
        # Load config from environment
        cfg = config or ConversationRAGConfig(
            use_postgres=os.getenv("POSTGRES_ENABLED", "true").lower() == "true",
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_db=os.getenv("POSTGRES_DB", "cursorbot"),
            postgres_user=os.getenv("POSTGRES_USER", "cursorbot"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", "cursorbot_secret"),
            embedding_provider=os.getenv("RAG_EMBEDDING_PROVIDER", "openai"),
            embedding_model=os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        
        _conversation_rag = ConversationRAG(cfg)
    
    return _conversation_rag


def reset_conversation_rag():
    """Reset the global ConversationRAG instance."""
    global _conversation_rag
    if _conversation_rag:
        asyncio.create_task(_conversation_rag.close())
    _conversation_rag = None


__all__ = [
    "PatternType",
    "ConversationMessage",
    "RelevantContext",
    "ConversationRAGConfig",
    "ConversationRAG",
    "get_conversation_rag",
    "reset_conversation_rag",
]
