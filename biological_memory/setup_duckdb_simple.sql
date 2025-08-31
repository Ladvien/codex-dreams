-- DuckDB Setup Script for Biological Memory Pipeline - Simple Version
-- Sets up postgres_scanner extension for cross-database connectivity

-- Install required extensions
INSTALL postgres_scanner;
INSTALL fts;
INSTALL json;
INSTALL httpfs;

-- Load extensions for current session
LOAD postgres_scanner;
LOAD fts;
LOAD json;
LOAD httpfs;

-- Verify postgres_scanner extension is loaded
SELECT extension_name, loaded, installed 
FROM duckdb_extensions() 
WHERE extension_name IN ('postgres_scanner', 'fts', 'json', 'httpfs');

-- Performance optimization settings
PRAGMA memory_limit='4GB';
PRAGMA threads=4;

-- Enable progress bar for long-running queries
PRAGMA enable_progress_bar=true;

-- Success message
SELECT 'DuckDB extensions configured successfully!' as status;