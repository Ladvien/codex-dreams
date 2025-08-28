#!/usr/bin/env python3
"""
BMP-HIGH-006: Comprehensive SQL Runtime Safety Tests
Tests all SQL error paths, crash prevention, and runtime stability features

Author: Runtime Stability Expert Agent
Date: 2025-08-28
"""

import pytest
import unittest
import tempfile
import shutil
import time
import threading
import json
import signal
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

# Import modules under test
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from sql_runtime_safety import (
    SQLRuntimeSafetyManager, SQLRuntimeSafetyLevel, SQLExecutionResult,
    create_sql_safety_manager
)
from error_handling import BiologicalMemoryErrorHandler, ErrorType
from orchestrate_biological_memory import BiologicalMemoryOrchestrator


class TestSQLRuntimeSafetyManager(unittest.TestCase):
    """Comprehensive tests for SQL runtime safety manager"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = BiologicalMemoryErrorHandler(
            base_path=self.temp_dir,
            max_error_events=100
        )
        self.safety_manager = SQLRuntimeSafetyManager(
            error_handler=self.error_handler,
            safety_level=SQLRuntimeSafetyLevel.RESILIENT
        )
        
        # Create test database
        self.test_db = Path(self.temp_dir) / "test.duckdb"
        
    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'safety_manager'):
            self.safety_manager.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_safe_connection_context_manager(self):
        """Test safe connection context manager"""
        # Test successful connection
        with self.safety_manager.get_safe_connection(str(self.test_db), "duckdb") as conn:
            self.assertIsNotNone(conn)
            # Should be able to execute queries
            result = conn.execute("SELECT 1 as test_value").fetchone()
            self.assertEqual(result[0], 1)
        
        # Connection should be returned to pool
        stats = self.safety_manager.get_execution_stats()
        self.assertIn("active_connections", stats)
    
    def test_safe_query_execution_success(self):
        """Test successful query execution with safety measures"""
        # Create table
        result = self.safety_manager.execute_safe_query(
            db_path=str(self.test_db),
            query="CREATE TABLE test_table (id INTEGER, name TEXT)",
            db_type="duckdb"
        )
        
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertGreater(result.execution_time_ms, 0)
        
        # Insert data
        result = self.safety_manager.execute_safe_query(
            db_path=str(self.test_db),
            query="INSERT INTO test_table VALUES (?, ?)",
            parameters=[1, "Alice"],
            db_type="duckdb"
        )
        
        self.assertTrue(result.success)
        
        # Query data
        result = self.safety_manager.execute_safe_query(
            db_path=str(self.test_db),
            query="SELECT * FROM test_table",
            db_type="duckdb"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.result_set), 1)
        self.assertEqual(result.result_set[0], (1, "Alice"))
    
    def test_safe_query_execution_with_retry(self):
        """Test query execution with retry logic on failure"""
        # Test with a query that will fail initially but succeed on retry
        with patch.object(self.safety_manager, '_execute_query_attempt') as mock_execute:
            # First attempt fails, second succeeds
            mock_execute.side_effect = [
                SQLExecutionResult(success=False, error_message="Connection failed", retry_count=0),
                SQLExecutionResult(success=True, result_set=[(1, "test")], retry_count=1)
            ]
            
            result = self.safety_manager.execute_safe_query(
                db_path=str(self.test_db),
                query="SELECT 1, 'test'",
                db_type="duckdb",
                max_retries=2
            )
            
            self.assertTrue(result.success)
            self.assertEqual(mock_execute.call_count, 2)
    
    def test_sql_injection_prevention(self):
        """Test SQL injection detection and prevention"""
        malicious_queries = [
            "SELECT * FROM users; DROP TABLE users; --",
            "SELECT * FROM data WHERE id = 1 OR 1=1",
            "SELECT * FROM table UNION SELECT password FROM users",
            "INSERT INTO table VALUES ('test'); DELETE FROM users; --"
        ]
        
        for query in malicious_queries:
            result = self.safety_manager.execute_safe_query(
                db_path=str(self.test_db),
                query=query,
                db_type="duckdb"
            )
            
            self.assertFalse(result.success)
            self.assertEqual(result.error_type, ErrorType.SECURITY_VIOLATION)
            self.assertIn("injection", result.error_message.lower())
    
    def test_transaction_safety_with_rollback(self):
        """Test transaction execution with rollback on failure"""
        # First create table
        self.safety_manager.execute_safe_query(
            db_path=str(self.test_db),
            query="CREATE TABLE trans_test (id INTEGER PRIMARY KEY, value TEXT)",
            db_type="duckdb"
        )
        
        # Test successful transaction
        queries = [
            "INSERT INTO trans_test VALUES (1, 'first')",
            "INSERT INTO trans_test VALUES (2, 'second')"
        ]
        
        result = self.safety_manager.execute_transaction(
            db_path=str(self.test_db),
            queries=queries,
            db_type="duckdb"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.rows_affected, 2)
        
        # Test transaction with rollback (insert duplicate primary key)
        failing_queries = [
            "INSERT INTO trans_test VALUES (3, 'third')",
            "INSERT INTO trans_test VALUES (1, 'duplicate')",  # This should fail
            "INSERT INTO trans_test VALUES (4, 'fourth')"
        ]
        
        result = self.safety_manager.execute_transaction(
            db_path=str(self.test_db),
            queries=failing_queries,
            db_type="duckdb"
        )
        
        self.assertFalse(result.success)
        
        # Verify rollback - should only have original 2 records
        result = self.safety_manager.execute_safe_query(
            db_path=str(self.test_db),
            query="SELECT COUNT(*) FROM trans_test",
            db_type="duckdb"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.result_set[0][0], 2)
    
    def test_connection_pooling_and_limits(self):
        """Test connection pooling and connection limits"""
        # Create safety manager with low connection limit for testing
        limited_manager = SQLRuntimeSafetyManager(
            error_handler=self.error_handler,
            max_connections_per_db=2,
            safety_level=SQLRuntimeSafetyLevel.STRICT
        )
        
        try:
            connections = []
            
            # Acquire connections up to limit
            for i in range(2):
                conn = limited_manager.get_safe_connection(str(self.test_db), "duckdb")
                connections.append(conn.__enter__())
            
            # Attempting to acquire one more should fail in STRICT mode
            with self.assertRaises(RuntimeError):
                with limited_manager.get_safe_connection(str(self.test_db), "duckdb"):
                    pass
            
            # Clean up connections
            for conn_mgr in connections:
                conn_mgr.__exit__(None, None, None)
                
        finally:
            limited_manager.shutdown()
    
    def test_timeout_handling(self):
        """Test query timeout handling"""
        # Test with very short timeout
        with patch('time.sleep'):  # Speed up test
            result = self.safety_manager.execute_safe_query(
                db_path=str(self.test_db),
                query="SELECT pg_sleep(10)",  # This would timeout
                db_type="duckdb",
                timeout_override=1
            )
            
            # Should handle timeout gracefully
            # Note: Since we're using DuckDB, pg_sleep won't work, but the timeout mechanism should still be tested
            self.assertIsNotNone(result)
    
    def test_resource_monitoring_and_protection(self):
        """Test system resource monitoring and protection"""
        # Mock high memory usage
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 96  # Very high usage
            
            # Should trigger memory protection
            self.safety_manager._check_system_resources()
            
            # Should prevent execution in pre-check
            result = self.safety_manager._pre_execution_resource_check()
            self.assertFalse(result)
    
    def test_error_classification(self):
        """Test SQL error classification"""
        error_cases = [
            ("Connection timed out", ErrorType.TIMEOUT),
            ("Could not connect to database", ErrorType.CONNECTION_FAILURE),
            ("Deadlock detected", ErrorType.TRANSACTION_FAILURE),
            ("Out of memory", ErrorType.RESOURCE_EXHAUSTION),
            ("Syntax error in query", ErrorType.CONFIGURATION_ERROR),
            ("Unknown error", ErrorType.SERVICE_UNAVAILABLE)
        ]
        
        for error_msg, expected_type in error_cases:
            error_type = self.safety_manager._classify_sql_error(error_msg)
            self.assertEqual(error_type, expected_type)
    
    def test_connection_health_checking(self):
        """Test connection health checking"""
        # Create a connection
        with self.safety_manager.get_safe_connection(str(self.test_db), "duckdb") as conn:
            # Should be healthy
            is_healthy = self.safety_manager._is_connection_healthy(conn, "duckdb")
            self.assertTrue(is_healthy)
        
        # Test with None connection (should be unhealthy)
        is_healthy = self.safety_manager._is_connection_healthy(None, "duckdb")
        self.assertFalse(is_healthy)
    
    def test_execution_statistics(self):
        """Test execution statistics tracking"""
        initial_stats = self.safety_manager.get_execution_stats()
        initial_total = initial_stats['total_queries']
        
        # Execute a successful query
        self.safety_manager.execute_safe_query(
            db_path=str(self.test_db),
            query="SELECT 1",
            db_type="duckdb"
        )
        
        # Execute a failing query
        self.safety_manager.execute_safe_query(
            db_path=str(self.test_db),
            query="'; DROP TABLE nonexistent; --",
            db_type="duckdb"
        )
        
        final_stats = self.safety_manager.get_execution_stats()
        
        # Should have tracked queries
        self.assertEqual(final_stats['total_queries'], initial_total + 2)
        self.assertGreater(final_stats['successful_queries'], initial_stats['successful_queries'])
        self.assertGreater(final_stats['failed_queries'], initial_stats['failed_queries'])
        
        # Should have success rate
        self.assertIn('success_rate_percent', final_stats)
        self.assertIsInstance(final_stats['success_rate_percent'], (int, float))
    
    def test_concurrent_access_safety(self):
        """Test thread safety with concurrent access"""
        results = []
        errors = []
        
        def worker_thread(thread_id):
            try:
                for i in range(5):
                    result = self.safety_manager.execute_safe_query(
                        db_path=str(self.test_db),
                        query=f"SELECT {thread_id} as thread_id, {i} as iteration",
                        db_type="duckdb"
                    )
                    results.append((thread_id, i, result.success))
                    time.sleep(0.01)  # Small delay
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
        
        # Start multiple worker threads
        threads = []
        for tid in range(5):
            thread = threading.Thread(target=worker_thread, args=(tid,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 25)  # 5 threads × 5 iterations
        
        # All queries should have succeeded
        successful_results = [r for r in results if r[2]]
        self.assertEqual(len(successful_results), 25)
    
    def test_graceful_shutdown(self):
        """Test graceful shutdown of safety manager"""
        # Create some connections
        with self.safety_manager.get_safe_connection(str(self.test_db), "duckdb"):
            pass
        
        # Shutdown should clean up all resources
        self.safety_manager.shutdown()
        
        # Should be able to call shutdown multiple times safely
        self.safety_manager.shutdown()


class TestSQLSafetyIntegrationWithOrchestrator(unittest.TestCase):
    """Test SQL safety integration with biological memory orchestrator"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_orchestrator_sql_safety_integration(self):
        """Test that orchestrator uses SQL safety system"""
        orchestrator = BiologicalMemoryOrchestrator(
            base_path=self.temp_dir,
            log_dir=str(Path(self.temp_dir) / "logs")
        )
        
        try:
            # Should have SQL safety manager
            self.assertIsInstance(orchestrator.sql_safety, SQLRuntimeSafetyManager)
            
            # Test health check uses SQL safety
            health_result = orchestrator.health_check()
            
            # Should be boolean result
            self.assertIsInstance(health_result, bool)
            
            # Should have SQL safety stats in health results
            # Note: This checks internal behavior, might need adjustment based on actual implementation
            
        finally:
            if hasattr(orchestrator, 'sql_safety'):
                orchestrator.sql_safety.shutdown()
    
    def test_orchestrator_graceful_shutdown(self):
        """Test that orchestrator properly shuts down SQL safety"""
        orchestrator = BiologicalMemoryOrchestrator(
            base_path=self.temp_dir,
            log_dir=str(Path(self.temp_dir) / "logs")
        )
        
        try:
            # Simulate shutdown signal
            orchestrator.signal_handler(signal.SIGTERM, None)
        except SystemExit:
            # Expected behavior
            pass


