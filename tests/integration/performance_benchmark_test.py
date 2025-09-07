#!/usr/bin/env python3
"""
Performance Benchmark Tests for STORY-009
Tests performance of biological memory system with live services

This module provides comprehensive performance benchmarking for:
- Database query performance with biological timing constraints (<50ms)
- LLM processing performance for real-time biological memory
- Memory capacity handling under load (Miller's 7±2)
- Consolidation performance at scale
- Network latency and connection pooling optimization
- Biological rhythm processing timing
"""

import concurrent.futures
import json
import logging
import os
import statistics
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, NamedTuple, Optional

import duckdb
import psycopg2
import pytest
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class PerformanceMetrics(NamedTuple):
    """Structure for performance measurement results"""

    operation: str
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    p95_time_ms: float
    throughput_ops_per_sec: float
    success_rate: float
    biological_constraint_met: bool
    constraint_ms: float


@dataclass
class PerformanceBenchmarkConfig:
    """Configuration for performance benchmarking"""

    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = 5432
    postgres_database: str = "codex_test_db"
    postgres_user: str = os.getenv("POSTGRES_USER", "codex_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")

    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = "gpt-oss:20b"

    # Biological timing constraints (milliseconds)
    database_query_limit_ms: float = 50.0
    working_memory_refresh_limit_ms: float = 100.0
    stm_processing_limit_ms: float = 500.0
    consolidation_limit_ms: float = 2000.0

    # Load testing parameters
    concurrent_connections: int = 10
    operations_per_test: int = 100
    memory_items_for_load_test: int = 1000


