"""
Tests for REM sleep simulation and creative association processing.

Validates REM sleep timing and creative processing based on:
- Dement & Kleitman (1957): REM sleep patterns and timing
- Crick & Mitchison (1983): REM sleep and memory processing
- Stickgold et al. (2001): Sleep-dependent memory consolidation
- Wagner et al. (2004): Sleep inspires insight and creative problem solving
"""

import pytest
import time
import subprocess
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from orchestration.biological_rhythm_scheduler import (
    BiologicalRhythmScheduler,
    BiologicalMemoryProcessor,
    BiologicalRhythmType,
    CircadianPhase
)


class TestREMSleepTiming:
    """Test REM sleep simulation follows neuroscience research timing"""
    
    def setup_method(self):
        """Setup test environment"""
        self.scheduler = BiologicalRhythmScheduler()
    
    def test_rem_dominant_phase_timing(self):
        """Test REM-dominant phase occurs 4-6 AM (Dement & Kleitman, 1957)"""
        # Dement & Kleitman showed REM sleep peaks in early morning hours
        
        rem_times = [
            (4, CircadianPhase.REM_DOMINANT),  # 4 AM - REM peak starts
            (5, CircadianPhase.REM_DOMINANT),  # 5 AM - continued REM
        ]
        
        for hour, expected_phase in rem_times:
            with patch('orchestration.biological_rhythm_scheduler.datetime') as mock_dt:
                mock_dt.now.return_value = datetime(2025, 9, 1, hour, 0, 0)
                phase = self.scheduler._get_current_circadian_phase()
                
                assert phase == expected_phase, (
                    f"Hour {hour} should be REM-dominant phase per Dement & Kleitman research"
                )
    
    def test_rem_simulation_only_during_rem_phase(self):
        """Test REM simulation only occurs during REM-dominant circadian phase"""
        # Set up timing to meet ultradian cycle requirement (90+ minutes)
        base_time = datetime(2025, 9, 1, 5, 0, 0)  # 5 AM (REM phase)
        self.scheduler.last_long_term = base_time - timedelta(minutes=91)
        
        # Test during REM-dominant phase
        with patch('orchestration.biological_rhythm_scheduler.datetime') as mock_dt:
            mock_dt.now.return_value = base_time
            self.scheduler._get_current_circadian_phase = Mock(return_value=CircadianPhase.REM_DOMINANT)
            
            should_run = self.scheduler._should_run_rem_sleep()
            assert should_run is True, "REM simulation should run during REM-dominant phase"
        
        # Test during non-REM phases
        non_rem_phases = [
            CircadianPhase.WAKE_ACTIVE,
            CircadianPhase.WAKE_QUIET,
            CircadianPhase.LIGHT_SLEEP,
            CircadianPhase.DEEP_SLEEP
        ]
        
        for phase in non_rem_phases:
            with patch('orchestration.biological_rhythm_scheduler.datetime') as mock_dt:
                mock_dt.now.return_value = base_time
                self.scheduler._get_current_circadian_phase = Mock(return_value=phase)
                
                should_run = self.scheduler._should_run_rem_sleep()
                assert should_run is False, f"REM simulation should not run during {phase.value}"
    
    def test_rem_simulation_ultradian_cycle_requirement(self):
        """Test REM simulation follows 90-minute ultradian cycles"""
        # Based on Kleitman's basic rest-activity cycle research
        
        rem_time = datetime(2025, 9, 1, 5, 0, 0)  # 5 AM (REM phase)
        
        # Test that insufficient time since last long-term cycle blocks REM
        with patch('orchestration.biological_rhythm_scheduler.datetime') as mock_dt:
            mock_dt.now.return_value = rem_time
            self.scheduler._get_current_circadian_phase = Mock(return_value=CircadianPhase.REM_DOMINANT)
            # Set last long-term cycle to 89 minutes ago (insufficient)
            self.scheduler.last_long_term = rem_time - timedelta(minutes=89)
            
            should_run = self.scheduler._should_run_rem_sleep()
            assert should_run is False, "REM simulation should wait for full 90-minute ultradian cycle"
        
        # Test that sufficient time allows REM simulation
        with patch('orchestration.biological_rhythm_scheduler.datetime') as mock_dt:
            mock_dt.now.return_value = rem_time
            self.scheduler._get_current_circadian_phase = Mock(return_value=CircadianPhase.REM_DOMINANT)
            # Set last long-term cycle to 90+ minutes ago
            self.scheduler.last_long_term = rem_time - timedelta(minutes=90)
            
            should_run = self.scheduler._should_run_rem_sleep()
            assert should_run is True, "REM simulation should run after full 90-minute cycle"


