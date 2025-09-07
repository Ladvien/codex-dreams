"""
Test dbt project configuration compliance with STORY-002 requirements.

This module validates that the dbt_project.yml configuration meets all
acceptance criteria for STORY-002: Fix dbt Project Configuration for Biological Processing
"""

from pathlib import Path

import pytest
import yaml


class TestDBTConfiguration:
    """Test suite for dbt project configuration validation."""

    @classmethod
    def setup_class(cls):
        """Load dbt_project.yml for testing."""
        cls.project_path = Path("/Users/ladvien/codex-dreams/biological_memory/dbt_project.yml")

        if not cls.project_path.exists():
            pytest.skip("dbt_project.yml not found")

        with open(cls.project_path, "r") as f:
            cls.config = yaml.safe_load(f)

    def test_project_basic_structure(self):
        """Test basic dbt project structure is valid."""
        assert self.config["name"] == "biological_memory"
        assert self.config["version"] == "1.0.0"
        assert self.config["config-version"] == 2
        assert self.config["profile"] == "biological_memory"

    def test_biological_orchestration_tags(self):
        """Test that all required biological orchestration tags are present."""

        models = self.config.get("models", {}).get("biological_memory", {})

        # Check working memory has continuous tag
        wm_tags = models.get("working_memory", {}).get("+tags", [])
        assert "continuous" in wm_tags, "Working memory missing 'continuous' tag"

        # Check short-term memory has short_term tag
        stm_tags = models.get("short_term_memory", {}).get("+tags", [])
        assert "short_term" in stm_tags, "Short-term memory missing 'short_term' tag"

        # Check consolidation has consolidation tag
        cons_tags = models.get("consolidation", {}).get("+tags", [])
        assert "consolidation" in cons_tags, "Consolidation missing 'consolidation' tag"

        # Check long-term memory has long_term tag
        ltm_tags = models.get("long_term_memory", {}).get("+tags", [])
        assert "long_term" in ltm_tags, "Long-term memory missing 'long_term' tag"

    def test_ollama_variables(self):
        """Test Ollama configuration variables are correctly set."""
        vars_config = self.config.get("vars", {})

        # Test ollama_url uses environment variable (no hardcoded defaults for security)
        ollama_url = vars_config.get("ollama_url", "")
        assert "OLLAMA_URL" in ollama_url, "ollama_url should use environment variable"
        # Security: No hardcoded IP addresses should be present
        assert "192.168" not in ollama_url, "ollama_url should not contain hardcoded IP addresses"

        # Test ollama_model has correct default
        ollama_model = vars_config.get("ollama_model", "")
        assert (
            "OLLAMA_MODEL" in ollama_model or ollama_model == "llama2"
        ), "ollama_model should be 'llama2' or use env var"

        # Test ollama_temperature is 0.7
        assert vars_config.get("ollama_temperature") == 0.7, "ollama_temperature should be 0.7"

    def test_biological_timing_parameters(self):
        """Test biological timing parameters are correctly configured."""
        vars_config = self.config.get("vars", {})

        # Test working memory duration is 5 minutes (300 seconds)
        assert (
            vars_config.get("working_memory_duration") == 300
        ), "working_memory_duration should be 300 seconds (5 minutes)"

        # Test working memory capacity parameters
        assert (
            vars_config.get("working_memory_capacity_base") == 7
        ), "working_memory_capacity_base should be 7"
        assert (
            vars_config.get("working_memory_capacity_variance") == 2
        ), "working_memory_capacity_variance should be 2"

        # Test short-term memory duration is 30 minutes (1800 seconds)
        assert (
            vars_config.get("short_term_memory_duration") == 1800
        ), "short_term_memory_duration should be 1800 seconds (30 minutes)"

    def test_model_materializations(self):
        """Test model materializations match ARCHITECTURE.md specifications."""
        models = self.config.get("models", {}).get("biological_memory", {})

        # Working memory should be view (real-time updates)
        wm_mat = models.get("working_memory", {}).get("+materialized")
        assert wm_mat == "view", "Working memory should be materialized as view"

        # Short-term memory should be incremental
        stm_mat = models.get("short_term_memory", {}).get("+materialized")
        assert stm_mat == "incremental", "Short-term memory should be materialized as incremental"

        # Consolidation should be incremental
        cons_mat = models.get("consolidation", {}).get("+materialized")
        assert cons_mat == "incremental", "Consolidation should be materialized as incremental"

        # Long-term memory should be table
        ltm_mat = models.get("long_term_memory", {}).get("+materialized")
        assert ltm_mat == "table", "Long-term memory should be materialized as table"

    def test_incremental_strategy_configuration(self):
        """Test incremental models have proper strategy configuration."""
        models = self.config.get("models", {}).get("biological_memory", {})

        # Check short-term memory incremental config
        stm_config = models.get("short_term_memory", {})
        assert (
            stm_config.get("+unique_key") == "memory_id"
        ), "STM should have memory_id as unique_key"
        assert stm_config.get("+incremental_strategy") == "merge", "STM should use merge strategy"

        # Check consolidation incremental config
        cons_config = models.get("consolidation", {})
        assert (
            cons_config.get("+unique_key") == "memory_id"
        ), "Consolidation should have memory_id as unique_key"
        assert (
            cons_config.get("+incremental_strategy") == "merge"
        ), "Consolidation should use merge strategy"

    def test_biological_parameter_ranges(self):
        """Test biological parameters are within scientifically valid ranges."""
        vars_config = self.config.get("vars", {})

        # Miller's 7±2 rule validation
        capacity = vars_config.get("working_memory_capacity", 0)
        assert 5 <= capacity <= 9, f"Working memory capacity {capacity} violates Miller's 7±2 rule"

        # Hebbian learning rate should be reasonable (0.01-0.5)
        hebbian_rate = vars_config.get("hebbian_learning_rate", 0)
        assert (
            0.01 <= hebbian_rate <= 0.5
        ), f"Hebbian learning rate {hebbian_rate} outside biological range"

        # Consolidation threshold should be reasonable (0.3-0.8)
        cons_threshold = vars_config.get("consolidation_threshold", 0)
        assert (
            0.3 <= cons_threshold <= 0.8
        ), f"Consolidation threshold {cons_threshold} outside biological range"

    def test_performance_hooks_configuration(self):
        """Test performance optimization hooks are properly configured."""
        models = self.config.get("models", {}).get("biological_memory", {})

        # Check working memory has performance optimizations
        wm_config = models.get("working_memory", {})
        pre_hooks = wm_config.get("+pre-hook", [])
        assert any(
            "threads" in hook for hook in pre_hooks
        ), "Working memory should have thread optimization"

        # Check consolidation has memory optimization
        cons_config = models.get("consolidation", {})
        cons_pre_hooks = cons_config.get("+pre-hook", [])
        assert any(
            "memory_limit" in hook for hook in cons_pre_hooks
        ), "Consolidation should have memory limit"

    def test_on_run_hooks(self):
        """Test on-run hooks are configured for biological orchestration."""
        on_run_start = self.config.get("on-run-start", [])
        on_run_end = self.config.get("on-run-end", [])

        assert len(on_run_start) > 0, "Should have on-run-start hooks"
        assert len(on_run_end) > 0, "Should have on-run-end hooks"

        # Check for biological pipeline logging
        start_hooks_str = " ".join(on_run_start)
        assert (
            "biological memory" in start_hooks_str.lower()
        ), "Start hooks should mention biological memory"


