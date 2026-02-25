"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    """LLM response container."""

    raw_response: str
    parsed_json: dict[str, Any] | None
    tokens_in: int
    tokens_out: int
    latency_ms: float
    provider_metadata: dict[str, Any]


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate structured output conforming to schema.

        Args:
            prompt: Input prompt
            schema: JSON schema for output
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with parsed JSON and metadata

        Raises:
            TransientExternalError: For retryable errors
            ModelOutputError: For non-retryable model errors
        """
        pass

    @abstractmethod
    async def close(self):
        """Close provider resources."""
        pass
