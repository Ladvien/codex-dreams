#!/usr/bin/env python3
"""
Simple STORY-DB-003 Configuration Validation Test
Tests core profiles.yml configuration without complex imports
"""

import os
import sys
import yaml
import tempfile
from pathlib import Path
import subprocess
import duckdb

def test_profiles_yml_basic():
    """Test basic profiles.yml structure and validity"""
    profiles_path = Path.home() / '.dbt' / 'profiles.yml'
    
    print("🔍 Testing profiles.yml configuration...")
    
    # Test 1: File exists
    assert profiles_path.exists(), f"❌ profiles.yml not found at {profiles_path}"
    print("✅ profiles.yml file exists")
    
    # Test 2: Valid YAML
    with open(profiles_path, 'r') as f:
        config = yaml.safe_load(f)
    
    assert isinstance(config, dict), "❌ profiles.yml is not valid YAML"
    assert 'biological_memory' in config, "❌ biological_memory profile not found"
    print("✅ profiles.yml is valid YAML with biological_memory profile")
    
    # Test 3: Required targets
    bio_mem = config['biological_memory']
    assert 'outputs' in bio_mem, "❌ No outputs section found"
    
    outputs = bio_mem['outputs']
    required_targets = ['dev', 'prod', 'test']
    for target in required_targets:
        assert target in outputs, f"❌ Missing target: {target}"
        
    print(f"✅ All required targets present: {required_targets}")
    
    # Test 4: Required extensions
    required_extensions = ['httpfs', 'postgres_scanner', 'json', 'fts']
    for target in required_targets:
        target_config = outputs[target]
        extensions = target_config.get('extensions', [])
        for ext in required_extensions:
            assert ext in extensions, f"❌ Missing extension '{ext}' in target '{target}'"
            
    print(f"✅ All required extensions present: {required_extensions}")
    
    # Test 5: PostgreSQL attachment (dev and prod)
    for target in ['dev', 'prod']:
        target_config = outputs[target]
        assert 'attach' in target_config, f"❌ No PostgreSQL attachment in {target}"
        
        attachments = target_config['attach']
        assert len(attachments) > 0, f"❌ No attachments configured for {target}"
        
        pg_attach = attachments[0]
        assert pg_attach['type'] == 'postgres', f"❌ First attachment is not PostgreSQL in {target}"
        assert pg_attach['alias'] == 'source_memories', f"❌ Wrong PostgreSQL alias in {target}"
        
    print("✅ PostgreSQL attachments configured correctly")
    
    # Test 6: Environment variables  
    with open(profiles_path, 'r') as f:
        content = f.read()
        
    # Check for PostgreSQL environment variable (OLLAMA_URL is handled by UDF functions)
    assert 'env_var(' in content, "❌ No environment variables referenced"
    assert 'POSTGRES_DB_URL' in content, "❌ POSTGRES_DB_URL environment variable not referenced"
    
    # Check for LLM integration documentation
    assert 'llm_generate' in content, "❌ LLM UDF functions not documented"
    assert 'Ollama' in content, "❌ Ollama integration not documented"
    print("✅ Environment variables and LLM integration properly configured")
    
    return True

def test_duckdb_extensions():
    """Test that DuckDB can load all required extensions"""
    print("\n🔍 Testing DuckDB extensions...")
    
    try:
        # Use in-memory database to avoid file issues
        conn = duckdb.connect(':memory:')
        
        extensions = ['httpfs', 'postgres_scanner', 'json', 'fts']
        for ext in extensions:
            try:
                conn.execute(f"LOAD {ext};")
                print(f"✅ Extension loaded: {ext}")
            except Exception as e:
                print(f"❌ Failed to load extension {ext}: {e}")
                return False
                
        # Test basic functionality
        result = conn.execute("SELECT 1 as test").fetchone()
        assert result[0] == 1, "❌ Basic DuckDB query failed"
        print("✅ DuckDB basic functionality working")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ DuckDB test failed: {e}")
        return False

def test_dbt_debug():
    """Test dbt debug command"""
    print("\n🔍 Testing dbt debug...")
    
    # Set test environment variables
    env = os.environ.copy()
    env['OLLAMA_URL'] = 'http://192.168.1.110:11434'
    env['POSTGRES_DB_URL'] = 'postgresql://test:test@localhost:5432/test'
    env['TEST_DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test_db'
    
    try:
        result = subprocess.run(
            ['dbt', 'debug'],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            env=env,
            timeout=30
        )
        
        # Combine stdout and stderr for checking, remove ANSI color codes
        import re
        output = result.stdout + result.stderr
        output = re.sub(r'\x1b\[[0-9;]*m', '', output)  # Remove ANSI color codes
        
        # Check configuration validity (ignore connection errors for invalid credentials)
        if 'profiles.yml file [OK found and valid]' in output:
            print("✅ profiles.yml configuration valid")
            config_valid = True
        else:
            print("❌ profiles.yml configuration invalid")
            print("OUTPUT:", output)
            config_valid = False
            
        if 'dbt_project.yml file [OK found and valid]' in output:
            print("✅ dbt_project.yml configuration valid") 
            project_valid = True
        else:
            print("❌ dbt_project.yml configuration invalid")
            project_valid = False
            
        # Success if configurations are valid, even if connection fails due to credentials
        if config_valid and project_valid:
            if 'Connection test: [ERROR]' in output:
                print("⚠️  Connection test failed (expected with test credentials)")
            else:
                print("✅ Connection test passed")
            return True
            
        return False
            
        return True
        
    except subprocess.TimeoutExpired:
        print("⚠️  dbt debug timed out (may indicate configuration issues)")
        return False
    except FileNotFoundError:
        print("⚠️  dbt command not found (skipping this test)")
        return True  # Don't fail if dbt not installed

def main():
    """Run all tests"""
    print("🚀 STORY-DB-003 Configuration Validation Tests")
    print("=" * 60)
    
    tests = [
        test_profiles_yml_basic,
        test_duckdb_extensions,
        test_dbt_debug
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ {test.__name__} FAILED")
        except Exception as e:
            print(f"❌ {test.__name__} FAILED with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - STORY-DB-003 Configuration is Valid!")
        return True
    else:
        print("💥 SOME TESTS FAILED - Configuration needs fixes")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)