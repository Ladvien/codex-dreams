-- DuckDB Connection Manager with Retry Logic
-- BMP-002: Comprehensive database and API connection setup

-- Create stored procedures for connection management
-- Note: DuckDB doesn't have stored procedures, so we use table-valued functions and macros

-- Create configuration table for connection parameters
CREATE TABLE IF NOT EXISTS connection_config (
    config_key VARCHAR PRIMARY KEY,
    config_value VARCHAR NOT NULL,
    description VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert configuration values
INSERT OR REPLACE INTO connection_config VALUES 
    ('postgres_url', 'postgresql://codex_user:MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a@192.168.1.104:5432/codex_db', 'PostgreSQL connection string', CURRENT_TIMESTAMP),
    ('ollama_url', 'http://192.168.1.110:11434', 'Ollama API base URL', CURRENT_TIMESTAMP),
    ('ollama_model', 'gpt-oss:20b', 'Default LLM model', CURRENT_TIMESTAMP),
    ('embedding_model', 'nomic-embed-text', 'Default embedding model', CURRENT_TIMESTAMP),
    ('max_retry_attempts', '5', 'Maximum connection retry attempts', CURRENT_TIMESTAMP),
    ('retry_base_delay', '1000', 'Base retry delay in milliseconds', CURRENT_TIMESTAMP),
    ('connection_timeout', '30000', 'Connection timeout in milliseconds', CURRENT_TIMESTAMP);

-- Create connection status tracking table
CREATE TABLE IF NOT EXISTS connection_status (
    connection_name VARCHAR PRIMARY KEY,
    is_connected BOOLEAN DEFAULT FALSE,
    last_check TIMESTAMP,
    error_message VARCHAR,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP
);

-- Initialize connection status
INSERT OR REPLACE INTO connection_status VALUES 
    ('postgres', FALSE, CURRENT_TIMESTAMP, 'Not tested yet', 0, NULL),
    ('ollama', FALSE, CURRENT_TIMESTAMP, 'Not tested yet', 0, NULL),
    ('httpfs', TRUE, CURRENT_TIMESTAMP, 'Extension loaded', 0, NULL);

-- Create macro for exponential backoff calculation
CREATE MACRO calculate_backoff(attempt INTEGER, base_delay INTEGER) AS 
    base_delay * (2 ** LEAST(attempt, 10));

-- Test JSON functionality
CREATE TABLE IF NOT EXISTS json_test AS 
SELECT 
    '{"status": "initialized", "timestamp": "' || CURRENT_TIMESTAMP || '", "extensions": ["httpfs", "postgres", "json", "spatial"]}' as config_json;

SELECT 
    json_extract(config_json, '$.status') as status,
    json_extract(config_json, '$.timestamp') as init_time,
    json_array_length(json_extract(config_json, '$.extensions')) as extension_count
FROM json_test;

-- Create a mock prompt function for testing (will be replaced when Ollama is available)
CREATE MACRO mock_prompt(model_name VARCHAR, prompt_text VARCHAR) AS 
    '{"response": "Mock response for: ' || prompt_text || '", "model": "' || model_name || '", "timestamp": "' || CURRENT_TIMESTAMP || '"}';

-- Test mock prompt function
SELECT mock_prompt('gpt-oss:20b', 'Hello, this is a test prompt') as mock_response;

-- Show all configuration
SELECT * FROM connection_config ORDER BY config_key;