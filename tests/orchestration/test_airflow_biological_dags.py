"""
Unit tests for Apache Airflow Biological Rhythm DAGs (STORY-011).

Tests the Airflow DAG implementations for biologically-accurate memory consolidation:
- Continuous processing (every 5 minutes during wake hours)
- Short-term consolidation (every 20 minutes)
- Long-term consolidation (every 90 minutes, ultradian cycles)
- Deep sleep consolidation (nightly 2-4 AM)
- REM sleep simulation (night cycles)
- Synaptic homeostasis (weekly Sunday 3 AM)

Research validation against:
- McGaugh (2000): Memory consolidation timing
- Dudai (2004): Neurobiology of consolidations
- Diekelmann & Born (2010): Sleep-dependent memory consolidation
- Tononi & Cirelli (2006): Synaptic homeostasis
"""

import sys
from datetime import timedelta
from pathlib import Path

import pytest

# Add project root to path for DAG imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from airflow.models import DagBag

    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False

# Skip all tests if Airflow not available
pytestmark = pytest.mark.skipif(not AIRFLOW_AVAILABLE, reason="Apache Airflow not installed")


@pytest.fixture
def dag_bag():
    """Load DAGs for testing."""
    dag_bag = DagBag(dag_folder=str(Path(__file__).parent.parent.parent / "dags"))
    return dag_bag


class TestDAGStructure:
    """Test DAG structure and configuration."""

    def test_dags_loaded_successfully(self, dag_bag):
        """Test that all biological rhythm DAGs load without errors."""
        assert len(dag_bag.import_errors) == 0, f"DAG import errors: {dag_bag.import_errors}"

        expected_dags = [
            "continuous_memory_processing",
            "short_term_memory_consolidation",
            "long_term_memory_consolidation",
            "deep_sleep_memory_consolidation",
            "rem_sleep_creative_associations",
            "synaptic_homeostasis_maintenance",
            "biological_rhythm_coordination",
        ]

        for dag_id in expected_dags:
            assert dag_id in dag_bag.dags, f"DAG {dag_id} should be loaded"

    def test_continuous_processing_dag_config(self, dag_bag):
        """Test continuous processing DAG configuration."""
        dag = dag_bag.get_dag("continuous_memory_processing")

        # Test schedule: every 5 minutes, 6 AM to 10 PM
        assert (
            dag.schedule_interval == "*/5 6-22 * * *"
        ), "Should run every 5 minutes during wake hours"
        assert dag.max_active_runs == 1, "Should have max 1 active run"

        # Test biological tags
        expected_tags = ["biological", "continuous", "working_memory", "miller_law"]
        for tag in expected_tags:
            assert tag in dag.tags, f"Should have {tag} tag"

    def test_short_term_consolidation_dag_config(self, dag_bag):
        """Test short-term consolidation DAG configuration."""
        dag = dag_bag.get_dag("short_term_memory_consolidation")

        # Test schedule: every 20 minutes
        assert dag.schedule_interval == "*/20 * * * *", "Should run every 20 minutes"
        assert dag.max_active_runs == 1, "Should have max 1 active run"

        # Test biological accuracy tags
        expected_tags = ["biological", "short_term", "episodic", "consolidation"]
        for tag in expected_tags:
            assert tag in dag.tags, f"Should have {tag} tag"

    def test_long_term_consolidation_dag_config(self, dag_bag):
        """Test long-term consolidation DAG configuration (ultradian cycles)."""
        dag = dag_bag.get_dag("long_term_memory_consolidation")

        # Test schedule: hourly (with 90-minute internal logic)
        assert dag.schedule_interval == "0 */1 * * *", "Should check hourly for 90-minute cycles"
        assert dag.max_active_runs == 1, "Should have max 1 active run"

        # Test ultradian tags
        expected_tags = ["biological", "long_term", "ultradian", "rem_cycles"]
        for tag in expected_tags:
            assert tag in dag.tags, f"Should have {tag} tag"

    def test_deep_sleep_dag_config(self, dag_bag):
        """Test deep sleep consolidation DAG configuration."""
        dag = dag_bag.get_dag("deep_sleep_memory_consolidation")

        # Test schedule: daily at 2 AM
        assert dag.schedule_interval == "0 2 * * *", "Should run daily at 2 AM"
        assert dag.max_active_runs == 1, "Should have max 1 active run"

        # Test sleep consolidation tags
        expected_tags = ["biological", "deep_sleep", "systems_consolidation", "nightly"]
        for tag in expected_tags:
            assert tag in dag.tags, f"Should have {tag} tag"

    def test_rem_sleep_dag_config(self, dag_bag):
        """Test REM sleep simulation DAG configuration."""
        dag = dag_bag.get_dag("rem_sleep_creative_associations")

        # Test schedule: every hour from 1 AM to 5 AM
        assert dag.schedule_interval == "0 1,2,3,4,5 * * *", "Should run during night REM hours"
        assert dag.max_active_runs == 1, "Should have max 1 active run"

        # Test creative association tags
        expected_tags = ["biological", "rem_sleep", "creative", "associations"]
        for tag in expected_tags:
            assert tag in dag.tags, f"Should have {tag} tag"

    def test_homeostasis_dag_config(self, dag_bag):
        """Test synaptic homeostasis DAG configuration."""
        dag = dag_bag.get_dag("synaptic_homeostasis_maintenance")

        # Test schedule: Sunday at 3 AM
        assert dag.schedule_interval == "0 3 * * 0", "Should run Sunday at 3 AM"
        assert dag.max_active_runs == 1, "Should have max 1 active run"

        # Test homeostasis tags
        expected_tags = ["biological", "homeostasis", "weekly", "maintenance"]
        for tag in expected_tags:
            assert tag in dag.tags, f"Should have {tag} tag"

    def test_coordination_dag_config(self, dag_bag):
        """Test biological rhythm coordination DAG configuration."""
        dag = dag_bag.get_dag("biological_rhythm_coordination")

        # Test schedule: every 10 minutes
        assert dag.schedule_interval == "*/10 * * * *", "Should run every 10 minutes for monitoring"
        assert dag.max_active_runs == 1, "Should have max 1 active run"

        # Test coordination tags
        expected_tags = ["biological", "coordination", "monitoring"]
        for tag in expected_tags:
            assert tag in dag.tags, f"Should have {tag} tag"


