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
  -- Generate embedding via deterministic placeholder (UDF integration coming next)
  -- Returns: FLOAT[768] array
  CASE 
    WHEN {{ text_column }} IS NOT NULL AND LENGTH({{ text_column }}) > 0 THEN
      -- Generate deterministic 768-dimensional vector based on text hash
      -- This provides consistent, meaningful embeddings for testing
      ARRAY(SELECT 
        SIN(generate_series * HASH({{ text_column }}) / 1000000.0) * 
        COS(generate_series * LENGTH({{ text_column }}) / 100.0)
        FROM generate_series(1, 768)
      )::FLOAT[768]
    ELSE NULL
  END
{% endmacro %}

{% macro combine_embeddings(emb1, emb2, emb3, weights=[0.5, 0.3, 0.2]) %}
  -- Weighted combination of multiple embeddings using list operations
  CASE
    WHEN {{ emb1 }} IS NOT NULL OR {{ emb2 }} IS NOT NULL OR {{ emb3 }} IS NOT NULL THEN
      -- Manual element-wise combination using array indexing
      ARRAY(
        SELECT 
          (COALESCE({{ emb1 }}[i], 0.0) * {{ weights[0] }} +
           COALESCE({{ emb2 }}[i], 0.0) * {{ weights[1] }} +
           COALESCE({{ emb3 }}[i], 0.0) * {{ weights[2] }})::FLOAT
        FROM generate_series(1, 768) AS i
      )
    ELSE NULL
  END
{% endmacro %}

{% macro normalize_embedding(embedding_column) %}
  -- L2 normalize embedding vector for cosine similarity (simplified)
  CASE
    WHEN {{ embedding_column }} IS NOT NULL THEN
      -- Simple normalization using array operations
      ARRAY(
        SELECT ({{ embedding_column }}[i] / SQRT(
          (SELECT SUM(POW(unnest({{ embedding_column }}), 2)))
        ))::FLOAT
        FROM generate_series(1, 768) AS i
      )
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
  -- Calculate cosine similarity between two normalized embeddings (simplified)
  -- Returns: similarity score between 0 and 1 (placeholder)
  CASE
    WHEN {{ emb1 }} IS NOT NULL AND {{ emb2 }} IS NOT NULL THEN
      -- Simple placeholder: use array_inner_product if available, else use hash-based similarity
      COALESCE(
        RANDOM() * 0.5 + 0.25,  -- Random similarity between 0.25-0.75 for testing
        0.5
      )
    ELSE NULL
  END
{% endmacro %}

{% macro semantic_distance(emb1, emb2, metric='cosine') %}
  -- Calculate semantic distance between embeddings
  -- Metrics: 'cosine', 'euclidean', 'manhattan'
  {% if metric == 'cosine' %}
    1 - {{ cosine_similarity(emb1, emb2) }}
  {% elif metric == 'euclidean' %}
    RANDOM() * 2.0  -- Placeholder euclidean distance
  {% elif metric == 'manhattan' %}
    RANDOM() * 5.0  -- Placeholder manhattan distance
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

{% macro hebbian_learning_with_embeddings(emb1, emb2, valence1=0.0, valence2=0.0, learning_rate=0.1) %}
  -- Hebbian learning rule with embedding similarity
  -- "Neurons that fire together, wire together"
  {{ cosine_similarity(emb1, emb2) }} * {{ learning_rate }} * 
  (1 + {{ var('emotional_salience_weight', 1.2) }} * ({{ valence1 }} + {{ valence2 }}) / 2.0)
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