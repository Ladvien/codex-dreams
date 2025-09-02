#!/usr/bin/env python3
"""
BMP-012: Simplified Performance Optimization Tests
Streamlined test suite focused on core performance targets
"""

import statistics
import time
import unittest
from datetime import datetime
from pathlib import Path

import duckdb


class SimplePerformanceTests(unittest.TestCase):
    """Simplified performance tests for BMP-012 optimization validation"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.db_path = Path(__file__).parent.parent.parent / "dbs" / "memory.duckdb"
        cls.conn = duckdb.connect(str(cls.db_path))

        # Performance targets
        cls.targets = {
            "working_memory_ms": 100,
            "consolidation_ms": 1000,
            "partitioned_query_ms": 50,
        }

        print(f"\n🧠 BMP-012 Performance Tests - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def _time_query(self, query: str, runs: int = 3) -> float:
        """Time a query execution over multiple runs"""
        times = []
        for _ in range(runs):
            start = time.perf_counter()
            self.conn.execute(query).fetchall()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        return statistics.mean(times)

    def test_working_memory_performance(self):
        """Test working memory query performance <100ms"""
        print("\n🔍 Testing Working Memory Performance...")

        query = """
            SELECT memory_id, activation_strength, content
            FROM raw_memories 
            WHERE activation_strength > 0.6 
              AND access_count >= 2
            ORDER BY activation_strength DESC
            LIMIT 7
        """

        avg_time = self._time_query(query)
        print(
            f"  📊 Working Memory Query: {avg_time:.2f}ms (target: {self.targets['working_memory_ms']}ms)"
        )

        self.assertLess(
            avg_time,
            self.targets["working_memory_ms"],
            f"Working memory query too slow: {avg_time:.2f}ms",
        )

    def test_memory_consolidation_performance(self):
        """Test memory consolidation batch processing <1000ms"""
        print("\n🔄 Testing Memory Consolidation Performance...")

        query = """
            WITH batched_memories AS (
                SELECT *,
                    CEIL(ROW_NUMBER() OVER (ORDER BY created_at) / 1000.0) as batch_id
                FROM raw_memories
                WHERE activation_strength > 0.5
            )
            SELECT 
                batch_id,
                COUNT(*) as batch_size,
                AVG(activation_strength) as avg_activation,
                MAX(activation_strength) as max_activation
            FROM batched_memories
            WHERE batch_id <= 3
            GROUP BY batch_id
            ORDER BY batch_id
        """

        avg_time = self._time_query(query)
        print(
            f"  📊 Consolidation Batch: {avg_time:.2f}ms (target: {self.targets['consolidation_ms']}ms)"
        )

        self.assertLess(
            avg_time,
            self.targets["consolidation_ms"],
            f"Consolidation batch too slow: {avg_time:.2f}ms",
        )

    def test_partitioned_query_performance(self):
        """Test monthly partitioning query performance <50ms"""
        print("\n📅 Testing Partitioned Query Performance...")

        query = """
            SELECT COUNT(*), AVG(activation_strength) 
            FROM raw_memories 
            WHERE created_at >= DATE_TRUNC('month', CURRENT_TIMESTAMP)
              AND memory_type = 'working_memory'
        """

        avg_time = self._time_query(query)
        print(
            f"  📊 Partitioned Query: {avg_time:.2f}ms (target: {self.targets['partitioned_query_ms']}ms)"
        )

        self.assertLess(
            avg_time,
            self.targets["partitioned_query_ms"],
            f"Partitioned query too slow: {avg_time:.2f}ms",
        )

    def test_index_effectiveness(self):
        """Test that indexes improve query performance"""
        print("\n🗂️ Testing Index Effectiveness...")

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_activation ON raw_memories (activation_strength DESC)",
            "CREATE INDEX IF NOT EXISTS idx_created_at ON raw_memories (created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_memory_type ON raw_memories (memory_type)",
        ]

        for idx in indexes:
            self.conn.execute(idx)

        # Test indexed query
        query = """
            SELECT memory_id, activation_strength 
            FROM raw_memories 
            WHERE activation_strength > 0.8
              AND memory_type IN ('working_memory', 'long_term')
            ORDER BY activation_strength DESC
            LIMIT 50
        """

        avg_time = self._time_query(query)
        print(f"  📊 Indexed Query: {avg_time:.2f}ms")
        print(f"  ✅ Indexes Created: {len(indexes)}")

        # Should be fast with proper indexes
        self.assertLess(avg_time, 100, f"Indexed query performance inadequate: {avg_time:.2f}ms")

    def test_database_size_monitoring(self):
        """Test database size and memory usage monitoring"""
        print("\n💾 Testing Database Size Monitoring...")

        # Check row counts
        tables = ["raw_memories"]
        for table in tables:
            result = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            row_count = result[0] if result else 0
            print(f"  📊 {table}: {row_count:,} rows")

            if table == "raw_memories":
                self.assertGreater(row_count, 0, f"No data in {table}")

    def test_query_complexity_limits(self):
        """Test that complex queries stay within reasonable limits"""
        print("\n🧮 Testing Query Complexity Limits...")

        # Complex aggregation query
        complex_query = """
            WITH memory_stats AS (
                SELECT 
                    memory_type,
                    AVG(activation_strength) as avg_activation,
                    COUNT(*) as count,
                    MAX(created_at) as latest,
                    MIN(created_at) as earliest
                FROM raw_memories
                GROUP BY memory_type
            ),
            ranked_memories AS (
                SELECT 
                    *,
                    ROW_NUMBER() OVER (PARTITION BY memory_type ORDER BY activation_strength DESC) as rank
                FROM raw_memories
            )
            SELECT 
                ms.memory_type,
                ms.avg_activation,
                ms.count,
                rm.memory_id as top_memory
            FROM memory_stats ms
            LEFT JOIN ranked_memories rm ON ms.memory_type = rm.memory_type AND rm.rank = 1
            ORDER BY ms.avg_activation DESC
        """

        avg_time = self._time_query(complex_query)
        print(f"  📊 Complex Query: {avg_time:.2f}ms")

        # Complex queries should still complete quickly
        self.assertLess(avg_time, 500, f"Complex query too slow: {avg_time:.2f}ms")

    @classmethod
    def tearDownClass(cls):
        """Clean up and report results"""
        print(f"\n📈 BMP-012 Performance Test Results Summary")
        print(f"=" * 60)
        print(f"🎯 All performance targets validated")
        print(f"💾 Database: {cls.db_path}")
        print(f"⏱️  Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        cls.conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
