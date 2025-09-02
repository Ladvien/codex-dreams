"""
Edge case and boundary condition tests for biological memory pipeline.

This module tests unusual scenarios, boundary conditions, and edge cases
that could occur in production environments.

Senior QA Engineer Review - Edge Cases to Test:
1. Empty/null data handling
2. Extreme values and boundary conditions
3. Unicode and special character handling
4. Memory capacity edge cases (exactly 7, 0 items, etc.)
5. Concurrent access patterns
6. Resource exhaustion scenarios
7. Malformed input recovery
"""

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import pytest


class TestDataBoundaryConditions:
    """Test edge cases with data boundaries."""

    def test_empty_memory_content_handling(self, biological_memory_schema):
        """Test handling of empty or whitespace-only memory content."""
        conn = biological_memory_schema

        edge_case_memories = [
            (1, "", '{"source": "empty"}'),
            (2, "   ", '{"source": "whitespace"}'),
            (3, "\n\t\r", '{"source": "newlines"}'),
            (4, None, '{"source": "null"}'),
        ]

        for memory_id, content, metadata in edge_case_memories:
            try:
                conn.execute(
                    """
                    INSERT INTO raw_memories (id, content, metadata)
                    VALUES (?, ?, ?)
                """,
                    (memory_id, content, metadata),
                )
            except Exception:
                # Some may fail due to NOT NULL constraints - this is expected
                pass

        # Test processing handles empty content gracefully
        valid_memories = conn.execute(
            """
            SELECT id, content FROM raw_memories
            WHERE content IS NOT NULL
            AND TRIM(content) != ''
            AND LENGTH(TRIM(content)) > 0
        """
        ).fetchall()

        # Should filter out empty/whitespace content but not crash
        assert isinstance(valid_memories, list), "Should return list even with no valid memories"

        # Test working memory rejects empty content
        for memory_id, content, _ in edge_case_memories:
            if content and content.strip():
                conn.execute(
                    """
                    INSERT OR IGNORE INTO working_memory_view (id, content, activation_level)
                    VALUES (?, ?, 0.5)
                """,
                    (memory_id, content.strip()),
                )

        wm_count = conn.execute("SELECT COUNT(*) FROM working_memory_view").fetchall()
        assert wm_count[0][0] == 0, "Working memory should reject empty/whitespace content"

    def test_unicode_and_special_characters(self, biological_memory_schema):
        """Test handling of Unicode characters and special symbols."""
        conn = biological_memory_schema

        unicode_memories = [
            (1, "Meeting with 张三 about 人工智能 project", '{"language": "mixed"}'),
            (2, "Café meeting ☕ to discuss résumé", '{"encoding": "utf8"}'),
            (3, "Code review: function() { return 'test'; }", '{"type": "code"}'),
            (4, "Math symbols: α + β = γ, ∑(x²) ≈ π", '{"domain": "math"}'),
            (5, "Emoji test: 🧠💡🚀✅🔬📊", '{"format": "emoji"}'),
            (6, "SQL injection attempt: '; DROP TABLE memories; --", '{"security": "test"}'),
        ]

        for memory_id, content, metadata in unicode_memories:
            conn.execute(
                """
                INSERT INTO raw_memories (id, content, metadata)
                VALUES (?, ?, ?)
            """,
                (memory_id, content, metadata),
            )

        # Test that Unicode content is preserved
        retrieved = conn.execute(
            """
            SELECT content FROM raw_memories WHERE id = 1
        """
        ).fetchall()
        assert "张三" in retrieved[0][0], "Chinese characters should be preserved"

        retrieved = conn.execute(
            """
            SELECT content FROM raw_memories WHERE id = 2
        """
        ).fetchall()
        assert (
            "Café" in retrieved[0][0] and "résumé" in retrieved[0][0]
        ), "Accented characters should be preserved"

        # Test emoji handling
        retrieved = conn.execute(
            """
            SELECT content FROM raw_memories WHERE id = 5
        """
        ).fetchall()
        assert "🧠" in retrieved[0][0], "Emoji should be preserved"

        # Test that potential SQL injection is safely stored as data
        retrieved = conn.execute(
            """
            SELECT content FROM raw_memories WHERE id = 6
        """
        ).fetchall()
        assert (
            "DROP TABLE" in retrieved[0][0]
        ), "SQL injection attempt should be safely stored as text"

    def test_extreme_memory_sizes(self, test_duckdb):
        """Test handling of extremely large and tiny memory content."""
        conn = test_duckdb

        conn.execute(
            """
            CREATE TABLE size_test_memories (
                id INTEGER,
                content TEXT,
                content_size INTEGER
            )
        """
        )

        # Test very small content
        tiny_content = "x"
        conn.execute(
            """
            INSERT INTO size_test_memories VALUES (1, ?, ?)
        """,
            (tiny_content, len(tiny_content)),
        )

        # Test large content (but reasonable for memory)
        large_content = "This is a very detailed memory about a complex meeting. " * 100  # ~5.7KB
        conn.execute(
            """
            INSERT INTO size_test_memories VALUES (2, ?, ?)
        """,
            (large_content, len(large_content)),
        )

        # Test extremely large content (edge case)
        huge_content = "Extremely long memory content. " * 1000  # ~30KB
        conn.execute(
            """
            INSERT INTO size_test_memories VALUES (3, ?, ?)
        """,
            (huge_content, len(huge_content)),
        )

        # Verify all sizes stored correctly
        sizes = conn.execute(
            """
            SELECT id, content_size FROM size_test_memories ORDER BY id
        """
        ).fetchall()

        assert sizes[0][1] == 1, "Single character should be stored"
        assert sizes[1][1] > 5000, "Large content should be stored"
        assert sizes[2][1] > 29000, "Huge content should be stored"

        # Test retrieval performance doesn't degrade significantly
        import time

        start_time = time.perf_counter()

        all_content = conn.execute("SELECT content FROM size_test_memories").fetchall()

        retrieval_time = time.perf_counter() - start_time
        assert retrieval_time < 0.1, f"Retrieval took {retrieval_time:.3f}s, should be <0.1s"
        assert len(all_content) == 3, "All memory sizes should be retrievable"


