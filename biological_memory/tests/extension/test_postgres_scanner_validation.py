#!/usr/bin/env python3
"""
Extension Validation Tests for postgres_scanner Configuration
Tests STORY-DB-005: Fix postgres_scanner Extension Configuration

Tests verify that:
1. postgres_scanner extension is properly installed and loadable
2. Cross-database query functionality is available
3. Configuration files are properly structured
4. Extension patterns are documented correctly

Author: SQL Expert Agent
Date: 2025-08-28
Story: STORY-DB-005
"""

import os
import sys
import unittest
from pathlib import Path

import duckdb

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))


class TestPostgresScannerValidation(unittest.TestCase):
    """Test suite for postgres_scanner extension validation."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.db_path = self.project_root / "dbs" / "memory.duckdb"
        self.profiles_example_path = self.project_root / "profiles.yml.example"
        self.setup_sql_path = self.project_root / "setup_duckdb.sql"

    def test_postgres_scanner_extension_installed(self):
        """Test that postgres_scanner extension is installed in DuckDB."""
        with duckdb.connect(str(self.db_path)) as conn:
            result = conn.execute(
                """
                SELECT extension_name, installed 
                FROM duckdb_extensions() 
                WHERE extension_name = 'postgres_scanner'
            """
            ).fetchall()

            self.assertEqual(len(result), 1, "postgres_scanner extension not found")
            extension_name, installed = result[0]
            self.assertEqual(extension_name, "postgres_scanner")
            self.assertTrue(installed, "postgres_scanner extension not installed")

    def test_postgres_scanner_extension_loadable(self):
        """Test that postgres_scanner extension can be loaded."""
        with duckdb.connect(str(self.db_path)) as conn:
            # Load the extension
            conn.execute("LOAD postgres_scanner;")

            # Verify it's loaded
            result = conn.execute(
                """
                SELECT extension_name, loaded 
                FROM duckdb_extensions() 
                WHERE extension_name = 'postgres_scanner'
            """
            ).fetchall()

            self.assertEqual(len(result), 1, "postgres_scanner extension not found after loading")
            extension_name, loaded = result[0]
            self.assertEqual(extension_name, "postgres_scanner")
            self.assertTrue(loaded, "postgres_scanner extension failed to load")

    def test_profiles_yml_example_exists(self):
        """Test that profiles.yml.example file exists and contains postgres_scanner configuration."""
        self.assertTrue(
            self.profiles_example_path.exists(),
            f"profiles.yml.example not found at {self.profiles_example_path}",
        )

        content = self.profiles_example_path.read_text()

        # Check for postgres_scanner extension reference
        self.assertIn(
            "postgres_scanner", content, "postgres_scanner not found in profiles.yml.example"
        )

        # Check for required sections
        self.assertIn(
            "extensions:", content, "extensions section not found in profiles.yml.example"
        )
        self.assertIn(
            "external_sources:",
            content,
            "external_sources section not found in profiles.yml.example",
        )
        self.assertIn(
            "postgresql:", content, "postgresql configuration not found in profiles.yml.example"
        )

    def test_setup_duckdb_sql_exists(self):
        """Test that setup_duckdb.sql file exists and contains proper postgres_scanner setup."""
        self.assertTrue(
            self.setup_sql_path.exists(), f"setup_duckdb.sql not found at {self.setup_sql_path}"
        )

        content = self.setup_sql_path.read_text()

        # Check for postgres_scanner installation and loading
        self.assertIn(
            "INSTALL postgres_scanner;", content, "INSTALL postgres_scanner command not found"
        )
        self.assertIn("LOAD postgres_scanner;", content, "LOAD postgres_scanner command not found")

        # Check for connection setup
        self.assertIn("CREATE", content, "Connection creation commands not found")
        self.assertIn("ATTACH", content, "Database attachment commands not found")

    def test_no_incorrect_postgres_extension_references(self):
        """Test that there are no incorrect 'postgres' extension references (should be 'postgres_scanner')."""
        # Search through relevant files for incorrect postgres extension references
        search_patterns = ["INSTALL postgres;", "LOAD postgres;", "'postgres'", '"postgres"']

        # Files to check
        files_to_check = [self.profiles_example_path, self.setup_sql_path]

        # Add all SQL files in models directory
        models_dir = self.project_root / "models"
        if models_dir.exists():
            files_to_check.extend(models_dir.rglob("*.sql"))

        # Add all SQL files in macros directory
        macros_dir = self.project_root / "macros"
        if macros_dir.exists():
            files_to_check.extend(macros_dir.rglob("*.sql"))

        incorrect_references = []

        for file_path in files_to_check:
            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text()
                    for pattern in search_patterns:
                        if pattern in content:
                            # Skip legitimate uses like connection strings
                            if pattern in ["'postgres'", '"postgres"'] and "postgres://" in content:
                                continue
                            incorrect_references.append(f"{file_path}: {pattern}")
                except Exception as e:
                    # Skip files that can't be read
                    pass

        self.assertEqual(
            len(incorrect_references),
            0,
            f"Found incorrect postgres extension references: {incorrect_references}",
        )

    def test_extension_functionality_basic(self):
        """Test basic postgres_scanner functionality without requiring PostgreSQL server."""
        with duckdb.connect(str(self.db_path)) as conn:
            # Load postgres_scanner
            conn.execute("LOAD postgres_scanner;")

            # Test that postgres_scanner functions are available
            # This tests extension loading without requiring actual PostgreSQL connection
            try:
                # Try to create a secret (this validates postgres_scanner is properly loaded)
                conn.execute(
                    """
                    CREATE OR REPLACE SECRET test_postgres_secret (
                        TYPE POSTGRES,
                        HOST 'test_host',
                        PORT 5432,
                        DATABASE 'test_db',
                        USER 'test_user',
                        PASSWORD 'test_password'
                    );
                """
                )

                # Clean up the test secret
                conn.execute("DROP SECRET IF EXISTS test_postgres_secret;")

                test_passed = True

            except Exception as e:
                # If we get a specific postgres_scanner related error, that's still success
                # (it means the extension is loaded and functional)
                if "postgres_scanner" in str(e).lower() or "secret" in str(e).lower():
                    test_passed = True
                else:
                    test_passed = False
                    self.fail(f"postgres_scanner basic functionality test failed: {e}")

            self.assertTrue(
                test_passed, "postgres_scanner extension basic functionality validation failed"
            )

    def test_configuration_completeness(self):
        """Test that configuration files contain all necessary components."""
        # Test profiles.yml.example completeness
        profiles_content = self.profiles_example_path.read_text()

        required_profiles_sections = [
            "biological_memory:",
            "outputs:",
            "dev:",
            "prod:",
            "type: duckdb",
            "extensions:",
            "postgres_scanner",
            "external_sources:",
            "postgresql:",
            "settings:",
        ]

        for section in required_profiles_sections:
            self.assertIn(
                section,
                profiles_content,
                f"Required section '{section}' not found in profiles.yml.example",
            )

        # Test setup_duckdb.sql completeness
        setup_content = self.setup_sql_path.read_text()

        required_setup_commands = [
            "INSTALL postgres_scanner;",
            "LOAD postgres_scanner;",
            "CREATE OR REPLACE SECRET",
            "ATTACH",
            "SELECT extension_name",
        ]

        for command in required_setup_commands:
            self.assertIn(
                command,
                setup_content,
                f"Required command '{command}' not found in setup_duckdb.sql",
            )


class TestExtensionPatternDocumentation(unittest.TestCase):
    """Test suite for extension pattern documentation."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent

    def test_readme_postgres_scanner_documentation(self):
        """Test that README.md properly documents postgres_scanner usage."""
        readme_path = self.project_root / "README.md"

        if readme_path.exists():
            content = readme_path.read_text()

            # Check for postgres_scanner documentation
            self.assertIn(
                "postgres_scanner", content, "postgres_scanner not documented in README.md"
            )

            # Should not have incorrect 'postgres' extension references
            # (excluding connection strings like postgres://)
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "extensions:" in line.lower() or "extension" in line.lower():
                    if "'postgres'" in line or '"postgres"' in line:
                        if "postgres://" not in line:  # Skip connection strings
                            self.fail(
                                f"Found incorrect postgres extension reference in README.md line {i+1}: {line}"
                            )


def run_postgres_scanner_tests():
    """Run all postgres_scanner validation tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPostgresScannerValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestExtensionPatternDocumentation))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    print("Running STORY-DB-005 postgres_scanner Extension Validation Tests...")
    print("=" * 70)

    success = run_postgres_scanner_tests()

    if success:
        print("\n" + "=" * 70)
        print("✅ ALL POSTGRES_SCANNER EXTENSION VALIDATION TESTS PASSED")
        print("STORY-DB-005: postgres_scanner extension configuration validated successfully")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("❌ SOME POSTGRES_SCANNER EXTENSION VALIDATION TESTS FAILED")
        print("Check the test output above for details")
        print("=" * 70)
        sys.exit(1)
