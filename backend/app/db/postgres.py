"""Relational database client (SQLite-first for local development)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, DateTime, String, Text, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base


class PostgresClient:
    """Async relational DB client with SQLite default compatibility."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None

    async def initialize(self):
        """Initialize database engine/session factory and create tables."""
        self.engine = create_async_engine(self.database_url, future=True)
        self.SessionLocal = async_sessionmaker(bind=self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        """Close database connections."""
        if self.engine is not None:
            await self.engine.dispose()

    async def get_session(self) -> AsyncSession:
        """Get database session."""
        if self.SessionLocal is None:
            raise RuntimeError("Database client is not initialized")
        return self.SessionLocal()

    async def health_check(self) -> bool:
        """Check database connectivity."""
        if self.engine is None:
            return False
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


Base = declarative_base()


class User(Base):
    """User model."""

    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user")
    created_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    """Session model."""

    __tablename__ = "sessions"

    session_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime)


class QueryLog(Base):
    """Query log model."""

    __tablename__ = "query_logs"

    id = Column(String(255), primary_key=True)
    user_id = Column(String(64), nullable=False)
    session_id = Column(String(64))
    query_text = Column(Text, nullable=False)
    router_decision = Column(JSON)
    latency_ms = Column(String(255))
    result_summary = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentMeta(Base):
    """Document metadata model."""

    __tablename__ = "documents_meta"

    doc_id = Column(String(255), primary_key=True)
    title = Column(String(255))
    source = Column(String(255))
    published_at = Column(DateTime)
    metadata_json = Column("metadata", JSON)
