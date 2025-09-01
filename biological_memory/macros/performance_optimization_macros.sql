{# 
  Performance Optimization Macros for BMP-012
  Advanced performance optimizations including partitioning, caching, and batch processing
#}

{# Monthly partitioning for large memory tables #}
{% macro create_monthly_partitions(table_name, date_column) %}
  {# Create monthly partitions for improved query performance #}
  {% if execute %}
    {{ log("Setting up monthly partitioning for " ~ table_name, info=true) }}
    
    -- Create partition tables for current and next 3 months
    {% set months = ['2025-08', '2025-09', '2025-10', '2025-11'] %}
    {% for month in months %}
      {% set partition_name = table_name ~ "_" ~ month | replace('-', '_') %}
      CREATE TABLE IF NOT EXISTS {{ partition_name }} (
        LIKE {{ table_name }} INCLUDING ALL
      );
      
      -- Add check constraint for partition
      ALTER TABLE {{ partition_name }} 
      ADD CONSTRAINT check_{{ partition_name }}_date 
      CHECK (DATE_TRUNC('month', {{ date_column }}) = '{{ month }}-01'::DATE);
    {% endfor %}
    
    -- Create view for transparent access
    CREATE OR REPLACE VIEW {{ table_name }}_partitioned AS
    {% for month in months %}
      SELECT * FROM {{ table_name ~ "_" ~ month | replace('-', '_') }}
      {% if not loop.last %} UNION ALL {% endif %}
    {% endfor %};
    
    {{ log("Monthly partitioning setup complete for " ~ table_name, info=true) }}
  {% endif %}
{% endmacro %}

{# LLM response caching to reduce Ollama API calls #}
{% macro create_llm_cache() %}
  {# Create LLM response cache for semantic processing #}
  CREATE TABLE IF NOT EXISTS llm_response_cache (
    prompt_hash VARCHAR(64) PRIMARY KEY,
    prompt_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    model_name VARCHAR(50) NOT NULL DEFAULT 'ollama',
    temperature FLOAT DEFAULT {{ var('creativity_temperature') }},
    max_tokens INTEGER DEFAULT 1000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1,
    cache_hit_rate FLOAT DEFAULT 1.0
  );
  
  -- Create index for fast lookups
  CREATE INDEX IF NOT EXISTS idx_llm_cache_prompt ON llm_response_cache (prompt_hash);
  CREATE INDEX IF NOT EXISTS idx_llm_cache_accessed ON llm_response_cache (last_accessed_at DESC);
  
  {{ log("LLM response cache initialized", info=true) }}
{% endmacro %}

{# Cached LLM query function #}
{% macro get_cached_llm_response(prompt, model_name, temperature) %}
  {# Get LLM response with caching to improve performance #}
  {% set prompt_hash = "MD5('" ~ prompt ~ "||" ~ model_name ~ "||" ~ temperature ~ "')" %}
  
  WITH cached_response AS (
    SELECT response_text, access_count
    FROM llm_response_cache 
    WHERE prompt_hash = {{ prompt_hash }}
  ),
  fresh_response AS (
    -- Placeholder for actual LLM call - would integrate with Ollama API
    SELECT CASE 
      WHEN '{{ prompt }}' ILIKE '%semantic%' THEN 
        '{"analysis": "semantic_processing", "confidence": 0.85, "concepts": ["meaning", "context"]}'
      WHEN '{{ prompt }}' ILIKE '%creative%' THEN
        '{"analysis": "creative_synthesis", "confidence": 0.78, "novel_connections": ["innovation", "insight"]}'
      ELSE 
        '{"analysis": "general_processing", "confidence": 0.70, "processing": "completed"}'
    END as response_text,
    0 as access_count
    WHERE NOT EXISTS (SELECT 1 FROM cached_response)
  )
  SELECT 
    COALESCE(c.response_text, f.response_text) as llm_response,
    CASE WHEN c.response_text IS NOT NULL THEN TRUE ELSE FALSE END as cache_hit
  FROM cached_response c
  FULL OUTER JOIN fresh_response f ON TRUE;
  
  -- Update cache statistics
  INSERT INTO llm_response_cache (prompt_hash, prompt_text, response_text, model_name, temperature)
  SELECT {{ prompt_hash }}, '{{ prompt }}', response_text, '{{ model_name }}', {{ temperature }}
  FROM fresh_response
  WHERE NOT EXISTS (SELECT 1 FROM cached_response)
  ON CONFLICT (prompt_hash) 
  DO UPDATE SET 
    last_accessed_at = CURRENT_TIMESTAMP,
    access_count = llm_response_cache.access_count + 1;
{% endmacro %}

{# Batch processing for multiple memories #}
{% macro process_memory_batch(batch_size, operation) %}
  {# Process memories in batches for improved performance #}
  WITH memory_batches AS (
    SELECT *,
      CEIL(ROW_NUMBER() OVER (ORDER BY created_at DESC) / {{ batch_size }}.0) as batch_id
    FROM {{ source('biological_memory', 'raw_memories') }}
    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '{{ var('recent_activity_window') }} HOURS'
  )
  
  {% if operation == 'consolidation' %}
    SELECT 
      batch_id,
      COUNT(*) as batch_size,
      AVG(activation_strength) as avg_activation,
      STRING_AGG(content, ' | ') as batch_content,
      ARRAY_AGG(DISTINCT memory_type) as memory_types,
      MIN(created_at) as batch_start,
      MAX(created_at) as batch_end
    FROM memory_batches
    GROUP BY batch_id
    ORDER BY batch_id;
  
  {% elif operation == 'semantic_analysis' %}
    SELECT 
      batch_id,
      ARRAY_AGG(memory_id) as memory_ids,
      ARRAY_AGG(concepts) as concept_arrays,
      COUNT(*) as memories_in_batch,
      -- Batch semantic processing would go here
      'batch_processed' as status
    FROM memory_batches
    GROUP BY batch_id
    ORDER BY batch_id;
  
  {% else %}
    SELECT * FROM memory_batches ORDER BY batch_id, created_at;
  {% endif %}
{% endmacro %}

{# Connection pool monitoring #}
{% macro monitor_connection_pool() %}
  {# Monitor database connection usage #}
  CREATE OR REPLACE VIEW connection_pool_metrics AS
  SELECT 
    COUNT(*) as active_connections,
    160 as max_connections,
    ROUND({{ safe_divide('COUNT(*) * 100.0', '160', '0.0') }}, 2) as utilization_percentage,
    CASE 
      WHEN {{ safe_divide('COUNT(*)', '160.0', '0.0') }} > {{ var('high_quality_threshold') }} THEN 'HIGH'
      WHEN {{ safe_divide('COUNT(*)', '160.0', '0.0') }} > {{ var('medium_quality_threshold') }} THEN 'MEDIUM' 
      ELSE 'LOW'
    END as utilization_status,
    CURRENT_TIMESTAMP as measured_at
  FROM (
    SELECT 1 as dummy_connection -- Simulated connection data for monitoring template
    FROM generate_series(1, FLOOR(RANDOM() * 100 + 20)) -- Simulate 20-120 connections
  ) connections;
  
  {{ log("Connection pool monitoring view created", info=true) }}
{% endmacro %}

{# Optimized incremental processing #}
{% macro optimize_incremental_strategy(model_name, timestamp_column) %}
  {# Advanced incremental processing with change detection #}
  {% if is_incremental() %}
    
    -- Get the maximum timestamp from existing data
    {% set max_timestamp_query %}
      SELECT COALESCE(MAX({{ timestamp_column }}), '1900-01-01'::TIMESTAMP) as max_ts
      FROM {{ this }}
    {% endset %}
    
    {% if execute %}
      {% set results = run_query(max_timestamp_query) %}
      {% set max_timestamp = results[0][0] %}
      {{ log("Incremental processing from: " ~ max_timestamp, info=true) }}
    {% endif %}
    
    -- Enhanced incremental logic with change detection
    WITH incremental_changes AS (
      SELECT *,
        {{ timestamp_column }} > '{{ max_timestamp }}'::TIMESTAMP OR
        last_modified_at > '{{ max_timestamp }}'::TIMESTAMP OR
        activation_strength != LAG(activation_strength) OVER (PARTITION BY memory_id ORDER BY {{ timestamp_column }})
        as has_changes
      FROM {{ source('biological_memory', 'raw_memories') }}
      WHERE {{ timestamp_column }} >= '{{ max_timestamp }}'::TIMESTAMP - INTERVAL '{{ var('short_processing_window') }} HOURS'
    )
    SELECT * FROM incremental_changes WHERE has_changes = TRUE
    
  {% else %}
    -- Full refresh logic
    SELECT * FROM {{ source('biological_memory', 'raw_memories') }}
  {% endif %}
{% endmacro %}

{# Performance indexes for memory tables #}
{% macro create_performance_indexes(table_name) %}
  {# Create comprehensive performance indexes #}
  {% set indexes = [
    "CREATE INDEX IF NOT EXISTS idx_" ~ table_name ~ "_activation_desc ON " ~ table_name ~ " (activation_strength DESC)",
    "CREATE INDEX IF NOT EXISTS idx_" ~ table_name ~ "_created_at_desc ON " ~ table_name ~ " (created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_" ~ table_name ~ "_memory_type ON " ~ table_name ~ " (memory_type)",
    "CREATE INDEX IF NOT EXISTS idx_" ~ table_name ~ "_access_count ON " ~ table_name ~ " (access_count DESC)",
    "CREATE INDEX IF NOT EXISTS idx_" ~ table_name ~ "_compound ON " ~ table_name ~ " (memory_type, activation_strength DESC, created_at DESC)",
    -- PostgreSQL GIN index syntax not supported in DuckDB - using regular index instead
    "CREATE INDEX IF NOT EXISTS idx_" ~ table_name ~ "_concepts ON " ~ table_name ~ " (concepts)",
    -- PostgreSQL FTS syntax not supported in DuckDB - will need custom FTS implementation
    -- "CREATE INDEX IF NOT EXISTS idx_" ~ table_name ~ "_content_fts ON " ~ table_name ~ " USING fts(content)"
  ] %}
  
  {% for index_sql in indexes %}
    {{ index_sql }};
  {% endfor %}
  
  {{ log("Performance indexes created for " ~ table_name, info=true) }}
{% endmacro %}

{# Memory usage monitoring #}
{% macro monitor_memory_usage() %}
  {# Track memory usage and table sizes #}
  CREATE OR REPLACE VIEW memory_usage_stats AS
  SELECT 
    table_name,
    estimated_size_bytes,
    {{ safe_divide('estimated_size_bytes', '(1024*1024)', '0.0') }} as size_mb,
    row_count,
    ROUND(estimated_size_bytes / NULLIF(row_count, 0), 2) as bytes_per_row,
    last_analyzed
  FROM information_schema.tables t
  LEFT JOIN (
    SELECT 
      table_name,
      COUNT(*) as row_count
    FROM information_schema.tables
    GROUP BY table_name
  ) rc ON t.table_name = rc.table_name
  WHERE t.table_schema = 'main'
    AND t.table_name LIKE '%memor%'
  ORDER BY estimated_size_bytes DESC;
  
  {{ log("Memory usage monitoring view created", info=true) }}
{% endmacro %}

{# Query performance analyzer #}
{% macro analyze_query_performance(query_name, target_ms) %}
  {# Analyze and log query performance #}
  {% set start_time = modules.datetime.datetime.now() %}
  
  {{ caller() }}
  
  {% if execute %}
    {% set end_time = modules.datetime.datetime.now() %}
    {% set duration_ms = (end_time - start_time).total_seconds() * 1000 %}
    
    INSERT INTO performance_metrics (
      query_name, 
      duration_ms, 
      target_ms, 
      performance_ratio,
      executed_at
    ) VALUES (
      '{{ query_name }}',
      {{ duration_ms }},
      {{ target_ms }},
      {{ safe_divide(duration_ms, target_ms, '0.0') }},
      CURRENT_TIMESTAMP
    );
    
    {% if duration_ms > target_ms %}
      {{ log("PERFORMANCE WARNING: " ~ query_name ~ " took " ~ duration_ms ~ "ms (target: " ~ target_ms ~ "ms)", info=true) }}
    {% else %}
      {{ log("PERFORMANCE OK: " ~ query_name ~ " took " ~ duration_ms ~ "ms (target: " ~ target_ms ~ "ms)", info=true) }}
    {% endif %}
  {% endif %}
{% endmacro %}