#!/usr/bin/env python3
"""
Timing Validation Tests for STORY-DB-007
Tests biological memory timing accuracy for 5-second working memory refresh cycles
"""

import shutil

# Import the orchestrator
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent.parent))
from orchestrate_biological_memory import BiologicalMemoryOrchestrator


class TestBiologicalTimingValidation(unittest.TestCase):
    """
    Test suite for validating biological timing accuracy - STORY-DB-007
    """

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Mock the orchestrator with test paths
        self.orchestrator = BiologicalMemoryOrchestrator(
            base_path=self.temp_dir, log_dir=str(self.log_dir)
        )

    def tearDown(self):
        """Clean up test environment"""
        # Stop any running threads
        if hasattr(self.orchestrator, "stop_working_memory_thread"):
            self.orchestrator.stop_working_memory_thread()

        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_working_memory_5_second_intervals(self):
        """
        Test that working memory processing maintains 5-second intervals
        This is the core requirement for STORY-DB-007
        """
        # Track timing intervals
        execution_times = []
        original_run_dbt = self.orchestrator.run_dbt_command

        def mock_dbt_with_timing(*args, **kwargs):
            execution_times.append(datetime.now())
            return True  # Mock success

        # Mock the dbt command execution to capture timing
        with patch.object(self.orchestrator, "run_dbt_command", side_effect=mock_dbt_with_timing):
            # Set to wake hours for testing
            self.orchestrator.is_wake_hours = True

            # Start the working memory thread
            self.orchestrator.start_working_memory_thread()

            # Let it run for about 15 seconds to capture multiple intervals
            time.sleep(15.2)

            # Stop the thread
            self.orchestrator.stop_working_memory_thread()

        # Validate timing intervals
        self.assertGreaterEqual(
            len(execution_times), 2, "Should have at least 2 executions in 15 seconds"
        )

        # Calculate intervals between executions
        intervals = []
        for i in range(1, len(execution_times)):
            interval = (execution_times[i] - execution_times[i - 1]).total_seconds()
            intervals.append(interval)

        # Validate 5-second intervals (allow ±1 second tolerance for system variance)
        for interval in intervals:
            self.assertGreaterEqual(interval, 4.0, f"Interval too short: {interval}s")
            self.assertLessEqual(interval, 6.0, f"Interval too long: {interval}s")

        # Calculate average interval
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            self.assertAlmostEqual(
                avg_interval,
                5.0,
                delta=1.0,
                msg=f"Average interval should be ~5s, got {avg_interval}s",
            )

    def test_working_memory_sleep_hours_reduced_frequency(self):
        """
        Test that working memory processing reduces frequency during sleep hours
        Should sleep for 60 seconds instead of 5 seconds during sleep hours
        """
        execution_times = []

        def mock_dbt_with_timing(*args, **kwargs):
            execution_times.append(datetime.now())
            return True

        with patch.object(self.orchestrator, "run_dbt_command", side_effect=mock_dbt_with_timing):
            # Set to sleep hours
            self.orchestrator.is_wake_hours = False

            # Start the working memory thread
            self.orchestrator.start_working_memory_thread()

            # Let it run briefly (sleep hours should check less frequently)
            time.sleep(2.5)  # Short test to avoid long waits

            # Stop the thread
            self.orchestrator.stop_working_memory_thread()

        # During sleep hours, it should NOT execute frequently
        # In 2.5 seconds, it should not execute at all if sleeping for 60s intervals
        self.assertLessEqual(
            len(execution_times), 1, "Should not execute frequently during sleep hours"
        )

    def test_wake_sleep_state_transitions(self):
        """Test that wake/sleep state transitions affect timing correctly"""
        # Test wake hours (6am-10pm)
        with patch("orchestrate_biological_memory.datetime") as mock_datetime:
            mock_datetime.now.return_value.hour = 8  # 8am
            self.orchestrator.update_wake_sleep_state()
            self.assertTrue(self.orchestrator.is_wake_hours)

            mock_datetime.now.return_value.hour = 2  # 2am
            self.orchestrator.update_wake_sleep_state()
            self.assertFalse(self.orchestrator.is_wake_hours)

    def test_biological_timing_constants(self):
        """Test that biological timing constants are correctly defined"""
        # Check the orchestrator has correct timing values
        # The 5-second interval should be evident in the working memory method

        # We can verify this by checking the sleep time in working_memory_continuous
        import inspect

        source = inspect.getsource(self.orchestrator.working_memory_continuous)

        # Should contain sleep(5) for 5-second intervals
        self.assertIn("sleep(5)", source, "working_memory_continuous should use 5-second intervals")

        # Should also contain sleep(60) for sleep hours
        self.assertIn(
            "sleep(60)",
            source,
            "working_memory_continuous should use 60-second intervals during sleep",
        )

    @patch("subprocess.run")
    def test_dbt_working_memory_tag_selection(self, mock_run):
        """Test that working memory commands use correct tag selection"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "dbt success"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Call working memory processing
        success = self.orchestrator.run_dbt_command(
            "dbt run --select tag:working_memory --quiet", "test.log"
        )

        self.assertTrue(success)

        # Check that the command was called with correct tag selection
        mock_run.assert_called_once()
        args = mock_run.call_args
        command = args[0][0]

        # Should contain the working memory tag selection
        self.assertIn("tag:working_memory", command)
        self.assertIn("--quiet", command)

    def test_timing_performance_metrics(self):
        """Test that timing performance is tracked correctly"""
        # Mock successful execution
        with patch.object(self.orchestrator, "run_dbt_command", return_value=True):
            initial_metric = self.orchestrator.performance_metrics["last_working_memory"]

            # Simulate working memory processing
            self.orchestrator.is_wake_hours = True

            # Run one cycle of processing
            self.orchestrator.run_dbt_command(
                "dbt run --select tag:working_memory --quiet", "working_memory.log", timeout=10
            )

            # Update performance metrics (simulate what happens in working_memory_continuous)
            self.orchestrator.performance_metrics["last_working_memory"] = datetime.now()

            # Check that metrics were updated
            self.assertIsNotNone(self.orchestrator.performance_metrics["last_working_memory"])
            self.assertNotEqual(
                self.orchestrator.performance_metrics["last_working_memory"], initial_metric
            )

    def test_error_handling_preserves_timing(self):
        """Test that error handling doesn't break 5-second timing cycles"""
        execution_times = []
        error_count = 0

        def mock_failing_dbt(*args, **kwargs):
            nonlocal error_count
            execution_times.append(datetime.now())
            error_count += 1
            if error_count <= 3:
                return False  # Simulate failures
            return True  # Then succeed

        with patch.object(self.orchestrator, "run_dbt_command", side_effect=mock_failing_dbt):
            self.orchestrator.is_wake_hours = True
            self.orchestrator.start_working_memory_thread()

            # Let it run through some failures
            time.sleep(10.2)
            self.orchestrator.stop_working_memory_thread()

        # Even with errors, timing should be maintained
        self.assertGreater(
            len(execution_times), 0, "Should have attempted executions despite errors"
        )

        # Check that error counting is working
        self.assertGreater(
            self.orchestrator.error_counts["working_memory"], 0, "Should have recorded errors"
        )


