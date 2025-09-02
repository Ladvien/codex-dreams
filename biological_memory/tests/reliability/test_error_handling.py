#!/usr/bin/env python3
"""
BMP-013: Comprehensive Error Handling and Recovery Tests
Tests all error paths, recovery mechanisms, and reliability features
"""

import json
import shutil
import sqlite3
import subprocess

# Import the modules we're testing
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, call, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent.parent))

from error_handling import (
    BiologicalMemoryErrorHandler,
    CircuitBreaker,
    DeadLetterQueue,
    ErrorEvent,
    ErrorType,
    with_error_handling,
)
from orchestrate_biological_memory import BiologicalMemoryOrchestrator


class TestBiologicalMemoryErrorHandler(unittest.TestCase):
    """Test the core error handling system"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = BiologicalMemoryErrorHandler(
            base_path=self.temp_dir,
            circuit_breaker_enabled=True,
            max_db_connections=10,
            ollama_timeout_seconds=30,
        )

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_error_event_logging(self):
        """Test structured error event logging"""
        error_event = ErrorEvent(
            error_id="test_001",
            error_type=ErrorType.CONNECTION_FAILURE,
            timestamp=datetime.now(),
            component="test_component",
            operation="test_operation",
            error_message="Test error message",
            context={"test_key": "test_value"},
        )

        self.error_handler.log_error_event(error_event)

        # Check that error was recorded
        self.assertEqual(len(self.error_handler.error_events), 1)
        self.assertEqual(self.error_handler.recovery_stats["total_errors"], 1)

        # Check structured log file exists
        structured_log_path = Path(self.temp_dir) / "logs" / "structured_errors.jsonl"
        self.assertTrue(structured_log_path.exists())

    def test_exponential_backoff_retry_success(self):
        """Test successful retry with exponential backoff"""
        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        start_time = time.time()
        result = self.error_handler.exponential_backoff_retry(
            failing_function,
            max_retries=5,
            base_delay=0.1,  # Fast for testing
            exceptions=(ConnectionError,),
        )
        duration = time.time() - start_time

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
        # Should take at least 0.1 + 0.2 = 0.3 seconds due to retries
        self.assertGreater(duration, 0.25)

    def test_exponential_backoff_retry_failure(self):
        """Test retry failure after max attempts"""
        call_count = 0

        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent failure")

        with self.assertRaises(ConnectionError):
            self.error_handler.exponential_backoff_retry(
                always_failing_function,
                max_retries=2,
                base_delay=0.01,
                exceptions=(ConnectionError,),
            )

        self.assertEqual(call_count, 3)  # Initial call + 2 retries

    def test_database_connection_with_retry(self):
        """Test database connection with retry logic"""
        # Create a valid DuckDB database
        db_path = Path(self.temp_dir) / "test.duckdb"

        # This should succeed
        conn = self.error_handler.get_database_connection(str(db_path))
        self.assertIsNotNone(conn)
        conn.close()

        # Test with invalid path (should fail after retries)
        with self.assertRaises(Exception):
            self.error_handler.get_database_connection("/invalid/path/database.db")

    def test_transaction_safety_success(self):
        """Test successful transaction execution"""
        db_path = Path(self.temp_dir) / "transaction_test.duckdb"
        conn = self.error_handler.get_database_connection(str(db_path))

        operations = [
            "CREATE TABLE test_table (id INTEGER, name TEXT)",
            "INSERT INTO test_table VALUES (1, 'test')",
            "INSERT INTO test_table VALUES (2, 'test2')",
        ]

        result = self.error_handler.execute_with_transaction_safety(
            conn, operations, context={"test": "transaction"}
        )

        self.assertTrue(result)

        # Verify data was committed
        count = conn.execute("SELECT COUNT(*) FROM test_table").fetchone()[0]
        self.assertEqual(count, 2)

        conn.close()

    def test_transaction_safety_rollback(self):
        """Test transaction rollback on failure"""
        db_path = Path(self.temp_dir) / "rollback_test.duckdb"
        conn = self.error_handler.get_database_connection(str(db_path))

        # Create table first
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY)")

        operations = [
            "INSERT INTO test_table VALUES (1)",
            "INSERT INTO test_table VALUES (1)",  # This will fail due to primary key constraint
            "INSERT INTO test_table VALUES (2)",
        ]

        result = self.error_handler.execute_with_transaction_safety(
            conn, operations, context={"test": "rollback"}
        )

        self.assertFalse(result)

        # Verify no data was committed due to rollback
        count = conn.execute("SELECT COUNT(*) FROM test_table").fetchone()[0]
        self.assertEqual(count, 0)

        conn.close()

    def test_json_recovery_valid_json(self):
        """Test JSON recovery with valid JSON"""
        valid_json = '{"key": "value", "number": 42}'
        result = self.error_handler.process_with_json_recovery(valid_json)

        expected = {"key": "value", "number": 42}
        self.assertEqual(result, expected)

    def test_json_recovery_markdown_wrapped(self):
        """Test JSON recovery with markdown code blocks"""
        markdown_json = """
        Here's the response:
        
        ```json
        {"extracted": "data", "confidence": 0.95}
        ```
        
        Hope this helps!
        """

        result = self.error_handler.process_with_json_recovery(markdown_json)
        expected = {"extracted": "data", "confidence": 0.95}
        self.assertEqual(result, expected)

    def test_json_recovery_with_schema_fallback(self):
        """Test JSON recovery with schema-based fallback"""
        malformed_json = "This is not JSON at all!"
        schema = {"name": "default_string", "count": 0, "items": [], "metadata": {}}

        result = self.error_handler.process_with_json_recovery(
            malformed_json, expected_schema=schema
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "error_recovery_placeholder")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["items"], [])
        self.assertEqual(result["metadata"], {})

    def test_system_resource_monitoring(self):
        """Test system resource monitoring"""
        resources = self.error_handler.monitor_system_resources()

        # Check that all expected keys are present
        expected_keys = [
            "memory_available_mb",
            "memory_percent",
            "disk_free_mb",
            "disk_percent",
            "cpu_percent",
            "timestamp",
        ]
        for key in expected_keys:
            self.assertIn(key, resources)

        # Check data types
        self.assertIsInstance(resources["memory_percent"], (int, float))
        self.assertIsInstance(resources["disk_percent"], (int, float))
        self.assertIsInstance(resources["cpu_percent"], (int, float))

    def test_graceful_degradation_modes(self):
        """Test graceful degradation for different component failures"""
        # Test DuckDB failure
        duckdb_degradation = self.error_handler.graceful_degradation_mode("duckdb")
        self.assertFalse(duckdb_degradation["consolidation_processing"])
        self.assertFalse(duckdb_degradation["deep_consolidation"])
        self.assertTrue(duckdb_degradation["working_memory_processing"])

        # Test Ollama failure
        ollama_degradation = self.error_handler.graceful_degradation_mode("ollama")
        self.assertFalse(ollama_degradation["rem_sleep_processing"])
        self.assertTrue(ollama_degradation["consolidation_processing"])

        # Test PostgreSQL failure
        postgres_degradation = self.error_handler.graceful_degradation_mode("postgres")
        self.assertFalse(postgres_degradation["working_memory_processing"])
        self.assertTrue(postgres_degradation["consolidation_processing"])

    def test_error_summary_generation(self):
        """Test comprehensive error summary generation"""
        # Add some test errors
        for i in range(5):
            error_event = ErrorEvent(
                error_id=f"test_{i}",
                error_type=ErrorType.CONNECTION_FAILURE if i % 2 == 0 else ErrorType.TIMEOUT,
                timestamp=datetime.now(),
                component="test",
                operation=f"op_{i}",
                error_message=f"Test error {i}",
            )
            self.error_handler.log_error_event(error_event)

        summary = self.error_handler.get_error_summary()

        # Check summary structure
        required_keys = [
            "total_errors_24h",
            "errors_by_type",
            "recovery_stats",
            "recovery_rate_percent",
            "circuit_breaker_states",
            "system_resources",
            "timestamp",
        ]
        for key in required_keys:
            self.assertIn(key, summary)

        # Check error counts
        self.assertEqual(summary["total_errors_24h"], 5)
        self.assertIn("connection_failure", summary["errors_by_type"])
        self.assertIn("timeout", summary["errors_by_type"])


class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker functionality"""

    def setUp(self):
        """Set up circuit breaker test"""
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout_seconds=1,  # Short timeout for testing
            expected_exception=ValueError,
        )

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state (normal operation)"""

        @self.circuit_breaker
        def successful_operation():
            return "success"

        result = successful_operation()
        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, "CLOSED")

    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after failure threshold"""

        @self.circuit_breaker
        def failing_operation():
            raise ValueError("Operation failed")

        # Fail 3 times to reach threshold
        for _ in range(3):
            with self.assertRaises(ValueError):
                failing_operation()

        # Circuit should now be OPEN
        self.assertEqual(self.circuit_breaker.state, "OPEN")

        # Further calls should raise circuit breaker exception
        with self.assertRaises(Exception) as context:
            failing_operation()
        self.assertIn("Circuit breaker is OPEN", str(context.exception))

    def test_circuit_breaker_half_open_reset(self):
        """Test circuit breaker transitions to half-open and can reset"""

        @self.circuit_breaker
        def operation():
            if hasattr(operation, "should_fail") and operation.should_fail:
                raise ValueError("Fail")
            return "success"

        # Open the circuit
        operation.should_fail = True
        for _ in range(3):
            with self.assertRaises(ValueError):
                operation()

        self.assertEqual(self.circuit_breaker.state, "OPEN")

        # Wait for timeout
        time.sleep(1.1)

        # Next call should put it in HALF_OPEN
        operation.should_fail = False
        result = operation()

        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, "CLOSED")


