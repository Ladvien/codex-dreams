"""
Biological Parameter Monitoring Package
STORY-MEM-002: Real-time biological parameter monitoring and runtime optimization

This package provides comprehensive monitoring of biological parameters
used in the CODEX DREAMS memory system, with neuroscience-validated ranges
and performance optimization capabilities.
"""

from .biological_parameter_monitor import (
    BiologicalParameterMonitor,
    BiologicalParameter,
    ParameterStatus,
    AlertType,
    ParameterAlert,
    get_biological_parameter_monitor
)

from .health_integration import (
    BiologicalHealthIntegration,
    EnhancedHealthHTTPHandler,
    integrate_biological_monitoring
)

__all__ = [
    'BiologicalParameterMonitor',
    'BiologicalParameter',
    'ParameterStatus',
    'AlertType',
    'ParameterAlert',
    'get_biological_parameter_monitor',
    'BiologicalHealthIntegration',
    'EnhancedHealthHTTPHandler',
    'integrate_biological_monitoring'
]

# Package metadata
__version__ = '1.0.0'
__description__ = 'Biological parameter monitoring for CODEX DREAMS memory system'
__author__ = 'CODEX DREAMS Team'