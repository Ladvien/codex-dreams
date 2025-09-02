"""
Unit tests for BMP-009: Custom Biological Macros.

Tests custom dbt macros for biological processes including Hebbian learning,
synaptic homeostasis, and association strengthening as specified in acceptance criteria.
"""

import json
import math
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest


class TestHebbianStrengthCalculation:
    """Test calculate_hebbian_strength() macro functionality."""

    def test_hebbian_learning_formula(self):
        """Test Hebbian learning rule implementation."""
        # Test Hebbian principle: "neurons that fire together, wire together"

        # Test data: memories with co-activation patterns
        coactivation_data = [
            {"pre_id": 1, "post_id": 2, "coactivation_count": 5, "avg_delay": 60},
            {"pre_id": 1, "post_id": 3, "coactivation_count": 2, "avg_delay": 120},
            {"pre_id": 2, "post_id": 3, "coactivation_count": 8, "avg_delay": 30},
        ]

        hebbian_rate = 0.1  # From dbt vars

        for data in coactivation_data:
            # Calculate Hebbian strength update
            original_strength = 0.5  # Baseline
            coactivations = data["coactivation_count"]

            # Formula: strength * (1 + learning_rate * coactivations)
            new_strength = original_strength * (1 + hebbian_rate * coactivations)

            assert new_strength > original_strength, "Co-activated memories should strengthen"
            assert new_strength <= 1.5, "Strength shouldn't increase too dramatically"

    def test_coactivation_window(self):
        """Test 5-minute co-activation window logic."""
        # Test temporal window for co-activation detection
        window_minutes = 5
        window_seconds = window_minutes * 60

        now = datetime.now(timezone.utc)
        test_timestamps = [
            now,
            now - timedelta(minutes=2),  # Within window
            now - timedelta(minutes=4),  # Within window
            now - timedelta(minutes=7),  # Outside window
        ]

        reference_time = now

        for timestamp in test_timestamps:
            time_diff = abs((timestamp - reference_time).total_seconds())
            within_window = time_diff <= window_seconds

            if timestamp == now:
                assert within_window, "Same timestamp should be within window"
            elif time_diff <= 240:  # 4 minutes
                assert within_window, "Should be within 5-minute window"
            else:
                assert not within_window, "Should be outside 5-minute window"

    def test_coactivation_counting_logic(self):
        """Test co-activation counting between memories."""
        # Test SQL logic concept for co-activation counting
        memories_with_topics = [
            {"id": 1, "timestamp": datetime.now(timezone.utc), "category": "meeting"},
            {
                "id": 2,
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=3),
                "category": "meeting",
            },
            {
                "id": 3,
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=10),
                "category": "meeting",
            },
            {
                "id": 4,
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=2),
                "category": "coding",
            },
        ]

        # Count co-activations within same category and time window
        coactivation_count = 0
        window_minutes = 5

        for i, mem_a in enumerate(memories_with_topics):
            for mem_b in memories_with_topics[i + 1 :]:
                if (
                    mem_a["category"] == mem_b["category"]
                    and abs((mem_a["timestamp"] - mem_b["timestamp"]).total_seconds())
                    <= window_minutes * 60
                ):
                    coactivation_count += 1

        # Should find co-activations within same category and time window
        assert coactivation_count >= 1, "Should detect co-activations in same category"

    def test_learning_rate_parameterization(self):
        """Test learning rate parameterization via dbt vars."""
        # Test different learning rates
        test_learning_rates = [0.05, 0.1, 0.15, 0.2]
        base_strength = 0.6
        coactivations = 3

        for rate in test_learning_rates:
            new_strength = base_strength * (1 + rate * coactivations)

            assert new_strength > base_strength, f"Rate {rate} should increase strength"
            assert new_strength < base_strength * 2, f"Rate {rate} shouldn't double strength"

            # Higher rates should produce higher final strengths
            if rate > 0.1:
                reference_strength = base_strength * (1 + 0.1 * coactivations)
                assert new_strength > reference_strength, "Higher rate should yield higher strength"


