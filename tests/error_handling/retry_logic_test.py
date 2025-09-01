#!/usr/bin/env python3
"""
STORY-004: Retry Logic and Recovery Strategy Tests
Comprehensive tests for retry logic, exponential backoff, circuit breakers,
dead letter queues, and recovery strategies.
"""

import pytest
import time
import random
from unittest.mock import Mock, patch
import tempfile
from datetime import datetime, timezone

# Import from biological_memory error handling
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'biological_memory'))

try:
    from error_handling import (
        BiologicalMemoryErrorHandler, ErrorType, ErrorEvent,
        CircuitBreaker, DeadLetterQueue, RecoveryStrategy
    )
except ImportError:
    pytest.skip("Error handling module not available", allow_module_level=True)


class TestRetryLogic:
    """Test comprehensive retry logic and exponential backoff."""
    
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
    
    def test_exponential_backoff_timing(self):
        """Test exponential backoff timing progression"""
        
        attempt_times = []
        
        def failing_operation():
            attempt_times.append(time.time())
            raise Exception("Simulated failure")
        
        start_time = time.time()
        
        with pytest.raises(Exception):
            self.error_handler.exponential_backoff_retry(
                failing_operation,
                max_retries=4,
                base_delay=0.1,
                max_delay=2.0,
                backoff_multiplier=2.0,
                jitter=False  # Disable jitter for predictable timing
            )
        
        # Verify exponential backoff timing
        assert len(attempt_times) == 5  # Initial + 4 retries
        
        # Check intervals between attempts (approximate due to execution time)
        intervals = [attempt_times[i] - attempt_times[i-1] for i in range(1, len(attempt_times))]
        
        # Should follow exponential pattern: ~0.1, ~0.2, ~0.4, ~0.8 seconds
        assert 0.08 <= intervals[0] <= 0.15  # ~0.1s
        assert 0.15 <= intervals[1] <= 0.25  # ~0.2s
        assert 0.35 <= intervals[2] <= 0.45  # ~0.4s
        assert 0.75 <= intervals[3] <= 0.85  # ~0.8s
    
    def test_exponential_backoff_with_jitter(self):
        """Test exponential backoff with jitter to prevent thundering herd"""
        
        attempt_times = []
        
        def failing_operation():
            attempt_times.append(time.time())
            raise Exception("Simulated failure")
        
        # Run multiple retry sequences to test jitter
        jitter_variations = []
        
        for i in range(3):
            attempt_times.clear()
            
            with pytest.raises(Exception):
                self.error_handler.exponential_backoff_retry(
                    failing_operation,
                    max_retries=2,
                    base_delay=0.1,
                    jitter=True
                )
            
            if len(attempt_times) >= 2:
                first_interval = attempt_times[1] - attempt_times[0]
                jitter_variations.append(first_interval)
        
        # With jitter, intervals should vary
        if len(jitter_variations) >= 2:
            assert not all(abs(t - jitter_variations[0]) < 0.01 for t in jitter_variations)
    
    def test_retry_with_different_exception_types(self):
        """Test retry behavior with different exception types"""
        
        exception_scenarios = [
            (ConnectionError, "Connection failed", True),
            (TimeoutError, "Operation timed out", True),
            (ValueError, "Invalid input", False),  # Should not retry
            (KeyError, "Key not found", False),   # Should not retry
        ]
        
        for exception_type, message, should_retry in exception_scenarios:
            attempt_count = 0
            
            def operation_with_specific_error():
                nonlocal attempt_count
                attempt_count += 1
                raise exception_type(message)
            
            # Configure retry for network-related errors only
            retryable_exceptions = (ConnectionError, TimeoutError)
            
            with pytest.raises(exception_type):
                self.error_handler.exponential_backoff_retry(
                    operation_with_specific_error,
                    max_retries=3,
                    base_delay=0.05,
                    exceptions=retryable_exceptions
                )
            
            if should_retry:
                # Should have attempted multiple times
                assert attempt_count == 4  # Initial + 3 retries
            else:
                # Should have failed immediately
                assert attempt_count == 1
    
    def test_retry_with_partial_success_recovery(self):
        """Test retry logic with partial success and recovery"""
        
        attempt_count = 0
        partial_results = []
        
        def operation_with_partial_success():
            nonlocal attempt_count
            attempt_count += 1
            
            # Simulate partial progress
            partial_results.append(f"partial_result_{attempt_count}")
            
            if attempt_count <= 3:
                raise Exception(f"Partial failure on attempt {attempt_count}")
            
            # Success on 4th attempt, return accumulated results
            return {"results": partial_results, "final_attempt": attempt_count}
        
        result = self.error_handler.exponential_backoff_retry(
            operation_with_partial_success,
            max_retries=5,
            base_delay=0.05,
            exceptions=(Exception,)
        )
        
        assert result["final_attempt"] == 4
        assert len(result["results"]) == 4  # Should have accumulated partial results
    
    def test_retry_with_recovery_callback(self):
        """Test retry logic with recovery callbacks between attempts"""
        
        recovery_actions = []
        attempt_count = 0
        
        def failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count <= 2:
                raise Exception(f"Failure on attempt {attempt_count}")
            return f"Success on attempt {attempt_count}"
        
        def recovery_callback():
            """Callback to perform recovery actions between retries"""
            recovery_actions.append(f"recovery_attempt_{len(recovery_actions) + 1}")
            time.sleep(0.01)  # Simulate recovery work
        
        # Enhanced retry with recovery callback
        def enhanced_retry_operation():
            try:
                return failing_operation()
            except Exception as e:
                recovery_callback()
                raise e
        
        result = self.error_handler.exponential_backoff_retry(
            enhanced_retry_operation,
            max_retries=3,
            base_delay=0.05,
            exceptions=(Exception,)
        )
        
        assert result == "Success on attempt 3"
        assert len(recovery_actions) == 2  # Recovery called twice before success
    
    def test_retry_with_context_preservation(self):
        """Test that retry logic preserves operation context"""
        
        operation_context = {
            'user_id': 'test_user_123',
            'operation_id': 'op_456',
            'attempt_history': []
        }
        
        def context_aware_operation():
            # Update context with attempt information
            attempt_num = len(operation_context['attempt_history']) + 1
            operation_context['attempt_history'].append({
                'attempt': attempt_num,
                'timestamp': datetime.now(timezone.utc),
                'context_preserved': operation_context.get('user_id') is not None
            })
            
            if attempt_num <= 2:
                raise Exception(f"Context-aware failure {attempt_num}")
            
            return operation_context
        
        result = self.error_handler.exponential_backoff_retry(
            context_aware_operation,
            max_retries=3,
            base_delay=0.05,
            exceptions=(Exception,)
        )
        
        # Verify context was preserved across attempts
        assert result['user_id'] == 'test_user_123'
        assert result['operation_id'] == 'op_456'
        assert len(result['attempt_history']) == 3
        
        # All attempts should have preserved context
        for attempt_info in result['attempt_history']:
            assert attempt_info['context_preserved'] is True


