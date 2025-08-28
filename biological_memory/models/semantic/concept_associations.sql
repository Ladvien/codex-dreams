{#
  Semantic Concept Associations Model
  Materialized as INCREMENTAL for efficient semantic graph updates
  
  Manages the semantic knowledge graph connecting related concepts
  Implements associative learning and concept clustering
#}

{{ config(
    materialized='incremental',
    unique_key=['source_concept', 'target_concept'],
    incremental_strategy='merge',
    on_schema_change='append_new_columns',
    tags=['semantic', 'knowledge_graph', 'associations'],
    pre_hook='{{ strengthen_associations() }}',
    post_hook='{{ update_semantic_graph() }}'
) }}

WITH concept_pairs AS (
  SELECT DISTINCT
    concept1 as source_concept,
    concept2 as target_concept
  FROM (
    SELECT 
      unnest(COALESCE(concepts, ['unknown_concept'])) as concept1,
      unnest(COALESCE(concepts, ['unknown_concept'])) as concept2,
      memory_id,
      COALESCE(activation_strength, 0.1)
    FROM {{ ref('stable_memories') }}
    WHERE COALESCE(len(concepts), 0) > 1
    
    {% if is_incremental() %}
      AND COALESCE(last_processed_at, '1900-01-01'::TIMESTAMP) > (
        SELECT COALESCE(MAX(last_updated_at), '1900-01-01'::TIMESTAMP)
        FROM {{ this }}
      ) - INTERVAL '1 HOUR'
    {% endif %}
  ) cross_concepts
  WHERE concept1 != concept2
    AND concept1 < concept2  -- Avoid duplicate pairs
),

co_occurrence_analysis AS (
  SELECT 
    cp.source_concept,
    cp.target_concept,
    COUNT(*) as co_occurrence_count,
    AVG(COALESCE(sm.activation_strength, 0.1)) as avg_activation_strength,
    MAX(COALESCE(sm.activation_strength, 0.1)) as max_activation_strength,
    COUNT(DISTINCT sm.memory_id) as shared_memories,
    
    -- Temporal co-occurrence patterns - NULL SAFE
    COUNT(CASE WHEN COALESCE(sm.created_at, '1900-01-01'::TIMESTAMP) > CURRENT_TIMESTAMP - INTERVAL '24 HOURS' 
          THEN 1 END) as recent_co_occurrences,
    COUNT(CASE WHEN COALESCE(sm.created_at, '1900-01-01'::TIMESTAMP) > CURRENT_TIMESTAMP - INTERVAL '7 DAYS' 
          THEN 1 END) as weekly_co_occurrences,
          
    -- Semantic similarity estimation - NULL SAFE
    COALESCE(
      {{ semantic_similarity('COALESCE(concept_vectors.vector1, [0.0])', 'COALESCE(concept_vectors.vector2, [0.0])') }},
      0.0
    ) as semantic_similarity
    
  FROM concept_pairs cp
  JOIN {{ ref('stable_memories') }} sm ON (
    list_contains(COALESCE(sm.concepts, ['unknown_concept']), cp.source_concept) AND 
    list_contains(COALESCE(sm.concepts, ['unknown_concept']), cp.target_concept)
  )
  LEFT JOIN (
    SELECT 
      concept1,
      concept2,
      {{ create_embedding_placeholder('concept1', 128) }} as vector1,
      {{ create_embedding_placeholder('concept2', 128) }} as vector2
    FROM concept_pairs
  ) concept_vectors ON (
    concept_vectors.concept1 = cp.source_concept AND
    concept_vectors.concept2 = cp.target_concept
  )
  GROUP BY 
    cp.source_concept, 
    cp.target_concept, 
    concept_vectors.vector1,
    concept_vectors.vector2
),

association_strength_calculation AS (
  SELECT *,
    -- Calculate association strength using multiple factors
    (
      -- Co-occurrence frequency (normalized) - NULL SAFE
      {{ safe_divide('LN(1 + COALESCE(co_occurrence_count, 1))', 'LN(1 + 100)', '0.0') }} * 0.3 +
      
      -- Average activation strength of shared memories
      COALESCE(avg_activation_strength, 0.1) * 0.25 +
      
      -- Recent activity bias
      LEAST(1.0, {{ safe_divide('COALESCE(recent_co_occurrences, 0)', '10.0', '0.0') }}) * 0.2 +
      
      -- Semantic similarity
      GREATEST(0.0, COALESCE(semantic_similarity, 0.0)) * 0.15 +
      
      -- Shared memory diversity
      LEAST(1.0, {{ safe_divide('COALESCE(shared_memories, 1)', '20.0', '0.0') }}) * 0.1
      
    ) as raw_association_strength,
    
    -- Hebbian learning application (simplified calculation) - NULL SAFE
    -- Strength = existing_strength + learning_rate * (pre * post)
    LEAST(1.0, 
      COALESCE(existing_strength, 0.1) + 
      COALESCE({{ var('hebbian_learning_rate') }}, 0.01) * COALESCE(avg_activation_strength, 0.1) * {{ safe_divide('COALESCE(co_occurrence_count, 1)', '10.0', '0.0') }}
    ) as hebbian_association_strength
    
  FROM co_occurrence_analysis coa
  LEFT JOIN (
    SELECT source_concept, target_concept, association_strength as existing_strength
    FROM {{ this }}
    WHERE {{ is_incremental() }}
  ) existing ON (
    existing.source_concept = coa.source_concept AND
    existing.target_concept = coa.target_concept
  )
),

final_associations AS (
  SELECT 
    source_concept,
    target_concept,
    co_occurrence_count,
    shared_memories,
    recent_co_occurrences,
    weekly_co_occurrences,
    avg_activation_strength,
    max_activation_strength,
    semantic_similarity,
    
    -- Final association strength with homeostasis - NULL SAFE
    -- Apply homeostatic scaling to prevent runaway potentiation
    CASE
      WHEN GREATEST(COALESCE(raw_association_strength, 0.1), COALESCE(hebbian_association_strength, 0.1)) > COALESCE({{ var('homeostasis_target') }}, 0.5) THEN
        GREATEST(COALESCE(raw_association_strength, 0.1), COALESCE(hebbian_association_strength, 0.1)) * 
        {{ safe_divide('COALESCE(' ~ var('homeostasis_target') ~ ', 0.5)', 'GREATEST(COALESCE(raw_association_strength, 0.1), COALESCE(hebbian_association_strength, 0.1))', '1.0') }}
      ELSE GREATEST(COALESCE(raw_association_strength, 0.1), COALESCE(hebbian_association_strength, 0.1))
    END as association_strength,
    
    -- Association quality metrics - NULL SAFE
    CASE 
      WHEN COALESCE(semantic_similarity, 0.0) > COALESCE({{ var('semantic_association_threshold') }}, 0.7) 
           AND COALESCE(co_occurrence_count, 0) >= 5 
      THEN 'strong_semantic'
      WHEN COALESCE(recent_co_occurrences, 0) >= 3 
      THEN 'strong_temporal'  
      WHEN COALESCE(co_occurrence_count, 0) >= 10
      THEN 'strong_frequency'
      WHEN COALESCE(semantic_similarity, 0.0) > 0.5 OR COALESCE(co_occurrence_count, 0) >= 3
      THEN 'moderate'
      ELSE 'weak'
    END as association_quality,
    
    -- Bidirectional strength (associations can be asymmetric) - NULL SAFE
    COALESCE(raw_association_strength, 0.1) * 
    (1.0 + COALESCE(semantic_similarity, 0.0) * 0.2) as forward_strength,
    
    COALESCE(raw_association_strength, 0.1) * 
    (1.0 + COALESCE(semantic_similarity, 0.0) * 0.1) as backward_strength,
    
    CURRENT_TIMESTAMP as last_updated_at
  FROM association_strength_calculation
)

SELECT 
  source_concept,
  target_concept,
  association_strength,
  co_occurrence_count,
  shared_memories,
  recent_co_occurrences,
  weekly_co_occurrences,
  avg_activation_strength,
  max_activation_strength,
  semantic_similarity,
  association_quality,
  forward_strength,
  backward_strength,
  last_updated_at
FROM final_associations
WHERE 
  COALESCE(association_strength, 0.0) > 0.05  -- Filter weak associations
  AND COALESCE(co_occurrence_count, 0) >= 2  -- Minimum evidence threshold
ORDER BY COALESCE(association_strength, 0.0) DESC
