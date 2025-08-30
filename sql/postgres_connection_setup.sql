-- Set up PostgreSQL connection via DuckDB postgres extension
-- BMP-002: Foreign Data Wrapper Configuration

-- IMPORTANT: Set environment variables in .env file:
-- POSTGRES_DB_URL=postgresql://username:password@192.168.1.104:5432/codex_db

-- Load the postgres extension
LOAD postgres;

-- Attach PostgreSQL database using environment variable
-- The connection string should come from POSTGRES_DB_URL env variable
SET postgres_connection = getenv('POSTGRES_DB_URL');
ATTACH $postgres_connection AS postgres_db (TYPE postgres);

-- Test the connection by listing schemas
SELECT schema_name FROM postgres_db.information_schema.schemata;

-- Test the connection by getting PostgreSQL version
SET postgres_url = getenv('POSTGRES_DB_URL');
SELECT * FROM postgres_query($postgres_url, 'SELECT version() as postgres_version;');

-- List available tables in public schema
SELECT table_name FROM postgres_db.information_schema.tables WHERE table_schema = 'public';

SELECT 'PostgreSQL connection successful' as status;