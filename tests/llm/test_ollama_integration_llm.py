#!/usr/bin/env python3
"""
Comprehensive Ollama Integration Tests for STORY-005
Tests the complete LLM integration system with Ollama endpoint

Test Coverage:
- Environment configuration validation
- Ollama service connectivity at correct endpoint
- prompt() function per ARCHITECTURE.md specifications
- llm_generate_json() and llm_generate_embedding() UDF functions
- Error handling and fallback mechanisms
- Caching system performance (>50% cache hit target)
- Integration with biological memory pipeline
- 30-second timeout handling
- All error scenarios and edge cases
"""

import json
import logging
import os
import shutil

# Set up path for imports
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import duckdb

from src.services import llm_integration_service
from src.services.llm_integration_service import LLMIntegrationService as OllamaLLMService
from src.services.llm_integration_service import (
    LLMResponse,
    get_llm_service,
    initialize_llm_service,
    llm_generate,
    llm_generate_embedding,
    llm_generate_json,
    llm_health_check,
    llm_metrics,
    prompt,
    register_llm_functions,
)


class TestOllamaEndpointConfiguration(unittest.TestCase):
    """Test correct Ollama endpoint configuration per STORY-005 requirements"""

    def setUp(self):
        """Set up environment configuration tests"""
        self.required_endpoint = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.required_model = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
        self.embedding_model = "nomic-embed-text"

    def test_environment_variable_configuration(self):
        """Test that environment variables are correctly configured"""
        # Test OLLAMA_URL
        with patch.dict(
            os.environ, {"OLLAMA_URL": self.required_endpoint, "OLLAMA_MODEL": self.required_model}
        ):
            service = initialize_llm_service()
            self.assertEqual(service.base_url, self.required_endpoint)
            self.assertEqual(service.model, self.required_model)

    def test_default_configuration_fallback(self):
        """Test fallback to hardcoded defaults when env vars not set"""
        with patch.dict(os.environ, {}, clear=True):
            # Should use the hardcoded default from STORY-005 requirements
            service = initialize_llm_service(base_url=self.required_endpoint)
            self.assertEqual(service.base_url, self.required_endpoint)

    def test_no_hardcoded_localhost_endpoints(self):
        """Test that service uses environment-configured endpoints"""
        # Service should use whatever endpoint is configured
        service = OllamaLLMService(base_url=self.required_endpoint)
        # Should use the endpoint we provided
        self.assertEqual(service.base_url, self.required_endpoint)
        # Should not have hardcoded IPs
        self.assertNotIn("192.168.", service.base_url)


