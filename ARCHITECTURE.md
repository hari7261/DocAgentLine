# DocAgentLine Architecture

## System Overview

DocAgentLine is a production-grade, headless document extraction pipeline that processes documents through a series of stages to extract structured data using LLMs.

## Core Principles

1. **Resumability**: Pipeline can resume from any stage after failure
2. **Idempotency**: Re-running same document+schema skips completed stages
3. **Observability**: Full structured logging and tracing
4. **Determinism**: Same input produces same output (where possible)
5. **Failure Safety**: Graceful error handling with retry policies

## Architecture Layers

### 1. API Layer (`app/api/`)

FastAPI-based REST API for document submission and status queries.

**Endpoints:**
- `POST /api/v1/documents` - Submit document
- `GET /api/v1/documents/{id}/status` - Get processing status
- `GET /api/v1/documents/{id}/extractions` - Get extraction results
- `GET /api/v1/documents/{id}/metrics` - Get processing metrics

### 2. CLI Layer (`cli/`)

Command-line interface for direct pipeline interaction.

**Commands:**
- `docagentline submit` - Submit document
- `docagentline status` - Check status
- `docagentline results` - Export results
- `docagentline metrics` - View metrics

### 3. Pipeline Engine (`pipeline/`)

Core execution engine with stage orchestration.

**Components:**
- `PipelineEngine`: Orchestrates stage execution
- `StageRegistry`: Manages stage dependencies
- `PipelineStage`: Protocol for stage implementations

**Stages:**
1. Ingest - Validate and store document
2. Text Extraction - Extract text from PDF/images
3. Layout Normalization - Normalize layout
4. Chunking - Split into semantic chunks
5. Embedding - Generate vector embeddings
6. Structured Extraction - LLM-driven extraction
7. Validation - JSON Schema validation
8. Persistence - Finalize storage
9. Metrics and Audit - Record metrics

### 4. Service Layer (`services/`)

Provider-agnostic service abstractions.

**LLM Service:**
- Abstract `LLMProvider` interface
- OpenAI provider implementation
- HuggingFace provider implementation
- Factory pattern for provider selection

**Embedding Service:**
- Abstract `EmbeddingProvider` interface
- OpenAI embeddings
- HuggingFace embeddings
- Batch processing support

**Validation Service:**
- JSON Schema validation
- Schema registry
- Validation error tracking

### 5. Storage Layer (`storage/`)

File handling and content management.

**Components:**
- `FileHandler`: Async file operations
- `ContentHasher`: Content hashing for deduplication
- Local file ingestion
- URL ingestion with validation

### 6. Database Layer (`db/`)

SQLAlchemy Core-based data access.

**Tables:**
- `documents` - Document metadata
- `pipeline_runs` - Stage execution records
- `chunks` - Text chunks
- `embeddings` - Vector embeddings
- `extractions` - Extraction results
- `validation_errors` - Validation failures
- `metrics` - Performance metrics
- `raw_content` - Original content
- `prompts` - LLM prompts (optional)

### 7. Observability Layer (`observability/`)

Structured logging and tracing.

**Components:**
- JSON log formatter
- OpenTelemetry integration
- Correlation ID tracking
- Performance metrics

### 8. Security Layer (`security/`)

Data protection and redaction.

**Components:**
- Field-level redaction
- Pattern-based redaction (SSN, credit cards)
- Configurable sensitive fields

## Data Flow

```
Document Submission
    ↓
Ingest Stage (validate, hash, store)
    ↓
Text Extraction (PDF/OCR)
    ↓
Layout Normalization
    ↓
Chunking (semantic splitting)
    ↓
Embedding (vector generation)
    ↓
Structured Extraction (LLM)
    ↓
Validation (JSON Schema)
    ↓
Persistence
    ↓
Metrics & Audit
    ↓
Results Available
```

## Error Handling

### Error Classification

1. **TransientExternalError**: Retryable (network, rate limits)
2. **ModelOutputError**: Not retryable (invalid JSON)
3. **SchemaValidationError**: Not retryable (schema mismatch)
4. **PipelineStateError**: Pipeline consistency issue
5. **StorageError**: Storage operation failure

### Retry Policy

- Only `TransientExternalError` is retried
- Exponential backoff with jitter
- Configurable max attempts
- Per-stage retry tracking

## Idempotency Strategy

Documents are uniquely identified by:
- Content hash (SHA-256)
- Schema version

Pipeline checks for completed stages before execution:
- Query `pipeline_runs` for successful completion
- Skip if already completed
- Re-run only failed or incomplete stages

## Concurrency Control

### Stage-Level Concurrency

Controlled by `PIPELINE_MAX_CONCURRENT_STAGES` - limits parallel stage execution.

### Chunk-Level Concurrency

Controlled by `PIPELINE_MAX_CONCURRENT_CHUNKS` - limits parallel chunk processing within extraction stage.

### Embedding Batching

Controlled by `EMBEDDING_BATCH_SIZE` - batches embedding requests for efficiency.

## Schema Management

### Schema Registry

- JSON schemas stored in `schemas/` directory
- Named by version: `{schema_name}_v{version}.json`
- Cached in memory after first load
- Validated using JSON Schema Draft-07

### Schema Versioning

- Each document tied to specific schema version
- Schema changes require new version
- Old versions maintained for historical data

## Cost Tracking

Tracks per-extraction:
- Input tokens
- Output tokens
- Estimated cost (USD)

Configurable cost rates:
- `COST_PER_1K_INPUT_TOKENS`
- `COST_PER_1K_OUTPUT_TOKENS`
- `COST_PER_1K_EMBEDDING_TOKENS`

## Performance Characteristics

### Throughput

- Depends on LLM provider latency
- Typical: 10-100 documents/hour
- Scales horizontally with workers

### Latency

- Small documents: 30-60 seconds
- Large documents: 2-5 minutes
- Dominated by LLM inference time

### Storage

- SQLite: Suitable for <10K documents
- PostgreSQL: Recommended for production
- Raw content stored in database or S3

## Extension Points

### Adding New Stages

1. Implement `PipelineStage` protocol
2. Register in `StageRegistry`
3. Add to stage order
4. Update database schema if needed

### Adding New Providers

1. Implement provider interface
2. Add to factory
3. Update configuration
4. Add provider-specific settings

### Custom Validation

1. Extend `SchemaValidator`
2. Add custom validation rules
3. Store custom errors

## Testing Strategy

### Unit Tests

- Service layer components
- Validation logic
- Utility functions

### Integration Tests

- Pipeline execution
- Database operations
- API endpoints

### End-to-End Tests

- Full document processing
- Error scenarios
- Retry behavior

## Deployment Patterns

### Single Instance

- API + Worker in same process
- SQLite database
- Local storage
- Suitable for development

### Distributed

- Separate API and worker processes
- PostgreSQL database
- S3 storage
- Message queue for coordination
- Suitable for production

### Serverless

- API on Lambda/Cloud Functions
- Workers on separate functions
- Managed database
- Object storage
- Event-driven processing
