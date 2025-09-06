"""
Error Handling Service - Comprehensive error management for biological memory system
"""

import json
import logging
import os
import pickle
import sqlite3
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, Generator, List, Optional, Union

import psycopg2
import requests

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for biological memory system"""

    DATABASE = "database"
    NETWORK = "network"
    LLM = "llm"
    EMBEDDING = "embedding"
    MEMORY = "memory"
    VALIDATION = "validation"
    SECURITY = "security"
    TIMEOUT = "timeout"
    FILE_IO = "file_io"
    CACHE = "cache"
    BIOLOGICAL_TIMING = "biological_timing"
    WRITEBACK = "writeback"
    CONSOLIDATION = "consolidation"
    UNKNOWN = "unknown"


class BiologicalMemoryError(Exception):
    """Base exception for biological memory system errors"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Dict = None,
        cause: Exception = None,
        retry_suggested: bool = True,
    ):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.cause = cause
        self.retry_suggested = retry_suggested
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/storage"""
        return {
            "message": str(self),
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
            "retry_suggested": self.retry_suggested,
            "timestamp": self.timestamp.isoformat(),
        }


class DatabaseError(BiologicalMemoryError):
    """Database-specific errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.DATABASE, **kwargs)


class NetworkError(BiologicalMemoryError):
    """Network-specific errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.NETWORK, **kwargs)


class LLMError(BiologicalMemoryError):
    """LLM service errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.LLM, **kwargs)


class EmbeddingError(BiologicalMemoryError):
    """Embedding generation errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.EMBEDDING, **kwargs)


class TimeoutError(BiologicalMemoryError):
    """Timeout errors with biological timing context"""

    def __init__(self, message: str, biological_context: str = None, **kwargs):
        details = kwargs.get("details", {})
        if biological_context:
            details["biological_context"] = biological_context
        super().__init__(message, category=ErrorCategory.TIMEOUT, details=details, **kwargs)


class FileIOError(BiologicalMemoryError):
    """File I/O errors"""

    def __init__(self, message: str, file_path: str = None, **kwargs):
        details = kwargs.get("details", {})
        if file_path:
            details["file_path"] = file_path
        super().__init__(message, category=ErrorCategory.FILE_IO, details=details, **kwargs)


class CacheError(BiologicalMemoryError):
    """Cache-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.CACHE, **kwargs)


class WritebackError(BiologicalMemoryError):
    """Memory writeback errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.WRITEBACK, **kwargs)


class ConsolidationError(BiologicalMemoryError):
    """Memory consolidation errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.CONSOLIDATION, **kwargs)