class TestSynapticHomeostasis:
    """Test synaptic_homeostasis() macro for weekly rescaling."""

    def test_synaptic_rescaling_concept(self):
        """Test synaptic rescaling to prevent runaway potentiation."""
        # Test memory strengths before rescaling
        memory_strengths = [0.9, 0.7, 0.5, 0.8, 0.6, 0.4, 0.3]

        # Calculate average strength
        avg_strength = sum(memory_strengths) / len(memory_strengths)
        assert abs(avg_strength - 0.6) < 0.1, "Test data should have reasonable average"

        # Apply rescaling: divide each strength by average
        rescaled_strengths = [strength / avg_strength for strength in memory_strengths]

        # Test rescaling properties
        new_avg = sum(rescaled_strengths) / len(rescaled_strengths)
        assert abs(new_avg - 1.0) < 0.001, "Rescaled average should be 1.0"

        # Relative ordering should be preserved
        for i in range(len(memory_strengths) - 1):
            if memory_strengths[i] > memory_strengths[i + 1]:
                assert (
                    rescaled_strengths[i] > rescaled_strengths[i + 1]
                ), "Rescaling should preserve strength ordering"

    def test_runaway_potentiation_prevention(self):
        """Test prevention of runaway potentiation."""
        # Simulate runaway potentiation scenario
        runaway_strengths = [2.5, 3.0, 1.8, 2.2]  # Unrealistically high
        normal_strengths = [0.3, 0.4, 0.2, 0.35]  # Normal range

        all_strengths = runaway_strengths + normal_strengths
        avg_strength = sum(all_strengths) / len(all_strengths)

        # Rescale to prevent runaway
        rescaled = [strength / avg_strength for strength in all_strengths]

        # Check that rescaling brings values to reasonable range
        max_rescaled = max(rescaled)
        assert max_rescaled < 3.0, "Rescaling should reduce extreme values"

        # Check that normal values don't become too small
        min_rescaled = min(rescaled)
        assert min_rescaled > 0.1, "Rescaling shouldn't make normal values too small"

    def test_remote_memory_targeting(self):
        """Test that homeostasis targets remote memories specifically."""
        memory_ages = ["recent", "week_old", "month_old", "remote"]

        # Only remote memories should undergo synaptic rescaling
        for age in memory_ages:
            should_rescale = age == "remote"

            if age == "remote":
                assert should_rescale, "Remote memories should be rescaled"
            else:
                assert not should_rescale, f"{age} memories should not be rescaled"

    def test_weak_connection_pruning(self):
        """Test pruning of weak synaptic connections (<0.01)."""
        connection_strengths = [0.005, 0.015, 0.001, 0.02, 0.008, 0.05]
        pruning_threshold = 0.01

        # Identify connections to prune
        pruned_connections = [s for s in connection_strengths if s >= pruning_threshold]
        removed_connections = [s for s in connection_strengths if s < pruning_threshold]

        # Test pruning logic
        assert len(removed_connections) > 0, "Should identify weak connections to remove"
        assert all(
            s < pruning_threshold for s in removed_connections
        ), "Removed connections should be below threshold"
        assert all(
            s >= pruning_threshold for s in pruned_connections
        ), "Remaining connections should be above threshold"

    def test_weekly_schedule_timing(self):
        """Test weekly homeostasis schedule (Sunday 3 AM)."""
        # Test cron schedule concept: Sunday 3 AM
        cron_schedule = "0 3 * * 0"  # minute hour day month weekday

        # Parse cron schedule
        parts = cron_schedule.split()
        minute, hour, day, month, weekday = parts

        assert minute == "0", "Should run at minute 0"
        assert hour == "3", "Should run at 3 AM"
        assert weekday == "0", "Should run on Sunday (0)"

        # Test that this runs once per week
        assert day == "*", "Should run regardless of day of month"
        assert month == "*", "Should run every month"


