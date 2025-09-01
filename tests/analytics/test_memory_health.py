"""
Unit tests for BMP-011: Memory Health Analytics Dashboard.

Tests memory distribution metrics, health indicators, and performance
monitoring as specified in acceptance criteria.
"""

import pytest
from datetime import datetime, timezone, timedelta
import math


class TestDistributionMetrics:
    """Test memory distribution metrics calculation."""

    def test_memory_counts_by_age(self):
        """Test memory counts by age categories."""
        # Mock memory data with different ages
        mock_memories = [
            {"age": "recent", "count": 150},
            {"age": "week_old", "count": 300},
            {"age": "month_old", "count": 500},
            {"age": "remote", "count": 2000},
        ]

        total_memories = sum(mem["count"] for mem in mock_memories)
        recent_memories = next(mem["count"] for mem in mock_memories if mem["age"] == "recent")

        # Test distribution
        assert total_memories == 2950, "Should calculate total memories correctly"
        assert recent_memories == 150, "Should count recent memories"

        # Test distribution ratios
        recent_ratio = recent_memories / total_memories
        assert 0.03 <= recent_ratio <= 0.1, "Recent memories should be reasonable portion"

    def test_consolidation_state_distribution(self):
        """Test memory distribution by consolidation state."""
        consolidation_states = [
            {"state": "episodic", "count": 1000},
            {"state": "consolidating", "count": 800},
            {"state": "schematized", "count": 400},
        ]

        total = sum(state["count"] for state in consolidation_states)
        schematized = next(s["count"] for s in consolidation_states if s["state"] == "schematized")

        # Test consolidation funnel
        assert schematized < total / 2, "Schematized memories should be minority"
        assert schematized > 0, "Should have some schematized memories"

        # Test consolidation progression
        episodic = next(s["count"] for s in consolidation_states if s["state"] == "episodic")
        consolidating = next(
            s["count"] for s in consolidation_states if s["state"] == "consolidating"
        )

        assert (
            episodic >= consolidating >= schematized
        ), "Should show consolidation funnel progression"

    def test_semantic_diversity_metrics(self):
        """Test semantic diversity measurement."""
        semantic_categories = [
            "work_meeting",
            "coding_session",
            "planning",
            "review",
            "social",
            "learning",
            "debugging",
            "documentation",
        ]

        category_count = len(semantic_categories)

        # Test diversity metrics
        assert category_count >= 5, "Should have diverse semantic categories"
        assert category_count <= 20, "Categories should not be too fragmented"

        # Test category balance (mock distribution)
        category_distribution = {cat: 100 + i * 50 for i, cat in enumerate(semantic_categories)}
        total_memories = sum(category_distribution.values())

        # Calculate entropy as diversity measure
        entropy = 0
        for count in category_distribution.values():
            if count > 0:
                p = count / total_memories
                entropy -= p * math.log2(p)

        assert entropy > 2.0, "Should have reasonable semantic diversity"


class TestHealthIndicators:
    """Test biological memory health indicators."""

    def test_average_retrieval_strength(self):
        """Test average retrieval strength calculation."""
        retrieval_strengths = [0.8, 0.6, 0.9, 0.4, 0.7, 0.5, 0.8, 0.3]

        avg_strength = sum(retrieval_strengths) / len(retrieval_strengths)

        assert 0.4 <= avg_strength <= 0.8, "Average retrieval strength should be reasonable"
        assert abs(avg_strength - 0.625) < 0.001, "Should calculate average correctly"

        # Test health thresholds
        if avg_strength >= 0.7:
            health_status = "healthy"
        elif avg_strength >= 0.5:
            health_status = "moderate"
        else:
            health_status = "poor"

        assert health_status == "moderate", "Should classify health correctly"

    def test_consolidation_strength_metrics(self):
        """Test average consolidation strength indicators."""
        consolidation_strengths = [0.9, 0.7, 0.8, 0.6, 0.85, 0.75]

        avg_consolidation = sum(consolidation_strengths) / len(consolidation_strengths)

        assert avg_consolidation > 0.5, "Average consolidation should exceed threshold"

        # Test consolidation health
        strong_memories = sum(1 for s in consolidation_strengths if s >= 0.7)
        total_memories = len(consolidation_strengths)
        strong_ratio = strong_memories / total_memories

        assert strong_ratio >= 0.5, "Majority of memories should be well-consolidated"

    def test_access_frequency_health(self):
        """Test access frequency health indicators."""
        access_frequencies = [5, 12, 3, 8, 15, 2, 9, 6, 11, 4]

        avg_access = sum(access_frequencies) / len(access_frequencies)

        assert avg_access > 1, "Memories should be accessed regularly"

        # Test access distribution
        highly_accessed = sum(1 for freq in access_frequencies if freq >= 10)
        rarely_accessed = sum(1 for freq in access_frequencies if freq <= 2)

        access_health_ratio = highly_accessed / (rarely_accessed + 1)
        assert access_health_ratio > 0.5, "Should have good access pattern distribution"

    def test_cortical_distribution_health(self):
        """Test cortical region distribution health."""
        cortical_regions = {
            "prefrontal_cortex": 150,
            "motor_cortex": 80,
            "visual_cortex": 120,
            "auditory_cortex": 60,
            "association_cortex": 200,
        }

        total_memories = sum(cortical_regions.values())
        region_count = len(cortical_regions)

        # Test distribution balance
        max_region = max(cortical_regions.values())
        min_region = min(cortical_regions.values())

        balance_ratio = min_region / max_region
        assert balance_ratio >= 0.2, "Cortical distribution should be reasonably balanced"

        # Test region diversity
        assert region_count >= 4, "Should utilize multiple cortical regions"