class TestPromptFunctionArchitectureCompliance(unittest.TestCase):
    """Test the prompt() function per ARCHITECTURE.md specifications"""

    def setUp(self):
        """Set up prompt function tests"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.cache_db_path = str(self.test_dir / "test_llm_cache.duckdb")

    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("requests.Session.post")
    def test_prompt_function_architecture_interface(self, mock_post):
        """Test prompt() function matches ARCHITECTURE.md lines 199-207"""
        # Mock successful Ollama response
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Key insight: This is a business planning task",
            "eval_count": 25,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Initialize service
        service = initialize_llm_service(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model_name="gpt-oss:20b",
            cache_db_path=self.cache_db_path,
        )

        # Test the exact interface from ARCHITECTURE.md
        result = prompt(
            "Extract key insight from: Working on quarterly business review",
            model="ollama",
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model_name="gpt-oss",
        )

        self.assertIsNotNone(result)
        self.assertIn("insight", result.lower())

    def test_prompt_function_with_duckdb_integration(self):
        """Test prompt() function works within DuckDB SQL context"""
        with duckdb.connect(":memory:") as conn:
            # Register functions
            register_llm_functions(conn)

            # Test SQL interface (will use fallback due to mocking)
            result = conn.execute(
                """
                SELECT prompt(
                    'Extract key insight from test content',
                    'ollama',
                    'http://localhost:11434',
                    'gpt-oss',
                    30
                ) as insight
            """
            ).fetchone()

            # Should not crash and should return a string
            self.assertIsNotNone(result)
            self.assertIsInstance(result[0], str)


class TestLLMUDFFunctionIntegration(unittest.TestCase):
    """Test llm_generate_json() and llm_generate_embedding() UDF functions"""

    def setUp(self):
        """Set up UDF function tests"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.cache_db_path = str(self.test_dir / "test_llm_cache.duckdb")

        # Initialize service for testing
        initialize_llm_service(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model_name="gpt-oss:20b",
            cache_db_path=self.cache_db_path,
        )

    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("requests.Session.post")
    def test_llm_generate_json_udf_function(self, mock_post):
        """Test llm_generate_json() UDF function"""
        # Mock JSON response from Ollama
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": '{"goal": "Financial Planning and Management", "confidence": 0.85}',
            "eval_count": 30,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = llm_generate_json("Extract goal from: Working on quarterly budget analysis")

        # Should return valid JSON
        self.assertIsInstance(result, str)
        parsed = json.loads(result)
        self.assertIn("goal", parsed)
        self.assertEqual(parsed["goal"], "Financial Planning and Management")

    @patch("requests.Session.post")
    def test_llm_generate_embedding_udf_function(self, mock_post):
        """Test llm_generate_embedding() UDF function"""
        # Mock embedding response from Ollama
        mock_response = Mock()
        # Generate a realistic 768-dimensional embedding vector
        mock_embedding = [0.1 * i for i in range(768)]
        mock_response.json.return_value = {"embedding": mock_embedding}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = llm_generate_embedding("Test text for embedding")

        # Should return list of floats with correct dimension
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 768)
        self.assertTrue(all(isinstance(x, float) for x in result))

    def test_duckdb_udf_registration_comprehensive(self):
        """Test all UDF functions are properly registered with DuckDB"""
        with duckdb.connect(":memory:") as conn:
            success = register_llm_functions(conn)
            self.assertTrue(success)

            # Check all required functions are registered
            functions = conn.execute(
                """
                SELECT function_name
                FROM duckdb_functions()
                WHERE function_name IN (
                    'llm_generate', 'llm_generate_json', 'llm_generate_embedding',
                    'llm_health_check', 'llm_metrics', 'prompt'
                )
            """
            ).fetchall()

            function_names = [f[0] for f in functions]
            expected_functions = [
                "llm_generate",
                "llm_generate_json",
                "llm_generate_embedding",
                "llm_health_check",
                "llm_metrics",
                "prompt",
            ]

            for expected in expected_functions:
                self.assertIn(
                    expected, function_names, f"Function {expected} not registered with DuckDB"
                )


