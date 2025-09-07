"""
Health Check Service - Production-ready health monitoring
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .error_handling import (
    get_global_error_handler,
)

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""

    service_name: str
    status: ServiceStatus
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    latency_ms: Optional[float] = None


class ComprehensiveHealthMonitor:
    """Comprehensive health monitoring for all services"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.services = {}
        self.last_check_results = {}
        self.error_handler = get_global_error_handler()
        logger.info("Health monitor initialized with comprehensive error handling")

    def register_service(self, name: str, check_func: Callable) -> None:
        """Register a service for health monitoring"""
        self.services[name] = check_func
        logger.debug(f"Registered service: {name}")

    def check_service(self, name: str) -> HealthCheckResult:
        """Check health of a specific service"""
        if name not in self.services:
            return HealthCheckResult(
                service_name=name,
                status=ServiceStatus.UNKNOWN,
                message=f"Service {name} not registered",
                timestamp=datetime.now(),
            )

        try:
            start_time = datetime.now()
            result = self.services[name]()
            latency = (datetime.now() - start_time).total_seconds() * 1000

            return HealthCheckResult(
                service_name=name,
                status=result.get("status", ServiceStatus.HEALTHY),
                message=result.get("message", "OK"),
                timestamp=datetime.now(),
                details=result.get("details"),
                latency_ms=latency,
            )
        except Exception as e:
            logger.error(f"Health check failed for {name}: {e}")
            return HealthCheckResult(
                service_name=name,
                status=ServiceStatus.CRITICAL,
                message=str(e),
                timestamp=datetime.now(),
            )

    def check_all_services(self) -> List[HealthCheckResult]:
        """Check health of all registered services"""
        results = []
        for name in self.services:
            result = self.check_service(name)
            self.last_check_results[name] = result
            results.append(result)
        return results

    def get_overall_status(self) -> ServiceStatus:
        """Get overall system health status"""
        if not self.last_check_results:
            return ServiceStatus.UNKNOWN

        statuses = [r.status for r in self.last_check_results.values()]

        if any(s == ServiceStatus.CRITICAL for s in statuses):
            return ServiceStatus.CRITICAL
        elif any(s == ServiceStatus.DEGRADED for s in statuses):
            return ServiceStatus.DEGRADED
        elif all(s == ServiceStatus.HEALTHY for s in statuses):
            return ServiceStatus.HEALTHY
        else:
            return ServiceStatus.UNKNOWN
