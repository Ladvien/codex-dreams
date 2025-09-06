# Tag Embeddings Deployment Guide

## Pre-Deployment Checklist

### System Requirements
- ✅ PostgreSQL with pgvector extension installed
- ✅ Ollama service running with nomic-embed-text model
- ✅ DuckDB with Python UDF support
- ✅ dbt Core installed and configured

### Environment Verification

```bash
# 1. Check PostgreSQL and pgvector
psql -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"

# 2. Check Ollama service and model
curl http://192.168.1.110:11434/api/tags
ollama list | grep nomic-embed-text

# 3. Test Python UDF integration
cd biological_memory/macros
python3 ollama_embeddings.py

# 4. Verify dbt configuration
cd biological_memory
dbt debug --profiles-dir .
```

## Step-by-Step Deployment

### Step 1: Apply Database Schema Migration

```bash
# Apply the migration to add tag embedding columns
psql -d codex_db -f biological_memory/sql/migrations/001_add_tag_embedding_columns.sql
```

**Expected Output:**
```
NOTICE: Tag embedding migration completed successfully
NOTICE: Added columns: tag_embedding, tag_embedding_reduced, tag_embedding_updated
NOTICE: Created HNSW indexes for tag similarity search
```

**Verification:**
```sql
-- Check new columns exist
\d+ memories
-- Should show tag_embedding, tag_embedding_reduced, tag_embedding_updated columns

-- Check indexes created
SELECT indexname FROM pg_indexes WHERE tablename = 'memories' AND indexname LIKE '%tag%';
-- Should show tag embedding HNSW indexes
```

### Step 2: Update dbt Models

```bash
cd biological_memory

# Full refresh to regenerate with tag embeddings
dbt run --select memory_embeddings --full-refresh

# Verify model compilation
dbt compile --select memory_embeddings
```

**Expected Output:**
```
Running with dbt=1.10.9
Found 1 model, 0 tests, 0 snapshots
Completed successfully
```

**Verification:**
```bash
# Check compiled SQL includes tag embedding logic
cat target/compiled/codex_dreams/models/semantic/memory_embeddings.sql | grep -A 10 "tag_embedding"
```

### Step 3: Test UDF Registration

```bash
# Test tag embedding UDF in isolation
cd biological_memory/macros
python3 -c "
from ollama_embeddings import test_tag_embedding_generation
test_tag_embedding_generation()
"
```

**Expected Output:**
```
Testing tag embedding generation for: ['python', 'programming', 'machine-learning', 'data-science']
✓ Generated 768-dimensional tag embedding
  Magnitude: 0.8234
  Deterministic test: 1.000000 similarity (should be 1.0)
✓ Tag embeddings are deterministic
```

### Step 4: Run Initial Embedding Generation

```bash
# Generate embeddings for existing memories
dbt run --select memory_embeddings --vars '{"mode": "production"}'
```

**Monitor Progress:**
```sql
-- Check embedding generation progress
SELECT
    COUNT(*) as total_memories,
    COUNT(*) FILTER (WHERE tags IS NOT NULL AND array_length(tags, 1) > 0) as with_tags,
    COUNT(*) FILTER (WHERE tag_embedding IS NOT NULL) as with_tag_embeddings
FROM memory.main.memory_embeddings;
```

### Step 5: Transfer to PostgreSQL

```bash
# Run enhanced transfer script
python3 biological_memory/scripts/transfer_embeddings_with_tags.py
```

**Expected Output:**
```
=== Enhanced Embeddings Transfer: DuckDB → PostgreSQL ===
Checking for memories without embeddings...
Missing content embeddings: 0
Missing tag embeddings: 1250
Fetching embeddings from DuckDB...
Transfer complete! Content: 0, Tags: 1250 in 45.2 seconds (27.6 records/sec)
=== Tag Embedding Health ===
Tag embeddings coverage: 98% (1250/1275)
```

### Step 6: Verify Health and Performance

```bash
# Check tag embedding health
psql -d codex_db -c "SELECT * FROM public.tag_embedding_stats;"
psql -d codex_db -c "SELECT * FROM public.check_tag_embedding_health();"
```

**Expected Health Status:**
```
check_name         | status  | details
------------------ | ------- | ---------------------------
coverage           | healthy | 98% of tagged memories have embeddings (1250/1275)
freshness          | healthy | Latest tag embedding: 2025-09-06 15:30:45
processing_backlog | healthy | 25 memories need tag embeddings
```

### Step 7: Performance Testing

```bash
# Test similarity search performance
psql -d codex_db -c "
EXPLAIN ANALYZE
SELECT id, tags, 1 - (tag_embedding <=> '[0.1,0.2,0.3]'::vector) as similarity
FROM memories
WHERE tag_embedding IS NOT NULL
ORDER BY tag_embedding <=> '[0.1,0.2,0.3]'::vector
LIMIT 10;
"
```

**Expected Performance:** Query should complete in <100ms with HNSW index usage.

