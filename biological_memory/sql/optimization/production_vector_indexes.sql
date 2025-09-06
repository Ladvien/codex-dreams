-- Production-Ready Vector Index Optimization for Biological Memory System
-- Expected Performance: <100ms P99 for semantic similarity searches
-- Supports 1M+ embeddings with high recall (>95%)

-- =============================================================================
-- 1. VECTOR INDEX CONFIGURATION
-- =============================================================================

-- Set optimal PostgreSQL configuration for vector operations
SET maintenance_work_mem = '2GB';  -- Critical for index builds
SET max_parallel_workers_per_gather = 4;
SET max_parallel_maintenance_workers = 4;
SET work_mem = '256MB';  -- For query execution
SET effective_cache_size = '8GB';  -- Adjust based on system RAM
SET shared_buffers = '2GB';  -- 25% of system RAM

-- pgvector specific settings for optimal performance
SET ivfflat.probes = 10;  -- Balance between speed and recall

-- =============================================================================
-- 2. HIGH-PERFORMANCE HNSW INDEXES
-- =============================================================================

-- Primary HNSW index for cosine similarity (highest performance)
-- Parameters optimized for 768-dimensional embeddings
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_embeddings_final_embedding_hnsw
ON memory_embeddings USING hnsw (final_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- HNSW index for content embeddings (subset searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_embeddings_content_embedding_hnsw  
ON memory_embeddings USING hnsw (content_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- HNSW index for summary embeddings (quick overview searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_embeddings_summary_embedding_hnsw
ON memory_embeddings USING hnsw (summary_embedding vector_cosine_ops)  
WITH (m = 12, ef_construction = 32);  -- Lower parameters for smaller vectors

-- =============================================================================
-- 3. IVFFLAT INDEXES FOR MEMORY-CONSTRAINED ENVIRONMENTS
-- =============================================================================

-- Alternative IVFFlat index (uses less memory, slightly lower recall)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_embeddings_final_embedding_ivfflat
ON memory_embeddings USING ivfflat (final_embedding vector_cosine_ops)
WITH (lists = 100);

-- Partial IVFFlat index for high-importance memories only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_embeddings_important_ivfflat
ON memory_embeddings USING ivfflat (final_embedding vector_cosine_ops)
WITH (lists = 50)
WHERE importance_score > 0.7;

-- =============================================================================
-- 4. COMPOSITE INDEXES FOR FILTERED SIMILARITY SEARCHES  
-- =============================================================================

-- Composite index for time-filtered similarity searches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_embeddings_time_embedding
ON memory_embeddings (created_at DESC) INCLUDE (final_embedding, memory_id);

-- Index for cluster-filtered searches (biological cortical regions)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_embeddings_cluster_embedding  
ON memory_embeddings (semantic_cluster) INCLUDE (final_embedding, importance_score);

-- Index for emotion-filtered similarity searches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_embeddings_valence_embedding
ON memory_embeddings (emotional_valence) INCLUDE (final_embedding, memory_id);

-- =============================================================================
-- 5. SEMANTIC NETWORK OPTIMIZATION INDEXES
-- =============================================================================

-- Optimized index for semantic network generation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_semantic_network_connections
ON semantic_network (memory_id_1, association_strength DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_semantic_network_reverse
ON semantic_network (memory_id_2, association_strength DESC);

-- Index for connection strength filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_semantic_network_strength_type
ON semantic_network (association_strength DESC, association_type);

-- =============================================================================
-- 6. PARTITIONING STRATEGY FOR LARGE DATASETS
-- =============================================================================

-- Partition memory_embeddings by creation date for better performance
-- Only implement if dataset exceeds 1M memories

-- Example partitioning setup (commented out by default)
/*
-- Create partitioned table
CREATE TABLE memory_embeddings_partitioned (
    LIKE memory_embeddings INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE memory_embeddings_2024_01 PARTITION OF memory_embeddings_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE memory_embeddings_2024_02 PARTITION OF memory_embeddings_partitioned  
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Create indexes on each partition
CREATE INDEX ON memory_embeddings_2024_01 USING hnsw (final_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX ON memory_embeddings_2024_02 USING hnsw (final_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
*/

-- =============================================================================
-- 7. VECTOR CLUSTERING AND QUANTIZATION
-- =============================================================================

-- Create materialized view with clustered embeddings for faster access
CREATE MATERIALIZED VIEW IF NOT EXISTS memory_embeddings_clustered AS
SELECT 
    memory_id,
    content,
    final_embedding,
    semantic_cluster,
    importance_score,
    created_at,
    -- Pre-compute vector magnitude for faster normalization
    sqrt(array_reduce(
        array_map(x -> x*x, final_embedding::float[]), 
        0.0, 
        (acc, x) -> acc + x
    )) as vector_magnitude
FROM memory_embeddings
WHERE final_embedding IS NOT NULL
ORDER BY semantic_cluster, importance_score DESC;

-- Create HNSW index on materialized view
CREATE UNIQUE INDEX ON memory_embeddings_clustered (memory_id);
CREATE INDEX ON memory_embeddings_clustered USING hnsw (final_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- =============================================================================
-- 8. PERFORMANCE MONITORING TABLES
-- =============================================================================

-- Table for tracking vector operation performance
CREATE TABLE IF NOT EXISTS vector_performance_log (
    id SERIAL PRIMARY KEY,
    operation_type VARCHAR(50) NOT NULL,
    query_duration_ms NUMERIC(8,2) NOT NULL,
    result_count INTEGER,
    index_used VARCHAR(100),
    query_hash VARCHAR(64),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query_plan TEXT
);

-- Index for performance analysis
CREATE INDEX ON vector_performance_log (operation_type, executed_at DESC);
CREATE INDEX ON vector_performance_log (query_duration_ms DESC);

-- =============================================================================
-- 9. MAINTENANCE AND OPTIMIZATION PROCEDURES
-- =============================================================================

-- Function to refresh vector statistics and optimize indexes
CREATE OR REPLACE FUNCTION optimize_vector_indexes()
RETURNS void AS $$
BEGIN
    -- Update table statistics for optimal query planning
    ANALYZE memory_embeddings;
    ANALYZE semantic_network;
    
    -- Refresh materialized view with latest data
    REFRESH MATERIALIZED VIEW CONCURRENTLY memory_embeddings_clustered;
    
    -- Log optimization completion
    INSERT INTO vector_performance_log (operation_type, query_duration_ms, result_count)
    VALUES ('index_optimization', 0, 1);
    
    RAISE NOTICE 'Vector index optimization completed';
END;
$$ LANGUAGE plpgsql;

-- Function to monitor vector query performance
CREATE OR REPLACE FUNCTION log_vector_performance(
    op_type VARCHAR(50),
    duration_ms NUMERIC(8,2),
    results INTEGER DEFAULT NULL,
    index_name VARCHAR(100) DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    INSERT INTO vector_performance_log (
        operation_type, 
        query_duration_ms, 
        result_count, 
        index_used
    )
    VALUES (op_type, duration_ms, results, index_name);
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 10. AUTOMATED MAINTENANCE SCHEDULE
-- =============================================================================

-- Schedule regular optimization (run via cron or pg_cron extension)
-- Add to crontab: 0 2 * * * psql -d your_db -c "SELECT optimize_vector_indexes();"

-- Performance monitoring query for alerts
CREATE VIEW vector_performance_alerts AS
SELECT 
    operation_type,
    AVG(query_duration_ms) as avg_duration_ms,
    MAX(query_duration_ms) as max_duration_ms,
    COUNT(*) as query_count,
    DATE_TRUNC('hour', executed_at) as hour_bucket
FROM vector_performance_log
WHERE executed_at >= NOW() - INTERVAL '24 hours'
GROUP BY operation_type, DATE_TRUNC('hour', executed_at)
HAVING AVG(query_duration_ms) > 100  -- Alert if average > 100ms
ORDER BY hour_bucket DESC, avg_duration_ms DESC;

-- =============================================================================
-- 11. VERIFICATION AND BENCHMARKING
-- =============================================================================

-- Verify index usage with EXPLAIN ANALYZE
-- Run these queries to confirm indexes are being used:

/*
-- Test HNSW index usage for similarity search
EXPLAIN (ANALYZE, BUFFERS) 
SELECT memory_id, final_embedding <-> '[0.1,0.2,...]'::vector as distance
FROM memory_embeddings 
ORDER BY final_embedding <-> '[0.1,0.2,...]'::vector 
LIMIT 10;

-- Test filtered similarity search performance  
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.memory_id, m.content, (1 - (m.final_embedding <-> '[0.1,0.2,...]'::vector)) as similarity
FROM memory_embeddings m
WHERE m.importance_score > 0.5
  AND (1 - (m.final_embedding <-> '[0.1,0.2,...]'::vector)) > 0.7
ORDER BY m.final_embedding <-> '[0.1,0.2,...]'::vector
LIMIT 20;
*/

-- Performance benchmark function
CREATE OR REPLACE FUNCTION benchmark_vector_performance()
RETURNS TABLE(test_name TEXT, avg_duration_ms NUMERIC, operations_per_second NUMERIC) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    duration_ms NUMERIC;
BEGIN
    -- Test 1: K-NN search with HNSW index
    SELECT clock_timestamp() INTO start_time;
    
    PERFORM memory_id 
    FROM memory_embeddings 
    ORDER BY final_embedding <-> (SELECT final_embedding FROM memory_embeddings LIMIT 1)
    LIMIT 10;
    
    SELECT clock_timestamp() INTO end_time;
    duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
    
    RETURN QUERY SELECT 
        'hnsw_knn_search'::TEXT,
        duration_ms,
        (1000.0 / duration_ms)::NUMERIC;
    
    -- Test 2: Filtered similarity search
    SELECT clock_timestamp() INTO start_time;
    
    PERFORM COUNT(*) 
    FROM memory_embeddings m1
    WHERE EXISTS (
        SELECT 1 FROM memory_embeddings m2
        WHERE m2.memory_id != m1.memory_id
        AND (1 - (m1.final_embedding <-> m2.final_embedding)) > 0.8
        LIMIT 5
    );
    
    SELECT clock_timestamp() INTO end_time;
    duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
    
    RETURN QUERY SELECT 
        'filtered_similarity'::TEXT,
        duration_ms,
        (1000.0 / duration_ms)::NUMERIC;
    
END;
$$ LANGUAGE plpgsql;

-- Run initial optimization
SELECT optimize_vector_indexes();

-- Display index information
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('memory_embeddings', 'semantic_network')
ORDER BY tablename, indexname;