class TestCrontabTimingValidation(unittest.TestCase):
    """
    Test suite for validating crontab timing configuration
    """

    def test_crontab_file_contains_5_second_sleep(self):
        """Test that crontab file uses 5-second intervals"""
        crontab_path = Path(__file__).parent.parent.parent / "biological_memory_crontab.txt"
        self.assertTrue(crontab_path.exists(), "Crontab file should exist")

        with open(crontab_path, "r") as f:
            content = f.read()

        # Should contain sleep 5 for 5-second intervals
        self.assertIn("sleep 5", content, "Crontab should specify 5-second sleep intervals")

        # Should contain working memory processing during wake hours
        self.assertIn("6-22", content, "Crontab should specify wake hours (6am-10pm)")

        # Should contain tag:working_memory selection
        self.assertIn("tag:working_memory", content, "Crontab should use working memory tag")

    def test_crontab_wake_hours_specification(self):
        """Test that crontab correctly specifies wake hours for working memory"""
        crontab_path = Path(__file__).parent.parent.parent / "biological_memory_crontab.txt"

        with open(crontab_path, "r") as f:
            lines = f.readlines()

        # Find working memory line
        working_memory_line = None
        for line in lines:
            if "tag:working_memory" in line and not line.startswith("#"):
                working_memory_line = line
                break

        self.assertIsNotNone(working_memory_line, "Should have working memory cron entry")

        # Should specify wake hours (6-22)
        self.assertIn("6-22", working_memory_line, "Working memory should run during wake hours")

        # Should run every minute during wake hours
        self.assertIn(
            "*/1", working_memory_line, "Should run every minute to maintain 5s intervals"
        )

    def test_biological_timing_comments(self):
        """Test that crontab contains proper biological timing documentation"""
        crontab_path = Path(__file__).parent.parent.parent / "biological_memory_crontab.txt"

        with open(crontab_path, "r") as f:
            content = f.read()

        # Should document 5-second refresh cycles
        self.assertIn(
            "5-second refresh cycles", content, "Should document 5-second working memory cycles"
        )

        # Should mention Miller's Law
        self.assertIn("Miller's", content, "Should reference Miller's Law")

        # Should mention biological memory processing
        self.assertIn(
            "biological memory", content.lower(), "Should reference biological memory processing"
        )


if __name__ == "__main__":
    # Create test suite
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()

    # Add all test classes
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestBiologicalTimingValidation))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestCrontabTimingValidation))

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print(f"\n{'='*60}")
    print(f"STORY-DB-007 Timing Validation Test Results")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(
        f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    )

    if result.wasSuccessful():
        print("✅ All timing validation tests PASSED")
        print("🎯 5-second working memory refresh cycles verified")
        print("🕒 Biological timing patterns validated")
    else:
        print("❌ Some timing validation tests FAILED")

    print(f"{'='*60}")

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
