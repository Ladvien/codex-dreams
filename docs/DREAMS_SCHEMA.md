# Dreams Schema: Biological Memory Processing Results

## Overview

The `dreams` schema in PostgreSQL stores all processed outputs from the biological memory pipeline, making them fully accessible for querying, analysis, and integration. This completes the data flow from raw memories through DuckDB analytical processing back to PostgreSQL for permanent storage.

## Architecture

```
Raw Memories (PostgreSQL) 
    ↓
DuckDB Analytical Processing (dbt models)
    ↓
Dreams Write-back Service
    ↓
Dreams Schema (PostgreSQL)
    ↓
Query Tools & Applications
```

## Schema Structure

### Core Tables

#### 1. `dreams.working_memory`
- **Purpose**: Active 5-minute attention window snapshots
- **Key Features**: Miller's 7±2 capacity limit, importance scoring, task classification
- **Update Frequency**: Every 5 seconds (configurable)

#### 2. `dreams.short_term_episodes`
- **Purpose**: Hierarchical episodic memories with goal-task-action decomposition
- **Key Features**: Spatial context, emotional salience, consolidation readiness
- **Update Frequency**: Every 5 minutes

#### 3. `dreams.long_term_memories`
- **Purpose**: Stable consolidated memories with semantic enrichment
- **Key Features**: Knowledge types, abstraction levels, stability scores
- **Update Frequency**: Every hour

#### 4. `dreams.semantic_network`
- **Purpose**: Knowledge graph of concept associations
- **Key Features**: Hebbian learning, association strengths, co-activation tracking
- **Update Frequency**: Daily consolidation

#### 5. `dreams.memory_insights`
- **Purpose**: Extracted patterns, predictions, and principles
- **Key Features**: Pattern detection, frequency analysis, confidence scoring
- **Update Frequency**: Daily analysis

#### 6. `dreams.processing_metrics`
- **Purpose**: Performance and health tracking
- **Key Features**: Processing times, resource usage, data quality scores
- **Update Frequency**: Every pipeline run

### Views for Easy Access

- **`dreams.current_context`**: Latest working memory snapshot
- **`dreams.recent_episodes`**: Last 24 hours of episodic memories
- **`dreams.knowledge_graph`**: Full semantic network with meanings
- **`dreams.memory_timeline`**: Chronological view across all stages

## Usage

### Command Line Tools

```bash
# Run full pipeline
python3 src/services/dreams_writeback_service.py full

# Run specific stages
python3 src/services/dreams_writeback_service.py working    # Working memory
python3 src/services/dreams_writeback_service.py episodes   # Short-term episodes
python3 src/services/dreams_writeback_service.py longterm   # Long-term consolidation
python3 src/services/dreams_writeback_service.py semantic   # Semantic network
python3 src/services/dreams_writeback_service.py insights   # Extract insights
python3 src/services/dreams_writeback_service.py cleanup    # Clean old data

# Query dreams data
python3 query_memories.py dreams    # Get schema statistics
python3 query_memories.py context   # View current working memory
```

### SQL Queries

```sql
-- Get memory statistics
SELECT * FROM dreams.get_memory_stats();

-- View current working memory
SELECT * FROM dreams.current_context;

-- Find memory insights
SELECT * FROM dreams.memory_insights 
WHERE confidence_score > 0.8
ORDER BY discovered_at DESC;

-- Explore semantic network
SELECT * FROM dreams.knowledge_graph
WHERE association_strength > 0.7;

-- Track processing performance
SELECT * FROM dreams.processing_metrics
WHERE processing_stage = 'working_memory'
ORDER BY start_time DESC LIMIT 10;
```

### Automated Scheduling

The `dreams_scheduler.py` runs the pipeline on biological rhythms:

- **Every 5 minutes**: Short-term episode processing
- **Every hour**: Long-term memory consolidation
- **Daily at 3 AM**: Semantic network building
- **Weekly Sunday 3 AM**: Data cleanup

To start the scheduler:

```bash
python3 src/services/dreams_scheduler.py
```

## Data Flow Examples

### 1. Working Memory Processing
```
New memory created → 
  Within 5 minutes → 
    Captured in working_memory snapshot →
      Ranked by importance →
        Top 7 items retained (Miller's Law)
```

### 2. Memory Consolidation
```
Short-term episode → 
  Strength > threshold → 
    Ready for consolidation →
      Transferred to long_term_memories →
        Semantic associations created
```

### 3. Pattern Extraction
```
Recurring tags/themes →
  Frequency analysis →
    Pattern detection →
      Insight creation →
        Stored with confidence score
```

## Performance Characteristics

- **Working Memory**: <100ms query time
- **Write-back Latency**: <1 second per stage
- **Storage Growth**: ~1MB per 1000 memories
- **Retention Period**: 30 days default (configurable)

## Integration Points

### With Codex CLI
```bash
# Access via codex command
codex stats  # Includes dreams schema data
```

### With MCP Interface
The dreams schema is accessible through the MCP server for Claude Desktop integration.

### With dbt Models
Future enhancement: dbt models can read from dreams schema for advanced analytics.

## Monitoring

Check pipeline health:

```sql
-- Recent processing runs
SELECT processing_stage, 
       AVG(processing_time_ms) as avg_time,
       SUM(memories_processed) as total_processed,
       MAX(end_time) as last_run
FROM dreams.processing_metrics
WHERE start_time > NOW() - INTERVAL '24 hours'
GROUP BY processing_stage;

-- Data quality
SELECT processing_stage,
       AVG(data_quality_score) as avg_quality,
       SUM(validation_errors) as total_errors
FROM dreams.processing_metrics
WHERE start_time > NOW() - INTERVAL '7 days'
GROUP BY processing_stage;
```

## Troubleshooting

### Common Issues

1. **DuckDB Lock Error**: The write-back service handles this by falling back to PostgreSQL queries
2. **Missing Data**: Check that the source memories exist and meet time window criteria
3. **Slow Performance**: Verify indexes exist and run `VACUUM ANALYZE` on dreams tables

### Maintenance

```sql
-- Clean old snapshots
SELECT dreams.cleanup_old_snapshots();

-- Vacuum and analyze for performance
VACUUM ANALYZE dreams.working_memory;
VACUUM ANALYZE dreams.short_term_episodes;
VACUUM ANALYZE dreams.long_term_memories;
```

## Future Enhancements

1. **Real-time Streaming**: WebSocket interface for live memory updates
2. **Advanced Analytics**: Machine learning models on memory patterns
3. **Visualization Dashboard**: Web interface for memory exploration
4. **Cross-Memory Correlation**: Identify relationships across time periods
5. **Adaptive Thresholds**: Dynamic adjustment of consolidation criteria

## Summary

The dreams schema successfully bridges the gap between analytical processing in DuckDB and accessible storage in PostgreSQL. All biological memory processing results are now permanently stored and queryable, enabling rich analysis of memory patterns, insights extraction, and integration with external systems.