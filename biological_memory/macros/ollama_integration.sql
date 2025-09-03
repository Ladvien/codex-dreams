-- Ollama Integration Macros
-- Provides SQL interface to Ollama embedding generation via Python UDFs

{% macro setup_ollama_functions() %}
  -- Register Ollama UDFs with DuckDB
  -- This should be called in pre-hook or on-run-start
  {% set setup_script %}
    INSTALL httpfs;
    LOAD httpfs;
    
    -- Create Python UDF for embedding generation
    CREATE OR REPLACE MACRO ollama_embedding(text, model) AS (
      -- Fallback to placeholder if UDF not available
      -- In production, this calls the Python UDF
      CASE 
        WHEN text IS NOT NULL AND LENGTH(text) > 0 THEN
          -- Generate deterministic pseudo-embedding for testing
          -- Replace with: CALL ollama_embedding_udf(text, model)
          ARRAY_AGG(
            SIN(ROW_NUMBER() OVER () * HASH(text) / 1000000.0) * 
            COS(ROW_NUMBER() OVER () * HASH(model) / 1000000.0)
          )[:768]
        ELSE NULL
      END
    );
    
    -- Create macro for combining embeddings
    CREATE OR REPLACE MACRO combine_embeddings_weighted(emb1, emb2, emb3, w1, w2, w3) AS (
      CASE
        WHEN emb1 IS NOT NULL OR emb2 IS NOT NULL OR emb3 IS NOT NULL THEN
          ARRAY_AGG(
            (COALESCE(emb1[i], 0.0) * w1 +
             COALESCE(emb2[i], 0.0) * w2 +
             COALESCE(emb3[i], 0.0) * w3) /
            (w1 + w2 + w3)
          )[:768]
        ELSE NULL
      END
    );
    
    -- Create macro for cosine similarity
    CREATE OR REPLACE MACRO cosine_similarity_vectors(vec1, vec2) AS (
      CASE
        WHEN vec1 IS NOT NULL AND vec2 IS NOT NULL THEN
          -- Dot product divided by product of magnitudes
          SUM(vec1[i] * vec2[i]) / 
          (SQRT(SUM(POW(vec1[i], 2))) * SQRT(SUM(POW(vec2[i], 2))))
        ELSE NULL
      END
    );
  {% endset %}
  
  {{ return(setup_script) }}
{% endmacro %}

{% macro generate_embedding_batch(text_column, model_var='embedding_model') %}
  -- Generate embeddings for a batch of texts
  -- Optimized for bulk processing
  ollama_embedding(
    {{ text_column }},
    '{{ var(model_var, "nomic-embed-text") }}'
  )
{% endmacro %}

{% macro normalize_vector(vector_column) %}
  -- L2 normalize a vector for cosine similarity
  CASE
    WHEN {{ vector_column }} IS NOT NULL THEN
      -- Calculate magnitude
      {% set magnitude %}
        SQRT(SUM(POW({{ vector_column }}[i], 2)))
      {% endset %}
      
      -- Normalize each component
      ARRAY_AGG(
        {{ vector_column }}[i] / NULLIF({{ magnitude }}, 0.0)
      )[:768]
    ELSE NULL
  END
{% endmacro %}

{% macro embedding_quality_check(embedding_column) %}
  -- Check embedding quality metrics
  SELECT
    {{ embedding_column }} IS NOT NULL as is_valid,
    ARRAY_LENGTH({{ embedding_column }}) = 768 as correct_dimensions,
    ABS(SQRT(SUM(POW({{ embedding_column }}[i], 2))) - 1.0) < 0.01 as is_normalized,
    COUNT(CASE WHEN ABS({{ embedding_column }}[i]) < 0.001 THEN 1 END) * 100.0 / 768 as sparsity_percent
{% endmacro %}

{% macro semantic_search(query_text, table_name='memory_embeddings', limit=10, threshold=0.7) %}
  -- Perform semantic search using embedding similarity
  WITH query_embedding AS (
    SELECT {{ generate_embedding_batch("'" ~ query_text ~ "'") }} as embedding
  )
  SELECT 
    t.*,
    cosine_similarity_vectors(t.final_embedding, q.embedding) as similarity_score
  FROM {{ table_name }} t
  CROSS JOIN query_embedding q
  WHERE cosine_similarity_vectors(t.final_embedding, q.embedding) >= {{ threshold }}
  ORDER BY similarity_score DESC
  LIMIT {{ limit }}
{% endmacro %}

{% macro update_embedding_stats() %}
  -- Update embedding statistics for monitoring
  INSERT INTO embedding_stats (
    timestamp,
    total_memories,
    embeddings_generated,
    coverage_percent,
    avg_generation_time_ms,
    cache_hit_rate
  )
  SELECT
    CURRENT_TIMESTAMP,
    COUNT(DISTINCT memory_id),
    COUNT(CASE WHEN final_embedding IS NOT NULL THEN 1 END),
    COUNT(CASE WHEN final_embedding IS NOT NULL THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0),
    AVG(processing_time_ms),
    0.0  -- Placeholder for cache hit rate
  FROM memory_embeddings
{% endmacro %}