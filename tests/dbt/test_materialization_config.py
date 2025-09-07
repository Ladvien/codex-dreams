#!/usr/bin/env python3
"""
Materialization Configuration Conflict Test
Tests to verify no conflicts between dbt_project.yml and model-level materialization configs.

Agent: Agent-DBT-009
Story: STORY-DBT-009 - Materialization Configuration Conflicts Resolution
"""

import re
from pathlib import Path

import yaml


def get_project_root():
    """Get the project root directory."""
    current_dir = Path(__file__).parent
    # Navigate up to find biological_memory directory
    while current_dir.parent != current_dir:
        if (current_dir / "biological_memory" / "dbt_project.yml").exists():
            return current_dir / "biological_memory"
        current_dir = current_dir.parent
    raise FileNotFoundError("Could not find dbt_project.yml in biological_memory directory")


def load_dbt_project_config():
    """Load dbt_project.yml configuration."""
    project_root = get_project_root()
    config_path = project_root / "dbt_project.yml"

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def find_model_files():
    """Find all SQL model files with materialization configs."""
    project_root = get_project_root()
    models_dir = project_root / "models"

    model_files = []
    for sql_file in models_dir.rglob("*.sql"):
        with open(sql_file, "r") as f:
            content = f.read()
            if "materialized=" in content:
                model_files.append(sql_file)

    return model_files


def extract_model_materialization(file_path):
    """Extract materialization setting from a model file."""
    with open(file_path, "r") as f:
        content = f.read()

    # Look for materialized= in config blocks
    pattern = r"materialized\s*=\s*['\"]([^'\"]+)['\"]"
    match = re.search(pattern, content)

    if match:
        return match.group(1)

    return None


def get_project_materialization(config, directory_name):
    """Get project-level materialization for a directory."""
    models_config = config.get("models", {}).get("biological_memory", {})

    directory_config = models_config.get(directory_name, {})
    materialization = directory_config.get("+materialized")

    return materialization