class TestREMCreativeProcessing:
    """Test REM sleep creative association processing"""
    
    def setup_method(self):
        """Setup mocked processor"""
        self.processor = BiologicalMemoryProcessor(Mock())
    
    @patch('subprocess.run')
    @patch('os.chdir')
    @patch('os.getcwd')
    def test_rem_simulation_targets_creative_models(self, mock_getcwd, mock_chdir, mock_run):
        """Test REM simulation targets concept association models"""
        mock_run.return_value = Mock(stdout="Success", returncode=0)
        mock_getcwd.return_value = "/test/path"
        
        result = self.processor.rem_sleep_simulation()
        
        # Verify REM processing targets creative association models
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        
        # Should target concept associations model specifically
        model_args = [call_args[i+1] for i, arg in enumerate(call_args) if arg == "--select"]
        model_str = " ".join(model_args)
        
        assert "concept_associations" in model_str, "Should target concept associations for creativity"
        
        # Should also include semantic tag for creative processing
        tag_args = [call_args[i+1] for i, arg in enumerate(call_args) if arg == "--select"]
        tag_str = " ".join(tag_args)
        assert "semantic" in tag_str, "Should include semantic tag for creative processing"
        
        assert result is True
    
    @patch('subprocess.run')
    def test_rem_simulation_failure_handling(self, mock_run):
        """Test REM simulation handles creative processing failures gracefully"""
        # Simulate creative processing failure
        mock_run.side_effect = subprocess.CalledProcessError(1, "dbt", stderr="Creative processing failed")
        
        result = self.processor.rem_sleep_simulation()
        assert result is False, "Should handle creative processing failures gracefully"


class TestREMCreativityValidation:
    """Validate REM creative processing against neuroscience research"""
    
    def test_crick_mitchison_rem_processing(self):
        """Validate REM processing follows Crick & Mitchison (1983) patterns"""
        # Crick & Mitchison proposed that REM sleep serves to eliminate
        # parasitic modes and strengthen useful associations
        
        scheduler = BiologicalRhythmScheduler()
        scheduler.processor = Mock()
        scheduler.processor.rem_sleep_simulation.return_value = True
        
        # Execute REM simulation
        result = scheduler._execute_rhythm_cycle(BiologicalRhythmType.REM_SLEEP)
        
        assert result is True
        scheduler.processor.rem_sleep_simulation.assert_called_once()
        
        # Verify metrics tracking (should track creative processing)
        metrics = scheduler.cycle_metrics[BiologicalRhythmType.REM_SLEEP.value]
        assert metrics["count"] == 1, "Should track REM creative processing cycles"
    
    def test_stickgold_rem_memory_integration(self):
        """Validate REM memory integration follows Stickgold et al. (2001)"""
        # Stickgold showed that REM sleep integrates disparate memories
        # into new associative networks
        
        scheduler = BiologicalRhythmScheduler()
        
        # REM simulation should only occur during appropriate circadian phase
        # and after sufficient ultradian cycle time
        rem_time = datetime(2025, 9, 1, 5, 0, 0)  # 5 AM
        
        with patch('orchestration.biological_rhythm_scheduler.datetime') as mock_dt:
            mock_dt.now.return_value = rem_time
            scheduler._get_current_circadian_phase = Mock(return_value=CircadianPhase.REM_DOMINANT)
            scheduler.last_long_term = rem_time - timedelta(minutes=90)
            
            should_run = scheduler._should_run_rem_sleep()
            assert should_run is True, "Should follow Stickgold's REM integration timing"
    
    def test_wagner_insight_generation_timing(self):
        """Validate creative insight timing follows Wagner et al. (2004)"""
        # Wagner showed that sleep (particularly REM) can lead to insight
        # and creative problem solving
        
        scheduler = BiologicalRhythmScheduler()
        
        # Creative processing should be most active during REM-dominant phase
        creative_hours = [4, 5]  # 4-6 AM REM peak
        
        for hour in creative_hours:
            with patch('orchestration.biological_rhythm_scheduler.datetime') as mock_dt:
                mock_dt.now.return_value = datetime(2025, 9, 1, hour, 0, 0)
                phase = scheduler._get_current_circadian_phase()
                
                assert phase == CircadianPhase.REM_DOMINANT, (
                    f"Hour {hour} should support creative insight generation per Wagner research"
                )


