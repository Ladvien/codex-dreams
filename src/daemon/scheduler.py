#!/usr/bin/env python3
"""
Cross-platform daemon scheduler for codex-dreams insights generation.
Supports Windows, macOS, and Linux with configurable scheduling.
"""

import os
import sys
import time
import signal
import threading
import logging
import json
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import subprocess
from collections import defaultdict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from generate_insights import main as generate_insights_main
except ImportError:
    # Fallback for when running as installed package
    def generate_insights_main():
        """Fallback to run generate_insights as subprocess"""
        try:
            subprocess.run([sys.executable, "-m", "src.generate_insights"], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to run generate_insights: {e}")
            raise

# Import config from the new module
from .config import DaemonConfig, load_config


class DaemonMetrics:
    """Track daemon performance metrics"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.runs_completed = 0
        self.runs_failed = 0
        self.total_runtime = timedelta()
        self.last_run_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.error_count_by_type = defaultdict(int)
    
    def record_success(self, runtime: timedelta):
        """Record a successful run"""
        self.runs_completed += 1
        self.total_runtime += runtime
        self.last_run_time = datetime.now()
        self.last_success_time = datetime.now()
    
    def record_failure(self, error: str, error_type: str = "unknown"):
        """Record a failed run"""
        self.runs_failed += 1
        self.last_run_time = datetime.now()
        self.last_error = error
        self.error_count_by_type[error_type] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        uptime = datetime.now() - self.start_time
        success_rate = (self.runs_completed / (self.runs_completed + self.runs_failed)) * 100 if (self.runs_completed + self.runs_failed) > 0 else 0
        avg_runtime = self.total_runtime / self.runs_completed if self.runs_completed > 0 else timedelta()
        
        return {
            "uptime": str(uptime),
            "runs_completed": self.runs_completed,
            "runs_failed": self.runs_failed,
            "success_rate": round(success_rate, 2),
            "average_runtime": str(avg_runtime),
            "last_run": self.last_run_time.isoformat() if self.last_run_time else None,
            "last_success": self.last_success_time.isoformat() if self.last_success_time else None,
            "last_error": self.last_error,
            "errors_by_type": dict(self.error_count_by_type)
        }


class DaemonScheduler:
    """Cross-platform daemon scheduler for insights generation"""
    
    def __init__(self, config: DaemonConfig):
        self.config = config
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.metrics = DaemonMetrics()
        self.logger = self._setup_logging()
        
        # Handle shutdown signals
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        if hasattr(signal, 'SIGHUP'):  # Unix-only
            signal.signal(signal.SIGHUP, self._signal_handler)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('codex_dreams_daemon')
        logger.setLevel(getattr(logging, self.config.log_level.upper(), logging.INFO))
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        if self.config.log_file:
            # Ensure log directory exists
            log_path = Path(self.config.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            handler = logging.FileHandler(self.config.log_file)
        else:
            handler = logging.StreamHandler()
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def _write_pid_file(self) -> None:
        """Write process ID to file"""
        if self.config.pid_file:
            pid_path = Path(self.config.pid_file)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            with open(pid_path, 'w') as f:
                f.write(str(os.getpid()))
            self.logger.debug(f"PID written to {pid_path}")
    
    def _remove_pid_file(self) -> None:
        """Remove PID file"""
        if self.config.pid_file:
            try:
                os.remove(self.config.pid_file)
                self.logger.debug(f"PID file {self.config.pid_file} removed")
            except FileNotFoundError:
                pass
    
    def _load_environment(self) -> None:
        """Load environment variables from file if specified"""
        if self.config.environment_file:
            env_path = Path(self.config.environment_file)
            if env_path.exists():
                try:
                    from dotenv import load_dotenv
                    load_dotenv(env_path)
                    self.logger.debug(f"Loaded environment from {env_path}")
                except ImportError:
                    self.logger.warning("python-dotenv not available, skipping .env file loading")
                except Exception as e:
                    self.logger.error(f"Failed to load environment file: {e}")
    
    def _run_insights_generation(self) -> bool:
        """Run the insights generation with retry logic and metrics"""
        start_time = datetime.now()
        
        for attempt in range(self.config.max_retries + 1):
            try:
                self.logger.info(f"Starting insights generation (attempt {attempt + 1}/{self.config.max_retries + 1})")
                
                # Change to working directory if specified
                original_cwd = None
                if self.config.working_directory:
                    original_cwd = os.getcwd()
                    os.chdir(self.config.working_directory)
                
                try:
                    # Run the insights generation
                    run_start = datetime.now()
                    generate_insights_main()
                    runtime = datetime.now() - run_start
                    
                    # Record success metrics
                    total_runtime = datetime.now() - start_time
                    self.metrics.record_success(total_runtime)
                    
                    self.logger.info(f"✅ Insights generation completed successfully in {runtime}")
                    self.logger.info(f"Total runs: {self.metrics.runs_completed}, Success rate: {self.metrics.get_stats()['success_rate']}%")
                    return True
                    
                finally:
                    # Restore original working directory
                    if original_cwd:
                        os.chdir(original_cwd)
                        
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                
                self.logger.error(f"❌ Insights generation failed (attempt {attempt + 1}): {error_msg}")
                
                # Log stack trace for debugging
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Exception traceback:\n{traceback.format_exc()}")
                
                if attempt < self.config.max_retries:
                    self.logger.info(f"⏳ Retrying in {self.config.retry_delay_seconds} seconds...")
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    # Record failure metrics
                    self.metrics.record_failure(error_msg, error_type)
                    self.logger.error(f"💥 Max retries exceeded, giving up. Total failures: {self.metrics.runs_failed}")
                    return False
        
        return False
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop with metrics reporting"""
        self.logger.info(f"🚀 Daemon scheduler started")
        self.logger.info(f"⏰ Running insights generation every {self.config.interval_minutes} minutes")
        self.logger.info(f"🔄 Max retries: {self.config.max_retries}, Retry delay: {self.config.retry_delay_seconds}s")
        
        # Log metrics every hour
        metrics_report_interval = 60  # minutes
        last_metrics_report = datetime.now()
        
        while self.running:
            next_run = datetime.now() + timedelta(minutes=self.config.interval_minutes)
            self.logger.debug(f"Next run scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Wait for the interval, checking for shutdown every 10 seconds
            elapsed = 0
            wait_interval = min(10, self.config.interval_minutes * 60)
            
            while elapsed < self.config.interval_minutes * 60 and self.running:
                time.sleep(wait_interval)
                elapsed += wait_interval
                
                # Report metrics periodically
                if (datetime.now() - last_metrics_report).total_seconds() >= metrics_report_interval * 60:
                    self._log_metrics()
                    last_metrics_report = datetime.now()
            
            if self.running:
                self._run_insights_generation()
    
    def _log_metrics(self) -> None:
        """Log current daemon metrics"""
        stats = self.metrics.get_stats()
        self.logger.info("📊 Daemon Metrics:")
        self.logger.info(f"  ⏱️  Uptime: {stats['uptime']}")
        self.logger.info(f"  ✅ Successful runs: {stats['runs_completed']}")
        self.logger.info(f"  ❌ Failed runs: {stats['runs_failed']}")
        self.logger.info(f"  📈 Success rate: {stats['success_rate']}%")
        self.logger.info(f"  ⚡ Average runtime: {stats['average_runtime']}")
        
        if stats['last_success']:
            self.logger.info(f"  🕐 Last success: {stats['last_success']}")
        
        if stats['last_error']:
            self.logger.info(f"  💥 Last error: {stats['last_error']}")
        
        if stats['errors_by_type']:
            self.logger.info(f"  📋 Error types: {stats['errors_by_type']}")
    
    def start(self, daemon_mode: bool = False) -> None:
        """Start the daemon scheduler"""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        # Load environment variables
        self._load_environment()
        
        # Write PID file
        self._write_pid_file()
        
        self.running = True
        
        if daemon_mode:
            # Run in background thread
            self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.thread.start()
            self.logger.info("Daemon started in background mode")
        else:
            # Run in foreground
            self.logger.info("Starting daemon in foreground mode")
            try:
                self._scheduler_loop()
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt, shutting down...")
            finally:
                self.stop()
    
    def stop(self) -> None:
        """Stop the daemon scheduler"""
        if not self.running:
            return
        
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.logger.info("Waiting for scheduler thread to finish...")
            self.thread.join(timeout=30)
        
        self._remove_pid_file()
        self.logger.info("Daemon stopped")
    
    def status(self) -> Dict[str, Any]:
        """Get daemon status information including metrics"""
        status_info = {
            "running": self.running,
            "config": self.config.get_effective_config(),
            "pid": os.getpid() if self.running else None,
            "metrics": self.metrics.get_stats(),
        }
        
        if self.config.pid_file:
            pid_path = Path(self.config.pid_file)
            status_info["pid_file_exists"] = pid_path.exists()
            if pid_path.exists():
                try:
                    with open(pid_path) as f:
                        status_info["pid_file_content"] = int(f.read().strip())
                except (ValueError, IOError):
                    status_info["pid_file_content"] = None
        
        return status_info




def main():
    """Main entry point for daemon scheduler"""
    import argparse
    from .config import get_default_config_path, load_config
    
    parser = argparse.ArgumentParser(description="Codex Dreams Daemon Scheduler")
    parser.add_argument("--config", type=Path, default=get_default_config_path(),
                       help="Configuration file path")
    parser.add_argument("--daemon", action="store_true",
                       help="Run in daemon mode (background)")
    parser.add_argument("--interval", type=int, 
                       help="Interval between runs in minutes")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Log level")
    parser.add_argument("--log-file", type=Path,
                       help="Log file path")
    parser.add_argument("--pid-file", type=Path,
                       help="PID file path")
    parser.add_argument("--working-dir", type=Path,
                       help="Working directory")
    parser.add_argument("--env-file", type=Path,
                       help="Environment file (.env)")
    
    args = parser.parse_args()
    
    # Load configuration using new config system
    config = load_config(args.config)
    
    # Override with command line arguments
    if args.interval is not None:
        config.interval_minutes = args.interval
    if args.log_level:
        config.log_level = args.log_level
    if args.log_file:
        config.log_file = str(args.log_file)
    if args.pid_file:
        config.pid_file = str(args.pid_file)
    if args.working_dir:
        config.working_directory = str(args.working_dir)
    if args.env_file:
        config.environment_file = str(args.env_file)
    
    # Save updated configuration
    config.to_file(args.config)
    
    # Create and start daemon
    scheduler = DaemonScheduler(config)
    scheduler.start(daemon_mode=args.daemon)


if __name__ == "__main__":
    main()