-- DuckDB Connection Manager for Biological Memory Pipeline
-- This manages all external connections (PostgreSQL, Ollama, etc.)

-- IMPORTANT: Set these environment variables in your .env file:
-- POSTGRES_DB_URL=postgresql://username:password@192.168.1.104:5432/codex_db
-- OLLAMA_URL=http://localhost:11434

-- Create connection configuration table
CREATE TABLE IF NOT EXISTS connection_config (
    config_key VARCHAR PRIMARY KEY,
    config_value VARCHAR,
    description VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Load configuration from environment variables
-- These should be set in .env file, not hardcoded here
INSERT OR REPLACE INTO connection_config VALUES
    ('postgres_url', getenv('POSTGRES_DB_URL'), 'PostgreSQL connection string from env', CURRENT_TIMESTAMP),
    ('ollama_url', getenv('OLLAMA_URL'), 'Ollama API base URL from env', CURRENT_TIMESTAMP),
    ('ollama_model', getenv('OLLAMA_MODEL'), 'Default Ollama model from env', CURRENT_TIMESTAMP),
    ('embedding_model', getenv('EMBEDDING_MODEL'), 'Embedding model from env', CURRENT_TIMESTAMP),
    ('max_retry_attempts', '3', 'Maximum connection retry attempts', CURRENT_TIMESTAMP),
    ('retry_base_delay', '1000', 'Base delay in ms for exponential backoff', CURRENT_TIMESTAMP),
    ('connection_timeout', '30000', 'Connection timeout in milliseconds', CURRENT_TIMESTAMP);

-- Create connection status tracking table
CREATE TABLE IF NOT EXISTS connection_status (
    connection_name VARCHAR PRIMARY KEY,
    is_active BOOLEAN DEFAULT FALSE,
    last_checked TIMESTAMP,
    last_error VARCHAR,
    consecutive_failures INT DEFAULT 0
);

-- Create retry log for debugging
CREATE TABLE IF NOT EXISTS retry_log (
    connection_name VARCHAR,
    attempt_number INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN,
    error_message VARCHAR
);

-- Function to get configuration value with fallback
CREATE OR REPLACE MACRO get_config(key VARCHAR, default_value VARCHAR) AS
    COALESCE(
        (SELECT config_value FROM connection_config WHERE config_key = key),
        default_value
    );

-- Function to validate PostgreSQL connection
CREATE OR REPLACE MACRO validate_postgres_connection() AS (
    WITH connection_test AS (
        SELECT
            CASE
                WHEN get_config('postgres_url', '') != '' THEN TRUE
                ELSE FALSE
            END as is_configured
    )
    SELECT
        is_configured,
        CASE
            WHEN is_configured THEN 'PostgreSQL URL configured'
            ELSE 'PostgreSQL URL not found in environment'
        END as status_message
    FROM connection_test
);

-- Function to validate Ollama connection
CREATE OR REPLACE MACRO validate_ollama_connection() AS (
    WITH connection_test AS (
        SELECT
            CASE
                WHEN get_config('ollama_url', '') != '' THEN TRUE
                ELSE FALSE
            END as is_configured
    )
    SELECT
        is_configured,
        CASE
            WHEN is_configured THEN 'Ollama URL configured'
            ELSE 'Ollama URL not found in environment'
        END as status_message
    FROM connection_test
);

-- Initialize connection status
INSERT OR REPLACE INTO connection_status VALUES
    ('postgres', FALSE, NULL, NULL, 0),
    ('ollama', FALSE, NULL, NULL, 0);

-- Create view to show current configuration (with sensitive data masked)
CREATE OR REPLACE VIEW connection_config_view AS
SELECT
    config_key,
    CASE
        WHEN config_key LIKE '%url%' AND config_value LIKE '%@%' THEN
            regexp_replace(config_value, ':[^:@]+@', ':****@', 'g')
        ELSE config_value
    END as config_value,
    description,
    created_at
FROM connection_config;

-- Exponential backoff calculator for retries
CREATE OR REPLACE VIEW backoff_calculator AS
WITH RECURSIVE backoff_sequence AS (
    SELECT
        0 as attempt,
        1000 as delay_ms
    UNION ALL
    SELECT
        attempt + 1,
        LEAST(delay_ms * 2, 32000) -- Cap at 32 seconds
    FROM backoff_sequence
    WHERE attempt < 5
)
SELECT * FROM backoff_sequence;

SELECT 'Connection manager initialized. Check connection_config_view for status.' as status;