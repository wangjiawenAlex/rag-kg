"""
Application configuration and settings.

Loads configuration from environment variables and files.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # App info
    app_name: str = "RAG Dynamic Router"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./rag.db"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "testpass123"
    
    # Vector DB
    vector_db_type: str = "chroma"  # chroma
    vector_db_url: str = "./chroma_data"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    embedding_api_key: Optional[str] = None
    embedding_api_base: str = "https://api.openai.com/v1/embeddings"
    embedding_timeout_seconds: int = 30
    
    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    
    # Features
    enable_cache: bool = True
    cache_ttl_seconds: int = 300
    max_query_length: int = 5000
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # LLM Configuration (DeepSeek / 通义千问)
    llm_provider: str = "deepseek"  # deepseek, tongyi, openai
    llm_api_key: Optional[str] = None
    llm_api_base: Optional[str] = None
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
