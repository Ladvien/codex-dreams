"""
Environment configuration module for testing
"""

import os
from dataclasses import dataclass
from typing import Dict, Optional, Callable, TypeVar

T = TypeVar('T')


@dataclass
class EnvironmentConfig:
    """Configuration for environment variables"""

    postgres_url: str
    ollama_url: str
    duckdb_path: str

    @classmethod
    def from_env(cls) -> "EnvironmentConfig":
        return cls(
            postgres_url=os.getenv("POSTGRES_DB_URL", ""),
            ollama_url=os.getenv("OLLAMA_URL", ""),
            duckdb_path=os.getenv("DUCKDB_PATH", ""),
        )


class PostgreSQLConnection:
    """PostgreSQL connection handler"""

    def __init__(self, url: str):
        self.url = url
        self.connected = False

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False


class OllamaConnection:
    """Ollama connection handler"""

    def __init__(self, url: str):
        self.url = url
        self.connected = False

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False


class ConnectionRetry:
    """Connection retry handler"""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.attempts = 0

    def retry(self, func: Callable[..., T]) -> Callable[..., T]:
        """Retry decorator"""

        def wrapper(*args, **kwargs) -> T:
            for i in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    self.attempts += 1
                    if i == self.max_retries - 1:
                        raise

        return wrapper
