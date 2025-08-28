#!/usr/bin/env python3
"""
BMP-013: Comprehensive Error Handling and Recovery System
Implements robust error handling, retry logic, and recovery mechanisms for biological memory pipeline

STORY-CS-001: Security Hardening - Credential Exposure Prevention
Adds comprehensive credential sanitization and PII redaction
"""

import time
import json
import logging
import threading
import sqlite3
import re
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List, Tuple
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from functools import wraps
import duckdb
import psutil


class ErrorType(Enum):
    """Error type classification for targeted recovery strategies"""
    CONNECTION_FAILURE = "connection_failure"
    TIMEOUT = "timeout"
    JSON_MALFORMED = "json_malformed"
    TRANSACTION_FAILURE = "transaction_failure" 
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATA_CORRUPTION = "data_corruption"
    CONFIGURATION_ERROR = "configuration_error"
    SECURITY_VIOLATION = "security_violation"


class RecoveryStrategy(Enum):
    """Recovery strategy options"""
    RETRY_EXPONENTIAL = "retry_exponential"
    RETRY_LINEAR = "retry_linear"
    FALLBACK = "fallback"
    CIRCUIT_BREAK = "circuit_break"
    DEAD_LETTER = "dead_letter"
    GRACEFUL_DEGRADE = "graceful_degrade"


@dataclass
class ErrorEvent:
    """Structured error event for comprehensive logging and analysis"""
    error_id: str
    error_type: ErrorType
    timestamp: datetime
    component: str
    operation: str
    error_message: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = None
    severity: str = "ERROR"
    recovery_attempts: int = 0
    recovered: bool = False
    recovery_time_seconds: Optional[float] = None
    impact_assessment: Optional[str] = None


