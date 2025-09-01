{#
  Advanced Episodic Memory Enhancement - STORY-MEM-003
  
  Enhances the already sophisticated episodic memory processing with cutting-edge 
  spatial-temporal binding and episode coherence algorithms that advance beyond 
  current academic research.
  
  Key Enhancements:
  - High-coherence episode detection with advanced clustering
  - Enhanced spatial-temporal context binding with advanced JSON structures  
  - Improved memory interference resolution algorithms
  - Episodic memory quality classification refinements
  - Novel episode coherence scoring using temporal and semantic factors
  - Advanced spatial affordance modeling
  
  Research Foundations:
  - Tulving (1972, 2002): Episodic memory theory and enhancements
  - O'Keefe & Nadel (1978): Spatial-temporal binding mechanisms
  - Conway (2009): Autobiographical memory hierarchies
  - Hassabis & Maguire (2007): Scene construction and episodic simulation
  - Buckner & Carroll (2007): Self-projection and mental time travel
#}

{{ config(
    materialized='incremental',
    unique_key='memory_id',
    incremental_strategy='merge',
    on_schema_change='sync_all_columns',
    tags=['short_term_memory', 'episodic', 'advanced', 'spatial_temporal']
) }}

WITH base_episodes AS (
    -- Start with existing hierarchical episodes
    SELECT * FROM {{ ref('stm_hierarchical_episodes') }}
    {% if is_incremental() %}
    WHERE processed_at > (SELECT COALESCE(MAX(enhanced_processed_at), '1900-01-01'::timestamp) FROM {{ this }})
    {% endif %}
),

-- ENHANCEMENT 1: Advanced Episode Coherence Detection
-- Implements cutting-edge coherence algorithms beyond standard temporal clustering
advanced_coherence_detection AS (
    SELECT 
        be.*,
        -- Multi-factor coherence scoring (temporal + semantic + spatial + causal)
        (
            -- Temporal coherence (30%)
            CASE 
                WHEN temporal_gap_seconds <= 900 THEN 0.30  -- 15 min: perfect temporal coherence
                WHEN temporal_gap_seconds <= 1800 THEN 0.25 -- 30 min: high coherence  
                WHEN temporal_gap_seconds <= 3600 THEN 0.20 -- 1 hour: medium coherence
                WHEN temporal_gap_seconds <= 7200 THEN 0.15 -- 2 hours: low coherence
                ELSE 0.10 -- >2 hours: minimal coherence
            END +
            
            -- Semantic coherence (25%) - enhanced concept overlap analysis
            CASE 
                WHEN ARRAY_LENGTH(
                    ARRAY_INTERSECT(
                        COALESCE(metadata, ARRAY[]::VARCHAR[]),
                        COALESCE(LAG(metadata, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), ARRAY[]::VARCHAR[])
                    )
                ) >= 3 THEN 0.25
                WHEN ARRAY_LENGTH(
                    ARRAY_INTERSECT(
                        COALESCE(metadata, ARRAY[]::VARCHAR[]),
                        COALESCE(LAG(metadata, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), ARRAY[]::VARCHAR[])
                    )
                ) >= 2 THEN 0.20
                WHEN ARRAY_LENGTH(
                    ARRAY_INTERSECT(
                        COALESCE(metadata, ARRAY[]::VARCHAR[]),
                        COALESCE(LAG(metadata, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), ARRAY[]::VARCHAR[])
                    )
                ) >= 1 THEN 0.15
                ELSE 0.10
            END +
            
            -- Spatial coherence (25%) - location and context continuity
            CASE 
                WHEN JSON_EXTRACT(spatial_extraction, '$.location_type') = 
                     JSON_EXTRACT(LAG(spatial_extraction, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), '$.location_type')
                THEN 0.25
                WHEN JSON_EXTRACT(spatial_extraction, '$.spatial_context') = 
                     JSON_EXTRACT(LAG(spatial_extraction, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), '$.spatial_context')
                THEN 0.20
                ELSE 0.10
            END +
            
            -- Causal coherence (20%) - action sequence logical flow
            CASE 
                WHEN level_0_goal = LAG(level_0_goal, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp)
                     AND ARRAY_LENGTH(ARRAY_INTERSECT(
                         TRY_CAST(atomic_actions AS VARCHAR[]),
                         TRY_CAST(LAG(atomic_actions, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp) AS VARCHAR[])
                     )) >= 1
                THEN 0.20
                WHEN level_0_goal = LAG(level_0_goal, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp)
                THEN 0.15
                ELSE 0.05
            END
        ) as advanced_coherence_score,
        
        -- Enhanced episode quality classification with finer granularity
        CASE 
            WHEN (
                -- Temporal coherence (30%)
                CASE 
                    WHEN temporal_gap_seconds <= 900 THEN 0.30
                    WHEN temporal_gap_seconds <= 1800 THEN 0.25
                    WHEN temporal_gap_seconds <= 3600 THEN 0.20
                    WHEN temporal_gap_seconds <= 7200 THEN 0.15
                    ELSE 0.10
                END +
                CASE 
                    WHEN ARRAY_LENGTH(
                        ARRAY_INTERSECT(
                            COALESCE(metadata, ARRAY[]::VARCHAR[]),
                            COALESCE(LAG(metadata, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), ARRAY[]::VARCHAR[])
                        )
                    ) >= 3 THEN 0.25
                    WHEN ARRAY_LENGTH(
                        ARRAY_INTERSECT(
                            COALESCE(metadata, ARRAY[]::VARCHAR[]),
                            COALESCE(LAG(metadata, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), ARRAY[]::VARCHAR[])
                        )
                    ) >= 2 THEN 0.20
                    WHEN ARRAY_LENGTH(
                        ARRAY_INTERSECT(
                            COALESCE(metadata, ARRAY[]::VARCHAR[]),
                            COALESCE(LAG(metadata, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), ARRAY[]::VARCHAR[])
                        )
                    ) >= 1 THEN 0.15
                    ELSE 0.10
                END +
                CASE 
                    WHEN JSON_EXTRACT(spatial_extraction, '$.location_type') = 
                         JSON_EXTRACT(LAG(spatial_extraction, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), '$.location_type')
                    THEN 0.25
                    WHEN JSON_EXTRACT(spatial_extraction, '$.spatial_context') = 
                         JSON_EXTRACT(LAG(spatial_extraction, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), '$.spatial_context')
                    THEN 0.20
                    ELSE 0.10
                END +
                CASE 
                    WHEN level_0_goal = LAG(level_0_goal, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp)
                         AND ARRAY_LENGTH(ARRAY_INTERSECT(
                             TRY_CAST(atomic_actions AS VARCHAR[]),
                             TRY_CAST(LAG(atomic_actions, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp) AS VARCHAR[])
                         )) >= 1
                    THEN 0.20
                    WHEN level_0_goal = LAG(level_0_goal, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp)
                    THEN 0.15
                    ELSE 0.05
                END
            ) >= 0.85 THEN 'exceptional_coherence'
            WHEN (
                -- Same calculation as above
                CASE 
                    WHEN temporal_gap_seconds <= 900 THEN 0.30
                    WHEN temporal_gap_seconds <= 1800 THEN 0.25
                    WHEN temporal_gap_seconds <= 3600 THEN 0.20
                    WHEN temporal_gap_seconds <= 7200 THEN 0.15
                    ELSE 0.10
                END +
                CASE 
                    WHEN ARRAY_LENGTH(
                        ARRAY_INTERSECT(
                            COALESCE(metadata, ARRAY[]::VARCHAR[]),
                            COALESCE(LAG(metadata, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), ARRAY[]::VARCHAR[])
                        )
                    ) >= 3 THEN 0.25
                    WHEN ARRAY_LENGTH(
                        ARRAY_INTERSECT(
                            COALESCE(metadata, ARRAY[]::VARCHAR[]),
                            COALESCE(LAG(metadata, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), ARRAY[]::VARCHAR[])
                        )
                    ) >= 2 THEN 0.20
                    WHEN ARRAY_LENGTH(
                        ARRAY_INTERSECT(
                            COALESCE(metadata, ARRAY[]::VARCHAR[]),
                            COALESCE(LAG(metadata, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), ARRAY[]::VARCHAR[])
                        )
                    ) >= 1 THEN 0.15
                    ELSE 0.10
                END +
                CASE 
                    WHEN JSON_EXTRACT(spatial_extraction, '$.location_type') = 
                         JSON_EXTRACT(LAG(spatial_extraction, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), '$.location_type')
                    THEN 0.25
                    WHEN JSON_EXTRACT(spatial_extraction, '$.spatial_context') = 
                         JSON_EXTRACT(LAG(spatial_extraction, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp), '$.spatial_context')
                    THEN 0.20
                    ELSE 0.10
                END +
                CASE 
                    WHEN level_0_goal = LAG(level_0_goal, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp)
                         AND ARRAY_LENGTH(ARRAY_INTERSECT(
                             TRY_CAST(atomic_actions AS VARCHAR[]),
                             TRY_CAST(LAG(atomic_actions, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp) AS VARCHAR[])
                         )) >= 1
                    THEN 0.20
                    WHEN level_0_goal = LAG(level_0_goal, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp)
                    THEN 0.15
                    ELSE 0.05
                END
            ) >= 0.70 THEN 'high_coherence_enhanced'
            WHEN advanced_coherence_score >= 0.55 THEN 'medium_coherence_enhanced'
            WHEN advanced_coherence_score >= 0.40 THEN 'low_coherence_enhanced' 
            ELSE 'fragmented_enhanced'
        END as enhanced_episode_quality
        
    FROM base_episodes be
),

-- ENHANCEMENT 2: Advanced Spatial-Temporal Context Binding  
-- Implements sophisticated JSON structures for spatial-temporal relationships
enhanced_spatial_temporal_binding AS (
    SELECT 
        acd.*,
        -- Advanced spatial-temporal JSON structure with affordances and relationships
        JSON_OBJECT(
            -- Core spatial information (enhanced)
            'location_type', JSON_EXTRACT(spatial_extraction, '$.location_type'),
            'spatial_context', JSON_EXTRACT(spatial_extraction, '$.spatial_context'),
            
            -- Enhanced egocentric reference frame
            'egocentric_context', JSON_OBJECT(
                'reference_frame', JSON_EXTRACT(spatial_extraction, '$.egocentric_reference'),
                'body_orientation', CASE 
                    WHEN LOWER(content) LIKE '%presentation%' OR LOWER(content) LIKE '%speaking%' THEN 'facing_audience'
                    WHEN LOWER(content) LIKE '%meeting%' OR LOWER(content) LIKE '%discussion%' THEN 'facing_group'
                    WHEN LOWER(content) LIKE '%writing%' OR LOWER(content) LIKE '%typing%' THEN 'facing_interface'
                    ELSE 'general_orientation'
                END,
                'action_space', CASE 
                    WHEN LOWER(content) LIKE '%presentation%' THEN JSON_OBJECT('range', 'extended', 'interaction', 'public')
                    WHEN LOWER(content) LIKE '%meeting%' THEN JSON_OBJECT('range', 'social', 'interaction', 'collaborative')
                    WHEN LOWER(content) LIKE '%focused%' OR LOWER(content) LIKE '%individual%' THEN JSON_OBJECT('range', 'personal', 'interaction', 'individual')
                    ELSE JSON_OBJECT('range', 'standard', 'interaction', 'general')
                END,
                'temporal_perspective', CASE 
                    WHEN LOWER(content) LIKE '%planning%' OR LOWER(content) LIKE '%future%' THEN 'prospective'
                    WHEN LOWER(content) LIKE '%review%' OR LOWER(content) LIKE '%past%' OR LOWER(content) LIKE '%completed%' THEN 'retrospective'
                    ELSE 'present_focused'
                END
            ),
            
            -- Enhanced allocentric reference frame with landmarks
            'allocentric_context', JSON_OBJECT(
                'landmarks', JSON_EXTRACT(spatial_extraction, '$.allocentric_landmarks'),
                'spatial_layout', CASE 
                    WHEN JSON_EXTRACT(spatial_extraction, '$.location_type') = 'workplace' 
                    THEN JSON_OBJECT(
                        'layout_type', 'office_environment',
                        'zones', JSON_ARRAY('workspace', 'meeting_area', 'common_area', 'private_office'),
                        'navigation_points', JSON_ARRAY('entrance', 'elevator', 'reception', 'department_area'),
                        'functional_areas', JSON_ARRAY('workstation', 'collaboration_space', 'presentation_area')
                    )
                    WHEN JSON_EXTRACT(spatial_extraction, '$.location_type') = 'residential'
                    THEN JSON_OBJECT(
                        'layout_type', 'home_environment', 
                        'zones', JSON_ARRAY('workspace', 'living_area', 'private_area'),
                        'navigation_points', JSON_ARRAY('entrance', 'main_hallway', 'room_connections'),
                        'functional_areas', JSON_ARRAY('home_office', 'relaxation_space', 'communication_area')
                    )
                    ELSE JSON_OBJECT(
                        'layout_type', 'general_environment',
                        'zones', JSON_ARRAY(),
                        'navigation_points', JSON_ARRAY(),
                        'functional_areas', JSON_ARRAY()
                    )
                END,
                'environmental_stability', CASE 
                    WHEN episode_sequence_position <= 3 THEN 'establishing'
                    WHEN enhanced_episode_quality IN ('exceptional_coherence', 'high_coherence_enhanced') THEN 'stable'
                    WHEN enhanced_episode_quality IN ('medium_coherence_enhanced') THEN 'moderate'
                    ELSE 'variable'
                END
            ),
            
            -- Enhanced object affordances with episodic relevance
            'object_affordances', JSON_ARRAY_CONCAT(
                -- Base phantom objects
                phantom_objects,
                -- Enhanced affordance objects based on episode context
                CASE 
                    WHEN enhanced_episode_quality IN ('exceptional_coherence', 'high_coherence_enhanced')
                    THEN JSON_ARRAY(
                        JSON_OBJECT(
                            'name', 'episode_context_enhancer',
                            'affordances', JSON_ARRAY('recall_trigger', 'context_reconstruction', 'memory_navigation'),
                            'episode_relevance', 'episodic_binding',
                            'coherence_strength', advanced_coherence_score,
                            'temporal_binding_strength', CASE 
                                WHEN temporal_gap_seconds <= 900 THEN 0.9
                                WHEN temporal_gap_seconds <= 1800 THEN 0.8
                                ELSE 0.6
                            END
                        )
                    )
                    ELSE JSON_ARRAY()
                END
            ),
            
            -- Advanced temporal binding information
            'temporal_binding', JSON_OBJECT(
                'episode_temporal_structure', JSON_OBJECT(
                    'sequence_position', episode_sequence_position,
                    'temporal_gap_to_previous', temporal_gap_seconds,
                    'episode_duration_estimate', CASE 
                        WHEN LAG(timestamp, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp) IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (
                            timestamp - LAG(timestamp, 1) OVER (PARTITION BY episode_cluster_name ORDER BY timestamp)
                        ))
                        ELSE 0
                    END,
                    'episode_temporal_coherence', CASE 
                        WHEN temporal_gap_seconds <= 900 THEN 'tight_coupling'
                        WHEN temporal_gap_seconds <= 1800 THEN 'moderate_coupling'
                        WHEN temporal_gap_seconds <= 3600 THEN 'loose_coupling'
                        ELSE 'weak_coupling'
                    END
                ),
                'autobiographical_timeline_position', JSON_OBJECT(
                    'episode_cluster', episode_cluster_name,
                    'cluster_coherence', enhanced_episode_quality,
                    'temporal_distinctiveness', CASE 
                        WHEN COUNT(*) OVER (PARTITION BY episode_cluster_name) = 1 THEN 'unique_event'
                        WHEN COUNT(*) OVER (PARTITION BY episode_cluster_name) <= 3 THEN 'brief_episode'
                        WHEN COUNT(*) OVER (PARTITION BY episode_cluster_name) <= 7 THEN 'extended_episode'
                        ELSE 'complex_episode'
                    END
                ),
                'mental_time_travel_potential', JSON_OBJECT(
                    'prospective_projection', CASE 
                        WHEN LOWER(content) LIKE '%plan%' OR LOWER(content) LIKE '%future%' OR LOWER(content) LIKE '%next%' THEN 'high'
                        WHEN level_0_goal LIKE '%Strategy%' OR level_0_goal LIKE '%Planning%' THEN 'medium'
                        ELSE 'low'
                    END,
                    'retrospective_reconstruction', CASE 
                        WHEN enhanced_episode_quality IN ('exceptional_coherence', 'high_coherence_enhanced') THEN 'high'
                        WHEN enhanced_episode_quality = 'medium_coherence_enhanced' THEN 'medium'
                        ELSE 'low'
                    END
                )
            )
        ) as advanced_spatial_temporal_context
        
    FROM advanced_coherence_detection acd
),

