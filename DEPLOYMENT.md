# DocAgentLine Deployment Guide

## Production Deployment Checklist

### 1. Database

For production, use PostgreSQL instead of SQLite:

```bash
# Install PostgreSQL
# Update DATABASE_URL
DATABASE_URL=postgresql://user:password@localhost:5432/docagentline

# Run migrations
alembic upgrade head
```

### 2. Environment Variables

Create production `.env` file with:

- Real API keys for LLM and embedding providers
- Production database URL
- Appropriate concurrency limits
- Enable OpenTelemetry tracing
- Configure CORS origins for API

### 3. Secret Management

Use a secret management service:

- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault
- Google Secret Manager

Update configuration to load secrets from the service instead of environment variables.

### 4. Logging and Monitoring

Configure log aggregation:

```bash
# Ship logs to centralized logging
# Options: ELK Stack, Datadog, CloudWatch, etc.

# Enable OpenTelemetry
ENABLE_OTEL_TRACING=true
OTEL_EXPORTER_ENDPOINT=http://your-collector:4317
```

### 5. API Deployment

Deploy API using:

**Docker:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY . .

CMD ["uvicorn", "docagentline.app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Kubernetes:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: docagentline-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: docagentline-api
  template:
    metadata:
      labels:
        app: docagentline-api
    spec:
      containers:
      - name: api
        image: docagentline:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: docagentline-secrets
              key: database-url
```

### 6. Worker Deployment

For background processing, deploy workers separately:

```python
# worker.py
import asyncio
from docagentline.pipeline.engine import PipelineEngine
from docagentline.pipeline.registry import StageRegistry
# ... initialize stages and process queue
```

### 7. Scaling Considerations

- Use message queue (RabbitMQ, SQS) for document submission
- Deploy multiple worker instances
- Use connection pooling for database
- Implement rate limiting for API
- Cache schema registry
- Use CDN for static assets

### 8. Backup Strategy

```bash
# Database backups
pg_dump docagentline > backup.sql

# Storage backups
aws s3 sync ./storage s3://docagentline-backups/storage/
```

### 9. Monitoring Metrics

Track:

- Pipeline throughput (documents/hour)
- Stage latencies
- Error rates by stage
- Token usage and costs
- API response times
- Database connection pool usage

### 10. Security Hardening

- Enable HTTPS/TLS
- Implement authentication (OAuth2, JWT)
- Rate limiting per user/API key
- Input validation and sanitization
- Regular security audits
- Keep dependencies updated

### 11. Cost Optimization

- Batch LLM requests where possible
- Use cheaper models for simple extractions
- Implement caching for repeated documents
- Monitor and alert on cost thresholds
- Use spot instances for workers

### 12. Disaster Recovery

- Document recovery procedures
- Test restore from backups regularly
- Implement circuit breakers
- Have rollback plan for deployments
- Maintain runbooks for common issues

## Health Checks

API health check:
```bash
curl http://localhost:8000/health
```

Database health check:
```python
from docagentline.db.connection import DatabaseManager
# Check connection
```

## Performance Tuning

### Database

```sql
-- PostgreSQL tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
```

### Application

- Adjust `PIPELINE_MAX_CONCURRENT_STAGES`
- Adjust `PIPELINE_MAX_CONCURRENT_CHUNKS`
- Tune `CHUNK_SIZE` based on model context limits
- Optimize `EMBEDDING_BATCH_SIZE`

## Troubleshooting

### High latency

- Check database query performance
- Review LLM provider latency
- Check network connectivity
- Review concurrency settings

### High costs

- Review token usage per document
- Check for retry loops
- Optimize chunk sizes
- Consider cheaper models

### Pipeline failures

- Check logs for error patterns
- Review retry configuration
- Verify schema validity
- Check provider API status
