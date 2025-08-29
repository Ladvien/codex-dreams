#!/usr/bin/env python3
"""
Simple CLI interface for Codex Dreams.
The ONE command interface that users interact with.
"""

import sys
import argparse
from pathlib import Path

from .codex_config import CodexConfig, get_config, create_default_config
from .codex_service import CodexService, format_uptime, format_time_until
from .codex_config_editor import (
    interactive_config_editor, 
    quick_schedule_change, 
    show_config, 
    first_time_setup
)


def cmd_init(args):
    """Initialize Codex Dreams with interactive setup"""
    config_path = Path.home() / ".codex" / "config.yaml"
    
    if config_path.exists() and not args.force:
        print(f"✅ Codex Dreams is already set up!")
        print(f"📄 Configuration: {config_path}")
        print()
        print("To reconfigure: codex init --force")
        print("To edit config: codex config")
        print("To start: codex start")
        return 0
    
    try:
        config = first_time_setup()
        return 0
    except KeyboardInterrupt:
        print("\n\n🛑 Setup cancelled")
        return 1
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return 1


def cmd_start(args):
    """Start the Codex Dreams service"""
    try:
        config = get_config()
        service = CodexService(config)
        
        if service.is_running():
            print("✅ Codex Dreams is already running")
            status = service.get_status()
            if 'schedule' in status:
                print(f"📊 Schedule: {status['schedule']}")
            print()
            print("Use 'codex status' for detailed information")
            return 0
        
        if args.foreground:
            return 0 if service.start(foreground=True) else 1
        else:
            return 0 if service.start(foreground=False) else 1
            
    except FileNotFoundError:
        print("❌ Configuration not found")
        print("Run 'codex init' first to set up Codex Dreams")
        return 1
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        return 1


def cmd_stop(args):
    """Stop the Codex Dreams service"""
    try:
        config = get_config()
        service = CodexService(config)
        return 0 if service.stop() else 1
    except Exception as e:
        print(f"❌ Failed to stop: {e}")
        return 1


def cmd_restart(args):
    """Restart the Codex Dreams service"""
    try:
        config = get_config()
        service = CodexService(config)
        return 0 if service.restart() else 1
    except Exception as e:
        print(f"❌ Failed to restart: {e}")
        return 1


def cmd_status(args):
    """Show detailed status of Codex Dreams"""
    try:
        config = get_config()
        service = CodexService(config)
        status = service.get_status()
        
        print("\n" + "="*50)
        print("📊 Codex Dreams Status")
        print("="*50)
        
        if status['running']:
            print("🟢 Status: Running")
            print(f"🆔 Process ID: {status['pid']}")
            print(f"⏱️  Running for: {format_uptime(status['uptime'])}")
            print(f"💾 Memory usage: {status['memory_mb']:.1f} MB")
            print(f"📅 Schedule: {status['schedule']}")
            print(f"⏰ Next run: {format_time_until(status['next_run'])}")
        else:
            print("🔴 Status: Not running")
            if 'error' in status:
                print(f"❌ Error: {status['error']}")
        
        print(f"\n⚙️  Configuration:")
        print(f"   📄 Config file: {config.config_path}")
        print(f"   💾 Database: {config.postgres_url}")
        print(f"   🤖 AI Model: {config.ollama_model}")
        print(f"   📁 DuckDB: {config.expanded_duckdb_path}")
        print(f"   📝 Log file: {config.log_file}")
        
        if args.verbose:
            print(f"\n🔧 Detailed Configuration:")
            print(f"   Ollama URL: {config.ollama_url}")
            print(f"   Log directory: {config.log_dir}")
            print(f"   PID file: {config.pid_file}")
        
        if status['running']:
            print(f"\n💡 Quick commands:")
            print(f"   codex stop              Stop the service")
            print(f"   codex config schedule   Change frequency")
            print(f"   codex logs              View recent logs")
        else:
            print(f"\n💡 Quick commands:")
            print(f"   codex start             Start the service")
            print(f"   codex config            Edit configuration")
            print(f"   codex run               Test run once")
        
        print()
        return 0
        
    except FileNotFoundError:
        print("❌ Configuration not found")
        print("Run 'codex init' first to set up Codex Dreams")
        return 1
    except Exception as e:
        print(f"❌ Failed to get status: {e}")
        return 1


def cmd_config(args):
    """Configure Codex Dreams"""
    try:
        config = get_config()
        
        if args.show:
            show_config(config)
            return 0
        
        elif args.schedule:
            changed = quick_schedule_change(config)
            if changed:
                # Restart service if running
                service = CodexService(config)
                if service.is_running():
                    print("🔄 Restarting service with new schedule...")
                    service.restart()
                else:
                    print("Service is not running. Start it with 'codex start'")
            return 0
        
        else:
            # Full interactive config editor
            changed = interactive_config_editor(config)
            if changed:
                # Ask about restarting service
                service = CodexService(config)
                if service.is_running():
                    restart = input("\n🔄 Restart service to apply changes? [Y/n]: ").strip().lower()
                    if restart in ['', 'y', 'yes']:
                        print("Restarting service...")
                        service.restart()
                    else:
                        print("Changes saved. Restart manually with 'codex restart'")
            return 0
            
    except FileNotFoundError:
        print("❌ Configuration not found")
        print("Run 'codex init' first to set up Codex Dreams")
        return 1
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return 1


