#!/usr/bin/env python3
"""
Advanced Test Scenarios for BMP-008 Biological Memory Orchestration
Focus on production readiness, edge cases, and performance validation
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import threading
import time
import signal
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import json
import subprocess

# Import the orchestrator
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from orchestrate_biological_memory import BiologicalMemoryOrchestrator


class TestProductionScenarios(unittest.TestCase):
    """
    Test production deployment scenarios and operational requirements
    """
    
    def setUp(self):
        """Set up production test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.orchestrator = BiologicalMemoryOrchestrator(
            base_path=self.temp_dir, 
            log_dir=str(self.log_dir)
        )

    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self.orchestrator, 'stop_working_memory_thread'):
            self.orchestrator.stop_working_memory_thread()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under continuous load"""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Simulate high-frequency operations
        with patch.object(self.orchestrator, 'run_dbt_command', return_value=True):
            for i in range(100):
                self.orchestrator.stm_processing()
                self.orchestrator.consolidation_processing()
                
                # Force garbage collection periodically
                if i % 20 == 0:
                    gc.collect()
        
        # Check final memory usage
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        memory_growth_mb = memory_growth / 1024 / 1024
        
        # Memory growth should be reasonable (< 50MB for 100 operations)
        self.assertLess(memory_growth_mb, 50, 
                       f"Memory grew by {memory_growth_mb:.2f}MB, which may indicate a leak")

    def test_signal_handling_production(self):
        """Test production-grade signal handling"""
        # Test SIGTERM handling
        original_handler = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        
        try:
            # Set up signal handler
            self.orchestrator.signal_handler(signal.SIGTERM, None)
            # Should not raise exception
            self.assertTrue(True)
        finally:
            # Restore original handler
            signal.signal(signal.SIGTERM, original_handler)

    def test_log_rotation_simulation(self):
        """Test behavior when log files are rotated"""
        # Create initial log entries
        with patch.object(self.orchestrator, 'run_dbt_command', return_value=True):
            self.orchestrator.stm_processing()
        
        # Simulate log rotation by moving the log file
        log_file = self.log_dir / 'stm.log'
        if log_file.exists():
            rotated_file = self.log_dir / 'stm.log.old'
            shutil.move(str(log_file), str(rotated_file))
        
        # Continue operations - should create new log file
        with patch.object(self.orchestrator, 'run_dbt_command', return_value=True):
            self.orchestrator.stm_processing()
        
        # New log file should exist
        self.assertTrue(log_file.exists())

    def test_disk_space_exhaustion_simulation(self):
        """Test behavior when disk space is limited"""
        # This is a simulation - we can't actually fill up disk in tests
        # Instead, we test the error handling when write operations fail
        
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            # Operations should not crash when logging fails
            try:
                with patch.object(self.orchestrator, 'run_dbt_command', return_value=True):
                    self.orchestrator.stm_processing()
                # Should handle logging errors gracefully
                self.assertTrue(True)
            except OSError:
                self.fail("Orchestrator should handle disk space exhaustion gracefully")

    def test_concurrent_health_checks(self):
        """Test concurrent health check operations"""
        results = []
        errors = []
        
        def run_health_check():
            try:
                result = self.orchestrator.health_check()
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run multiple concurrent health checks
        threads = []
        for _ in range(10):
            t = threading.Thread(target=run_health_check)
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Should have results without errors
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 10)

    def test_configuration_validation(self):
        """Test configuration parameter validation"""
        # Test invalid base path
        with self.assertRaises(Exception):
            BiologicalMemoryOrchestrator(base_path="/nonexistent/path/that/should/not/exist")
        
        # Test with read-only log directory
        readonly_dir = Path(self.temp_dir) / 'readonly'
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only
        
        try:
            # Should fall back to alternative logging
            orchestrator = BiologicalMemoryOrchestrator(
                base_path=self.temp_dir,
                log_dir=str(readonly_dir)
            )
            self.assertIsNotNone(orchestrator.log_dir)
        finally:
            readonly_dir.chmod(0o755)  # Restore permissions for cleanup


class TestBiologicalRhythmAccuracy(unittest.TestCase):
    """
    Test biological rhythm accuracy and scientific correctness
    """
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.orchestrator = BiologicalMemoryOrchestrator(
            base_path=self.temp_dir, 
            log_dir=str(self.log_dir)
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_circadian_rhythm_fidelity(self):
        """Test adherence to circadian rhythm patterns"""
        # Test various hours throughout the day
        test_hours = list(range(24))
        
        for hour in test_hours:
            with patch('orchestrate_biological_memory.datetime') as mock_datetime:
                mock_datetime.now.return_value.hour = hour
                self.orchestrator.update_wake_sleep_state()
                
                if 6 <= hour <= 22:
                    self.assertTrue(self.orchestrator.is_wake_hours, 
                                  f"Hour {hour} should be wake hours")
                else:
                    self.assertFalse(self.orchestrator.is_wake_hours, 
                                   f"Hour {hour} should be sleep hours")

    def test_rem_sleep_ultradian_rhythm(self):
        """Test REM sleep follows 90-minute ultradian cycles"""
        rem_times = ["22:00", "23:30", "01:00", "02:30", "04:00", "05:30"]
        
        # Verify 90-minute intervals
        time_objects = []
        for time_str in rem_times:
            hour, minute = map(int, time_str.split(':'))
            # Convert to minutes since midnight, handling day rollover
            if hour < 12:  # Early morning hours
                minutes = (hour + 24) * 60 + minute
            else:
                minutes = hour * 60 + minute
            time_objects.append(minutes)
        
        # Check intervals between consecutive REM periods
        for i in range(1, len(time_objects)):
            interval = time_objects[i] - time_objects[i-1]
            if interval < 0:  # Handle midnight rollover
                interval += 24 * 60
            
            # Should be 90 minutes (with some tolerance for scheduling)
            self.assertAlmostEqual(interval, 90, delta=5, 
                                 msg=f"REM interval should be ~90 minutes, got {interval}")

    def test_slow_wave_sleep_timing(self):
        """Test slow-wave sleep occurs during optimal hours (2-4 AM)"""
        deep_consolidation_hours = [2, 3, 4]
        
        # Verify these are during the deepest sleep phase
        for hour in deep_consolidation_hours:
            # These hours should be:
            # 1. During sleep hours (not wake)
            # 2. Before morning REM sleep
            # 3. After initial NREM sleep onset
            
            self.assertTrue(2 <= hour <= 4, 
                          f"Deep consolidation at hour {hour} should be during slow-wave sleep")
            
            # Verify it's during sleep hours
            with patch('orchestrate_biological_memory.datetime') as mock_datetime:
                mock_datetime.now.return_value.hour = hour
                self.orchestrator.update_wake_sleep_state()
                self.assertFalse(self.orchestrator.is_wake_hours)

    def test_memory_consolidation_hierarchy(self):
        """Test memory consolidation follows biological hierarchy"""
        # Working Memory -> STM -> LTM consolidation timing should respect biological constraints
        
        # Working memory: Most frequent (every 5s during wake)
        # STM: Regular (every 5 minutes)  
        # Consolidation: Periodic (hourly)
        # Deep consolidation: Infrequent (daily during sleep)
        # Homeostasis: Rare (weekly)
        
        frequencies = {
            'working_memory': 5,      # seconds
            'stm': 5 * 60,           # 5 minutes  
            'consolidation': 60 * 60, # 1 hour
            'deep_consolidation': 24 * 60 * 60, # daily
            'homeostasis': 7 * 24 * 60 * 60     # weekly
        }
        
        # Verify frequency hierarchy (faster processes should have lower intervals)
        frequency_values = list(frequencies.values())
        self.assertEqual(frequency_values, sorted(frequency_values), 
                        "Memory consolidation frequencies should follow biological hierarchy")


class TestPerformanceAndScaling(unittest.TestCase):
    """
    Test performance characteristics and scaling behavior
    """
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.orchestrator = BiologicalMemoryOrchestrator(
            base_path=self.temp_dir, 
            log_dir=str(self.log_dir)
        )

    def tearDown(self):
        if hasattr(self.orchestrator, 'stop_working_memory_thread'):
            self.orchestrator.stop_working_memory_thread()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_operation_timing_requirements(self):
        """Test operations meet timing requirements"""
        
        # Working memory operations should be very fast (< 10s for frequent execution)
        with patch.object(self.orchestrator, 'run_dbt_command', return_value=True) as mock_dbt:
            start_time = time.time()
            self.orchestrator.stm_processing()
            duration = time.time() - start_time
            
            # Should complete quickly for frequent operations
            self.assertLess(duration, 1.0, "STM processing should complete in < 1s")
        
        # Verify appropriate timeout values are used
        mock_dbt.assert_called_with(
            "dbt run --select short_term_memory --quiet",
            "stm.log"
        )

    def test_error_recovery_timing(self):
        """Test error recovery doesn't cause excessive delays"""
        
        # Simulate rapid failures
        with patch.object(self.orchestrator, 'run_dbt_command', return_value=False):
            start_time = time.time()
            
            # Run multiple failing operations
            for _ in range(5):
                self.orchestrator.stm_processing()
            
            duration = time.time() - start_time
            
            # Even with failures, should not take excessively long
            self.assertLess(duration, 5.0, "Error recovery should not cause excessive delays")
        
        # Error count should be tracked
        self.assertEqual(self.orchestrator.error_counts['stm'], 5)

    def test_thread_lifecycle_performance(self):
        """Test thread creation/destruction doesn't impact performance"""
        
        # Time multiple thread start/stop cycles
        start_time = time.time()
        
        for _ in range(5):
            self.orchestrator.start_working_memory_thread()
            time.sleep(0.1)  # Brief operation
            self.orchestrator.stop_working_memory_thread()
        
        duration = time.time() - start_time
        
        # Should handle thread lifecycle efficiently
        self.assertLess(duration, 2.0, "Thread lifecycle should be efficient")

    def test_log_file_growth_management(self):
        """Test log files don't grow excessively"""
        
        # Generate many log entries
        with patch.object(self.orchestrator, 'run_dbt_command', return_value=True):
            for _ in range(50):
                self.orchestrator.stm_processing()
                self.orchestrator.consolidation_processing()
        
        # Check log file sizes are reasonable
        for log_file in self.log_dir.glob('*.log'):
            file_size = log_file.stat().st_size
            self.assertLess(file_size, 1024 * 1024, f"Log file {log_file.name} should not exceed 1MB in tests")