class TestREMIntegrationWithConsolidation:
    """Test REM sleep integration with other consolidation processes"""
    
    def setup_method(self):
        """Setup scheduler with mocked processor"""
        self.scheduler = BiologicalRhythmScheduler()
        self.scheduler.processor = Mock()
        self.scheduler.processor.rem_sleep_simulation.return_value = True
        self.scheduler.processor.long_term_consolidation.return_value = True
    
    def test_rem_follows_long_term_consolidation_cycle(self):
        """Test REM simulation properly follows long-term consolidation timing"""
        base_time = datetime(2025, 9, 1, 5, 0, 0)  # 5 AM (REM phase)
        
        # Set long-term consolidation to have occurred 90 minutes ago
        self.scheduler.last_long_term = base_time - timedelta(minutes=90)
        
        with patch('orchestration.biological_rhythm_scheduler.datetime') as mock_dt:
            mock_dt.now.return_value = base_time
            self.scheduler._get_current_circadian_phase = Mock(return_value=CircadianPhase.REM_DOMINANT)
            
            # Both long-term consolidation and REM should be ready
            long_term_ready = self.scheduler._should_run_long_term()
            rem_ready = self.scheduler._should_run_rem_sleep()
            
            assert long_term_ready is True, "Long-term consolidation should be ready"
            assert rem_ready is True, "REM simulation should be ready after ultradian cycle"
            
            # Execute both processes
            long_term_result = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.LONG_TERM)
            rem_result = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.REM_SLEEP)
            
            assert long_term_result is True
            assert rem_result is True
    
    def test_rem_creative_associations_after_consolidation(self):
        """Test REM creative processing builds on consolidated memories"""
        scheduler = BiologicalRhythmScheduler()
        scheduler.processor = Mock()
        
        # Mock both consolidation and creative processing as successful
        scheduler.processor.long_term_consolidation.return_value = True
        scheduler.processor.rem_sleep_simulation.return_value = True
        
        base_time = datetime(2025, 9, 1, 5, 0, 0)  # 5 AM
        
        with patch('orchestration.biological_rhythm_scheduler.datetime') as mock_dt:
            mock_dt.now.return_value = base_time
            scheduler._get_current_circadian_phase = Mock(return_value=CircadianPhase.REM_DOMINANT)
            # Set up timing for both processes
            scheduler.last_long_term = base_time - timedelta(minutes=90)
            
            # Execute long-term consolidation first
            consolidation_result = scheduler._execute_rhythm_cycle(BiologicalRhythmType.LONG_TERM)
            assert consolidation_result is True
            
            # Then execute REM creative processing
            rem_result = scheduler._execute_rhythm_cycle(BiologicalRhythmType.REM_SLEEP)
            assert rem_result is True
            
            # Both processes should have been called
            scheduler.processor.long_term_consolidation.assert_called_once()
            scheduler.processor.rem_sleep_simulation.assert_called_once()