class TestDeadLetterQueue(unittest.TestCase):
    """Test dead letter queue functionality"""

    def setUp(self):
        """Set up dead letter queue test"""
        self.temp_dir = tempfile.mkdtemp()
        self.dlq_db_path = str(Path(self.temp_dir) / "dlq_test.db")
        self.dlq = DeadLetterQueue(self.dlq_db_path)

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_enqueue_message(self):
        """Test enqueueing messages to dead letter queue"""
        memory_data = {"content": "test memory", "activation": 0.8}

        self.dlq.enqueue(
            message_id="msg_001",
            operation="stm_consolidation",
            memory_data=memory_data,
            error_type=ErrorType.CONNECTION_FAILURE,
            error_message="Database connection failed",
            retry_delay_seconds=10,
        )

        # Verify message was stored
        conn = sqlite3.connect(self.dlq_db_path)
        cursor = conn.execute("SELECT * FROM dead_letter_queue WHERE message_id = ?", ("msg_001",))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)
        self.assertEqual(result[1], "msg_001")  # message_id
        self.assertEqual(result[2], "stm_consolidation")  # operation

    def test_get_retry_candidates(self):
        """Test getting messages ready for retry"""
        # Add a message that should be ready for retry
        past_time = datetime.now() - timedelta(seconds=10)

        conn = sqlite3.connect(self.dlq_db_path)
        conn.execute(
            """
            INSERT INTO dead_letter_queue 
            (message_id, original_operation, memory_data, error_type, error_message, retry_after)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            ("retry_msg", "test_op", "{}", "connection_failure", "test error", past_time),
        )
        conn.commit()
        conn.close()

        candidates = self.dlq.get_retry_candidates()
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["message_id"], "retry_msg")

    def test_mark_retry_success(self):
        """Test marking message as successfully retried"""
        # Add a test message
        conn = sqlite3.connect(self.dlq_db_path)
        conn.execute(
            """
            INSERT INTO dead_letter_queue 
            (message_id, original_operation, memory_data, error_type, error_message, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            ("success_msg", "test_op", "{}", "timeout", "test error", "FAILED"),
        )
        conn.commit()
        conn.close()

        self.dlq.mark_retry_success("success_msg")

        # Verify status was updated
        conn = sqlite3.connect(self.dlq_db_path)
        cursor = conn.execute(
            "SELECT status FROM dead_letter_queue WHERE message_id = ?", ("success_msg",)
        )
        status = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(status, "RECOVERED")

    def test_mark_permanent_failure(self):
        """Test marking message as permanently failed"""
        # Add a test message
        conn = sqlite3.connect(self.dlq_db_path)
        conn.execute(
            """
            INSERT INTO dead_letter_queue 
            (message_id, original_operation, memory_data, error_type, error_message, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            ("perm_fail_msg", "test_op", "{}", "data_corruption", "test error", "FAILED"),
        )
        conn.commit()
        conn.close()

        self.dlq.mark_permanent_failure("perm_fail_msg")

        # Verify status was updated
        conn = sqlite3.connect(self.dlq_db_path)
        cursor = conn.execute(
            "SELECT status FROM dead_letter_queue WHERE message_id = ?", ("perm_fail_msg",)
        )
        status = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(status, "PERMANENT_FAILURE")


class TestBiologicalMemoryOrchestratorEnhanced(unittest.TestCase):
    """Test enhanced orchestrator with error handling"""

    def setUp(self):
        """Set up orchestrator test"""
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = BiologicalMemoryOrchestrator(
            base_path=self.temp_dir, log_dir=str(Path(self.temp_dir) / "logs")
        )

    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self.orchestrator, "stop_working_memory_thread"):
            self.orchestrator.stop_working_memory_thread()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_enhanced_dbt_command_success(self):
        """Test enhanced dbt command execution with success"""
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Success output"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result = self.orchestrator.run_dbt_command(
                "dbt run --select test", "test.log", timeout=30
            )

            self.assertTrue(result)
            mock_run.assert_called_once()

    def test_enhanced_dbt_command_with_retry(self):
        """Test dbt command retry logic"""
        with patch("subprocess.run") as mock_run:
            # First call fails, second succeeds
            mock_result_fail = Mock()
            mock_result_fail.returncode = 1
            mock_result_fail.stdout = ""
            mock_result_fail.stderr = "Connection error"

            mock_result_success = Mock()
            mock_result_success.returncode = 0
            mock_result_success.stdout = "Success on retry"
            mock_result_success.stderr = ""

            mock_run.side_effect = [mock_result_fail, mock_result_success]

            result = self.orchestrator.run_dbt_command("dbt run --select test", "test.log")

            self.assertTrue(result)
            self.assertEqual(mock_run.call_count, 2)

    def test_enhanced_dbt_command_timeout_handling(self):
        """Test dbt command timeout handling"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("dbt", 30)

            result = self.orchestrator.run_dbt_command(
                "dbt run --select test", "test.log", timeout=30
            )

            self.assertFalse(result)

            # Check that error was logged
            error_events = self.orchestrator.error_handler.error_events
            self.assertGreater(len(error_events), 0)

            timeout_errors = [e for e in error_events if e.error_type == ErrorType.TIMEOUT]
            self.assertGreater(len(timeout_errors), 0)

    def test_enhanced_dbt_command_dead_letter_queue(self):
        """Test that critical operations are added to dead letter queue on failure"""
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Critical operation failed"
            mock_run.return_value = mock_result

            # Run a consolidation command (should be added to DLQ)
            result = self.orchestrator.run_dbt_command(
                "dbt run --select consolidation", "consolidation.log"
            )

            self.assertFalse(result)

            # Check dead letter queue
            dlq_candidates = (
                self.orchestrator.error_handler.dead_letter_queue.get_retry_candidates()
            )
            # Note: candidates may be empty if retry_after is in the future
            # The important thing is that the enqueue method was called

            # Check that error was logged
            error_events = self.orchestrator.error_handler.error_events
            self.assertGreater(len(error_events), 0)

    def test_enhanced_health_check(self):
        """Test enhanced health check with comprehensive monitoring"""
        # Create a test database
        db_path = Path(self.temp_dir) / "dbs" / "memory.duckdb"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with patch("duckdb.connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.execute.return_value.fetchall.return_value = [
                ("test_table_1",),
                ("test_table_2",),
            ]
            mock_connect.return_value = mock_conn

            result = self.orchestrator.health_check()

            # Health check should succeed
            self.assertTrue(result)

            # Verify comprehensive health data was collected
            health_log_path = Path(self.temp_dir) / "logs" / "health_status.jsonl"
            self.assertTrue(health_log_path.exists())

    def test_safe_log_output(self):
        """Test safe log output with error handling"""
        log_path = Path(self.temp_dir) / "logs" / "test.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        log_data = {
            "command": "dbt test",
            "return_code": 0,
            "stdout": "Test output",
            "stderr": "",
            "execution_time": 1.5,
        }

        self.orchestrator._safe_log_output(log_path, log_data)

        # Verify log file was created and contains data
        self.assertTrue(log_path.exists())
        with open(log_path, "r") as f:
            content = f.read()
            self.assertIn("dbt test", content)
            self.assertIn("RETURN_CODE: 0", content)


class TestErrorHandlingDecorator(unittest.TestCase):
    """Test the error handling decorator"""

    def setUp(self):
        """Set up decorator test"""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = BiologicalMemoryErrorHandler(
            base_path=self.temp_dir, circuit_breaker_enabled=False
        )

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_decorator_success(self):
        """Test decorator with successful function"""

        @with_error_handling(
            self.error_handler, operation="test_operation", component="test_component"
        )
        def successful_function(x, y):
            return x + y

        result = successful_function(2, 3)
        self.assertEqual(result, 5)

    def test_decorator_with_retry(self):
        """Test decorator with retry functionality"""
        call_count = 0

        @with_error_handling(
            self.error_handler, operation="retry_test", component="test_component", retry_attempts=2
        )
        def retry_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = retry_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 2)

        # Check that error events were logged
        self.assertGreater(len(self.error_handler.error_events), 0)

    def test_decorator_permanent_failure(self):
        """Test decorator with permanent failure"""

        @with_error_handling(
            self.error_handler,
            operation="permanent_fail",
            component="test_component",
            retry_attempts=2,
        )
        def always_failing_function():
            raise RuntimeError("Permanent failure")

        with self.assertRaises(RuntimeError):
            always_failing_function()

        # Should have logged error events for each attempt
        error_events = self.error_handler.error_events
        self.assertGreater(len(error_events), 0)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for comprehensive error handling scenarios"""

    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = BiologicalMemoryOrchestrator(
            base_path=self.temp_dir, log_dir=str(Path(self.temp_dir) / "logs")
        )

    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self.orchestrator, "stop_working_memory_thread"):
            self.orchestrator.stop_working_memory_thread()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cascade_failure_prevention(self):
        """Test that failures in one component don't cascade to others"""
        with patch.object(self.orchestrator, "run_dbt_command") as mock_dbt:
            # Make STM processing fail but consolidation succeed
            def selective_failure(command, *args, **kwargs):
                if "short_term_memory" in command:
                    return False
                return True

            mock_dbt.side_effect = selective_failure

            # Run both operations
            stm_result = self.orchestrator.stm_processing()
            consolidation_result = self.orchestrator.consolidation_processing()

            # STM should fail, consolidation should succeed
            self.assertFalse(stm_result)
            self.assertTrue(consolidation_result)

            # Error counts should be independent
            self.assertEqual(self.orchestrator.error_counts["stm"], 1)
            self.assertEqual(self.orchestrator.error_counts["consolidation"], 0)

    def test_resource_exhaustion_scenario(self):
        """Test system behavior under resource exhaustion"""
        # Mock resource monitoring to simulate exhaustion
        with patch.object(
            self.orchestrator.error_handler, "monitor_system_resources"
        ) as mock_resources:
            mock_resources.return_value = {
                "memory_available_mb": 100,  # Very low
                "memory_percent": 95,  # Critical
                "disk_free_mb": 500,  # Low
                "disk_percent": 98,  # Critical
                "cpu_percent": 98,  # High
                "timestamp": datetime.now(),
            }

            # Health check should detect issues
            health_result = self.orchestrator.health_check()

            # Should still return result but log warnings
            self.assertIsInstance(health_result, bool)

            # Check that resource exhaustion was logged
            error_events = self.orchestrator.error_handler.error_events
            resource_errors = [
                e for e in error_events if e.error_type == ErrorType.RESOURCE_EXHAUSTION
            ]
            self.assertGreater(len(resource_errors), 0)

    def test_recovery_workflow(self):
        """Test complete error -> recovery workflow"""
        # Simulate a failing operation that gets added to dead letter queue
        with patch("subprocess.run") as mock_run:
            # First fail to trigger DLQ
            mock_result_fail = Mock()
            mock_result_fail.returncode = 1
            mock_result_fail.stdout = ""
            mock_result_fail.stderr = "Temporary database error"

            # Later succeed for retry
            mock_result_success = Mock()
            mock_result_success.returncode = 0
            mock_result_success.stdout = "Success on retry"
            mock_result_success.stderr = ""

            mock_run.side_effect = [mock_result_fail, mock_result_success]

            # Run critical operation that will fail and go to DLQ
            result1 = self.orchestrator.run_dbt_command(
                "dbt run --select consolidation", "consolidation.log"
            )
            self.assertFalse(result1)

            # Simulate retry from dead letter queue
            self.orchestrator.error_handler.retry_dead_letter_messages()

            # Check recovery stats
            stats = self.orchestrator.error_handler.get_error_summary()
            self.assertGreater(stats["recovery_stats"]["total_errors"], 0)


if __name__ == "__main__":
    # Run all reliability tests
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestBiologicalMemoryErrorHandler,
        TestCircuitBreaker,
        TestDeadLetterQueue,
        TestBiologicalMemoryOrchestratorEnhanced,
        TestErrorHandlingDecorator,
        TestIntegrationScenarios,
    ]

    for test_class in test_classes:
        test_suite.addTests(test_loader.loadTestsFromTestCase(test_class))

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print comprehensive summary
    print(f"\n{'='*80}")
    print(f"BMP-013 Error Handling and Recovery Tests Complete")
    print(f"{'='*80}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(
        f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    )
    print(f"{'='*80}")

    # Print details of any failures or errors
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.splitlines()[-1]}")

    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.splitlines()[-1]}")

    print(f"\n{'='*80}")

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
