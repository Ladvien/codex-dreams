#!/usr/bin/env python3
"""
STORY-DB-003 Configuration Validation Tests
DevOps Engineer Agent - Complete profiles.yml Configuration

Tests all aspects of the dbt profiles.yml configuration for biological memory pipeline:
- DuckDB extensions loading
- PostgreSQL attachment configuration
- Ollama LLM integration settings
- Environment variable handling
- Multi-target configuration validation
"""

import os
import sys
import unittest
import tempfile
import subprocess
from pathlib import Path
import yaml
import duckdb

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from llm_integration_service import register_llm_functions
from error_handling import BiologicalMemoryErrorHandler


class TestStoryDB003Configuration(unittest.TestCase):
    """Test suite for STORY-DB-003 profiles.yml configuration"""
    
    def setUp(self):
        """Set up test environment"""
        self.profiles_path = Path.home() / '.dbt' / 'profiles.yml'
        self.project_root = Path(__file__).parent.parent.parent
        
        # Ensure test environment variables
        os.environ.setdefault('OLLAMA_URL', 'http://localhost:11434')
        os.environ.setdefault('POSTGRES_DB_URL', 'postgresql://user:pass@localhost:5432/test')
        os.environ.setdefault('TEST_DATABASE_URL', 'postgresql://user:pass@localhost:5432/test_db')
        
    def test_profiles_yml_exists_and_valid(self):
        """Test that profiles.yml exists and is valid YAML"""
        self.assertTrue(self.profiles_path.exists(), f"profiles.yml not found at {self.profiles_path}")
        
        with open(self.profiles_path, 'r') as f:
            try:
                config = yaml.safe_load(f)
                self.assertIsInstance(config, dict)
                self.assertIn('biological_memory', config)
            except yaml.YAMLError as e:
                self.fail(f"Invalid YAML in profiles.yml: {e}")
                
    def test_required_profile_structure(self):
        """Test that profiles.yml has correct structure for biological_memory"""
        with open(self.profiles_path, 'r') as f:
            config = yaml.safe_load(f)
            
        bio_mem = config['biological_memory']
        self.assertIn('target', bio_mem)
        self.assertIn('outputs', bio_mem)
        
        # Test all required targets
        outputs = bio_mem['outputs']
        self.assertIn('dev', outputs)
        self.assertIn('prod', outputs)
        self.assertIn('test', outputs)
        
    def test_duckdb_extensions_configuration(self):
        """Test that all required DuckDB extensions are configured"""
        with open(self.profiles_path, 'r') as f:
            config = yaml.safe_load(f)
            
        required_extensions = ['httpfs', 'postgres_scanner', 'json', 'fts']
        
        for target in ['dev', 'prod', 'test']:
            target_config = config['biological_memory']['outputs'][target]
            self.assertEqual(target_config['type'], 'duckdb')
            
            extensions = target_config.get('extensions', [])
            for ext in required_extensions:
                self.assertIn(ext, extensions, 
                    f"Missing required extension '{ext}' in target '{target}'")
                    
    def test_postgresql_attachment_configuration(self):
        """Test PostgreSQL attachment configuration"""
        with open(self.profiles_path, 'r') as f:
            config = yaml.safe_load(f)
            
        for target in ['dev', 'prod']:
            target_config = config['biological_memory']['outputs'][target]
            
            # Check PostgreSQL attachment
            self.assertIn('attach', target_config)
            attachments = target_config['attach']
            self.assertIsInstance(attachments, list)
            self.assertGreater(len(attachments), 0)
            
            pg_attach = attachments[0]  # First attachment should be PostgreSQL
            self.assertEqual(pg_attach['type'], 'postgres')
            self.assertEqual(pg_attach['alias'], 'source_memories')
            self.assertIn('env_var(', pg_attach['path'])
            
    def test_environment_variable_references(self):
        """Test that environment variables are properly referenced"""
        with open(self.profiles_path, 'r') as f:
            content = f.read()
            
        # Check for proper dbt environment variable syntax
        self.assertIn('{{ env_var("OLLAMA_URL") }}', content)
        self.assertIn('{{ env_var("POSTGRES_DB_URL") }}', content)
        
        # Ensure no hardcoded credentials
        self.assertNotIn('password123', content.lower())
        self.assertNotIn('username:', content.lower())
        
    def test_duckdb_connection_basic(self):
        """Test basic DuckDB connection with extensions"""
        with tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False) as tmp:
            try:
                conn = duckdb.connect(tmp.name)
                
                # Test loading required extensions
                extensions = ['httpfs', 'postgres_scanner', 'json', 'fts']
                for ext in extensions:
                    try:
                        conn.execute(f"LOAD {ext};")
                    except Exception as e:
                        self.fail(f"Failed to load extension {ext}: {e}")
                        
                # Test basic functionality
                result = conn.execute("SELECT 1 as test").fetchone()
                self.assertEqual(result[0], 1)
                
                conn.close()
            finally:
                os.unlink(tmp.name)
                
    def test_llm_udf_functions_registration(self):
        """Test that LLM UDF functions can be registered"""
        with tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False) as tmp:
            try:
                conn = duckdb.connect(tmp.name)
                
                # Load required extensions
                conn.execute("LOAD httpfs;")
                conn.execute("LOAD json;")
                
                # Test UDF registration
                success = register_llm_functions(conn)
                self.assertTrue(success, "Failed to register LLM UDF functions")
                
                # Test that functions are available
                functions = conn.execute("""
                    SELECT function_name 
                    FROM duckdb_functions() 
                    WHERE function_name IN ('llm_generate', 'llm_generate_json')
                """).fetchall()
                
                function_names = [f[0] for f in functions]
                self.assertIn('llm_generate', function_names)
                self.assertIn('llm_generate_json', function_names)
                
                conn.close()
            finally:
                os.unlink(tmp.name)
                
    def test_dbt_debug_configuration_validity(self):
        """Test that dbt debug reports configuration as valid"""
        # Set environment variables for the test
        env = os.environ.copy()
        env['OLLAMA_URL'] = 'http://localhost:11434'
        env['POSTGRES_DB_URL'] = 'postgresql://test:test@localhost:5432/test'
        
        # Run dbt debug and capture output
        result = subprocess.run(
            ['dbt', 'debug', '--target', 'test'],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            env=env
        )
        
        # Check that configuration files are valid
        self.assertIn('profiles.yml file [OK found and valid]', result.stderr)
        self.assertIn('dbt_project.yml file [OK found and valid]', result.stderr)
        
    def test_target_specific_configurations(self):
        """Test target-specific configuration differences"""
        with open(self.profiles_path, 'r') as f:
            config = yaml.safe_load(f)
            
        outputs = config['biological_memory']['outputs']
        
        # Dev should use 4GB memory, 4 threads
        dev_config = outputs['dev']
        self.assertEqual(dev_config['settings']['max_memory'], '4GB')
        self.assertEqual(dev_config['threads'], 4)
        
        # Prod should use 8GB memory, 8 threads
        prod_config = outputs['prod']
        self.assertEqual(prod_config['settings']['max_memory'], '8GB')
        self.assertEqual(prod_config['threads'], 8)
        
        # Test should use 2GB memory, 2 threads, memory database
        test_config = outputs['test']
        self.assertEqual(test_config['settings']['max_memory'], '2GB')
        self.assertEqual(test_config['threads'], 2)
        self.assertEqual(test_config['path'], ':memory:')
        
    def test_ollama_connectivity(self):
        """Test that Ollama endpoint is accessible"""
        import requests
        
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=10)
            response.raise_for_status()
            
            # Check that required models are available
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            
            # Look for gpt-oss model (any version)
            gpt_oss_available = any('gpt-oss' in model for model in models)
            self.assertTrue(gpt_oss_available, 
                f"gpt-oss model not found in available models: {models}")
                
        except requests.RequestException as e:
            self.skipTest(f"Ollama endpoint not accessible: {e}")
            
    def test_configuration_comments_documentation(self):
        """Test that configuration is well-documented with comments"""
        with open(self.profiles_path, 'r') as f:
            content = f.read()
            
        # Check for key documentation comments
        self.assertIn('# Updated by DevOps Engineer Agent for STORY-DB-003', content)
        self.assertIn('# DuckDB extensions', content.lower())
        self.assertIn('# PostgreSQL', content.lower())  
        self.assertIn('# Ollama', content.lower())
        
        # Check that each extension is documented
        extensions = ['httpfs', 'postgres_scanner', 'json', 'fts']
        for ext in extensions:
            self.assertTrue(
                any(ext in line and '#' in line for line in content.splitlines()),
                f"Extension {ext} should be documented with inline comment"
            )