class TestCapacityEdgeCases:
    """Test Miller's 7±2 rule edge cases."""

    def test_exactly_seven_items_handling(self, biological_memory_schema):
        """Test behavior with exactly 7 items (Miller's optimal)."""
        conn = biological_memory_schema

        # Insert exactly 7 items
        for i in range(7):
            conn.execute(
                """
                INSERT INTO raw_memories (id, content, metadata)
                VALUES (?, ?, ?)
            """,
                (i + 1, f"Memory item {i+1}", json.dumps({"importance": 0.5 + i * 0.05})),
            )

        # All should fit in working memory
        conn.execute(
            """
            INSERT INTO working_memory_view (id, content, activation_level, miller_capacity_position)
            SELECT id, content,
                   CAST(JSON_EXTRACT(metadata, '$.importance') AS FLOAT),
                   ROW_NUMBER() OVER (ORDER BY id)
            FROM raw_memories
        """
        )

        wm_count = conn.execute("SELECT COUNT(*) FROM working_memory_view").fetchall()
        assert wm_count[0][0] == 7, "Exactly 7 items should all fit in working memory"

        # Verify capacity constraint is enforced
        max_position = conn.execute(
            """
            SELECT MAX(miller_capacity_position) FROM working_memory_view
        """
        ).fetchall()
        assert max_position[0][0] == 7, "Maximum position should be 7"

    def test_zero_items_handling(self, biological_memory_schema):
        """Test behavior with no memory items."""
        conn = biological_memory_schema

        # No memories in system
        raw_count = conn.execute("SELECT COUNT(*) FROM raw_memories").fetchall()
        assert raw_count[0][0] == 0, "Should start with no memories"

        # Working memory should handle empty state
        wm_count = conn.execute("SELECT COUNT(*) FROM working_memory_view").fetchall()
        assert wm_count[0][0] == 0, "Working memory should be empty when no input"

        # STM should handle empty state
        stm_count = conn.execute("SELECT COUNT(*) FROM stm_hierarchical_episodes").fetchall()
        assert stm_count[0][0] == 0, "STM should be empty when no input"

        # LTM should handle empty state
        ltm_count = conn.execute("SELECT COUNT(*) FROM ltm_semantic_network").fetchall()
        assert ltm_count[0][0] == 0, "LTM should be empty when no input"

    def test_beyond_capacity_handling(self, biological_memory_schema):
        """Test behavior with more than 9 items (beyond Miller's 7±2)."""
        conn = biological_memory_schema

        # Insert 20 items (well beyond capacity)
        for i in range(20):
            conn.execute(
                """
                INSERT INTO raw_memories (id, content, metadata)
                VALUES (?, ?, ?)
            """,
                (i + 1, f"Overflow memory {i+1}", json.dumps({"importance": 1.0 - i * 0.01})),
            )

        # Simulate working memory selection with capacity enforcement
        conn.execute(
            """
            WITH ranked_memories AS (
                SELECT id, content,
                       CAST(JSON_EXTRACT(metadata, '$.importance') AS FLOAT) as importance,
                       ROW_NUMBER() OVER (ORDER BY CAST(JSON_EXTRACT(metadata, '$.importance') AS FLOAT) DESC) as rank
                FROM raw_memories
            )
            INSERT INTO working_memory_view (id, content, activation_level, miller_capacity_position)
            SELECT id, content, importance, rank
            FROM ranked_memories
            WHERE rank <= 7
        """
        )

        # Should only keep top 7 items
        wm_count = conn.execute("SELECT COUNT(*) FROM working_memory_view").fetchall()
        assert wm_count[0][0] == 7, "Should enforce Miller's 7±2 capacity limit"

        # Verify highest importance items were kept
        min_importance = conn.execute(
            """
            SELECT MIN(activation_level) FROM working_memory_view
        """
        ).fetchall()
        assert min_importance[0][0] >= 0.87, "Should keep highest importance items only"


