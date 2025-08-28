{#
  Working Memory Active Context Model - BMP-004
  
  Implements Miller's 7±2 working memory capacity with 5-minute attention window.
  Connects to PostgreSQL source via postgres_scanner and enriches with LLM extraction.
  
  Key Features:
  - 5-minute sliding window for recent memories
  - LLM-based entity and semantic extraction via prompt() function
  - Importance-based ranking with capacity limits (≤7 items)  
  - Phantom objects with affordances for embodied cognition
  - Continuous view optimization for <100ms performance
#}

{{ config(
    materialized='view',
    tags=['working_memory', 'continuous', 'real_time'],
    post_hook='{{ calculate_memory_stats("working_memory") }}'
) }}

WITH raw_input AS (
    -- Pull from PostgreSQL source via postgres_scanner (5-minute window)
    SELECT 
        id,
        content,
        timestamp,
        metadata,
        COALESCE(activation_strength, 0.5) as activation_strength,
        COALESCE(access_count, 1) as access_count,
        COALESCE(importance_score, 0.3) as base_importance
    FROM {{ source('biological_memory', 'raw_memories') }}
    WHERE timestamp > NOW() - INTERVAL '5 minutes'
    AND content IS NOT NULL
    AND LENGTH(TRIM(content)) > 10  -- Filter out trivial entries
),

-- Enhanced rule-based extraction with biological memory features
-- TODO: Replace with LLM extraction when Ollama endpoint is available
semantic_extraction AS (
    SELECT *,
        -- Enhanced entity extraction
        CASE 
            WHEN LOWER(content) LIKE '%client%' OR LOWER(content) LIKE '%customer%' 
                THEN ARRAY['client', 'business_contact']
            WHEN LOWER(content) LIKE '%team%' OR LOWER(content) LIKE '%colleague%'
                THEN ARRAY['team', 'internal']
            WHEN LOWER(content) LIKE '%presentation%' OR LOWER(content) LIKE '%report%'
                THEN ARRAY['document', 'deliverable']
            WHEN LOWER(content) LIKE '%meeting%' OR LOWER(content) LIKE '%standup%'
                THEN ARRAY['event', 'collaboration']
            ELSE ARRAY['general']
        END as entities,
        
        -- Enhanced topic classification using biological categories
        CASE 
            WHEN LOWER(content) LIKE '%meeting%' OR LOWER(content) LIKE '%presentation%' 
                THEN ARRAY['social_interaction', 'communication']
            WHEN LOWER(content) LIKE '%report%' OR LOWER(content) LIKE '%review%' OR LOWER(content) LIKE '%analysis%'
                THEN ARRAY['cognitive_processing', 'analysis']  
            WHEN LOWER(content) LIKE '%fix%' OR LOWER(content) LIKE '%broken%' OR LOWER(content) LIKE '%maintenance%'
                THEN ARRAY['problem_solving', 'maintenance']
            WHEN LOWER(content) LIKE '%schedule%' OR LOWER(content) LIKE '%appointment%'
                THEN ARRAY['temporal_planning', 'organization']
            WHEN LOWER(content) LIKE '%budget%' OR LOWER(content) LIKE '%financial%' OR LOWER(content) LIKE '%pricing%'
                THEN ARRAY['resource_management', 'planning']
            ELSE ARRAY['general_task', 'processing']
        END as topics,
        
        -- Sentiment with emotional salience
        CASE 
            WHEN LOWER(content) LIKE '%important%' OR LOWER(content) LIKE '%urgent%' OR LOWER(content) LIKE '%critical%'
                THEN 'negative'  -- High arousal, requires attention
            WHEN LOWER(content) LIKE '%success%' OR LOWER(content) LIKE '%good%' OR LOWER(content) LIKE '%excellent%'
                THEN 'positive'
            WHEN LOWER(content) LIKE '%broken%' OR LOWER(content) LIKE '%problem%' OR LOWER(content) LIKE '%issue%'
                THEN 'negative'
            ELSE 'neutral'
        END as sentiment,
        
        -- Enhanced importance scoring with biological factors
        GREATEST(
            base_importance,
            CASE 
                WHEN LOWER(content) LIKE '%important%' OR LOWER(content) LIKE '%critical%' THEN 0.9
                WHEN LOWER(content) LIKE '%urgent%' OR LOWER(content) LIKE '%deadline%' THEN 0.85
                WHEN LOWER(content) LIKE '%client%' OR LOWER(content) LIKE '%customer%' THEN 0.8
                WHEN LOWER(content) LIKE '%meeting%' OR LOWER(content) LIKE '%presentation%' THEN 0.75
                WHEN LOWER(content) LIKE '%review%' OR LOWER(content) LIKE '%report%' THEN 0.7
                WHEN LOWER(content) LIKE '%schedule%' OR LOWER(content) LIKE '%appointment%' THEN 0.6
                WHEN LOWER(content) LIKE '%broken%' OR LOWER(content) LIKE '%fix%' THEN 0.5
                ELSE base_importance
            END
        ) as importance_score,
        
        -- Hierarchical task classification (goal-task-action hierarchy)
        CASE 
            WHEN LOWER(content) LIKE '%launch%' OR LOWER(content) LIKE '%strategy%' OR LOWER(content) LIKE '%campaign%'
                THEN 'goal'      -- High-level objectives
            WHEN LOWER(content) LIKE '%need to%' OR LOWER(content) LIKE '%schedule%' OR LOWER(content) LIKE '%review%'
                THEN 'task'      -- Mid-level tasks
            WHEN LOWER(content) LIKE '%fix%' OR LOWER(content) LIKE '%order%' OR LOWER(content) LIKE '%update%'
                THEN 'action'    -- Specific actions
            WHEN LOWER(content) LIKE '%meeting%' OR LOWER(content) LIKE '%presentation%'
                THEN 'goal'      -- Social/communication goals
            ELSE 'observation'   -- General information processing
        END as task_type,
        
        -- Phantom objects with affordances (embodied cognition)
        CASE 
            WHEN LOWER(content) LIKE '%coffee machine%' 
                THEN '[{"name": "coffee_machine", "affordances": ["brew_coffee", "fix", "maintain", "clean"]}]'::JSON
            WHEN LOWER(content) LIKE '%presentation%' OR LOWER(content) LIKE '%slides%'
                THEN '[{"name": "presentation_slides", "affordances": ["present", "review", "edit", "share"]}]'::JSON
            WHEN LOWER(content) LIKE '%report%' OR LOWER(content) LIKE '%document%'
                THEN '[{"name": "document", "affordances": ["read", "write", "review", "analyze", "share"]}]'::JSON
            WHEN LOWER(content) LIKE '%budget%' OR LOWER(content) LIKE '%financial%'
                THEN '[{"name": "budget_spreadsheet", "affordances": ["calculate", "update", "review", "approve"]}]'::JSON
            WHEN LOWER(content) LIKE '%timeline%' OR LOWER(content) LIKE '%project%'
                THEN '[{"name": "project_timeline", "affordances": ["update", "review", "plan", "track"]}]'::JSON
            WHEN LOWER(content) LIKE '%supplies%' OR LOWER(content) LIKE '%order%'
                THEN '[{"name": "supply_inventory", "affordances": ["order", "stock", "check", "manage"]}]'::JSON
            ELSE '[]'::JSON
        END as phantom_objects
        
    FROM raw_input
),

-- Renamed for consistency with architecture
parsed AS (
    SELECT * FROM semantic_extraction
),

-- Calculate working memory strength and ranking
ranked_memories AS (
    SELECT *,
        -- Multi-factor importance scoring for working memory priority
        (
            importance_score * 0.4 +                    -- LLM-assessed importance
            (CASE sentiment 
                WHEN 'positive' THEN 0.3 
                WHEN 'negative' THEN 0.25
                ELSE 0.15 
            END) +                                       -- Emotional salience
            (activation_strength * 0.2) +               -- Neural activation
            (LEAST(access_count, 10) / 10.0 * 0.15)     -- Access frequency (capped)
        ) as working_memory_strength,
        
        -- Recency boost for 5-minute window
        EXP(-EXTRACT(EPOCH FROM (NOW() - timestamp)) / 300.0) as recency_boost,
        
        -- Task urgency modifier
        (CASE task_type
            WHEN 'goal' THEN 1.3
            WHEN 'task' THEN 1.1  
            WHEN 'action' THEN 0.9
            ELSE 1.0
        END) as task_urgency_modifier
        
    FROM parsed
),

-- Apply Miller's 7±2 capacity constraint with importance-based selection
capacity_limited AS (
    SELECT *,
        -- Final working memory priority score
        working_memory_strength * recency_boost * task_urgency_modifier as final_priority,
        
        -- Rank by importance for capacity limiting
        ROW_NUMBER() OVER (
            ORDER BY 
                working_memory_strength * recency_boost * task_urgency_modifier DESC,
                timestamp DESC
        ) as wm_slot
    FROM ranked_memories
)

-- Final working memory context (Miller's 7±2 limit)
SELECT 
    id as memory_id,
    content,
    timestamp,
    metadata,
    
    -- Extracted semantic content
    entities,
    topics,  
    sentiment,
    importance_score,
    task_type,
    phantom_objects,
    
    -- Working memory dynamics  
    working_memory_strength,
    recency_boost,
    task_urgency_modifier,
    final_priority,
    wm_slot,
    
    -- Biological memory features
    activation_strength,
    access_count,
    {{ memory_age_seconds('timestamp') }} as age_seconds,
    
    -- Hebbian strength for co-activation tracking
    {{ calculate_hebbian_strength(
        'final_priority', 
        'working_memory_strength', 
        'COALESCE(activation_strength, 0.1)', 
        var('hebbian_learning_rate')
    ) }} as hebbian_strength,
    
    -- Memory type classification
    'working_memory' as memory_type,
    CURRENT_TIMESTAMP as processed_at
    
FROM capacity_limited
-- Critical: Implement Miller's 7±2 capacity limit 
WHERE wm_slot <= {{ var('working_memory_capacity') }}
ORDER BY final_priority DESC, timestamp DESC