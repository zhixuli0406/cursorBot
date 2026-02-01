-- CursorBot PostgreSQL Initialization Script
-- Creates tables for conversation RAG with pgvector

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema for CursorBot
CREATE SCHEMA IF NOT EXISTS cursorbot;

-- Conversation messages table
-- Stores all conversation history with embeddings
CREATE TABLE IF NOT EXISTS cursorbot.conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    session_id VARCHAR(64),
    role VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI text-embedding-3-small dimension
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON cursorbot.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON cursorbot.conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON cursorbot.conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_user_time ON cursorbot.conversations(user_id, created_at DESC);

-- Create vector similarity search index (HNSW for better performance)
CREATE INDEX IF NOT EXISTS idx_conversations_embedding ON cursorbot.conversations 
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- User preferences table
CREATE TABLE IF NOT EXISTS cursorbot.user_preferences (
    user_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128),
    secretary_name VARCHAR(64) DEFAULT '小雅',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User tasks table
CREATE TABLE IF NOT EXISTS cursorbot.tasks (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    description TEXT,
    priority VARCHAR(16) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status VARCHAR(16) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    due_date TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON cursorbot.tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON cursorbot.tasks(user_id, status);

-- Learned patterns table (for RAG optimization)
-- Stores successful interaction patterns to improve future responses
CREATE TABLE IF NOT EXISTS cursorbot.learned_patterns (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64),  -- NULL for global patterns
    pattern_type VARCHAR(32) NOT NULL,  -- 'intent', 'preference', 'correction', 'feedback'
    trigger_text TEXT,
    response_pattern TEXT,
    embedding vector(1536),
    confidence FLOAT DEFAULT 0.5,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_learned_patterns_user ON cursorbot.learned_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_learned_patterns_type ON cursorbot.learned_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_learned_patterns_embedding ON cursorbot.learned_patterns 
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Function to update timestamp
CREATE OR REPLACE FUNCTION cursorbot.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS conversations_updated_at ON cursorbot.conversations;
CREATE TRIGGER conversations_updated_at
    BEFORE UPDATE ON cursorbot.conversations
    FOR EACH ROW
    EXECUTE FUNCTION cursorbot.update_updated_at();

DROP TRIGGER IF EXISTS user_preferences_updated_at ON cursorbot.user_preferences;
CREATE TRIGGER user_preferences_updated_at
    BEFORE UPDATE ON cursorbot.user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION cursorbot.update_updated_at();

DROP TRIGGER IF EXISTS tasks_updated_at ON cursorbot.tasks;
CREATE TRIGGER tasks_updated_at
    BEFORE UPDATE ON cursorbot.tasks
    FOR EACH ROW
    EXECUTE FUNCTION cursorbot.update_updated_at();

-- Grant permissions (for cursorbot user)
GRANT ALL PRIVILEGES ON SCHEMA cursorbot TO cursorbot;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cursorbot TO cursorbot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA cursorbot TO cursorbot;

-- Print success message
DO $$
BEGIN
    RAISE NOTICE 'CursorBot database initialized successfully with pgvector support!';
END $$;