class TestDAGTasks:
    """Test individual DAG task configuration."""

    def test_continuous_processing_tasks(self, dag_bag):
        """Test continuous processing DAG tasks."""
        dag = dag_bag.get_dag("continuous_memory_processing")

        expected_tasks = [
            "validate_continuous_parameters",
            "log_circadian_phase",
            "run_working_memory_processing",
        ]

        for task_id in expected_tasks:
            assert task_id in dag.task_dict, f"Task {task_id} should exist"

        # Test task dependencies
        run_task = dag.get_task("run_working_memory_processing")
        upstream_task_ids = [task.task_id for task in run_task.upstream_list]
        assert "validate_continuous_parameters" in upstream_task_ids, "Should depend on validation"
        assert "log_circadian_phase" in upstream_task_ids, "Should depend on circadian logging"

    def test_short_term_consolidation_tasks(self, dag_bag):
        """Test short-term consolidation DAG tasks."""
        dag = dag_bag.get_dag("short_term_memory_consolidation")

        expected_tasks = [
            "validate_short_term_parameters",
            "run_short_term_consolidation",
        ]

        for task_id in expected_tasks:
            assert task_id in dag.task_dict, f"Task {task_id} should exist"

    def test_long_term_consolidation_tasks(self, dag_bag):
        """Test long-term consolidation DAG tasks."""
        dag = dag_bag.get_dag("long_term_memory_consolidation")

        expected_tasks = [
            "wait_for_ultradian_cycle",
            "validate_long_term_parameters",
            "run_long_term_consolidation",
        ]

        for task_id in expected_tasks:
            assert task_id in dag.task_dict, f"Task {task_id} should exist"

        # Test ultradian sensor
        sensor_task = dag.get_task("wait_for_ultradian_cycle")
        assert sensor_task is not None, "Ultradian cycle sensor should exist"

    def test_deep_sleep_tasks(self, dag_bag):
        """Test deep sleep consolidation DAG tasks."""
        dag = dag_bag.get_dag("deep_sleep_memory_consolidation")

        expected_tasks = [
            "validate_deep_sleep_parameters",
            "run_deep_sleep_consolidation",
            "run_semantic_network_optimization",
        ]

        for task_id in expected_tasks:
            assert task_id in dag.task_dict, f"Task {task_id} should exist"

        # Test parallel execution
        consolidation_task = dag.get_task("run_deep_sleep_consolidation")
        semantic_task = dag.get_task("run_semantic_network_optimization")

        # Both should have the same upstream (validation)
        consolidation_upstream = set(task.task_id for task in consolidation_task.upstream_list)
        semantic_upstream = set(task.task_id for task in semantic_task.upstream_list)
        assert (
            consolidation_upstream == semantic_upstream
        ), "Tasks should run in parallel after validation"

    def test_homeostasis_tasks(self, dag_bag):
        """Test synaptic homeostasis DAG tasks."""
        dag = dag_bag.get_dag("synaptic_homeostasis_maintenance")

        expected_tasks = [
            "validate_homeostasis_parameters",
            "run_memory_cleanup",
            "run_semantic_network_pruning",
        ]

        for task_id in expected_tasks:
            assert task_id in dag.task_dict, f"Task {task_id} should exist"


