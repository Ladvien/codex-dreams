#!/usr/bin/env python3
"""
Test suite for dbt configuration validation
Tests biological memory pipeline dbt setup and functionality

This test suite validates:
1. dbt profile and project configuration
2. Database connections (DuckDB and PostgreSQL)
3. Custom macro functionality
4. Model compilation and execution
5. Biological parameter validation
"""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml


class TestDbtConfiguration:
    """Test dbt project configuration and setup"""

    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        cls.project_dir = Path("/Users/ladvien/biological_memory")
        cls.profiles_dir = Path.home() / ".dbt"
        os.chdir(cls.project_dir)

    def test_dbt_profiles_exist(self):
        """Test that dbt profiles.yml exists and is valid"""
        profiles_path = self.profiles_dir / "profiles.yml"
        assert profiles_path.exists(), "profiles.yml not found"

        with open(profiles_path, "r") as f:
            profiles = yaml.safe_load(f)

        assert "biological_memory" in profiles, "biological_memory profile not found"
        assert "outputs" in profiles["biological_memory"], "No outputs defined"
        assert "dev" in profiles["biological_memory"]["outputs"], "Dev output not found"

    def test_dbt_project_yml_valid(self):
        """Test that dbt_project.yml is valid and has required configs"""
        project_file = self.project_dir / "dbt_project.yml"
        assert project_file.exists(), "dbt_project.yml not found"

        with open(project_file, "r") as f:
            project_config = yaml.safe_load(f)

        # Check required fields
        assert project_config["name"] == "biological_memory", "Project name incorrect"
        assert project_config["profile"] == "biological_memory", "Profile name incorrect"
        assert "vars" in project_config, "Variables not defined"

        # Check biological parameters
        vars_config = project_config["vars"]
        required_vars = [
            "working_memory_capacity",
            "short_term_memory_duration",
            "long_term_memory_threshold",
            "hebbian_learning_rate",
            "synaptic_decay_rate",
            "homeostasis_target",
        ]

        for var in required_vars:
            assert var in vars_config, f"Required variable {var} not found"

    def test_dbt_debug_runs(self):
        """Test that dbt debug command runs successfully"""
        try:
            result = subprocess.run(["dbt", "debug"], capture_output=True, text=True, timeout=60)

            assert result.returncode == 0, f"dbt debug failed: {result.stderr}"
            assert "All checks passed!" in result.stdout, "dbt debug checks failed"

        except subprocess.TimeoutExpired:
            pytest.fail("dbt debug command timed out")
        except FileNotFoundError:
            pytest.fail("dbt command not found - is dbt installed?")

    def test_macros_directory_exists(self):
        """Test that macros directory and files exist"""
        macros_dir = self.project_dir / "macros"
        assert macros_dir.exists(), "Macros directory not found"

        expected_macro_files = ["biological_memory_macros.sql", "utility_macros.sql"]

        for macro_file in expected_macro_files:
            macro_path = macros_dir / macro_file
            assert macro_path.exists(), f"Macro file {macro_file} not found"

    def test_models_directory_structure(self):
        """Test that model directory structure is correct"""
        models_dir = self.project_dir / "models"
        assert models_dir.exists(), "Models directory not found"

        expected_subdirs = [
            "working_memory",
            "short_term_memory",
            "long_term_memory",
            "semantic",
            "analytics",
        ]

        for subdir in expected_subdirs:
            subdir_path = models_dir / subdir
            assert subdir_path.exists(), f"Model subdirectory {subdir} not found"

    def test_dbt_parse_succeeds(self):
        """Test that dbt can parse the project without errors"""
        try:
            result = subprocess.run(["dbt", "parse"], capture_output=True, text=True, timeout=120)

            assert result.returncode == 0, f"dbt parse failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            pytest.fail("dbt parse command timed out")

    def test_biological_parameters_valid(self):
        """Test that biological parameters are within valid ranges"""
        project_file = self.project_dir / "dbt_project.yml"
        with open(project_file, "r") as f:
            project_config = yaml.safe_load(f)

        vars_config = project_config["vars"]

        # Test parameter ranges
        assert (
            5 <= vars_config["working_memory_capacity"] <= 9
        ), "Working memory capacity out of biological range"
        assert (
            vars_config["short_term_memory_duration"] > 0
        ), "Short-term memory duration must be positive"
        assert 0 < vars_config["long_term_memory_threshold"] <= 1, "LTM threshold must be 0-1"
        assert 0 < vars_config["hebbian_learning_rate"] <= 1, "Hebbian learning rate must be 0-1"
        assert 0 < vars_config["synaptic_decay_rate"] <= 1, "Synaptic decay rate must be 0-1"
        assert 0 < vars_config["homeostasis_target"] <= 1, "Homeostasis target must be 0-1"

    def test_packages_yml_exists(self):
        """Test that packages.yml exists for dependencies"""
        packages_file = self.project_dir / "packages.yml"
        assert packages_file.exists(), "packages.yml not found"

        with open(packages_file, "r") as f:
            packages = yaml.safe_load(f)

        assert "packages" in packages, "No packages defined"

        # Check for dbt-utils dependency
        package_names = [pkg.get("package", "") for pkg in packages["packages"]]
        assert any("dbt_utils" in name for name in package_names), "dbt-utils dependency not found"


