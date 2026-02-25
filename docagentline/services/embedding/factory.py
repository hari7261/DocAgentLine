"""Embedding provider factory."""

from docagentline.config import get_settings
from docagentline.services.embedding.base import EmbeddingProvider
from docagentline.services.embedding.openai_provider import OpenAIEmbeddingProvider
from docagentline.services.embedding.huggingface_provider import HuggingFaceEmbeddingProvider
from docagentline.utils.errors import ConfigurationError


def get_embedding_provider() -> EmbeddingProvider:
    """Get embedding provider instance based on configuration."""
    settings = get_settings()

    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider()
    elif settings.embedding_provider == "huggingface":
        return HuggingFaceEmbeddingProvider()
    else:
        raise ConfigurationError(
            f"Unknown embedding provider: {settings.embedding_provider}",
            details={"provider": settings.embedding_provider},
        )