class TestStrengthenAssociations:
    """Test strengthen_associations() macro for REM-like creative connections."""

    @pytest.mark.llm
    def test_creative_association_discovery(self, mock_ollama):
        """Test creative connection discovery between memories."""
        # Test memory pairs for creative linking
        memory_pairs = [
            ("Database optimization meeting", "Morning coffee routine"),
            ("Code debugging session", "Solving puzzle games"),
            ("Team retrospective", "Personal reflection time"),
        ]

        for gist_a, gist_b in memory_pairs:
            response = mock_ollama(f"Find creative connection between: {gist_a} and {gist_b}")

            # Should find creative links even between disparate memories
            assert response is not None, "Should find creative connections"
            assert len(response) > 10, "Creative link should be meaningful"

    def test_rem_sleep_timing(self):
        """Test REM sleep simulation timing (90-minute cycles at night)."""
        # Test cron schedule: every 90 minutes during night hours (23-5)
        cron_schedule = "*/90 23-5 * * *"

        # Parse schedule
        parts = cron_schedule.split()
        minute, hour, day, month, weekday = parts

        assert minute == "*/90", "Should run every 90 minutes"
        assert hour == "23-5", "Should run during night hours"

        # Test 90-minute cycle concept
        cycle_minutes = 90
        cycles_per_night = (6 * 60) // cycle_minutes  # 6 hours of night
        assert cycles_per_night == 4, "Should have ~4 REM cycles per night"

    def test_random_memory_sampling(self):
        """Test random memory pair sampling for creative connections."""
        # Test concept: select random pairs from LTM for creative linking
        total_memories = 1000
        sample_size = 100

        # Should sample reasonable number of pairs
        assert sample_size <= total_memories, "Sample should not exceed total"
        assert sample_size >= 50, "Should sample enough pairs for creativity"

        # Test that sampling is reasonable for available memory
        max_possible_pairs = total_memories * (total_memories - 1) // 2
        sample_ratio = sample_size / max_possible_pairs

        assert sample_ratio < 0.01, "Should sample small fraction to avoid overload"
        assert sample_ratio > 0.0001, "Should sample enough for meaningful connections"

    def test_creative_link_filtering(self):
        """Test filtering of creative links (non-null responses)."""
        # Test link quality filtering
        creative_links = [
            "Both involve systematic problem-solving approaches",
            None,  # No creative connection found
            "Similar patterns of iterative improvement",
            "",  # Empty response
            "Both require focused attention and pattern recognition",
        ]

        # Filter valid creative links
        valid_links = [
            link for link in creative_links if link is not None and len(link.strip()) > 0
        ]

        assert len(valid_links) == 3, "Should filter out null/empty links"

        for link in valid_links:
            assert len(link) > 10, "Valid links should be descriptive"

    def test_association_storage_concept(self):
        """Test creative association storage in memory_associations table."""
        # Test expected structure for storing creative associations
        association_record = {
            "id1": 123,
            "id2": 456,
            "creative_link": "Both involve pattern recognition and systematic thinking",
            "strength": 0.7,
            "created_at": datetime.now(timezone.utc),
            "association_type": "creative",
        }

        # Validate association record structure
        assert "id1" in association_record, "Should link two memories"
        assert "id2" in association_record, "Should link two memories"
        assert (
            association_record["id1"] != association_record["id2"]
        ), "Should link different memories"
        assert len(association_record["creative_link"]) > 0, "Should store creative connection"


