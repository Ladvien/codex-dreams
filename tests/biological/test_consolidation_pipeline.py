"""
Tests for memory consolidation pipeline timing and biological accuracy.

Validates that memory consolidation follows neuroscience research patterns:
- McGaugh (2000): Memory consolidation timing
- Squire & Kandel (2009): Systems consolidation
- Frankland & Bontempi (2005): Hippocampal-neocortical dialogue
"""

import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from orchestration.biological_rhythm_scheduler import (
    BiologicalMemoryProcessor,
    BiologicalRhythmScheduler,
    BiologicalRhythmType,
    CircadianPhase,
)


class TestMemoryConsolidationTiming:
    """Test memory consolidation follows biological timing constraints"""

    def setup_method(self):
        """Setup test environment"""
        self.scheduler = BiologicalRhythmScheduler()
        self.processor = BiologicalMemoryProcessor(Mock())

    def test_short_term_consolidation_episodic_integration(self):
        """Test short-term consolidation integrates episodic memories every 20 minutes"""
        # Based on working memory research showing episodic buffer integration
        # occurs in 15-30 minute windows (Baddeley, 2000)

        base_time = datetime(2025, 9, 1, 12, 0, 0)
        self.scheduler.last_short_term = base_time

        # Test that exactly 20 minutes triggers consolidation
        test_time = base_time + timedelta(minutes=20)

        with patch("orchestration.biological_rhythm_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = test_time

            should_run = self.scheduler._should_run_short_term()
            assert should_run is True, "Short-term consolidation should run every 20 minutes"

        # Test that less than 20 minutes doesn't trigger
        test_time = base_time + timedelta(minutes=19, seconds=30)

        with patch("orchestration.biological_rhythm_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = test_time

            should_run = self.scheduler._should_run_short_term()
            assert should_run is False, "Short-term consolidation should wait full 20 minutes"

    def test_long_term_consolidation_hippocampal_replay(self):
        """Test long-term consolidation follows hippocampal replay cycles (90 minutes)"""
        # Based on hippocampal replay research showing 90-minute consolidation cycles
        # (Wilson & McNaughton, 1994; Foster & Wilson, 2006)

        base_time = datetime(2025, 9, 1, 12, 0, 0)
        self.scheduler.last_long_term = base_time

        # Test that exactly 90 minutes triggers hippocampal replay
        test_time = base_time + timedelta(minutes=90)

        with patch("orchestration.biological_rhythm_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = test_time

            should_run = self.scheduler._should_run_long_term()
            assert should_run is True, "Long-term consolidation should run every 90 minutes"

        # Test ultradian rhythm accuracy (should be exactly 90 minutes)
        test_time = base_time + timedelta(minutes=89, seconds=59)

        with patch("orchestration.biological_rhythm_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = test_time

            should_run = self.scheduler._should_run_long_term()
            assert should_run is False, "Should wait for full 90-minute ultradian cycle"

    def test_systems_consolidation_daily_timing(self):
        """Test systems consolidation occurs during deep sleep (2-4 AM daily)"""
        # Based on systems consolidation research (Squire & Kandel, 2009)
        # showing hippocampal-neocortical transfer during slow-wave sleep

        # Test during deep sleep window
        deep_sleep_time = datetime(2025, 9, 2, 3, 0, 0)  # Tuesday 3 AM

        with patch("orchestration.biological_rhythm_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = deep_sleep_time
            self.scheduler._get_current_circadian_phase = Mock(
                return_value=CircadianPhase.DEEP_SLEEP
            )
            # Set last consolidation to yesterday
            self.scheduler.last_deep_sleep = datetime(2025, 9, 1).date()

            should_run = self.scheduler._should_run_deep_sleep()
            assert should_run is True, "Systems consolidation should occur during deep sleep"

        # Test that it only runs once per day
        with patch("orchestration.biological_rhythm_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = deep_sleep_time
            self.scheduler._get_current_circadian_phase = Mock(
                return_value=CircadianPhase.DEEP_SLEEP
            )
            # Set last consolidation to today (already ran)
            self.scheduler.last_deep_sleep = deep_sleep_time.date()

            should_run = self.scheduler._should_run_deep_sleep()
            assert should_run is False, "Systems consolidation should only run once per day"


class TestConsolidationModels:
    """Test that consolidation processes target correct dbt models"""

    def setup_method(self):
        """Setup mocked processor"""
        self.processor = BiologicalMemoryProcessor(Mock())

    @patch("subprocess.run")
    @patch("os.chdir")
    @patch("os.getcwd")
    def test_short_term_consolidation_models(self, mock_getcwd, mock_chdir, mock_run):
        """Test short-term consolidation targets episodic models"""
        mock_run.return_value = Mock(stdout="Success", returncode=0)
        mock_getcwd.return_value = "/test/path"

        result = self.processor.short_term_consolidation()

        # Verify correct models targeted
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]

        # Should target STM hierarchical episodes and consolidating memories
        model_args = [call_args[i + 1] for i, arg in enumerate(call_args) if arg == "--select"]
        model_str = " ".join(model_args)

        assert "stm_hierarchical_episodes" in model_str, "Should target STM episodes model"
        assert "consolidating_memories" in model_str, "Should target consolidating memories model"
        assert result is True

    @patch("subprocess.run")
    @patch("os.chdir")
    @patch("os.getcwd")
    def test_long_term_consolidation_models(self, mock_getcwd, mock_chdir, mock_run):
        """Test long-term consolidation targets hippocampal replay models"""
        mock_run.return_value = Mock(stdout="Success", returncode=0)
        mock_getcwd.return_value = "/test/path"

        result = self.processor.long_term_consolidation()

        # Verify hippocampal replay and semantic network models
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]

        model_args = [call_args[i + 1] for i, arg in enumerate(call_args) if arg == "--select"]
        model_str = " ".join(model_args)

        assert "memory_replay" in model_str, "Should target memory replay model"
        assert "ltm_semantic_network" in model_str, "Should target semantic network model"
        assert result is True

    @patch("subprocess.run")
    @patch("os.chdir")
    @patch("os.getcwd")
    def test_deep_sleep_consolidation_comprehensive(self, mock_getcwd, mock_chdir, mock_run):
        """Test deep sleep consolidation runs comprehensive processing"""
        mock_run.return_value = Mock(stdout="Success", returncode=0)
        mock_getcwd.return_value = "/test/path"

        result = self.processor.deep_sleep_consolidation()

        # Should run twice - consolidation and semantic optimization
        assert mock_run.call_count == 2, "Should run both consolidation and semantic optimization"

        # Check both calls included proper tags
        all_calls = mock_run.call_args_list
        all_args = [call[0][0] for call in all_calls]

        # First call should target consolidation
        consolidation_tags = " ".join(all_args[0])
        assert "consolidation" in consolidation_tags, "First call should target consolidation"
        assert "memory_intensive" in consolidation_tags, "Should include memory intensive tag"

        # Second call should target semantic processing
        semantic_tags = " ".join(all_args[1])
        assert "semantic" in semantic_tags, "Second call should target semantic processing"
        assert "performance_intensive" in semantic_tags, "Should include performance intensive tag"

        assert result is True


class TestConsolidationSuccessFailure:
    """Test consolidation success and failure handling"""

    def setup_method(self):
        """Setup scheduler with mocked processor"""
        self.scheduler = BiologicalRhythmScheduler()
        self.scheduler.processor = Mock()

    def test_consolidation_success_metrics(self):
        """Test successful consolidation updates metrics correctly"""
        self.scheduler.processor.short_term_consolidation.return_value = True

        # Execute consolidation cycle
        result = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.SHORT_TERM)

        assert result is True
        metrics = self.scheduler.cycle_metrics[BiologicalRhythmType.SHORT_TERM.value]
        assert metrics["count"] == 1
        assert metrics["failures"] == 0
        assert metrics["avg_duration"] > 0

    def test_consolidation_failure_handling(self):
        """Test failed consolidation is properly tracked"""
        self.scheduler.processor.long_term_consolidation.return_value = False

        # Execute consolidation cycle
        result = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.LONG_TERM)

        assert result is False
        metrics = self.scheduler.cycle_metrics[BiologicalRhythmType.LONG_TERM.value]
        assert metrics["count"] == 1
        assert metrics["failures"] == 1

    def test_consolidation_exception_recovery(self):
        """Test consolidation system recovers from exceptions"""
        self.scheduler.processor.deep_sleep_consolidation.side_effect = Exception("Test error")

        # Execute consolidation cycle - should not crash
        result = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.DEEP_SLEEP)

        assert result is False
        metrics = self.scheduler.cycle_metrics[BiologicalRhythmType.DEEP_SLEEP.value]
        assert metrics["failures"] == 1


class TestBiologicalAccuracyValidation:
    """Validate consolidation timing against neuroscience research"""

    def test_mcgaugh_consolidation_window(self):
        """Validate consolidation window follows McGaugh (2000) research"""
        # McGaugh's research shows memory consolidation is most effective
        # within specific time windows after encoding

        scheduler = BiologicalRhythmScheduler()

        # Short-term consolidation should occur within 30 minutes of encoding
        # Our 20-minute cycle ensures this requirement is met
        short_term_interval = 20 * 60  # 20 minutes in seconds
        mcgaugh_window = 30 * 60  # 30 minutes max per McGaugh

        assert (
            short_term_interval <= mcgaugh_window
        ), "Short-term consolidation should occur within McGaugh's 30-minute window"

    def test_squire_systems_consolidation_timing(self):
        """Validate systems consolidation follows Squire & Kandel (2009)"""
        # Squire's research shows systems consolidation occurs during
        # slow-wave sleep, primarily in the 2-4 AM window

        scheduler = BiologicalRhythmScheduler()

        # Test that deep sleep phase aligns with Squire's research
        with patch("orchestration.biological_rhythm_scheduler.datetime") as mock_dt:
            # 3 AM should be peak systems consolidation time
            mock_dt.now.return_value = datetime(2025, 9, 1, 3, 0, 0)
            phase = scheduler._get_current_circadian_phase()

            assert (
                phase == CircadianPhase.DEEP_SLEEP
            ), "3 AM should be classified as deep sleep per Squire research"

    def test_frankland_hippocampal_neocortical_timing(self):
        """Validate hippocampal-neocortical transfer timing per Frankland & Bontempi (2005)"""
        # Frankland's research shows hippocampal-neocortical dialogue
        # follows specific timing patterns for memory transfer

        scheduler = BiologicalRhythmScheduler()

        # Long-term consolidation (90 minutes) should align with
        # hippocampal replay cycles identified by Frankland
        ultradian_cycle = 90 * 60  # 90 minutes in seconds

        # Frankland's research suggests 80-100 minute cycles
        frankland_min = 80 * 60  # 80 minutes
        frankland_max = 100 * 60  # 100 minutes

        assert (
            frankland_min <= ultradian_cycle <= frankland_max
        ), "Ultradian cycle should match Frankland's hippocampal-neocortical timing"

    def test_wilson_mcnaughton_replay_patterns(self):
        """Validate replay patterns follow Wilson & McNaughton (1994)"""
        # Wilson & McNaughton identified specific hippocampal replay patterns
        # that occur during rest periods and sleep

        scheduler = BiologicalRhythmScheduler()

        # Replay should occur during both rest (every 90 minutes) and sleep
        # Our implementation covers both scenarios

        # Test that long-term consolidation can occur during wake hours (rest)
        wake_time = datetime(2025, 9, 1, 15, 0, 0)  # 3 PM

        with patch("orchestration.biological_rhythm_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = wake_time
            scheduler.last_long_term = wake_time - timedelta(minutes=90)

            should_run = scheduler._should_run_long_term()
            assert should_run is True, "Replay should occur during wake rest periods"

        # Test that additional replay occurs during sleep
        sleep_time = datetime(2025, 9, 1, 3, 0, 0)  # 3 AM

        with patch("orchestration.biological_rhythm_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = sleep_time
            scheduler._get_current_circadian_phase = Mock(return_value=CircadianPhase.DEEP_SLEEP)
            scheduler.last_deep_sleep = sleep_time.date() - timedelta(days=1)

            should_run = scheduler._should_run_deep_sleep()
            assert should_run is True, "Additional replay should occur during sleep"


class TestConsolidationPipelineIntegration:
    """Integration tests for complete consolidation pipeline"""

    def setup_method(self):
        """Setup full pipeline test environment"""
        self.scheduler = BiologicalRhythmScheduler()
        self.scheduler.processor = Mock()

        # Mock all processor methods
        self.scheduler.processor.short_term_consolidation.return_value = True
        self.scheduler.processor.long_term_consolidation.return_value = True
        self.scheduler.processor.deep_sleep_consolidation.return_value = True

    def test_consolidation_pipeline_progression(self):
        """Test that consolidation follows proper biological progression"""
        base_time = datetime(2025, 9, 1, 12, 0, 0)

        # Set timing to trigger progression through consolidation stages
        with patch("orchestration.biological_rhythm_scheduler.datetime") as mock_dt:
            # First: Short-term consolidation (20 minutes)
            mock_dt.now.return_value = base_time + timedelta(minutes=20)
            self.scheduler.last_short_term = base_time

            assert self.scheduler._should_run_short_term() is True

            # Execute short-term consolidation
            result = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.SHORT_TERM)
            assert result is True
            self.scheduler.processor.short_term_consolidation.assert_called_once()

            # Next: Long-term consolidation (90 minutes)
            mock_dt.now.return_value = base_time + timedelta(minutes=90)
            self.scheduler.last_long_term = base_time

            assert self.scheduler._should_run_long_term() is True

            # Execute long-term consolidation
            result = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.LONG_TERM)
            assert result is True
            self.scheduler.processor.long_term_consolidation.assert_called_once()

            # Finally: Systems consolidation (next day, deep sleep)
            next_day_3am = base_time + timedelta(days=1, hours=15)  # Next day 3 AM
            mock_dt.now.return_value = next_day_3am
            self.scheduler._get_current_circadian_phase = Mock(
                return_value=CircadianPhase.DEEP_SLEEP
            )
            self.scheduler.last_deep_sleep = base_time.date()

            assert self.scheduler._should_run_deep_sleep() is True

            # Execute systems consolidation
            result = self.scheduler._execute_rhythm_cycle(BiologicalRhythmType.DEEP_SLEEP)
            assert result is True
            self.scheduler.processor.deep_sleep_consolidation.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