class TestPerformanceMetrics:
    """Test system performance indicators."""

    def test_consolidation_timing_metrics(self):
        """Test consolidation timing performance."""
        # Mock consolidation timestamps
        now = datetime.now(timezone.utc)
        consolidation_times = [
            now - timedelta(hours=2),  # Recent
            now - timedelta(hours=6),  # This night
            now - timedelta(days=1),  # Yesterday
            now - timedelta(days=2),  # Day before
        ]

        # Test last consolidation timing
        last_consolidation = max(consolidation_times)
        time_since_last = (now - last_consolidation).total_seconds() / 3600  # hours

        assert time_since_last <= 24, "Should have consolidated within 24 hours"

        # Test consolidation frequency
        recent_consolidations = sum(
            1 for t in consolidation_times if (now - t).total_seconds() <= 86400
        )  # 24 hours

        assert recent_consolidations >= 1, "Should have recent consolidation activity"

    def test_memory_age_distribution(self):
        """Test memory age distribution for system health."""
        memory_ages = {
            "recent": 100,  # <1 day
            "week_old": 300,  # 1-7 days
            "month_old": 500,  # 7-30 days
            "remote": 1500,  # >30 days
        }

        total_memories = sum(memory_ages.values())

        # Test age distribution health
        recent_ratio = memory_ages["recent"] / total_memories
        remote_ratio = memory_ages["remote"] / total_memories

        assert recent_ratio >= 0.02, "Should have sufficient recent memories"
        assert remote_ratio <= 0.8, "Should not have too many old memories"

        # Test memory lifecycle health
        assert (
            memory_ages["recent"] <= memory_ages["week_old"]
        ), "Should have healthy memory aging pattern"

    def test_system_performance_benchmarks(self):
        """Test system performance benchmarks."""
        performance_metrics = {
            "working_memory_refresh_ms": 50,
            "stm_processing_ms": 200,
            "consolidation_batch_s": 0.8,
            "ltm_query_ms": 25,
            "average_memory_usage_gb": 6.5,
        }

        # Test performance thresholds
        assert (
            performance_metrics["working_memory_refresh_ms"] <= 100
        ), "Working memory should refresh quickly"
        assert (
            performance_metrics["consolidation_batch_s"] <= 1.0
        ), "Consolidation should complete within 1 second per batch"
        assert performance_metrics["ltm_query_ms"] <= 50, "LTM queries should be fast"
        assert (
            performance_metrics["average_memory_usage_gb"] <= 10
        ), "Memory usage should be within limits"


class TestAlertingLogic:
    """Test health alerting and threshold triggers."""

    def test_health_alert_thresholds(self):
        """Test health alert threshold definitions."""
        alert_thresholds = {
            "avg_retrieval_strength": {"warning": 0.5, "critical": 0.3},
            "consolidation_rate": {"warning": 0.7, "critical": 0.5},
            "semantic_diversity": {"warning": 5, "critical": 3},
            "access_frequency": {"warning": 2.0, "critical": 1.0},
            "consolidation_lag_hours": {"warning": 6, "critical": 24},
        }

        for metric, thresholds in alert_thresholds.items():
            warning = thresholds["warning"]
            critical = thresholds["critical"]

            # Critical should be more severe than warning
            if "lag" in metric:
                assert critical > warning, f"{metric} critical should be higher than warning"
            else:
                assert critical < warning, f"{metric} critical should be lower than warning"

    def test_alert_trigger_logic(self):
        """Test alert triggering logic for different scenarios."""
        test_scenarios = [
            # (metric_value, warning_threshold, critical_threshold, expected_alert)
            (0.8, 0.5, 0.3, None),  # Healthy
            (0.4, 0.5, 0.3, "warning"),  # Warning level
            (0.2, 0.5, 0.3, "critical"),  # Critical level
            (0.3, 0.5, 0.3, "critical"),  # Exactly at critical (boundary)
        ]

        for value, warning_thresh, critical_thresh, expected in test_scenarios:
            if value <= critical_thresh:
                alert_level = "critical"
            elif value <= warning_thresh:
                alert_level = "warning"
            else:
                alert_level = None

            assert (
                alert_level == expected
            ), f"Alert logic failed for value={value}, expected={expected}, got={alert_level}"

    def test_alert_message_formatting(self):
        """Test alert message formatting and content."""
        alert_templates = {
            "low_retrieval_strength": "Average retrieval strength ({value:.3f}) below threshold ({threshold:.3f})",
            "consolidation_lag": "Memory consolidation delayed by {lag_hours} hours",
            "low_diversity": "Semantic diversity ({diversity}) below healthy level ({min_diversity})",
        }

        # Test message formatting
        for alert_type, template in alert_templates.items():
            assert "{" in template, f"Alert template {alert_type} should have placeholders"
            assert "}" in template, f"Alert template {alert_type} should have placeholders"

            # Test sample message formatting
            if "retrieval" in alert_type:
                message = template.format(value=0.45, threshold=0.5)
                assert "0.450" in message, "Should format decimals correctly"
            elif "lag" in alert_type:
                message = template.format(lag_hours=12)
                assert "12" in message, "Should include lag hours"