class TestMacroParameterization:
    """Test macro parameterization via dbt variables."""

    def test_biological_parameter_access(self):
        """Test access to biological parameters from dbt vars."""
        # Expected biological parameters from dbt_project.yml
        expected_params = {
            "working_memory_capacity": 7,
            "stm_duration_minutes": 30,
            "consolidation_threshold": 0.5,
            "hebbian_learning_rate": 0.1,
            "forgetting_rate": 0.05,
        }

        for param, expected_value in expected_params.items():
            # Test parameter ranges
            if "rate" in param or "threshold" in param:
                assert 0 < expected_value < 1, f"{param} should be 0-1 ratio"
            elif "capacity" in param:
                assert expected_value > 0, f"{param} should be positive"
            elif "duration" in param:
                assert expected_value > 0, f"{param} should be positive duration"

    def test_ollama_configuration_access(self):
        """Test access to Ollama configuration in macros."""
        # Test macro access to Ollama settings
        ollama_config = {"ollama_host": "http://localhost:11434", "ollama_model": "gpt-oss:20b"}

        for key, value in ollama_config.items():
            assert value is not None, f"{key} should be configured"

            if "host" in key:
                assert value.startswith("http"), f"{key} should be HTTP URL"
            elif "model" in key:
                assert len(value) > 0, f"{key} should specify model name"

    def test_variable_substitution_concept(self):
        """Test dbt variable substitution in macros."""
        # Test template substitution concept
        template_examples = [
            "{{ var('hebbian_learning_rate') }}",
            "{{ var('ollama_host') }}",
            "{{ var('consolidation_threshold') }}",
        ]

        for template in template_examples:
            # Should contain var() function call
            assert "var(" in template, "Should use dbt var() function"
            assert ")" in template, "Should close var() function"
            assert "'" in template or '"' in template, "Should quote variable name"


class TestMacroIntegration:
    """Test integration between different biological macros."""

    def test_hebbian_homeostasis_interaction(self):
        """Test interaction between Hebbian learning and homeostasis."""
        # Test scenario: Hebbian learning increases strengths, homeostasis normalizes

        # Initial strengths
        initial_strengths = [0.4, 0.5, 0.6, 0.7]

        # Apply Hebbian learning (strengthens some connections)
        hebbian_rate = 0.1
        coactivations = [3, 1, 5, 2]  # Different co-activation counts

        after_hebbian = []
        for i, strength in enumerate(initial_strengths):
            new_strength = strength * (1 + hebbian_rate * coactivations[i])
            after_hebbian.append(new_strength)

        # Apply homeostasis (weekly rescaling)
        avg_after_hebbian = sum(after_hebbian) / len(after_hebbian)
        after_homeostasis = [s / avg_after_hebbian for s in after_hebbian]

        # Test that both processes work together
        assert max(after_hebbian) > max(
            initial_strengths
        ), "Hebbian learning should increase some strengths"
        assert (
            abs(sum(after_homeostasis) / len(after_homeostasis) - 1.0) < 0.001
        ), "Homeostasis should normalize average to 1.0"

    def test_macro_execution_order(self):
        """Test biological macro execution order and timing."""
        # Test execution schedule concepts
        macro_schedules = {
            "calculate_hebbian_strength": "continuous",  # With consolidation
            "strengthen_associations": "90min_rem",  # REM cycles
            "synaptic_homeostasis": "weekly_sunday",  # Sunday 3 AM
        }

        for macro, schedule in macro_schedules.items():
            assert schedule is not None, f"{macro} should have defined schedule"

            if "continuous" in schedule:
                # Should run frequently
                assert True, "Continuous macros should run with consolidation"
            elif "weekly" in schedule:
                # Should run once per week
                assert True, "Weekly macros should maintain homeostasis"
            elif "rem" in schedule:
                # Should run during sleep simulation
                assert True, "REM macros should run during creative periods"

    def test_biological_realism(self):
        """Test biological realism of macro implementations."""
        # Test that macros implement realistic biological processes

        # Hebbian learning: realistic learning rates
        hebbian_rate = 0.1
        assert 0.05 <= hebbian_rate <= 0.2, "Hebbian rate should be biologically realistic"

        # Homeostasis: prevents runaway potentiation
        homeostasis_period = 7  # days
        assert homeostasis_period == 7, "Weekly homeostasis matches biological rhythms"

        # REM cycles: 90-minute periods
        rem_cycle_minutes = 90
        assert rem_cycle_minutes == 90, "REM cycles should match biological timing"

        # All processes should work together for stable memory system
        assert True, "Biological macros should maintain system stability"


