"""
Configuration management for Evergreen.

Uses pydantic-settings for type-safe configuration with environment variables.
"""

from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Application
    # ==========================================================================
    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"
    
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ==========================================================================
    # Authentication (JWT)
    # ==========================================================================
    jwt_secret_key: str = Field(default="change-me-in-production-use-openssl-rand-hex-32")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ==========================================================================
    # Azure AD / Microsoft 365
    # ==========================================================================
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_client_secret: str | None = None

    # ==========================================================================
    # Google Workspace
    # ==========================================================================
    google_service_account_json: str | None = None
    google_delegated_user: str | None = None

    # ==========================================================================
    # LLM Providers
    # ==========================================================================
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    cohere_api_key: str | None = None
    voyage_api_key: str | None = None

    # ==========================================================================
    # Infrastructure
    # ==========================================================================
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    
    falkordb_url: str = "redis://localhost:6379"
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    
    # Railway provides DATABASE_URL, support both postgres:// and postgresql://
    database_url: str = "postgresql://evergreen:evergreen@localhost:5432/evergreen"
    
    redis_url: str = "redis://localhost:6380"

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_postgres_scheme(cls, v: str) -> str:
        """Railway uses postgres:// but SQLAlchemy needs postgresql://"""
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @property
    def async_database_url(self) -> str:
        """Convert sync URL to async (postgresql+asyncpg://)"""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # ==========================================================================
    # Feature Flags
    # ==========================================================================
    enable_google_connector: bool = False
    enable_slack_connector: bool = False
    dry_run_mode: bool = False

    # ==========================================================================
    # Sync Settings
    # ==========================================================================
    initial_sync_lookback_days: int = 90
    incremental_sync_interval_minutes: int = 5
    max_concurrent_syncs: int = 3

    # ==========================================================================
    # Model Settings
    # ==========================================================================
    embedding_model: str = "voyage-3"
    embedding_dimensions: int = 1024
    llm_model: str = "claude-3-5-sonnet-latest"
    rerank_model: str = "rerank-v3.5"

    # ==========================================================================
    # Computed Properties
    # ==========================================================================
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def m365_configured(self) -> bool:
        return all([
            self.azure_tenant_id,
            self.azure_client_id,
            self.azure_client_secret,
        ])

    @property
    def google_configured(self) -> bool:
        return all([
            self.google_service_account_json,
            self.google_delegated_user,
        ])


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