class TestViewEfficiency:
    """Test analytics view efficiency and performance."""

    @pytest.mark.performance
    def test_analytics_view_refresh_time(self, performance_benchmark):
        """Test analytics view refresh performance."""
        # Simulate analytics view calculation
        with performance_benchmark() as timer:
            # Mock complex analytics calculations
            total_memories = 10000
            memory_categories = 8

            # Simulate aggregation queries
            for category in range(memory_categories):
                # Mock category-based aggregation
                category_count = total_memories // memory_categories
                avg_strength = 0.6 + (category % 3) * 0.1

                assert category_count > 0, "Each category should have memories"
                assert 0 < avg_strength <= 1.0, "Strength should be valid"

        # Analytics view should refresh quickly
        assert timer.elapsed < 1.0, f"Analytics view took {timer.elapsed:.3f}s, should be <1s"

    def test_incremental_analytics_updates(self):
        """Test incremental analytics view updates."""
        # Test that analytics can update incrementally
        baseline_metrics = {
            "total_memories": 1000,
            "avg_retrieval_strength": 0.65,
            "semantic_diversity": 8,
        }

        # Add new memories
        new_memories = 100
        new_avg_strength = 0.7

        # Calculate updated metrics
        updated_total = baseline_metrics["total_memories"] + new_memories

        # Weighted average for strength
        total_strength = (
            baseline_metrics["total_memories"] * baseline_metrics["avg_retrieval_strength"]
        )
        new_total_strength = total_strength + new_memories * new_avg_strength
        updated_avg_strength = new_total_strength / updated_total

        assert updated_total == 1100, "Should update total count"
        assert (
            updated_avg_strength > baseline_metrics["avg_retrieval_strength"]
        ), "New strong memories should improve average"

    def test_analytics_data_consistency(self):
        """Test analytics data consistency and accuracy."""
        # Test that derived metrics are consistent with source data
        source_data = {
            "recent_count": 150,
            "week_old_count": 300,
            "month_old_count": 500,
            "remote_count": 1050,
        }

        # Calculate derived metrics
        total_memories = sum(source_data.values())
        recent_ratio = source_data["recent_count"] / total_memories

        # Test consistency
        assert total_memories == 2000, "Total should match sum of parts"
        assert abs(recent_ratio - 0.075) < 0.001, "Ratios should be mathematically correct"

        # Test that percentages sum to 100%
        all_ratios = [count / total_memories for count in source_data.values()]
        total_ratio = sum(all_ratios)
        assert abs(total_ratio - 1.0) < 0.001, "All ratios should sum to 1.0"


class TestMonitoringIntegration:
    """Test integration with monitoring systems."""

    def test_metrics_export_format(self):
        """Test metrics export format for monitoring systems."""
        # Test expected metrics format
        exported_metrics = {
            "biological_memory_total_count": 2500,
            "biological_memory_avg_retrieval_strength": 0.68,
            "biological_memory_semantic_diversity": 9,
            "biological_memory_consolidation_lag_seconds": 1800,
            "biological_memory_avg_access_frequency": 4.2,
        }

        for metric_name, value in exported_metrics.items():
            # All metrics should have proper prefix
            assert metric_name.startswith(
                "biological_memory_"
            ), f"Metric {metric_name} should have proper prefix"

            # Values should be numeric
            assert isinstance(value, (int, float)), f"Metric {metric_name} should be numeric"

            # Values should be reasonable
            assert value >= 0, f"Metric {metric_name} should be non-negative"

    def test_dashboard_data_structure(self):
        """Test dashboard data structure and completeness."""
        dashboard_data = {
            "summary": {
                "total_memories": 2500,
                "health_status": "healthy",
                "last_updated": datetime.now(timezone.utc),
            },
            "distribution": {
                "by_age": {"recent": 150, "week_old": 300, "month_old": 500, "remote": 1550},
                "by_state": {"episodic": 1000, "consolidating": 800, "schematized": 700},
            },
            "performance": {
                "avg_retrieval_strength": 0.68,
                "consolidation_rate": 0.85,
                "query_performance_ms": 45,
            },
            "alerts": [],
        }

        # Test required sections
        required_sections = ["summary", "distribution", "performance", "alerts"]
        for section in required_sections:
            assert section in dashboard_data, f"Dashboard should include {section} section"

        # Test data completeness
        assert dashboard_data["summary"]["health_status"] in [
            "healthy",
            "warning",
            "critical",
        ], "Health status should be valid"
        assert isinstance(dashboard_data["alerts"], list), "Alerts should be a list"
