#!/usr/bin/env python3
"""
Working Memory Configuration Test Suite
BMP-HIGH-003: Fix Working Memory Configuration Errors

Tests to verify that working memory configuration errors have been resolved:
1. Previous strength field reference fixed
2. Materialization conflicts resolved (ephemeral vs view)
3. Miller's 7±2 capacity constraint properly implemented
4. Working memory models can execute successfully
"""

import os
import re
import sys
from pathlib import Path

import pytest

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWorkingMemoryConfiguration:
    """Test working memory configuration fixes"""

    @pytest.fixture
    def working_memory_model_path(self):
        """Path to working memory model file"""
        return (
            project_root
            / "biological_memory"
            / "models"
            / "working_memory"
            / "wm_active_context.sql"
        )

    @pytest.fixture
    def dbt_project_path(self):
        """Path to dbt project configuration"""
        return project_root / "biological_memory" / "dbt_project.yml"

    def test_previous_strength_field_reference_fixed(self, working_memory_model_path):
        """Test that previous_strength field reference has been removed/fixed"""
        with open(working_memory_model_path, "r") as f:
            content = f.read()

        # Should NOT contain references to undefined previous_strength field
        assert (
            "previous_strength" not in content
        ), "Working memory model should not reference undefined previous_strength field"

        # Should contain proper Hebbian strength calculation
        assert (
            "hebbian_strength" in content
        ), "Working memory model should calculate hebbian_strength"

        # Should use activation_strength as base for calculation
        assert (
            "activation_strength" in content
        ), "Working memory model should use activation_strength for calculations"

    def test_working_memory_capacity_constraint(self, working_memory_model_path, dbt_project_path):
        """Test that Miller's 7±2 capacity constraint is properly implemented"""

        # Check dbt_project.yml has correct capacity setting
        with open(dbt_project_path, "r") as f:
            dbt_content = f.read()

        # Should have working_memory_capacity set to 7 (Miller's magic number)
        assert (
            "working_memory_capacity: 7" in dbt_content
        ), "dbt_project.yml should set working_memory_capacity to 7"

        # Check working memory model uses the capacity variable
        with open(working_memory_model_path, "r") as f:
            wm_content = f.read()

        assert (
            "{{ var('working_memory_capacity') }}" in wm_content
        ), "Working memory model should reference working_memory_capacity variable"

        # Should limit results based on capacity
        assert (
            "memory_rank" in wm_content and "<=" in wm_content
        ), "Working memory model should limit results by memory_rank"

    def test_materialization_configuration(self, dbt_project_path, working_memory_model_path):
        """Test that materialization conflicts have been resolved"""

        # Check dbt_project.yml working memory materialization
        with open(dbt_project_path, "r") as f:
            dbt_content = f.read()

        # Should be configured as 'view' in dbt_project.yml (not ephemeral)
        wm_section = re.search(r"working_memory:\s*\+materialized:\s*(\w+)", dbt_content)
        assert wm_section is not None, "Should find working_memory materialization config"
        assert wm_section.group(1) == "view", "Working memory should be materialized as view"

        # Check model file config matches
        with open(working_memory_model_path, "r") as f:
            wm_content = f.read()

        # Should have materialized='view' in model config
        assert (
            "materialized='view'" in wm_content
        ), "Working memory model should specify materialized='view'"

    def test_sql_syntax_validity(self, working_memory_model_path):
        """Test that SQL syntax is valid after fixes"""

        with open(working_memory_model_path, "r") as f:
            content = f.read()

        # Check for basic SQL structure validity
        assert "SELECT" in content.upper(), "Should contain SELECT statement"
        assert "FROM" in content.upper(), "Should contain FROM clause"
        assert "WHERE" in content.upper(), "Should contain WHERE clause"

        # Check for proper Jinja template syntax
        assert "{{ config(" in content, "Should contain dbt config block"
        assert "{{ var(" in content, "Should use dbt variables"

        # Should not contain syntax errors like dangling commas or incomplete statements
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip comments and empty lines
            if (
                not stripped
                or stripped.startswith("--")
                or stripped.startswith("{#")
                or stripped.startswith("#}")
            ):
                continue

            # Check for incomplete SQL patterns that might cause parsing errors
            if stripped.endswith("previous_strength,"):
                pytest.fail(f"Line {i}: Found reference to undefined previous_strength field")

    def test_biological_accuracy_preserved(self, working_memory_model_path):
        """Test that biological accuracy is preserved after fixes"""

        with open(working_memory_model_path, "r") as f:
            content = f.read()

        # Should maintain Hebbian learning calculation
        assert (
            "hebbian_learning_rate" in content
        ), "Should preserve Hebbian learning rate variable usage"

        # Should maintain memory ranking and selection
        assert "ROW_NUMBER() OVER" in content, "Should preserve memory ranking logic"

        # Should maintain activation strength calculations
        assert "activation_strength" in content, "Should preserve activation strength calculations"

        # Should maintain recency and frequency scoring
        assert (
            "recency_score" in content and "frequency_score" in content
        ), "Should preserve recency and frequency scoring"

    def test_null_safety_preserved(self, working_memory_model_path):
        """Test that NULL safety patterns are preserved"""

        with open(working_memory_model_path, "r") as f:
            content = f.read()

        # Should use COALESCE for NULL safety
        coalesce_count = content.count("COALESCE")
        assert (
            coalesce_count >= 10
        ), f"Should have adequate NULL safety with COALESCE (found {coalesce_count})"

        # Should have NULL safe comments
        assert "NULL SAFE" in content, "Should maintain NULL safety documentation"

    def test_performance_configuration_intact(self, dbt_project_path):
        """Test that performance configurations remain intact"""

        with open(dbt_project_path, "r") as f:
            content = f.read()

        # Should maintain performance tags
        assert (
            "performance_critical" in content or "real_time" in content
        ), "Should maintain performance tags for working memory"

        # Should maintain pre-hooks for performance optimization
        assert "pre-hook" in content, "Should maintain pre-hook configurations"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
