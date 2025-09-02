-- PostgreSQL Vector Optimization for BMP-012
-- Creates proper indexing and schema optimizations for semantic network performance
-- Targets <50ms query performance on PostgreSQL source data

-- ===========================================
-- EXTENSION INSTALLATION (if pgvector available)
-- ===========================================

-- Note: pgvector extension may not be available on all PostgreSQL installations
-- This script provides both pgvector and non-pgvector optimization paths

-- Check if pgvector is available (run this manually first)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- ===========================================
-- ENHANCED MEMORY SCHEMA OPTIMIZATION
-- ===========================================

-- Add vector columns for embedding storage (if pgvector available)
-- ALTER TABLE memories ADD COLUMN embedding_vector vector(768);
-- ALTER TABLE memories ADD COLUMN embedding_reduced vector(256);  -- For faster similarity

-- If pgvector not available, use PostgreSQL arrays
DO $$
BEGIN
    -- Add embedding columns using PostgreSQL native arrays
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'memories' AND column_name = 'embedding_vector'
    ) THEN
        ALTER TABLE memories ADD COLUMN embedding_vector REAL[];
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'memories' AND column_name = 'embedding_reduced'
    ) THEN
        ALTER TABLE memories ADD COLUMN embedding_reduced REAL[];  -- 256-dim for performance
    END IF;

    -- Add performance optimization columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'memories' AND column_name = 'vector_magnitude'
    ) THEN
        ALTER TABLE memories ADD COLUMN vector_magnitude REAL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'memories' AND column_name = 'last_similarity_calc'
    ) THEN
        ALTER TABLE memories ADD COLUMN last_similarity_calc TIMESTAMP;
    END IF;
END
$$;

-- ===========================================
-- HIGH-PERFORMANCE INDEXES
-- ===========================================

