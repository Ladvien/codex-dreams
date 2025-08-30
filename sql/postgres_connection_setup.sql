-- Set up PostgreSQL connection via DuckDB postgres extension
-- BMP-002: Foreign Data Wrapper Configuration

-- Attach PostgreSQL database
ATTACH 'postgresql://codex_user:MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a@192.168.1.104:5432/codex_db' AS postgres_db (TYPE postgres);

-- Test the connection by listing schemas
SELECT schema_name FROM postgres_db.information_schema.schemata;

-- Test the connection by getting PostgreSQL version
SELECT * FROM postgres_query('postgresql://codex_user:MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a@192.168.1.104:5432/codex_db', 'SELECT version() as postgres_version;');

-- List available tables in public schema
SELECT table_name FROM postgres_db.information_schema.tables WHERE table_schema = 'public';

SELECT 'PostgreSQL connection successful' as status;