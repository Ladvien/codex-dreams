"""
Mocking fixtures for external service dependencies.

Provides realistic mock implementations for Ollama LLM service
and HTTP requests, enabling offline testing with deterministic responses.
"""

import json
import random
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(scope="function")
def mock_ollama():
    """Mock Ollama responses for offline testing with realistic biological data."""

    # Comprehensive mock responses for different biological memory operations
    mock_responses = {
        "extraction": {
            "entities": ["person", "organization", "location", "task"],
            "topics": ["meeting", "planning", "collaboration", "decision_making"],
            "sentiment": "positive",
            "importance": 0.8,
            "task_type": "goal",
            "objects": ["laptop", "notebook", "whiteboard", "documents"],
            "temporal_markers": ["today", "next week", "deadline"],
            "emotional_context": "focused_productive",
        },
        "hierarchy": {
            "goal": "Complete project milestone",
            "tasks": ["Review requirements", "Plan implementation", "Coordinate team"],
            "actions": ["Open document", "Take notes", "Schedule follow-up"],
            "time_pointer": "sequential",
            "dependencies": ["approval needed", "resource allocation"],
            "priority_level": "high",
        },
        "spatial": {
            "location": "conference room",
            "egocentric": "in front of me",
            "allocentric": "north wall",
            "objects": [
                {"name": "whiteboard", "position": "wall", "distance": "near"},
                {"name": "projector", "position": "ceiling", "distance": "above"},
                {"name": "table", "position": "center", "distance": "immediate"},
            ],
            "spatial_relationships": ["adjacent_to_door", "facing_screen"],
            "environmental_context": "indoor_meeting_space",
        },
        "associations": [
            {"concept": "collaboration", "strength": 0.9, "type": "semantic"},
            {"concept": "productivity", "strength": 0.7, "type": "functional"},
            {"concept": "teamwork", "strength": 0.85, "type": "social"},
            {"concept": "planning", "strength": 0.75, "type": "procedural"},
        ],
        "semantic_gist": "Team planning session for project milestone with collaborative discussion",
        "category": "work_meeting",
        "subcategory": "project_planning",
        "region": "prefrontal_cortex",
        "confidence": 0.92,
        "similarity": 0.85,
        "creative_link": "Both involve problem-solving and creative thinking",
        "consolidation_potential": 0.78,
        "retrieval_cues": ["team", "project", "milestone", "planning"],
        "memory_strength": 0.65,
        "forgetting_curve_position": 0.3,
    }

    def mock_prompt(prompt_text: str, **kwargs) -> str:
        """Mock the DuckDB prompt() function with context-aware responses."""
        prompt_lower = prompt_text.lower()

        if "extract" in prompt_lower or "entities" in prompt_lower:
            return json.dumps(mock_responses["extraction"])
        elif "hierarchy" in prompt_lower or "goal" in prompt_lower or "task" in prompt_lower:
            return json.dumps(mock_responses["hierarchy"])
        elif "spatial" in prompt_lower or "location" in prompt_lower:
            return json.dumps(mock_responses["spatial"])
        elif "association" in prompt_lower or "relate" in prompt_lower:
            return json.dumps(mock_responses["associations"])
        elif "gist" in prompt_lower or "summary" in prompt_lower or "summarize" in prompt_lower:
            return json.dumps(
                {
                    "gist": mock_responses["semantic_gist"],
                    "category": mock_responses["category"],
                    "subcategory": mock_responses["subcategory"],
                    "region": mock_responses["region"],
                    "confidence": mock_responses["confidence"],
                }
            )
        elif "similarity" in prompt_lower or "compare" in prompt_lower:
            return str(mock_responses["similarity"])
        elif "creative" in prompt_lower or "connect" in prompt_lower:
            return mock_responses["creative_link"]
        elif "consolidation" in prompt_lower or "consolidate" in prompt_lower:
            return json.dumps(
                {
                    "consolidation_potential": mock_responses["consolidation_potential"],
                    "memory_strength": mock_responses["memory_strength"],
                    "retrieval_cues": mock_responses["retrieval_cues"],
                }
            )
        elif "forget" in prompt_lower or "decay" in prompt_lower:
            return json.dumps(
                {
                    "forgetting_curve_position": mock_responses["forgetting_curve_position"],
                    "retention_probability": 0.7,
                    "decay_rate": 0.05,
                }
            )
        elif "embed" in prompt_lower or "vector" in prompt_lower:
            # Mock embedding vector (384 dimensions for nomic-embed-text)
            random.seed(hash(prompt_text) % 2147483647)  # Deterministic based on prompt
            embedding = [random.uniform(-1, 1) for _ in range(384)]
            return json.dumps({"embedding": embedding})
        else:
            return json.dumps(
                {"response": "Generic mock response", "prompt_type": "unknown", "confidence": 0.5}
            )

    with patch("duckdb.DuckDBPyConnection.execute") as mock_execute:
        # Configure mock to handle prompt() function calls
        def side_effect(query: str):
            if "prompt(" in query:
                return Mock(fetchall=lambda: [(mock_prompt(query),)])
            else:
                return Mock(fetchall=lambda: [])

        mock_execute.side_effect = side_effect
        yield mock_prompt


