"""Tests for pipeline engine."""

import pytest
from datetime import datetime

from sqlalchemy import insert, select

from docagentline.db import documents, raw_content
from docagentline.db.connection import DatabaseManager
from docagentline.pipeline.engine import PipelineEngine
from docagentline.pipeline.registry import StageRegistry


class MockStage:
    """Mock pipeline stage."""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.executed = False

    async def execute(self, document_id: int):
        """Execute mock stage."""
        self.executed = True
        if self.should_fail:
            raise Exception("Mock failure")


@pytest.mark.asyncio
async def test_pipeline_stage_execution(test_db):
    """Test pipeline stage execution."""
    db_manager = DatabaseManager()

    # Create test document
    async with db_manager.get_connection() as conn:
        result = await conn.execute(
            insert(documents).values(
                source="test.txt",
                content_hash="abc123",
                schema_version="test_v1",
                status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        document_id = result.inserted_primary_key[0]

        await conn.execute(
            insert(raw_content).values(
                document_id=document_id,
                content=b"test content",
                is_hashed=False,
                created_at=datetime.utcnow(),
            )
        )
        await conn.commit()

    # Setup pipeline with mock stage
    registry = StageRegistry()
    mock_stage = MockStage()
    registry.register("ingest", mock_stage)
    registry._order = ["ingest"]

    engine = PipelineEngine()
    engine.registry = registry

    # Execute pipeline
    results = await engine.execute_pipeline(document_id)

    assert mock_stage.executed
    assert results["ingest"] == "completed"


@pytest.mark.asyncio
async def test_pipeline_idempotency(test_db):
    """Test pipeline idempotency - completed stages are skipped."""
    db_manager = DatabaseManager()

    # Create test document
    async with db_manager.get_connection() as conn:
        result = await conn.execute(
            insert(documents).values(
                source="test.txt",
                content_hash="abc123",
                schema_version="test_v1",
                status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        document_id = result.inserted_primary_key[0]

        await conn.execute(
            insert(raw_content).values(
                document_id=document_id,
                content=b"test content",
                is_hashed=False,
                created_at=datetime.utcnow(),
            )
        )
        await conn.commit()

    # Setup pipeline
    registry = StageRegistry()
    mock_stage = MockStage()
    registry.register("ingest", mock_stage)
    registry._order = ["ingest"]

    engine = PipelineEngine()
    engine.registry = registry

    # Execute first time
    await engine.execute_pipeline(document_id)
    assert mock_stage.executed

    # Reset mock
    mock_stage.executed = False

    # Execute second time - should skip
    results = await engine.execute_pipeline(document_id)
    assert not mock_stage.executed
    assert results["ingest"] == "skipped"
