-- Working Memory Active Context (Miller's 7±2)
-- Implements biological working memory constraints with 5-minute attention window
-- Created for biological memory system compliance

{{ config(
    materialized='view',
    indexes=[
        {'columns': ['memory_id'], 'unique': false},
        {'columns': ['final_priority'], 'unique': false},
        {'columns': ['wm_slot'], 'unique': false}
    ]
) }}

WITH recent_memories AS (
    SELECT 
        id as memory_id,
        content,
        timestamp,
        importance_score,
        activation_strength,
        access_count,
        metadata,
        -- Age calculation for recency scoring
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - timestamp)) as age_seconds,
        -- Recency boost (newer memories get higher scores)
        CASE 
            WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - timestamp)) < 300 THEN 0.3
            WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - timestamp)) < 600 THEN 0.2
            ELSE 0.1
        END as recency_boost
    FROM {{ ref('raw_memories') }}
    WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
    AND content IS NOT NULL
    AND TRIM(content) != ''
),

enriched_memories AS (
    SELECT 
        *,
        -- Entity extraction (basic pattern matching)
        CASE WHEN content LIKE '%meeting%' THEN '["meeting"]'::JSON
             WHEN content LIKE '%project%' THEN '["project"]'::JSON
             ELSE '[]'::JSON END as entities,
        -- Topic extraction 
        CASE WHEN content LIKE '%work%' THEN '["work"]'::JSON
             WHEN content LIKE '%technical%' THEN '["technical"]'::JSON
             ELSE '[]'::JSON END as topics,
        -- Task type classification
        CASE WHEN content LIKE '%meeting%' THEN 'Communication and Collaboration'
             WHEN content LIKE '%project%' THEN 'Project Management and Execution'
             WHEN content LIKE '%analysis%' THEN 'Financial Planning and Management'
             ELSE 'Product Launch Strategy' END as task_type,
        -- Sentiment analysis
        CASE WHEN content LIKE '%good%' OR content LIKE '%excellent%' THEN 0.8
             WHEN content LIKE '%bad%' OR content LIKE '%problem%' THEN 0.3
             ELSE 0.5 END as sentiment,
        -- Phantom objects placeholder
        '[]'::JSON as phantom_objects,
        -- Hebbian strength calculation using biological learning rate
        (COALESCE(activation_strength, 0.0) * 0.8 + COALESCE(importance_score, 0.0) * 0.2) * {{ var('hebbian_learning_rate') }} as hebbian_strength,
        -- Working memory strength NULL SAFE
        LEAST(1.0, COALESCE(importance_score, 0.0) + COALESCE(recency_boost, 0.0)) as working_memory_strength,
        -- Recency and frequency scoring NULL SAFE
        COALESCE(recency_boost, 0.0) as recency_score,
        COALESCE(access_count, 0) / 10.0 as frequency_score
    FROM recent_memories
),

prioritized_memories AS (
    SELECT *,
        -- Final priority calculation using biological factors NULL SAFE
        (COALESCE(importance_score, 0.0) * 0.4 + COALESCE(working_memory_strength, 0.0) * 0.3 + COALESCE(hebbian_strength, 0.0) * 0.2 + COALESCE(sentiment, 0.5) * 0.1) as final_priority
    FROM enriched_memories
),

top_memories AS (
    SELECT *,
        -- Miller's 7±2 constraint - assign working memory slots
        ROW_NUMBER() OVER (ORDER BY final_priority DESC) as wm_slot,
        -- Memory ranking for capacity enforcement
        ROW_NUMBER() OVER (ORDER BY final_priority DESC) as memory_rank
    FROM prioritized_memories
    WHERE ROW_NUMBER() OVER (ORDER BY final_priority DESC) <= {{ var('working_memory_capacity') }}
    ORDER BY final_priority DESC
)

SELECT * FROM top_memories