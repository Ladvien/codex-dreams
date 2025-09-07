#!/usr/bin/env python3
"""
Biological Rhythm Pipeline Orchestration System

This module implements biologically-accurate memory consolidation timing based on:
- Circadian rhythms (24-hour biological clock)
- Ultradian rhythms (90-minute REM/NREM cycles)
- Memory consolidation research (McGaugh, 2000; Diekelmann & Born, 2010)
- Sleep stage neuroscience (Dement & Kleitman, 1957)

Key biological timing patterns:
- Continuous processing: Every 5 minutes (working memory refresh)
- Short-term consolidation: Every 20 minutes (episode integration)
- Long-term consolidation: Every 90 minutes (ultradian REM cycles)
- Deep sleep consolidation: 2-4 AM daily (systems consolidation)
- Synaptic homeostasis: Sunday 3 AM weekly (synaptic scaling)

Research Foundation:
- Miller, G. A. (1956). The magical number seven
- McGaugh, J. L. (2000). Memory consolidation
- Diekelmann, S. & Born, J. (2010). The memory function of sleep
- Tononi, G. & Cirelli, C. (2006). Sleep-dependent synaptic homeostasis
- Kleitman, N. & Rosenberg, R. S. (1953). Basic rest-activity cycle
"""

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from types import FrameType
from typing import Any, Dict, List, Optional

from src.daemon.config import DaemonConfig

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class BiologicalRhythmType(Enum):
    """Biological memory processing rhythm types with neuroscience timing"""

    # Continuous processing (Miller's working memory refresh)
    CONTINUOUS = "continuous"  # Every 5 minutes during wake hours

    # Short-term consolidation (episodic integration)
    SHORT_TERM = "short_term"  # Every 20 minutes

    # Long-term consolidation (ultradian REM cycles)
    LONG_TERM = "long_term"  # Every 90 minutes

    # Deep sleep consolidation (systems consolidation)
    DEEP_SLEEP = "deep_sleep"  # 2-4 AM daily

    # REM sleep simulation (creative associations)
    REM_SLEEP = "rem_sleep"  # 90-minute cycles at night

    # Synaptic homeostasis (synaptic scaling)
    HOMEOSTASIS = "homeostasis"  # Weekly Sunday 3 AM


class CircadianPhase(Enum):
    """Circadian rhythm phases affecting memory processing"""

    WAKE_ACTIVE = "wake_active"  # 6 AM - 10 PM (peak cognitive activity)
    WAKE_QUIET = "wake_quiet"  # 10 PM - 12 AM (pre-sleep transition)
    LIGHT_SLEEP = "light_sleep"  # 12 AM - 2 AM (NREM stage 1-2)
    DEEP_SLEEP = "deep_sleep"  # 2 AM - 4 AM (NREM stage 3-4)
    REM_DOMINANT = "rem_dominant"  # 4 AM - 6 AM (REM sleep peak)


