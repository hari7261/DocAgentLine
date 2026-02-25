"""OpenAI embedding provider."""

import time

import httpx

from docagentline.config import get_settings
from docagentline.observability import get_logger
from docagentline.services.embedding.base import EmbeddingProvider, EmbeddingResponse
from docagentline.utils.errors import TransientExternalError, EmbeddingError

logger = get_logger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding API provider."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.embedding_base_url.rstrip("/")
        self.api_key = settings.embedding_api_key
        self.model = settings.embedding_model
        self.timeout = settings.embedding_timeout

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

    async def embed_batch(self, texts: list[str]) -> EmbeddingResponse:
        """Generate embeddings using OpenAI API."""
        start_time = time.time()

        payload = {
            "model": self.model,
            "input": texts,
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/embeddings",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )

            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 429:
                raise TransientExternalError(
                    "Rate limit exceeded",
                    details={"status_code": response.status_code},
                )
            elif response.status_code >= 500:
                raise TransientExternalError(
                    f"Server error: {response.status_code}",
                    details={"status_code": response.status_code},
                )
            elif response.status_code != 200:
                raise EmbeddingError(
                    f"API error: {response.status_code}",
                    details={"status_code": response.status_code, "body": response.text},
                )

            data = response.json()
            embeddings_data = sorted(data["data"], key=lambda x: x["index"])
            vectors = [item["embedding"] for item in embeddings_data]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)

            return EmbeddingResponse(
                vectors=vectors,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                provider_metadata={"model": self.model},
            )

        except httpx.TimeoutException:
            latency_ms = (time.time() - start_time) * 1000
            raise TransientExternalError(
                "Request timeout",
                details={"timeout": self.timeout, "latency_ms": latency_ms},
            )
        except httpx.NetworkError as e:
            latency_ms = (time.time() - start_time) * 1000
            raise TransientExternalError(
                "Network error",
                details={"error": str(e), "latency_ms": latency_ms},
            )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