class ValidationError(BiologicalMemoryError):
    """Data validation errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, category=ErrorCategory.VALIDATION, retry_suggested=False, **kwargs
        )


class BiologicalMemoryErrorHandler:
    """Comprehensive error handler for the biological memory system"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.error_log = []
        self._error_log_lock = Lock()
        self.retry_config = {
            "max_retries": self.config.get("max_retries", 3),
            "base_delay": self.config.get("base_delay", 1.0),
            "max_delay": self.config.get("max_delay", 60.0),
            "exponential_base": self.config.get("exponential_base", 2),
            # Biological timing constraints
            "working_memory_timeout": self.config.get("working_memory_timeout", 5.0),  # 5 minutes
            "consolidation_timeout": self.config.get("consolidation_timeout", 300.0),  # 5 minutes
            "llm_timeout": self.config.get("llm_timeout", 30.0),  # 30 seconds
            "database_timeout": self.config.get("database_timeout", 60.0),  # 1 minute
        }
        self.error_handlers = {}
        self._setup_structured_logging()
        self._register_default_handlers()
        self._initialize_persistent_storage()
        logger.info("BiologicalMemoryErrorHandler initialized with comprehensive error handling")

    def _setup_structured_logging(self):
        """Setup structured logging with appropriate levels"""
        # Configure root logger if not already configured
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('biological_memory_errors.log', mode='a')
            ]
        )
        
        # Ensure our logger uses the configuration
        global logger
        logger.setLevel(self.config.get('log_level', logging.INFO))
    
    def _initialize_persistent_storage(self):
        """Initialize persistent error storage"""
        self.error_db_path = self.config.get('error_db_path', 'biological_memory_errors.db')
        try:
            with sqlite3.connect(self.error_db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS error_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        category TEXT,
                        severity TEXT,
                        message TEXT,
                        details TEXT,
                        traceback TEXT,
                        resolved BOOLEAN DEFAULT FALSE,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not initialize error database: {e}")
    
    def _register_default_handlers(self):
        """Register default error handlers with biological context"""
        self.register_handler(ErrorCategory.DATABASE, self._handle_database_error)
        self.register_handler(ErrorCategory.NETWORK, self._handle_network_error)
        self.register_handler(ErrorCategory.LLM, self._handle_llm_error)
        self.register_handler(ErrorCategory.EMBEDDING, self._handle_embedding_error)
        self.register_handler(ErrorCategory.TIMEOUT, self._handle_timeout_error)
        self.register_handler(ErrorCategory.SECURITY, self._handle_security_error)
        self.register_handler(ErrorCategory.FILE_IO, self._handle_file_io_error)
        self.register_handler(ErrorCategory.CACHE, self._handle_cache_error)
        self.register_handler(ErrorCategory.WRITEBACK, self._handle_writeback_error)
        self.register_handler(ErrorCategory.CONSOLIDATION, self._handle_consolidation_error)
        self.register_handler(ErrorCategory.BIOLOGICAL_TIMING, self._handle_biological_timing_error)

    def register_handler(self, category: ErrorCategory, handler: Callable):
        """Register a custom error handler for a category"""
        self.error_handlers[category] = handler

    def handle_error(self, error: Exception, context: Dict = None) -> Dict[str, Any]:
        """Handle an error with comprehensive recovery strategy and persistent logging"""
        # Classify error
        category = self._classify_error(error)
        severity = self._assess_severity(error, category)

        # Create comprehensive error record
        error_record = {
            "error_id": f"{category.value}_{int(time.time())}_{id(error)}",
            "error_type": type(error).__name__,
            "message": str(error),
            "category": category.value,
            "severity": severity.value,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
            "traceback": traceback.format_exc(),
            "system_state": self._capture_system_state(),
            "biological_context": self._extract_biological_context(context or {}),
        }

        # Thread-safe logging
        with self._error_log_lock:
            self.error_log.append(error_record)
            self._persist_error(error_record)

        # Structured logging based on severity
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR: {category.value} - {error}", 
                           extra={'error_id': error_record['error_id']})
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH SEVERITY: {category.value} - {error}", 
                        extra={'error_id': error_record['error_id']})
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM SEVERITY: {category.value} - {error}", 
                          extra={'error_id': error_record['error_id']})
        else:
            logger.info(f"LOW SEVERITY: {category.value} - {error}", 
                       extra={'error_id': error_record['error_id']})

        # Execute handler if available
        if category in self.error_handlers:
            try:
                recovery_result = self.error_handlers[category](error, error_record)
                error_record["recovery_attempted"] = True
                error_record["recovery_result"] = recovery_result
            except Exception as handler_error:
                logger.error(f"Error handler failed for {category.value}: {handler_error}")
                error_record["recovery_attempted"] = False
                error_record["recovery_error"] = str(handler_error)
        else:
            error_record["recovery_attempted"] = False
            error_record["recovery_result"] = {"action": "no_handler", "fallback": "log_only"}

        return error_record

    def _capture_system_state(self) -> Dict[str, Any]:
        """Capture current system state for error analysis"""
        try:
            import psutil
            return {
                "memory_usage": psutil.virtual_memory()._asdict(),
                "cpu_usage": psutil.cpu_percent(interval=0.1),
                "disk_usage": psutil.disk_usage('/')._asdict(),
                "process_count": len(psutil.pids()),
            }
        except ImportError:
            return {
                "memory_usage": "psutil not available",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error_capturing_state": str(e)}
    
    def _extract_biological_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract biological memory system context from error context"""
        bio_context = {}
        
        # Memory stage context
        if 'memory_stage' in context:
            bio_context['memory_stage'] = context['memory_stage']
        if 'consolidation_phase' in context:
            bio_context['consolidation_phase'] = context['consolidation_phase']
        if 'working_memory_capacity' in context:
            bio_context['working_memory_capacity'] = context['working_memory_capacity']
            
        # Timing context
        if 'biological_rhythm' in context:
            bio_context['biological_rhythm'] = context['biological_rhythm']
        if 'sleep_phase' in context:
            bio_context['sleep_phase'] = context['sleep_phase']
            
        # Operation context
        if 'operation_type' in context:
            bio_context['operation_type'] = context['operation_type']
            
        return bio_context
    
    def _persist_error(self, error_record: Dict[str, Any]):
        """Persist error to database for analysis"""
        try:
            with sqlite3.connect(self.error_db_path) as conn:
                conn.execute("""
                    INSERT INTO error_log (timestamp, category, severity, message, details, traceback)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    error_record['timestamp'],
                    error_record['category'], 
                    error_record['severity'],
                    error_record['message'],
                    json.dumps(error_record.get('details', {})),
                    error_record.get('traceback', '')
                ))
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not persist error to database: {e}")
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error into biological memory system category"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Check if it's already a BiologicalMemoryError with category
        if isinstance(error, BiologicalMemoryError):
            return error.category

        # Database errors
        if any(term in error_str for term in ['database', 'sql', 'duckdb', 'postgres', 'psycopg2']):
            return ErrorCategory.DATABASE
        elif any(term in error_str for term in ['connection', 'network', 'host']):
            return ErrorCategory.NETWORK
        elif 'timeout' in error_str or 'timed out' in error_str:
            return ErrorCategory.TIMEOUT
        elif any(term in error_str for term in ['llm', 'ollama', 'generate', 'prompt']):
            return ErrorCategory.LLM
        elif any(term in error_str for term in ['embedding', 'vector', 'similarity']):
            return ErrorCategory.EMBEDDING
        elif any(term in error_str for term in ['file', 'directory', 'permission', 'path', 'io']):
            return ErrorCategory.FILE_IO
        elif any(term in error_str for term in ['cache', 'pickle', 'redis']):
            return ErrorCategory.CACHE
        elif any(term in error_str for term in ['writeback', 'transfer', 'sync']):
            return ErrorCategory.WRITEBACK
        elif any(term in error_str for term in ['consolidation', 'hebbian', 'replay']):
            return ErrorCategory.CONSOLIDATION
        elif any(term in error_str for term in ['security', 'permission', 'unauthorized', 'auth']):
            return ErrorCategory.SECURITY
        elif any(term in error_str for term in ['working_memory', 'sleep', 'rhythm', 'biological']):
            return ErrorCategory.BIOLOGICAL_TIMING
        elif any(term in error_type for term in ['validation', 'value', 'type']):
            return ErrorCategory.VALIDATION
        elif 'memory' in error_str:
            return ErrorCategory.MEMORY
        else:
            return ErrorCategory.UNKNOWN

    def _assess_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Assess error severity with biological memory system context"""
        error_str = str(error).lower()
        
        # Already classified BiologicalMemoryError
        if isinstance(error, BiologicalMemoryError):
            return error.severity
        
        # Critical severity conditions
        if category == ErrorCategory.SECURITY:
            return ErrorSeverity.CRITICAL
        elif category == ErrorCategory.DATABASE and any(term in error_str for term in ['corruption', 'constraint', 'integrity']):
            return ErrorSeverity.CRITICAL
        elif category == ErrorCategory.CONSOLIDATION and 'memory_loss' in error_str:
            return ErrorSeverity.CRITICAL
        
        # High severity conditions
        elif category == ErrorCategory.DATABASE and any(term in error_str for term in ['connection', 'authentication']):
            return ErrorSeverity.HIGH
        elif category == ErrorCategory.WRITEBACK and 'data_loss' in error_str:
            return ErrorSeverity.HIGH
        elif category == ErrorCategory.BIOLOGICAL_TIMING and any(term in error_str for term in ['sleep_disruption', 'rhythm_failure']):
            return ErrorSeverity.HIGH
        elif category == ErrorCategory.LLM and 'service_down' in error_str:
            return ErrorSeverity.HIGH
        
        # Medium severity (default for most operational errors)
        elif category in [ErrorCategory.TIMEOUT, ErrorCategory.NETWORK, ErrorCategory.CACHE]:
            return ErrorSeverity.MEDIUM
        elif category == ErrorCategory.EMBEDDING and 'generation_failed' in error_str:
            return ErrorSeverity.MEDIUM
        elif category == ErrorCategory.FILE_IO and 'permission' not in error_str:
            return ErrorSeverity.MEDIUM
        
        # Low severity (recoverable errors)
        elif category == ErrorCategory.VALIDATION:
            return ErrorSeverity.LOW
        elif 'retry' in error_str or 'temporary' in error_str:
            return ErrorSeverity.LOW
        
        # Default to medium
        return ErrorSeverity.MEDIUM

    def _handle_database_error(self, error: Exception, record: Dict) -> Dict:
        """Handle database errors with biological memory context"""
        error_str = str(error).lower()
        
        if 'connection' in error_str or 'network' in error_str:
            return {
                "action": "retry_with_exponential_backoff",
                "fallback": "use_cached_data",
                "max_retries": 5,
                "initial_delay": 2.0,
                "biological_note": "Connection failures may disrupt memory consolidation"
            }
        elif 'timeout' in error_str:
            return {
                "action": "increase_timeout_and_retry",
                "fallback": "async_processing",
                "max_retries": 3,
                "timeout_multiplier": 1.5,
                "biological_note": "Respect biological timing constraints during retry"
            }
        elif 'lock' in error_str or 'deadlock' in error_str:
            return {
                "action": "retry_with_jitter",
                "fallback": "defer_to_next_cycle",
                "max_retries": 10,
                "jitter_range": (0.1, 2.0),
                "biological_note": "Database contention during memory writeback"
            }
        else:
            return {
                "action": "retry_with_backoff",
                "fallback": "use_cached_data",
                "max_retries": 3,
                "biological_note": "General database error during memory processing"
            }

    def _handle_network_error(self, error: Exception, record: Dict) -> Dict:
        """Handle network errors with graceful degradation"""
        return {
            "action": "retry_with_exponential_backoff",
            "fallback": "offline_mode",
            "max_retries": 5,
            "base_delay": 1.0,
            "max_delay": 60.0,
            "circuit_breaker": True,
            "biological_note": "Network issues may affect LLM processing and embedding generation"
        }

    def _handle_llm_error(self, error: Exception, record: Dict) -> Dict:
        """Handle LLM service errors with intelligent fallbacks"""
        error_str = str(error).lower()
        
        if 'timeout' in error_str:
            return {
                "action": "increase_timeout_and_retry",
                "fallback": "use_cached_responses",
                "max_retries": 2,
                "timeout_increase": 1.5,
                "biological_note": "LLM timeout may affect memory enrichment"
            }
        elif 'model' in error_str and 'not found' in error_str:
            return {
                "action": "use_fallback_model",
                "fallback": "skip_llm_processing",
                "max_retries": 1,
                "fallback_model": "llama2:7b",
                "biological_note": "Model unavailable, using simpler processing"
            }
        elif 'service unavailable' in error_str or '503' in error_str:
            return {
                "action": "circuit_breaker_pattern",
                "fallback": "use_cached_responses",
                "max_retries": 3,
                "circuit_timeout": 300,  # 5 minutes
                "biological_note": "LLM service down, using cached data to maintain memory flow"
            }
        else:
            return {
                "action": "retry_with_backoff",
                "fallback": "use_cached_embeddings",
                "max_retries": 2,
                "biological_note": "General LLM error during memory processing"
            }

    def _handle_timeout_error(self, error: Exception, record: Dict) -> Dict:
        """Handle timeout errors with biological timing awareness"""
        context = record.get('biological_context', {})
        
        # Determine biological context for timeout handling
        if context.get('memory_stage') == 'working_memory':
            return {
                "action": "respect_biological_limit",
                "fallback": "defer_to_consolidation",
                "max_retries": 1,
                "biological_note": "Working memory timeout - respecting 5-minute window",
                "timeout_strategy": "biological_constraint"
            }
        elif context.get('memory_stage') == 'consolidation':
            return {
                "action": "extend_consolidation_window",
                "fallback": "partial_consolidation",
                "max_retries": 2,
                "extended_timeout": self.retry_config["consolidation_timeout"] * 1.5,
                "biological_note": "Consolidation timeout - allowing extended processing"
            }
        else:
            return {
                "action": "increase_timeout_gradually",
                "fallback": "async_processing",
                "max_retries": 1,
                "timeout_multiplier": 1.5,
                "biological_note": "General timeout - increasing processing window"
            }

    def _handle_security_error(self, error: Exception, record: Dict) -> Dict:
        """Handle security errors with immediate containment"""
        logger.critical(f"SECURITY BREACH DETECTED: {error}")
        
        # Immediate containment actions
        security_actions = {
            "action": "immediate_containment",
            "fallback": "alert_admin_and_audit",
            "max_retries": 0,
            "containment_steps": [
                "disable_external_connections",
                "backup_current_state",
                "enable_audit_logging",
                "notify_security_team"
            ],
            "biological_note": "Security incident - protecting memory system integrity"
        }
        
        # Additional logging for security incidents
        try:
            with sqlite3.connect(self.error_db_path) as conn:
                conn.execute("""
                    INSERT INTO security_incidents (timestamp, error_type, details, severity)
                    VALUES (?, ?, ?, 'CRITICAL')
                """, (datetime.now().isoformat(), str(type(error).__name__), str(error)))
                conn.commit()
        except Exception as log_error:
            logger.error(f"Failed to log security incident: {log_error}")
        
        return security_actions

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


def with_database_error_handling(timeout_seconds: float = 60.0):
    """Decorator specifically for database operations"""
    return with_error_handling(
        category=ErrorCategory.DATABASE,
        biological_context={'operation_type': 'database'},
        timeout_seconds=timeout_seconds
    )


def with_llm_error_handling(timeout_seconds: float = 30.0):
    """Decorator specifically for LLM operations"""
    return with_error_handling(
        category=ErrorCategory.LLM,
        biological_context={'operation_type': 'llm_processing'},
        timeout_seconds=timeout_seconds
    )


def with_embedding_error_handling(timeout_seconds: float = 45.0):
    """Decorator specifically for embedding operations"""
    return with_error_handling(
        category=ErrorCategory.EMBEDDING,
        biological_context={'operation_type': 'embedding_generation'},
        timeout_seconds=timeout_seconds
    )


def with_biological_timing_constraints(memory_stage: str, max_duration: float = None):
    """Decorator that enforces biological timing constraints"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Set biological constraints
            if memory_stage == 'working_memory' and not max_duration:
                max_duration_actual = 300.0  # 5 minutes
            elif memory_stage == 'consolidation' and not max_duration:
                max_duration_actual = 3600.0  # 1 hour
            else:
                max_duration_actual = max_duration or 600.0  # 10 minutes default
            
            try:
                result = func(*args, **kwargs)
                
                # Check if we exceeded biological constraints
                duration = time.time() - start_time
                if duration > max_duration_actual:
                    logger.warning(f"Function {func.__name__} exceeded biological constraint: "
                                 f"{duration:.1f}s > {max_duration_actual}s for {memory_stage}")
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                context = {
                    'memory_stage': memory_stage,
                    'duration_seconds': duration,
                    'max_allowed_duration': max_duration_actual
                }
                raise BiologicalMemoryError(
                    f"Error in {memory_stage} processing after {duration:.1f}s: {e}",
                    category=ErrorCategory.BIOLOGICAL_TIMING,
                    details=context,
                    cause=e
                )
        return wrapper
    return decorator


