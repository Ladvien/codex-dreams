{#
  Short-Term Memory Hierarchical Episodes Model - BMP-HIGH-005
  
  Implements biologically accurate hierarchical episodic memory with proper STM organization.
  Enforces Miller's Law (7±2 capacity), episode clustering, and temporal binding.
  Models the critical WM→STM→CONSOLIDATION→LTM memory hierarchy bridge.
  
  Key Biological Features:
  - Miller's Law enforcement: 7±2 episode capacity with competition-based selection
  - Episode clustering: Coherent sequences grouped by goal and temporal proximity
  - Spatial-temporal binding: Proper episodic memory formation with context
  - Interference resolution: Competition mechanisms for memory selection  
  - Consolidation patterns: Biologically accurate transitions to long-term storage
  - Hierarchical organization: Goal → Episode Clusters → Episodes → Actions
  
  Neuroscientific Basis:
  - Based on hippocampal episodic memory formation (Tulving, 1972)
  - Implements working memory capacity constraints (Miller, 1956; Cowan, 2001)
  - Models spatial-temporal binding in episodic memory (O'Keefe & Nadel, 1978)
  - Incorporates memory interference and competition (Anderson, 1983)
#}

{{ config(
    materialized='incremental',
    unique_key='id',
    incremental_strategy='merge',
    on_schema_change='sync_all_columns',
    tags=['short_term_memory', 'hierarchical', 'episodic']
) }}

WITH working_memories AS (
    -- Reference the working memory model with enhanced selection criteria
    SELECT *,
        -- Calculate WM→STM transition readiness based on biological criteria
        CASE 
            WHEN age_seconds > {{ var('short_term_memory_duration') }}  -- Aged out of WM
                 AND activation_strength > {{ var('plasticity_threshold') }}  -- Strong enough for STM
                 AND access_count >= 2  -- Sufficient rehearsal
                 THEN TRUE
            WHEN activation_strength > {{ var('high_quality_threshold') }}  -- High salience override
                 AND recency_score > 0.7
                 THEN TRUE
            ELSE FALSE
        END as ready_for_stm_transition
    FROM {{ ref('wm_active_context') }}
    {% if is_incremental() %}
    WHERE last_accessed_at > (SELECT COALESCE(MAX(processed_at), '1900-01-01'::timestamp) FROM {{ this }})
    {% endif %}
),

-- STEP 1: Miller's Law Capacity Management
-- Enforce 7±2 capacity constraint with competition-based selection
millers_law_selection AS (
    SELECT 
        wm.*,
        -- Calculate competitive strength for STM entry
        (activation_strength * 0.4 +
         recency_score * 0.3 +
         frequency_score * 0.2 +
         CASE WHEN ready_for_stm_transition THEN 0.1 ELSE 0.0 END
        ) as stm_competition_score,
        
        -- Rank memories for STM admission based on biological criteria
        ROW_NUMBER() OVER (
            ORDER BY 
                CASE WHEN ready_for_stm_transition THEN 1 ELSE 2 END,
                activation_strength DESC,
                recency_score DESC,
                frequency_score DESC
        ) as stm_admission_rank
    FROM working_memories wm
    WHERE ready_for_stm_transition = TRUE
),

-- Apply Miller's Law capacity constraint (7±2 items)
capacity_constrained_selection AS (
    SELECT *,
        CASE 
            WHEN stm_admission_rank <= {{ var('working_memory_capacity') }} - 2 THEN 'core_capacity'  -- 5 items (7-2)
            WHEN stm_admission_rank <= {{ var('working_memory_capacity') }} THEN 'standard_capacity' -- 7 items  
            WHEN stm_admission_rank <= {{ var('working_memory_capacity') }} + 2 THEN 'extended_capacity' -- 9 items (7+2)
            ELSE 'exceeds_capacity'
        END as capacity_status
    FROM millers_law_selection
    WHERE stm_admission_rank <= {{ var('working_memory_capacity') }} + 2  -- Maximum 9 items (7+2)
),

-- STEP 2: Episode Clustering and Temporal Organization
-- Group memories into coherent episodic sequences based on goals and temporal proximity
episode_clustering AS (
    SELECT 
        ccs.*,
        -- Identify goal-based episode clusters using temporal windows
        LAG(created_at) OVER (PARTITION BY COALESCE(concepts[1], 'unknown') ORDER BY created_at) as prev_episode_time,
        LEAD(created_at) OVER (PARTITION BY COALESCE(concepts[1], 'unknown') ORDER BY created_at) as next_episode_time,
        
        -- Calculate temporal gaps between related memories
        COALESCE(
            EXTRACT(EPOCH FROM (created_at - LAG(created_at) OVER (PARTITION BY COALESCE(concepts[1], 'unknown') ORDER BY created_at))),
            0
        ) as temporal_gap_seconds,
        
        -- Create episode cluster IDs based on temporal proximity and semantic similarity
        SUM(CASE 
            WHEN COALESCE(
                EXTRACT(EPOCH FROM (created_at - LAG(created_at) OVER (PARTITION BY COALESCE(concepts[1], 'unknown') ORDER BY created_at))),
                0
            ) > 1800  -- 30-minute gap creates new episode cluster
            THEN 1 
            ELSE 0 
        END) OVER (PARTITION BY COALESCE(concepts[1], 'unknown') ORDER BY created_at ROWS UNBOUNDED PRECEDING) as episode_cluster_id,
        
        -- Calculate intra-episode position for temporal binding
        ROW_NUMBER() OVER (PARTITION BY COALESCE(concepts[1], 'unknown') ORDER BY created_at) as episode_sequence_position
        
    FROM capacity_constrained_selection ccs
),

-- STEP 3: Spatial-Temporal Binding for Episodic Memory Formation
spatial_temporal_binding AS (
    SELECT 
        ec.*,
        -- Generate unique episode cluster identifier
        CONCAT(COALESCE(concepts[1], 'unknown'), '_', episode_cluster_id) as episode_cluster_name,
        
        -- Calculate episode cluster coherence based on temporal and semantic factors
        CASE 
            WHEN COUNT(*) OVER (PARTITION BY COALESCE(concepts[1], 'unknown'), episode_cluster_id) >= 3 
                 AND AVG(temporal_gap_seconds) OVER (PARTITION BY COALESCE(concepts[1], 'unknown'), episode_cluster_id) < 3600
            THEN 'high_coherence'
            WHEN COUNT(*) OVER (PARTITION BY COALESCE(concepts[1], 'unknown'), episode_cluster_id) >= 2
                 AND AVG(temporal_gap_seconds) OVER (PARTITION BY COALESCE(concepts[1], 'unknown'), episode_cluster_id) < 7200  
            THEN 'medium_coherence'
            ELSE 'low_coherence'
        END as episode_coherence,
        
        -- Enhanced spatial context binding for episodic memory
        CASE 
            WHEN LOWER(content) LIKE '%office%' OR LOWER(content) LIKE '%meeting room%'
                THEN JSON_OBJECT(
                    'location_type', 'workplace',
                    'spatial_context', 'professional_environment',
                    'egocentric_reference', 'workspace_relative', 
                    'allocentric_landmarks', JSON_ARRAY('building_entrance', 'elevator', 'department_area'),
                    'episode_objects', JSON_ARRAY('desk', 'computer', 'meeting_table', 'presentation_screen'),
                    'spatial_relationships', JSON_OBJECT('self_to_objects', 'engaged_with', 'movement_pattern', 'stationary_focused')
                )
            WHEN LOWER(content) LIKE '%home%' OR LOWER(content) LIKE '%remote%'
                THEN JSON_OBJECT(
                    'location_type', 'residential',
                    'spatial_context', 'personal_environment',
                    'egocentric_reference', 'home_relative',
                    'allocentric_landmarks', JSON_ARRAY('front_door', 'living_room', 'home_office'),
                    'episode_objects', JSON_ARRAY('personal_computer', 'home_workspace', 'communication_devices'),
                    'spatial_relationships', JSON_OBJECT('self_to_objects', 'comfortable_access', 'movement_pattern', 'relaxed_mobile')
                )
            ELSE JSON_OBJECT(
                'location_type', 'unspecified',
                'spatial_context', 'general_environment', 
                'egocentric_reference', 'context_relative',
                'allocentric_landmarks', JSON_ARRAY(),
                'episode_objects', JSON_ARRAY(),
                'spatial_relationships', JSON_OBJECT()
            )
        END as spatial_temporal_context
    FROM episode_clustering ec
),

-- Build hierarchical task structure via LLM extraction  
-- Uses Ollama endpoint for semantic understanding and task decomposition
hierarchical AS (
    SELECT 
        stb.*,
        -- LLM-enhanced goal extraction (high-level objectives) - NULL SAFE
        COALESCE(
            TRY_CAST(
                COALESCE(
                    json_extract(
                        CASE 
                            WHEN llm_generate_json(
                                'Extract the high-level goal from this content: ' || COALESCE(LEFT(content, 300), 'no content') ||
                                '. Return JSON with key "goal" containing one of: Product Launch Strategy, ' ||
                                'Communication and Collaboration, Financial Planning and Management, ' ||
                                'Project Management and Execution, Client Relations and Service, ' ||
                                'Operations and Maintenance, or General Task Processing.',
                                'gpt-oss',
                                COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                                300
                            ) IS NOT NULL AND JSON_VALID(
                                llm_generate_json(
                                    'Extract the high-level goal from this content: ' || COALESCE(LEFT(content, 300), 'no content') ||
                                    '. Return JSON with key "goal" containing one of: Product Launch Strategy, ' ||
                                    'Communication and Collaboration, Financial Planning and Management, ' ||
                                    'Project Management and Execution, Client Relations and Service, ' ||
                                    'Operations and Maintenance, or General Task Processing.',
                                    'gpt-oss',
                                    COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                                    300
                                )
                            )
                            THEN llm_generate_json(
                                'Extract the high-level goal from this content: ' || COALESCE(LEFT(content, 300), 'no content') ||
                                '. Return JSON with key "goal" containing one of: Product Launch Strategy, ' ||
                                'Communication and Collaboration, Financial Planning and Management, ' ||
                                'Project Management and Execution, Client Relations and Service, ' ||
                                'Operations and Maintenance, or General Task Processing.',
                                'gpt-oss',
                                COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                                300
                            )
                            ELSE '{"goal": "General Task Processing"}'
                        END,
                        '$.goal'
                    ),
                    'General Task Processing'
                ) AS VARCHAR
            ),
            -- Fallback to rule-based extraction
            CASE 
                WHEN LOWER(content) LIKE '%launch%' OR LOWER(content) LIKE '%strategy%' 
                    THEN 'Product Launch Strategy'
                WHEN LOWER(content) LIKE '%presentation%' OR LOWER(content) LIKE '%meeting%' 
                    THEN 'Communication and Collaboration'
                WHEN LOWER(content) LIKE '%budget%' OR LOWER(content) LIKE '%financial%'
                    THEN 'Financial Planning and Management'
                WHEN LOWER(content) LIKE '%project%' OR LOWER(content) LIKE '%deadline%'
                    THEN 'Project Management and Execution'
                WHEN LOWER(content) LIKE '%client%' OR LOWER(content) LIKE '%customer%' 
                    THEN 'Client Relations and Service'
                WHEN LOWER(content) LIKE '%maintenance%' OR LOWER(content) LIKE '%fix%'
                    THEN 'Operations and Maintenance'
                ELSE 'General Task Processing'
            END
        ) as level_0_goal,
        
        -- LLM-enhanced mid-level task extraction - NULL SAFE
        COALESCE(
            TRY_CAST(
                CASE 
                    WHEN llm_generate_json(
                        'Extract mid-level tasks from this content: ' || COALESCE(LEFT(content, 300), 'no content') ||
                        '. Return JSON array of 3 specific tasks as strings.',
                        'gpt-oss',
                        COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                        300
                    ) IS NOT NULL AND JSON_VALID(
                        llm_generate_json(
                            'Extract mid-level tasks from this content: ' || COALESCE(LEFT(content, 300), 'no content') ||
                            '. Return JSON array of 3 specific tasks as strings.',
                            'gpt-oss',
                            COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                            300
                        )
                    )
                    THEN llm_generate_json(
                        'Extract mid-level tasks from this content: ' || COALESCE(LEFT(content, 300), 'no content') ||
                        '. Return JSON array of 3 specific tasks as strings.',
                        'gpt-oss',
                        COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                        300
                    )
                    ELSE '["Task execution", "Process completion", "Quality assurance"]'
                END AS JSON
            ),
            -- Fallback to rule-based extraction
            CASE 
                WHEN LOWER(content) LIKE '%schedule%' OR LOWER(content) LIKE '%appointment%'
                    THEN '["Schedule coordination", "Calendar management", "Time allocation"]'
                WHEN LOWER(content) LIKE '%review%' OR LOWER(content) LIKE '%analysis%'
                    THEN '["Document review", "Data analysis", "Report generation"]'
                ELSE '["Task execution", "Process completion", "Quality assurance"]'
            END::JSON
        ) as level_1_tasks,
        
        -- LLM-enhanced atomic action extraction - NULL SAFE
        COALESCE(
            TRY_CAST(
                CASE 
                    WHEN llm_generate_json(
                        'Extract atomic actions from this content: ' || COALESCE(LEFT(content, 200), 'no content') ||
                        '. Return JSON array of specific actions like: verify_status, transmit_information, ' ||
                        'generate_artifact, modify_record, evaluate_content, allocate_time.',
                        'gpt-oss',
                        COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                        300
                    ) IS NOT NULL AND JSON_VALID(
                        llm_generate_json(
                            'Extract atomic actions from this content: ' || COALESCE(LEFT(content, 200), 'no content') ||
                            '. Return JSON array of specific actions like: verify_status, transmit_information, ' ||
                            'generate_artifact, modify_record, evaluate_content, allocate_time.',
                            'gpt-oss',
                            COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                            300
                        )
                    )
                    THEN llm_generate_json(
                        'Extract atomic actions from this content: ' || COALESCE(LEFT(content, 200), 'no content') ||
                        '. Return JSON array of specific actions like: verify_status, transmit_information, ' ||
                        'generate_artifact, modify_record, evaluate_content, allocate_time.',
                        'gpt-oss',
                        COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                        300
                    )
                    ELSE '["verify_status", "process_information", "complete_task"]'
                END AS JSON
            ),
            -- Fallback to rule-based extraction - NULL SAFE
            COALESCE(
                ARRAY_REMOVE(
                    ARRAY[
                        CASE WHEN LOWER(COALESCE(content, '')) LIKE '%check%' THEN 'verify_status' ELSE NULL END,
                        CASE WHEN LOWER(COALESCE(content, '')) LIKE '%send%' THEN 'transmit_information' ELSE NULL END,
                        CASE WHEN LOWER(COALESCE(content, '')) LIKE '%create%' THEN 'generate_artifact' ELSE NULL END,
                        CASE WHEN LOWER(COALESCE(content, '')) LIKE '%update%' THEN 'modify_record' ELSE NULL END,
                        CASE WHEN LOWER(COALESCE(content, '')) LIKE '%review%' THEN 'evaluate_content' ELSE NULL END,
                        CASE WHEN LOWER(COALESCE(content, '')) LIKE '%schedule%' THEN 'allocate_time' ELSE NULL END
                    ],
                    NULL
                ),
                ['verify_status', 'process_information', 'complete_task']
            )
        ) as atomic_actions
    FROM spatial_temporal_binding stb
),

-- STEP 4: Memory Interference and Competition Mechanisms  
-- Implement biological competition for STM resources and interference resolution
memory_interference AS (
    SELECT 
        h.*,
        
        -- Calculate proactive interference (older memories interfering with new ones)
        COALESCE(
            (SELECT AVG(activation_strength) 
             FROM hierarchical h2 
             WHERE h2.episode_cluster_name = h.episode_cluster_name 
               AND h2.created_at < h.created_at
               AND h2.level_0_goal = h.level_0_goal
            ), 0.0
        ) as proactive_interference_strength,
        
        -- Calculate retroactive interference (newer memories interfering with older ones)
        COALESCE(
            (SELECT AVG(activation_strength)
             FROM hierarchical h3
             WHERE h3.episode_cluster_name = h.episode_cluster_name
               AND h3.created_at > h.created_at  
               AND h3.level_0_goal = h.level_0_goal
            ), 0.0  
        ) as retroactive_interference_strength,
        
        -- Memory competition score within episode cluster
        COALESCE(activation_strength, 0.1) / NULLIF(
            (SELECT SUM(COALESCE(activation_strength, 0.1)) 
             FROM hierarchical h4
             WHERE h4.episode_cluster_name = h.episode_cluster_name), 0.1
        ) as episode_competition_score,
        
        -- Interference resolution based on recency and strength
        GREATEST(0.1, 
            COALESCE(activation_strength, 0.1) * 
            (1.0 - LEAST(0.8, 
                (COALESCE(proactive_interference_strength, 0.0) * 0.3 + 
                 COALESCE(retroactive_interference_strength, 0.0) * 0.2)
            ))
        ) as interference_adjusted_strength
        
    FROM hierarchical h
),

-- Add biological memory features with enhanced spatial-temporal integration
biological_features AS (
    SELECT 
        mi.*,
        -- Use the enhanced spatial_temporal_context from earlier step
        spatial_temporal_context as enhanced_spatial_extraction,
        
        -- Enhanced biological decay with episode cluster effects
        COALESCE(
            EXP(-{{ safe_divide('GREATEST(0, EXTRACT(EPOCH FROM (NOW() - COALESCE(last_accessed_at, NOW()))))', '3600.0', '1.0') }}) * 
            -- Episode cluster bonus: memories in coherent episodes decay slower
            CASE 
                WHEN episode_coherence = 'high_coherence' THEN 1.2
                WHEN episode_coherence = 'medium_coherence' THEN 1.1
                ELSE 1.0
            END,
            1.0
        ) as recency_factor,
        
        -- Enhanced emotional salience with episodic context - NULL SAFE
        LEAST(1.0, (
            -- Base emotional extraction
            (COALESCE(interference_adjusted_strength, 0.1) * 0.3 + 
            CASE 
                WHEN LOWER(COALESCE(content, '')) LIKE '%important%' OR LOWER(COALESCE(content, '')) LIKE '%critical%' OR LOWER(COALESCE(content, '')) LIKE '%urgent%' THEN 0.3
                WHEN LOWER(COALESCE(content, '')) LIKE '%success%' OR LOWER(COALESCE(content, '')) LIKE '%achievement%' OR LOWER(COALESCE(content, '')) LIKE '%completed%' THEN 0.25 
                WHEN LOWER(COALESCE(content, '')) LIKE '%problem%' OR LOWER(COALESCE(content, '')) LIKE '%issue%' OR LOWER(COALESCE(content, '')) LIKE '%broken%' THEN 0.2
                WHEN LOWER(COALESCE(content, '')) LIKE '%deadline%' OR LOWER(COALESCE(content, '')) LIKE '%due%' OR LOWER(COALESCE(content, '')) LIKE '%pending%' THEN 0.15
                ELSE 0.1 
            END) +
            -- Episode coherence emotional boost
            CASE 
                WHEN episode_coherence = 'high_coherence' THEN 0.15
                WHEN episode_coherence = 'medium_coherence' THEN 0.1
                ELSE 0.0
            END +
            -- Competition success emotional component  
            COALESCE(episode_competition_score, 0.0) * 0.15
        )) as emotional_salience,
        
        -- Enhanced Hebbian strength with episode cluster co-activation - NULL SAFE
        COALESCE(
            -- Count co-activations within episode cluster
            COUNT(*) OVER (
                PARTITION BY episode_cluster_name
                ORDER BY COALESCE(last_accessed_at, NOW()) 
                RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND CURRENT ROW
            ) +
            -- Add cross-cluster co-activations for same goal
            COUNT(*) OVER (
                PARTITION BY COALESCE(level_0_goal, 'Unknown Goal') 
                ORDER BY COALESCE(last_accessed_at, NOW()) 
                RANGE BETWEEN INTERVAL '2 hour' PRECEDING AND CURRENT ROW
            ) * 0.5,  -- Lower weight for cross-cluster
            1
        ) as co_activation_count,
        
        -- Enhanced phantom objects with episode-aware affordances
        COALESCE(
            JSON_ARRAY_CONCAT(
                -- Extract objects from spatial_temporal_context
                JSON_EXTRACT(spatial_temporal_context, '$.episode_objects'),
                -- Add content-based phantom objects
                CASE 
                    WHEN LOWER(content) LIKE '%presentation%' OR LOWER(content) LIKE '%slides%'
                        THEN JSON_ARRAY(JSON_OBJECT(
                            'name', 'presentation_slides', 
                            'affordances', JSON_ARRAY('present', 'review', 'edit', 'share', 'animate', 'discuss'),
                            'episode_relevance', 'primary',
                            'spatial_relation', 'in_front_of_speaker',
                            'episode_cluster', episode_cluster_name
                        ))
                    WHEN LOWER(content) LIKE '%report%' OR LOWER(content) LIKE '%document%'
                        THEN JSON_ARRAY(JSON_OBJECT(
                            'name', 'business_document', 
                            'affordances', JSON_ARRAY('read', 'write', 'review', 'analyze', 'share', 'archive'),
                            'episode_relevance', 'primary',
                            'spatial_relation', 'on_desk',
                            'episode_cluster', episode_cluster_name
                        ))
                    WHEN LOWER(content) LIKE '%meeting%' OR LOWER(content) LIKE '%appointment%'
                        THEN JSON_ARRAY(JSON_OBJECT(
                            'name', 'meeting_space',
                            'affordances', JSON_ARRAY('convene', 'discuss', 'present', 'decide', 'collaborate'),
                            'episode_relevance', 'contextual',
                            'spatial_relation', 'shared_environment',
                            'episode_cluster', episode_cluster_name
                        ))
                    ELSE JSON_ARRAY()
                END
            ),
            JSON_ARRAY()
        ) as phantom_objects
    FROM memory_interference mi
)

SELECT 
    memory_id as id,
    content,
    last_accessed_at as timestamp,
    concepts as metadata,
    
    -- ENHANCED HIERARCHICAL STRUCTURE with Episode Organization
    level_0_goal,
    level_1_tasks,
    atomic_actions,
    
    -- NEW: Episode Clustering and Organization Features  
    episode_cluster_name,
    episode_cluster_id,
    episode_sequence_position,
    episode_coherence,
    temporal_gap_seconds,
    
    -- NEW: Miller's Law Capacity Management
    capacity_status,
    stm_admission_rank,  
    stm_competition_score,
    
    -- NEW: Memory Interference and Competition
    proactive_interference_strength,
    retroactive_interference_strength, 
    episode_competition_score,
    interference_adjusted_strength,
    
    -- ENHANCED: Spatial-Temporal Binding for Episodic Memory
    enhanced_spatial_extraction as spatial_extraction,
    phantom_objects,
    
    -- ENHANCED: STM Strength Calculation with Interference Resolution
    LEAST(1.0, recency_factor * emotional_salience * (1.0 + episode_competition_score * 0.2)) as stm_strength,
    co_activation_count as hebbian_potential,
    
    -- ENHANCED: Consolidation Readiness with Episode Cluster Criteria
    CASE 
        -- High coherence episodes get priority consolidation
        WHEN episode_coherence = 'high_coherence' 
             AND co_activation_count >= 2 
             AND emotional_salience > {{ var('homeostasis_target') }} * 0.8 THEN TRUE
        -- Standard consolidation criteria with interference adjustment     
        WHEN co_activation_count >= 3 
             AND emotional_salience > {{ var('homeostasis_target') }}
             AND interference_adjusted_strength > {{ var('plasticity_threshold') }} THEN TRUE
        -- High activation override with competition success
        WHEN interference_adjusted_strength > {{ var('high_quality_threshold') }} 
             AND recency_factor > {{ var('plasticity_threshold') }} * {{ var('homeostasis_target') }}
             AND episode_competition_score > 0.3 THEN TRUE  
        ELSE FALSE
    END as ready_for_consolidation,
    
    -- Enhanced biological features for consolidation
    interference_adjusted_strength as activation_strength,
    recency_factor,
    emotional_salience, 
    co_activation_count,
    
    -- NEW: Episodic Memory Quality Metrics
    CASE 
        WHEN episode_coherence = 'high_coherence' AND spatial_temporal_context IS NOT NULL THEN 'high_fidelity_episodic'
        WHEN episode_coherence = 'medium_coherence' AND temporal_gap_seconds < 7200 THEN 'medium_fidelity_episodic'  
        WHEN episode_coherence = 'low_coherence' THEN 'fragmented_episodic'
        ELSE 'semantic_dominant'
    END as episodic_memory_quality,
    
    -- Biological timestamps and processing metadata
    CURRENT_TIMESTAMP as processed_at,
    'enhanced_stm_hierarchical_episodes_v2' as model_version

FROM biological_features

{% if is_incremental() %}
-- Only process new or updated memories in incremental runs
WHERE last_accessed_at > (SELECT COALESCE(MAX(processed_at), '1900-01-01'::timestamp) FROM {{ this }})
{% endif %}