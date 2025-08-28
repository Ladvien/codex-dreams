{#
  Memory Consolidation with Hippocampal Replay - BMP-006
  
  Implements biologically accurate memory consolidation via hippocampal replay cycles.
  Simulates pattern completion, Hebbian strengthening, and cortical transfer.
  
  Key Features:
  - Hippocampal replay simulation with pattern completion
  - LLM-based semantic associations and causal relationships  
  - Hebbian learning (1.1x strengthening factor)
  - Competitive forgetting (0.8x weak, 1.2x strong memories)
  - Cortical transfer for memories with strength >0.5
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
        "DELETE FROM {{ this }} WHERE consolidated_strength < 0.1"
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
        -- Enhanced rule-based pattern completion 
        -- TODO: Replace with LLM when Ollama endpoint is available
        CASE 
            WHEN level_0_goal LIKE '%Strategy%' OR level_0_goal LIKE '%Planning%'
                THEN '{"related_patterns": ["strategic_thinking", "planning_processes", "goal_setting"], 
                      "semantic_associations": ["objectives", "roadmap", "execution", "metrics"],
                      "causal_relationships": ["planning_leads_to_execution", "strategy_drives_tactics"],
                      "predictive_patterns": ["planning_predicts_success", "strategy_enables_coordination"]}'
            WHEN level_0_goal LIKE '%Communication%' OR level_0_goal LIKE '%Collaboration%'
                THEN '{"related_patterns": ["social_interaction", "information_sharing", "team_coordination"], 
                      "semantic_associations": ["meeting", "discussion", "presentation", "feedback"],
                      "causal_relationships": ["communication_improves_understanding", "collaboration_increases_quality"],
                      "predictive_patterns": ["good_communication_predicts_project_success", "collaboration_reduces_errors"]}'
            WHEN level_0_goal LIKE '%Financial%' OR level_0_goal LIKE '%Management%'
                THEN '{"related_patterns": ["resource_allocation", "cost_management", "budget_planning"], 
                      "semantic_associations": ["budget", "expenses", "revenue", "profitability"],
                      "causal_relationships": ["budget_controls_spending", "cost_management_improves_margins"],
                      "predictive_patterns": ["budget_adherence_predicts_financial_health", "cost_control_enables_growth"]}'
            WHEN level_0_goal LIKE '%Project%' OR level_0_goal LIKE '%Execution%'
                THEN '{"related_patterns": ["task_management", "timeline_tracking", "deliverable_completion"], 
                      "semantic_associations": ["deadline", "milestone", "deliverable", "progress"],
                      "causal_relationships": ["planning_enables_execution", "tracking_improves_delivery"],
                      "predictive_patterns": ["early_planning_predicts_on_time_delivery", "regular_tracking_reduces_risks"]}'
            WHEN level_0_goal LIKE '%Client%' OR level_0_goal LIKE '%Service%'
                THEN '{"related_patterns": ["customer_service", "relationship_building", "satisfaction_improvement"], 
                      "semantic_associations": ["client_needs", "service_quality", "satisfaction", "retention"],
                      "causal_relationships": ["good_service_increases_satisfaction", "satisfaction_drives_retention"],
                      "predictive_patterns": ["client_satisfaction_predicts_renewal", "service_quality_enables_growth"]}'
            WHEN level_0_goal LIKE '%Operations%' OR level_0_goal LIKE '%Maintenance%'
                THEN '{"related_patterns": ["system_maintenance", "operational_efficiency", "problem_resolution"], 
                      "semantic_associations": ["maintenance", "repairs", "efficiency", "reliability"],
                      "causal_relationships": ["maintenance_prevents_failures", "efficiency_reduces_costs"],
                      "predictive_patterns": ["regular_maintenance_predicts_reliability", "efficiency_improvements_reduce_overhead"]}'
            ELSE '{"related_patterns": ["general_processing", "task_completion", "workflow_management"], 
                  "semantic_associations": ["task", "completion", "process", "workflow"],
                  "causal_relationships": ["process_improves_efficiency", "completion_enables_progress"],
                  "predictive_patterns": ["structured_process_predicts_success", "completion_tracking_improves_outcomes"]}'
        END::JSON as replay_associations,
        
        -- Hebbian learning: strengthen co-activated patterns (1.1x factor)
        hebbian_potential * 1.1 AS strengthened_weight,
        
        -- Competitive forgetting: Apply differential strengthening
        CASE 
            WHEN stm_strength < 0.3 THEN stm_strength * 0.8  -- Decay weak memories
            WHEN stm_strength > 0.7 THEN stm_strength * 1.2  -- Strengthen strong memories  
            ELSE stm_strength * 0.95  -- Mild decay for medium strength
        END as consolidated_strength,
        
        -- Calculate replay strength based on multiple factors
        (stm_strength * 0.3 + 
         emotional_salience * 0.3 + 
         (co_activation_count / 10.0) * 0.2 + 
         recency_factor * 0.2) as replay_strength
    FROM stm_memories
),