class TestCircuitBreakerPatterns:
    """Test comprehensive circuit breaker patterns and behaviors."""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = BiologicalMemoryErrorHandler(base_path=self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_circuit_breaker_state_transitions(self):
        """Test circuit breaker state transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED"""
        
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            timeout_seconds=1,  # Short timeout for testing
            expected_exception=Exception
        )
        
        call_count = 0
        
        @circuit_breaker
        def monitored_service():
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:
                raise Exception(f"Service failure {call_count}")
            return f"Service success {call_count}"
        
        # Initial state should be CLOSED
        assert circuit_breaker.state == "CLOSED"
        
        # First failure
        with pytest.raises(Exception):
            monitored_service()
        assert circuit_breaker.state == "CLOSED"
        assert circuit_breaker.failure_count == 1
        
        # Second failure should open circuit
        with pytest.raises(Exception):
            monitored_service()
        assert circuit_breaker.state == "OPEN"
        assert circuit_breaker.failure_count == 2
        
        # Wait for timeout period
        time.sleep(1.1)
        
        # Next call should succeed and close circuit
        result = monitored_service()
        assert circuit_breaker.state == "CLOSED"
        assert circuit_breaker.failure_count == 0
        assert result == "Service success 3"
    
    def test_circuit_breaker_prevents_cascade_failures(self):
        """Test circuit breaker prevents cascade failures"""
        
        circuit_breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=10)
        
        service_calls = 0
        
        @circuit_breaker
        def cascading_failure_service():
            nonlocal service_calls
            service_calls += 1
            raise Exception("Service always fails")
        
        # Trigger circuit breaker opening
        for _ in range(2):
            with pytest.raises(Exception):
                cascading_failure_service()
        
        # Circuit should be open
        assert circuit_breaker.state == "OPEN"
        
        # Multiple subsequent calls should be rejected without calling service
        rejected_calls = 0
        for _ in range(5):
            with pytest.raises(Exception, match="Circuit breaker is OPEN"):
                cascading_failure_service()
                rejected_calls += 1
        
        # Service should only have been called 2 times (to open circuit)
        assert service_calls == 2
        assert rejected_calls == 5
    
    def test_circuit_breaker_with_different_services(self):
        """Test independent circuit breakers for different services"""
        
        # Create separate circuit breakers for different services
        db_breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=1)
        api_breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=1)
        
        db_calls = 0
        api_calls = 0
        
        @db_breaker
        def database_service():
            nonlocal db_calls
            db_calls += 1
            raise Exception("Database failure")
        
        @api_breaker
        def api_service():
            nonlocal api_calls
            api_calls += 1
            raise Exception("API failure")
        
        # Open database circuit breaker
        for _ in range(2):
            with pytest.raises(Exception):
                database_service()
        
        assert db_breaker.state == "OPEN"
        assert api_breaker.state == "CLOSED"  # API breaker should still be closed
        
        # API service should still work (until its threshold)
        for _ in range(2):
            with pytest.raises(Exception):
                api_service()
        
        assert db_breaker.state == "OPEN"
        assert api_breaker.state == "CLOSED"  # Still closed (threshold is 3)
        
        # One more API failure should open its circuit
        with pytest.raises(Exception):
            api_service()
        
        assert db_breaker.state == "OPEN"
        assert api_breaker.state == "OPEN"  # Now open
    
    def test_circuit_breaker_metrics_collection(self):
        """Test circuit breaker collects metrics"""
        
        circuit_breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=1)
        
        success_count = 0
        failure_count = 0
        
        @circuit_breaker
        def monitored_service():
            nonlocal success_count, failure_count
            if failure_count < 2:
                failure_count += 1
                raise Exception("Service failure")
            else:
                success_count += 1
                return f"Success {success_count}"
        
        # Mix of failures and successes
        results = []
        for i in range(5):
            try:
                result = monitored_service()
                results.append(result)
            except Exception as e:
                results.append(str(e))
        
        # Should have 2 failures followed by 3 successes
        assert failure_count == 2
        assert success_count == 3
        assert circuit_breaker.failure_count == 0  # Reset after successes


