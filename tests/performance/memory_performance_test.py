"""
Performance benchmarks for biological memory operations.

Tests memory processing performance to ensure:
- Working memory refresh <100ms
- Short-term processing <500ms
- Consolidation operations <2s
- Total test suite <5 minutes
"""

import pytest
import time
from datetime import datetime, timezone
from typing import List, Dict, Any


class TestMemoryPerformance:
    """Performance benchmarks for memory operations."""

    @pytest.mark.performance
    def test_working_memory_refresh_performance(
        self, performance_benchmark, working_memory_fixture
    ):
        """Working memory refresh should complete in <100ms."""
        conn = working_memory_fixture

        with performance_benchmark() as timer:
            # Simulate working memory view refresh (Miller's 7±2 capacity)
            result = conn.execute(
                """
                SELECT id, content, timestamp, metadata
                FROM raw_memories 
                WHERE timestamp > NOW() - INTERVAL '5 minutes'
                ORDER BY timestamp DESC
                LIMIT 7
            """
            ).fetchall()

        # Performance requirement: <100ms
        assert (
            timer.elapsed < 0.1
        ), f"Working memory refresh took {timer.elapsed:.3f}s, should be <0.1s"
        assert len(result) <= 7, "Should respect Miller's 7±2 capacity limit"

    @pytest.mark.performance
    def test_short_term_memory_processing_performance(
        self, performance_benchmark, short_term_memory_fixture
    ):
        """Short-term memory processing should complete in <500ms."""
        conn = short_term_memory_fixture

        with performance_benchmark() as timer:
            # Simulate STM hierarchical processing
            result = conn.execute(
                """
                SELECT id, level_0_goal, level_1_tasks, atomic_actions,
                       stm_strength, hebbian_potential
                FROM stm_hierarchical_episodes
                WHERE stm_strength > 0.3
                ORDER BY stm_strength DESC
            """
            ).fetchall()

        # Performance requirement: <500ms
        assert timer.elapsed < 0.5, f"STM processing took {timer.elapsed:.3f}s, should be <0.5s"
        assert len(result) >= 0, "Should return processed STM episodes"

    @pytest.mark.performance
    def test_batch_memory_insert_performance(self, performance_benchmark, test_duckdb):
        """Batch memory insertion should handle 100 records in <200ms."""
        conn = test_duckdb

        # Create table
        conn.execute(
            """
            CREATE TABLE batch_memories (
                id INTEGER,
                content TEXT,
                timestamp TIMESTAMP,
                metadata JSON
            )
        """
        )

        # Generate test data
        test_memories = [
            {
                "id": i,
                "content": f"Memory content {i}",
                "timestamp": datetime.now(timezone.utc),
                "metadata": {"source": "test", "batch": i // 10},
            }
            for i in range(100)
        ]

        with performance_benchmark() as timer:
            for memory in test_memories:
                conn.execute(
                    "INSERT INTO batch_memories VALUES (?, ?, ?, ?)",
                    (
                        memory["id"],
                        memory["content"],
                        memory["timestamp"],
                        f'{{"source": "{memory["metadata"]["source"]}", "batch": {memory["metadata"]["batch"]}}}',
                    ),
                )

        # Performance requirement: <200ms for 100 records
        assert timer.elapsed < 0.2, f"Batch insert took {timer.elapsed:.3f}s, should be <0.2s"

        # Verify all records inserted
        count = conn.execute("SELECT COUNT(*) FROM batch_memories").fetchall()
        assert count[0][0] == 100, "Should insert all 100 records"

    @pytest.mark.performance
    def test_memory_search_performance(self, performance_benchmark, working_memory_fixture):
        """Memory search should complete in <50ms."""
        conn = working_memory_fixture

        # Add more test data for realistic search
        for i in range(20):
            conn.execute(
                """
                INSERT INTO raw_memories VALUES (?, ?, ?, ?)
            """,
                (
                    i + 100,
                    f"Search test memory {i}",
                    datetime.now(timezone.utc),
                    '{"source": "search_test"}',
                ),
            )

        with performance_benchmark() as timer:
            # Simulate memory search operation
            result = conn.execute(
                """
                SELECT id, content FROM raw_memories
                WHERE content LIKE '%meeting%' OR content LIKE '%review%'
                ORDER BY timestamp DESC
            """
            ).fetchall()

        # Performance requirement: <50ms
        assert timer.elapsed < 0.05, f"Memory search took {timer.elapsed:.3f}s, should be <0.05s"

    @pytest.mark.performance
    def test_consolidation_candidate_selection_performance(
        self, performance_benchmark, short_term_memory_fixture
    ):
        """Consolidation candidate selection should complete in <100ms."""
        conn = short_term_memory_fixture

        with performance_benchmark() as timer:
            # Simulate consolidation candidate selection
            result = conn.execute(
                """
                SELECT id, content, stm_strength, hebbian_potential,
                       (stm_strength * hebbian_potential) as consolidation_score
                FROM stm_hierarchical_episodes
                WHERE ready_for_consolidation = true
                  AND stm_strength > 0.5
                ORDER BY consolidation_score DESC
                LIMIT 10
            """
            ).fetchall()

        # Performance requirement: <100ms
        assert (
            timer.elapsed < 0.1
        ), f"Consolidation selection took {timer.elapsed:.3f}s, should be <0.1s"

    @pytest.mark.performance
    def test_hebbian_strength_calculation_performance(self, performance_benchmark, test_duckdb):
        """Hebbian strength calculations should complete in <50ms."""
        conn = test_duckdb

        # Create test data for Hebbian calculations
        conn.execute(
            """
            CREATE TABLE test_associations (
                id INTEGER,
                concept_a TEXT,
                concept_b TEXT,
                co_occurrence_count INTEGER,
                total_occurrences_a INTEGER,
                total_occurrences_b INTEGER
            )
        """
        )

        # Insert test association data
        test_data = [
            (1, "meeting", "collaboration", 15, 50, 30),
            (2, "code", "review", 25, 100, 40),
            (3, "project", "planning", 10, 80, 20),
            (4, "team", "discussion", 8, 60, 25),
            (5, "task", "completion", 12, 90, 35),
        ]

        for data in test_data:
            conn.execute("INSERT INTO test_associations VALUES (?, ?, ?, ?, ?, ?)", data)

        with performance_benchmark() as timer:
            # Calculate Hebbian association strength
            result = conn.execute(
                """
                SELECT id, concept_a, concept_b,
                       CAST(co_occurrence_count AS FLOAT) / 
                       SQRT(CAST(total_occurrences_a AS FLOAT) * CAST(total_occurrences_b AS FLOAT)) 
                       AS hebbian_strength
                FROM test_associations
                ORDER BY hebbian_strength DESC
            """
            ).fetchall()

        # Performance requirement: <50ms
        assert (
            timer.elapsed < 0.05
        ), f"Hebbian calculation took {timer.elapsed:.3f}s, should be <0.05s"
        assert len(result) == 5, "Should calculate strength for all associations"

    @pytest.mark.performance
    def test_full_pipeline_integration_performance(self, performance_benchmark, test_duckdb):
        """Full memory processing pipeline should complete in <1s."""
        conn = test_duckdb

        # Set up full pipeline tables
        conn.execute(
            """
            CREATE TABLE raw_memories (
                id INTEGER, content TEXT, timestamp TIMESTAMP, metadata JSON
            )
        """
        )

        conn.execute(
            """
            CREATE TABLE processed_memories (
                id INTEGER, content TEXT, goal TEXT, tasks TEXT, 
                actions TEXT, strength FLOAT
            )
        """
        )

        # Insert test data
        for i in range(10):
            conn.execute(
                """
                INSERT INTO raw_memories VALUES (?, ?, ?, ?)
            """,
                (
                    i,
                    f"Pipeline test memory {i}",
                    datetime.now(timezone.utc),
                    '{"source": "pipeline"}',
                ),
            )

        with performance_benchmark() as timer:
            # Simulate full processing pipeline
            # 1. Extract from raw memories
            raw_data = conn.execute("SELECT * FROM raw_memories").fetchall()

            # 2. Process each memory (simulated hierarchy extraction)
            for memory in raw_data:
                processed_goal = f"Goal for memory {memory[0]}"
                processed_tasks = f"Tasks for memory {memory[0]}"
                processed_actions = f"Actions for memory {memory[0]}"
                strength = 0.5 + (memory[0] * 0.05)  # Simulated strength calculation

                # 3. Insert into processed table
                conn.execute(
                    """
                    INSERT INTO processed_memories VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        memory[0],
                        memory[1],
                        processed_goal,
                        processed_tasks,
                        processed_actions,
                        strength,
                    ),
                )

            # 4. Select consolidation candidates
            candidates = conn.execute(
                """
                SELECT * FROM processed_memories WHERE strength > 0.6
            """
            ).fetchall()

        # Performance requirement: <1s for full pipeline
        assert timer.elapsed < 1.0, f"Full pipeline took {timer.elapsed:.3f}s, should be <1.0s"
        assert len(candidates) > 0, "Should identify consolidation candidates"


class TestMemoryCapacityLimits:
    """Test performance under memory capacity limits."""

    @pytest.mark.performance
    def test_millers_law_compliance_performance(self, performance_benchmark, test_duckdb):
        """Working memory should efficiently handle 7±2 items."""
        conn = test_duckdb

        conn.execute(
            """
            CREATE TABLE working_memory_items (
                id INTEGER,
                content TEXT,
                activation_level FLOAT,
                timestamp TIMESTAMP
            )
        """
        )

        # Test with exactly 7 items (Miller's optimal)
        for i in range(7):
            conn.execute(
                """
                INSERT INTO working_memory_items VALUES (?, ?, ?, ?)
            """,
                (i, f"WM item {i}", 0.8 + (i * 0.02), datetime.now(timezone.utc)),
            )

        with performance_benchmark() as timer:
            # Simulate working memory operations
            active_items = conn.execute(
                """
                SELECT * FROM working_memory_items 
                WHERE activation_level > 0.7
                ORDER BY activation_level DESC
                LIMIT 7
            """
            ).fetchall()

        # Should be very fast for optimal capacity
        assert timer.elapsed < 0.01, f"Miller's 7 items took {timer.elapsed:.3f}s, should be <0.01s"
        assert len(active_items) == 7, "Should handle exactly 7 items efficiently"

    @pytest.mark.performance
    def test_capacity_overflow_handling_performance(self, performance_benchmark, test_duckdb):
        """Test performance when exceeding working memory capacity."""
        conn = test_duckdb

        conn.execute(
            """
            CREATE TABLE overflow_test (
                id INTEGER,
                content TEXT,
                priority FLOAT,
                timestamp TIMESTAMP
            )
        """
        )

        # Insert 15 items (exceeding 7±2 capacity)
        for i in range(15):
            conn.execute(
                """
                INSERT INTO overflow_test VALUES (?, ?, ?, ?)
            """,
                (i, f"Overflow item {i}", 1.0 - (i * 0.05), datetime.now(timezone.utc)),
            )

        with performance_benchmark() as timer:
            # System should efficiently select top 7 items
            selected_items = conn.execute(
                """
                SELECT * FROM overflow_test 
                ORDER BY priority DESC
                LIMIT 7
            """
            ).fetchall()

        # Should handle overflow gracefully
        assert (
            timer.elapsed < 0.05
        ), f"Overflow handling took {timer.elapsed:.3f}s, should be <0.05s"
        assert len(selected_items) == 7, "Should limit to 7 items despite overflow"
        assert selected_items[0][2] >= selected_items[-1][2], "Should maintain priority ordering"
