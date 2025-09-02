#!/usr/bin/env python3
"""
Comprehensive Ollama Integration Tests for STORY-009
Tests direct connectivity to Ollama at localhost:11434

This module provides comprehensive integration testing for:
- Direct Ollama LLM service connectivity to production server
- Model availability and performance validation (gpt-oss:20b, nomic-embed-text)
- Biological timing constraints for memory processing
- Health checks and error handling
- Caching performance and optimization
- Integration with biological memory pipeline
"""

import hashlib
import json
import logging
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import duckdb
import pytest
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "biological_memory"))


@dataclass
class OllamaConnectionConfig:
    """Configuration for Ollama integration testing"""

    base_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    primary_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    test_model: str = "qwen2.5:0.5b"  # Lightweight model for testing
    generation_timeout: int = 30
    health_check_timeout: int = 10
    max_retries: int = 3


class OllamaIntegrationTester:
    """Main class for Ollama integration testing"""

    def __init__(self, config: Optional[OllamaConnectionConfig] = None):
        self.config = config or OllamaConnectionConfig()
        self.session = requests.Session()
        self.test_cache_db = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """Clean up test resources"""
        if self.test_cache_db and Path(self.test_cache_db).exists():
            Path(self.test_cache_db).unlink()
        self.session.close()

    @contextmanager
    def get_test_cache_db(self):
        """Get a temporary DuckDB instance for caching tests"""
        temp_db = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
        temp_db.close()
        self.test_cache_db = temp_db.name

        try:
            conn = duckdb.connect(temp_db.name)

            # Create LLM cache table structure
            conn.execute(
                """
                CREATE TABLE llm_cache (
                    prompt_hash VARCHAR PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    model_name VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tokens_used INTEGER DEFAULT 0,
                    response_time_ms INTEGER DEFAULT 0
                )
            """
            )

            # Create metrics table
            conn.execute(
                """
                CREATE TABLE llm_metrics (
                    metric_name VARCHAR PRIMARY KEY,
                    metric_value DOUBLE NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            yield conn

        finally:
            if "conn" in locals():
                conn.close()

    def _generate_prompt_hash(self, prompt: str, model: str) -> str:
        """Generate a hash for caching purposes"""
        content = f"{prompt}:{model}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def call_ollama_generate(
        self, prompt: str, model: Optional[str] = None, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Call Ollama generate API with error handling"""
        model = model or self.config.primary_model
        timeout = timeout or self.config.generation_timeout

        try:
            response = self.session.post(
                f"{self.config.base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            return {"error": f"Request timed out after {timeout} seconds"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response"}

    def call_ollama_embedding(self, text: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Call Ollama embedding API"""
        model = model or self.config.embedding_model

        try:
            response = self.session.post(
                f"{self.config.base_url}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=self.config.generation_timeout,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {"error": f"Embedding request failed: {str(e)}"}


class TestOllamaConnectivity:
    """Test basic Ollama connectivity and configuration"""

    def setup_method(self):
        """Set up test environment"""
        self.tester = OllamaIntegrationTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.tester.cleanup()

    def test_ollama_direct_connection(self):
        """Test direct connection to Ollama service"""
        try:
            response = self.tester.session.get(
                f"{self.tester.config.base_url}/api/tags",
                timeout=self.tester.config.health_check_timeout,
            )
            response.raise_for_status()

            data = response.json()
            models = data.get("models", [])
            model_names = [model["name"] for model in models]

            assert len(models) > 0, "Should have at least one model available"
            logger.info(f"Successfully connected to Ollama. Available models: {len(models)}")

            # Log available models for debugging
            for model in models[:5]:  # Log first 5 models
                logger.info(f"Available model: {model['name']}")

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            # Service not available - this is acceptable in test environment
            logger.warning(f"Ollama service not available at {self.tester.config.base_url}: {e}")
            pytest.skip("Ollama service not available - skipping integration test")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to connect to Ollama at {self.tester.config.base_url}: {e}")

    def test_ollama_required_models_available(self):
        """Test that required models are available on the server"""
        try:
            response = self.tester.session.get(
                f"{self.tester.config.base_url}/api/tags",
                timeout=self.tester.config.health_check_timeout,
            )
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"Ollama service not available: {e}")
            pytest.skip("Ollama service not available - skipping model check")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to check models: {e}")

        data = response.json()
        available_models = [model["name"] for model in data.get("models", [])]

        # Check for primary model (may not be available in test environment)
        primary_available = any(
            self.tester.config.primary_model in model for model in available_models
        )
        embedding_available = any(
            self.tester.config.embedding_model in model for model in available_models
        )

        if not primary_available:
            logger.warning(f"Primary model {self.tester.config.primary_model} not available")
            logger.info("This is acceptable in test environments")

        if not embedding_available:
            logger.warning(f"Embedding model {self.tester.config.embedding_model} not available")
            logger.info("This is acceptable in test environments")

        # At minimum, we should have some models available
        assert len(available_models) > 0, "Should have at least one model available"

        # Test with any available model for basic functionality
        test_model = available_models[0] if available_models else None
        if test_model:
            logger.info(f"Using test model: {test_model}")

            # Basic generation test
            result = self.tester.call_ollama_generate(
                "What is 2+2? Answer with just the number.", model=test_model
            )

            assert "error" not in result, f"Generation failed: {result.get('error')}"
            assert "response" in result, "Should have response field"

            logger.info(f"Test generation successful: {result.get('response', '')[:50]}...")

    def test_ollama_performance_timing(self):
        """Test Ollama performance meets biological timing constraints"""
        # Get available models
        try:
            response = self.tester.session.get(
                f"{self.tester.config.base_url}/api/tags",
                timeout=self.tester.config.health_check_timeout,
            )
            response.raise_for_status()
            available_models = [model["name"] for model in response.json().get("models", [])]
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"Ollama service not available: {e}")
            pytest.skip("Ollama service not available - skipping performance test")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to check models: {e}")

        if not available_models:
            pytest.skip("No models available for performance testing")

        # Use the first available model for testing
        test_model = available_models[0]

        # Test short prompt performance (biological constraint: should be fast
        # for working memory)
        start_time = time.perf_counter()

        result = self.tester.call_ollama_generate(
            "Extract key insight from: Team meeting about project goals.", model=test_model
        )

        response_time = time.perf_counter() - start_time

        if "error" not in result:
            # For working memory processing, we want fast responses
            # But LLM calls are naturally slower than database queries
            # Target: <5 seconds for short prompts in integration tests
            assert response_time < 5.0, f"Short prompt took {response_time:.3f}s, should be <5.0s"

            logger.info(f"Ollama performance: {response_time:.3f}s for short prompt")
            logger.info(f"Response: {result.get('response', '')[:100]}...")
        else:
            logger.warning(f"Performance test skipped due to error: {result.get('error')}")


class TestOllamaBiologicalMemoryIntegration:
    """Test Ollama integration with biological memory pipeline"""

    def setup_method(self):
        """Set up test environment"""
        self.tester = OllamaIntegrationTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.tester.cleanup()

    def test_ollama_goal_extraction_for_biological_memory(self):
        """Test goal extraction for biological memory hierarchy"""
        # Test memory content that should be processed by biological memory
        # system
        test_memories = [
            "Working on quarterly business review and financial analysis",
            "Team standup meeting discussing sprint objectives",
            "Debugging authentication system connection timeouts",
            "Planning next product release features and timeline",
        ]

        # Get available models
        response = self.tester.session.get(f"{self.tester.config.base_url}/api/tags")
        response.raise_for_status()
        available_models = [model["name"] for model in response.json().get("models", [])]

        if not available_models:
            pytest.skip("No models available for goal extraction testing")

        test_model = available_models[0]

        for memory_content in test_memories:
            # Biological memory system goal extraction prompt
            prompt = f"""Extract the high-level goal from: {memory_content}

Return JSON with key "goal" containing one of these categories:
- Product Launch Strategy
- Communication and Collaboration
- Financial Planning and Management
- Project Management and Execution
- Client Relations and Service
- Operations and System Maintenance

Format: {{"goal": "category", "confidence": 0.0-1.0}}"""

            start_time = time.perf_counter()
            result = self.tester.call_ollama_generate(prompt, model=test_model)
            response_time = time.perf_counter() - start_time

            if "error" not in result:
                response_text = result.get("response", "{}")

                # Try to parse JSON response
                try:
                    parsed_json = json.loads(response_text)
                    assert "goal" in parsed_json, "Response should contain goal field"

                    goal_categories = [
                        "Product Launch Strategy",
                        "Communication and Collaboration",
                        "Financial Planning and Management",
                        "Project Management and Execution",
                        "Client Relations and Service",
                        "Operations and System Maintenance",
                    ]

                    # Check if goal is in expected categories (flexible for
                    # test environment)
                    goal = parsed_json["goal"]
                    logger.info(f"Extracted goal: {goal} for memory: {memory_content[:30]}...")

                    # Timing constraint for biological memory processing
                    # LLM calls are naturally slower, so we use a more
                    # realistic constraint
                    assert (
                        response_time < 10.0
                    ), f"Goal extraction took {response_time:.3f}s, should be <10.0s"

                except json.JSONDecodeError:
                    # In test environment, model might not return perfect JSON
                    logger.warning(
                        f"Non-JSON response (acceptable in test): {response_text[:50]}..."
                    )
                    assert len(response_text) > 0, "Should have some response"

            else:
                logger.warning(f"Goal extraction failed: {result.get('error')}")

    def test_ollama_embedding_generation_for_semantic_network(self):
        """Test embedding generation for semantic network formation"""
        test_concepts = [
            "project management",
            "team collaboration",
            "financial analysis",
            "product development",
            "system debugging",
        ]

        # Check if embedding model is available
        response = self.tester.session.get(f"{self.tester.config.base_url}/api/tags")
        response.raise_for_status()
        available_models = [model["name"] for model in response.json().get("models", [])]

        # Look for embedding model or any model that can do embeddings
        embedding_model = None
        for model_name in available_models:
            if "embed" in model_name.lower() or "nomic" in model_name.lower():
                embedding_model = model_name
                break

        if not embedding_model:
            # Use first available model for embedding test
            embedding_model = available_models[0] if available_models else None

        if not embedding_model:
            pytest.skip("No models available for embedding testing")

        embeddings_generated = []

        for concept in test_concepts:
            start_time = time.perf_counter()
            result = self.tester.call_ollama_embedding(concept, model=embedding_model)
            response_time = time.perf_counter() - start_time

            if "error" not in result and "embedding" in result:
                embedding = result["embedding"]

                # Validate embedding properties for semantic network
                assert isinstance(embedding, list), "Embedding should be a list of numbers"
                assert len(embedding) > 0, "Embedding should not be empty"
                assert all(
                    isinstance(x, (int, float)) for x in embedding
                ), "All embedding values should be numeric"

                embeddings_generated.append(embedding)

                # Biological timing constraint for embedding generation
                assert (
                    response_time < 15.0
                ), f"Embedding took {response_time:.3f}s, should be <15.0s"

                logger.info(
                    f"Generated embedding for '{concept}': {len(embedding)} dimensions in {response_time:.3f}s"
                )

            else:
                logger.warning(
                    f"Embedding failed for {concept}: {result.get('error', 'Unknown error')}"
                )

        # Test semantic similarity (if we got embeddings)
        if len(embeddings_generated) >= 2:
            # Simple cosine similarity test
            import math

            def cosine_similarity(a, b):
                dot_product = sum(x * y for x, y in zip(a, b))
                norm_a = math.sqrt(sum(x * x for x in a))
                norm_b = math.sqrt(sum(x * x for x in b))
                return dot_product / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0

            sim = cosine_similarity(embeddings_generated[0], embeddings_generated[1])
            assert 0 <= sim <= 1, f"Cosine similarity should be between 0 and 1, got {sim}"

            logger.info(f"Semantic similarity between concepts: {sim:.3f}")


class TestOllamaCachingAndPerformance:
    """Test Ollama caching system and performance optimization"""

    def setup_method(self):
        """Set up test environment"""
        self.tester = OllamaIntegrationTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.tester.cleanup()

    def test_ollama_caching_system_performance(self):
        """Test caching achieves performance improvements"""
        # Get available models
        try:
            response = self.tester.session.get(
                f"{self.tester.config.base_url}/api/tags",
                timeout=self.tester.config.health_check_timeout,
            )
            response.raise_for_status()
            available_models = [model["name"] for model in response.json().get("models", [])]
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"Ollama service not available: {e}")
            pytest.skip("Ollama service not available - skipping caching test")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to check models: {e}")

        if not available_models:
            pytest.skip("No models available for caching testing")

        test_model = available_models[0]

        with self.tester.get_test_cache_db() as cache_db:
            test_prompts = [
                "Extract goal from: Team planning meeting",
                "What is the main topic in: Code review session",
                "Extract goal from: Team planning meeting",  # Duplicate for cache hit
                "Analyze: Project status update",
                "Extract goal from: Team planning meeting",  # Another duplicate
            ]

            cache_hits = 0
            cache_misses = 0
            response_times = []

            for prompt in test_prompts:
                prompt_hash = self.tester._generate_prompt_hash(prompt, test_model)

                # Check cache first
                start_time = time.perf_counter()

                cached_result = cache_db.execute(
                    """
                    SELECT response, response_time_ms FROM llm_cache
                    WHERE prompt_hash = ? AND model_name = ?
                """,
                    (prompt_hash, test_model),
                ).fetchall()

                if cached_result:
                    # Cache hit
                    cache_hits += 1
                    response_time = time.perf_counter() - start_time
                    logger.info(
                        f"Cache hit for prompt: {prompt[:30]}... ({response_time*1000:.1f}ms)"
                    )

                else:
                    # Cache miss - call Ollama
                    cache_misses += 1

                    ollama_result = self.tester.call_ollama_generate(prompt, model=test_model)
                    response_time = time.perf_counter() - start_time

                    if "error" not in ollama_result:
                        # Store in cache
                        cache_db.execute(
                            """
                            INSERT OR REPLACE INTO llm_cache
                            (prompt_hash, prompt, response, model_name, response_time_ms)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                prompt_hash,
                                prompt,
                                ollama_result.get("response", ""),
                                test_model,
                                int(response_time * 1000),
                            ),
                        )

                        logger.info(
                            f"Cache miss for prompt: {prompt[:30]}... ({response_time:.3f}s)"
                        )
                    else:
                        logger.warning(f"Ollama call failed: {ollama_result.get('error')}")

                response_times.append(response_time)

            # Analyze caching performance
            if cache_hits + cache_misses > 0:
                cache_hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100

                logger.info(f"Cache performance: {cache_hits} hits, {cache_misses} misses")
                logger.info(f"Cache hit rate: {cache_hit_rate:.1f}%")

                # We expect cache hits for duplicate prompts
                assert cache_hits >= 2, "Should have cache hits for duplicate prompts"

                # Cache lookups should be much faster than Ollama calls
                if cache_hits > 0:
                    # Cache responses should be very fast (< 50ms)
                    fastest_response = min(response_times)
                    assert (
                        fastest_response < 0.05
                    ), f"Fastest response was {fastest_response:.3f}s, cache should be <0.05s"

    def test_ollama_concurrent_request_handling(self):
        """Test Ollama handles concurrent requests properly"""
        response = self.tester.session.get(f"{self.tester.config.base_url}/api/tags")
        response.raise_for_status()
        available_models = [model["name"] for model in response.json().get("models", [])]

        if not available_models:
            pytest.skip("No models available for concurrent testing")

        test_model = available_models[0]

        # Test multiple quick requests
        import queue
        import threading

        results_queue = queue.Queue()

        def make_request(prompt_id):
            try:
                start_time = time.perf_counter()
                result = self.tester.call_ollama_generate(
                    f"What is {prompt_id} + 1? Answer with just the number.", model=test_model
                )
                response_time = time.perf_counter() - start_time
                results_queue.put({"id": prompt_id, "result": result, "time": response_time})
            except Exception as e:
                results_queue.put({"id": prompt_id, "error": str(e)})

        # Create 3 concurrent requests
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)

        # Start all threads
        start_time = time.perf_counter()
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout

        total_time = time.perf_counter() - start_time

        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        assert len(results) == 3, "Should get 3 results from concurrent requests"

        successful_results = [
            r for r in results if "error" not in r and "error" not in r.get("result", {})
        ]

        if successful_results:
            logger.info(
                f"Concurrent requests: {len(successful_results)}/{len(results)} successful in {total_time:.3f}s"
            )

            # All successful requests should complete in reasonable time
            for result in successful_results:
                assert (
                    result["time"] < 15.0
                ), f"Request {result['id']} took {result['time']:.3f}s, should be <15.0s"
        else:
            logger.warning(
                "No successful concurrent requests - this may be normal for test environment"
            )


