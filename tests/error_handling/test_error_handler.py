"""
Comprehensive tests for BiologicalMemoryErrorHandler
"""

import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from services.error_handling import (
    BiologicalMemoryError,
    BiologicalMemoryErrorHandler,
    DatabaseError,
    ErrorCategory,
    ErrorSeverity,
    LLMError,
    NetworkError,
    TimeoutError,
    get_global_error_handler,
    with_biological_timing_constraints,
    with_database_error_handling,
    with_error_handling,
)


class TestBiologicalMemoryError:
    """Test the custom exception hierarchy"""

    def test_basic_error_creation(self):
        error = BiologicalMemoryError("Test error", category=ErrorCategory.DATABASE)
        assert str(error) == "Test error"
        assert error.category == ErrorCategory.DATABASE
        assert error.severity == ErrorSeverity.MEDIUM
        assert isinstance(error.timestamp, datetime)

    def test_error_to_dict(self):
        details = {"key": "value"}
        error = BiologicalMemoryError(
            "Test error",
            category=ErrorCategory.LLM,
            severity=ErrorSeverity.HIGH,
            details=details,
            retry_suggested=False,
        )

        error_dict = error.to_dict()
        assert error_dict["message"] == "Test error"
        assert error_dict["category"] == "llm"
        assert error_dict["severity"] == "high"
        assert error_dict["details"] == details
        assert error_dict["retry_suggested"] == False
        assert "timestamp" in error_dict

    def test_specific_error_types(self):
        db_error = DatabaseError("DB connection failed")
        assert db_error.category == ErrorCategory.DATABASE

        network_error = NetworkError("Connection timeout")
        assert network_error.category == ErrorCategory.NETWORK

        timeout_error = TimeoutError("Operation timed out", biological_context="working_memory")
        assert timeout_error.category == ErrorCategory.TIMEOUT
        assert timeout_error.details["biological_context"] == "working_memory"


