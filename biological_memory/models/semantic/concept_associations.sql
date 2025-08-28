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
      unnest(concepts) as concept1,
      unnest(concepts) as concept2,
      memory_id,
      activation_strength
    FROM {{ ref('stable_memories') }}
    WHERE array_length(concepts, 1) > 1
    
    {% if is_incremental() %}
      AND last_processed_at > (
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
    AVG(sm.activation_strength) as avg_activation_strength,
    MAX(sm.activation_strength) as max_activation_strength,
    COUNT(DISTINCT sm.memory_id) as shared_memories,
    
    -- Temporal co-occurrence patterns
    COUNT(CASE WHEN sm.created_at > CURRENT_TIMESTAMP - INTERVAL '24 HOURS' 
          THEN 1 END) as recent_co_occurrences,
    COUNT(CASE WHEN sm.created_at > CURRENT_TIMESTAMP - INTERVAL '7 DAYS' 
          THEN 1 END) as weekly_co_occurrences,
          
    -- Semantic similarity estimation
    {{ semantic_similarity('concept_vectors.vector1', 'concept_vectors.vector2') }} as semantic_similarity
    
  FROM concept_pairs cp
  JOIN {{ ref('stable_memories') }} sm ON (
    sm.concepts @> ARRAY[cp.source_concept] AND 
    sm.concepts @> ARRAY[cp.target_concept]
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
      -- Co-occurrence frequency (normalized)
      LN(1 + co_occurrence_count) / LN(1 + 100) * 0.3 +
      
      -- Average activation strength of shared memories
      avg_activation_strength * 0.25 +
      
      -- Recent activity bias
      LEAST(1.0, recent_co_occurrences / 10.0) * 0.2 +
      
      -- Semantic similarity
      GREATEST(0.0, semantic_similarity) * 0.15 +
      
      -- Shared memory diversity
      LEAST(1.0, shared_memories / 20.0) * 0.1
      
    ) as raw_association_strength,
    
    -- Hebbian learning application
    {{ calculate_hebbian_strength(
      'avg_activation_strength',
      'LEAST(1.0, co_occurrence_count / 10.0)',
      'COALESCE(existing_strength, 0.1)',
      var('hebbian_learning_rate')
    ) }} as hebbian_association_strength
    
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
    
    -- Final association strength with homeostasis
    {{ synaptic_homeostasis(
      'GREATEST(raw_association_strength, hebbian_association_strength)',
      var('homeostasis_target'),
      0.05
    ) }} as association_strength,
    
    -- Association quality metrics
    CASE 
      WHEN semantic_similarity > {{ var('semantic_association_threshold') }} 
           AND co_occurrence_count >= 5 
      THEN 'strong_semantic'
      WHEN recent_co_occurrences >= 3 
      THEN 'strong_temporal'  
      WHEN co_occurrence_count >= 10
      THEN 'strong_frequency'
      WHEN semantic_similarity > 0.5 OR co_occurrence_count >= 3
      THEN 'moderate'
      ELSE 'weak'
    END as association_quality,
    
    -- Bidirectional strength (associations can be asymmetric)
    raw_association_strength * 
    (1.0 + semantic_similarity * 0.2) as forward_strength,
    
    raw_association_strength * 
    (1.0 + semantic_similarity * 0.1) as backward_strength,
    
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
  association_strength > 0.05  -- Filter weak associations
  AND co_occurrence_count >= 2  -- Minimum evidence threshold
ORDER BY association_strength DESC
