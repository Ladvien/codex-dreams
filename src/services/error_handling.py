"""
Error Handling Service - Comprehensive error management for biological memory system
"""

import json
import logging
import time
import traceback
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories"""

    DATABASE = "database"
    NETWORK = "network"
    LLM = "llm"
    MEMORY = "memory"
    VALIDATION = "validation"
    SECURITY = "security"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class BiologicalMemoryError(Exception):
    """Base exception for biological memory errors"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Dict = None,
    ):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.timestamp = datetime.now()


class BiologicalMemoryErrorHandler:
    """Comprehensive error handler for the biological memory system"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.error_log = []
        self.retry_config = {
            "max_retries": self.config.get("max_retries", 3),
            "base_delay": self.config.get("base_delay", 1.0),
            "max_delay": self.config.get("max_delay", 60.0),
            "exponential_base": self.config.get("exponential_base", 2),
        }
        self.error_handlers = {}
        self._register_default_handlers()
        logger.info("Error handler initialized")

    def _register_default_handlers(self):
        """Register default error handlers"""
        self.register_handler(ErrorCategory.DATABASE, self._handle_database_error)
        self.register_handler(ErrorCategory.NETWORK, self._handle_network_error)
        self.register_handler(ErrorCategory.LLM, self._handle_llm_error)
        self.register_handler(ErrorCategory.TIMEOUT, self._handle_timeout_error)
        self.register_handler(ErrorCategory.SECURITY, self._handle_security_error)

    def register_handler(self, category: ErrorCategory, handler: Callable):
        """Register a custom error handler for a category"""
        self.error_handlers[category] = handler

    def handle_error(self, error: Exception, context: Dict = None) -> Dict[str, Any]:
        """Handle an error with appropriate recovery strategy"""
        # Classify error
        category = self._classify_error(error)
        severity = self._assess_severity(error, category)

        # Create error record
        error_record = {
            "error_type": type(error).__name__,
            "message": str(error),
            "category": category.value,
            "severity": severity.value,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
            "traceback": traceback.format_exc(),
        }

        # Log error
        self.error_log.append(error_record)
        logger.error(f"Error handled: {category.value} - {severity.value}: {error}")

        # Execute handler if available
        if category in self.error_handlers:
            try:
                recovery_result = self.error_handlers[category](error, error_record)
                error_record["recovery_attempted"] = True
                error_record["recovery_result"] = recovery_result
            except Exception as handler_error:
                logger.error(f"Error handler failed: {handler_error}")
                error_record["recovery_attempted"] = False
                error_record["recovery_error"] = str(handler_error)

        return error_record

    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error into category"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        if "database" in error_str or "sql" in error_str or "duckdb" in error_str:
            return ErrorCategory.DATABASE
        elif "timeout" in error_str or "timed out" in error_str:
            return ErrorCategory.TIMEOUT
        elif "connection" in error_str or "network" in error_str:
            return ErrorCategory.NETWORK
        elif "llm" in error_str or "ollama" in error_str:
            return ErrorCategory.LLM
        elif "permission" in error_str or "security" in error_str:
            return ErrorCategory.SECURITY
        elif "memory" in error_str:
            return ErrorCategory.MEMORY
        elif "validation" in error_type or "value" in error_type:
            return ErrorCategory.VALIDATION
        else:
            return ErrorCategory.UNKNOWN

    def _assess_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Assess error severity"""
        # Security errors are always critical
        if category == ErrorCategory.SECURITY:
            return ErrorSeverity.CRITICAL

        # Database connection errors are high severity
        if category == ErrorCategory.DATABASE and "connection" in str(error).lower():
            return ErrorSeverity.HIGH

        # Timeout errors are medium severity
        if category == ErrorCategory.TIMEOUT:
            return ErrorSeverity.MEDIUM

        # Default to medium
        return ErrorSeverity.MEDIUM

    def _handle_database_error(self, error: Exception, record: Dict) -> Dict:
        """Handle database errors"""
        return {"action": "retry_with_backoff", "fallback": "use_cached_data", "max_retries": 3}

    def _handle_network_error(self, error: Exception, record: Dict) -> Dict:
        """Handle network errors"""
        return {
            "action": "retry_with_exponential_backoff",
            "fallback": "offline_mode",
            "max_retries": 5,
        }

    def _handle_llm_error(self, error: Exception, record: Dict) -> Dict:
        """Handle LLM errors"""
        return {
            "action": "use_fallback_model",
            "fallback": "use_cached_embeddings",
            "max_retries": 2,
        }

    def _handle_timeout_error(self, error: Exception, record: Dict) -> Dict:
        """Handle timeout errors"""
        return {"action": "increase_timeout", "fallback": "async_processing", "max_retries": 1}

    def _handle_security_error(self, error: Exception, record: Dict) -> Dict:
        """Handle security errors"""
        logger.critical(f"Security error detected: {error}")
        return {"action": "terminate_operation", "fallback": "alert_admin", "max_retries": 0}

    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Retry function with exponential backoff"""
        last_exception = None

        for attempt in range(self.retry_config["max_retries"]):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.retry_config["max_retries"] - 1:
                    delay = min(
                        self.retry_config["base_delay"]
                        * (self.retry_config["exponential_base"] ** attempt),
                        self.retry_config["max_delay"],
                    )
                    logger.warning(f"Retry {attempt + 1}/{self.retry_config['max_retries']}: {e}")
                    time.sleep(delay)

        raise last_exception

    def safe_execute(self, func: Callable, *args, **kwargs) -> Union[Any, None]:
        """Safely execute function with error handling"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_error(e, {"function": func.__name__, "args": str(args)[:100]})
            return None

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_log:
            return {"total_errors": 0, "categories": {}, "severities": {}}

        stats = {
            "total_errors": len(self.error_log),
            "categories": {},
            "severities": {},
            "recent_errors": self.error_log[-10:],
        }

        for error in self.error_log:
            cat = error["category"]
            sev = error["severity"]
            stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
            stats["severities"][sev] = stats["severities"].get(sev, 0) + 1

        return stats


def with_error_handling(category: ErrorCategory = ErrorCategory.UNKNOWN):
    """Decorator for adding error handling to functions"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error = BiologicalMemoryError(
                    str(e), category=category, details={"function": func.__name__}
                )
                logger.error(f"Error in {func.__name__}: {error}")
                raise error

        return wrapper

    return decorator
