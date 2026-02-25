# DocAgentLine Operations Guide

## System Monitoring

### Key Metrics to Track

1. **Pipeline Throughput**
   - Documents processed per hour
   - Average processing time per document
   - Stage-level latencies

2. **Error Rates**
   - Failed pipeline runs by stage
   - Retry counts
   - Error type distribution

3. **Cost Metrics**
   - Total token usage (input/output)
   - Cost per document
   - Cost by schema version

4. **Resource Usage**
   - Database connection pool utilization
   - Memory usage
   - CPU usage
   - Storage growth rate

### Monitoring Queries

```sql
-- Documents processed today
SELECT COUNT(*) FROM documents 
WHERE DATE(created_at) = CURRENT_DATE;

-- Average processing time by stage
SELECT stage, AVG(latency_ms) as avg_latency_ms
FROM metrics
GROUP BY stage
ORDER BY avg_latency_ms DESC;

-- Error rate by stage
SELECT stage, error_type, COUNT(*) as error_count
FROM pipeline_runs
WHERE status = 'failed'
GROUP BY stage, error_type
ORDER BY error_count DESC;

-- Cost analysis
SELECT 
  schema_version,
  COUNT(*) as document_count,
  SUM(cost_usd) as total_cost,
  AVG(cost_usd) as avg_cost_per_doc
FROM extractions e
JOIN chunks c ON e.chunk_id = c.id
JOIN documents d ON c.document_id = d.id
GROUP BY schema_version;

-- Validation failure rate
SELECT 
  schema_version,
  COUNT(*) as total_extractions,
  SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) as valid_count,
  ROUND(100.0 * SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) / COUNT(*), 2) as valid_percentage
FROM extractions e
JOIN chunks c ON e.chunk_id = c.id
JOIN documents d ON c.document_id = d.id
GROUP BY schema_version;
```

## Operational Tasks

### Daily Operations

1. **Check System Health**
   ```bash
   # API health
   curl http://localhost:8000/health
   
   # Database connectivity
   python -c "from docagentline.db.connection import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().get_engine())"
   ```

2. **Review Error Logs**
   ```bash
   # Filter for errors
   cat logs/app.log | jq 'select(.level == "ERROR")'
   
   # Group by error type
   cat logs/app.log | jq -r 'select(.level == "ERROR") | .error_type' | sort | uniq -c
   ```

3. **Monitor Costs**
   ```bash
   # Daily cost report
   docagentline metrics --date today
   ```

### Weekly Operations

1. **Database Maintenance**
   ```sql
   -- PostgreSQL
   VACUUM ANALYZE;
   REINDEX DATABASE docagentline;
   
   -- SQLite
   VACUUM;
   PRAGMA optimize;
   ```

2. **Storage Cleanup**
   ```bash
   # Remove old raw content (if configured)
   # Implement retention policy
   ```

3. **Performance Review**
   - Review slow queries
   - Check index usage
   - Analyze stage bottlenecks

### Monthly Operations

1. **Capacity Planning**
   - Review growth trends
   - Forecast storage needs
   - Plan scaling requirements

2. **Cost Optimization**
   - Review token usage patterns
   - Identify optimization opportunities
   - Adjust chunk sizes if needed

3. **Security Audit**
   - Review access logs
   - Update dependencies
   - Rotate credentials

## Troubleshooting

### Pipeline Stuck

**Symptoms**: Document status not progressing

**Diagnosis**:
```sql
SELECT * FROM pipeline_runs 
WHERE document_id = ? 
ORDER BY started_at DESC;
```

**Resolution**:
1. Check for running stages with no finish time
2. Review error messages
3. Restart pipeline from failed stage
4. Check LLM provider status

### High Error Rate

**Symptoms**: Many failed pipeline runs

**Diagnosis**:
```sql
SELECT error_type, error_message, COUNT(*) 
FROM pipeline_runs 
WHERE status = 'failed' 
  AND started_at > NOW() - INTERVAL '1 hour'
GROUP BY error_type, error_message;
```

**Resolution**:
1. Identify error pattern
2. Check provider API status
3. Review rate limits
4. Adjust retry configuration

### Validation Failures

**Symptoms**: High rate of invalid extractions

**Diagnosis**:
```sql
SELECT ve.json_path, ve.message, COUNT(*) as error_count
FROM validation_errors ve
JOIN extractions e ON ve.extraction_id = e.id
GROUP BY ve.json_path, ve.message
ORDER BY error_count DESC;
```

**Resolution**:
1. Review schema requirements
2. Improve prompts
3. Adjust model parameters
4. Consider schema relaxation

### High Costs

**Symptoms**: Unexpected token usage

**Diagnosis**:
```sql
SELECT 
  d.schema_version,
  AVG(c.token_count) as avg_chunk_tokens,
  AVG(e.tokens_in) as avg_input_tokens,
  AVG(e.tokens_out) as avg_output_tokens,
  AVG(e.cost_usd) as avg_cost
FROM documents d
JOIN chunks c ON d.id = c.document_id
JOIN extractions e ON c.id = e.chunk_id
GROUP BY d.schema_version;
```

