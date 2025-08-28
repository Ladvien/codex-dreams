{# 
  Biological Memory Processing Macros
  Advanced dbt macros implementing biological memory algorithms
  
  These macros implement core biological memory processes:
  - Hebbian learning strength calculation
  - Synaptic homeostasis maintenance  
  - Association strengthening
  - Memory consolidation logic
#}

{# Calculate Hebbian learning strength based on co-activation patterns #}
{% macro calculate_hebbian_strength(source_activation, target_activation, current_strength, learning_rate) %}
  {# Hebbian rule: "Neurons that fire together, wire together" #}
  {# ΔW = η × X₁ × X₂ × (1 - W) where η is learning rate #}
  (
    COALESCE({{ current_strength }}, 0.1) + 
    COALESCE({{ learning_rate }}, 0.01) * 
    COALESCE({{ source_activation }}, 0.0) * 
    COALESCE({{ target_activation }}, 0.0) * 
    (1.0 - COALESCE({{ current_strength }}, 0.1))
  )
{% endmacro %}

{# Implement synaptic homeostasis to prevent runaway strengthening #}
{% macro synaptic_homeostasis(connection_strength, homeostasis_target, adjustment_rate) %}
  {# Homeostatic scaling to maintain network stability #}
  {# Adjusts connection strength toward target to prevent saturation #}
  (
    COALESCE({{ connection_strength }}, 0.5) + 
    COALESCE({{ adjustment_rate }}, 0.01) * 
    (COALESCE({{ homeostasis_target }}, 0.5) - COALESCE({{ connection_strength }}, 0.5))
  )
{% endmacro %}

{# Strengthen associations based on frequency and recency #}
{% macro strengthen_associations() %}
  {# Pre-hook macro to strengthen memory associations before processing #}
  {% if execute %}
    {{ log("Strengthening memory associations based on usage patterns", info=true) }}
  {% endif %}
  
  -- Update association strengths using frequency and recency weights
  UPDATE {{ this.schema }}.memory_associations 
  SET 
    association_strength = LEAST(1.0, 
      association_strength + 
      (frequency_score * 0.3 + recency_score * 0.2) * {{ var('hebbian_learning_rate') }}
    ),
    last_strengthened_at = CURRENT_TIMESTAMP
  WHERE last_accessed_at > CURRENT_TIMESTAMP - INTERVAL '{{ var('consolidation_window_hours') }} HOURS'
{% endmacro %}

{# Calculate memory statistics for monitoring #}
{% macro calculate_memory_stats(memory_type) %}
  {# Post-hook macro to calculate and log memory statistics #}
  {% if execute %}
    {% set stats_query %}
      SELECT 
        COUNT(*) as total_memories,
        AVG(activation_strength) as avg_activation,
        MAX(activation_strength) as max_activation,
        COUNT(CASE WHEN activation_strength > {{ var('long_term_memory_threshold') }} THEN 1 END) as long_term_count
      FROM {{ this }}
    {% endset %}
    
    {% set results = run_query(stats_query) %}
    {% if results %}
      {% for row in results %}
        {{ log(memory_type ~ " stats - Total: " ~ row[0] ~ ", Avg Activation: " ~ row[1] ~ ", LTM Count: " ~ row[3], info=true) }}
      {% endfor %}
    {% endif %}
  {% endif %}
{% endmacro %}

{# Create optimized indexes for memory tables #}
{% macro create_memory_indexes() %}
  {# Post-hook macro to create performance indexes #}
  {% if execute %}
    {{ log("Creating optimized indexes for memory table", info=true) }}
  {% endif %}
  
  {% set index_statements = [
    "CREATE INDEX IF NOT EXISTS idx_" ~ this.name ~ "_activation ON " ~ this ~ " (activation_strength DESC)",
    "CREATE INDEX IF NOT EXISTS idx_" ~ this.name ~ "_timestamp ON " ~ this ~ " (created_at, last_accessed_at)",
    "CREATE INDEX IF NOT EXISTS idx_" ~ this.name ~ "_type ON " ~ this ~ " (memory_type)",
    "CREATE INDEX IF NOT EXISTS idx_" ~ this.name ~ "_concepts ON " ~ this ~ " USING GIN(concepts)"
  ] %}
  
  {% for statement in index_statements %}
    {{ statement }};
  {% endfor %}
{% endmacro %}

{# Update semantic knowledge graph connections #}
{% macro update_semantic_graph() %}
  {# Post-hook macro to maintain semantic relationship graph #}
  {% if execute %}
    {{ log("Updating semantic knowledge graph", info=true) }}
  {% endif %}
  
  -- Refresh materialized view of semantic connections
  REFRESH MATERIALIZED VIEW IF EXISTS {{ this.schema }}.semantic_graph_view;
  
  -- Update graph centrality measures
  UPDATE {{ this.schema }}.semantic_concepts 
  SET 
    centrality_score = (
      SELECT COUNT(*) * 1.0 / (SELECT COUNT(*) FROM {{ this.schema }}.semantic_concepts)
      FROM {{ this.schema }}.memory_associations ma
      WHERE ma.source_concept = semantic_concepts.concept_id 
         OR ma.target_concept = semantic_concepts.concept_id
    ),
    last_updated_at = CURRENT_TIMESTAMP;
{% endmacro %}

{# Decay unused synaptic connections over time #}
{% macro synaptic_decay(connection_table, decay_rate) %}
  {# Apply synaptic decay to unused connections #}
  UPDATE {{ connection_table }}
  SET 
    connection_strength = GREATEST(0.0,
      connection_strength * (1.0 - {{ decay_rate }})
    ),
    last_decayed_at = CURRENT_TIMESTAMP
  WHERE last_accessed_at < CURRENT_TIMESTAMP - INTERVAL '24 HOURS'
    AND connection_strength > 0.01  -- Only decay non-trivial connections
{% endmacro %}

{# Generate memory consolidation batch #}
{% macro get_consolidation_batch(batch_size) %}
  {# Select memories for consolidation based on biological criteria #}
  (
    SELECT memory_id, content, activation_strength, memory_type
    FROM {{ ref('working_memory') }}
    WHERE activation_strength > {{ var('plasticity_threshold') }}
      AND created_at > CURRENT_TIMESTAMP - INTERVAL '{{ var('short_term_memory_duration') }} SECONDS'
    ORDER BY activation_strength DESC, frequency_accessed DESC
    LIMIT {{ batch_size }}
  )
{% endmacro %}

{# Implement memory interference patterns #}
{% macro calculate_interference(similarity_score, time_difference) %}
  {# Calculate retroactive and proactive interference #}
  {# Higher similarity and closer timing = more interference #}
  (
    {{ similarity_score }} * EXP(-{{ time_difference }} / 3600.0)  -- Exponential decay over hours
  )
{% endmacro %}

{# Semantic similarity using vector operations #}
{% macro semantic_similarity(vector1, vector2) %}
  {# Calculate cosine similarity between semantic vectors #}
  {# Returns value between -1 and 1, where 1 is identical #}
  (
    array_dot_product({{ vector1 }}, {{ vector2 }}) / 
    (array_magnitude({{ vector1 }}) * array_magnitude({{ vector2 }}))
  )
{% endmacro %}
