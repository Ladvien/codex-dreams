-- DuckDB Performance Optimization Configuration
-- Optimized settings for biological memory workload patterns
-- Target: <50ms average query response times

-- ====================
-- MEMORY AND THREADS
-- ====================

-- Set memory limit for biological memory processing
-- Reserve 8GB for complex semantic operations
SET memory_limit = '8GB';

-- Use 4 threads for parallel processing
SET threads = 4;

-- ====================
-- QUERY OPTIMIZATION 
-- ====================

-- Set max memory for joins
SET max_memory = '6GB';

-- Enable external sorting if needed
SET preserve_insertion_order = false;

-- Optimize for analytical workloads
SET default_order = 'ASC';

-- ====================
-- I/O AND STORAGE
-- ====================

-- Enable compression for better storage efficiency
-- DuckDB automatically handles compression

-- ====================
-- PROGRESS AND MONITORING
-- ====================

-- Enable progress bar for long-running queries
SET enable_progress_bar = true;

-- Enable profiling for performance monitoring
SET enable_profiling = 'json';

-- ====================
-- BIOLOGICAL MEMORY SPECIFIC
-- ====================

-- Configure for semantic similarity workloads
SET max_expression_depth = 1000;  -- Deep nested expressions in similarity calculations

-- Enable parallel aggregation (built-in to DuckDB, no explicit setting needed)
-- DuckDB automatically uses parallel aggregation based on thread count

-- ====================
-- REMOTE TABLE NOTES
-- ====================

-- Note: DuckDB cannot create indexes on remote PostgreSQL tables.
-- Index optimization should be done directly on PostgreSQL server:
--   codex_db.public.memories (activation_strength DESC, created_at DESC)
--   codex_db.public.memories (created_at DESC)
--   codex_db.public.memories (memory_type, activation_strength DESC)
--   codex_db.public.memories (memory_id)
--
-- DuckDB will leverage PostgreSQL's existing indexes through postgres_scanner

-- ====================
-- LLM CACHE OPTIMIZATION
-- ====================

-- Note: LLM cache tables are created locally in DuckDB
-- Index creation is handled by dbt models that create these tables

-- ====================
-- PERFORMANCE METRICS
-- ====================

-- Create performance benchmarks table if not exists (corrected for DuckDB)
CREATE TABLE IF NOT EXISTS performance_benchmarks (
    benchmark_id VARCHAR PRIMARY KEY DEFAULT ('perf_' || gen_random_uuid()),
    query_type VARCHAR NOT NULL,
    query_name VARCHAR NOT NULL,
    execution_time_ms DOUBLE NOT NULL,
    rows_processed INTEGER,
    target_time_ms DOUBLE DEFAULT 50.0,
    memory_usage_mb DOUBLE,
    cpu_usage_percent DOUBLE,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance monitoring
CREATE INDEX IF NOT EXISTS idx_performance_benchmarks_query_type 
ON performance_benchmarks (query_type, executed_at DESC);

CREATE INDEX IF NOT EXISTS idx_performance_benchmarks_execution_time 
ON performance_benchmarks (execution_time_ms DESC);

-- ====================
-- ANALYZE TABLES
-- ====================

-- Update table statistics for query optimization
-- Note: Remote PostgreSQL tables cannot be analyzed from DuckDB
-- Statistics are maintained by PostgreSQL server automatically
--
-- Local DuckDB tables will be analyzed by dbt when they are created

-- ====================
-- SUCCESS MESSAGE
-- ====================

SELECT 'DuckDB optimized for biological memory workload - Target: <50ms queries' as status,
       '8GB' as memory_limit,
       '4' as thread_count,
       CURRENT_TIMESTAMP as configured_at;