class TestStoryDB003IntegrationScenarios(unittest.TestCase):
    """Integration test scenarios for STORY-DB-003"""
    
    def test_full_pipeline_configuration_compatibility(self):
        """Test that configuration works with actual biological memory models"""
        # This would be expanded to test actual dbt model compilation
        # For now, test that the structure supports the expected usage patterns
        
        profiles_path = Path.home() / '.dbt' / 'profiles.yml'
        with open(profiles_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Ensure configuration supports the model patterns we see in the codebase
        bio_mem = config['biological_memory']
        
        # Test that we can handle multiple environments
        self.assertIn('dev', bio_mem['outputs'])
        self.assertIn('prod', bio_mem['outputs'])
        self.assertIn('test', bio_mem['outputs'])
        
        # Test that each environment has the capabilities needed by our models
        for target_name, target_config in bio_mem['outputs'].items():
            self.assertIn('httpfs', target_config['extensions'])  # For LLM HTTP calls
            self.assertIn('json', target_config['extensions'])     # For LLM JSON responses
            
    def test_story_db_003_acceptance_criteria(self):
        """Test all acceptance criteria for STORY-DB-003 are met"""
        profiles_path = Path.home() / '.dbt' / 'profiles.yml'
        
        # 1. Complete DuckDB configuration ✅
        self.assertTrue(profiles_path.exists())
        
        with open(profiles_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # 2. PostgreSQL attachment via postgres_scanner ✅
        dev_config = config['biological_memory']['outputs']['dev']
        self.assertIn('postgres_scanner', dev_config['extensions'])
        self.assertIn('attach', dev_config)
        
        # 3. Ollama LLM integration configured ✅
        # (Via UDF functions rather than prompt_model settings)
        content = open(profiles_path).read()
        self.assertIn('Ollama', content)
        self.assertIn('llm_generate', content)
        
        # 4. Required DuckDB extensions ✅
        required_exts = ['httpfs', 'postgres_scanner', 'json', 'fts']
        for ext in required_exts:
            self.assertIn(ext, dev_config['extensions'])
            
        # 5. Environment variables properly used ✅
        self.assertIn('env_var("OLLAMA_URL")', content)
        self.assertIn('env_var("POSTGRES_DB_URL")', content)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestStoryDB003Configuration))
    suite.addTests(loader.loadTestsFromTestCase(TestStoryDB003IntegrationScenarios))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with proper code
    sys.exit(0 if result.wasSuccessful() else 1)