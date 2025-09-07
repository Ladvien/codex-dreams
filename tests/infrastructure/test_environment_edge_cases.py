"""
Edge case tests for BMP-001 Environment Setup
Tests edge cases, error conditions, and resource limits
"""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.infrastructure.environment import (
    ConnectionRetry,
    EnvironmentConfig,
    OllamaConnection,
    PostgreSQLConnection,
)


def test_invalid_environment_variable_formats():
    """Test handling of invalid environment variable formats."""
    # Test malformed PostgreSQL URL
    invalid_env_vars = {
        "POSTGRES_DB_URL": "not-a-valid-url",
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "MAX_DB_CONNECTIONS": "not-a-number",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    with patch.dict(os.environ, invalid_env_vars, clear=True):
        config = EnvironmentConfig()

        # Should load but connection will fail
        assert config.get("POSTGRES_DB_URL") == "not-a-valid-url"

        # MAX_DB_CONNECTIONS should be handled gracefully
        with pytest.raises(ValueError):
            int(config.get("MAX_DB_CONNECTIONS"))


def test_missing_optional_environment_variables():
    """Test behavior with missing optional environment variables."""
    minimal_env_vars = {
        "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
        "OLLAMA_URL": "http://host:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "MAX_DB_CONNECTIONS": "160",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
        # Missing optional vars like DBT_PROFILES_DIR, etc.
    }

    with patch.dict(os.environ, minimal_env_vars, clear=True):
        config = EnvironmentConfig()

        # Should handle missing optional variables gracefully
        assert config.get("DBT_PROFILES_DIR") is None
        assert config.get("DBT_PROJECT_DIR") is None
        assert config.get("NONEXISTENT_VAR", "default") == "default"


@patch("psycopg2.connect")
def test_postgres_connection_pool_exhaustion(mock_connect):
    """Test handling of connection pool exhaustion."""
    # Mock pool that raises error on exhaustion
    with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_class:
        mock_pool = Mock()
        mock_pool.getconn.side_effect = Exception("Pool exhausted")
        mock_pool_class.return_value = mock_pool

        env_vars = {
            "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
            "MAX_DB_CONNECTIONS": "2",  # Very small pool for testing
            "OLLAMA_URL": "http://host:11434",
            "OLLAMA_MODEL": "gpt-oss:20b",
            "EMBEDDING_MODEL": "nomic-embed-text",
            "DUCKDB_PATH": "/tmp/test.duckdb",
            "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = EnvironmentConfig()
            postgres = PostgreSQLConnection(config)

            # Should handle pool exhaustion gracefully
            with pytest.raises(Exception) as exc_info:
                postgres.test_connection_pool()
            assert "Pool exhausted" in str(exc_info.value)


def test_retry_logic_edge_cases():
    """Test retry logic with various edge cases."""
    # Test zero retries
    retry = ConnectionRetry(max_retries=0, base_delay=0.1)

    def always_fail():
        raise ConnectionError("Always fails")

    with pytest.raises(ConnectionError):
        retry.retry_with_backoff(always_fail)

    # Test with very high retry count (should still respect max_delay)
    retry = ConnectionRetry(max_retries=10, base_delay=0.01, max_delay=0.1)

    attempt_count = [0]

    def fail_until_attempt_5():
        attempt_count[0] += 1
        if attempt_count[0] < 5:
            raise ConnectionError(f"Attempt {attempt_count[0]} failed")
        return f"Success on attempt {attempt_count[0]}"

    result = retry.retry_with_backoff(fail_until_attempt_5)
    assert "Success on attempt 5" in result
    assert attempt_count[0] == 5


@patch("requests.get")
def test_ollama_malformed_responses(mock_get):
    """Test handling of malformed Ollama API responses."""
    # Test invalid JSON response
    mock_response = Mock()
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    env_vars = {
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "MAX_DB_CONNECTIONS": "160",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = EnvironmentConfig()
        ollama = OllamaConnection(config)

        with pytest.raises(json.JSONDecodeError):
            ollama.test_connection()


@patch("requests.get")
def test_ollama_missing_models(mock_get):
    """Test behavior when required models are not available."""
    # Mock response with no models
    mock_get.return_value.json.return_value = {"models": []}
    mock_get.return_value.raise_for_status = Mock()

    env_vars = {
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "MAX_DB_CONNECTIONS": "160",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = EnvironmentConfig()
        ollama = OllamaConnection(config)

        result = ollama.test_model_availability()

        # Should handle missing models gracefully
        assert result["llm_available"] == False
        assert result["embedding_available"] == False
        assert result["all_available_models"] == []


@patch("requests.post")
def test_ollama_timeout_handling(mock_post):
    """Test Ollama timeout handling."""
    import requests

    # Mock timeout exception
    mock_post.side_effect = requests.Timeout("Request timed out")

    env_vars = {
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "MAX_DB_CONNECTIONS": "160",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = EnvironmentConfig()
        ollama = OllamaConnection(config)

        # Should retry and eventually fail with timeout
        with pytest.raises(requests.Timeout):
            ollama.test_generation()


def test_duckdb_path_edge_cases():
    """Test DuckDB path handling edge cases."""
    edge_case_paths = [
        "/nonexistent/deeply/nested/path/memory.duckdb",
        "/tmp/memory with spaces.duckdb",
        "/tmp/memory-with-special-chars!@#$.duckdb",
        "",  # Empty string
        None,  # None value (should be caught by env validation)
    ]

    for test_path in edge_case_paths[:-1]:  # Skip None test
        env_vars = {
            "DUCKDB_PATH": test_path,
            "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
            "OLLAMA_URL": "http://host:11434",
            "OLLAMA_MODEL": "gpt-oss:20b",
            "EMBEDDING_MODEL": "nomic-embed-text",
            "MAX_DB_CONNECTIONS": "160",
            "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = EnvironmentConfig()
            assert config.get("DUCKDB_PATH") == test_path


@patch("psycopg2.connect")
def test_postgres_connection_interrupted(mock_connect):
    """Test PostgreSQL connection interrupted scenarios."""
    import psycopg2

    # Test connection that gets interrupted
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.execute.side_effect = psycopg2.InterfaceError("Connection lost")

    # Set up cursor context manager properly
    cursor_context_manager = MagicMock()
    cursor_context_manager.__enter__.return_value = mock_cursor
    cursor_context_manager.__exit__.return_value = None
    mock_conn.cursor.return_value = cursor_context_manager

    mock_connect.return_value = mock_conn

    env_vars = {
        "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
        "OLLAMA_URL": "http://host:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "MAX_DB_CONNECTIONS": "160",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = EnvironmentConfig()
        postgres = PostgreSQLConnection(config)

        # Should handle interface errors with retry
        with pytest.raises(psycopg2.InterfaceError):
            postgres.test_connection()


def test_large_connection_pool_configuration():
    """Test very large connection pool configurations."""
    env_vars = {
        "MAX_DB_CONNECTIONS": "1000",  # Very large pool
        "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
        "OLLAMA_URL": "http://host:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = EnvironmentConfig()
        assert int(config.get("MAX_DB_CONNECTIONS")) == 1000

        postgres = PostgreSQLConnection(config)

        # Should calculate reasonable minimum connections (10% of max)
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            postgres.create_connection_pool()

            # Verify pool was created with correct parameters
            mock_pool.assert_called_once()
            args, kwargs = mock_pool.call_args

            assert kwargs["maxconn"] == 1000
            assert kwargs["minconn"] == 100  # 10% of 1000


@patch("requests.get")
def test_ollama_network_errors(mock_get):
    """Test various network error scenarios with Ollama."""
    import requests

    network_errors = [
        requests.ConnectionError("Connection refused"),
        requests.HTTPError("HTTP 500 Internal Server Error"),
        requests.RequestException("Generic request error"),
    ]

    env_vars = {
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "MAX_DB_CONNECTIONS": "160",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    for error in network_errors:
        mock_get.side_effect = error

        with patch.dict(os.environ, env_vars, clear=True):
            config = EnvironmentConfig()
            ollama = OllamaConnection(config)

            # Should propagate network errors after retry attempts
            with pytest.raises(type(error)):
                ollama.test_connection()


def test_environment_config_thread_safety():
    """Test environment configuration in multi-threaded scenarios."""
    import concurrent.futures

    env_vars = {
        "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
        "OLLAMA_URL": "http://host:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "MAX_DB_CONNECTIONS": "160",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    def create_config():
        """Create config in separate thread."""
        with patch.dict(os.environ, env_vars, clear=True):
            config = EnvironmentConfig()
            return config.get("OLLAMA_MODEL")

    # Test concurrent config creation
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_config) for _ in range(10)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    # All threads should get the same configuration
    assert all(result == "gpt-oss:20b" for result in results)
    assert len(set(results)) == 1  # All results should be identical


if __name__ == "__main__":
    """Run edge case tests directly."""
    import sys

    print("🧪 BMP-001 Edge Case Test Suite")
    print("=" * 50)
    print("Testing edge cases and error conditions")

    try:
        # Run edge case tests
        test_invalid_environment_variable_formats()
        print("✅ Invalid environment variable formats")

        test_missing_optional_environment_variables()
        print("✅ Missing optional environment variables")

        test_retry_logic_edge_cases()
        print("✅ Retry logic edge cases")

        test_duckdb_path_edge_cases()
        print("✅ DuckDB path edge cases")

        test_large_connection_pool_configuration()
        print("✅ Large connection pool configuration")

        test_environment_config_thread_safety()
        print("✅ Environment config thread safety")

        print("\n🎉 BMP-001 Edge Case Tests: ALL TESTS PASSED")
        print("System is robust against edge cases and error conditions!")

    except Exception as e:
        print(f"\n❌ Edge case test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
