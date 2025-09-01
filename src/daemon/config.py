#!/usr/bin/env python3
"""
Configuration management for codex-dreams daemon.
Handles loading from files, environment variables, and defaults.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict, fields
import logging


@dataclass
class DaemonConfig:
    """Configuration class for the daemon with environment variable support"""

    # Scheduling configuration
    interval_minutes: int = 5
    max_retries: int = 3
    retry_delay_seconds: int = 30

    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # Process management
    pid_file: Optional[str] = None
    working_directory: Optional[str] = None

    # Environment configuration
    environment_file: Optional[str] = None

    # Service configuration
    service_name: str = "codex-dreams-daemon"
    service_description: str = "Codex Dreams Insights Generation Daemon"

    # Database and API configuration (with env var fallbacks)
    postgres_db_url: Optional[str] = None
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    duckdb_path: Optional[str] = None

    def __post_init__(self):
        """Load environment variables after initialization"""
        self._load_from_environment()

    def _load_from_environment(self):
        """Load configuration from environment variables"""
        env_mappings = {
            "postgres_db_url": "POSTGRES_DB_URL",
            "ollama_url": "OLLAMA_URL",
            "ollama_model": "OLLAMA_MODEL",
            "duckdb_path": "DUCKDB_PATH",
            "log_level": "CODEX_LOG_LEVEL",
            "log_file": "CODEX_LOG_FILE",
            "pid_file": "CODEX_PID_FILE",
            "working_directory": "CODEX_WORKING_DIR",
            "environment_file": "CODEX_ENV_FILE",
            "interval_minutes": "CODEX_INTERVAL_MINUTES",
            "max_retries": "CODEX_MAX_RETRIES",
            "retry_delay_seconds": "CODEX_RETRY_DELAY_SECONDS",
        }

        for field_name, env_var in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert to appropriate type based on field annotation
                field_info = next((f for f in fields(self) if f.name == field_name), None)
                if field_info:
                    if field_info.type == int:
                        try:
                            setattr(self, field_name, int(env_value))
                        except ValueError:
                            logging.warning(f"Invalid integer value for {env_var}: {env_value}")
                    else:
                        setattr(self, field_name, env_value)

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "DaemonConfig":
        """Load configuration from JSON file with environment variable overlay"""
        config_path = Path(config_path)

        # Start with defaults
        config_data = {}

        # Load from file if it exists
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config_data = json.load(f)
                logging.debug(f"Loaded configuration from {config_path}")
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load config from {config_path}: {e}. Using defaults.")

        # Create instance (this will also load from environment)
        return cls(**config_data)

    def to_file(self, config_path: Union[str, Path]) -> None:
        """Save configuration to JSON file"""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and remove None values for cleaner output
        config_dict = {k: v for k, v in asdict(self).items() if v is not None}

        with open(config_path, "w") as f:
            json.dump(config_dict, f, indent=2, sort_keys=True)

        logging.debug(f"Saved configuration to {config_path}")

    def update_from_dict(self, updates: Dict[str, Any]) -> None:
        """Update configuration from dictionary"""
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_effective_config(self) -> Dict[str, Any]:
        """Get the effective configuration including resolved paths"""
        config = asdict(self)

        # Resolve default paths if not set
        if not config["log_file"]:
            config["log_file"] = str(get_default_log_path())

        if not config["pid_file"]:
            config["pid_file"] = str(get_default_pid_path())

        if not config["working_directory"]:
            # Default to the codex-dreams project directory
            config["working_directory"] = str(find_project_root())

        if not config["environment_file"]:
            # Look for .env file in project root
            project_root = find_project_root()
            env_file = project_root / ".env"
            if env_file.exists():
                config["environment_file"] = str(env_file)

        return config

    def validate(self) -> None:
        """Validate configuration and raise ValueError if invalid"""
        errors = []

        if self.interval_minutes <= 0:
            errors.append("interval_minutes must be positive")

        if self.max_retries < 0:
            errors.append("max_retries cannot be negative")

        if self.retry_delay_seconds < 0:
            errors.append("retry_delay_seconds cannot be negative")

        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors.append(f"Invalid log_level: {self.log_level}")

        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")


def get_default_config_path() -> Path:
    """Get the default configuration file path based on platform"""
    import sys

    if sys.platform == "win32":
        config_dir = Path.home() / "AppData" / "Local" / "codex-dreams"
    elif sys.platform == "darwin":  # macOS
        config_dir = Path.home() / "Library" / "Application Support" / "codex-dreams"
    else:  # Linux and other Unix-like
        config_dir = Path.home() / ".config" / "codex-dreams"

    return config_dir / "daemon.json"


def get_default_log_path() -> Path:
    """Get the default log file path based on platform"""
    import sys

    if sys.platform == "win32":
        log_dir = Path.home() / "AppData" / "Local" / "codex-dreams" / "logs"
    elif sys.platform == "darwin":  # macOS
        log_dir = Path.home() / "Library" / "Logs" / "codex-dreams"
    else:  # Linux and other Unix-like
        log_dir = Path.home() / ".local" / "share" / "codex-dreams" / "logs"

    return log_dir / "daemon.log"


def get_default_pid_path() -> Path:
    """Get the default PID file path based on platform and permissions"""
    import sys

    if sys.platform == "win32":
        pid_dir = Path.home() / "AppData" / "Local" / "codex-dreams"
    else:
        # Try system directories first, fall back to user directories
        if os.access("/var/run", os.W_OK):
            pid_dir = Path("/var/run")
        elif os.access("/tmp", os.W_OK):
            pid_dir = Path("/tmp")
        else:
            if sys.platform == "darwin":
                pid_dir = Path.home() / "Library" / "Application Support" / "codex-dreams"
            else:
                pid_dir = Path.home() / ".local" / "share" / "codex-dreams"

    return pid_dir / "codex-dreams-daemon.pid"


def find_project_root() -> Path:
    """Find the codex-dreams project root directory"""
    # Start from current file and work upward
    current = Path(__file__).parent

    while current != current.parent:
        # Look for project markers
        if any((current / marker).exists() for marker in ["pyproject.toml", "CLAUDE.md", "src"]):
            return current
        current = current.parent

    # Fallback to current working directory
    return Path.cwd()


def create_default_config(config_path: Optional[Path] = None) -> DaemonConfig:
    """Create a default configuration file"""
    if config_path is None:
        config_path = get_default_config_path()

    config = DaemonConfig()
    config.to_file(config_path)

    logging.info(f"Created default configuration at {config_path}")
    return config


def load_config(config_path: Optional[Union[str, Path]] = None) -> DaemonConfig:
    """Load configuration with smart defaults"""
    if config_path is None:
        config_path = get_default_config_path()

    config = DaemonConfig.from_file(config_path)
    config.validate()

    return config
