#!/usr/bin/env python3
"""
Command-line interface for codex-dreams daemon management.
Provides unified commands for installation, configuration, and management.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import (
    DaemonConfig,
    create_default_config,
    find_project_root,
    get_default_config_path,
    load_config,
)
from .scheduler import DaemonScheduler
from .service_manager import ServiceManager


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def cmd_install(args: argparse.Namespace) -> int:
    """Install the daemon as a system service"""
    try:
        config = load_config(args.config)
        service_manager = ServiceManager(config)

        print(f"Installing {config.service_name} service...")
        if not args.user and not service_manager.is_admin:
            print("Warning: Installing system service without admin privileges may fail.")
            print("Consider using --user flag or running with elevated privileges.")

        success = service_manager.install(user_mode=args.user)

        if success:
            print(f"✅ Successfully installed {config.service_name} service")
            print(f"Configuration: {args.config}")
            print(f"Log file: {config.log_file}")
            print(f"PID file: {config.pid_file}")
            print()
            print("To start the service:")
            if args.user:
                print(f"  codex-daemon start")
            else:
                print(f"  codex-daemon start")
            return 0
        else:
            print("❌ Failed to install service")
            return 1

    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return 1


def cmd_uninstall(args: argparse.Namespace) -> int:
    """Uninstall the daemon service"""
    try:
        config = load_config(args.config)
        service_manager = ServiceManager(config)

        print(f"Uninstalling {config.service_name} service...")
        success = service_manager.uninstall()

        if success:
            print(f"✅ Successfully uninstalled {config.service_name} service")
            return 0
        else:
            print("❌ Failed to uninstall service")
            return 1

    except Exception as e:
        print(f"❌ Uninstallation failed: {e}")
        return 1


def cmd_start(args: argparse.Namespace) -> int:
    """Start the daemon service"""
    try:
        config = load_config(args.config)

        if args.foreground:
            # Run in foreground mode
            print(f"Starting {config.service_name} in foreground mode...")
            print("Press Ctrl+C to stop")
            scheduler = DaemonScheduler(config)
            scheduler.start(daemon_mode=False)
            return 0
        else:
            # Start as service
            service_manager = ServiceManager(config)
            print(f"Starting {config.service_name} service...")
            success = service_manager.start()

            if success:
                print(f"✅ Successfully started {config.service_name} service")
                return 0
            else:
                print("❌ Failed to start service")
                return 1

    except KeyboardInterrupt:
        print("\nStopped by user")
        return 0
    except Exception as e:
        print(f"❌ Start failed: {e}")
        return 1


def cmd_stop(args: argparse.Namespace) -> int:
    """Stop the daemon service"""
    try:
        config = load_config(args.config)
        service_manager = ServiceManager(config)

        print(f"Stopping {config.service_name} service...")
        success = service_manager.stop()

        if success:
            print(f"✅ Successfully stopped {config.service_name} service")
            return 0
        else:
            print("❌ Failed to stop service")
            return 1

    except Exception as e:
        print(f"❌ Stop failed: {e}")
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Show daemon service status"""
    try:
        config = load_config(args.config)
        service_manager = ServiceManager(config)

        print(f"Status for {config.service_name}:")
        print("=" * 50)

        status = service_manager.status()

        # Basic status
        print(f"Platform: {status['platform']}")
        print(f"Service Name: {status['service_name']}")
        print(f"Installed: {'✅' if status['installed'] else '❌'}")
        print(f"Running: {'✅' if status['running'] else '❌'}")
        print(f"Enabled: {'✅' if status['enabled'] else '❌'}")

        # Configuration info
        print(f"\nConfiguration:")
        print(f"  Config File: {args.config}")
        print(f"  Interval: {config.interval_minutes} minutes")
        print(f"  Log Level: {config.log_level}")
        print(f"  Log File: {config.log_file}")
        print(f"  PID File: {config.pid_file}")
        print(f"  Working Dir: {config.working_directory}")

        if config.environment_file:
            print(f"  Environment File: {config.environment_file}")

        # Check PID file
        if config.pid_file:
            pid_path = Path(config.pid_file)
            if pid_path.exists():
                try:
                    with open(pid_path) as f:
                        pid = f.read().strip()
                    print(f"  PID: {pid}")

                    # Check if process is actually running
                    try:
                        import psutil

                        if psutil.pid_exists(int(pid)):
                            process = psutil.Process(int(pid))
                            print(f"  Process Status: {process.status()}")
                            print(f"  CPU %: {process.cpu_percent()}")
                            print(f"  Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
                    except ImportError:
                        print("  (Install 'psutil' for detailed process info)")
                    except Exception:
                        print(f"  Process Status: Not running (stale PID)")
                except Exception:
                    print(f"  PID File: Corrupted")
            else:
                print(f"  PID File: Not found")

        return 0

    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return 1


def cmd_config(args: argparse.Namespace) -> int:
    """Manage daemon configuration"""
    try:
        if args.init:
            # Initialize default configuration
            config = create_default_config(args.config)
            print(f"✅ Created default configuration at {args.config}")
            print("\nEdit the configuration file to customize settings:")
            print(f"  {args.config}")
            return 0

        elif args.show:
            # Show current configuration
            config = load_config(args.config)
            effective_config = config.get_effective_config()

            print(f"Configuration from: {args.config}")
            print("=" * 50)

            for key, value in effective_config.items():
                if value is not None:
                    print(f"{key}: {value}")

            return 0

        elif args.validate:
            # Validate configuration
            config = load_config(args.config)
            config.validate()
            print("✅ Configuration is valid")
            return 0

        else:
            print("Please specify --init, --show, or --validate")
            return 1

    except Exception as e:
        print(f"❌ Configuration command failed: {e}")
        return 1


def cmd_run_once(args: argparse.Namespace) -> int:
    """Run insights generation once"""
    try:
        # Import and run the insights generation directly
        from ..generate_insights import main as generate_insights_main

        print("Running insights generation once...")
        generate_insights_main()
        print("✅ Insights generation completed")
        return 0

    except Exception as e:
        print(f"❌ Insights generation failed: {e}")
        return 1


def main() -> int:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Codex Dreams Daemon Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  codex-daemon install            Install system service
  codex-daemon install --user    Install user service
  codex-daemon start             Start the service
  codex-daemon start --foreground Run in foreground
  codex-daemon status            Show service status
  codex-daemon config --init     Create default config
  codex-daemon run-once          Run insights generation once
        """,
    )

    parser.add_argument(
        "--config", type=Path, default=get_default_config_path(), help="Configuration file path"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Install command
    install_parser = subparsers.add_parser("install", help="Install daemon service")
    install_parser.add_argument("--user", action="store_true", help="Install as user service")
    install_parser.set_defaults(func=cmd_install)

    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall daemon service")
    uninstall_parser.set_defaults(func=cmd_uninstall)

    # Start command
    start_parser = subparsers.add_parser("start", help="Start daemon service")
    start_parser.add_argument("--foreground", action="store_true", help="Run in foreground mode")
    start_parser.set_defaults(func=cmd_start)

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop daemon service")
    stop_parser.set_defaults(func=cmd_stop)

    # Status command
    status_parser = subparsers.add_parser("status", help="Show daemon status")
    status_parser.set_defaults(func=cmd_status)

    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_group = config_parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument("--init", action="store_true", help="Create default configuration")
    config_group.add_argument("--show", action="store_true", help="Show current configuration")
    config_group.add_argument("--validate", action="store_true", help="Validate configuration")
    config_parser.set_defaults(func=cmd_config)

    # Run-once command
    run_once_parser = subparsers.add_parser("run-once", help="Run insights generation once")
    run_once_parser.set_defaults(func=cmd_run_once)

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # Show help if no command specified
    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
