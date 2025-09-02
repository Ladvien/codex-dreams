"""
Test helper utilities for managing test dependencies
"""

import os

import psycopg2
import pytest
import requests


def check_postgres_available():
    """Check if PostgreSQL is available for testing"""
    try:
        conn = psycopg2.connect(
            os.getenv("TEST_DATABASE_URL", "postgresql://ladvien@localhost:5432/codex")
        )
        conn.close()
        return True
    except:
        return False


def check_ollama_available():
    """Check if Ollama is available for testing"""
    try:
        response = requests.get(
            f"{os.getenv('OLLAMA_URL', 'http://localhost:11434')}/api/tags", timeout=1
        )
        return response.status_code == 200
    except:
        return False


# Skip decorators for conditional test execution
skip_if_no_postgres = pytest.mark.skipif(
    not check_postgres_available(), reason="PostgreSQL not available for testing"
)

skip_if_no_ollama = pytest.mark.skipif(
    not check_ollama_available(), reason="Ollama not available for testing"
)

skip_if_ci = pytest.mark.skipif(
    os.getenv("CI", "false").lower() == "true", reason="Skipping in CI environment"
)
