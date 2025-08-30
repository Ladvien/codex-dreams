-- DuckDB Setup Script for Biological Memory Pipeline
-- Sets up postgres_scanner extension for cross-database connectivity
-- Run this script before executing dbt commands

-- Install required extensions
INSTALL postgres_scanner;
INSTALL fts;
INSTALL json;

-- Load extensions for current session
LOAD postgres_scanner;
LOAD fts;
LOAD json;

-- Create PostgreSQL connection for codex_db using postgres_scanner
-- Connection to PostgreSQL server (configured via environment)
-- IMPORTANT: Use environment variables for production
CREATE OR REPLACE SECRET codex_db_connection (
    TYPE POSTGRES,
    HOST getenv('POSTGRES_HOST', '192.168.1.104'),
    PORT 5432,
    DATABASE getenv('POSTGRES_DB', 'codex_db'),
    USER getenv('POSTGRES_USER', 'codex_user'),
    PASSWORD getenv('POSTGRES_PASSWORD')
);

-- Note: Set these environment variables in your .env file:
-- POSTGRES_HOST=192.168.1.104  # Or use 'postgres' if using Docker/hostname
-- POSTGRES_DB=codex_db
-- POSTGRES_USER=codex_user
-- POSTGRES_PASSWORD=your_password_here

-- Attach PostgreSQL database for cross-database queries
-- This allows DuckDB to query the memories table directly from PostgreSQL
ATTACH '' AS codex_db (TYPE POSTGRES, SECRET codex_db_connection);


-- Alternative using the secret (recommended approach)
-- ATTACH '' AS source_memories (TYPE POSTGRES, SECRET postgres_connection);

-- Verify postgres_scanner extension is loaded
SELECT extension_name, loaded, installed 
FROM duckdb_extensions() 
WHERE extension_name = 'postgres_scanner';

-- Test PostgreSQL connectivity (will fail if PostgreSQL is not accessible)
-- PRAGMA show_tables_extended;

-- Create schema for external source references if needed
CREATE SCHEMA IF NOT EXISTS source_integration;

-- Example: Query PostgreSQL table through postgres_scanner
-- This demonstrates cross-database functionality
-- SELECT COUNT(*) as postgres_row_count 
-- FROM source_memories.public.raw_memories 
-- LIMIT 5;

-- Performance optimization settings for postgres_scanner
PRAGMA memory_limit='4GB';
PRAGMA threads=4;

-- Enable progress bar for long-running cross-database queries
PRAGMA enable_progress_bar=true;

-- Note: postgres_scanner_timeout and postgres_scanner_batch_size
-- are no longer supported in recent DuckDB versions
-- Connection timeouts are handled by the underlying PostgreSQL driver

-- Success message
SELECT 'DuckDB postgres_scanner extension configured successfully!' as status;

-- Instructions for next steps:
SELECT 'Next steps:' as instruction_header,
       '1. Update PostgreSQL connection parameters in this file' as step_1,
       '2. Verify PostgreSQL server is accessible' as step_2,
       '3. Run dbt deps to install packages' as step_3,
       '4. Run dbt run to execute models with cross-database queries' as step_4,
       '5. Use sources.yml to reference PostgreSQL tables' as step_5;

-- Example sources.yml configuration:
-- sources:
--   - name: source_memories
--     description: "External PostgreSQL database with raw memory data"
--     tables:
--       - name: raw_memories
--         description: "Raw memory events from external systems"
--         columns:
--           - name: memory_id
--             description: "Unique identifier for memory event"
--           - name: content
--             description: "Memory content data"
--           - name: created_at
--             description: "Timestamp when memory was created"