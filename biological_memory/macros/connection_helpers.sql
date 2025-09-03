{% macro exponential_backoff(attempt, base_delay=1000, max_delay=30000) %}
-- Calculate exponential backoff delay in milliseconds
-- Usage: {{ exponential_backoff(3) }} returns delay for 3rd attempt
    {{ base_delay }} * (2 ^ LEAST({{ attempt }}, 10))
{% endmacro %}

{% macro retry_with_backoff(sql_query, max_attempts=3) %}
-- Retry pattern for external service calls
-- This is a template - actual retry logic would be implemented in Python services
    {% set attempt = 1 %}
    {% set delay = exponential_backoff(attempt) %}
    
    -- Log retry attempt
    INSERT INTO retry_log (connection_name, attempt_number, attempt_time, success, error_message)
    VALUES ('{{ this.name }}', {{ attempt }}, CURRENT_TIMESTAMP, false, 'Attempting connection...');
    
    -- Execute the actual query
    {{ sql_query }}
{% endmacro %}

{% macro connection_health_check(connection_name) %}
-- Generate connection health status for monitoring
SELECT 
    '{{ connection_name }}' as connection_name,
    COUNT(*) as total_attempts,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_attempts,
    MAX(attempt_time) as last_attempt,
    CASE 
        WHEN MAX(CASE WHEN success THEN attempt_time END) > 
             MAX(CASE WHEN NOT success THEN attempt_time END) 
        THEN 'healthy'
        ELSE 'unhealthy'
    END as status
FROM retry_log
WHERE connection_name = '{{ connection_name }}'
GROUP BY connection_name
{% endmacro %}

{% macro create_retry_log_table() %}
-- Create retry logging infrastructure
CREATE TABLE IF NOT EXISTS retry_log (
    connection_name VARCHAR,
    attempt_number INTEGER,
    attempt_time TIMESTAMP,
    success BOOLEAN,
    error_message VARCHAR
)
{% endmacro %}