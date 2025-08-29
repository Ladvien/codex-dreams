"""
Tests for infrastructure.environment module
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from src.infrastructure.environment import (
    EnvironmentConfig,
    PostgreSQLConnection,
    OllamaConnection,
    ConnectionRetry
)


class TestEnvironmentConfig:
    """Test environment configuration"""
    
    def test_from_env_with_values(self):
        """Test creating config from environment variables"""
        with patch.dict(os.environ, {
            'POSTGRES_DB_URL': 'postgresql://test@localhost/test',
            'OLLAMA_URL': 'http://localhost:11434',
            'DUCKDB_PATH': '/tmp/test.duckdb'
        }):
            config = EnvironmentConfig.from_env()
            assert config.postgres_url == 'postgresql://test@localhost/test'
            assert config.ollama_url == 'http://localhost:11434'
            assert config.duckdb_path == '/tmp/test.duckdb'
    
    def test_from_env_with_defaults(self):
        """Test creating config with default values"""
        with patch.dict(os.environ, {}, clear=True):
            config = EnvironmentConfig.from_env()
            assert config.postgres_url == ''
            assert config.ollama_url == ''
            assert config.duckdb_path == ''


class TestPostgreSQLConnection:
    """Test PostgreSQL connection handler"""
    
    def test_connection_initialization(self):
        """Test connection initialization"""
        conn = PostgreSQLConnection('postgresql://test@localhost/test')
        assert conn.url == 'postgresql://test@localhost/test'
        assert conn.connected is False
    
    def test_connect(self):
        """Test connection method"""
        conn = PostgreSQLConnection('postgresql://test@localhost/test')
        result = conn.connect()
        assert result is True
        assert conn.connected is True
    
    def test_disconnect(self):
        """Test disconnection method"""
        conn = PostgreSQLConnection('postgresql://test@localhost/test')
        conn.connect()
        conn.disconnect()
        assert conn.connected is False


class TestOllamaConnection:
    """Test Ollama connection handler"""
    
    def test_connection_initialization(self):
        """Test connection initialization"""
        conn = OllamaConnection('http://localhost:11434')
        assert conn.url == 'http://localhost:11434'
        assert conn.connected is False
    
    def test_connect(self):
        """Test connection method"""
        conn = OllamaConnection('http://localhost:11434')
        result = conn.connect()
        assert result is True
        assert conn.connected is True
    
    def test_disconnect(self):
        """Test disconnection method"""
        conn = OllamaConnection('http://localhost:11434')
        conn.connect()
        conn.disconnect()
        assert conn.connected is False


class TestConnectionRetry:
    """Test connection retry handler"""
    
    def test_initialization(self):
        """Test retry initialization"""
        retry = ConnectionRetry(max_retries=5)
        assert retry.max_retries == 5
        assert retry.attempts == 0
    
    def test_retry_success(self):
        """Test successful retry"""
        retry = ConnectionRetry(max_retries=3)
        
        @retry.retry
        def successful_func():
            return "success"
        
        result = successful_func()
        assert result == "success"
    
    def test_retry_with_failures(self):
        """Test retry with failures before success"""
        retry = ConnectionRetry(max_retries=3)
        call_count = 0
        
        @retry.retry
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Test error")
            return "success"
        
        result = failing_then_success()
        assert result == "success"
        assert retry.attempts == 1
    
    def test_retry_max_attempts_exceeded(self):
        """Test retry when max attempts exceeded"""
        retry = ConnectionRetry(max_retries=2)
        
        @retry.retry
        def always_fails():
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            always_fails()
        assert retry.attempts == 2