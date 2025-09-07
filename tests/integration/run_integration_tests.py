#!/usr/bin/env python3
"""
Integration Test Runner for STORY-009
Comprehensive test execution with environment validation and health checks

This script:
1. Validates environment configuration
2. Performs health checks on live resources
3. Runs integration test suite with proper isolation
4. Generates detailed test reports
5. Cleans up test data automatically
"""

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

import psycopg2
import pytest
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
env_file = Path(__file__).parent / ".env.test"
if env_file.exists():
    load_dotenv(env_file)
    logger.info(f"Loaded test environment from {env_file}")
else:
    load_dotenv()
    logger.info("Using default environment configuration")


class IntegrationTestRunner:
    """Comprehensive integration test runner with health checks"""

    def __init__(self):
        self.postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_db = os.getenv("POSTGRES_DB", "codex_db")
        self.postgres_user = os.getenv("POSTGRES_USER", "codex_user")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "")

        self.ollama_url = os.getenv("OLLAMA_URL", "http://192.168.1.110:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

        self.health_checks_passed = False

    def validate_environment(self) -> bool:
        """Validate required environment variables"""
        logger.info("Validating environment configuration...")

        required_vars = [
            ("POSTGRES_HOST", self.postgres_host),
            ("POSTGRES_USER", self.postgres_user),
            ("POSTGRES_PASSWORD", self.postgres_password),
            ("OLLAMA_URL", self.ollama_url),
        ]

        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)

        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            return False

        logger.info("Environment validation passed")
        return True

    def check_postgresql_health(self) -> bool:
        """Check PostgreSQL connectivity and health"""
        logger.info(f"Checking PostgreSQL health at {self.postgres_host}:{self.postgres_port}")

        try:
            conn = psycopg2.connect(
                host=self.postgres_host,
                port=self.postgres_port,
                database=self.postgres_db,
                user=self.postgres_user,
                password=self.postgres_password,
                connect_timeout=10,
            )

            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                logger.info(f"PostgreSQL connection successful: {version}")

            conn.close()
            return True

        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False

    def check_ollama_health(self) -> bool:
        """Check Ollama service health and model availability"""
        logger.info(f"Checking Ollama health at {self.ollama_url}")

        try:
            # Check service availability
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            if response.status_code != 200:
                logger.error(f"Ollama service not available: {response.status_code}")
                return False

            models = response.json().get("models", [])
            available_models = [model["name"] for model in models]
            logger.info(f"Ollama service available with {len(models)} models: {available_models}")

            # Check required models (handle :latest suffix variations)
            required_models = [self.ollama_model, self.embedding_model]
            missing_models = []

            for required_model in required_models:
                # Check exact match or with :latest suffix
                model_available = any(
                    available_model == required_model
                    or available_model == f"{required_model}:latest"
                    or available_model.startswith(f"{required_model}:")
                    for available_model in available_models
                )

                if not model_available:
                    missing_models.append(required_model)

            if missing_models:
                logger.warning(f"Missing required models: {missing_models}")
                # Don't fail - tests can handle missing models with fallbacks
            else:
                logger.info("All required models are available")

            return True

        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def perform_health_checks(self) -> bool:
        """Perform comprehensive health checks"""
        logger.info("Starting health checks...")

        postgres_ok = self.check_postgresql_health()
        ollama_ok = self.check_ollama_health()

        self.health_checks_passed = postgres_ok and ollama_ok

        if self.health_checks_passed:
            logger.info("All health checks passed - ready for integration testing")
        else:
            logger.warning("Some health checks failed - tests may have limited functionality")

        return self.health_checks_passed

    def run_integration_tests(self, test_patterns: Optional[List[str]] = None) -> int:
        """Run integration tests with proper configuration"""
        logger.info("Starting integration test execution...")

        # Prepare test command
        test_dir = Path(__file__).parent
        cmd_args = [
            "-v",
            "--tb=short",
            "--disable-warnings",
            "-m",
            "integration",
            "--timeout=300",
            str(test_dir),
        ]

        if test_patterns:
            for pattern in test_patterns:
                cmd_args.extend(["-k", pattern])

        logger.info(f"Running pytest with args: {' '.join(cmd_args)}")

        # Run tests
        return pytest.main(cmd_args)

    def cleanup_test_data(self):
        """Clean up any test data created during testing"""
        logger.info("Cleaning up test data...")

        try:
            # Clean up DuckDB test files
            test_files = [
                "./test_memory.duckdb",
                "./test_llm_cache.duckdb",
            ]

            for file_path in test_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Removed test file: {file_path}")

        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")

    def run_complete_test_suite(self) -> int:
        """Run complete integration test suite with health checks"""
        logger.info("=== STORY-009 Integration Test Suite ===")

        # Validate environment
        if not self.validate_environment():
            logger.error("Environment validation failed - aborting tests")
            return 1

        # Perform health checks
        self.perform_health_checks()

        # Run tests
        try:
            exit_code = self.run_integration_tests()

            if exit_code == 0:
                logger.info("✅ All integration tests passed successfully")
            else:
                logger.error(f"❌ Some integration tests failed (exit code: {exit_code})")

            return exit_code

        finally:
            # Always cleanup
            self.cleanup_test_data()


def main():
    """Main entry point for integration test runner"""
    runner = IntegrationTestRunner()

    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--health-only":
            # Run health checks only
            success = runner.perform_health_checks()
            return 0 if success else 1
        elif sys.argv[1] == "--postgres-only":
            # Run PostgreSQL tests only
            return runner.run_integration_tests(["postgres"])
        elif sys.argv[1] == "--ollama-only":
            # Run Ollama tests only
            return runner.run_integration_tests(["ollama"])
        elif sys.argv[1] == "--performance-only":
            # Run performance tests only
            return runner.run_integration_tests(["performance"])

    # Run complete test suite
    return runner.run_complete_test_suite()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