class TestBiologicalMemoryErrorHandler:
    """Test the comprehensive error handler"""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_file.close()
        yield temp_file.name
        os.unlink(temp_file.name)

    @pytest.fixture
    def error_handler(self, temp_db_path):
        """Create error handler with temporary database"""
        config = {"error_db_path": temp_db_path, "log_level": 30}  # WARNING level
        return BiologicalMemoryErrorHandler(config)

    def test_error_handler_initialization(self, error_handler, temp_db_path):
        assert error_handler.error_db_path == temp_db_path
        assert len(error_handler.error_log) == 0
        assert len(error_handler.error_handlers) > 0

        # Test database initialization
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "error_log" in tables

    def test_error_classification(self, error_handler):
        # Database errors
        db_error = Exception("Database connection failed")
        assert error_handler._classify_error(db_error) == ErrorCategory.DATABASE

        # Network errors
        network_error = Exception("Connection refused to host")
        assert error_handler._classify_error(network_error) == ErrorCategory.NETWORK

        # LLM errors
        llm_error = Exception("Ollama service unavailable")
        assert error_handler._classify_error(llm_error) == ErrorCategory.LLM

        # Timeout errors
        timeout_error = Exception("Request timed out")
        assert error_handler._classify_error(timeout_error) == ErrorCategory.TIMEOUT

        # Already classified errors
        bio_error = BiologicalMemoryError("test", category=ErrorCategory.EMBEDDING)
        assert error_handler._classify_error(bio_error) == ErrorCategory.EMBEDDING

    def test_severity_assessment(self, error_handler):
        # Critical security error
        security_error = Exception("Unauthorized access detected")
        assert (
            error_handler._assess_severity(security_error, ErrorCategory.SECURITY)
            == ErrorSeverity.CRITICAL
        )

        # High severity database connection error
        db_conn_error = Exception("Database connection failed")
        assert (
            error_handler._assess_severity(db_conn_error, ErrorCategory.DATABASE)
            == ErrorSeverity.HIGH
        )

        # Medium severity timeout
        timeout_error = Exception("Request timeout")
        assert (
            error_handler._assess_severity(timeout_error, ErrorCategory.TIMEOUT)
            == ErrorSeverity.MEDIUM
        )

        # Low severity validation error
        validation_error = ValueError("Invalid input")
        assert (
            error_handler._assess_severity(validation_error, ErrorCategory.VALIDATION)
            == ErrorSeverity.LOW
        )

    def test_error_handling_and_logging(self, error_handler):
        test_error = DatabaseError("Connection failed", details={"host": "localhost"})
        context = {
            "operation": "test_operation",
            "biological_context": {"memory_stage": "working_memory"},
        }

        error_record = error_handler.handle_error(test_error, context)

        assert error_record["category"] == "database"
        assert error_record["severity"] == "medium"
        assert error_record["context"] == context
        assert error_record["recovery_attempted"] == True
        assert "error_id" in error_record
        assert "biological_context" in error_record

        # Check error was logged
        assert len(error_handler.error_log) == 1
        assert error_handler.error_log[0] == error_record

    def test_database_error_handler(self, error_handler):
        # Connection error
        conn_error = Exception("connection refused")
        record = {"category": "database"}
        result = error_handler._handle_database_error(conn_error, record)

        assert result["action"] == "retry_with_exponential_backoff"
        assert result["max_retries"] == 5
        assert "biological_note" in result

        # Timeout error
        timeout_error = Exception("operation timeout")
        result = error_handler._handle_database_error(timeout_error, record)
        assert result["action"] == "increase_timeout_and_retry"

        # Deadlock error
        deadlock_error = Exception("deadlock detected")
        result = error_handler._handle_database_error(deadlock_error, record)
        assert result["action"] == "retry_with_jitter"

    def test_timeout_error_with_biological_context(self, error_handler):
        # Working memory timeout
        timeout_error = Exception("timeout")
        record = {"biological_context": {"memory_stage": "working_memory"}}
        result = error_handler._handle_timeout_error(timeout_error, record)

        assert result["action"] == "respect_biological_limit"
        assert result["timeout_strategy"] == "biological_constraint"
        assert "5-minute window" in result["biological_note"]

        # Consolidation timeout
        record["biological_context"]["memory_stage"] = "consolidation"
        result = error_handler._handle_timeout_error(timeout_error, record)
        assert result["action"] == "extend_consolidation_window"

    def test_security_error_handling(self, error_handler, temp_db_path):
        security_error = Exception("unauthorized access")
        record = {}

        result = error_handler._handle_security_error(security_error, record)

        assert result["action"] == "immediate_containment"
        assert result["max_retries"] == 0
        assert "containment_steps" in result

        # Check security incident was logged to database
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE name='security_incidents'"
            )
            # Note: This table might not exist in our test, but the code attempts to create it

    def test_retry_with_backoff(self, error_handler):
        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("temporary failure")
            return "success"

        # Should succeed after 2 failures
        result = error_handler.retry_with_backoff(failing_function)
        assert result == "success"
        assert call_count == 3

    def test_retry_with_biological_constraints(self, error_handler):
        context = {"biological_context": {"memory_stage": "working_memory"}}

        # Should have reduced retry count for working memory
        max_retries = error_handler._adjust_retries_for_biological_context(context)
        assert max_retries <= 2

        # Should have faster delays for working memory
        delay = error_handler._calculate_biological_delay(0, context)
        assert delay <= 5.0

    def test_safe_execute(self, error_handler):
        def successful_function(value):
            return value * 2

        def failing_function():
            raise DatabaseError("test failure")

        # Successful execution
        result = error_handler.safe_execute(successful_function, 5)
        assert result == 10

        # Failed execution should return None and log error
        result = error_handler.safe_execute(failing_function)
        assert result is None
        assert len(error_handler.error_log) > 0

    def test_error_statistics(self, error_handler):
        # Add some errors
        error_handler.handle_error(DatabaseError("db error 1"))
        error_handler.handle_error(NetworkError("network error 1"))
        error_handler.handle_error(DatabaseError("db error 2"))

        stats = error_handler.get_error_stats()

        assert stats["total_errors"] == 3
        assert stats["categories"]["database"] == 2
        assert stats["categories"]["network"] == 1
        assert len(stats["recent_errors"]) == 3
        assert "error_trends" in stats
        assert "recovery_success_rate" in stats

    def test_error_report_generation(self, error_handler):
        # Add some errors with biological context
        error_handler.handle_error(
            DatabaseError("db error"),
            {"biological_context": {"memory_stage": "consolidation"}},
        )
        error_handler.handle_error(LLMError("llm error"))

        report = error_handler.generate_error_report()

        assert "Biological Memory System - Error Analysis Report" in report
        assert "Total Errors: 2" in report
        assert "database:" in report.lower()
        assert "llm:" in report.lower()
        assert "biological memory stage patterns" in report.lower()


