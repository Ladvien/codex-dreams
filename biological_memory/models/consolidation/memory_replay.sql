{#
  Memory Consolidation with Hippocampal Replay - BMP-006
  
  Implements biologically accurate memory consolidation via hippocampal replay cycles.
  Simulates pattern completion, Hebbian strengthening, and cortical transfer.
  
  Key Features:
  - Hippocampal replay simulation with pattern completion
  - LLM-based semantic associations and causal relationships  
  - Hebbian learning (1.1x strengthening factor)
  - Competitive forgetting (0.8x weak, 1.2x strong memories)
  - Cortical transfer for memories with strength >{{ var('stability_threshold') }}
  - Semantic gist generation for long-term neocortical storage
  - Memory pool optimization with pre/post hooks
#}

{{ config(
    materialized='incremental',
    unique_key='id',
    incremental_strategy='merge',
    on_schema_change='sync_all_columns',
    tags=['consolidation', 'hippocampal_replay', 'memory_consolidation'],
    pre_hook="SET memory_limit = '10GB'",
    post_hook=[
        "VACUUM ANALYZE {{ this }}",
        "DELETE FROM {{ this }} WHERE consolidated_strength < {{ var('weak_connection_threshold') }}"
    ]
) }}

WITH stm_memories AS (
    -- Pull memories ready for consolidation from STM
    SELECT * FROM {{ ref('stm_hierarchical_episodes') }}
    WHERE ready_for_consolidation = TRUE
    {% if is_incremental() %}
    AND processed_at > (SELECT COALESCE(MAX(consolidated_at), '1900-01-01'::timestamp) FROM {{ this }})
    {% endif %}
),

-- PHASE 1: Hippocampal Replay with Pattern Completion
-- Simulate sharp-wave ripple patterns and memory reactivation
replay_cycles AS (
    SELECT *,
        -- LLM-enhanced pattern completion with hippocampal replay simulation - NULL SAFE
        -- Uses Ollama endpoint for semantic association and causal relationship extraction
        COALESCE(
            TRY_CAST(
                CASE 
                    WHEN llm_generate_json(
                        'Extract memory patterns and associations for hippocampal replay. Goal: ' || COALESCE(level_0_goal, 'Unknown Goal') || 
                        '. Content: ' || COALESCE(LEFT(content, 500), 'No content available') ||
                        '. Return JSON with keys: related_patterns (array), semantic_associations (array), ' ||
                        'causal_relationships (array), predictive_patterns (array). Be specific to the goal context.',
                        'gpt-oss',
                        COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                        300
                    ) IS NOT NULL AND JSON_VALID(
                        llm_generate_json(
                            'Extract memory patterns and associations for hippocampal replay. Goal: ' || COALESCE(level_0_goal, 'Unknown Goal') || 
                            '. Content: ' || COALESCE(LEFT(content, 500), 'No content available') ||
                            '. Return JSON with keys: related_patterns (array), semantic_associations (array), ' ||
                            'causal_relationships (array), predictive_patterns (array). Be specific to the goal context.',
                            'gpt-oss',
                            COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                            300
                        )
                    )
                    THEN llm_generate_json(
                        'Extract memory patterns and associations for hippocampal replay. Goal: ' || COALESCE(level_0_goal, 'Unknown Goal') || 
                        '. Content: ' || COALESCE(LEFT(content, 500), 'No content available') ||
                        '. Return JSON with keys: related_patterns (array), semantic_associations (array), ' ||
                        'causal_relationships (array), predictive_patterns (array). Be specific to the goal context.',
                        'gpt-oss',
                        COALESCE('{{ env_var("OLLAMA_URL") }}', 'http://localhost:11434'),
                        300
                    )
                    ELSE '{"related_patterns": ["general_processing"], "semantic_associations": ["task", "completion"], "causal_relationships": ["process_improves_efficiency"], "predictive_patterns": ["structured_process_predicts_success"]}'
                END AS JSON
            ),
            -- Fallback to rule-based if LLM fails - NULL SAFE
            CASE 
                WHEN COALESCE(level_0_goal, '') LIKE '%Strategy%' OR COALESCE(level_0_goal, '') LIKE '%Planning%'
                    THEN '{"related_patterns": ["strategic_thinking", "planning_processes"], 
                          "semantic_associations": ["objectives", "roadmap", "execution"],
                          "causal_relationships": ["planning_leads_to_execution"],
                          "predictive_patterns": ["planning_predicts_success"]}'
                WHEN COALESCE(level_0_goal, '') LIKE '%Communication%' OR COALESCE(level_0_goal, '') LIKE '%Collaboration%'
                    THEN '{"related_patterns": ["social_interaction", "team_coordination"], 
                          "semantic_associations": ["meeting", "discussion", "feedback"],
                          "causal_relationships": ["communication_improves_understanding"],
                          "predictive_patterns": ["good_communication_predicts_project_success"]}'
                ELSE '{"related_patterns": ["general_processing"], 
                      "semantic_associations": ["task", "completion"],
                      "causal_relationships": ["process_improves_efficiency"],
                      "predictive_patterns": ["structured_process_predicts_success"]}'
            END::JSON
        ) as replay_associations,
        
        -- Hebbian learning: strengthen co-activated patterns (1.1x factor) - NULL SAFE
        COALESCE(hebbian_potential, 0.1) * {{ var('strong_memory_boost_factor') }} AS strengthened_weight,
        
        -- Competitive forgetting: Apply differential strengthening - NULL SAFE
        CASE 
            WHEN COALESCE(stm_strength, 0.1) < {{ var('plasticity_threshold') }} * {{ var('homeostasis_target') }} THEN COALESCE(stm_strength, 0.1) * {{ var('weak_memory_decay_factor') }}  -- Decay weak memories
            WHEN COALESCE(stm_strength, 0.1) > {{ var('strong_connection_threshold') }} THEN COALESCE(stm_strength, 0.1) * {{ var('strong_memory_boost_factor') }}  -- Strengthen strong memories  
            ELSE COALESCE(stm_strength, 0.1) * {{ var('gradual_forgetting_rate') }}  -- Mild decay for medium strength
        END as consolidated_strength,
        
        -- Calculate replay strength based on multiple factors - NULL SAFE
        (COALESCE(stm_strength, 0.1) * 0.3 + 
         COALESCE(emotional_salience, 0.1) * 0.3 + 
         {{ safe_divide('COALESCE(co_activation_count, 1)', '10.0', '0.0') }} * 0.2 + 
         COALESCE(recency_factor, 0.1) * 0.2) as replay_strength
    FROM stm_memories
),

