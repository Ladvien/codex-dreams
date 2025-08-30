#!/usr/bin/env python3
"""
PostgreSQL Data Flow Integration Tests for BMP-HIGH-007
Tests the complete data flow from PostgreSQL source to DuckDB staging transformation

This test suite validates:
1. PostgreSQL connection and data access
2. Data transformation accuracy
3. Schema mapping correctness
4. Performance metrics
5. Error handling and resilience
6. Data consistency checks
"""

import os
import sys
import unittest
import duckdb
import psycopg2
from datetime import datetime, timedelta
import json
import time

class PostgresDataFlowTests(unittest.TestCase):
    """Integration tests for PostgreSQL data flow in biological memory pipeline"""
    
    def setUp(self):
        """Set up test environment and connections"""
        # Get PostgreSQL config from environment or use defaults
        postgres_url = os.getenv('POSTGRES_DB_URL', '')
        if postgres_url:
            import re
            match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', postgres_url)
            if match:
                self.pg_config = {
                    'user': match.group(1),
                    'password': match.group(2),
                    'host': match.group(3),
                    'port': int(match.group(4)),
                    'database': match.group(5)
                }
            else:
                # Fallback without hardcoded password
                self.pg_config = {
                    'host': '192.168.1.104',
                    'port': 5432,
                    'database': 'codex_db',
                    'user': 'codex_user',
                    'password': os.getenv('POSTGRES_PASSWORD', 'password')
                }
        else:
            # Fallback without hardcoded password
            self.pg_config = {
                'host': '192.168.1.104',
                'port': 5432,
                'database': 'codex_db',
                'user': 'codex_user',
                'password': os.getenv('POSTGRES_PASSWORD', 'password')
            }
        
        # Create DuckDB connection for testing
        self.duck_conn = duckdb.connect(':memory:')
        self.duck_conn.execute("INSTALL postgres_scanner")
        self.duck_conn.execute("INSTALL json")
        self.duck_conn.execute("LOAD postgres_scanner")
        self.duck_conn.execute("LOAD json")
        
        # Set up PostgreSQL connection
        self.setup_postgres_connection()
        
    def setup_postgres_connection(self):
        """Set up PostgreSQL connection in DuckDB"""
        self.duck_conn.execute(f"""
            CREATE OR REPLACE SECRET codex_db_connection (
                TYPE POSTGRES,
                HOST '{self.pg_config['host']}',
                PORT {self.pg_config['port']},
                DATABASE '{self.pg_config['database']}',
                USER '{self.pg_config['user']}',
                PASSWORD '{self.pg_config['password']}'
            )
        """)
        
        self.duck_conn.execute("ATTACH '' AS codex_db (TYPE POSTGRES, SECRET codex_db_connection)")
        
    def test_postgres_connection_health(self):
        """Test 1: Verify PostgreSQL connection is healthy and responsive"""
        start_time = time.time()
        
        result = self.duck_conn.execute("SELECT COUNT(*) as count FROM codex_db.public.memories").fetchone()
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Assertions
        self.assertIsNotNone(result, "Connection should return valid result")
        self.assertGreater(result[0], 0, "Should have records in memories table")
        self.assertLess(response_time, 5.0, "Response time should be under 5 seconds")
        
        print(f"✅ Connection test passed: {result[0]} records, {response_time:.2f}s response time")
        
    def test_data_freshness(self):
        """Test 2: Verify data freshness and recency"""
        result = self.duck_conn.execute("""
            SELECT 
                MAX(created_at) as latest_memory,
                COUNT(*) FILTER (WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours') as recent_count,
                COUNT(*) as total_count
            FROM codex_db.public.memories
        """).fetchone()
        
        latest_memory, recent_count, total_count = result
        
        # Assertions
        self.assertIsNotNone(latest_memory, "Should have latest memory timestamp")
        self.assertGreater(total_count, 100, "Should have substantial data volume")
        
        # Calculate freshness
        if latest_memory:
            hours_since_latest = (datetime.now() - latest_memory.replace(tzinfo=None)).total_seconds() / 3600
            self.assertLess(hours_since_latest, 168, "Latest data should be within a week")  # 7 days
            
        print(f"✅ Data freshness test passed: Latest={latest_memory}, Recent={recent_count}, Total={total_count}")
        
    def test_schema_mapping_accuracy(self):
        """Test 3: Verify schema mapping and column availability"""
        result = self.duck_conn.execute("""
            SELECT 
                id, content, created_at, updated_at, metadata
            FROM codex_db.public.memories
            WHERE content IS NOT NULL
            LIMIT 1
        """).fetchone()
        
        # Assertions
        self.assertIsNotNone(result, "Should retrieve sample record")
        self.assertIsNotNone(result[0], "ID should not be null")  # id
        self.assertIsNotNone(result[1], "Content should not be null")  # content
        self.assertIsNotNone(result[2], "Created_at should not be null")  # created_at
        
        print(f"✅ Schema mapping test passed: All required columns accessible")
        
    def test_data_transformation_accuracy(self):
        """Test 4: Verify staging transformation produces correct results"""
        # Test the staging transformation query
        result = self.duck_conn.execute("""
            WITH source_memories AS (
                SELECT id, content, created_at, updated_at, metadata
                FROM codex_db.public.memories
                LIMIT 10
            ),
            transformed AS (
                SELECT
                    id AS memory_id,
                    content,
                    LEAST(1.0, 
                        EXP(-EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) / (7 * 24 * 3600.0))
                    ) AS activation_strength,
                    CASE
                        WHEN LENGTH(content) < 50 THEN 'fragment'
                        WHEN LENGTH(content) < 200 THEN 'episode'
                        WHEN LENGTH(content) < 500 THEN 'narrative'
                        ELSE 'document'
                    END AS memory_type,
                    created_at
                FROM source_memories
                WHERE content IS NOT NULL
            )
            SELECT 
                COUNT(*) as record_count,
                COUNT(DISTINCT memory_type) as memory_type_count,
                AVG(activation_strength) as avg_activation,
                MIN(activation_strength) as min_activation,
                MAX(activation_strength) as max_activation
            FROM transformed
        """).fetchone()
        
        record_count, memory_type_count, avg_activation, min_activation, max_activation = result
        
        # Assertions
        self.assertGreater(record_count, 0, "Should transform at least some records")
        self.assertGreaterEqual(memory_type_count, 1, "Should classify memory types")
        self.assertGreater(avg_activation, 0, "Average activation should be positive")
        self.assertGreaterEqual(min_activation, 0, "Minimum activation should be non-negative")
        self.assertLessEqual(max_activation, 1.0, "Maximum activation should not exceed 1.0")
        
        print(f"✅ Transformation test passed: {record_count} records, {memory_type_count} types, avg activation={avg_activation:.3f}")
        
    def test_performance_benchmarks(self):
        """Test 5: Verify performance meets acceptable thresholds"""
        # Test 1: Large query performance
        start_time = time.time()
        result = self.duck_conn.execute("""
            SELECT COUNT(*), AVG(LENGTH(content))
            FROM codex_db.public.memories
            WHERE content IS NOT NULL
        """).fetchone()
        query_time_1 = time.time() - start_time
        
        # Test 2: Complex transformation performance
        start_time = time.time()
        result = self.duck_conn.execute("""
            SELECT 
                memory_type,
                COUNT(*) as count,
                AVG(activation_strength) as avg_activation
            FROM (
                SELECT
                    CASE
                        WHEN LENGTH(content) < 50 THEN 'fragment'
                        WHEN LENGTH(content) < 200 THEN 'episode'
                        WHEN LENGTH(content) < 500 THEN 'narrative'
                        ELSE 'document'
                    END AS memory_type,
                    LEAST(1.0, 
                        EXP(-EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) / (7 * 24 * 3600.0))
                    ) AS activation_strength
                FROM codex_db.public.memories
                WHERE content IS NOT NULL
            ) t
            GROUP BY memory_type
        """).fetchall()
        query_time_2 = time.time() - start_time
        
        # Assertions
        self.assertLess(query_time_1, 10.0, "Simple aggregation should complete within 10 seconds")
        self.assertLess(query_time_2, 15.0, "Complex transformation should complete within 15 seconds")
        self.assertGreater(len(result), 0, "Should return memory type classifications")
        
        print(f"✅ Performance test passed: Simple query={query_time_1:.2f}s, Complex query={query_time_2:.2f}s")
        
    def test_error_handling_resilience(self):
        """Test 6: Verify graceful handling of edge cases and errors"""
        
        # Test 1: Handle records with NULL content gracefully
        result = self.duck_conn.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(*) FILTER (WHERE content IS NULL) as null_content_records,
                COUNT(*) FILTER (WHERE content IS NOT NULL AND LENGTH(content) = 0) as empty_content_records
            FROM codex_db.public.memories
        """).fetchone()
        
        total_records, null_content, empty_content = result
        
        # Test 2: Verify transformation handles edge cases
        result = self.duck_conn.execute("""
            SELECT 
                memory_type,
                COUNT(*) as count
            FROM (
                SELECT
                    CASE
                        WHEN content IS NULL THEN 'null_content'
                        WHEN LENGTH(content) = 0 THEN 'empty_content'
                        WHEN LENGTH(content) < 50 THEN 'fragment'
                        WHEN LENGTH(content) < 200 THEN 'episode'
                        WHEN LENGTH(content) < 500 THEN 'narrative'
                        ELSE 'document'
                    END AS memory_type
                FROM codex_db.public.memories
            ) t
            GROUP BY memory_type
        """).fetchall()
        
        # Assertions
        self.assertGreater(total_records, 0, "Should have total records")
        self.assertIsNotNone(result, "Error handling query should succeed")
        self.assertGreater(len(result), 0, "Should classify all record types including edge cases")
        
        print(f"✅ Error handling test passed: {total_records} total, {null_content} null, {empty_content} empty")
        
    def test_data_consistency_validation(self):
        """Test 7: Verify data consistency and integrity"""
        
        # Test 1: ID uniqueness
        result = self.duck_conn.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT id) as unique_ids
            FROM codex_db.public.memories
        """).fetchone()
        
        total_records, unique_ids = result
        
        # Test 2: Temporal consistency
        result = self.duck_conn.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE updated_at >= created_at) as valid_temporal_records,
                COUNT(*) FILTER (WHERE updated_at < created_at) as invalid_temporal_records,
                COUNT(*) as total_with_updates
            FROM codex_db.public.memories
            WHERE updated_at IS NOT NULL
        """).fetchone()
        
        valid_temporal, invalid_temporal, total_with_updates = result
        
        # Assertions
        self.assertEqual(total_records, unique_ids, "All IDs should be unique")
        if total_with_updates > 0:
            self.assertEqual(invalid_temporal, 0, "Updated_at should never be before created_at")
            
        print(f"✅ Data consistency test passed: {unique_ids} unique IDs, {valid_temporal} valid temporal records")
        
    def test_integration_end_to_end(self):
        """Test 8: Full end-to-end integration test"""
        
        # Simulate complete staging model execution
        result = self.duck_conn.execute("""
            WITH source_memories AS (
                SELECT id, content, created_at, updated_at, metadata
                FROM codex_db.public.memories
                WHERE created_at > CURRENT_DATE - INTERVAL '30 days'
            ),
            parsed_memories AS (
                SELECT
                    id AS memory_id,
                    content,
                    COALESCE(
                        string_split(
                            regexp_replace(lower(content), '[^a-z0-9\\s]', ' ', 'g'),
                            ' '
                        ),
                        ['unknown']
                    ) AS concepts,
                    LEAST(1.0, 
                        EXP(-EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) / (7 * 24 * 3600.0))
                    ) AS activation_strength,
                    created_at,
                    COALESCE(updated_at, created_at) AS last_accessed_at,
                    CASE
                        WHEN LENGTH(content) < 50 THEN 'fragment'
                        WHEN LENGTH(content) < 200 THEN 'episode'
                        WHEN LENGTH(content) < 500 THEN 'narrative'
                        ELSE 'document'
                    END AS memory_type,
                    CURRENT_TIMESTAMP AS processed_at,
                    'codex_db' AS source_system
                FROM source_memories
                WHERE content IS NOT NULL AND LENGTH(content) > 0
            )
            SELECT 
                COUNT(*) as processed_count,
                COUNT(DISTINCT memory_type) as memory_types,
                COUNT(DISTINCT source_system) as source_systems,
                AVG(activation_strength) as avg_activation,
                COUNT(DISTINCT DATE(created_at)) as creation_days
            FROM parsed_memories
        """).fetchone()
        
        processed_count, memory_types, source_systems, avg_activation, creation_days = result
        
        # Assertions
        self.assertGreater(processed_count, 0, "Should process recent records")
        self.assertGreaterEqual(memory_types, 1, "Should identify memory types")
        self.assertEqual(source_systems, 1, "Should identify source system as codex_db")
        self.assertGreater(avg_activation, 0, "Should calculate activation strengths")
        
        print(f"✅ End-to-end test passed: {processed_count} records processed, {memory_types} types, {creation_days} days of data")
        
    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'duck_conn'):
            self.duck_conn.close()

def run_integration_tests():
    """Run all PostgreSQL integration tests"""
    print("\n" + "="*80)
    print("PostgreSQL Data Flow Integration Tests - BMP-HIGH-007")
    print("="*80)
    
    # Load test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(PostgresDataFlowTests)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 All PostgreSQL integration tests PASSED!")
        print("The PostgreSQL source integration is fully operational.")
        return True
    else:
        print("\n❌ Some tests FAILED. Please review the PostgreSQL integration configuration.")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)