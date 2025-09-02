#!/usr/bin/env python3
"""
Schema Documentation Test Suite
Tests to verify that schema.yml files exist and are valid for all model directories
Part of STORY-DBT-011: Missing Schema Documentation & Model Validation
"""

import os
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml


class TestSchemaDocumentation:
    """Test suite for dbt schema documentation validation."""

    @classmethod
    def setup_class(cls):
        """Set up test class with project paths."""
        cls.project_root = Path("/Users/ladvien/codex-dreams")
        cls.models_dir = cls.project_root / "biological_memory" / "models"
        cls.required_directories = [
            "working_memory",
            "short_term_memory",
            "consolidation",
            "long_term_memory",
        ]

    def test_schema_files_exist(self):
        """Test that schema.yml files exist in all required directories."""
        missing_schemas = []

        for directory in self.required_directories:
            schema_path = self.models_dir / directory / "schema.yml"
            if not schema_path.exists():
                missing_schemas.append(f"{directory}/schema.yml")

        assert not missing_schemas, f"Missing schema files: {missing_schemas}"

    def test_schema_files_are_valid_yaml(self):
        """Test that all schema.yml files contain valid YAML."""
        invalid_schemas = []

        for directory in self.required_directories:
            schema_path = self.models_dir / directory / "schema.yml"
            if schema_path.exists():
                try:
                    with open(schema_path, "r") as f:
                        yaml.safe_load(f)
                except yaml.YAMLError as e:
                    invalid_schemas.append(f"{directory}/schema.yml: {str(e)}")

        assert not invalid_schemas, f"Invalid YAML in schema files: {invalid_schemas}"

    def test_schema_files_have_required_structure(self):
        """Test that schema.yml files have the required dbt structure."""
        structural_errors = []

        for directory in self.required_directories:
            schema_path = self.models_dir / directory / "schema.yml"
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    schema_content = yaml.safe_load(f)

                # Check required top-level keys
                if not isinstance(schema_content, dict):
                    structural_errors.append(f"{directory}/schema.yml: Root must be a dictionary")
                    continue

                if "version" not in schema_content:
                    structural_errors.append(f"{directory}/schema.yml: Missing 'version' key")

                if "models" not in schema_content:
                    structural_errors.append(f"{directory}/schema.yml: Missing 'models' key")
                    continue

                if not isinstance(schema_content["models"], list):
                    structural_errors.append(f"{directory}/schema.yml: 'models' must be a list")

        assert not structural_errors, f"Structural errors in schema files: {structural_errors}"

    def test_models_have_required_fields(self):
        """Test that all models have required name and description fields."""
        model_errors = []

        for directory in self.required_directories:
            schema_path = self.models_dir / directory / "schema.yml"
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    schema_content = yaml.safe_load(f)

                if "models" in schema_content and isinstance(schema_content["models"], list):
                    for i, model in enumerate(schema_content["models"]):
                        if not isinstance(model, dict):
                            model_errors.append(
                                f"{directory}/schema.yml: Model {i} must be a dictionary"
                            )
                            continue

                        if "name" not in model:
                            model_errors.append(
                                f"{directory}/schema.yml: Model {i} missing 'name' field"
                            )

                        if "description" not in model:
                            model_errors.append(
                                f"{directory}/schema.yml: Model {model.get('name', i)} missing 'description' field"
                            )

        assert not model_errors, f"Model field errors: {model_errors}"

    def test_columns_have_required_fields(self):
        """Test that all columns have required name and description fields."""
        column_errors = []

        for directory in self.required_directories:
            schema_path = self.models_dir / directory / "schema.yml"
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    schema_content = yaml.safe_load(f)

                if "models" in schema_content and isinstance(schema_content["models"], list):
                    for model in schema_content["models"]:
                        model_name = model.get("name", "unknown")

                        if "columns" in model and isinstance(model["columns"], list):
                            for i, column in enumerate(model["columns"]):
                                if not isinstance(column, dict):
                                    column_errors.append(
                                        f"{directory}/{model_name}: Column {i} must be a dictionary"
                                    )
                                    continue

                                if "name" not in column:
                                    column_errors.append(
                                        f"{directory}/{model_name}: Column {i} missing 'name' field"
                                    )

                                if "description" not in column:
                                    column_errors.append(
                                        f"{directory}/{model_name}: Column {column.get('name', i)} missing 'description' field"
                                    )

        assert not column_errors, f"Column field errors: {column_errors}"

    def test_basic_tests_exist(self):
        """Test that basic tests (not_null, unique) exist for key columns."""
        test_coverage_issues = []

        for directory in self.required_directories:
            schema_path = self.models_dir / directory / "schema.yml"
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    schema_content = yaml.safe_load(f)

                if "models" in schema_content:
                    for model in schema_content["models"]:
                        model_name = model.get("name", "unknown")

                        if "columns" in model:
                            # Check for ID columns that should have not_null
                            # and unique tests
                            for column in model["columns"]:
                                column_name = column.get("name", "")
                                tests = column.get("tests", [])

                                # ID columns should have not_null and unique
                                # tests
                                if column_name in ["id", "memory_id"]:
                                    has_not_null = any("not_null" in str(test) for test in tests)
                                    has_unique = any("unique" in str(test) for test in tests)

                                    if not has_not_null:
                                        test_coverage_issues.append(
                                            f"{directory}/{model_name}: Column {column_name} missing not_null test"
                                        )

                                    if not has_unique:
                                        test_coverage_issues.append(
                                            f"{directory}/{model_name}: Column {column_name} missing unique test"
                                        )

        assert not test_coverage_issues, f"Test coverage issues: {test_coverage_issues}"

    def test_strength_columns_have_range_tests(self):
        """Test that strength/score columns have appropriate range tests."""
        range_test_issues = []
        strength_columns = [
            "activation_strength",
            "stm_strength",
            "consolidated_strength",
            "hebbian_strength",
            "recency_score",
            "frequency_score",
            "emotional_salience",
            "consolidation_priority",
            "stability_score",
            "importance_score",
            "decay_resistance",
        ]

        for directory in self.required_directories:
            schema_path = self.models_dir / directory / "schema.yml"
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    schema_content = yaml.safe_load(f)

                if "models" in schema_content:
                    for model in schema_content["models"]:
                        model_name = model.get("name", "unknown")

                        if "columns" in model:
                            for column in model["columns"]:
                                column_name = column.get("name", "")
                                tests = column.get("tests", [])

                                # Strength columns should have range validation
                                if column_name in strength_columns:
                                    has_range_test = any(
                                        "accepted_range" in str(test)
                                        or "dbt_utils.accepted_range" in str(test)
                                        for test in tests
                                    )

                                    if not has_range_test:
                                        range_test_issues.append(
                                            f"{directory}/{model_name}: Column {column_name} missing range test"
                                        )

        assert not range_test_issues, f"Range test issues: {range_test_issues}"

    def test_schema_coverage_completeness(self):
        """Test that all SQL model files have corresponding schema documentation."""
        coverage_issues = []

        for directory in self.required_directories:
            dir_path = self.models_dir / directory
            schema_path = dir_path / "schema.yml"

            if dir_path.exists():
                # Get all SQL files in directory
                sql_files = list(dir_path.glob("*.sql"))
                model_names = [f.stem for f in sql_files]

                if schema_path.exists():
                    with open(schema_path, "r") as f:
                        schema_content = yaml.safe_load(f)

                    if "models" in schema_content:
                        documented_models = [m.get("name") for m in schema_content["models"]]

                        # Check for undocumented models
                        for model_name in model_names:
                            if model_name not in documented_models:
                                coverage_issues.append(
                                    f"{directory}: Model {model_name}.sql not documented in schema.yml"
                                )

        assert not coverage_issues, f"Schema coverage issues: {coverage_issues}"


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
