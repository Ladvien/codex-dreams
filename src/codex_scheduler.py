#!/usr/bin/env python3
"""
Simple scheduler for Codex Dreams insights generation.
Runs generate_insights.py on a schedule.
"""

import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .codex_config import CodexConfig


class CodexScheduler:
    """Simple scheduler that runs insights generation on interval"""

    def __init__(self, config: CodexConfig):
        self.config = config
        self.running = False
        self.last_run: Optional[datetime] = None
        self.last_success: Optional[datetime] = None
        self.run_count = 0
        self.success_count = 0

        # Set up logging
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up logging to file"""
        self.config.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Clear any existing handlers to avoid duplicates
        logger = logging.getLogger()
        logger.handlers = []

        # Only add file handler - stdout is redirected to log file by the
        # service
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(self.config.log_file)],
        )
        self.logger = logging.getLogger(__name__)

    def run_once(self) -> bool:
        """Run insights generation once"""
        self.logger.info("Running insights generation...")
        self.run_count += 1
        self.last_run = datetime.now()

        try:
            # Find the generate_insights.py script
            script_path = Path(__file__).parent / "generate_insights.py"

            if not script_path.exists():
                self.logger.error(f"Could not find generate_insights.py at {script_path}")
                return False

            # Set environment variables from config
            env = {
                **dict(os.environ),  # Keep existing environment
                "POSTGRES_DB_URL": self.config.postgres_url,
                "OLLAMA_URL": self.config.ollama_url,
                "OLLAMA_MODEL": self.config.ollama_model,
                "DUCKDB_PATH": self.config.expanded_duckdb_path,
            }

            # Run the script
            result = subprocess.run(
                [sys.executable, str(script_path)],
                env=env,
                cwd=Path(__file__).parent.parent,  # codex-dreams directory
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                self.success_count += 1
                self.last_success = datetime.now()
                self.logger.info(f"✅ Insights generation completed successfully")

                # Log any output from the script
                if result.stdout:
                    for line in result.stdout.strip().split("\n"):
                        if line.strip():
                            self.logger.info(f"Script output: {line}")

                return True
            else:
                self.logger.error(f"❌ Insights generation failed with code {result.returncode}")
                if result.stderr:
                    for line in result.stderr.strip().split("\n"):
                        if line.strip():
                            self.logger.error(f"Script error: {line}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("❌ Insights generation timed out after 5 minutes")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error running insights generation: {e}")
            return False

    def run(self) -> None:
        """Run the scheduler loop"""
        self.running = True
        interval_minutes = self.config.parse_schedule()
        interval_seconds = interval_minutes * 60

        self.logger.info(f"Starting Codex scheduler")
        self.logger.info(f"Schedule: {self.config.schedule} ({interval_minutes} minutes)")
        self.logger.info(f"Database: {self.config.postgres_url}")
        self.logger.info(f"Ollama: {self.config.ollama_url} ({self.config.ollama_model})")
        self.logger.info(f"DuckDB: {self.config.expanded_duckdb_path}")

        # Run once immediately on startup
        self.run_once()

        while self.running:
            try:
                self.logger.info(f"Next run in {interval_minutes} minutes...")

                # Sleep in 1-second intervals so we can respond to shutdown
                # quickly
                for _ in range(interval_seconds):
                    if not self.running:
                        break
                    time.sleep(1)

                if self.running:
                    self.run_once()

            except KeyboardInterrupt:
                self.logger.info("Received shutdown signal")
                break
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                # Continue running despite errors
                time.sleep(60)  # Wait a minute before trying again

        self.logger.info("Scheduler stopped")

    def stop(self) -> None:
        """Stop the scheduler"""
        self.running = False

    def get_stats(self) -> dict:
        """Get scheduler statistics"""
        return {
            "running": self.running,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "last_run": self.last_run,
            "last_success": self.last_success,
            "success_rate": (self.success_count / self.run_count if self.run_count > 0 else 0),
        }


# Import os here to avoid issues with the env dict
