{#
  Long-Term Memory Stable Memories Model
  Materialized as TABLE with proper indexing for fast retrieval
  
  Stores consolidated memories that have proven persistent and important
  Optimized for complex queries and long-term analysis
#}

{{ config(
    materialized='table',
    tags=['long_term_memory', 'stable', 'production'],
    post_hook='{{ create_memory_indexes() }}'
) }}

WITH consolidated_memories AS (
  SELECT 
    memory_id,
    content,
    concepts,
    activation_strength,
    created_at,
    last_accessed_at,
    access_count,
    memory_type,
    recency_score,
    frequency_score,
    hebbian_strength,
    consolidation_priority,
    consolidated_at
  FROM {{ ref('stm_hierarchical_episodes') }}
  WHERE 
    -- Only memories that meet long-term storage criteria
    activation_strength > {{ var('long_term_memory_threshold') }}
    AND consolidation_priority > {{ var('consolidation_threshold') }}
    AND {{ memory_age_seconds('created_at') }} > 3600  -- At least 1 hour old
),

semantic_enrichment AS (
  SELECT 
    cm.*,
    -- Calculate semantic relationships
    COALESCE(sa.association_count, 0) as semantic_associations,
    COALESCE(sa.avg_association_strength, 0.0) as avg_association_strength,
    COALESCE(sa.max_association_strength, 0.0) as max_association_strength,
    
    -- Memory network position
    COALESCE(nc.centrality_score, 0.0) as network_centrality,
    COALESCE(nc.clustering_coefficient, 0.0) as clustering_coefficient,
    
    -- Temporal patterns
    {{ safe_divide(
      'access_count', 
      'GREATEST(1, ' ~ memory_age_seconds('created_at') ~ ' / 3600.0)',
      '0.0'
    ) }} as access_rate_per_hour
  FROM consolidated_memories cm
  LEFT JOIN -- REMOVED: semantic_associations table not available in codex_db sa
    ON cm.memory_id = sa.memory_id
  LEFT JOIN -- REMOVED: network_centrality table not available in codex_db nc
    ON cm.memory_id = nc.memory_id
),

stability_scoring AS (
  SELECT *,
    -- Calculate long-term stability score
    (
      LEAST(1.0, activation_strength) * 0.3 +
      LEAST(1.0, {{ safe_divide('semantic_associations', '10.0', '0.0') }}) * 0.2 +
      LEAST(1.0, avg_association_strength) * 0.2 +
      LEAST(1.0, network_centrality) * 0.15 +
      LEAST(1.0, access_rate_per_hour) * 0.15
    ) as stability_score,
    
    -- Memory importance based on network effects
    (
      hebbian_strength * 0.4 +
      network_centrality * 0.3 +
      avg_association_strength * 0.3
    ) as importance_score,
    
    -- Decay resistance (ability to persist over time)
    EXP(-{{ var('synaptic_decay_rate') }} * 
        {{ safe_divide(memory_age_seconds('created_at'), '86400.0', '1.0') }}  -- Days
    ) * stability_score as decay_resistance
  FROM semantic_enrichment
)

SELECT 
  memory_id,
  content,
  concepts,
  activation_strength,
  created_at,
  last_accessed_at,
  access_count,
  'long_term_memory' as memory_type,
  recency_score,
  frequency_score,
  hebbian_strength,
  consolidation_priority,
  consolidated_at,
  semantic_associations,
  avg_association_strength,
  max_association_strength,
  network_centrality,
  clustering_coefficient,
  access_rate_per_hour,
  stability_score,
  importance_score,
  decay_resistance,
  CURRENT_TIMESTAMP as last_processed_at,
  
  -- Memory quality indicators
  CASE 
    WHEN stability_score > {{ var('high_quality_threshold') }} THEN 'high_quality'
    WHEN stability_score > {{ var('medium_quality_threshold') }} THEN 'medium_quality'
    WHEN stability_score > 0.4 THEN 'low_quality'
    ELSE 'unstable'
  END as memory_quality,
  
  -- Consolidation status
  CASE
    WHEN decay_resistance > {{ var('strong_connection_threshold') }} AND importance_score > {{ var('consolidation_threshold') }} THEN 'fully_consolidated'
    WHEN decay_resistance > 0.5 AND importance_score > 0.4 THEN 'partially_consolidated'
    ELSE 'consolidating'
  END as consolidation_status

FROM stability_scoring
WHERE 
  decay_resistance > 0.1  -- Only memories with some persistence
  AND stability_score > 0.3  -- Minimum stability threshold
ORDER BY 
  importance_score DESC,
  stability_score DESC,
  last_accessed_at DESC
