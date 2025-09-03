"""
Real service fixtures for external service dependencies.

Provides real implementations for Ollama LLM service
and database connections, enabling authentic testing with live services.
"""

import json
import os
import time
from typing import Any, Dict, Optional

import duckdb
import psycopg2
import pytest
import requests


@pytest.fixture(scope="session")
def real_ollama_service():
    """Real Ollama service connection for authentic testing."""
    ollama_url = os.getenv("OLLAMA_URL", "http://192.168.1.110:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
    embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

    class RealOllamaService:
        def __init__(self):
            self.url = ollama_url
            self.model = ollama_model
            self.embedding_model = embedding_model
            self._verify_service()

        def _verify_service(self):
            """Verify Ollama service is available and models are loaded - STRICT VERIFICATION."""
            try:
                response = requests.get(f"{self.url}/api/tags", timeout=2)
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Ollama service not available at {self.url} - status {response.status_code}"
                    )

                models = [m["name"] for m in response.json().get("models", [])]

                # Check if main model is available (exact match or with :latest tag)
                model_available = self.model in models or f"{self.model}:latest" in models
                if not model_available:
                    raise RuntimeError(
                        f"Model {self.model} not available. Available models: {models}"
                    )

                # Check if embedding model is available (exact match or with :latest tag)
                embedding_available = (
                    self.embedding_model in models or f"{self.embedding_model}:latest" in models
                )
                if not embedding_available:
                    raise RuntimeError(
                        f"Embedding model {self.embedding_model} not available. Available models: {models}"
                    )

                # Use the exact model name that exists (prefer without :latest tag)
                if self.model not in models and f"{self.model}:latest" in models:
                    self.model = f"{self.model}:latest"
                if (
                    self.embedding_model not in models
                    and f"{self.embedding_model}:latest" in models
                ):
                    self.embedding_model = f"{self.embedding_model}:latest"

                print(
                    f"✓ Verified real Ollama service at {self.url} with models {self.model}, {self.embedding_model}"
                )

            except Exception as e:
                raise RuntimeError(
                    f"Cannot connect to real Ollama service at {self.url}: {e}"
                ) from e

        def generate(self, prompt: str, **kwargs) -> str:
            """Generate text using REAL Ollama service - NO FALLBACKS."""
            try:
                response = requests.post(
                    f"{self.url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False, **kwargs},
                    timeout=5,  # Short timeout for tests
                )
                response.raise_for_status()
                result = response.json().get("response", "")

                # Ensure we got actual LLM response, not empty or error
                if not result or "generated response for prompt" in result.lower():
                    raise ValueError(f"Real Ollama service returned invalid response: {result}")

                return result
            except Exception as e:
                # NO FALLBACKS - fail the test if service is not working
                raise RuntimeError(
                    f"Real Ollama service failed - test requires actual LLM: {str(e)}"
                ) from e

        def embed(self, text: str) -> list:
            """Generate embeddings using REAL Ollama service - NO FALLBACKS."""
            try:
                response = requests.post(
                    f"{self.url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                    timeout=5,  # Short timeout for tests
                )
                response.raise_for_status()
                embedding = response.json().get("embedding", [])

                # Ensure we got actual embedding, not empty
                if not embedding or len(embedding) == 0:
                    raise ValueError(f"Real Ollama embedding service returned empty embedding")

                return embedding
            except Exception as e:
                # NO FALLBACKS - fail the test if service is not working
                raise RuntimeError(
                    f"Real Ollama embedding service failed - test requires actual embeddings: {str(e)}"
                ) from e

    return RealOllamaService()


@pytest.fixture(scope="function")
def real_ollama(real_ollama_service):
    """Function-scoped real Ollama service for tests."""
    return real_ollama_service


@pytest.fixture(scope="session")
def real_postgres_connection():
    """Real PostgreSQL connection for testing."""
    postgres_url = os.getenv("POSTGRES_DB_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_DB_URL not configured")

    try:
        conn = psycopg2.connect(postgres_url)
        conn.autocommit = True
        yield conn
        conn.close()
    except Exception as e:
        pytest.skip(f"Cannot connect to PostgreSQL: {e}")


