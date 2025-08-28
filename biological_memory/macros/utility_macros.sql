{# 
  Utility Macros for Biological Memory Pipeline
  Helper functions for data processing and transformations
#}

{# Generate UUID for memory records - NULL SAFE #}
{% macro generate_memory_id() %}
  {# Create unique identifier for memory records with null safety #}
  {{ dbt_utils.generate_surrogate_key(['COALESCE(content, \'no_content\')', 'COALESCE(created_at, NOW())', 'random()']) }}
{% endmacro %}

{# Convert timestamp to memory age in seconds #}
{% macro memory_age_seconds(created_at) %}
  {# Calculate memory age for decay calculations #}
  EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - {{ created_at }}))
{% endmacro %}

{# Normalize activation strength to 0-1 range - NULL SAFE #}
{% macro normalize_activation(raw_activation, min_val, max_val) %}
  {# Min-max normalization for activation values with null safety #}
  COALESCE(
    {{ safe_divide('(COALESCE(' ~ raw_activation ~ ', 0.0) - COALESCE(' ~ min_val ~ ', 0.0))', 'NULLIF(COALESCE(' ~ max_val ~ ', 1.0) - COALESCE(' ~ min_val ~ ', 0.0), 0)', '0.0') }},
    0.0
  )
{% endmacro %}

{# Calculate recency score using exponential decay - NULL SAFE #}
{% macro recency_score(last_accessed_at, half_life_hours) %}
  {# Exponential decay score based on last access time with null safety #}
  COALESCE(
    EXP(-LN(2) * {{ safe_divide(memory_age_seconds('COALESCE(' ~ last_accessed_at ~ ', NOW())'), '(COALESCE(' ~ half_life_hours ~ ', 1.0) * 3600.0)', '1.0') }}),
    1.0
  )
{% endmacro %}

{# Calculate frequency score using log scaling - NULL SAFE #}
{% macro frequency_score(access_count) %}
  {# Logarithmic scaling for frequency to prevent dominance with null safety #}
  COALESCE(
    {{ safe_divide('LN(1 + GREATEST(COALESCE(' ~ access_count ~ ', 0), 0))', 'LN(1 + 100)', '0.0') }},
    0.0
  )  -- Normalize to 0-1 range
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

{# Create semantic embedding placeholder - NULL SAFE #}
{% macro create_embedding_placeholder(text_content, embedding_dim) %}
  {# Generate placeholder embedding vector with null safety - DuckDB compatible #}
  COALESCE(
    [{% for i in range(embedding_dim) %}
      {{ safe_divide('ABS(hash(COALESCE(' ~ text_content ~ ', \'empty_content\') || \'' ~ i ~ '\') % 10000)', '10000.0', '0.1') }}
      {%- if not loop.last %},{% endif %}
    {% endfor %}]::FLOAT[],
    [{% for i in range(embedding_dim) %}
      0.1{%- if not loop.last %},{% endif %}
    {% endfor %}]::FLOAT[]
  )
{% endmacro %}

{# JSON extraction helper for flexible schema - ENHANCED NULL SAFETY #}
{% macro extract_json_field(json_column, field_path, default_value) %}
  {# Enhanced safe JSON field extraction with validation and default fallback #}
  COALESCE(
    CASE 
      WHEN {{ json_column }} IS NOT NULL AND JSON_VALID({{ json_column }}::TEXT) 
      THEN ({{ json_column }} ->> '{{ field_path }}')::TEXT
      ELSE NULL
    END,
    '{{ default_value }}'
  )
{% endmacro %}

{# Memory consolidation priority score - NULL SAFE #}
{% macro consolidation_priority(activation_strength, frequency, recency, importance) %}
  {# Calculate priority for memory consolidation with null safety #}
  (
    COALESCE({{ activation_strength }}, 0.1) * 0.4 +
    COALESCE({{ frequency }}, 0.0) * 0.3 + 
    COALESCE({{ recency }}, 0.0) * 0.2 +
    COALESCE({{ importance }}, 0.0) * 0.1
  )
{% endmacro %}

{# Batch processing helper #}
{% macro process_in_batches(source_query, batch_size, batch_column) %}
  {# Template for batch processing large datasets #}
  WITH batched_data AS (
    SELECT *,
      ROW_NUMBER() OVER (ORDER BY {{ batch_column }}) as row_num,
      CEIL({{ safe_divide('ROW_NUMBER() OVER (ORDER BY ' ~ batch_column ~ ')', batch_size ~ '.0', '1.0') }}) as batch_id
    FROM ({{ source_query }})
  )
  SELECT * FROM batched_data
{% endmacro %}

{# Time window helper for incremental models - NULL SAFE #}
{% macro get_incremental_window(timestamp_column, window_hours) %}
  {# Generate WHERE clause for incremental processing with null safety #}
  {% if is_incremental() %}
    WHERE COALESCE({{ timestamp_column }}, '1900-01-01'::TIMESTAMP) > (
      SELECT COALESCE(MAX(COALESCE({{ timestamp_column }}, '1900-01-01'::TIMESTAMP)), '1900-01-01'::TIMESTAMP)
      FROM {{ this }}
    ) - INTERVAL '{{ window_hours }} HOURS'
  {% endif %}
{% endmacro %}

{# Enhanced null-safe array operations #}
{% macro safe_array_access(array_col, index, default_value) %}
  {# Safely access array element with bounds checking #}
  COALESCE(
    CASE 
      WHEN {{ array_col }} IS NOT NULL 
           AND len({{ array_col }}) >= {{ index }}
           AND {{ index }} > 0
      THEN {{ array_col }}[{{ index }}]
      ELSE NULL
    END,
    {{ default_value }}
  )
{% endmacro %}

{# Safe JSON array extraction #}
{% macro safe_json_array_extract(json_col, index, default_value) %}
  {# Safely extract from JSON array with null checking #}
  COALESCE(
    CASE 
      WHEN {{ json_col }} IS NOT NULL 
           AND JSON_VALID({{ json_col }}::TEXT)
           AND JSON_TYPE({{ json_col }}) = 'array'
           AND JSON_ARRAY_LENGTH({{ json_col }}) > {{ index }}
      THEN JSON_EXTRACT_STRING({{ json_col }}, '$[{{ index }}]')
      ELSE NULL
    END,
    '{{ default_value }}'
  )
{% endmacro %}

{# Null-safe mathematical operations #}
{% macro safe_math_operation(operation, operand1, operand2, default_value) %}
  {# Perform mathematical operations with null safety #}
  COALESCE(
    CASE 
      WHEN '{{ operation }}' = 'divide' AND COALESCE({{ operand2 }}, 0) != 0
      THEN COALESCE({{ operand1 }}, 0.0) / COALESCE({{ operand2 }}, 1.0)
      WHEN '{{ operation }}' = 'multiply'
      THEN COALESCE({{ operand1 }}, 0.0) * COALESCE({{ operand2 }}, 0.0)
      WHEN '{{ operation }}' = 'add'
      THEN COALESCE({{ operand1 }}, 0.0) + COALESCE({{ operand2 }}, 0.0)
      WHEN '{{ operation }}' = 'subtract'
      THEN COALESCE({{ operand1 }}, 0.0) - COALESCE({{ operand2 }}, 0.0)
      ELSE NULL
    END,
    {{ default_value }}
  )
{% endmacro %}
