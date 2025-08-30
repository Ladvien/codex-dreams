-- Test PostgreSQL connection from DuckDB
-- Requires postgres_scanner extension and environment variables

-- IMPORTANT: Ensure POSTGRES_DB_URL is set in your .env file
-- Format: postgresql://username:password@192.168.1.104:5432/codex_db

-- Load postgres extension
LOAD postgres;

-- Test direct query to PostgreSQL using environment variable
SET postgres_url = getenv('POSTGRES_DB_URL');
SELECT * FROM postgres_query($postgres_url, 'SELECT version();');

-- List tables in public schema
SELECT * FROM postgres_query($postgres_url, 'SELECT schemaname, tablename FROM pg_tables WHERE schemaname = ''public'';');

-- Check if memories table exists and has data
SELECT * FROM postgres_query($postgres_url, 'SELECT COUNT(*) as memory_count FROM public.memories;');

-- Connection test complete
SELECT 'PostgreSQL connection test completed successfully' as status;