class TestDeadLetterQueueRecovery:
    """Test dead letter queue recovery mechanisms."""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = BiologicalMemoryErrorHandler(base_path=self.temp_dir)
        self.dlq = self.error_handler.dead_letter_queue
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_dead_letter_queue_enqueue_and_retry(self):
        """Test dead letter queue enqueue and retry functionality"""
        
        # Test data for memory processing
        failed_memory_data = {
            'memory_id': 'mem_123',
            'content': 'Failed to process this memory',
            'strength': 0.7,
            'processing_stage': 'consolidation'
        }
        
        # Enqueue failed operation
        self.dlq.enqueue(
            message_id="dlq_test_001",
            operation="memory_consolidation",
            memory_data=failed_memory_data,
            error_type=ErrorType.CONNECTION_FAILURE,
            error_message="Database connection failed during consolidation",
            retry_delay_seconds=0.5  # Short delay for testing
        )
        
        # Initially, no retry candidates
        candidates = self.dlq.get_retry_candidates()
        assert len(candidates) == 0
        
        # Wait for retry delay
        time.sleep(0.6)
        
        # Should now be available for retry
        candidates = self.dlq.get_retry_candidates()
        assert len(candidates) == 1
        
        candidate = candidates[0]
        assert candidate['message_id'] == "dlq_test_001"
        assert candidate['original_operation'] == "memory_consolidation"
        assert candidate['error_type'] == ErrorType.CONNECTION_FAILURE.value
        
        # Parse memory data
        import json
        memory_data = json.loads(candidate['memory_data'])
        assert memory_data['memory_id'] == 'mem_123'
        assert memory_data['processing_stage'] == 'consolidation'
        
        # Mark as successfully retried
        self.dlq.mark_retry_success("dlq_test_001")
        
        # Should no longer be in retry candidates
        candidates = self.dlq.get_retry_candidates()
        assert len(candidates) == 0
    
    def test_dead_letter_queue_max_retries(self):
        """Test dead letter queue respects maximum retry attempts"""
        
        memory_data = {'test': 'data'}
        
        # Enqueue with max_retries = 2
        self.dlq.enqueue(
            message_id="max_retry_test",
            operation="test_operation",
            memory_data=memory_data,
            error_type=ErrorType.TIMEOUT,
            error_message="Test timeout",
            retry_delay_seconds=0.1
        )
        
        time.sleep(0.2)
        
        # Should be available for retry
        candidates = self.dlq.get_retry_candidates()
        assert len(candidates) == 1
        
        # Simulate multiple failed retry attempts
        for attempt in range(3):
            time.sleep(0.2)
            candidates = self.dlq.get_retry_candidates()
            
            if candidates:
                # Simulate retry failure by re-enqueueing
                self.dlq.enqueue(
                    message_id="max_retry_test",
                    operation="test_operation",
                    memory_data=memory_data,
                    error_type=ErrorType.TIMEOUT,
                    error_message=f"Test timeout (retry {attempt + 1})",
                    retry_delay_seconds=0.1
                )
        
        # After max retries, should be marked as permanent failure
        time.sleep(0.2)
        candidates = self.dlq.get_retry_candidates()
        
        # Should filter out messages that exceed max retries
        active_candidates = [c for c in candidates if c['failure_count'] <= c['max_retries']]
        assert len(active_candidates) == 0
    
    def test_dead_letter_queue_batch_processing(self):
        """Test dead letter queue batch processing of multiple failures"""
        
        # Enqueue multiple failed operations
        failed_operations = [
            {
                'message_id': f'batch_msg_{i}',
                'operation': f'operation_type_{i % 3}',
                'data': {'batch_id': i, 'content': f'batch content {i}'},
                'error_type': ErrorType.CONNECTION_FAILURE if i % 2 == 0 else ErrorType.TIMEOUT
            }
            for i in range(10)
        ]
        
        for op in failed_operations:
            self.dlq.enqueue(
                message_id=op['message_id'],
                operation=op['operation'],
                memory_data=op['data'],
                error_type=op['error_type'],
                error_message=f"Batch failure for {op['message_id']}",
                retry_delay_seconds=0.1
            )
        
        time.sleep(0.2)
        
        # Get all retry candidates
        candidates = self.dlq.get_retry_candidates()
        assert len(candidates) == 10
        
        # Process batch retry
        retry_results = {'successful': 0, 'failed': 0}
        
        for candidate in candidates:
            try:
                # Simulate retry logic
                message_id = candidate['message_id']
                operation = candidate['original_operation']
                
                # Simulate success for even-numbered messages
                batch_id = int(message_id.split('_')[-1])
                if batch_id % 2 == 0:
                    self.dlq.mark_retry_success(message_id)
                    retry_results['successful'] += 1
                else:
                    # Would normally re-enqueue or mark as permanent failure
                    retry_results['failed'] += 1
                    
            except Exception:
                retry_results['failed'] += 1
        
        # Verify batch processing results
        assert retry_results['successful'] == 5  # Even-numbered messages
        assert retry_results['failed'] == 5     # Odd-numbered messages
        
        # Successful messages should no longer be in retry queue
        remaining_candidates = self.dlq.get_retry_candidates()
        successful_messages = [c for c in remaining_candidates 
                             if int(c['message_id'].split('_')[-1]) % 2 == 0]
        assert len(successful_messages) == 0


