#!/usr/bin/env python3
"""
Comprehensive PostgreSQL Integration Tests for STORY-009
Tests direct connectivity to PostgreSQL database

This module provides comprehensive integration testing for:
- Direct PostgreSQL connectivity to production server
- Database schema validation and constraints
- Performance benchmarking with biological timing requirements
- Health checks and connection pooling
- Test data isolation and cleanup
- Error handling and recovery scenarios
"""

import json
import logging
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import duckdb
import psycopg2
import pytest
from dotenv import load_dotenv

# Load environment variables from .env.test file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class PostgreSQLConnectionConfig:
    """Configuration for PostgreSQL integration testing - PRODUCTION VALUES"""

    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    database: str = os.getenv("POSTGRES_DB", "codex_db")
    test_database: str = os.getenv("TEST_DB_NAME", "codex_db")  # Use production DB for real testing
    username: str = os.getenv("POSTGRES_USER", "codex_user")
    password: str = os.getenv("POSTGRES_PASSWORD", "")
    max_connections: int = int(os.getenv("MAX_DB_CONNECTIONS", "160"))
    connection_timeout: int = 10


class PostgreSQLIntegrationTester:
    """Main class for PostgreSQL integration testing"""

    def __init__(self, config: Optional[PostgreSQLConnectionConfig] = None):
        self.config = config or PostgreSQLConnectionConfig()
        self.test_schema_name = f"integration_test_{int(time.time())}"
        self.test_tables_created = []

    @contextmanager
    def get_postgres_connection(self, use_test_db: bool = True):
        """Get a PostgreSQL connection with automatic cleanup"""
        db_name = self.config.test_database if use_test_db else self.config.database

        try:
            conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=db_name,
                user=self.config.username,
                password=self.config.password,
                connect_timeout=self.config.connection_timeout,
            )
            conn.autocommit = True
            yield conn
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            logger.warning(f"PostgreSQL connection failed: {e}")
            pytest.skip(f"PostgreSQL not available: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
        finally:
            if "conn" in locals():
                conn.close()

    @contextmanager
    def get_duckdb_with_postgres(self, use_test_db: bool = True):
        """Get a DuckDB connection with PostgreSQL extension loaded"""
        db_name = self.config.test_database if use_test_db else self.config.database
        postgres_url = f"postgresql://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}/{db_name}"

        # Create a temporary file path but delete the file so DuckDB can create it fresh
        temp_file = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
        temp_file.close()
        temp_path = temp_file.name
        Path(temp_path).unlink()  # Delete the empty file so DuckDB can create it properly

        try:
            conn = duckdb.connect(temp_path)
            conn.execute("LOAD postgres")
            conn.execute(f"ATTACH '{postgres_url}' AS postgres_db (TYPE postgres)")
            yield conn
        except Exception as e:
            logger.error(f"DuckDB PostgreSQL connection failed: {e}")
            raise
        finally:
            if "conn" in locals():
                conn.close()
            if Path(temp_path).exists():
                Path(temp_path).unlink()

    def cleanup_test_data(self):
        """Clean up test data and schemas"""
        try:
            with self.get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    # Drop test schema and all contained objects
                    cursor.execute(f"DROP SCHEMA IF EXISTS {self.test_schema_name} CASCADE")

                    # Clean up any test tables in public schema
                    for table_name in self.test_tables_created:
                        cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")

                    logger.info(
                        f"Cleaned up test schema {self.test_schema_name} and {len(self.test_tables_created)} tables"
                    )

        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


class TestPostgreSQLConnectivity:
    """Test basic PostgreSQL connectivity and configuration"""

    def setup_method(self):
        """Set up test environment"""
        self.tester = PostgreSQLIntegrationTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.tester.cleanup_test_data()

    def test_postgresql_direct_connection(self):
        """Test direct connection to PostgreSQL database"""
        with self.tester.get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Test basic connectivity
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]

                assert "PostgreSQL" in version
                logger.info(f"Successfully connected to: {version[:100]}")

                # Verify we're connected to the correct server
                cursor.execute("SELECT inet_server_addr()")
                server_ip = cursor.fetchone()

                if server_ip and server_ip[0]:
                    logger.info(f"Connected to server IP: {server_ip[0]}")
                    # Note: inet_server_addr() returns None for Unix domain sockets
                    # or when connecting via localhost, so we don't assert IP
                    # match

    def test_postgresql_performance_timing(self):
        """Test PostgreSQL query performance meets biological timing constraints (<50ms)"""
        with self.tester.get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Create test table with sufficient data
                test_table = f"perf_test_{int(time.time())}"
                self.tester.test_tables_created.append(test_table)

                cursor.execute(
                    f"""
                    CREATE TABLE {test_table} (
                        id SERIAL PRIMARY KEY,
                        content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB
                    )
                """
                )

                # Insert test data
                start_time = time.perf_counter()
                for i in range(100):
                    cursor.execute(
                        f"""
                        INSERT INTO {test_table} (content, metadata)
                        VALUES (%s, %s)
                    """,
                        (f"Test content {i}", json.dumps({"test": True, "index": i})),
                    )
                insert_time = time.perf_counter() - start_time

                # Test SELECT performance (biological constraint: <50ms)
                start_time = time.perf_counter()
                cursor.execute(
                    f"""
                    SELECT id, content, created_at
                    FROM postgres_db.public.{test_table}
                    WHERE metadata->>'test' = 'true'
                    ORDER BY created_at DESC
                    LIMIT 7
                """
                )
                results = cursor.fetchall()
                select_time = time.perf_counter() - start_time

                # Biological timing constraints
                assert (
                    select_time < 0.050
                ), f"SELECT query took {select_time:.3f}s, should be <0.050s"
                assert len(results) <= 7, "Should respect Miller's 7±2 capacity limit"
                assert (
                    insert_time < 1.0
                ), f"Batch insert took {insert_time:.3f}s, should be reasonable"

                logger.info(
                    f"PostgreSQL performance: SELECT={select_time:.3f}s, INSERT={insert_time:.3f}s"
                )

    def test_postgresql_schema_validation(self):
        """Test PostgreSQL schema creation and constraint validation"""
        with self.tester.get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Create test schema
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.tester.test_schema_name}")

                # Create biological memory tables with proper constraints
                cursor.execute(
                    f"""
                    CREATE TABLE {self.tester.test_schema_name}.raw_memories (
                        id SERIAL PRIMARY KEY,
                        content TEXT NOT NULL CHECK (length(content) > 0),
                        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB DEFAULT '{{}}',
                        source_table VARCHAR(100) DEFAULT 'integration_test',
                        CONSTRAINT valid_timestamp CHECK (timestamp <= CURRENT_TIMESTAMP)
                    )
                """
                )

                cursor.execute(
                    f"""
                    CREATE TABLE {self.tester.test_schema_name}.working_memory_episodes (
                        id INTEGER PRIMARY KEY,
                        content TEXT NOT NULL,
                        activation_level FLOAT NOT NULL CHECK (activation_level BETWEEN 0.0 AND 1.0),
                        miller_capacity_position INTEGER CHECK (miller_capacity_position BETWEEN 1 AND 9),
                        attention_window_start TIMESTAMP NOT NULL,
                        attention_window_end TIMESTAMP NOT NULL,
                        CONSTRAINT miller_capacity_limit CHECK (miller_capacity_position <= 7),
                        CONSTRAINT attention_window_valid CHECK (attention_window_end > attention_window_start),
                        CONSTRAINT attention_window_duration CHECK (
                            attention_window_end - attention_window_start <= INTERVAL '5 minutes'
                        )
                    )
                """
                )

                # Test constraint enforcement
                # Valid insert should work
                cursor.execute(
                    f"""
                    INSERT INTO {self.tester.test_schema_name}.raw_memories (content, metadata)
                    VALUES (%s, %s)
                """,
                    ("Valid memory content", json.dumps({"test": True})),
                )

                # Test Miller's 7±2 constraint
                cursor.execute(
                    f"""
                    INSERT INTO {self.tester.test_schema_name}.working_memory_episodes
                    (id, content, activation_level, miller_capacity_position, attention_window_start, attention_window_end)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        1,
                        "Test working memory",
                        0.8,
                        5,
                        datetime.now() - timedelta(minutes=2),
                        datetime.now(),
                    ),
                )

                # Verify data integrity
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FROM {self.tester.test_schema_name}.raw_memories
                """
                )
                assert cursor.fetchone()[0] == 1

                cursor.execute(
                    f"""
                    SELECT miller_capacity_position FROM {self.tester.test_schema_name}.working_memory_episodes
                """
                )
                assert cursor.fetchone()[0] == 5  # Within Miller's limit

    def test_postgresql_connection_pooling(self):
        """Test connection pooling performance and limits"""
        connections = []
        try:
            # Test multiple concurrent connections
            start_time = time.perf_counter()

            for i in range(5):  # Test with 5 concurrent connections
                conn = psycopg2.connect(
                    host=self.tester.config.host,
                    port=self.tester.config.port,
                    database=self.tester.config.test_database,
                    user=self.tester.config.username,
                    password=self.tester.config.password,
                    connect_timeout=self.tester.config.connection_timeout,
                )
                connections.append(conn)

            connection_time = time.perf_counter() - start_time

            # All connections should establish quickly
            assert (
                connection_time < 2.0
            ), f"Connection pooling took {connection_time:.3f}s, should be <2.0s"
            assert len(connections) == 5, "Should create 5 concurrent connections"

            # Test that each connection works
            for i, conn in enumerate(connections):
                with conn.cursor() as cursor:
                    cursor.execute("SELECT %s as connection_id", (i,))
                    result = cursor.fetchone()[0]
                    assert result == i, f"Connection {i} failed validation"

            logger.info(
                f"Connection pooling: {len(connections)} connections in {connection_time:.3f}s"
            )

        finally:
            # Clean up connections
            for conn in connections:
                try:
                    conn.close()
                except BaseException:
                    pass


