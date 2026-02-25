"""Error model and exception hierarchy."""


class DocAgentLineError(Exception):
    """Base exception for all DocAgentLine errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class TransientExternalError(DocAgentLineError):
    """Transient external service error - should be retried."""

    pass


class ModelOutputError(DocAgentLineError):
    """LLM model output error - should not be retried."""

    pass


class SchemaValidationError(DocAgentLineError):
    """JSON schema validation error - should not be retried."""

    pass


class PipelineStateError(DocAgentLineError):
    """Pipeline state consistency error."""

    pass


class StorageError(DocAgentLineError):
    """Storage operation error."""

    pass


class ConfigurationError(DocAgentLineError):
    """Configuration error."""

    pass


class SchemaRegistryError(DocAgentLineError):
    """Schema registry error."""

    pass


class IngestionError(DocAgentLineError):
    """Document ingestion error."""

    pass


class ExtractionError(DocAgentLineError):
    """Text extraction error."""

    pass


class ChunkingError(DocAgentLineError):
    """Chunking error."""

    pass


class EmbeddingError(DocAgentLineError):
    """Embedding generation error."""

    pass


def is_retryable(error: Exception) -> bool:
    """Check if error should be retried."""
    return isinstance(error, TransientExternalError)


def classify_error(error: Exception) -> str:
    """Classify error type for logging and metrics."""
    if isinstance(error, TransientExternalError):
        return "transient_external"
    elif isinstance(error, ModelOutputError):
        return "model_output"
    elif isinstance(error, SchemaValidationError):
        return "schema_validation"
    elif isinstance(error, PipelineStateError):
        return "pipeline_state"
    elif isinstance(error, StorageError):
        return "storage"
    elif isinstance(error, ConfigurationError):
        return "configuration"
    elif isinstance(error, SchemaRegistryError):
        return "schema_registry"
    elif isinstance(error, IngestionError):
        return "ingestion"
    elif isinstance(error, ExtractionError):
        return "extraction"
    elif isinstance(error, ChunkingError):
        return "chunking"
    elif isinstance(error, EmbeddingError):
        return "embedding"
    else:
        return "unknown"
