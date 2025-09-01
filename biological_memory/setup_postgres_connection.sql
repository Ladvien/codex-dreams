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

-- Create PostgreSQL connection secret using environment variables
-- SECURITY: This file should be used with a companion script that substitutes
-- environment variables. Never commit hardcoded passwords.
--
-- Usage: substitute_env.py setup_postgres_connection.sql | duckdb
-- 
-- Required environment variables:
-- POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

-- Template placeholders for environment substitution:
CREATE OR REPLACE SECRET codex_db_connection (
    TYPE POSTGRES,
    HOST '${POSTGRES_HOST}',
    PORT 5432,
    DATABASE '${POSTGRES_DB}',
    USER '${POSTGRES_USER}',
    PASSWORD '${POSTGRES_PASSWORD}'
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