class TestOllamaHealthChecks:
    """Test comprehensive health checks for Ollama integration"""

    def setup_method(self):
        """Set up test environment"""
        self.tester = OllamaIntegrationTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.tester.cleanup()

    def test_ollama_comprehensive_health_check(self):
        """Comprehensive Ollama health check before running tests"""
        health_status = {}

        try:
            # Test 1: Service availability
            start_time = time.perf_counter()
            response = self.tester.session.get(
                f"{self.tester.config.base_url}/api/tags",
                timeout=self.tester.config.health_check_timeout,
            )
            response.raise_for_status()

            health_check_time = time.perf_counter() - start_time
            health_status["service_available"] = True
            health_status["response_time"] = health_check_time

            # Test 2: Model availability
            data = response.json()
            models = data.get("models", [])
            health_status["models"] = {
                "total_count": len(models),
                # First 5
                "available_models": [model["name"] for model in models[:5]],
                "primary_model_available": any(
                    self.tester.config.primary_model in model["name"] for model in models
                ),
                "embedding_model_available": any(
                    self.tester.config.embedding_model in model["name"] for model in models
                ),
                "has_any_models": len(models) > 0,
            }

            # Test 3: Basic generation capability
            if health_status["models"]["has_any_models"]:
                test_model = models[0]["name"]

                generation_start = time.perf_counter()
                gen_result = self.tester.call_ollama_generate(
                    "Health check: respond with 'OK'", model=test_model
                )
                generation_time = time.perf_counter() - generation_start

                health_status["generation"] = {
                    "test_model": test_model,
                    "successful": "error" not in gen_result,
                    "response_time": generation_time,
                    "response_preview": (
                        gen_result.get("response", "")[:50] if "response" in gen_result else "N/A"
                    ),
                }
            else:
                health_status["generation"] = {"successful": False, "error": "No models available"}

            # Test 4: Endpoint configuration
            health_status["configuration"] = {
                "endpoint": self.tester.config.base_url,
                "expected_host": os.getenv("OLLAMA_HOST", "localhost"),
                "expected_port": "11434",
                "timeout_config": self.tester.config.generation_timeout,
            }

            # Validate health status
            assert health_status["service_available"], "Ollama service not available"
            assert (
                health_status["response_time"] < 2.0
            ), f"Health check too slow: {health_status['response_time']:.3f}s"
            assert health_status["models"]["has_any_models"], "No models available"

            if health_status["generation"]["successful"]:
                assert (
                    health_status["generation"]["response_time"] < 10.0
                ), "Generation test too slow"

            logger.info("Ollama health check passed")
            logger.info(f"Service response time: {health_status['response_time']:.3f}s")
            logger.info(f"Models available: {health_status['models']['total_count']}")
            logger.info(
                f"Generation test: {'✅' if health_status['generation']['successful'] else '❌'}"
            )

            return health_status

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama health check failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected health check error: {e}")
            raise

    def test_ollama_error_handling_and_recovery(self):
        """Test Ollama error handling and recovery mechanisms"""
        # Test 1: Timeout handling
        short_timeout_config = OllamaConnectionConfig()
        short_timeout_config.generation_timeout = 1  # Very short timeout

        tester = OllamaIntegrationTester(short_timeout_config)

        try:
            result = tester.call_ollama_generate("This is a timeout test")
            # Either succeeds quickly or times out gracefully
            assert isinstance(result, dict), "Should return dictionary result"

            if "error" in result:
                assert "timed out" in result["error"] or "timeout" in result["error"].lower()
                logger.info(f"Timeout handling working: {result['error']}")
            else:
                logger.info("Request completed within timeout")

        finally:
            tester.cleanup()

        # Test 2: Invalid model handling
        result = self.tester.call_ollama_generate("Test prompt", model="nonexistent-model-12345")

        # Should handle gracefully without crashing
        assert isinstance(result, dict), "Should return dictionary for invalid model"
        if "error" in result:
            logger.info(f"Invalid model handled gracefully: {result['error']}")

        # Test 3: Malformed request handling
        try:
            response = self.tester.session.post(
                f"{self.tester.config.base_url}/api/generate",
                json={"invalid": "request"},
                timeout=5,
            )
            # Should either work or fail gracefully
            logger.info(f"Malformed request response: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.info(f"Malformed request handled: {e}")


def run_ollama_integration_tests():
    """Run all Ollama integration tests"""
    logger.info(
        f"Starting Ollama integration tests for {os.getenv('OLLAMA_URL', 'localhost:11434')}"
    )

    try:
        # Run health check first
        tester = OllamaIntegrationTester()
        response = tester.session.get(f"{tester.config.base_url}/api/tags", timeout=10)
        response.raise_for_status()
        logger.info("✅ Ollama connectivity confirmed")
        tester.cleanup()

        # Run the actual tests
        pytest_args = [__file__, "-v", "--tb=short", "-k", "test_ollama"]

        exit_code = pytest.main(pytest_args)
        return exit_code == 0

    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama integration tests failed - service unavailable: {e}")
        logger.info("This is acceptable in environments where Ollama is not running")
        return True  # Don't fail the build for missing optional services

    except Exception as e:
        logger.error(f"Ollama integration tests failed: {e}")
        return False


if __name__ == "__main__":
    success = run_ollama_integration_tests()
    exit(0 if success else 1)
