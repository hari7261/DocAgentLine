"""LLM provider factory."""

from docagentline.config import get_settings
from docagentline.services.llm.base import LLMProvider
from docagentline.services.llm.openai_provider import OpenAIProvider
from docagentline.services.llm.huggingface_provider import HuggingFaceProvider
from docagentline.utils.errors import ConfigurationError


def get_llm_provider() -> LLMProvider:
    """Get LLM provider instance based on configuration."""
    settings = get_settings()

    if settings.llm_provider == "openai":
        return OpenAIProvider()
    elif settings.llm_provider == "huggingface":
        return HuggingFaceProvider()
    else:
        raise ConfigurationError(
            f"Unknown LLM provider: {settings.llm_provider}",
            details={"provider": settings.llm_provider},
        )
