"""
Database fixtures for biological memory testing.

Provides isolated DuckDB and PostgreSQL connections with proper cleanup,
schema setup, and transaction-based test isolation.
"""

import os
import tempfile
from typing import Generator

import duckdb
import pytest


@pytest.fixture(scope="function")
def test_duckdb() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Create isolated test DuckDB instance with proper cleanup."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".duckdb") as f:
        db_path = f.name

    # Ensure file is removed if it exists
    if os.path.exists(db_path):
        os.unlink(db_path)

    conn = duckdb.connect(db_path)

    # Install required extensions
    try:
        conn.execute("INSTALL json")
        conn.execute("LOAD json")
    except Exception:
        pass  # Extension might already be installed

    yield conn

    conn.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope="function")
def test_postgres_connection(test_env_vars):
    """Create isolated PostgreSQL test connection with proper cleanup."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    # Connect to test database
    test_db_url = test_env_vars["POSTGRES_DB_URL"]

    try:
        conn = psycopg2.connect(test_db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        # Create test schema with unique name for isolation
        test_schema = f"test_schema_{os.getpid()}_{id(conn)}"
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {test_schema}")

        yield conn, test_schema

        # Cleanup: Drop test schema after test
        with conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA IF EXISTS {test_schema} CASCADE")

        conn.close()
    except Exception:
        # If PostgreSQL connection fails, yield None (tests can check and skip)
        yield None, None


@pytest.fixture(scope="function")
def isolated_test_db(test_duckdb, test_postgres_connection):
    """Provide both DuckDB and PostgreSQL isolated test connections."""
    postgres_conn, schema = test_postgres_connection if test_postgres_connection else (None, None)
    return {"duckdb": test_duckdb, "postgres": postgres_conn, "postgres_schema": schema}


@pytest.fixture(scope="function")
def biological_memory_schema(test_duckdb):
    """Set up complete biological memory schema for testing."""
    conn = test_duckdb

    # Create all required tables for biological memory testing
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_memories (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON,
            processed BOOLEAN DEFAULT FALSE
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS working_memory_view (
            id INTEGER PRIMARY KEY,
            content TEXT,
            activation_level FLOAT DEFAULT 0.5,
            timestamp TIMESTAMP,
            miller_capacity_position INTEGER CHECK (miller_capacity_position <= 7)
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
            atomic_actions TEXT,
            phantom_objects TEXT,
            spatial_extraction TEXT,
            semantic_category TEXT,
            stm_strength FLOAT DEFAULT 0.0,
            hebbian_potential INTEGER DEFAULT 0,
            ready_for_consolidation BOOLEAN DEFAULT FALSE,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ltm_semantic_network (
            id INTEGER PRIMARY KEY,
            concept_a TEXT,
            concept_b TEXT,
            association_strength FLOAT,
            association_type TEXT,
            consolidation_timestamp TIMESTAMP,
            retrieval_count INTEGER DEFAULT 0
        )
    """
    )

    # Create working memory table for edge case tests
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS working_memory_view (
            memory_id INTEGER PRIMARY KEY,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activation_level FLOAT DEFAULT 0.5,
            miller_capacity_position INTEGER
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_metrics (
            id INTEGER PRIMARY KEY,
            metric_name TEXT,
            metric_value FLOAT,
            measurement_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    return conn


@pytest.fixture(scope="function")
def transactional_duckdb(test_duckdb):
    """Provide DuckDB connection with transaction-based isolation.

    Note: DuckDB doesn't support full transactions like PostgreSQL,
    but we can simulate isolation by using temporary tables.
    """
    conn = test_duckdb

    # Begin "transaction" by creating temporary tables
    temp_tables = []

    def create_temp_table(name: str, schema: str):
        temp_name = f"temp_{name}_{os.getpid()}"
        conn.execute(f"CREATE TEMP TABLE {temp_name} AS {schema}")
        temp_tables.append(temp_name)
        return temp_name

    yield conn, create_temp_table

    # Cleanup temporary tables
    for table in temp_tables:
        try:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        except Exception:
            pass


# Test data constants for biological parameters
TEST_MEMORY_CAPACITY = 7  # Miller's 7±2
TEST_STM_DURATION = 30  # minutes
TEST_CONSOLIDATION_THRESHOLD = 0.5
TEST_HEBBIAN_RATE = 0.1
TEST_FORGETTING_RATE = 0.05


# Session-level cleanup for PostgreSQL
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_schemas():
    """Clean up any remaining test schemas after all tests complete."""
    yield

    # Clean up any leftover test schemas
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            database=os.getenv("POSTGRES_DB", "codex_db"),
            user=os.getenv("POSTGRES_USER", os.getenv("USER")),
            password=os.getenv("POSTGRES_PASSWORD", ""),
        )

        with conn.cursor() as cur:
            # Find and drop all test schemas
            cur.execute(
                """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name LIKE 'test_schema_%'
            """
            )
            schemas = cur.fetchall()

            for (schema,) in schemas:
                cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")

            conn.commit()

        conn.close()

        if schemas:
            print(f"\nCleaned up {len(schemas)} test schema(s)")
    except Exception as e:
        print(f"\nWarning: Could not clean up test schemas: {e}")