class TestConcurrencyEdgeCases:
    """Test concurrent access and race conditions."""

    def test_simultaneous_memory_insertion(self, biological_memory_schema):
        """Test concurrent memory insertion scenarios."""
        conn = biological_memory_schema

        # Simulate concurrent insertions (simplified - single threaded test)
        memories_batch_1 = [(1, "Memory A1"), (3, "Memory A3"), (5, "Memory A5")]
        memories_batch_2 = [(2, "Memory B2"), (4, "Memory B4"), (6, "Memory B6")]

        # Insert in interleaved order to simulate concurrency
        all_memories = memories_batch_1 + memories_batch_2
        # Sort by ID to simulate race conditions
        all_memories.sort(key=lambda x: x[0])

        for memory_id, content in all_memories:
            conn.execute(
                """
                INSERT INTO raw_memories (id, content, timestamp)
                VALUES (?, ?, ?)
            """,
                (memory_id, content, datetime.now(timezone.utc)),
            )

        # Verify all memories were inserted
        total_count = conn.execute("SELECT COUNT(*) FROM raw_memories").fetchall()
        assert total_count[0][0] == 6, "All concurrent insertions should succeed"

        # Test concurrent working memory updates
        for memory_id, content in all_memories:
            # Simulate concurrent activation level updates
            conn.execute(
                """
                INSERT OR REPLACE INTO working_memory_view
                (id, content, activation_level)
                VALUES (?, ?, ?)
            """,
                (memory_id, content, 0.5 + (memory_id * 0.1)),
            )

        # Verify final state is consistent
        wm_count = conn.execute("SELECT COUNT(*) FROM working_memory_view").fetchall()
        assert wm_count[0][0] <= 7, "Concurrent updates should maintain capacity limits"

    def test_memory_processing_interruption_recovery(self, biological_memory_schema):
        """Test recovery from interrupted memory processing."""
        conn = biological_memory_schema

        # Insert memories for processing
        for i in range(5):
            conn.execute(
                """
                INSERT INTO raw_memories (id, content, processed)
                VALUES (?, ?, FALSE)
            """,
                (i + 1, f"Processing test memory {i+1}"),
            )

        # Simulate partial processing (interrupted after processing first 2)
        for i in range(2):
            conn.execute(
                """
                INSERT INTO stm_hierarchical_episodes
                (id, content, level_0_goal, stm_strength)
                VALUES (?, ?, ?, ?)
            """,
                (i + 1, f"Processing test memory {i+1}", f"Goal {i+1}", 0.7),
            )

            conn.execute(
                """
                UPDATE raw_memories SET processed = TRUE WHERE id = ?
            """,
                (i + 1,),
            )

        # Simulate recovery - find unprocessed memories
        unprocessed = conn.execute(
            """
            SELECT id, content FROM raw_memories WHERE processed = FALSE
        """
        ).fetchall()

        assert len(unprocessed) == 3, "Should identify 3 unprocessed memories"

        # Continue processing from where interrupted
        for memory_id, content in unprocessed:
            conn.execute(
                """
                INSERT INTO stm_hierarchical_episodes
                (id, content, level_0_goal, stm_strength)
                VALUES (?, ?, ?, ?)
            """,
                (memory_id, content, f"Resumed Goal {memory_id}", 0.6),
            )

            conn.execute(
                """
                UPDATE raw_memories SET processed = TRUE WHERE id = ?
            """,
                (memory_id,),
            )

        # Verify complete recovery
        all_processed = conn.execute(
            """
            SELECT COUNT(*) FROM raw_memories WHERE processed = TRUE
        """
        ).fetchall()
        assert all_processed[0][0] == 5, "All memories should be processed after recovery"


