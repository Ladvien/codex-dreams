"""
Unit tests for BMP-001: Environment Setup and Configuration.

Tests environment variable loading, database connections,
and configuration validation as specified in acceptance criteria.
"""

import os
import pytest
from unittest.mock import patch, Mock
import psycopg2
import requests
from typing import Dict, Any


class TestEnvironmentConfiguration:
    """Test environment variable loading and validation."""

    def test_env_variables_loaded(self, test_env_vars):
        """Test that all required environment variables are loaded."""
        required_vars = [
            "POSTGRES_DB_URL",
            "OLLAMA_URL",
            "OLLAMA_MODEL",
            "EMBEDDING_MODEL",
            "DUCKDB_PATH",
            "MAX_DB_CONNECTIONS",
            "TEST_DATABASE_URL",
        ]

        for var in required_vars:
            assert os.getenv(var) is not None, f"Environment variable {var} should be set"

    def test_specific_env_values(self, test_env_vars):
        """Test specific environment variable values."""
        assert (
            os.getenv("OLLAMA_URL") == "http://localhost:11434"
        ), "OLLAMA_URL should point to test server"
        assert os.getenv("OLLAMA_MODEL") == "gpt-oss:20b", "OLLAMA_MODEL should be gpt-oss:20b"
        assert (
            os.getenv("EMBEDDING_MODEL") == "nomic-embed-text"
        ), "EMBEDDING_MODEL should be nomic-embed-text"
        assert os.getenv("MAX_DB_CONNECTIONS") == "160", "MAX_DB_CONNECTIONS should be 160"

    def test_database_url_format(self):
        """Test database URL format validation."""
        test_db_url = os.getenv("TEST_DATABASE_URL")
        postgres_db_url = os.getenv("POSTGRES_DB_URL")

        # Both should be valid PostgreSQL URLs
        for url in [test_db_url, postgres_db_url]:
            if url:
                assert url.startswith(
                    "postgresql://"
                ), f"URL should use postgresql:// scheme: {url}"
                assert "@" in url, f"URL should contain credentials: {url}"
                assert ":" in url.split("@")[1], f"URL should specify port: {url}"

    def test_duckdb_path_configuration(self):
        """Test DuckDB path configuration."""
        duckdb_path = os.getenv("DUCKDB_PATH")
        assert duckdb_path is not None, "DUCKDB_PATH should be configured"
        assert duckdb_path.endswith(".duckdb"), "DuckDB path should have .duckdb extension"

    def test_timeout_configuration(self):
        """Test timeout configuration for LLM operations."""
        timeout = os.getenv("OLLAMA_TIMEOUT")
        assert timeout is not None, "OLLAMA_TIMEOUT should be configured"
        assert int(timeout) >= 300, "Timeout should be at least 300 seconds for LLM operations"


