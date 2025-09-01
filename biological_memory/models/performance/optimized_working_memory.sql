{# 
  Optimized Working Memory Model - BMP-012 Performance Enhancement
  High-performance view with indexing and caching optimizations
#}

{{ config(
    materialized='ephemeral',
    tags=['working_memory', 'performance_optimized'],
    post_hook='{{ create_performance_indexes("raw_memories") }}'
) }}

-- Performance-optimized working memory query
WITH high_activation_memories AS (
  SELECT 
    memory_id,
    content,
    concepts,
    activation_strength,
    created_at,
    last_accessed_at,
    access_count,
    memory_type,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) as age_seconds,
    EXP(-LN(2) * {{ safe_divide('EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_accessed_at))', '3600.0', '1.0') }}) as recency_score,
    {{ safe_divide('LN(1 + access_count)', 'LN(101)', '0.0') }} as frequency_score
  FROM {{ source('codex_db', 'memories') }}
  WHERE 
    -- Optimized filters with indexes
    activation_strength > {{ var('plasticity_threshold') }}
    AND access_count >= 2
    -- Temporal filter for performance
    AND created_at > CURRENT_TIMESTAMP - INTERVAL '{{ var("short_term_memory_duration") }} SECONDS'
),

ranked_working_memories AS (
  SELECT *,
    ROW_NUMBER() OVER (
      ORDER BY 
        activation_strength DESC, 
        recency_score DESC,
        frequency_score DESC
    ) as memory_rank
  FROM high_activation_memories
)

SELECT 
  memory_id,
  content,
  concepts,
  activation_strength,
  created_at,
  last_accessed_at,
  access_count,
  'working_memory' as memory_type,
  age_seconds,
  recency_score,
  frequency_score,
  memory_rank,
  -- Optimized Hebbian calculation
  LEAST(1.0, activation_strength * {{ var('hebbian_learning_rate') }} + 0.1) as hebbian_strength,
  CURRENT_TIMESTAMP as processed_at
FROM ranked_working_memories
WHERE memory_rank <= {{ var('working_memory_capacity') }}