{{
  config(
    materialized='view',
    tags=['insights', 'mvp'],
    description='MVP Memory Insights - Prepares memories for insight generation'
  )
}}

-- MVP Memory Insights View
-- Prepares memories for processing through Ollama
-- This view will be consumed by a Python script that calls Ollama and writes back to PostgreSQL

WITH recent_memories AS (
    -- Pull recent memories from PostgreSQL
    SELECT 
        id as memory_id,
        content,
        content_hash,
        tier,
        importance_score,
        created_at,
        updated_at,
        metadata
    FROM codex_db.public.memories
    WHERE status = 'active'
      AND created_at > CURRENT_DATE - INTERVAL '30 days'
    ORDER BY created_at DESC
    LIMIT 20  -- Process recent 20 memories for MVP
),

-- Analyze memory patterns
memory_patterns AS (
    SELECT
        memory_id,
        content,
        created_at,
        
        -- Extract simple keywords for initial tags
        array_agg(DISTINCT lower(word)) FILTER (WHERE length(word) > 4) AS potential_tags
    FROM (
        SELECT 
            memory_id,
            content,
            created_at,
            unnest(string_split(
                regexp_replace(lower(content), '[^a-z0-9\s]', ' ', 'g'),
                ' '
            )) AS word
        FROM recent_memories
    ) word_extraction
    GROUP BY memory_id, content, created_at
),

-- Identify connections between memories
memory_connections AS (
    SELECT 
        m1.memory_id AS source_memory_id,
        m2.memory_id AS related_memory_id,
        -- Simple similarity based on common words
        array_length(
            list_intersect(m1.potential_tags, m2.potential_tags)
        ) AS common_tags_count
    FROM memory_patterns m1
    CROSS JOIN memory_patterns m2
    WHERE m1.memory_id != m2.memory_id
      AND array_length(list_intersect(m1.potential_tags, m2.potential_tags)) > 2
)

-- Prepare data for insight generation
SELECT 
    mp.memory_id,
    mp.content,
    mp.created_at,
    mp.potential_tags[1:5] AS suggested_tags,  -- Top 5 tags
    array_agg(DISTINCT mc.related_memory_id) AS related_memories,
    COUNT(DISTINCT mc.related_memory_id) AS connection_count,
    -- Prepare prompt for Ollama
    'Analyze this memory and identify key patterns or insights: ' || mp.content AS insight_prompt,
    'Extract 3-5 descriptive tags for this memory: ' || mp.content AS tag_prompt
FROM memory_patterns mp
LEFT JOIN memory_connections mc ON mp.memory_id = mc.source_memory_id
GROUP BY mp.memory_id, mp.content, mp.created_at, mp.potential_tags
ORDER BY mp.created_at DESC