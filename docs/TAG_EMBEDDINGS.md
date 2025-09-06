# Tag Embeddings Feature Documentation

## Overview

The Tag Embeddings feature extends the biological memory processing system to generate semantic embeddings for memory tags alongside content embeddings. This enables sophisticated tag-based similarity search and filtering that can be utilized by the codex-memory MCP server for enhanced memory retrieval.

## Architecture

### System Integration

Tag embeddings integrate seamlessly with the existing biological memory pipeline:

```
Raw Memory → Working Memory → Short-Term → Consolidation → Long-Term
     ↓              ↓              ↓             ↓            ↓
Content Embedding + Tag Embedding Generation → PostgreSQL Write-back
```

### Key Components

1. **Ollama UDF Extension** (`biological_memory/macros/ollama_embeddings.py`)
   - `generate_tag_embedding()` function for deterministic tag processing
   - Registered as DuckDB UDF: `ollama_tag_embedding(tags, model)`
   - Caching and error handling inherited from existing system

2. **Enhanced dbt Model** (`biological_memory/models/semantic/memory_embeddings.sql`)
   - Tag embedding generation with UDF fallback to mathematical approximation
   - Quality metrics and processing metadata
   - Incremental processing support

3. **PostgreSQL Schema** (Migration: `biological_memory/sql/migrations/001_add_tag_embedding_columns.sql`)
   - `tag_embedding vector(768)` - Full semantic embedding
   - `tag_embedding_reduced vector(256)` - Fast similarity search
   - `tag_embedding_updated timestamp` - Freshness tracking
   - HNSW indexes for efficient similarity search
   - Health monitoring views and functions

4. **Enhanced Transfer Script** (`biological_memory/scripts/transfer_embeddings_with_tags.py`)
   - Dual-mode transfer (content + tag embeddings)
   - Batch processing for optimal performance
   - Health monitoring integration

## Implementation Details

### Tag Processing Strategy

Tags are processed using a **deterministic concatenation approach**:

1. **Filter**: Remove empty/null tags
2. **Sort**: Alphabetically order tags for consistency
3. **Concatenate**: Join with ` | ` separator
4. **Embed**: Generate 768-dimensional vector via Ollama

**Example:**
```python
tags = ['machine-learning', 'python', 'AI']
# Becomes: "AI | machine-learning | python"
embedding = generate_embedding("AI | machine-learning | python")
```

### Database Schema Extensions

```sql
-- New columns added to memories table
ALTER TABLE memories
ADD COLUMN tag_embedding vector(768),           -- Semantic embedding
ADD COLUMN tag_embedding_reduced vector(256),   -- Fast search vector
ADD COLUMN tag_embedding_updated timestamp;     -- Update tracking

-- Optimized HNSW indexes
CREATE INDEX idx_memories_tag_embedding_hnsw
ON memories USING hnsw (tag_embedding vector_cosine_ops)
WITH (m = 8, ef_construction = 64);
```

### Quality Assurance

- **Deterministic Output**: Identical tag sets produce identical embeddings
- **Null Handling**: Graceful handling of empty/missing tags
- **Error Recovery**: Fallback to mathematical approximation
- **Performance Monitoring**: Health checks and coverage metrics

## Usage

### Deployment Steps

1. **Apply Database Migration**:
   ```bash
   psql -f biological_memory/sql/migrations/001_add_tag_embedding_columns.sql
   ```

2. **Update dbt Models**:
   ```bash
   cd biological_memory
   dbt run --select memory_embeddings --full-refresh
   ```

3. **Transfer Embeddings**:
   ```bash
   python3 biological_memory/scripts/transfer_embeddings_with_tags.py
   ```

4. **Monitor Health**:
   ```sql
   SELECT * FROM public.tag_embedding_stats;
   SELECT * FROM public.check_tag_embedding_health();
   ```

### Configuration

Tag embedding generation uses existing configuration variables:

```yaml
# dbt_project.yml
vars:
  embedding_model: "nomic-embed-text"  # Ollama model
  ollama_url: "http://192.168.1.110:11434"  # Ollama endpoint
```

### Testing

Run the comprehensive test suite:

```bash
# Unit tests for tag embedding generation
python -m pytest tests/tag_embeddings/test_tag_embedding_generation.py -v

# SQL integration tests
python -m pytest tests/tag_embeddings/test_tag_embedding_sql.py -v

# PostgreSQL integration tests (requires test DB)
python -m pytest tests/tag_embeddings/test_tag_embedding_postgres.py -v
```