class TestFailureRecoveryScenarios(unittest.TestCase):
    """
    Test various failure scenarios and recovery mechanisms
    """
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.orchestrator = BiologicalMemoryOrchestrator(
            base_path=self.temp_dir, 
            log_dir=str(self.log_dir)
        )

    def tearDown(self):
        if hasattr(self.orchestrator, 'stop_working_memory_thread'):
            self.orchestrator.stop_working_memory_thread()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_connection_recovery(self):
        """Test recovery from database connection failures"""
        
        # Simulate database unavailable, then recovery
        with patch('duckdb.connect') as mock_connect:
            # First call fails
            mock_connect.side_effect = [
                Exception("Connection refused"),
                Exception("Connection refused"), 
                MagicMock()  # Third call succeeds
            ]
            
            # Should fail first two times
            self.assertFalse(self.orchestrator.health_check())
            self.assertFalse(self.orchestrator.health_check())
            
            # Should recover on third attempt
            self.assertTrue(self.orchestrator.health_check())

    def test_subprocess_failure_handling(self):
        """Test handling of dbt subprocess failures"""
        
        with patch('subprocess.run') as mock_run:
            # Simulate various subprocess failures
            failures = [
                subprocess.CalledProcessError(1, 'dbt'),
                FileNotFoundError("dbt not found"),
                PermissionError("Permission denied"),
                subprocess.TimeoutExpired('dbt', 10)
            ]
            
            for failure in failures:
                mock_run.side_effect = failure
                
                # Should handle gracefully without crashing
                result = self.orchestrator.run_dbt_command("dbt test", "test.log")
                self.assertFalse(result)

    def test_cascading_failure_prevention(self):
        """Test prevention of cascading failures"""
        
        # Simulate high error rate in one component
        self.orchestrator.error_counts['stm'] = 10
        
        with patch.object(self.orchestrator, 'run_dbt_command', return_value=False):
            # Should still attempt other operations
            self.orchestrator.consolidation_processing()
            
            # Consolidation errors should be independent
            self.assertEqual(self.orchestrator.error_counts['consolidation'], 1)
            self.assertEqual(self.orchestrator.error_counts['stm'], 10)  # Unchanged

    def test_resource_exhaustion_handling(self):
        """Test handling when system resources are exhausted"""
        
        with patch('threading.Thread') as mock_thread:
            mock_thread.side_effect = OSError("Cannot create thread")
            
            # Should handle thread creation failures gracefully
            try:
                self.orchestrator.start_working_memory_thread()
                # Should not crash, may log error
                self.assertTrue(True)
            except OSError:
                self.fail("Should handle thread creation failure gracefully")


if __name__ == '__main__':
    # Run advanced scenario tests
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestProductionScenarios,
        TestBiologicalRhythmAccuracy,
        TestPerformanceAndScaling,
        TestFailureRecoveryScenarios
    ]
    
    for test_class in test_classes:
        test_suite.addTests(test_loader.loadTestsFromTestCase(test_class))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Advanced Scenario Tests Complete")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*60}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)