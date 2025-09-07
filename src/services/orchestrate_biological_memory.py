"""
Biological Memory Orchestrator - Main orchestration service
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import duckdb
import psycopg2

logger = logging.getLogger(__name__)


class BiologicalMemoryOrchestrator:
    """Orchestrates biological memory processing pipeline"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_config()
        self.duckdb_conn = None
        self.postgres_conn = None
        self.running = False
        self.last_run = None
        self.logger = logger  # Make logger accessible for tests
        # Add error handler for compatibility
        self.error_handler = type(
            "ErrorHandler",
            (),
            {"exponential_backoff_retry": lambda self, *a, **k: None},
        )()
        # Security patterns for argument validation (compiled regex)
        import re

        self.safe_argument_patterns = {
            "--select": re.compile(r"^[a-zA-Z0-9_\+\*\.\:\-]+$"),
            "--exclude": re.compile(r"^[a-zA-Z0-9_\+\*\.\:\-]+$"),
            "--vars": re.compile(r"^\{[^;}|&<>$`]+\}$"),
            "--target": re.compile(r"^[a-zA-Z0-9_]+$"),
            "--profiles-dir": re.compile(r"^[a-zA-Z0-9_/\.\-]+$"),
            "--project-dir": re.compile(r"^[a-zA-Z0-9_/\.\-]+$"),
        }

        # Dangerous characters for shell injection prevention
        self.dangerous_chars = [";", "&&", "||", "|", "`", "$", ">", "<", "&"]
        logger.info("Biological Memory Orchestrator initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment"""
        return {
            "postgres_url": os.getenv("POSTGRES_DB_URL", "postgresql://localhost:5432/test_db"),
            "duckdb_path": os.getenv("DUCKDB_PATH", ":memory:"),
            "working_memory_capacity": 7,
            "stm_duration_minutes": 30,
            "consolidation_threshold": 0.5,
            "hebbian_learning_rate": 0.1,
            "forgetting_rate": 0.05,
        }

    def connect(self) -> None:
        """Establish database connections"""
        try:
            # Connect to DuckDB
            self.duckdb_conn = duckdb.connect(self.config["duckdb_path"])
            self.duckdb_conn.execute("INSTALL httpfs; LOAD httpfs;")
            self.duckdb_conn.execute("INSTALL postgres; LOAD postgres;")
            self.duckdb_conn.execute("INSTALL json; LOAD json;")

            # Test PostgreSQL connection
            conn_params = self._parse_postgres_url(self.config["postgres_url"])
            self.postgres_conn = psycopg2.connect(**conn_params)
            self.postgres_conn.close()  # Just testing

            logger.info("Database connections established")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to databases: {e}")
            return False

    def _parse_postgres_url(self, url: str) -> Dict[str, Any]:
        """Parse PostgreSQL connection URL"""
        # Simple parser for postgresql://user:pass@host:port/db
        import re

        pattern = r"postgresql://(?:([^:]+):([^@]+)@)?([^:/]+)(?::(\d+))?/(.+)"
        match = re.match(pattern, url)

        if not match:
            return {"host": "localhost", "port": 5432, "database": "test_db"}

        user, password, host, port, database = match.groups()
        return {
            "host": host or "localhost",
            "port": int(port) if port else 5432,
            "database": database or "test_db",
            "user": user,
            "password": password,
        }

    def run_pipeline(self) -> None:
        """Run the complete memory processing pipeline"""
        if not self.duckdb_conn:
            if not self.connect():
                raise RuntimeError("Cannot run pipeline without database connections")

        try:
            self.running = True

            # Stage 1: Process working memory
            self._process_working_memory()

            # Stage 2: Process short-term memory
            self._process_short_term_memory()

            # Stage 3: Consolidate memories
            self._consolidate_memories()

            # Stage 4: Update long-term memory
            self._update_long_term_memory()

            self.last_run = datetime.now()
            logger.info("Pipeline completed successfully")

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
        finally:
            self.running = False

    def _process_working_memory(self) -> int:
        """Process working memory with Miller's 7±2 constraint"""
        query = f"""
        CREATE OR REPLACE VIEW working_memory AS
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (ORDER BY timestamp DESC) as position
            FROM raw_memories
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
        ) t
        WHERE position <= {self.config['working_memory_capacity']}
        """
        self.duckdb_conn.execute(query)
        logger.debug("Working memory processed")

    def _process_short_term_memory(self) -> int:
        """Process short-term memory with hierarchical structure"""
        query = f"""
        CREATE OR REPLACE VIEW short_term_memory AS
        SELECT * FROM raw_memories
        WHERE timestamp > NOW() - INTERVAL '{self.config['stm_duration_minutes']} minutes'
        """
        self.duckdb_conn.execute(query)
        logger.debug("Short-term memory processed")

    def _consolidate_memories(self) -> int:
        """Consolidate memories using Hebbian learning"""
        query = f"""
        CREATE OR REPLACE VIEW consolidated_memories AS
        SELECT
            *,
            {self.config['hebbian_learning_rate']} * strength as hebbian_weight
        FROM short_term_memory
        WHERE strength > {self.config['consolidation_threshold']}
        """
        self.duckdb_conn.execute(query)
        logger.debug("Memory consolidation completed")

    def _update_long_term_memory(self) -> int:
        """Update long-term memory with consolidated memories"""
        query = f"""
        CREATE OR REPLACE VIEW long_term_memory AS
        SELECT
            *,
            strength * (1 - {self.config['forgetting_rate']}) as decayed_strength
        FROM consolidated_memories
        """
        self.duckdb_conn.execute(query)
        logger.debug("Long-term memory updated")

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "running": self.running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "config": self.config,
            "connections": {
                "duckdb": self.duckdb_conn is not None,
                "postgres": self.postgres_conn is not None,
            },
        }

    def shutdown(self) -> None:
        """Shutdown orchestrator and close connections"""
        self.running = False
        if self.duckdb_conn:
            self.duckdb_conn.close()
        if self.postgres_conn:
            self.postgres_conn.close()
        logger.info("Orchestrator shutdown complete")

    def _validate_dbt_command(self, command: str) -> bool:
        """Validate dbt command for security"""
        # Block newlines and carriage returns
        if "\n" in command or "\r" in command:
            self.logger.error(f"Blocked command with newline/carriage return")
            return False

        # Block any shell injection attempts
        for char in self.dangerous_chars:
            if char in command:
                self.logger.error(f"Dangerous character '{char}' detected")
                return False

        # Block path traversal
        if ".." in command or "~" in command:
            self.logger.error(f"Blocked path traversal attempt")
            return False

        # Only allow specific dbt commands
        allowed_subcommands = [
            "run",
            "test",
            "compile",
            "debug",
            "run-operation",
            "deps",
            "clean",
            "parse",
        ]

        # Check if it's a valid dbt command
        if not command.startswith("dbt "):
            self.logger.error(f"Blocked non-dbt command: {command}")
            return False

        # Extract subcommand
        parts = command.split()
        if len(parts) < 2:
            self.logger.error("Invalid command format")
            return False

        subcommand = parts[1]
        if subcommand not in allowed_subcommands:
            self.logger.error(f"Disallowed dbt subcommand '{subcommand}'")
            return False

        # Validate arguments if present
        allowed_args = ["--select", "--exclude", "--vars", "--full-refresh", "--quiet"]
        for i in range(2, len(parts)):
            if parts[i].startswith("--"):
                arg_name = parts[i].split("=")[0] if "=" in parts[i] else parts[i]
                if arg_name not in allowed_args:
                    self.logger.error(f"Unexpected argument format: {arg_name}")
                    return False

        return True

    def _sanitize_command(self, command: str) -> str:
        """Sanitize command for safe logging"""
        # Check for dangerous characters
        sanitized = command
        has_dangerous_chars = any(char in command for char in self.dangerous_chars)

        if has_dangerous_chars:
            # Remove dangerous characters and mark as filtered
            for char in self.dangerous_chars:
                sanitized = sanitized.replace(char, "")
            sanitized = f"[FILTERED] {sanitized}"

        # Remove any potentially sensitive information
        sanitized = sanitized.replace("password=", "password=***").replace("token=", "token=***")
        return sanitized

    def _sanitize_command_for_logging(self, command: str) -> str:
        """Sanitize command for safe logging - alias for compatibility"""
        return self._sanitize_command(command)

    def run_dbt_command(self, command: str, log_file: str = None, timeout: int = 30) -> bool:
        """Run a dbt command securely"""
        import subprocess

        # Validate command first
        if not self._validate_dbt_command(command):
            raise ValueError(f"Invalid or unsafe command: {self._sanitize_command(command)}")

        # Convert string command to list for security (prevents shell injection)
        command_parts = command.split()

        # Run command with shell=False for security
        result = subprocess.run(
            command_parts,
            shell=False,  # CRITICAL: shell=False prevents injection
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return result

    def _validate_argument(self, arg: str) -> bool:
        """Validate command line argument"""
        # Allow only safe arguments
        allowed_args = [
            "--select",
            "--exclude",
            "--quiet",
            "--vars",
            "--target",
            "--profiles-dir",
            "--project-dir",
            "--full-refresh",
        ]

        arg_name = arg.split("=")[0] if "=" in arg else arg
        return arg_name in allowed_args
