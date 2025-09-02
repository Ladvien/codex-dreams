#!/usr/bin/env python3
"""
BMP-012: Load Scenario Performance Tests
Additional performance tests for various load scenarios and edge cases
"""

import json
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import duckdb


class LoadScenarioTests(unittest.TestCase):
    """Load scenario performance tests for BMP-012"""

    @classmethod
    def setUpClass(cls):
        """Set up load testing environment"""
        cls.db_path = Path(__file__).parent.parent.parent / "dbs" / "memory.duckdb"
        cls.conn = duckdb.connect(str(cls.db_path))

        # Create larger test dataset for load testing
        cls._create_load_test_data(10000)

        print(f"\n🚀 BMP-012 Load Scenario Tests - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    @classmethod
    def _create_load_test_data(cls, record_count: int):
        """Create larger dataset for load testing"""
        print(f"📊 Creating {record_count:,} test records for load testing...")

        # Clear existing load test data
        cls.conn.execute("DELETE FROM raw_memories WHERE memory_id LIKE 'load_test_%'")

        # Generate larger dataset with varied characteristics
        batch_size = 1000
        for batch_start in range(0, record_count, batch_size):
            batch_data = []
            for i in range(batch_start, min(batch_start + batch_size, record_count)):
                memory_time = datetime.now() - timedelta(
                    days=i % 30, hours=i % 24, minutes=(i * 13) % 60  # Spread across 30 days
                )

                activation = 0.1 + (i % 90) / 100.0  # 0.1 to 1.0
                concepts = [f"load_concept_{i%50}", f"category_{i%20}", f"type_{i%8}"]

                batch_data.append(
                    (
                        f"load_test_{i:06d}",
                        f"Load test memory content for performance analysis record {i} with extended text content to simulate realistic memory sizes",
                        json.dumps(concepts),
                        activation,
                        memory_time.strftime("%Y-%m-%d %H:%M:%S"),
                        memory_time.strftime("%Y-%m-%d %H:%M:%S"),
                        1 + i % 100,  # access_count 1-100
                        0.1 + (i % 90) / 100.0,  # importance_score
                        ["working_memory", "short_term", "long_term"][i % 3],
                        0.1 + (i % 70) / 100.0,  # previous_strength
                    )
                )

            # Insert batch
            cls.conn.executemany(
                """
                INSERT INTO raw_memories 
                (memory_id, content, concepts, activation_strength, created_at, 
                 last_accessed_at, access_count, importance_score, memory_type, previous_strength)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                batch_data,
            )

        print(f"✅ Load test data created: {record_count:,} records")

    def _time_concurrent_queries(self, query: str, thread_count: int = 4) -> float:
        """Time concurrent query execution"""
        results = []
        threads = []

        def run_query():
            conn = duckdb.connect(str(self.db_path))
            start = time.perf_counter()
            conn.execute(query).fetchall()
            end = time.perf_counter()
            conn.close()
            results.append((end - start) * 1000)

        # Start concurrent threads
        for _ in range(thread_count):
            thread = threading.Thread(target=run_query)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        return max(results)  # Return worst-case time

    def test_high_volume_working_memory(self):
        """Test working memory performance with high record volumes"""
        print("\n📈 Testing High Volume Working Memory Performance...")

        query = """
            WITH high_activation AS (
                SELECT memory_id, activation_strength, access_count, created_at
                FROM raw_memories 
                WHERE memory_id LIKE 'load_test_%'
                  AND activation_strength > 0.7
                  AND access_count > 10
                ORDER BY activation_strength DESC, access_count DESC
                LIMIT 50
            )
            SELECT COUNT(*), AVG(activation_strength), MAX(access_count)
            FROM high_activation
        """

        start = time.perf_counter()
        result = self.conn.execute(query).fetchall()
        end = time.perf_counter()

        duration_ms = (end - start) * 1000
        print(f"  📊 High Volume Query: {duration_ms:.2f}ms")
        print(f"  📦 Records Found: {result[0][0] if result else 0}")

        # Should handle high volume efficiently
        self.assertLess(duration_ms, 200, f"High volume query too slow: {duration_ms:.2f}ms")

    def test_concurrent_access_performance(self):
        """Test performance under concurrent access"""
        print("\n🔄 Testing Concurrent Access Performance...")

        query = """
            SELECT memory_type, COUNT(*), AVG(activation_strength)
            FROM raw_memories 
            WHERE memory_id LIKE 'load_test_%'
              AND created_at > CURRENT_TIMESTAMP - INTERVAL '7 DAYS'
            GROUP BY memory_type
            ORDER BY COUNT(*) DESC
        """

        max_duration = self._time_concurrent_queries(query, thread_count=8)
        print(f"  📊 Concurrent Query (8 threads): {max_duration:.2f}ms")

        # Concurrent queries should still perform well
        self.assertLess(max_duration, 500, f"Concurrent access too slow: {max_duration:.2f}ms")

    def test_large_result_set_performance(self):
        """Test performance when returning large result sets"""
        print("\n📋 Testing Large Result Set Performance...")

        query = """
            SELECT 
                memory_id,
                content,
                activation_strength,
                access_count,
                created_at,
                LENGTH(content) as content_length
            FROM raw_memories 
            WHERE memory_id LIKE 'load_test_%'
              AND activation_strength > 0.3
            ORDER BY activation_strength DESC
            LIMIT 1000
        """

        start = time.perf_counter()
        result = self.conn.execute(query).fetchall()
        end = time.perf_counter()

        duration_ms = (end - start) * 1000
        result_count = len(result)

        print(f"  📊 Large Result Set: {duration_ms:.2f}ms")
        print(f"  📦 Records Retrieved: {result_count:,}")

        # Large result sets should be retrieved efficiently
        self.assertLess(duration_ms, 300, f"Large result set query too slow: {duration_ms:.2f}ms")
        self.assertGreater(result_count, 500, "Insufficient results returned")

    def test_complex_aggregation_performance(self):
        """Test performance of complex aggregations"""
        print("\n🧮 Testing Complex Aggregation Performance...")

        query = """
            WITH daily_stats AS (
                SELECT 
                    DATE(created_at) as memory_date,
                    memory_type,
                    COUNT(*) as daily_count,
                    AVG(activation_strength) as avg_activation,
                    MAX(activation_strength) as max_activation,
                    SUM(access_count) as total_accesses
                FROM raw_memories
                WHERE memory_id LIKE 'load_test_%'
                GROUP BY DATE(created_at), memory_type
            ),
            summary_stats AS (
                SELECT 
                    memory_type,
                    COUNT(*) as type_count,
                    AVG(daily_count) as avg_daily_count,
                    AVG(avg_activation) as overall_avg_activation,
                    SUM(total_accesses) as type_total_accesses
                FROM daily_stats
                GROUP BY memory_type
            )
            SELECT 
                memory_type,
                type_count,
                ROUND(avg_daily_count, 2) as avg_daily,
                ROUND(overall_avg_activation, 3) as avg_activation,
                type_total_accesses
            FROM summary_stats
            ORDER BY type_total_accesses DESC
        """

        start = time.perf_counter()
        result = self.conn.execute(query).fetchall()
        end = time.perf_counter()

        duration_ms = (end - start) * 1000
        print(f"  📊 Complex Aggregation: {duration_ms:.2f}ms")
        print(f"  📈 Result Groups: {len(result)}")

        # Complex aggregations should complete efficiently
        self.assertLess(duration_ms, 400, f"Complex aggregation too slow: {duration_ms:.2f}ms")

    def test_temporal_range_queries(self):
        """Test performance of temporal range queries"""
        print("\n📅 Testing Temporal Range Query Performance...")

        query = """
            SELECT 
                DATE_TRUNC('week', created_at) as week_start,
                COUNT(*) as weekly_count,
                AVG(activation_strength) as avg_strength
            FROM raw_memories
            WHERE memory_id LIKE 'load_test_%'
              AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 DAYS'
              AND activation_strength > 0.5
            GROUP BY DATE_TRUNC('week', created_at)
            ORDER BY week_start DESC
            LIMIT 10
        """

        start = time.perf_counter()
        result = self.conn.execute(query).fetchall()
        end = time.perf_counter()

        duration_ms = (end - start) * 1000
        print(f"  📊 Temporal Range Query: {duration_ms:.2f}ms")
        print(f"  🗓️  Weekly Groups: {len(result)}")

        # Temporal queries should be fast with proper indexing
        self.assertLess(duration_ms, 150, f"Temporal range query too slow: {duration_ms:.2f}ms")

    def test_memory_usage_under_load(self):
        """Test memory usage during load scenarios"""
        print("\n💾 Testing Memory Usage Under Load...")

        # Multiple queries to simulate load
        queries = [
            "SELECT COUNT(*) FROM raw_memories WHERE memory_id LIKE 'load_test_%' AND activation_strength > 0.8",
            "SELECT memory_type, AVG(access_count) FROM raw_memories WHERE memory_id LIKE 'load_test_%' GROUP BY memory_type",
            "SELECT * FROM raw_memories WHERE memory_id LIKE 'load_test_%' ORDER BY created_at DESC LIMIT 100",
        ]

        total_start = time.perf_counter()

        for i, query in enumerate(queries):
            start = time.perf_counter()
            self.conn.execute(query).fetchall()
            end = time.perf_counter()
            print(f"  📊 Query {i+1}: {(end-start)*1000:.2f}ms")

        total_end = time.perf_counter()
        total_duration = (total_end - total_start) * 1000

        print(f"  ⏱️  Total Load Test Duration: {total_duration:.2f}ms")

        # Total load should be manageable
        self.assertLess(
            total_duration, 1000, f"Load test duration too high: {total_duration:.2f}ms"
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up load test data"""
        print(f"\n📊 Load Scenario Test Results")
        print(f"=" * 50)

        # Clean up test data
        deleted_count = cls.conn.execute(
            "DELETE FROM raw_memories WHERE memory_id LIKE 'load_test_%'"
        ).fetchone()
        print(f"🧹 Cleaned up load test data")

        cls.conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
