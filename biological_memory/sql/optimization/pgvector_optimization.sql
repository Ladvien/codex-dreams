-- =====================================================
-- PostgreSQL pgvector HNSW Index Optimization Guide
-- =====================================================
-- For biological_memory system with 8,694 embeddings
-- Target: <50ms similarity search performance
-- Generated: 2025-09-03

-- =====================================================
-- 1. OPTIMAL HNSW INDEX CONFIGURATION
-- =====================================================

-- Drop existing indexes if present
DROP INDEX IF EXISTS idx_memories_embedding_hnsw;
DROP INDEX IF EXISTS idx_memories_embedding_reduced_hnsw;

-- Create optimized HNSW index for 8K+ dataset
-- m=32: Higher connectivity for better recall (vs default m=16)
-- ef_construction=200: Better index quality (vs default ef_construction=64)
CREATE INDEX CONCURRENTLY idx_memories_embedding_hnsw_optimized 
ON memories USING hnsw (embedding_vector vector_cosine_ops) 
WITH (m=32, ef_construction=200);

-- Create optimized reduced-dimension index for faster searches
CREATE INDEX CONCURRENTLY idx_memories_embedding_reduced_optimized 
ON memories USING hnsw (embedding_reduced vector_cosine_ops) 
WITH (m=24, ef_construction=150);

-- Supporting index for semantic clustering queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_semantic_cluster_optimized 
ON memories(semantic_cluster) WHERE embedding_vector IS NOT NULL;

-- =====================================================
-- 2. POSTGRESQL CONFIGURATION OPTIMIZATION
-- =====================================================

-- Set optimal search parameters for HNSW queries
-- Higher ef_search = better recall but slower queries
-- For production, balance between speed and accuracy
SET hnsw.ef_search = 100;  -- Default: 40, Recommended: 100-200

-- Memory settings for vector operations
SET work_mem = '512MB';          -- Increase for complex vector operations
SET maintenance_work_mem = '2GB'; -- Essential for index builds
SET shared_buffers = '4GB';       -- 25-40% of available RAM
SET effective_cache_size = '12GB'; -- 50-75% of available RAM

-- Disable sequential scans to force index usage during testing
-- SET enable_seqscan = false;  -- Use only for testing!

-- =====================================================
-- 3. OPTIMIZED QUERY PATTERNS
-- =====================================================

-- ❌ PROBLEMATIC: Subquery in ORDER BY prevents index usage
/*
SELECT id, content, semantic_cluster,
       embedding_vector <-> (SELECT embedding_vector FROM memories WHERE semantic_cluster = 3 LIMIT 1) as distance
FROM memories
WHERE embedding_vector IS NOT NULL
ORDER BY embedding_vector <-> (SELECT embedding_vector FROM memories WHERE semantic_cluster = 3 LIMIT 1)
LIMIT 10;
*/

-- ✅ OPTIMIZED: Use CTE to eliminate subqueries
WITH reference_vector AS (
  SELECT embedding_vector FROM memories 
  WHERE semantic_cluster = 3 
  LIMIT 1
)
SELECT m.id, m.content, m.semantic_cluster,
       m.embedding_vector <-> r.embedding_vector as distance
FROM memories m, reference_vector r
WHERE m.embedding_vector IS NOT NULL
ORDER BY m.embedding_vector <-> r.embedding_vector
LIMIT 10;

-- ✅ BEST: Direct parameterized query (for application use)
-- Pass the reference vector as a parameter from your application
SELECT id, content, semantic_cluster,
       embedding_vector <-> $1::vector as distance
FROM memories 
WHERE embedding_vector IS NOT NULL
ORDER BY embedding_vector <-> $1::vector
LIMIT 10;

-- =====================================================
-- 4. PERFORMANCE TESTING QUERIES
-- =====================================================

-- Test HNSW index usage with EXPLAIN ANALYZE
EXPLAIN (ANALYZE, BUFFERS) 
SELECT id, content, semantic_cluster,
       embedding_vector <-> '[0.1,0.2,0.3,0.4]'::vector(4) as distance
FROM memories 
WHERE embedding_vector IS NOT NULL
ORDER BY embedding_vector <-> '[0.1,0.2,0.3,0.4]'::vector(4)
LIMIT 10;

-- Monitor index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes 
WHERE indexname LIKE '%hnsw%'
ORDER BY idx_scan DESC;

-- =====================================================
-- 5. BIOLOGICAL MEMORY MACRO OPTIMIZATIONS
-- =====================================================

-- For use in dbt biological memory macros:
-- Replace dynamic subqueries with pre-computed reference vectors

-- Example optimized macro pattern:
{% macro similarity_search(reference_id, limit=10) %}
WITH reference AS (
  SELECT embedding_vector 
  FROM {{ ref('memories') }} 
  WHERE id = '{{ reference_id }}'
)
SELECT 
    m.id,
    m.content,
    m.semantic_cluster,
    m.embedding_vector <-> r.embedding_vector as similarity_distance
FROM {{ ref('memories') }} m
CROSS JOIN reference r
WHERE m.embedding_vector IS NOT NULL
  AND m.id != '{{ reference_id }}'
ORDER BY m.embedding_vector <-> r.embedding_vector
LIMIT {{ limit }}
{% endmacro %}

-- =====================================================
-- 6. MONITORING AND MAINTENANCE
-- =====================================================

-- Check for degenerate vectors (all values identical)
-- This is a critical issue that prevents effective similarity search
SELECT 
    COUNT(*) as total_vectors,
    COUNT(CASE WHEN embedding_vector::text LIKE '%,-0.9712242,%' THEN 1 END) as degenerate_negative,
    COUNT(CASE WHEN embedding_vector::text LIKE '%,0.37265405,%' THEN 1 END) as degenerate_positive,
    AVG(vector_magnitude) as avg_magnitude
FROM memories 
WHERE embedding_vector IS NOT NULL;

-- Monitor query performance over time
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    min_time,
    max_time
FROM pg_stat_statements 
WHERE query LIKE '%embedding_vector%'
ORDER BY mean_time DESC
LIMIT 10;

-- =====================================================
-- 7. TROUBLESHOOTING COMMON ISSUES
-- =====================================================

-- Issue 1: Sequential scans instead of index usage
-- Solution: Use direct vector constants, avoid subqueries

-- Issue 2: Poor recall with HNSW
-- Solution: Increase hnsw.ef_search parameter

-- Issue 3: Slow index builds
-- Solution: Increase maintenance_work_mem to at least 2GB

-- Issue 4: Memory errors during queries
-- Solution: Increase work_mem for vector operations

-- =====================================================
-- 8. EXPECTED PERFORMANCE BENCHMARKS
-- =====================================================

-- Target Performance (with proper diverse embeddings):
-- - Vector similarity search: <50ms P99
-- - Index build time: <10 minutes for 8K vectors
-- - Memory usage: ~2-4GB during index operations
-- - Recall@10: >95% with ef_search=100

-- Current Status:
-- ⚠️  CRITICAL: Degenerate embeddings detected
-- ⚠️  All vectors have identical repeated values
-- ⚠️  Need to fix embedding generation process
-- ✅  Indexes optimized for 8K dataset size
-- ✅  Query patterns optimized to use indexes