-- PostgreSQL pgvector Helper Macros
-- Native pgvector operations for biological memory system
-- These macros work when running dbt on PostgreSQL target

{% macro pgvector_cosine_similarity(emb1_column, emb2_column) %}
  -- Calculate cosine similarity using pgvector native operations
  -- Returns similarity score between -1 and 1 (higher = more similar)
  1 - ({{ emb1_column }} <-> {{ emb2_column }})
{% endmacro %}

{% macro pgvector_cosine_distance(emb1_column, emb2_column) %}
  -- Calculate cosine distance using pgvector native operations  
  -- Returns distance score (lower = more similar)
  {{ emb1_column }} <-> {{ emb2_column }}
{% endmacro %}

{% macro pgvector_euclidean_distance(emb1_column, emb2_column) %}
  -- Calculate euclidean distance using pgvector
  {{ emb1_column }} <-> {{ emb2_column }}
{% endmacro %}

{% macro pgvector_inner_product(emb1_column, emb2_column) %}
  -- Calculate negative inner product using pgvector
  {{ emb1_column }} <#> {{ emb2_column }}
{% endmacro %}

{% macro find_similar_memories_pgvector(query_embedding, similarity_threshold=0.7, limit=10) %}
  -- Find memories similar to query using pgvector HNSW index
  -- This will use the HNSW index for fast similarity search
  SELECT 
    m.id as memory_id,
    m.content,
    m.semantic_cluster,
    m.vector_magnitude,
    (1 - ({{ query_embedding }} <-> m.embedding_vector)) as similarity_score,
    ({{ query_embedding }} <-> m.embedding_vector) as cosine_distance
  FROM memories m
  WHERE m.embedding_vector IS NOT NULL
    AND (1 - ({{ query_embedding }} <-> m.embedding_vector)) >= {{ similarity_threshold }}
  ORDER BY m.embedding_vector <-> {{ query_embedding }}
  LIMIT {{ limit }}
{% endmacro %}

{% macro semantic_network_pgvector(memory_table='memories', similarity_threshold=0.5, limit=1000) %}
  -- Generate semantic network connections using pgvector similarity
  -- Optimized for PostgreSQL with HNSW indexes
  WITH memory_pairs AS (
    SELECT 
      m1.id as memory_id_1,
      m2.id as memory_id_2,
      m1.embedding_vector as embedding_1,
      m2.embedding_vector as embedding_2,
      m1.semantic_cluster as cluster_1,
      m2.semantic_cluster as cluster_2,
      m1.vector_magnitude as magnitude_1,
      m2.vector_magnitude as magnitude_2,
      (1 - (m1.embedding_vector <-> m2.embedding_vector)) as similarity_score
    FROM {{ memory_table }} m1
    CROSS JOIN LATERAL (
      SELECT id, embedding_vector, semantic_cluster, vector_magnitude
      FROM {{ memory_table }}
      WHERE embedding_vector IS NOT NULL 
        AND id > m1.id  -- Avoid duplicates
      ORDER BY embedding_vector <-> m1.embedding_vector
      LIMIT {{ limit }}  -- Limit connections per memory for performance
    ) m2
    WHERE m1.embedding_vector IS NOT NULL
      AND (1 - (m1.embedding_vector <-> m2.embedding_vector)) >= {{ similarity_threshold }}
  )
  SELECT 
    memory_id_1,
    memory_id_2,
    similarity_score,
    CASE 
      WHEN cluster_1 = cluster_2 THEN 'intra_cluster'
      ELSE 'inter_cluster' 
    END as connection_type,
    embedding_1 <-> embedding_2 as cosine_distance,
    CASE
      WHEN similarity_score > 0.8 THEN 'strong'
      WHEN similarity_score > 0.6 THEN 'medium'
      ELSE 'weak'
    END as connection_strength
  FROM memory_pairs
  ORDER BY similarity_score DESC
{% endmacro %}

