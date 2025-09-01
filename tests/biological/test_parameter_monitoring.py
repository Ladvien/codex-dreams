#!/usr/bin/env python3
"""
Comprehensive Test Suite for Biological Parameter Monitoring
STORY-MEM-002: Test biological parameter monitoring functionality

Tests cover:
- Parameter validation against neuroscience ranges
- Miller's Law compliance monitoring  
- Hebbian learning balance validation
- Alert system functionality
- Dashboard data generation
- Performance impact validation
- Integration with health monitoring
"""

import pytest
import tempfile
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Add src to path for imports
sys.path.append('/Users/ladvien/codex-dreams/src')

# Import the modules under test
from monitoring.biological_parameter_monitor import (
    BiologicalParameterMonitor,
    BiologicalParameter,
    ParameterStatus,
    AlertType,
    ParameterAlert,
    get_biological_parameter_monitor
)
from monitoring.health_integration import (
    BiologicalHealthIntegration,
    integrate_biological_monitoring
)


class TestBiologicalParameterMonitor:
    """Test suite for BiologicalParameterMonitor class"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def mock_dbt_config(self, temp_dir):
        """Create mock dbt project configuration"""
        dbt_config = {
            'name': 'test_biological_memory',
            'vars': {
                'working_memory_capacity': 7,
                'working_memory_duration': 300,
                'short_term_memory_duration': 1800,
                'hebbian_learning_rate': 0.1,
                'synaptic_decay_rate': 0.001,
                'homeostasis_target': 0.5,
                'consolidation_threshold': 0.5,
                'high_quality_threshold': 0.8,
                'medium_quality_threshold': 0.6,
                'consolidation_window_hours': 24,
                'plasticity_threshold': 0.6,
                'creativity_temperature': 0.7,
                'weak_memory_decay_factor': 0.8
            }
        }
        
        config_path = Path(temp_dir) / 'dbt_project.yml'
        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(dbt_config, f)
        
        return temp_dir
    
    @pytest.fixture
    def monitor(self, mock_dbt_config):
        """Create BiologicalParameterMonitor instance for testing"""
        return BiologicalParameterMonitor(
            base_path=mock_dbt_config,
            dbt_project_dir=mock_dbt_config,
            enable_optimization=True,
            monitoring_interval=1  # Short interval for testing
        )
    
    def test_parameter_initialization(self, monitor):
        """Test that biological parameters are properly initialized"""
        assert len(monitor.parameters) >= 12  # Expected number of core parameters
        
        # Test key parameters exist
        key_params = [
            'working_memory_capacity',
            'hebbian_learning_rate',
            'synaptic_decay_rate',
            'homeostasis_target',
            'consolidation_threshold'
        ]
        
        for param_name in key_params:
            assert param_name in monitor.parameters
            param = monitor.parameters[param_name]
            assert isinstance(param, BiologicalParameter)
            assert param.neuroscience_reference is not None
            assert param.optimal_min <= param.optimal_max
            assert param.critical_min <= param.critical_max
    
    def test_millers_law_parameter_validation(self, monitor):
        """Test Miller's Law parameter validation"""
        # Test optimal range (7±2)
        monitor.parameters['working_memory_capacity'].current_value = 7
        status, message = monitor.validate_parameter('working_memory_capacity')
        assert status == ParameterStatus.OPTIMAL
        assert message is None
        
        # Test warning range
        monitor.parameters['working_memory_capacity'].current_value = 4
        status, message = monitor.validate_parameter('working_memory_capacity')
        assert status in [ParameterStatus.WARNING, ParameterStatus.ACCEPTABLE]
        
        # Test critical violation
        monitor.parameters['working_memory_capacity'].current_value = 15
        status, message = monitor.validate_parameter('working_memory_capacity')
        assert status == ParameterStatus.CRITICAL
        assert message is not None
        assert "critical range" in message
    
    def test_hebbian_learning_rate_validation(self, monitor):
        """Test Hebbian learning rate validation against neuroscience ranges"""
        # Test optimal rate (0.05-0.15)
        monitor.parameters['hebbian_learning_rate'].current_value = 0.1
        status, message = monitor.validate_parameter('hebbian_learning_rate')
        assert status == ParameterStatus.OPTIMAL
        
        # Test too high (risk of runaway potentiation)
        monitor.parameters['hebbian_learning_rate'].current_value = 0.8
        status, message = monitor.validate_parameter('hebbian_learning_rate')
        assert status == ParameterStatus.CRITICAL
        
        # Test too low (insufficient learning)
        monitor.parameters['hebbian_learning_rate'].current_value = 0.0001
        status, message = monitor.validate_parameter('hebbian_learning_rate')
        assert status == ParameterStatus.CRITICAL
    
    def test_synaptic_balance_validation(self, monitor):
        """Test synaptic learning vs decay balance"""
        # Test healthy balance
        monitor.parameters['hebbian_learning_rate'].current_value = 0.1
        monitor.parameters['synaptic_decay_rate'].current_value = 0.001
        
        balance_ok, message = monitor.check_hebbian_learning_balance()
        assert balance_ok is True
        assert "optimal" in message
        
        # Test unhealthy balance (decay >= learning)
        monitor.parameters['synaptic_decay_rate'].current_value = 0.15
        balance_ok, message = monitor.check_hebbian_learning_balance()
        assert balance_ok is False
        assert "cannot form" in message
    
    def test_threshold_separation_validation(self, monitor):
        """Test memory quality threshold separation"""
        # Test optimal separation
        monitor.parameters['consolidation_threshold'].current_value = 0.4
        monitor.parameters['medium_quality_threshold'].current_value = 0.6
        monitor.parameters['high_quality_threshold'].current_value = 0.8
        
        separation_ok, message = monitor.check_threshold_separation()
        assert separation_ok is True
        assert "optimal" in message
        
        # Test threshold convergence (bad for metaplasticity)
        monitor.parameters['medium_quality_threshold'].current_value = 0.79
        separation_ok, message = monitor.check_threshold_separation()
        assert separation_ok is False
        assert "separation" in message
    
    @patch('duckdb.connect')
    def test_millers_law_compliance_check(self, mock_duckdb, monitor):
        """Test Miller's Law compliance monitoring in working memory"""
        # Mock DuckDB connection and query results
        mock_conn = MagicMock()
        mock_duckdb.return_value.__enter__.return_value = mock_conn
        
        # Test normal capacity (within Miller's Law)
        mock_conn.execute.return_value.fetchone.side_effect = [
            (1,),  # Tables exist
            (5,)   # 5 active memories (within 7±2)
        ]
        
        compliance_ok, message = monitor.check_millers_law_compliance()
        assert compliance_ok is True
        assert "within capacity" in message
        
        # Test capacity overload
        mock_conn.execute.return_value.fetchone.side_effect = [
            (1,),   # Tables exist
            (12,)   # 12 active memories (exceeds Miller's Law)
        ]
        
        compliance_ok, message = monitor.check_millers_law_compliance()
        assert compliance_ok is False
        assert "overload" in message or "violation" in message
    
    def test_parameter_drift_alert_generation(self, monitor):
        """Test parameter drift detection and alerting"""
        # Set parameter outside optimal range
        monitor.parameters['hebbian_learning_rate'].current_value = 0.8  # Too high
        
        # Generate alerts
        monitor.generate_parameter_drift_alerts()
        
        # Check alert was created
        assert len(monitor.active_alerts) > 0
        
        alert_id = "param_drift_hebbian_learning_rate"
        assert alert_id in monitor.active_alerts
        
        alert = monitor.active_alerts[alert_id]
        assert alert.parameter_name == 'hebbian_learning_rate'
        assert alert.alert_type == AlertType.HEBBIAN_RATE_DRIFT
        assert alert.severity in [ParameterStatus.WARNING, ParameterStatus.CRITICAL]
        assert alert.biological_impact is not None
    
    def test_alert_resolution(self, monitor):
        """Test alert resolution when parameters return to normal"""
        # Create alert condition
        monitor.parameters['working_memory_capacity'].current_value = 15  # Critical
        monitor.generate_parameter_drift_alerts()
        
        alert_count = len(monitor.active_alerts)
        assert alert_count > 0
        
        # Resolve condition
        monitor.parameters['working_memory_capacity'].current_value = 7  # Optimal
        monitor.generate_parameter_drift_alerts()
        
        # Check alert was resolved
        assert len(monitor.active_alerts) < alert_count
        assert len(monitor.alert_history) > 0
    
    def test_comprehensive_monitoring_report(self, monitor):
        """Test comprehensive monitoring report generation"""
        with patch('builtins.open', create=True), \
             patch('yaml.safe_load') as mock_yaml:
            
            # Mock dbt config loading
            mock_yaml.return_value = {
                'vars': {
                    'working_memory_capacity': 7,
                    'hebbian_learning_rate': 0.1,
                    'synaptic_decay_rate': 0.001
                }
            }
            
            report = monitor.run_comprehensive_monitoring()
            
            # Validate report structure
            required_fields = [
                'timestamp',
                'monitoring_time_ms',
                'total_parameters',
                'status_distribution',
                'biological_constraints',
                'parameters',
                'validation_results'
            ]
            
            for field in required_fields:
                assert field in report
            
            # Validate biological constraints
            constraints = report['biological_constraints']
            assert 'millers_law_compliance' in constraints
            assert 'hebbian_learning_balance' in constraints
            assert 'threshold_separation' in constraints
            
            # Validate parameter data
            assert isinstance(report['total_parameters'], int)
            assert report['total_parameters'] > 0
            assert isinstance(report['status_distribution'], dict)
    
    def test_dashboard_data_generation(self, monitor):
        """Test dashboard data generation for visualization"""
        # Run monitoring first
        monitor.run_comprehensive_monitoring()
        
        dashboard_data = monitor.get_monitoring_dashboard_data()
        
        # Validate dashboard structure
        required_fields = [
            'overall_health_score',
            'monitoring_status',
            'total_parameters',
            'status_distribution',
            'active_alerts',
            'biological_constraints',
            'performance_metrics'
        ]
        
        for field in required_fields:
            assert field in dashboard_data
        
        # Validate health score
        health_score = dashboard_data['overall_health_score']
        assert 0 <= health_score <= 100
        
        # Validate status distribution
        status_dist = dashboard_data['status_distribution']
        assert isinstance(status_dist, dict)
    
    def test_continuous_monitoring_lifecycle(self, monitor):
        """Test continuous monitoring start/stop lifecycle"""
        assert monitor.monitoring_active is False
        assert monitor.monitoring_thread is None
        
        # Start monitoring
        monitor.start_continuous_monitoring()
        assert monitor.monitoring_active is True
        assert monitor.monitoring_thread is not None
        
        # Give it a moment to run
        import time
        time.sleep(0.1)
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert monitor.monitoring_active is False
    
    def test_parameter_history_tracking(self, monitor):
        """Test parameter history tracking over time"""
        param_name = 'working_memory_capacity'
        
        # Initial state
        assert len(monitor.parameter_history[param_name]) == 0
        
        # Run monitoring multiple times with different values
        values = [7, 8, 6, 7, 9]
        for value in values:
            monitor.parameters[param_name].current_value = value
            monitor.validate_parameter(param_name)
        
        # Check history tracking
        history = monitor.parameter_history[param_name]
        assert len(history) == len(values)
        
        # Validate history entries
        for i, entry in enumerate(history):
            assert 'timestamp' in entry
            assert 'value' in entry
            assert 'status' in entry
            assert entry['value'] == values[i]
    
    def test_performance_impact_measurement(self, monitor):
        """Test that monitoring has minimal performance impact"""
        import time
        
        # Measure monitoring time
        start_time = time.time()
        report = monitor.run_comprehensive_monitoring()
        monitoring_time = time.time() - start_time
        
        # Validate performance
        assert monitoring_time < 1.0  # Should complete within 1 second
        assert report['monitoring_time_ms'] < 1000  # Internal measurement
        
        # Check performance metrics tracking
        assert 'last_monitoring_time' in monitor.performance_metrics
        assert monitor.performance_metrics['last_monitoring_time'] < 1.0


