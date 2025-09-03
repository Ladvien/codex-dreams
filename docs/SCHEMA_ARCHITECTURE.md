# Schema Architecture: Biological Memory System

## Overview

The biological memory system uses **three distinct PostgreSQL schemas** with clear separation of concerns:

```
┌─────────────────────┐
│   public schema     │ ← Raw source data
│  (memories table)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ biological_memory   │ ← dbt source configuration
│   (source views)    │
└──────────┬──────────┘
           │
           ▼
   [DuckDB Processing]
           │
           ▼
┌─────────────────────┐
│   dreams schema     │ ← All processed outputs
│ (consolidated data) │
└─────────────────────┘
```

## Schema Purposes

### 1. **public** Schema
- **Purpose**: Raw data storage
- **Main Table**: `memories` - Original memory records from codex
- **Usage**: Source of truth for all raw memory data
- **Access**: Direct PostgreSQL queries

### 2. **biological_memory** Schema  
- **Purpose**: dbt source layer configuration
- **Contents**: Views and staging tables for dbt models
- **Usage**: Bridge between PostgreSQL and DuckDB analytical processing
- **Note**: Managed by dbt, not for direct access

### 3. **dreams** Schema (Consolidated)
- **Purpose**: All processed biological memory outputs
- **Contents**: 
  - Working memory snapshots
  - Short-term episodic memories
  - Long-term consolidated memories
  - Semantic network associations
  - Memory insights and patterns
  - Processing metrics
- **Usage**: Primary schema for querying processed data
- **Access**: Query tools, MCP interface, direct SQL

## Consolidation History

Originally, there were two schemas for processed data:
- `codex_processed` - Early design for write-back storage
- `dreams` - Complete implementation with biological memory stages

These have been **consolidated into the single `dreams` schema** to reduce complexity. Compatibility views are provided for backward compatibility:

```sql
-- Legacy references automatically map to dreams tables
dreams.processed_memories  → dreams.long_term_memories
dreams.memory_associations → dreams.semantic_network  
dreams.generated_insights  → dreams.memory_insights
dreams.processing_metadata → dreams.processing_metrics
```

## Dreams Schema Structure

### Core Memory Tables

| Table | Purpose | Update Frequency |
|-------|---------|------------------|
| `working_memory` | Active 5-minute attention window | Every 5 seconds |
| `short_term_episodes` | Hierarchical episodic memories | Every 5 minutes |
| `long_term_memories` | Stable consolidated memories | Every hour |
| `semantic_network` | Knowledge graph associations | Daily |
| `semantic_memory` | High-level knowledge store | On-demand |
| `memory_insights` | Patterns and predictions | Daily |
| `processing_metrics` | Pipeline health tracking | Every run |

### Convenience Views

| View | Purpose |
|------|---------|
| `current_context` | Latest working memory snapshot |
| `recent_episodes` | Last 24 hours of episodes |
| `knowledge_graph` | Semantic network with meanings |
| `memory_timeline` | Chronological view across all stages |

### Compatibility Views (Legacy Support)

| View | Maps To |
|------|---------|
| `processed_memories` | `long_term_memories` |
| `memory_associations` | `semantic_network` |
| `generated_insights` | `memory_insights` |
| `processing_metadata` | `processing_metrics` |

## Data Flow

```
1. Raw memories inserted → public.memories
2. dbt reads via → biological_memory source views
3. DuckDB processes → analytical models
4. Write-back service → dreams schema tables
5. Applications query → dreams views/tables
```

## Query Examples

```sql
-- Get current working memory
SELECT * FROM dreams.current_context;

-- View memory processing timeline
SELECT * FROM dreams.memory_timeline 
WHERE timestamp > NOW() - INTERVAL '1 day';

-- Explore semantic associations
SELECT * FROM dreams.knowledge_graph
WHERE association_strength > 0.7;

-- Check processing health
SELECT * FROM dreams.get_memory_stats();
```

## Benefits of Consolidation

1. **Simplicity**: Only 3 schemas instead of 4
2. **Clarity**: Each schema has a distinct purpose
3. **Compatibility**: Legacy code continues to work via views
4. **Performance**: Fewer schemas to maintain and index
5. **Organization**: All processed data in one place (dreams)

## Migration Notes

If you have existing code referencing `codex_processed`:
- The schema has been dropped and merged into `dreams`
- Compatibility views ensure existing queries still work
- Update new code to reference `dreams` tables directly

## Summary

The three-schema architecture provides clean separation:
- **public**: Raw source data
- **biological_memory**: dbt configuration layer
- **dreams**: All processed outputs (consolidated from codex_processed)

This structure maintains the biological memory processing pipeline while simplifying data access and management.