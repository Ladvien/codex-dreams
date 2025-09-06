-- =====================================================
-- Vector Similarity Helper Macros for Biological Memory
-- =====================================================
-- Optimized pgvector similarity search patterns
-- Compatible with HNSW indexes for <50ms performance

{% macro similarity_search(reference_vector, limit=10, distance_threshold=null) %}
-- Optimized similarity search using direct vector parameter
-- Avoids subqueries that prevent HNSW index usage
SELECT 
    id,
    content,
    semantic_cluster,
    vector_magnitude,
    embedding_vector <-> '{{ reference_vector }}'::vector as similarity_distance
FROM {{ ref('memories') }}
WHERE embedding_vector IS NOT NULL
{% if distance_threshold %}
  AND embedding_vector <-> '{{ reference_vector }}'::vector < {{ distance_threshold }}
{% endif %}
ORDER BY embedding_vector <-> '{{ reference_vector }}'::vector
LIMIT {{ limit }}
{% endmacro %}

{% macro similarity_search_by_id(reference_id, limit=10, exclude_self=true) %}
-- Find similar memories to a reference memory by ID
-- Uses CTE to avoid subqueries in ORDER BY clause
WITH reference AS (
  SELECT embedding_vector 
  FROM {{ ref('memories') }} 
  WHERE id = '{{ reference_id }}'
  AND embedding_vector IS NOT NULL
)
SELECT 
    m.id,
    m.content,
    m.semantic_cluster,
    m.vector_magnitude,
    m.embedding_vector <-> r.embedding_vector as similarity_distance
FROM {{ ref('memories') }} m
CROSS JOIN reference r
WHERE m.embedding_vector IS NOT NULL
{% if exclude_self %}
  AND m.id != '{{ reference_id }}'
{% endif %}
ORDER BY m.embedding_vector <-> r.embedding_vector
LIMIT {{ limit }}
{% endmacro %}

{% macro cluster_similarity_search(cluster_id, limit=10) %}
-- Find memories similar to the centroid of a semantic cluster
WITH cluster_centroid AS (
  SELECT AVG(embedding_vector) as centroid_vector
  FROM {{ ref('memories') }}
  WHERE semantic_cluster = {{ cluster_id }}
    AND embedding_vector IS NOT NULL
)
SELECT 
    m.id,
    m.content,
    m.semantic_cluster,
    m.vector_magnitude,
    m.embedding_vector <-> c.centroid_vector as similarity_distance
FROM {{ ref('memories') }} m
CROSS JOIN cluster_centroid c
WHERE m.embedding_vector IS NOT NULL
  AND m.semantic_cluster != {{ cluster_id }}
ORDER BY m.embedding_vector <-> c.centroid_vector
LIMIT {{ limit }}
{% endmacro %}

{% macro hebbian_association_search(memory_id, co_activation_threshold=0.3, limit=20) %}
-- Find memories with strong Hebbian co-activation patterns
-- Combines vector similarity with temporal co-activation
WITH target_memory AS (
  SELECT 
    embedding_vector,
    created_at,
    semantic_cluster
  FROM {{ ref('memories') }}
  WHERE id = '{{ memory_id }}'
),
temporal_window AS (
  SELECT id, embedding_vector, created_at, semantic_cluster
  FROM {{ ref('memories') }} m, target_memory t
  WHERE m.embedding_vector IS NOT NULL
    AND ABS(EXTRACT(EPOCH FROM m.created_at - t.created_at)) < 3600 -- 1 hour window
)
SELECT 
    tw.id,
    tw.semantic_cluster,
    tw.embedding_vector <-> tm.embedding_vector as vector_distance,
    ABS(EXTRACT(EPOCH FROM tw.created_at - tm.created_at)) as time_distance,
    -- Hebbian strength: inverse of combined distance
    1.0 / (1.0 + tw.embedding_vector <-> tm.embedding_vector + 
           ABS(EXTRACT(EPOCH FROM tw.created_at - tm.created_at))/3600.0) as hebbian_strength
FROM temporal_window tw
CROSS JOIN target_memory tm
WHERE tw.embedding_vector <-> tm.embedding_vector < {{ co_activation_threshold }}
ORDER BY hebbian_strength DESC
LIMIT {{ limit }}
{% endmacro %}

{% macro consolidation_candidate_search(consolidation_threshold=0.5, min_activation_count=3, limit=50) %}
-- Find memory pairs that are candidates for consolidation
-- Based on similarity and co-activation patterns
WITH memory_pairs AS (
  SELECT DISTINCT
    m1.id as memory1_id,
    m2.id as memory2_id,
    m1.embedding_vector <-> m2.embedding_vector as similarity_distance,
    m1.semantic_cluster as cluster1,
    m2.semantic_cluster as cluster2,
    ABS(EXTRACT(EPOCH FROM m1.created_at - m2.created_at)) as time_difference
  FROM {{ ref('memories') }} m1
  JOIN {{ ref('memories') }} m2 ON m1.id < m2.id  -- Avoid duplicates
  WHERE m1.embedding_vector IS NOT NULL
    AND m2.embedding_vector IS NOT NULL
    AND m1.embedding_vector <-> m2.embedding_vector < {{ consolidation_threshold }}
)
SELECT 
  memory1_id,
  memory2_id,
  similarity_distance,
  cluster1,
  cluster2,
  time_difference,
  -- Consolidation priority score
  (1.0 - similarity_distance) * 
  CASE 
    WHEN cluster1 = cluster2 THEN 1.5  -- Same cluster bonus
    ELSE 1.0 
  END * 
  EXP(-time_difference / 86400.0) as consolidation_priority  -- Recency bonus
