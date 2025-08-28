-- Test PostgreSQL connection from DuckDB
-- Using postgres_scanner extension

-- Test basic connection to PostgreSQL
SELECT * FROM postgres_query('postgresql://codex_user:MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a@192.168.1.104:5432/codex_db', 'SELECT version();');

-- List available tables in PostgreSQL
SELECT * FROM postgres_query('postgresql://codex_user:MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a@192.168.1.104:5432/codex_db', 'SELECT schemaname, tablename FROM pg_tables WHERE schemaname = ''public'';');