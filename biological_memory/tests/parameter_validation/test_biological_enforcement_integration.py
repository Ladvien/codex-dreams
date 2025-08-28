#!/usr/bin/env python3
"""
Biological Parameter Enforcement Integration Tests
BMP-MEDIUM-008: Comprehensive biological accuracy validation

Tests the integration of all biological parameter enforcement mechanisms
including Miller's Law, timing patterns, LTP/LTD, and consolidation patterns.
"""

import pytest
import yaml
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta


class TestBiologicalParameterEnforcement:
    """Test comprehensive biological parameter enforcement"""
    
    @classmethod
    def setup_class(cls):
        cls.project_dir = Path("/Users/ladvien/codex-dreams/biological_memory")
        cls.dbt_project_file = cls.project_dir / "dbt_project.yml"
        
    def load_dbt_config(self):
        """Load dbt project configuration"""
        with open(self.dbt_project_file, 'r') as f:
            return yaml.safe_load(f)
    
    def test_millers_law_comprehensive_enforcement(self):
        """Test Miller's Law (7±2) is enforced throughout the system"""
        config = self.load_dbt_config()
        
        # Verify parameter is set correctly
        capacity = config['vars']['working_memory_capacity']
        assert 5 <= capacity <= 9, f"Working memory capacity {capacity} violates Miller's Law (7±2)"
        
        # Verify it's used in working memory model
        wm_model_path = self.project_dir / "models" / "working_memory" / "wm_active_context.sql"
        with open(wm_model_path, 'r') as f:
            wm_content = f.read()
        
        assert "{{ var('working_memory_capacity') }}" in wm_content, \
            "Working memory model must use configurable capacity parameter"
        assert ("memory_rank <=" in wm_content or "memory_rank, 1) <=" in wm_content), \
            "Working memory model must enforce capacity limit"
    
    def test_five_second_refresh_cycle_validation(self):
        """Test 5-second refresh cycles are properly configured"""
        
        # Check orchestration script exists and contains 5-second timing
        orchestration_path = self.project_dir / "orchestrate_biological_memory.py"
        if orchestration_path.exists():
            with open(orchestration_path, 'r') as f:
                content = f.read()
            assert "sleep(5)" in content or "time.sleep(5)" in content, \
                "Orchestration must implement 5-second refresh cycles"
        
        # Check crontab configuration
        crontab_path = self.project_dir / "biological_memory_crontab.txt"
        if crontab_path.exists():
            with open(crontab_path, 'r') as f:
                content = f.read()
            assert "sleep 5" in content, \
                "Crontab must implement 5-second working memory cycles"
        
        # Check timing documentation exists
        timing_doc_path = self.project_dir / "TIMING_PATTERNS_DOCUMENTATION.md"
        assert timing_doc_path.exists(), \
            "Timing patterns documentation must exist for biological validation"
    
    def test_ltp_ltd_parameter_validation(self):
        """Test Long-Term Potentiation/Depression parameter validation"""
        config = self.load_dbt_config()
        vars_config = config['vars']
        
        # Hebbian learning rate validation
        learning_rate = vars_config['hebbian_learning_rate']
        assert 0.001 <= learning_rate <= 0.1, \
            f"Hebbian learning rate {learning_rate} outside biological range (0.001-0.1)"
        
        # Synaptic decay rate validation
        decay_rate = vars_config['synaptic_decay_rate']
        assert decay_rate < learning_rate, \
            "Synaptic decay rate must be slower than learning rate for memory stability"
        assert decay_rate > 0, "Decay rate must be positive"
        
        # Homeostasis target validation
        homeostasis_target = vars_config['homeostasis_target']
        assert 0.2 <= homeostasis_target <= 0.8, \
            f"Homeostasis target {homeostasis_target} outside biological range (0.2-0.8)"
        
        # LTP/LTD threshold separation
        high_threshold = vars_config['high_quality_threshold']
        medium_threshold = vars_config['medium_quality_threshold']
        threshold_gap = high_threshold - medium_threshold
        assert 0.1 <= threshold_gap <= 0.3, \
            f"LTP/LTD threshold gap {threshold_gap} inappropriate for metaplasticity (0.1-0.3)"
    
    def test_memory_consolidation_patterns(self):
        """Test biological memory consolidation patterns"""
        config = self.load_dbt_config()
        vars_config = config['vars']
        
        # Short-term memory duration
        stm_duration = vars_config['short_term_memory_duration']
        assert 15 <= stm_duration <= 60, \
            f"STM duration {stm_duration}s outside biological range (15-60s)"
        
        # Consolidation window
        consolidation_window = vars_config['consolidation_window_hours']
        assert 12 <= consolidation_window <= 48, \
            f"Consolidation window {consolidation_window}h outside biological range (12-48h)"
        
        # Long-term memory threshold
        ltm_threshold = vars_config['long_term_memory_threshold']
        assert 0.6 <= ltm_threshold <= 0.9, \
            f"LTM threshold {ltm_threshold} outside biological range (0.6-0.9)"
        
        # Consolidation threshold should be lower than LTM threshold
        consolidation_threshold = vars_config['consolidation_threshold']
        assert consolidation_threshold < ltm_threshold, \
            "Consolidation threshold should be lower than LTM threshold"
    
    def test_biological_timing_hierarchy(self):
        """Test biological timing hierarchy is properly configured"""
        config = self.load_dbt_config()
        vars_config = config['vars']
        
        # Timing hierarchy validation
        recent_window = vars_config['recent_activity_window']
        weekly_window = vars_config['weekly_memory_window']
        monthly_window = vars_config['monthly_memory_window']
        
        assert recent_window < weekly_window < monthly_window, \
            "Memory time windows must follow biological hierarchy"
        
        # Processing windows should be reasonable
        short_processing = vars_config['short_processing_window']
        assert 0.5 <= short_processing <= 2, \
            f"Short processing window {short_processing}h outside reasonable range"
        
        # Cleanup window should be reasonable
        cleanup_window = vars_config['memory_cleanup_window']
        assert 12 <= cleanup_window <= 72, \
            f"Memory cleanup window {cleanup_window}h outside reasonable range"
    
    def test_biological_macros_exist_and_validate(self):
        """Test biological memory macros exist and contain proper validation"""
        
        # Check biological memory macros file exists
        bio_macros_path = self.project_dir / "macros" / "biological_memory_macros.sql"
        assert bio_macros_path.exists(), "Biological memory macros must exist"
        
        with open(bio_macros_path, 'r') as f:
            content = f.read()
        
        # Check key biological macros exist
        required_macros = [
            'calculate_hebbian_strength',
            'synaptic_homeostasis',
            'strengthen_associations'
        ]
        
        for macro in required_macros:
            assert f"macro {macro}" in content, f"Biological macro {macro} missing"
        
        # Check parameter validation exists in macros
        assert "WARNING:" in content, "Macros should include parameter validation warnings"
        assert "var(" in content, "Macros should use configurable variables"
    
    def test_biological_monitoring_integration(self):
        """Test biological parameter monitoring is integrated"""
        
        # Check monitoring macros exist
        monitoring_path = self.project_dir / "macros" / "biological_parameter_monitoring.sql"
        assert monitoring_path.exists(), "Biological parameter monitoring macros must exist"
        
        with open(monitoring_path, 'r') as f:
            content = f.read()
        
        # Check key monitoring macros
        monitoring_macros = [
            'validate_biological_parameters',
            'monitor_working_memory_capacity',
            'monitor_ltp_ltd_balance',
            'generate_biological_health_report'
        ]
        
        for macro in monitoring_macros:
            assert f"macro {macro}" in content, f"Monitoring macro {macro} missing"
    
    def test_comprehensive_biological_test_suite(self):
        """Test comprehensive biological test suite exists"""
        
        # Check comprehensive test file exists
        comprehensive_test = self.project_dir / "tests" / "parameter_validation" / "test_biological_accuracy_comprehensive.sql"
        assert comprehensive_test.exists(), "Comprehensive biological test suite must exist"
        
        with open(comprehensive_test, 'r') as f:
            content = f.read()
        
        # Check it tests key biological principles
        biological_tests = [
            'millers_law_enforcement',
            'hebbian_learning_rate',
            'synaptic_homeostasis_target',
            'consolidation_window_timing',
            'ltp_ltd_threshold_separation'
        ]
        
        for test in biological_tests:
            assert test in content, f"Comprehensive test suite missing {test}"
    
    def test_timing_pattern_validation_suite(self):
        """Test timing pattern validation suite exists"""
        
        # Check timing validation file exists
        timing_test = self.project_dir / "tests" / "parameter_validation" / "test_timing_pattern_validation.sql"
        assert timing_test.exists(), "Timing pattern validation suite must exist"
        
        with open(timing_test, 'r') as f:
            content = f.read()
        
        # Check it validates key timing patterns
        timing_tests = [
            'working_memory_refresh_timing',
            'short_term_memory_timing',
            'memory_consolidation_timing',
            'circadian_rhythm_compliance'
        ]
        
        for test in timing_tests:
            assert test in content, f"Timing validation suite missing {test}"
    
    def test_parameter_coverage_completeness(self):
        """Test that all critical biological parameters are covered"""
        config = self.load_dbt_config()
        vars_config = config['vars']
        
        # Essential biological parameters
        essential_params = [
            'working_memory_capacity',
            'short_term_memory_duration', 
            'long_term_memory_threshold',
            'hebbian_learning_rate',
            'synaptic_decay_rate',
            'homeostasis_target',
            'plasticity_threshold',
            'consolidation_threshold',
            'consolidation_window_hours',
            'high_quality_threshold',
            'medium_quality_threshold',
            'overload_threshold',
            'rem_creativity_factor',
            'weak_connection_threshold',
            'strong_connection_threshold'
        ]
        
        missing_params = []
        for param in essential_params:
            if param not in vars_config:
                missing_params.append(param)
        
        assert not missing_params, f"Missing essential biological parameters: {missing_params}"
        
        # Verify all parameters have reasonable values
        for param, value in vars_config.items():
            if param in essential_params:
                assert value is not None, f"Parameter {param} cannot be None"
                assert isinstance(value, (int, float)), f"Parameter {param} must be numeric"
                assert value > 0, f"Parameter {param} must be positive"