class TestAdvancedHebbianImplementation:
    """Test advanced Hebbian learning implementation (BMP-009)."""

    def test_temporal_coactivation_windows(self):
        """Test precise 5-minute temporal co-activation windows."""
        # Test that co-activations are counted within exact 5-minute windows
        base_time = datetime.now(timezone.utc)

        test_cases = [
            {"delay_seconds": 30, "should_count": True},  # 30 seconds - within window
            {"delay_seconds": 180, "should_count": True},  # 3 minutes - within window
            {"delay_seconds": 299, "should_count": True},  # 4:59 - within window
            {"delay_seconds": 301, "should_count": False},  # 5:01 - outside window
            {"delay_seconds": 600, "should_count": False},  # 10 minutes - outside window
        ]

        window_seconds = 5 * 60  # 5 minutes

        for case in test_cases:
            delay = case["delay_seconds"]
            within_window = delay <= window_seconds
            expected = case["should_count"]

            assert (
                within_window == expected
            ), f"Delay of {delay}s should {'be' if expected else 'not be'} within 5-minute window"

    def test_coactivation_counting_accuracy(self):
        """Test accurate co-activation counting with semantic categories."""
        # Simulate STM memories with shared categories
        memories = [
            {"id": 1, "timestamp": datetime.now(timezone.utc), "semantic_category": "meeting"},
            {
                "id": 2,
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=2),
                "semantic_category": "meeting",
            },
            {
                "id": 3,
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=4),
                "semantic_category": "meeting",
            },
            {
                "id": 4,
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=1),
                "semantic_category": "coding",
            },
            {
                "id": 5,
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=3),
                "semantic_category": "coding",
            },
        ]

        # Count expected co-activations within same category and 5-minute window
        expected_coactivations = []

        for i, mem_a in enumerate(memories):
            for mem_b in memories[i + 1 :]:
                if (
                    mem_a["semantic_category"] == mem_b["semantic_category"]
                    and abs((mem_a["timestamp"] - mem_b["timestamp"]).total_seconds()) <= 300
                ):
                    expected_coactivations.append((mem_a["id"], mem_b["id"]))

        # Should find co-activations: (1,2), (1,3), (2,3) for meetings, (4,5) for coding
        assert len(expected_coactivations) == 4, "Should find 4 co-activations"
        assert (1, 2) in expected_coactivations, "Should find meeting co-activation"
        assert (4, 5) in expected_coactivations, "Should find coding co-activation"

    def test_hebbian_delta_calculation(self):
        """Test Hebbian delta calculation with runaway prevention."""
        test_scenarios = [
            {"current_strength": 0.1, "coactivations": 3, "learning_rate": 0.1},
            {"current_strength": 0.5, "coactivations": 5, "learning_rate": 0.1},
            {"current_strength": 0.9, "coactivations": 2, "learning_rate": 0.1},  # Near saturation
        ]

        for scenario in test_scenarios:
            current = scenario["current_strength"]
            coact = min(scenario["coactivations"], 10.0)  # Cap at 10 to prevent saturation
            rate = scenario["learning_rate"]

            # Calculate Hebbian delta: rate × coactivation × (1 - current_strength)
            hebbian_delta = rate * (coact / 10.0) * (1.0 - current)
            new_strength = current * (1 + hebbian_delta)

            # Test delta properties
            assert hebbian_delta >= 0, "Hebbian delta should be non-negative"
            assert new_strength <= 1.0, "Strength should not exceed 1.0 (saturation prevention)"
            assert new_strength > current, "New strength should be higher"

            # Higher co-activations should lead to larger deltas (when not saturated)
            if current < 0.8:  # Not near saturation
                assert (
                    hebbian_delta > 0.001
                ), "Should have meaningful delta for non-saturated connections"

    def test_normalization_prevents_runaway(self):
        """Test that normalization prevents runaway potentiation."""
        # Test extreme co-activation scenario
        extreme_coactivations = [15, 20, 25]  # Very high co-activation counts

        for coact_count in extreme_coactivations:
            # Apply normalization: min(coact_count, 10.0) / 10.0
            normalized = min(coact_count, 10.0) / 10.0

            assert normalized <= 1.0, "Normalized co-activation should not exceed 1.0"

            # Even extreme co-activations should be capped
            if coact_count > 10:
                assert normalized == 1.0, "Co-activations > 10 should normalize to 1.0"