{% macro create_memory_embedding_index(table_name, embedding_column='embedding_vector', index_type='hnsw') %}
  -- Create optimal pgvector index for memory embeddings
  {% if index_type == 'hnsw' %}
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_{{ table_name }}_{{ embedding_column }}_hnsw
    ON {{ table_name }} USING hnsw ({{ embedding_column }} vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
  {% elif index_type == 'ivfflat' %}
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_{{ table_name }}_{{ embedding_column }}_ivfflat
    ON {{ table_name }} USING ivfflat ({{ embedding_column }} vector_cosine_ops)
    WITH (lists = 100)
  {% endif %}
{% endmacro %}

{% macro benchmark_pgvector_performance(test_queries=10) %}
  -- Benchmark pgvector similarity search performance
  WITH benchmark_data AS (
    SELECT 
      embedding_vector,
      clock_timestamp() as start_time
    FROM memories 
    WHERE embedding_vector IS NOT NULL
    ORDER BY random()
    LIMIT {{ test_queries }}
  ),
  similarity_tests AS (
    SELECT 
      b.start_time,
      COUNT(*) as similar_memories,
      clock_timestamp() as end_time
    FROM benchmark_data b
    CROSS JOIN LATERAL (
      SELECT id
      FROM memories m
      WHERE m.embedding_vector IS NOT NULL
      ORDER BY m.embedding_vector <-> b.embedding_vector
      LIMIT 10
    ) similar
    GROUP BY b.start_time
  )
  SELECT 
    AVG(EXTRACT(EPOCH FROM (end_time - start_time)) * 1000) as avg_query_time_ms,
    MIN(EXTRACT(EPOCH FROM (end_time - start_time)) * 1000) as min_query_time_ms,
    MAX(EXTRACT(EPOCH FROM (end_time - start_time)) * 1000) as max_query_time_ms,
    COUNT(*) as queries_tested,
    AVG(similar_memories) as avg_results_per_query
  FROM similarity_tests
{% endmacro %}

{% macro memory_consolidation_pgvector(consolidation_threshold=0.6, max_connections=50) %}
  -- Memory consolidation using pgvector similarity for Hebbian learning
  WITH consolidation_candidates AS (
    SELECT 
      m.id,
      m.content,
      m.embedding_vector,
      m.semantic_cluster,
      m.vector_magnitude,
      -- Find strongly connected memories using HNSW index
      ARRAY(
        SELECT sim.id
        FROM memories sim
        WHERE sim.embedding_vector IS NOT NULL
          AND sim.id != m.id
          AND (1 - (m.embedding_vector <-> sim.embedding_vector)) >= {{ consolidation_threshold }}
        ORDER BY sim.embedding_vector <-> m.embedding_vector
        LIMIT {{ max_connections }}
      ) as connected_memories,
      -- Calculate consolidation strength
      (
        SELECT AVG(1 - (m.embedding_vector <-> sim.embedding_vector))
        FROM memories sim
        WHERE sim.embedding_vector IS NOT NULL
          AND sim.id != m.id
          AND (1 - (m.embedding_vector <-> sim.embedding_vector)) >= {{ consolidation_threshold }}
        ORDER BY sim.embedding_vector <-> m.embedding_vector
        LIMIT {{ max_connections }}
      ) as avg_connection_strength
    FROM memories m
    WHERE m.embedding_vector IS NOT NULL
  )
  SELECT 
    id,
    content,
    semantic_cluster,
    vector_magnitude,
    array_length(connected_memories, 1) as connection_count,
    connected_memories,
    avg_connection_strength,
    CASE
      WHEN avg_connection_strength > 0.8 THEN 'strong_consolidation'
      WHEN avg_connection_strength > 0.6 THEN 'medium_consolidation'
      ELSE 'weak_consolidation'
    END as consolidation_strength
  FROM consolidation_candidates
  WHERE avg_connection_strength IS NOT NULL
  ORDER BY avg_connection_strength DESC
{% endmacro %}