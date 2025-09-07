"""
Test configuration for Biological Memory Pipeline.

This is the main conftest.py file that imports modular fixtures from
the fixtures/ directory. The fixtures are organized by concern:
- database.py: Database connections and schema setup
- mocking.py: Mock implementations for external services
- test_data.py: Test data factories and biological memory scenarios

This modular approach enables better maintainability, parallel testing,
and proper test isolation.
"""

from pathlib import Path

import pytest

# Load test environment file if it exists
test_env_path = Path(__file__).parent.parent / ".env.test"
if test_env_path.exists():
    from dotenv import load_dotenv

    load_dotenv(test_env_path)

# Import all fixtures from modular fixture files
pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.mocking",
    "tests.fixtures.test_data",
]


# Configure pytest for parallel execution
def pytest_configure(config):
    """Configure pytest settings for optimized testing."""
    # Enable parallel execution if pytest-xdist is available
    if config.option.dist == "no":
        try:
            pass

            # Set up for automatic parallel execution
            config.option.dist = "worksteal"
            config.option.numprocesses = "auto"
        except ImportError:
            pass


# Test collection optimization
def pytest_collection_modifyitems(config, items):
    """Optimize test collection and add markers."""
    for item in items:
        # Mark slow tests
        if "performance_test" in item.nodeid or "large_dataset" in item.name:
            item.add_marker(pytest.mark.slow)

        # Mark database tests
        if "test_postgres" in item.nodeid or "database" in item.nodeid:
            item.add_marker(pytest.mark.database)

        # Mark integration tests
        if "integration" in item.nodeid or "test_live" in item.nodeid:
            item.add_marker(pytest.mark.integration)


# Skip markers for conditional testing
pytestmark = [
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
    pytest.mark.filterwarnings("ignore::PendingDeprecationWarning"),
]