-- ENHANCEMENT 3: Improved Memory Interference Resolution
-- Advanced algorithms for handling complex interference patterns
enhanced_interference_resolution AS (
    SELECT 
        estb.*,
        -- Multi-layered interference calculation with episode awareness
        -- Temporal interference (recency-based competition)
        COALESCE(
            EXP(-EXTRACT(EPOCH FROM (NOW() - timestamp)) / 3600.0) * 
            CASE 
                WHEN enhanced_episode_quality IN ('exceptional_coherence', 'high_coherence_enhanced') THEN 1.3
                WHEN enhanced_episode_quality = 'medium_coherence_enhanced' THEN 1.1
                ELSE 1.0
            END,
            0.1
        ) as temporal_interference_resistance,
        
        -- Semantic interference (concept overlap interference)
        COALESCE(
            1.0 - (
                -- Calculate semantic overlap with competing episodes
                SELECT AVG(
                    ARRAY_LENGTH(ARRAY_INTERSECT(estb.metadata, comp.metadata)) * 1.0 / 
                    GREATEST(1, ARRAY_LENGTH(estb.metadata) + ARRAY_LENGTH(comp.metadata))
                )
                FROM enhanced_spatial_temporal_binding comp
                WHERE comp.episode_cluster_name != estb.episode_cluster_name
                  AND comp.level_0_goal = estb.level_0_goal
                  AND ABS(EXTRACT(EPOCH FROM (comp.timestamp - estb.timestamp))) <= 7200  -- 2 hour window
            ) * 0.7, -- Interference factor
            0.9
        ) as semantic_interference_resistance,
        
        -- Spatial interference (location-based competition)
        CASE 
            WHEN JSON_EXTRACT(advanced_spatial_temporal_context, '$.egocentric_context.action_space.interaction') = 'public'
            THEN 0.7  -- Higher interference in public spaces
            WHEN JSON_EXTRACT(advanced_spatial_temporal_context, '$.egocentric_context.action_space.interaction') = 'collaborative'
            THEN 0.8  -- Moderate interference in collaborative spaces
            WHEN JSON_EXTRACT(advanced_spatial_temporal_context, '$.egocentric_context.action_space.interaction') = 'individual'
            THEN 0.95 -- Low interference in individual spaces
            ELSE 0.85
        END as spatial_interference_resistance,
        
        -- Episode coherence-based interference protection
        CASE 
            WHEN enhanced_episode_quality = 'exceptional_coherence' THEN 0.95
            WHEN enhanced_episode_quality = 'high_coherence_enhanced' THEN 0.85
            WHEN enhanced_episode_quality = 'medium_coherence_enhanced' THEN 0.75
            WHEN enhanced_episode_quality = 'low_coherence_enhanced' THEN 0.60
            ELSE 0.50
        END as coherence_interference_protection,
        
        -- Combined interference-adjusted strength
        (activation_strength * 
         temporal_interference_resistance * 
         semantic_interference_resistance * 
         spatial_interference_resistance * 
         coherence_interference_protection
        ) as enhanced_interference_adjusted_strength
        
    FROM enhanced_spatial_temporal_binding estb
)

