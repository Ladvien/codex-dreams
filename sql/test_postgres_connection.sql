-- Test PostgreSQL connection from DuckDB
-- Requires postgres_scanner extension and environment variables

-- IMPORTANT: Ensure POSTGRES_DB_URL is set in your .env file
-- Format: postgresql://username:password@192.168.1.104:5432/codex_db

-- Load postgres_scanner extension
LOAD postgres_scanner;

-- Create PostgreSQL connection secret using environment variables
CREATE OR REPLACE SECRET test_postgres_connection (
    TYPE POSTGRES,
    HOST getenv('POSTGRES_HOST', '192.168.1.104'),
    PORT 5432,
    DATABASE getenv('POSTGRES_DB', 'codex_db'),
    USER getenv('POSTGRES_USER', 'codex_user'),
    PASSWORD getenv('POSTGRES_PASSWORD')
);

-- Attach PostgreSQL database
ATTACH '' AS test_db (TYPE POSTGRES, SECRET test_postgres_connection);

-- Test PostgreSQL version
SELECT version() as postgres_version FROM test_db.pg_catalog.pg_stat_database LIMIT 1;

-- List tables in public schema
SELECT schemaname, tablename FROM test_db.pg_catalog.pg_tables WHERE schemaname = 'public';

-- Check if memories table exists and has data
SELECT COUNT(*) as memory_count FROM test_db.public.memories;

-- Connection test complete
SELECT 'PostgreSQL connection test completed successfully' as status;