class BiologicalMemoryProcessor:
    """Handles individual biological memory processing tasks"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.dbt_project_dir = Path(
            os.getenv("DBT_PROJECT_DIR", "/Users/ladvien/codex-dreams/biological_memory")
        )

    def run_dbt_models(self, tags: List[str], models: Optional[List[str]] = None) -> bool:
        """Execute dbt models with specific tags or model names"""
        try:
            cmd = [
                "dbt",
                "run",
                "--profiles-dir",
                str(self.dbt_project_dir / "profiles"),
            ]

            if tags:
                for tag in tags:
                    cmd.extend(["--select", f"tag:{tag}"])

            if models:
                for model in models:
                    cmd.extend(["--select", model])

            self.logger.info(f"Running dbt command: {' '.join(cmd)}")

            # Change to dbt project directory
            original_cwd = os.getcwd()
            os.chdir(self.dbt_project_dir)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout
                    check=True,
                )

                self.logger.info(f"dbt run successful: {result.stdout}")
                return True

            finally:
                os.chdir(original_cwd)

        except subprocess.TimeoutExpired:
            self.logger.error(f"dbt run timed out after 10 minutes")
            return False
        except subprocess.CalledProcessError as e:
            self.logger.error(f"dbt run failed: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error in dbt run: {e}")
            return False

    def continuous_processing(self) -> bool:
        """Working memory refresh - 5 minute cycles (Miller's Law implementation)"""
        self.logger.info("🧠 Running continuous working memory processing")
        return self.run_dbt_models(tags=["continuous", "real_time", "working_memory"])

    def short_term_consolidation(self) -> bool:
        """Short-term memory consolidation - 20 minute cycles"""
        self.logger.info("📝 Running short-term memory consolidation")
        return self.run_dbt_models(
            tags=["short_term", "incremental"],
            models=["stm_hierarchical_episodes", "consolidating_memories"],
        )

    def long_term_consolidation(self) -> bool:
        """Long-term consolidation - 90 minute ultradian cycles"""
        self.logger.info("🔄 Running long-term memory consolidation (ultradian cycle)")
        return self.run_dbt_models(
            tags=["long_term", "consolidation"],
            models=["memory_replay", "ltm_semantic_network"],
        )

    def deep_sleep_consolidation(self) -> bool:
        """Deep sleep systems consolidation - nightly 2-4 AM"""
        self.logger.info("😴 Running deep sleep memory consolidation")
        success = self.run_dbt_models(tags=["consolidation", "memory_intensive"])

        # Also run semantic network optimization during deep sleep
        semantic_success = self.run_dbt_models(tags=["semantic", "performance_intensive"])

        return success and semantic_success

    def rem_sleep_simulation(self) -> bool:
        """REM sleep creative associations - 90 minute night cycles"""
        self.logger.info("💭 Running REM sleep creative association processing")
        return self.run_dbt_models(models=["concept_associations"], tags=["semantic"])

    def synaptic_homeostasis(self) -> bool:
        """Synaptic homeostasis - weekly Sunday 3 AM"""
        self.logger.info("⚖️ Running synaptic homeostasis (weekly maintenance)")

        # Run comprehensive memory cleanup and optimization
        cleanup_success = self.run_dbt_models(tags=["performance_optimized", "analytics"])

        # Run semantic network pruning
        pruning_success = self.run_dbt_models(models=["ltm_semantic_network_optimized"])

        return cleanup_success and pruning_success


class BiologicalRhythmScheduler:
    """
    Advanced biological rhythm scheduler implementing neuroscience-based timing

    Based on research from:
    - Kleitman & Rosenberg (1953): Basic rest-activity cycle (90-min ultradian)
    - McGaugh (2000): Memory consolidation timing
    - Diekelmann & Born (2010): Sleep-dependent memory consolidation
    - Tononi & Cirelli (2006): Synaptic homeostasis during sleep
    """

    def __init__(self, config: Optional[DaemonConfig] = None):
        self.config = config or self._create_default_config()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.processor = BiologicalMemoryProcessor(self._setup_logging())
        self.logger = self._setup_logging()

        # Timing state tracking
        self.last_continuous = datetime.now()
        self.last_short_term = datetime.now()
        self.last_long_term = datetime.now()
        self.last_deep_sleep = datetime.now().date()
        self.last_homeostasis = self._get_last_sunday()

        # Performance metrics
        self.cycle_metrics = defaultdict(lambda: {"count": 0, "failures": 0, "avg_duration": 0.0})

        # Handle shutdown signals
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._signal_handler)

    def _create_default_config(self) -> DaemonConfig:
        """Create default configuration for biological rhythm scheduling"""
        config = DaemonConfig()
        config.log_level = "INFO"
        config.working_directory = os.getenv("DBT_PROJECT_DIR", os.getcwd())
        return config

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for biological rhythm scheduler"""
        logger = logging.getLogger("biological_rhythm_scheduler")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - 🧬 [BIOLOGICAL] %(message)s"
            )
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _signal_handler(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down biological scheduler...")
        self.stop()

    def _get_current_circadian_phase(self) -> CircadianPhase:
        """Determine current circadian phase based on time of day"""
        current_hour = datetime.now().hour

        if 6 <= current_hour < 22:  # 6 AM - 10 PM
            return CircadianPhase.WAKE_ACTIVE
        elif 22 <= current_hour < 24:  # 10 PM - 12 AM
            return CircadianPhase.WAKE_QUIET
        elif 0 <= current_hour < 2:  # 12 AM - 2 AM
            return CircadianPhase.LIGHT_SLEEP
        elif 2 <= current_hour < 4:  # 2 AM - 4 AM
            return CircadianPhase.DEEP_SLEEP
        else:  # 4 AM - 6 AM
            return CircadianPhase.REM_DOMINANT

    def _get_last_sunday(self) -> datetime:
        """Get the most recent Sunday for homeostasis scheduling"""
        today = datetime.now()
        days_since_sunday = today.weekday() + 1  # Monday = 0, Sunday = 6
        if days_since_sunday == 7:  # Today is Sunday
            days_since_sunday = 0
        last_sunday = today - timedelta(days=days_since_sunday)
        return last_sunday.replace(hour=3, minute=0, second=0, microsecond=0)

    def _should_run_continuous(self) -> bool:
        """Check if continuous processing should run (every 5 minutes during wake)"""
        circadian_phase = self._get_current_circadian_phase()

        # Only run during wake hours (biological accuracy)
        if circadian_phase not in [
            CircadianPhase.WAKE_ACTIVE,
            CircadianPhase.WAKE_QUIET,
        ]:
            return False

        time_diff = (datetime.now() - self.last_continuous).total_seconds()
        return time_diff >= 300  # 5 minutes = 300 seconds

    def _should_run_short_term(self) -> bool:
        """Check if short-term consolidation should run (every 20 minutes)"""
        time_diff = (datetime.now() - self.last_short_term).total_seconds()
        return time_diff >= 1200  # 20 minutes = 1200 seconds

    def _should_run_long_term(self) -> bool:
        """Check if long-term consolidation should run (90-minute ultradian cycles)"""
        time_diff = (datetime.now() - self.last_long_term).total_seconds()
        return time_diff >= 5400  # 90 minutes = 5400 seconds

    def _should_run_deep_sleep(self) -> bool:
        """Check if deep sleep consolidation should run (2-4 AM daily)"""
        now = datetime.now()
        circadian_phase = self._get_current_circadian_phase()

        # Only during deep sleep phase (2-4 AM)
        if circadian_phase != CircadianPhase.DEEP_SLEEP:
            return False

        # Only once per day
        return now.date() > self.last_deep_sleep

    def _should_run_rem_sleep(self) -> bool:
        """Check if REM sleep simulation should run (4-6 AM, 90-min cycles)"""
        circadian_phase = self._get_current_circadian_phase()

        # Only during REM-dominant phase
        if circadian_phase != CircadianPhase.REM_DOMINANT:
            return False

        # Check 90-minute ultradian cycle timing
        time_diff = (datetime.now() - self.last_long_term).total_seconds()
        return time_diff >= 5400  # 90 minutes

    def _should_run_homeostasis(self) -> bool:
        """Check if synaptic homeostasis should run (weekly Sunday 3 AM)"""
        now = datetime.now()

        # Only on Sunday at 3 AM
        if now.weekday() != 6 or now.hour != 3:  # Sunday = 6
            return False

        # Only once per week
        time_diff = (now - self.last_homeostasis).total_seconds()
        return time_diff >= 604800  # 1 week = 604800 seconds

    def _execute_rhythm_cycle(self, rhythm_type: BiologicalRhythmType) -> bool:
        """Execute a specific biological rhythm cycle with metrics tracking"""
        start_time = datetime.now()

        try:
            self.logger.info(f"🔄 Starting {rhythm_type.value} cycle")

            success = False
            if rhythm_type == BiologicalRhythmType.CONTINUOUS:
                success = self.processor.continuous_processing()
                self.last_continuous = datetime.now()
            elif rhythm_type == BiologicalRhythmType.SHORT_TERM:
                success = self.processor.short_term_consolidation()
                self.last_short_term = datetime.now()
            elif rhythm_type == BiologicalRhythmType.LONG_TERM:
                success = self.processor.long_term_consolidation()
                self.last_long_term = datetime.now()
            elif rhythm_type == BiologicalRhythmType.DEEP_SLEEP:
                success = self.processor.deep_sleep_consolidation()
                self.last_deep_sleep = datetime.now().date()
            elif rhythm_type == BiologicalRhythmType.REM_SLEEP:
                success = self.processor.rem_sleep_simulation()
            elif rhythm_type == BiologicalRhythmType.HOMEOSTASIS:
                success = self.processor.synaptic_homeostasis()
                self.last_homeostasis = datetime.now()

            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            metrics = self.cycle_metrics[rhythm_type.value]
            metrics["count"] += 1
            if not success:
                metrics["failures"] += 1

            # Update average duration (exponential moving average)
            if metrics["avg_duration"] == 0:
                metrics["avg_duration"] = duration
            else:
                metrics["avg_duration"] = 0.8 * metrics["avg_duration"] + 0.2 * duration

            status = "✅ SUCCESS" if success else "❌ FAILED"
            self.logger.info(f"{status} {rhythm_type.value} cycle completed in {duration:.2f}s")

            return success

        except Exception as e:
            self.logger.error(f"💥 Exception in {rhythm_type.value} cycle: {e}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")

            # Update metrics for failed attempt
            duration = (datetime.now() - start_time).total_seconds()
            metrics = self.cycle_metrics[rhythm_type.value]
            metrics["count"] += 1
            metrics["failures"] += 1

            # Update average duration (exponential moving average)
            if metrics["avg_duration"] == 0:
                metrics["avg_duration"] = duration
            else:
                metrics["avg_duration"] = 0.8 * metrics["avg_duration"] + 0.2 * duration

            return False

    def _log_biological_status(self) -> None:
        """Log current biological rhythm status and metrics"""
        now = datetime.now()
        circadian_phase = self._get_current_circadian_phase()

        self.logger.info("🧬 BIOLOGICAL RHYTHM STATUS:")
        self.logger.info(f"  🕐 Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"  🌙 Circadian phase: {circadian_phase.value}")

        # Show next scheduled cycles
        next_continuous = self.last_continuous + timedelta(minutes=5)
        next_short_term = self.last_short_term + timedelta(minutes=20)
        next_long_term = self.last_long_term + timedelta(minutes=90)

        self.logger.info(f"  🧠 Next continuous: {next_continuous.strftime('%H:%M:%S')}")
        self.logger.info(f"  📝 Next short-term: {next_short_term.strftime('%H:%M:%S')}")
        self.logger.info(f"  🔄 Next long-term: {next_long_term.strftime('%H:%M:%S')}")

        # Show cycle metrics
        for rhythm_type, metrics in self.cycle_metrics.items():
            if metrics["count"] > 0:
                success_rate = ((metrics["count"] - metrics["failures"]) / metrics["count"]) * 100
                self.logger.info(
                    f"  📊 {rhythm_type}: {metrics['count']} runs, "
                    f"{success_rate:.1f}% success, {metrics['avg_duration']:.1f}s avg"
                )

    def _scheduler_main_loop(self) -> None:
        """Main biological rhythm scheduling loop"""
        self.logger.info("🧬 Biological rhythm scheduler started")
        self.logger.info("📚 Based on neuroscience research:")
        self.logger.info("   • Miller (1956) - Working memory capacity")
        self.logger.info("   • McGaugh (2000) - Memory consolidation")
        self.logger.info("   • Diekelmann & Born (2010) - Sleep and memory")
        self.logger.info("   • Tononi & Cirelli (2006) - Synaptic homeostasis")

        # Status reporting interval (every 10 minutes)
        last_status_report = datetime.now()
        status_interval = timedelta(minutes=10)

        while self.running:
            try:
                current_time = datetime.now()

                # Check and execute each biological rhythm
                if self._should_run_continuous():
                    self._execute_rhythm_cycle(BiologicalRhythmType.CONTINUOUS)

                if self._should_run_short_term():
                    self._execute_rhythm_cycle(BiologicalRhythmType.SHORT_TERM)

                if self._should_run_long_term():
                    self._execute_rhythm_cycle(BiologicalRhythmType.LONG_TERM)

                if self._should_run_deep_sleep():
                    self._execute_rhythm_cycle(BiologicalRhythmType.DEEP_SLEEP)

                if self._should_run_rem_sleep():
                    self._execute_rhythm_cycle(BiologicalRhythmType.REM_SLEEP)

                if self._should_run_homeostasis():
                    self._execute_rhythm_cycle(BiologicalRhythmType.HOMEOSTASIS)

                # Periodic status reporting
                if current_time - last_status_report >= status_interval:
                    self._log_biological_status()
                    last_status_report = current_time

                # Sleep for 30 seconds before next check (biological accuracy)
                time.sleep(30)

            except Exception as e:
                self.logger.error(f"💥 Error in main scheduler loop: {e}")
                self.logger.debug(f"Traceback: {traceback.format_exc()}")
                time.sleep(60)  # Wait 1 minute before retrying

    def start(self, daemon_mode: bool = False) -> None:
        """Start the biological rhythm scheduler"""
        if self.running:
            self.logger.warning("Biological scheduler is already running")
            return

        self.running = True

        if daemon_mode:
            self.thread = threading.Thread(target=self._scheduler_main_loop, daemon=True)
            self.thread.start()
            self.logger.info("🧬 Biological scheduler started in daemon mode")
        else:
            try:
                self._scheduler_main_loop()
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received, shutting down...")
            finally:
                self.stop()

    def stop(self) -> None:
        """Stop the biological rhythm scheduler"""
        if not self.running:
            return

        self.running = False

        if self.thread and self.thread.is_alive():
            self.logger.info("Waiting for biological scheduler thread to finish...")
            self.thread.join(timeout=30)

        self.logger.info("🧬 Biological rhythm scheduler stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current biological rhythm scheduler status"""
        circadian_phase = self._get_current_circadian_phase()

        return {
            "running": self.running,
            "circadian_phase": circadian_phase.value,
            "current_time": datetime.now().isoformat(),
            "last_cycles": {
                "continuous": self.last_continuous.isoformat(),
                "short_term": self.last_short_term.isoformat(),
                "long_term": self.last_long_term.isoformat(),
                "deep_sleep": self.last_deep_sleep.isoformat(),
                "homeostasis": self.last_homeostasis.isoformat(),
            },
            "metrics": dict(self.cycle_metrics),
            "should_run": {
                "continuous": self._should_run_continuous(),
                "short_term": self._should_run_short_term(),
                "long_term": self._should_run_long_term(),
                "deep_sleep": self._should_run_deep_sleep(),
                "rem_sleep": self._should_run_rem_sleep(),
                "homeostasis": self._should_run_homeostasis(),
            },
        }


def main() -> None:
    """Main entry point for biological rhythm scheduler"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Biological Rhythm Pipeline Orchestration - Neuroscience-based Memory Scheduling"
    )
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )

    args = parser.parse_args()

    # Create configuration
    config = DaemonConfig()
    config.log_level = args.log_level

    scheduler = BiologicalRhythmScheduler(config)

    if args.status:
        status = scheduler.get_status()
        print(json.dumps(status, indent=2))
        return

    # Start the biological rhythm scheduler
    scheduler.start(daemon_mode=args.daemon)


if __name__ == "__main__":
    main()
