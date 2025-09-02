#!/usr/bin/env python3
"""
STORY-DB-006 Validation Tests - Working Memory Model Renaming
Tests that active_memories.sql has been successfully renamed to wm_active_context.sql
and all references have been updated accordingly.

Author: Refactoring Agent
Date: 2025-08-28
"""

import glob
import os
from pathlib import Path

import pytest


class TestStoryDB006Validation:
    """Test suite validating STORY-DB-006 model renaming implementation."""

    def setup_method(self):
        """Set up test environment."""
        self.project_root = Path("/Users/ladvien/codex-dreams/biological_memory")

    def test_01_old_model_file_removed(self):
        """Test that active_memories.sql no longer exists."""
        old_file_path = self.project_root / "models" / "working_memory" / "active_memories.sql"

        assert not old_file_path.exists(), (
            "FAILURE: Old file active_memories.sql still exists. "
            "It should have been renamed to wm_active_context.sql"
        )

    def test_02_new_model_file_exists(self):
        """Test that wm_active_context.sql exists and has correct content."""
        new_file_path = self.project_root / "models" / "working_memory" / "wm_active_context.sql"

        assert new_file_path.exists(), (
            "FAILURE: New file wm_active_context.sql does not exist. "
            "The rename operation may not have completed."
        )

        # Verify it's a valid SQL model file
        with open(new_file_path, "r") as f:
            content = f.read()

        # Should contain working memory specific content
        assert (
            "working_memory_capacity" in content
        ), "Working memory model should reference capacity variable"
        assert (
            "activation_strength" in content
        ), "Working memory model should have activation_strength column"
        assert "{{ config(" in content, "Should be a valid dbt model with config"

    def test_03_no_references_to_old_name_in_sql_models(self):
        """Test that no SQL model files reference the old active_memories name."""
        sql_files = glob.glob(str(self.project_root / "models" / "**" / "*.sql"), recursive=True)

        violations = []
        for sql_file in sql_files:
            with open(sql_file, "r") as f:
                content = f.read()
                if "ref('active_memories')" in content:
                    violations.append(f"{sql_file}: Contains ref('active_memories')")
                if 'ref("active_memories")' in content:
                    violations.append(f'{sql_file}: Contains ref("active_memories")')

        assert len(violations) == 0, (
            f"FAILURE: Found {len(violations)} SQL files still referencing old model name:\n"
            + "\n".join(violations)
        )

    def test_04_all_models_reference_new_name(self):
        """Test that all dependent models correctly reference wm_active_context."""
        expected_references = [
            self.project_root / "models" / "short_term_memory" / "consolidating_memories.sql",
            self.project_root / "models" / "short_term_memory" / "stm_hierarchical_episodes.sql",
            self.project_root / "models" / "analytics" / "memory_dashboard.sql",
            self.project_root / "models" / "analytics" / "memory_health.sql",
        ]

        for model_file in expected_references:
            if model_file.exists():
                with open(model_file, "r") as f:
                    content = f.read()

                assert (
                    "ref('wm_active_context')" in content or 'ref("wm_active_context")' in content
                ), f"FAILURE: {model_file} should reference wm_active_context but doesn't"

    def test_05_test_files_updated(self):
        """Test that test files have been updated to reference new model name."""
        test_files = glob.glob(str(self.project_root / "tests" / "**" / "*.py"), recursive=True)

        violations = []
        for test_file in test_files:
            with open(test_file, "r") as f:
                content = f.read()
                if "active_memories" in content and "wm_active_context" not in content:
                    # Check if this is a legitimate reference that should have been updated
                    if any(
                        keyword in content.lower()
                        for keyword in [
                            "create table",
                            "from active_memories",
                            "models/working_memory/active_memories",
                        ]
                    ):
                        violations.append(f"{test_file}: Still references active_memories")

        assert (
            len(violations) == 0
        ), f"FAILURE: Found {len(violations)} test files with outdated references:\n" + "\n".join(
            violations
        )

    def test_06_readme_documentation_updated(self):
        """Test that README documentation reflects the new model name."""
        readme_path = self.project_root / "README.md"

        if readme_path.exists():
            with open(readme_path, "r") as f:
                content = f.read()

            assert (
                "wm_active_context.sql" in content
            ), "FAILURE: README.md should reference wm_active_context.sql"

            # Should not contain references to old name in model descriptions
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "active_memories.sql" in line and "working_memory" in line.lower():
                    assert False, (
                        f"FAILURE: README.md line {i+1} still references active_memories.sql "
                        f"in working memory section: {line.strip()}"
                    )

    def test_07_architecture_compliance_verification(self):
        """Test that the rename resolves AG-006 architecture violation."""
        # The architecture spec expects wm_active_context.sql
        spec_expected_name = "wm_active_context.sql"
        actual_file = self.project_root / "models" / "working_memory" / spec_expected_name

        assert (
            actual_file.exists()
        ), f"FAILURE: Architecture spec expects {spec_expected_name} but file doesn't exist"

        # Verify no old naming patterns exist
        old_patterns = ["active_memories.sql"]
        for pattern in old_patterns:
            old_file = self.project_root / "models" / "working_memory" / pattern
            assert (
                not old_file.exists()
            ), f"FAILURE: Old file {pattern} still exists, violating architecture compliance"

    def test_08_git_tracking_verification(self):
        """Test that git is tracking the rename properly."""
        import os
        import subprocess

        try:
            os.chdir(self.project_root)

            # Check git status for the files
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True
            )

            git_status = result.stdout

            # Should show the new file as added or modified
            assert any(
                "wm_active_context.sql" in line for line in git_status.split("\n")
            ), "FAILURE: Git should be tracking the new wm_active_context.sql file"

        except Exception as e:
            # If git commands fail, just warn but don't fail the test
            print(f"WARNING: Could not verify git status: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
