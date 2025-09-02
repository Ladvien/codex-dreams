#!/usr/bin/env python3
"""
Health Monitoring Integration for Biological Parameter Monitoring
STORY-MEM-002: Integration layer between biological parameter monitoring and health checks

This module provides integration between the biological parameter monitoring system
and the existing health check infrastructure, adding biological parameter endpoints
to the health monitoring HTTP interface.
"""

import json
import logging

# Import existing health monitoring components
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Type
from http.server import BaseHTTPRequestHandler

sys.path.append("/Users/ladvien/codex-dreams/biological_memory")
from health_check_service import ComprehensiveHealthMonitor, HealthCheckResult, ServiceStatus

# Import biological parameter monitoring
from .biological_parameter_monitor import get_biological_parameter_monitor


class BiologicalHealthIntegration:
    """
    Integration layer for biological parameter monitoring in health checks
    """

    def __init__(self, health_monitor: ComprehensiveHealthMonitor):
        self.health_monitor = health_monitor
        self.logger = logging.getLogger("BiologicalHealthIntegration")

        # Initialize biological parameter monitor
        self.biological_monitor = None
        try:
            self.biological_monitor = get_biological_parameter_monitor(
                base_path=str(health_monitor.base_path),
                dbt_project_dir=str(health_monitor.base_path),
            )
            self.logger.info("Biological parameter monitoring integrated with health system")
        except Exception as e:
            self.logger.error(f"Failed to initialize biological parameter monitoring: {e}")

    def check_biological_parameters(self) -> HealthCheckResult:
        """Check biological parameter health and compliance"""
        start_time = time.time()
        service_name = "biological_parameters"

        try:
            if not self.biological_monitor:
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.UNKNOWN,
                    response_time_ms=0,
                    timestamp=datetime.now(),
                    details={"error": "Biological parameter monitoring not available"},
                    error_message="Biological parameter monitoring not initialized",
                )

            # Run comprehensive biological parameter monitoring
            report = self.biological_monitor.run_comprehensive_monitoring()
            response_time_ms = int((time.time() - start_time) * 1000)

            # Determine overall status based on parameter health
            status_dist = report.get("status_distribution", {})
            critical_count = status_dist.get("critical", 0)
            warning_count = status_dist.get("warning", 0)
            total_params = report.get("total_parameters", 1)

            if critical_count > 0:
                status = ServiceStatus.CRITICAL
                error_message = f"{critical_count} critical parameter violations"
            elif warning_count > total_params * 0.3:  # More than 30% warnings
                status = ServiceStatus.DEGRADED
                error_message = f"{warning_count} parameter warnings detected"
            elif warning_count > 0:
                status = ServiceStatus.HEALTHY
                error_message = f"{warning_count} minor parameter warnings"
            else:
                status = ServiceStatus.HEALTHY
                error_message = None

            # Extract biological constraint status
            bio_constraints = report.get("biological_constraints", {})
            constraint_failures = [
                name for name, data in bio_constraints.items() if not data.get("status", True)
            ]

            if constraint_failures and status == ServiceStatus.HEALTHY:
                status = ServiceStatus.DEGRADED
                error_message = (
                    f"Biological constraint violations: {', '.join(constraint_failures)}"
                )

            details = {
                "total_parameters": total_params,
                "status_distribution": status_dist,
                "biological_constraints": bio_constraints,
                "active_alerts": report.get("active_alerts", 0),
                "monitoring_time_ms": report.get("monitoring_time_ms", 0),
                "critical_parameters": [
                    name
                    for name, data in report.get("parameters", {}).items()
                    if data.get("status") == "critical"
                ],
                "health_score": self._calculate_parameter_health_score(status_dist, total_params),
            }

            return HealthCheckResult(
                service_name=service_name,
                status=status,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                details=details,
                error_message=error_message,
            )

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Biological parameter health check failed: {str(e)}"
            self.logger.error(error_msg)

            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.CRITICAL,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                details={"monitoring_error": True},
                error_message=error_msg,
            )

    def _calculate_parameter_health_score(
        self, status_dist: Dict[str, int], total_params: int
    ) -> float:
        """Calculate parameter health score (0-100)"""
        if total_params == 0:
            return 0.0

        return (
            status_dist.get("optimal", 0) * 100
            + status_dist.get("acceptable", 0) * 80
            + status_dist.get("warning", 0) * 40
            + status_dist.get("critical", 0) * 0
        ) / total_params

    def get_biological_dashboard_data(self) -> Dict[str, Any]:
        """Get biological parameter dashboard data"""
        if not self.biological_monitor:
            return {
                "error": "Biological parameter monitoring not available",
                "status": "unavailable",
            }

        try:
            return self.biological_monitor.get_monitoring_dashboard_data()
        except Exception as e:
            self.logger.error(f"Failed to get dashboard data: {e}")
            return {"error": str(e), "status": "error"}

    def get_biological_parameters_detailed(self) -> Dict[str, Any]:
        """Get detailed biological parameters data"""
        if not self.biological_monitor:
            return {
                "error": "Biological parameter monitoring not available",
                "status": "unavailable",
            }

        try:
            return self.biological_monitor.run_comprehensive_monitoring()
        except Exception as e:
            self.logger.error(f"Failed to get detailed parameters: {e}")
            return {"error": str(e), "status": "error"}

    def start_biological_monitoring(self) -> None:
        """Start continuous biological parameter monitoring"""
        if self.biological_monitor:
            self.biological_monitor.start_continuous_monitoring()
            self.logger.info("Biological parameter continuous monitoring started")
        else:
            self.logger.warning("Cannot start biological monitoring - not initialized")

    def stop_biological_monitoring(self) -> None:
        """Stop continuous biological parameter monitoring"""
        if self.biological_monitor:
            self.biological_monitor.stop_monitoring()
            self.logger.info("Biological parameter monitoring stopped")


