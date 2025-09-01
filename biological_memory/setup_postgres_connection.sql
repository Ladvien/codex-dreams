-- Setup PostgreSQL connection in DuckDB with real credentials
-- This creates the connection to 192.168.1.104:codex_db

-- Install and load required extensions
INSTALL postgres_scanner;
INSTALL fts;
INSTALL json;
INSTALL httpfs;

LOAD postgres_scanner;
LOAD fts;
LOAD json;
LOAD httpfs;

-- Create PostgreSQL connection secret
CREATE OR REPLACE SECRET codex_db_connection (
    TYPE POSTGRES,
    HOST '192.168.1.104',
    PORT 5432,
    DATABASE 'codex_db',
    USER 'codex_user',
    PASSWORD 'M|h!y,3:tL^-MJSRswpH09N_JJnNkj?Q'
);

-- Attach PostgreSQL database for cross-database queries
ATTACH '' AS codex_db (TYPE POSTGRES, SECRET codex_db_connection);

-- Test the connection by querying the memories table
SELECT COUNT(*) as postgres_memories_count FROM codex_db.public.memories;

-- Performance optimization settings
PRAGMA memory_limit='4GB';
PRAGMA threads=4;
PRAGMA enable_progress_bar=true;

-- Show available schemas and tables
PRAGMA show_tables_extended;