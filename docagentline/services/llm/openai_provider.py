"""OpenAI-compatible LLM provider."""

import json
import time
from typing import Any

import httpx

from docagentline.config import get_settings
from docagentline.observability import get_logger
from docagentline.services.llm.base import LLMProvider, LLMResponse
from docagentline.utils.errors import TransientExternalError, ModelOutputError

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible HTTP API provider."""

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
        """Generate structured output using OpenAI API."""
        start_time = time.time()

        system_prompt = (
            "You are a precise data extraction assistant. "
            "Extract information from the provided text and return ONLY valid JSON "
            "that strictly conforms to the provided schema. "
            "Do not include any explanations, markdown formatting, or additional text. "
            "Return only the raw JSON object."
        )

        schema_str = json.dumps(schema, indent=2)
        full_prompt = f"{prompt}\n\nRequired JSON Schema:\n{schema_str}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
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
            raw_response = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)

            # Parse JSON from response
            parsed_json = None
            try:
                # Try to extract JSON if wrapped in markdown
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
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                provider_metadata={
                    "model": self.model,
                    "finish_reason": data["choices"][0].get("finish_reason"),
                },
            )

        except httpx.TimeoutException as e:
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
