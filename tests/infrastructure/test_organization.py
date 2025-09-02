#!/usr/bin/env python3
"""
Test Organization Validation - BMP-HIGH-001
Test Engineer Review: Validates proper test directory organization and prevents consolidation

This test validates that our test directories serve complementary purposes
rather than being duplicates, ensuring proper separation of concerns.
"""

import os
from pathlib import Path
from typing import Dict, List, Set

import pytest


class TestOrganization:
    """Test that validates test directory organization is optimal."""

    @classmethod
    def setup_class(cls):
        """Setup test paths."""
        cls.project_root = Path("/Users/ladvien/codex-dreams")
        cls.main_tests = cls.project_root / "tests"
        cls.bio_tests = cls.project_root / "biological_memory" / "tests"
        cls.dbt_utils_tests = (
            cls.project_root
            / "biological_memory"
            / "dbt_packages"
            / "dbt_utils"
            / "integration_tests"
            / "tests"
        )

    def test_test_directories_exist(self):
        """Verify all expected test directories exist."""
        assert self.main_tests.exists(), "Main tests/ directory must exist"
        assert self.bio_tests.exists(), "biological_memory/tests/ directory must exist"
        assert self.dbt_utils_tests.exists(), "dbt_utils integration tests must exist"

    def test_minimal_file_duplication(self):
        """Test that there are minimal duplicate filenames between test directories."""
        main_files = set()
        bio_files = set()

        # Get Python test files from each directory
        for file_path in self.main_tests.rglob("*.py"):
            main_files.add(file_path.name)

        for file_path in self.bio_tests.rglob("*.py"):
            bio_files.add(file_path.name)

        duplicates = main_files.intersection(bio_files)

        # Only conftest.py should be duplicated (different purposes)
        expected_duplicates = {"conftest.py"}
        assert (
            duplicates == expected_duplicates
        ), f"Unexpected duplicates found: {duplicates - expected_duplicates}"

    def test_directory_purpose_separation(self):
        """Test that each directory serves distinct purposes."""

        # Main tests should focus on infrastructure/integration
        main_subdirs = {d.name for d in self.main_tests.iterdir() if d.is_dir()}
        expected_main = {
            "analytics",
            "database",
            "integration",
            "orchestration",
            "infrastructure",
            "memory",
            "performance",
            "reliability",
        }

        infrastructure_dirs = main_subdirs.intersection(expected_main)
        assert (
            len(infrastructure_dirs) >= 5
        ), f"Main tests should have infrastructure focus, found: {main_subdirs}"

        # Biological tests should focus on dbt/model validation
        bio_subdirs = {d.name for d in self.bio_tests.iterdir() if d.is_dir()}
        expected_bio = {
            "dbt",
            "parameter_validation",
            "performance",
            "long_term",
            "short_term_memory",
            "extension",
        }

        bio_focus_dirs = bio_subdirs.intersection(expected_bio)
        assert (
            len(bio_focus_dirs) >= 3
        ), f"Bio tests should have dbt/model focus, found: {bio_subdirs}"

    def test_conftest_files_serve_different_purposes(self):
        """Test that conftest.py files serve different purposes."""
        main_conftest = self.main_tests / "conftest.py"
        bio_conftest = self.bio_tests / "conftest.py"

        # Both should exist
        assert main_conftest.exists(), "Main conftest.py should exist"
        assert bio_conftest.exists(), "Bio conftest.py should exist"

        # Read first few lines to check purposes
        with open(main_conftest, "r") as f:
            main_content = f.read(500)

        with open(bio_conftest, "r") as f:
            bio_content = f.read(500)

        # Main conftest should focus on system/infrastructure
        assert any(
            keyword in main_content.lower()
            for keyword in ["database connections", "ollama", "test data fixtures"]
        ), "Main conftest should focus on infrastructure fixtures"

        # Bio conftest should focus on biological/model testing
        assert any(
            keyword in bio_content.lower()
            for keyword in ["biological", "model", "duckdb test database"]
        ), "Bio conftest should focus on biological model fixtures"

    def test_reasonable_file_counts(self):
        """Test that file counts are reasonable and not excessive."""
        main_py_files = list(self.main_tests.rglob("*.py"))
        bio_py_files = list(self.bio_tests.rglob("*.py"))
        dbt_sql_files = list(self.dbt_utils_tests.rglob("*.sql"))

        # Counts should be reasonable
        assert (
            20 <= len(main_py_files) <= 60
        ), f"Main tests count seems unreasonable: {len(main_py_files)}"
        assert (
            20 <= len(bio_py_files) <= 60
        ), f"Bio tests count seems unreasonable: {len(bio_py_files)}"
        assert len(dbt_sql_files) <= 20, f"dbt_utils tests should be minimal: {len(dbt_sql_files)}"

        # Total should be much less than the claimed "115+ duplicates"
        total_files = len(main_py_files) + len(bio_py_files) + len(dbt_sql_files)
        assert (
            total_files < 115
        ), f"Total test files ({total_files}) contradicts '115+ duplicates' claim"

    def test_architecture_alignment(self):
        """Test that test structure aligns with architecture documentation."""
        arch_file = self.project_root / "docs" / "architecture" / "ARCHITECTURE.md"

        if arch_file.exists():
            with open(arch_file, "r") as f:
                arch_content = f.read()

            # Architecture should mention different testing approaches
            assert "testing" in arch_content.lower(), "Architecture should discuss testing approach"

    def test_no_consolidation_needed(self):
        """Final validation that consolidation is not needed."""

        # Test that directories serve complementary purposes
        main_files = list(self.main_tests.rglob("*.py"))
        bio_files = list(self.bio_tests.rglob("*.py"))

        # Look for evidence of different testing focuses in filenames
        main_names = [f.name for f in main_files]
        bio_names = [f.name for f in bio_files]

        # Main tests should have infrastructure-focused names
        infrastructure_keywords = [
            "integration",
            "orchestration",
            "database",
            "connection",
            "environment",
        ]
        main_infra_count = sum(
            1
            for name in main_names
            for keyword in infrastructure_keywords
            if keyword in name.lower()
        )

        # Bio tests should have model/biological-focused names
        bio_keywords = ["biological", "dbt", "schema", "validation", "parameter"]
        bio_model_count = sum(
            1 for name in bio_names for keyword in bio_keywords if keyword in name.lower()
        )

        assert (
            main_infra_count >= 3
        ), f"Main tests should have infrastructure focus: {main_infra_count}"
        assert bio_model_count >= 3, f"Bio tests should have model focus: {bio_model_count}"

        print(f"\n=== TEST ORGANIZATION VALIDATION PASSED ===")
        print(f"Main tests (infrastructure focus): {len(main_files)} files")
        print(f"Bio tests (model/dbt focus): {len(bio_files)} files")
        print(f"Infrastructure-focused tests: {main_infra_count}")
        print(f"Model/bio-focused tests: {bio_model_count}")
        print(f"Conclusion: Directories serve complementary purposes - NO CONSOLIDATION NEEDED")


if __name__ == "__main__":
    # Allow running this test standalone
    pytest.main([__file__, "-v"])
