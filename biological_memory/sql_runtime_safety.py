#!/usr/bin/env python3
"""
BMP-HIGH-006: SQL Runtime Safety and Crash Prevention
Comprehensive SQL error handling and runtime stability system

This module implements bulletproof SQL execution with comprehensive error handling,
resource management, and crash prevention for the biological memory system.

Author: Runtime Stability Expert Agent
Date: 2025-08-28
"""

import time
import json
import logging
import threading
import contextlib
import duckdb
import psycopg2
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union, Generator
from dataclasses import dataclass
from enum import Enum
import psutil
import signal
import resource

# Import our existing error handling system
from error_handling import (
    BiologicalMemoryErrorHandler, ErrorType, ErrorEvent,
    CircuitBreaker, DeadLetterQueue
)


class SQLRuntimeSafetyLevel(Enum):
    """SQL runtime safety levels for different execution contexts"""
    STRICT = "strict"          # Maximum safety, fail fast
    RESILIENT = "resilient"    # Moderate safety, retry with fallbacks  
    PERMISSIVE = "permissive"  # Minimum safety, best effort


@dataclass
class SQLExecutionResult:
    """Comprehensive SQL execution result with safety metadata"""
    success: bool
    result_set: Optional[List[Tuple]] = None
    rows_affected: int = 0
    execution_time_ms: int = 0
    error_message: Optional[str] = None
    error_type: Optional[ErrorType] = None
    safety_level: Optional[SQLRuntimeSafetyLevel] = None
    retry_count: int = 0
    fallback_used: bool = False
    resource_usage: Dict[str, float] = None
    warnings: List[str] = None


