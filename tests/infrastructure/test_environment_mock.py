"""
Mock tests for BMP-001 when live servers are not available
These tests validate configuration and connection logic without requiring live endpoints
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


def test_environment_config_validation():
    """Test environment configuration validation logic."""
    # Test with missing variables
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(EnvironmentError) as exc_info:
            EnvironmentConfig()
        assert "Missing required environment variables" in str(exc_info.value)

    # Test with all required variables
    env_vars = {
        "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "MAX_DB_CONNECTIONS": "160",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = EnvironmentConfig()
        assert config.get("OLLAMA_URL") == "http://localhost:11434"
        assert config.get("MAX_DB_CONNECTIONS") == "160"


def test_retry_logic():
    """Test connection retry logic with exponential backoff."""
    retry = ConnectionRetry(max_retries=3, base_delay=0.1, max_delay=1.0)

    # Test successful function
    def success_func():
        return "success"

    result = retry.retry_with_backoff(success_func)
    assert result == "success"

    # Test function that fails then succeeds
    attempt_count = [0]

    def fail_then_succeed():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise ConnectionError("Connection failed")
        return "success"

    result = retry.retry_with_backoff(fail_then_succeed)
    assert result == "success"
    assert attempt_count[0] == 3

    # Test function that always fails
    def always_fail():
        raise ConnectionError("Always fails")

    with pytest.raises(ConnectionError):
        retry.retry_with_backoff(always_fail)


@patch("psycopg2.connect")
def test_postgres_connection_mock(mock_connect):
    """Test PostgreSQL connection logic with mocked connection."""
    # Mock connection and cursor
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.fetchone.side_effect = [
        {
            "version": "PostgreSQL 14.0",
            "current_database": "codex_db",
            "current_user": "codex_user",
        },
        {"connection_count": 5},
    ]
    mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
    mock_connect.return_value = mock_conn

    # Test environment config
    env_vars = {
        "POSTGRES_DB_URL": "postgresql://codex_user:pass@localhost:5432/codex_db",
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "MAX_DB_CONNECTIONS": "160",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = EnvironmentConfig()
        postgres = PostgreSQLConnection(config)

        result = postgres.test_connection()

        # Verify connection was called with correct URL
        mock_connect.assert_called_once()
        args, kwargs = mock_connect.call_args
        assert args[0] == "postgresql://codex_user:pass@localhost:5432/codex_db"
        assert "cursor_factory" in kwargs

        assert result["status"] == "connected"
        assert result["database"] == "codex_db"
        assert result["user"] == "codex_user"
        assert "PostgreSQL" in result["version"]


@patch("psycopg2.pool.ThreadedConnectionPool")
def test_postgres_connection_pool_mock(mock_pool_class):
    """Test PostgreSQL connection pool with mocked pool."""
    mock_pool = Mock()
    mock_pool.minconn = 16
    mock_pool.maxconn = 160
    mock_pool_class.return_value = mock_pool

    # Mock connections from pool
    mock_connections = [Mock() for _ in range(5)]
    for i, conn in enumerate(mock_connections):
        cursor = Mock()
        cursor.fetchone.return_value = {"pg_backend_pid": 1000 + i}
        conn.cursor.return_value.__enter__ = Mock(return_value=cursor)
        conn.cursor.return_value.__exit__ = Mock(return_value=None)

    mock_pool.getconn.side_effect = mock_connections

    env_vars = {
        "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
        "MAX_DB_CONNECTIONS": "160",
        "OLLAMA_URL": "http://host:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = EnvironmentConfig()
        postgres = PostgreSQLConnection(config)

        result = postgres.test_connection_pool()

        assert result["status"] == "pool_working"
        assert result["max_connections"] == 160
        assert result["min_connections"] == 16
        assert result["active_test_connections"] == 5


@patch("requests.get")
@patch("requests.post")
def test_ollama_connection_mock(mock_post, mock_get):
    """Test Ollama connection with mocked HTTP responses."""
    # Mock API responses
    mock_get.return_value.json.return_value = {
        "models": [{"name": "gpt-oss:20b"}, {"name": "nomic-embed-text"}, {"name": "other-model"}]
    }
    mock_get.return_value.raise_for_status = Mock()

    mock_post.return_value.json.return_value = {
        "response": "Connection test successful",
        "total_duration": 1000000,
        "load_duration": 500000,
        "eval_count": 5,
    }
    mock_post.return_value.raise_for_status = Mock()

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

        # Test connection
        result = ollama.test_connection()
        assert result["status"] == "connected"
        assert result["base_url"] == "http://localhost:11434"
        assert "gpt-oss:20b" in result["available_models"]

        # Test model availability
        model_result = ollama.test_model_availability()
        assert model_result["llm_available"]
        assert model_result["embedding_available"]

        # Test generation
        gen_result = ollama.test_generation()
        assert gen_result["status"] == "generation_tested"
        assert gen_result["model"] == "gpt-oss:20b"
        assert gen_result["eval_count"] == 5


@patch("requests.post")
def test_ollama_embeddings_mock(mock_post):
    """Test Ollama embedding generation with mock."""
    # Mock embedding response
    mock_post.return_value.json.return_value = {
        # 768 dimensions total
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
        + [0.0] * 763
    }
    mock_post.return_value.raise_for_status = Mock()

    env_vars = {
        "OLLAMA_URL": "http://localhost:11434",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "POSTGRES_DB_URL": "postgresql://test:test@host:5432/db",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "DUCKDB_PATH": "/tmp/test.duckdb",
        "MAX_DB_CONNECTIONS": "160",
        "TEST_DATABASE_URL": "postgresql://test:test@host:5432/testdb",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = EnvironmentConfig()
        ollama = OllamaConnection(config)

        result = ollama.test_embeddings()

        assert result["status"] == "embeddings_tested"
        assert result["model"] == "nomic-embed-text"
        assert result["embedding_dimensions"] == 768
        assert len(result["embedding_sample"]) == 5


def test_environment_variables_validation():
    """Test specific environment variable validation from BMP-001 acceptance criteria."""
    env_vars = {
        "POSTGRES_DB_URL": "postgresql://codex_user:pass@localhost:5432/codex_db",
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "gpt-oss:20b",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "DUCKDB_PATH": "/Users/test/biological_memory/dbs/memory.duckdb",
        "MAX_DB_CONNECTIONS": "160",
        "TEST_DATABASE_URL": "postgresql://test_user:test_pass@localhost:5432/test_db",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = EnvironmentConfig()

        # Test BMP-001 acceptance criteria
        assert config.get("POSTGRES_DB_URL") is not None
        assert config.get("OLLAMA_URL") == "http://localhost:11434"
        assert config.get("OLLAMA_MODEL") == "gpt-oss:20b"
        assert config.get("EMBEDDING_MODEL") == "nomic-embed-text"
        assert config.get("DUCKDB_PATH") is not None
        assert config.get("TEST_DATABASE_URL") is not None

        # Test PostgreSQL URL format
        postgres_url = config.get("POSTGRES_DB_URL")
        assert "localhost:5432" in postgres_url

        # Test MAX_DB_CONNECTIONS
        max_connections = config.get("MAX_DB_CONNECTIONS")
        assert int(max_connections) == 160


if __name__ == "__main__":
    """Run mock tests directly."""
    import sys

    print("🔧 BMP-001 Mock Environment Test Suite")
    print("=" * 50)
    print("Running tests with mocked connections (for offline testing)")

    try:
        # Run all the test functions
        test_environment_config_validation()
        print("✅ Environment config validation")

        test_retry_logic()
        print("✅ Connection retry logic")

        test_postgres_connection_mock()
        print("✅ PostgreSQL connection logic (mocked)")

        test_postgres_connection_pool_mock()
        print("✅ PostgreSQL connection pool (mocked)")

        test_ollama_connection_mock()
        print("✅ Ollama connection logic (mocked)")

        test_ollama_embeddings_mock()
        print("✅ Ollama embeddings logic (mocked)")

        test_environment_variables_validation()
        print("✅ Environment variables validation")

        print("\n🎉 BMP-001 Mock Tests: ALL TESTS PASSED")
        print("Connection logic validated - ready for live server testing!")

    except Exception as e:
        print(f"\n❌ Mock test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