## Performance

### Benchmarks

| Operation | Target Time | Notes |
|-----------|-------------|-------|
| Tag Embedding Generation | <2s per 100 tags | Includes caching |
| Batch Transfer | <5s per 500 records | Content + tag embeddings |
| Similarity Search | <100ms | Using HNSW indexes |

### Optimization Features

- **Caching**: SHA-256 based embedding cache
- **Batch Processing**: 500 records per batch
- **Incremental Updates**: Only process changed memories
- **Index Optimization**: Lower HNSW parameters for tag vectors

## Monitoring

### Health Checks

```sql
-- Coverage statistics
SELECT * FROM public.tag_embedding_stats;

-- Health check details
SELECT * FROM public.check_tag_embedding_health();
```

**Sample Output:**
```
check_name         | status    | details
------------------ | --------- | -------------------------
coverage           | healthy   | 95% of tagged memories have embeddings
freshness          | healthy   | Latest: 2025-09-06 10:30:00
processing_backlog | healthy   | 0 memories need tag embeddings
```

### Key Metrics

- **Coverage Percentage**: % of tagged memories with embeddings
- **Processing Backlog**: Count of memories needing tag embeddings
- **Freshness**: Latest tag embedding generation time
- **Error Rate**: Failed embedding generations per batch

## Integration with codex-memory

Tag embeddings are designed for use by the codex-memory MCP server's `recall_memories` method:

1. **Stage 1**: Tag similarity search to filter candidates (70%+ reduction)
2. **Stage 2**: Content similarity on filtered set
3. **Fallback**: Direct content search if tag embeddings unavailable

## Biological Integration

Tag embeddings integrate with existing biological memory stages:

- **Working Memory**: Tag semantic information contributes to attention scoring
- **Short-Term Memory**: Tag patterns influence episode formation
- **Consolidation**: Tag similarity affects memory association strength
- **Long-Term Memory**: Tag embeddings enhance semantic network organization

## Troubleshooting

### Common Issues

**No tag embeddings generated:**
- Check Ollama service availability (`http://192.168.1.110:11434/api/tags`)
- Verify nomic-embed-text model is installed: `ollama pull nomic-embed-text`
- Review UDF registration: Check DuckDB connection logs

**Performance issues:**
- Monitor batch sizes in transfer script
- Check HNSW index usage: `EXPLAIN ANALYZE` on similarity queries
- Verify embedding cache hit rate

**Inconsistent embeddings:**
- Confirm deterministic tag sorting in logs
- Check for special characters in tags
- Validate cache integrity

### Debug Commands

```bash
# Test Ollama integration
python3 biological_memory/macros/ollama_embeddings.py

# Check UDF registration
duckdb -c "SELECT ollama_tag_embedding(['test'], 'nomic-embed-text');"

# Monitor transfer progress
tail -f logs/tag_embedding_transfer.log
```

## Future Enhancements

### Planned Features

1. **Multi-lingual Tag Support**: Language detection and model routing
2. **Hierarchical Tag Embeddings**: Parent-child tag relationship modeling
3. **Dynamic Dimensionality**: Adaptive embedding dimensions based on tag complexity
4. **Real-time Updates**: Stream processing for immediate tag embedding generation

### Research Directions

- **Tag Cluster Analysis**: Automatic discovery of semantic tag groups
- **Temporal Tag Evolution**: Tracking tag meaning changes over time
- **Cross-memory Tag Propagation**: Suggesting related tags based on embeddings

## API Reference

### Python Functions

```python
def generate_tag_embedding(
    tags: Optional[List[str]],
    model: str = "nomic-embed-text",
    max_retries: int = 3
) -> Optional[List[float]]
```

### SQL Functions

```sql
-- Generate tag embedding (UDF)
SELECT ollama_tag_embedding(tags, model) FROM memories;

-- Check embedding health
SELECT * FROM public.check_tag_embedding_health();

-- Get embedding statistics
SELECT * FROM public.tag_embedding_stats;
```

### Transfer Script

```bash
# Full transfer with health check
python3 biological_memory/scripts/transfer_embeddings_with_tags.py

# Environment variables
export POSTGRES_DB_URL="postgresql://user:pass@host:5432/db"
export OLLAMA_URL="http://192.168.1.110:11434"
export EMBEDDING_MODEL="nomic-embed-text"
```

---

*This feature maintains the biological memory system's commitment to research-grade neuroscience accuracy while adding sophisticated semantic tag processing capabilities for enhanced memory retrieval and organization.*