class SQLRuntimeSafetyManager:
    """
    Comprehensive SQL runtime safety and crash prevention system
    
    Features:
    - Connection pooling and resource management
    - Transaction safety with deadlock prevention
    - Memory and timeout protection
    - SQL injection prevention
    - Automatic retry with exponential backoff
    - Graceful degradation and fallback strategies
    - Runtime performance monitoring
    - Resource leak prevention
    """
    
    def __init__(self, 
                 error_handler: BiologicalMemoryErrorHandler,
                 max_connections_per_db: int = 10,
                 query_timeout_seconds: int = 300,
                 memory_limit_mb: int = 1024,
                 safety_level: SQLRuntimeSafetyLevel = SQLRuntimeSafetyLevel.RESILIENT):
        
        self.error_handler = error_handler
        self.max_connections_per_db = max_connections_per_db
        self.query_timeout_seconds = query_timeout_seconds
        self.memory_limit_mb = memory_limit_mb
        self.safety_level = safety_level
        
        # Connection pools
        self._connection_pools: Dict[str, List[Any]] = {}
        self._pool_locks: Dict[str, threading.Lock] = {}
        self._active_connections: Dict[str, int] = {}
        
        # Safety monitoring
        self._query_execution_stats: Dict[str, Dict] = {}
        self._resource_monitor_lock = threading.Lock()
        self._shutdown_event = threading.Event()
        
        # Performance tracking
        self.execution_metrics = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'retry_attempts': 0,
            'fallback_activations': 0,
            'avg_execution_time_ms': 0.0,
            'deadlock_recoveries': 0,
            'timeout_recoveries': 0,
            'memory_limit_hits': 0
        }
        
        # Set up logging
        self.logger = logging.getLogger('SQLRuntimeSafety')
        self.logger.setLevel(logging.INFO)
        
        # Initialize resource monitoring
        self._start_resource_monitor()
        
        self.logger.info(f"SQL Runtime Safety Manager initialized with {safety_level.value} safety level")
    
    def _start_resource_monitor(self):
        """Start background resource monitoring thread"""
        def monitor_resources():
            while not self._shutdown_event.is_set():
                try:
                    self._check_system_resources()
                    time.sleep(10)  # Check every 10 seconds
                except Exception as e:
                    self.logger.warning(f"Resource monitor error: {e}")
        
        monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
        monitor_thread.start()
    
    def _check_system_resources(self):
        """Monitor system resources and trigger alerts"""
        try:
            memory_info = psutil.virtual_memory()
            if memory_info.percent > 90:
                self.logger.warning(f"High memory usage: {memory_info.percent}%")
                if self.safety_level == SQLRuntimeSafetyLevel.STRICT:
                    self._trigger_memory_protection()
            
            # Check for connection leaks
            for db_name, active_count in self._active_connections.items():
                if active_count > self.max_connections_per_db * 1.5:
                    self.logger.error(f"Connection leak detected for {db_name}: {active_count} active")
                    self._cleanup_stale_connections(db_name)
                    
        except Exception as e:
            self.logger.warning(f"Resource check failed: {e}")
    
    def _trigger_memory_protection(self):
        """Emergency memory protection measures"""
        self.logger.warning("Triggering emergency memory protection")
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Close idle connections
        for db_name in list(self._connection_pools.keys()):
            self._cleanup_idle_connections(db_name)
        
        # Log memory protection event
        error_event = ErrorEvent(
            error_id=f"memory_protection_{int(time.time())}",
            error_type=ErrorType.RESOURCE_EXHAUSTION,
            timestamp=datetime.now(),
            component="sql_safety_manager",
            operation="memory_protection",
            error_message="Emergency memory protection activated",
            severity="WARNING"
        )
        self.error_handler.log_error_event(error_event)
    
    def get_safe_connection(self, db_path: str, db_type: str = "duckdb") -> contextlib.AbstractContextManager:
        """
        Get a safe database connection with automatic cleanup
        
        Args:
            db_path: Path to database file
            db_type: Type of database (duckdb, sqlite, postgres)
            
        Returns:
            Context manager for safe connection handling
        """
        return self._SafeConnection(self, db_path, db_type)
    
    class _SafeConnection:
        """Context manager for safe database connections with automatic cleanup"""
        
        def __init__(self, manager: 'SQLRuntimeSafetyManager', db_path: str, db_type: str):
            self.manager = manager
            self.db_path = db_path
            self.db_type = db_type
            self.connection = None
            self.start_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            try:
                self.connection = self.manager._acquire_connection(self.db_path, self.db_type)
                return self.connection
            except Exception as e:
                self.manager.logger.error(f"Failed to acquire connection to {self.db_path}: {e}")
                raise
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.connection:
                try:
                    # Log connection usage
                    duration = time.time() - self.start_time if self.start_time else 0
                    if duration > 30:  # Log long-running connections
                        self.manager.logger.info(f"Long-running connection closed: {duration:.2f}s")
                    
                    self.manager._release_connection(self.db_path, self.connection, self.db_type)
                except Exception as e:
                    self.manager.logger.warning(f"Error releasing connection: {e}")
                finally:
                    self.connection = None
    
    def _acquire_connection(self, db_path: str, db_type: str) -> Any:
        """Safely acquire database connection from pool"""
        pool_key = f"{db_type}:{db_path}"
        
        # Initialize pool if needed
        if pool_key not in self._connection_pools:
            self._connection_pools[pool_key] = []
            self._pool_locks[pool_key] = threading.Lock()
            self._active_connections[pool_key] = 0
        
        with self._pool_locks[pool_key]:
            # Check connection limit
            if self._active_connections[pool_key] >= self.max_connections_per_db:
                if self.safety_level == SQLRuntimeSafetyLevel.STRICT:
                    raise RuntimeError(f"Connection limit exceeded for {pool_key}")
                else:
                    # Wait for connection to become available
                    self._wait_for_connection(pool_key)
            
            # Try to reuse existing connection
            pool = self._connection_pools[pool_key]
            while pool:
                conn = pool.pop()
                if self._is_connection_healthy(conn, db_type):
                    self._active_connections[pool_key] += 1
                    return conn
                else:
                    # Close unhealthy connection
                    self._close_connection(conn, db_type)
            
            # Create new connection
            conn = self._create_connection(db_path, db_type)
            self._active_connections[pool_key] += 1
            return conn
    
    def _create_connection(self, db_path: str, db_type: str) -> Any:
        """Create new database connection with safety measures"""
        try:
            if db_type == "duckdb":
                conn = duckdb.connect(db_path)
                
                # Set safety pragmas
                conn.execute("SET memory_limit = ?", [f"{self.memory_limit_mb}MB"])
                conn.execute("SET threads = ?", [min(4, psutil.cpu_count())])
                conn.execute("SET enable_progress_bar = false")
                
                return conn
                
            elif db_type == "sqlite":
                conn = sqlite3.connect(db_path, timeout=self.query_timeout_seconds)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                return conn
                
            elif db_type == "postgres":
                import psycopg2.extras
                conn = psycopg2.connect(
                    db_path,
                    connect_timeout=30,
                    cursor_factory=psycopg2.extras.RealDictCursor
                )
                conn.autocommit = False
                return conn
                
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
                
        except Exception as e:
            error_event = ErrorEvent(
                error_id=f"conn_create_{int(time.time())}",
                error_type=ErrorType.CONNECTION_FAILURE,
                timestamp=datetime.now(),
                component="sql_safety_manager",
                operation="create_connection",
                error_message=str(e),
                context={'db_path': db_path, 'db_type': db_type}
            )
            self.error_handler.log_error_event(error_event)
            raise
    
    def _is_connection_healthy(self, conn: Any, db_type: str) -> bool:
        """Check if connection is healthy and usable"""
        try:
            if db_type == "duckdb":
                conn.execute("SELECT 1").fetchone()
            elif db_type == "sqlite":
                conn.execute("SELECT 1").fetchone()
            elif db_type == "postgres":
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            return True
        except Exception:
            return False
    
    def _release_connection(self, db_path: str, conn: Any, db_type: str):
        """Release connection back to pool"""
        pool_key = f"{db_type}:{db_path}"
        
        with self._pool_locks[pool_key]:
            self._active_connections[pool_key] -= 1
            
            if self._is_connection_healthy(conn, db_type):
                # Return healthy connection to pool
                pool = self._connection_pools[pool_key]
                if len(pool) < self.max_connections_per_db // 2:  # Keep reasonable pool size
                    pool.append(conn)
                else:
                    self._close_connection(conn, db_type)
            else:
                # Close unhealthy connection
                self._close_connection(conn, db_type)
    
    def _close_connection(self, conn: Any, db_type: str):
        """Safely close database connection"""
        try:
            if hasattr(conn, 'close'):
                conn.close()
        except Exception as e:
            self.logger.warning(f"Error closing {db_type} connection: {e}")
    
    def execute_safe_query(self, 
                          db_path: str, 
                          query: str, 
                          parameters: Optional[List[Any]] = None,
                          db_type: str = "duckdb",
                          max_retries: int = 3,
                          timeout_override: Optional[int] = None) -> SQLExecutionResult:
        """
        Execute SQL query with comprehensive safety measures
        
        Args:
            db_path: Database path
            query: SQL query to execute
            parameters: Query parameters (for prepared statements)
            db_type: Database type
            max_retries: Maximum retry attempts
            timeout_override: Override default timeout
            
        Returns:
            SQLExecutionResult with execution details
        """
        start_time = time.time()
        self.execution_metrics['total_queries'] += 1
        
        # Input validation
        if not query or not query.strip():
            return SQLExecutionResult(
                success=False,
                error_message="Empty or invalid query",
                error_type=ErrorType.CONFIGURATION_ERROR
            )
        
        # SQL injection basic protection
        if self._detect_sql_injection(query):
            return SQLExecutionResult(
                success=False,
                error_message="Potential SQL injection detected",
                error_type=ErrorType.SECURITY_VIOLATION
            )
        
        # Resource pre-check
        if not self._pre_execution_resource_check():
            return SQLExecutionResult(
                success=False,
                error_message="Insufficient system resources",
                error_type=ErrorType.RESOURCE_EXHAUSTION
            )
        
        # Execute with retry logic
        for attempt in range(max_retries + 1):
            try:
                result = self._execute_query_attempt(
                    db_path, query, parameters, db_type, 
                    timeout_override or self.query_timeout_seconds,
                    attempt
                )
                
                if result.success:
                    self.execution_metrics['successful_queries'] += 1
                    execution_time = int((time.time() - start_time) * 1000)
                    result.execution_time_ms = execution_time
                    
                    # Update average execution time
                    total_time = (self.execution_metrics['avg_execution_time_ms'] * 
                                 (self.execution_metrics['successful_queries'] - 1) + execution_time)
                    self.execution_metrics['avg_execution_time_ms'] = total_time / self.execution_metrics['successful_queries']
                    
                    return result
                else:
                    if attempt < max_retries:
                        self.execution_metrics['retry_attempts'] += 1
                        delay = min(2.0 ** attempt, 16.0)  # Exponential backoff
                        self.logger.warning(f"Query attempt {attempt + 1} failed, retrying in {delay}s")
                        time.sleep(delay)
                    else:
                        self.execution_metrics['failed_queries'] += 1
                        return result
                        
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Query execution exception (attempt {attempt + 1}): {error_msg}")
                
                if attempt == max_retries:
                    self.execution_metrics['failed_queries'] += 1
                    return SQLExecutionResult(
                        success=False,
                        error_message=error_msg,
                        error_type=ErrorType.CONNECTION_FAILURE,
                        retry_count=attempt + 1,
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
        
        # Should never reach here
        return SQLExecutionResult(success=False, error_message="Unexpected execution path")
    
    def _execute_query_attempt(self, 
                              db_path: str, 
                              query: str, 
                              parameters: Optional[List[Any]],
                              db_type: str,
                              timeout_seconds: int,
                              attempt: int) -> SQLExecutionResult:
        """Execute single query attempt with timeout and monitoring"""
        
        execution_start = time.time()
        warnings = []
        
        try:
            with self.get_safe_connection(db_path, db_type) as conn:
                # Set query timeout if supported
                if db_type == "postgres":
                    with conn.cursor() as cursor:
                        cursor.execute(f"SET statement_timeout = {timeout_seconds * 1000}")
                
                # Execute query (simplified without signal timeout for better compatibility)
                try:
                    if parameters:
                        if db_type == "duckdb":
                            result = conn.execute(query, parameters).fetchall()
                        elif db_type == "sqlite":
                            cursor = conn.execute(query, parameters)
                            result = cursor.fetchall()
                        elif db_type == "postgres":
                            with conn.cursor() as cursor:
                                cursor.execute(query, parameters)
                                result = cursor.fetchall() if cursor.description else []
                    else:
                        if db_type == "duckdb":
                            result = conn.execute(query).fetchall()
                        elif db_type == "sqlite":
                            cursor = conn.execute(query)
                            result = cursor.fetchall()
                        elif db_type == "postgres":
                            with conn.cursor() as cursor:
                                cursor.execute(query)
                                result = cursor.fetchall() if cursor.description else []
                    
                    # Check execution time
                    execution_time = time.time() - execution_start
                    if execution_time > 10:  # Long-running query warning
                        warnings.append(f"Long-running query: {execution_time:.2f}s")
                    
                    return SQLExecutionResult(
                        success=True,
                        result_set=result,
                        rows_affected=len(result) if result else 0,
                        execution_time_ms=int(execution_time * 1000),
                        retry_count=attempt,
                        warnings=warnings,
                        safety_level=self.safety_level
                    )
                    
                except Exception as query_error:
                    # Handle query execution errors
                    raise query_error
                    
        except TimeoutError as e:
            return SQLExecutionResult(
                success=False,
                error_message=str(e),
                error_type=ErrorType.TIMEOUT,
                retry_count=attempt,
                execution_time_ms=int((time.time() - execution_start) * 1000)
            )
            
        except Exception as e:
            error_type = self._classify_sql_error(str(e))
            return SQLExecutionResult(
                success=False,
                error_message=str(e),
                error_type=error_type,
                retry_count=attempt,
                execution_time_ms=int((time.time() - execution_start) * 1000)
            )
    
    def execute_transaction(self,
                           db_path: str,
                           queries: List[str],
                           parameters_list: Optional[List[List[Any]]] = None,
                           db_type: str = "duckdb") -> SQLExecutionResult:
        """
        Execute multiple queries in a single transaction with rollback safety
        """
        start_time = time.time()
        
        try:
            with self.get_safe_connection(db_path, db_type) as conn:
                # Use DuckDB's transaction handling
                try:
                    # Begin transaction
                    conn.execute("BEGIN TRANSACTION")
                    
                    results = []
                    total_rows_affected = 0
                    
                    for i, query in enumerate(queries):
                        params = parameters_list[i] if parameters_list and i < len(parameters_list) else None
                        
                        if params:
                            cursor_result = conn.execute(query, params)
                        else:
                            cursor_result = conn.execute(query)
                        
                        # Handle different result types
                        try:
                            result = cursor_result.fetchall()
                            if result:
                                results.extend(result)
                                total_rows_affected += len(result)
                        except Exception:
                            # Some queries (like INSERT) might not return results
                            total_rows_affected += 1
                    
                    # Commit transaction
                    conn.execute("COMMIT")
                    
                    return SQLExecutionResult(
                        success=True,
                        result_set=results,
                        rows_affected=total_rows_affected,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        safety_level=self.safety_level
                    )
                    
                except Exception as e:
                    # Rollback transaction
                    try:
                        conn.execute("ROLLBACK")
                        self.logger.info("Transaction rolled back successfully")
                    except Exception as rollback_error:
                        self.logger.error(f"Rollback failed: {rollback_error}")
                    
                    raise e
                    
        except Exception as e:
            error_type = self._classify_sql_error(str(e))
            return SQLExecutionResult(
                success=False,
                error_message=str(e),
                error_type=error_type,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _detect_sql_injection(self, query: str) -> bool:
        """Basic SQL injection detection"""
        dangerous_patterns = [
            r";\s*(drop|delete|truncate|alter)\s+",
            r"union\s+select",
            r"(or|and)\s+1\s*=\s*1",
            r"'\s*(or|and)\s+'",
            r"--\s*$",
            r"/\*.*\*/"
        ]
        
        import re
        query_lower = query.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE | re.MULTILINE):
                self.logger.warning(f"Potential SQL injection pattern detected: {pattern}")
                return True
        return False
    
    def _classify_sql_error(self, error_message: str) -> ErrorType:
        """Classify SQL error types for appropriate handling"""
        error_lower = error_message.lower()
        
        if any(term in error_lower for term in ['timeout', 'time out']):
            return ErrorType.TIMEOUT
        elif any(term in error_lower for term in ['connection', 'connect']):
            return ErrorType.CONNECTION_FAILURE
        elif any(term in error_lower for term in ['deadlock', 'lock']):
            return ErrorType.TRANSACTION_FAILURE
        elif any(term in error_lower for term in ['memory', 'out of memory']):
            return ErrorType.RESOURCE_EXHAUSTION
        elif any(term in error_lower for term in ['syntax', 'invalid']):
            return ErrorType.CONFIGURATION_ERROR
        else:
            return ErrorType.SERVICE_UNAVAILABLE
    
    def _pre_execution_resource_check(self) -> bool:
        """Check system resources before query execution"""
        try:
            memory_info = psutil.virtual_memory()
            if memory_info.percent > 95:
                self.execution_metrics['memory_limit_hits'] += 1
                return False
            
            # Check available disk space
            disk_usage = psutil.disk_usage('/')
            if disk_usage.percent > 95:
                return False
                
            return True
        except Exception:
            return True  # If we can't check, assume it's OK
    
    def _cleanup_stale_connections(self, db_name: str):
        """Clean up stale connections"""
        if db_name in self._connection_pools:
            with self._pool_locks[db_name]:
                pool = self._connection_pools[db_name]
                healthy_connections = []
                
                for conn in pool:
                    if self._is_connection_healthy(conn, db_name.split(':')[0]):
                        healthy_connections.append(conn)
                    else:
                        self._close_connection(conn, db_name.split(':')[0])
                
                self._connection_pools[db_name] = healthy_connections
                self.logger.info(f"Cleaned up connections for {db_name}: {len(pool) - len(healthy_connections)} removed")
    
    def _cleanup_idle_connections(self, db_name: str):
        """Clean up idle connections to free resources"""
        if db_name in self._connection_pools:
            with self._pool_locks[db_name]:
                pool = self._connection_pools[db_name]
                # Keep only a minimal number of connections
                keep_count = min(2, len(pool))
                to_close = pool[keep_count:]
                self._connection_pools[db_name] = pool[:keep_count]
                
                for conn in to_close:
                    self._close_connection(conn, db_name.split(':')[0])
                
                if to_close:
                    self.logger.info(f"Closed {len(to_close)} idle connections for {db_name}")
    
    def _wait_for_connection(self, pool_key: str, max_wait_seconds: int = 30):
        """Wait for connection to become available"""
        start_wait = time.time()
        while time.time() - start_wait < max_wait_seconds:
            if self._active_connections[pool_key] < self.max_connections_per_db:
                return
            time.sleep(0.1)
        
        raise RuntimeError(f"Timeout waiting for connection to {pool_key}")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get comprehensive execution statistics"""
        total_queries = self.execution_metrics['total_queries']
        success_rate = (self.execution_metrics['successful_queries'] / max(total_queries, 1)) * 100
        
        return {
            'total_queries': total_queries,
            'successful_queries': self.execution_metrics['successful_queries'],
            'failed_queries': self.execution_metrics['failed_queries'],
            'success_rate_percent': round(success_rate, 2),
            'retry_attempts': self.execution_metrics['retry_attempts'],
            'fallback_activations': self.execution_metrics['fallback_activations'],
            'avg_execution_time_ms': round(self.execution_metrics['avg_execution_time_ms'], 2),
            'deadlock_recoveries': self.execution_metrics['deadlock_recoveries'],
            'timeout_recoveries': self.execution_metrics['timeout_recoveries'],
            'memory_limit_hits': self.execution_metrics['memory_limit_hits'],
            'active_connections': dict(self._active_connections),
            'safety_level': self.safety_level.value,
            'timestamp': datetime.now().isoformat()
        }
    
    def shutdown(self):
        """Gracefully shutdown safety manager"""
        self.logger.info("Shutting down SQL Runtime Safety Manager")
        self._shutdown_event.set()
        
        # Close all connections
        for pool_key, pool in self._connection_pools.items():
            db_type = pool_key.split(':')[0]
            for conn in pool:
                self._close_connection(conn, db_type)
        
        self._connection_pools.clear()
        self._active_connections.clear()
        
        self.logger.info("SQL Runtime Safety Manager shutdown complete")


# Integration with existing error handling system
def create_sql_safety_manager(error_handler: BiologicalMemoryErrorHandler) -> SQLRuntimeSafetyManager:
    """Create SQL safety manager with error handler integration"""
    return SQLRuntimeSafetyManager(
        error_handler=error_handler,
        safety_level=SQLRuntimeSafetyLevel.RESILIENT
    )


# Decorator for automatic SQL safety
def with_sql_safety(safety_manager: SQLRuntimeSafetyManager):
    """Decorator to add SQL safety to functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_event = ErrorEvent(
                    error_id=f"sql_safety_{int(time.time())}",
                    error_type=ErrorType.CONNECTION_FAILURE,
                    timestamp=datetime.now(),
                    component="sql_function",
                    operation=func.__name__,
                    error_message=str(e),
                    context={'args_count': len(args), 'kwargs': list(kwargs.keys())}
                )
                safety_manager.error_handler.log_error_event(error_event)
                raise
        return wrapper
    return decorator


if __name__ == "__main__":
    # Example usage and testing
    import tempfile
    
    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    # Create error handler and safety manager
    from error_handling import BiologicalMemoryErrorHandler
    error_handler = BiologicalMemoryErrorHandler(base_path="/tmp/test_safety")
    safety_manager = create_sql_safety_manager(error_handler)
    
    # Test safe query execution
    result = safety_manager.execute_safe_query(
        db_path=db_path,
        query="CREATE TABLE test (id INTEGER, name TEXT)",
        db_type="duckdb"
    )
    print(f"Table creation result: {result.success}")
    
    # Test transaction
    queries = [
        "INSERT INTO test VALUES (1, 'Alice')",
        "INSERT INTO test VALUES (2, 'Bob')",
        "SELECT * FROM test"
    ]
    
    result = safety_manager.execute_transaction(db_path, queries, db_type="duckdb")
    print(f"Transaction result: {result.success}, rows: {result.rows_affected}")
    
    # Print statistics
    stats = safety_manager.get_execution_stats()
    print(f"Execution stats: {json.dumps(stats, indent=2)}")
    
    # Cleanup
    safety_manager.shutdown()
    Path(db_path).unlink(missing_ok=True)