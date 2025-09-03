-- Semantic Network Model
-- Builds associative connections between memories based on embedding similarity
-- Implements Hebbian learning and synaptic plasticity

{{ config(
    materialized='incremental',
    unique_key='connection_id',
    incremental_strategy='merge',
    on_schema_change='sync_all_columns',
    indexes=[
        {'columns': ['memory_id_1', 'memory_id_2'], 'unique': true},
        {'columns': ['association_strength'], 'unique': false},
        {'columns': ['last_activated'], 'unique': false},
        {'columns': ['association_type'], 'unique': false}
    ],
    post_hook=[
        "DELETE FROM {{ this }} WHERE association_strength < {{ var('forgetting_rate', 0.05) }}",
        "ANALYZE {{ this }}"
    ]
) }}

WITH memory_pairs AS (
    SELECT 
        m1.memory_id as memory_id_1,
        m2.memory_id as memory_id_2,
        m1.final_embedding as embedding_1,
        m2.final_embedding as embedding_2,
        m1.content as content_1,
        m2.content as content_2,
        m1.semantic_cluster as cluster_1,
        m2.semantic_cluster as cluster_2,
        m1.importance_score as importance_1,
        m2.importance_score as importance_2,
        m1.emotional_valence as valence_1,
        m2.emotional_valence as valence_2,
        m1.consolidation_priority as priority_1,
        m2.consolidation_priority as priority_2,
        GREATEST(m1.created_at, m2.created_at) as latest_timestamp
    FROM {{ ref('memory_embeddings') }} m1
    INNER JOIN {{ ref('memory_embeddings') }} m2 
        ON m1.memory_id < m2.memory_id  -- Avoid duplicates and self-connections
    WHERE m1.final_embedding IS NOT NULL 
      AND m2.final_embedding IS NOT NULL
    {% if is_incremental() %}
        -- Only process new or updated memory pairs
        AND (m1.updated_at > (SELECT MAX(last_activated) FROM {{ this }})
          OR m2.updated_at > (SELECT MAX(last_activated) FROM {{ this }}))
    {% endif %}
),

similarity_calculations AS (
    SELECT 
        *,
        
        -- Calculate semantic similarity
        {{ cosine_similarity('embedding_1', 'embedding_2') }} as semantic_similarity,
        
        -- Calculate temporal proximity (memories close in time)
        EXP(-ABS(EXTRACT(EPOCH FROM (
            (SELECT timestamp FROM {{ ref('raw_memories') }} WHERE id = memory_id_1) -
            (SELECT timestamp FROM {{ ref('raw_memories') }} WHERE id = memory_id_2)
        )) / 3600.0)) as temporal_proximity,
        
        -- Check if memories are in same semantic cluster
        CASE 
            WHEN cluster_1 = cluster_2 THEN 1.0
            ELSE 0.0
        END as cluster_coherence,
        
        -- Emotional congruence (similar emotional valence)
        1.0 - ABS(valence_1 - valence_2) as emotional_congruence
        
    FROM memory_pairs
),

hebbian_associations AS (
    SELECT 
        *,
        
        -- Generate unique connection ID
        MD5(LEAST(memory_id_1, memory_id_2) || '|' || GREATEST(memory_id_1, memory_id_2)) as connection_id,
        
        -- Hebbian strength calculation with multiple factors
        {{ hebbian_learning_with_embeddings('embedding_1', 'embedding_2') }} as hebbian_strength,
        
        -- Calculate association strength using biological principles
        GREATEST(
            semantic_similarity * {{ var('synaptic_scaling_factor', 1.5) }},
            temporal_proximity * 0.8,
            cluster_coherence * 0.6,
            emotional_congruence * {{ var('emotional_salience_weight', 1.2) }}
        ) * (
            -- Importance weighting
            (importance_1 + importance_2) / 2.0
        ) as raw_association_strength,
        
        -- Determine association type
        CASE
            WHEN semantic_similarity > {{ var('strong_connection_threshold', 0.8) }} THEN 'semantic_strong'
            WHEN semantic_similarity > {{ var('medium_quality_threshold', 0.5) }} THEN 'semantic_medium'
            WHEN temporal_proximity > 0.7 THEN 'temporal'
            WHEN cluster_coherence = 1.0 THEN 'cluster'
            WHEN emotional_congruence > 0.8 THEN 'emotional'
            ELSE 'weak'
        END as association_type
        
    FROM similarity_calculations
    WHERE semantic_similarity > {{ var('consolidation_threshold', 0.5) }}
       OR temporal_proximity > 0.7
       OR cluster_coherence = 1.0
),

