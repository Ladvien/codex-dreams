#!/usr/bin/env python3
"""
Simple service management for Codex Dreams.
Handles starting/stopping the background process.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from types import FrameType

import psutil

from .codex_config import CodexConfig


class CodexService:
    """Simple service manager for Codex Dreams"""

    def __init__(self, config: CodexConfig):
        self.config = config
        self.pid_file = config.pid_file

    def is_running(self) -> bool:
        """Check if the service is currently running"""
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            # Check if process with this PID exists and is our process
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                # Simple check: if it's a Python process, assume it's ours
                if "python" in proc.name().lower():
                    return True

            # PID file exists but process doesn't, clean up
            self.pid_file.unlink()
            return False

        except (ValueError, FileNotFoundError, psutil.Error):
            # Corrupted PID file, clean up
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False

    def get_status(self) -> dict:
        """Get detailed service status"""
        if not self.is_running():
            return {
                "running": False,
                "pid": None,
                "uptime": None,
                "memory_mb": None,
                "next_run": None,
            }

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            proc = psutil.Process(pid)
            uptime_seconds = time.time() - proc.create_time()

            # Calculate next run time based on schedule
            interval_minutes = self.config.parse_schedule()
            interval_seconds = interval_minutes * 60

            # Simple approximation - actual next run depends on when process started
            time_since_start = uptime_seconds % interval_seconds
            next_run_seconds = interval_seconds - time_since_start

            return {
                "running": True,
                "pid": pid,
                "uptime": uptime_seconds,
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
                "next_run": next_run_seconds,
                "schedule": self.config.schedule,
            }

        except (ValueError, FileNotFoundError, psutil.Error):
            return {"running": False, "error": "Could not get process info"}

    def start(self, foreground: bool = False) -> bool:
        """Start the service"""
        if self.is_running():
            print("✅ Codex is already running")
            return True

        # Ensure directories exist
        self.config.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

        if foreground:
            # Run in foreground
            print("🚀 Starting Codex in foreground mode...")
            print("Press Ctrl+C to stop")
            try:
                self._run_scheduler()
                return True
            except KeyboardInterrupt:
                print("\n🛑 Stopped by user")
                return True
        else:
            # Run in background
            print("🚀 Starting Codex in background...")

            try:
                # Start the scheduler as a subprocess
                cmd = [
                    sys.executable,
                    "-c",
                    f"from src.codex_service import run_scheduler_daemon; run_scheduler_daemon()",
                ]

                with open(self.config.log_file, "a") as log_file:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=log_file,
                        stderr=log_file,
                        cwd=Path(__file__).parent.parent,  # codex-dreams directory
                    )

                # Write PID file
                with open(self.pid_file, "w") as f:
                    f.write(str(proc.pid))

                # Give it a moment to start
                time.sleep(1)

                if self.is_running():
                    print(f"✅ Codex started successfully (PID: {proc.pid})")
                    print(f"📊 Schedule: {self.config.schedule}")
                    print(f"📝 Logs: {self.config.log_file}")
                    return True
                else:
                    print("❌ Failed to start Codex")
                    return False

            except Exception as e:
                print(f"❌ Failed to start service: {e}")
                return False

    def stop(self) -> bool:
        """Stop the service"""
        if not self.is_running():
            print("⏹️  Codex is not running")
            return True

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            print(f"🛑 Stopping Codex (PID: {pid})...")

            # Try graceful shutdown first
            os.kill(pid, signal.SIGTERM)

            # Wait for it to stop
            for _ in range(10):  # Wait up to 10 seconds
                if not psutil.pid_exists(pid):
                    break
                time.sleep(1)
            else:
                # Force kill if it didn't stop gracefully
                print("Force stopping...")
                os.kill(pid, signal.SIGKILL)

            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()

            print("✅ Codex stopped")
            return True

        except (ValueError, FileNotFoundError, ProcessLookupError):
            # Process already gone, just clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            print("✅ Codex stopped")
            return True
        except Exception as e:
            print(f"❌ Failed to stop service: {e}")
            return False

    def restart(self) -> bool:
        """Restart the service"""
        print("🔄 Restarting Codex...")
        self.stop()
        time.sleep(1)
        return self.start()

    def _run_scheduler(self) -> None:
        """Run the scheduler loop"""
        from .codex_scheduler import CodexScheduler

        scheduler = CodexScheduler(self.config)
        scheduler.run()


def run_scheduler_daemon() -> None:
    """Entry point for daemon process"""

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum: int, frame: Optional[FrameType]) -> None:
        # Silent shutdown on signal
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Load config and start scheduler
    from .codex_config import get_config
    from .codex_scheduler import CodexScheduler

    config = get_config()
    scheduler = CodexScheduler(config)

    # Don't print here - the scheduler logs everything
    try:
        scheduler.run()
    except KeyboardInterrupt:
        # Silent shutdown for Ctrl+C
        sys.exit(0)
    except Exception as e:
        # Log critical errors before exit
        import logging

        logging.error(f"Scheduler error: {e}")
        sys.exit(1)


def format_uptime(seconds: float) -> str:
    """Format uptime in human readable format"""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        return f"{int(seconds/60)} minutes"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        return f"{days}d {hours}h"


def format_time_until(seconds: float) -> str:
    """Format time until next run"""
    if seconds < 60:
        return f"in {int(seconds)} seconds"
    elif seconds < 3600:
        return f"in {int(seconds/60)} minutes"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"in {hours}h {minutes}m"
