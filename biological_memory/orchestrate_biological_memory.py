#!/usr/bin/env python3
"""
Biological Memory Pipeline Orchestrator - BMP-008
Implements biological rhythm scheduling with error handling and recovery
"""

import subprocess
import logging
import time
import json
import threading
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import duckdb
import schedule


class BiologicalMemoryOrchestrator:
    """
    Orchestrates biological memory processing following circadian rhythms
    """
    
    def __init__(self, base_path: str = "/Users/ladvien/codex-dreams/biological_memory", log_dir: Optional[str] = None):
        self.base_path = Path(base_path)
        
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

    def setup_logging(self):
        """Set up comprehensive logging for biological rhythms"""
        self.logger = logging.getLogger('BiologicalMemory')
        self.logger.setLevel(logging.INFO)
        
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
        Execute dbt command with error handling and logging
        """
        start_time = datetime.now()
        log_path = self.log_dir / log_file
        
        try:
            self.logger.info(f"Starting dbt command: {command}")
            
            # Change to biological memory directory
            full_command = f"cd {self.base_path} && {command}"
            
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Log output
            with open(log_path, 'a') as f:
                f.write(f"\n=== {datetime.now()} ===\n")
                f.write(f"Command: {command}\n")
                f.write(f"Return code: {result.returncode}\n")
                f.write(f"STDOUT:\n{result.stdout}\n")
                if result.stderr:
                    f.write(f"STDERR:\n{result.stderr}\n")
                f.write("="*50 + "\n")
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                self.logger.info(f"dbt command completed successfully in {duration:.2f}s: {command}")
                return True
            else:
                self.logger.error(f"dbt command failed after {duration:.2f}s: {command}")
                self.logger.error(f"Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"dbt command timed out after {timeout}s: {command}")
            return False
        except Exception as e:
            self.logger.error(f"Exception running dbt command: {command}, Error: {e}")
            return False

    def health_check(self) -> bool:
        """
        Perform health check on the biological memory system
        """
        try:
            # Test database connectivity
            db_path = self.base_path / 'dbs' / 'memory.duckdb'
            conn = duckdb.connect(str(db_path))
            
            # Check if core tables exist
            tables = conn.execute("SELECT table_name FROM information_schema.tables").fetchall()
            table_names = [t[0] for t in tables]
            
            conn.close()
            
            # Log health status
            health_status = {
                'timestamp': datetime.now().isoformat(),
                'database_accessible': True,
                'table_count': len(table_names),
                'tables': table_names
            }
            
            with open(self.log_dir / 'health_status.jsonl', 'a') as f:
                f.write(json.dumps(health_status) + '\\n')
            
            self.logger.info(f"Health check passed: {len(table_names)} tables found")
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
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
        Handle shutdown signals gracefully
        """
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop_working_memory_thread()
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