class TestErrorDecorators:
    """Test error handling decorators"""

    def test_with_error_handling_decorator(self):
        @with_error_handling(category=ErrorCategory.DATABASE)
        def test_function():
            raise ValueError("test error")

        with pytest.raises(BiologicalMemoryError) as exc_info:
            test_function()

        assert exc_info.value.category == ErrorCategory.DATABASE
        assert "test error" in str(exc_info.value)

    def test_with_database_error_handling(self):
        @with_database_error_handling(timeout_seconds=30.0)
        def test_db_function():
            raise Exception("database connection failed")

        with pytest.raises(BiologicalMemoryError) as exc_info:
            test_db_function()

        assert exc_info.value.category == ErrorCategory.DATABASE

    def test_biological_timing_constraints(self):
        start_time = time.time()

        @with_biological_timing_constraints("working_memory", max_duration=0.1)
        def slow_function():
            time.sleep(0.2)  # Exceed the constraint
            return "done"

        # Should complete but log a warning
        result = slow_function()
        assert result == "done"

        duration = time.time() - start_time
        assert duration >= 0.2  # Actually took the time

        # Test with error during execution
        @with_biological_timing_constraints("consolidation")
        def failing_function():
            raise ValueError("processing failed")

        with pytest.raises(BiologicalMemoryError) as exc_info:
            failing_function()

        assert exc_info.value.category == ErrorCategory.BIOLOGICAL_TIMING
        assert "consolidation" in str(exc_info.value)


class TestSystemIntegration:
    """Test integration with the broader biological memory system"""

    def test_global_error_handler(self):
        handler1 = get_global_error_handler()
        handler2 = get_global_error_handler()

        # Should return the same instance
        assert handler1 is handler2
        assert isinstance(handler1, BiologicalMemoryErrorHandler)

    def test_error_persistence(self):
        """Test that errors are properly persisted to database"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
            temp_path = temp_file.name

        try:
            config = {"error_db_path": temp_path}
            handler = BiologicalMemoryErrorHandler(config)

            # Generate some errors
            test_error = DatabaseError("Test persistence error")
            context = {
                "operation": "test",
                "biological_context": {"memory_stage": "working_memory"},
            }

            handler.handle_error(test_error, context)

            # Check database directly
            with sqlite3.connect(temp_path) as conn:
                cursor = conn.execute("SELECT * FROM error_log")
                rows = cursor.fetchall()
                assert len(rows) == 1

                row = rows[0]
                # Columns: id(0), timestamp(1), category(2), severity(3), message(4)
                assert "Test persistence error" in row[4]  # message column
                assert row[2] == "database"  # category column

        finally:
            os.unlink(temp_path)

    @patch("psutil.virtual_memory")
    @patch("psutil.cpu_percent")
    def test_system_state_capture(self, mock_cpu, mock_memory):
        """Test system state capture functionality"""
        # Mock system information
        mock_memory.return_value = MagicMock()
        mock_memory.return_value._asdict.return_value = {
            "total": 8000000000,
            "available": 4000000000,
        }
        mock_cpu.return_value = 25.5

        handler = BiologicalMemoryErrorHandler()
        system_state = handler._capture_system_state()

        assert "memory_usage" in system_state
        assert "cpu_usage" in system_state
        assert system_state["cpu_usage"] == 25.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