synaptic_plasticity AS (
    SELECT 
        connection_id,
        LEAST(memory_id_1, memory_id_2) as memory_id_1,
        GREATEST(memory_id_1, memory_id_2) as memory_id_2,
        
        -- Apply STDP (Spike-Timing Dependent Plasticity)
        CASE
            WHEN raw_association_strength > {{ var('ltp_threshold', 0.6) }} THEN
                -- Long-term potentiation
                raw_association_strength * (1.0 + {{ var('hebbian_learning_rate', 0.1) }})
            WHEN raw_association_strength < {{ var('ltd_threshold', 0.3) }} THEN
                -- Long-term depression
                raw_association_strength * {{ var('hebbian_decay_factor', 0.95) }}
            ELSE
                -- Maintain current strength
                raw_association_strength
        END as association_strength,
        
        association_type,
        semantic_similarity,
        temporal_proximity,
        cluster_coherence,
        emotional_congruence,
        hebbian_strength,
        
        -- Track co-activation
        1 as co_activation_count,
        
        -- Metadata
        latest_timestamp as last_activated,
        CURRENT_TIMESTAMP as created_at,
        CURRENT_TIMESTAMP as updated_at
        
    FROM hebbian_associations
),

existing_connections AS (
    {% if is_incremental() %}
        SELECT 
            connection_id,
            association_strength as existing_strength,
            co_activation_count as existing_count
        FROM {{ this }}
    {% else %}
        SELECT 
            NULL::VARCHAR as connection_id,
            0.0 as existing_strength,
            0 as existing_count
        WHERE FALSE
    {% endif %}
),

merged_connections AS (
    SELECT 
        sp.*,
        
        -- Merge with existing connections (incremental updates)
        COALESCE(ec.existing_strength, 0.0) as previous_strength,
        COALESCE(ec.existing_count, 0) as previous_count,
        
        -- Update association strength with history
        CASE
            WHEN ec.connection_id IS NOT NULL THEN
                -- Weighted average of new and existing strength
                (sp.association_strength * 0.3 + ec.existing_strength * 0.7) * 
                -- Apply forgetting curve
                {{ apply_forgetting_curve('1.0', 'EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - sp.last_activated))') }}
            ELSE
                sp.association_strength
        END as final_association_strength,
        
        -- Increment co-activation count
        sp.co_activation_count + COALESCE(ec.existing_count, 0) as total_co_activation_count
        
    FROM synaptic_plasticity sp
    LEFT JOIN existing_connections ec ON sp.connection_id = ec.connection_id
)

SELECT 
    connection_id,
    memory_id_1,
    memory_id_2,
    final_association_strength as association_strength,
    association_type,
    
    -- Similarity metrics
    semantic_similarity,
    temporal_proximity,
    cluster_coherence,
    emotional_congruence,
    
    -- Hebbian learning metrics
    hebbian_strength,
    total_co_activation_count as co_activation_count,
    
    -- Categorize connection strength
    CASE
        WHEN final_association_strength > {{ var('strong_connection_threshold', 0.8) }} THEN 'strong'
        WHEN final_association_strength > {{ var('medium_quality_threshold', 0.5) }} THEN 'medium'
        ELSE 'weak'
    END as connection_strength,
    
    -- Metadata
    last_activated,
    created_at,
    updated_at,
    
    -- Synaptic health indicator
    CASE
        WHEN final_association_strength > previous_strength THEN 'potentiating'
        WHEN final_association_strength < previous_strength THEN 'depressing'
        ELSE 'stable'
    END as synaptic_state
    
FROM merged_connections
WHERE final_association_strength >= {{ var('forgetting_rate', 0.05) }}
ORDER BY association_strength DESC