class SecuritySanitizer:
    \"\"\"
    STORY-CS-001: Security Hardening - Credential Exposure Prevention
    Handles sanitization of sensitive data in logs and error contexts
    \"\"\"
    
    # Sensitive data patterns for detection and masking
    SENSITIVE_PATTERNS = {
        'password': [
            r'password[\'\"\\s]*[:=][\'\"\\s]*([^\\s\'\"]+)',
            r'passwd[\'\"\\s]*[:=][\'\"\\s]*([^\\s\'\"]+)',
            r'pwd[\'\"\\s]*[:=][\'\"\\s]*([^\\s\'\"]+)'
        ],
        'api_key': [
            r'api[_\\-]?key[\'\"\\s]*[:=][\'\"\\s]*([a-zA-Z0-9\\-_]{16,})',
            r'apikey[\'\"\\s]*[:=][\'\"\\s]*([a-zA-Z0-9\\-_]{16,})',
            r'sk-[a-zA-Z0-9]{20,}',
            r'Bearer\\s+([a-zA-Z0-9\\-._~+/]+=*)',
        ],
        'token': [
            r'token[\'\"\\s]*[:=][\'\"\\s]*([a-zA-Z0-9\\-_]{16,})',
            r'access[_\\-]?token[\'\"\\s]*[:=][\'\"\\s]*([a-zA-Z0-9\\-_]{16,})',
            r'refresh[_\\-]?token[\'\"\\s]*[:=][\'\"\\s]*([a-zA-Z0-9\\-_]{16,})',
            r'auth[_\\-]?token[\'\"\\s]*[:=][\'\"\\s]*([a-zA-Z0-9\\-_]{16,})',
        ],
        'connection_string': [
            r'://[^:]+:([^@]+)@',  # Captures password in connection strings
            r'postgres://[^:]+:([^@]+)@',
            r'mysql://[^:]+:([^@]+)@',
            r'mongodb://[^:]+:([^@]+)@'
        ],
        'jwt': [
            r'eyJ[a-zA-Z0-9\\-_]+=*\\.[a-zA-Z0-9\\-_]+=*\\.[a-zA-Z0-9\\-_]+=*',
        ],
        'secret': [
            r'secret[\'\"\\s]*[:=][\'\"\\s]*([^\\s\'\"]+)',
            r'private[_\\-]?key[\'\"\\s]*[:=][\'\"\\s]*([^\\s\'\"]+)',
        ],
        'credit_card': [
            r'\\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\\b',
        ],
        'ssn': [
            r'\\b\\d{3}-\\d{2}-\\d{4}\\b',
            r'\\b\\d{9}\\b'
        ],
        'email': [
            r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b'
        ],
        'phone': [
            r'\\b\\d{3}-\\d{3}-\\d{4}\\b',
            r'\\(\\d{3}\\)\\s*\\d{3}-\\d{4}',
            r'\\b\\d{10}\\b'
        ]
    }
    
    # Sensitive keys to look for in dictionaries
    SENSITIVE_KEYS = {
        'password', 'passwd', 'pwd', 'secret', 'private_key', 'api_key', 'apikey',
        'token', 'access_token', 'refresh_token', 'auth_token', 'session_token',
        'connection_string', 'database_url', 'db_url', 'connection_url',
        'authorization', 'bearer', 'x-api-key', 'x-auth-token',
        'ssn', 'social_security_number', 'credit_card', 'cc_number',
        'private', 'confidential', 'sensitive'
    }
    
    @staticmethod
    def sanitize_string(text: str, preserve_structure: bool = True) -> str:
        \"\"\"
        Sanitize a string by masking sensitive data patterns
        
        Args:
            text: Input string to sanitize
            preserve_structure: Whether to preserve the structure of masked data
            
        Returns:
            Sanitized string with sensitive data masked
        \"\"\"
        if not isinstance(text, str):
            text = str(text)
            
        sanitized_text = text
        
        # Apply sensitive patterns
        for pattern_type, patterns in SecuritySanitizer.SENSITIVE_PATTERNS.items():
            for pattern in patterns:
                if preserve_structure:
                    # Replace with masked version preserving length
                    def mask_match(match):
                        if match.groups():
                            # Mask captured group (the sensitive part)
                            sensitive_part = match.group(1)
                            prefix_length = len(sensitive_part) // 4  # Show first 25%
                            if len(sensitive_part) <= 4:
                                return match.group(0).replace(sensitive_part, '*' * len(sensitive_part))
                            else:
                                prefix = sensitive_part[:prefix_length]
                                mask_length = len(sensitive_part) - prefix_length
                                return match.group(0).replace(sensitive_part, f\"{prefix}{'*' * mask_length}\")
                        else:
                            # Mask entire match
                            return '*' * len(match.group(0))
                    
                    sanitized_text = re.sub(pattern, mask_match, sanitized_text, flags=re.IGNORECASE)
                else:
                    # Replace with generic placeholder
                    sanitized_text = re.sub(pattern, f\"[REDACTED_{pattern_type.upper()}]\", 
                                          sanitized_text, flags=re.IGNORECASE)
        
        return sanitized_text
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any], preserve_structure: bool = True) -> Dict[str, Any]:
        \"\"\"
        Recursively sanitize dictionary data
        
        Args:
            data: Dictionary to sanitize
            preserve_structure: Whether to preserve the structure of masked data
            
        Returns:
            Sanitized dictionary
        \"\"\"
        if not isinstance(data, dict):
            return data
            
        sanitized_data = {}
        
        for key, value in data.items():
            # Check if key is sensitive
            if isinstance(key, str) and key.lower() in SecuritySanitizer.SENSITIVE_KEYS:
                if preserve_structure and isinstance(value, str) and len(value) > 4:
                    # Show first character + asterisks
                    sanitized_data[key] = value[0] + '*' * (len(value) - 1)
                else:
                    sanitized_data[key] = \"[REDACTED]\"
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized_data[key] = SecuritySanitizer.sanitize_dict(value, preserve_structure)
            elif isinstance(value, list):
                # Sanitize list items
                sanitized_data[key] = [
                    SecuritySanitizer.sanitize_dict(item, preserve_structure) if isinstance(item, dict)
                    else SecuritySanitizer.sanitize_string(str(item), preserve_structure) if isinstance(item, str)
                    else item
                    for item in value
                ]
            elif isinstance(value, str):
                # Sanitize string values
                sanitized_data[key] = SecuritySanitizer.sanitize_string(value, preserve_structure)
            else:
                # Keep non-string, non-dict values as-is
                sanitized_data[key] = value
                
        return sanitized_data
    
    @staticmethod
    def generate_secure_error_id() -> str:
        \"\"\"
        Generate a cryptographically secure error ID instead of predictable timestamp-based IDs
        
        Returns:
            Secure UUID-based error ID
        \"\"\"
        # Generate UUID4 (random) and convert to compact format
        error_uuid = uuid.uuid4()
        # Create shorter but still unique ID using hex and timestamp hash
        timestamp_hash = hashlib.sha256(str(int(time.time())).encode()).hexdigest()[:8]
        return f\"err_{error_uuid.hex[:16]}_{timestamp_hash}\"
    
    @staticmethod
    def sanitize_log_message(message: str) -> str:
        \"\"\"
        Sanitize log messages to prevent log injection attacks
        
        Args:
            message: Raw log message
            
        Returns:
            Sanitized log message
        \"\"\"
        if not isinstance(message, str):
            message = str(message)
            
        # Remove/escape characters used for log injection
        sanitized_message = message.replace('\\n', '\\\\n')
        sanitized_message = sanitized_message.replace('\\r', '\\\\r')
        sanitized_message = sanitized_message.replace('\\t', '\\\\t')
        sanitized_message = sanitized_message.replace('\\x00', '\\\\x00')  # Null bytes
        
        # Remove ANSI escape codes that could manipulate terminal output
        ansi_escape = re.compile(r'\\x1B(?:[@-Z\\-_]|\\[[0-?]*[ -/]*[@-~])')
        sanitized_message = ansi_escape.sub('', sanitized_message)
        
        # Apply sensitive data sanitization
        sanitized_message = SecuritySanitizer.sanitize_string(sanitized_message)
        
        # Limit message length to prevent log flooding
        max_length = 2000
        if len(sanitized_message) > max_length:
            sanitized_message = sanitized_message[:max_length] + \"... [TRUNCATED]\"
            
        return sanitized_message


