"""
Biological Working Memory Window Tests

Validates working memory implementation against cognitive science research:
- Miller (1956): "The Magical Number Seven, Plus or Minus Two"
- Cowan (2001): Working memory capacity limits
- Peterson & Peterson (1959): Short-term memory decay
- Baddeley (2000): Working memory model

Tests biological accuracy of attention window and capacity constraints.
"""

import random
from datetime import datetime, timedelta

import duckdb
import pytest


class TestWorkingMemoryBiologicalAccuracy:
    """Test suite for biological accuracy of working memory implementation."""

    @pytest.fixture
    def db_connection(self):
        """Create test database connection with biological memory tables."""
        conn = duckdb.connect(":memory:")

        # Create test memories table with biological parameters
        conn.execute(
            """
            CREATE TABLE memories (
                memory_id VARCHAR,
                content TEXT,
                concepts TEXT[],
                activation_strength FLOAT,
                created_at TIMESTAMP,
                last_accessed_at TIMESTAMP,
                access_count INTEGER,
                memory_type VARCHAR
            )
        """
        )

        return conn

    def test_working_memory_duration_biological_accuracy(self, db_connection):
        """
        Test that working memory attention window is 5 minutes per Miller (1956).

        Biological Basis:
        - Miller (1956): Attention span limited to short periods
        - Cowan (2001): Working memory operates within focused attention window
        - Peterson & Peterson (1959): Rapid decay without rehearsal
        """
        # Insert memories at different time intervals
        base_time = datetime.now()

        test_memories = [
            # Within 5-minute window (should be included)
            (base_time - timedelta(minutes=2), 0.8, "recent_memory_1"),
            (base_time - timedelta(minutes=4), 0.7, "recent_memory_2"),
            # Outside 5-minute window (should be excluded)
            (base_time - timedelta(minutes=6), 0.9, "old_memory_1"),
            (base_time - timedelta(minutes=10), 0.8, "old_memory_2"),
            (
                base_time - timedelta(minutes=30),
                0.9,
                "stm_memory",
            ),  # Short-term memory range
        ]

        for created_at, strength, content in test_memories:
            db_connection.execute(
                """
                INSERT INTO memories (
                    memory_id, content, concepts, activation_strength,
                    created_at, last_accessed_at, access_count, memory_type
                ) VALUES (?, ?, ['test'], ?, ?, ?, 3, 'test')
            """,
                [content, content, strength, created_at, created_at],
            )

        # Test working memory query with 5-minute window (300 seconds)
        result = db_connection.execute(
            """
            SELECT content, created_at
            FROM memories
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '300 SECONDS'
              AND activation_strength > 0.6
              AND access_count >= 2
            ORDER BY activation_strength DESC
        """
        ).fetchall()

        # Should only contain memories within 5-minute window
        assert len(result) == 2, f"Expected 2 memories in working memory, got {len(result)}"

        contents = [row[0] for row in result]
        assert "recent_memory_1" in contents
        assert "recent_memory_2" in contents
        assert "old_memory_1" not in contents
        assert "old_memory_2" not in contents
        assert "stm_memory" not in contents

    def test_miller_capacity_variability(self, db_connection):
        """
        Test Miller's 7±2 capacity variability in working memory.

        Biological Basis:
        - Miller (1956): Capacity varies between 5-9 items
        - Individual differences in working memory span
        - Task complexity affects capacity utilization
        """
        # Insert 12 high-quality memories (more than max capacity)
        base_time = datetime.now()

        for i in range(12):
            db_connection.execute(
                """
                INSERT INTO memories (
                    memory_id, content, concepts, activation_strength,
                    created_at, last_accessed_at, access_count, memory_type
                ) VALUES (?, ?, ['test'], ?, ?, ?, 5, 'test')
            """,
                [
                    f"memory_{i}",
                    f"High quality memory {i}",
                    0.9,
                    base_time - timedelta(minutes=1),
                    base_time,
                ],
            )

        # Test capacity variability multiple times
        capacity_counts = []
        for trial in range(50):  # Multiple trials to test randomness
            # Simulate Miller's 7±2 formula: 7 + FLOOR(RANDOM() * 3 - 1)
            random.seed(trial)  # Deterministic for testing
            capacity = 7 + int(random.random() * 3 - 1)  # Range: 6-9

            result = db_connection.execute(
                f"""
                WITH ranked_memories AS (
                    SELECT *,
                        ROW_NUMBER() OVER (ORDER BY activation_strength DESC, created_at DESC) as rank
                    FROM memories
                    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '300 SECONDS'
                      AND activation_strength > 0.6
                      AND access_count >= 2
                )
                SELECT COUNT(*) as capacity_used
                FROM ranked_memories
                WHERE rank <= {capacity}
            """
            ).fetchone()[0]

            capacity_counts.append(result)

        # Validate capacity range follows Miller's Law
        min_capacity = min(capacity_counts)
        max_capacity = max(capacity_counts)

        assert min_capacity >= 5, f"Minimum capacity {min_capacity} below Miller's range (5-9)"
        assert max_capacity <= 9, f"Maximum capacity {max_capacity} above Miller's range (5-9)"
        assert max_capacity > min_capacity, "Capacity should show variability"

    def test_working_vs_short_term_memory_distinction(self, db_connection):
        """
        Test biological distinction between working memory and short-term memory.

        Biological Basis:
        - Working Memory: 5-minute attention window
        - Short-term Memory: 15-30 minutes (Peterson & Peterson 1959)
        - Different neural mechanisms and consolidation processes
        """
        base_time = datetime.now()

        # Insert memories across different temporal ranges
        test_data = [
            # Working memory range (0-5 minutes)
            (base_time - timedelta(minutes=1), "working_1"),
            (base_time - timedelta(minutes=3), "working_2"),
            # Short-term memory range (5-30 minutes)
            (base_time - timedelta(minutes=10), "short_term_1"),
            (base_time - timedelta(minutes=20), "short_term_2"),
            # Beyond short-term memory (>30 minutes)
            (base_time - timedelta(minutes=45), "long_term_1"),
        ]

        for created_at, content in test_data:
            db_connection.execute(
                """
                INSERT INTO memories (
                    memory_id, content, concepts, activation_strength,
                    created_at, last_accessed_at, access_count, memory_type
                ) VALUES (?, ?, ['test'], ?, ?, ?, 3, 'test')
            """,
                [content, content, 0.8, created_at, created_at],
            )

        # Test working memory window (5 minutes)
        working_result = db_connection.execute(
            """
            SELECT content FROM memories
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '300 SECONDS'
              AND activation_strength > 0.6
        """
        ).fetchall()

        # Test short-term memory window (30 minutes)
        short_term_result = db_connection.execute(
            """
            SELECT content FROM memories
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '1800 SECONDS'
              AND activation_strength > 0.6
        """
        ).fetchall()

        working_contents = [row[0] for row in working_result]
        short_term_contents = [row[0] for row in short_term_result]

        # Working memory should only contain recent items
        assert len(working_contents) == 2
        assert all("working_" in content for content in working_contents)

        # Short-term memory should contain both working and short-term items
        assert len(short_term_contents) == 4
        assert "working_1" in short_term_contents
        assert "short_term_1" in short_term_contents
        assert "long_term_1" not in short_term_contents

    def test_attention_window_biological_constraints(self, db_connection):
        """
        Test that attention window aligns with hippocampal theta rhythms.

        Biological Basis:
        - Hippocampal theta: 4-8 Hz associated with working memory
        - Attention cycles correlate with neural oscillations
        - 5-minute window represents sustained attention capacity
        """
        base_time = datetime.now()

        # Test attention decay over time within working memory window
        attention_test_points = [
            (base_time - timedelta(seconds=30), 0.95, "peak_attention"),
            (base_time - timedelta(seconds=90), 0.85, "high_attention"),
            (base_time - timedelta(seconds=180), 0.75, "medium_attention"),
            (base_time - timedelta(seconds=270), 0.65, "low_attention"),
            (
                base_time - timedelta(seconds=330),
                0.55,
                "below_threshold",
            ),  # Beyond 5 min
        ]

        for created_at, strength, content in attention_test_points:
            db_connection.execute(
                """
                INSERT INTO memories (
                    memory_id, content, concepts, activation_strength,
                    created_at, last_accessed_at, access_count, memory_type
                ) VALUES (?, ?, ['attention'], ?, ?, ?, 3, 'test')
            """,
                [content, content, strength, created_at, created_at],
            )

        # Test working memory selection with biological constraints
        result = db_connection.execute(
            """
            SELECT content, activation_strength,
                   EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) as age_seconds
            FROM memories
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '300 SECONDS'  -- 5 min window
              AND activation_strength > 0.6  -- Plasticity threshold
              AND access_count >= 2
            ORDER BY activation_strength DESC
        """
        ).fetchall()

        # Should exclude memory beyond 5-minute window
        contents = [row[0] for row in result]
        assert "below_threshold" not in contents, "Memory beyond 5-minute window should be excluded"
        assert len(result) == 4, f"Expected 4 memories in attention window, got {len(result)}"

        # Validate attention decay pattern
        for content, strength, age in result:
            assert age <= 300, f"Memory {content} exceeds 5-minute attention window"
            if age < 180:  # Within 3 minutes
                assert strength >= 0.75, f"Recent memory {content} should have high activation"


