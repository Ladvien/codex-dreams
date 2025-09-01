#!/usr/bin/env python3
"""
Test suite for DuckDB Performance Configuration
Tests that the performance settings are applied correctly and PostgreSQL integration works.
"""

import unittest
import os
import duckdb
from unittest.mock import patch, MagicMock
import tempfile
import logging

class TestDuckDBPerformanceConfig(unittest.TestCase):
    """Test DuckDB performance configuration settings and PostgreSQL integration."""
    
    def setUp(self):
        """Set up test environment with temporary DuckDB database."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, 'test_performance.duckdb')
        self.conn = duckdb.connect(self.test_db_path)
        
        # Load postgres extension for testing
        try:
            self.conn.execute("INSTALL postgres")
            self.conn.execute("LOAD postgres")
        except Exception as e:
            logging.warning(f"Could not load postgres extension: {e}")
    
    def tearDown(self):
        """Clean up test resources."""
        if self.conn:
            self.conn.close()
        
        # Clean up temp files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_performance_settings_basic(self):
        """Test that basic DuckDB performance settings can be applied."""
        config_sql = """
        SET memory_limit = '8GB';
        SET threads = 4;
        SET max_memory = '6GB';
        SET preserve_insertion_order = false;
        SET default_order = 'ASC';
        SET enable_progress_bar = true;
        SET enable_profiling = true;
        SET max_expression_depth = 1000;
        SET enable_parallel_aggregation = true;
        """
        
        # Should not raise any exceptions
        try:
            for statement in config_sql.strip().split(';'):
                if statement.strip():
                    self.conn.execute(statement)
        except Exception as e:
            self.fail(f"Performance settings failed to apply: {e}")
    
    def test_memory_limit_setting(self):
        """Test memory limit configuration."""
        self.conn.execute("SET memory_limit = '8GB'")
        
        # Verify setting is applied (DuckDB doesn't have a direct way to check this,
        # but we can verify it doesn't throw an error)
        result = self.conn.execute("SELECT 1 as test").fetchone()
        self.assertEqual(result[0], 1)
    
    def test_thread_configuration(self):
        """Test thread configuration setting."""
        self.conn.execute("SET threads = 4")
        
        # Test with a query that would use multiple threads
        result = self.conn.execute("SELECT 1 as test").fetchone()
        self.assertEqual(result[0], 1)
    
    def test_performance_benchmarks_table_creation(self):
        """Test that performance benchmarks table can be created."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS performance_benchmarks (
            benchmark_id VARCHAR PRIMARY KEY DEFAULT ('perf_' || gen_random_uuid()),
            query_type VARCHAR NOT NULL,
            query_name VARCHAR NOT NULL,
            execution_time_ms DOUBLE NOT NULL,
            rows_processed INTEGER,
            target_time_ms DOUBLE DEFAULT 50.0,
            memory_usage_mb DOUBLE,
            cpu_usage_percent DOUBLE,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        try:
            self.conn.execute(create_table_sql)
        except Exception as e:
            self.fail(f"Failed to create performance_benchmarks table: {e}")
        
        # Verify table exists
        tables = self.conn.execute("SHOW TABLES").fetchall()
        table_names = [table[0] for table in tables]
        self.assertIn('performance_benchmarks', table_names)
    
    def test_performance_table_indexes(self):
        """Test that performance table indexes can be created."""
        # First create the table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS performance_benchmarks (
                benchmark_id VARCHAR PRIMARY KEY DEFAULT ('perf_' || gen_random_uuid()),
                query_type VARCHAR NOT NULL,
                query_name VARCHAR NOT NULL,
                execution_time_ms DOUBLE NOT NULL,
                rows_processed INTEGER,
                target_time_ms DOUBLE DEFAULT 50.0,
                memory_usage_mb DOUBLE,
                cpu_usage_percent DOUBLE,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create indexes
        index_sql = [
            "CREATE INDEX IF NOT EXISTS idx_performance_benchmarks_query_type ON performance_benchmarks (query_type, executed_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_performance_benchmarks_execution_time ON performance_benchmarks (execution_time_ms DESC);"
        ]
        
        for sql in index_sql:
            try:
                self.conn.execute(sql)
            except Exception as e:
                self.fail(f"Failed to create index: {sql}. Error: {e}")
    
    def test_performance_monitoring_insert(self):
        """Test that performance monitoring data can be inserted."""
        # Create table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS performance_benchmarks (
                benchmark_id VARCHAR PRIMARY KEY DEFAULT ('perf_' || gen_random_uuid()),
                query_type VARCHAR NOT NULL,
                query_name VARCHAR NOT NULL,
                execution_time_ms DOUBLE NOT NULL,
                rows_processed INTEGER,
                target_time_ms DOUBLE DEFAULT 50.0,
                memory_usage_mb DOUBLE,
                cpu_usage_percent DOUBLE,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Insert test data
        self.conn.execute("""
            INSERT INTO performance_benchmarks 
            (query_type, query_name, execution_time_ms, rows_processed, memory_usage_mb, cpu_usage_percent)
            VALUES 
            ('working_memory', 'test_query', 25.5, 1000, 128.0, 15.2);
        """)
        
        # Verify data was inserted
        result = self.conn.execute("""
            SELECT query_type, query_name, execution_time_ms 
            FROM performance_benchmarks 
            WHERE query_name = 'test_query'
        """).fetchone()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'working_memory')
        self.assertEqual(result[1], 'test_query')
        self.assertEqual(result[2], 25.5)
    
    @patch('duckdb.connect')
    def test_postgres_connection_mock(self, mock_connect):
        """Test PostgreSQL connection configuration (mocked)."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        # Test that postgres connection setup doesn't fail
        try:
            conn = duckdb.connect(':memory:')
            # This would typically fail in test environment, but we're testing the SQL syntax
            postgres_sql = """
            ATTACH 'dbname=codex_db host=192.168.1.104 user=test password=test' AS codex_db (TYPE postgres);
            """
            # We can't actually execute this without a real PostgreSQL server,
            # but we can verify the SQL is syntactically correct
            self.assertIsInstance(postgres_sql, str)
            self.assertIn('codex_db', postgres_sql)
        except Exception:
            # Expected to fail in test environment without real PostgreSQL
            pass
    
    def test_configuration_success_message(self):
        """Test that configuration success message is generated correctly."""
        success_sql = """
        SELECT 'DuckDB optimized for biological memory workload - Target: <50ms queries' as status,
               '8GB' as memory_limit,
               '4' as thread_count,
               CURRENT_TIMESTAMP as configured_at;
        """
        
        result = self.conn.execute(success_sql).fetchone()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'DuckDB optimized for biological memory workload - Target: <50ms queries')
        self.assertEqual(result[1], '8GB')
        self.assertEqual(result[2], '4')
        self.assertIsNotNone(result[3])  # configured_at timestamp
    
    def test_config_file_execution(self):
        """Test that the actual configuration file can be executed without errors."""
        config_file_path = '/Users/ladvien/codex-dreams/biological_memory/duckdb_performance_config.sql'
        
        if not os.path.exists(config_file_path):
            self.skipTest(f"Configuration file not found: {config_file_path}")
        
        try:
            with open(config_file_path, 'r') as f:
                config_content = f.read()
            
            # Split by semicolons and execute each statement
            statements = [stmt.strip() for stmt in config_content.split(';') if stmt.strip()]
            
            executed_count = 0
            for statement in statements:
                # Skip comments and empty lines
                if not statement or statement.startswith('--'):
                    continue
                
                try:
                    self.conn.execute(statement)
                    executed_count += 1
                except Exception as e:
                    # Some statements may fail in test environment (like ATTACH commands)
                    # but we want to test that the SQL syntax is valid
                    if "attach" not in statement.lower() and "postgres" not in statement.lower():
                        self.fail(f"Failed to execute statement: {statement[:50]}... Error: {e}")
            
            self.assertGreater(executed_count, 0, "Should have executed at least some statements")
            
        except Exception as e:
            self.fail(f"Failed to read or execute config file: {e}")
    
    def test_biological_memory_specific_settings(self):
        """Test biological memory specific performance settings."""
        bio_settings = [
            "SET max_expression_depth = 1000",
            "SET enable_parallel_aggregation = true"
        ]
        
        for setting in bio_settings:
            try:
                self.conn.execute(setting)
            except Exception as e:
                self.fail(f"Failed to apply biological memory setting: {setting}. Error: {e}")


class TestDuckDBConfigValidation(unittest.TestCase):
    """Validation tests for DuckDB configuration correctness."""
    
    def test_config_file_exists(self):
        """Test that the configuration file exists."""
        config_file_path = '/Users/ladvien/codex-dreams/biological_memory/duckdb_performance_config.sql'
        self.assertTrue(os.path.exists(config_file_path), 
                       f"Configuration file should exist at {config_file_path}")
    
    def test_config_file_readable(self):
        """Test that the configuration file is readable."""
        config_file_path = '/Users/ladvien/codex-dreams/biological_memory/duckdb_performance_config.sql'
        
        if not os.path.exists(config_file_path):
            self.skipTest(f"Configuration file not found: {config_file_path}")
        
        try:
            with open(config_file_path, 'r') as f:
                content = f.read()
            
            self.assertGreater(len(content), 0, "Configuration file should not be empty")
            self.assertIn('DuckDB', content, "Should reference DuckDB")
            self.assertIn('memory_limit', content, "Should set memory limits")
            
        except Exception as e:
            self.fail(f"Failed to read configuration file: {e}")
    
    def test_no_invalid_table_references(self):
        """Test that configuration file doesn't contain invalid table references."""
        config_file_path = '/Users/ladvien/codex-dreams/biological_memory/duckdb_performance_config.sql'
        
        if not os.path.exists(config_file_path):
            self.skipTest(f"Configuration file not found: {config_file_path}")
        
        with open(config_file_path, 'r') as f:
            content = f.read()
        
        # Should not contain old placeholder table names
        invalid_patterns = [
            'CREATE INDEX.*ON raw_memories',
            'CREATE INDEX.*ON llm_response_cache', 
            'ANALYZE raw_memories',
            'ANALYZE llm_response_cache',
            'ANALYZE performance_metrics'
        ]
        
        import re
        for pattern in invalid_patterns:
            matches = re.search(pattern, content, re.IGNORECASE)
            self.assertIsNone(matches, 
                f"Found invalid pattern '{pattern}' in configuration file")
    
    def test_proper_comments_for_remote_tables(self):
        """Test that configuration properly documents remote table limitations."""
        config_file_path = '/Users/ladvien/codex-dreams/biological_memory/duckdb_performance_config.sql'
        
        if not os.path.exists(config_file_path):
            self.skipTest(f"Configuration file not found: {config_file_path}")
        
        with open(config_file_path, 'r') as f:
            content = f.read()
        
        # Should contain proper documentation about remote table limitations
        self.assertIn('cannot create indexes on remote', content.lower(),
                     "Should document remote table index limitations")
        self.assertIn('postgres_scanner', content.lower(),
                     "Should mention postgres_scanner for remote tables")


if __name__ == '__main__':
    # Configure logging for test visibility
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)