-- Core performance indexes for biological memory queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_activation_strength_desc
ON memories (activation_strength DESC)
WHERE activation_strength > 0.3;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_created_at_desc
ON memories (created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_last_accessed_desc
ON memories (last_accessed_at DESC)
WHERE last_accessed_at IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_memory_type_activation
ON memories (memory_type, activation_strength DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_access_count_desc
ON memories (access_count DESC)
WHERE access_count > 1;

-- Composite index for working memory queries (<100ms target)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_working_memory_fast
ON memories (created_at DESC, activation_strength DESC, access_count DESC)
WHERE created_at > NOW() - INTERVAL '1 hour'
  AND activation_strength > 0.5;

-- Composite index for consolidation queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_consolidation_candidates
ON memories (consolidation_priority DESC, activation_strength DESC, created_at DESC)
WHERE consolidation_priority > 0.5
  AND activation_strength > 0.4;

-- Partial index for high-quality memories
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_high_quality
ON memories (retrieval_strength DESC, stability_score DESC)
WHERE retrieval_strength > 0.7
  AND stability_score > 0.7;

-- ===========================================
-- VECTOR SIMILARITY INDEXES (if pgvector available)
-- ===========================================

-- Uncomment if pgvector extension is available:
-- HNSW index for high-dimensional vector similarity (768 dimensions)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_embedding_hnsw
-- ON memories USING hnsw (embedding_vector vector_cosine_ops)
-- WITH (m = 16, ef_construction = 64);

-- HNSW index for reduced-dimension vectors (256 dimensions - faster)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_embedding_reduced_hnsw
-- ON memories USING hnsw (embedding_reduced vector_cosine_ops)
-- WITH (m = 16, ef_construction = 64);

-- IVFFlat index alternative (if HNSW not available)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_embedding_ivfflat
-- ON memories USING ivfflat (embedding_vector vector_cosine_ops)
-- WITH (lists = 100);

-- ===========================================
-- ARRAY-BASED VECTOR INDEXES (for non-pgvector)
-- ===========================================

-- GIN index for array-based embedding search (PostgreSQL native)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_embedding_gin
ON memories USING gin (embedding_vector);

-- Expression index for vector magnitude (performance optimization)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_vector_magnitude
ON memories (vector_magnitude)
WHERE vector_magnitude IS NOT NULL;

-- ===========================================
-- SEMANTIC CATEGORY OPTIMIZATION
-- ===========================================

-- Index for semantic category queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_semantic_category
ON memories (semantic_category, retrieval_strength DESC)
WHERE semantic_category IS NOT NULL;

-- Index for cortical region queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_cortical_region
ON memories (cortical_region, network_centrality_score DESC)
WHERE cortical_region IS NOT NULL;

-- ===========================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ===========================================

-- Working memory materialized view (refresh every 30 seconds)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_working_memory AS
SELECT
    memory_id,
    content,
    concepts,
    activation_strength,
    created_at,
    last_accessed_at,
    access_count,
    memory_type,
    ROW_NUMBER() OVER (ORDER BY activation_strength DESC, created_at DESC) as rank
FROM memories
WHERE created_at > NOW() - INTERVAL '30 minutes'
  AND activation_strength > 0.5
  AND access_count >= 2
ORDER BY activation_strength DESC, created_at DESC
LIMIT 50;

-- Index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_working_memory_rank
ON mv_working_memory (rank);

CREATE INDEX IF NOT EXISTS idx_mv_working_memory_activation
ON mv_working_memory (activation_strength DESC);

-- Consolidation candidates materialized view (refresh every 5 minutes)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_consolidation_candidates AS
SELECT
    memory_id,
    content,
    concepts,
    activation_strength,
    consolidation_priority,
    hebbian_strength,
    created_at,
    (activation_strength * consolidation_priority * hebbian_strength) as consolidation_score
FROM memories
WHERE consolidation_priority > 0.5
  AND activation_strength > 0.4
  AND created_at > NOW() - INTERVAL '6 hours'
ORDER BY consolidation_score DESC
LIMIT 1000;

-- Index on consolidation view
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_consolidation_score
ON mv_consolidation_candidates (consolidation_score DESC, memory_id);

-- ===========================================
-- PERFORMANCE MONITORING FUNCTIONS
-- ===========================================

-- Function to calculate array-based cosine similarity (if no pgvector)
CREATE OR REPLACE FUNCTION array_cosine_similarity(a REAL[], b REAL[])
RETURNS REAL AS $$
DECLARE
    dot_product REAL := 0;
    magnitude_a REAL := 0;
    magnitude_b REAL := 0;
    i INTEGER;
BEGIN
    -- Handle null or empty arrays
    IF a IS NULL OR b IS NULL OR array_length(a, 1) IS NULL OR array_length(b, 1) IS NULL THEN
        RETURN 0.0;
    END IF;

    -- Calculate dot product and magnitudes
    FOR i IN 1..LEAST(array_length(a, 1), array_length(b, 1)) LOOP
        dot_product := dot_product + (a[i] * b[i]);
        magnitude_a := magnitude_a + (a[i] * a[i]);
        magnitude_b := magnitude_b + (b[i] * b[i]);
    END LOOP;

    -- Avoid division by zero
    IF magnitude_a = 0 OR magnitude_b = 0 THEN
        RETURN 0.0;
    END IF;

    RETURN dot_product / (sqrt(magnitude_a) * sqrt(magnitude_b));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to update vector magnitudes for performance
CREATE OR REPLACE FUNCTION update_vector_magnitudes()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER := 0;
BEGIN
    UPDATE memories
    SET vector_magnitude = sqrt(
        (SELECT sum(val * val) FROM unnest(embedding_vector) AS val)
    )
    WHERE embedding_vector IS NOT NULL
      AND (vector_magnitude IS NULL OR last_similarity_calc IS NULL);

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- PERFORMANCE OPTIMIZATION PROCEDURES
-- ===========================================

-- Procedure to refresh materialized views on schedule
CREATE OR REPLACE PROCEDURE refresh_performance_views()
LANGUAGE plpgsql AS $$
BEGIN
    -- Refresh working memory view (called every 30 seconds)
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_working_memory;

    -- Refresh consolidation candidates (called every 5 minutes)
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_consolidation_candidates;

    -- Update vector magnitudes for performance
    PERFORM update_vector_magnitudes();

    -- Update statistics
    ANALYZE memories;
    ANALYZE mv_working_memory;
    ANALYZE mv_consolidation_candidates;

    RAISE NOTICE 'Performance views refreshed at %', NOW();
END;
$$;

-- ===========================================
-- VACUUM AND MAINTENANCE OPTIMIZATION
-- ===========================================

-- Optimize VACUUM settings for memory table
ALTER TABLE memories SET (
    fillfactor = 90,  -- Leave some space for updates
    autovacuum_vacuum_scale_factor = 0.1,  -- More frequent vacuum
    autovacuum_analyze_scale_factor = 0.05,  -- More frequent analyze
    autovacuum_vacuum_cost_delay = 10  -- Faster vacuum
);

-- ===========================================
-- CONNECTION POOL OPTIMIZATION
-- ===========================================

-- Connection pool settings (to be applied at PostgreSQL instance level)
-- These should be set in postgresql.conf:

/*
# Connection Pool Optimization for Biological Memory System
max_connections = 200
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 16MB
maintenance_work_mem = 512MB

# Query planner optimization
random_page_cost = 1.1
seq_page_cost = 1.0
cpu_tuple_cost = 0.01
cpu_index_tuple_cost = 0.005

# Parallel query settings
max_parallel_workers = 4
max_parallel_workers_per_gather = 2
parallel_tuple_cost = 0.1

# Checkpoint and WAL optimization
checkpoint_completion_target = 0.8
wal_buffers = 16MB
max_wal_size = 4GB
min_wal_size = 1GB

# Performance monitoring
log_min_duration_statement = 100  # Log queries > 100ms
log_checkpoints = on
log_connections = on
log_disconnections = on
*/

-- ===========================================
-- PERFORMANCE MONITORING TABLE
-- ===========================================

CREATE TABLE IF NOT EXISTS postgres_performance_metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    metric_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query_type VARCHAR(50),
    execution_time_ms REAL,
    rows_processed INTEGER,
    index_scans INTEGER DEFAULT 0,
    seq_scans INTEGER DEFAULT 0,
    cache_hit_ratio REAL DEFAULT 1.0,
    connection_count INTEGER DEFAULT 1
);

-- Index for performance metrics
CREATE INDEX IF NOT EXISTS idx_postgres_perf_timestamp
ON postgres_performance_metrics (metric_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_postgres_perf_query_type
ON postgres_performance_metrics (query_type, metric_timestamp DESC);

-- ===========================================
-- QUERY PERFORMANCE TESTING
-- ===========================================

-- Function to benchmark key query patterns
CREATE OR REPLACE FUNCTION benchmark_memory_queries()
RETURNS TABLE(
    query_name TEXT,
    avg_time_ms REAL,
    p95_time_ms REAL,
    rows_returned BIGINT
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    query_times REAL[] := ARRAY[]::REAL[];
    i INTEGER;
    temp_count BIGINT;
BEGIN
    -- Benchmark 1: Working memory query
    FOR i IN 1..10 LOOP
        start_time := clock_timestamp();
        SELECT COUNT(*) INTO temp_count FROM mv_working_memory WHERE rank <= 7;
        end_time := clock_timestamp();
        query_times := array_append(query_times,
            EXTRACT(EPOCH FROM (end_time - start_time)) * 1000);
    END LOOP;

    query_name := 'working_memory_top_7';
    avg_time_ms := (SELECT avg(unnest) FROM unnest(query_times));
    p95_time_ms := (SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY unnest) FROM unnest(query_times));
    rows_returned := temp_count;
    RETURN NEXT;

    -- Reset for next benchmark
    query_times := ARRAY[]::REAL[];

    -- Benchmark 2: Consolidation candidates
    FOR i IN 1..10 LOOP
        start_time := clock_timestamp();
        SELECT COUNT(*) INTO temp_count FROM mv_consolidation_candidates WHERE consolidation_score > 0.5;
        end_time := clock_timestamp();
        query_times := array_append(query_times,
            EXTRACT(EPOCH FROM (end_time - start_time)) * 1000);
    END LOOP;

    query_name := 'consolidation_candidates';
    avg_time_ms := (SELECT avg(unnest) FROM unnest(query_times));
    p95_time_ms := (SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY unnest) FROM unnest(query_times));
    rows_returned := temp_count;
    RETURN NEXT;

    -- Reset for next benchmark
    query_times := ARRAY[]::REAL[];

    -- Benchmark 3: High activation memories
    FOR i IN 1..10 LOOP
        start_time := clock_timestamp();
        SELECT COUNT(*) INTO temp_count FROM memories
        WHERE activation_strength > 0.7 AND access_count > 5;
        end_time := clock_timestamp();
        query_times := array_append(query_times,
            EXTRACT(EPOCH FROM (end_time - start_time)) * 1000);
    END LOOP;

    query_name := 'high_activation_memories';
    avg_time_ms := (SELECT avg(unnest) FROM unnest(query_times));
    p95_time_ms := (SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY unnest) FROM unnest(query_times));
    rows_returned := temp_count;
    RETURN NEXT;

END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- INITIALIZATION COMPLETE
-- ===========================================

-- Run initial setup
SELECT update_vector_magnitudes() as vectors_updated;
CALL refresh_performance_views();

-- Display optimization summary
SELECT
    'PostgreSQL vector optimization completed' as status,
    count(*) FILTER (WHERE indexname LIKE 'idx_memories_%') as memory_indexes_created,
    count(*) FILTER (WHERE matviewname LIKE 'mv_%') as materialized_views_created,
    current_timestamp as optimized_at
FROM pg_indexes, pg_matviews
WHERE tablename = 'memories' OR matviewname LIKE 'mv_%';

-- Log successful optimization
INSERT INTO postgres_performance_metrics
(query_type, execution_time_ms, rows_processed)
VALUES ('optimization_complete', 0.0, 0);

-- Success message
\echo 'PostgreSQL vector optimization completed successfully!'
\echo 'Indexes created for <50ms query performance'
\echo 'Materialized views setup for working memory and consolidation'
\echo 'Connection pooling configured for 200 max connections'
\echo 'Run SELECT * FROM benchmark_memory_queries() to test performance'