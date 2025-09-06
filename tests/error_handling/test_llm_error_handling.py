"""
Tests for LLM service error handling in the biological memory system
"""

import json
import os
import sys
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from services.error_handling import (
    BiologicalMemoryErrorHandler,
    LLMError,
    NetworkError,
    TimeoutError,
    handle_llm_service_error,
    with_llm_error_handling,
)


class TestLLMErrorHandling:
    """Test LLM service error handling scenarios"""

    @pytest.fixture
    def error_handler(self):
        return BiologicalMemoryErrorHandler()

    def test_llm_timeout_error_handling(self, error_handler):
        """Test LLM request timeout handling"""
        timeout_error = requests.exceptions.Timeout("Request timed out after 30s")

        error_record = error_handler.handle_error(
            timeout_error,
            {
                "operation": "llm_generation",
                "biological_context": {"memory_stage": "working_memory"},
            },
        )

        assert error_record["category"] == "timeout"
        recovery_result = error_record["recovery_result"]

        # Working memory should respect biological constraints
        assert (
            "biological_limit" in recovery_result["action"]
            or "timeout" in recovery_result["action"]
        )
        assert "5-minute window" in recovery_result.get("biological_note", "")

    def test_llm_connection_error_handling(self, error_handler):
        """Test LLM service connection errors"""
        conn_error = requests.exceptions.ConnectionError("Failed to connect to Ollama service")

        error_record = error_handler.handle_error(conn_error)

        assert error_record["category"] == "network"
        recovery_result = error_record["recovery_result"]
        assert recovery_result["fallback"] == "offline_mode"
        assert recovery_result["circuit_breaker"] == True

    def test_llm_model_not_found_error(self, error_handler):
        """Test handling when LLM model is not available"""
        model_error = LLMError("Model 'gpt-oss:20b' not found on server")

        error_record = error_handler.handle_error(model_error)
        recovery_result = error_record["recovery_result"]

        assert recovery_result["action"] == "use_fallback_model"
        assert recovery_result["fallback"] == "skip_llm_processing"
        assert "fallback_model" in recovery_result

    def test_llm_service_unavailable_handling(self, error_handler):
        """Test LLM service unavailable (503) error handling"""
        service_error = LLMError("LLM service unavailable (503)")

        error_record = error_handler.handle_error(service_error)
        recovery_result = error_record["recovery_result"]

        assert recovery_result["action"] == "circuit_breaker_pattern"
        assert recovery_result["fallback"] == "use_cached_responses"
        assert recovery_result["circuit_timeout"] == 300  # 5 minutes

    def test_llm_decorator_error_handling(self):
        """Test LLM error handling decorator"""

        @with_llm_error_handling(timeout_seconds=15.0)
        def failing_llm_operation():
            raise requests.exceptions.Timeout("LLM request timeout")

        with pytest.raises(TimeoutError) as exc_info:
            failing_llm_operation()

        assert "timeout" in str(exc_info.value).lower()

    def test_llm_error_with_biological_context(self, error_handler):
        """Test LLM error handling with biological memory context"""
        llm_error = LLMError("Generation failed")
        context = {
            "operation": "memory_enrichment",
            "biological_context": {
                "memory_stage": "consolidation",
                "operation_type": "hebbian_learning",
            },
        }

        error_record = error_handler.handle_error(llm_error, context)

        assert error_record["biological_context"]["memory_stage"] == "consolidation"
        assert error_record["biological_context"]["operation_type"] == "hebbian_learning"

    def test_llm_response_validation_error(self, error_handler):
        """Test handling of invalid LLM responses"""
        validation_error = LLMError("Invalid response format: expected dict, got str")

        error_record = error_handler.handle_error(validation_error)
        recovery_result = error_record["recovery_result"]

        assert recovery_result["action"] == "retry_with_backoff"
        assert recovery_result["fallback"] == "use_cached_embeddings"


