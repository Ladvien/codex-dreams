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
SET enable_profiling = true;

-- ====================
-- BIOLOGICAL MEMORY SPECIFIC
-- ====================

-- Configure for semantic similarity workloads
SET max_expression_depth = 1000;  -- Deep nested expressions in similarity calculations

-- Enable parallel aggregation for memory consolidation
SET enable_parallel_aggregation = true;

-- ====================
-- PERFORMANCE INDEXES
-- ====================

-- Create performance-critical indexes for biological memory queries

-- Working memory access patterns (most frequent)
CREATE INDEX IF NOT EXISTS idx_raw_memories_activation_strength 
ON raw_memories (activation_strength DESC, created_at DESC);

-- Temporal access patterns for memory decay
CREATE INDEX IF NOT EXISTS idx_raw_memories_created_at_desc 
ON raw_memories (created_at DESC);

-- Access frequency patterns
CREATE INDEX IF NOT EXISTS idx_raw_memories_access_count 
ON raw_memories (access_count DESC, last_accessed_at DESC);

-- Memory type filtering
CREATE INDEX IF NOT EXISTS idx_raw_memories_memory_type 
ON raw_memories (memory_type, activation_strength DESC);

-- Compound index for working memory queries (covers most common filters)
CREATE INDEX IF NOT EXISTS idx_raw_memories_working_memory_compound
ON raw_memories (memory_type, activation_strength DESC, created_at DESC, access_count DESC);

-- Memory ID for joins  
CREATE INDEX IF NOT EXISTS idx_raw_memories_memory_id 
ON raw_memories (memory_id);

-- ====================
-- LLM CACHE OPTIMIZATION
-- ====================

-- Optimize LLM cache for fast lookups
CREATE INDEX IF NOT EXISTS idx_llm_cache_prompt_hash 
ON llm_response_cache (prompt_hash);

CREATE INDEX IF NOT EXISTS idx_llm_cache_accessed_at 
ON llm_response_cache (last_accessed_at DESC);

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
ANALYZE raw_memories;
ANALYZE llm_response_cache;
ANALYZE performance_metrics;

-- ====================
-- SUCCESS MESSAGE
-- ====================

SELECT 'DuckDB optimized for biological memory workload - Target: <50ms queries' as status,
       '8GB' as memory_limit,
       '4' as thread_count,
       CURRENT_TIMESTAMP as configured_at;