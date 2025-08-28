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
    content,
    concepts,
    activation_strength,
    created_at,
    last_accessed_at,
    access_count,
    memory_type,
    {{ memory_age_seconds('created_at') }} as age_seconds,
    {{ recency_score('last_accessed_at', 1) }} as recency_score,
    {{ frequency_score('access_count') }} as frequency_score
  FROM {{ source('biological_memory', 'raw_memories') }}
  WHERE 
    -- Only recent, highly active memories in working memory
    created_at > CURRENT_TIMESTAMP - INTERVAL '{{ var("short_term_memory_duration") }} SECONDS'
    AND activation_strength > {{ var('plasticity_threshold') }}
    AND access_count >= 2
),

ranked_memories AS (
  SELECT *,
    ROW_NUMBER() OVER (
      ORDER BY 
        activation_strength DESC, 
        recency_score DESC,
        frequency_score DESC
    ) as memory_rank
  FROM current_working_set
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
  -- Hebbian strength calculation for active processing
  {{ calculate_hebbian_strength(
    'activation_strength', 
    'recency_score', 
    'COALESCE(previous_strength, 0.1)', 
    var('hebbian_learning_rate')
  ) }} as hebbian_strength,
  CURRENT_TIMESTAMP as processed_at
FROM ranked_memories
WHERE memory_rank <= {{ var('working_memory_capacity') }}