class TestBiologicalAccuracy:
    """Test biological accuracy of DAG timing and parameters."""

    def test_circadian_rhythm_compliance(self, dag_bag):
        """Test DAG schedules comply with circadian rhythms."""
        # Continuous processing should only run during wake hours (6 AM - 10 PM)
        continuous_dag = dag_bag.get_dag("continuous_memory_processing")
        schedule = continuous_dag.schedule_interval
        assert "6-22" in schedule, "Continuous processing should respect circadian wake hours"

        # Deep sleep should run at 2 AM (lowest body temperature)
        deep_sleep_dag = dag_bag.get_dag("deep_sleep_memory_consolidation")
        assert (
            deep_sleep_dag.schedule_interval == "0 2 * * *"
        ), "Deep sleep should align with biological timing"

        # Homeostasis should run Sunday 3 AM (minimal interference)
        homeostasis_dag = dag_bag.get_dag("synaptic_homeostasis_maintenance")
        assert (
            homeostasis_dag.schedule_interval == "0 3 * * 0"
        ), "Homeostasis should run during quiet period"

    def test_ultradian_rhythm_compliance(self, dag_bag):
        """Test compliance with 90-minute ultradian cycles."""
        # Long-term consolidation should check for 90-minute intervals
        long_term_dag = dag_bag.get_dag("long_term_memory_consolidation")

        # Should have ultradian sensor
        assert (
            "wait_for_ultradian_cycle" in long_term_dag.task_dict
        ), "Should have ultradian timing sensor"

        # REM cycles should align with night hours
        rem_dag = dag_bag.get_dag("rem_sleep_creative_associations")
        schedule = rem_dag.schedule_interval
        assert "1,2,3,4,5" in schedule, "REM cycles should run during night hours"

    def test_consolidation_timing_research_validation(self, dag_bag):
        """Validate consolidation timing against research papers."""
        # McGaugh (2000): Memory consolidation during sleep
        deep_sleep_dag = dag_bag.get_dag("deep_sleep_memory_consolidation")
        assert (
            "2" in deep_sleep_dag.schedule_interval
        ), "Should consolidate during deep sleep (McGaugh 2000)"

        # Diekelmann & Born (2010): Different sleep stages for different processes
        rem_dag = dag_bag.get_dag("rem_sleep_creative_associations")
        assert "associations" in rem_dag.dag_id, "REM should handle creative associations"

        # Short-term consolidation every 20 minutes aligns with episodic processing
        short_term_dag = dag_bag.get_dag("short_term_memory_consolidation")
        assert (
            "*/20" in short_term_dag.schedule_interval
        ), "Should consolidate episodes every 20 minutes"

    def test_working_memory_parameters(self, dag_bag):
        """Test working memory parameters align with Miller's Law."""
        continuous_dag = dag_bag.get_dag("continuous_memory_processing")

        # Should have Miller's Law tag
        assert "miller_law" in continuous_dag.tags, "Should reference Miller's Law"

        # Should run every 5 minutes for working memory refresh
        assert (
            "*/5" in continuous_dag.schedule_interval
        ), "Should refresh working memory every 5 minutes"