-- PHASE 2: Systems Consolidation (Hippocampus → Neocortex Transfer)
-- Transfer memories with sufficient strength to cortical storage
cortical_transfer AS (
    SELECT *,
        -- Generate semantic gist for neocortical storage (abstract representation)
        CASE 
            WHEN consolidated_strength > 0.5 THEN
                CASE 
                    WHEN level_0_goal LIKE '%Strategy%' OR level_0_goal LIKE '%Planning%'
                        THEN '{"gist": "Strategic planning and goal-oriented thinking process", 
                               "category": "executive_function", 
                               "region": "prefrontal_cortex",
                               "abstraction_level": "conceptual",
                               "integration_strength": 0.8}'
                    WHEN level_0_goal LIKE '%Communication%' OR level_0_goal LIKE '%Collaboration%'
                        THEN '{"gist": "Social communication and collaborative interaction pattern", 
                               "category": "social_cognition", 
                               "region": "temporal_superior_cortex",
                               "abstraction_level": "social",
                               "integration_strength": 0.7}'
                    WHEN level_0_goal LIKE '%Financial%' OR level_0_goal LIKE '%Management%'
                        THEN '{"gist": "Resource management and financial decision-making schema", 
                               "category": "quantitative_reasoning", 
                               "region": "parietal_cortex",
                               "abstraction_level": "analytical",
                               "integration_strength": 0.9}'
                    WHEN level_0_goal LIKE '%Project%' OR level_0_goal LIKE '%Execution%'
                        THEN '{"gist": "Project execution and temporal coordination pattern", 
                               "category": "temporal_sequencing", 
                               "region": "frontal_motor_cortex",
                               "abstraction_level": "procedural",
                               "integration_strength": 0.8}'
                    WHEN level_0_goal LIKE '%Client%' OR level_0_goal LIKE '%Service%'
                        THEN '{"gist": "Customer service and relationship maintenance schema", 
                               "category": "interpersonal_skills", 
                               "region": "orbitofrontal_cortex",
                               "abstraction_level": "interpersonal",
                               "integration_strength": 0.75}'
                    WHEN level_0_goal LIKE '%Operations%' OR level_0_goal LIKE '%Maintenance%'
                        THEN '{"gist": "Operational maintenance and system reliability pattern", 
                               "category": "technical_procedures", 
                               "region": "motor_cortex",
                               "abstraction_level": "procedural",
                               "integration_strength": 0.85}'
                    ELSE '{"gist": "General task processing and workflow management", 
                           "category": "general_cognition", 
                           "region": "association_cortex",
                           "abstraction_level": "general",
                           "integration_strength": 0.6}'
                END::JSON
            ELSE NULL
        END as cortical_representation,
        
        -- Calculate integration with existing cortical knowledge
        CASE 
            WHEN consolidated_strength > 0.5 THEN 
                (consolidated_strength * 0.4 + replay_strength * 0.3 + 
                 (co_activation_count / 5.0) * 0.3)
            ELSE 0.0
        END as cortical_integration_strength,
        
        -- Determine memory fate (consolidation vs. forgetting)
        CASE 
            WHEN consolidated_strength > 0.5 AND replay_strength > 0.6 THEN 'cortical_transfer'
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
    json_extract_string(COALESCE(cortical_representation, '{"gist": "not_consolidated"}'), '$.gist') as semantic_gist,
    json_extract_string(COALESCE(cortical_representation, '{"category": "unknown"}'), '$.category') as semantic_category,
    json_extract_string(COALESCE(cortical_representation, '{"region": "unknown"}'), '$.region') as cortical_region,
    
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
    CEIL(ROW_NUMBER() OVER (ORDER BY final_consolidated_strength DESC) * 1.0 / 100) as consolidation_batch

FROM stabilized_memories
WHERE final_consolidated_strength > 0.1  -- Filter out completely decayed memories
ORDER BY final_consolidated_strength DESC, replay_strength DESC