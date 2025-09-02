"""
LLM Integration Service - Ollama integration for memory processing
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM service"""

    content: str
    model: str
    latency_ms: float
    metadata: Optional[Dict[str, Any]] = None


class LLMIntegrationService:
    """Service for integrating with Ollama LLM"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gpt-oss:20b",
        model_name: str = None,
        timeout: int = 30,
        cache_db_path: str = None,
    ):
        self.base_url = base_url.rstrip("/")
        # Support both model and model_name parameters for compatibility
        self.model = model_name or model
        self.timeout = timeout
        self.cache_db_path = cache_db_path
        self.session = self._create_session()
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_response_time": 0.0,
        }
        logger.info(f"LLM service initialized: {base_url} with model {self.model}")

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic"""
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate text using LLM"""
        start_time = time.time()
        self.metrics["total_requests"] += 1

        payload = {
            "model": kwargs.get("model", self.model),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "max_tokens": kwargs.get("max_tokens", 500),
            },
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/generate", json=payload, timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            latency = (time.time() - start_time) * 1000

            self.metrics["successful_requests"] += 1
            # Update average response time
            total_requests = self.metrics["total_requests"]
            self.metrics["avg_response_time"] = (
                self.metrics["avg_response_time"] * (total_requests - 1) + latency
            ) / total_requests
            return LLMResponse(
                content=data.get("response", ""),
                model=data.get("model", self.model),
                latency_ms=latency,
                metadata=data,
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"LLM generation failed: {e}")
            self.metrics["failed_requests"] += 1
            # Return mock response for testing
            return LLMResponse(
                content="[Mock response due to connection error]",
                model=self.model,
                latency_ms=0,
                metadata={"error": str(e), "mock": True},
            )

    def extract_entities(self, text: str) -> List[str]:
        """Extract entities from text"""
        prompt = f"Extract key entities from this text (return as comma-separated list): {text}"
        response = self.generate(prompt, temperature=0.3)
        entities = [e.strip() for e in response.content.split(",")]
        return entities[:10]  # Limit to 10 entities

    def calculate_importance(self, text: str) -> float:
        """Calculate importance score for text"""
        prompt = (
            f"Rate the importance of this text on a scale of 0-1 (return only the number): {text}"
        )
        response = self.generate(prompt, temperature=0.1)
        try:
            score = float(response.content.strip())
            return max(0.0, min(1.0, score))
        except (ValueError, AttributeError):
            return 0.5  # Default importance

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [0.0] * 384)  # Default 384-dim vector
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return mock embedding for testing
            import random

            return [random.random() for _ in range(384)]

    def health_check(self) -> Dict[str, Any]:
        """Check LLM service health"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return {
                "status": "healthy",
                "endpoint": self.base_url,
                "model": self.model,
                "models": response.json(),
                "metrics": self.metrics,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "endpoint": self.base_url,
                "error": str(e),
                "metrics": self.metrics,
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        metrics = self.metrics.copy()

        # Add calculated metrics
        total_cache_requests = metrics.get("cache_hits", 0) + metrics.get("cache_misses", 0)
        if total_cache_requests > 0:
            metrics["cache_hit_rate_percent"] = (
                metrics.get("cache_hits", 0) / total_cache_requests
            ) * 100
        else:
            metrics["cache_hit_rate_percent"] = 0.0

        # Add service details
        metrics["model"] = self.model
        metrics["endpoint"] = self.base_url
        metrics["timestamp"] = time.time()

        return metrics


# Module-level service instance
_llm_service = None


def initialize_llm_service(
    base_url: str = None, model: str = None, model_name: str = None, cache_db_path: str = None
) -> LLMIntegrationService:
    """Initialize the global LLM service"""
    global _llm_service
    # Support both 'model' and 'model_name' parameters for compatibility
    effective_model = model or model_name or os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
    _llm_service = LLMIntegrationService(
        base_url=base_url or os.getenv("OLLAMA_URL", "http://localhost:11434"),
        model=effective_model,
        cache_db_path=cache_db_path,
    )
    return _llm_service


def get_llm_service() -> LLMIntegrationService:
    """Get the global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = initialize_llm_service()
    return _llm_service


def llm_generate(prompt: str, **kwargs) -> str:
    """Generate text using the global LLM service"""
    service = get_llm_service()
    response = service.generate(prompt, **kwargs)
    return response.content


def llm_generate_embedding(text: str) -> List[float]:
    """Generate embedding using the global LLM service"""
    service = get_llm_service()
    return service.generate_embedding(text)


def llm_generate_json(prompt: str, **kwargs) -> Dict[str, Any]:
    """Generate JSON response using the global LLM service"""
    service = get_llm_service()
    response = service.generate(prompt, **kwargs)
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON response", "raw": response.content}


# Alias for compatibility
OllamaLLMService = LLMIntegrationService


def llm_health_check() -> str:
    """Check health of LLM service and return as JSON string"""
    service = get_llm_service()
    health_data = service.health_check()
    return json.dumps(health_data)


def llm_health_check_json() -> str:
    """Check health of LLM service and return as JSON string for DuckDB"""
    health_data = llm_health_check()
    return json.dumps(health_data)


def llm_metrics() -> Dict[str, Any]:
    """Get LLM service metrics"""
    service = get_llm_service()
    return {
        "model": service.model,
        "base_url": service.base_url,
        "timeout": service.timeout,
        "health": service.health_check(),
    }


def prompt(text: str, **kwargs) -> str:
    """Alias for llm_generate matching ARCHITECTURE.md spec"""
    return llm_generate(text, **kwargs)


def prompt_simple(text: str) -> str:
    """Simple prompt function for DuckDB UDF with single parameter"""
    return llm_generate(text)


def prompt_full(text: str, provider: str, url: str, model: str, timeout: int) -> str:
    """Full prompt function with all parameters for DuckDB UDF"""
    # For now, we'll use the global service but could extend to use these parameters
    # In a production system, this would create a service with the provided
    # parameters
    return llm_generate(text)


def register_llm_functions(conn) -> bool:
    """Register LLM functions with DuckDB connection"""
    try:
        # Register prompt function with full parameters for DuckDB (text,
        # provider, url, model, timeout)
        conn.create_function("prompt", prompt_full, [str, str, str, str, int], str)

        # Register simplified prompt function
        conn.create_function("llm_generate", prompt, [str], str)

        # Register JSON generation with wrapper that returns JSON as string
        def _json_wrapper(text: str) -> str:
            result = llm_generate_json(text)
            return json.dumps(result) if isinstance(result, dict) else str(result)

        conn.create_function("llm_generate_json", _json_wrapper, [str], str)

        # Register embedding generation
        def _embed_wrapper(text: str) -> str:
            embedding = llm_generate_embedding(text)
            return json.dumps(embedding)

        conn.create_function("llm_generate_embedding", _embed_wrapper, [str], str)

        # Register health check function
        conn.create_function("llm_health_check", llm_health_check_json, [], str)

        # Register metrics function
        def _metrics_wrapper() -> str:
            metrics = llm_metrics()
            return json.dumps(metrics) if isinstance(metrics, dict) else str(metrics)

        conn.create_function("llm_metrics", _metrics_wrapper, [], str)

        return True
    except Exception as e:
        logger.error(f"Failed to register LLM functions: {e}")
        return False
