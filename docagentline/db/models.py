"""Database schema definitions using SQLAlchemy Core."""

from datetime import datetime
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
)

metadata = MetaData()

documents = Table(
    "documents",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source", String(512), nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("schema_version", String(64), nullable=False),
    Column("status", String(32), nullable=False, default="pending"),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
    Column("file_size_bytes", Integer, nullable=True),
    Column("mime_type", String(128), nullable=True),
    Index("idx_documents_content_hash_schema", "content_hash", "schema_version"),
    Index("idx_documents_status", "status"),
    Index("idx_documents_created_at", "created_at"),
)

pipeline_runs = Table(
    "pipeline_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("document_id", Integer, ForeignKey("documents.id"), nullable=False),
    Column("stage", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("attempt", Integer, nullable=False, default=1),
    Column("error_type", String(128), nullable=True),
    Column("error_message", Text, nullable=True),
    Column("started_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("finished_at", DateTime, nullable=True),
    Column("correlation_id", String(64), nullable=True),
    Index("idx_pipeline_runs_document_stage", "document_id", "stage"),
    Index("idx_pipeline_runs_status", "status"),
    Index("idx_pipeline_runs_correlation_id", "correlation_id"),
)

chunks = Table(
    "chunks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("document_id", Integer, ForeignKey("documents.id"), nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("text", Text, nullable=False),
    Column("token_count", Integer, nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Index("idx_chunks_document_sequence", "document_id", "sequence"),
)

embeddings = Table(
    "embeddings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("chunk_id", Integer, ForeignKey("chunks.id"), nullable=False),
    Column("model", String(128), nullable=False),
    Column("vector", LargeBinary, nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Index("idx_embeddings_chunk_id", "chunk_id"),
)

extractions = Table(
    "extractions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("chunk_id", Integer, ForeignKey("chunks.id"), nullable=False),
    Column("schema_version", String(64), nullable=False),
    Column("model", String(128), nullable=False),
    Column("json_result", Text, nullable=False),
    Column("is_valid", Boolean, nullable=False),
    Column("latency_ms", Float, nullable=False),
    Column("tokens_in", Integer, nullable=False),
    Column("tokens_out", Integer, nullable=False),
    Column("cost_usd", Float, nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("prompt_hash", String(64), nullable=True),
    Column("raw_response", Text, nullable=True),
    Index("idx_extractions_chunk_id", "chunk_id"),
    Index("idx_extractions_schema_version", "schema_version"),
    Index("idx_extractions_is_valid", "is_valid"),
)

validation_errors = Table(
    "validation_errors",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("extraction_id", Integer, ForeignKey("extractions.id"), nullable=False),
    Column("json_path", String(256), nullable=False),
    Column("message", Text, nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Index("idx_validation_errors_extraction_id", "extraction_id"),
)

metrics = Table(
    "metrics",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", Integer, ForeignKey("pipeline_runs.id"), nullable=False),
    Column("stage", String(64), nullable=False),
    Column("latency_ms", Float, nullable=False),
    Column("tokens_in", Integer, nullable=True),
    Column("tokens_out", Integer, nullable=True),
    Column("cost_usd", Float, nullable=True),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Index("idx_metrics_run_id", "run_id"),
    Index("idx_metrics_stage", "stage"),
)

raw_content = Table(
    "raw_content",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("document_id", Integer, ForeignKey("documents.id"), nullable=False, unique=True),
    Column("content", LargeBinary, nullable=False),
    Column("is_hashed", Boolean, nullable=False, default=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Index("idx_raw_content_document_id", "document_id"),
)

prompts = Table(
    "prompts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("extraction_id", Integer, ForeignKey("extractions.id"), nullable=False),
    Column("prompt_text", Text, nullable=False),
    Column("prompt_hash", String(64), nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Index("idx_prompts_extraction_id", "extraction_id"),
    Index("idx_prompts_prompt_hash", "prompt_hash"),
)
