#!/usr/bin/env python3
"""
Script to load .env file and run environment tests
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_path = project_root / '.env'
    
    if not env_path.exists():
        print(f"❌ .env file not found at {env_path}")
        return False
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip('"\'')
                os.environ[key] = value
    
    print(f"✅ Loaded environment from {env_path}")
    return True

if __name__ == "__main__":
    print("🔧 BMP-001 Environment Test Runner")
    print("=" * 50)
    
    # Load .env file
    if not load_env_file():
        sys.exit(1)
    
    # Print loaded variables (mask sensitive data)
    print("\n📋 Environment Variables:")
    for key in ['POSTGRES_DB_URL', 'OLLAMA_URL', 'OLLAMA_MODEL', 'EMBEDDING_MODEL', 'MAX_DB_CONNECTIONS']:
        value = os.environ.get(key, 'NOT SET')
        if 'password' in value.lower() or 'pass' in key.lower():
            # Mask passwords
            value = value[:10] + "***" + value[-10:] if len(value) > 20 else "***"
        print(f"  {key}: {value}")
    
    print("\n🧪 Running tests...")
    
    # Import and run the test
    try:
        # Set PYTHONPATH to include current directory
        sys.path.insert(0, str(project_root))
        
        # Import all functions from the test module
        import tests.infrastructure.test_environment as test_env
        
        # Initialize components
        config = test_env.EnvironmentConfig()
        postgres = test_env.PostgreSQLConnection(config)
        ollama = test_env.OllamaConnection(config)
        
        print("\n📋 Testing Environment Variables...")
        test_env.test_env_variables_loaded(config)
        test_env.test_postgres_db_url_format(config)
        test_env.test_max_db_connections_configuration(config)
        print("✅ Environment variables validated")
        
        print("\n🐘 Testing PostgreSQL Connection...")
        postgres_result = postgres.test_connection()
        print(f"✅ PostgreSQL: {postgres_result['database']} as {postgres_result['user']}")
        
        pool_result = postgres.test_connection_pool()
        print(f"✅ Connection Pool: {pool_result['max_connections']} max connections")
        
        print("\n🦙 Testing Ollama Connection...")
        ollama_result = ollama.test_connection()
        print(f"✅ Ollama: {len(ollama_result['available_models'])} models available")
        
        model_result = ollama.test_model_availability()
        print(f"✅ Models: LLM={model_result['llm_available']}, Embedding={model_result['embedding_available']}")
        
        if model_result['llm_available']:
            gen_result = ollama.test_generation()
            print(f"✅ Generation: {gen_result['eval_count']} tokens")
        
        if model_result['embedding_available']:
            emb_result = ollama.test_embeddings()
            print(f"✅ Embeddings: {emb_result['embedding_dimensions']} dimensions")
        
        print("\n🔗 Running End-to-End Validation...")
        test_env.test_end_to_end_environment_validation(config, postgres, ollama)
        print("✅ End-to-end validation successful")
        
        print("\n🎉 BMP-001 Environment Setup: ALL TESTS PASSED")
        print("Ready for biological memory pipeline implementation!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)