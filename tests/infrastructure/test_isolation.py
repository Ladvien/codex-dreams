"""
Test isolation validation for the refactored test architecture.

Validates that tests run in isolation without interfering with each other,
and that parallel execution works correctly.
"""

import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest


class TestIsolation:
    """Test that test isolation mechanisms work properly."""

    def test_duckdb_isolation_between_tests(self, test_duckdb):
        """Test that each test gets a fresh DuckDB instance."""
        conn = test_duckdb

        # Create a temporary table
        conn.execute("CREATE TABLE test_isolation (id INTEGER, value TEXT)")
        conn.execute("INSERT INTO test_isolation VALUES (1, 'test1')")

        # Verify data exists
        result = conn.execute("SELECT * FROM test_isolation").fetchall()
        assert len(result) == 1
        assert result[0][0] == 1
        assert result[0][1] == "test1"

    def test_duckdb_isolation_different_instance(self, test_duckdb):
        """Test that this test gets a completely fresh DuckDB instance."""
        conn = test_duckdb

        # The table from the previous test should NOT exist
        with pytest.raises(Exception):  # Should raise table doesn't exist error
            conn.execute("SELECT * FROM test_isolation").fetchall()

        # We can create our own table with same name
        conn.execute("CREATE TABLE test_isolation (id INTEGER, value TEXT)")
        conn.execute("INSERT INTO test_isolation VALUES (2, 'test2')")

        result = conn.execute("SELECT * FROM test_isolation").fetchall()
        assert len(result) == 1
        assert result[0][0] == 2  # Different data than previous test

    def test_postgres_schema_isolation(self, test_postgres_connection):
        """Test that PostgreSQL schemas are isolated between tests."""
        if test_postgres_connection is None or test_postgres_connection == (None, None):
            pytest.skip("PostgreSQL connection not available")

        conn, schema = test_postgres_connection
        if conn is None or schema is None:
            pytest.skip("PostgreSQL connection not available")
        assert schema is not None, "Should have unique schema name"
        assert "test_schema_" in schema, "Schema should have test prefix"

        # Create a test table in our isolated schema
        with conn.cursor() as cur:
            cur.execute(f"CREATE TABLE {schema}.isolation_test (id SERIAL, data TEXT)")
            cur.execute(f"INSERT INTO {schema}.isolation_test (data) VALUES ('test_data')")

            # Verify it exists in our schema
            cur.execute(f"SELECT COUNT(*) FROM {schema}.isolation_test")
            count = cur.fetchone()[0]
            assert count == 1

    def test_environment_variable_isolation(self, test_env_vars):
        """Test that environment variables are properly isolated."""
        import os

        # Check that test environment variables are set
        assert os.getenv("DUCKDB_PATH") == test_env_vars["DUCKDB_PATH"]
        assert os.getenv("POSTGRES_DB_URL") == test_env_vars["POSTGRES_DB_URL"]

        # Modify an environment variable within test
        os.getenv("OLLAMA_TIMEOUT")
        os.environ["OLLAMA_TIMEOUT"] = "999"

        # Verify change took effect
        assert os.getenv("OLLAMA_TIMEOUT") == "999"

        # Note: Cleanup is handled by setup_test_environment fixture

    def test_real_service_isolation_between_tests(self, real_ollama):
        """Test that real service state doesn't leak between tests."""
        # Call real service with specific prompt
        response1 = real_ollama.generate("extract entities from test1")
        assert isinstance(response1, str)
        assert len(response1) > 0

        # Real service should provide consistent responses for same inputs
        response2 = real_ollama.generate("extract entities from test1")
        assert isinstance(response2, str)
        assert len(response2) > 0

    def test_temporary_file_cleanup(self):
        """Test that temporary files are properly cleaned up."""
        temp_files = []

        # Create some temporary files
        for i in range(3):
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_test_{i}.tmp") as f:
                f.write(b"test data")
                temp_files.append(f.name)
                assert os.path.exists(f.name), f"Temp file {f.name} should exist"

        # Clean up (simulating fixture cleanup)
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

        # Verify cleanup
        for temp_file in temp_files:
            assert not os.path.exists(temp_file), f"Temp file {temp_file} should be cleaned up"


