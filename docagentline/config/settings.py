"""Application settings using pydantic-settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./docagentline.db",
        description="Database connection URL",
    )
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    database_echo: bool = Field(default=False)

    # LLM Provider
    llm_provider: Literal["openai", "huggingface"] = Field(default="openai")
    llm_base_url: str = Field(default="https://api.openai.com/v1")
    llm_api_key: str = Field(default="")
    llm_model: str = Field(default="gpt-4-turbo-preview")
    llm_timeout: int = Field(default=120, ge=1)
    llm_max_retries: int = Field(default=3, ge=0)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=4096, ge=1)

    # Embedding Provider
    embedding_provider: Literal["openai", "huggingface"] = Field(default="openai")
    embedding_base_url: str = Field(default="https://api.openai.com/v1")
    embedding_api_key: str = Field(default="")
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_batch_size: int = Field(default=100, ge=1)
    embedding_timeout: int = Field(default=60, ge=1)
    embedding_max_retries: int = Field(default=3, ge=0)

    # Pipeline
    pipeline_max_concurrent_stages: int = Field(default=4, ge=1)
    pipeline_max_concurrent_chunks: int = Field(default=10, ge=1)
    pipeline_stage_timeout: int = Field(default=3600, ge=1)
    pipeline_retry_backoff_base: float = Field(default=2.0, ge=1.0)
    pipeline_retry_backoff_max: float = Field(default=60.0, ge=1.0)
    pipeline_retry_jitter: bool = Field(default=True)

    # Chunking
    chunk_size: int = Field(default=1000, ge=100)
    chunk_overlap: int = Field(default=200, ge=0)
    chunk_min_size: int = Field(default=100, ge=1)

    # Schema Registry
    schema_registry_path: Path = Field(default=Path("./schemas"))

    # Storage
    storage_path: Path = Field(default=Path("./storage"))
    storage_hash_raw_content: bool = Field(default=False)
    storage_persist_prompts: bool = Field(default=True)
    storage_persist_raw_responses: bool = Field(default=True)
    storage_max_file_size_mb: int = Field(default=100, ge=1)

    # Security
    redact_fields: list[str] = Field(
        default_factory=lambda: ["ssn", "credit_card", "password"],
        description="Fields to redact from logs and output",
    )

    # Observability
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    enable_otel_tracing: bool = Field(default=False)
    otel_service_name: str = Field(default="docagentline")
    otel_exporter_endpoint: str = Field(default="")

    # Cost Calculation (USD per 1K tokens)
    cost_per_1k_input_tokens: float = Field(default=0.01)
    cost_per_1k_output_tokens: float = Field(default=0.03)
    cost_per_1k_embedding_tokens: float = Field(default=0.0001)

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_cors_origins: list[str] = Field(default_factory=list)
    api_max_upload_size_mb: int = Field(default=100, ge=1)

    def get_storage_path(self) -> Path:
        """Get storage path, creating if necessary."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        return self.storage_path

    def get_schema_registry_path(self) -> Path:
        """Get schema registry path."""
        return self.schema_registry_path


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
