#!/usr/bin/env python3
"""
PostgreSQL Extension Configuration Standardization Tests
Tests DB-008: PostgreSQL Extension Configuration Standardization

Tests verify that:
1. All files use 'postgres_scanner' (not 'postgres') extension
2. All files use consistent SECRET + ATTACH connection pattern
3. Environment variable usage is standardized
4. Configuration patterns are properly documented

Author: Agent-DB-008
Date: 2025-09-01
Story: DB-008
"""

import unittest
import os
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))


class TestPostgreSQLExtensionStandardization(unittest.TestCase):
    """Test suite for PostgreSQL extension configuration standardization."""
    
    def setUp(self):
        """Set up test environment."""
        self.project_root = project_root
        self.profiles_example_path = self.project_root / 'biological_memory' / 'profiles.yml.example'
        self.setup_sql_path = self.project_root / 'sql' / 'postgres_connection_setup.sql'
        self.test_sql_path = self.project_root / 'sql' / 'test_postgres_connection.sql'
        self.monitor_sql_path = self.project_root / 'biological_memory' / 'postgres_integration_monitor.sql'
        self.bio_setup_sql_path = self.project_root / 'biological_memory' / 'setup_postgres_connection.sql'
    
    def test_profiles_yml_uses_postgres_scanner(self):
        """Test that profiles.yml.example uses postgres_scanner extension."""
        self.assertTrue(
            self.profiles_example_path.exists(),
            f"profiles.yml.example not found at {self.profiles_example_path}"
        )
        
        content = self.profiles_example_path.read_text()
        
        # Should use postgres_scanner
        self.assertIn('postgres_scanner', content, 
                     "profiles.yml.example should use postgres_scanner extension")
        
        # Should NOT use incorrect 'postgres' extension
        # Check context around extensions to avoid false positives from connection strings
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Look for extension definitions
            if 'extensions:' in line.lower():
                # Check the next few lines for postgres extension reference
                for j in range(i+1, min(i+10, len(lines))):
                    ext_line = lines[j].strip()
                    if ext_line.startswith('- postgres') and 'postgres_scanner' not in ext_line:
                        self.fail(f"Found incorrect 'postgres' extension reference in profiles.yml.example line {j+1}: {ext_line}")
    
    def test_sql_files_use_postgres_scanner(self):
        """Test that all SQL files use postgres_scanner extension."""
        sql_files = [
            self.setup_sql_path,
            self.test_sql_path,
            self.monitor_sql_path,
            self.bio_setup_sql_path
        ]
        
        for sql_file in sql_files:
            if sql_file.exists():
                with self.subTest(file=str(sql_file)):
                    content = sql_file.read_text()
                    
                    # Should use postgres_scanner
                    self.assertTrue(
                        'postgres_scanner' in content or 'LOAD postgres_scanner' in content,
                        f"{sql_file.name} should use postgres_scanner extension"
                    )
                    
                    # Should NOT use incorrect 'LOAD postgres;'
                    self.assertNotIn('LOAD postgres;', content,
                                   f"{sql_file.name} should not use 'LOAD postgres;' (should be 'LOAD postgres_scanner;')")
    
    def test_secret_attach_pattern_consistency(self):
        """Test that files consistently use SECRET + ATTACH pattern."""
        sql_files = [
            self.setup_sql_path,
            self.test_sql_path,
            self.monitor_sql_path,
            self.bio_setup_sql_path
        ]
        
        for sql_file in sql_files:
            if sql_file.exists():
                with self.subTest(file=str(sql_file)):
                    content = sql_file.read_text()
                    
                    # If file has ATTACH, it should also have SECRET
                    if 'ATTACH' in content:
                        self.assertIn('SECRET', content,
                                    f"{sql_file.name} uses ATTACH but should also define SECRET")
                        self.assertIn('CREATE OR REPLACE SECRET', content,
                                    f"{sql_file.name} should use CREATE OR REPLACE SECRET pattern")
    
    def test_environment_variable_standardization(self):
        """Test that environment variable usage is standardized."""
        standardized_files = [
            self.setup_sql_path,
            self.test_sql_path,
            self.monitor_sql_path
        ]
        
        for sql_file in standardized_files:
            if sql_file.exists():
                with self.subTest(file=str(sql_file)):
                    content = sql_file.read_text()
                    
                    # Should use getenv() function for environment variables
                    if 'POSTGRES' in content and 'SECRET' in content:
                        self.assertTrue(
                            'getenv(' in content,
                            f"{sql_file.name} should use getenv() for environment variables"
                        )
                        
                        # Should use standardized environment variable names
                        if 'getenv(' in content:
                            expected_vars = ['POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
                            found_vars = [var for var in expected_vars if var in content]
                            self.assertTrue(
                                len(found_vars) > 0,
                                f"{sql_file.name} should use standardized environment variable names"
                            )
    
    def test_no_hardcoded_credentials(self):
        """Test that no files contain hardcoded credentials."""
        all_files = [
            self.profiles_example_path,
            self.setup_sql_path,
            self.test_sql_path,
            self.monitor_sql_path
        ]
        
        # Sensitive patterns to avoid (allow the bio setup file as it's for testing)
        sensitive_patterns = [
            'PASSWORD \'',
            'PASSWORD "',
            'password:',
            'pwd='
        ]
        
        for file_path in all_files:
            if file_path.exists():
                with self.subTest(file=str(file_path)):
                    content = file_path.read_text()
                    
                    # Check for hardcoded credentials (but allow environment variable usage)
                    for pattern in sensitive_patterns:
                        if pattern in content:
                            # Make sure it's not followed by getenv or environment variable
                            lines_with_pattern = [line for line in content.split('\n') if pattern in line]
                            for line in lines_with_pattern:
                                if 'getenv(' not in line and '$' not in line:
                                    # Allow the bio setup file as it has test credentials
                                    if file_path == self.bio_setup_sql_path:
                                        continue
                                    self.fail(f"Found potential hardcoded credential in {file_path.name}: {line.strip()}")
    
    def test_connection_alias_consistency(self):
        """Test that connection aliases are consistently named."""
        sql_files = [
            (self.setup_sql_path, 'postgres_db'),
            (self.test_sql_path, 'test_db'),
            (self.monitor_sql_path, 'codex_db'),
            (self.bio_setup_sql_path, 'codex_db')
        ]
        
        for sql_file, expected_alias in sql_files:
            if sql_file.exists():
                with self.subTest(file=str(sql_file)):
                    content = sql_file.read_text()
                    
                    # If file has ATTACH, check for expected alias
                    if 'ATTACH' in content:
                        self.assertIn(f'AS {expected_alias}', content,
                                    f"{sql_file.name} should use consistent connection alias '{expected_alias}'")
    
    def test_extension_loading_order(self):
        """Test that extensions are loaded in proper order."""
        sql_files = [
            self.setup_sql_path,
            self.test_sql_path,
            self.monitor_sql_path,
            self.bio_setup_sql_path
        ]
        
        for sql_file in sql_files:
            if sql_file.exists():
                with self.subTest(file=str(sql_file)):
                    content = sql_file.read_text()
                    
                    # postgres_scanner should be loaded before ATTACH commands
                    if 'LOAD postgres_scanner' in content and 'ATTACH' in content:
                        load_pos = content.find('LOAD postgres_scanner')
                        attach_pos = content.find('ATTACH')
                        
                        self.assertTrue(
                            load_pos < attach_pos,
                            f"{sql_file.name} should load postgres_scanner before ATTACH commands"
                        )
    
    def test_documentation_accuracy(self):
        """Test that documentation accurately reflects the standardized configuration."""
        # Check profiles.yml.example documentation
        if self.profiles_example_path.exists():
            content = self.profiles_example_path.read_text()
            
            # Should have accurate comments
            if 'postgres_scanner' in content:
                self.assertIn('PostgreSQL', content,
                            "profiles.yml.example should document PostgreSQL connection purpose")
        
        # Check SQL file documentation
        sql_files = [self.setup_sql_path, self.test_sql_path]
        for sql_file in sql_files:
            if sql_file.exists():
                with self.subTest(file=str(sql_file)):
                    content = sql_file.read_text()
                    
                    # Should have header comments explaining purpose
                    lines = content.split('\n')
                    comment_lines = [line for line in lines[:10] if line.strip().startswith('--')]
                    self.assertTrue(
                        len(comment_lines) >= 1,
                        f"{sql_file.name} should have header comments explaining its purpose"
                    )


class TestExtensionFunctionality(unittest.TestCase):
    """Test PostgreSQL extension functionality without requiring live connection."""
    
    def setUp(self):
        """Set up test environment."""
        self.project_root = project_root
    
    def test_postgres_scanner_syntax_validity(self):
        """Test that postgres_scanner usage follows correct DuckDB syntax."""
        sql_files = [
            self.project_root / 'sql' / 'postgres_connection_setup.sql',
            self.project_root / 'sql' / 'test_postgres_connection.sql',
            self.project_root / 'biological_memory' / 'postgres_integration_monitor.sql',
            self.project_root / 'biological_memory' / 'setup_postgres_connection.sql'
        ]
        
        for sql_file in sql_files:
            if sql_file.exists():
                with self.subTest(file=str(sql_file)):
                    content = sql_file.read_text()
                    
                    # Check SECRET syntax if present
                    if 'CREATE OR REPLACE SECRET' in content:
                        # Should have TYPE POSTGRES
                        self.assertIn('TYPE POSTGRES', content,
                                    f"{sql_file.name} SECRET should specify TYPE POSTGRES")
                        
                        # Should have required parameters
                        required_params = ['HOST', 'DATABASE', 'USER', 'PASSWORD']
                        for param in required_params:
                            self.assertIn(param, content,
                                        f"{sql_file.name} SECRET should include {param} parameter")
                    
                    # Check ATTACH syntax if present
                    if 'ATTACH' in content and 'SECRET' in content:
                        # Should use empty string with SECRET
                        self.assertIn("ATTACH ''", content,
                                    f"{sql_file.name} should use ATTACH '' with SECRET pattern")
                        
                        # Should specify TYPE POSTGRES in ATTACH
                        self.assertIn('TYPE POSTGRES', content,
                                    f"{sql_file.name} ATTACH should specify TYPE POSTGRES")


def run_postgres_extension_tests():
    """Run all PostgreSQL extension standardization tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPostgreSQLExtensionStandardization))
    suite.addTests(loader.loadTestsFromTestCase(TestExtensionFunctionality))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("Running DB-008 PostgreSQL Extension Configuration Standardization Tests...")
    print("=" * 70)
    
    success = run_postgres_extension_tests()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ ALL POSTGRESQL EXTENSION STANDARDIZATION TESTS PASSED")
        print("DB-008: PostgreSQL extension configuration standardized successfully")
        print("Extension: postgres_scanner (standardized)")
        print("Pattern: SECRET + ATTACH (standardized)")
        print("Environment: getenv() with fallbacks (standardized)")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("❌ SOME POSTGRESQL EXTENSION STANDARDIZATION TESTS FAILED")
        print("Check the test output above for details")
        print("=" * 70)
        sys.exit(1)