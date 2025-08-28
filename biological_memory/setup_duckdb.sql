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

-- Create PostgreSQL connection using postgres_scanner
-- Note: Replace connection parameters with your PostgreSQL server details
CREATE OR REPLACE SECRET postgres_connection (
    TYPE POSTGRES,
    HOST 'localhost',
    PORT 5432,
    DATABASE 'biological_memory_source',
    USER 'your_postgres_user',
    PASSWORD 'your_postgres_password'
);

-- Alternative: Create connection using environment variables (recommended for production)
-- CREATE OR REPLACE SECRET postgres_connection (
--     TYPE POSTGRES,
--     HOST getenv('POSTGRES_HOST'),
--     PORT getenv('POSTGRES_PORT')::INT,
--     DATABASE getenv('POSTGRES_DATABASE'),
--     USER getenv('POSTGRES_USER'),
--     PASSWORD getenv('POSTGRES_PASSWORD')
-- );

-- Attach PostgreSQL database for cross-database queries
ATTACH 'postgresql://localhost:5432/biological_memory_source' AS source_memories (TYPE POSTGRES);

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

-- Set timeout for postgres_scanner connections (30 seconds)
PRAGMA postgres_scanner_timeout=30000;

-- Configure batch size for postgres_scanner operations
PRAGMA postgres_scanner_batch_size=10000;

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