-- Working Memory with Semantic Context
-- Enhanced version using embedding-based similarity for better memory selection
-- Implements Miller's 7±2 with semantic clustering

{{ config(
    materialized='view',
    indexes=[
        {'columns': ['memory_id'], 'unique': false},
        {'columns': ['semantic_priority'], 'unique': false},
        {'columns': ['wm_slot'], 'unique': false},
        {'columns': ['semantic_cluster'], 'unique': false}
    ],
    pre_hook="{{ setup_ollama_functions() }}"
) }}

WITH recent_memories AS (
    SELECT 
        rm.id as memory_id,
        rm.content,
        rm.timestamp,
        rm.importance_score,
        rm.activation_strength,
        rm.access_count,
        rm.metadata,
        rm.emotional_valence,
        rm.novelty_score,
        rm.context,
        rm.summary,
        
        -- Get embeddings if available
        me.final_embedding,
        me.content_embedding,
        me.consolidation_priority,
        
        -- Age calculation for recency
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - rm.timestamp)) as age_seconds,
        
        -- Enhanced recency boost
        CASE 
            WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - rm.timestamp)) < 60 THEN 0.5   -- Last minute
            WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - rm.timestamp)) < 300 THEN 0.3  -- Last 5 minutes
            WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - rm.timestamp)) < 600 THEN 0.2  -- Last 10 minutes
            ELSE 0.1
        END as recency_boost
        
    FROM {{ ref('raw_memories') }} rm
    LEFT JOIN {{ ref('memory_embeddings') }} me ON rm.id = me.memory_id
    WHERE rm.timestamp > CURRENT_TIMESTAMP - INTERVAL '{{ var("working_memory_window_minutes", 5) }} minutes'
    AND rm.content IS NOT NULL
    AND TRIM(rm.content) != ''
),

semantic_enrichment AS (
    SELECT 
        *,
        
        -- Semantic clustering using embeddings
        {{ semantic_clustering('final_embedding', n_clusters=var('working_memory_capacity', 7)) }} as semantic_cluster,
        
        -- Calculate semantic coherence with recent context
        CASE 
            WHEN final_embedding IS NOT NULL THEN
                -- Average similarity to other recent memories
                AVG({{ cosine_similarity('final_embedding', 'other.final_embedding') }}) 
                OVER (PARTITION BY 1)
            ELSE 0.5
        END as semantic_coherence,
        
        -- Semantic novelty (inverse of average similarity)
        CASE 
            WHEN final_embedding IS NOT NULL THEN
                1.0 - AVG({{ cosine_similarity('final_embedding', 'other.final_embedding') }}) 
                OVER (PARTITION BY 1)
            ELSE novelty_score
        END as semantic_novelty,
        
        -- Extract entities using semantic similarity to known concepts
        CASE 
            WHEN final_embedding IS NOT NULL THEN
                -- In production, compare to concept embeddings
                '["semantic_entities"]'::JSON
            ELSE
                -- Fallback to pattern matching
                CASE WHEN content LIKE '%meeting%' THEN '["meeting"]'::JSON
                     WHEN content LIKE '%project%' THEN '["project"]'::JSON
                     ELSE '[]'::JSON 
                END
        END as entities,
        
        -- Semantic topic extraction
        CASE 
            WHEN semantic_cluster = 0 THEN 'Technical Development'
            WHEN semantic_cluster = 1 THEN 'Communication & Collaboration'
            WHEN semantic_cluster = 2 THEN 'Project Management'
            WHEN semantic_cluster = 3 THEN 'Strategic Planning'
            WHEN semantic_cluster = 4 THEN 'Problem Solving'
            WHEN semantic_cluster = 5 THEN 'Knowledge Management'
            WHEN semantic_cluster = 6 THEN 'Personal Development'
            ELSE 'General'
        END as semantic_topic,
        
        -- Biological factors
        {{ calculate_hebbian_strength('activation_strength', 'importance_score') }} as hebbian_strength,
        
        -- Working memory strength with semantic weighting
        LEAST(1.0, 
            importance_score * 0.3 + 
            recency_boost * 0.2 + 
            semantic_coherence * 0.2 +
            emotional_valence * 0.15 +
            (1.0 - semantic_novelty) * 0.15
        ) as working_memory_strength
        
    FROM recent_memories
),

attention_gating AS (
    SELECT *,
        -- Gate based on semantic relevance to current focus
        CASE
            WHEN semantic_coherence > {{ var('medium_quality_threshold', 0.5) }} THEN 1.2
            WHEN semantic_novelty > {{ var('novelty_bonus', 0.15) }} THEN 1.1
            ELSE 1.0
        END as attention_gate,
        
        -- Calculate semantic priority
        (
            working_memory_strength * 0.35 +
            hebbian_strength * 0.25 +
            semantic_coherence * 0.20 +
            consolidation_priority * 0.10 +
            emotional_valence * 0.10
        ) as semantic_priority
        
    FROM semantic_enrichment
),

clustered_selection AS (
    SELECT *,
        -- Ensure diversity by selecting top from each semantic cluster
        ROW_NUMBER() OVER (
            PARTITION BY semantic_cluster 
            ORDER BY semantic_priority * attention_gate DESC
        ) as cluster_rank,
        
        -- Overall ranking
        ROW_NUMBER() OVER (
            ORDER BY semantic_priority * attention_gate DESC
        ) as global_rank
        
    FROM attention_gating
),

working_memory_selection AS (
    SELECT *,
        -- Assign working memory slots with cluster diversity
        ROW_NUMBER() OVER (
            ORDER BY 
                CASE 
                    WHEN cluster_rank = 1 THEN 0  -- Prioritize cluster leaders
                    ELSE 1 
                END,
                semantic_priority * attention_gate DESC
        ) as wm_slot,
        
        -- Track selection method
        CASE
            WHEN cluster_rank = 1 THEN 'cluster_leader'
            WHEN global_rank <= {{ var('working_memory_capacity_base', 7) }} THEN 'global_priority'
            ELSE 'overflow'
        END as selection_method
        
    FROM clustered_selection
    WHERE global_rank <= {{ var('working_memory_capacity_base', 7) }} + {{ var('working_memory_capacity_variance', 2) }}
)

SELECT 
    memory_id,
    content,
    summary,
    context,
    timestamp,
    
    -- Semantic information
    semantic_cluster,
    semantic_topic,
    semantic_coherence,
    semantic_novelty,
    semantic_priority,
    
    -- Biological factors
    hebbian_strength,
    working_memory_strength,
    emotional_valence,
    consolidation_priority,
    
    -- Working memory position
    wm_slot,
    selection_method,
    attention_gate,
    
    -- Metadata
    entities,
    final_embedding,
    
    -- Capacity check
    CASE 
        WHEN wm_slot <= {{ var('working_memory_capacity', 7) }} THEN 'active'
        ELSE 'buffer'
    END as memory_status
    
FROM working_memory_selection
WHERE wm_slot <= {{ var('working_memory_capacity', 7) }} + {{ var('working_memory_capacity_variance', 2) }}
ORDER BY wm_slot