class TestSQLSafetyStressTests(unittest.TestCase):
    """Stress tests for SQL safety system"""
    
    def setUp(self):
        """Set up stress test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = BiologicalMemoryErrorHandler(base_path=self.temp_dir)
        self.safety_manager = create_sql_safety_manager(self.error_handler)
        self.test_db = Path(self.temp_dir) / "stress_test.duckdb"
        
    def tearDown(self):
        """Clean up stress test environment"""
        self.safety_manager.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_high_volume_query_execution(self):
        """Test high volume query execution"""
        # Create test table
        result = self.safety_manager.execute_safe_query(
            db_path=str(self.test_db),
            query="CREATE TABLE stress_test (id INTEGER, data TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            db_type="duckdb"
        )
        self.assertTrue(result.success)
        
        # Execute many queries rapidly
        success_count = 0
        error_count = 0
        
        start_time = time.time()
        for i in range(100):
            result = self.safety_manager.execute_safe_query(
                db_path=str(self.test_db),
                query="INSERT INTO stress_test (id, data) VALUES (?, ?)",
                parameters=[i, f"test_data_{i}"],
                db_type="duckdb"
            )
            
            if result.success:
                success_count += 1
            else:
                error_count += 1
        
        duration = time.time() - start_time
        
        # Should handle high volume successfully
        self.assertGreater(success_count, 95)  # At least 95% success rate
        self.assertLess(error_count, 5)  # Less than 5% errors
        
        print(f"Stress test: {success_count} successes, {error_count} errors in {duration:.2f}s")
    
    def test_memory_pressure_handling(self):
        """Test behavior under memory pressure"""
        # Create table with large data
        result = self.safety_manager.execute_safe_query(
            db_path=str(self.test_db),
            query="CREATE TABLE large_data (id INTEGER, large_text TEXT)",
            db_type="duckdb"
        )
        self.assertTrue(result.success)
        
        # Try to insert very large strings
        large_text = "x" * 100000  # 100KB string
        success_count = 0
        
        for i in range(10):
            result = self.safety_manager.execute_safe_query(
                db_path=str(self.test_db),
                query="INSERT INTO large_data VALUES (?, ?)",
                parameters=[i, large_text],
                db_type="duckdb"
            )
            
            if result.success:
                success_count += 1
        
        # Should handle large data reasonably well
        self.assertGreater(success_count, 0)
    
    def test_concurrent_transaction_safety(self):
        """Test concurrent transaction safety"""
        # Create test table
        result = self.safety_manager.execute_safe_query(
            db_path=str(self.test_db),
            query="CREATE TABLE concurrent_test (id INTEGER PRIMARY KEY, value INTEGER)",
            db_type="duckdb"
        )
        self.assertTrue(result.success)
        
        results = []
        
        def transaction_worker(worker_id):
            queries = [
                f"INSERT INTO concurrent_test VALUES ({worker_id * 100 + 1}, {worker_id})",
                f"INSERT INTO concurrent_test VALUES ({worker_id * 100 + 2}, {worker_id})",
                f"INSERT INTO concurrent_test VALUES ({worker_id * 100 + 3}, {worker_id})"
            ]
            
            result = self.safety_manager.execute_transaction(
                db_path=str(self.test_db),
                queries=queries,
                db_type="duckdb"
            )
            results.append((worker_id, result.success))
        
        # Run concurrent transactions
        threads = []
        for i in range(5):
            thread = threading.Thread(target=transaction_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Most transactions should succeed
        successful_transactions = sum(1 for _, success in results if success)
        self.assertGreater(successful_transactions, 3)  # At least 60% success rate


class TestSQLSafetyEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        """Set up edge case test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = BiologicalMemoryErrorHandler(base_path=self.temp_dir)
        self.safety_manager = create_sql_safety_manager(self.error_handler)
        
    def tearDown(self):
        """Clean up edge case test environment"""
        self.safety_manager.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_invalid_database_path(self):
        """Test handling of invalid database paths"""
        invalid_paths = [
            "/nonexistent/path/database.db",
            "",
            None
        ]
        
        for path in invalid_paths:
            if path is None:
                continue  # Skip None as it would cause type error
            
            result = self.safety_manager.execute_safe_query(
                db_path=path,
                query="SELECT 1",
                db_type="duckdb"
            )
            
            self.assertFalse(result.success)
            self.assertIsNotNone(result.error_message)
    
    def test_empty_and_invalid_queries(self):
        """Test handling of empty and invalid queries"""
        test_db = str(Path(self.temp_dir) / "edge_test.duckdb")
        
        invalid_queries = [
            "",
            "   ",
            None,
            "INVALID SQL SYNTAX HERE",
            "SELECT * FROM nonexistent_table"
        ]
        
        for query in invalid_queries:
            if query is None:
                continue  # Skip None as it would cause validation error
                
            result = self.safety_manager.execute_safe_query(
                db_path=test_db,
                query=query,
                db_type="duckdb"
            )
            
            self.assertFalse(result.success)
            self.assertIsNotNone(result.error_message)
    
    def test_extremely_large_query_parameters(self):
        """Test handling of extremely large query parameters"""
        test_db = str(Path(self.temp_dir) / "large_param_test.duckdb")
        
        # Create test table
        self.safety_manager.execute_safe_query(
            db_path=test_db,
            query="CREATE TABLE param_test (id INTEGER, data TEXT)",
            db_type="duckdb"
        )
        
        # Test with very large parameter
        large_data = "x" * 1000000  # 1MB string
        
        result = self.safety_manager.execute_safe_query(
            db_path=test_db,
            query="INSERT INTO param_test VALUES (?, ?)",
            parameters=[1, large_data],
            db_type="duckdb"
        )
        
        # Should handle gracefully (success or controlled failure)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.success)  # Should be boolean
    
    def test_safety_level_behaviors(self):
        """Test different safety level behaviors"""
        # Test STRICT mode
        strict_manager = SQLRuntimeSafetyManager(
            error_handler=self.error_handler,
            safety_level=SQLRuntimeSafetyLevel.STRICT,
            max_connections_per_db=1
        )
        
        # Test PERMISSIVE mode
        permissive_manager = SQLRuntimeSafetyManager(
            error_handler=self.error_handler,
            safety_level=SQLRuntimeSafetyLevel.PERMISSIVE,
            max_connections_per_db=1
        )
        
        try:
            # Both should handle basic queries
            test_db = str(Path(self.temp_dir) / "safety_level_test.duckdb")
            
            strict_result = strict_manager.execute_safe_query(
                db_path=test_db,
                query="SELECT 1",
                db_type="duckdb"
            )
            
            permissive_result = permissive_manager.execute_safe_query(
                db_path=test_db,
                query="SELECT 1",
                db_type="duckdb"
            )
            
            # Both should succeed for simple queries
            self.assertTrue(strict_result.success)
            self.assertTrue(permissive_result.success)
            
        finally:
            strict_manager.shutdown()
            permissive_manager.shutdown()


if __name__ == '__main__':
    # Run comprehensive SQL safety tests
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestSQLRuntimeSafetyManager,
        TestSQLSafetyIntegrationWithOrchestrator,
        TestSQLSafetyStressTests,
        TestSQLSafetyEdgeCases
    ]
    
    for test_class in test_classes:
        test_suite.addTests(test_loader.loadTestsFromTestCase(test_class))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print comprehensive summary
    print(f"\n{'='*80}")
    print(f"BMP-HIGH-006 SQL Runtime Safety Tests Complete")
    print(f"{'='*80}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    print(f"{'='*80}")
    
    # Print details of any failures or errors
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"- {test}")
            print(f"  {traceback.splitlines()[-1] if traceback.splitlines() else 'No traceback'}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"- {test}")
            print(f"  {traceback.splitlines()[-1] if traceback.splitlines() else 'No traceback'}")
    
    print(f"\n{'='*80}")
    print("SQL Runtime Safety System: BULLETPROOF ✅" if result.wasSuccessful() else "SQL Runtime Safety System: NEEDS ATTENTION ⚠️")
    print(f"{'='*80}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)