# Global error handler instance
_global_error_handler = None


def get_global_error_handler() -> BiologicalMemoryErrorHandler:
    """Get or create the global error handler instance"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = BiologicalMemoryErrorHandler()
    return _global_error_handler


@contextmanager
def database_transaction(connection, error_handler: Optional[BiologicalMemoryErrorHandler] = None):
    """Context manager for database transactions with comprehensive error handling"""
    try:
        yield connection
        connection.commit()
    except Exception as e:
        try:
            connection.rollback()
        except Exception as rollback_error:
            logger.error(f"Rollback failed: {rollback_error}")
        
        if error_handler:
            error_handler.handle_error(e, {'operation': 'database_transaction'})
        raise DatabaseError(f"Transaction failed: {e}", cause=e)


def log_biological_error(error: Exception, memory_stage: str = None, 
                        operation_type: str = None, details: Dict = None):
    """Convenience function for logging errors with biological context"""
    handler = get_global_error_handler()
    context = {
        'biological_context': {
            'memory_stage': memory_stage,
            'operation_type': operation_type
        },
        'details': details or {}
    }
    handler.handle_error(error, context)


# Utility functions for common error scenarios

def handle_database_connection_error(func: Callable, *args, **kwargs):
    """Handle database connection errors with automatic retry"""
    handler = get_global_error_handler()
    return handler.safe_execute(func, {'operation_type': 'database_connection'}, *args, **kwargs)


def handle_llm_service_error(func: Callable, *args, **kwargs):
    """Handle LLM service errors with fallback strategies"""
    handler = get_global_error_handler()
    return handler.safe_execute(func, {'operation_type': 'llm_service'}, *args, **kwargs)


def handle_file_operation_error(func: Callable, file_path: str, *args, **kwargs):
    """Handle file operation errors with cleanup"""
    handler = get_global_error_handler()
    
    def cleanup():
        # Clean up any temporary files or locks
        try:
            temp_file = Path(file_path).with_suffix('.tmp')
            if temp_file.exists():
                temp_file.unlink()
        except Exception as e:
            logger.debug(f"Cleanup warning: {e}")
    
    return handler.safe_execute_with_cleanup(
        func, cleanup, 
        {'operation_type': 'file_io', 'file_path': file_path}, 
        *args, **kwargs
    )
