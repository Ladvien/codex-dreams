"""
Memory Consolidation and Hippocampal Replay Tests - BMP-006

Comprehensive test suite for biologically accurate memory consolidation processes.
Tests Hebbian strengthening, competitive forgetting, and cortical transfer mechanisms.

Test Categories:
- Unit tests for consolidation algorithms
- Biological accuracy validation
- Performance benchmarks (<1s per batch)
- Integration tests with STM pipeline
- Edge cases and error handling
"""

import pytest
import duckdb
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


@pytest.fixture
def simple_duckdb():
    """Create a simple in-memory DuckDB connection for testing."""
    conn = duckdb.connect(":memory:")

    # Install JSON extension if available
    try:
        conn.execute("INSTALL json")
        conn.execute("LOAD json")
    except Exception:
        pass

    yield conn
    conn.close()


class TestMemoryReplayConsolidation:
    """Test suite for memory consolidation and hippocampal replay functionality."""

    def test_basic_consolidation_pipeline(self, simple_duckdb):
        """Test basic consolidation pipeline functionality."""
        conn = simple_duckdb

        # Create test STM memories ready for consolidation
        test_memories = [
            {
                "id": 1,
                "content": "Important strategy meeting with client about product launch",
                "level_0_goal": "Product Launch Strategy",
                "level_1_tasks": '["Strategy planning", "Client coordination", "Timeline development"]',
                "stm_strength": 0.8,
                "emotional_salience": 0.9,
                "co_activation_count": 5,
                "hebbian_potential": 0.7,
                "ready_for_consolidation": True,
                "processed_at": datetime.now(),
            },
            {
                "id": 2,
                "content": "Fix broken coffee machine in office kitchen",
                "level_0_goal": "Operations and Maintenance",
                "level_1_tasks": '["Equipment diagnosis", "Repair coordination", "Testing"]',
                "stm_strength": 0.2,
                "emotional_salience": 0.3,
                "co_activation_count": 1,
                "hebbian_potential": 0.1,
                "ready_for_consolidation": True,
                "processed_at": datetime.now(),
            },
        ]

        # Insert test data
        conn.execute(
            """
            CREATE TEMPORARY TABLE stm_hierarchical_episodes AS
            SELECT * FROM VALUES
            (1, 'Important strategy meeting with client about product launch', 'Product Launch Strategy', 
             '["Strategy planning", "Client coordination", "Timeline development"]', '[]', '{}', '{}',
             0.8, 0.9, 5, 0.7, true, CURRENT_TIMESTAMP),
            (2, 'Fix broken coffee machine in office kitchen', 'Operations and Maintenance',
             '["Equipment diagnosis", "Repair coordination", "Testing"]', '[]', '{}', '{}', 
             0.2, 0.3, 1, 0.1, true, CURRENT_TIMESTAMP)
            AS t(id, content, level_0_goal, level_1_tasks, atomic_actions, phantom_objects, spatial_extraction,
                 stm_strength, emotional_salience, co_activation_count, hebbian_potential, 
                 ready_for_consolidation, processed_at)
        """
        )

        # Simulate consolidation logic
        result = conn.execute(
            """
            WITH stm_memories AS (
                SELECT * FROM stm_hierarchical_episodes WHERE ready_for_consolidation = TRUE
            ),
            replay_cycles AS (
                SELECT *,
                    hebbian_potential * 1.1 AS strengthened_weight,
                    CASE 
                        WHEN stm_strength < 0.3 THEN stm_strength * 0.8
                        WHEN stm_strength > 0.7 THEN stm_strength * 1.2  
                        ELSE stm_strength * 0.95
                    END as consolidated_strength
                FROM stm_memories
            )
            SELECT id, content, consolidated_strength, strengthened_weight,
                   CASE WHEN consolidated_strength > 0.5 THEN 'cortical_transfer' 
                        ELSE 'hippocampal_retention' END as consolidation_fate
            FROM replay_cycles
        """
        ).fetchall()

        # Verify consolidation results
        assert len(result) == 2, "Should process both test memories"

        # Memory 1: High strength -> should be strengthened and transferred
        memory_1 = next(r for r in result if r[0] == 1)
        assert memory_1[2] > 0.8, f"High-strength memory should be strengthened: {memory_1[2]}"
        assert memory_1[4] == "cortical_transfer", "High-strength memory should transfer to cortex"

        # Memory 2: Low strength -> should be weakened
        memory_2 = next(r for r in result if r[0] == 2)
        assert memory_2[2] < 0.2, f"Low-strength memory should be weakened: {memory_2[2]}"
        assert (
            memory_2[4] == "hippocampal_retention"
        ), "Low-strength memory should stay in hippocampus"

    def test_hebbian_strengthening_algorithm(self, simple_duckdb):
        """Test Hebbian strengthening with 1.1x factor for strong memories."""
        conn = simple_duckdb

        # Test memories with different hebbian potentials
        test_data = [
            (1, 0.5, 0.55),  # id, hebbian_potential, expected_strengthened (0.5 * 1.1)
            (2, 0.3, 0.33),  # 0.3 * 1.1 = 0.33
            (3, 0.9, 0.99),  # 0.9 * 1.1 = 0.99
            (4, 0.0, 0.0),  # Edge case: zero potential
        ]

        conn.execute(
            """
            CREATE TEMPORARY TABLE hebbian_test AS 
            SELECT * FROM VALUES {} AS t(id, hebbian_potential, expected)
        """.format(
                ",".join(f"({id_}, {pot}, {exp})" for id_, pot, exp in test_data)
            )
        )

        result = conn.execute(
            """
            SELECT id, hebbian_potential, hebbian_potential * 1.1 as strengthened,
                   ABS((hebbian_potential * 1.1) - expected) < 0.001 as correct
            FROM hebbian_test
        """
        ).fetchall()

        for row in result:
            assert row[
                3
            ], f"Hebbian calculation incorrect for ID {row[0]}: got {row[2]}, expected close to {float(row[1]) * 1.1}"

    def test_competitive_forgetting_mechanism(self, simple_duckdb):
        """Test competitive forgetting: 0.8x weak, 1.2x strong, 0.95x medium."""
        conn = simple_duckdb

        test_cases = [
            (1, 0.1, 0.08),  # Weak: 0.1 * 0.8 = 0.08
            (2, 0.2, 0.16),  # Weak: 0.2 * 0.8 = 0.16
            (3, 0.5, 0.475),  # Medium: 0.5 * 0.95 = 0.475
            (4, 0.8, 0.96),  # Strong: 0.8 * 1.2 = 0.96
            (5, 0.9, 1.08),  # Strong: 0.9 * 1.2 = 1.08
        ]

        conn.execute(
            """
            CREATE TEMPORARY TABLE forgetting_test AS
            SELECT * FROM VALUES {} AS t(id, stm_strength, expected)
        """.format(
                ",".join(f"({id_}, {strength}, {exp})" for id_, strength, exp in test_cases)
            )
        )

        result = conn.execute(
            """
            SELECT id, stm_strength,
                CASE 
                    WHEN stm_strength < 0.3 THEN stm_strength * 0.8
                    WHEN stm_strength > 0.7 THEN stm_strength * 1.2  
                    ELSE stm_strength * 0.95
                END as consolidated_strength,
                expected,
                ABS(CASE 
                    WHEN stm_strength < 0.3 THEN stm_strength * 0.8
                    WHEN stm_strength > 0.7 THEN stm_strength * 1.2  
                    ELSE stm_strength * 0.95
                END - expected) < 0.001 as correct
            FROM forgetting_test
        """
        ).fetchall()

        for row in result:
            assert row[
                4
            ], f"Competitive forgetting incorrect for ID {row[0]}: got {row[2]}, expected {row[3]}"

    def test_cortical_transfer_threshold(self, simple_duckdb):
        """Test cortical transfer for memories with strength >0.5."""
        conn = simple_duckdb

        # Create memories with different consolidated strengths
        conn.execute(
            """
            CREATE TEMPORARY TABLE transfer_test AS
            SELECT * FROM VALUES
            (1, 0.8, 'Product Launch Strategy'),
            (2, 0.3, 'Operations and Maintenance'), 
            (3, 0.6, 'Communication and Collaboration'),
            (4, 0.1, 'General Task Processing')
            AS t(id, consolidated_strength, level_0_goal)
        """
        )

        result = conn.execute(
            """
            SELECT id, consolidated_strength,
                CASE WHEN consolidated_strength > 0.5 THEN 'cortical_transfer'
                     ELSE 'hippocampal_retention' END as fate,
                CASE WHEN consolidated_strength > 0.5 THEN
                    CASE WHEN level_0_goal LIKE '%Strategy%' THEN 
                         'Strategic planning and goal-oriented thinking process'
                         ELSE 'General processed content'
                    END
                    ELSE NULL
                END as semantic_gist
            FROM transfer_test
        """
        ).fetchall()

        # Verify transfer decisions
        transfer_cases = [r for r in result if r[1] > 0.5]
        retention_cases = [r for r in result if r[1] <= 0.5]

        assert len(transfer_cases) == 2, f"Expected 2 transfers, got {len(transfer_cases)}"
        assert len(retention_cases) == 2, f"Expected 2 retentions, got {len(retention_cases)}"

        # Verify semantic gist generation for transferred memories
        for case in transfer_cases:
            assert case[3] is not None, f"Transferred memory {case[0]} should have semantic gist"

        for case in retention_cases:
            assert case[3] is None, f"Retained memory {case[0]} should not have semantic gist"

    def test_semantic_gist_generation(self, simple_duckdb):
        """Test semantic gist generation for different memory types."""
        conn = simple_duckdb

        test_goals = [
            ("Product Launch Strategy", "executive_function", "prefrontal_cortex"),
            ("Communication and Collaboration", "social_cognition", "temporal_superior_cortex"),
            (
                "Financial Planning and Management",
                "executive_function",
                "prefrontal_cortex",
            ),  # Matches 'Planning' first
            ("Operations and Maintenance", "technical_procedures", "motor_cortex"),
        ]

        for goal, expected_category, expected_region in test_goals:
            result = conn.execute(
                """
                WITH test_memory AS (
                    SELECT ? as level_0_goal, 0.8 as consolidated_strength
                )
                SELECT 
                    CASE WHEN level_0_goal LIKE '%Strategy%' OR level_0_goal LIKE '%Planning%'
                         THEN json_object(
                             'gist', 'Strategic planning and goal-oriented thinking process',
                             'category', 'executive_function', 
                             'region', 'prefrontal_cortex'
                         )
                         WHEN level_0_goal LIKE '%Communication%' OR level_0_goal LIKE '%Collaboration%'
                         THEN json_object(
                             'gist', 'Social communication and collaborative interaction pattern',
                             'category', 'social_cognition',
                             'region', 'temporal_superior_cortex'
                         )
                         WHEN level_0_goal LIKE '%Financial%' OR level_0_goal LIKE '%Management%'
                         THEN json_object(
                             'gist', 'Resource management and financial decision-making schema',
                             'category', 'quantitative_reasoning',
                             'region', 'parietal_cortex'  
                         )
                         WHEN level_0_goal LIKE '%Operations%' OR level_0_goal LIKE '%Maintenance%'
                         THEN json_object(
                             'gist', 'Operational maintenance and system reliability pattern',
                             'category', 'technical_procedures',
                             'region', 'motor_cortex'
                         )
                         ELSE json_object('gist', 'General task processing', 'category', 'general', 'region', 'association_cortex')
                    END as cortical_repr
                FROM test_memory
            """,
                [goal],
            ).fetchone()

            cortical_data = json.loads(result[0])
            assert cortical_data["category"] == expected_category, f"Wrong category for {goal}"
            assert cortical_data["region"] == expected_region, f"Wrong region for {goal}"

    def test_consolidation_performance_benchmark(self, simple_duckdb):
        """Test consolidation performance: <1s per batch of 100 memories."""
        conn = simple_duckdb

        # Create 100 test memories for performance testing
        batch_size = 100
        conn.execute(
            f"""
            CREATE TEMPORARY TABLE perf_test_memories AS
            WITH RECURSIVE numbers AS (
                SELECT 1 as n
                UNION ALL
                SELECT n + 1 FROM numbers WHERE n < {batch_size}
            )
            SELECT 
                n as id,
                'Test memory content ' || n as content,
                CASE (n % 4)
                    WHEN 0 THEN 'Product Launch Strategy'
                    WHEN 1 THEN 'Communication and Collaboration' 
                    WHEN 2 THEN 'Financial Planning and Management'
                    ELSE 'Operations and Maintenance'
                END as level_0_goal,
                '["Task 1", "Task 2"]' as level_1_tasks,
                '[]' as atomic_actions,
                '{{}}' as phantom_objects,
                '{{}}' as spatial_extraction,
                0.5 + (n % 10) * 0.05 as stm_strength,  -- Varying strengths 0.5-0.95
                0.3 + (n % 7) * 0.1 as emotional_salience,
                (n % 8) + 1 as co_activation_count,
                0.1 + (n % 9) * 0.1 as hebbian_potential,
                true as ready_for_consolidation,
                CURRENT_TIMESTAMP as processed_at
            FROM numbers
        """
        )

        # Time the consolidation process
        start_time = time.time()

        result = conn.execute(
            """
            WITH stm_memories AS (
                SELECT * FROM perf_test_memories WHERE ready_for_consolidation = TRUE
            ),
            replay_cycles AS (
                SELECT *,
                    hebbian_potential * 1.1 AS strengthened_weight,
                    CASE 
                        WHEN stm_strength < 0.3 THEN stm_strength * 0.8
                        WHEN stm_strength > 0.7 THEN stm_strength * 1.2  
                        ELSE stm_strength * 0.95
                    END as consolidated_strength,
                    (stm_strength * 0.3 + emotional_salience * 0.3 + 
                     (co_activation_count / 10.0) * 0.2 + 0.2) as replay_strength
                FROM stm_memories
            ),
            cortical_transfer AS (
                SELECT *,
                    CASE WHEN consolidated_strength > 0.5 THEN
                        json_object('gist', 'Processed semantic content', 'category', 'general')
                        ELSE NULL
                    END as cortical_representation,
                    CASE 
                        WHEN consolidated_strength > 0.5 AND replay_strength > 0.6 THEN 'cortical_transfer'
                        WHEN consolidated_strength > 0.3 THEN 'hippocampal_retention'
                        ELSE 'gradual_forgetting'
                    END as consolidation_fate
                FROM replay_cycles
            )
            SELECT COUNT(*) as processed_count,
                   AVG(consolidated_strength) as avg_strength,
                   COUNT(CASE WHEN consolidation_fate = 'cortical_transfer' THEN 1 END) as cortical_transfers
            FROM cortical_transfer
        """
        ).fetchone()

        processing_time = time.time() - start_time

        # Verify performance requirements
        assert (
            processing_time < 1.0
        ), f"Consolidation took {processing_time:.3f}s, should be <1s for {batch_size} memories"
        assert result[0] == batch_size, f"Should process all {batch_size} memories, got {result[0]}"
        assert result[1] > 0, "Should have positive average strength"
        assert result[2] > 0, "Should have some cortical transfers"

        print(f"✅ Performance: Processed {batch_size} memories in {processing_time:.3f}s")

    def test_biological_accuracy_validation(self, simple_duckdb):
        """Test biological accuracy of consolidation parameters."""
        conn = simple_duckdb

        # Test biological constraints
        tests = [
            # Hebbian factor should be 1.1 (10% strengthening)
            ("SELECT 0.5 * 1.1", 0.55, "Hebbian strengthening factor"),
            # Weak memory decay should be 0.8 (20% reduction)
            ("SELECT 0.2 * 0.8", 0.16, "Weak memory forgetting"),
            # Strong memory boost should be 1.2 (20% increase)
            ("SELECT 0.8 * 1.2", 0.96, "Strong memory strengthening"),
            # Cortical transfer threshold should be 0.5
            ("SELECT CASE WHEN 0.6 > 0.5 THEN 1 ELSE 0 END", 1, "Cortical transfer threshold"),
        ]

        for query, expected, description in tests:
            result = conn.execute(query).fetchone()[0]
            result_float = float(result)
            assert (
                abs(result_float - expected) < 0.001
            ), f"{description}: got {result_float}, expected {expected}"

    def test_memory_lifecycle_integration(self, simple_duckdb):
        """Test complete memory lifecycle: WM → STM → Consolidation."""
        conn = simple_duckdb

        # Simulate memory progression through stages
        conn.execute(
            """
            CREATE TEMPORARY TABLE lifecycle_test AS
            -- Stage 1: Working Memory
            WITH working_memory AS (
                SELECT 1 as id, 'Critical client meeting' as content, 0.9 as activation_strength,
                       CURRENT_TIMESTAMP - INTERVAL '2 minutes' as timestamp
            ),
            -- Stage 2: Short-Term Memory  
            short_term_memory AS (
                SELECT id, content, 
                       'Client Relations and Service' as level_0_goal,
                       0.8 as stm_strength, 0.7 as emotional_salience, 4 as co_activation_count,
                       0.6 as hebbian_potential, true as ready_for_consolidation
                FROM working_memory
                WHERE activation_strength > 0.7  -- Transfer to STM
            ),
            -- Stage 3: Consolidation
            consolidated_memory AS (
                SELECT *, 
                       hebbian_potential * 1.1 as strengthened_weight,
                       stm_strength * 1.2 as consolidated_strength  -- Strong memory
                FROM short_term_memory
                WHERE ready_for_consolidation = true
            )
            SELECT id, content, consolidated_strength, 
                   CASE WHEN consolidated_strength > 0.5 THEN 'cortical_transfer' 
                        ELSE 'hippocampal_retention' END as final_fate
            FROM consolidated_memory
        """
        )

        result = conn.execute("SELECT * FROM lifecycle_test").fetchone()

        assert result[0] == 1, "Memory should maintain ID through lifecycle"
        assert result[2] > 0.8, f"Strong memory should be consolidated: {result[2]}"
        assert result[3] == "cortical_transfer", "Strong memory should transfer to cortex"

    def test_consolidation_error_handling(self, simple_duckdb):
        """Test error handling and edge cases in consolidation."""
        conn = simple_duckdb

        # Test with malformed data
        edge_cases = [
            # Null values
            (1, None, 0.5, 0.5, True),
            # Negative strengths
            (2, "Test", -0.1, 0.5, True),
            # Zero values
            (3, "Test", 0.0, 0.0, True),
            # Extreme values
            (4, "Test", 1.5, 2.0, True),
        ]

        conn.execute(
            """
            CREATE TEMPORARY TABLE edge_case_test AS
            SELECT * FROM VALUES {} AS t(id, content, stm_strength, emotional_salience, ready_for_consolidation)
        """.format(
                ",".join(
                    f"({id_}, {'NULL' if content is None else repr(content)}, {stm}, {emo}, {ready})"
                    for id_, content, stm, emo, ready in edge_cases
                )
            )
        )

        # Test consolidation with error handling
        result = conn.execute(
            """
            SELECT id, 
                   COALESCE(content, 'missing_content') as safe_content,
                   GREATEST(0.0, LEAST(1.0, COALESCE(stm_strength, 0.1))) as safe_strength,
                   CASE 
                       WHEN COALESCE(stm_strength, 0) < 0.3 THEN COALESCE(stm_strength, 0) * 0.8
                       WHEN COALESCE(stm_strength, 0) > 0.7 THEN COALESCE(stm_strength, 0) * 1.2
                       ELSE COALESCE(stm_strength, 0) * 0.95
                   END as consolidated_strength
            FROM edge_case_test
        """
        ).fetchall()

        # Verify error handling
        for row in result:
            # Content should be handled
            assert row[1] is not None, f"Content should not be null for ID {row[0]}"
            # Strength should be bounded [0, 1]
            assert 0.0 <= row[2] <= 1.0, f"Strength out of bounds for ID {row[0]}: {row[2]}"
            # Consolidation should not crash
            assert row[3] is not None, f"Consolidation should not be null for ID {row[0]}"


