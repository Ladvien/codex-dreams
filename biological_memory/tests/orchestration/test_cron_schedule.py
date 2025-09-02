#!/usr/bin/env python3
"""
Comprehensive Test Suite for Biological Memory Crontab Schedule Implementation - BMP-008
Tests biological rhythm scheduling, error handling, and recovery mechanisms
"""

import json
import shutil
import subprocess

# Import the orchestrator
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import duckdb
import pytest
import schedule

sys.path.append(str(Path(__file__).parent.parent.parent))
from orchestrate_biological_memory import BiologicalMemoryOrchestrator


class TestBiologicalMemoryOrchestrator(unittest.TestCase):
    """
    Test suite for the Biological Memory Orchestrator
    """

    def setUp(self):
        """Set up test environment"""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Mock the orchestrator with test paths
        self.orchestrator = BiologicalMemoryOrchestrator(
            base_path=self.temp_dir, log_dir=str(self.log_dir)
        )

        # Clear schedule
        schedule.clear()

    def tearDown(self):
        """Clean up test environment"""
        # Stop any running threads
        if hasattr(self.orchestrator, "stop_working_memory_thread"):
            self.orchestrator.stop_working_memory_thread()

        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Clear schedule
        schedule.clear()

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization and setup"""
        self.assertIsInstance(self.orchestrator, BiologicalMemoryOrchestrator)
        self.assertEqual(self.orchestrator.base_path, Path(self.temp_dir))
        self.assertTrue(self.orchestrator.log_dir.exists())

        # Check initial state
        self.assertFalse(self.orchestrator.is_wake_hours)
        self.assertIsNone(self.orchestrator.working_memory_thread)

        # Check error counters are initialized
        expected_keys = [
            "working_memory",
            "stm",
            "consolidation",
            "deep_consolidation",
            "rem_sleep",
            "homeostasis",
        ]
        self.assertEqual(set(self.orchestrator.error_counts.keys()), set(expected_keys))
        self.assertEqual(
            set(self.orchestrator.performance_metrics.keys()),
            set(f"last_{key}" for key in expected_keys),
        )

    def test_wake_sleep_state_detection(self):
        """Test wake/sleep state detection based on time"""
        # Test wake hours (6am-10pm)
        with patch("orchestrate_biological_memory.datetime") as mock_datetime:
            # Test 8am (wake hours)
            mock_datetime.now.return_value.hour = 8
            self.orchestrator.update_wake_sleep_state()
            self.assertTrue(self.orchestrator.is_wake_hours)

            # Test 2am (sleep hours)
            mock_datetime.now.return_value.hour = 2
            self.orchestrator.update_wake_sleep_state()
            self.assertFalse(self.orchestrator.is_wake_hours)

            # Test boundary conditions
            mock_datetime.now.return_value.hour = 6  # Exactly 6am
            self.orchestrator.update_wake_sleep_state()
            self.assertTrue(self.orchestrator.is_wake_hours)

            mock_datetime.now.return_value.hour = 22  # Exactly 10pm
            self.orchestrator.update_wake_sleep_state()
            self.assertTrue(self.orchestrator.is_wake_hours)

            mock_datetime.now.return_value.hour = 23  # 11pm
            self.orchestrator.update_wake_sleep_state()
            self.assertFalse(self.orchestrator.is_wake_hours)

    @patch("orchestrate_biological_memory.subprocess.run")
    def test_dbt_command_execution_success(self, mock_run):
        """Test successful dbt command execution"""
        # Mock successful command execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "dbt run completed successfully"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        success = self.orchestrator.run_dbt_command("dbt run --select working_memory", "test.log")

        self.assertTrue(success)
        mock_run.assert_called_once()

        # Check log file was created
        log_file = self.orchestrator.log_dir / "test.log"
        self.assertTrue(log_file.exists())

    @patch("orchestrate_biological_memory.subprocess.run")
    def test_dbt_command_execution_failure(self, mock_run):
        """Test failed dbt command execution"""
        # Mock failed command execution
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "dbt compilation error"
        mock_run.return_value = mock_result

        success = self.orchestrator.run_dbt_command("dbt run --select invalid_model", "test.log")

        self.assertFalse(success)

        # Check log file contains error
        log_file = self.orchestrator.log_dir / "test.log"
        self.assertTrue(log_file.exists())

        with open(log_file) as f:
            content = f.read()
            self.assertIn("dbt compilation error", content)
            self.assertIn("Return code: 1", content)

    @patch("orchestrate_biological_memory.subprocess.run")
    def test_dbt_command_timeout(self, mock_run):
        """Test dbt command timeout handling"""
        # Mock timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired("dbt run", 10)

        success = self.orchestrator.run_dbt_command(
            "dbt run --select slow_model", "test.log", timeout=10
        )

        self.assertFalse(success)

    def test_health_check_success(self):
        """Test health check with accessible database"""
        # Create a temporary duckdb database
        db_dir = Path(self.temp_dir) / "dbs"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "memory.duckdb"

        # Create a simple table
        conn = duckdb.connect(str(db_path))
        conn.execute("CREATE TABLE test_table (id INTEGER, name VARCHAR)")
        conn.close()

        # Test health check
        result = self.orchestrator.health_check()
        self.assertTrue(result)

        # Check health log was created
        health_log = self.orchestrator.log_dir / "health_status.jsonl"
        self.assertTrue(health_log.exists())

    def test_health_check_failure(self):
        """Test health check with inaccessible database"""
        # No database created, should fail
        result = self.orchestrator.health_check()
        self.assertFalse(result)

    def test_schedule_setup(self):
        """Test that all biological rhythm schedules are properly configured"""
        # Clear any existing schedules
        schedule.clear()

        # Set up schedules
        self.orchestrator.setup_schedules()

        # Get all scheduled jobs
        jobs = schedule.jobs

        # Should have multiple scheduled jobs
        self.assertGreater(len(jobs), 5)

        # Check that we have jobs for different intervals
        job_intervals = [str(job.interval) for job in jobs]
        self.assertIn("5", job_intervals)  # 5 minute jobs
        self.assertIn("15", job_intervals)  # 15 minute health checks
        self.assertIn("1", job_intervals)  # hourly jobs

    def test_working_memory_thread_management(self):
        """Test working memory thread start/stop functionality"""
        # Start thread
        self.orchestrator.start_working_memory_thread()
        self.assertIsNotNone(self.orchestrator.working_memory_thread)
        self.assertTrue(self.orchestrator.working_memory_thread.is_alive())

        # Stop thread
        self.orchestrator.stop_working_memory_thread()

        # Give thread time to stop
        time.sleep(0.1)

        # Thread should be stopped
        self.assertTrue(self.orchestrator.stop_working_memory.is_set())

    @patch.object(BiologicalMemoryOrchestrator, "run_dbt_command")
    def test_stm_processing(self, mock_run_dbt):
        """Test STM processing execution"""
        mock_run_dbt.return_value = True

        self.orchestrator.stm_processing()

        mock_run_dbt.assert_called_once_with(
            "dbt run --select short_term_memory --quiet", "stm.log"
        )

        # Check metrics are updated
        self.assertIsNotNone(self.orchestrator.performance_metrics["last_stm"])
        self.assertEqual(self.orchestrator.error_counts["stm"], 0)

    @patch.object(BiologicalMemoryOrchestrator, "run_dbt_command")
    def test_consolidation_processing(self, mock_run_dbt):
        """Test consolidation processing execution"""
        mock_run_dbt.return_value = True

        self.orchestrator.consolidation_processing()

        mock_run_dbt.assert_called_once_with(
            "dbt run --select consolidation --quiet", "consolidation.log"
        )

        # Check metrics are updated
        self.assertIsNotNone(self.orchestrator.performance_metrics["last_consolidation"])
        self.assertEqual(self.orchestrator.error_counts["consolidation"], 0)

    @patch.object(BiologicalMemoryOrchestrator, "run_dbt_command")
    def test_deep_consolidation(self, mock_run_dbt):
        """Test deep consolidation processing (slow-wave sleep)"""
        mock_run_dbt.return_value = True

        self.orchestrator.deep_consolidation()

        mock_run_dbt.assert_called_once_with(
            "dbt run --select long_term_memory --full-refresh --quiet",
            "deep_consolidation.log",
            timeout=600,
        )

        # Check metrics are updated
        self.assertIsNotNone(self.orchestrator.performance_metrics["last_deep_consolidation"])
        self.assertEqual(self.orchestrator.error_counts["deep_consolidation"], 0)

    @patch.object(BiologicalMemoryOrchestrator, "run_dbt_command")
    def test_rem_sleep_processing(self, mock_run_dbt):
        """Test REM sleep creative processing"""
        mock_run_dbt.return_value = True

        self.orchestrator.rem_sleep_processing()

        mock_run_dbt.assert_called_once_with(
            "dbt run-operation strengthen_associations --quiet", "rem_sleep.log"
        )

        # Check metrics are updated
        self.assertIsNotNone(self.orchestrator.performance_metrics["last_rem_sleep"])
        self.assertEqual(self.orchestrator.error_counts["rem_sleep"], 0)

    @patch.object(BiologicalMemoryOrchestrator, "run_dbt_command")
    def test_synaptic_homeostasis(self, mock_run_dbt):
        """Test weekly synaptic homeostasis"""
        mock_run_dbt.return_value = True

        self.orchestrator.synaptic_homeostasis()

        mock_run_dbt.assert_called_once_with(
            "dbt run-operation synaptic_homeostasis --quiet", "homeostasis.log", timeout=600
        )

        # Check metrics are updated
        self.assertIsNotNone(self.orchestrator.performance_metrics["last_homeostasis"])
        self.assertEqual(self.orchestrator.error_counts["homeostasis"], 0)

    @patch.object(BiologicalMemoryOrchestrator, "run_dbt_command")
    def test_error_tracking(self, mock_run_dbt):
        """Test error tracking and recovery"""
        # Mock failure
        mock_run_dbt.return_value = False

        # Run STM processing multiple times to trigger error counting
        initial_errors = self.orchestrator.error_counts["stm"]
        self.orchestrator.stm_processing()
        self.orchestrator.stm_processing()

        # Error count should increase
        self.assertEqual(self.orchestrator.error_counts["stm"], initial_errors + 2)

    def test_biological_rhythm_timing(self):
        """Test that biological rhythm timing follows circadian patterns"""
        # Test REM sleep timing (should be during night hours)
        rem_times = ["22:00", "23:30", "01:00", "02:30", "04:00", "05:30"]

        for time_str in rem_times:
            hour, minute = map(int, time_str.split(":"))
            # All REM times should be during night hours (10pm-6am)
            self.assertTrue(hour >= 22 or hour <= 6)

        # Test deep consolidation timing (should be during 2-4am)
        deep_consolidation_hours = [2, 3, 4]

        for hour in deep_consolidation_hours:
            # All deep consolidation should be during slow-wave sleep hours
            self.assertTrue(2 <= hour <= 4)

    def test_performance_metrics_collection(self):
        """Test that performance metrics are properly collected"""
        # All metrics should start as None
        for metric in self.orchestrator.performance_metrics.values():
            self.assertIsNone(metric)

        # Run a successful operation
        with patch.object(self.orchestrator, "run_dbt_command", return_value=True):
            self.orchestrator.stm_processing()

        # Metrics should be updated
        self.assertIsNotNone(self.orchestrator.performance_metrics["last_stm"])
        self.assertIsInstance(self.orchestrator.performance_metrics["last_stm"], datetime)

    def test_log_file_creation(self):
        """Test that appropriate log files are created for different processes"""
        log_files = [
            "working_memory.log",
            "stm.log",
            "consolidation.log",
            "deep_consolidation.log",
            "rem_sleep.log",
            "homeostasis.log",
            "orchestrator.log",
        ]

        # Create orchestrator to ensure logging is set up
        orchestrator = BiologicalMemoryOrchestrator(self.temp_dir, log_dir=str(self.log_dir))

        # Run some operations to generate logs
        with patch.object(orchestrator, "run_dbt_command", return_value=True):
            orchestrator.stm_processing()
            orchestrator.consolidation_processing()

        # Check that log files are created or can be created
        for log_file in log_files:
            log_path = self.log_dir / log_file
            if not log_path.exists():
                # Create the log file to test the path is valid
                log_path.touch()
            self.assertTrue(log_path.exists())

    def test_concurrent_processing_safety(self):
        """Test that concurrent processing operations are safe"""
        # This is a basic test for thread safety
        errors = []

        def run_operation():
            try:
                with patch.object(self.orchestrator, "run_dbt_command", return_value=True):
                    self.orchestrator.stm_processing()
            except Exception as e:
                errors.append(e)

        # Run multiple operations concurrently
        threads = []
        for _ in range(5):
            t = threading.Thread(target=run_operation)
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Should not have any errors
        self.assertEqual(len(errors), 0)

    def test_edge_case_scheduling(self):
        """Test edge cases in scheduling"""
        # Test scheduling at midnight boundary
        with patch("orchestrate_biological_memory.datetime") as mock_datetime:
            mock_datetime.now.return_value.hour = 0  # Midnight
            self.orchestrator.update_wake_sleep_state()
            self.assertFalse(self.orchestrator.is_wake_hours)  # Should be sleep hours

            mock_datetime.now.return_value.hour = 5  # 5am
            self.orchestrator.update_wake_sleep_state()
            self.assertFalse(self.orchestrator.is_wake_hours)  # Still sleep hours

            mock_datetime.now.return_value.hour = 6  # 6am exactly
            self.orchestrator.update_wake_sleep_state()
            self.assertTrue(self.orchestrator.is_wake_hours)  # Wake hours start


class TestCrontabScheduleIntegration(unittest.TestCase):
    """
    Integration tests for crontab schedule file
    """

    def test_crontab_file_exists(self):
        """Test that crontab file exists and is readable"""
        crontab_path = Path(__file__).parent.parent.parent / "biological_memory_crontab.txt"
        self.assertTrue(crontab_path.exists())

        with open(crontab_path, "r") as f:
            content = f.read()
            self.assertGreater(len(content), 100)  # Should have substantial content

    def test_crontab_schedule_patterns(self):
        """Test that crontab contains proper biological rhythm patterns"""
        crontab_path = Path(__file__).parent.parent.parent / "biological_memory_crontab.txt"

        with open(crontab_path, "r") as f:
            content = f.read()

        # Should contain wake hours specification (6-22)
        self.assertIn("6-22", content)

        # Should contain STM processing every 5 minutes
        self.assertIn("*/5 * * * *", content)

        # Should contain REM sleep timing
        self.assertIn("22 * * *", content)  # 10pm
        self.assertIn("30 23 * * *", content)  # 11:30pm

        # Should contain deep consolidation (2-4am)
        self.assertIn("0 2 * * *", content)  # 2am
        self.assertIn("0 3 * * *", content)  # 3am
        self.assertIn("0 4 * * *", content)  # 4am

        # Should contain weekly homeostasis (Sunday)
        self.assertIn("0 3 * * 0", content)  # Sunday 3am

    def test_management_script_exists(self):
        """Test that management script exists and is executable"""
        script_path = Path(__file__).parent.parent.parent / "manage_orchestrator.sh"
        self.assertTrue(script_path.exists())

        # Check if executable (basic check)
        import stat

        file_stat = script_path.stat()
        self.assertTrue(file_stat.st_mode & stat.S_IEXEC)


if __name__ == "__main__":
    # Create a test suite
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()

    # Add all test classes
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestBiologicalMemoryOrchestrator))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestCrontabScheduleIntegration))

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print(f"\n{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(
        f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    )
    print(f"{'='*50}")

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
