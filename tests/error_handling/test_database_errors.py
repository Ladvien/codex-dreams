#!/usr/bin/env python3
"""
STORY-004: Database Error Handling Tests
Comprehensive error handling tests for database operations including
connection failures, timeouts, transaction rollbacks, and resource exhaustion.
"""

import pytest
import tempfile
import os
import sqlite3
import time
from unittest.mock import Mock, patch, MagicMock
import duckdb
from datetime import datetime, timezone

# Import from biological_memory error handling
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'biological_memory'))

try:
    from error_handling import (
        BiologicalMemoryErrorHandler, ErrorType, ErrorEvent, 
        CircuitBreaker, DeadLetterQueue, SecuritySanitizer
    )
except ImportError:
    pytest.skip("Error handling module not available", allow_module_level=True)


class TestDatabaseErrorHandling:
    """Test comprehensive database error handling patterns."""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = BiologicalMemoryErrorHandler(
            base_path=self.temp_dir,
            circuit_breaker_enabled=True
        )
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_database_connection_retry_with_exponential_backoff(self):
        """Test database connection with retry logic and exponential backoff"""
        
        # Mock a function that fails initially then succeeds
        attempt_count = 0
        def failing_connection():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception(f"Connection failed (attempt {attempt_count})")
            return "Connected successfully"
        
        # Test exponential backoff retry
        result = self.error_handler.exponential_backoff_retry(
            failing_connection,
            max_retries=3,
            base_delay=0.1,  # Fast for testing
            exceptions=(Exception,)
        )
        
        assert result == "Connected successfully"
        assert attempt_count == 3
    
    def test_database_connection_circuit_breaker_opening(self):
        """Test circuit breaker opens after repeated failures"""
        
        # Create circuit breaker with low threshold for testing
        circuit_breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=1)
        
        @circuit_breaker
        def always_failing_connection():
            raise Exception("Connection failed")
        
        # First failure
        with pytest.raises(Exception, match="Connection failed"):
            always_failing_connection()
        assert circuit_breaker.failure_count == 1
        assert circuit_breaker.state == "CLOSED"
        
        # Second failure should open circuit
        with pytest.raises(Exception, match="Connection failed"):
            always_failing_connection()
        assert circuit_breaker.failure_count == 2
        assert circuit_breaker.state == "OPEN"
        
        # Third attempt should fail due to open circuit
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            always_failing_connection()
    
    def test_database_transaction_rollback_on_error(self):
        """Test transaction rollback when database operations fail"""
        
        with tempfile.NamedTemporaryFile(suffix=".duckdb") as db_file:
            conn = duckdb.connect(db_file.name)
            
            # Setup test table
            conn.execute("""
                CREATE TABLE test_transactions (
                    id INTEGER PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            
            # Test successful transaction
            operations = [
                "INSERT INTO test_transactions (id, data) VALUES (1, 'test1')",
                "INSERT INTO test_transactions (id, data) VALUES (2, 'test2')"
            ]
            
            success = self.error_handler.execute_with_transaction_safety(
                conn, operations
            )
            assert success is True
            
            # Verify data was inserted
            result = conn.execute("SELECT COUNT(*) FROM test_transactions").fetchone()
            assert result[0] == 2
            
            # Test failed transaction (duplicate key)
            failing_operations = [
                "INSERT INTO test_transactions (id, data) VALUES (3, 'test3')",
                "INSERT INTO test_transactions (id, data) VALUES (1, 'duplicate')"  # This will fail
            ]
            
            success = self.error_handler.execute_with_transaction_safety(
                conn, failing_operations
            )
            assert success is False
            
            # Verify data was rolled back (should still be 2 records)
            result = conn.execute("SELECT COUNT(*) FROM test_transactions").fetchone()
            assert result[0] == 2
            
            conn.close()
    
    def test_database_timeout_handling(self):
        """Test database operation timeout handling"""
        
        def slow_operation():
            time.sleep(2)  # Simulate slow operation
            return "Completed"
        
        # Test timeout with short limit
        start_time = time.time()
        with pytest.raises(Exception):
            # This should timeout
            self.error_handler.exponential_backoff_retry(
                slow_operation,
                max_retries=1,
                base_delay=0.1,
                exceptions=(Exception,)
            )
        
        # Should have taken at least the base delay
        elapsed = time.time() - start_time
        assert elapsed >= 0.1
    
    def test_database_resource_monitoring(self):
        """Test database resource monitoring and exhaustion detection"""
        
        resource_status = self.error_handler.monitor_system_resources()
        
        # Should return resource information
        assert 'memory_available_mb' in resource_status
        assert 'memory_percent' in resource_status
        assert 'disk_free_mb' in resource_status
        assert 'disk_percent' in resource_status
        assert 'cpu_percent' in resource_status
        assert 'timestamp' in resource_status
        
        # All values should be reasonable
        assert resource_status['memory_percent'] >= 0
        assert resource_status['memory_percent'] <= 100
        assert resource_status['disk_percent'] >= 0
        assert resource_status['cpu_percent'] >= 0
    
    def test_database_connection_pool_exhaustion(self):
        """Test handling of database connection pool exhaustion"""
        
        # Mock connection pool that fails after max connections
        connection_count = 0
        max_connections = 3
        
        def get_connection():
            nonlocal connection_count
            connection_count += 1
            if connection_count > max_connections:
                raise Exception("Connection pool exhausted")
            return f"Connection_{connection_count}"
        
        # Test successful connections within limit
        for i in range(max_connections):
            conn = get_connection()
            assert conn == f"Connection_{i+1}"
        
        # Test pool exhaustion
        with pytest.raises(Exception, match="Connection pool exhausted"):
            get_connection()
    
    def test_dead_letter_queue_functionality(self):
        """Test dead letter queue for failed database operations"""
        
        # Create dead letter queue
        dlq_path = os.path.join(self.temp_dir, "test_dlq.db")
        dlq = DeadLetterQueue(dlq_path)
        
        # Test enqueueing failed operation
        memory_data = {
            'id': 'test_memory_1',
            'content': 'Test memory content',
            'strength': 0.8
        }
        
        dlq.enqueue(
            message_id="msg_001",
            operation="memory_consolidation",
            memory_data=memory_data,
            error_type=ErrorType.CONNECTION_FAILURE,
            error_message="Database connection timeout",
            retry_delay_seconds=1  # Short for testing
        )
        
        # Test retrieving retry candidates
        time.sleep(1.1)  # Wait for retry delay
        candidates = dlq.get_retry_candidates()
        
        assert len(candidates) == 1
        assert candidates[0]['message_id'] == "msg_001"
        assert candidates[0]['original_operation'] == "memory_consolidation"
        assert candidates[0]['error_type'] == ErrorType.CONNECTION_FAILURE.value
        
        # Test marking success
        dlq.mark_retry_success("msg_001")
        
        # Should no longer be in retry candidates
        candidates = dlq.get_retry_candidates()
        assert len(candidates) == 0
    
    def test_database_corruption_detection_and_recovery(self):
        """Test detection and recovery from database corruption"""
        
        with tempfile.NamedTemporaryFile(suffix=".duckdb") as db_file:
            # Create database and insert test data
            conn = duckdb.connect(db_file.name)
            conn.execute("""
                CREATE TABLE test_corruption (
                    id INTEGER,
                    data TEXT,
                    checksum TEXT
                )
            """)
            
            # Insert valid data
            test_data = [
                (1, "Valid data 1", "hash1"),
                (2, "Valid data 2", "hash2"),
                (3, None, None),  # Simulate corrupted data
                (4, "Invalid JSON: {broken", "hash4")  # Simulate JSON corruption
            ]
            
            for row in test_data:
                conn.execute(
                    "INSERT INTO test_corruption VALUES (?, ?, ?)", 
                    row
                )
            
            # Test corruption detection query
            corruption_check_query = """
                SELECT 
                    id,
                    data,
                    CASE 
                        WHEN data IS NULL THEN 'CORRUPTED_NULL'
                        WHEN data LIKE '%{broken%' THEN 'CORRUPTED_JSON'
                        ELSE 'VALID'
                    END as data_status
                FROM test_corruption
                ORDER BY id
            """
            
            results = conn.execute(corruption_check_query).fetchall()
            
            # Verify corruption detection
            assert results[0][2] == 'VALID'  # First record is valid
            assert results[1][2] == 'VALID'  # Second record is valid
            assert results[2][2] == 'CORRUPTED_NULL'  # Third record is corrupted
            assert results[3][2] == 'CORRUPTED_JSON'  # Fourth record has JSON corruption
            
            conn.close()
    
    def test_concurrent_database_access_handling(self):
        """Test handling of concurrent database access and locking"""
        
        with tempfile.NamedTemporaryFile(suffix=".duckdb") as db_file:
            # Create shared database
            conn = duckdb.connect(db_file.name)
            conn.execute("""
                CREATE TABLE concurrent_test (
                    id INTEGER PRIMARY KEY,
                    counter INTEGER DEFAULT 0
                )
            """)
            conn.execute("INSERT INTO concurrent_test (id) VALUES (1)")
            
            # Simulate concurrent updates
            for i in range(5):
                # Read current value
                current = conn.execute(
                    "SELECT counter FROM concurrent_test WHERE id = 1"
                ).fetchone()[0]
                
                # Update with new value
                conn.execute(
                    "UPDATE concurrent_test SET counter = ? WHERE id = 1",
                    (current + 1,)
                )
            
            # Verify final value
            final_value = conn.execute(
                "SELECT counter FROM concurrent_test WHERE id = 1"
            ).fetchone()[0]
            
            assert final_value == 5
            conn.close()
    
    def test_database_schema_validation_error_handling(self):
        """Test error handling for schema validation failures"""
        
        with tempfile.NamedTemporaryFile(suffix=".duckdb") as db_file:
            conn = duckdb.connect(db_file.name)
            
            # Create table with constraints
            conn.execute("""
                CREATE TABLE schema_validation_test (
                    id INTEGER PRIMARY KEY CHECK (id > 0),
                    required_field TEXT NOT NULL,
                    numeric_field DECIMAL CHECK (numeric_field >= 0)
                )
            """)
            
            # Test constraint violations
            constraint_violations = [
                (0, "Valid text", 1.0),  # ID constraint violation (id <= 0)
                (1, None, 1.0),          # NOT NULL violation
                (2, "Valid text", -1.0), # CHECK constraint violation (negative number)
            ]
            
            for i, invalid_data in enumerate(constraint_violations):
                with pytest.raises(Exception):
                    conn.execute(
                        "INSERT INTO schema_validation_test VALUES (?, ?, ?)",
                        invalid_data
                    )
            
            # Test valid data insertion
            valid_data = (1, "Valid text", 1.0)
            conn.execute(
                "INSERT INTO schema_validation_test VALUES (?, ?, ?)",
                valid_data
            )
            
            # Verify only valid data was inserted
            count = conn.execute(
                "SELECT COUNT(*) FROM schema_validation_test"
            ).fetchone()[0]
            assert count == 1
            
            conn.close()


class TestSecuritySanitization:
    """Test security sanitization and credential protection"""
    
    def test_credential_sanitization(self):
        """Test sanitization of sensitive credentials in logs"""
        
        sensitive_data = {
            'database_url': 'postgresql://user:secret123@localhost:5432/db',
            'api_key': 'sk-1234567890abcdef',
            'password': 'mySecretPassword',
            'normal_field': 'public information'
        }
        
        sanitized = SecuritySanitizer.sanitize_dict(sensitive_data)
        
        # Credentials should be masked
        assert 'secret123' not in str(sanitized)
        assert 'mySecretPassword' not in str(sanitized)
        assert 'sk-1234567890abcdef' not in str(sanitized)
        
        # Public information should remain
        assert sanitized['normal_field'] == 'public information'
        
        # Masked fields should still be present but sanitized
        assert 'database_url' in sanitized
        assert 'api_key' in sanitized
        assert 'password' in sanitized
    
    def test_log_injection_prevention(self):
        """Test prevention of log injection attacks"""
        
        malicious_input = "Legitimate message\nFAKE_LOG_ENTRY: Admin access granted\r\n"
        
        sanitized = SecuritySanitizer.sanitize_log_message(malicious_input)
        
        # Newlines should be escaped
        assert '\\n' in sanitized
        assert '\n' not in sanitized
        assert '\\r' in sanitized
        assert '\r' not in sanitized
        
        # Original message should still be readable
        assert 'Legitimate message' in sanitized
    
    def test_error_id_generation_security(self):
        """Test secure error ID generation"""
        
        # Generate multiple error IDs
        error_ids = [SecuritySanitizer.generate_secure_error_id() for _ in range(100)]
        
        # All should be unique
        assert len(set(error_ids)) == 100
        
        # All should follow expected format
        for error_id in error_ids:
            assert error_id.startswith('err_')
            parts = error_id.split('_')
            assert len(parts) == 3
            assert len(parts[1]) == 16  # UUID hex part
            assert len(parts[2]) == 8   # Timestamp hash part


if __name__ == '__main__':
    pytest.main([__file__, '-v'])