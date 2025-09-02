#!/usr/bin/env python3
"""
Environment management for Codex Dreams.
Allows switching between local and production configurations.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List


def get_env_config_path(env: str) -> Path:
    """Get the config path for a specific environment"""
    config_dir = Path.home() / ".codex"

    if env == "production" or env == "prod":
        return config_dir / "config-production.yaml"
    elif env == "local" or env == "dev":
        return config_dir / "config-local.yaml"
    else:
        raise ValueError(f"Unknown environment: {env}. Use 'local' or 'production'")


def get_current_env() -> Optional[str]:
    """Determine which environment is currently active"""
    config_path = Path.home() / ".codex" / "config.yaml"

    if not config_path.exists():
        return None

    # Read the config to determine environment
    with open(config_path) as f:
        content = f.read()

    if "localhost" in content:
        return "local"
    elif any(keyword in content for keyword in ["192.168", "10.0.", "172.16."]):
        return "production"
    else:
        return "unknown"


def switch_env(env: str) -> bool:
    """Switch to a different environment configuration"""
    try:
        # Get the source config for the environment
        env_config = get_env_config_path(env)

        if not env_config.exists():
            print(f"❌ Configuration for '{env}' not found at {env_config}")
            return False

        # Target config location
        main_config = Path.home() / ".codex" / "config.yaml"

        # Back up current config if it exists
        if main_config.exists():
            backup_path = main_config.with_suffix(".yaml.backup")
            shutil.copy2(main_config, backup_path)

        # Copy environment config to main config
        shutil.copy2(env_config, main_config)

        print(f"✅ Switched to '{env}' environment")

        # Show what changed
        with open(env_config) as f:
            for line in f:
                if "host:" in line and "ollama" not in line:
                    print(f"   Database: {line.strip()}")
                elif "host:" in line and "ollama" in line:
                    # Look for ollama section
                    pass
                elif "model:" in line:
                    print(f"   AI Model: {line.strip()}")
                elif "schedule:" in line:
                    print(f"   Schedule: {line.strip().split('#')[0].strip()}")

        return True

    except Exception as e:
        print(f"❌ Failed to switch environment: {e}")
        return False


def show_environments() -> None:
    """Show available environments and which is active"""
    current = get_current_env()

    print("\n📋 Available Environments:")
    print("=" * 50)

    # Local environment
    local_config = get_env_config_path("local")
    if local_config.exists():
        marker = "❯" if current == "local" else " "
        print(f"{marker} local")
        print(f"    Database: {os.getenv('POSTGRES_HOST', 'localhost')}:5432")
        print(f"    Ollama: {os.getenv('OLLAMA_HOST', 'localhost')}:11434")
        print(f"    Model: gpt-oss:20b")

    # Production environment
    prod_config = get_env_config_path("production")
    if prod_config.exists():
        marker = "❯" if current == "production" else " "
        print(f"{marker} production")
        print(f"    Database: localhost:5432")
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        print(f"    Ollama: {ollama_url.replace('http://', '')}")
        print(f"    Model: gpt-oss:20b")

    print("\n💡 To switch environments:")
    print("   codex env local       # Use local services")
    print("   codex env production  # Use production services")
    print()


def main() -> None:
    """CLI entry point for environment management"""
    import sys

    if len(sys.argv) < 2:
        show_environments()
        return

    env = sys.argv[1].lower()

    if env in ["show", "list", "status"]:
        show_environments()
    elif env in ["local", "dev", "production", "prod"]:
        from .codex_config import get_config
        from .codex_service import CodexService

        # Check if service is running
        config = get_config()
        service = CodexService(config)

        if service.is_running():
            print("⚠️  Codex is currently running")
            response = input("Stop and switch environment? [y/N]: ").strip().lower()
            if response in ["y", "yes"]:
                print("Stopping service...")
                service.stop()
                switch_env(env)
                print("\nRestarting with new environment...")
                service = CodexService(get_config())
                service.start()
            else:
                print("Environment not changed")
        else:
            switch_env(env)
    else:
        print(f"❌ Unknown command: {env}")
        print("Usage: codex env [local|production|show]")


if __name__ == "__main__":
    main()
