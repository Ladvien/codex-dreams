#!/usr/bin/env python3
"""
Configuration Consistency Tests - BMP-CRITICAL-005

This test suite validates consistency across all configuration files in the project:
- .env.example vs actual .env structure
- Variable naming standardization
- Model name consistency
- Timeout configuration alignment
- Database URL hierarchy compliance

Tests ensure single source of truth for configuration management.
"""

import os
import re
import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ConfigurationConsistencyTest(unittest.TestCase):
    """Test configuration consistency across all files"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.project_root = Path(__file__).parent.parent.parent
        cls.env_example_path = cls.project_root / ".env.example"
        cls.env_testing_path = cls.project_root / ".env.testing"
        cls.readme_path = cls.project_root / "README.md"
        cls.claude_md_path = cls.project_root / "CLAUDE.md"

        # Standard configuration variables that should be consistent
        cls.required_vars = {
            "POSTGRES_DB_URL",
            "OLLAMA_URL",
            "OLLAMA_MODEL",
            "EMBEDDING_MODEL",
            "DUCKDB_PATH",
            "DBT_PROFILES_DIR",
            "DBT_PROJECT_DIR",
            "MAX_DB_CONNECTIONS",
        }

        # Expected model names for consistency
        cls.expected_production_model = "gpt-oss:20b"
        cls.expected_test_model = "qwen2.5:0.5b"
        cls.expected_embedding_model = "nomic-embed-text"

        # Expected timeout variable naming
        cls.standardized_timeout_vars = {
            "OLLAMA_GENERATION_TIMEOUT_SECONDS",
            "EMBEDDING_TIMEOUT_SECONDS",
        }

    def test_env_example_structure_completeness(self):
        """Test that .env.example contains all necessary configuration variables"""

        if not self.env_example_path.exists():
            self.fail(f".env.example not found at {self.env_example_path}")

        with open(self.env_example_path, "r") as f:
            env_example_content = f.read()

        missing_vars = []
        for var in self.required_vars:
            if var not in env_example_content:
                missing_vars.append(var)

        self.assertEqual(
            [], missing_vars, f"Missing required variables in .env.example: {missing_vars}"
        )

    def test_model_name_consistency(self):
        """Test that model names are consistent across configuration files"""

        # Check .env.example for production model
        with open(self.env_example_path, "r") as f:
            env_example = f.read()

        production_model_match = re.search(r"OLLAMA_MODEL=([^\s\n]+)", env_example)
        self.assertIsNotNone(production_model_match, "OLLAMA_MODEL not found in .env.example")
        self.assertEqual(
            production_model_match.group(1),
            self.expected_production_model,
            f"Production model should be {self.expected_production_model}",
        )

        # Check .env.testing for test model
        if self.env_testing_path.exists():
            with open(self.env_testing_path, "r") as f:
                env_testing = f.read()

            test_model_match = re.search(r"OLLAMA_MODEL=([^\s\n]+)", env_testing)
            self.assertIsNotNone(test_model_match, "OLLAMA_MODEL not found in .env.testing")
            self.assertEqual(
                test_model_match.group(1),
                self.expected_test_model,
                f"Test model should be {self.expected_test_model}",
            )

    def test_embedding_model_consistency(self):
        """Test that embedding model is consistent across files"""

        files_to_check = [self.env_example_path, self.env_testing_path]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            with open(file_path, "r") as f:
                content = f.read()

            embedding_match = re.search(r"EMBEDDING_MODEL=([^\s\n]+)", content)
            self.assertIsNotNone(embedding_match, f"EMBEDDING_MODEL not found in {file_path.name}")
            self.assertEqual(
                embedding_match.group(1),
                self.expected_embedding_model,
                f"Embedding model in {file_path.name} should be {self.expected_embedding_model}",
            )

    def test_timeout_variable_standardization(self):
        """Test that timeout variables use standardized naming"""

        deprecated_patterns = [r"OLLAMA_TIMEOUT=", r"TIMEOUT=", r"LLM_TIMEOUT="]

        files_to_check = [self.env_example_path, self.env_testing_path]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            with open(file_path, "r") as f:
                content = f.read()

            # Check for deprecated timeout patterns
            for pattern in deprecated_patterns:
                matches = re.findall(pattern, content)
                self.assertEqual(
                    [], matches, f"Deprecated timeout pattern '{pattern}' found in {file_path.name}"
                )

            # Check for standardized timeout variables
            for timeout_var in self.standardized_timeout_vars:
                if timeout_var in content:
                    # Ensure it has a proper format
                    var_match = re.search(f"{timeout_var}=([0-9]+)", content)
                    self.assertIsNotNone(
                        var_match,
                        f"Standardized timeout variable {timeout_var} should have numeric value",
                    )
                    timeout_value = int(var_match.group(1))
                    self.assertGreater(
                        timeout_value, 0, f"Timeout value for {timeout_var} should be positive"
                    )

    def test_database_url_hierarchy(self):
        """Test that database URL variables follow the established hierarchy"""

        with open(self.env_example_path, "r") as f:
            content = f.read()

        # Check that POSTGRES_DB_URL is present and documented as primary
        self.assertIn(
            "POSTGRES_DB_URL",
            content,
            "POSTGRES_DB_URL should be present as primary database connection",
        )

        # Check that legacy variables are documented as such
        legacy_vars = ["DATABASE_URL", "DB_CONN"]
        for var in legacy_vars:
            if var in content:
                # Should be documented as legacy/alternative
                var_line_match = re.search(f"^.*{var}.*$", content, re.MULTILINE)
                if var_line_match:
                    line = var_line_match.group(0)
                    # Should have some indication it's legacy (before or after the line)
                    context_start = max(0, content.find(line) - 200)
                    context_end = min(len(content), content.find(line) + len(line) + 200)
                    context = content[context_start:context_end].lower()
                    self.assertTrue(
                        any(word in context for word in ["legacy", "alternative", "compatibility"]),
                        f"Variable {var} should be documented as legacy/alternative",
                    )

    def test_no_hardcoded_ip_addresses(self):
        """Test that configuration files use localhost defaults instead of hardcoded IPs"""

        hardcoded_ip_pattern = r"192\.168\.1\.\d+"

        files_to_check = [self.env_example_path, self.env_testing_path]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            with open(file_path, "r") as f:
                content = f.read()

            hardcoded_ips = re.findall(hardcoded_ip_pattern, content)
            self.assertEqual(
                [],
                hardcoded_ips,
                f"Hardcoded IP addresses found in {file_path.name}: {hardcoded_ips}",
            )

    def test_documentation_consistency(self):
        """Test that documentation reflects current configuration standards"""

        # Check README.md for model consistency
        if self.readme_path.exists():
            with open(self.readme_path, "r") as f:
                readme_content = f.read()

            # Should mention gpt-oss:20b for production
            self.assertIn(
                self.expected_production_model,
                readme_content,
                f"README.md should reference production model {self.expected_production_model}",
            )

            # Should not have hardcoded IPs in configuration examples
            config_section_match = re.search(
                r"```.*?POSTGRES_DB_URL.*?```", readme_content, re.DOTALL
            )
            if config_section_match:
                config_section = config_section_match.group(0)
                hardcoded_ips = re.findall(r"192\.168\.1\.\d+", config_section)
                self.assertEqual(
                    [],
                    hardcoded_ips,
                    f"README.md configuration examples should not contain hardcoded IPs: {hardcoded_ips}",
                )

    def test_configuration_variable_naming_consistency(self):
        """Test that configuration variable names are consistent across files"""

        # Define expected variable patterns
        variable_patterns = {
            "database": [r"POSTGRES_DB_URL", r"DATABASE_URL", r"DB_CONN"],
            "ollama": [r"OLLAMA_URL", r"OLLAMA_MODEL"],
            "dbt": [r"DBT_PROFILES_DIR", r"DBT_PROJECT_DIR"],
            "paths": [r"DUCKDB_PATH", r"LLM_CACHE_PATH"],
        }

        files_to_check = [self.env_example_path, self.env_testing_path]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            with open(file_path, "r") as f:
                content = f.read()

            # Check for consistent naming patterns
            for category, patterns in variable_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, content):
                        # Ensure it follows naming convention (UPPER_CASE with underscores)
                        var_matches = re.findall(f"({pattern}[A-Z_]*)", content)
                        for var in var_matches:
                            self.assertRegex(
                                var,
                                r"^[A-Z_]+$",
                                f"Variable '{var}' in {file_path.name} should use UPPER_CASE naming",
                            )

    def test_environment_variable_documentation(self):
        """Test that all environment variables are properly documented"""

        with open(self.env_example_path, "r") as f:
            content = f.read()

        # Find all environment variables
        env_vars = re.findall(r"^([A-Z_]+)=", content, re.MULTILINE)

        # Check that each variable has some documentation (comment above or inline)
        poorly_documented_vars = []

        for var in env_vars:
            # Look for comments within 3 lines before the variable
            var_line_match = re.search(f"^{var}=.*$", content, re.MULTILINE)
            if not var_line_match:
                continue

            var_start = var_line_match.start()

            # Get the 200 characters before the variable line to check for comments
            context_start = max(0, var_start - 200)
            context = content[context_start:var_start]

            # Check if there's a comment explaining the variable
            has_comment = "#" in context and any(
                word in context.lower()
                for word in ["config", "server", "database", "path", "model", "timeout"]
            )

            if not has_comment:
                poorly_documented_vars.append(var)

        # Allow some core variables to have minimal documentation
        allowed_minimal = {"DB_NAME", "DB_USER", "DB_PASS", "HOST"}
        poorly_documented_vars = [v for v in poorly_documented_vars if v not in allowed_minimal]

        self.assertEqual(
            [], poorly_documented_vars, f"Variables lacking documentation: {poorly_documented_vars}"
        )

    def test_production_vs_test_environment_separation(self):
        """Test that production and test environments are properly separated"""

        # Production (.env.example) should use robust models and settings
        with open(self.env_example_path, "r") as f:
            prod_content = f.read()

        # Test (.env.testing) should use lightweight models
        if self.env_testing_path.exists():
            with open(self.env_testing_path, "r") as f:
                test_content = f.read()

            # Test environment should have lighter timeout values
            test_timeout_match = re.search(
                r"OLLAMA_GENERATION_TIMEOUT_SECONDS=([0-9]+)", test_content
            )
            if test_timeout_match:
                test_timeout = int(test_timeout_match.group(1))

                prod_timeout_match = re.search(
                    r"OLLAMA_GENERATION_TIMEOUT_SECONDS=([0-9]+)", prod_content
                )
                if prod_timeout_match:
                    prod_timeout = int(prod_timeout_match.group(1))
                    self.assertLessEqual(
                        test_timeout,
                        prod_timeout,
                        "Test environment should have shorter timeouts than production",
                    )


def run_configuration_consistency_tests():
    """Run the configuration consistency test suite"""

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(ConfigurationConsistencyTest)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_configuration_consistency_tests()
    exit(0 if success else 1)
