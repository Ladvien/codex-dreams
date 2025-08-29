#!/usr/bin/env python3
"""
Interactive configuration editor for Codex Dreams.
Provides simple menu-driven config editing.
"""

from .codex_config import CodexConfig, interactive_schedule_selection


def interactive_config_editor(config: CodexConfig) -> bool:
    """Interactive configuration editor. Returns True if config was changed."""
    changed = False
    
    while True:
        print("\n" + "="*50)
        print("🔧 Codex Dreams Configuration")
        print("="*50)
        
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
                    print(f"✅ Database updated to: {config.db_host}:{config.db_port}/{config.db_name}")
            
            elif choice == "3":
                new_user = input(f"Database user [{config.db_user}]: ").strip()
                if new_user:
                    config.db_user = new_user
                    changed = True
                    print(f"✅ Database user updated to: {config.db_user}")
                
                # Ask about password
                current_pass = "set" if config.db_password else "not set"
                set_pass = input(f"Set database password? (currently {current_pass}) [y/N]: ").strip().lower()
                if set_pass in ['y', 'yes']:
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
                    if discard in ['y', 'yes']:
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
    print("\n" + "="*50)
    print("📋 Current Codex Dreams Configuration")
    print("="*50)
    
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
    print("\n" + "="*60)
    print("🎉 Welcome to Codex Dreams!")
    print("="*60)
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
    if change_db in ['y', 'yes']:
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
    if change_model in ['y', 'yes']:
        print("Available models (you may need to download them first):")
        print("  • qwen2.5:0.5b (fastest, good for testing)")
        print("  • qwen2.5:1.5b (balanced)")
        print("  • qwen2.5:3b (better quality)")
        
        new_model = input(f"AI model [{config.ollama_model}]: ").strip()
        if new_model:
            config.ollama_model = new_model
    
    # Save configuration
    config.save()
    
    print(f"\n✅ Setup complete!")
    print(f"📄 Configuration saved to: {config.config_path}")
    print(f"📊 Schedule: {config.schedule}")
    print(f"💾 Database: {config.postgres_url}")
    print(f"🤖 AI Model: {config.ollama_model}")
    print()
    print("🚀 Ready to start! Run 'codex start' to begin generating insights.")
    
    return config