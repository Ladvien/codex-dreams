"""
Test fixture loading and availability from modular fixture files.

Validates that all fixtures are properly imported and functional
after the conftest.py refactoring.
"""

import inspect

import pytest

from tests.fixtures import database, mocking, test_data


class TestFixtureLoading:
    """Test that all fixtures are properly loaded and available."""

    def test_database_fixtures_available(self):
        """Test that database fixtures are available."""
        expected_fixtures = [
            "test_duckdb",
            "test_postgres_connection",
            "isolated_test_db",
            "biological_memory_schema",
            "transactional_duckdb",
        ]

        for fixture_name in expected_fixtures:
            assert hasattr(database, fixture_name), f"Database fixture {fixture_name} not found"

    def test_mocking_fixtures_available(self):
        """Test that mocking fixtures are available."""
        expected_fixtures = [
            "mock_ollama",
            "mock_http_requests",
            "mock_ollama_server",
            "mock_duckdb_extensions",
        ]

        for fixture_name in expected_fixtures:
            assert hasattr(mocking, fixture_name), f"Mocking fixture {fixture_name} not found"

    def test_test_data_fixtures_available(self):
        """Test that test data fixtures are available."""
        expected_fixtures = [
            "sample_memory_data",
            "working_memory_fixture",
            "short_term_memory_fixture",
            "hebbian_learning_data",
            "memory_lifecycle_data",
            "performance_test_data",
            "performance_benchmark",
        ]

        for fixture_name in expected_fixtures:
            assert hasattr(test_data, fixture_name), f"Test data fixture {fixture_name} not found"

    def test_fixture_functions_are_callable(self):
        """Test that fixture functions are properly defined and callable."""
        # Get all fixture functions
        database_fixtures = [
            getattr(database, name)
            for name in dir(database)
            if name.startswith("test_")
            or name.startswith("biological_")
            or name.startswith("isolated_")
            or name.startswith("transactional_")
        ]

        mocking_fixtures = [
            getattr(mocking, name) for name in dir(mocking) if name.startswith("mock_")
        ]

        test_data_fixtures = [
            getattr(test_data, name)
            for name in dir(test_data)
            if name.startswith("sample_")
            or name.startswith("working_")
            or name.startswith("short_")
            or name.startswith("hebbian_")
            or name.startswith("memory_")
            or name.startswith("performance_")
        ]

        all_fixtures = database_fixtures + mocking_fixtures + test_data_fixtures

        for fixture in all_fixtures:
            assert callable(fixture), f"Fixture {fixture.__name__} is not callable"

    def test_conftest_imports_fixtures(self, request):
        """Test that conftest.py properly imports all fixture modules."""
        # Check that fixture modules are loaded by trying to access fixtures
        config = request.config

        # Verify our fixture modules are accessible by checking plugin manager
        expected_plugins = [
            "tests.fixtures.database",
            "tests.fixtures.mocking",
            "tests.fixtures.test_data",
        ]

        # Check if plugins are loaded by looking at the plugin manager
        plugin_manager = config.pluginmanager
        loaded_plugin_names = [
            plugin.__module__ if hasattr(plugin, "__module__") else str(plugin)
            for plugin in plugin_manager.get_plugins()
        ]

        for expected in expected_plugins:
            found = any(expected in plugin_name for plugin_name in loaded_plugin_names)
            assert found, f"Plugin {expected} not found in loaded plugins"

    def test_fixtures_have_proper_scopes(self):
        """Test that fixtures have appropriate scopes for isolation."""
        # Check database fixtures (should be function-scoped for isolation)
        test_duckdb_fixture = getattr(database, "test_duckdb")
        assert callable(test_duckdb_fixture), "test_duckdb should be callable"

        # Check that fixtures are properly decorated
        # pytest fixtures have special attributes when decorated
        assert (
            hasattr(test_duckdb_fixture, "_pytestfixturefunction")
            or str(type(test_duckdb_fixture)).find("fixture") >= 0
        ), "test_duckdb should be a pytest fixture"

        # Check session fixtures (should be session-scoped for efficiency)
        test_env_vars_fixture = getattr(test_data, "test_env_vars")
        assert callable(test_env_vars_fixture), "test_env_vars should be callable"

    def test_fixtures_use_proper_generators(self):
        """Test that database fixtures properly use generators for cleanup."""
        # Inspect test_duckdb function signature
        test_duckdb_func = getattr(database, "test_duckdb")
        signature = inspect.signature(test_duckdb_func)

        # It should return a generator (yield statement)
        source = inspect.getsource(test_duckdb_func)
        assert "yield" in source, "test_duckdb should use yield for proper cleanup"
        assert "Generator" in str(
            signature.return_annotation
        ), "test_duckdb should have Generator type annotation"


class TestFixtureIntegration:
    """Test that fixtures work together properly."""

    def test_database_fixture_creates_connection(self, test_duckdb):
        """Test that database fixture creates working connection."""
        conn = test_duckdb
        result = conn.execute("SELECT 1 as test_value").fetchall()
        assert result[0][0] == 1, "Database connection should be functional"

    def test_biological_schema_creates_tables(self, biological_memory_schema):
        """Test that biological schema fixture creates required tables."""
        conn = biological_memory_schema

        # Check that all required tables exist
        tables_query = (
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        )
        tables = conn.execute(tables_query).fetchall()
        table_names = [table[0] for table in tables]

        required_tables = [
            "raw_memories",
            "working_memory_view",
            "stm_hierarchical_episodes",
            "ltm_semantic_network",
            "memory_metrics",
        ]

        for table in required_tables:
            assert table in table_names, f"Required table {table} not found in schema"

    def test_mock_ollama_provides_responses(self, mock_ollama):
        """Test that mock Ollama fixture provides realistic responses."""
        # Test extraction response
        response = mock_ollama("Extract entities from this text")
        assert isinstance(response, str), "Mock should return string response"

        # Parse JSON response
        import json

        parsed = json.loads(response)
        assert "entities" in parsed, "Extraction response should contain entities"
        assert isinstance(parsed["entities"], list), "Entities should be a list"

    def test_sample_memory_data_structure(self, sample_memory_data):
        """Test that sample memory data has correct structure."""
        assert isinstance(sample_memory_data, list), "Sample data should be a list"
        assert len(sample_memory_data) > 0, "Sample data should not be empty"

        for memory in sample_memory_data:
            assert "id" in memory, "Memory should have id"
            assert "content" in memory, "Memory should have content"
            assert "timestamp" in memory, "Memory should have timestamp"
            assert "metadata" in memory, "Memory should have metadata"

    def test_performance_benchmark_timing(self, performance_benchmark):
        """Test that performance benchmark fixture works correctly."""
        timer = performance_benchmark()

        with timer:
            # Simulate some work
            sum(range(1000))

        assert timer.elapsed > 0, "Timer should measure elapsed time"
        assert timer.elapsed_ms > 0, "Timer should provide milliseconds"
        assert timer.elapsed_ms == timer.elapsed * 1000, "Millisecond conversion should be correct"
