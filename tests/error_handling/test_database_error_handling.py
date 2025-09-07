"""
Tests for database error handling in the biological memory system
"""

import os
import sqlite3
import sys
from unittest.mock import Mock, patch

import psycopg2
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from services.error_handling import (
    BiologicalMemoryErrorHandler,
    DatabaseError,
    database_transaction,
    handle_database_connection_error,
    with_database_error_handling,
)


class TestDatabaseErrorHandling:
    """Test database-specific error handling scenarios"""

    @pytest.fixture
    def mock_connection(self):
        """Mock database connection"""
        conn = Mock()
        conn.commit = Mock()
        conn.rollback = Mock()
        return conn

    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing"""
        return BiologicalMemoryErrorHandler()

    def test_database_transaction_success(self, mock_connection):
        """Test successful database transaction"""
        with database_transaction(mock_connection) as conn:
            # Simulate successful operation
            conn.execute("SELECT 1")

        mock_connection.commit.assert_called_once()
        mock_connection.rollback.assert_not_called()

    def test_database_transaction_rollback(self, mock_connection):
        """Test database transaction rollback on error"""
        with pytest.raises(DatabaseError):
            with database_transaction(mock_connection) as conn:
                raise Exception("Database operation failed")

        mock_connection.rollback.assert_called_once()
        mock_connection.commit.assert_not_called()

    def test_database_transaction_rollback_failure(self, mock_connection):
        """Test handling of rollback failure"""
        mock_connection.rollback.side_effect = Exception("Rollback failed")

        with pytest.raises(DatabaseError):
            with database_transaction(mock_connection) as conn:
                raise Exception("Database operation failed")

        # Should still attempt rollback
        mock_connection.rollback.assert_called_once()

    @patch("psycopg2.connect")
    def test_connection_error_handling(self, mock_connect):
        """Test PostgreSQL connection error handling"""
        mock_connect.side_effect = psycopg2.OperationalError("Connection refused")

        def attempt_connection():
            return psycopg2.connect("postgresql://localhost/test")

        result = handle_database_connection_error(attempt_connection)
        assert result is None  # Should return None on failure

    def test_database_decorator_error_handling(self):
        """Test database error handling decorator"""

        @with_database_error_handling(timeout_seconds=30.0)
        def failing_database_operation():
            raise psycopg2.DatabaseError("Table does not exist")

        with pytest.raises(DatabaseError) as exc_info:
            failing_database_operation()

        assert "Table does not exist" in str(exc_info.value)
        assert exc_info.value.retry_suggested  # Database errors should be retryable by default

    def test_connection_timeout_handling(self, error_handler):
        """Test database connection timeout handling"""
        timeout_error = psycopg2.OperationalError("Connection timeout")

        error_record = error_handler.handle_error(
            timeout_error,
            {
                "operation": "database_connection",
                "biological_context": {"memory_stage": "consolidation"},
            },
        )

        assert error_record["category"] == "database"
        assert error_record["recovery_attempted"] == True

        recovery_result = error_record["recovery_result"]
        assert recovery_result["action"] == "increase_timeout_and_retry"
        assert "biological" in recovery_result["biological_note"].lower()

    def test_deadlock_handling(self, error_handler):
        """Test database deadlock error handling"""
        deadlock_error = psycopg2.DatabaseError("deadlock detected")

        error_record = error_handler.handle_error(deadlock_error)
        recovery_result = error_record["recovery_result"]

        assert recovery_result["action"] == "retry_with_jitter"
        assert recovery_result["max_retries"] == 10  # More retries for deadlocks
        assert "jitter_range" in recovery_result

    def test_database_integrity_error(self, error_handler):
        """Test handling of database integrity constraint violations"""
        integrity_error = psycopg2.IntegrityError("UNIQUE constraint failed")

        error_record = error_handler.handle_error(integrity_error)

        # Integrity errors should be classified as critical
        assert error_record["severity"] == "critical"

    @patch("sqlite3.connect")
    def test_sqlite_error_handling(self, mock_connect):
        """Test SQLite-specific error handling"""
        mock_connect.side_effect = sqlite3.OperationalError("Database is locked")

        @with_database_error_handling()
        def sqlite_operation():
            return sqlite3.connect(":memory:")

        with pytest.raises(DatabaseError):
            sqlite_operation()

    def test_writeback_error_recovery(self, error_handler):
        """Test memory writeback error recovery strategies"""
        from services.error_handling import WritebackError

        writeback_error = WritebackError("Failed to write processed memories")
        error_record = error_handler.handle_error(
            writeback_error, {"operation": "memory_writeback", "batch_size": 1000}
        )

        recovery_result = error_record["recovery_result"]
        assert recovery_result["action"] == "retry_with_validation"
        assert recovery_result["fallback"] == "queue_for_later"
        assert "validation_steps" in recovery_result

    def test_database_connection_pool_error(self, error_handler):
        """Test connection pool exhaustion handling"""
        pool_error = Exception("connection pool exhausted")

        error_record = error_handler.handle_error(
            pool_error,
            {
                "operation": "get_connection",
                "biological_context": {"memory_stage": "working_memory"},
            },
        )

        # Should be classified as database error
        assert error_record["category"] == "database"

        # Working memory operations should have limited retries
        bio_context = error_record["biological_context"]
        assert bio_context["memory_stage"] == "working_memory"

    def test_database_migration_error_handling(self, error_handler):
        """Test handling of database schema migration errors"""
        migration_error = Exception("column does not exist after migration")

        error_record = error_handler.handle_error(
            migration_error,
            {"operation": "schema_migration", "migration_version": "v2.1.0"},
        )

        # Should be high severity as it affects system functionality
        assert error_record["severity"] in ["high", "critical"]

    def test_biological_memory_database_constraints(self, error_handler):
        """Test database operations with biological memory constraints"""
        # Working memory operations should be fast
        working_memory_context = {"biological_context": {"memory_stage": "working_memory"}}

        # Simulate a slow database operation during working memory processing
        slow_db_error = Exception("query timeout - working memory constraint exceeded")

        error_record = error_handler.handle_error(slow_db_error, working_memory_context)

        assert "working_memory" in str(error_record["biological_context"])

        # The recovery strategy should respect biological constraints
        recovery_result = error_record.get("recovery_result", {})
        if recovery_result:
            assert "biological" in recovery_result.get("biological_note", "").lower()


class TestDatabaseRecoveryStrategies:
    """Test database error recovery strategies"""

    @pytest.fixture
    def error_handler(self):
        return BiologicalMemoryErrorHandler()

    def test_connection_failure_recovery(self, error_handler):
        """Test recovery from connection failures"""
        conn_error = psycopg2.OperationalError("could not connect to server")

        recovery_strategy = error_handler._handle_database_error(conn_error, {})

        assert recovery_strategy["action"] == "retry_with_exponential_backoff"
        assert recovery_strategy["fallback"] == "use_cached_data"
        assert recovery_strategy["max_retries"] == 5
        assert recovery_strategy["initial_delay"] == 2.0

    def test_lock_contention_recovery(self, error_handler):
        """Test recovery from database lock contention"""
        lock_error = Exception("could not obtain lock on relation")

        recovery_strategy = error_handler._handle_database_error(lock_error, {})

        assert recovery_strategy["action"] == "retry_with_jitter"
        assert recovery_strategy["jitter_range"] == (0.1, 2.0)
        assert "contention" in recovery_strategy["biological_note"]

    def test_timeout_recovery_with_biological_context(self, error_handler):
        """Test timeout recovery considering biological constraints"""
        timeout_error = Exception("query timeout")
        context = {"biological_context": {"memory_stage": "consolidation"}}

        recovery_strategy = error_handler._handle_database_error(timeout_error, context)

        assert recovery_strategy["action"] == "increase_timeout_and_retry"
        assert recovery_strategy["timeout_multiplier"] == 1.5
        assert "biological timing" in recovery_strategy["biological_note"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
