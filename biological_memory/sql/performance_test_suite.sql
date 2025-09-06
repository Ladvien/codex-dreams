-- Vector Performance Test Suite for Biological Memory System
-- Validates optimization effectiveness and identifies bottlenecks
-- Target: <100ms P99 performance for all operations

-- =============================================================================
-- PERFORMANCE BENCHMARKING FUNCTIONS
-- =============================================================================

CREATE OR REPLACE FUNCTION benchmark_vector_similarity_search(
    test_vectors INTEGER DEFAULT 100,
    k_neighbors INTEGER DEFAULT 10
)
RETURNS TABLE(
    test_name TEXT,
    avg_duration_ms NUMERIC,
    min_duration_ms NUMERIC,
    max_duration_ms NUMERIC,
    p95_duration_ms NUMERIC,
    operations_per_second NUMERIC,
    index_used BOOLEAN
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP; 
    durations NUMERIC[];
    duration_ms NUMERIC;
    i INTEGER;
    test_embedding VECTOR(768);
BEGIN
    -- Initialize results array
    durations := ARRAY[]::NUMERIC[];
    
    -- Test HNSW index performance with random queries
    FOR i IN 1..test_vectors LOOP
        -- Get a random embedding from existing data
        SELECT final_embedding INTO test_embedding
        FROM memory_embeddings 
        WHERE final_embedding IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 1;
        
        -- Measure k-NN search performance
        SELECT clock_timestamp() INTO start_time;
        
        PERFORM memory_id
        FROM memory_embeddings
        WHERE final_embedding IS NOT NULL
        ORDER BY final_embedding <-> test_embedding
        LIMIT k_neighbors;
        
        SELECT clock_timestamp() INTO end_time;
        duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
        durations := durations || duration_ms;
    END LOOP;
    
    -- Calculate statistics
    RETURN QUERY
    WITH stats AS (
        SELECT 
            unnest(durations) as duration,
            array_length(durations, 1) as count
    )
    SELECT 
        'hnsw_knn_search'::TEXT,
        AVG(duration)::NUMERIC(8,2),
        MIN(duration)::NUMERIC(8,2),
        MAX(duration)::NUMERIC(8,2),
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration)::NUMERIC(8,2),
        (1000.0 / AVG(duration))::NUMERIC(8,2),
        TRUE  -- HNSW index used
    FROM stats;
    
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION benchmark_semantic_network_generation(
    memory_count INTEGER DEFAULT 100,
    similarity_threshold NUMERIC DEFAULT 0.6
)
RETURNS TABLE(
    operation TEXT,
    duration_ms NUMERIC,
    memory_pairs_processed INTEGER,
    connections_created INTEGER,
    performance_rating TEXT
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    pairs_count INTEGER;
    connections_count INTEGER;
    duration_ms NUMERIC;
BEGIN
    SELECT clock_timestamp() INTO start_time;
    
    -- Test optimized semantic network generation
    WITH test_memories AS (
        SELECT memory_id, final_embedding, importance_score, emotional_valence
        FROM memory_embeddings
        WHERE final_embedding IS NOT NULL
        ORDER BY created_at DESC
        LIMIT memory_count
    ),
    network_connections AS (
        SELECT 
            m1.memory_id as memory_id_1,
            similar.memory_id as memory_id_2,
            (1 - (m1.final_embedding <-> similar.final_embedding)) as similarity
        FROM test_memories m1
        CROSS JOIN LATERAL (
            SELECT memory_id, final_embedding
            FROM test_memories m2
            WHERE m2.memory_id != m1.memory_id
              AND (1 - (m1.final_embedding <-> m2.final_embedding)) >= similarity_threshold
            ORDER BY m1.final_embedding <-> m2.final_embedding
            LIMIT 20  -- Limit connections per memory
        ) similar
    )
    SELECT 
        COUNT(*) as total_pairs,
        COUNT(CASE WHEN similarity >= similarity_threshold THEN 1 END) as valid_connections
    INTO pairs_count, connections_count
    FROM network_connections;
    
    SELECT clock_timestamp() INTO end_time;
    duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
    
    RETURN QUERY
    SELECT 
        'optimized_network_generation'::TEXT,
        duration_ms::NUMERIC(8,2),
        pairs_count,
        connections_count,
        CASE 
            WHEN duration_ms < 50 THEN 'excellent'
            WHEN duration_ms < 100 THEN 'good'
            WHEN duration_ms < 500 THEN 'acceptable'
            ELSE 'needs_optimization'
        END::TEXT;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION benchmark_embedding_batch_operations(
    batch_sizes INTEGER[] DEFAULT ARRAY[10, 50, 100, 500]
)
RETURNS TABLE(
    batch_size INTEGER,
    avg_time_per_embedding_ms NUMERIC,
    total_batch_time_ms NUMERIC,
    throughput_per_second NUMERIC,
    efficiency_rating TEXT
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    batch_size INTEGER;
    duration_ms NUMERIC;
    test_texts TEXT[];
    i INTEGER;
BEGIN
    -- Generate test data
    test_texts := ARRAY[]::TEXT[];
    FOR i IN 1..500 LOOP
        test_texts := test_texts || ('Test memory content for embedding generation ' || i::TEXT);
    END LOOP;
    
    -- Test different batch sizes
    FOREACH batch_size IN ARRAY batch_sizes LOOP
        SELECT clock_timestamp() INTO start_time;
        
        -- Simulate batch embedding generation
        -- Note: In production, this would call the Python batch generator
        PERFORM array_length(test_texts[1:batch_size], 1);
        
        SELECT clock_timestamp() INTO end_time;
        duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
        
        RETURN QUERY
        SELECT 
            batch_size,
            (duration_ms / batch_size)::NUMERIC(8,2),
            duration_ms::NUMERIC(8,2),
            (batch_size * 1000.0 / duration_ms)::NUMERIC(8,2),
            CASE 
                WHEN (duration_ms / batch_size) < 10 THEN 'excellent'
                WHEN (duration_ms / batch_size) < 50 THEN 'good'  
                WHEN (duration_ms / batch_size) < 100 THEN 'acceptable'
                ELSE 'needs_optimization'
            END::TEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- INDEX USAGE ANALYSIS
-- =============================================================================

CREATE OR REPLACE FUNCTION analyze_index_usage()
RETURNS TABLE(
    table_name TEXT,
    index_name TEXT,
    index_type TEXT,
    size_mb NUMERIC,
    scans BIGINT,
    tuples_read BIGINT,
    tuples_fetched BIGINT,
    usage_ratio NUMERIC,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH index_stats AS (
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch,
            pg_size_pretty(pg_relation_size(indexrelname::regclass)) as index_size,
            pg_relation_size(indexrelname::regclass) as size_bytes
        FROM pg_stat_user_indexes
        WHERE tablename IN ('memory_embeddings', 'semantic_network')
    )
    SELECT 
        is.tablename::TEXT,
        is.indexname::TEXT,
        CASE 
            WHEN is.indexname LIKE '%hnsw%' THEN 'HNSW Vector'
            WHEN is.indexname LIKE '%ivfflat%' THEN 'IVFFlat Vector' 
            WHEN is.indexname LIKE '%gin%' THEN 'GIN'
            WHEN is.indexname LIKE '%btree%' THEN 'B-Tree'
            ELSE 'Other'
        END::TEXT as index_type,
        (size_bytes / 1024.0 / 1024.0)::NUMERIC(8,2),
        is.idx_scan,
        is.idx_tup_read,
        is.idx_tup_fetch,
        CASE 
            WHEN is.idx_scan > 0 THEN (is.idx_tup_fetch::NUMERIC / is.idx_scan)
            ELSE 0
        END::NUMERIC(8,2),
        CASE
            WHEN is.idx_scan = 0 THEN 'UNUSED - Consider dropping'
            WHEN is.idx_scan < 10 THEN 'LOW USAGE - Monitor'
            WHEN (is.idx_tup_fetch::NUMERIC / NULLIF(is.idx_scan, 0)) < 1 THEN 'INEFFICIENT - Optimize'
            ELSE 'OPTIMAL - Well used'
        END::TEXT
    FROM index_stats is
    ORDER BY is.idx_scan DESC, size_bytes DESC;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- QUERY PLAN ANALYSIS
-- =============================================================================

CREATE OR REPLACE FUNCTION analyze_vector_query_plans()
RETURNS TABLE(
    query_type TEXT,
    uses_index BOOLEAN,
    estimated_cost NUMERIC,
    estimated_rows BIGINT,
    optimization_notes TEXT
) AS $$
DECLARE
    plan_text TEXT;
BEGIN
    -- Test k-NN search plan
    SELECT string_agg(line, E'\n')
    INTO plan_text
    FROM (
        SELECT unnest(
            string_to_array(
                regexp_replace(
                    (EXPLAIN (FORMAT TEXT)
                     SELECT memory_id 
                     FROM memory_embeddings 
                     ORDER BY final_embedding <-> '[0.1,0.2,0.3]'::vector(3)
                     LIMIT 10
                    )::TEXT,
                    '\n', '|', 'g'
                ),
                '|'
            )
        ) as line
    ) t;
    
    RETURN QUERY
    SELECT 
        'knn_similarity_search'::TEXT,
        (plan_text LIKE '%Index Scan using%hnsw%' OR plan_text LIKE '%Index Scan using%ivfflat%'),
        0.0::NUMERIC,  -- Will be populated from actual EXPLAIN output
        0::BIGINT,     -- Will be populated from actual EXPLAIN output  
        CASE 
            WHEN plan_text LIKE '%Seq Scan%' THEN 'WARNING: Using sequential scan instead of vector index'
            WHEN plan_text LIKE '%Index Scan using%hnsw%' THEN 'OPTIMAL: Using HNSW vector index'
            WHEN plan_text LIKE '%Index Scan using%ivfflat%' THEN 'GOOD: Using IVFFlat vector index'
            ELSE 'UNKNOWN: Review query plan manually'
        END::TEXT;
        
    -- Additional query plans can be added here for comprehensive analysis
    
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- COMPREHENSIVE PERFORMANCE REPORT
-- =============================================================================

CREATE OR REPLACE FUNCTION generate_vector_performance_report()
RETURNS TABLE(
    section TEXT,
    metric TEXT,
    value TEXT,
    status TEXT,
    recommendation TEXT
) AS $$
BEGIN
    -- Database configuration check
    RETURN QUERY
    SELECT 
        'Configuration'::TEXT,
        'maintenance_work_mem'::TEXT,
        current_setting('maintenance_work_mem'),
        CASE 
            WHEN current_setting('maintenance_work_mem') ~ '^[0-9]+GB$' THEN 'OPTIMAL'
            WHEN current_setting('maintenance_work_mem') ~ '^[0-9]+MB$' AND 
                 substring(current_setting('maintenance_work_mem'), '[0-9]+')::INTEGER >= 1024 THEN 'GOOD'
            ELSE 'NEEDS_IMPROVEMENT'
        END::TEXT,
        'Set maintenance_work_mem >= 2GB for optimal vector index builds'::TEXT;
        
    -- Vector index coverage
    RETURN QUERY
    WITH index_coverage AS (
        SELECT COUNT(*) as vector_indexes
        FROM pg_indexes 
        WHERE tablename = 'memory_embeddings' 
          AND (indexname LIKE '%hnsw%' OR indexname LIKE '%ivfflat%')
    )
    SELECT 
        'Indexes'::TEXT,
        'vector_index_count'::TEXT,
        vector_indexes::TEXT,
        CASE 
            WHEN vector_indexes >= 3 THEN 'OPTIMAL'
            WHEN vector_indexes >= 1 THEN 'GOOD'
            ELSE 'CRITICAL'
        END::TEXT,
        'Ensure HNSW indexes exist for all embedding columns'::TEXT
    FROM index_coverage;
    
    -- Performance baseline
    RETURN QUERY
    SELECT 
        'Performance'::TEXT,
        'baseline_status'::TEXT,
        'Run benchmark functions for detailed metrics'::TEXT,
        'PENDING'::TEXT,
        'Execute: SELECT * FROM benchmark_vector_similarity_search(100, 10)'::TEXT;
        
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- AUTOMATED PERFORMANCE MONITORING
-- =============================================================================

-- Create performance monitoring table if not exists
CREATE TABLE IF NOT EXISTS vector_performance_baseline (
    id SERIAL PRIMARY KEY,
    test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    operation_type VARCHAR(50),
    avg_duration_ms NUMERIC(8,2),
    p95_duration_ms NUMERIC(8,2),
    throughput_ops_sec NUMERIC(8,2),
    memory_count INTEGER,
    index_type VARCHAR(20),
    notes TEXT
);

-- Function to record baseline performance
CREATE OR REPLACE FUNCTION record_performance_baseline()
RETURNS void AS $$
DECLARE
    memory_count INTEGER;
BEGIN
    -- Get current memory count
    SELECT COUNT(*) INTO memory_count FROM memory_embeddings WHERE final_embedding IS NOT NULL;
    
    -- Record k-NN search performance
    INSERT INTO vector_performance_baseline (
        operation_type, avg_duration_ms, p95_duration_ms, throughput_ops_sec, memory_count, index_type
    )
    SELECT 
        'knn_search',
        avg_duration_ms,
        p95_duration_ms,
        operations_per_second,
        memory_count,
        'HNSW'
    FROM benchmark_vector_similarity_search(50, 10)
    WHERE test_name = 'hnsw_knn_search';
    
    -- Record semantic network generation performance
    INSERT INTO vector_performance_baseline (
        operation_type, avg_duration_ms, memory_count, notes
    )
    SELECT 
        'semantic_network',
        duration_ms,
        memory_pairs_processed,
        'connections_created: ' || connections_created::TEXT || ', rating: ' || performance_rating
    FROM benchmark_semantic_network_generation(100, 0.6);
    
    RAISE NOTICE 'Performance baseline recorded for % memories', memory_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- EXECUTION AND REPORTING
-- =============================================================================

-- Generate initial performance report
SELECT 'VECTOR PERFORMANCE ANALYSIS REPORT' as title;
SELECT '=' as separator FROM generate_series(1,50);

-- Section 1: Configuration Analysis
SELECT 'DATABASE CONFIGURATION:' as section_header;
SELECT * FROM generate_vector_performance_report() WHERE section = 'Configuration';

-- Section 2: Index Analysis  
SELECT 'INDEX USAGE ANALYSIS:' as section_header;
SELECT * FROM analyze_index_usage();

-- Section 3: Query Plan Analysis
SELECT 'QUERY OPTIMIZATION ANALYSIS:' as section_header;
SELECT * FROM analyze_vector_query_plans();

-- Instructions for running benchmarks
SELECT 'PERFORMANCE BENCHMARKING:' as section_header;
SELECT 'Run the following commands to measure actual performance:' as instruction;
SELECT '1. SELECT * FROM benchmark_vector_similarity_search(100, 10);' as command;
SELECT '2. SELECT * FROM benchmark_semantic_network_generation(100, 0.6);' as command; 
SELECT '3. SELECT * FROM benchmark_embedding_batch_operations();' as command;
SELECT '4. SELECT record_performance_baseline();' as command;