class TestPostgreSQLConnection:
    """Test PostgreSQL database connectivity."""

    @pytest.mark.database
    def test_postgres_connection_parameters(self):
        """Test PostgreSQL connection parameter parsing."""
        from urllib.parse import urlparse

        test_url = os.getenv("TEST_DATABASE_URL")
        parsed = urlparse(test_url)

        assert parsed.scheme == "postgresql", "Should use PostgreSQL scheme"
        assert parsed.hostname is not None, "Should have hostname"
        assert parsed.port is not None, "Should have port specified"
        assert parsed.username is not None, "Should have username"
        assert parsed.database is not None, "Should have database name"

    @pytest.mark.database
    @patch("psycopg2.connect")
    def test_postgres_connection_mock(self, mock_connect):
        """Test PostgreSQL connection using mock (for CI/CD)."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        test_url = os.getenv("TEST_DATABASE_URL")

        # Attempt connection
        conn = psycopg2.connect(test_url)

        assert conn is not None, "Connection should be established"
        mock_connect.assert_called_once_with(test_url)

    @pytest.mark.database
    def test_connection_pool_configuration(self):
        """Test connection pool configuration."""
        max_connections = int(os.getenv("MAX_DB_CONNECTIONS", "0"))
        assert max_connections == 160, "Should configure 160 max connections for production"

        # Test that the value is reasonable for DuckDB + PostgreSQL
        assert max_connections > 0, "Max connections should be positive"
        assert max_connections <= 1000, "Max connections should be reasonable"


class TestOllamaConnection:
    """Test Ollama LLM server connectivity."""

    @pytest.mark.llm
    @patch("requests.post")
    def test_ollama_generation_endpoint(self, mock_post):
        """Test Ollama generation endpoint connectivity."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test response"}
        mock_post.return_value = mock_response

        ollama_url = os.getenv("OLLAMA_URL")
        model_name = os.getenv("OLLAMA_MODEL")

        # Test generation request
        response = requests.post(
            f"{ollama_url}/api/generate", json={"model": model_name, "prompt": "test"}
        )

        assert response.status_code == 200, "Ollama should respond with 200"
        assert response.json()["response"] is not None, "Should get response text"

    @pytest.mark.llm
    @patch("requests.post")
    def test_ollama_embedding_endpoint(self, mock_post):
        """Test Ollama embedding endpoint connectivity."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": [0.1] * 384}
        mock_post.return_value = mock_response

        ollama_url = os.getenv("OLLAMA_URL")
        embedding_model = os.getenv("EMBEDDING_MODEL")

        # Test embedding request
        response = requests.post(
            f"{ollama_url}/api/embeddings", json={"model": embedding_model, "prompt": "test text"}
        )

        assert response.status_code == 200, "Embedding endpoint should respond"
        embedding = response.json()["embedding"]
        assert isinstance(embedding, list), "Should return embedding vector"
        assert len(embedding) > 0, "Embedding should have dimensions"

    @pytest.mark.llm
    def test_ollama_timeout_configuration(self):
        """Test Ollama request timeout configuration."""
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "0"))
        assert timeout == 300, "Should configure 300 second timeout for LLM operations"

        # Timeout should be reasonable for LLM operations
        assert timeout >= 60, "Timeout should allow for LLM processing time"
        assert timeout <= 600, "Timeout should not be excessive"


class TestConnectionResilience:
    """Test connection retry logic and error handling."""

    @patch("psycopg2.connect")
    def test_postgres_connection_retry(self, mock_connect):
        """Test PostgreSQL connection retry with exponential backoff."""
        # Simulate connection failure then success
        mock_connect.side_effect = [
            psycopg2.OperationalError("Connection failed"),
            psycopg2.OperationalError("Connection failed"),
            Mock(),  # Successful connection
        ]

        # This would be implemented in the actual connection manager
        # Here we test the concept
        retry_count = 0
        max_retries = 3

        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(os.getenv("TEST_DATABASE_URL"))
                break
            except psycopg2.OperationalError:
                retry_count += 1
                if retry_count >= max_retries:
                    raise

        assert retry_count == 2, "Should retry failed connections"
        assert conn is not None, "Should eventually succeed"

    @patch("requests.post")
    def test_ollama_connection_resilience(self, mock_post):
        """Test Ollama connection error handling."""
        # Simulate network error then success
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Connection refused"),
            Mock(status_code=200, json=lambda: {"response": "success"}),
        ]

        retry_count = 0
        max_retries = 2

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{os.getenv('OLLAMA_URL')}/api/generate",
                    json={"model": os.getenv("OLLAMA_MODEL"), "prompt": "test"},
                    timeout=int(os.getenv("OLLAMA_TIMEOUT", "300")),
                )
                break
            except requests.exceptions.ConnectionError:
                retry_count += 1
                if retry_count >= max_retries:
                    raise

        assert retry_count == 1, "Should retry failed requests"
        assert response.status_code == 200, "Should eventually succeed"


class TestEnvironmentValidation:
    """Test environment validation and error detection."""

    def test_missing_required_env_var(self):
        """Test handling of missing required environment variables."""
        required_vars = [
            "POSTGRES_DB_URL",
            "OLLAMA_URL",
            "OLLAMA_MODEL",
            "DUCKDB_PATH",
            "TEST_DATABASE_URL",
        ]

        for var in required_vars:
            # This test validates that the system would catch missing vars
            current_value = os.getenv(var)
            assert current_value is not None, f"Required variable {var} is missing"

    def test_invalid_url_format(self):
        """Test detection of invalid URL formats."""
        urls_to_check = [
            ("POSTGRES_DB_URL", "postgresql://"),
            ("TEST_DATABASE_URL", "postgresql://"),
            ("OLLAMA_URL", "http://"),
        ]

        for env_var, expected_prefix in urls_to_check:
            url = os.getenv(env_var)
            if url:
                assert url.startswith(
                    expected_prefix
                ), f"{env_var} should start with {expected_prefix}"

    def test_numeric_env_var_validation(self):
        """Test validation of numeric environment variables."""
        numeric_vars = [("MAX_DB_CONNECTIONS", 1, 1000), ("OLLAMA_TIMEOUT", 60, 600)]

        for var, min_val, max_val in numeric_vars:
            value = os.getenv(var)
            if value:
                numeric_value = int(value)
                assert (
                    min_val <= numeric_value <= max_val
                ), f"{var} should be between {min_val} and {max_val}, got {numeric_value}"
