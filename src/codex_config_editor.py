#!/usr/bin/env python3
"""
Interactive configuration editor for Codex Dreams.
Provides simple menu-driven config editing.
"""

import socket
import subprocess
from pathlib import Path
from typing import Any, Tuple

from .codex_config import CodexConfig, interactive_schedule_selection


def check_postgresql_connection(
    host: str, port: int, user: str, database: str, password: str = None
) -> Tuple[bool, str]:
    """Check if PostgreSQL is accessible and database exists"""
    try:
        import psycopg2

        # Build connection string
        conn_params = {
            "host": host,
            "port": port,
            "user": user,
            "database": database,
        }
        if password:
            conn_params["password"] = password

        # Try to connect
        conn = psycopg2.connect(**conn_params)
        conn.close()
        return True, "✅ PostgreSQL connection successful"

    except ImportError:
        return False, "❌ psycopg2 not installed (pip install psycopg2-binary)"
    except psycopg2.OperationalError as e:
        if "does not exist" in str(e):
            return False, f"❌ Database '{database}' does not exist"
        elif "authentication failed" in str(e):
            return False, f"❌ Authentication failed for user '{user}'"
        else:
            return False, f"❌ PostgreSQL connection failed: {str(e)[:100]}..."
    except Exception as e:
        return False, f"❌ Connection error: {str(e)[:100]}..."


def check_ollama_service(host: str, port: int, model: str = None) -> Tuple[bool, str]:
    """Check if Ollama service is running and model is available"""
    try:
        import requests

        # Check if Ollama is running
        ollama_url = f"http://{host}:{port}"
        response = requests.get(f"{ollama_url}/api/version", timeout=5)

        if response.status_code != 200:
            return False, f"❌ Ollama service not responding (status: {response.status_code})"

        # Check if specific model is available
        if model:
            response = requests.post(f"{ollama_url}/api/show", json={"name": model}, timeout=10)
            if response.status_code == 404:
                return (
                    False,
                    f"⚠️  Ollama running, but model '{model}' not found. Run: ollama pull {model}",
                )
            elif response.status_code != 200:
                return False, f"⚠️  Ollama running, but can't verify model '{model}'"

        return True, f"✅ Ollama service running" + (f" with {model}" if model else "")

    except ImportError:
        return False, "❌ requests library not installed (pip install requests)"
    except requests.exceptions.ConnectionError:
        return False, f"❌ Cannot connect to Ollama at {host}:{port}"
    except requests.exceptions.Timeout:
        return False, f"❌ Ollama connection timeout at {host}:{port}"
    except Exception as e:
        return False, f"❌ Ollama check error: {str(e)[:100]}..."