class EnhancedHealthHTTPHandler:
    """
    Enhanced HTTP handler with biological parameter monitoring endpoints
    """

    @staticmethod
    def add_biological_endpoints(
        handler_class: Type[BaseHTTPRequestHandler], biological_integration: BiologicalHealthIntegration
    ) -> Type[BaseHTTPRequestHandler]:
        """Add biological monitoring endpoints to existing HTTP handler"""

        original_do_get = handler_class.do_GET

        def enhanced_do_get(self: BaseHTTPRequestHandler) -> None:
            """Enhanced GET handler with biological endpoints"""
            try:
                if self.path == "/health/biological":
                    self._handle_biological_dashboard()
                elif self.path == "/health/biological/parameters":
                    self._handle_biological_parameters()
                elif self.path == "/health/biological/alerts":
                    self._handle_biological_alerts()
                else:
                    # Call original handler
                    original_do_get(self)
            except Exception as e:
                self._send_error(500, str(e))

        def _handle_biological_dashboard(self: BaseHTTPRequestHandler) -> None:
            """Handle biological parameter dashboard endpoint"""
            dashboard_data = biological_integration.get_biological_dashboard_data()
            self._send_json_response(dashboard_data)

        def _handle_biological_parameters(self: BaseHTTPRequestHandler) -> None:
            """Handle detailed biological parameters endpoint"""
            parameters_data = biological_integration.get_biological_parameters_detailed()
            self._send_json_response(parameters_data)

        def _handle_biological_alerts(self: BaseHTTPRequestHandler) -> None:
            """Handle biological parameter alerts endpoint"""
            if not biological_integration.biological_monitor:
                self._send_error(503, "Biological parameter monitoring not available")
                return

            try:
                alerts_data = {
                    "active_alerts": [
                        {
                            "alert_id": alert.alert_id,
                            "parameter_name": alert.parameter_name,
                            "alert_type": alert.alert_type.value,
                            "severity": alert.severity.value,
                            "message": alert.message,
                            "current_value": alert.current_value,
                            "expected_range": alert.expected_range,
                            "timestamp": alert.timestamp.isoformat(),
                            "biological_impact": alert.biological_impact,
                        }
                        for alert in biological_integration.biological_monitor.active_alerts.values()
                    ],
                    "recent_alerts": [
                        {
                            "alert_id": alert.alert_id,
                            "parameter_name": alert.parameter_name,
                            "alert_type": alert.alert_type.value,
                            "severity": alert.severity.value,
                            "message": alert.message,
                            "timestamp": alert.timestamp.isoformat(),
                            "resolved": alert.resolved,
                        }
                        for alert in list(biological_integration.biological_monitor.alert_history)[
                            -10:
                        ]
                    ],
                }
                self._send_json_response(alerts_data)
            except Exception as e:
                self._send_error(500, f"Failed to get biological alerts: {str(e)}")

        # Replace methods
        handler_class.do_GET = enhanced_do_get
        handler_class._handle_biological_dashboard = _handle_biological_dashboard
        handler_class._handle_biological_parameters = _handle_biological_parameters
        handler_class._handle_biological_alerts = _handle_biological_alerts

        return handler_class


def integrate_biological_monitoring(
    health_monitor: ComprehensiveHealthMonitor,
) -> BiologicalHealthIntegration:
    """
    Integrate biological parameter monitoring with existing health monitoring system
    """
    biological_integration = BiologicalHealthIntegration(health_monitor)

    # Add biological parameter health check to the comprehensive health check
    original_run_check = health_monitor.run_comprehensive_health_check

    def enhanced_run_check() -> Dict[str, Any]:
        """Enhanced health check including biological parameters"""
        health_checks = original_run_check()

        # Add biological parameter check
        biological_check = biological_integration.check_biological_parameters()
        health_checks["biological_parameters"] = biological_check

        # Update health results
        health_monitor.health_results["biological_parameters"] = biological_check
        health_monitor.health_history.append(biological_check)

        # Maintain history size
        if len(health_monitor.health_history) > health_monitor.max_history_size:
            health_monitor.health_history = health_monitor.health_history[
                -health_monitor.max_history_size :
            ]

        return health_checks

    # Replace the method
    health_monitor.run_comprehensive_health_check = enhanced_run_check

    return biological_integration


if __name__ == "__main__":
    """Test the integration"""
    import logging

    logging.basicConfig(level=logging.INFO)

    # This would be used in the main health monitoring system
    print("Biological parameter monitoring integration module ready")
    print("Use integrate_biological_monitoring(health_monitor) to add biological monitoring")
