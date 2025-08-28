{# 
  Utility Macros for Biological Memory Pipeline
  Helper functions for data processing and transformations
#}

{# Generate UUID for memory records #}
{% macro generate_memory_id() %}
  {# Create unique identifier for memory records #}
  {{ dbt_utils.generate_surrogate_key(['content', 'created_at', 'random()']) }}
{% endmacro %}

{# Convert timestamp to memory age in seconds #}
{% macro memory_age_seconds(created_at) %}
  {# Calculate memory age for decay calculations #}
  EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - {{ created_at }}))
{% endmacro %}

{# Normalize activation strength to 0-1 range #}
{% macro normalize_activation(raw_activation, min_val, max_val) %}
  {# Min-max normalization for activation values #}
  ({{ raw_activation }} - {{ min_val }}) / NULLIF({{ max_val }} - {{ min_val }}, 0)
{% endmacro %}

{# Calculate recency score using exponential decay #}
{% macro recency_score(last_accessed_at, half_life_hours) %}
  {# Exponential decay score based on last access time #}
  EXP(-LN(2) * {{ memory_age_seconds(last_accessed_at) }} / ({{ half_life_hours }} * 3600.0))
{% endmacro %}

{# Calculate frequency score using log scaling #}
{% macro frequency_score(access_count) %}
  {# Logarithmic scaling for frequency to prevent dominance #}
  LN(1 + {{ access_count }}) / LN(1 + 100)  -- Normalize to 0-1 range
{% endmacro %}

{# Memory type classification logic #}
{% macro classify_memory_type(activation_strength, age_hours, access_count) %}
  {# Classify memory into working/short-term/long-term based on biological criteria #}
  CASE 
    WHEN {{ age_hours }} < 0.5 AND {{ access_count }} >= 2 
      THEN 'working_memory'
    WHEN {{ age_hours }} < 24 AND {{ activation_strength }} > {{ var('plasticity_threshold') }}
      THEN 'short_term_memory'  
    WHEN {{ activation_strength }} > {{ var('long_term_memory_threshold') }}
      THEN 'long_term_memory'
    ELSE 'transient_memory'
  END
{% endmacro %}

{# Safe division to avoid divide by zero errors #}
{% macro safe_divide(numerator, denominator, default_value) %}
  {# Division with null/zero protection #}
  CASE 
    WHEN {{ denominator }} IS NULL OR {{ denominator }} = 0 
      THEN {{ default_value }}
    ELSE {{ numerator }} / {{ denominator }}
  END
{% endmacro %}

{# Create semantic embedding placeholder #}
{% macro create_embedding_placeholder(text_content, embedding_dim) %}
  {# Generate placeholder embedding vector until real embeddings are available #}
  ARRAY[{% for i in range(embedding_dim) %}
    MD5({{ text_content }} || '{{ i }}')::INT % 100 / 100.0
    {%- if not loop.last %},{% endif %}
  {% endfor %}]::FLOAT[]
{% endmacro %}

{# JSON extraction helper for flexible schema #}
{% macro extract_json_field(json_column, field_path, default_value) %}
  {# Safe JSON field extraction with default fallback #}
  COALESCE(
    ({{ json_column }} ->> '{{ field_path }}')::TEXT,
    '{{ default_value }}'
  )
{% endmacro %}

{# Memory consolidation priority score #}
{% macro consolidation_priority(activation_strength, frequency, recency, importance) %}
  {# Calculate priority for memory consolidation #}
  (
    {{ activation_strength }} * 0.4 +
    {{ frequency }} * 0.3 + 
    {{ recency }} * 0.2 +
    {{ importance }} * 0.1
  )
{% endmacro %}

{# Batch processing helper #}
{% macro process_in_batches(source_query, batch_size, batch_column) %}
  {# Template for batch processing large datasets #}
  WITH batched_data AS (
    SELECT *,
      ROW_NUMBER() OVER (ORDER BY {{ batch_column }}) as row_num,
      CEIL(ROW_NUMBER() OVER (ORDER BY {{ batch_column }}) / {{ batch_size }}.0) as batch_id
    FROM ({{ source_query }})
  )
  SELECT * FROM batched_data
{% endmacro %}

{# Time window helper for incremental models #}
{% macro get_incremental_window(timestamp_column, window_hours) %}
  {# Generate WHERE clause for incremental processing #}
  {% if is_incremental() %}
    WHERE {{ timestamp_column }} > (
      SELECT COALESCE(MAX({{ timestamp_column }}), '1900-01-01'::TIMESTAMP)
      FROM {{ this }}
    ) - INTERVAL '{{ window_hours }} HOURS'
  {% endif %}
{% endmacro %}