@pytest.fixture(scope="function")
def clean_test_database(real_postgres_connection):
    """Clean test database between tests."""
    conn = real_postgres_connection
    with conn.cursor() as cur:
        # Clean up any test data
        cur.execute("DELETE FROM processed_memories WHERE content LIKE 'Test%'")
        cur.execute("DELETE FROM insights WHERE content LIKE 'Test%'")

    yield conn


@pytest.fixture(scope="function")
def real_duckdb_connection():
    """Real DuckDB connection for testing."""
    import os
    import tempfile

    # Create temporary DuckDB file for testing
    temp_db = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
    temp_path = temp_db.name
    temp_db.close()

    # Remove the file if it exists to ensure clean start
    if os.path.exists(temp_path):
        os.unlink(temp_path)

    try:
        conn = duckdb.connect(temp_path)

        # Load required extensions
        try:
            conn.execute("INSTALL postgres")
            conn.execute("LOAD postgres")

            # Attach PostgreSQL if available
            postgres_url = os.getenv("POSTGRES_DB_URL")
            if postgres_url:
                conn.execute(f"ATTACH '{postgres_url}' AS postgres_db (TYPE postgres)")
        except BaseException:
            pass  # Extensions may not be available in all environments

        yield conn
        conn.close()
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


# Renamed to avoid conflict with test_data.py
@pytest.fixture(scope="function")
def memory_lifecycle_data_mock(real_duckdb_connection):
    """Create test data for memory lifecycle testing - mock version."""
    conn = real_duckdb_connection

    # Create test tables
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_memories (
            id INTEGER PRIMARY KEY,
            content TEXT,
            timestamp TIMESTAMP,
            metadata JSON
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS working_memory_view (
            id INTEGER PRIMARY KEY,
            content TEXT,
            activation_level FLOAT,
            miller_capacity_position INTEGER
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stm_hierarchical_episodes (
            id INTEGER PRIMARY KEY,
            content TEXT,
            level_0_goal TEXT,
            level_1_tasks TEXT,
            ready_for_consolidation BOOLEAN,
            stm_strength FLOAT
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ltm_semantic_network (
            concept_a TEXT,
            concept_b TEXT,
            association_strength FLOAT,
            association_type TEXT,
            consolidation_timestamp TIMESTAMP
        )
    """
    )

    # Insert test data
    from datetime import datetime, timezone

    for i in range(5):
        conn.execute(
            "INSERT INTO raw_memories (id, content, timestamp, metadata) VALUES (?, ?, ?, ?)",
            (i, f"Test memory {i}", datetime.now(timezone.utc), '{"importance": 0.8}'),
        )

    # Create working memory entries (respecting Miller's 7±2)
    for i in range(min(7, 5)):
        conn.execute(
            "INSERT INTO working_memory_view (id, content, activation_level, miller_capacity_position) VALUES (?, ?, ?, ?)",
            (i, f"Test memory {i}", 0.8, i + 1),
        )

    # Create STM episodes
    for i in range(3):
        conn.execute(
            "INSERT INTO stm_hierarchical_episodes (id, content, level_0_goal, level_1_tasks, ready_for_consolidation, stm_strength) VALUES (?, ?, ?, ?, ?, ?)",
            (i, f"Episode {i}", f"Goal {i}", f"Task {i}", i > 0, 0.7 + i * 0.1),
        )

    return conn


# Renamed to avoid conflict with database.py
@pytest.fixture(scope="function")
def biological_memory_schema_mock(real_duckdb_connection):
    """Create biological memory schema for testing - mock version."""
    conn = real_duckdb_connection

    # Create the biological memory tables needed for testing
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_memories (
            id INTEGER PRIMARY KEY,
            content TEXT,
            metadata JSON
        )
    """
    )

    # Create working memory view table for capacity testing
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS working_memory_view (
            id INTEGER PRIMARY KEY,
            content TEXT,
            activation_level FLOAT,
            miller_capacity_position INTEGER
        )
    """
    )

    # Create STM hierarchical episodes table for hierarchy testing
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stm_hierarchical_episodes (
            id INTEGER PRIMARY KEY,
            content TEXT,
            level_0_goal TEXT,
            level_1_tasks TEXT,
            atomic_actions TEXT,
            stm_strength FLOAT
        )
    """
    )

    return conn