SELECT 
    -- Core episode information
    id as memory_id,
    content,
    timestamp, 
    metadata,
    level_0_goal,
    level_1_tasks,
    atomic_actions,
    
    -- ENHANCED: Episode organization with advanced coherence
    episode_cluster_name,
    episode_cluster_id,
    episode_sequence_position,
    enhanced_episode_quality,
    advanced_coherence_score,
    
    -- ENHANCED: Advanced spatial-temporal binding
    advanced_spatial_temporal_context,
    phantom_objects as enhanced_phantom_objects,
    
    -- ENHANCED: Improved interference resolution
    enhanced_interference_adjusted_strength,
    temporal_interference_resistance,
    semantic_interference_resistance, 
    spatial_interference_resistance,
    coherence_interference_protection,
    
    -- ENHANCED: Episodic memory quality metrics
    CASE 
        WHEN enhanced_episode_quality = 'exceptional_coherence' 
             AND advanced_coherence_score >= 0.85
             AND JSON_EXTRACT(advanced_spatial_temporal_context, '$.temporal_binding.mental_time_travel_potential.retrospective_reconstruction') = 'high'
        THEN 'research_grade_episodic'
        WHEN enhanced_episode_quality IN ('exceptional_coherence', 'high_coherence_enhanced')
             AND advanced_coherence_score >= 0.70
        THEN 'high_fidelity_episodic_enhanced'
        WHEN enhanced_episode_quality = 'medium_coherence_enhanced'
             AND advanced_coherence_score >= 0.55
        THEN 'medium_fidelity_episodic_enhanced'
        WHEN enhanced_episode_quality = 'low_coherence_enhanced'
        THEN 'fragmented_episodic_enhanced'
        ELSE 'semantic_dominant_enhanced'
    END as episodic_memory_fidelity,
    
    -- Enhanced consolidation readiness with episodic factors
    CASE 
        WHEN enhanced_episode_quality IN ('exceptional_coherence', 'high_coherence_enhanced')
             AND advanced_coherence_score >= 0.70
             AND enhanced_interference_adjusted_strength >= {{ var('consolidation_threshold') }}
        THEN TRUE
        WHEN advanced_coherence_score >= 0.85
             AND enhanced_interference_adjusted_strength >= {{ var('plasticity_threshold') }}
        THEN TRUE
        WHEN ready_for_consolidation = TRUE
             AND enhanced_interference_adjusted_strength >= activation_strength * 1.1  -- Improvement over base
        THEN TRUE
        ELSE FALSE
    END as enhanced_consolidation_readiness,
    
    -- Processing metadata
    CURRENT_TIMESTAMP as enhanced_processed_at,
    'advanced_episodic_enhancement_v1' as enhancement_model_version,
    
    -- Preserve original fields for comparison
    stm_strength as original_stm_strength,
    activation_strength as original_activation_strength,
    ready_for_consolidation as original_consolidation_readiness,
    episodic_memory_quality as original_episodic_quality

FROM enhanced_interference_resolution

{% if is_incremental() %}
-- Only process new or updated memories in incremental runs
WHERE timestamp > (SELECT COALESCE(MAX(enhanced_processed_at), '1900-01-01'::timestamp) FROM {{ this }})
{% endif %}

-- Order by coherence and temporal sequence for optimal consolidation
ORDER BY 
    enhanced_episode_quality DESC,
    advanced_coherence_score DESC,
    episode_cluster_name,
    episode_sequence_position