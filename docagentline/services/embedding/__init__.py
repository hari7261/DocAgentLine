"""Embedding service abstraction."""

from docagentline.services.embedding.base import EmbeddingProvider, EmbeddingResponse
from docagentline.services.embedding.factory import get_embedding_provider

__all__ = ["EmbeddingProvider", "EmbeddingResponse", "get_embedding_provider"]
