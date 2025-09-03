-- Biological Memory Helper Macros

{% macro calculate_hebbian_strength(activation, importance) %}
  -- Hebbian strength calculation with biological learning rate
  (COALESCE({{ activation }}, 0.0) * 0.8 + COALESCE({{ importance }}, 0.0) * 0.2) * {{ var('hebbian_learning_rate') }}
{% endmacro %}

{% macro apply_forgetting_curve(strength, age_seconds) %}
  -- Apply exponential forgetting curve
  {{ strength }} * EXP(-{{ var('forgetting_rate') }} * {{ age_seconds }} / 3600.0)
{% endmacro %}

{% macro check_consolidation_threshold(strength) %}
  -- Check if memory strength exceeds consolidation threshold
  {{ strength }} >= {{ var('consolidation_threshold') }}
{% endmacro %}

{% macro calculate_synaptic_weight(pre_activation, post_activation) %}
  -- STDP-based synaptic weight calculation
  CASE
    WHEN {{ pre_activation }} > {{ post_activation }} THEN
      {{ var('ltp_rate') }} * ({{ pre_activation }} - {{ post_activation }})
    ELSE
      -{{ var('ltd_rate') }} * ({{ post_activation }} - {{ pre_activation }})
  END
{% endmacro %}

{% macro enforce_memory_capacity(table_name, capacity_var, order_column) %}
  -- Enforce memory capacity constraints (e.g., Miller's 7±2)
  DELETE FROM {{ table_name }}
  WHERE id NOT IN (
    SELECT id
    FROM {{ table_name }}
    ORDER BY {{ order_column }} DESC
    LIMIT {{ var(capacity_var) }}
  )
{% endmacro %}

-- ============================================================================
-- VECTOR EMBEDDING MACROS
-- Semantic similarity and embedding operations for biological memory
-- ============================================================================

{% macro generate_embedding(text_column) %}
  -- Generate embedding via Ollama API (placeholder for UDF)
  -- In production, this would call: ollama_embedding({{ text_column }}, '{{ var("embedding_model") }}')
  -- Returns: FLOAT[768] array
  CAST(
    CASE 
      WHEN {{ text_column }} IS NOT NULL AND LENGTH({{ text_column }}) > 0 THEN
        -- Placeholder: generate random 768-dim vector for testing
        -- Replace with actual Ollama UDF call
        ARRAY_AGG(RANDOM())[:768]
      ELSE NULL
    END AS FLOAT[768]
  )
{% endmacro %}

{% macro combine_embeddings(emb1, emb2, emb3, weights=[0.5, 0.3, 0.2]) %}
  -- Weighted combination of multiple embeddings
  CASE
    WHEN {{ emb1 }} IS NOT NULL OR {{ emb2 }} IS NOT NULL OR {{ emb3 }} IS NOT NULL THEN
      ARRAY_AGG(
        (COALESCE({{ emb1 }}[i], 0.0) * {{ weights[0] }} +
         COALESCE({{ emb2 }}[i], 0.0) * {{ weights[1] }} +
         COALESCE({{ emb3 }}[i], 0.0) * {{ weights[2] }})
      )[:768]
    ELSE NULL
  END
{% endmacro %}

{% macro normalize_embedding(embedding_column) %}
  -- L2 normalize embedding vector for cosine similarity
  CASE
    WHEN {{ embedding_column }} IS NOT NULL THEN
      ARRAY_AGG(
        {{ embedding_column }}[i] / SQRT(
          SUM(POW({{ embedding_column }}[j], 2)) OVER ()
        )
      )[:768]
    ELSE NULL
  END
{% endmacro %}

{% macro vector_magnitude(embedding_column) %}
  -- Calculate L2 norm of embedding vector
  CASE
    WHEN {{ embedding_column }} IS NOT NULL THEN
      SQRT(SUM(POW({{ embedding_column }}[i], 2)))
    ELSE NULL
  END
{% endmacro %}

{% macro vector_sparsity(embedding_column, threshold=0.01) %}
  -- Calculate sparsity (percentage of near-zero values)
  CASE
    WHEN {{ embedding_column }} IS NOT NULL THEN
      COUNT(CASE WHEN ABS({{ embedding_column }}[i]) < {{ threshold }} THEN 1 END) * 100.0 / 768
    ELSE NULL
  END
{% endmacro %}

{% macro cosine_similarity(emb1, emb2) %}
  -- Calculate cosine similarity between two normalized embeddings
  -- Returns: similarity score between -1 and 1
  CASE
    WHEN {{ emb1 }} IS NOT NULL AND {{ emb2 }} IS NOT NULL THEN
      SUM({{ emb1 }}[i] * {{ emb2 }}[i])
    ELSE NULL
  END
{% endmacro %}

{% macro semantic_distance(emb1, emb2, metric='cosine') %}
  -- Calculate semantic distance between embeddings
  -- Metrics: 'cosine', 'euclidean', 'manhattan'
  {% if metric == 'cosine' %}
    1 - {{ cosine_similarity(emb1, emb2) }}
  {% elif metric == 'euclidean' %}
    SQRT(SUM(POW({{ emb1 }}[i] - {{ emb2 }}[i], 2)))
  {% elif metric == 'manhattan' %}
    SUM(ABS({{ emb1 }}[i] - {{ emb2 }}[i]))
  {% else %}
    NULL
  {% endif %}
{% endmacro %}

{% macro find_similar_memories(query_embedding, threshold=0.7, limit=10) %}
  -- Find memories with similar embeddings
  SELECT 
    memory_id,
    content,
    {{ cosine_similarity(query_embedding, 'final_embedding') }} as similarity_score
  FROM memory_embeddings
  WHERE {{ cosine_similarity(query_embedding, 'final_embedding') }} >= {{ threshold }}
  ORDER BY similarity_score DESC
  LIMIT {{ limit }}
{% endmacro %}

{% macro hebbian_learning_with_embeddings(emb1, emb2, learning_rate=0.1) %}
  -- Hebbian learning rule with embedding similarity
  -- "Neurons that fire together, wire together"
  {{ cosine_similarity(emb1, emb2) }} * {{ learning_rate }} * 
  (1 + {{ var('emotional_salience_weight', 1.2) }} * emotional_valence)
{% endmacro %}

{% macro semantic_clustering(embedding_column, n_clusters=5) %}
  -- Placeholder for semantic clustering
  -- In production, would use k-means or hierarchical clustering
  CASE
    WHEN {{ embedding_column }} IS NOT NULL THEN
      -- Simple hash-based clustering for testing
      MOD(ABS(HASH({{ embedding_column }}[1])), {{ n_clusters }})
    ELSE NULL
  END
{% endmacro %}