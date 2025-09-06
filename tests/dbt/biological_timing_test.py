"""
Test biological timing parameters compliance with neuroscience research.

This module validates that timing parameters in the dbt configuration
align with established cognitive science research and biological constraints.
"""

import pytest
import yaml
from pathlib import Path
from datetime import timedelta


class TestBiologicalTiming:
    """Test suite for biological timing parameter validation."""
    
    @classmethod
    def setup_class(cls):
        """Load dbt configuration for timing tests."""
        project_path = Path("/Users/ladvien/codex-dreams/biological_memory/dbt_project.yml")
        
        if not project_path.exists():
            pytest.skip("dbt_project.yml not found")
        
        with open(project_path, 'r') as f:
            config = yaml.safe_load(f)
        
        cls.vars = config.get('vars', {})
    
    def test_working_memory_attention_window(self):
        """
        Test working memory attention window matches cognitive research.
        
        Based on:
        - Cowan (2001): "The magical number 4 in short-term memory"
        - Baddeley (2003): "Working memory and conscious awareness"
        - Duration should be 5 minutes for active attention span
        """
        wm_duration = self.vars.get('working_memory_duration', 0)
        wm_window_minutes = self.vars.get('working_memory_window_minutes', 0)
        
        # Test duration in seconds
        expected_duration = 5 * 60  # 5 minutes in seconds
        assert wm_duration == expected_duration, (
            f"Working memory duration should be {expected_duration}s (5 min), "
            f"got {wm_duration}s. Research basis: Cowan (2001) attention span limits"
        )
        
        # Test window in minutes
        assert wm_window_minutes == 5, (
            f"Working memory window should be 5 minutes, got {wm_window_minutes}. "
            f"Research basis: Baddeley (2003) conscious awareness window"
        )
    
    def test_short_term_memory_consolidation_window(self):
        """
        Test STM duration matches hippocampal consolidation research.
        
        Based on:
        - Squire & Kandel (1999): "Memory: From Mind to Molecules"  
        - McGaugh (2000): "Memory consolidation and the medial temporal lobe"
        - Duration should be 30 minutes for hippocampal consolidation
        """
        stm_duration = self.vars.get('short_term_memory_duration', 0)
        stm_minutes = self.vars.get('stm_duration_minutes', 0)
        
        expected_duration = 30 * 60  # 30 minutes in seconds
        assert stm_duration == expected_duration, (
            f"STM duration should be {expected_duration}s (30 min), "
            f"got {stm_duration}s. Research basis: McGaugh (2000) consolidation window"
        )
        
        assert stm_minutes == 30, (
            f"STM duration should be 30 minutes, got {stm_minutes}. "
            f"Research basis: Squire & Kandel (1999) hippocampal processing"
        )
    
    def test_circadian_rhythm_parameters(self):
        """
        Test circadian rhythm timing matches sleep research.
        
        Based on:
        - Dijk & Czeisler (1995): "Contribution of circadian physiology"
        - Walker (2017): "Why We Sleep" - memory consolidation timing
        """
        peak_hour = self.vars.get('circadian_peak_hour', 0)
        trough_hour = self.vars.get('circadian_trough_hour', 0)
        ultradian_minutes = self.vars.get('ultradian_cycle_minutes', 0)
        
        # Peak cognitive performance typically 2 PM (14:00)
        assert peak_hour == 14, (
            f"Circadian peak should be 14 (2 PM), got {peak_hour}. "
            f"Research basis: Dijk & Czeisler (1995) cognitive performance peaks"
        )
        
        # Cognitive trough typically 3 AM (optimal for consolidation)
        assert trough_hour == 3, (
            f"Circadian trough should be 3 (3 AM), got {trough_hour}. "
            f"Research basis: Walker (2017) memory consolidation timing"
        )
        
        # Ultradian cycles are ~90 minutes (REM sleep cycles)
        assert ultradian_minutes == 90, (
            f"Ultradian cycle should be 90 minutes, got {ultradian_minutes}. "
            f"Research basis: REM sleep cycle duration"
        )
    
    def test_consolidation_timing_parameters(self):
        """
        Test memory consolidation timing matches neuroscience research.
        
        Based on:
        - Diekelmann & Born (2010): "The memory function of sleep"
        - Rasch & Born (2013): "About sleep's role in memory"
        """
        consolidation_interval = self.vars.get('consolidation_interval_hours', 0)
        consolidation_threshold = self.vars.get('consolidation_threshold', 0)
        
        # Consolidation should occur hourly during wake, intensively during sleep
        assert consolidation_interval == 1, (
            f"Consolidation interval should be 1 hour, got {consolidation_interval}. "
            f"Research basis: Diekelmann & Born (2010) consolidation cycles"
        )
        
        # Consolidation threshold should be moderate (0.5) for realistic transfer
        assert consolidation_threshold == 0.5, (
            f"Consolidation threshold should be 0.5, got {consolidation_threshold}. "
            f"Research basis: Rasch & Born (2013) memory strength requirements"
        )
    
    def test_forgetting_curve_parameters(self):
        """
        Test forgetting curve parameters match Ebbinghaus research.
        
        Based on:
        - Ebbinghaus (1885): "Memory: A Contribution to Experimental Psychology"
        - Wixted & Ebbesen (1991): "On the form of forgetting"
        """
        forgetting_rate = self.vars.get('forgetting_rate', 0)
        forgetting_time_constant = self.vars.get('forgetting_time_constant', 0)
        
        # Forgetting rate should be small (memories persist)
        assert 0.01 <= forgetting_rate <= 0.1, (
            f"Forgetting rate {forgetting_rate} should be 0.01-0.1. "
            f"Research basis: Ebbinghaus (1885) forgetting curve"
        )
        
        # Time constant should be ~24 hours (daily forgetting cycle)
        assert forgetting_time_constant == 24, (
            f"Forgetting time constant should be 24 hours, got {forgetting_time_constant}. "
            f"Research basis: Wixted & Ebbesen (1991) forgetting dynamics"
        )
    
    def test_synaptic_plasticity_timing(self):
        """
        Test synaptic plasticity timing parameters.
        
        Based on:
        - Bi & Poo (1998): "Synaptic modifications in cultured hippocampal neurons"
        - Abbott & Nelson (2000): "Synaptic plasticity: taming the beast"
        """
        stdp_window = self.vars.get('stdp_window_ms', 0)
        ltp_threshold = self.vars.get('ltp_threshold', 0)
        ltd_threshold = self.vars.get('ltd_threshold', 0)
        
        # STDP window should be ~20ms (spike timing window)
        assert stdp_window == 20, (
            f"STDP window should be 20ms, got {stdp_window}ms. "
            f"Research basis: Bi & Poo (1998) spike timing dependent plasticity"
        )
        
        # LTP threshold should be positive (strengthening)
        assert 0.5 <= ltp_threshold <= 0.8, (
            f"LTP threshold {ltp_threshold} should be 0.5-0.8. "
            f"Research basis: Abbott & Nelson (2000) plasticity thresholds"
        )
        
        # LTD threshold should be negative (weakening)
        assert -0.6 <= ltd_threshold <= -0.2, (
            f"LTD threshold {ltd_threshold} should be -0.6 to -0.2. "
            f"Research basis: Abbott & Nelson (2000) depression thresholds"
        )
    
    def test_performance_timing_constraints(self):
        """Test that timing parameters support real-time biological processing."""
        # Working memory should process quickly (<50ms for biological realism)
        wm_duration = self.vars.get('working_memory_duration', 0)
        
        # Convert to processing frequency
        # With 5-minute window and real-time updates, should allow <1s processing
        max_processing_time = 1.0  # 1 second max for biological realism
        
        # This is a design constraint test - processing should be much faster than window
        assert wm_duration >= max_processing_time * 60, (
            f"Working memory window ({wm_duration}s) should allow real-time processing "
            f"(max {max_processing_time}s per update)"
        )
    
    def test_biological_constraint_consistency(self):
        """Test that timing parameters are internally consistent."""
        wm_duration = self.vars.get('working_memory_duration', 0)
        stm_duration = self.vars.get('short_term_memory_duration', 0)
        consolidation_interval = self.vars.get('consolidation_interval_hours', 0) * 3600
        
        # STM should be longer than WM (memory hierarchy)
        assert stm_duration > wm_duration, (
            f"STM duration ({stm_duration}s) should be longer than WM duration ({wm_duration}s)"
        )
        
        # Consolidation interval should be reasonable compared to STM
        assert consolidation_interval <= stm_duration, (
            f"Consolidation interval ({consolidation_interval}s) should be <= STM duration ({stm_duration}s)"
        )


