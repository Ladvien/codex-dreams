-- Test PostgreSQL integration in a single session
-- This verifies postgres_scanner FDW configuration

-- Load required extensions
LOAD postgres_scanner;

-- Create PostgreSQL connection secret using environment variables
CREATE OR REPLACE SECRET codex_db_connection (
    TYPE POSTGRES,
    HOST getenv('POSTGRES_HOST', '192.168.1.104'),
    PORT 5432,
    DATABASE getenv('POSTGRES_DB', 'codex_db'),
    USER getenv('POSTGRES_USER', 'codex_user'),
    PASSWORD getenv('POSTGRES_PASSWORD')
);

-- Attach PostgreSQL database
ATTACH '' AS codex_db (TYPE POSTGRES, SECRET codex_db_connection);

-- Test connection and data access
SELECT 'Testing PostgreSQL connection...' as status;

-- Count records in memories table
SELECT COUNT(*) as total_memories FROM codex_db.public.memories;

-- Get recent memories with metadata
SELECT 
    COUNT(*) as total_with_content,
    MIN(created_at) as oldest_memory,
    MAX(created_at) as newest_memory,
    AVG(LENGTH(content)) as avg_content_length
FROM codex_db.public.memories
WHERE content IS NOT NULL;

-- Test staging model transformation pattern
SELECT 'Testing staging transformation pattern...' as status;

SELECT 
    id as memory_id,
    CASE
        WHEN LENGTH(content) < 50 THEN 'fragment'
        WHEN LENGTH(content) < 200 THEN 'episode'
        WHEN LENGTH(content) < 500 THEN 'narrative'
        ELSE 'document'
    END AS memory_type,
    LEAST(1.0, 
        EXP(-EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) / (7 * 24 * 3600.0))
    ) AS activation_strength
FROM codex_db.public.memories
WHERE content IS NOT NULL
LIMIT 5;

SELECT 'PostgreSQL integration test complete!' as final_status;