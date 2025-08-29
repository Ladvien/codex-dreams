#!/usr/bin/env python3
"""
Simple YAML-only configuration for Codex Dreams.
Single source of truth: ~/.codex/config.yaml
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional
import yaml


@dataclass
class CodexConfig:
    """Simple configuration class for Codex Dreams"""
    
    # Core settings
    schedule: str = "every 5 minutes"
    
    # Database settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "codex"
    db_user: str = "ladvien"
    db_password: Optional[str] = None
    
    # Ollama settings
    ollama_host: str = "localhost"
    ollama_port: int = 11434
    ollama_model: str = "qwen2.5:0.5b"
    
    # Storage settings
    duckdb_path: str = "~/codex-dreams/memory.duckdb"
    log_dir: str = "~/.codex/logs/"
    
    @property
    def config_path(self) -> Path:
        """Get the config file path"""
        return Path.home() / ".codex" / "config.yaml"
    
    @property
    def log_file(self) -> Path:
        """Get the log file path"""
        return Path(self.log_dir).expanduser() / "codex.log"
    
    @property
    def pid_file(self) -> Path:
        """Get the PID file path"""
        return Path.home() / ".codex" / "codex.pid"
    
    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection string"""
        if self.db_password:
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        else:
            return f"postgresql://{self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def ollama_url(self) -> str:
        """Get Ollama API URL"""
        return f"http://{self.ollama_host}:{self.ollama_port}"
    
    @property
    def expanded_duckdb_path(self) -> str:
        """Get expanded DuckDB path"""
        return str(Path(self.duckdb_path).expanduser())
    
    def parse_schedule(self) -> int:
        """Parse schedule string to minutes"""
        schedule = self.schedule.lower().strip()
        
        # Handle "every X minutes"
        if match := re.match(r'every (\d+) minutes?', schedule):
            return int(match.group(1))
        
        # Handle "every X hours"
        if match := re.match(r'every (\d+) hours?', schedule):
            return int(match.group(1)) * 60
        
        # Handle shortcuts
        shortcuts = {
            'every minute': 1,
            'minutely': 1,
            'every hour': 60,
            'hourly': 60,
            'every day': 1440,
            'daily': 1440,
        }
        
        if schedule in shortcuts:
            return shortcuts[schedule]
        
        # Default fallback
        print(f"Warning: Could not parse schedule '{self.schedule}', using 5 minutes")
        return 5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for YAML"""
        return {
            'schedule': self.schedule,
            'database': {
                'host': self.db_host,
                'port': self.db_port,
                'name': self.db_name,
                'user': self.db_user,
                'password': self.db_password,
            },
            'ollama': {
                'host': self.ollama_host,
                'port': self.ollama_port,
                'model': self.ollama_model,
            },
            'storage': {
                'duckdb': self.duckdb_path,
                'logs': self.log_dir,
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodexConfig':
        """Create config from dictionary"""
        config = cls()
        
        # Top level
        if 'schedule' in data:
            config.schedule = data['schedule']
        
        # Database section
        if 'database' in data:
            db = data['database']
            config.db_host = db.get('host', config.db_host)
            config.db_port = db.get('port', config.db_port)
            config.db_name = db.get('name', config.db_name)
            config.db_user = db.get('user', config.db_user)
            config.db_password = db.get('password', config.db_password)
        
        # Ollama section
        if 'ollama' in data:
            ollama = data['ollama']
            config.ollama_host = ollama.get('host', config.ollama_host)
            config.ollama_port = ollama.get('port', config.ollama_port)
            config.ollama_model = ollama.get('model', config.ollama_model)
        
        # Storage section
        if 'storage' in data:
            storage = data['storage']
            config.duckdb_path = storage.get('duckdb', config.duckdb_path)
            config.log_dir = storage.get('logs', config.log_dir)
        
        return config
    
    def save(self) -> None:
        """Save configuration to YAML file"""
        self.config_path.parent.mkdir(exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Configuration saved to {self.config_path}")
    
    @classmethod
    def load(cls) -> 'CodexConfig':
        """Load configuration from YAML file"""
        config_path = Path.home() / ".codex" / "config.yaml"
        
        if not config_path.exists():
            # Return default config
            return cls()
        
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            return cls.from_dict(data)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            print("Using default configuration")
            return cls()


def create_default_config() -> CodexConfig:
    """Create default configuration file with comments"""
    config_path = Path.home() / ".codex" / "config.yaml"
    config_path.parent.mkdir(exist_ok=True)
    
    # Create YAML with comments
    yaml_content = """# Codex Dreams Configuration
# This is your single source of truth for all settings

# How often to generate insights
schedule: every 5 minutes

# Database connection (PostgreSQL)
database:
  host: localhost
  port: 5432
  name: codex
  user: ladvien
  password: null  # Leave null if no password needed

# AI model settings (Ollama)
ollama:
  host: localhost
  port: 11434
  model: qwen2.5:0.5b

# File storage locations
storage:
  duckdb: ~/codex-dreams/memory.duckdb
  logs: ~/.codex/logs/
"""
    
    with open(config_path, 'w') as f:
        f.write(yaml_content)
    
    return CodexConfig.load()


def get_config() -> CodexConfig:
    """Get the current configuration"""
    return CodexConfig.load()


# Schedule options for interactive selection
SCHEDULE_OPTIONS = [
    ("Every minute", "every minute"),
    ("Every 5 minutes (recommended)", "every 5 minutes"),
    ("Every 10 minutes", "every 10 minutes"),
    ("Every 15 minutes", "every 15 minutes"),
    ("Every 30 minutes", "every 30 minutes"),
    ("Every hour", "every hour"),
    ("Daily at 3 AM", "daily at 3am"),
]


def interactive_schedule_selection(current: str) -> str:
    """Interactive schedule selection"""
    print("\n? How often should I analyze memories?")
    
    for i, (display, value) in enumerate(SCHEDULE_OPTIONS, 1):
        marker = "❯" if value == current else " "
        current_marker = " (current)" if value == current else ""
        print(f"  {marker} {i}. {display}{current_marker}")
    
    print(f"  › {len(SCHEDULE_OPTIONS) + 1}. Custom...")
    
    try:
        choice = input(f"\nSelect [1-{len(SCHEDULE_OPTIONS) + 1}]: ").strip()
        
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(SCHEDULE_OPTIONS):
                return SCHEDULE_OPTIONS[idx][1]
            elif int(choice) == len(SCHEDULE_OPTIONS) + 1:
                # Custom option
                custom = input("Enter custom schedule (e.g., 'every 2 hours'): ").strip()
                return custom if custom else current
        
        print("Invalid selection, keeping current schedule.")
        return current
        
    except (ValueError, KeyboardInterrupt):
        print("\nKeeping current schedule.")
        return current