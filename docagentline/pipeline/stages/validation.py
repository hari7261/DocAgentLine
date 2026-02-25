"""Validation stage - validate extractions against schema."""

import json
from datetime import datetime

from sqlalchemy import select, update, insert, delete

from docagentline.db import documents, chunks, extractions, validation_errors
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger
from docagentline.services.validation import SchemaRegistry, SchemaValidator

logger = get_logger(__name__)


class ValidationStage:
    """Validation stage."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.schema_registry = SchemaRegistry()
        self.validator = SchemaValidator()

    async def execute(self, document_id: int):
        """Execute validation stage."""
        async with self.db_manager.get_connection() as conn:
            # Get document
            result = await conn.execute(
                select(documents).where(documents.c.id == document_id)
            )
            doc = result.fetchone()

            if not doc:
                return

            schema_version = doc.schema_version
            schema = self.schema_registry.get_schema(schema_version)

            # Get all extractions for this document
            result = await conn.execute(
                select(extractions, chunks)
                .join(chunks, extractions.c.chunk_id == chunks.c.id)
                .where(chunks.c.document_id == document_id)
            )
            extraction_rows = result.fetchall()

            valid_count = 0
            invalid_count = 0

            for row in extraction_rows:
                extraction_id = row.id
                json_result = json.loads(row.json_result)

                # Delete existing validation errors
                await conn.execute(
                    delete(validation_errors).where(
                        validation_errors.c.extraction_id == extraction_id
                    )
                )

                # Validate
                validation_result = self.validator.validate(json_result, schema)

                # Update extraction
                await conn.execute(
                    update(extractions)
                    .where(extractions.c.id == extraction_id)
                    .values(is_valid=validation_result.is_valid)
                )

                # Store validation errors
                if not validation_result.is_valid:
                    invalid_count += 1
                    for error in validation_result.errors:
                        await conn.execute(
                            insert(validation_errors).values(
                                extraction_id=extraction_id,
                                json_path=error.json_path,
                                message=error.message,
                                created_at=datetime.utcnow(),
                            )
                        )
                else:
                    valid_count += 1

            await conn.execute(
                update(documents)
                .where(documents.c.id == document_id)
                .values(status="validated", updated_at=datetime.utcnow())
            )
            await conn.commit()

            logger.info(
                "Validation completed",
                extra={
                    "document_id": document_id,
                    "valid_count": valid_count,
                    "invalid_count": invalid_count,
                },
            )