class TestMaterializationConfigs:
    """Test suite for materialization configuration consistency."""

    def test_project_config_loads(self):
        """Test that dbt_project.yml loads successfully."""
        config = load_dbt_project_config()
        assert config is not None
        assert "models" in config
        assert "biological_memory" in config["models"]

    def test_working_memory_consistency(self):
        """Test working memory materialization consistency."""
        config = load_dbt_project_config()
        project_materialization = get_project_materialization(config, "working_memory")

        # Check working memory models
        project_root = get_project_root()
        wm_models = list((project_root / "models" / "working_memory").glob("*.sql"))

        for model_file in wm_models:
            model_materialization = extract_model_materialization(model_file)
            if model_materialization:
                assert model_materialization == project_materialization, (
                    f"Materialization conflict in {model_file.name}: "
                    f"model uses '{model_materialization}' but project config uses '{project_materialization}'"
                )

    def test_semantic_materialization_consistency(self):
        """Test semantic models materialization consistency."""
        config = load_dbt_project_config()
        project_materialization = get_project_materialization(config, "semantic")

        # Check semantic models
        project_root = get_project_root()
        semantic_models = list((project_root / "models" / "semantic").glob("*.sql"))

        for model_file in semantic_models:
            model_materialization = extract_model_materialization(model_file)
            if model_materialization:
                assert model_materialization == project_materialization, (
                    f"Materialization conflict in {model_file.name}: "
                    f"model uses '{model_materialization}' but project config uses '{project_materialization}'"
                )

    def test_short_term_memory_consistency(self):
        """Test short-term memory materialization consistency."""
        config = load_dbt_project_config()
        project_materialization = get_project_materialization(config, "short_term_memory")

        # Check short-term memory models
        project_root = get_project_root()
        stm_models = list((project_root / "models" / "short_term_memory").glob("*.sql"))

        for model_file in stm_models:
            model_materialization = extract_model_materialization(model_file)
            if model_materialization:
                assert model_materialization == project_materialization, (
                    f"Materialization conflict in {model_file.name}: "
                    f"model uses '{model_materialization}' but project config uses '{project_materialization}'"
                )

    def test_long_term_memory_consistency(self):
        """Test long-term memory materialization consistency."""
        config = load_dbt_project_config()
        project_materialization = get_project_materialization(config, "long_term_memory")

        # Check long-term memory models
        project_root = get_project_root()
        ltm_models = list((project_root / "models" / "long_term_memory").glob("*.sql"))

        for model_file in ltm_models:
            model_materialization = extract_model_materialization(model_file)
            if model_materialization:
                assert model_materialization == project_materialization, (
                    f"Materialization conflict in {model_file.name}: "
                    f"model uses '{model_materialization}' but project config uses '{project_materialization}'"
                )

    def test_consolidation_consistency(self):
        """Test consolidation models materialization consistency."""
        config = load_dbt_project_config()
        project_materialization = get_project_materialization(config, "consolidation")

        # Check consolidation models
        project_root = get_project_root()
        consolidation_models = list((project_root / "models" / "consolidation").glob("*.sql"))

        for model_file in consolidation_models:
            model_materialization = extract_model_materialization(model_file)
            if model_materialization:
                assert model_materialization == project_materialization, (
                    f"Materialization conflict in {model_file.name}: "
                    f"model uses '{model_materialization}' but project config uses '{project_materialization}'"
                )

    def test_analytics_consistency(self):
        """Test analytics models materialization consistency."""
        config = load_dbt_project_config()
        project_materialization = get_project_materialization(config, "analytics")

        # Check analytics models
        project_root = get_project_root()
        analytics_models = list((project_root / "models" / "analytics").glob("*.sql"))

        for model_file in analytics_models:
            model_materialization = extract_model_materialization(model_file)
            if model_materialization:
                assert model_materialization == project_materialization, (
                    f"Materialization conflict in {model_file.name}: "
                    f"model uses '{model_materialization}' but project config uses '{project_materialization}'"
                )

    def test_performance_consistency(self):
        """Test performance models materialization consistency."""
        config = load_dbt_project_config()
        project_materialization = get_project_materialization(config, "performance")

        # Check performance models
        project_root = get_project_root()
        performance_models = list((project_root / "models" / "performance").glob("*.sql"))

        for model_file in performance_models:
            model_materialization = extract_model_materialization(model_file)
            if model_materialization:
                assert model_materialization == project_materialization, (
                    f"Materialization conflict in {model_file.name}: "
                    f"model uses '{model_materialization}' but project config uses '{project_materialization}'"
                )

    def test_insights_consistency(self):
        """Test insights models materialization consistency."""
        config = load_dbt_project_config()
        project_materialization = get_project_materialization(config, "insights")

        # Check insights models
        project_root = get_project_root()
        insights_models = list((project_root / "models" / "insights").glob("*.sql"))

        for model_file in insights_models:
            model_materialization = extract_model_materialization(model_file)
            if model_materialization:
                assert model_materialization == project_materialization, (
                    f"Materialization conflict in {model_file.name}: "
                    f"model uses '{model_materialization}' but project config uses '{project_materialization}'"
                )

    def test_no_conflicting_overrides(self):
        """Test that there are no unexpected materialization overrides."""
        config = load_dbt_project_config()
        model_files = find_model_files()

        conflicts = []

        for model_file in model_files:
            # Get directory name from path
            relative_path = model_file.relative_to(get_project_root() / "models")
            directory_name = relative_path.parts[0]

            project_materialization = get_project_materialization(config, directory_name)
            model_materialization = extract_model_materialization(model_file)

            if model_materialization and project_materialization:
                if model_materialization != project_materialization:
                    conflicts.append(
                        f"{model_file.name}: model='{model_materialization}' vs project='{project_materialization}'"
                    )

        assert len(conflicts) == 0, f"Found materialization conflicts: {conflicts}"

    def test_materialization_strategy_documented(self):
        """Test that materialization strategy is documented in dbt_project.yml."""
        project_root = get_project_root()
        config_path = project_root / "dbt_project.yml"

        with open(config_path, "r") as f:
            content = f.read()

        # Check that materialization strategy is documented
        assert (
            "MATERIALIZATION STRATEGY:" in content
        ), "Materialization strategy should be documented"

        # Check that key stages are documented
        expected_stages = [
            "working_memory:",
            "short_term_memory:",
            "long_term_memory:",
            "semantic:",
            "analytics:",
            "insights:",
            "performance:",
            "consolidation:",
        ]

        for stage in expected_stages:
            assert (
                stage in content
            ), f"Stage '{stage}' should be documented in materialization strategy"


if __name__ == "__main__":
    # Run basic tests
    test_instance = TestMaterializationConfigs()

    print("Running materialization configuration conflict tests...")

    try:
        test_instance.test_project_config_loads()
        print("✓ Project config loads successfully")

        test_instance.test_working_memory_consistency()
        print("✓ Working memory materialization consistent")

        test_instance.test_semantic_materialization_consistency()
        print("✓ Semantic materialization consistent")

        test_instance.test_no_conflicting_overrides()
        print("✓ No conflicting materialization overrides found")

        test_instance.test_materialization_strategy_documented()
        print("✓ Materialization strategy documented")

        print("\n✅ All materialization configuration tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
