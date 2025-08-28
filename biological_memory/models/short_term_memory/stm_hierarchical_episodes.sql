{#
  Short-Term Memory Hierarchical Episodes Model - BMP-005
  
  Implements hierarchical episodic memory with goal-task-action decomposition.
  Uses LLM extraction for biological memory features and spatial representations.
  Prepares memories for consolidation via hippocampal replay.
  
  Key Features:
  - Hierarchical task structure (goal → tasks → actions)
  - Spatial memory components (egocentric/allocentric/object positions)  
  - Biological recency factor and emotional salience
  - Hebbian co-activation counting for pattern strengthening
  - Consolidation readiness based on co-activation and salience
#}

{{ config(
    materialized='incremental',
    unique_key='id',
    incremental_strategy='merge',
    on_schema_change='sync_all_columns',
    tags=['short_term_memory', 'hierarchical', 'episodic']
) }}

WITH working_memories AS (
    -- Reference the working memory model (BMP-004 dependency)
    SELECT * FROM {{ ref('active_memories') }}
    {% if is_incremental() %}
    WHERE last_accessed_at > (SELECT MAX(processed_at) FROM {{ this }})
    {% endif %}
),

-- Build hierarchical task structure via LLM extraction
-- Uses Ollama endpoint for semantic understanding and task decomposition
hierarchical AS (
    SELECT *,
        -- LLM-enhanced goal extraction (high-level objectives)
        COALESCE(
            TRY_CAST(
                json_extract_string(
                    llm_generate_json(
                        'Extract the high-level goal from this content: ' || LEFT(content, 300) ||
                        '. Return JSON with key "goal" containing one of: Product Launch Strategy, ' ||
                        'Communication and Collaboration, Financial Planning and Management, ' ||
                        'Project Management and Execution, Client Relations and Service, ' ||
                        'Operations and Maintenance, or General Task Processing.',
                        'gpt-oss',
                        '{{ env_var("OLLAMA_URL") }}',
                        300
                    ),
                    '$.goal'
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
        
        -- LLM-enhanced mid-level task extraction
        COALESCE(
            TRY_CAST(
                llm_generate_json(
                    'Extract mid-level tasks from this content: ' || LEFT(content, 300) ||
                    '. Return JSON array of 3 specific tasks as strings.',
                    'gpt-oss',
                    '{{ env_var("OLLAMA_URL") }}',
                    300
                ) AS JSON
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
        
        -- LLM-enhanced atomic action extraction
        COALESCE(
            TRY_CAST(
                llm_generate_json(
                    'Extract atomic actions from this content: ' || LEFT(content, 200) ||
                    '. Return JSON array of specific actions like: verify_status, transmit_information, ' ||
                    'generate_artifact, modify_record, evaluate_content, allocate_time.',
                    'gpt-oss',
                    '{{ env_var("OLLAMA_URL") }}',
                    300
                ) AS JSON
            ),
            -- Fallback to rule-based extraction
            ARRAY[
                CASE WHEN LOWER(content) LIKE '%check%' THEN 'verify_status' ELSE NULL END,
                CASE WHEN LOWER(content) LIKE '%send%' THEN 'transmit_information' ELSE NULL END,
                CASE WHEN LOWER(content) LIKE '%create%' THEN 'generate_artifact' ELSE NULL END,
                CASE WHEN LOWER(content) LIKE '%update%' THEN 'modify_record' ELSE NULL END,
                CASE WHEN LOWER(content) LIKE '%review%' THEN 'evaluate_content' ELSE NULL END,
                CASE WHEN LOWER(content) LIKE '%schedule%' THEN 'allocate_time' ELSE NULL END
            ]
        ) as atomic_actions
    FROM working_memories
),

-- Add biological memory features
biological_features AS (
    SELECT *,
        -- Enhanced spatial memory extraction (rule-based approach)
        CASE 
            WHEN LOWER(content) LIKE '%office%' OR LOWER(content) LIKE '%meeting room%'
                THEN '{"location": "office environment", "egocentric": "workplace context", "allocentric": "corporate building", "objects": ["desk", "meeting_table", "presentation_screen"]}'
            WHEN LOWER(content) LIKE '%home%' OR LOWER(content) LIKE '%remote%'
                THEN '{"location": "home environment", "egocentric": "personal workspace", "allocentric": "residential area", "objects": ["computer", "home_office", "communication_tools"]}'
            WHEN LOWER(content) LIKE '%client site%' OR LOWER(content) LIKE '%customer location%'
                THEN '{"location": "client environment", "egocentric": "external workspace", "allocentric": "client facility", "objects": ["meeting_materials", "client_systems", "presentation_tools"]}'
            WHEN LOWER(content) LIKE '%online%' OR LOWER(content) LIKE '%virtual%' OR LOWER(content) LIKE '%video%'
                THEN '{"location": "virtual environment", "egocentric": "digital workspace", "allocentric": "cyberspace", "objects": ["video_interface", "screen_share", "digital_tools"]}'
            ELSE '{"location": "unspecified", "egocentric": "current context", "allocentric": "general environment", "objects": []}'
        END::JSON as spatial_extraction,
        
        -- Calculate decay and consolidation potential (biological timing)
        EXP(-EXTRACT(EPOCH FROM (NOW() - last_accessed_at)) / 3600.0) as recency_factor,
        
        -- Enhanced emotional salience calculation
        (activation_strength * 0.4 + 
        CASE 
            WHEN LOWER(content) LIKE '%important%' OR LOWER(content) LIKE '%critical%' OR LOWER(content) LIKE '%urgent%' THEN 0.4
            WHEN LOWER(content) LIKE '%success%' OR LOWER(content) LIKE '%achievement%' OR LOWER(content) LIKE '%completed%' THEN 0.3 
            WHEN LOWER(content) LIKE '%problem%' OR LOWER(content) LIKE '%issue%' OR LOWER(content) LIKE '%broken%' THEN 0.25
            WHEN LOWER(content) LIKE '%deadline%' OR LOWER(content) LIKE '%due%' OR LOWER(content) LIKE '%pending%' THEN 0.2
            ELSE 0.1 
        END) as emotional_salience,
        
        -- Hebbian strength (co-activation patterns within 1-hour window)
        COUNT(*) OVER (
            PARTITION BY level_0_goal 
            ORDER BY last_accessed_at 
            RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND CURRENT ROW
        ) as co_activation_count,
        
        -- Phantom objects with affordances (enhanced embodied cognition)
        CASE 
            WHEN LOWER(content) LIKE '%presentation%' OR LOWER(content) LIKE '%slides%'
                THEN '[{"name": "presentation_slides", "affordances": ["present", "review", "edit", "share", "animate", "discuss"], "spatial_relation": "in_front_of_speaker"}]'
            WHEN LOWER(content) LIKE '%coffee machine%' OR LOWER(content) LIKE '%broken%'
                THEN '[{"name": "coffee_machine", "affordances": ["brew_coffee", "fix", "maintain", "clean", "troubleshoot"], "spatial_relation": "kitchen_area"}]'
            WHEN LOWER(content) LIKE '%report%' OR LOWER(content) LIKE '%document%'
                THEN '[{"name": "business_document", "affordances": ["read", "write", "review", "analyze", "share", "archive"], "spatial_relation": "on_desk"}]'
            WHEN LOWER(content) LIKE '%budget%' OR LOWER(content) LIKE '%financial%'
                THEN '[{"name": "financial_spreadsheet", "affordances": ["calculate", "update", "review", "approve", "forecast"], "spatial_relation": "on_screen"}]'
            WHEN LOWER(content) LIKE '%supplies%' OR LOWER(content) LIKE '%order%'
                THEN '[{"name": "supply_inventory", "affordances": ["order", "stock", "check", "manage", "distribute"], "spatial_relation": "storage_area"}]'
            WHEN LOWER(content) LIKE '%meeting%' OR LOWER(content) LIKE '%appointment%'
                THEN '[{"name": "meeting_space", "affordances": ["convene", "discuss", "present", "decide", "collaborate"], "spatial_relation": "shared_environment"}]'
            ELSE '[]'
        END::JSON as phantom_objects
    FROM hierarchical
)

SELECT 
    memory_id as id,
    content,
    last_accessed_at as timestamp,
    concepts as metadata,
    
    -- Hierarchical structure (goal-task-action decomposition)
    level_0_goal,
    level_1_tasks,
    atomic_actions,
    
    -- Biological features
    phantom_objects,
    spatial_extraction,
    
    -- Memory dynamics (STM strength calculation)
    recency_factor * emotional_salience as stm_strength,
    co_activation_count as hebbian_potential,
    
    -- Consolidation readiness (biological thresholds)
    CASE 
        WHEN co_activation_count >= 3 AND emotional_salience > 0.5 THEN TRUE
        WHEN activation_strength > 0.8 AND recency_factor > 0.3 THEN TRUE  -- High activation override
        ELSE FALSE
    END as ready_for_consolidation,
    
    -- Enhanced biological features for consolidation
    activation_strength,
    recency_factor,
    emotional_salience,
    co_activation_count,
    
    CURRENT_TIMESTAMP as processed_at

FROM biological_features

{% if is_incremental() %}
-- Only process new or updated memories in incremental runs
WHERE last_accessed_at > (SELECT COALESCE(MAX(processed_at), '1900-01-01'::timestamp) FROM {{ this }})
{% endif %}