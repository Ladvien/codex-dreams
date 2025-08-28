{# 
  LLM Response Cache Metrics - BMP-012 Performance Optimization
  Monitors LLM caching performance and hit rates
#}

{{ config(
    materialized='view',
    tags=['caching', 'performance', 'llm'],
    post_hook='{{ create_llm_cache() }}'
) }}

-- LLM Cache Performance Analytics
WITH cache_statistics AS (
  SELECT 
    COUNT(*) as total_cached_responses,
    COUNT(DISTINCT prompt_text) as unique_prompts,
    AVG(access_count) as avg_access_count,
    SUM(access_count) as total_cache_hits,
    MAX(last_accessed_at) as most_recent_access,
    MIN(created_at) as oldest_cache_entry
  FROM llm_response_cache
  WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 HOURS'
),

cache_performance AS (
  SELECT 
    CASE 
      WHEN total_cache_hits > 0 THEN 
        {{ safe_divide('(total_cache_hits - total_cached_responses) * 100.0', 'total_cache_hits', '0.0') }}
      ELSE 0.0 
    END as cache_hit_rate_percent,
    
    CASE 
      WHEN cache_hit_rate_percent >= 80 THEN 'EXCELLENT'
      WHEN cache_hit_rate_percent >= 60 THEN 'GOOD'  
      WHEN cache_hit_rate_percent >= 40 THEN 'FAIR'
      ELSE 'NEEDS_IMPROVEMENT'
    END as performance_rating
  FROM cache_statistics
)

SELECT 
  cs.total_cached_responses,
  cs.unique_prompts,
  cs.avg_access_count,
  cs.total_cache_hits,
  cp.cache_hit_rate_percent,
  cp.performance_rating,
  cs.most_recent_access,
  cs.oldest_cache_entry,
  
  -- Cache efficiency metrics
  CASE 
    WHEN cs.unique_prompts > 0 THEN 
      {{ safe_divide('cs.total_cached_responses * 1.0', 'cs.unique_prompts', '0.0') }}
    ELSE 0.0
  END as cache_efficiency_ratio,
  
  CURRENT_TIMESTAMP as metrics_generated_at
  
FROM cache_statistics cs
CROSS JOIN cache_performance cp