**Resolution**:
1. Optimize chunk sizes
2. Simplify prompts
3. Use cheaper models
4. Implement caching

### Database Performance

**Symptoms**: Slow queries

**Diagnosis**:
```sql
-- PostgreSQL
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

**Resolution**:
1. Add missing indexes
2. Optimize queries
3. Increase connection pool
4. Consider read replicas

## Backup and Recovery

### Backup Strategy

```bash
# Database backup
pg_dump docagentline > backup_$(date +%Y%m%d).sql

# Storage backup
tar -czf storage_backup_$(date +%Y%m%d).tar.gz storage/

# Schema backup
tar -czf schemas_backup_$(date +%Y%m%d).tar.gz schemas/
```

### Recovery Procedure

```bash
# Restore database
psql docagentline < backup_20260225.sql

# Restore storage
tar -xzf storage_backup_20260225.tar.gz

# Restore schemas
tar -xzf schemas_backup_20260225.tar.gz
```

## Scaling Guidelines

### Vertical Scaling

Increase resources for single instance:
- CPU: 4-8 cores recommended
- Memory: 8-16GB recommended
- Storage: SSD recommended

### Horizontal Scaling

Deploy multiple workers:

```python
# worker.py
from docagentline.pipeline.engine import PipelineEngine
# Process documents from queue
```

Use message queue:
- RabbitMQ
- AWS SQS
- Redis Queue

### Database Scaling

1. **Connection Pooling**
   ```python
   DATABASE_POOL_SIZE=20
   DATABASE_MAX_OVERFLOW=40
   ```

2. **Read Replicas**
   - Route read queries to replicas
   - Write to primary only

3. **Partitioning**
   - Partition by date
   - Partition by schema_version

## Performance Tuning

### Application Level

```bash
# Increase concurrency
PIPELINE_MAX_CONCURRENT_STAGES=8
PIPELINE_MAX_CONCURRENT_CHUNKS=20

# Optimize chunking
CHUNK_SIZE=800
CHUNK_OVERLAP=150

# Batch embeddings
EMBEDDING_BATCH_SIZE=200
```

### Database Level

```sql
-- Add indexes for common queries
CREATE INDEX idx_documents_status_created ON documents(status, created_at);
CREATE INDEX idx_extractions_valid_created ON extractions(is_valid, created_at);

-- Analyze query plans
EXPLAIN ANALYZE SELECT ...;
```

### LLM Provider Level

- Use faster models for simple extractions
- Implement request batching
- Use streaming where available
- Cache common responses

## Security Operations

### Access Control

1. **API Authentication**
   - Implement API key authentication
   - Use JWT tokens
   - Rate limit per user

2. **Database Access**
   - Use least privilege principle
   - Separate read/write users
   - Audit access logs

### Data Protection

1. **Encryption**
   - Enable TLS for API
   - Encrypt database connections
   - Encrypt storage at rest

2. **Redaction**
   ```bash
   # Configure sensitive fields
   REDACT_FIELDS=ssn,credit_card,password,email
   ```

### Compliance

1. **Data Retention**
   - Implement retention policies
   - Automated cleanup
   - Audit trail preservation

2. **Privacy**
   - GDPR compliance
   - Data deletion requests
   - Access logs

## Alerting

### Critical Alerts

- Pipeline failure rate > 10%
- API response time > 5s
- Database connection failures
- Disk space < 10%
- Cost spike > 2x average

### Warning Alerts

- Pipeline failure rate > 5%
- API response time > 2s
- Validation failure rate > 20%
- Token usage > 1.5x average

### Alert Channels

- Email for critical issues
- Slack for warnings
- PagerDuty for on-call
- Dashboard for monitoring

## Maintenance Windows

### Planned Maintenance

1. **Database Upgrades**
   - Schedule during low traffic
   - Test on staging first
   - Have rollback plan

2. **Application Updates**
   - Deploy to staging
   - Run smoke tests
   - Blue-green deployment

3. **Schema Changes**
   - Version schemas properly
   - Maintain backward compatibility
   - Migrate data if needed

## Runbooks

### Restart Pipeline for Document

```bash
# 1. Check current status
docagentline status --document-id <id>

# 2. Identify failed stage
# Review pipeline_runs table

# 3. Fix underlying issue
# (e.g., update schema, fix provider config)

# 4. Delete failed run records
# DELETE FROM pipeline_runs WHERE document_id = ? AND status = 'failed';

# 5. Resubmit or trigger pipeline
# Pipeline will resume from last successful stage
```

### Handle Rate Limit Errors

```bash
# 1. Check error frequency
# Review logs for rate limit errors

# 2. Adjust retry configuration
PIPELINE_RETRY_BACKOFF_BASE=3.0
PIPELINE_RETRY_BACKOFF_MAX=120.0

# 3. Reduce concurrency
PIPELINE_MAX_CONCURRENT_CHUNKS=5

# 4. Contact provider for limit increase
```

### Recover from Database Corruption

```bash
# 1. Stop all services
docker-compose down

# 2. Restore from backup
psql docagentline < latest_backup.sql

# 3. Verify data integrity
# Run validation queries

# 4. Restart services
docker-compose up -d

# 5. Monitor for issues
docker-compose logs -f
```
