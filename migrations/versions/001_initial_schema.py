"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-02-25

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source', sa.String(length=512), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('schema_version', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_documents_content_hash_schema', 'documents', ['content_hash', 'schema_version'])
    op.create_index('idx_documents_status', 'documents', ['status'])
    op.create_index('idx_documents_created_at', 'documents', ['created_at'])

    op.create_table(
        'pipeline_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('stage', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('error_type', sa.String(length=128), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pipeline_runs_document_stage', 'pipeline_runs', ['document_id', 'stage'])
    op.create_index('idx_pipeline_runs_status', 'pipeline_runs', ['status'])
    op.create_index('idx_pipeline_runs_correlation_id', 'pipeline_runs', ['correlation_id'])

    op.create_table(
        'chunks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chunks_document_sequence', 'chunks', ['document_id', 'sequence'])

    op.create_table(
        'embeddings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chunk_id', sa.Integer(), nullable=False),
        sa.Column('model', sa.String(length=128), nullable=False),
        sa.Column('vector', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['chunk_id'], ['chunks.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_embeddings_chunk_id', 'embeddings', ['chunk_id'])

    op.create_table(
        'extractions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chunk_id', sa.Integer(), nullable=False),
        sa.Column('schema_version', sa.String(length=64), nullable=False),
        sa.Column('model', sa.String(length=128), nullable=False),
        sa.Column('json_result', sa.Text(), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=False),
        sa.Column('tokens_out', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('prompt_hash', sa.String(length=64), nullable=True),
        sa.Column('raw_response', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['chunk_id'], ['chunks.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_extractions_chunk_id', 'extractions', ['chunk_id'])
    op.create_index('idx_extractions_schema_version', 'extractions', ['schema_version'])
    op.create_index('idx_extractions_is_valid', 'extractions', ['is_valid'])

    op.create_table(
        'validation_errors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('extraction_id', sa.Integer(), nullable=False),
        sa.Column('json_path', sa.String(length=256), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['extraction_id'], ['extractions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_validation_errors_extraction_id', 'validation_errors', ['extraction_id'])

    op.create_table(
        'metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('stage', sa.String(length=64), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=True),
        sa.Column('tokens_out', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['pipeline_runs.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_metrics_run_id', 'metrics', ['run_id'])
    op.create_index('idx_metrics_stage', 'metrics', ['stage'])

    op.create_table(
        'raw_content',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.LargeBinary(), nullable=False),
        sa.Column('is_hashed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id')
    )
    op.create_index('idx_raw_content_document_id', 'raw_content', ['document_id'])

    op.create_table(
        'prompts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('extraction_id', sa.Integer(), nullable=False),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('prompt_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['extraction_id'], ['extractions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_prompts_extraction_id', 'prompts', ['extraction_id'])
    op.create_index('idx_prompts_prompt_hash', 'prompts', ['prompt_hash'])


def downgrade() -> None:
    op.drop_table('prompts')
    op.drop_table('raw_content')
    op.drop_table('metrics')
    op.drop_table('validation_errors')
    op.drop_table('extractions')
    op.drop_table('embeddings')
    op.drop_table('chunks')
    op.drop_table('pipeline_runs')
    op.drop_table('documents')
