#!/usr/bin/env python3
"""
BMP-MEDIUM-010: Comprehensive Health Check and Monitoring Service
Production-level health monitoring with circuit breakers and alerting
"""

import json
import logging
import time
import threading
import os
import psutil
import duckdb
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from urllib.parse import urlparse

# Import error handling system
from error_handling import (
    BiologicalMemoryErrorHandler, ErrorType, ErrorEvent, CircuitBreaker,
    SecuritySanitizer
)
from llm_integration_service import get_llm_service


class ServiceStatus(Enum):
    """Service health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Structured health check result"""
    service_name: str
    status: ServiceStatus
    response_time_ms: int
    timestamp: datetime
    details: Dict[str, Any]
    error_message: Optional[str] = None
    last_successful_check: Optional[datetime] = None


@dataclass
class SystemAlert:
    """System alert for monitoring"""
    alert_id: str
    severity: AlertSeverity
    service: str
    message: str
    timestamp: datetime
    resolved: bool = False
    acknowledged: bool = False
    metadata: Dict[str, Any] = None


class PostgreSQLCircuitBreaker:
    """Enhanced circuit breaker specifically for PostgreSQL connections"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 timeout_seconds: int = 60,
                 connection_params: Dict[str, Any] = None):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.connection_params = connection_params or {}
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
        self.logger = logging.getLogger(f'PostgreSQLCircuitBreaker')
        
    def test_connection(self) -> Tuple[bool, str]:
        """Test PostgreSQL connection with circuit breaker protection"""
        with self._lock:
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                    self.logger.info("PostgreSQL circuit breaker moving to HALF_OPEN state")
                else:
                    return False, f"Circuit breaker is OPEN. Service unavailable until {self.last_failure_time + timedelta(seconds=self.timeout_seconds)}"
            
            try:
                start_time = time.time()
                
                # Attempt connection with timeout
                conn = psycopg2.connect(
                    **self.connection_params,
                    connect_timeout=10
                )
                
                # Test query
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                conn.close()
                
                response_time = int((time.time() - start_time) * 1000)
                
                self._on_success()
                return True, f"Connection successful in {response_time}ms"
                
            except Exception as e:
                self._on_failure()
                error_msg = f"PostgreSQL connection failed: {str(e)}"
                self.logger.error(error_msg)
                return False, error_msg
    
    def _should_attempt_reset(self) -> bool:
        return (datetime.now() - self.last_failure_time).total_seconds() >= self.timeout_seconds
    
    def _on_success(self):
        self.failure_count = 0
        if self.state != "CLOSED":
            self.logger.info("PostgreSQL circuit breaker reset to CLOSED state")
        self.state = "CLOSED"
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold and self.state != "OPEN":
            self.state = "OPEN"
            self.logger.error(f"PostgreSQL circuit breaker opened after {self.failure_count} failures")


class ComprehensiveHealthMonitor:
    """
    Production-level health monitoring system with circuit breakers and alerting
    """
    
    def __init__(self,
                 base_path: str,
                 error_handler: Optional[BiologicalMemoryErrorHandler] = None,
                 enable_http_endpoints: bool = True,
                 http_port: int = 8080,
                 alert_webhook_url: Optional[str] = None):
        
        self.base_path = Path(base_path)
        self.error_handler = error_handler
        self.enable_http_endpoints = enable_http_endpoints
        self.http_port = http_port
        self.alert_webhook_url = alert_webhook_url
        
        # Set up logging
        self.logger = logging.getLogger('HealthMonitor')
        self._setup_logging()
        
        # Health check results storage
        self.health_results: Dict[str, HealthCheckResult] = {}
        self.health_history: List[HealthCheckResult] = []
        self.max_history_size = 1000
        
        # Alert system
        self.active_alerts: Dict[str, SystemAlert] = {}
        self.alert_history: List[SystemAlert] = []
        self.max_alert_history = 500
        
        # Circuit breakers for external services
        self.circuit_breakers: Dict[str, Any] = {}
        self._setup_circuit_breakers()
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitoring_interval = 30  # seconds
        
        # HTTP server for health endpoints
        self.http_server = None
        self.http_thread = None
        
        self.logger.info(f"Health monitor initialized for {base_path}")
    
    def _setup_logging(self):
        """Setup health monitoring logging"""
        log_dir = self.base_path / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Health monitoring log
        health_handler = logging.FileHandler(log_dir / 'health_monitoring.log')
        health_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(health_handler)
        self.logger.setLevel(logging.INFO)
        
        # Alerts log (structured JSON)
        alerts_handler = logging.FileHandler(log_dir / 'alerts.jsonl')
        alerts_handler.setFormatter(logging.Formatter('%(message)s'))
        
        alerts_logger = logging.getLogger('AlertSystem')
        alerts_logger.addHandler(alerts_handler)
        alerts_logger.setLevel(logging.INFO)
        
    def _setup_circuit_breakers(self):
        """Setup circuit breakers for all external services"""
        
        # PostgreSQL circuit breaker
        postgres_params = {
            'host': '192.168.1.104',
            'port': 5432,
            'database': 'codex_db',
            'user': 'codex_user',
            'password': 'MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a'
        }
        
        self.circuit_breakers['postgresql'] = PostgreSQLCircuitBreaker(
            failure_threshold=5,
            timeout_seconds=60,
            connection_params=postgres_params
        )
        
        # Ollama circuit breaker (enhanced)
        self.circuit_breakers['ollama'] = CircuitBreaker(
            failure_threshold=3,
            timeout_seconds=30,
            expected_exception=Exception
        )
        
        # DuckDB circuit breaker (enhanced)
        self.circuit_breakers['duckdb'] = CircuitBreaker(
            failure_threshold=3,
            timeout_seconds=20,
            expected_exception=Exception
        )
    
    def check_postgresql_health(self) -> HealthCheckResult:
        """Check PostgreSQL service health with circuit breaker protection"""
        start_time = time.time()
        service_name = "postgresql"
        
        try:
            circuit_breaker = self.circuit_breakers['postgresql']
            success, message = circuit_breaker.test_connection()
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if success:
                status = ServiceStatus.HEALTHY
                details = {
                    'connection_state': circuit_breaker.state,
                    'failure_count': circuit_breaker.failure_count,
                    'host': '192.168.1.104',
                    'database': 'codex_db'
                }
                error_message = None
            else:
                status = ServiceStatus.CRITICAL if circuit_breaker.state == "OPEN" else ServiceStatus.UNHEALTHY
                details = {
                    'connection_state': circuit_breaker.state,
                    'failure_count': circuit_breaker.failure_count,
                    'last_failure': circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None
                }
                error_message = message
            
            return HealthCheckResult(
                service_name=service_name,
                status=status,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                details=details,
                error_message=error_message
            )
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"PostgreSQL health check failed: {str(e)}"
            self.logger.error(error_msg)
            
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.CRITICAL,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                details={'circuit_breaker_error': True},
                error_message=error_msg
            )
    
    def check_duckdb_health(self) -> HealthCheckResult:
        """Check DuckDB service health"""
        start_time = time.time()
        service_name = "duckdb"
        
        try:
            # Test connection to memory database
            memory_db_path = self.base_path / "dbs" / "memory.duckdb"
            
            with duckdb.connect(str(memory_db_path)) as conn:
                # Test basic operations
                result = conn.execute("SELECT 1 as test").fetchone()
                
                # Check table existence
                tables = conn.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'main'
                """).fetchall()
                
                response_time_ms = int((time.time() - start_time) * 1000)
                
                status = ServiceStatus.HEALTHY
                details = {
                    'database_path': str(memory_db_path),
                    'table_count': len(tables),
                    'test_query_result': result[0] if result else None,
                    'database_exists': memory_db_path.exists()
                }
                
                return HealthCheckResult(
                    service_name=service_name,
                    status=status,
                    response_time_ms=response_time_ms,
                    timestamp=datetime.now(),
                    details=details
                )
                
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"DuckDB health check failed: {str(e)}"
            self.logger.error(error_msg)
            
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.CRITICAL,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                details={'database_path': str(memory_db_path)},
                error_message=error_msg
            )
    
    def check_ollama_health(self) -> HealthCheckResult:
        """Check Ollama LLM service health"""
        start_time = time.time()
        service_name = "ollama"
        
        try:
            llm_service = get_llm_service()
            
            if not llm_service:
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.UNKNOWN,
                    response_time_ms=0,
                    timestamp=datetime.now(),
                    details={},
                    error_message="LLM service not initialized"
                )
            
            # Get health check from LLM service
            health_data = llm_service.health_check()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if health_data.get('status') == 'healthy':
                status = ServiceStatus.HEALTHY
                error_message = None
            else:
                status = ServiceStatus.UNHEALTHY
                error_message = health_data.get('error', 'Ollama service unhealthy')
            
            return HealthCheckResult(
                service_name=service_name,
                status=status,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                details=health_data,
                error_message=error_message
            )
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Ollama health check failed: {str(e)}"
            self.logger.error(error_msg)
            
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.CRITICAL,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                details={},
                error_message=error_msg
            )
    
    def check_system_resources(self) -> HealthCheckResult:
        """Check system resource health"""
        start_time = time.time()
        service_name = "system_resources"
        
        try:
            # Get system metrics
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(str(self.base_path))
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Load averages (Unix-like systems)
            try:
                load_avg = os.getloadavg()
            except (AttributeError, OSError):
                load_avg = [0, 0, 0]
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Determine status based on thresholds
            status = ServiceStatus.HEALTHY
            warnings = []
            
            if memory.percent > 90:
                status = ServiceStatus.CRITICAL
                warnings.append(f"Memory usage critical: {memory.percent:.1f}%")
            elif memory.percent > 80:
                status = ServiceStatus.DEGRADED
                warnings.append(f"Memory usage high: {memory.percent:.1f}%")
            
            disk_usage_percent = (disk.total - disk.free) / disk.total * 100
            if disk_usage_percent > 95:
                status = ServiceStatus.CRITICAL
                warnings.append(f"Disk usage critical: {disk_usage_percent:.1f}%")
            elif disk_usage_percent > 85:
                if status == ServiceStatus.HEALTHY:
                    status = ServiceStatus.DEGRADED
                warnings.append(f"Disk usage high: {disk_usage_percent:.1f}%")
            
            if cpu_percent > 95:
                status = ServiceStatus.CRITICAL
                warnings.append(f"CPU usage critical: {cpu_percent:.1f}%")
            elif cpu_percent > 80:
                if status == ServiceStatus.HEALTHY:
                    status = ServiceStatus.DEGRADED
                warnings.append(f"CPU usage high: {cpu_percent:.1f}%")
            
            details = {
                'memory': {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'used_percent': memory.percent
                },
                'disk': {
                    'total_gb': round(disk.total / (1024**3), 2),
                    'free_gb': round(disk.free / (1024**3), 2),
                    'used_percent': round(disk_usage_percent, 1)
                },
                'cpu': {
                    'usage_percent': cpu_percent,
                    'load_average': load_avg
                },
                'warnings': warnings
            }
            
            return HealthCheckResult(
                service_name=service_name,
                status=status,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                details=details,
                error_message="; ".join(warnings) if warnings else None
            )
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"System resource check failed: {str(e)}"
            self.logger.error(error_msg)
            
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNKNOWN,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                details={},
                error_message=error_msg
            )
    
    def run_comprehensive_health_check(self) -> Dict[str, HealthCheckResult]:
        """Run health checks on all critical services"""
        health_checks = {
            'postgresql': self.check_postgresql_health(),
            'duckdb': self.check_duckdb_health(),
            'ollama': self.check_ollama_health(),
            'system_resources': self.check_system_resources()
        }
        
        # Update health results
        self.health_results = health_checks
        
        # Add to history
        for result in health_checks.values():
            self.health_history.append(result)
        
        # Maintain history size
        if len(self.health_history) > self.max_history_size:
            self.health_history = self.health_history[-self.max_history_size:]
        
        # Check for alerting conditions
        self._process_health_alerts(health_checks)
        
        return health_checks
    
    def _process_health_alerts(self, health_results: Dict[str, HealthCheckResult]):
        """Process health results and generate alerts"""
        current_time = datetime.now()
        
        for service_name, result in health_results.items():
            alert_id = f"health_{service_name}"
            
            # Check if we should create or resolve alerts
            if result.status in [ServiceStatus.UNHEALTHY, ServiceStatus.CRITICAL]:
                if alert_id not in self.active_alerts:
                    # Create new alert
                    severity = AlertSeverity.CRITICAL if result.status == ServiceStatus.CRITICAL else AlertSeverity.ERROR
                    
                    alert = SystemAlert(
                        alert_id=alert_id,
                        severity=severity,
                        service=service_name,
                        message=result.error_message or f"{service_name} is {result.status.value}",
                        timestamp=current_time,
                        metadata={
                            'response_time_ms': result.response_time_ms,
                            'details': result.details
                        }
                    )
                    
                    self.active_alerts[alert_id] = alert
                    self._send_alert(alert)
                    
            else:
                # Service is healthy, resolve any active alerts
                if alert_id in self.active_alerts:
                    alert = self.active_alerts[alert_id]
                    alert.resolved = True
                    
                    # Move to history
                    self.alert_history.append(alert)
                    del self.active_alerts[alert_id]
                    
                    # Send resolution notification
                    self._send_alert_resolution(alert, result)
    
    def _send_alert(self, alert: SystemAlert):
        """Send alert notification"""
        self.logger.error(f"ALERT: {alert.service} - {alert.message}")
        
        # Log structured alert
        alerts_logger = logging.getLogger('AlertSystem')
        alert_data = asdict(alert)
        alert_data['timestamp'] = alert.timestamp.isoformat()
        alerts_logger.info(json.dumps(alert_data))
        
        # Send webhook if configured
        if self.alert_webhook_url:
            try:
                payload = {
                    'alert_type': 'health_check',
                    'service': alert.service,
                    'severity': alert.severity.value,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'metadata': alert.metadata
                }
                
                response = requests.post(
                    self.alert_webhook_url,
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
                
            except Exception as e:
                self.logger.error(f"Failed to send webhook alert: {e}")
    
    def _send_alert_resolution(self, alert: SystemAlert, health_result: HealthCheckResult):
        """Send alert resolution notification"""
        self.logger.info(f"RESOLVED: {alert.service} - Service recovered")
        
        # Log structured resolution
        alerts_logger = logging.getLogger('AlertSystem')
        resolution_data = {
            'alert_id': alert.alert_id,
            'service': alert.service,
            'status': 'resolved',
            'resolved_at': datetime.now().isoformat(),
            'recovery_time_seconds': (datetime.now() - alert.timestamp).total_seconds(),
            'current_status': health_result.status.value
        }
        alerts_logger.info(json.dumps(resolution_data))
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        overall_status = ServiceStatus.HEALTHY
        unhealthy_services = []
        
        for service_name, result in self.health_results.items():
            if result.status in [ServiceStatus.CRITICAL, ServiceStatus.UNHEALTHY]:
                overall_status = ServiceStatus.CRITICAL if result.status == ServiceStatus.CRITICAL else ServiceStatus.UNHEALTHY
                unhealthy_services.append({
                    'service': service_name,
                    'status': result.status.value,
                    'error': result.error_message
                })
        
        return {
            'overall_status': overall_status.value,
            'timestamp': datetime.now().isoformat(),
            'services': {name: {
                'status': result.status.value,
                'response_time_ms': result.response_time_ms,
                'last_check': result.timestamp.isoformat()
            } for name, result in self.health_results.items()},
            'active_alerts': len(self.active_alerts),
            'unhealthy_services': unhealthy_services,
            'uptime_checks': len(self.health_history)
        }
    
    def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        if self.enable_http_endpoints:
            self._start_http_server()
        
        self.logger.info(f"Health monitoring started (interval: {self.monitoring_interval}s)")
    
    def stop_monitoring(self):
        """Stop continuous health monitoring"""
        self.monitoring_active = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        if self.http_server:
            self.http_server.shutdown()
        
        self.logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self):
        """Continuous monitoring loop"""
        while self.monitoring_active:
            try:
                self.run_comprehensive_health_check()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Short pause on error
    
    def _start_http_server(self):
        """Start HTTP server for health endpoints"""
        handler = HealthHTTPHandler
        handler.health_monitor = self
        
        self.http_server = HTTPServer(('localhost', self.http_port), handler)
        self.http_thread = threading.Thread(target=self.http_server.serve_forever)
        self.http_thread.daemon = True
        self.http_thread.start()
        
        self.logger.info(f"Health check HTTP server started on port {self.http_port}")


class HealthHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoints"""
    health_monitor: ComprehensiveHealthMonitor = None
    
    def do_GET(self):
        """Handle GET requests for health endpoints"""
        try:
            if self.path == '/health':
                self._handle_health_summary()
            elif self.path == '/health/detailed':
                self._handle_detailed_health()
            elif self.path == '/health/alerts':
                self._handle_alerts()
            elif self.path.startswith('/health/'):
                service_name = self.path.split('/')[-1]
                self._handle_service_health(service_name)
            else:
                self._send_404()
        except Exception as e:
            self._send_error(500, str(e))
    
    def _handle_health_summary(self):
        """Handle /health endpoint"""
        summary = self.health_monitor.get_health_summary()
        self._send_json_response(summary)
    
    def _handle_detailed_health(self):
        """Handle /health/detailed endpoint"""
        health_results = {
            name: asdict(result)
            for name, result in self.health_monitor.health_results.items()
        }
        
        # Convert datetime objects to ISO strings
        for result in health_results.values():
            result['timestamp'] = result['timestamp'].isoformat() if isinstance(result['timestamp'], datetime) else result['timestamp']
            if result.get('last_successful_check'):
                result['last_successful_check'] = result['last_successful_check'].isoformat()
        
        self._send_json_response(health_results)
    
    def _handle_alerts(self):
        """Handle /health/alerts endpoint"""
        alerts_data = {
            'active_alerts': {
                alert_id: asdict(alert) 
                for alert_id, alert in self.health_monitor.active_alerts.items()
            },
            'recent_alerts': [
                asdict(alert) for alert in self.health_monitor.alert_history[-10:]
            ]
        }
        
        # Convert datetime objects
        for alert_data in alerts_data['active_alerts'].values():
            alert_data['timestamp'] = alert_data['timestamp'].isoformat()
        
        for alert_data in alerts_data['recent_alerts']:
            alert_data['timestamp'] = alert_data['timestamp'].isoformat()
        
        self._send_json_response(alerts_data)
    
    def _handle_service_health(self, service_name: str):
        """Handle /health/{service} endpoint"""
        if service_name not in self.health_monitor.health_results:
            self._send_404()
            return
        
        result = self.health_monitor.health_results[service_name]
        result_data = asdict(result)
        result_data['timestamp'] = result_data['timestamp'].isoformat()
        if result_data.get('last_successful_check'):
            result_data['last_successful_check'] = result_data['last_successful_check'].isoformat()
        
        self._send_json_response(result_data)
    
    def _send_json_response(self, data: Dict[str, Any], status_code: int = 200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        json_data = json.dumps(data, indent=2, default=str)
        self.wfile.write(json_data.encode())
    
    def _send_404(self):
        """Send 404 response"""
        self.send_response(404)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        error_data = {'error': 'Not found', 'path': self.path}
        self.wfile.write(json.dumps(error_data).encode())
    
    def _send_error(self, status_code: int, message: str):
        """Send error response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        error_data = {'error': message, 'status_code': status_code}
        self.wfile.write(json.dumps(error_data).encode())
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging"""
        pass


# Global health monitor instance
_health_monitor: Optional[ComprehensiveHealthMonitor] = None


def initialize_health_monitor(
    base_path: str,
    error_handler: Optional[BiologicalMemoryErrorHandler] = None,
    enable_http_endpoints: bool = True,
    http_port: int = 8080,
    alert_webhook_url: Optional[str] = None
) -> ComprehensiveHealthMonitor:
    """Initialize global health monitor instance"""
    global _health_monitor
    
    _health_monitor = ComprehensiveHealthMonitor(
        base_path=base_path,
        error_handler=error_handler,
        enable_http_endpoints=enable_http_endpoints,
        http_port=http_port,
        alert_webhook_url=alert_webhook_url
    )
    
    return _health_monitor


def get_health_monitor() -> Optional[ComprehensiveHealthMonitor]:
    """Get global health monitor instance"""
    return _health_monitor


if __name__ == "__main__":
    # Example usage and testing
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize health monitor
    monitor = initialize_health_monitor(
        base_path="/Users/ladvien/codex-dreams/biological_memory",
        enable_http_endpoints=True,
        http_port=8080
    )
    
    # Run single health check
    print("Running comprehensive health check...")
    results = monitor.run_comprehensive_health_check()
    
    for service_name, result in results.items():
        print(f"\n{service_name.upper()}:")
        print(f"  Status: {result.status.value}")
        print(f"  Response Time: {result.response_time_ms}ms")
        if result.error_message:
            print(f"  Error: {result.error_message}")
    
    # Get health summary
    print(f"\nHealth Summary:")
    summary = monitor.get_health_summary()
    print(json.dumps(summary, indent=2, default=str))
    
    # Start continuous monitoring (uncomment for production)
    # monitor.start_monitoring()
    # print(f"\nHealth monitoring started on http://localhost:8080/health")
    # 
    # try:
    #     # Keep running
    #     while True:
    #         time.sleep(60)
    # except KeyboardInterrupt:
    #     print("\nShutting down health monitor...")
    #     monitor.stop_monitoring()