class CircuitBreaker:
    """Circuit breaker implementation to prevent cascade failures"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 timeout_seconds: int = 60,
                 expected_exception: Exception = Exception):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
        
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self._lock:
                if self.state == "OPEN":
                    if self._should_attempt_reset():
                        self.state = "HALF_OPEN"
                    else:
                        raise Exception(f"Circuit breaker is OPEN. Service unavailable.")
                
                try:
                    result = func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.expected_exception as e:
                    self._on_failure()
                    raise e
                    
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        return (datetime.now() - self.last_failure_time).total_seconds() >= self.timeout_seconds
    
    def _on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class DeadLetterQueue:
    """Dead letter queue for failed memory processing operations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for dead letter queue"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dead_letter_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE NOT NULL,
                    original_operation TEXT NOT NULL,
                    memory_data TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    failure_count INTEGER DEFAULT 1,
                    first_failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    retry_after TIMESTAMP,
                    max_retries INTEGER DEFAULT 3,
                    status TEXT DEFAULT 'FAILED'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dlq_retry_after 
                ON dead_letter_queue(retry_after)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dlq_status 
                ON dead_letter_queue(status)
            """)
            conn.commit()
        finally:
            conn.close()
    
    def enqueue(self, 
                message_id: str,
                operation: str, 
                memory_data: Dict[str, Any],
                error_type: ErrorType,
                error_message: str,
                retry_delay_seconds: int = 300):
        """Add failed memory to dead letter queue"""
        conn = sqlite3.connect(self.db_path)
        try:
            retry_after = datetime.now() + timedelta(seconds=retry_delay_seconds)
            conn.execute("""
                INSERT OR REPLACE INTO dead_letter_queue 
                (message_id, original_operation, memory_data, error_type, error_message, 
                 retry_after, last_failed_at, failure_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT failure_count FROM dead_letter_queue WHERE message_id = ?) + 1, 1))
            """, (message_id, operation, json.dumps(memory_data), error_type.value, 
                 error_message, retry_after, datetime.now(), message_id))
            conn.commit()
        finally:
            conn.close()
    
    def get_retry_candidates(self) -> List[Dict[str, Any]]:
        """Get messages ready for retry"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT * FROM dead_letter_queue 
                WHERE retry_after <= CURRENT_TIMESTAMP 
                AND failure_count <= max_retries
                AND status = 'FAILED'
                ORDER BY first_failed_at
                LIMIT 100
            """)
            return [dict(zip([col[0] for col in cursor.description], row)) 
                   for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def mark_retry_success(self, message_id: str):
        """Mark message as successfully retried"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                UPDATE dead_letter_queue 
                SET status = 'RECOVERED' 
                WHERE message_id = ?
            """, (message_id,))
            conn.commit()
        finally:
            conn.close()
    
    def mark_permanent_failure(self, message_id: str):
        """Mark message as permanently failed"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                UPDATE dead_letter_queue 
                SET status = 'PERMANENT_FAILURE' 
                WHERE message_id = ?
            """, (message_id,))
            conn.commit()
        finally:
            conn.close()


class BiologicalMemoryErrorHandler:
    """
    Comprehensive error handling and recovery system for biological memory pipeline
    
    STORY-CS-001: Enhanced with security hardening for credential exposure prevention
    """
    
    def __init__(self, 
                 base_path: str,
                 circuit_breaker_enabled: bool = True,
                 max_db_connections: int = 160,
                 ollama_timeout_seconds: int = 300,
                 max_error_events: int = 1000,  # Prevent unbounded memory growth
                 sanitize_sensitive_data: bool = True):
        
        self.base_path = Path(base_path)
        self.circuit_breaker_enabled = circuit_breaker_enabled
        self.max_db_connections = max_db_connections
        self.ollama_timeout_seconds = ollama_timeout_seconds
        self.max_error_events = max_error_events
        self.sanitize_sensitive_data = sanitize_sensitive_data
        self.security_sanitizer = SecuritySanitizer()
        
        # Initialize components
        self.logger = self._setup_error_logging()
        
        # Ensure dbs directory exists
        dbs_dir = self.base_path / "dbs"
        dbs_dir.mkdir(parents=True, exist_ok=True)
        
        self.dead_letter_queue = DeadLetterQueue(str(dbs_dir / "dead_letter.db"))
        self.error_events: List[ErrorEvent] = []
        self.recovery_stats = {
            'total_errors': 0,
            'recovered_errors': 0,
            'permanent_failures': 0,
            'circuit_breaks': 0
        }
        
        # Circuit breakers for different services
        self.circuit_breakers = {}
        if circuit_breaker_enabled:
            self.circuit_breakers['duckdb'] = CircuitBreaker(failure_threshold=3, timeout_seconds=30)
            self.circuit_breakers['postgres'] = CircuitBreaker(failure_threshold=5, timeout_seconds=60)
            self.circuit_breakers['ollama'] = CircuitBreaker(failure_threshold=2, timeout_seconds=120)
        
        # Connection pools and resource management
        self._db_connections = {}
        self._connection_lock = threading.Lock()
        
        self.logger.info("BiologicalMemoryErrorHandler initialized")
    
    def _setup_error_logging(self) -> logging.Logger:
        """Setup comprehensive error logging"""
        logger = logging.getLogger('BiologicalMemoryErrors')
        logger.setLevel(logging.INFO)
        
        # Error log file
        log_dir = self.base_path / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        error_handler = logging.FileHandler(log_dir / 'error_handling.log')
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(error_handler)
        
        # Structured error log (JSON)
        structured_handler = logging.FileHandler(log_dir / 'structured_errors.jsonl')
        structured_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(structured_handler)
        
        return logger
    
    def log_error_event(self, error_event: ErrorEvent):
        """
        STORY-CS-001: Log structured error event with credential sanitization and PII redaction
        """
        # STORY-CS-001: Implement credential sanitization and PII redaction
        if self.sanitize_sensitive_data:
            # Sanitize error message for log injection prevention
            error_event.error_message = self.security_sanitizer.sanitize_log_message(error_event.error_message)
            
            # Sanitize stack trace if present
            if error_event.stack_trace:
                error_event.stack_trace = self.security_sanitizer.sanitize_string(error_event.stack_trace)
            
            # Sanitize context data to remove sensitive information
            if error_event.context:
                error_event.context = self.security_sanitizer.sanitize_dict(error_event.context)
        
        # Implement bounded error event storage to prevent memory exhaustion
        self.error_events.append(error_event)
        if len(self.error_events) > self.max_error_events:
            # Remove oldest events to maintain circular buffer
            self.error_events = self.error_events[-self.max_error_events:]
        
        self.recovery_stats['total_errors'] += 1
        
        # Prepare sanitized event data for logging
        sanitized_event_dict = asdict(error_event)
        
        # Log structured JSON
        structured_log = self.logger.handlers[1]  # JSON handler
        structured_log.handle(logging.LogRecord(
            name='BiologicalMemoryErrors',
            level=logging.ERROR,
            pathname='',
            lineno=0,
            msg=json.dumps(sanitized_event_dict, default=str),
            args=(),
            exc_info=None
        ))
        
        # Log human-readable message with sanitization
        sanitized_message = self.security_sanitizer.sanitize_log_message(
            f"[{error_event.error_type.value}] {error_event.component}.{error_event.operation}: "
            f"{error_event.error_message} (Recovery attempts: {error_event.recovery_attempts})"
        )
        self.logger.error(sanitized_message)
    
    def exponential_backoff_retry(self,
                                func: Callable,
                                max_retries: int = 5,
                                base_delay: float = 1.0,
                                max_delay: float = 32.0,
                                exceptions: tuple = (Exception,)) -> Any:
        """Execute function with exponential backoff retry"""
        
        for attempt in range(max_retries + 1):
            try:
                return func()
            except exceptions as e:
                if attempt == max_retries:
                    raise e
                
                delay = min(base_delay * (2 ** attempt), max_delay)
                self.logger.warning(f"Retry attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                                  f"Retrying in {delay:.2f}s")
                time.sleep(delay)
    
    def get_database_connection(self, db_path: str, timeout: int = 30) -> duckdb.DuckDBPyConnection:
        """Get database connection with retry logic and connection pooling"""
        
        def connect_with_retry():
            try:
                if self.circuit_breaker_enabled and 'duckdb' in self.circuit_breakers:
                    @self.circuit_breakers['duckdb']
                    def protected_connect():
                        return duckdb.connect(db_path)
                    return protected_connect()
                else:
                    return duckdb.connect(db_path)
            except Exception as e:
                error_event = ErrorEvent(
                    error_id=SecuritySanitizer.generate_secure_error_id(),
                    error_type=ErrorType.CONNECTION_FAILURE,
                    timestamp=datetime.now(),
                    component="database",
                    operation="connect",
                    error_message=str(e),
                    context={"db_path": db_path}
                )
                self.log_error_event(error_event)
                raise
        
        return self.exponential_backoff_retry(
            connect_with_retry,
            max_retries=3,
            exceptions=(Exception,)
        )
    
    def execute_with_transaction_safety(self,
                                      connection: duckdb.DuckDBPyConnection,
                                      operations: List[str],
                                      context: Dict[str, Any] = None) -> bool:
        """Execute database operations with transaction rollback on failure"""
        
        try:
            connection.begin()
            
            for operation in operations:
                connection.execute(operation)
            
            connection.commit()
            return True
            
        except Exception as e:
            try:
                connection.rollback()
                self.logger.info("Transaction rolled back successfully")
            except Exception as rollback_error:
                self.logger.error(f"Rollback failed: {rollback_error}")
            
            error_event = ErrorEvent(
                error_id=SecuritySanitizer.generate_secure_error_id(),
                error_type=ErrorType.TRANSACTION_FAILURE,
                timestamp=datetime.now(),
                component="database",
                operation="transaction_block",
                error_message=str(e),
                context=context or {}
            )
            self.log_error_event(error_event)
            return False
    
    def process_with_json_recovery(self, 
                                 llm_response: str,
                                 expected_schema: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Process LLM response with JSON malformation recovery"""
        
        def attempt_json_parse(text: str) -> Dict[str, Any]:
            """Attempt to parse JSON with various recovery strategies"""
            
            # Strategy 1: Direct parse
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            
            # Strategy 2: Extract JSON from markdown code blocks
            import re
            json_pattern = r'```(?:json)?\s*(.*?)\s*```'
            matches = re.findall(json_pattern, text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
            
            # Strategy 3: Find JSON-like patterns
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, text)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
            
            # Strategy 4: Create minimal valid response
            if expected_schema:
                minimal_response = {}
                for key, default_value in expected_schema.items():
                    if isinstance(default_value, str):
                        minimal_response[key] = "error_recovery_placeholder"
                    elif isinstance(default_value, (int, float)):
                        minimal_response[key] = 0
                    elif isinstance(default_value, list):
                        minimal_response[key] = []
                    elif isinstance(default_value, dict):
                        minimal_response[key] = {}
                    else:
                        minimal_response[key] = None
                return minimal_response
            
            raise json.JSONDecodeError("All recovery strategies failed", text, 0)
        
        try:
            return attempt_json_parse(llm_response)
            
        except json.JSONDecodeError as e:
            error_event = ErrorEvent(
                error_id=SecuritySanitizer.generate_secure_error_id(),
                error_type=ErrorType.JSON_MALFORMED,
                timestamp=datetime.now(),
                component="llm_processor",
                operation="json_parse",
                error_message=str(e),
                context={
                    "response_length": len(llm_response),
                    "response_preview": llm_response[:200]
                }
            )
            self.log_error_event(error_event)
            return None
    
    def monitor_system_resources(self) -> Dict[str, Any]:
        """Monitor system resources and detect exhaustion"""
        
        try:
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage(str(self.base_path))
            cpu_percent = psutil.cpu_percent(interval=1)
            
            resource_status = {
                'memory_available_mb': memory_info.available / 1024 / 1024,
                'memory_percent': memory_info.percent,
                'disk_free_mb': disk_info.free / 1024 / 1024,
                'disk_percent': (disk_info.total - disk_info.free) / disk_info.total * 100,
                'cpu_percent': cpu_percent,
                'timestamp': datetime.now()
            }
            
            # Check for resource exhaustion
            warnings = []
            if memory_info.percent > 90:
                warnings.append("Memory usage critical (>90%)")
            if disk_info.free < 1024 * 1024 * 1024:  # Less than 1GB free
                warnings.append("Disk space critical (<1GB free)")
            if cpu_percent > 95:
                warnings.append("CPU usage critical (>95%)")
            
            if warnings:
                error_event = ErrorEvent(
                    error_id=SecuritySanitizer.generate_secure_error_id(),
                    error_type=ErrorType.RESOURCE_EXHAUSTION,
                    timestamp=datetime.now(),
                    component="system_monitor",
                    operation="resource_check",
                    error_message="; ".join(warnings),
                    context=resource_status,
                    severity="WARNING"
                )
                self.log_error_event(error_event)
            
            return resource_status
            
        except Exception as e:
            self.logger.error(f"Failed to monitor system resources: {e}")
            return {}
    
    def graceful_degradation_mode(self, failed_component: str) -> Dict[str, bool]:
        """Enable graceful degradation when components fail"""
        
        degradation_config = {
            'working_memory_processing': True,
            'short_term_memory_processing': True, 
            'consolidation_processing': True,
            'deep_consolidation': True,
            'rem_sleep_processing': True,
            'analytics_dashboard': True,
            'health_monitoring': True
        }
        
        # Disable specific functionality based on failed component
        if failed_component == "duckdb":
            degradation_config.update({
                'consolidation_processing': False,
                'deep_consolidation': False,
                'analytics_dashboard': False
            })
        elif failed_component == "ollama":
            degradation_config.update({
                'rem_sleep_processing': False,
                'creative_associations': False
            })
        elif failed_component == "postgres":
            degradation_config.update({
                'working_memory_processing': False
            })
        
        self.logger.warning(f"Graceful degradation enabled due to {failed_component} failure")
        self.logger.info(f"Active capabilities: {degradation_config}")
        
        return degradation_config
    
    def retry_dead_letter_messages(self):
        """Process and retry messages from dead letter queue"""
        
        retry_candidates = self.dead_letter_queue.get_retry_candidates()
        
        for message in retry_candidates:
            try:
                message_id = message['message_id']
                operation = message['original_operation']
                memory_data = json.loads(message['memory_data'])
                
                self.logger.info(f"Retrying dead letter message: {message_id}")
                
                # Attempt to reprocess based on original operation
                success = self._retry_operation(operation, memory_data)
                
                if success:
                    self.dead_letter_queue.mark_retry_success(message_id)
                    self.recovery_stats['recovered_errors'] += 1
                    self.logger.info(f"Dead letter message recovered: {message_id}")
                else:
                    if message['failure_count'] >= message['max_retries']:
                        self.dead_letter_queue.mark_permanent_failure(message_id)
                        self.recovery_stats['permanent_failures'] += 1
                        self.logger.error(f"Dead letter message permanently failed: {message_id}")
                    else:
                        # Will be retried again later
                        self.logger.warning(f"Dead letter message retry failed: {message_id}")
                        
            except Exception as e:
                self.logger.error(f"Error processing dead letter message: {e}")
    
    def _retry_operation(self, operation: str, memory_data: Dict[str, Any]) -> bool:
        """Retry a specific failed operation"""
        
        try:
            # This would integrate with the actual memory processing pipeline
            # For now, simulate the retry logic
            
            if operation == "working_memory_processing":
                # Retry working memory processing
                pass
            elif operation == "stm_consolidation":
                # Retry STM consolidation
                pass
            elif operation == "ltm_consolidation":
                # Retry LTM consolidation  
                pass
            
            return True  # Simulate success for now
            
        except Exception as e:
            self.logger.error(f"Retry operation failed for {operation}: {e}")
            return False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error handling summary and metrics"""
        
        recent_errors = [e for e in self.error_events 
                        if e.timestamp > datetime.now() - timedelta(hours=24)]
        
        error_by_type = {}
        for error in recent_errors:
            error_type = error.error_type.value
            if error_type not in error_by_type:
                error_by_type[error_type] = 0
            error_by_type[error_type] += 1
        
        recovery_rate = (self.recovery_stats['recovered_errors'] / 
                        max(self.recovery_stats['total_errors'], 1)) * 100
        
        return {
            'total_errors_24h': len(recent_errors),
            'errors_by_type': error_by_type,
            'recovery_stats': self.recovery_stats,
            'recovery_rate_percent': round(recovery_rate, 2),
            'circuit_breaker_states': {name: cb.state for name, cb in self.circuit_breakers.items()},
            'system_resources': self.monitor_system_resources(),
            'dead_letter_queue_size': len(self.dead_letter_queue.get_retry_candidates()),
            'timestamp': datetime.now()
        }


# Decorator for automatic error handling
def with_error_handling(error_handler: BiologicalMemoryErrorHandler,
                       operation: str,
                       component: str,
                       retry_attempts: int = 3):
    """Decorator to automatically apply error handling to functions"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            for attempt in range(retry_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # Log successful recovery if previous attempts failed
                    if attempt > 0:
                        recovery_time = time.time() - start_time
                        error_handler.logger.info(
                            f"Operation recovered after {attempt} attempts in {recovery_time:.2f}s: "
                            f"{component}.{operation}"
                        )
                    
                    return result
                    
                except Exception as e:
                    error_event = ErrorEvent(
                        error_id=SecuritySanitizer.generate_secure_error_id(),
                        error_type=ErrorType.CONNECTION_FAILURE,  # Default, should be customized
                        timestamp=datetime.now(),
                        component=component,
                        operation=operation,
                        error_message=str(e),
                        recovery_attempts=attempt,
                        context={'args_count': len(args), 'kwargs_keys': list(kwargs.keys())}
                    )
                    
                    if attempt == retry_attempts:
                        error_handler.log_error_event(error_event)
                        raise e
                    else:
                        error_handler.logger.warning(
                            f"Attempt {attempt + 1}/{retry_attempts} failed for {component}.{operation}: {str(e)}"
                        )
        
        return wrapper
    return decorator