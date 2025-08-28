#!/usr/bin/env python3
"""
Comprehensive LLM Integration Tests for Biological Memory Pipeline
Tests end-to-end LLM integration with Ollama and DuckDB UDF functions

Test Coverage:
- Ollama service connectivity and health
- DuckDB UDF function registration and execution
- JSON response parsing and validation
- Error handling and fallback mechanisms
- Performance and caching functionality
- Integration with biological memory models
"""

import unittest
import json
import logging
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import duckdb

# Set up path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from llm_integration_service import (
    OllamaLLMService, LLMResponse, initialize_llm_service, 
    register_llm_functions, get_llm_service,
    llm_generate, llm_generate_json, llm_health_check, llm_metrics
)
from error_handling import BiologicalMemoryErrorHandler


class TestLLMIntegrationService(unittest.TestCase):
    """Test the core LLM integration service functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(__file__).parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)
        
        self.cache_db_path = str(self.test_dir / "test_llm_cache.duckdb")
        self.ollama_url = "http://127.0.0.1:11434"  # Local test URL
        
        # Mock error handler
        self.mock_error_handler = Mock(spec=BiologicalMemoryErrorHandler)
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            if Path(self.cache_db_path).exists():
                Path(self.cache_db_path).unlink()
        except Exception:
            pass
    
    def test_service_initialization(self):
        """Test LLM service initialization"""
        service = OllamaLLMService(
            ollama_url=self.ollama_url,
            model_name="test-model",
            cache_db_path=self.cache_db_path,
            error_handler=self.mock_error_handler
        )
        
        self.assertEqual(service.ollama_url, self.ollama_url)
        self.assertEqual(service.model_name, "test-model")
        self.assertEqual(service.cache_db_path, self.cache_db_path)
        
        # Test cache database initialization
        self.assertTrue(Path(self.cache_db_path).exists())
    
    def test_cache_functionality(self):
        """Test LLM response caching"""
        service = OllamaLLMService(
            ollama_url=self.ollama_url,
            cache_db_path=self.cache_db_path
        )
        
        # Create a test response
        test_response = LLMResponse(
            content='{"test": "response"}',
            parsed_json={"test": "response"},
            tokens_used=10,
            response_time_ms=100,
            model_name="test-model"
        )
        
        # Test caching
        prompt_hash = service._generate_prompt_hash("test prompt", "test-model")
        service._cache_response(prompt_hash, "test prompt", test_response)
        
        # Test retrieval
        cached_response = service._get_cached_response(prompt_hash)
        self.assertIsNotNone(cached_response)
        self.assertEqual(cached_response.content, '{"test": "response"}')
        self.assertTrue(cached_response.cached)
    
    @patch('requests.Session.post')
    def test_ollama_api_call_success(self, mock_post):
        """Test successful Ollama API call"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'response': '{"goal": "Test Goal"}',
            'eval_count': 50
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        service = OllamaLLMService(
            ollama_url=self.ollama_url,
            cache_db_path=self.cache_db_path
        )
        
        response = service._call_ollama_api("Test prompt")
        
        self.assertIsNone(response.error)
        self.assertEqual(response.content, '{"goal": "Test Goal"}')
        self.assertIsNotNone(response.parsed_json)
        self.assertEqual(response.parsed_json['goal'], "Test Goal")
        self.assertEqual(response.tokens_used, 50)
    
    @patch('requests.Session.post')
    def test_ollama_api_call_failure(self, mock_post):
        """Test Ollama API call failure handling"""
        # Mock failed response
        mock_post.side_effect = Exception("Connection failed")
        
        service = OllamaLLMService(
            ollama_url=self.ollama_url,
            cache_db_path=self.cache_db_path,
            error_handler=self.mock_error_handler
        )
        
        response = service._call_ollama_api("Test prompt")
        
        self.assertIsNotNone(response.error)
        self.assertEqual(response.content, "")
        self.assertIsNone(response.parsed_json)
    
    @patch('requests.Session.get')
    def test_health_check_healthy(self, mock_get):
        """Test health check with healthy service"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'models': [{'name': 'gpt-oss:20b'}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        service = OllamaLLMService(
            ollama_url=self.ollama_url,
            model_name="gpt-oss:20b",
            cache_db_path=self.cache_db_path
        )
        
        health = service.health_check()
        
        self.assertEqual(health['status'], 'healthy')
        self.assertTrue(health['model_available'])
        self.assertEqual(health['models_count'], 1)
    
    @patch('requests.Session.get')
    def test_health_check_unhealthy(self, mock_get):
        """Test health check with unhealthy service"""
        mock_get.side_effect = Exception("Service unavailable")
        
        service = OllamaLLMService(
            ollama_url=self.ollama_url,
            cache_db_path=self.cache_db_path
        )
        
        health = service.health_check()
        
        self.assertEqual(health['status'], 'unhealthy')
        self.assertIn('error', health)


class TestDuckDBUDFIntegration(unittest.TestCase):
    """Test DuckDB UDF function integration"""
    
    def setUp(self):
        """Set up test database"""
        self.test_dir = Path(__file__).parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)
        
        self.test_db_path = str(self.test_dir / "test_memory.duckdb")
        self.cache_db_path = str(self.test_dir / "test_llm_cache.duckdb")
        
        # Initialize LLM service for testing
        initialize_llm_service(
            ollama_url="http://127.0.0.1:11434",
            model_name="gpt-oss:20b",
            cache_db_path=self.cache_db_path
        )
    
    def tearDown(self):
        """Clean up test databases"""
        for path in [self.test_db_path, self.cache_db_path]:
            try:
                if Path(path).exists():
                    Path(path).unlink()
            except Exception:
                pass
    
    def test_udf_function_registration(self):
        """Test UDF function registration with DuckDB"""
        with duckdb.connect(self.test_db_path) as conn:
            success = register_llm_functions(conn)
            self.assertTrue(success)
            
            # Test that functions are registered
            functions = conn.execute("""
                SELECT function_name 
                FROM duckdb_functions() 
                WHERE function_name IN ('llm_generate', 'llm_generate_json', 'llm_health_check', 'llm_metrics')
            """).fetchall()
            
            function_names = [f[0] for f in functions]
            self.assertIn('llm_generate', function_names)
            self.assertIn('llm_generate_json', function_names)
            self.assertIn('llm_health_check', function_names)
            self.assertIn('llm_metrics', function_names)
    
    @patch('llm_integration_service._llm_service')
    def test_llm_generate_udf(self, mock_service):
        """Test llm_generate UDF function"""
        # Mock LLM service response
        mock_response = LLMResponse(
            content="Test response",
            parsed_json=None,
            tokens_used=10,
            response_time_ms=100,
            model_name="gpt-oss:20b"
        )
        mock_service.generate_response.return_value = mock_response
        
        result = llm_generate("Test prompt")
        self.assertEqual(result, "Test response")
    
    @patch('llm_integration_service._llm_service')
    def test_llm_generate_json_udf(self, mock_service):
        """Test llm_generate_json UDF function"""
        # Mock LLM service response with JSON
        mock_response = LLMResponse(
            content='{"goal": "Test Goal"}',
            parsed_json={"goal": "Test Goal"},
            tokens_used=10,
            response_time_ms=100,
            model_name="gpt-oss:20b"
        )
        mock_service.generate_response.return_value = mock_response
        
        result = llm_generate_json("Test prompt")
        result_json = json.loads(result)
        self.assertEqual(result_json['goal'], "Test Goal")
    
    def test_biological_memory_sql_integration(self):
        """Test integration with biological memory SQL models"""
        with duckdb.connect(self.test_db_path) as conn:
            register_llm_functions(conn)
            
            # Create test data structure similar to biological memory
            conn.execute("""
                CREATE TABLE test_memories (
                    id INTEGER PRIMARY KEY,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                INSERT INTO test_memories (content) VALUES 
                ('Working on quarterly business review presentation'),
                ('Debugging authentication system issues'),
                ('Planning team meeting for next week')
            """)
            
            # Test LLM integration in SQL (with fallback for testing)
            result = conn.execute("""
                SELECT 
                    id,
                    content,
                    COALESCE(
                        llm_generate_json(
                            'Extract the high-level goal from: ' || content || 
                            '. Return JSON with key "goal".',
                            'gpt-oss',
                            'http://localhost:11434',
                            300
                        ),
                        '{"goal": "General Task Processing"}'
                    ) as llm_analysis
                FROM test_memories
                LIMIT 1
            """).fetchone()
            
            self.assertIsNotNone(result)
            self.assertIsNotNone(result[2])  # LLM analysis result


class TestLLMIntegrationEndToEnd(unittest.TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        """Set up end-to-end test environment"""
        self.test_dir = Path(__file__).parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)
        
        # Only run if Ollama is available
        self.ollama_available = self._check_ollama_availability()
        
    def _check_ollama_availability(self):
        """Check if Ollama service is available for testing"""
        try:
            import requests
            response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def test_end_to_end_llm_workflow(self):
        """Test complete LLM workflow if Ollama is available"""
        if not self.ollama_available:
            self.skipTest("Ollama service not available for end-to-end testing")
        
        # Initialize real LLM service
        service = initialize_llm_service(
            ollama_url="http://127.0.0.1:11434",
            model_name="gpt-oss:20b"
        )
        
        # Test health check
        health = service.health_check()
        self.assertEqual(health['status'], 'healthy')
        
        # Test actual LLM generation
        test_prompt = """Extract the high-level goal from this content: Working on quarterly business review presentation.
        Return JSON with key "goal" containing one of: Product Launch Strategy, Communication and Collaboration,
        Financial Planning and Management, Project Management and Execution."""
        
        response = service.generate_response(test_prompt, timeout=30)
        
        self.assertIsNotNone(response.content)
        self.assertIsNone(response.error)
        self.assertGreater(response.response_time_ms, 0)
        
        # Test caching (second call should be faster)
        start_time = time.time()
        cached_response = service.generate_response(test_prompt, timeout=30)
        cache_time = time.time() - start_time
        
        self.assertTrue(cached_response.cached)
        self.assertLess(cache_time, 0.1)  # Should be very fast from cache


class TestLLMIntegrationPerformance(unittest.TestCase):
    """Performance tests for LLM integration"""
    
    def setUp(self):
        """Set up performance test environment"""
        self.test_dir = Path(__file__).parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)
        
        self.cache_db_path = str(self.test_dir / "perf_llm_cache.duckdb")
    
    def tearDown(self):
        """Clean up performance test data"""
        try:
            if Path(self.cache_db_path).exists():
                Path(self.cache_db_path).unlink()
        except Exception:
            pass
    
    @patch('requests.Session.post')
    def test_concurrent_requests_performance(self, mock_post):
        """Test performance under concurrent requests"""
        # Mock fast response
        mock_response = Mock()
        mock_response.json.return_value = {
            'response': '{"goal": "Test Goal"}',
            'eval_count': 10
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        service = OllamaLLMService(
            ollama_url="http://127.0.0.1:11434",
            cache_db_path=self.cache_db_path
        )
        
        # Test multiple requests
        start_time = time.time()
        responses = []
        
        for i in range(10):
            response = service.generate_response(f"Test prompt {i}")
            responses.append(response)
        
        total_time = time.time() - start_time
        
        # Verify all responses
        self.assertEqual(len(responses), 10)
        for response in responses:
            self.assertIsNone(response.error)
            self.assertIsNotNone(response.content)
        
        # Performance should be reasonable
        self.assertLess(total_time, 5.0)  # Should complete in under 5 seconds
    
    def test_cache_hit_performance(self):
        """Test cache performance improvement"""
        service = OllamaLLMService(
            ollama_url="http://127.0.0.1:11434",
            cache_db_path=self.cache_db_path
        )
        
        # Prime cache with mock data
        test_response = LLMResponse(
            content='{"test": "cached_response"}',
            parsed_json={"test": "cached_response"},
            tokens_used=5,
            response_time_ms=50,
            model_name="test-model"
        )
        
        prompt_hash = service._generate_prompt_hash("test prompt", service.model_name)
        service._cache_response(prompt_hash, "test prompt", test_response)
        
        # Measure cache retrieval time
        start_time = time.time()
        cached_response = service._get_cached_response(prompt_hash)
        cache_time = time.time() - start_time
        
        self.assertIsNotNone(cached_response)
        self.assertTrue(cached_response.cached)
        self.assertLess(cache_time, 0.01)  # Should be very fast


if __name__ == '__main__':
    # Configure logging for test runs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    unittest.main(verbosity=2)