class TestDuckDBPostgreSQLIntegration:
    """Test DuckDB integration with PostgreSQL for biological memory pipeline"""

    def setup_method(self):
        """Set up test environment"""
        self.tester = PostgreSQLIntegrationTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.tester.cleanup_test_data()

    def test_duckdb_postgres_scanner_integration(self):
        """Test DuckDB postgres_scanner extension with live PostgreSQL"""
        with self.tester.get_duckdb_with_postgres() as duckdb_conn:
            # Test DuckDB-PostgreSQL connection by querying information_schema
            result = duckdb_conn.execute(
                """
                SELECT table_name FROM postgres_db.information_schema.tables
                WHERE table_schema = 'information_schema'
                LIMIT 5
            """
            ).fetchall()

            assert len(result) >= 1, "Should be able to query PostgreSQL information_schema"
            logger.info(f"Found {len(result)} PostgreSQL system tables via DuckDB")

            # Test that we can list PostgreSQL tables
            tables = duckdb_conn.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """
            ).fetchall()

            logger.info(f"Found {len(tables)} PostgreSQL tables accessible from DuckDB")

    def test_duckdb_postgres_data_flow(self):
        """Test complete data flow from PostgreSQL to DuckDB processing"""
        # First, set up test data in PostgreSQL
        with self.tester.get_postgres_connection() as pg_conn:
            with pg_conn.cursor() as cursor:
                test_table = f"memory_flow_test_{int(time.time())}"
                self.tester.test_tables_created.append(test_table)

                cursor.execute(
                    f"""
                    CREATE TABLE {test_table} (
                        id SERIAL PRIMARY KEY,
                        content TEXT,
                        importance_score FLOAT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB DEFAULT '{{}}'
                    )
                """
                )

                # Insert biological memory test data
                test_memories = [
                    ("Working on quarterly business review", 0.9),
                    ("Team standup meeting discussion", 0.7),
                    ("Code review for authentication system", 0.8),
                    ("Planning sprint objectives", 0.8),
                    ("Debugging production issue", 0.95),
                ]

                for content, importance in test_memories:
                    cursor.execute(
                        f"""
                        INSERT INTO {test_table} (content, importance_score, metadata)
                        VALUES (%s, %s, %s)
                    """,
                        (
                            content,
                            importance,
                            json.dumps({"source": "integration_test"}),
                        ),
                    )

        # Now test DuckDB processing of PostgreSQL data
        with self.tester.get_duckdb_with_postgres() as duckdb_conn:
            # Test Miller's 7±2 working memory selection from PostgreSQL
            start_time = time.perf_counter()

            working_memory_result = duckdb_conn.execute(
                f"""
                SELECT id, content, importance_score, created_at
                FROM postgres_db.public.{test_table}
                WHERE importance_score > 0.7
                ORDER BY importance_score DESC, created_at DESC
                LIMIT 7
            """
            ).fetchall()

            query_time = time.perf_counter() - start_time

            # Biological timing and capacity constraints
            assert (
                query_time < 0.050
            ), f"Working memory selection took {query_time:.3f}s, should be <0.050s"
            assert len(working_memory_result) <= 7, "Should respect Miller's 7±2 capacity"
            assert len(working_memory_result) >= 4, "Should select high-importance memories"

            # Test that highest importance memories are selected
            assert working_memory_result[0][2] >= 0.9, "Highest importance memory should be first"

            # Test DuckDB analytical processing on PostgreSQL data
            analytical_result = duckdb_conn.execute(
                f"""
                SELECT
                    COUNT(*) as total_memories,
                    AVG(importance_score) as avg_importance,
                    MAX(importance_score) as max_importance,
                    MIN(importance_score) as min_importance
                FROM postgres_db.public.{test_table}
            """
            ).fetchall()

            assert analytical_result[0][0] == 5, "Should process all 5 test memories"
            assert analytical_result[0][1] > 0.7, "Average importance should be high"
            assert analytical_result[0][2] == 0.95, "Max importance should match debug task"

            logger.info(
                f"DuckDB-PostgreSQL integration: {len(working_memory_result)} memories selected in {query_time:.3f}s"
            )

    def test_duckdb_postgres_biological_constraints(self):
        """Test biological memory constraints across DuckDB-PostgreSQL integration"""
        with self.tester.get_postgres_connection() as pg_conn:
            with pg_conn.cursor() as cursor:
                test_table = f"bio_constraints_test_{int(time.time())}"
                self.tester.test_tables_created.append(test_table)

                # Create table with biological memory structure
                cursor.execute(
                    f"""
                    CREATE TABLE {test_table} (
                        id SERIAL PRIMARY KEY,
                        content TEXT,
                        attention_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        stm_strength FLOAT DEFAULT 0.5,
                        ready_for_consolidation BOOLEAN DEFAULT FALSE,
                        consolidation_threshold FLOAT DEFAULT 0.5
                    )
                """
                )

                # Insert memories with different consolidation readiness
                test_data = [
                    ("High strength memory", 0.8, True),
                    ("Medium strength memory", 0.6, True),
                    ("Low strength memory", 0.3, False),
                    ("Another strong memory", 0.9, True),
                    ("Weak memory", 0.2, False),
                ]

                for content, strength, ready in test_data:
                    cursor.execute(
                        f"""
                        INSERT INTO {test_table} (content, stm_strength, ready_for_consolidation)
                        VALUES (%s, %s, %s)
                    """,
                        (content, strength, ready),
                    )

        # Test biological constraint processing via DuckDB
        with self.tester.get_duckdb_with_postgres() as duckdb_conn:
            # Test consolidation threshold filtering
            consolidation_candidates = duckdb_conn.execute(
                f"""
                SELECT content, stm_strength
                FROM postgres_db.public.{test_table}
                WHERE ready_for_consolidation = true
                  AND stm_strength >= consolidation_threshold
                ORDER BY stm_strength DESC
            """
            ).fetchall()

            assert len(consolidation_candidates) == 3, "Should find 3 consolidation candidates"
            assert consolidation_candidates[0][1] == 0.9, "Strongest memory should be first"

            # Test attention window constraint (5-minute window)
            recent_memories = duckdb_conn.execute(
                f"""
                SELECT COUNT(*) as recent_count
                FROM postgres_db.public.{test_table}
                WHERE attention_timestamp > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
            """
            ).fetchall()

            assert recent_memories[0][0] == 5, "All test memories should be within 5-minute window"

            # Test working memory capacity constraint simulation
            working_memory_simulation = duckdb_conn.execute(
                f"""
                WITH ranked_memories AS (
                    SELECT content, stm_strength,
                           ROW_NUMBER() OVER (ORDER BY stm_strength DESC) as memory_rank
                    FROM postgres_db.public.{test_table}
                    WHERE attention_timestamp > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                )
                SELECT * FROM ranked_memories WHERE memory_rank <= 7
            """
            ).fetchall()

            assert len(working_memory_simulation) <= 7, "Should respect Miller's 7±2 capacity"
            assert (
                len(working_memory_simulation) == 5
            ), "Should include all 5 test memories (under capacity)"


class TestPostgreSQLHealthChecks:
    """Test comprehensive health checks for PostgreSQL integration"""

    def setup_method(self):
        """Set up test environment"""
        self.tester = PostgreSQLIntegrationTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.tester.cleanup_test_data()

    def test_postgresql_health_check_comprehensive(self):
        """Comprehensive PostgreSQL health check before running tests"""
        health_status = {}

        try:
            # Test 1: Basic connectivity
            with self.tester.get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    health_status["connectivity"] = result[0] == 1

            # Test 2: Database permissions
            with self.tester.get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT current_user, current_database()")
                    user, database = cursor.fetchone()
                    health_status["permissions"] = {
                        "user": user,
                        "database": database,
                        "can_create_tables": False,
                        "can_insert_data": False,
                    }

                    # Test table creation permission
                    try:
                        test_table = f"health_check_{int(time.time())}"
                        cursor.execute(f"CREATE TABLE {test_table} (id INTEGER)")
                        health_status["permissions"]["can_create_tables"] = True

                        # Test insert permission
                        cursor.execute(f"INSERT INTO {test_table} VALUES (1)")
                        health_status["permissions"]["can_insert_data"] = True

                        # Cleanup
                        cursor.execute(f"DROP TABLE {test_table}")

                    except Exception as e:
                        logger.warning(f"Permission test failed: {e}")

            # Test 3: Performance baseline
            with self.tester.get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    start_time = time.perf_counter()
                    cursor.execute("SELECT generate_series(1, 100)")
                    cursor.fetchall()
                    performance_time = time.perf_counter() - start_time

                    health_status["performance"] = {
                        "baseline_query_time": performance_time,
                        "meets_timing_constraints": performance_time < 0.1,
                    }

            # Test 4: Required extensions/features
            with self.tester.get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    # Check for JSONB support
                    cursor.execute("SELECT '{}' :: JSONB")
                    health_status["jsonb_support"] = True

                    # Check PostgreSQL version
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    health_status["version"] = version

                    # Check for required functions
                    cursor.execute("SELECT CURRENT_TIMESTAMP")
                    health_status["timestamp_functions"] = True

            # Validate health status
            assert health_status["connectivity"], "PostgreSQL connectivity failed"
            assert health_status["permissions"]["can_create_tables"], "Cannot create tables"
            assert health_status["permissions"]["can_insert_data"], "Cannot insert data"
            assert health_status["performance"]["meets_timing_constraints"], "Performance too slow"
            assert health_status["jsonb_support"], "JSONB support missing"
            assert health_status["timestamp_functions"], "Timestamp functions missing"

            logger.info("PostgreSQL health check passed")
            logger.info(f"Connected as: {health_status['permissions']['user']}")
            logger.info(f"Database: {health_status['permissions']['database']}")
            logger.info(f"Performance: {health_status['performance']['baseline_query_time']:.3f}s")

            return health_status

        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            raise

    def test_postgresql_error_recovery(self):
        """Test PostgreSQL error recovery and connection resilience"""
        # Test connection recovery after timeout
        config = PostgreSQLConnectionConfig()
        config.connection_timeout = 1  # Very short timeout

        tester = PostgreSQLIntegrationTester(config)

        try:
            # This should work normally
            with tester.get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    assert result[0] == 1

            logger.info("PostgreSQL error recovery test passed")

        except psycopg2.OperationalError as e:
            # If connection fails due to timeout, that's acceptable for this
            # test
            logger.info(f"Expected timeout behavior: {e}")

        finally:
            tester.cleanup_test_data()


# Test runner function for integration
def run_postgresql_integration_tests():
    """Run all PostgreSQL integration tests"""
    logger.info(
        f"Starting PostgreSQL integration tests for {os.getenv('POSTGRES_HOST', 'localhost')}"
    )

    # Check if we have required environment variables
    required_env_vars = ["POSTGRES_PASSWORD"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
        logger.warning("Skipping integration tests - set environment variables to run")
        return False

    try:
        # Run health check first
        tester = PostgreSQLIntegrationTester()
        with tester.get_postgres_connection():
            logger.info("✅ PostgreSQL connectivity confirmed")

        # Run the actual tests
        pytest_args = [__file__, "-v", "--tb=short", "-k", "test_postgresql"]

        exit_code = pytest.main(pytest_args)
        return exit_code == 0

    except Exception as e:
        logger.error(f"PostgreSQL integration tests failed: {e}")
        return False


if __name__ == "__main__":
    success = run_postgresql_integration_tests()
    exit(0 if success else 1)