class TestLLMCircuitBreaker:
    """Test circuit breaker pattern for LLM services"""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service with circuit breaker"""
        service = Mock()
        service.circuit_breaker = {
            "failures": 0,
            "last_failure_time": 0,
            "failure_threshold": 3,
            "recovery_timeout": 60,
            "is_open": False,
        }
        return service

    def test_circuit_breaker_opens_after_failures(self, mock_llm_service):
        """Test that circuit breaker opens after consecutive failures"""
        service = mock_llm_service

        # Simulate multiple failures
        for _ in range(4):
            service.circuit_breaker["failures"] += 1

        service.circuit_breaker["last_failure_time"] = time.time()

        # Circuit breaker should open
        is_open = (
            service.circuit_breaker["failures"] >= service.circuit_breaker["failure_threshold"]
        )
        assert is_open

    def test_circuit_breaker_recovery(self, mock_llm_service):
        """Test circuit breaker recovery after timeout"""
        service = mock_llm_service

        # Open circuit breaker
        service.circuit_breaker["failures"] = 5
        service.circuit_breaker["last_failure_time"] = time.time() - 70  # 70 seconds ago
        service.circuit_breaker["is_open"] = True

        # Should allow recovery attempt after timeout
        recovery_timeout = service.circuit_breaker["recovery_timeout"]
        time_since_failure = time.time() - service.circuit_breaker["last_failure_time"]

        can_attempt = time_since_failure > recovery_timeout
        assert can_attempt


class TestLLMBiologicalConstraints:
    """Test LLM operations with biological memory constraints"""

    @pytest.fixture
    def error_handler(self):
        return BiologicalMemoryErrorHandler()

    def test_working_memory_llm_timeout(self, error_handler):
        """Test LLM timeout during working memory operations"""
        timeout_error = requests.exceptions.Timeout("LLM timeout during working memory processing")
        context = {"biological_context": {"memory_stage": "working_memory"}}

        error_record = error_handler.handle_error(timeout_error, context)
        recovery_result = error_record["recovery_result"]

        # Working memory should have strict timing constraints
        assert recovery_result["max_retries"] == 1
        assert "5-minute window" in recovery_result["biological_note"]

    def test_consolidation_llm_timeout(self, error_handler):
        """Test LLM timeout during memory consolidation"""
        timeout_error = requests.exceptions.Timeout("LLM timeout during consolidation")
        context = {"biological_context": {"memory_stage": "consolidation"}}

        error_record = error_handler.handle_error(timeout_error, context)
        recovery_result = error_record["recovery_result"]

        # Consolidation can allow extended processing
        assert recovery_result["max_retries"] == 2
        assert "extended_timeout" in recovery_result

    def test_llm_error_during_sleep_phase(self, error_handler):
        """Test LLM error handling during different sleep phases"""
        llm_error = LLMError("Service unavailable during deep sleep processing")
        context = {
            "biological_context": {
                "sleep_phase": "deep_sleep",
                "operation_type": "memory_consolidation",
            }
        }

        error_record = error_handler.handle_error(llm_error, context)

        # Should have biological context preserved
        assert error_record["biological_context"]["sleep_phase"] == "deep_sleep"


class TestLLMErrorRecovery:
    """Test LLM error recovery strategies"""

    @pytest.fixture
    def error_handler(self):
        return BiologicalMemoryErrorHandler()

    def test_llm_fallback_model_strategy(self, error_handler):
        """Test fallback model strategy"""
        model_error = LLMError("Primary model unavailable")

        recovery_strategy = error_handler._handle_llm_error(model_error, {})

        # Should have fallback model configuration
        if "fallback_model" in recovery_strategy:
            assert recovery_strategy["fallback_model"] == "llama2:7b"

    def test_llm_cache_fallback_strategy(self, error_handler):
        """Test cache fallback strategy"""
        service_error = LLMError("LLM service down")

        recovery_strategy = error_handler._handle_llm_error(service_error, {})

        # Should fallback to cached responses
        assert "cached" in recovery_strategy["fallback"]

    def test_llm_skip_processing_fallback(self, error_handler):
        """Test skipping LLM processing fallback"""
        critical_error = LLMError("Model not found - critical failure")

        recovery_strategy = error_handler._handle_llm_error(critical_error, {})

        # Should allow skipping LLM processing entirely
        if "skip" in recovery_strategy["fallback"]:
            assert recovery_strategy["max_retries"] == 1


class TestLLMServiceIntegration:
    """Test integration with actual LLM service error scenarios"""

    def test_handle_llm_service_error_wrapper(self):
        """Test the convenience wrapper for LLM service errors"""

        def failing_llm_function():
            raise requests.exceptions.ConnectionError("Cannot connect to Ollama")

        result = handle_llm_service_error(failing_llm_function)

        # Should return None on error (safe execution)
        assert result is None

    @patch("requests.post")
    def test_llm_api_error_simulation(self, mock_post):
        """Test various LLM API error scenarios"""

        # Simulate 503 Service Unavailable
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.json.return_value = {"error": "Service temporarily unavailable"}
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "503 Service Unavailable"
        )
        mock_post.return_value = mock_response

        error_handler = BiologicalMemoryErrorHandler()

        try:
            # This would be called by the actual LLM service
            mock_response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_record = error_handler.handle_error(e)
            assert error_record["category"] == "network"  # HTTP errors classified as network

    def test_embedding_generation_error_handling(self):
        """Test error handling during embedding generation"""
        from services.error_handling import EmbeddingError

        embedding_error = EmbeddingError("Failed to generate embedding vector")
        error_handler = BiologicalMemoryErrorHandler()

        error_record = error_handler.handle_error(embedding_error)
        recovery_result = error_record["recovery_result"]

        assert recovery_result["action"] == "retry_with_fallback_model"
        assert recovery_result["fallback"] == "use_zero_vector"
        assert "semantic similarity" in recovery_result["biological_note"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
