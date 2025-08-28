{# 
  Working Memory Active Memories Model
  Materialized as VIEW for real-time access to current working memory
  
  Working memory holds 7±2 items actively being processed
  High-speed access, temporary storage, frequent updates
#}

{{ config(
    materialized='view',
    tags=['working_memory', 'real_time'],
    post_hook='{{ calculate_memory_stats("working_memory") }}'
) }}

WITH current_working_set AS (
  SELECT 
    {{ generate_memory_id() }} as memory_id,
    COALESCE(content, 'No content') as content,
    COALESCE(concepts, ['unknown']) as concepts,
    COALESCE(activation_strength, 0.1) as activation_strength,
    COALESCE(created_at, NOW()) as created_at,
    COALESCE(last_accessed_at, NOW()) as last_accessed_at,
    COALESCE(access_count, 0) as access_count,
    COALESCE(memory_type, 'working_memory') as memory_type,
    {{ memory_age_seconds('COALESCE(created_at, NOW())') }} as age_seconds,
    {{ recency_score('COALESCE(last_accessed_at, NOW())', 1) }} as recency_score,
    {{ frequency_score('COALESCE(access_count, 0)') }} as frequency_score
  FROM {{ source('self_sensored', 'raw_memories') }}
  WHERE 
    -- Only recent, highly active memories in working memory - NULL SAFE
    COALESCE(created_at, '1900-01-01'::TIMESTAMP) > CURRENT_TIMESTAMP - INTERVAL '{{ var("short_term_memory_duration") }} SECONDS'
    AND COALESCE(activation_strength, 0.0) > {{ var('plasticity_threshold') }}
    AND COALESCE(access_count, 0) >= 2
),

ranked_memories AS (
  SELECT *,
    ROW_NUMBER() OVER (
      ORDER BY 
        COALESCE(activation_strength, 0.0) DESC, 
        COALESCE(recency_score, 0.0) DESC,
        COALESCE(frequency_score, 0.0) DESC
    ) as memory_rank
  FROM current_working_set
)

SELECT 
  memory_id,
  COALESCE(content, 'No content') as content,
  COALESCE(concepts, ARRAY['unknown']) as concepts,
  COALESCE(activation_strength, 0.1) as activation_strength,
  COALESCE(created_at, NOW()) as created_at,
  COALESCE(last_accessed_at, NOW()) as last_accessed_at,
  COALESCE(access_count, 0) as access_count,
  'working_memory' as memory_type,
  COALESCE(age_seconds, 0) as age_seconds,
  COALESCE(recency_score, 0.0) as recency_score,
  COALESCE(frequency_score, 0.0) as frequency_score,
  COALESCE(memory_rank, 1) as memory_rank,
  -- Hebbian strength calculation for active processing - NULL SAFE
  LEAST(1.0, COALESCE(activation_strength, 0.1) * {{ var('hebbian_learning_rate') }} + 
    COALESCE(previous_strength, 0.1)) as hebbian_strength,
  CURRENT_TIMESTAMP as processed_at
FROM ranked_memories
WHERE COALESCE(memory_rank, 1) <= {{ var('working_memory_capacity') }}
