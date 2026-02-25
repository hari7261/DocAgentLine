"""HuggingFace Inference API provider."""

import json
import time
from typing import Any

import httpx

from docagentline.config import get_settings
from docagentline.observability import get_logger
from docagentline.services.llm.base import LLMProvider, LLMResponse
from docagentline.utils.errors import TransientExternalError, ModelOutputError

logger = get_logger(__name__)


class HuggingFaceProvider(LLMProvider):
    """HuggingFace Inference API provider."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate structured output using HuggingFace API."""
        start_time = time.time()

        system_prompt = (
            "You are a precise data extraction assistant. "
            "Extract information and return ONLY valid JSON conforming to the schema. "
            "No explanations, no markdown, just raw JSON."
        )

        schema_str = json.dumps(schema, indent=2)
        full_prompt = f"{system_prompt}\n\n{prompt}\n\nJSON Schema:\n{schema_str}\n\nJSON Output:"

        payload = {
            "inputs": full_prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
            },
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/models/{self.model}",
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
                    details={"status_code": response.status_code, "body": response.text},
                )
            elif response.status_code != 200:
                raise ModelOutputError(
                    f"API error: {response.status_code}",
                    details={"status_code": response.status_code, "body": response.text},
                )

            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                raw_response = data[0].get("generated_text", "")
            else:
                raw_response = data.get("generated_text", "")

            # Estimate tokens (rough approximation)
            tokens_in = len(full_prompt.split()) * 1.3
            tokens_out = len(raw_response.split()) * 1.3

            # Parse JSON
            parsed_json = None
            try:
                content = raw_response.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                parsed_json = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse JSON from model output",
                    extra={"error": str(e), "raw_response": raw_response[:500]},
                )
                raise ModelOutputError(
                    "Invalid JSON in model output",
                    details={"parse_error": str(e), "raw_response": raw_response[:500]},
                )

            return LLMResponse(
                raw_response=raw_response,
                parsed_json=parsed_json,
                tokens_in=int(tokens_in),
                tokens_out=int(tokens_out),
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