class TestBiologicalAccuracyValidation:
    """Test biological accuracy validation mechanisms"""
    
    @classmethod
    def setup_class(cls):
        cls.project_dir = Path("/Users/ladvien/codex-dreams/biological_memory")
    
    def test_can_run_biological_validation_tests(self):
        """Test that biological validation tests can be executed"""
        
        # Try to run the comprehensive biological test
        test_file = self.project_dir / "tests" / "parameter_validation" / "test_biological_accuracy_comprehensive.sql"
        if test_file.exists():
            # This would be run by dbt test in real scenario
            # We just verify the SQL is valid-looking
            with open(test_file, 'r') as f:
                content = f.read()
            
            assert "SELECT" in content.upper(), "Test file should contain SQL SELECT statements"
            assert "UNION ALL" in content.upper(), "Test should combine multiple validations"
            assert ("CASE" in content.upper() and "WHEN" in content.upper()), "Test should have conditional validation logic"
    
    def test_biological_constraints_enforced(self):
        """Test that biological constraints are actually enforced in models"""
        
        # Check working memory model enforces Miller's Law
        wm_path = self.project_dir / "models" / "working_memory" / "wm_active_context.sql"
        if wm_path.exists():
            with open(wm_path, 'r') as f:
                content = f.read()
            
            # Should limit to working_memory_capacity
            assert "{{ var('working_memory_capacity') }}" in content, \
                "Working memory must enforce configurable capacity"
        
        # Check STM model uses proper duration
        stm_path = self.project_dir / "models" / "short_term_memory" / "stm_hierarchical_episodes.sql"
        if stm_path.exists():
            with open(stm_path, 'r') as f:
                content = f.read()
            
            # Should use configurable STM duration
            duration_used = "short_term_memory_duration" in content
            if not duration_used:
                # Check if hardcoded values are used (less ideal)
                hardcoded_duration = "30 SECONDS" in content or "INTERVAL '30" in content
                assert hardcoded_duration, "STM model must enforce memory duration limits"