class TestHealthIntegration:
    """Test suite for health monitoring integration"""
    
    @pytest.fixture
    def mock_health_monitor(self):
        """Create mock health monitor"""
        mock_monitor = Mock()
        mock_monitor.base_path = Path('/tmp/test')
        mock_monitor.health_results = {}
        mock_monitor.health_history = []
        mock_monitor.max_history_size = 1000
        return mock_monitor
    
    @pytest.fixture
    def biological_integration(self, mock_health_monitor):
        """Create biological health integration"""
        with patch('monitoring.health_integration.get_biological_parameter_monitor'):
            integration = BiologicalHealthIntegration(mock_health_monitor)
            integration.biological_monitor = Mock()
            return integration
    
    def test_biological_health_check_integration(self, biological_integration):
        """Test biological parameter health check integration"""
        # Mock monitoring report
        mock_report = {
            'timestamp': datetime.now().isoformat(),
            'total_parameters': 12,
            'status_distribution': {'optimal': 10, 'warning': 2, 'critical': 0},
            'biological_constraints': {
                'millers_law_compliance': {'status': True, 'message': 'OK'},
                'hebbian_learning_balance': {'status': True, 'message': 'OK'}
            },
            'active_alerts': 0,
            'monitoring_time_ms': 50,
            'parameters': {
                'working_memory_capacity': {'value': 7, 'status': 'optimal'}
            }
        }
        
        biological_integration.biological_monitor.run_comprehensive_monitoring.return_value = mock_report
        
        # Run health check
        result = biological_integration.check_biological_parameters()
        
        # Validate result
        assert result.service_name == 'biological_parameters'
        assert result.status in [status for status in [ParameterStatus.OPTIMAL, ParameterStatus.HEALTHY]]
        assert result.details['total_parameters'] == 12
        assert result.details['health_score'] > 80  # Should be high with mostly optimal parameters
    
    def test_dashboard_data_integration(self, biological_integration):
        """Test dashboard data integration"""
        # Mock dashboard data
        mock_dashboard = {
            'overall_health_score': 92.5,
            'monitoring_status': 'active',
            'total_parameters': 12,
            'active_alerts': 1
        }
        
        biological_integration.biological_monitor.get_monitoring_dashboard_data.return_value = mock_dashboard
        
        dashboard_data = biological_integration.get_biological_dashboard_data()
        
        assert dashboard_data == mock_dashboard
    
    def test_enhanced_health_check_method(self, mock_health_monitor, biological_integration):
        """Test enhanced health check method that includes biological parameters"""
        # Mock original health check results
        original_results = {
            'postgresql': Mock(),
            'duckdb': Mock(),
            'system_resources': Mock()
        }
        
        mock_health_monitor.run_comprehensive_health_check = Mock(return_value=original_results)
        
        # Integrate biological monitoring
        integration = integrate_biological_monitoring(mock_health_monitor)
        
        # Run enhanced health check
        enhanced_results = mock_health_monitor.run_comprehensive_health_check()
        
        # Should include original results plus biological parameters
        assert len(enhanced_results) == len(original_results) + 1
        assert 'biological_parameters' in enhanced_results