## Post-Deployment Monitoring

### Automated Health Checks

Add to cron for continuous monitoring:

```bash
# Add to crontab (run every hour)
0 * * * * psql -d codex_db -c "SELECT * FROM public.check_tag_embedding_health();" >> /var/log/codex-dreams/tag_health.log 2>&1
```

### Key Metrics to Monitor

1. **Coverage Percentage**: Should remain >95%
2. **Processing Backlog**: Should stay <100 memories
3. **Embedding Generation Rate**: ~30-50 embeddings/second
4. **Search Performance**: <100ms for tag similarity queries

### Alerting Thresholds

```bash
# Example health check with alerting
psql -d codex_db -t -c "
SELECT CASE
    WHEN status IN ('unhealthy', 'backlogged', 'stale') THEN 'ALERT: ' || details
    ELSE 'OK: ' || details
END
FROM public.check_tag_embedding_health();
"
```

## Rollback Procedures

### Emergency Rollback

If issues arise, rollback can be performed safely:

```bash
# 1. Revert dbt model (remove tag embedding generation)
git checkout HEAD~1 -- biological_memory/models/semantic/memory_embeddings.sql
dbt run --select memory_embeddings

# 2. Remove columns (optional - data preserved)
psql -d codex_db -c "
ALTER TABLE memories
DROP COLUMN IF EXISTS tag_embedding,
DROP COLUMN IF EXISTS tag_embedding_reduced,
DROP COLUMN IF EXISTS tag_embedding_updated;
"
```

### Gradual Rollback

```bash
# 1. Stop new tag embedding generation
dbt run --select memory_embeddings --vars '{"skip_tag_embeddings": true}'

# 2. Monitor system health
# 3. Remove columns only after confirming stability
```

## Integration Testing

### End-to-End Validation

```bash
# 1. Create test memory with tags
psql -d codex_db -c "
INSERT INTO memories (content, context, summary, tags)
VALUES ('Test deployment', 'deployment test', 'validation', ARRAY['test', 'deployment', 'validation']);
"

# 2. Run pipeline
dbt run --select memory_embeddings
python3 biological_memory/scripts/transfer_embeddings_with_tags.py

# 3. Verify embedding generated
psql -d codex_db -c "
SELECT tags, tag_embedding IS NOT NULL as has_embedding
FROM memories
WHERE content = 'Test deployment';
"
```

### Performance Validation

```bash
# Run comprehensive test suite
cd tests/tag_embeddings
python -m pytest . -v --tb=short

# Integration tests with real databases
python -m pytest test_tag_embedding_postgres.py -v -k postgres_conn
```

## Troubleshooting Common Issues

### Issue: No Tag Embeddings Generated

**Symptoms:**
- `has_tag_embedding = FALSE` for memories with tags
- Transfer script reports 0 tag embeddings

**Solution:**
```bash
# 1. Check Ollama service
curl http://192.168.1.110:11434/api/generate -d '{"model": "nomic-embed-text", "prompt": "test"}'

# 2. Test UDF directly
python3 -c "
from biological_memory.macros.ollama_embeddings import generate_tag_embedding
print(generate_tag_embedding(['test', 'embedding']))
"

# 3. Check dbt logs
dbt run --select memory_embeddings --debug
```

### Issue: Slow Performance

**Symptoms:**
- Tag similarity queries >1 second
- Transfer script <10 records/second

**Solution:**
```bash
# 1. Check index usage
psql -d codex_db -c "
EXPLAIN ANALYZE
SELECT * FROM memories
WHERE tag_embedding <=> '[0.1]'::vector < 0.5;
"

# 2. Rebuild indexes if needed
psql -d codex_db -c "REINDEX INDEX idx_memories_tag_embedding_hnsw;"

# 3. Tune batch sizes
export BATCH_SIZE=250  # Reduce if memory constrained
python3 biological_memory/scripts/transfer_embeddings_with_tags.py
```

### Issue: Inconsistent Embeddings

**Symptoms:**
- Same tags producing different embeddings
- Low deterministic similarity scores

**Solution:**
```bash
# 1. Verify tag sorting
python3 -c "
tags1 = ['python', 'programming']
tags2 = ['programming', 'python']
print('Sorted:', sorted(tags1) == sorted(tags2))
"

# 2. Clear embedding cache
rm -rf biological_memory/embedding_cache/*

# 3. Regenerate embeddings
dbt run --select memory_embeddings --full-refresh
```

## Success Criteria

✅ **Migration Applied**: New columns visible in `\d+ memories`
✅ **Health Status**: All checks return 'healthy' status
✅ **Coverage >95%**: Most tagged memories have embeddings
✅ **Performance**: Similarity queries <100ms
✅ **Integration**: End-to-end test passes
✅ **Monitoring**: Health checks running automatically

---

**Deployment Complete!** 🎉

Your biological memory system now has sophisticated tag embedding capabilities for enhanced semantic search and memory organization.
