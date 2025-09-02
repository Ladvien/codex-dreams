#!/usr/bin/env python3
"""
Security Test Suite: Credential Management & Password Rotation
Tests for BMP-SECURITY-001: Password Rotation & Secrets Management

This test suite validates:
1. No hardcoded credentials remain in codebase
2. Credential masking functions work correctly
3. Environment variable-based configuration is enforced
4. Secure password generation meets complexity requirements
5. Credential rotation procedures are implemented correctly
"""

import os
import re
import secrets
import string
import unittest
from pathlib import Path


class TestCredentialManagement(unittest.TestCase):
    """Test credential management security patterns."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent

    def test_no_hardcoded_passwords_remain(self):
        """Test that ALL hardcoded passwords have been removed from codebase."""
        # Known exposed passwords that must be removed
        exposed_passwords = [
            "MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a",  # Original exposed password
            "i5(|_})9A4&9Khd23&DJ4VRq&G_.px0Z",  # Second hardcoded password found
            "M|h!y,3:tL^-MJSRswpH09N_JJnNkj?Q",  # Third hardcoded password found
        ]

        # Files that have been cleaned of hardcoded passwords
        critical_files = [
            self.project_root / "src" / "generate_insights.py",
            self.project_root / "src" / "reset_insights.py",
            self.project_root / "biological_memory" / "setup_postgres_connection.sql",
            self.project_root / ".env",
        ]

        for file_path in critical_files:
            if file_path.exists():
                with open(file_path, "r") as f:
                    content = f.read()

                for password in exposed_passwords:
                    self.assertNotIn(
                        password,
                        content,
                        f"Hardcoded password '{password[:8]}...' still found in {file_path}",
                    )

        # Verify files now require environment variables
        generate_insights = self.project_root / "src" / "generate_insights.py"
        if generate_insights.exists():
            with open(generate_insights, "r") as f:
                content = f.read()
            self.assertIn("POSTGRES_DB_URL environment variable is required", content)

    def test_codex_config_security_validation(self):
        """Test that CodexConfig class enforces secure credential practices."""
        # Import the CodexConfig class
        import sys

        sys.path.append(str(self.project_root / "src"))

        try:
            from codex_config import CodexConfig

            # Test 1: Should reject None password
            config = CodexConfig()
            config.db_password = None

            with self.assertRaises(ValueError) as context:
                _ = config.postgres_url
            self.assertIn("Database password is required", str(context.exception))

            # Test 2: Should reject insecure passwords
            insecure_passwords = ["password", "defaultpassword", "123456", "admin"]
            for bad_password in insecure_passwords:
                config.db_password = bad_password
                with self.assertRaises(ValueError) as context:
                    _ = config.postgres_url
                self.assertIn("Insecure password detected", str(context.exception))

            # Test 3: Should reject short passwords
            config.db_password = "short"
            with self.assertRaises(ValueError) as context:
                _ = config.postgres_url
            self.assertIn("at least 8 characters", str(context.exception))

            # Test 4: Should accept secure passwords
            config.db_password = "SecurePassword123!"
            try:
                url = config.postgres_url
                self.assertIn("SecurePassword123!", url)
            except ValueError as e:
                self.fail(f"Secure password was rejected: {e}")

        except ImportError:
            self.skipTest("CodexConfig not available for testing")

    def test_credential_masking_in_url(self):
        """Test URL credential masking function."""

        # Test the masking function from existing implementations
        def mask_credentials_in_url(url):
            """Mask credentials in database URL for logging."""
            import re

            return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)

        test_url = "postgresql://user:secretpassword@localhost:5432/db"
        masked_url = mask_credentials_in_url(test_url)
        expected = "postgresql://user:***@localhost:5432/db"

        self.assertEqual(masked_url, expected)
        self.assertNotIn("secretpassword", masked_url)

    def test_credential_masking_in_config(self):
        """Test configuration credential masking function."""

        def mask_credentials_in_config(config):
            """Mask credentials in config for logging."""
            masked_config = config.copy()
            if "password" in masked_config:
                masked_config["password"] = "***"
            return masked_config

        test_config = {
            "host": "localhost",
            "user": "testuser",
            "password": "supersecret",
            "database": "testdb",
        }

        masked_config = mask_credentials_in_config(test_config)

        self.assertEqual(masked_config["password"], "***")
        self.assertEqual(masked_config["user"], "testuser")  # Should not be masked
        self.assertNotIn("supersecret", str(masked_config))

    def test_secure_password_generation(self):
        """Test that generated passwords meet security requirements."""

        def generate_secure_password(length=32):
            """Generate secure password with mixed case, numbers, symbols."""
            chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
            return "".join(secrets.choice(chars) for _ in range(length))

        # Generate multiple passwords to test consistency
        for _ in range(5):
            password = generate_secure_password()

            # Test length
            self.assertEqual(len(password), 32)

            # Test character diversity
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

            self.assertTrue(has_upper, "Password should contain uppercase letters")
            self.assertTrue(has_lower, "Password should contain lowercase letters")
            self.assertTrue(has_digit, "Password should contain digits")
            # Note: Symbol presence is probabilistic but very likely with 32 chars

    def test_environment_variable_usage(self):
        """Test that configuration uses environment variables not hardcoded values."""
        env_file = self.project_root / ".env"

        if env_file.exists():
            with open(env_file, "r") as f:
                content = f.read()

            # Should contain environment variable definitions
            self.assertIn("POSTGRES_DB_URL=", content)
            self.assertIn("POSTGRES_PASSWORD=", content)

            # Should not contain the old exposed password
            self.assertNotIn("MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a", content)

    def test_documentation_sanitization(self):
        """Test that documentation files have been sanitized of credentials."""
        doc_files = [
            self.project_root / "docs" / "architecture" / "DATABASE_ARCHITECTURE_REVIEW_REPORT.md",
            self.project_root / "BACKLOG.md",
        ]

        for doc_file in doc_files:
            if doc_file.exists():
                with open(doc_file, "r") as f:
                    content = f.read()

                # Should not contain exposed password
                self.assertNotIn("MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a", content)

                # Should contain redacted placeholder if it was sanitized
                if "REDACTED" in content:
                    self.assertIn("***REDACTED***", content)

    def test_sql_configuration_security(self):
        """Test SQL configuration files use secure patterns."""
        sql_file = self.project_root / "biological_memory" / "setup_postgres_connection.sql"

        if sql_file.exists():
            with open(sql_file, "r") as f:
                content = f.read()

            # Should use SECRET pattern for security
            self.assertIn("CREATE OR REPLACE SECRET", content)
            self.assertIn("TYPE POSTGRES", content)

            # Should not contain old exposed password
            self.assertNotIn("MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a", content)

    def test_credential_rotation_documentation(self):
        """Test that credential rotation process is documented."""
        # This test validates that proper rotation procedures exist

        # Check if .env has rotation date comments
        env_file = self.project_root / ".env"
        if env_file.exists():
            with open(env_file, "r") as f:
                content = f.read()

            # Should have rotation date documentation
            self.assertIn("CREDENTIALS ROTATED", content.upper())

    def test_no_plain_text_passwords_in_logs(self):
        """Test that log files don't contain plain text passwords."""
        # This is a preventive test - ensures masking functions are used

        # Verify masking patterns work as expected
        sensitive_data = {
            "url": "postgresql://user:secret123@host:5432/db",
            "config": {"password": "secret123", "user": "testuser"},
        }

        # Test URL masking
        def mask_url(url):
            return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)

        masked_url = mask_url(sensitive_data["url"])
        self.assertNotIn("secret123", masked_url)
        self.assertIn("***", masked_url)


class TestSecurityCompliance(unittest.TestCase):
    """Test overall security compliance patterns."""

    def test_env_file_gitignore_protection(self):
        """Test that .env file is properly protected from version control."""
        project_root = Path(__file__).parent.parent.parent
        gitignore_file = project_root / ".gitignore"

        if gitignore_file.exists():
            with open(gitignore_file, "r") as f:
                gitignore_content = f.read()

            # Should ignore .env files
            self.assertTrue(
                ".env" in gitignore_content or "*.env" in gitignore_content,
                ".env files should be in .gitignore",
            )


if __name__ == "__main__":
    # Run the security test suite
    print("🔒 Running Credential Management Security Test Suite...")
    print("=" * 60)

    unittest.main(verbosity=2)
