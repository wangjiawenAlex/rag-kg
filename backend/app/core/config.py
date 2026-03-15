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
    database_url: str = "postgresql://postgres:example@localhost:5432/ragdb"
    neo4j_url: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "test"
    
    # Vector DB
    vector_db_type: str = "milvus"  # milvus, chroma, faiss, weaviate
    vector_db_url: str = "http://localhost:19530"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    
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
