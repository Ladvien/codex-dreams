#!/usr/bin/env python3
"""
Biological Memory Pipeline Orchestrator - BMP-008 Enhanced with BMP-013
Implements biological rhythm scheduling with comprehensive error handling and recovery
"""

import subprocess
import logging
import time
import json
import threading
import signal
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import duckdb
import schedule

# Import BMP-013 error handling system
from error_handling import (
    BiologicalMemoryErrorHandler, ErrorType, ErrorEvent, 
    with_error_handling, CircuitBreaker
)

# Import SQL runtime safety system - BMP-HIGH-006
from sql_runtime_safety import (
    SQLRuntimeSafetyManager, SQLRuntimeSafetyLevel, create_sql_safety_manager
)

# Import LLM integration service
from llm_integration_service import (
    initialize_llm_service, register_llm_functions, get_llm_service
)

# Import health monitoring service
from health_check_service import (
    initialize_health_monitor, get_health_monitor, ComprehensiveHealthMonitor
)

# Import automated recovery service
from automated_recovery_service import (
    initialize_recovery_service, get_recovery_service, AutomatedRecoveryService
)


class BiologicalMemoryOrchestrator:
    """
    Orchestrates biological memory processing following circadian rhythms
    """
    
    def __init__(self, base_path: str = "/Users/ladvien/codex-dreams/biological_memory", log_dir: Optional[str] = None):
        self.base_path = Path(base_path)
        
        # Environment variables for BMP-013
        self.max_db_connections = int(os.getenv('MAX_DB_CONNECTIONS', '160'))
        self.ollama_timeout_seconds = int(os.getenv('OLLAMA_GENERATION_TIMEOUT_SECONDS', '300'))
        self.circuit_breaker_enabled = os.getenv('MCP_CIRCUIT_BREAKER_ENABLED', 'true').lower() == 'true'
        
        # Set log directory - default to /var/log/biological_memory, fallback to project logs
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            try:
                self.log_dir = Path("/var/log/biological_memory")
                self.log_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                # Fallback to project directory if /var/log is not writable
                self.log_dir = self.base_path / "logs"
                self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self.setup_logging()
        
        # Initialize BMP-013 error handling system
        self.error_handler = BiologicalMemoryErrorHandler(
            base_path=str(self.base_path),
            circuit_breaker_enabled=self.circuit_breaker_enabled,
            max_db_connections=self.max_db_connections,
            ollama_timeout_seconds=self.ollama_timeout_seconds
        )
        
        # Initialize BMP-HIGH-006 SQL runtime safety system
        self.sql_safety = create_sql_safety_manager(self.error_handler)
        
        # Initialize LLM integration service
        self._init_llm_service()
        
        # Initialize health monitoring system
        self._init_health_monitoring()
        
        # Initialize automated recovery system
        self._init_automated_recovery()
        
        # Processing state
        self.is_wake_hours = False
        self.working_memory_thread = None
        self.stop_working_memory = threading.Event()
        
        # Error tracking
        self.error_counts = {
            'working_memory': 0,
            'stm': 0,
            'consolidation': 0,
            'deep_consolidation': 0,
            'rem_sleep': 0,
            'homeostasis': 0
        }
        
        # Performance tracking
        self.performance_metrics = {
            'last_working_memory': None,
            'last_stm': None,
            'last_consolidation': None,
            'last_deep_consolidation': None,
            'last_rem_sleep': None,
            'last_homeostasis': None
        }
        
        self.logger.info("Biological Memory Orchestrator initialized")

    def _init_llm_service(self):
        """Initialize LLM integration service with Ollama"""
        try:
            # Get Ollama URL from environment
            ollama_url = os.getenv('OLLAMA_URL', 'http://192.168.1.110:11434')
            
            # Initialize LLM service with error handler
            llm_service = initialize_llm_service(
                ollama_url=ollama_url,
                model_name="gpt-oss:20b",
                cache_db_path=str(self.base_path / "dbs" / "llm_cache.duckdb"),
                error_handler=self.error_handler
            )
            
            # Test database connection and register UDF functions
            db_path = self.base_path / 'dbs' / 'memory.duckdb'
            with duckdb.connect(str(db_path)) as conn:
                success = register_llm_functions(conn)
                if success:
                    self.logger.info("LLM UDF functions registered successfully")
                    
                    # Test LLM service connectivity
                    health = llm_service.health_check()
                    if health['status'] == 'healthy':
                        self.logger.info(f"LLM service healthy: {ollama_url}")
                    else:
                        self.logger.warning(f"LLM service unhealthy: {health.get('error', 'Unknown error')}")
                else:
                    self.logger.error("Failed to register LLM UDF functions")
                    
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM service: {e}")
            # Continue without LLM - fallbacks will handle this

    def _init_health_monitoring(self):
        """Initialize comprehensive health monitoring system"""
        try:
            # Get configuration from environment variables
            enable_http_endpoints = os.getenv('HEALTH_HTTP_ENDPOINTS', 'true').lower() == 'true'
            http_port = int(os.getenv('HEALTH_HTTP_PORT', '8080'))
            alert_webhook_url = os.getenv('HEALTH_ALERT_WEBHOOK_URL')
            
            # Initialize health monitor
            self.health_monitor = initialize_health_monitor(
                base_path=str(self.base_path),
                error_handler=self.error_handler,
                enable_http_endpoints=enable_http_endpoints,
                http_port=http_port,
                alert_webhook_url=alert_webhook_url
            )
            
            # Start continuous monitoring if enabled
            if os.getenv('HEALTH_CONTINUOUS_MONITORING', 'true').lower() == 'true':
                self.health_monitor.start_monitoring()
                self.logger.info(f"Health monitoring started on port {http_port}")
            else:
                self.logger.info("Health monitoring initialized (manual checks only)")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize health monitoring: {e}")
            # Continue without health monitoring - not critical for basic operation

    def _init_automated_recovery(self):
        """Initialize automated recovery system"""
        try:
            # Get configuration from environment variables
            recovery_enabled = os.getenv('AUTOMATED_RECOVERY_ENABLED', 'true').lower() == 'true'
            dry_run = os.getenv('RECOVERY_DRY_RUN', 'false').lower() == 'true'
            
            # Initialize recovery service
            self.recovery_service = initialize_recovery_service(
                base_path=str(self.base_path),
                error_handler=self.error_handler,
                recovery_enabled=recovery_enabled,
                dry_run=dry_run
            )
            
            # Start automated recovery if enabled
            if recovery_enabled:
                self.recovery_service.start_automated_recovery()
                mode = "DRY RUN" if dry_run else "PRODUCTION"
                self.logger.info(f"Automated recovery started ({mode} mode)")
            else:
                self.logger.info("Automated recovery initialized but disabled")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize automated recovery: {e}")
            # Continue without recovery - not critical for basic operation

    def setup_logging(self):
        """Set up comprehensive logging for biological rhythms"""
        self.logger = logging.getLogger('BiologicalMemory')
        self.logger.setLevel(logging.INFO)
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Main log file
        main_handler = logging.FileHandler(self.log_dir / 'orchestrator.log')
        main_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(main_handler)
        
        # Console output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(console_handler)

    def run_dbt_command(self, command: str, log_file: str, timeout: int = 300) -> bool:
        """
        Execute dbt command with comprehensive error handling and recovery - BMP-013 Enhanced
        """
        start_time = datetime.now()
        log_path = self.log_dir / log_file
        operation_id = f"dbt_{int(time.time())}"
        
        def execute_dbt():
            # Change to biological memory directory
            full_command = f"cd {self.base_path} && {command}"
            
            # Apply timeout from environment or default
            effective_timeout = min(timeout, self.ollama_timeout_seconds) if 'llm' in command else timeout
            
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=effective_timeout
            )
            return result
        
        try:
            self.logger.info(f"Starting dbt command: {command}")
            
            # Execute with retry logic
            result = self.error_handler.exponential_backoff_retry(
                execute_dbt,
                max_retries=3,
                base_delay=2.0,
                exceptions=(subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError)
            )
            
            # Enhanced logging with error context
            self._safe_log_output(log_path, {
                'command': command,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'timeout_used': timeout,
                'execution_time': (datetime.now() - start_time).total_seconds()
            })
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                self.logger.info(f"dbt command completed successfully in {duration:.2f}s: {command}")
                return True
            else:
                # Enhanced error handling with dead letter queue
                error_event = ErrorEvent(
                    error_id=operation_id,
                    error_type=ErrorType.SERVICE_UNAVAILABLE,
                    timestamp=datetime.now(),
                    component="dbt_executor",
                    operation=command.split()[0],  # dbt subcommand
                    error_message=result.stderr or "Command failed with no stderr",
                    context={
                        'command': command,
                        'return_code': result.returncode,
                        'duration_seconds': duration,
                        'stdout_length': len(result.stdout) if result.stdout else 0
                    }
                )
                self.error_handler.log_error_event(error_event)
                
                # Add to dead letter queue for critical operations
                if any(critical in command for critical in ['consolidation', 'long_term', 'homeostasis']):
                    self.error_handler.dead_letter_queue.enqueue(
                        message_id=operation_id,
                        operation=f"dbt_command_{command.split()[1] if len(command.split()) > 1 else 'unknown'}",
                        memory_data={'command': command, 'log_file': log_file},
                        error_type=ErrorType.SERVICE_UNAVAILABLE,
                        error_message=result.stderr or "Command execution failed"
                    )
                
                return False
                
        except subprocess.TimeoutExpired as e:
            error_event = ErrorEvent(
                error_id=operation_id,
                error_type=ErrorType.TIMEOUT,
                timestamp=datetime.now(),
                component="dbt_executor", 
                operation="timeout",
                error_message=f"Command timed out after {timeout}s",
                context={'command': command, 'timeout_seconds': timeout}
            )
            self.error_handler.log_error_event(error_event)
            return False
            
        except Exception as e:
            error_event = ErrorEvent(
                error_id=operation_id,
                error_type=ErrorType.CONNECTION_FAILURE,
                timestamp=datetime.now(),
                component="dbt_executor",
                operation="execute",
                error_message=str(e),
                context={'command': command}
            )
            self.error_handler.log_error_event(error_event)
            return False
    
    def _safe_log_output(self, log_path: Path, log_data: Dict[str, Any]):
        """Safely log command output with error handling"""
        try:
            with open(log_path, 'a') as f:
                f.write(f"\n=== {datetime.now()} ===\n")
                for key, value in log_data.items():
                    f.write(f"{key.upper()}: {value}\n")
                f.write("="*50 + "\n")
        except Exception as e:
            self.logger.warning(f"Failed to write to log file {log_path}: {e}")

    def health_check(self) -> bool:
        """
        Perform comprehensive health check with enhanced error handling - BMP-013 Enhanced
        """
        health_results = {
            'database_accessible': False,
            'system_resources': {},
            'error_summary': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Test database connectivity with SQL safety system - BMP-HIGH-006
            db_path = self.base_path / 'dbs' / 'memory.duckdb'
            
            # Use SQL safety manager for bulletproof database operations
            result = self.sql_safety.execute_safe_query(
                db_path=str(db_path),
                query="SELECT table_name FROM information_schema.tables",
                db_type="duckdb",
                timeout_override=10
            )
            
            if result.success:
                table_names = [row[0] for row in result.result_set] if result.result_set else []
                
                # Enhanced health checks with SQL safety metrics
                health_results.update({
                    'database_accessible': True,
                    'table_count': len(table_names),
                    'tables': table_names,
                    'db_file_size_mb': (db_path.stat().st_size / 1024 / 1024) if db_path.exists() else 0,
                    'sql_safety_stats': self.sql_safety.get_execution_stats(),
                    'query_execution_time_ms': result.execution_time_ms
                })
            else:
                health_results.update({
                    'database_accessible': False,
                    'connection_error': result.error_message,
                    'sql_safety_stats': self.sql_safety.get_execution_stats()
                })
                table_names = []
            
            # System resource monitoring
            health_results['system_resources'] = self.error_handler.monitor_system_resources()
            
            # Error handling summary
            health_results['error_summary'] = self.error_handler.get_error_summary()
            
            # Retry dead letter messages during health check
            try:
                self.error_handler.retry_dead_letter_messages()
            except Exception as retry_error:
                self.logger.warning(f"Dead letter retry during health check failed: {retry_error}")
            
            # Log comprehensive health status
            self._safe_log_output(self.log_dir / 'health_status.jsonl', health_results)
            
            # Determine overall health including SQL safety metrics
            sql_stats = health_results.get('sql_safety_stats', {})
            sql_success_rate = sql_stats.get('success_rate_percent', 0)
            
            overall_healthy = (
                health_results['database_accessible'] and
                len(table_names) > 0 and
                health_results['system_resources'].get('memory_percent', 100) < 95 and
                health_results['system_resources'].get('disk_percent', 100) < 95 and
                sql_success_rate >= 90  # SQL operations must be at least 90% successful
            )
            
            if overall_healthy:
                self.logger.info(
                    f"Health check passed: {len(table_names)} tables, "
                    f"Memory: {health_results['system_resources'].get('memory_percent', 0):.1f}%, "
                    f"Disk: {health_results['system_resources'].get('disk_percent', 0):.1f}%"
                )
            else:
                self.logger.warning("Health check detected issues - see health_status.jsonl for details")
            
            return overall_healthy
            
        except Exception as e:
            # Enhanced error reporting
            error_event = ErrorEvent(
                error_id=f"health_check_{int(time.time())}",
                error_type=ErrorType.CONNECTION_FAILURE,
                timestamp=datetime.now(),
                component="health_monitor",
                operation="health_check",
                error_message=str(e),
                context=health_results
            )
            self.error_handler.log_error_event(error_event)
            
            health_results.update({
                'health_check_failed': True,
                'error_message': str(e)
            })
            
            # Still try to log what we can
            self._safe_log_output(self.log_dir / 'health_status.jsonl', health_results)
            
            return False

    def working_memory_continuous(self):
        """
        Continuous working memory processing during wake hours (6am-10pm)
        Runs every 5 seconds during wake hours
        """
        self.logger.info("Starting continuous working memory processing")
        
        while not self.stop_working_memory.is_set():
            try:
                if self.is_wake_hours:
                    success = self.run_dbt_command(
                        "dbt run --select tag:working_memory --quiet",
                        "working_memory.log",
                        timeout=10  # Short timeout for frequent operations
                    )
                    
                    if success:
                        self.performance_metrics['last_working_memory'] = datetime.now()
                        self.error_counts['working_memory'] = 0
                    else:
                        self.error_counts['working_memory'] += 1
                        
                    # If too many errors, increase sleep time
                    if self.error_counts['working_memory'] > 5:
                        self.logger.warning("High working memory error count, increasing sleep interval")
                        time.sleep(15)
                    else:
                        time.sleep(5)
                else:
                    # During sleep hours, check less frequently
                    time.sleep(60)
                    
            except Exception as e:
                self.logger.error(f"Error in working memory continuous processing: {e}")
                self.error_counts['working_memory'] += 1
                time.sleep(10)

    def stm_processing(self):
        """
        Short-term memory processing every 5 minutes
        """
        self.logger.info("Running STM processing")
        success = self.run_dbt_command(
            "dbt run --select short_term_memory --quiet",
            "stm.log"
        )
        
        if success:
            self.performance_metrics['last_stm'] = datetime.now()
            self.error_counts['stm'] = 0
        else:
            self.error_counts['stm'] += 1

    def consolidation_processing(self):
        """
        Memory consolidation processing every hour
        """
        self.logger.info("Running consolidation processing")
        success = self.run_dbt_command(
            "dbt run --select consolidation --quiet",
            "consolidation.log"
        )
        
        if success:
            self.performance_metrics['last_consolidation'] = datetime.now()
            self.error_counts['consolidation'] = 0
        else:
            self.error_counts['consolidation'] += 1

    def deep_consolidation(self):
        """
        Deep consolidation during slow-wave sleep (2-4 AM)
        """
        self.logger.info("Running deep consolidation (slow-wave sleep)")
        success = self.run_dbt_command(
            "dbt run --select long_term_memory --full-refresh --quiet",
            "deep_consolidation.log",
            timeout=600  # Longer timeout for full refresh
        )
        
        if success:
            self.performance_metrics['last_deep_consolidation'] = datetime.now()
            self.error_counts['deep_consolidation'] = 0
        else:
            self.error_counts['deep_consolidation'] += 1

    def rem_sleep_processing(self):
        """
        REM sleep creative processing
        """
        self.logger.info("Running REM sleep creative processing")
        success = self.run_dbt_command(
            "dbt run-operation strengthen_associations --quiet",
            "rem_sleep.log"
        )
        
        if success:
            self.performance_metrics['last_rem_sleep'] = datetime.now()
            self.error_counts['rem_sleep'] = 0
        else:
            self.error_counts['rem_sleep'] += 1

    def synaptic_homeostasis(self):
        """
        Weekly synaptic homeostasis (Sunday 3 AM)
        """
        self.logger.info("Running weekly synaptic homeostasis")
        success = self.run_dbt_command(
            "dbt run-operation synaptic_homeostasis --quiet",
            "homeostasis.log",
            timeout=600
        )
        
        if success:
            self.performance_metrics['last_homeostasis'] = datetime.now()
            self.error_counts['homeostasis'] = 0
        else:
            self.error_counts['homeostasis'] += 1

    def update_wake_sleep_state(self):
        """
        Update wake/sleep state based on current time
        """
        current_hour = datetime.now().hour
        was_wake_hours = self.is_wake_hours
        self.is_wake_hours = 6 <= current_hour <= 22  # 6am to 10pm
        
        if was_wake_hours != self.is_wake_hours:
            if self.is_wake_hours:
                self.logger.info("Entering wake hours - starting working memory processing")
            else:
                self.logger.info("Entering sleep hours - reducing working memory activity")

    def setup_schedules(self):
        """
        Set up all biological rhythm schedules
        """
        # Update wake/sleep state every hour
        schedule.every().hour.do(self.update_wake_sleep_state)
        
        # STM processing every 5 minutes
        schedule.every(5).minutes.do(self.stm_processing)
        
        # Consolidation every hour
        schedule.every().hour.do(self.consolidation_processing)
        
        # Health checks every 15 minutes
        schedule.every(15).minutes.do(self.health_check)
        
        # Deep consolidation during slow-wave sleep (2-4 AM)
        schedule.every().day.at("02:00").do(self.deep_consolidation)
        schedule.every().day.at("03:00").do(self.deep_consolidation)
        schedule.every().day.at("04:00").do(self.deep_consolidation)
        
        # REM sleep processing every 90 minutes during night (10pm-6am)
        schedule.every().day.at("22:00").do(self.rem_sleep_processing)
        schedule.every().day.at("23:30").do(self.rem_sleep_processing)
        schedule.every().day.at("01:00").do(self.rem_sleep_processing)
        schedule.every().day.at("02:30").do(self.rem_sleep_processing)
        schedule.every().day.at("04:00").do(self.rem_sleep_processing)
        schedule.every().day.at("05:30").do(self.rem_sleep_processing)
        
        # Weekly synaptic homeostasis (Sunday 3 AM)
        schedule.every().sunday.at("03:00").do(self.synaptic_homeostasis)
        
        self.logger.info("All biological rhythm schedules configured")

    def start_working_memory_thread(self):
        """
        Start the working memory continuous processing thread
        """
        if self.working_memory_thread is None or not self.working_memory_thread.is_alive():
            self.stop_working_memory.clear()
            self.working_memory_thread = threading.Thread(
                target=self.working_memory_continuous,
                daemon=True
            )
            self.working_memory_thread.start()
            self.logger.info("Working memory continuous processing thread started")

    def stop_working_memory_thread(self):
        """
        Stop the working memory continuous processing thread
        """
        self.stop_working_memory.set()
        if self.working_memory_thread and self.working_memory_thread.is_alive():
            self.working_memory_thread.join(timeout=5)
            self.logger.info("Working memory continuous processing thread stopped")

    def signal_handler(self, signum, frame):
        """
        Handle shutdown signals gracefully - BMP-HIGH-006 Enhanced
        """
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop_working_memory_thread()
        
        # BMP-HIGH-006: Gracefully shutdown SQL safety system
        if hasattr(self, 'sql_safety'):
            self.sql_safety.shutdown()
            
        sys.exit(0)

    def run(self):
        """
        Main orchestrator loop
        """
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Initial setup
        self.setup_schedules()
        self.update_wake_sleep_state()
        self.health_check()
        self.start_working_memory_thread()
        
        self.logger.info("Biological Memory Orchestrator started - following circadian rhythms")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.stop_working_memory_thread()
            self.logger.info("Biological Memory Orchestrator stopped")


def main():
    """
    Entry point for the biological memory orchestrator
    """
    orchestrator = BiologicalMemoryOrchestrator()
    orchestrator.run()


if __name__ == "__main__":
    main()