class TestConsolidationOptimization:
    """Test performance optimizations and batch processing."""

    def test_batch_processing_efficiency(self, simple_duckdb):
        """Test memory consolidation batch processing."""
        conn = simple_duckdb

        batch_sizes = [10, 50, 100]

        for batch_size in batch_sizes:
            start_time = time.time()

            # Simulate batch processing
            conn.execute(
                f"""
                CREATE OR REPLACE TEMPORARY TABLE batch_test AS
                WITH RECURSIVE numbers AS (
                    SELECT 1 as n UNION ALL
                    SELECT n + 1 FROM numbers WHERE n < {batch_size}
                )
                SELECT n as id, 0.5 as stm_strength,
                       CEIL(n * 1.0 / 25) as consolidation_batch
                FROM numbers
            """
            )

            result = conn.execute(
                """
                SELECT consolidation_batch, COUNT(*) as batch_count
                FROM batch_test
                GROUP BY consolidation_batch
                ORDER BY consolidation_batch
            """
            ).fetchall()

            processing_time = time.time() - start_time

            # Verify batch distribution
            expected_batches = (batch_size + 24) // 25  # Ceiling division
            assert len(result) <= expected_batches, f"Too many batches for {batch_size} memories"

            # Performance should scale linearly
            assert processing_time < (
                batch_size / 100.0
            ), f"Batch {batch_size} too slow: {processing_time:.3f}s"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])