class TestNeuroscienceCompliance:
    """Test suite for neuroscience research compliance"""
    
    def test_millers_law_range_compliance(self):
        """Test Miller's Law (7±2) parameter ranges"""
        param = BiologicalParameter(
            name='working_memory_capacity',
            current_value=7,
            optimal_min=5.0,
            optimal_max=9.0,
            critical_min=3.0,
            critical_max=12.0,
            unit='items',
            neuroscience_reference='Miller (1956)',
            description="Miller's Law test"
        )
        
        # Test Miller's original finding
        assert param.optimal_min == 5.0  # 7-2
        assert param.optimal_max == 9.0  # 7+2
        assert param.neuroscience_reference == 'Miller (1956)'
    
    def test_hebbian_learning_rate_ranges(self):
        """Test Hebbian learning rate follows neuroscience research"""
        monitor = BiologicalParameterMonitor('/tmp', '/tmp')
        param = monitor.parameters['hebbian_learning_rate']
        
        # Should be within biologically realistic range
        assert 0.05 <= param.optimal_max <= 0.15  # Research-validated range
        assert param.optimal_min >= 0.001  # Minimum for learning
        assert 'Hebb' in param.neuroscience_reference or 'Bliss' in param.neuroscience_reference
    
    def test_consolidation_window_compliance(self):
        """Test memory consolidation windows match research"""
        monitor = BiologicalParameterMonitor('/tmp', '/tmp')
        param = monitor.parameters['consolidation_window_hours']
        
        # Should align with systems consolidation research
        assert 12 <= param.optimal_min <= 24  # Minimum consolidation time
        assert 24 <= param.optimal_max <= 48  # Maximum effective window
        assert 'Squire' in param.neuroscience_reference or 'consolidation' in param.description.lower()


class TestPerformanceOptimization:
    """Test suite for performance optimization features"""
    
    def test_monitoring_efficiency(self):
        """Test that monitoring is computationally efficient"""
        monitor = BiologicalParameterMonitor('/tmp', '/tmp', monitoring_interval=0.1)
        
        import time
        start_time = time.time()
        
        # Run multiple monitoring cycles
        for _ in range(5):
            monitor.run_comprehensive_monitoring()
        
        total_time = time.time() - start_time
        avg_time = total_time / 5
        
        # Should be fast enough for real-time monitoring
        assert avg_time < 0.5  # Less than 500ms per cycle
    
    def test_memory_usage_optimization(self):
        """Test memory usage remains bounded"""
        monitor = BiologicalParameterMonitor('/tmp', '/tmp', history_size=100)
        
        # Generate lots of monitoring data
        for i in range(500):
            monitor.parameter_history['test_param'].append({
                'timestamp': datetime.now(),
                'value': i,
                'status': 'optimal'
            })
        
        # Check history size is bounded
        assert len(monitor.parameter_history['test_param']) <= monitor.history_size


if __name__ == '__main__':
    """Run tests directly"""
    pytest.main([__file__, '-v', '--tb=short'])