class TestDbtMacros:
    """Test custom dbt macros functionality"""

    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        cls.project_dir = Path("/Users/ladvien/biological_memory")
        os.chdir(cls.project_dir)

    def test_macro_compilation(self):
        """Test that all macros can be compiled"""
        macros_dir = self.project_dir / "macros"

        for macro_file in macros_dir.glob("*.sql"):
            # Read and check macro syntax
            with open(macro_file, "r") as f:
                content = f.read()

            # Basic Jinja syntax validation
            assert "{%" in content or "{{" in content, f"No Jinja syntax found in {macro_file}"
            assert content.count("{%") == content.count(
                "%}"
            ), f"Unmatched Jinja blocks in {macro_file}"
            assert content.count("{{") == content.count(
                "}}"
            ), f"Unmatched Jinja expressions in {macro_file}"

    def test_hebbian_macro_parameters(self):
        """Test Hebbian learning macro parameter validation"""
        macro_file = self.project_dir / "macros" / "biological_memory_macros.sql"

        with open(macro_file, "r") as f:
            content = f.read()

        # Check that required Hebbian macros exist
        required_macros = [
            "calculate_hebbian_strength",
            "synaptic_homeostasis",
            "strengthen_associations",
        ]

        for macro in required_macros:
            assert f"macro {macro}" in content, f"Macro {macro} not found"


class TestDbtModels:
    """Test dbt model configurations and structure"""

    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        cls.project_dir = Path("/Users/ladvien/biological_memory")
        os.chdir(cls.project_dir)

    def test_model_materialization_config(self):
        """Test that models have appropriate materialization strategies"""
        models_dir = self.project_dir / "models"

        # Working memory should be views (fast access)
        working_memory_models = (models_dir / "working_memory").glob("*.sql")
        for model_file in working_memory_models:
            with open(model_file, "r") as f:
                content = f.read()
            assert (
                "materialized='view'" in content
            ), f"Working memory model {model_file.name} should be view"

        # Long-term memory should be tables (optimized storage)
        ltm_models = (models_dir / "long_term_memory").glob("*.sql")
        for model_file in ltm_models:
            with open(model_file, "r") as f:
                content = f.read()
            assert "materialized='table'" in content, f"LTM model {model_file.name} should be table"

    def test_model_dependencies(self):
        """Test that model dependencies are correctly defined"""
        models_dir = self.project_dir / "models"

        for model_file in models_dir.rglob("*.sql"):
            with open(model_file, "r") as f:
                content = f.read()

            # Check for proper ref() usage instead of direct table references
            if "FROM " in content or "JOIN " in content:
                # Should use ref() for model dependencies
                if "biological_memory" in content:
                    assert (
                        "ref(" in content or "source(" in content
                    ), f"Model {model_file.name} missing ref/source"


def run_dbt_tests():
    """Run the complete dbt test suite"""
    print("Running dbt configuration tests...")

    # Run pytest with detailed output
    exit_code = pytest.main([__file__, "-v", "--tb=short", "--disable-warnings"])

    return exit_code == 0


if __name__ == "__main__":
    success = run_dbt_tests()
    if success:
        print("✅ All dbt configuration tests passed!")
        exit(0)
    else:
        print("❌ Some dbt configuration tests failed!")
        exit(1)