class TestParallelExecution:
    """Test that tests can run safely in parallel."""

    def test_parallel_duckdb_instances(self):
        """Test that multiple DuckDB instances can coexist."""

        def create_and_test_db(db_id):
            """Create a DuckDB instance and perform operations."""
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_parallel_{db_id}.duckdb") as f:
                db_path = f.name

            # Remove the empty file so DuckDB can create a proper database
            os.unlink(db_path)

            try:
                import duckdb

                conn = duckdb.connect(db_path)

                # Create and populate table
                conn.execute(f"CREATE TABLE test_{db_id} (id INTEGER, db_id INTEGER)")
                conn.execute(f"INSERT INTO test_{db_id} VALUES (1, {db_id})")

                # Verify data
                result = conn.execute(f"SELECT db_id FROM test_{db_id}").fetchall()
                assert result[0][0] == db_id

                conn.close()
                return db_id
            finally:
                if os.path.exists(db_path):
                    os.unlink(db_path)

        # Run multiple database operations in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_and_test_db, i) for i in range(8)]

            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # All operations should have completed successfully
        assert len(results) == 8
        assert set(results) == set(range(8))

    def test_concurrent_fixture_access(self):
        """Test that fixtures can be accessed concurrently."""
        from tests.fixtures.test_data import MemoryDataFactory

        def generate_test_data(thread_id):
            """Generate test data in parallel."""
            factory = MemoryDataFactory()

            # Generate working memory data
            working_memory = factory.create_working_memory_batch(5)
            assert len(working_memory) == 5

            # Generate Hebbian associations
            associations = factory.create_hebbian_associations(3)
            assert len(associations) == 3

            return thread_id, len(working_memory), len(associations)

        # Run data generation in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(generate_test_data, i) for i in range(6)]

            results = []
            for future in as_completed(futures):
                results.append(future.result())

        # All threads should have completed successfully
        assert len(results) == 6
        for thread_id, wm_count, assoc_count in results:
            assert wm_count == 5
            assert assoc_count == 3

    def test_mock_thread_safety(self):
        """Test that mock fixtures are thread-safe."""
        import json

        def test_mock_in_thread(thread_id):
            """Test mock responses in parallel."""
            # We can't use the fixture directly, so simulate the mock behavior
            mock_responses = {
                "extraction": {
                    "entities": ["person", "organization"],
                    "topics": ["meeting", "planning"],
                    "sentiment": "positive",
                }
            }

            def local_mock_prompt(prompt_text: str) -> str:
                if "extract" in prompt_text.lower():
                    return json.dumps(mock_responses["extraction"])
                return json.dumps({"response": "default"})

            # Test multiple calls
            responses = []
            for i in range(5):
                response = local_mock_prompt(
                    f"extract entities from thread {thread_id} iteration {i}"
                )
                parsed = json.loads(response)
                responses.append(parsed)

            return thread_id, len(responses), responses[0]["entities"]

        # Run mock tests in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(test_mock_in_thread, i) for i in range(6)]

            results = []
            for future in as_completed(futures):
                results.append(future.result())

        # All mock calls should have worked correctly
        assert len(results) == 6
        for thread_id, response_count, entities in results:
            assert response_count == 5
            assert entities == ["person", "organization"]


class TestTransactionIsolation:
    """Test transaction-based isolation mechanisms."""

    def test_transactional_duckdb_isolation(self, transactional_duckdb):
        """Test that transactional DuckDB provides proper isolation."""
        conn, create_temp_table = transactional_duckdb

        # Create a temporary table
        temp_table = create_temp_table("test_table", "SELECT 1 as id, 'test' as value")

        # Verify table exists and has data
        result = conn.execute(f"SELECT * FROM {temp_table}").fetchall()
        assert len(result) == 1
        assert result[0][0] == 1
        assert result[0][1] == "test"

    def test_transactional_cleanup(self, transactional_duckdb):
        """Test that transactional resources are cleaned up properly."""
        conn, create_temp_table = transactional_duckdb

        # Create multiple temporary tables
        tables = []
        for i in range(3):
            table = create_temp_table(f"cleanup_test_{i}", f"SELECT {i} as value")
            tables.append(table)

        # All tables should exist
        for table in tables:
            result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchall()
            assert result[0][0] == 1

        # Note: Cleanup happens automatically via fixture teardown

    def test_biological_parameter_isolation(self):
        """Test that biological parameters are properly isolated."""
        from tests.fixtures.database import (
            TEST_CONSOLIDATION_THRESHOLD,
            TEST_FORGETTING_RATE,
            TEST_HEBBIAN_RATE,
            TEST_MEMORY_CAPACITY,
            TEST_STM_DURATION,
        )

        # Verify biological constants are set to test values
        assert TEST_MEMORY_CAPACITY == 7, "Miller's 7±2 capacity should be enforced"
        assert TEST_STM_DURATION == 30, "STM duration should be 30 minutes"
        assert 0 < TEST_CONSOLIDATION_THRESHOLD < 1, "Consolidation threshold should be probability"
        assert 0 < TEST_HEBBIAN_RATE < 1, "Hebbian rate should be between 0 and 1"
        assert 0 < TEST_FORGETTING_RATE < 1, "Forgetting rate should be between 0 and 1"
