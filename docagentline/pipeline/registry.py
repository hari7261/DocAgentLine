"""Stage registry for pipeline."""

from typing import Protocol


class PipelineStage(Protocol):
    """Protocol for pipeline stages."""

    async def execute(self, document_id: int) -> None:
        """Execute stage for document."""
        ...


class StageRegistry:
    """Registry for pipeline stages."""

    def __init__(self):
        self._stages: dict[str, PipelineStage] = {}
        self._order: list[str] = [
            "ingest",
            "text_extraction",
            "layout_normalization",
            "chunking",
            "embedding",
            "structured_extraction",
            "validation",
            "persistence",
            "metrics_and_audit",
        ]

    def register(self, name: str, stage: PipelineStage):
        """Register a stage."""
        self._stages[name] = stage

    def get_stage(self, name: str) -> PipelineStage:
        """Get stage by name."""
        return self._stages[name]

    def get_ordered_stages(self) -> list[str]:
        """Get stages in execution order."""
        return self._order.copy()
