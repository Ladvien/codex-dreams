-- DuckDB Performance Configuration for Biological Memory System
-- This file contains optimized settings for biological memory processing

-- Memory and Resource Settings
SET memory_limit = '8GB';
SET max_memory = '6GB';
SET threads = 4;

-- Performance Optimizations
SET preserve_insertion_order = false;
SET default_order = 'ASC';
SET enable_progress_bar = true;
SET max_expression_depth = 1000;

-- External Access (disabled for security)
SET enable_external_access = false;

-- Remote Table Considerations
-- Note: Cannot create indexes on remote tables (e.g., PostgreSQL tables via postgres_scanner)
-- Remote tables must be indexed at the source database for optimal performance
-- postgres_scanner extension provides access to remote PostgreSQL data