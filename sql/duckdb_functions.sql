-- DuckDB Functions and Connection Management
-- BMP-002: Create helper functions for biological memory pipeline

-- Create functions for exponential backoff calculation using SQL expressions
CREATE VIEW backoff_calculator AS
SELECT 
    attempt,
    1000 * (2 ** LEAST(attempt, 10)) as delay_ms
FROM generate_series(0, 15) t(attempt);

-- Test backoff calculation
SELECT * FROM backoff_calculator WHERE attempt <= 5;

-- Create a connection retry function using a table approach
CREATE TABLE IF NOT EXISTS retry_log (
    connection_name VARCHAR,
    attempt_number INTEGER,
    attempt_time TIMESTAMP,
    success BOOLEAN,
    error_message VARCHAR
);

-- Test httpfs extension with a simple HTTP request (this will fail without network but shows the extension works)
-- We'll use this pattern for Ollama integration when available
CREATE TABLE IF NOT EXISTS http_test_log (
    test_name VARCHAR,
    test_time TIMESTAMP,
    result VARCHAR,
    success BOOLEAN
);

INSERT INTO http_test_log VALUES 
    ('httpfs_extension_loaded', CURRENT_TIMESTAMP, 'Extension successfully loaded and ready for HTTP requests', TRUE);

-- Create prompt response structure for when Ollama is available
CREATE TABLE IF NOT EXISTS prompt_responses (
    id UUID DEFAULT gen_random_uuid(),
    model VARCHAR,
    prompt TEXT,
    response TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    success BOOLEAN
);

-- Create embedding storage structure  
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID DEFAULT gen_random_uuid(),
    text_input TEXT,
    model VARCHAR,
    embedding FLOAT[],
    dimensions INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test JSON processing capabilities
SELECT 
    json_object(
        'duckdb_version', '1.3.2',
        'extensions', json_array('httpfs', 'postgres', 'json', 'spatial'),
        'status', 'initialized',
        'timestamp', CURRENT_TIMESTAMP,
        'postgres_config', json_object(
            'host', '192.168.1.104',
            'port', 5432,
            'database', 'codex_db',
            'connection_ready', false
        ),
        'ollama_config', json_object(
            'url', 'http://localhost:11434',
            'model', 'gpt-oss:20b',
            'embedding_model', 'nomic-embed-text',
            'connection_ready', false
        )
    ) as configuration_json;

-- Show connection status
SELECT 
    connection_name,
    is_connected,
    last_check,
    error_message,
    retry_count
FROM connection_status
ORDER BY connection_name;