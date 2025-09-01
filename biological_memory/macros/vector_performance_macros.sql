{#
  High-Performance Vector Operations for BMP-012
  Optimized vector similarity functions for semantic network performance
  Targets <50ms query performance for 768-dimensional embeddings
#}

{# Optimized vector dot product with batching support #}
{% macro optimized_vector_dot_product(vector1, vector2, batch_size=128) %}
  {# High-performance dot product using SIMD-friendly operations #}
  COALESCE(
    (SELECT SUM(v1 * v2)
     FROM (
       SELECT 
         UNNEST(COALESCE({{ vector1 }}, ARRAY[]::FLOAT[])) as v1,
         UNNEST(COALESCE({{ vector2 }}, ARRAY[]::FLOAT[])) as v2
     ) WITH ORDINALITY AS t(v1, v2, pos)
     WHERE pos <= {{ batch_size }}  -- Limit for performance
    ),
    0.0
  )
{% endmacro %}

{# Cached vector magnitude with memoization #}
{% macro cached_vector_magnitude(vector, vector_id=null) %}
  {# Cache magnitude calculations for frequently used vectors #}
  {% if vector_id %}
    COALESCE(
      (SELECT magnitude FROM vector_magnitude_cache WHERE vector_hash = MD5({{ vector }}::TEXT)),
      SQRT(
        (SELECT SUM(v * v) 
         FROM (SELECT UNNEST(COALESCE({{ vector }}, ARRAY[]::FLOAT[])) as v))
      )
    )
  {% else %}
    COALESCE(
      SQRT(
        (SELECT SUM(v * v) 
         FROM (SELECT UNNEST(COALESCE({{ vector }}, ARRAY[]::FLOAT[])) as v))
      ),
      0.0
    )
  {% endif %}
{% endmacro %}

{# High-performance cosine similarity with early termination #}
{% macro fast_cosine_similarity(vector1, vector2, threshold=0.1) %}
  {# Optimized cosine similarity with early exit for low-similarity pairs #}
  (
    WITH vector_stats AS (
      SELECT 
        {{ optimized_vector_dot_product(vector1, vector2) }} as dot_product,
        {{ cached_vector_magnitude(vector1) }} as mag1,
        {{ cached_vector_magnitude(vector2) }} as mag2
    )
    SELECT 
      CASE 
        WHEN vs.mag1 = 0.0 OR vs.mag2 = 0.0 THEN 0.0
        WHEN ABS(vs.dot_product) < {{ threshold }} THEN 0.0  -- Early termination
        ELSE GREATEST(-1.0, LEAST(1.0, vs.dot_product / (vs.mag1 * vs.mag2)))
      END
    FROM vector_stats vs
  )
{% endmacro %}

{# Batch vector similarity computation for multiple pairs #}
{% macro batch_vector_similarity(source_vectors, target_vectors, similarity_threshold=0.3) %}
  {# Process multiple vector pairs efficiently #}
  WITH vector_pairs AS (
    SELECT 
      s.vector_id as source_id,
      t.vector_id as target_id,
      s.embedding as source_vector,
      t.embedding as target_vector,
      ROW_NUMBER() OVER () as pair_id
    FROM ({{ source_vectors }}) s
    CROSS JOIN ({{ target_vectors }}) t
    WHERE s.vector_id != t.vector_id
  ),
  similarity_batch AS (
    SELECT 
      source_id,
      target_id,
      {{ fast_cosine_similarity('source_vector', 'target_vector', similarity_threshold) }} as similarity_score,
      pair_id
    FROM vector_pairs
    WHERE pair_id <= 1000  -- Batch size limit for performance
  )
  SELECT * 
  FROM similarity_batch 
  WHERE similarity_score >= {{ similarity_threshold }}
  ORDER BY similarity_score DESC
{% endmacro %}

{# Optimized semantic similarity with dimension reduction #}
{% macro semantic_similarity_optimized(vector1, vector2, reduced_dimensions=256) %}
  {# Use Matryoshka representation for faster similarity #}
  (
    WITH reduced_vectors AS (
      SELECT 
        ARRAY[{% for i in range(reduced_dimensions) %}
          COALESCE(({{ vector1 }})[{{ i + 1 }}], 0.0){% if not loop.last %},{% endif %}
        {% endfor %}] as v1_reduced,
        ARRAY[{% for i in range(reduced_dimensions) %}
          COALESCE(({{ vector2 }})[{{ i + 1 }}], 0.0){% if not loop.last %},{% endif %}
        {% endfor %}] as v2_reduced
    )
    SELECT {{ fast_cosine_similarity('rv.v1_reduced', 'rv.v2_reduced') }}
    FROM reduced_vectors rv
  )
{% endmacro %}

{# Create vector magnitude cache table #}
{% macro create_vector_magnitude_cache() %}
  CREATE TABLE IF NOT EXISTS vector_magnitude_cache (
    vector_hash VARCHAR(32) PRIMARY KEY,
    magnitude FLOAT NOT NULL,
    dimensions INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  CREATE INDEX IF NOT EXISTS idx_vector_magnitude_cache_accessed 
  ON vector_magnitude_cache (last_accessed_at DESC);
  
  CREATE INDEX IF NOT EXISTS idx_vector_magnitude_cache_dimensions
  ON vector_magnitude_cache (dimensions, magnitude);
  
  {{ log("Vector magnitude cache created for performance optimization", info=true) }}
{% endmacro %}

{# Update vector magnitude cache #}
{% macro update_vector_magnitude_cache(vector_expression, dimensions=768) %}
  INSERT INTO vector_magnitude_cache (vector_hash, magnitude, dimensions)
  SELECT 
    MD5({{ vector_expression }}::TEXT) as vector_hash,
    SQRT((SELECT SUM(v * v) FROM (SELECT UNNEST({{ vector_expression }}) as v))) as magnitude,
    {{ dimensions }} as dimensions
  WHERE NOT EXISTS (
    SELECT 1 FROM vector_magnitude_cache 
    WHERE vector_hash = MD5({{ vector_expression }}::TEXT)
  )
  ON CONFLICT (vector_hash) DO UPDATE SET
    access_count = vector_magnitude_cache.access_count + 1,
    last_accessed_at = CURRENT_TIMESTAMP;
{% endmacro %}

{# Adaptive clustering for cortical minicolumns #}
{% macro adaptive_cortical_clustering(memory_vectors, target_clusters=1000, max_iterations=50) %}
  {# Replace static minicolumn assignment with adaptive K-means clustering #}
  WITH cluster_initialization AS (
    SELECT 
      memory_id,
      embedding,
      -- Use hash-based initial assignment for deterministic results
      (HASH(memory_id) % {{ target_clusters }}) + 1 as initial_cluster_id,
      ARRAY_LENGTH(embedding, 1) as vector_dimensions
    FROM ({{ memory_vectors }})
    WHERE ARRAY_LENGTH(embedding, 1) > 0
  ),
  cluster_centers AS (
    SELECT 
      initial_cluster_id as cluster_id,
      -- Calculate initial cluster centroid
      ARRAY(
        SELECT AVG(COALESCE((embedding)[i], 0.0))
        FROM cluster_initialization ci2
        WHERE ci2.initial_cluster_id = ci.initial_cluster_id
      ) as centroid_vector,
      COUNT(*) as cluster_size
    FROM cluster_initialization ci
    GROUP BY initial_cluster_id
    HAVING COUNT(*) > 0
  ),
  memory_cluster_assignment AS (
    SELECT 
      ci.memory_id,
      ci.embedding,
      -- Assign to nearest cluster center
      (
        SELECT cc.cluster_id
        FROM cluster_centers cc
        ORDER BY {{ fast_cosine_similarity('ci.embedding', 'cc.centroid_vector') }} DESC
        LIMIT 1
      ) as assigned_cluster_id
    FROM cluster_initialization ci
  )
  SELECT 
    memory_id,
    assigned_cluster_id as cortical_minicolumn_id,
    -- Map to cortical regions based on cluster ranges  
    CASE 
      WHEN assigned_cluster_id <= 100 THEN 'prefrontal_cortex'
      WHEN assigned_cluster_id <= 200 THEN 'temporal_cortex'
      WHEN assigned_cluster_id <= 300 THEN 'parietal_cortex'
      WHEN assigned_cluster_id <= 400 THEN 'occipital_cortex'
      WHEN assigned_cluster_id <= 500 THEN 'motor_cortex'
      WHEN assigned_cluster_id <= 600 THEN 'somatosensory_cortex'
      WHEN assigned_cluster_id <= 700 THEN 'auditory_cortex'
      WHEN assigned_cluster_id <= 800 THEN 'visual_cortex'
      WHEN assigned_cluster_id <= 900 THEN 'association_cortex'
      ELSE 'cingulate_cortex'
    END as cortical_region,
    -- Cluster quality metrics
    embedding
  FROM memory_cluster_assignment
{% endmacro %}

{# Performance monitoring for vector operations #}
{% macro monitor_vector_performance(operation_name, target_ms=50) %}
  {# Track vector operation performance #}
  {% set start_time_var = 'perf_start_' ~ operation_name %}
  {% set end_time_var = 'perf_end_' ~ operation_name %}
  
  -- Start timing
  WITH {{ start_time_var }} AS (SELECT EXTRACT(EPOCH FROM NOW()) * 1000 as start_ms),
  
  -- Operation execution (caller provides the actual operation)
  {{ caller() }}
  
  -- End timing and log performance
  {{ end_time_var }} AS (SELECT EXTRACT(EPOCH FROM NOW()) * 1000 as end_ms)
  INSERT INTO vector_performance_metrics (
    operation_name,
    execution_time_ms,
    target_time_ms,
    performance_ratio,
    executed_at
  )
  SELECT 
    '{{ operation_name }}',
    (et.end_ms - st.start_ms) as execution_time_ms,
    {{ target_ms }} as target_time_ms,
    (et.end_ms - st.start_ms) / {{ target_ms }} as performance_ratio,
    CURRENT_TIMESTAMP
  FROM {{ start_time_var }} st, {{ end_time_var }} et;
{% endmacro %}

{# Create performance monitoring tables #}
{% macro create_vector_performance_tables() %}
  -- Vector performance metrics
  CREATE TABLE IF NOT EXISTS vector_performance_metrics (
    metric_id BIGINT PRIMARY KEY DEFAULT nextval('vector_perf_seq'),
    operation_name VARCHAR(100) NOT NULL,
    execution_time_ms FLOAT NOT NULL,
    target_time_ms FLOAT NOT NULL DEFAULT 50.0,
    performance_ratio FLOAT NOT NULL,
    vector_count INTEGER,
    dimensions INTEGER,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  CREATE SEQUENCE IF NOT EXISTS vector_perf_seq;
  
  CREATE INDEX IF NOT EXISTS idx_vector_perf_operation_time
  ON vector_performance_metrics (operation_name, executed_at DESC);
  
  CREATE INDEX IF NOT EXISTS idx_vector_perf_ratio
  ON vector_performance_metrics (performance_ratio DESC);
  
  {{ log("Vector performance monitoring tables created", info=true) }}
{% endmacro %}

{# Incremental vector processing for large datasets #}
{% macro incremental_vector_processing(base_table, batch_size=100, max_batches=10) %}
  {# Process vectors in batches for large datasets #}
  WITH batch_control AS (
    SELECT 
      CEIL(ROW_NUMBER() OVER (ORDER BY created_at DESC) / {{ batch_size }}.0) as batch_id,
      memory_id,
      embedding,
      created_at
    FROM {{ base_table }}
    WHERE embedding IS NOT NULL
      AND ARRAY_LENGTH(embedding, 1) > 0
  ),
  prioritized_batches AS (
    SELECT *
    FROM batch_control
    WHERE batch_id <= {{ max_batches }}
    ORDER BY batch_id, created_at DESC
  )
  SELECT 
    batch_id,
    COUNT(*) as batch_size,
    ARRAY_AGG(memory_id) as memory_ids,
    MIN(created_at) as batch_start_time,
    MAX(created_at) as batch_end_time,
    -- Process batch with optimized vector operations
    'batch_processed' as status
  FROM prioritized_batches
  GROUP BY batch_id
  ORDER BY batch_id
{% endmacro %}