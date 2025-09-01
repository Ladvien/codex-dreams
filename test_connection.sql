-- Simple PostgreSQL connection test
INSTALL postgres_scanner;
LOAD postgres_scanner;

-- Create PostgreSQL connection secret with hardcoded values
CREATE OR REPLACE SECRET test_connection (
    TYPE POSTGRES,
    HOST '192.168.1.104',
    PORT 5432,
    DATABASE 'codex_db',
    USER 'codex_user',
    PASSWORD 'M|h!y,3:tL^-MJSRswpH09N_JJnNkj?Q'
);

-- Attach PostgreSQL database
ATTACH '' AS test_db (TYPE POSTGRES, SECRET test_connection);

-- List all schemas
SELECT schema_name FROM test_db.information_schema.schemata 
WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast');

-- List tables in public schema
SELECT table_name FROM test_db.information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- List tables in codex_processed schema if it exists
SELECT table_name FROM test_db.information_schema.tables 
WHERE table_schema = 'codex_processed' AND table_type = 'BASE TABLE';