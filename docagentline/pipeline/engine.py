"""Pipeline execution engine."""

import asyncio
import random
import time
from datetime import datetime
from typing import Any

from sqlalchemy import select, update, insert

from docagentline.config import get_settings
from docagentline.db import pipeline_runs, documents, metrics
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger
from docagentline.pipeline.registry import StageRegistry
from docagentline.utils.errors import (
    PipelineStateError,
    is_retryable,
    classify_error,
)

logger = get_logger(__name__)


class PipelineEngine:
    """Pipeline execution engine with resumability and idempotency."""

    def __init__(self):
        self.settings = get_settings()
        self.db_manager = DatabaseManager()
        self.registry = StageRegistry()
        self.max_retries = self.settings.llm_max_retries
        self.backoff_base = self.settings.pipeline_retry_backoff_base
        self.backoff_max = self.settings.pipeline_retry_backoff_max
        self.use_jitter = self.settings.pipeline_retry_jitter

    async def execute_pipeline(
        self,
        document_id: int,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute full pipeline for document.

        Args:
            document_id: Document ID
            correlation_id: Optional correlation ID for tracing

        Returns:
            Pipeline execution summary

        Raises:
            PipelineStateError: If pipeline state is inconsistent
        """
        logger.info(
            "Starting pipeline execution",
            extra={
                "document_id": document_id,
                "correlation_id": correlation_id,
            },
        )

        stages = self.registry.get_ordered_stages()
        results = {}

        for stage_name in stages:
            stage = self.registry.get_stage(stage_name)

            # Check if stage already completed successfully
            if await self._is_stage_completed(document_id, stage_name):
                logger.info(
                    "Stage already completed, skipping",
                    extra={
                        "document_id": document_id,
                        "stage": stage_name,
                    },
                )
                results[stage_name] = "skipped"
                continue

            # Execute stage with retry logic
            result = await self._execute_stage_with_retry(
                document_id=document_id,
                stage_name=stage_name,
                stage=stage,
                correlation_id=correlation_id,
            )

            results[stage_name] = result

        logger.info(
            "Pipeline execution completed",
            extra={
                "document_id": document_id,
                "correlation_id": correlation_id,
                "results": results,
            },
        )

        # Update document status
        async with self.db_manager.get_connection() as conn:
            await conn.execute(
                update(documents)
                .where(documents.c.id == document_id)
                .values(status="completed", updated_at=datetime.utcnow())
            )
            await conn.commit()

        return results

    async def _is_stage_completed(self, document_id: int, stage_name: str) -> bool:
        """Check if stage completed successfully."""
        async with self.db_manager.get_connection() as conn:
            result = await conn.execute(
                select(pipeline_runs)
                .where(
                    pipeline_runs.c.document_id == document_id,
                    pipeline_runs.c.stage == stage_name,
                    pipeline_runs.c.status == "completed",
                )
                .limit(1)
            )
            row = result.fetchone()
            return row is not None

    async def _execute_stage_with_retry(
        self,
        document_id: int,
        stage_name: str,
        stage: Any,
        correlation_id: str | None,
    ) -> str:
        """Execute stage with retry logic."""
        attempt = 1

        while attempt <= self.max_retries + 1:
            run_id = await self._create_run_record(
                document_id=document_id,
                stage_name=stage_name,
                attempt=attempt,
                correlation_id=correlation_id,
            )

            start_time = time.time()

            try:
                logger.info(
                    "Executing stage",
                    extra={
                        "document_id": document_id,
                        "stage": stage_name,
                        "attempt": attempt,
                        "run_id": run_id,
                    },
                )

                # Execute stage
                await stage.execute(document_id)

                latency_ms = (time.time() - start_time) * 1000

                # Mark as completed
                await self._complete_run_record(run_id, latency_ms)

                logger.info(
                    "Stage completed successfully",
                    extra={
                        "document_id": document_id,
                        "stage": stage_name,
                        "attempt": attempt,
                        "latency_ms": latency_ms,
                        "run_id": run_id,
                    },
                )

                return "completed"

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                error_type = classify_error(e)

                logger.error(
                    "Stage execution failed",
                    extra={
                        "document_id": document_id,
                        "stage": stage_name,
                        "attempt": attempt,
                        "error_type": error_type,
                        "error": str(e),
                        "run_id": run_id,
                    },
                    exc_info=True,
                )

                await self._fail_run_record(
                    run_id=run_id,
                    error_type=error_type,
                    error_message=str(e),
                    latency_ms=latency_ms,
                )

                # Check if retryable
                if not is_retryable(e):
                    logger.warning(
                        "Error not retryable, failing stage",
                        extra={
                            "document_id": document_id,
                            "stage": stage_name,
                            "error_type": error_type,
                        },
                    )
                    raise

                # Check if we should retry
                if attempt > self.max_retries:
                    logger.error(
                        "Max retries exceeded",
                        extra={
                            "document_id": document_id,
                            "stage": stage_name,
                            "attempts": attempt,
                        },
                    )
                    raise

                # Calculate backoff
                backoff = min(
                    self.backoff_base ** (attempt - 1),
                    self.backoff_max,
                )

                if self.use_jitter:
                    backoff = backoff * (0.5 + random.random())

                logger.info(
                    "Retrying stage after backoff",
                    extra={
                        "document_id": document_id,
                        "stage": stage_name,
                        "attempt": attempt,
                        "backoff_seconds": backoff,
                    },
                )

                await asyncio.sleep(backoff)
                attempt += 1

        raise PipelineStateError("Unexpected retry loop exit")

    async def _create_run_record(
        self,
        document_id: int,
        stage_name: str,
        attempt: int,
        correlation_id: str | None,
    ) -> int:
        """Create pipeline run record."""
        async with self.db_manager.get_connection() as conn:
            result = await conn.execute(
                insert(pipeline_runs).values(
                    document_id=document_id,
                    stage=stage_name,
                    status="running",
                    attempt=attempt,
                    started_at=datetime.utcnow(),
                    correlation_id=correlation_id,
                )
            )
            await conn.commit()
            return result.inserted_primary_key[0]

    async def _complete_run_record(self, run_id: int, latency_ms: float):
        """Mark run as completed."""
        async with self.db_manager.get_connection() as conn:
            await conn.execute(
                update(pipeline_runs)
                .where(pipeline_runs.c.id == run_id)
                .values(
                    status="completed",
                    finished_at=datetime.utcnow(),
                )
            )

            # Record metrics
            await conn.execute(
                insert(metrics).values(
                    run_id=run_id,
                    stage=await self._get_run_stage(conn, run_id),
                    latency_ms=latency_ms,
                    created_at=datetime.utcnow(),
                )
            )

            await conn.commit()

    async def _fail_run_record(
        self,
        run_id: int,
        error_type: str,
        error_message: str,
        latency_ms: float,
    ):
        """Mark run as failed."""
        async with self.db_manager.get_connection() as conn:
            await conn.execute(
                update(pipeline_runs)
                .where(pipeline_runs.c.id == run_id)
                .values(
                    status="failed",
                    error_type=error_type,
                    error_message=error_message[:1000],
                    finished_at=datetime.utcnow(),
                )
            )

            # Record metrics
            await conn.execute(
                insert(metrics).values(
                    run_id=run_id,
                    stage=await self._get_run_stage(conn, run_id),
                    latency_ms=latency_ms,
                    created_at=datetime.utcnow(),
                )
            )

            await conn.commit()

    async def _get_run_stage(self, conn, run_id: int) -> str:
        """Get stage name for run."""
        result = await conn.execute(
            select(pipeline_runs.c.stage).where(pipeline_runs.c.id == run_id)
        )
        row = result.fetchone()
        return row[0] if row else "unknown"
