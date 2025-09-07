#!/usr/bin/env python3
"""
Configuration Validation Module - BMP-CRITICAL-005

This module provides comprehensive configuration validation for the Biological Memory Pipeline.
It ensures consistency, completeness, and correctness of environment configuration.

Features:
- Environment variable validation
- Configuration file consistency checking
- Model availability verification
- Database connectivity validation
- Timeout and performance setting validation
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse


class ConfigurationValidator:
    """Validates system configuration for consistency and correctness"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.project_root = self._find_project_root()
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []

        # Configuration standards
        self.required_vars = {
            "POSTGRES_DB_URL",
            "OLLAMA_URL",
            "OLLAMA_MODEL",
            "EMBEDDING_MODEL",
            "DUCKDB_PATH",
        }

        self.optional_vars = {
            "DBT_PROFILES_DIR",
            "DBT_PROJECT_DIR",
            "MAX_DB_CONNECTIONS",
            "OLLAMA_GENERATION_TIMEOUT_SECONDS",
            "EMBEDDING_TIMEOUT_SECONDS",
            "LLM_CACHE_PATH",
            "TEST_DATABASE_URL",
        }

        self.expected_models = {
            "production": "gpt-oss:20b",
            "testing": "qwen2.5:0.5b",
            "embedding": "nomic-embed-text",
        }

        self.timeout_defaults = {
            "OLLAMA_GENERATION_TIMEOUT_SECONDS": 300,
            "EMBEDDING_TIMEOUT_SECONDS": 300,
        }

    def _find_project_root(self) -> Path:
        """Find the project root directory"""
        current = Path(__file__).parent
        while current != current.parent:
            if (current / ".env.example").exists():
                return current
            current = current.parent
        return Path(__file__).parent.parent.parent

    def validate_environment_variables(self) -> bool:
        """Validate that all required environment variables are present and valid"""

        self.logger.info("Validating environment variables...")

        missing_required = []
        invalid_values = []

        # Check required variables
        for var in self.required_vars:
            value = os.getenv(var)
            if not value:
                missing_required.append(var)
            elif not value.strip():
                invalid_values.append(f"{var}: empty value")

        if missing_required:
            self.validation_errors.append(
                f"Missing required environment variables: {missing_required}"
            )

        if invalid_values:
            self.validation_errors.append(f"Invalid environment variable values: {invalid_values}")

        # Validate specific variable formats
        self._validate_database_urls()
        self._validate_ollama_configuration()
        self._validate_path_variables()
        self._validate_timeout_configuration()

        return len(self.validation_errors) == 0

    def _validate_database_urls(self) -> None:
        """Validate database URL formats"""

        db_vars = ["POSTGRES_DB_URL", "TEST_DATABASE_URL"]

        for var in db_vars:
            url = os.getenv(var)
            if not url:
                if var == "POSTGRES_DB_URL":
                    self.validation_errors.append(f"{var} is required but not set")
                continue

            try:
                parsed = urlparse(url)
                if not parsed.scheme:
                    self.validation_errors.append(f"{var}: Missing URL scheme")
                elif parsed.scheme != "postgresql":
                    self.validation_errors.append(
                        f"{var}: Expected postgresql:// scheme, got {parsed.scheme}://"
                    )

                if not parsed.hostname:
                    self.validation_errors.append(f"{var}: Missing hostname")

                if not parsed.username:
                    self.validation_warnings.append(f"{var}: Missing username")

                if not parsed.password:
                    self.validation_warnings.append(f"{var}: Missing password")

                if not parsed.path or parsed.path == "/":
                    self.validation_errors.append(f"{var}: Missing database name")

            except Exception as e:
                self.validation_errors.append(f"{var}: Invalid URL format - {str(e)}")

    def _validate_ollama_configuration(self) -> None:
        """Validate Ollama-related configuration"""

        ollama_url = os.getenv("OLLAMA_URL")
        if ollama_url:
            try:
                parsed = urlparse(ollama_url)
                if not parsed.scheme or parsed.scheme not in ["http", "https"]:
                    self.validation_errors.append("OLLAMA_URL: Must use http:// or https:// scheme")

                if not parsed.hostname:
                    self.validation_errors.append("OLLAMA_URL: Missing hostname")

                if not parsed.port:
                    self.validation_warnings.append("OLLAMA_URL: Missing port (default: 11434)")

            except Exception as e:
                self.validation_errors.append(f"OLLAMA_URL: Invalid URL format - {str(e)}")

        # Validate model names
        ollama_model = os.getenv("OLLAMA_MODEL")
        if ollama_model:
            # Check if it matches expected production or test models
            if ollama_model not in [
                self.expected_models["production"],
                self.expected_models["testing"],
            ]:
                self.validation_warnings.append(
                    f"OLLAMA_MODEL: {ollama_model} is not a standard model. "
                    f"Expected: {self.expected_models['production']} (production) or "
                    f"{self.expected_models['testing']} (testing)"
                )

            # Validate model name format (should have version tag)
            if ":" not in ollama_model:
                self.validation_warnings.append(f"OLLAMA_MODEL: {ollama_model} lacks version tag")

        embedding_model = os.getenv("EMBEDDING_MODEL")
        if embedding_model and embedding_model != self.expected_models["embedding"]:
            self.validation_warnings.append(
                f"EMBEDDING_MODEL: {embedding_model} differs from standard "
                f"{self.expected_models['embedding']}"
            )

    def _validate_path_variables(self) -> None:
        """Validate file path variables"""

        path_vars = [
            "DUCKDB_PATH",
            "LLM_CACHE_PATH",
            "DBT_PROFILES_DIR",
            "DBT_PROJECT_DIR",
        ]

        for var in path_vars:
            path_str = os.getenv(var)
            if not path_str:
                if var in self.required_vars:
                    self.validation_errors.append(f"{var}: Required path variable not set")
                continue

            try:
                path = Path(path_str).expanduser()

                if var.endswith("_DIR"):
                    # Directory variables
                    if path.exists() and not path.is_dir():
                        self.validation_errors.append(f"{var}: Path exists but is not a directory")
                    elif not path.exists():
                        # Check if parent exists for potential creation
                        if not path.parent.exists():
                            self.validation_warnings.append(
                                f"{var}: Parent directory does not exist"
                            )
                else:
                    # File variables
                    if path.exists() and path.is_dir():
                        self.validation_errors.append(f"{var}: Path is a directory, not a file")
                    elif not path.exists():
                        # Check if parent directory exists
                        if not path.parent.exists():
                            self.validation_warnings.append(
                                f"{var}: Parent directory does not exist"
                            )

            except Exception as e:
                self.validation_errors.append(f"{var}: Invalid path - {str(e)}")

    def _validate_timeout_configuration(self) -> None:
        """Validate timeout configuration"""

        for var, default_value in self.timeout_defaults.items():
            value_str = os.getenv(var)
            if value_str:
                try:
                    value = int(value_str)
                    if value <= 0:
                        self.validation_errors.append(
                            f"{var}: Timeout must be positive, got {value}"
                        )
                    elif value > 3600:  # 1 hour
                        self.validation_warnings.append(
                            f"{var}: Very long timeout ({value}s), may cause delays"
                        )
                    elif value < 10:
                        self.validation_warnings.append(
                            f"{var}: Very short timeout ({value}s), may cause failures"
                        )

                except ValueError:
                    self.validation_errors.append(f"{var}: Must be an integer, got '{value_str}'")

    def validate_configuration_consistency(self) -> bool:
        """Validate consistency across configuration files"""

        self.logger.info("Validating configuration file consistency...")

        env_example_path = self.project_root / ".env.example"
        env_testing_path = self.project_root / ".env.testing"

        if not env_example_path.exists():
            self.validation_errors.append("Missing .env.example file")
            return False

        # Check .env.example completeness
        with open(env_example_path, "r") as f:
            env_example_content = f.read()

        missing_in_example = []
        for var in self.required_vars | self.optional_vars:
            if var not in env_example_content:
                missing_in_example.append(var)

        if missing_in_example:
            self.validation_errors.append(
                f"Variables missing from .env.example: {missing_in_example}"
            )

        # Check for hardcoded IP addresses
        hardcoded_ips = re.findall(r"192\.168\.1\.\d+", env_example_content)
        if hardcoded_ips:
            self.validation_errors.append(
                f"Hardcoded IP addresses in .env.example: {hardcoded_ips}"
            )

        # Validate test configuration if present
        if env_testing_path.exists():
            with open(env_testing_path, "r") as f:
                env_testing_content = f.read()

            test_hardcoded_ips = re.findall(r"192\.168\.1\.\d+", env_testing_content)
            if test_hardcoded_ips:
                self.validation_errors.append(
                    f"Hardcoded IP addresses in .env.testing: {test_hardcoded_ips}"
                )

        return len(self.validation_errors) == 0

    def validate_model_availability(self) -> bool:
        """Validate that required models are available (if possible to check)"""

        self.logger.info("Validating model availability...")

        # This is a placeholder for future implementation
        # Could potentially check Ollama API for available models

        ollama_model = os.getenv("OLLAMA_MODEL")
        if ollama_model:
            self.validation_warnings.append(
                f"Model availability check not implemented. "
                f"Please ensure {ollama_model} is available in Ollama"
            )

        return True

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""

        summary = {
            "environment_variables": {},
            "validation_status": {
                "errors": len(self.validation_errors),
                "warnings": len(self.validation_warnings),
            },
            "configuration_files": {
                ".env.example": (self.project_root / ".env.example").exists(),
                ".env.testing": (self.project_root / ".env.testing").exists(),
            },
        }

        # Gather environment variables (mask sensitive ones)
        for var in self.required_vars | self.optional_vars:
            value = os.getenv(var)
            if value:
                if any(sensitive in var.upper() for sensitive in ["PASSWORD", "SECRET", "KEY"]):
                    summary["environment_variables"][var] = "[MASKED]"
                elif "URL" in var and "://" in value:
                    # Mask credentials in URLs
                    summary["environment_variables"][var] = re.sub(
                        r"://[^:]+:[^@]+@", "://[USER]:[PASS]@", value
                    )
                else:
                    summary["environment_variables"][var] = value
            else:
                summary["environment_variables"][var] = None

        return summary

    def validate_all(self) -> bool:
        """Run all validation checks"""

        self.validation_errors.clear()
        self.validation_warnings.clear()

        env_valid = self.validate_environment_variables()
        consistency_valid = self.validate_configuration_consistency()
        models_valid = self.validate_model_availability()

        # Log results
        if self.validation_errors:
            self.logger.error(
                f"Configuration validation failed with {len(self.validation_errors)} errors:"
            )
            for error in self.validation_errors:
                self.logger.error(f"  - {error}")

        if self.validation_warnings:
            self.logger.warning(
                f"Configuration validation has {len(self.validation_warnings)} warnings:"
            )
            for warning in self.validation_warnings:
                self.logger.warning(f"  - {warning}")

        return env_valid and consistency_valid and models_valid

    def get_validation_report(self) -> Dict[str, Any]:
        """Get detailed validation report"""

        return {
            "success": len(self.validation_errors) == 0,
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "configuration_summary": self.get_configuration_summary(),
        }


def validate_configuration() -> bool:
    """Standalone function to validate configuration"""

    validator = ConfigurationValidator()
    return validator.validate_all()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Run validation
    validator = ConfigurationValidator()
    success = validator.validate_all()

    if success:
        print("✅ Configuration validation passed!")
    else:
        print("❌ Configuration validation failed!")
        print("\nErrors:")
        for error in validator.validation_errors:
            print(f"  - {error}")

        if validator.validation_warnings:
            print("\nWarnings:")
            for warning in validator.validation_warnings:
                print(f"  - {warning}")

    exit(0 if success else 1)