-- PHASE 2: Systems Consolidation (Hippocampus → Neocortex Transfer)
-- Transfer memories with sufficient strength to cortical storage
cortical_transfer AS (
    SELECT *,
        -- Generate semantic gist for neocortical storage (abstract representation) - NULL SAFE
        CASE 
            WHEN COALESCE(consolidated_strength, 0.0) > {{ var('stability_threshold') }} THEN
                CASE 
                    WHEN COALESCE(level_0_goal, '') LIKE '%Strategy%' OR COALESCE(level_0_goal, '') LIKE '%Planning%'
                        THEN '{"gist": "Strategic planning and goal-oriented thinking process", 
                               "category": "executive_function", 
                               "region": "prefrontal_cortex",
                               "abstraction_level": "conceptual",
                               "integration_strength": {{ var('high_quality_threshold') }}}}'
                    WHEN COALESCE(level_0_goal, '') LIKE '%Communication%' OR COALESCE(level_0_goal, '') LIKE '%Collaboration%'
                        THEN '{"gist": "Social communication and collaborative interaction pattern", 
                               "category": "social_cognition", 
                               "region": "temporal_superior_cortex",
                               "abstraction_level": "social",
                               "integration_strength": {{ var('strong_connection_threshold') }}}}'
                    WHEN COALESCE(level_0_goal, '') LIKE '%Financial%' OR COALESCE(level_0_goal, '') LIKE '%Management%'
                        THEN '{"gist": "Resource management and financial decision-making schema", 
                               "category": "quantitative_reasoning", 
                               "region": "parietal_cortex",
                               "abstraction_level": "analytical",
                               "integration_strength": {{ var('overload_threshold') }}}}'
                    WHEN COALESCE(level_0_goal, '') LIKE '%Project%' OR COALESCE(level_0_goal, '') LIKE '%Execution%'
                        THEN '{"gist": "Project execution and temporal coordination pattern", 
                               "category": "temporal_sequencing", 
                               "region": "frontal_motor_cortex",
                               "abstraction_level": "procedural",
                               "integration_strength": {{ var('high_quality_threshold') }}}}'
                    WHEN COALESCE(level_0_goal, '') LIKE '%Client%' OR COALESCE(level_0_goal, '') LIKE '%Service%'
                        THEN '{"gist": "Customer service and relationship maintenance schema", 
                               "category": "interpersonal_skills", 
                               "region": "orbitofrontal_cortex",
                               "abstraction_level": "interpersonal",
                               "integration_strength": 0.75}'
                    WHEN COALESCE(level_0_goal, '') LIKE '%Operations%' OR COALESCE(level_0_goal, '') LIKE '%Maintenance%'
                        THEN '{"gist": "Operational maintenance and system reliability pattern", 
                               "category": "technical_procedures", 
                               "region": "motor_cortex",
                               "abstraction_level": "procedural",
                               "integration_strength": 0.85}'
                    ELSE '{"gist": "General task processing and workflow management", 
                           "category": "general_cognition", 
                           "region": "association_cortex",
                           "abstraction_level": "general",
                           "integration_strength": {{ var('consolidation_threshold') }}}'
                END::JSON
            ELSE NULL
        END as cortical_representation,
        
        -- Calculate integration with existing cortical knowledge
        CASE 
            WHEN consolidated_strength > {{ var('stability_threshold') }} THEN 
                (consolidated_strength * 0.4 + replay_strength * 0.3 + 
                 {{ safe_divide('co_activation_count', '5.0', '0.0') }} * 0.3)
            ELSE 0.0
        END as cortical_integration_strength,
        
        -- Determine memory fate (consolidation vs. forgetting)
        CASE 
            WHEN consolidated_strength > {{ var('stability_threshold') }} AND replay_strength > {{ var('consolidation_threshold') }} THEN 'cortical_transfer'
            WHEN consolidated_strength > 0.3 AND replay_strength > 0.4 THEN 'hippocampal_retention'
            WHEN consolidated_strength > 0.1 THEN 'gradual_forgetting'
            ELSE 'rapid_forgetting'
        END as consolidation_fate
    FROM replay_cycles
),