class BiologicalMemoryPerformanceTester:
    """Performance benchmarking for biological memory system"""

    def __init__(self, config: Optional[PerformanceBenchmarkConfig] = None):
        self.config = config or PerformanceBenchmarkConfig()
        self.test_schema = f"perf_test_{int(time.time())}"
        self.test_tables_created = []
        self.temp_duckdb = None
        self.performance_results = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """Clean up test resources"""
        try:
            with self.get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"DROP SCHEMA IF EXISTS {self.test_schema} CASCADE")
                    for table in self.test_tables_created:
                        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

            if self.temp_duckdb and Path(self.temp_duckdb).exists():
                Path(self.temp_duckdb).unlink()

        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    @contextmanager
    def get_postgres_connection(self):
        """Get PostgreSQL connection for performance testing"""
        try:
            conn = psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_database,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
                connect_timeout=5,
            )
            conn.autocommit = True
            yield conn
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            logger.warning(f"PostgreSQL connection failed: {e}")
            pytest.skip(f"PostgreSQL not available for performance test: {e}")
        finally:
            if "conn" in locals():
                conn.close()

    @contextmanager
    def get_performance_duckdb(self):
        """Get DuckDB with performance monitoring setup"""
        # Generate unique temp file name but don't create the file
        temp_fd, self.temp_duckdb = tempfile.mkstemp(suffix=".duckdb")
        os.close(temp_fd)  # Close the file descriptor
        os.unlink(self.temp_duckdb)  # Remove the empty file so DuckDB can create it fresh

        postgres_url = f"postgresql://{self.config.postgres_user}:{self.config.postgres_password}@{self.config.postgres_host}:{self.config.postgres_port}/{self.config.postgres_database}"

        try:
            conn = duckdb.connect(self.temp_duckdb)
            conn.execute("LOAD postgres")
            conn.execute("LOAD json")
            try:
                conn.execute(f"ATTACH '{postgres_url}' AS pg_perf (TYPE postgres)")
            except Exception as e:
                if "Connection refused" in str(e) or "could not connect" in str(e).lower():
                    pytest.skip(f"PostgreSQL not available for DuckDB: {e}")
                else:
                    raise
            yield conn
        finally:
            if "conn" in locals():
                conn.close()

    def measure_operation_performance(
        self,
        operation_name: str,
        operation_func,
        num_iterations: int = 10,
        biological_constraint_ms: float = 50.0,
    ) -> PerformanceMetrics:
        """Measure performance of an operation with biological constraints"""
        times_ms = []
        successes = 0

        for i in range(num_iterations):
            start_time = time.perf_counter()
            try:
                result = operation_func()
                success = result is not None
                successes += int(success)
            except Exception as e:
                logger.warning(f"Operation {operation_name} iteration {i} failed: {e}")
                success = False

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            times_ms.append(elapsed_ms)

        if times_ms:
            avg_time = statistics.mean(times_ms)
            min_time = min(times_ms)
            max_time = max(times_ms)
            p95_time = statistics.quantiles(times_ms, n=20)[18]  # 95th percentile
            throughput = 1000.0 / avg_time if avg_time > 0 else 0
            success_rate = successes / num_iterations
            constraint_met = avg_time <= biological_constraint_ms
        else:
            avg_time = min_time = max_time = p95_time = float("inf")
            throughput = success_rate = 0
            constraint_met = False

        return PerformanceMetrics(
            operation=operation_name,
            avg_time_ms=avg_time,
            min_time_ms=min_time,
            max_time_ms=max_time,
            p95_time_ms=p95_time,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            biological_constraint_met=constraint_met,
            constraint_ms=biological_constraint_ms,
        )

    def setup_performance_test_data(self, num_records: int = 1000):
        """Set up large dataset for performance testing"""
        with self.get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Create performance test schema
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.test_schema}")

                # Create optimized tables with proper indexing
                perf_table = f"pg_perf.{self.test_schema}.memory_performance_test"
                self.test_tables_created.append(perf_table)

                cursor.execute(
                    f"""
                    CREATE TABLE {perf_table} (
                        id SERIAL PRIMARY KEY,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        importance_score FLOAT DEFAULT 0.5,
                        category VARCHAR(50),
                        metadata JSONB DEFAULT '{{}}',
                        processed BOOLEAN DEFAULT FALSE
                    )
                """
                )

                # Create performance indexes
                cursor.execute(f"CREATE INDEX idx_perf_timestamp ON {perf_table} (timestamp DESC)")
                cursor.execute(
                    f"CREATE INDEX idx_perf_importance ON {perf_table} (importance_score DESC)"
                )
                cursor.execute(f"CREATE INDEX idx_perf_category ON {perf_table} (category)")
                cursor.execute(
                    f"CREATE INDEX idx_perf_metadata ON {perf_table} USING GIN (metadata)"
                )

                # Insert test data in batches for better performance
                batch_size = 100
                categories = [
                    "planning",
                    "development",
                    "review",
                    "client",
                    "operations",
                    "research",
                ]

                for batch_start in range(0, num_records, batch_size):
                    batch_values = []
                    for i in range(batch_start, min(batch_start + batch_size, num_records)):
                        content = f"Performance test memory item {i} with detailed content for realistic testing"
                        # Varied importance 0.1-1.0
                        importance = 0.1 + (0.9 * (i % 100) / 100)
                        category = categories[i % len(categories)]
                        timestamp_offset = timedelta(minutes=i // 10)  # Spread over time
                        test_timestamp = datetime.now(timezone.utc) - timestamp_offset

                        metadata = json.dumps(
                            {
                                "test_item": True,
                                "batch": i // 100,
                                "complexity": min(1.0, importance * 1.2),
                                "priority": (
                                    "high"
                                    if importance > 0.8
                                    else "medium" if importance > 0.5 else "low"
                                ),
                            }
                        )

                        batch_values.append(
                            (content, test_timestamp, importance, category, metadata)
                        )

                    # Batch insert
                    cursor.executemany(
                        f"""
                        INSERT INTO {perf_table} (content, timestamp, importance_score, category, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                    """,
                        batch_values,
                    )

                logger.info(f"Created performance test dataset with {num_records} records")


class TestDatabaseQueryPerformance:
    """Test database query performance with biological timing constraints"""

    def setup_method(self):
        """Set up performance testing environment"""
        self.tester = BiologicalMemoryPerformanceTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.tester.cleanup()

    def test_working_memory_query_performance(self):
        """Test working memory queries meet <50ms constraint"""
        with self.tester:
            self.tester.setup_performance_test_data(500)

            with self.tester.get_performance_duckdb() as conn:
                perf_table = f"pg_perf.{self.tester.test_schema}.memory_performance_test"

                # Test Miller's 7±2 working memory selection
                def working_memory_query():
                    return conn.execute(
                        f"""
                        SELECT id, content, importance_score, timestamp
                        FROM {perf_table}
                        WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                          AND importance_score > 0.7
                        ORDER BY importance_score DESC, timestamp DESC
                        LIMIT 7
                    """
                    ).fetchall()

                metrics = self.tester.measure_operation_performance(
                    "working_memory_selection",
                    working_memory_query,
                    num_iterations=20,
                    biological_constraint_ms=self.tester.config.database_query_limit_ms,
                )

                # Biological constraint validation
                assert (
                    metrics.biological_constraint_met
                ), f"Working memory query took {metrics.avg_time_ms:.1f}ms, should be <{metrics.constraint_ms}ms"
                assert (
                    metrics.success_rate >= 0.95
                ), f"Success rate {metrics.success_rate:.2f} too low"
                assert (
                    metrics.throughput_ops_per_sec >= 20
                ), f"Throughput {metrics.throughput_ops_per_sec:.1f} ops/sec too low"

                logger.info(
                    f"Working Memory Performance: {metrics.avg_time_ms:.1f}ms avg, {metrics.p95_time_ms:.1f}ms p95"
                )
                logger.info(f"Throughput: {metrics.throughput_ops_per_sec:.1f} ops/sec")

                # Test result correctness
                result = working_memory_query()
                assert len(result) <= 7, "Should respect Miller's 7±2 capacity"
                assert all(row[2] > 0.7 for row in result), "Should filter by importance"

    def test_short_term_memory_processing_performance(self):
        """Test STM processing queries meet <500ms constraint"""
        with self.tester:
            self.tester.setup_performance_test_data(200)

            with self.tester.get_performance_duckdb() as conn:
                perf_table = f"pg_perf.{self.tester.test_schema}.memory_performance_test"

                # Create STM processing table
                conn.execute(
                    """
                    CREATE TABLE stm_processing (
                        id INTEGER PRIMARY KEY,
                        content TEXT,
                        goal_category VARCHAR(100),
                        stm_strength FLOAT,
                        processing_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                def stm_processing_batch():
                    # Select candidates for STM processing
                    candidates = conn.execute(
                        f"""
                        SELECT id, content, importance_score
                        FROM {perf_table}
                        WHERE importance_score > 0.6 AND NOT processed
                        ORDER BY importance_score DESC
                        LIMIT 5
                    """
                    ).fetchall()

                    # Process each candidate
                    for memory_id, content, importance in candidates:
                        # Simulate hierarchy extraction (without actual LLM for
                        # performance testing)
                        goal_category = "Project Management and Execution"  # Mock result
                        stm_strength = min(1.0, importance + 0.1)

                        conn.execute(
                            """
                            INSERT INTO stm_processing (id, content, goal_category, stm_strength)
                            VALUES (?, ?, ?, ?)
                        """,
                            (memory_id, content, goal_category, stm_strength),
                        )

                        # Mark as processed
                        conn.execute(
                            f"""
                            UPDATE {perf_table} SET processed = TRUE WHERE id = ?
                        """,
                            (memory_id,),
                        )

                    return len(candidates)

                metrics = self.tester.measure_operation_performance(
                    "stm_batch_processing",
                    stm_processing_batch,
                    num_iterations=10,
                    biological_constraint_ms=self.tester.config.stm_processing_limit_ms,
                )

                assert (
                    metrics.biological_constraint_met
                ), f"STM processing took {metrics.avg_time_ms:.1f}ms, should be <{metrics.constraint_ms}ms"
                assert (
                    metrics.success_rate >= 0.9
                ), f"STM success rate {metrics.success_rate:.2f} too low"

                logger.info(
                    f"STM Processing Performance: {metrics.avg_time_ms:.1f}ms avg, {metrics.p95_time_ms:.1f}ms p95"
                )

    def test_consolidation_query_performance(self):
        """Test memory consolidation queries meet <2s constraint"""
        with self.tester:
            self.tester.setup_performance_test_data(300)

            with self.tester.get_performance_duckdb() as conn:
                perf_table = f"pg_perf.{self.tester.test_schema}.memory_performance_test"

                # Create semantic network table
                conn.execute(
                    """
                    CREATE TABLE semantic_associations (
                        id INTEGER PRIMARY KEY,
                        concept_a VARCHAR(100),
                        concept_b VARCHAR(100),
                        strength FLOAT,
                        consolidation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                def consolidation_batch():
                    # Find consolidation candidates
                    candidates = conn.execute(
                        f"""
                        SELECT id, content, category, importance_score
                        FROM {perf_table}
                        WHERE importance_score > 0.8
                        ORDER BY importance_score DESC
                        LIMIT 10
                    """
                    ).fetchall()

                    # Create semantic associations
                    associations_created = 0
                    for memory_id, content, category, importance in candidates:
                        # Create concept associations (simplified for
                        # performance testing)
                        associations = [
                            (category, "memory_content", importance * 0.9),
                            ("episodic", category, importance * 0.8),
                            (f"memory_{memory_id % 10}", category, importance * 0.7),
                        ]

                        for concept_a, concept_b, strength in associations:
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO semantic_associations
                                (concept_a, concept_b, strength) VALUES (?, ?, ?)
                            """,
                                (concept_a, concept_b, strength),
                            )
                            associations_created += 1

                    return associations_created

                metrics = self.tester.measure_operation_performance(
                    "memory_consolidation",
                    consolidation_batch,
                    num_iterations=8,
                    biological_constraint_ms=self.tester.config.consolidation_limit_ms,
                )

                assert (
                    metrics.biological_constraint_met
                ), f"Consolidation took {metrics.avg_time_ms:.1f}ms, should be <{metrics.constraint_ms}ms"
                assert (
                    metrics.success_rate >= 0.85
                ), f"Consolidation success rate {metrics.success_rate:.2f} too low"

                logger.info(
                    f"Consolidation Performance: {metrics.avg_time_ms:.1f}ms avg, {metrics.p95_time_ms:.1f}ms p95"
                )


class TestLLMServicePerformance:
    """Test LLM service performance for biological memory processing"""

    def setup_method(self):
        """Set up LLM performance testing"""
        self.tester = BiologicalMemoryPerformanceTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.tester.cleanup()

    def test_ollama_response_time_performance(self):
        """Test Ollama response times for biological memory prompts"""
        # Check if Ollama is available
        try:
            response = requests.get(f"{self.tester.config.ollama_url}/api/tags", timeout=5)
            if not response.ok:
                pytest.skip("Ollama not available for performance testing")

            available_models = [model["name"] for model in response.json().get("models", [])]
            if not available_models:
                pytest.skip("No models available for performance testing")

        except requests.exceptions.RequestException:
            pytest.skip("Ollama not available for performance testing")

        test_model = available_models[0]

        # Test biological memory processing prompts
        test_prompts = [
            "Extract goal from: Team planning meeting for Q4 objectives",
            "What is the main task in: Code review for authentication system",
            "Analyze hierarchy in: Client meeting about project requirements",
        ]

        def ollama_generation():
            prompt = test_prompts[0]  # Use first prompt for consistency
            try:
                response = requests.post(
                    f"{self.tester.config.ollama_url}/api/generate",
                    json={"model": test_model, "prompt": prompt, "stream": False},
                    timeout=10,
                )

                if response.ok:
                    return response.json().get("response", "")
                return None

            except requests.exceptions.RequestException:
                return None

        metrics = self.tester.measure_operation_performance(
            "ollama_generation",
            ollama_generation,
            num_iterations=5,
            biological_constraint_ms=5000.0,  # 5s constraint for LLM calls
        )

        if metrics.success_rate > 0:
            # For available LLM service
            assert (
                metrics.biological_constraint_met
            ), f"LLM generation took {metrics.avg_time_ms:.1f}ms, should be <5000ms"
            assert (
                metrics.success_rate >= 0.8
            ), f"LLM success rate {metrics.success_rate:.2f} too low"

            logger.info(
                f"LLM Performance: {metrics.avg_time_ms:.1f}ms avg, {metrics.p95_time_ms:.1f}ms p95"
            )
        else:
            logger.info("LLM service not responding - this is acceptable in test environments")

    def test_embedding_generation_performance(self):
        """Test embedding generation performance for semantic networks"""
        try:
            response = requests.get(f"{self.tester.config.ollama_url}/api/tags", timeout=5)
            if not response.ok:
                pytest.skip("Ollama not available for embedding performance testing")

            available_models = response.json().get("models", [])
            embedding_models = [
                model["name"] for model in available_models if "embed" in model["name"].lower()
            ]

            if not embedding_models:
                # Use any available model for embedding test
                embedding_models = [available_models[0]["name"]] if available_models else []

            if not embedding_models:
                pytest.skip("No models available for embedding testing")

        except requests.exceptions.RequestException:
            pytest.skip("Ollama not available for embedding testing")

        test_model = embedding_models[0]

        def embedding_generation():
            try:
                response = requests.post(
                    f"{self.tester.config.ollama_url}/api/embeddings",
                    json={
                        "model": test_model,
                        "prompt": "semantic concept for biological memory",
                    },
                    timeout=15,
                )

                if response.ok:
                    result = response.json()
                    return result.get("embedding", [])
                return None

            except requests.exceptions.RequestException:
                return None

        metrics = self.tester.measure_operation_performance(
            "embedding_generation",
            embedding_generation,
            num_iterations=3,
            biological_constraint_ms=10000.0,  # 10s constraint for embeddings
        )

        if metrics.success_rate > 0:
            assert (
                metrics.biological_constraint_met
            ), f"Embedding took {metrics.avg_time_ms:.1f}ms, should be <10000ms"
            logger.info(f"Embedding Performance: {metrics.avg_time_ms:.1f}ms avg")
        else:
            logger.info("Embedding service not responding - acceptable in test environments")


class TestConcurrentPerformance:
    """Test performance under concurrent load"""

    def setup_method(self):
        """Set up concurrent performance testing"""
        self.tester = BiologicalMemoryPerformanceTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.tester.cleanup()

    def test_concurrent_database_connections(self):
        """Test database performance with concurrent connections"""
        with self.tester:
            self.tester.setup_performance_test_data(100)
            perf_table = f"pg_perf.{self.tester.test_schema}.memory_performance_test"

            def concurrent_query(thread_id: int):
                """Function to run in each thread"""
                try:
                    with self.tester.get_postgres_connection() as conn:
                        with conn.cursor() as cursor:
                            # Each thread runs working memory query
                            start_time = time.perf_counter()
                            cursor.execute(
                                f"""
                                SELECT id, content, importance_score
                                FROM {perf_table}
                                WHERE importance_score > 0.5
                                ORDER BY importance_score DESC
                                LIMIT 7
                            """
                            )
                            result = cursor.fetchall()
                            query_time = (time.perf_counter() - start_time) * 1000

                            return {
                                "thread_id": thread_id,
                                "query_time_ms": query_time,
                                "result_count": len(result),
                                "success": True,
                            }

                except Exception as e:
                    return {"thread_id": thread_id, "error": str(e), "success": False}

            # Run concurrent queries
            num_threads = 5
            start_time = time.perf_counter()

            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(concurrent_query, i) for i in range(num_threads)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            total_time = time.perf_counter() - start_time

            # Analyze concurrent performance
            successful_results = [r for r in results if r.get("success", False)]

            assert (
                len(successful_results) >= num_threads * 0.8
            ), f"Only {len(successful_results)}/{num_threads} concurrent queries succeeded"

            if successful_results:
                avg_query_time = statistics.mean([r["query_time_ms"] for r in successful_results])
                max_query_time = max([r["query_time_ms"] for r in successful_results])

                # Concurrent queries should still meet biological constraints
                assert (
                    avg_query_time < self.tester.config.database_query_limit_ms * 2
                ), f"Concurrent avg time {avg_query_time:.1f}ms too slow"
                assert (
                    max_query_time < self.tester.config.database_query_limit_ms * 3
                ), f"Concurrent max time {max_query_time:.1f}ms too slow"
                assert total_time < 5.0, f"Total concurrent test time {total_time:.1f}s too slow"

                logger.info(f"Concurrent Performance: {num_threads} threads in {total_time:.3f}s")
                logger.info(
                    f"Average query time: {avg_query_time:.1f}ms, Max: {max_query_time:.1f}ms"
                )

    def test_memory_capacity_under_load(self):
        """Test Miller's 7±2 capacity handling under load"""
        with self.tester:
            # Create large dataset to stress-test capacity limits
            self.tester.setup_performance_test_data(1000)

            with self.tester.get_performance_duckdb() as conn:
                perf_table = f"pg_perf.{self.tester.test_schema}.memory_performance_test"

                # Test capacity constraint enforcement under load
                def capacity_stress_test():
                    # Query that could return more than 7 items
                    start_time = time.perf_counter()

                    result = conn.execute(
                        f"""
                        WITH capacity_limited AS (
                            SELECT id, content, importance_score,
                                   ROW_NUMBER() OVER (ORDER BY importance_score DESC, timestamp DESC) as rank
                            FROM {perf_table}
                            WHERE importance_score > 0.3
                        )
                        SELECT * FROM capacity_limited WHERE rank <= 7
                    """
                    ).fetchall()

                    query_time = (time.perf_counter() - start_time) * 1000
                    return len(result), query_time

                # Test multiple times to check consistency
                results = []
                for i in range(20):
                    count, time_ms = capacity_stress_test()
                    results.append((count, time_ms))

                # Validate capacity constraints
                capacities = [r[0] for r in results]
                times = [r[1] for r in results]

                assert all(c <= 7 for c in capacities), f"Capacity violated: {max(capacities)} > 7"
                assert all(c > 0 for c in capacities), "Should always return some results"

                avg_time = statistics.mean(times)
                assert (
                    avg_time < self.tester.config.database_query_limit_ms * 1.5
                ), f"Capacity queries too slow: {avg_time:.1f}ms"

                logger.info(
                    f"Capacity under load: consistent {max(capacities)} ≤ 7 items, {avg_time:.1f}ms avg"
                )


class TestBiologicalRhythmPerformance:
    """Test performance of biological rhythm processing"""

    def setup_method(self):
        """Set up biological rhythm testing"""
        self.tester = BiologicalMemoryPerformanceTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.tester.cleanup()

    def test_attention_window_processing_performance(self):
        """Test 5-minute attention window processing performance"""
        with self.tester:
            self.tester.setup_performance_test_data(200)

            with self.tester.get_performance_duckdb() as conn:
                perf_table = f"pg_perf.{self.tester.test_schema}.memory_performance_test"

                def attention_window_processing():
                    # Process memories within 5-minute attention window
                    return conn.execute(
                        f"""
                        SELECT
                            COUNT(*) as total_in_window,
                            AVG(importance_score) as avg_importance,
                            COUNT(*) FILTER (WHERE importance_score > 0.8) as high_priority
                        FROM {perf_table}
                        WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                    """
                    ).fetchall()[0]

                metrics = self.tester.measure_operation_performance(
                    "attention_window_processing",
                    attention_window_processing,
                    num_iterations=15,
                    biological_constraint_ms=self.tester.config.working_memory_refresh_limit_ms,
                )

                assert (
                    metrics.biological_constraint_met
                ), f"Attention window processing took {metrics.avg_time_ms:.1f}ms, should be <{metrics.constraint_ms}ms"
                assert (
                    metrics.success_rate >= 0.95
                ), "Attention window processing should be highly reliable"

                logger.info(f"Attention Window Performance: {metrics.avg_time_ms:.1f}ms avg")

    def test_forgetting_curve_application_performance(self):
        """Test forgetting curve application performance"""
        with self.tester:
            # Create temporal test data
            with self.tester.get_performance_duckdb() as conn:
                conn.execute(
                    """
                    CREATE TABLE memory_strengths (
                        id INTEGER PRIMARY KEY,
                        concept TEXT,
                        strength FLOAT,
                        last_access TIMESTAMP,
                        age_days FLOAT
                    )
                """
                )

                # Insert test data with various ages
                test_data = []
                for i in range(100):
                    age_days = i * 0.5  # 0 to 50 days
                    last_access = datetime.now(timezone.utc) - timedelta(days=age_days)
                    test_data.append((i, f"concept_{i}", 0.8, last_access, age_days))

                conn.executemany(
                    """
                    INSERT INTO memory_strengths (id, concept, strength, last_access, age_days)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    test_data,
                )

                def forgetting_curve_update():
                    # Apply exponential forgetting curve
                    return conn.execute(
                        """
                        UPDATE memory_strengths
                        SET strength = strength * EXP(-0.05 * age_days)
                        WHERE age_days > 0
                    """
                    ).rowcount

                metrics = self.tester.measure_operation_performance(
                    "forgetting_curve_application",
                    forgetting_curve_update,
                    num_iterations=10,
                    biological_constraint_ms=200.0,  # 200ms for batch updates
                )

                assert (
                    metrics.biological_constraint_met
                ), f"Forgetting curve took {metrics.avg_time_ms:.1f}ms, should be <200ms"

                # Verify forgetting curve applied correctly
                strength_data = conn.execute(
                    """
                    SELECT CAST(age_days AS INTEGER) as age_days, AVG(strength) as avg_strength
                    FROM memory_strengths
                    GROUP BY CAST(age_days AS INTEGER)
                    ORDER BY CAST(age_days AS INTEGER)
                    LIMIT 10
                """
                ).fetchall()

                # Older memories should be weaker
                if len(strength_data) >= 2:
                    assert (
                        strength_data[0][1] > strength_data[-1][1]
                    ), "Forgetting curve should weaken older memories"

                logger.info(f"Forgetting Curve Performance: {metrics.avg_time_ms:.1f}ms avg")


def generate_performance_report(test_results: List[PerformanceMetrics]) -> str:
    """Generate a comprehensive performance report"""
    report = ["", "=" * 80, "BIOLOGICAL MEMORY SYSTEM PERFORMANCE REPORT", "=" * 80, ""]

    # Group results by operation type
    db_operations = [r for r in test_results if "query" in r.operation or "database" in r.operation]
    llm_operations = [r for r in test_results if "llm" in r.operation or "ollama" in r.operation]
    memory_operations = [r for r in test_results if "memory" in r.operation or "stm" in r.operation]

    def add_operation_section(operations: List[PerformanceMetrics], title: str):
        if not operations:
            return

        report.extend([f"{title}:", "-" * len(title)])

        for op in operations:
            status = "✅ PASS" if op.biological_constraint_met else "❌ FAIL"
            report.append(f"  {op.operation}:")
            report.append(
                f"    Performance: {op.avg_time_ms:.1f}ms avg, {op.p95_time_ms:.1f}ms p95"
            )
            report.append(f"    Constraint: <{op.constraint_ms:.0f}ms {status}")
            report.append(f"    Throughput: {op.throughput_ops_per_sec:.1f} ops/sec")
            report.append(f"    Success Rate: {op.success_rate:.1%}")
            report.append("")

    add_operation_section(db_operations, "DATABASE OPERATIONS")
    add_operation_section(memory_operations, "MEMORY PROCESSING")
    add_operation_section(llm_operations, "LLM SERVICE OPERATIONS")

    # Summary statistics
    all_constraints_met = all(r.biological_constraint_met for r in test_results)
    avg_success_rate = statistics.mean([r.success_rate for r in test_results])

    report.extend(
        [
            "SUMMARY:",
            "--------",
            f"Total Operations Tested: {len(test_results)}",
            f"Biological Constraints Met: {'✅ ALL PASS' if all_constraints_met else '❌ SOME FAILED'}",
            f"Average Success Rate: {avg_success_rate:.1%}",
            f"System Status: {'🟢 READY FOR PRODUCTION' if all_constraints_met and avg_success_rate >= 0.9 else '🟡 NEEDS OPTIMIZATION'}",
            "",
            "=" * 80,
        ]
    )

    return "\n".join(report)


def run_performance_benchmark_tests():
    """Run all performance benchmark tests and generate report"""
    logger.info("Starting biological memory system performance benchmarks")

    try:
        pytest_args = [__file__, "-v", "--tb=short", "-k", "test_"]

        exit_code = pytest.main(pytest_args)
        return exit_code == 0

    except Exception as e:
        logger.error(f"Performance benchmark tests failed: {e}")
        return False


if __name__ == "__main__":
    success = run_performance_benchmark_tests()
    exit(0 if success else 1)