class TestDAGDefaultArgs:
    """Test DAG default arguments and error handling."""

    def test_default_arguments_consistency(self, dag_bag):
        """Test that all DAGs have consistent default arguments."""
        all_dags = dag_bag.dags.values()

        for dag in all_dags:
            # All should have cognitive-memory-researcher owner
            assert (
                dag.default_args.get("owner") == "cognitive-memory-researcher"
            ), f"DAG {dag.dag_id} should have correct owner"

            # All should not depend on past
            assert not dag.default_args.get(
                "depends_on_past"
            ), f"DAG {dag.dag_id} should not depend on past"

            # All should have retries configured
            assert dag.default_args.get("retries") == 2, f"DAG {dag.dag_id} should have 2 retries"

            # All should have retry delay
            retry_delay = dag.default_args.get("retry_delay")
            assert retry_delay == timedelta(
                minutes=5
            ), f"DAG {dag.dag_id} should have 5-minute retry delay"

    def test_email_configuration(self, dag_bag):
        """Test email configuration for biological process monitoring."""
        all_dags = dag_bag.dags.values()

        for dag in all_dags:
            # Should email on failure for biological process monitoring
            assert dag.default_args.get(
                "email_on_failure"
            ), f"DAG {dag.dag_id} should email on failure"

            # Should not email on retry (too noisy for biological processes)
            assert not dag.default_args.get(
                "email_on_retry"
            ), f"DAG {dag.dag_id} should not email on retry"

    def test_catchup_disabled(self, dag_bag):
        """Test that catchup is disabled for real-time biological processes."""
        all_dags = dag_bag.dags.values()

        for dag in all_dags:
            # Biological processes should not catch up (real-time only)
            assert not dag.catchup, f"DAG {dag.dag_id} should have catchup disabled"


class TestTaskCommands:
    """Test dbt task command structure and parameters."""

    def test_dbt_command_structure(self, dag_bag):
        """Test dbt commands have correct structure."""
        # Test continuous processing commands
        continuous_dag = dag_bag.get_dag("continuous_memory_processing")
        run_task = continuous_dag.get_task("run_working_memory_processing")

        # Should change to project directory
        assert "cd" in run_task.bash_command, "Should change to project directory"

        # Should use dbt run
        assert "dbt run" in run_task.bash_command, "Should use dbt run command"

        # Should specify profiles directory
        assert "--profiles-dir" in run_task.bash_command, "Should specify profiles directory"

        # Should use biological tags
        assert "tag:continuous" in run_task.bash_command, "Should use continuous tag"
        assert "tag:working_memory" in run_task.bash_command, "Should use working memory tag"

    def test_biological_variables(self, dag_bag):
        """Test biological variables passed to dbt models."""
        continuous_dag = dag_bag.get_dag("continuous_memory_processing")
        run_task = continuous_dag.get_task("run_working_memory_processing")

        # Should pass working memory capacity (Miller's Law)
        assert (
            "working_memory_capacity: 7" in run_task.bash_command
        ), "Should pass working memory capacity"

        # Should pass attention window
        assert (
            "attention_window_minutes: 5" in run_task.bash_command
        ), "Should pass attention window"

        # Test long-term consolidation variables
        long_term_dag = dag_bag.get_dag("long_term_memory_consolidation")
        long_term_task = long_term_dag.get_task("run_long_term_consolidation")

        # Should pass ultradian cycle timing
        assert (
            "ultradian_cycle_minutes: 90" in long_term_task.bash_command
        ), "Should pass ultradian timing"

        # Should pass Hebbian learning rate
        assert (
            "hebbian_learning_rate: 0.1" in long_term_task.bash_command
        ), "Should pass learning rate"