class TestBiologicalParameters:
    """Test biological parameter accuracy and compliance."""

    @classmethod
    def setup_class(cls):
        """Load configuration for biological parameter testing."""
        project_path = Path("/Users/ladvien/codex-dreams/biological_memory/dbt_project.yml")
        with open(project_path, "r") as f:
            cls.config = yaml.safe_load(f)
        cls.vars = cls.config.get("vars", {})

    def test_millers_law_compliance(self):
        """Test Miller's 7±2 working memory capacity law compliance."""
        base_capacity = self.vars.get("working_memory_capacity_base", 0)
        variance = self.vars.get("working_memory_capacity_variance", 0)

        # Base should be 7 (Miller's magic number)
        assert base_capacity == 7, f"Base capacity should be 7, got {base_capacity}"

        # Variance should allow 5-9 range (7±2)
        min_capacity = base_capacity - variance
        max_capacity = base_capacity + variance
        assert min_capacity == 5, f"Min capacity should be 5, got {min_capacity}"
        assert max_capacity == 9, f"Max capacity should be 9, got {max_capacity}"

    def test_temporal_window_accuracy(self):
        """Test temporal window durations match cognitive science research."""
        # Working memory: 5 minutes (short-term attention span)
        wm_duration = self.vars.get("working_memory_duration", 0)
        assert wm_duration == 300, f"WM duration should be 300s (5 min), got {wm_duration}"

        # Short-term memory: 30 minutes (consolidation window)
        stm_duration = self.vars.get("short_term_memory_duration", 0)
        assert stm_duration == 1800, f"STM duration should be 1800s (30 min), got {stm_duration}"

    def test_hebbian_learning_parameters(self):
        """Test Hebbian learning parameters are biologically realistic."""
        learning_rate = self.vars.get("hebbian_learning_rate", 0)
        decay_rate = self.vars.get("synaptic_decay_rate", 0)

        # Learning rate should be in biological range (Hebb 1949, Kandel 1992)
        assert (
            0.05 <= learning_rate <= 0.2
        ), f"Learning rate {learning_rate} outside biological range"

        # Decay rate should be small (synaptic maintenance)
        assert 0 < decay_rate <= 0.01, f"Decay rate {decay_rate} outside biological range"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
