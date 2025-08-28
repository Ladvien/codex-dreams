{{
  config(
    materialized='view',
    tags=['staging', 'codex_db'],
    description='Staging model for memories from codex_db PostgreSQL database'
  )
}}

-- Staging model for memories from codex_db PostgreSQL server (192.168.1.104)
-- This model ingests memories from the external PostgreSQL database
-- and prepares them for the biological memory processing pipeline

WITH source_memories AS (
    SELECT 
        id,
        content,
        created_at,
        updated_at,
        metadata
    FROM {{ source('codex_db', 'memories') }}
),

-- Parse metadata JSON and extract relevant fields
parsed_memories AS (
    SELECT
        id AS memory_id,
        content,
        
        -- Extract concepts from metadata if available
        COALESCE(
            TRY_CAST(json_extract(metadata, '$.concepts') AS VARCHAR[]),
            -- Fallback to simple keyword extraction if no concepts in metadata
            string_split(
                regexp_replace(
                    lower(content),
                    '[^a-z0-9\s]',
                    ' ',
                    'g'
                ),
                ' '
            )
        ) AS concepts,
        
        -- Calculate initial activation strength based on recency
        LEAST(1.0, 
            EXP(-EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) / (7 * 24 * 3600.0))
        ) AS activation_strength,
        
        -- Timestamps
        created_at,
        updated_at,
        COALESCE(updated_at, created_at) AS last_accessed_at,
        
        -- Calculate access count estimate (1 + number of updates)
        1 + CASE 
            WHEN updated_at IS NOT NULL AND updated_at > created_at 
            THEN EXTRACT(DAY FROM (updated_at - created_at)) + 1
            ELSE 1
        END AS access_count,
        
        -- Calculate importance score based on recency and update frequency
        CASE
            WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - created_at)) < 1 THEN 0.9
            WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - created_at)) < 7 THEN 0.7
            WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - created_at)) < 30 THEN 0.5
            ELSE 0.3
        END AS importance_score,
        
        -- Classify memory type based on content characteristics
        CASE
            WHEN LENGTH(content) < 50 THEN 'fragment'
            WHEN LENGTH(content) < 200 THEN 'episode'
            WHEN LENGTH(content) < 500 THEN 'narrative'
            ELSE 'document'
        END AS memory_type,
        
        -- Original metadata for reference
        metadata AS raw_metadata,
        
        -- Add processing metadata
        CURRENT_TIMESTAMP AS processed_at,
        'codex_db' AS source_system
        
    FROM source_memories
    WHERE content IS NOT NULL
      AND LENGTH(content) > 0
)

SELECT
    memory_id,
    content,
    concepts,
    activation_strength,
    created_at,
    last_accessed_at,
    access_count,
    importance_score,
    memory_type,
    raw_metadata,
    processed_at,
    source_system
FROM parsed_memories
-- Filter out extremely old or irrelevant memories
WHERE created_at > CURRENT_DATE - INTERVAL '1 year'
ORDER BY created_at DESC