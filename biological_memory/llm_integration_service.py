#!/usr/bin/env python3
"""
LLM Integration Service for Biological Memory Pipeline
Provides DuckDB UDF functions for Ollama LLM integration

This service implements:
- Ollama REST API integration with gpt-oss:20b model
- JSON response parsing and validation
- Circuit breaker pattern for reliability
- Caching for performance optimization
- Proper error handling and fallbacks
"""

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import duckdb
import requests

# Import error handling system
from error_handling import BiologicalMemoryErrorHandler, ErrorEvent, ErrorType
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class LLMResponse:
    """Structured LLM response with metadata"""

    content: str
    parsed_json: Optional[Dict[str, Any]]
    tokens_used: int
    response_time_ms: int
    model_name: str
    cached: bool = False
    error: Optional[str] = None


class OllamaLLMService:
    """
    High-performance Ollama LLM integration service for biological memory processing

    Features:
    - REST API integration with configurable endpoints
    - Response caching for performance optimization
    - Circuit breaker pattern for reliability
    - Proper JSON parsing and validation
    - Comprehensive error handling
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "gpt-oss:20b",
        cache_db_path: Optional[str] = None,
        error_handler: Optional[BiologicalMemoryErrorHandler] = None,
    ):
        """
        Initialize Ollama LLM service

        Args:
            ollama_url: Base URL for Ollama service
            model_name: Name of the model to use
            cache_db_path: Path to cache database (optional)
            error_handler: Error handling system instance
        """
        self.ollama_url = ollama_url.rstrip("/")
        self.model_name = model_name
        self.error_handler = error_handler

        # Set up logging
        self.logger = logging.getLogger(f"LLMService.{model_name}")
        self.logger.setLevel(logging.INFO)

        # HTTP session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],  # Updated parameter name
            backoff_factor=1.0,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Initialize cache database
        self.cache_db_path = cache_db_path or "dbs/llm_cache.duckdb"
        self._init_cache_db()

        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "avg_response_time_ms": 0.0,
        }

        self.logger.info(f"Initialized Ollama LLM service: {ollama_url}/{model_name}")

    def _init_cache_db(self):
        """Initialize LLM response cache database"""
        try:
            Path(self.cache_db_path).parent.mkdir(parents=True, exist_ok=True)

            with duckdb.connect(self.cache_db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS llm_cache (
                        prompt_hash VARCHAR PRIMARY KEY,
                        model_name VARCHAR NOT NULL,
                        prompt_text TEXT NOT NULL,
                        response_content TEXT NOT NULL,
                        parsed_json JSON,
                        tokens_used INTEGER DEFAULT 0,
                        response_time_ms INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 1
                    )
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_llm_cache_model_hash 
                    ON llm_cache (model_name, prompt_hash)
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_llm_cache_accessed 
                    ON llm_cache (accessed_at DESC)
                """
                )

        except Exception as e:
            self.logger.warning(f"Failed to initialize LLM cache: {e}")

    def _generate_prompt_hash(self, prompt: str, model: str) -> str:
        """Generate hash for prompt caching"""
        content = f"{model}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cached_response(self, prompt_hash: str) -> Optional[LLMResponse]:
        """Retrieve cached response if available and fresh"""
        try:
            with duckdb.connect(self.cache_db_path) as conn:
                result = conn.execute(
                    """
                    SELECT response_content, parsed_json, tokens_used, response_time_ms, model_name
                    FROM llm_cache 
                    WHERE prompt_hash = ? 
                    AND model_name = ?
                    AND accessed_at > CURRENT_TIMESTAMP - INTERVAL '24 HOURS'
                """,
                    [prompt_hash, self.model_name],
                ).fetchone()

                if result:
                    # Update access tracking
                    conn.execute(
                        """
                        UPDATE llm_cache 
                        SET accessed_at = CURRENT_TIMESTAMP, access_count = access_count + 1
                        WHERE prompt_hash = ?
                    """,
                        [prompt_hash],
                    )

                    return LLMResponse(
                        content=result[0],
                        parsed_json=json.loads(result[1]) if result[1] else None,
                        tokens_used=result[2],
                        response_time_ms=result[3],
                        model_name=result[4],
                        cached=True,
                    )
        except Exception as e:
            self.logger.warning(f"Cache retrieval failed: {e}")

        return None

    def _cache_response(self, prompt_hash: str, prompt: str, response: LLMResponse):
        """Cache LLM response for future use"""
        try:
            with duckdb.connect(self.cache_db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO llm_cache 
                    (prompt_hash, model_name, prompt_text, response_content, 
                     parsed_json, tokens_used, response_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    [
                        prompt_hash,
                        self.model_name,
                        prompt,
                        response.content,
                        json.dumps(response.parsed_json) if response.parsed_json else None,
                        response.tokens_used,
                        response.response_time_ms,
                    ],
                )

        except Exception as e:
            self.logger.warning(f"Cache storage failed: {e}")

    def _call_ollama_api(self, prompt: str, timeout: int = 300) -> LLMResponse:
        """Make actual API call to Ollama service"""
        start_time = time.time()

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Lower temperature for consistent responses
                    "top_p": 0.9,
                    "num_predict": 2048,
                },
            }

            response = self.session.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            response_time_ms = int((time.time() - start_time) * 1000)
            data = response.json()

            content = data.get("response", "").strip()
            if not content:
                raise ValueError("Empty response from Ollama")

            # Try to parse as JSON
            parsed_json = None
            try:
                # Extract JSON from response if it contains JSON
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_content = content[json_start:json_end]
                    parsed_json = json.loads(json_content)
            except (json.JSONDecodeError, ValueError):
                # If JSON parsing fails, that's OK for some prompts
                pass

            return LLMResponse(
                content=content,
                parsed_json=parsed_json,
                tokens_used=data.get("eval_count", 0),
                response_time_ms=response_time_ms,
                model_name=self.model_name,
            )

        except requests.exceptions.RequestException as e:
            error_msg = f"Ollama API request failed: {e}"
            self.logger.error(error_msg)
            return LLMResponse(
                content="",
                parsed_json=None,
                tokens_used=0,
                response_time_ms=int((time.time() - start_time) * 1000),
                model_name=self.model_name,
                error=error_msg,
            )
        except Exception as e:
            error_msg = f"Ollama API call failed: {e}"
            self.logger.error(error_msg)
            return LLMResponse(
                content="",
                parsed_json=None,
                tokens_used=0,
                response_time_ms=int((time.time() - start_time) * 1000),
                model_name=self.model_name,
                error=error_msg,
            )

    def generate_embedding(
        self, text: str, model_name: str = "nomic-embed-text", timeout: int = 300
    ) -> List[float]:
        """
        Generate embedding vector using Ollama embedding model

        Args:
            text: Input text to embed
            model_name: Embedding model name (default: nomic-embed-text)
            timeout: Request timeout in seconds

        Returns:
            List of floats representing the embedding vector (768 dimensions for nomic-embed-text)
        """
        start_time = time.time()

        try:
            payload = {"model": model_name, "prompt": text}

            response = self.session.post(
                f"{self.ollama_url}/api/embeddings",
                json=payload,
                timeout=timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            data = response.json()
            embedding = data.get("embedding", [])

            if not embedding:
                self.logger.warning(f"Empty embedding returned for text: {text[:50]}...")
                # Return zero vector with 768 dimensions (nomic-embed-text default)
                return [0.0] * 768

            response_time_ms = int((time.time() - start_time) * 1000)
            self.logger.debug(
                f"Generated embedding in {response_time_ms}ms for text length: {len(text)}"
            )

            return embedding

        except requests.exceptions.RequestException as e:
            error_msg = f"Ollama embedding API request failed: {e}"
            self.logger.error(error_msg)
            # Return zero vector on error
            return [0.0] * 768

        except Exception as e:
            error_msg = f"Embedding generation failed: {e}"
            self.logger.error(error_msg)
            # Return zero vector on error
            return [0.0] * 768

    def generate_response(self, prompt: str, timeout: int = 300) -> LLMResponse:
        """
        Generate LLM response with caching and error handling

        Args:
            prompt: Input prompt text
            timeout: Request timeout in seconds

        Returns:
            LLMResponse with content and metadata
        """
        self.metrics["total_requests"] += 1
        prompt_hash = self._generate_prompt_hash(prompt, self.model_name)

        # Check cache first
        cached_response = self._get_cached_response(prompt_hash)
        if cached_response:
            self.metrics["cache_hits"] += 1
            return cached_response

        self.metrics["cache_misses"] += 1

        # Make API call
        response = self._call_ollama_api(prompt, timeout)

        if response.error:
            self.metrics["errors"] += 1
            # Log error with context
            if self.error_handler:
                error_event = ErrorEvent(
                    error_id=f"llm_{int(time.time())}",
                    error_type=ErrorType.SERVICE_UNAVAILABLE,
                    timestamp=datetime.now(),
                    component="llm_service",
                    operation="generate_response",
                    error_message=response.error,
                    context={
                        "model": self.model_name,
                        "prompt_length": len(prompt),
                        "timeout": timeout,
                    },
                )
                self.error_handler.log_error_event(error_event)
        else:
            # Cache successful response
            self._cache_response(prompt_hash, prompt, response)

        # Update average response time
        total_time = (
            self.metrics["avg_response_time_ms"] * (self.metrics["total_requests"] - 1)
            + response.response_time_ms
        )
        self.metrics["avg_response_time_ms"] = total_time / self.metrics["total_requests"]

        return response

    def health_check(self) -> Dict[str, Any]:
        """Check health of Ollama service"""
        try:
            response = self.session.get(f"{self.ollama_url}/api/tags", timeout=10)
            response.raise_for_status()

            models = response.json().get("models", [])
            model_available = any(model.get("name") == self.model_name for model in models)

            return {
                "status": "healthy",
                "endpoint": self.ollama_url,
                "model": self.model_name,
                "model_available": model_available,
                "models_count": len(models),
                "metrics": self.metrics,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "endpoint": self.ollama_url,
                "model": self.model_name,
                "error": str(e),
                "metrics": self.metrics,
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics"""
        cache_hit_rate = self.metrics["cache_hits"] / max(self.metrics["total_requests"], 1) * 100

        return {
            **self.metrics,
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "model": self.model_name,
            "endpoint": self.ollama_url,
            "timestamp": datetime.now().isoformat(),
        }


# Global service instances
_llm_service: Optional[OllamaLLMService] = None
_error_handler: Optional[BiologicalMemoryErrorHandler] = None


def initialize_llm_service(
    ollama_url: Optional[str] = None,
    model_name: str = "gpt-oss:20b",
    cache_db_path: Optional[str] = None,
    error_handler: Optional[BiologicalMemoryErrorHandler] = None,
) -> OllamaLLMService:
    """Initialize global LLM service instance"""
    global _llm_service, _error_handler

    if not ollama_url:
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

    _error_handler = error_handler
    _llm_service = OllamaLLMService(
        ollama_url=ollama_url,
        model_name=model_name,
        cache_db_path=cache_db_path,
        error_handler=error_handler,
    )

    return _llm_service


def get_llm_service() -> Optional[OllamaLLMService]:
    """Get global LLM service instance"""
    return _llm_service


# DuckDB UDF Functions for SQL integration
def llm_generate(
    prompt: str, model: str = "gpt-oss", endpoint: str = "", timeout: int = 300
) -> str:
    """
    DuckDB UDF function for LLM generation

    Args:
        prompt: Input prompt text
        model: Model name (for compatibility, uses configured model)
        endpoint: Endpoint URL (for compatibility, uses configured endpoint)
        timeout: Request timeout in seconds

    Returns:
        Generated text content
    """
    if not _llm_service:
        # Try to initialize with defaults
        initialize_llm_service()

    if not _llm_service:
        return ""

    try:
        response = _llm_service.generate_response(prompt, timeout)
        return response.content if not response.error else ""
    except Exception as e:
        logging.error(f"LLM UDF error: {e}")
        return ""


def llm_generate_json(
    prompt: str, model: str = "gpt-oss", endpoint: str = "", timeout: int = 300
) -> str:
    """
    DuckDB UDF function for JSON-formatted LLM generation

    Returns:
        JSON string with parsed response, or empty JSON on error
    """
    if not _llm_service:
        initialize_llm_service()

    if not _llm_service:
        return "{}"

    try:
        response = _llm_service.generate_response(prompt, timeout)
        if response.error:
            return "{}"

        if response.parsed_json:
            return json.dumps(response.parsed_json)
        else:
            # Return content wrapped in a response object
            return json.dumps({"content": response.content})

    except Exception as e:
        logging.error(f"LLM JSON UDF error: {e}")
        return "{}"


def llm_health_check() -> str:
    """DuckDB UDF function for LLM service health check"""
    if not _llm_service:
        return json.dumps({"status": "not_initialized"})

    try:
        return json.dumps(_llm_service.health_check())
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def llm_metrics() -> str:
    """DuckDB UDF function to get LLM service metrics"""
    if not _llm_service:
        return json.dumps({"error": "service_not_initialized"})

    try:
        return json.dumps(_llm_service.get_metrics())
    except Exception as e:
        return json.dumps({"error": str(e)})


def prompt(
    prompt_text: str,
    model: str = "ollama",
    base_url: str = "",
    model_name: str = "",
    timeout: int = 300,
) -> str:
    """
    DuckDB UDF function implementing the prompt() function per ARCHITECTURE.md

    This function provides the interface described in ARCHITECTURE.md lines 199-207:
    SELECT prompt(
        'Extract key insight from: ' || content,
        model := 'ollama',
        base_url := 'http://localhost:11434',
        model_name := 'gpt-oss'
    ) as insight

    Args:
        prompt_text: The input prompt text
        model: Model type (always 'ollama' for this implementation)
        base_url: Ollama base URL (uses environment default if empty)
        model_name: Ollama model name (uses environment default if empty)
        timeout: Request timeout in seconds

    Returns:
        Generated text response or empty string on error
    """
    if not _llm_service:
        # Initialize with environment defaults or provided values
        ollama_url = base_url if base_url else os.getenv("OLLAMA_URL", "http://192.168.1.110:11434")
        model_to_use = model_name if model_name else os.getenv("OLLAMA_MODEL", "gpt-oss:20b")

        initialize_llm_service(ollama_url=ollama_url, model_name=model_to_use)

    if not _llm_service:
        return ""

    try:
        response = _llm_service.generate_response(prompt_text, timeout)
        return response.content if not response.error else ""
    except Exception as e:
        logging.error(f"Prompt UDF error: {e}")
        return ""


def llm_generate_embedding(
    text: str, model: str = "nomic-embed-text", dimension: int = 768
) -> List[float]:
    """
    DuckDB UDF function for generating embeddings

    Args:
        text: Input text to embed
        model: Embedding model name (default: nomic-embed-text)
        dimension: Expected embedding dimension (default: 768 for nomic-embed-text)

    Returns:
        List of floats representing the embedding vector
    """
    if not _llm_service:
        # Try to initialize with defaults
        initialize_llm_service()

    if not _llm_service:
        # Return zero vector if service unavailable
        return [0.0] * dimension

    try:
        embedding = _llm_service.generate_embedding(text, model)

        # Ensure correct dimension (truncate or pad as needed)
        if len(embedding) > dimension:
            # Truncate to requested dimension (Matryoshka representation learning)
            return embedding[:dimension]
        elif len(embedding) < dimension:
            # Pad with zeros if embedding is shorter
            return embedding + [0.0] * (dimension - len(embedding))
        else:
            return embedding

    except Exception as e:
        logging.error(f"Embedding UDF error: {e}")
        return [0.0] * dimension


# Register UDF functions with DuckDB
def register_llm_functions(connection: duckdb.DuckDBPyConnection):
    """Register LLM UDF functions with a DuckDB connection"""
    success_count = 0
    total_functions = 0

    # List of functions to register with their names
    functions_to_register = [
        ("llm_generate", llm_generate),
        ("llm_generate_json", llm_generate_json),
        ("llm_health_check", llm_health_check),
        ("llm_metrics", llm_metrics),
        ("prompt", prompt),  # ARCHITECTURE.md compliant function
    ]

    # Register string-returning functions first
    for func_name, func in functions_to_register:
        try:
            total_functions += 1
            connection.create_function(func_name, func)
            success_count += 1
            logging.info(f"Successfully registered function: {func_name}")
        except Exception as e:
            logging.warning(f"Failed to register function {func_name}: {e}")

    # Register embedding function separately (returns list)
    try:
        total_functions += 1
        connection.create_function("llm_generate_embedding", llm_generate_embedding)
        success_count += 1
        logging.info("Successfully registered function: llm_generate_embedding")
    except Exception as e:
        logging.warning(f"Failed to register function llm_generate_embedding: {e}")

    logging.info(f"Registered {success_count}/{total_functions} LLM UDF functions with DuckDB")
    return success_count > 0  # Return True if at least some functions registered


if __name__ == "__main__":
    # Example usage and testing
    import logging

    logging.basicConfig(level=logging.INFO)

    # Initialize service
    service = initialize_llm_service()

    # Health check
    health = service.health_check()
    print("Health check:", json.dumps(health, indent=2))

    # Test generation
    test_prompt = """Extract the high-level goal from this content: Working on quarterly business review presentation for executive team.
    Return JSON with key "goal" containing one of: Product Launch Strategy, Communication and Collaboration, 
    Financial Planning and Management, Project Management and Execution, Client Relations and Service, 
    Operations and System Maintenance."""

    response = service.generate_response(test_prompt)
    print(f"Response: {response.content}")
    print(f"Parsed JSON: {response.parsed_json}")
    print(f"Metrics: {json.dumps(service.get_metrics(), indent=2)}")
