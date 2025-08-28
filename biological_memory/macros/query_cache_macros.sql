{# 
  Advanced Query Result Caching Macros for BMP-MEDIUM-009
  Implements intelligent caching strategies for biological memory queries
  Target: Reduce query times from 100ms+ to <50ms through caching
#}

{# Smart query result caching with TTL and invalidation #}
{% macro create_query_cache() %}
  {# Create intelligent query result cache #}
  CREATE TABLE IF NOT EXISTS query_result_cache (
    cache_key VARCHAR PRIMARY KEY,
    query_hash VARCHAR NOT NULL,
    query_type VARCHAR NOT NULL,
    result_data JSON NOT NULL,
    cache_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cache_expires_at TIMESTAMP NOT NULL,
    access_count INTEGER DEFAULT 1,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cache_hit_rate DOUBLE DEFAULT 1.0,
    query_execution_time_ms DOUBLE,
    cached_row_count INTEGER DEFAULT 0
  );
  
  -- Indexes for fast cache lookups
  CREATE INDEX IF NOT EXISTS idx_query_cache_key ON query_result_cache (cache_key);
  CREATE INDEX IF NOT EXISTS idx_query_cache_expires ON query_result_cache (cache_expires_at);
  CREATE INDEX IF NOT EXISTS idx_query_cache_type ON query_result_cache (query_type, cache_created_at DESC);
  CREATE INDEX IF NOT EXISTS idx_query_cache_accessed ON query_result_cache (last_accessed_at DESC);
  
  {{ log("Query result cache initialized with intelligent caching", info=true) }}
{% endmacro %}

{# Generate cache key for query with parameters #}
{% macro generate_cache_key(query_name, params) %}
  {# Generate deterministic cache key #}
  'cache_' || MD5('{{ query_name }}' || '||' || '{{ params | tojsonstring }}')
{% endmacro %}

{# Cached query execution with TTL and smart invalidation #}
{% macro execute_cached_query(query_sql, query_name, query_type, cache_ttl_minutes) %}
  {# Execute query with intelligent caching layer #}
  {% set cache_key = generate_cache_key(query_name, "") %}
  
  WITH cache_lookup AS (
    -- Check if cached result exists and is still valid
    SELECT 
      result_data,
      cache_created_at,
      access_count,
      CASE 
        WHEN cache_expires_at > CURRENT_TIMESTAMP THEN TRUE 
        ELSE FALSE 
      END as cache_valid
    FROM query_result_cache 
    WHERE cache_key = {{ cache_key }}
  ),
  
  fresh_query AS (
    -- Execute fresh query if cache miss or expired
    SELECT 
      '{{ query_sql }}' as query_executed,
      CURRENT_TIMESTAMP as query_start
    WHERE NOT EXISTS (
      SELECT 1 FROM cache_lookup WHERE cache_valid = TRUE
    )
  ),
  
  query_results AS (
    -- This is where the actual query would be executed
    {{ query_sql }}
  )
  
  -- Return cached or fresh results
  SELECT 
    CASE 
      WHEN cl.cache_valid = TRUE THEN cl.result_data
      ELSE TO_JSON(qr)  -- Convert fresh results to JSON
    END as query_result,
    CASE WHEN cl.cache_valid = TRUE THEN TRUE ELSE FALSE END as cache_hit
  FROM cache_lookup cl
  FULL OUTER JOIN query_results qr ON TRUE;
  
  -- Update cache statistics
  INSERT INTO query_result_cache 
  (cache_key, query_hash, query_type, result_data, cache_expires_at, query_execution_time_ms, cached_row_count)
  SELECT 
    {{ cache_key }},
    MD5('{{ query_sql }}'),
    '{{ query_type }}',
    TO_JSON(({{ query_sql }})),
    CURRENT_TIMESTAMP + INTERVAL '{{ cache_ttl_minutes }} MINUTES',
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - (SELECT query_start FROM fresh_query))) * 1000,
    (SELECT COUNT(*) FROM ({{ query_sql }}) cnt)
  WHERE NOT EXISTS (SELECT 1 FROM cache_lookup WHERE cache_valid = TRUE)
  ON CONFLICT (cache_key) 
  DO UPDATE SET 
    last_accessed_at = CURRENT_TIMESTAMP,
    access_count = query_result_cache.access_count + 1;
{% endmacro %}

{# Working memory optimized caching (5 second TTL) #}
{% macro cache_working_memory_query(base_query) %}
  {# Ultra-fast caching for working memory queries #}
  {% set cache_key = "'wm_cache_' || EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::INTEGER / 5" %}
  
  WITH working_memory_cache AS (
    SELECT 
      result_data,
      cache_created_at
    FROM query_result_cache 
    WHERE cache_key = {{ cache_key }}
      AND query_type = 'working_memory'
      AND cache_expires_at > CURRENT_TIMESTAMP
    LIMIT 1
  ),
  
  fresh_working_memory AS (
    {{ base_query }}
    WHERE NOT EXISTS (SELECT 1 FROM working_memory_cache)
  )
  
  SELECT 
    COALESCE(
      -- Use cached result if available
      (SELECT result_data FROM working_memory_cache),
      -- Otherwise return fresh results  
      TO_JSON(ARRAY_AGG(fresh_working_memory))
    ) as working_memory_data,
    CASE WHEN working_memory_cache.result_data IS NOT NULL THEN TRUE ELSE FALSE END as cache_hit
  FROM working_memory_cache
  FULL OUTER JOIN fresh_working_memory ON TRUE;
{% endmacro %}

{# Semantic similarity result caching (30 minute TTL) #}
{% macro cache_semantic_similarity(concept_query) %}
  {# Cache computationally expensive semantic similarity calculations #}
  {% set similarity_cache_key = "'sem_' || MD5('" ~ concept_query ~ "')" %}
  
  WITH similarity_cache AS (
    SELECT result_data
    FROM query_result_cache
    WHERE cache_key = {{ similarity_cache_key }}
      AND query_type = 'semantic_similarity'  
      AND cache_expires_at > CURRENT_TIMESTAMP
  ),
  
  fresh_similarity AS (
    {{ concept_query }}
    WHERE NOT EXISTS (SELECT 1 FROM similarity_cache)
  )
  
  SELECT 
    COALESCE(
      similarity_cache.result_data,
      TO_JSON(ARRAY_AGG(fresh_similarity))
    ) as similarity_results
  FROM similarity_cache
  FULL OUTER JOIN fresh_similarity ON TRUE;
  
  -- Cache the expensive similarity calculation
  INSERT INTO query_result_cache 
  (cache_key, query_hash, query_type, result_data, cache_expires_at)
  SELECT 
    {{ similarity_cache_key }},
    MD5('{{ concept_query }}'),
    'semantic_similarity',
    TO_JSON(ARRAY_AGG(fresh_similarity)),
    CURRENT_TIMESTAMP + INTERVAL '30 MINUTES'
  FROM fresh_similarity
  WHERE NOT EXISTS (SELECT 1 FROM similarity_cache);
{% endmacro %}

{# LLM response caching with smart invalidation #}
{% macro cache_llm_response(prompt_text, model_name, temperature) %}
  {# Advanced caching for LLM responses with deduplication #}
  {% set llm_cache_key = "'llm_' || MD5('" ~ prompt_text ~ "||" ~ model_name ~ "||" ~ temperature ~ "')" %}
  
  WITH llm_cache_lookup AS (
    SELECT 
      response_text,
      access_count,
      cache_created_at
    FROM llm_response_cache
    WHERE prompt_hash = MD5('{{ prompt_text }}||{{ model_name }}||{{ temperature }}')
      AND created_at > CURRENT_TIMESTAMP - INTERVAL '24 HOURS'  -- 24h TTL
  ),
  
  fresh_llm_response AS (
    -- This would call the actual LLM service
    SELECT 
      CASE 
        WHEN '{{ prompt_text }}' ILIKE '%semantic%' THEN 
          '{"analysis": "semantic_processing", "confidence": 0.85}'
        WHEN '{{ prompt_text }}' ILIKE '%creative%' THEN
          '{"analysis": "creative_synthesis", "confidence": 0.78}'
        ELSE 
          '{"analysis": "general_processing", "confidence": 0.70}'
      END as llm_response
    WHERE NOT EXISTS (SELECT 1 FROM llm_cache_lookup)
  )
  
  SELECT 
    COALESCE(llm_cache_lookup.response_text, fresh_llm_response.llm_response) as response,
    CASE WHEN llm_cache_lookup.response_text IS NOT NULL THEN TRUE ELSE FALSE END as cache_hit,
    COALESCE(llm_cache_lookup.access_count, 0) as previous_access_count
  FROM llm_cache_lookup
  FULL OUTER JOIN fresh_llm_response ON TRUE;
{% endmacro %}

{# Cache invalidation and cleanup #}
{% macro cleanup_expired_caches() %}
  {# Clean up expired cache entries to maintain performance #}
  DELETE FROM query_result_cache 
  WHERE cache_expires_at < CURRENT_TIMESTAMP;
  
  DELETE FROM llm_response_cache 
  WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '7 DAYS'
    AND access_count = 1;  -- Only cleanup rarely accessed entries
  
  -- Update cache statistics
  UPDATE query_result_cache 
  SET cache_hit_rate = {{ safe_divide('access_count * 1.0', 'GREATEST(1, access_count)', '1.0') }}
  WHERE last_accessed_at > CURRENT_TIMESTAMP - INTERVAL '1 HOUR';
  
  {{ log("Cache cleanup completed - expired entries removed", info=true) }}
{% endmacro %}

{# Cache performance metrics #}
{% macro cache_performance_metrics() %}
  {# Generate cache performance analytics #}
  CREATE OR REPLACE VIEW cache_performance_dashboard AS
  WITH cache_stats AS (
    SELECT 
      query_type,
      COUNT(*) as total_cached_queries,
      AVG(access_count) as avg_access_count,
      SUM(CASE WHEN access_count > 1 THEN 1 ELSE 0 END) as cache_hits,
      AVG(query_execution_time_ms) as avg_original_execution_time,
      MAX(last_accessed_at) as most_recent_access
    FROM query_result_cache
    WHERE cache_created_at > CURRENT_TIMESTAMP - INTERVAL '24 HOURS'
    GROUP BY query_type
  )
  SELECT 
    query_type,
    total_cached_queries,
    cache_hits,
    ROUND({{ safe_divide('cache_hits * 100.0', 'total_cached_queries', '0.0') }}, 2) as cache_hit_rate_percent,
    ROUND(avg_original_execution_time, 2) as avg_saved_time_ms,
    ROUND(avg_access_count, 2) as avg_access_count,
    most_recent_access,
    CASE 
      WHEN {{ safe_divide('cache_hits * 100.0', 'total_cached_queries', '0.0') }} >= 80 THEN 'EXCELLENT'
      WHEN {{ safe_divide('cache_hits * 100.0', 'total_cached_queries', '0.0') }} >= 60 THEN 'GOOD'
      WHEN {{ safe_divide('cache_hits * 100.0', 'total_cached_queries', '0.0') }} >= 40 THEN 'FAIR'
      ELSE 'NEEDS_OPTIMIZATION'
    END as cache_efficiency_rating
  FROM cache_stats
  ORDER BY cache_hit_rate_percent DESC;
  
  {{ log("Cache performance dashboard created", info=true) }}
{% endmacro %}

{# Adaptive cache TTL based on query patterns #}
{% macro adaptive_cache_ttl(query_type, base_ttl_minutes) %}
  {# Dynamically adjust cache TTL based on access patterns #}
  {% set adaptive_ttl %}
    CASE 
      WHEN '{{ query_type }}' = 'working_memory' THEN {{ base_ttl_minutes }} / 12  -- 5 seconds for working memory
      WHEN '{{ query_type }}' = 'semantic_similarity' THEN {{ base_ttl_minutes }} * 6  -- 30 minutes for similarity
      WHEN '{{ query_type }}' = 'consolidation' THEN {{ base_ttl_minutes }} * 2  -- 10 minutes for consolidation
      WHEN '{{ query_type }}' = 'analytics' THEN {{ base_ttl_minutes }} / 2  -- 2.5 minutes for analytics
      ELSE {{ base_ttl_minutes }}  -- Default TTL
    END
  {% endset %}
  
  {{ adaptive_ttl }}
{% endmacro %}