@pytest.fixture(scope="function")
def mock_http_requests():
    """Mock HTTP requests to Ollama server for integration testing."""
    import responses

    @responses.activate
    def _mock_requests():
        # Mock embedding endpoint
        responses.add(
            responses.POST,
            "http://localhost:11434/api/embeddings",
            json={"embedding": [0.1, 0.2, 0.3] * 128},  # Mock 384-dim embedding
            status=200,
        )

        # Mock generation endpoint
        responses.add(
            responses.POST,
            "http://localhost:11434/api/generate",
            json={"response": "Mock LLM response"},
            status=200,
        )

        # Mock model list endpoint
        responses.add(
            responses.GET,
            "http://localhost:11434/api/tags",
            json={
                "models": [
                    {"name": "qwen2.5:0.5b", "size": 352000000},
                    {"name": "nomic-embed-text", "size": 274000000},
                ]
            },
            status=200,
        )

        return responses

    return _mock_requests


@pytest.fixture(scope="function")
def mock_ollama_server():
    """Mock complete Ollama server for end-to-end testing."""

    class MockOllamaServer:
        def __init__(self):
            self.models = ["qwen2.5:0.5b", "nomic-embed-text"]
            self.embedding_dim = 384

        def generate_response(self, prompt: str, model: str) -> Dict[str, Any]:
            """Generate realistic response based on prompt content."""
            if "extract" in prompt.lower():
                return {
                    "model": model,
                    "response": json.dumps(
                        {
                            "entities": ["meeting", "team", "project"],
                            "topics": ["collaboration", "planning"],
                            "sentiment": "positive",
                            "importance": 0.8,
                        }
                    ),
                    "done": True,
                }
            elif "embed" in prompt.lower():
                # Generate deterministic embedding
                random.seed(hash(prompt) % 2147483647)
                return {"embedding": [random.uniform(-1, 1) for _ in range(self.embedding_dim)]}
            else:
                return {
                    "model": model,
                    "response": f"Mock response for: {prompt[:50]}...",
                    "done": True,
                }

        def is_model_available(self, model: str) -> bool:
            """Check if model is available."""
            return model in self.models

    return MockOllamaServer()


@pytest.fixture(scope="function")
def mock_duckdb_extensions():
    """Mock DuckDB extension loading for environments without extensions."""

    def mock_extension_loader():
        """Mock extension loading that always succeeds."""
        return True

    with patch("duckdb.DuckDBPyConnection.execute") as mock_execute:
        original_execute = mock_execute.side_effect

        def extension_aware_execute(query: str):
            query_lower = query.lower().strip()
            if query_lower.startswith("install ") or query_lower.startswith("load "):
                # Mock successful extension operations
                return Mock(fetchall=lambda: [])
            else:
                # Pass through to original or other mock behavior
                if original_execute:
                    return original_execute(query)
                return Mock(fetchall=lambda: [])

        mock_execute.side_effect = extension_aware_execute
        yield mock_extension_loader


@pytest.fixture(scope="function")
def mock_environment_isolation():
    """Mock environment variables for test isolation."""
    import os

    original_env = {}
    test_env = {
        "DUCKDB_PATH": ":memory:",  # Use in-memory database for tests
        "POSTGRES_DB_URL": "postgresql://test:test@localhost:5432/test_db",
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_TIMEOUT": "5",  # Shorter timeout for tests
        "MAX_DB_CONNECTIONS": "50",  # Lower connection limit for tests
    }

    # Store original values
    for key in test_env:
        original_env[key] = os.environ.get(key)

    # Set test values
    for key, value in test_env.items():
        os.environ[key] = value

    yield test_env

    # Restore original values
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]
