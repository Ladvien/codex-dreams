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