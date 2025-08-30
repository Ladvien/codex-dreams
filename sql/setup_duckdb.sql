-- DuckDB Extension and Configuration Setup
-- BMP-002: Initialize DuckDB with all required extensions

-- Install required extensions
INSTALL httpfs;
INSTALL postgres;
INSTALL json;
INSTALL spatial;

-- Load all extensions
LOAD httpfs;
LOAD postgres;
LOAD json;
LOAD spatial;

-- Display installed extensions for verification
SELECT * FROM duckdb_extensions() WHERE installed = true;

-- Test basic functionality
SELECT 'DuckDB initialization successful' as status;