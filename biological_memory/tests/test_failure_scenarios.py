#!/usr/bin/env python3
"""
BMP-MEDIUM-010: Failure Scenarios Test Suite
Comprehensive testing of error handling, circuit breakers, and graceful degradation
"""

import sys
import time
import json
import threading
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Import our services
from error_handling import BiologicalMemoryErrorHandler, ErrorType, ErrorEvent
from health_check_service import initialize_health_monitor, ServiceStatus
from automated_recovery_service import initialize_recovery_service
from orchestrate_biological_memory import BiologicalMemoryOrchestrator


class FailureScenarioTester:
    """
    Test suite for comprehensive failure scenario validation
    """
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.test_results: List[Dict[str, Any]] = []
        self.temp_dir = None
        
        # Test configuration
        self.test_timeout = 30  # seconds
        
        print("="*80)
        print("BMP-MEDIUM-010: Failure Scenarios Test Suite")
        print("="*80)
    
    def setup_test_environment(self):
        """Setup isolated test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="bmp_failure_test_")
        temp_path = Path(self.temp_dir)
        
        # Create necessary directories
        (temp_path / "dbs").mkdir(parents=True)
        (temp_path / "logs").mkdir(parents=True)
        
        print(f"Test environment setup: {self.temp_dir}")
        return temp_path
    
    def cleanup_test_environment(self):
        """Cleanup test environment"""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"Test environment cleaned up: {self.temp_dir}")
    
    def test_error_handler_functionality(self) -> Dict[str, Any]:
        """Test error handler basic functionality"""
        print("\n🧪 Testing Error Handler Functionality...")
        
        test_path = self.setup_test_environment()
        
        try:
            # Initialize error handler
            error_handler = BiologicalMemoryErrorHandler(
                base_path=str(test_path),
                circuit_breaker_enabled=True,
                max_db_connections=10,
                ollama_timeout_seconds=30
            )
            
            # Test error event logging
            error_event = ErrorEvent(
                error_id="test_001",
                error_type=ErrorType.CONNECTION_FAILURE,
                timestamp=datetime.now(),
                component="test_component",
                operation="test_operation",
                error_message="Test error for validation",
                context={"test": True}
            )
            
            error_handler.log_error_event(error_event)
            
            # Test retry mechanism
            call_count = 0
            def failing_function():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ConnectionError("Simulated connection failure")
                return "success"
            
            result = error_handler.exponential_backoff_retry(
                failing_function,
                max_retries=5,
                base_delay=0.1,
                exceptions=(ConnectionError,)
            )
            
            # Test system resource monitoring
            resources = error_handler.monitor_system_resources()
            
            # Test graceful degradation
            degradation = error_handler.graceful_degradation_mode("duckdb")
            
            # Verify results
            success = (
                len(error_handler.error_events) > 0 and
                result == "success" and
                call_count == 3 and
                'memory_percent' in resources and
                not degradation['consolidation_processing']
            )
            
            return {
                'test': 'error_handler_functionality',
                'status': 'PASS' if success else 'FAIL',
                'details': {
                    'error_events_logged': len(error_handler.error_events),
                    'retry_success': result == "success",
                    'retry_attempts': call_count,
                    'resource_monitoring': len(resources) > 0,
                    'graceful_degradation': not degradation['consolidation_processing']
                }
            }
            
        except Exception as e:
            return {
                'test': 'error_handler_functionality',
                'status': 'FAIL',
                'error': str(e)
            }
        finally:
            self.cleanup_test_environment()
    
    def test_health_monitoring(self) -> Dict[str, Any]:
        """Test health monitoring system"""
        print("\n🔍 Testing Health Monitoring System...")
        
        test_path = self.setup_test_environment()
        
        try:
            # Initialize error handler
            error_handler = BiologicalMemoryErrorHandler(
                base_path=str(test_path),
                circuit_breaker_enabled=True
            )
            
            # Initialize health monitor
            health_monitor = initialize_health_monitor(
                base_path=str(test_path),
                error_handler=error_handler,
                enable_http_endpoints=False  # Disable for testing
            )
            
            # Run health checks
            health_results = health_monitor.run_comprehensive_health_check()
            
            # Test individual service checks
            services_tested = ['system_resources']  # Safe to test
            if 'duckdb' in health_results:
                services_tested.append('duckdb')
            
            # Verify health summary
            summary = health_monitor.get_health_summary()
            
            success = (
                len(health_results) > 0 and
                'system_resources' in health_results and
                'overall_status' in summary and
                summary['overall_status'] in ['healthy', 'degraded', 'unhealthy', 'critical']
            )
            
            return {
                'test': 'health_monitoring',
                'status': 'PASS' if success else 'FAIL',
                'details': {
                    'services_checked': list(health_results.keys()),
                    'overall_status': summary.get('overall_status', 'unknown'),
                    'active_alerts': summary.get('active_alerts', 0),
                    'services_tested': services_tested
                }
            }
            
        except Exception as e:
            return {
                'test': 'health_monitoring',
                'status': 'FAIL',
                'error': str(e)
            }
        finally:
            self.cleanup_test_environment()
    
    def test_automated_recovery(self) -> Dict[str, Any]:
        """Test automated recovery system"""
        print("\n🔄 Testing Automated Recovery System...")
        
        test_path = self.setup_test_environment()
        
        try:
            # Initialize error handler
            error_handler = BiologicalMemoryErrorHandler(
                base_path=str(test_path),
                circuit_breaker_enabled=True
            )
            
            # Initialize recovery service in dry-run mode
            recovery_service = initialize_recovery_service(
                base_path=str(test_path),
                error_handler=error_handler,
                recovery_enabled=True,
                dry_run=True  # Safe for testing
            )
            
            # Test recovery status
            status = recovery_service.get_recovery_status()
            
            # Test recovery rule configuration
            rules_configured = status.get('rules_configured', [])
            
            success = (
                status['recovery_enabled'] and
                status['dry_run'] and
                len(rules_configured) > 0 and
                'postgresql' in rules_configured and
                'duckdb' in rules_configured
            )
            
            return {
                'test': 'automated_recovery',
                'status': 'PASS' if success else 'FAIL',
                'details': {
                    'recovery_enabled': status['recovery_enabled'],
                    'dry_run_mode': status['dry_run'],
                    'rules_configured': rules_configured,
                    'service_failures': status['service_failures']
                }
            }
            
        except Exception as e:
            return {
                'test': 'automated_recovery',
                'status': 'FAIL',
                'error': str(e)
            }
        finally:
            self.cleanup_test_environment()
    
    def test_circuit_breaker_patterns(self) -> Dict[str, Any]:
        """Test circuit breaker patterns"""
        print("\n⚡ Testing Circuit Breaker Patterns...")
        
        test_path = self.setup_test_environment()
        
        try:
            # Initialize error handler with circuit breakers
            error_handler = BiologicalMemoryErrorHandler(
                base_path=str(test_path),
                circuit_breaker_enabled=True
            )
            
            # Test circuit breaker states
            circuit_breakers = error_handler.circuit_breakers
            
            # Test DuckDB circuit breaker if available
            circuit_breaker_test = False
            if 'duckdb' in circuit_breakers:
                cb = circuit_breakers['duckdb']
                initial_state = cb.state
                circuit_breaker_test = initial_state == "CLOSED"
            
            success = (
                len(circuit_breakers) > 0 and
                'duckdb' in circuit_breakers and
                circuit_breaker_test
            )
            
            return {
                'test': 'circuit_breaker_patterns',
                'status': 'PASS' if success else 'FAIL',
                'details': {
                    'circuit_breakers_configured': list(circuit_breakers.keys()),
                    'duckdb_cb_state': circuit_breakers.get('duckdb', {}).state if 'duckdb' in circuit_breakers else 'N/A',
                    'ollama_cb_state': circuit_breakers.get('ollama', {}).state if 'ollama' in circuit_breakers else 'N/A'
                }
            }
            
        except Exception as e:
            return {
                'test': 'circuit_breaker_patterns',
                'status': 'FAIL',
                'error': str(e)
            }
        finally:
            self.cleanup_test_environment()
    
    def test_graceful_degradation(self) -> Dict[str, Any]:
        """Test graceful degradation scenarios"""
        print("\n🛡️ Testing Graceful Degradation...")
        
        test_path = self.setup_test_environment()
        
        try:
            # Initialize error handler
            error_handler = BiologicalMemoryErrorHandler(
                base_path=str(test_path),
                circuit_breaker_enabled=True
            )
            
            # Test different degradation modes
            degradation_tests = {}
            
            # Test DuckDB failure degradation
            duckdb_degradation = error_handler.graceful_degradation_mode("duckdb")
            degradation_tests['duckdb'] = {
                'consolidation_disabled': not duckdb_degradation['consolidation_processing'],
                'deep_consolidation_disabled': not duckdb_degradation['deep_consolidation'],
                'working_memory_enabled': duckdb_degradation['working_memory_processing']
            }
            
            # Test Ollama failure degradation
            ollama_degradation = error_handler.graceful_degradation_mode("ollama")
            degradation_tests['ollama'] = {
                'rem_sleep_disabled': not ollama_degradation['rem_sleep_processing'],
                'consolidation_enabled': ollama_degradation['consolidation_processing']
            }
            
            # Test PostgreSQL failure degradation
            postgres_degradation = error_handler.graceful_degradation_mode("postgres")
            degradation_tests['postgres'] = {
                'working_memory_disabled': not postgres_degradation['working_memory_processing'],
                'consolidation_enabled': postgres_degradation['consolidation_processing']
            }
            
            success = (
                degradation_tests['duckdb']['consolidation_disabled'] and
                degradation_tests['ollama']['rem_sleep_disabled'] and
                degradation_tests['postgres']['working_memory_disabled']
            )
            
            return {
                'test': 'graceful_degradation',
                'status': 'PASS' if success else 'FAIL',
                'details': degradation_tests
            }
            
        except Exception as e:
            return {
                'test': 'graceful_degradation',
                'status': 'FAIL',
                'error': str(e)
            }
        finally:
            self.cleanup_test_environment()
    
    def test_dead_letter_queue(self) -> Dict[str, Any]:
        """Test dead letter queue functionality"""
        print("\n📮 Testing Dead Letter Queue...")
        
        test_path = self.setup_test_environment()
        
        try:
            # Initialize error handler
            error_handler = BiologicalMemoryErrorHandler(
                base_path=str(test_path),
                circuit_breaker_enabled=True
            )
            
            # Test dead letter queue operations
            dlq = error_handler.dead_letter_queue
            
            # Enqueue a test message
            dlq.enqueue(
                message_id="test_dlq_001",
                operation="test_operation",
                memory_data={"test": "data"},
                error_type=ErrorType.CONNECTION_FAILURE,
                error_message="Test DLQ message",
                retry_delay_seconds=0  # Immediate retry for testing
            )
            
            # Check retry candidates
            candidates = dlq.get_retry_candidates()
            
            # Mark as success
            if candidates:
                dlq.mark_retry_success("test_dlq_001")
            
            success = len(candidates) > 0
            
            return {
                'test': 'dead_letter_queue',
                'status': 'PASS' if success else 'FAIL',
                'details': {
                    'messages_enqueued': 1,
                    'retry_candidates': len(candidates),
                    'dlq_functional': success
                }
            }
            
        except Exception as e:
            return {
                'test': 'dead_letter_queue',
                'status': 'FAIL',
                'error': str(e)
            }
        finally:
            self.cleanup_test_environment()
    
    def test_orchestrator_integration(self) -> Dict[str, Any]:
        """Test orchestrator integration with error handling"""
        print("\n🎭 Testing Orchestrator Integration...")
        
        test_path = self.setup_test_environment()
        
        try:
            # Initialize orchestrator with test configuration
            orchestrator = BiologicalMemoryOrchestrator(
                base_path=str(test_path)
            )
            
            # Test error handler integration
            error_handler_available = hasattr(orchestrator, 'error_handler')
            
            # Test health monitor integration
            health_monitor_available = hasattr(orchestrator, 'health_monitor')
            
            # Test recovery service integration
            recovery_service_available = hasattr(orchestrator, 'recovery_service')
            
            # Test error summary
            if error_handler_available:
                error_summary = orchestrator.error_handler.get_error_summary()
                error_summary_valid = 'overall_status' in error_summary or 'recovery_stats' in error_summary
            else:
                error_summary_valid = False
            
            success = (
                error_handler_available and
                health_monitor_available and
                recovery_service_available
            )
            
            return {
                'test': 'orchestrator_integration',
                'status': 'PASS' if success else 'FAIL',
                'details': {
                    'error_handler_integrated': error_handler_available,
                    'health_monitor_integrated': health_monitor_available,
                    'recovery_service_integrated': recovery_service_available,
                    'error_summary_available': error_summary_valid
                }
            }
            
        except Exception as e:
            return {
                'test': 'orchestrator_integration',
                'status': 'FAIL',
                'error': str(e)
            }
        finally:
            self.cleanup_test_environment()
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all failure scenario tests"""
        print("\n🚀 Running All Failure Scenario Tests...")
        
        test_methods = [
            self.test_error_handler_functionality,
            self.test_health_monitoring,
            self.test_automated_recovery,
            self.test_circuit_breaker_patterns,
            self.test_graceful_degradation,
            self.test_dead_letter_queue,
            self.test_orchestrator_integration
        ]
        
        results = []
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                result = test_method()
                results.append(result)
                
                if result['status'] == 'PASS':
                    passed += 1
                    print(f"  ✅ {result['test']}: PASS")
                else:
                    failed += 1
                    print(f"  ❌ {result['test']}: FAIL")
                    if 'error' in result:
                        print(f"     Error: {result['error']}")
                        
            except Exception as e:
                failed += 1
                error_result = {
                    'test': test_method.__name__,
                    'status': 'FAIL',
                    'error': str(e)
                }
                results.append(error_result)
                print(f"  ❌ {test_method.__name__}: FAIL - {str(e)}")
        
        # Calculate summary
        total_tests = len(test_methods)
        success_rate = (passed / total_tests) * 100
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'success_rate': round(success_rate, 1),
            'test_results': results
        }
        
        print(f"\n{'='*80}")
        print(f"FAILURE SCENARIOS TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"{'='*80}")
        
        # Print detailed results for failed tests
        if failed > 0:
            print(f"\nFAILED TEST DETAILS:")
            for result in results:
                if result['status'] == 'FAIL':
                    print(f"\n❌ {result['test']}:")
                    if 'error' in result:
                        print(f"   Error: {result['error']}")
                    if 'details' in result:
                        print(f"   Details: {json.dumps(result['details'], indent=4)}")
        
        return summary


def main():
    """Run the failure scenarios test suite"""
    
    # Get base path
    base_path = Path(__file__).parent
    
    # Initialize tester
    tester = FailureScenarioTester(str(base_path))
    
    # Run all tests
    try:
        results = tester.run_all_tests()
        
        # Save results to file
        results_file = base_path / "logs" / "failure_scenarios_test_results.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nTest results saved to: {results_file}")
        
        # Exit with appropriate code
        if results['failed'] > 0:
            print("\n⚠️  Some tests failed. Review the results above.")
            sys.exit(1)
        else:
            print("\n🎉 All failure scenario tests passed!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()