FROM memory_pairs
ORDER BY consolidation_priority DESC
LIMIT {{ limit }}
{% endmacro %}

{% macro working_memory_attention_search(attention_vector, working_capacity=7, attention_threshold=0.4) %}
-- Simulate working memory attention mechanism
-- Returns most relevant memories within cognitive capacity limits
SELECT 
    id,
    content,
    semantic_cluster,
    embedding_vector <-> '{{ attention_vector }}'::vector as attention_distance,
    -- Attention strength (higher = more attention)
    1.0 / (1.0 + embedding_vector <-> '{{ attention_vector }}'::vector) as attention_strength,
    created_at
FROM {{ ref('memories') }}
WHERE embedding_vector IS NOT NULL
  AND embedding_vector <-> '{{ attention_vector }}'::vector < {{ attention_threshold }}
ORDER BY embedding_vector <-> '{{ attention_vector }}'::vector
LIMIT {{ working_capacity }}  -- Miller's 7±2 rule
{% endmacro %}

{% macro semantic_network_expansion(seed_memory_id, expansion_depth=3, similarity_threshold=0.6) %}
-- Expand semantic network from a seed memory
-- Returns connected memories up to specified depth
WITH RECURSIVE semantic_expansion AS (
  -- Base case: seed memory
  SELECT 
    id,
    content,
    semantic_cluster,
    embedding_vector,
    0 as depth,
    id::text as path
  FROM {{ ref('memories') }}
  WHERE id = '{{ seed_memory_id }}'
    AND embedding_vector IS NOT NULL

  UNION

  -- Recursive case: find similar memories
  SELECT 
    m.id,
    m.content,
    m.semantic_cluster,
    m.embedding_vector,
    se.depth + 1,
    se.path || '->' || m.id::text
  FROM semantic_expansion se
  JOIN {{ ref('memories') }} m ON 
    m.embedding_vector IS NOT NULL
    AND m.id != se.id  -- Avoid cycles
    AND se.embedding_vector <-> m.embedding_vector < {{ similarity_threshold }}
    AND se.depth < {{ expansion_depth }}
    AND POSITION(m.id::text IN se.path) = 0  -- Prevent revisiting
)
SELECT 
  id,
  content,
  semantic_cluster,
  depth,
  path
FROM semantic_expansion
ORDER BY depth, embedding_vector <-> (
  SELECT embedding_vector 
  FROM semantic_expansion 
  WHERE depth = 0
)
{% endmacro %}

{% macro optimize_vector_search_settings() %}
-- Apply optimal PostgreSQL settings for vector operations
-- Should be run before intensive similarity search operations
SET work_mem = '512MB';
SET hnsw.ef_search = 100;
-- Note: In production, these should be set at connection/session level
{% endmacro %}

{% macro vector_index_health_check() %}
-- Monitor HNSW index usage and performance
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    -- Calculate index effectiveness
    CASE 
      WHEN idx_scan > 0 THEN ROUND((idx_tup_fetch::float / idx_scan), 2)
      ELSE 0 
    END as avg_tuples_per_scan
FROM pg_stat_user_indexes 
WHERE indexname LIKE '%hnsw%'
  OR indexname LIKE '%embedding%'
ORDER BY idx_scan DESC
{% endmacro %}

{% macro detect_degenerate_embeddings() %}
-- Detect problematic embedding vectors (all identical values)
-- Critical for diagnosing similarity search issues
WITH embedding_analysis AS (
  SELECT 
    id,
    embedding_vector,
    -- Extract first few dimensions for pattern detection
    (embedding_vector::text LIKE '%,-0.9712242,%') as is_negative_degenerate,
    (embedding_vector::text LIKE '%,0.37265405,%') as is_positive_degenerate,
    vector_magnitude
  FROM {{ ref('memories') }}
  WHERE embedding_vector IS NOT NULL
)
SELECT 
  COUNT(*) as total_embeddings,
  SUM(CASE WHEN is_negative_degenerate THEN 1 ELSE 0 END) as negative_degenerate_count,
  SUM(CASE WHEN is_positive_degenerate THEN 1 ELSE 0 END) as positive_degenerate_count,
  AVG(vector_magnitude) as avg_magnitude,
  STDDEV(vector_magnitude) as magnitude_stddev,
  -- Health assessment
  CASE 
    WHEN SUM(CASE WHEN is_negative_degenerate OR is_positive_degenerate THEN 1 ELSE 0 END) > COUNT(*) * 0.1 
    THEN 'CRITICAL: >10% degenerate embeddings detected'
    WHEN SUM(CASE WHEN is_negative_degenerate OR is_positive_degenerate THEN 1 ELSE 0 END) > 0
    THEN 'WARNING: Some degenerate embeddings detected'
    ELSE 'HEALTHY: No degenerate embeddings'
  END as health_status
FROM embedding_analysis
{% endmacro %}