class TestRecoveryStrategies:
    """Test various recovery strategies and patterns."""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = BiologicalMemoryErrorHandler(base_path=self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_graceful_degradation_strategy(self):
        """Test graceful degradation when components fail"""
        
        # Test degradation for different failed components
        degradation_scenarios = [
            ('duckdb', ['consolidation_processing', 'deep_consolidation', 'analytics_dashboard']),
            ('ollama', ['rem_sleep_processing', 'creative_associations']),
            ('postgres', ['working_memory_processing'])
        ]
        
        for failed_component, expected_disabled in degradation_scenarios:
            degradation_config = self.error_handler.graceful_degradation_mode(failed_component)
            
            # Verify expected features are disabled
            for feature in expected_disabled:
                if feature in degradation_config:
                    assert degradation_config[feature] is False
            
            # Verify other features remain enabled
            enabled_features = [k for k, v in degradation_config.items() if v is True]
            assert len(enabled_features) > 0
    
    def test_automatic_error_recovery_workflow(self):
        """Test complete automatic error recovery workflow"""
        
        recovery_steps = []
        
        def failing_biological_memory_operation():
            """Simulate biological memory operation that may fail"""
            step = len(recovery_steps)
            
            if step == 0:
                recovery_steps.append("initial_attempt")
                raise ConnectionError("Database connection lost")
            elif step == 1:
                recovery_steps.append("retry_with_backoff")
                raise TimeoutError("Operation timed out")
            elif step == 2:
                recovery_steps.append("circuit_breaker_check")
                # Circuit breaker should allow this attempt
                recovery_steps.append("successful_recovery")
                return {
                    'status': 'recovered',
                    'recovery_steps': recovery_steps,
                    'data_processed': True
                }
        
        # Execute with automatic recovery
        result = self.error_handler.exponential_backoff_retry(
            failing_biological_memory_operation,
            max_retries=5,
            base_delay=0.05,
            exceptions=(ConnectionError, TimeoutError)
        )
        
        assert result['status'] == 'recovered'
        assert 'initial_attempt' in result['recovery_steps']
        assert 'retry_with_backoff' in result['recovery_steps']
        assert 'successful_recovery' in result['recovery_steps']
    
    def test_error_correlation_and_pattern_detection(self):
        """Test error correlation and pattern detection for proactive recovery"""
        
        # Simulate series of related errors
        error_patterns = [
            (ErrorType.CONNECTION_FAILURE, "database", "10.0.1.100"),
            (ErrorType.CONNECTION_FAILURE, "database", "10.0.1.100"),
            (ErrorType.TIMEOUT, "database", "10.0.1.100"),
            (ErrorType.CONNECTION_FAILURE, "database", "10.0.1.100"),
        ]
        
        for i, (error_type, component, host) in enumerate(error_patterns):
            error_event = ErrorEvent(
                error_id=f"pattern_test_{i}",
                error_type=error_type,
                timestamp=datetime.now(timezone.utc),
                component=component,
                operation="test_operation",
                error_message=f"Test error {i}",
                context={"host": host, "pattern_sequence": i}
            )
            
            self.error_handler.log_error_event(error_event)
        
        # Analyze error patterns (simplified)
        recent_errors = self.error_handler.error_events[-4:]
        
        # Check for error concentration
        db_errors = [e for e in recent_errors if e.component == "database"]
        connection_errors = [e for e in recent_errors if e.error_type == ErrorType.CONNECTION_FAILURE]
        
        assert len(db_errors) == 4  # All errors from database
        assert len(connection_errors) == 3  # 3 connection failures
        
        # Pattern detected: database connectivity issues
        # In production, this would trigger proactive recovery
    
    def test_resource_cleanup_during_error_recovery(self):
        """Test that resources are properly cleaned up during error recovery"""
        
        allocated_resources = []
        cleaned_resources = []
        
        def resource_intensive_operation():
            """Operation that allocates resources and may fail"""
            
            # Allocate resources
            resources = [f"resource_{i}" for i in range(3)]
            allocated_resources.extend(resources)
            
            try:
                # Simulate operation that might fail
                if len(allocated_resources) <= 6:  # Fail first 2 attempts
                    raise Exception("Operation failed during processing")
                
                return {"status": "success", "resources_used": len(resources)}
                
            except Exception:
                # Cleanup resources on failure
                for resource in resources:
                    if resource not in cleaned_resources:
                        cleaned_resources.append(resource)
                raise
            finally:
                # Final cleanup
                for resource in resources:
                    if resource not in cleaned_resources:
                        cleaned_resources.append(resource)
        
        # Execute with retry and resource cleanup
        result = self.error_handler.exponential_backoff_retry(
            resource_intensive_operation,
            max_retries=3,
            base_delay=0.05,
            exceptions=(Exception,)
        )
        
        assert result["status"] == "success"
        
        # Verify all allocated resources were cleaned up
        assert len(allocated_resources) == 9  # 3 attempts × 3 resources
        assert len(cleaned_resources) == 9    # All resources cleaned up
        assert set(allocated_resources) == set(cleaned_resources)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])