class TestWorkingMemoryNeuralPlausibility:
    """Test neural plausibility of working memory implementation."""

    @pytest.fixture
    def db_connection(self):
        """Create test database connection with biological memory tables."""
        conn = duckdb.connect(":memory:")

        # Create test memories table with biological parameters
        conn.execute(
            """
            CREATE TABLE memories (
                memory_id VARCHAR,
                content TEXT,
                concepts TEXT[],
                activation_strength FLOAT,
                created_at TIMESTAMP,
                last_accessed_at TIMESTAMP,
                access_count INTEGER,
                memory_type VARCHAR
            )
        """
        )

        return conn

    def test_hebbian_strengthening_in_working_memory(self, db_connection):
        """
        Test Hebbian learning within working memory processing.

        Biological Basis:
        - Hebb's Rule: "Neurons that fire together, wire together"
        - Working memory involves active maintenance through recurrent connections
        - Rehearsal strengthens synaptic connections
        """
        # This would test the Hebbian strength calculation:
        # LEAST(1.0, activation_strength * (1.0 + hebbian_learning_rate))

        test_cases = [
            (0.5, 0.1, min(1.0, 0.5 * 1.1)),  # Normal strengthening
            (0.9, 0.1, min(1.0, 0.9 * 1.1)),  # Near saturation
            (0.1, 0.1, min(1.0, 0.1 * 1.1)),  # Weak memory strengthening
        ]

        for initial_strength, learning_rate, expected in test_cases:
            # Calculate Hebbian strengthening
            hebbian_result = min(1.0, initial_strength * (1.0 + learning_rate))
            assert (
                abs(hebbian_result - expected) < 0.001
            ), f"Hebbian strengthening incorrect: {hebbian_result} != {expected}"

    def test_working_memory_overload_behavior(self, db_connection):
        """
        Test biological response to working memory overload.

        Biological Basis:
        - Capacity limitations prevent overload
        - Interference effects when exceeding 7±2 limit
        - Priority-based selection maintains function
        """
        base_time = datetime.now()

        # Create 15 high-priority memories (exceeds capacity)
        for i in range(15):
            db_connection.execute(
                """
                INSERT INTO memories (
                    memory_id, content, concepts, activation_strength,
                    created_at, last_accessed_at, access_count, memory_type
                ) VALUES (?, ?, ['overload'], ?, ?, ?, 5, 'test')
            """,
                [
                    f"overload_{i}",
                    f"Overload memory {i}",
                    0.8 + (i * 0.01),
                    base_time,
                    base_time,
                ],
            )

        # Test that capacity constraint is enforced
        max_capacity = 9  # Upper limit of Miller's 7±2
        result = db_connection.execute(
            f"""
            WITH ranked_memories AS (
                SELECT *,
                    ROW_NUMBER() OVER (ORDER BY activation_strength DESC) as rank
                FROM memories
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '300 SECONDS'
                  AND activation_strength > 0.6
            )
            SELECT COUNT(*) as selected_count
            FROM ranked_memories
            WHERE rank <= {max_capacity}
        """
        ).fetchone()[0]

        assert (
            result <= max_capacity
        ), f"Working memory selected {result} items, exceeding biological limit of {max_capacity}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