def check_service_dependencies(config: CodexConfig) -> None:
    """Check all service dependencies and provide guidance"""
    print(f"\n🔍 Checking Service Dependencies")
    print("=" * 50)

    # Check PostgreSQL
    print("📊 Checking PostgreSQL...")
    pg_ok, pg_msg = check_postgresql_connection(
        config.db_host, config.db_port, config.db_user, config.db_name, config.db_password
    )
    print(f"   {pg_msg}")

    if not pg_ok:
        print("   💡 To fix PostgreSQL issues:")
        print("   • Install PostgreSQL: brew install postgresql")
        print("   • Start service: brew services start postgresql")
        print(f"   • Create database: createdb {config.db_name}")
        print(f"   • Create user: createuser {config.db_user}")

    # Check Ollama
    print("\n🤖 Checking Ollama...")
    ollama_ok, ollama_msg = check_ollama_service(
        config.ollama_host, config.ollama_port, config.ollama_model
    )
    print(f"   {ollama_msg}")

    if not ollama_ok:
        print("   💡 To fix Ollama issues:")
        print("   • Install Ollama: curl -fsSL https://ollama.ai/install.sh | sh")
        print("   • Start service: ollama serve")
        print(f"   • Download model: ollama pull {config.ollama_model}")
        print("   • Alternative model: ollama pull qwen2.5:0.5b")

    # Check dbt
    print("\n🏗️  Checking dbt...")
    try:
        result = subprocess.run(["dbt", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("   ✅ dbt installed and accessible")
        else:
            print("   ⚠️  dbt installed but may have issues")
    except FileNotFoundError:
        print("   ❌ dbt not found in PATH")
        print("   💡 Install: pip install dbt-core dbt-duckdb")
    except Exception as e:
        print(f"   ⚠️  dbt check error: {str(e)[:50]}...")

    # Overall status
    print("\n" + "=" * 50)
    if pg_ok and ollama_ok:
        print("🎉 All services ready! You can start using codex-dreams.")
    else:
        print("⚠️  Some services need setup. Follow the suggestions above.")
        print("💡 You can run 'codex config' to adjust settings anytime.")


def interactive_config_editor(config: CodexConfig) -> bool:
    """Interactive configuration editor. Returns True if config was changed."""
    changed = False

    while True:
        print("\n" + "=" * 50)
        print("🔧 Codex Dreams Configuration")
        print("=" * 50)

        print(f"Current Settings:")
        print(f"  1. Schedule: {config.schedule}")
        print(f"  2. Database: {config.db_host}:{config.db_port}/{config.db_name}")
        print(f"  3. Database User: {config.db_user}")
        print(f"  4. AI Model: {config.ollama_model}")
        print(f"  5. Ollama Server: {config.ollama_host}:{config.ollama_port}")
        print(f"  6. DuckDB Path: {config.duckdb_path}")
        print(f"  7. Save & Exit")
        print(f"  8. Exit without saving")

        try:
            choice = input(f"\nWhat would you like to change? [1-8]: ").strip()

            if choice == "1":
                new_schedule = interactive_schedule_selection(config.schedule)
                if new_schedule != config.schedule:
                    config.schedule = new_schedule
                    changed = True
                    print(f"✅ Schedule updated to: {config.schedule}")

            elif choice == "2":
                print(f"\nCurrent database: {config.db_host}:{config.db_port}/{config.db_name}")
                new_host = input(f"Database host [{config.db_host}]: ").strip()
                if new_host:
                    config.db_host = new_host
                    changed = True

                new_port = input(f"Database port [{config.db_port}]: ").strip()
                if new_port and new_port.isdigit():
                    config.db_port = int(new_port)
                    changed = True

                new_name = input(f"Database name [{config.db_name}]: ").strip()
                if new_name:
                    config.db_name = new_name
                    changed = True

                if changed:
                    print(
                        f"✅ Database updated to: {config.db_host}:{config.db_port}/{config.db_name}"
                    )

            elif choice == "3":
                new_user = input(f"Database user [{config.db_user}]: ").strip()
                if new_user:
                    config.db_user = new_user
                    changed = True
                    print(f"✅ Database user updated to: {config.db_user}")

                # Ask about password
                current_pass = "set" if config.db_password else "not set"
                set_pass = (
                    input(f"Set database password? (currently {current_pass}) [y/N]: ")
                    .strip()
                    .lower()
                )
                if set_pass in ["y", "yes"]:
                    import getpass

                    new_password = getpass.getpass("Enter password (or leave blank to clear): ")
                    if new_password:
                        config.db_password = new_password
                        print("✅ Database password updated")
                    else:
                        config.db_password = None
                        print("✅ Database password cleared")
                    changed = True

            elif choice == "4":
                print(f"\nCurrent AI model: {config.ollama_model}")
                print("Common models:")
                print("  • qwen2.5:0.5b (fastest)")
                print("  • qwen2.5:1.5b (balanced)")
                print("  • qwen2.5:3b (better quality)")
                print("  • qwen2.5:7b (highest quality)")

                new_model = input(f"AI model [{config.ollama_model}]: ").strip()
                if new_model:
                    config.ollama_model = new_model
                    changed = True
                    print(f"✅ AI model updated to: {config.ollama_model}")

            elif choice == "5":
                print(f"\nCurrent Ollama server: {config.ollama_host}:{config.ollama_port}")
                new_host = input(f"Ollama host [{config.ollama_host}]: ").strip()
                if new_host:
                    config.ollama_host = new_host
                    changed = True

                new_port = input(f"Ollama port [{config.ollama_port}]: ").strip()
                if new_port and new_port.isdigit():
                    config.ollama_port = int(new_port)
                    changed = True

                if changed:
                    print(f"✅ Ollama server updated to: {config.ollama_host}:{config.ollama_port}")

            elif choice == "6":
                new_path = input(f"DuckDB path [{config.duckdb_path}]: ").strip()
                if new_path:
                    config.duckdb_path = new_path
                    changed = True
                    print(f"✅ DuckDB path updated to: {config.duckdb_path}")

            elif choice == "7":
                if changed:
                    config.save()
                    print("✅ Configuration saved!")
                else:
                    print("No changes to save.")
                return changed

            elif choice == "8":
                if changed:
                    discard = input("Discard changes? [y/N]: ").strip().lower()
                    if discard in ["y", "yes"]:
                        print("Changes discarded.")
                        return False
                else:
                    return False

            else:
                print("Invalid choice. Please enter 1-8.")

        except KeyboardInterrupt:
            print("\n\nExiting configuration editor.")
            return changed
        except Exception as e:
            print(f"Error: {e}")
            continue


def quick_schedule_change(config: CodexConfig) -> bool:
    """Quick schedule change without full menu"""
    print(f"\nCurrent schedule: {config.schedule}")
    new_schedule = interactive_schedule_selection(config.schedule)

    if new_schedule != config.schedule:
        config.schedule = new_schedule
        config.save()
        return True

    return False


def show_config(config: CodexConfig) -> None:
    """Display current configuration in a readable format"""
    print("\n" + "=" * 50)
    print("📋 Current Codex Dreams Configuration")
    print("=" * 50)

    print(f"\n🕒 Schedule:")
    interval_minutes = config.parse_schedule()
    print(f"   {config.schedule} ({interval_minutes} minutes)")

    print(f"\n💾 Database:")
    print(f"   PostgreSQL: {config.postgres_url}")

    print(f"\n🤖 AI Model:")
    print(f"   Ollama: {config.ollama_url}")
    print(f"   Model: {config.ollama_model}")

    print(f"\n📁 Storage:")
    print(f"   DuckDB: {config.expanded_duckdb_path}")
    print(f"   Logs: {config.log_file}")

    print(f"\n📄 Config File:")
    print(f"   {config.config_path}")

    print(f"\n💡 To change settings:")
    print(f"   codex config          # Interactive editor")
    print(f"   codex config schedule # Quick schedule change")
    print()


def first_time_setup() -> CodexConfig:
    """First-time interactive setup"""
    print("\n" + "=" * 60)
    print("🎉 Welcome to Codex Dreams!")
    print("=" * 60)
    print("Let's set up your biologically-inspired memory system.")
    print()

    config = CodexConfig()

    # Schedule selection
    print("First, let's choose how often to analyze your memories:")
    config.schedule = interactive_schedule_selection(config.schedule)

    # Database setup
    print(f"\n📊 Database Configuration")
    print(f"I'll connect to PostgreSQL to read your memories.")
    print(f"Current settings: {config.db_host}:{config.db_port}/{config.db_name}")

    change_db = input("Change database settings? [y/N]: ").strip().lower()
    if change_db in ["y", "yes"]:
        new_host = input(f"Database host [{config.db_host}]: ").strip()
        if new_host:
            config.db_host = new_host

        new_port = input(f"Database port [{config.db_port}]: ").strip()
        if new_port and new_port.isdigit():
            config.db_port = int(new_port)

        new_name = input(f"Database name [{config.db_name}]: ").strip()
        if new_name:
            config.db_name = new_name

        new_user = input(f"Database user [{config.db_user}]: ").strip()
        if new_user:
            config.db_user = new_user

    # AI Model setup
    print(f"\n🤖 AI Model Configuration")
    print(f"I'll use Ollama to generate insights from your memories.")
    print(f"Current model: {config.ollama_model}")

    change_model = input("Change AI model? [y/N]: ").strip().lower()
    if change_model in ["y", "yes"]:
        print("Available models (you may need to download them first):")
        print("  • qwen2.5:0.5b (fastest, good for testing)")
        print("  • qwen2.5:1.5b (balanced)")
        print("  • qwen2.5:3b (better quality)")

        new_model = input(f"AI model [{config.ollama_model}]: ").strip()
        if new_model:
            config.ollama_model = new_model

    # .env file setup
    print(f"\n📄 Environment File Setup")
    print(f"I'll create a .env file for dbt and other services.")

    env_file_path = Path.cwd() / ".env"
    env_example_path = Path.cwd() / ".env.example"

    create_env = True
    if env_file_path.exists():
        overwrite = input(f".env file exists. Overwrite? [y/N]: ").strip().lower()
        create_env = overwrite in ["y", "yes"]

    if create_env:
        if env_example_path.exists():
            # Read the template
            with open(env_example_path, "r") as f:
                env_content = f.read()

            # Replace placeholder values with actual configuration
            postgres_url = f"postgresql://{config.db_user}:{config.db_password or 'YOUR_PASSWORD'}@{config.db_host}:{config.db_port}/{config.db_name}"

            # Replace key variables
            replacements = {
                "GENERATE_SECURE_PASSWORD_HERE": config.db_password or "YOUR_PASSWORD_HERE",
                "localhost": config.db_host,
                "5432": str(config.db_port),
                "codex_db": config.db_name,
                "codex_user": config.db_user,
                "gpt-oss:20b": config.ollama_model,
            }

            for old_val, new_val in replacements.items():
                env_content = env_content.replace(old_val, new_val)

            # Write the .env file
            with open(env_file_path, "w") as f:
                f.write(env_content)

            print(f"✅ .env file created at {env_file_path}")

            if not config.db_password:
                print(f"⚠️  Remember to set your database password in .env file!")
        else:
            # Create basic .env file
            basic_env = f"""# Codex Dreams Environment Configuration
POSTGRES_DB_URL={postgres_url}
DATABASE_URL={postgres_url}
OLLAMA_URL=http://{config.ollama_host}:{config.ollama_port}
OLLAMA_MODEL={config.ollama_model}
EMBEDDING_MODEL=nomic-embed-text
DUCKDB_PATH={config.duckdb_path}
"""
            with open(env_file_path, "w") as f:
                f.write(basic_env)
            print(f"✅ Basic .env file created at {env_file_path}")

    # Save configuration
    config.save()

    # Check service dependencies
    check_service_dependencies(config)

    print(f"\n✅ Setup complete!")
    print(f"📄 Configuration saved to: {config.config_path}")
    print(f"📊 Schedule: {config.schedule}")
    print(f"💾 Database: {config.postgres_url}")
    print(f"🤖 AI Model: {config.ollama_model}")
    print()
    print("🚀 Next steps:")
    print("   • Fix any service issues shown above")
    print("   • Run 'codex start' to begin generating insights")
    print("   • Use 'codex status' to monitor the service")

    return config