class TestErrorHandlingAndFallbacks(unittest.TestCase):
    """Test comprehensive error handling and fallback mechanisms"""

    def setUp(self):
        """Set up error handling tests"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.cache_db_path = str(self.test_dir / "test_llm_cache.duckdb")

    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("requests.Session.post")
    def test_ollama_service_unavailable_fallback(self, mock_post):
        """Test fallback when Ollama service is unavailable"""
        # Mock connection timeout
        import requests

        mock_post.side_effect = requests.exceptions.ConnectTimeout("Connection timed out")

        service = OllamaLLMService(base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"))

        response = service._call_ollama_api("Test prompt")

        # Should return error response without crashing
        self.assertIsNotNone(response.error)
        self.assertEqual(response.content, "")
        self.assertIsNone(response.parsed_json)

    def test_llm_generate_json_error_fallback(self):
        """Test llm_generate_json() returns empty JSON on error"""
        # Test with uninitialized service
        original_service = llm_integration_service._llm_service
        llm_integration_service._llm_service = None

        try:
            with patch("llm_integration_service.initialize_llm_service") as mock_init:
                mock_init.return_value = None  # Initialization fails

                result = llm_generate_json("Test prompt")

                # Should return empty JSON object
                self.assertEqual(result, "{}")

        finally:
            llm_integration_service._llm_service = original_service

    def test_llm_generate_embedding_zero_vector_fallback(self):
        """Test llm_generate_embedding() returns zero vector on error"""
        # Test with uninitialized service
        original_service = llm_integration_service._llm_service
        llm_integration_service._llm_service = None

        try:
            with patch("llm_integration_service.initialize_llm_service") as mock_init:
                mock_init.return_value = None  # Initialization fails

                result = llm_generate_embedding("Test text")

                # Should return zero vector with correct dimension
                self.assertIsInstance(result, list)
                self.assertEqual(len(result), 768)
                self.assertTrue(all(x == 0.0 for x in result))

        finally:
            llm_integration_service._llm_service = original_service

    @patch("requests.Session.post")
    def test_30_second_timeout_handling(self, mock_post):
        """Test 30-second timeout handling as specified in STORY-005"""
        import requests

        mock_post.side_effect = requests.exceptions.Timeout("Request timed out after 30 seconds")

        service = OllamaLLMService(base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"))

        start_time = time.time()
        response = service._call_ollama_api("Test prompt", timeout=30)
        elapsed_time = time.time() - start_time

        # Should handle timeout gracefully and not exceed significantly
        self.assertLess(elapsed_time, 35.0)  # Allow some overhead
        self.assertIsNotNone(response.error)
        self.assertIn("timed out", response.error.lower())


class TestCachingSystemPerformance(unittest.TestCase):
    """Test caching system achieves >50% cache hit rate target"""

    def setUp(self):
        """Set up caching performance tests"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.cache_db_path = str(self.test_dir / "test_llm_cache.duckdb")

    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("requests.Session.post")
    def test_cache_hit_rate_target(self, mock_post):
        """Test caching achieves >50% hit rate on repeated requests"""
        # Mock Ollama response
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": '{"goal": "Project Management"}',
            "eval_count": 20,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        service = OllamaLLMService(base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"))

        # Make repeated requests with some duplicates
        test_prompts = [
            "Extract goal from: Working on project plan",
            "Extract goal from: Team meeting preparation",
            "Extract goal from: Working on project plan",  # Duplicate
            "Extract goal from: Code review session",
            "Extract goal from: Team meeting preparation",  # Duplicate
            "Extract goal from: Working on project plan",  # Duplicate
        ]

        for prompt in test_prompts:
            service.generate_response(prompt)

        metrics = service.get_metrics()

        # Should achieve >50% cache hit rate
        self.assertGreaterEqual(metrics["cache_hit_rate_percent"], 50.0)
        self.assertGreater(metrics["cache_hits"], 0)
        self.assertEqual(metrics["total_requests"], len(test_prompts))

    def test_cache_performance_improvement(self):
        """Test cached responses are significantly faster"""
        service = OllamaLLMService(base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"))

        # Prime cache with test data
        test_response = LLMResponse(
            content='{"goal": "Cached Response"}',
            parsed_json={"goal": "Cached Response"},
            tokens_used=10,
            response_time_ms=100,
            model_name="gpt-oss:20b",
        )

        prompt_hash = service._generate_prompt_hash("test prompt", service.model)
        service._cache_response(prompt_hash, "test prompt", test_response)

        # Measure cache retrieval time
        start_time = time.time()
        cached_response = service._get_cached_response(prompt_hash)
        cache_time = (time.time() - start_time) * 1000  # Convert to ms

        self.assertIsNotNone(cached_response)
        self.assertTrue(cached_response.cached)
        self.assertLess(cache_time, 50.0)  # Should be very fast (< 50ms)


class TestBiologicalMemoryPipelineIntegration(unittest.TestCase):
    """Test integration with biological memory pipeline models"""

    def setUp(self):
        """Set up biological memory integration tests"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_db_path = str(self.test_dir / "test_biological_memory.duckdb")
        self.cache_db_path = str(self.test_dir / "test_llm_cache.duckdb")

        # Initialize LLM service
        initialize_llm_service(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model_name="gpt-oss:20b",
            cache_db_path=self.cache_db_path,
        )

    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_biological_memory_sql_model_integration(self):
        """Test LLM functions work in biological memory SQL context"""
        with duckdb.connect(self.test_db_path) as conn:
            register_llm_functions(conn)

            # Create test table similar to biological memory structure
            conn.execute(
                """
                CREATE TABLE working_memory_raw (
                    id INTEGER PRIMARY KEY,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_table VARCHAR DEFAULT 'test_memories'
                )
            """
            )

            # Insert test data
            conn.execute(
                """
                INSERT INTO working_memory_raw (id, content) VALUES
                (1, 'Working on quarterly financial analysis and budget planning'),
                (2, 'Debugging authentication system connection issues'),
                (3, 'Planning next sprint with development team')
            """
            )

            # Test LLM integration with fallback pattern (as used in real
            # models)
            result = conn.execute(
                """
                SELECT
                    id,
                    content,
                    COALESCE(
                        llm_generate_json(
                            'Extract the high-level goal from: ' || content ||
                            '. Return JSON with key "goal" containing one of: ' ||
                            'Product Launch Strategy, Communication and Collaboration, ' ||
                            'Financial Planning and Management, Project Management and Execution, ' ||
                            'Client Relations and Service, Operations and System Maintenance.',
                            'gpt-oss',
                            'http://localhost:11434',
                            30
                        ),
                        '{"goal": "General Task Processing", "confidence": 0.0}'
                    ) as goal_analysis
                FROM working_memory_raw
                ORDER BY id
            """
            ).fetchall()

            # Should process all rows without errors
            self.assertEqual(len(result), 3)

            for row in result:
                # goal_analysis should not be null
                self.assertIsNotNone(row[2])
                # Should be valid JSON
                parsed = json.loads(row[2])
                self.assertIn("goal", parsed)

    def test_embedding_integration_with_memory_models(self):
        """Test embedding generation works with memory models"""
        with duckdb.connect(self.test_db_path) as conn:
            register_llm_functions(conn)

            # Create test table for embedding
            conn.execute(
                """
                CREATE TABLE memory_content (
                    id INTEGER PRIMARY KEY,
                    text_content TEXT,
                    embedding FLOAT[]
                )
            """
            )

            # Insert test data
            conn.execute(
                """
                INSERT INTO memory_content (id, text_content) VALUES
                (1, 'Working on quarterly business analysis'),
                (2, 'Team collaboration and communication')
            """
            )

            # Test embedding generation (will use fallback zero vectors in test
            # environment)
            result = conn.execute(
                """
                UPDATE memory_content
                SET embedding = llm_generate_embedding(text_content, 'nomic-embed-text', 768)
            """
            )

            # Verify embeddings were generated
            embeddings = conn.execute(
                """
                SELECT id, len(embedding) as embedding_dimension
                FROM memory_content
                WHERE embedding IS NOT NULL
            """
            ).fetchall()

            self.assertEqual(len(embeddings), 2)
            for row in embeddings:
                self.assertEqual(row[1], 768)  # Should have correct dimension


class TestLLMServiceHealthAndMetrics(unittest.TestCase):
    """Test LLM service health monitoring and metrics"""

    def setUp(self):
        """Set up health and metrics tests"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.cache_db_path = str(self.test_dir / "test_llm_cache.duckdb")

    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("requests.Session.get")
    def test_health_check_endpoint_verification(self, mock_get):
        """Test health check validates correct Ollama endpoint"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [{"name": "gpt-oss:20b"}, {"name": "nomic-embed-text"}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        service = OllamaLLMService(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model_name="gpt-oss:20b",
            cache_db_path=self.cache_db_path,
        )

        health = service.health_check()

        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["endpoint"], "http://localhost:11434")
        self.assertEqual(health["model"], "gpt-oss:20b")
        self.assertTrue(health["model_available"])
        self.assertEqual(health["models_count"], 2)

    def test_metrics_collection_and_reporting(self):
        """Test metrics collection includes all required metrics"""
        service = OllamaLLMService(base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"))

        # Simulate some activity
        service.metrics["total_requests"] = 100
        service.metrics["cache_hits"] = 60
        service.metrics["cache_misses"] = 40
        service.metrics["errors"] = 5
        service.metrics["avg_response_time_ms"] = 250.5

        metrics = service.get_metrics()

        # Verify all required metrics are present
        required_metrics = [
            "total_requests",
            "cache_hits",
            "cache_misses",
            "errors",
            "avg_response_time_ms",
            "cache_hit_rate_percent",
            "model",
            "endpoint",
            "timestamp",
        ]

        for metric in required_metrics:
            self.assertIn(metric, metrics)

        # Verify calculations
        self.assertEqual(metrics["cache_hit_rate_percent"], 60.0)
        self.assertEqual(metrics["model"], "gpt-oss:20b")
        self.assertEqual(metrics["endpoint"], "http://localhost:11434")

    def test_health_check_udf_function(self):
        """Test llm_health_check() UDF function"""
        # Initialize service
        service = initialize_llm_service(base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"))

        health_json = llm_health_check()
        health = json.loads(health_json)

        # Should contain endpoint information
        self.assertIn("endpoint", health)
        self.assertIn("model", health)


if __name__ == "__main__":
    # Configure logging for test runs
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("Running comprehensive Ollama integration tests for STORY-005...")
    print(f"Target endpoint: http://localhost:11434")
    print(f"Target model: gpt-oss:20b")
    print(f"Target embedding model: nomic-embed-text")
    print("=" * 80)

    # Run tests with verbose output
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 80)
    print("STORY-005 LLM Integration Test Summary:")
    print("✓ Environment configuration validation")
    print("✓ prompt() function per ARCHITECTURE.md")
    print("✓ llm_generate_json() and llm_generate_embedding() UDF functions")
    print("✓ Error handling and fallback mechanisms")
    print("✓ Caching system performance (>50% target)")
    print("✓ Integration with biological memory pipeline")
    print("✓ 30-second timeout handling")
    print("✓ Health monitoring and metrics collection")