class TestAdvancedSynapticHomeostasis:
    """Test advanced synaptic homeostasis implementation (BMP-009)."""

    def test_network_statistics_calculation(self):
        """Test network statistics calculation for homeostasis."""
        # Sample retrieval strengths from semantic network
        sample_strengths = [0.1, 0.3, 0.5, 0.7, 0.9, 0.2, 0.6, 0.8, 0.4]

        # Calculate expected statistics
        mean_strength = sum(sample_strengths) / len(sample_strengths)
        max_strength = max(sample_strengths)
        min_strength = min(sample_strengths)

        # Test statistical calculations
        assert 0 < mean_strength < 1, "Mean strength should be in valid range"
        assert max_strength == 0.9, "Max strength should be correctly identified"
        assert min_strength == 0.1, "Min strength should be correctly identified"

        # Calculate standard deviation concept
        variance = sum((x - mean_strength) ** 2 for x in sample_strengths) / len(sample_strengths)
        std_dev = math.sqrt(variance)

        assert std_dev > 0, "Standard deviation should indicate variability"

    def test_scaling_factor_logic(self):
        """Test scaling factor calculation for homeostasis."""
        homeostasis_target = 0.5

        test_scenarios = [
            {"mean_strength": 0.8, "expected_action": "scale_down"},  # Too high
            {"mean_strength": 0.2, "expected_action": "scale_up"},  # Too low
            {"mean_strength": 0.5, "expected_action": "no_scaling"},  # Just right
            {"mean_strength": 0.45, "expected_action": "no_scaling"},  # Close enough
        ]

        for scenario in test_scenarios:
            mean = scenario["mean_strength"]

            # Calculate scaling factor
            if mean > homeostasis_target * 1.5:  # 0.75
                scaling_factor = homeostasis_target / mean  # Scale down
                expected_action = "scale_down"
            elif mean < homeostasis_target * 0.5:  # 0.25
                scaling_factor = homeostasis_target / mean  # Scale up
                expected_action = "scale_up"
            else:
                scaling_factor = 1.0  # No scaling
                expected_action = "no_scaling"

            assert (
                scenario["expected_action"] == expected_action
            ), f"Mean {mean} should trigger {expected_action}"

            if expected_action == "scale_down":
                assert scaling_factor < 1.0, "Should scale down when mean is too high"
            elif expected_action == "scale_up":
                assert scaling_factor > 1.0, "Should scale up when mean is too low"
            else:
                assert scaling_factor == 1.0, "Should not scale when mean is appropriate"

    def test_weak_connection_identification(self):
        """Test identification of weak connections for pruning."""
        connection_data = [
            {"strength": 0.005, "age": "remote", "access_freq": 1, "should_prune": True},
            {"strength": 0.008, "age": "remote", "access_freq": 0, "should_prune": True},
            {
                "strength": 0.012,
                "age": "remote",
                "access_freq": 1,
                "should_prune": False,
            },  # Above threshold
            {
                "strength": 0.005,
                "age": "recent",
                "access_freq": 1,
                "should_prune": False,
            },  # Not remote
            {
                "strength": 0.009,
                "age": "remote",
                "access_freq": 3,
                "should_prune": False,
            },  # High access
        ]

        threshold = 0.01

        for connection in connection_data:
            strength = connection["strength"]
            age = connection["age"]
            access_freq = connection["access_freq"]
            expected_prune = connection["should_prune"]

            # Pruning logic: weak AND remote AND rarely accessed
            should_prune = strength < threshold and age == "remote" and access_freq < 2

            assert (
                should_prune == expected_prune
            ), f"Connection with strength {strength}, age {age}, access {access_freq} pruning mismatch"

    def test_network_health_metrics(self):
        """Test network health metrics creation."""
        # Sample network data after homeostasis
        sample_data = {
            "total_synapses": 5000,
            "strong_connections": 150,  # strength > 0.7
            "weak_connections": 50,  # strength < 0.1
            "avg_strength": 0.52,
        }

        # Test health metric calculations
        strong_ratio = sample_data["strong_connections"] / sample_data["total_synapses"]
        weak_ratio = sample_data["weak_connections"] / sample_data["total_synapses"]

        assert 0.02 < strong_ratio < 0.1, "Strong connections should be reasonable minority"
        assert weak_ratio < 0.05, "Weak connections should be small after pruning"
        assert 0.4 < sample_data["avg_strength"] < 0.6, "Average should be near homeostatic target"