class TestDAGValidation:
    """Test DAG validation functions."""

    def test_biological_parameter_validation(self):
        """Test biological parameter validation function."""
        # Import the validation function
        from dags.biological_rhythms import validate_biological_parameters

        # Should run without exceptions for valid parameters
        try:
            validate_biological_parameters()
        except AssertionError:
            pytest.fail("Biological parameter validation should pass for valid parameters")
        except Exception as e:
            pytest.fail(f"Unexpected error in validation: {e}")

    def test_circadian_phase_logging(self):
        """Test circadian phase logging function."""
        from dags.biological_rhythms import log_circadian_phase

        # Should run without exceptions
        try:
            log_circadian_phase()
        except Exception as e:
            pytest.fail(f"Circadian phase logging should not raise exceptions: {e}")


class TestBiologicalResearchCompliance:
    """Test compliance with specific neuroscience research papers."""

    def test_mcgaugh_2000_compliance(self, dag_bag):
        """Test compliance with McGaugh (2000) memory consolidation timing."""
        # McGaugh (2000): Memory consolidation occurs during sleep, particularly deep sleep

        deep_sleep_dag = dag_bag.get_dag("deep_sleep_memory_consolidation")

        # Should run during optimal consolidation window (2-4 AM)
        assert (
            deep_sleep_dag.schedule_interval == "0 2 * * *"
        ), "Should align with McGaugh (2000) consolidation timing"

        # Should have consolidation tags
        assert (
            "systems_consolidation" in deep_sleep_dag.tags
        ), "Should reference systems consolidation"

    def test_dudai_2004_compliance(self, dag_bag):
        """Test compliance with Dudai (2004) consolidation research."""
        # Dudai (2004): Different types of consolidation occur at different times

        # Short-term: synaptic consolidation (minutes to hours)
        short_term_dag = dag_bag.get_dag("short_term_memory_consolidation")
        assert "*/20" in short_term_dag.schedule_interval, "Should handle synaptic consolidation"

        # Long-term: systems consolidation (hours to days)
        long_term_dag = dag_bag.get_dag("long_term_memory_consolidation")
        assert "long_term" in long_term_dag.tags, "Should handle systems consolidation"

    def test_tononi_cirelli_2006_compliance(self, dag_bag):
        """Test compliance with Tononi & Cirelli (2006) synaptic homeostasis."""
        # Tononi & Cirelli (2006): Synaptic homeostasis occurs during sleep

        homeostasis_dag = dag_bag.get_dag("synaptic_homeostasis_maintenance")

        # Should run during minimal activity (Sunday 3 AM)
        assert (
            homeostasis_dag.schedule_interval == "0 3 * * 0"
        ), "Should align with homeostasis research"

        # Should have homeostasis tags
        assert "homeostasis" in homeostasis_dag.tags, "Should reference synaptic homeostasis"

        # Should include memory cleanup and pruning
        expected_tasks = ["run_memory_cleanup", "run_semantic_network_pruning"]
        for task_id in expected_tasks:
            assert task_id in homeostasis_dag.task_dict, f"Should include {task_id} for homeostasis"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