def cmd_run(args):
    """Run insights generation once (for testing)"""
    try:
        config = get_config()
        
        print("🔄 Running insights generation once...")
        print(f"📊 Database: {config.postgres_url}")
        print(f"🤖 Model: {config.ollama_model}")
        print()
        
        from .codex_scheduler import CodexScheduler
        scheduler = CodexScheduler(config)
        success = scheduler.run_once()
        
        if success:
            print("\n✅ Insights generation completed successfully!")
            return 0
        else:
            print("\n❌ Insights generation failed")
            print("Check the logs for details: codex logs")
            return 1
            
    except FileNotFoundError:
        print("❌ Configuration not found")
        print("Run 'codex init' first to set up Codex Dreams")
        return 1
    except Exception as e:
        print(f"❌ Failed to run: {e}")
        return 1


def cmd_env(args):
    """Manage environment configurations"""
    from .codex_env import show_environments, switch_env
    
    if not args.environment:
        show_environments()
        return 0
    
    env = args.environment.lower()
    
    if env in ["show", "list", "status"]:
        show_environments()
        return 0
    elif env in ["local", "dev", "production", "prod"]:
        # Check if service is running
        try:
            config = get_config()
            service = CodexService(config)
            
            if service.is_running():
                print("⚠️  Codex is currently running")
                response = input("Stop and switch environment? [y/N]: ").strip().lower()
                if response in ['y', 'yes']:
                    print("Stopping service...")
                    service.stop()
                    switch_env(env)
                    print("\nRestarting with new environment...")
                    new_config = get_config()
                    new_service = CodexService(new_config)
                    new_service.start()
                else:
                    print("Environment not changed")
            else:
                switch_env(env)
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
    else:
        print(f"❌ Unknown environment: {env}")
        print("Available: local, production")
        return 1
    return 0


def cmd_logs(args):
    """Show recent logs"""
    try:
        config = get_config()
        log_file = config.log_file
        
        if not log_file.exists():
            print("📝 No log file found")
            print(f"Expected location: {log_file}")
            print("Start the service to generate logs: codex start")
            return 0
        
        print(f"📝 Recent logs from {log_file}:")
        print("-" * 50)
        
        # Show last N lines
        lines_to_show = args.lines if hasattr(args, 'lines') else 20
        
        with open(log_file) as f:
            lines = f.readlines()
            for line in lines[-lines_to_show:]:
                print(line.rstrip())
        
        print("-" * 50)
        print(f"Full log file: {log_file}")
        return 0
        
    except FileNotFoundError:
        print("❌ Configuration not found")
        print("Run 'codex init' first to set up Codex Dreams")
        return 1
    except Exception as e:
        print(f"❌ Failed to read logs: {e}")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Codex Dreams - Biologically-inspired memory insights",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  codex init                 # First-time setup
  codex start                # Start generating insights
  codex status               # Check if running
  codex config               # Change settings
  codex config schedule      # Quick schedule change
  codex run                  # Test run once
  codex logs                 # View recent activity
        """)
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='First-time setup')
    init_parser.add_argument('--force', action='store_true', 
                           help='Force re-initialization')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start the service')
    start_parser.add_argument('--foreground', action='store_true',
                            help='Run in foreground (for testing)')
    
    # Stop command
    subparsers.add_parser('stop', help='Stop the service')
    
    # Restart command
    subparsers.add_parser('restart', help='Restart the service')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show service status')
    status_parser.add_argument('--verbose', '-v', action='store_true',
                             help='Show detailed information')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure settings')
    config_parser.add_argument('--show', action='store_true',
                             help='Show current configuration')
    config_parser.add_argument('--schedule', action='store_true',
                             help='Quick schedule change')
    
    # Run command
    subparsers.add_parser('run', help='Run insights generation once')
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Show recent logs')
    logs_parser.add_argument('--lines', type=int, default=20,
                           help='Number of lines to show')
    
    # Env command
    env_parser = subparsers.add_parser('env', help='Manage environments')
    env_parser.add_argument('environment', nargs='?',
                          help='Environment to switch to (local/production)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show help if no command provided
    if not args.command:
        # Check if config exists to suggest appropriate next step
        config_path = Path.home() / ".codex" / "config.yaml"
        if not config_path.exists():
            print("🎉 Welcome to Codex Dreams!")
            print()
            print("Get started with: codex init")
        else:
            print("📊 Codex Dreams")
            print()
            print("Quick commands:")
            print("  codex status    # Check if running")
            print("  codex start     # Start the service")
            print("  codex config    # Change settings")
        print()
        parser.print_help()
        return 0
    
    # Route to command handlers
    commands = {
        'init': cmd_init,
        'start': cmd_start,
        'stop': cmd_stop,
        'restart': cmd_restart,
        'status': cmd_status,
        'config': cmd_config,
        'run': cmd_run,
        'logs': cmd_logs,
        'env': cmd_env,
    }
    
    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())