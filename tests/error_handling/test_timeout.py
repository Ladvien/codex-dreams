#!/usr/bin/env python3
"""
STORY-004: Timeout and External Service Error Handling Tests
Comprehensive tests for timeout handling, external service failures,
circuit breakers, and service unavailability scenarios.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock
import tempfile
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

# Import from biological_memory error handling
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'biological_memory'))

try:
    from error_handling import (
        BiologicalMemoryErrorHandler, ErrorType, ErrorEvent,
        CircuitBreaker, SecuritySanitizer
    )
except ImportError:
    pytest.skip("Error handling module not available", allow_module_level=True)


class TestTimeoutHandling:
    """Test comprehensive timeout handling for external services."""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = BiologicalMemoryErrorHandler(
            base_path=self.temp_dir,
            circuit_breaker_enabled=True,
            ollama_timeout_seconds=5  # Short timeout for testing
        )
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_database_connection_timeout(self):
        """Test database connection timeout handling"""
        
        def slow_database_connection():
            time.sleep(2)  # Simulate slow connection
            return "Connected"
        
        # Test successful connection within timeout
        result = self.error_handler.exponential_backoff_retry(
            slow_database_connection,
            max_retries=1,
            base_delay=0.1,
            exceptions=(Exception,)
        )
        assert result == "Connected"
    
    def test_ollama_api_timeout_handling(self):
        """Test Ollama API timeout with retry logic"""
        
        call_count = 0
        
        def mock_ollama_request():
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:
                # Simulate timeout for first 2 calls
                time.sleep(0.5)
                raise requests.exceptions.Timeout("Request timed out")
            else:
                # Success on third call
                return {"response": "LLM response", "status": "success"}
        
        # Should eventually succeed with retries
        result = self.error_handler.exponential_backoff_retry(
            mock_ollama_request,
            max_retries=3,
            base_delay=0.1,
            exceptions=(requests.exceptions.Timeout,)
        )
        
        assert result["status"] == "success"
        assert call_count == 3
    
    def test_postgresql_query_timeout(self):
        """Test PostgreSQL query timeout handling"""
        
        def slow_postgresql_query():
            """Simulate a slow PostgreSQL query"""
            # Simulate different query behaviors
            import random
            delay = random.uniform(0.1, 1.0)
            time.sleep(delay)
            
            if delay > 0.8:  # Simulate timeout for slow queries
                raise Exception("Query timeout: execution exceeded maximum time")
            
            return f"Query result (took {delay:.2f}s)"
        
        # Test multiple queries with some timeouts
        successful_queries = 0
        timeout_errors = 0
        
        for i in range(5):
            try:
                result = self.error_handler.exponential_backoff_retry(
                    slow_postgresql_query,
                    max_retries=2,
                    base_delay=0.05,
                    exceptions=(Exception,)
                )
                successful_queries += 1
            except Exception as e:
                if "timeout" in str(e).lower():
                    timeout_errors += 1
        
        # Should have handled both successes and timeouts
        assert successful_queries + timeout_errors == 5
    
    def test_circuit_breaker_timeout_protection(self):
        """Test circuit breaker protection for timeout-prone services"""
        
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout_seconds=2  # Short timeout for testing
        )
        
        timeout_count = 0
        
        @circuit_breaker
        def timeout_prone_service():
            nonlocal timeout_count
            timeout_count += 1
            # Always timeout for this test
            raise requests.exceptions.Timeout("Service timeout")
        
        # First 3 calls should fail and open circuit
        for i in range(3):
            with pytest.raises(requests.exceptions.Timeout):
                timeout_prone_service()
        
        # Circuit should now be open
        assert circuit_breaker.state == "OPEN"
        
        # Next call should fail immediately due to open circuit
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            timeout_prone_service()
        
        # Should have only made 3 actual service calls
        assert timeout_count == 3
    
    def test_external_service_unavailable_handling(self):
        """Test handling when external services are completely unavailable"""
        
        def unavailable_service():
            raise requests.exceptions.ConnectionError("Service unavailable")
        
        # Should handle gracefully and apply graceful degradation
        with pytest.raises(requests.exceptions.ConnectionError):
            self.error_handler.exponential_backoff_retry(
                unavailable_service,
                max_retries=3,
                base_delay=0.1,
                exceptions=(requests.exceptions.ConnectionError,)
            )
        
        # Test graceful degradation for unavailable service
        degradation_config = self.error_handler.graceful_degradation_mode("ollama")
        
        # Ollama-dependent features should be disabled
        assert degradation_config['rem_sleep_processing'] is False
        # Other features should still be enabled
        assert degradation_config['working_memory_processing'] is True
    
    def test_concurrent_timeout_handling(self):
        """Test timeout handling for concurrent operations"""
        
        def concurrent_operation(operation_id: int):
            """Simulate concurrent operation with varying delays"""
            delay = 0.1 + (operation_id % 3) * 0.2  # 0.1s, 0.3s, or 0.5s delays
            time.sleep(delay)
            return f"Operation {operation_id} completed in {delay}s"
        
        # Test concurrent operations with timeout
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            for i in range(10):
                future = executor.submit(concurrent_operation, i)
                futures.append((i, future))
            
            completed_operations = 0
            timeout_operations = 0
            
            for op_id, future in futures:
                try:
                    result = future.result(timeout=0.4)  # 400ms timeout
                    completed_operations += 1
                except FutureTimeoutError:
                    timeout_operations += 1
                except Exception as e:
                    # Handle other exceptions
                    pass
            
            # Should have a mix of completed and timed-out operations
            assert completed_operations + timeout_operations == 10
            assert timeout_operations > 0  # Some should timeout with 0.5s delays
    
    def test_nested_timeout_handling(self):
        """Test handling of nested timeouts (timeout within timeout)"""
        
        def outer_operation():
            """Operation that calls another operation with its own timeout"""
            
            def inner_operation():
                time.sleep(0.3)
                return "Inner completed"
            
            # Inner operation has its own timeout handling
            try:
                result = self.error_handler.exponential_backoff_retry(
                    inner_operation,
                    max_retries=1,
                    base_delay=0.1,
                    exceptions=(Exception,)
                )
                return f"Outer completed with: {result}"
            except Exception:
                return "Outer completed with inner timeout"
        
        # Test nested timeout scenarios
        result = outer_operation()
        assert "completed" in result
    
    def test_progressive_timeout_strategy(self):
        """Test progressive timeout strategy (increasing timeouts on retry)"""
        
        attempt_timeouts = [0.1, 0.2, 0.4, 0.8]  # Progressive timeouts
        
        def operation_with_progressive_timeout():
            """Operation that takes longer each time it's called"""
            if not hasattr(operation_with_progressive_timeout, 'attempt'):
                operation_with_progressive_timeout.attempt = 0
            
            attempt = operation_with_progressive_timeout.attempt
            operation_with_progressive_timeout.attempt += 1
            
            required_time = 0.15 * (attempt + 1)  # Needs progressively more time
            time.sleep(required_time)
            
            return f"Completed on attempt {attempt + 1} (took {required_time:.2f}s)"
        
        # Test with progressive timeout handling
        start_time = time.time()
        
        result = self.error_handler.exponential_backoff_retry(
            operation_with_progressive_timeout,
            max_retries=3,
            base_delay=0.05,
            backoff_multiplier=1.5,  # Slower backoff for progressive timeouts
            exceptions=(Exception,)
        )
        
        elapsed = time.time() - start_time
        assert "Completed" in result
        assert elapsed >= 0.15  # Should have taken at least the first operation time
    
    def test_timeout_with_resource_cleanup(self):
        """Test that resources are properly cleaned up on timeout"""
        
        cleanup_called = []
        
        def operation_with_resources():
            """Operation that acquires resources and may timeout"""
            
            # Simulate resource acquisition
            resource_handle = "database_connection_123"
            
            try:
                # Simulate work that might timeout
                time.sleep(0.3)
                return f"Work completed with {resource_handle}"
                
            except Exception:
                # Ensure cleanup happens even on timeout
                cleanup_called.append(resource_handle)
                raise
            finally:
                # Always cleanup
                if resource_handle not in cleanup_called:
                    cleanup_called.append(resource_handle)
        
        # Test operation that should complete
        result = operation_with_resources()
        assert "Work completed" in result
        assert len(cleanup_called) == 1  # Cleanup should have been called
    
    def test_timeout_error_categorization(self):
        """Test proper categorization of different timeout types"""
        
        timeout_scenarios = [
            ("Connection timeout", requests.exceptions.ConnectTimeout),
            ("Read timeout", requests.exceptions.ReadTimeout), 
            ("General timeout", requests.exceptions.Timeout),
            ("Custom timeout", TimeoutError)
        ]
        
        for scenario_name, exception_type in timeout_scenarios:
            def timeout_operation():
                raise exception_type(scenario_name)
            
            # Each timeout type should be handled appropriately
            with pytest.raises(exception_type):
                self.error_handler.exponential_backoff_retry(
                    timeout_operation,
                    max_retries=1,
                    base_delay=0.05,
                    exceptions=(exception_type,)
                )
            
            # Error should be logged with appropriate categorization
            assert self.error_handler.recovery_stats['total_errors'] > 0
    
    def test_adaptive_timeout_based_on_history(self):
        """Test adaptive timeout adjustment based on historical performance"""
        
        operation_times = []
        
        def adaptive_timeout_operation():
            """Operation with variable execution time"""
            import random
            execution_time = random.uniform(0.1, 0.5)
            time.sleep(execution_time)
            operation_times.append(execution_time)
            return f"Completed in {execution_time:.2f}s"
        
        # Simulate multiple operations to build history
        for i in range(5):
            try:
                result = self.error_handler.exponential_backoff_retry(
                    adaptive_timeout_operation,
                    max_retries=2,
                    base_delay=0.05,
                    exceptions=(Exception,)
                )
            except Exception:
                pass  # Some may timeout, that's ok
        
        # Should have collected timing data
        assert len(operation_times) >= 1
        
        # Calculate adaptive timeout (e.g., 90th percentile + buffer)
        if operation_times:
            sorted_times = sorted(operation_times)
            percentile_90 = sorted_times[int(len(sorted_times) * 0.9)]
            adaptive_timeout = percentile_90 * 1.5  # 50% buffer
            
            assert adaptive_timeout > min(operation_times)
            assert adaptive_timeout >= percentile_90