class TestREMSleepFailureRecovery:
    """Test REM sleep simulation failure handling and recovery"""
    
    def setup_method(self):
        """Setup scheduler with failure scenarios"""
        self.scheduler = BiologicalRhythmScheduler()
        self.scheduler.processor = Mock()
    
    def test_rem_simulation_failure_tracking(self):
        """Test REM simulation failures are properly tracked"""
        # Mock REM simulation failure
        self.scheduler.processor.rem_sleep_simulation.return_value = False
        
        result = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.REM_SLEEP)
        
        assert result is False
        metrics = self.scheduler.cycle_metrics[BiologicalRhythmType.REM_SLEEP.value]
        assert metrics["count"] == 1
        assert metrics["failures"] == 1
    
    def test_rem_simulation_exception_recovery(self):
        """Test REM simulation recovers from processing exceptions"""
        # Mock REM simulation exception
        self.scheduler.processor.rem_sleep_simulation.side_effect = Exception("Creative processing error")
        
        # Should not crash the scheduler
        result = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.REM_SLEEP)
        
        assert result is False
        metrics = self.scheduler.cycle_metrics[BiologicalRhythmType.REM_SLEEP.value]
        assert metrics["failures"] == 1
    
    def test_rem_continues_after_failure(self):
        """Test REM simulation continues scheduling after failures"""
        # First attempt fails
        self.scheduler.processor.rem_sleep_simulation.side_effect = [Exception("Error"), True]
        
        # First execution fails
        result1 = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.REM_SLEEP)
        assert result1 is False
        
        # Second execution succeeds
        result2 = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.REM_SLEEP)
        assert result2 is True
        
        # Metrics should reflect both attempts
        metrics = self.scheduler.cycle_metrics[BiologicalRhythmType.REM_SLEEP.value]
        assert metrics["count"] == 2
        assert metrics["failures"] == 1


class TestREMCircadianInteraction:
    """Test REM sleep interaction with circadian rhythms"""
    
    def setup_method(self):
        """Setup scheduler for circadian testing"""
        self.scheduler = BiologicalRhythmScheduler()
    
    def test_rem_blocked_during_wake_hours(self):
        """Test REM simulation is blocked during wake hours"""
        wake_times = [
            (8, CircadianPhase.WAKE_ACTIVE),   # 8 AM
            (12, CircadianPhase.WAKE_ACTIVE),  # 12 PM  
            (18, CircadianPhase.WAKE_ACTIVE),  # 6 PM
            (22, CircadianPhase.WAKE_QUIET),   # 10 PM
        ]
        
        for hour, phase in wake_times:
            with patch('orchestration.biological_rhythm_scheduler.datetime') as mock_dt:
                mock_dt.now.return_value = datetime(2025, 9, 1, hour, 0, 0)
                self.scheduler._get_current_circadian_phase = Mock(return_value=phase)
                # Set ultradian timing to be ready
                self.scheduler.last_long_term = mock_dt.now.return_value - timedelta(minutes=90)
                
                should_run = self.scheduler._should_run_rem_sleep()
                assert should_run is False, f"REM should be blocked at {hour}:00 during {phase.value}"
    
    def test_rem_blocked_during_non_rem_sleep(self):
        """Test REM simulation is blocked during non-REM sleep phases"""
        non_rem_sleep_times = [
            (1, CircadianPhase.LIGHT_SLEEP),  # 1 AM - NREM 1-2
            (3, CircadianPhase.DEEP_SLEEP),   # 3 AM - NREM 3-4
        ]
        
        for hour, phase in non_rem_sleep_times:
            with patch('orchestration.biological_rhythm_scheduler.datetime') as mock_dt:
                mock_dt.now.return_value = datetime(2025, 9, 1, hour, 0, 0)
                self.scheduler._get_current_circadian_phase = Mock(return_value=phase)
                # Set ultradian timing to be ready
                self.scheduler.last_long_term = mock_dt.now.return_value - timedelta(minutes=90)
                
                should_run = self.scheduler._should_run_rem_sleep()
                assert should_run is False, f"REM should be blocked during {phase.value} at {hour}:00"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])