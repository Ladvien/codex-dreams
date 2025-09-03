"""
Test fixtures for the Biological Memory Pipeline.

This module provides modular test fixtures organized by concern:
- database.py: Database connections and schema setup
- mocking.py: Mock implementations for external services
- test_data.py: Test data factories and realistic biological memory scenarios

All fixtures support proper test isolation and parallel execution.
"""

# Import all fixtures for easy access
from .database import (
    TEST_CONSOLIDATION_THRESHOLD,
    TEST_FORGETTING_RATE,
    TEST_HEBBIAN_RATE,
    TEST_MEMORY_CAPACITY,
    TEST_STM_DURATION,
    biological_memory_schema,
    isolated_test_db,
    test_duckdb,
    test_postgres_connection,
    transactional_duckdb,
)
from .mocking import memory_lifecycle_data_mock  # Renamed to avoid conflict
from .mocking import (
    clean_test_database,
    real_duckdb_connection,
    real_ollama,
    real_ollama_service,
    real_postgres_connection,
)
from .test_data import memory_lifecycle_data  # The actual fixture from test_data.py
from .test_data import (
    MemoryDataFactory,
    hebbian_learning_data,
    performance_benchmark,
    performance_test_data,
    sample_memory_data,
    setup_test_environment,
    short_term_memory_fixture,
    test_env_vars,
    working_memory_fixture,
)

__all__ = [
    # Database fixtures
    "test_duckdb",
    "test_postgres_connection",
    "isolated_test_db",
    "biological_memory_schema",
    # Real service fixtures
    "real_ollama",
    "real_ollama_service",
    "real_postgres_connection",
    "real_duckdb_connection",
    # Test data fixtures
    "sample_memory_data",
    "working_memory_fixture",
    "short_term_memory_fixture",
    "hebbian_learning_data",
    "memory_lifecycle_data",
    "performance_test_data",
    # Environment fixtures
    "test_env_vars",
    "setup_test_environment",
    # Utility fixtures
    "performance_benchmark",
]