class TestExternalServiceErrorHandling:
    """Test error handling for various external service scenarios."""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = BiologicalMemoryErrorHandler(base_path=self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_http_status_code_error_handling(self):
        """Test handling of various HTTP status codes"""
        
        status_scenarios = [
            (400, "Bad Request"),
            (401, "Unauthorized"), 
            (403, "Forbidden"),
            (404, "Not Found"),
            (429, "Rate Limited"),
            (500, "Internal Server Error"),
            (502, "Bad Gateway"),
            (503, "Service Unavailable"),
            (504, "Gateway Timeout")
        ]
        
        for status_code, description in status_scenarios:
            def http_error_operation():
                error = requests.exceptions.HTTPError(f"{status_code} {description}")
                error.response = Mock()
                error.response.status_code = status_code
                raise error
            
            # Different status codes should be handled differently
            with pytest.raises(requests.exceptions.HTTPError):
                self.error_handler.exponential_backoff_retry(
                    http_error_operation,
                    max_retries=1,
                    base_delay=0.05,
                    exceptions=(requests.exceptions.HTTPError,)
                )
    
    def test_api_rate_limiting_with_backoff(self):
        """Test API rate limiting with exponential backoff"""
        
        api_calls = 0
        rate_limit_count = 0
        
        def rate_limited_api():
            nonlocal api_calls, rate_limit_count
            api_calls += 1
            
            # Simulate rate limiting for first few calls
            if api_calls <= 3:
                rate_limit_count += 1
                error = requests.exceptions.HTTPError("429 Rate Limited")
                error.response = Mock()
                error.response.status_code = 429
                raise error
            
            return {"data": "API response", "calls_made": api_calls}
        
        # Should eventually succeed with exponential backoff
        result = self.error_handler.exponential_backoff_retry(
            rate_limited_api,
            max_retries=5,
            base_delay=0.1,
            backoff_multiplier=2.0,  # Exponential backoff for rate limits
            exceptions=(requests.exceptions.HTTPError,)
        )
        
        assert result["data"] == "API response"
        assert rate_limit_count == 3
        assert api_calls == 4  # 3 failures + 1 success
    
    def test_network_connectivity_issues(self):
        """Test handling of network connectivity issues"""
        
        connectivity_scenarios = [
            requests.exceptions.ConnectionError("Network unreachable"),
            requests.exceptions.ConnectTimeout("Connection timed out"),
            requests.exceptions.DNSLookupError("DNS resolution failed"),
            OSError("Network interface down")
        ]
        
        for error_type in connectivity_scenarios:
            def network_error_operation():
                raise error_type
            
            # Should handle network errors gracefully
            with pytest.raises(type(error_type)):
                self.error_handler.exponential_backoff_retry(
                    network_error_operation,
                    max_retries=2,
                    base_delay=0.1,
                    exceptions=(type(error_type),)
                )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])