{{
  config(
    materialized='table',
    tags=['insights', 'mvp'],
    description='MVP Insights Generator - Creates insights from memories using Ollama'
  )
}}

-- MVP Insights Generator
-- Processes memories from PostgreSQL through Ollama to generate insights
-- Writes results back to PostgreSQL insights table

WITH source_memories AS (
    -- Pull recent memories from PostgreSQL
    SELECT 
        id as memory_id,
        content,
        created_at,
        updated_at,
        metadata
    FROM codex_db.public.memories
    WHERE created_at > CURRENT_DATE - INTERVAL '30 days'
    ORDER BY created_at DESC
    LIMIT 10  -- Start with recent 10 memories for MVP
),

-- Generate insights using Ollama via HTTP
insights_generation AS (
    SELECT
        memory_id,
        content,
        created_at,
        
        -- Call Ollama to generate insight
        json_extract_string(
            http_get(
                'http://localhost:11434/api/generate',
                headers => map_from_entries([
                    ('Content-Type', 'application/json')
                ]),
                params => json_object(
                    'model', 'qwen2.5:0.5b',
                    'prompt', 'Analyze this memory and generate a brief insight about patterns or themes: ' || content,
                    'stream', false,
                    'options', json_object('temperature', 0.7, 'max_tokens', 100)
                )
            )::json,
            '$.response'
        ) AS insight_content,
        
        -- Extract tags using Ollama
        string_split(
            regexp_replace(
                json_extract_string(
                    http_get(
                        'http://localhost:11434/api/generate',
                        headers => map_from_entries([
                            ('Content-Type', 'application/json')
                        ]),
                        params => json_object(
                            'model', 'qwen2.5:0.5b',
                            'prompt', 'Extract 3-5 single-word tags from this text (comma-separated): ' || content,
                            'stream', false,
                            'options', json_object('temperature', 0.3, 'max_tokens', 30)
                        )
                    )::json,
                    '$.response'
                ),
                '[^a-z0-9,]', '', 'g'
            ),
            ','
        ) AS tags_array
        
    FROM source_memories
),

-- Format insights for insertion
formatted_insights AS (
    SELECT
        gen_random_uuid() AS id,
        insight_content AS content,
        'pattern' AS insight_type,  -- Default to pattern type for MVP
        0.7 AS confidence_score,     -- Default confidence
        ARRAY[memory_id] AS source_memory_ids,
        json_object(
            'generated_at', CURRENT_TIMESTAMP::TEXT,
            'model', 'qwen2.5:0.5b',
            'source', 'mvp_pipeline'
        ) AS metadata,
        tags_array AS tags,
        'working' AS tier,
        CURRENT_TIMESTAMP AS created_at,
        CURRENT_TIMESTAMP AS updated_at,
        NULL AS last_accessed_at,
        0.0 AS feedback_score,
        1 AS version,
        NULL AS previous_version,
        NULL AS previous_version_id
    FROM insights_generation
    WHERE insight_content IS NOT NULL
      AND length(insight_content) > 10
)

-- Return formatted insights ready for insertion
SELECT * FROM formatted_insights