class TestMemoryStageTransitionTiming:
    """Test timing of transitions between memory stages."""
    
    @classmethod
    def setup_class(cls):
        """Load configuration for transition timing tests."""
        project_path = Path("/Users/ladvien/codex-dreams/biological_memory/dbt_project.yml")
        with open(project_path, 'r') as f:
            config = yaml.safe_load(f)
        cls.vars = config.get('vars', {})
    
    def test_working_to_short_term_transition(self):
        """Test WM to STM transition timing is biologically realistic."""
        wm_window = self.vars.get('working_memory_window_minutes', 0) * 60  # Convert to seconds
        stm_duration = self.vars.get('short_term_memory_duration', 0)
        
        # WM items should transfer to STM within the attention window
        assert wm_window <= stm_duration, (
            f"WM window ({wm_window}s) should be <= STM duration ({stm_duration}s) "
            f"for proper memory transfer"
        )
    
    def test_short_term_to_long_term_transition(self):
        """Test STM to LTM consolidation timing."""
        stm_duration = self.vars.get('short_term_memory_duration', 0)
        consolidation_threshold = self.vars.get('consolidation_threshold', 0)
        consolidation_interval = self.vars.get('consolidation_interval_hours', 0) * 3600
        
        # Consolidation should happen multiple times during STM window
        consolidation_opportunities = stm_duration // consolidation_interval
        assert consolidation_opportunities >= 1, (
            f"Should have at least 1 consolidation opportunity during STM window. "
            f"STM duration: {stm_duration}s, consolidation interval: {consolidation_interval}s"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])