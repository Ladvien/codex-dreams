{#
  Short-Term Memory Consolidating Memories Model
  Materialized as INCREMENTAL for efficient processing of new memories
  
  Handles memories in transition from working to long-term storage
  Implements biological consolidation processes
#}

{{ config(
    materialized='incremental',
    unique_key='memory_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns',
    tags=['short_term_memory', 'consolidation'],
    pre_hook='{{ strengthen_associations() }}'
) }}

WITH source_memories AS (
  SELECT *
  FROM {{ ref('active_memories') }}
  
  {{ get_incremental_window('last_accessed_at', 2) }}
),

consolidation_candidates AS (
  SELECT 
    memory_id,
    content,
    concepts,
    activation_strength,
    created_at,
    last_accessed_at,
    access_count,
    recency_score,
    frequency_score,
    hebbian_strength,
    -- Calculate consolidation priority
    {{ consolidation_priority(
      'activation_strength',
      'frequency_score', 
      'recency_score',
      'COALESCE(importance_score, 0.5)'
    ) }} as consolidation_priority,
    
    -- Apply synaptic homeostasis (simplified calculation)
    LEAST(1.0, activation_strength * (1.0 + ({{ var('homeostasis_target') }} - activation_strength) * 0.1)) as homeostatic_strength,
    
    -- Calculate interference from similar memories
    (
      SELECT AVG({{ calculate_interference('similarity_score', 'time_diff_hours') }})
      FROM {{ source('self_sensored', 'memory_similarities') }} ms
      WHERE ms.target_memory_id = source_memories.memory_id
    ) as interference_score,
    
    CURRENT_TIMESTAMP as consolidated_at
  FROM source_memories
  WHERE 
    -- Biological criteria for consolidation
    {{ memory_age_seconds('created_at') }} > {{ var('short_term_memory_duration') }}
    AND activation_strength > {{ var('plasticity_threshold') }}
    AND access_count >= 3
),

final_consolidation AS (
  SELECT *,
    -- Final activation strength after homeostasis and interference
    GREATEST(0.0, LEAST(1.0, 
      homeostatic_strength - (interference_score * 0.2)
    )) as final_activation_strength,
    
    -- Memory type classification
    {{ classify_memory_type(
      'homeostatic_strength',
      '{{ safe_divide(' ~ memory_age_seconds('created_at') ~ ', \'3600.0\', \'0.0\') }}',
      'access_count'
    ) }} as classified_memory_type
  FROM consolidation_candidates
)

SELECT 
  memory_id,
  content,
  concepts,
  final_activation_strength as activation_strength,
  created_at,
  last_accessed_at,
  access_count,
  classified_memory_type as memory_type,
  recency_score,
  frequency_score,
  hebbian_strength,
  consolidation_priority,
  interference_score,
  consolidated_at,
  -- Batch processing for performance
  CEIL({{ safe_divide('ROW_NUMBER() OVER (ORDER BY consolidation_priority DESC) * 1.0', var('consolidation_batch_size'), '1') }}) as consolidation_batch
FROM final_consolidation
WHERE final_activation_strength > 0.1  -- Filter out decayed memories