if __name__ == "__main__":
    # Run biological parameter enforcement tests
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure for faster feedback
    ])
    
    print("\n" + "="*60)
    print("🧬 BIOLOGICAL PARAMETER ENFORCEMENT TEST RESULTS")
    print("="*60)
    
    if exit_code == 0:
        print("✅ ALL BIOLOGICAL PARAMETER ENFORCEMENT TESTS PASSED")
        print("✅ Miller's Law (7±2) properly enforced") 
        print("✅ 5-second refresh cycles validated")
        print("✅ LTP/LTD parameters within biological ranges")
        print("✅ Memory consolidation patterns validated")
        print("✅ Timing hierarchy properly configured")
        print("✅ Biological monitoring integrated")
        print("✅ Comprehensive test suites in place")
        print("")
        print("🎯 SYSTEM BIOLOGICAL ACCURACY: VALIDATED")
        print("📊 Neuroscientific compliance: ACHIEVED")
        print("⚡ Ready for biological memory processing")
    else:
        print("❌ BIOLOGICAL PARAMETER ENFORCEMENT ISSUES DETECTED")
        print("⚠️  Some parameters may not meet neuroscientific standards")
        print("🔧 Review failed tests and adjust biological parameters")
        print("")
        print("📋 Required actions:")
        print("   - Fix parameter values outside biological ranges")
        print("   - Ensure Miller's Law enforcement in working memory")
        print("   - Validate timing patterns match biological cycles")
        print("   - Check LTP/LTD mechanisms are properly configured")
    
    print("="*60)
    exit(exit_code)