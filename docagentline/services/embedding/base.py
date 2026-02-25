"""Base embedding provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmbeddingResponse:
    """Embedding response container."""

    vectors: list[list[float]]
    tokens_used: int
    latency_ms: float
    provider_metadata: dict


class EmbeddingProvider(ABC):
    """Abstract embedding provider interface."""

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> EmbeddingResponse:
        """Generate embeddings for batch of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            EmbeddingResponse with vectors and metadata

        Raises:
            TransientExternalError: For retryable errors
            EmbeddingError: For non-retryable errors
        """
        pass

    @abstractmethod
    async def close(self):
        """Close provider resources."""
        pass
