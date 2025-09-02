{% macro calculate_hebbian_weight(pre_strength, post_strength, learning_rate=0.1) %}
  -- Calculate Hebbian learning weight: ΔW = η * Pre * Post
  -- Note: GIN indexes not supported in DuckDB for compatibility with PostgreSQL
  -- VACUUM operations removed for DuckDB compatibility as they are PostgreSQL specific
  ({{ learning_rate }} * {{ pre_strength }} * {{ post_strength }})
{% endmacro %}

{% macro apply_memory_decay(strength, decay_rate=0.05, time_elapsed=1) %}
  -- Apply exponential decay to memory strength
  ({{ strength }} * EXP(-{{ decay_rate }} * {{ time_elapsed }}))
{% endmacro %}

{% macro millers_capacity_constraint(memory_count, max_capacity=7) %}
  -- Enforce Miller's 7±2 working memory constraint
  CASE 
    WHEN {{ memory_count }} > {{ max_capacity }} THEN {{ max_capacity }}
    ELSE {{ memory_count }}
  END
{% endmacro %}