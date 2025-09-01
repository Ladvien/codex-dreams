-- Set up PostgreSQL connection via DuckDB postgres extension
-- BMP-002: Foreign Data Wrapper Configuration

-- IMPORTANT: Set environment variables in .env file:
-- POSTGRES_DB_URL=postgresql://username:password@192.168.1.104:5432/codex_db

-- Load the postgres_scanner extension
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
ATTACH '' AS postgres_db (TYPE POSTGRES, SECRET codex_db_connection);

-- Test the connection by listing schemas
SELECT schema_name FROM postgres_db.information_schema.schemata;

-- Test the connection by getting PostgreSQL version
SET postgres_url = getenv('POSTGRES_DB_URL');
SELECT * FROM postgres_query($postgres_url, 'SELECT version() as postgres_version;');

-- List available tables in public schema
SELECT table_name FROM postgres_db.information_schema.tables WHERE table_schema = 'public';

SELECT 'PostgreSQL connection successful' as status;