-- Test staging model query pattern directly
-- Simulates the stg_codex_memories model without dbt dependencies

-- Load required extensions
LOAD postgres_scanner;
LOAD json;

-- Create PostgreSQL connection secret
CREATE OR REPLACE SECRET codex_db_connection (
    TYPE POSTGRES,
    HOST '192.168.1.104',
    PORT 5432,
    DATABASE 'codex_db',
    USER 'codex_user',
    PASSWORD 'MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a'
);

-- Attach PostgreSQL database
ATTACH '' AS codex_db (TYPE POSTGRES, SECRET codex_db_connection);

-- Test the staging model transformation
WITH source_memories AS (
    SELECT 
        id,
        content,
        created_at,
        updated_at,
        metadata
    FROM codex_db.public.memories
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
    'Data Ingestion Test Results:' as status,
    COUNT(*) as total_records_processed,
    COUNT(DISTINCT memory_type) as memory_types_found,
    AVG(activation_strength) as avg_activation_strength,
    MAX(created_at) as most_recent_memory,
    MIN(created_at) as oldest_memory
FROM parsed_memories
WHERE created_at > CURRENT_DATE - INTERVAL '1 year'

UNION ALL

SELECT
    'Sample processed records:' as status,
    NULL as total_records_processed,
    NULL as memory_types_found,
    NULL as avg_activation_strength,
    NULL as most_recent_memory,
    NULL as oldest_memory

;