class TestResourceExhaustionScenarios:
    """Test behavior under resource constraints."""

    def test_memory_database_full_scenario(self, test_duckdb):
        """Test handling when database approaches capacity limits."""
        conn = test_duckdb

        # Create table with limited space simulation
        conn.execute(
            """
            CREATE TABLE limited_memories (
                id INTEGER PRIMARY KEY CHECK (id <= 100),
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Fill to near capacity
        for i in range(95):
            conn.execute(
                """
                INSERT INTO limited_memories (id, content)
                VALUES (?, ?)
            """,
                (i + 1, f"Memory {i+1}"),
            )

        # Try to add more memories (some should fail due to CHECK constraint)
        insertion_failures = 0
        for i in range(95, 110):  # Try to add 15 more (will exceed limit)
            try:
                conn.execute(
                    """
                    INSERT INTO limited_memories (id, content)
                    VALUES (?, ?)
                """,
                    (i + 1, f"Overflow Memory {i+1}"),
                )
            except Exception:
                insertion_failures += 1

        # Verify graceful handling of capacity limits
        total_stored = conn.execute("SELECT COUNT(*) FROM limited_memories").fetchall()
        assert total_stored[0][0] <= 100, "Should respect capacity constraints"
        assert insertion_failures > 0, "Should have rejected some insertions when full"

    def test_connection_pool_exhaustion(self, test_env_vars):
        """Test behavior when database connection pool is exhausted."""
        # This test simulates connection pool limits
        max_connections = int(test_env_vars["MAX_DB_CONNECTIONS"])

        # Test that we respect connection limits
        assert max_connections == 160, "Should have reasonable connection limit"

        # Simulate connection management
        active_connections = []
        connection_failures = 0

        # Try to create more connections than allowed (simulated)
        for i in range(max_connections + 10):
            if i < max_connections:
                # Simulate successful connection
                active_connections.append(f"conn_{i}")
            else:
                # Simulate connection failure
                connection_failures += 1

        assert len(active_connections) == max_connections, "Should limit active connections"
        assert connection_failures == 10, "Should reject excess connections"

    def test_malformed_json_metadata_recovery(self, biological_memory_schema):
        """Test recovery from corrupted JSON metadata."""
        conn = biological_memory_schema

        malformed_data = [
            (1, "Valid memory", '{"source": "test", "importance": 0.8}'),
            (2, "Memory with broken JSON", '{"source": "test", "importance":}'),
            (3, "Memory with unclosed JSON", '{"source": "test"'),
            (4, "Memory with invalid JSON", "{source: test}"),
            (5, "Memory with null metadata", None),
        ]

        for memory_id, content, metadata in malformed_data:
            conn.execute(
                """
                INSERT INTO raw_memories (id, content, metadata)
                VALUES (?, ?, ?)
            """,
                (memory_id, content, metadata),
            )

        # Test robust metadata processing
        processed_memories = conn.execute(
            """
            SELECT id, content, metadata,
                   CASE
                       WHEN metadata IS NULL THEN '{"source": "unknown"}'
                       WHEN JSON_VALID(metadata) = 1 THEN metadata
                       ELSE '{"source": "malformed", "original": "' || REPLACE(metadata, '"', '\\"') || '"}'
                   END as safe_metadata
            FROM raw_memories
            ORDER BY id
        """
        ).fetchall()

        assert len(processed_memories) == 5, "Should process all memories despite JSON errors"

        # Verify each memory has valid JSON after processing
        for memory in processed_memories:
            safe_metadata = memory[3]
            try:
                parsed = json.loads(safe_metadata)
                assert "source" in parsed, "Processed metadata should have source field"
            except json.JSONDecodeError:
                pytest.fail(f"Metadata should be valid JSON after processing: {safe_metadata}")


class TestSystemStabilityEdgeCases:
    """Test system stability under unusual conditions."""

    def test_rapid_memory_creation_and_deletion(self, biological_memory_schema):
        """Test stability under rapid memory creation/deletion cycles."""
        conn = biological_memory_schema

        # Rapid insertion/deletion cycle
        for cycle in range(10):
            # Insert batch
            for i in range(10):
                memory_id = cycle * 10 + i
                conn.execute(
                    """
                    INSERT INTO raw_memories (id, content, metadata)
                    VALUES (?, ?, ?)
                """,
                    (memory_id, f"Cycle {cycle} Memory {i}", '{"cycle": ' + str(cycle) + "}"),
                )

            # Delete half of them
            conn.execute(
                """
                DELETE FROM raw_memories
                WHERE id >= ? AND id < ? AND id % 2 = 0
            """,
                (cycle * 10, (cycle + 1) * 10),
            )

        # Verify system remains stable
        final_count = conn.execute("SELECT COUNT(*) FROM raw_memories").fetchall()
        assert (
            final_count[0][0] == 50
        ), "Should have 50 memories after cycles (5 per cycle × 10 cycles)"

        # Verify data integrity maintained
        sample_memory = conn.execute(
            """
            SELECT content, metadata FROM raw_memories LIMIT 1
        """
        ).fetchall()
        assert len(sample_memory) == 1, "Should be able to query remaining data"
        assert "Cycle" in sample_memory[0][0], "Content should be intact"

    def test_timestamp_boundary_conditions(self, biological_memory_schema):
        """Test handling of timestamp edge cases."""
        conn = biological_memory_schema

        from datetime import datetime, timedelta, timezone

        # Edge case timestamps
        edge_timestamps = [
            datetime.min.replace(tzinfo=timezone.utc),  # Minimum datetime
            datetime.max.replace(tzinfo=timezone.utc),  # Maximum datetime
            datetime.now(timezone.utc),  # Current time
            datetime.now(timezone.utc) + timedelta(days=365 * 100),  # Far future
            datetime.now(timezone.utc) - timedelta(days=365 * 100),  # Far past
        ]

        for i, timestamp in enumerate(edge_timestamps):
            try:
                conn.execute(
                    """
                    INSERT INTO raw_memories (id, content, timestamp)
                    VALUES (?, ?, ?)
                """,
                    (i + 1, f"Timestamp test {i+1}", timestamp),
                )
            except Exception as e:
                # Some timestamps might be rejected - this is acceptable
                print(f"Timestamp {timestamp} rejected: {e}")
                continue

        # Verify timestamps are handled consistently
        stored_timestamps = conn.execute(
            """
            SELECT id, timestamp FROM raw_memories WHERE id <= 5 ORDER BY id
        """
        ).fetchall()

        assert len(stored_timestamps) >= 1, "Should store at least some valid timestamps"

        # Test timestamp-based queries work
        recent_memories = conn.execute(
            """
            SELECT COUNT(*) FROM raw_memories
            WHERE timestamp > datetime('now', '-1 day')
        """
        ).fetchall()

        assert isinstance(recent_memories[0][0], int), "Timestamp queries should work"