-- PHASE 3: Long-term Potentiation and Memory Stabilization
stabilized_memories AS (
    SELECT *,
        -- Apply long-term potentiation for frequently replayed memories
        CASE 
            WHEN consolidation_fate = 'cortical_transfer' THEN consolidated_strength * 1.3
            WHEN consolidation_fate = 'hippocampal_retention' THEN consolidated_strength * 1.1  
            WHEN consolidation_fate = 'gradual_forgetting' THEN consolidated_strength * 0.9
            ELSE consolidated_strength * 0.7
        END as final_consolidated_strength,
        
        -- Calculate synaptic plasticity changes
        (strengthened_weight - hebbian_potential) as synaptic_change,
        
        -- Determine memory accessibility for retrieval
        CASE 
            WHEN consolidation_fate IN ('cortical_transfer', 'hippocampal_retention') THEN
                (final_consolidated_strength * 0.5 + replay_strength * 0.3 + emotional_salience * 0.2)
            ELSE 0.1
        END as retrieval_accessibility
    FROM cortical_transfer
)

SELECT 
    id,
    content,
    level_0_goal,
    level_1_tasks,
    atomic_actions,
    phantom_objects,
    
    -- Consolidation results
    json_extract(COALESCE(cortical_representation, '{"gist": "not_consolidated"}'), '$.gist') as semantic_gist,
    json_extract(COALESCE(cortical_representation, '{"category": "unknown"}'), '$.category') as semantic_category,
    json_extract(COALESCE(cortical_representation, '{"region": "unknown"}'), '$.region') as cortical_region,
    
    -- Memory strength and dynamics
    final_consolidated_strength as consolidated_strength,
    replay_associations,
    replay_strength,
    cortical_integration_strength,
    retrieval_accessibility,
    
    -- Biological processes
    strengthened_weight as hebbian_strength,
    synaptic_change,
    consolidation_fate,
    
    -- Original STM features  
    stm_strength,
    emotional_salience,
    co_activation_count as original_coactivation,
    
    -- Processing metadata
    CURRENT_TIMESTAMP as consolidated_at,
    'consolidated' as memory_status,
    
    -- Performance optimization: batch processing
    CEIL({{ safe_divide('ROW_NUMBER() OVER (ORDER BY final_consolidated_strength DESC) * 1.0', '100', '1') }}) as consolidation_batch

FROM stabilized_memories
WHERE final_consolidated_strength > {{ var('weak_connection_threshold') }}  -- Filter out completely decayed memories
ORDER BY final_consolidated_strength DESC, replay_strength DESC