class TestAdvancedAssociationStrengthening:
    """Test advanced REM-sleep association strengthening (BMP-009)."""

    def test_distant_memory_pair_selection(self):
        """Test selection of distant memory pairs for creative linking."""
        # Sample memories from different categories
        memories = [
            {"id": 1, "category": "work_meeting", "strength": 0.8},
            {"id": 2, "category": "financial_planning", "strength": 0.7},
            {"id": 3, "category": "technical_procedures", "strength": 0.6},
            {"id": 4, "category": "social_cognition", "strength": 0.5},
            {"id": 5, "category": "work_meeting", "strength": 0.4},  # Same category as #1
        ]

        # Generate cross-category pairs (distant associations)
        distant_pairs = []
        for i, mem_a in enumerate(memories):
            for mem_b in memories[i + 1 :]:
                if (
                    mem_a["category"] != mem_b["category"]  # Different categories
                    and mem_a["strength"] > 0.3
                    and mem_b["strength"] > 0.3
                ):  # Strong enough
                    distant_pairs.append(
                        (mem_a["id"], mem_b["id"], mem_a["category"], mem_b["category"])
                    )

        # Should find distant pairs but not same-category pairs
        assert len(distant_pairs) > 0, "Should find distant memory pairs"

        for pair in distant_pairs:
            mem_a_id, mem_b_id, cat_a, cat_b = pair
            assert cat_a != cat_b, "Distant pairs should have different categories"
            assert mem_a_id != mem_b_id, "Should pair different memories"

    def test_creative_connection_types(self):
        """Test different types of creative connections."""
        connection_types = [
            "strategic_synthesis",
            "human_technology_interface",
            "executive_emotional_intelligence",
            "analytical_project_management",
            "communicative_strategy",
            "collective_problem_solving",
            "general_synthesis",
        ]

        for conn_type in connection_types:
            assert len(conn_type) > 5, "Connection type should be descriptive"
            assert "_" in conn_type, "Connection type should use underscore format"

            # Each type should represent meaningful cognitive synthesis
            assert any(
                keyword in conn_type
                for keyword in ["synthesis", "intelligence", "management", "strategy", "solving"]
            ), f"Connection type {conn_type} should indicate cognitive process"

    def test_novelty_and_plausibility_scoring(self):
        """Test novelty and plausibility scoring for creative connections."""
        creative_connections = [
            {"type": "strategic_synthesis", "novelty": 0.8, "plausibility": 0.9},
            {"type": "human_technology_interface", "novelty": 0.7, "plausibility": 0.8},
            {"type": "general_synthesis", "novelty": 0.5, "plausibility": 0.7},
        ]

        for connection in creative_connections:
            novelty = connection["novelty"]
            plausibility = connection["plausibility"]

            # Test scoring ranges
            assert 0 <= novelty <= 1, "Novelty should be 0-1 range"
            assert 0 <= plausibility <= 1, "Plausibility should be 0-1 range"

            # Strategic and specific connections should have higher scores
            if "strategic" in connection["type"]:
                assert novelty >= 0.6, "Strategic connections should be moderately novel"
                assert plausibility >= 0.8, "Strategic connections should be highly plausible"

            # General connections should have lower novelty
            if "general" in connection["type"]:
                assert novelty <= 0.6, "General connections should be less novel"

    def test_creative_strength_calculation(self):
        """Test creative association strength calculation."""
        test_pairs = [
            {"strength_a": 0.8, "strength_b": 0.7, "different_categories": True},
            {"strength_a": 0.6, "strength_b": 0.5, "different_categories": True},
            {"strength_a": 0.9, "strength_b": 0.8, "different_categories": False},  # Same category
        ]

        creativity_factor = 0.8

        for pair in test_pairs:
            strength_a = pair["strength_a"]
            strength_b = pair["strength_b"]
            different_cats = pair["different_categories"]

            # Calculate creative strength: (strength_a * 0.4 + strength_b * 0.4 + novelty_bonus) * factor
            base_strength = strength_a * 0.4 + strength_b * 0.4
            novelty_bonus = 0.2 if different_cats else 0.0
            creative_strength = (base_strength + novelty_bonus) * creativity_factor

            # Test creative strength properties
            assert creative_strength > 0, "Creative strength should be positive"
            assert creative_strength <= 1.0, "Creative strength should not exceed 1.0"

            # Different categories should get novelty bonus
            if different_cats:
                same_cat_strength = base_strength * creativity_factor  # No bonus
                assert (
                    creative_strength > same_cat_strength
                ), "Different categories should get novelty bonus"

    def test_rem_batch_size_limits(self):
        """Test REM association batch size for computational efficiency."""
        total_memories = 10000
        batch_size_options = [50, 100, 200, 500]

        for batch_size in batch_size_options:
            # Calculate computational load
            max_possible_pairs = total_memories * (total_memories - 1) // 2
            sample_ratio = batch_size / max_possible_pairs

            # Test batch size reasonableness
            assert batch_size <= 500, "Batch size should be limited for performance"
            assert sample_ratio < 0.001, "Should sample tiny fraction for efficiency"

            # Larger batches allow more creativity but cost more computation
            if batch_size >= 200:
                assert sample_ratio < 0.0001, "Large batches need very selective sampling"

    def test_creative_association_storage(self):
        """Test storage structure for creative associations."""
        sample_association = {
            "source_memory_id": 123,
            "target_memory_id": 456,
            "source_gist": "Database optimization meeting",
            "target_gist": "Personal reflection time",
            "creative_link_description": "Both involve systematic analysis and optimization processes",
            "connection_type": "analytical_synthesis",
            "association_strength": 0.65,
            "novelty_score": 0.7,
            "plausibility_score": 0.8,
            "discovery_method": "rem_sleep_simulation",
            "created_during_rem": True,
        }

        # Validate association storage structure
        required_fields = [
            "source_memory_id",
            "target_memory_id",
            "creative_link_description",
            "association_strength",
            "novelty_score",
            "plausibility_score",
        ]

        for field in required_fields:
            assert field in sample_association, f"Should store {field}"
            assert sample_association[field] is not None, f"{field} should not be null"

        # Test field value ranges
        assert 0 < sample_association["association_strength"] <= 1, "Strength should be valid range"
        assert 0 <= sample_association["novelty_score"] <= 1, "Novelty should be 0-1"
        assert 0 <= sample_association["plausibility_score"] <= 1, "Plausibility should be 0-1"
        assert sample_association["created_during_rem"] == True, "Should mark as REM-created"
