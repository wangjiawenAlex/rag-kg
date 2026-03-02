# Database Initialization Script

# This script sets up the initial database schema
# Run this against PostgreSQL for initial setup

CREATE SCHEMA IF NOT EXISTS rag;

-- Users table
CREATE TABLE rag.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Sessions table
CREATE TABLE rag.sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES rag.users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_active_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ
);

-- Query logs table
CREATE TABLE rag.query_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES rag.users(user_id),
    session_id UUID REFERENCES rag.sessions(session_id),
    query_text TEXT NOT NULL,
    router_decision JSONB,
    latency_ms INTEGER,
    result_summary JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Documents metadata table
CREATE TABLE rag.documents_meta (
    doc_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT,
    published_at DATE,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_users_username ON rag.users(username);
CREATE INDEX idx_sessions_user_id ON rag.sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON rag.sessions(expires_at);
CREATE INDEX idx_query_logs_user_id ON rag.query_logs(user_id);
CREATE INDEX idx_query_logs_session_id ON rag.query_logs(session_id);
CREATE INDEX idx_query_logs_created_at ON rag.query_logs(created_at);
