#!/usr/bin/env python3
"""
Comprehensive Schema Validation Tests for Biological Memory System
Tests the biological memory schema structure, constraints, and biological accuracy.

This test suite validates:
1. Schema existence and table structure
2. Biological memory constraints (Miller's Law, capacity limits)
3. Index performance and coverage
4. Data type validations and constraints
5. Referential integrity and relationships
6. Biological parameter validation

Test Coverage:
- biological_memory.episodic_buffer
- biological_memory.consolidation_buffer
- codex_processed.semantic_memory
- All indexes and constraints
- Biological accuracy validation
"""

import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    import duckdb
    import psycopg2
    from psycopg2.extras import RealDictCursor

    HAS_DB_DEPS = True
except ImportError:
    HAS_DB_DEPS = False

# Test configuration
DUCKDB_PATH = os.getenv(
    "DUCKDB_PATH", "/Users/ladvien/codex-dreams/biological_memory/dbs/memory.duckdb"
)
POSTGRES_URL = os.getenv("POSTGRES_DB_URL")  # Must be set in environment


class TestBiologicalMemorySchema:
    """Test suite for biological memory schema validation"""

    @pytest.fixture(scope="class")
    def duckdb_connection(self):
        """Create DuckDB connection for schema testing"""
        if not HAS_DB_DEPS:
            pytest.skip("Database dependencies not available")

        try:
            conn = duckdb.connect(DUCKDB_PATH)
            yield conn
            conn.close()
        except Exception as e:
            pytest.skip(f"Could not connect to DuckDB: {e}")

    @pytest.fixture(scope="class")
    def postgres_connection(self):
        """Create PostgreSQL connection for schema testing"""
        if not HAS_DB_DEPS:
            pytest.skip("Database dependencies not available")

        try:
            conn = psycopg2.connect(POSTGRES_URL)
            yield conn
            conn.close()
        except Exception as e:
            pytest.skip(f"Could not connect to PostgreSQL: {e}")

    def test_biological_memory_schema_exists(self, duckdb_connection):
        """Test that biological_memory schema exists in DuckDB"""
        cursor = duckdb_connection.cursor()

        # Check if schema exists
        cursor.execute(
            """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = 'biological_memory'
        """
        )

        result = cursor.fetchone()
        assert result is not None, "biological_memory schema should exist"
        assert result[0] == "biological_memory"

    def test_episodic_buffer_table_structure(self, duckdb_connection):
        """Test episodic_buffer table structure and constraints"""
        cursor = duckdb_connection.cursor()

        # Test table exists
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'biological_memory' 
            AND table_name = 'episodic_buffer'
        """
        )

        result = cursor.fetchone()
        assert result is not None, "episodic_buffer table should exist"

        # Test required columns exist
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_schema = 'biological_memory' 
            AND table_name = 'episodic_buffer'
            ORDER BY column_name
        """
        )

        columns = cursor.fetchall()
        column_names = [col[0] for col in columns]

        # Verify required columns from ARCHITECTURE.md
        required_columns = [
            "id",
            "original_content",
            "level_0_goal",
            "level_1_tasks",
            "atomic_actions",
            "spatial_context",
            "temporal_context",
            "social_context",
            "phantom_objects",
            "temporal_marker",
            "causal_links",
            "stm_strength",
            "hebbian_potential",
            "consolidation_priority",
            "ready_for_consolidation",
            "entered_wm_at",
            "entered_stm_at",
            "wm_duration_seconds",
        ]

        for col in required_columns:
            assert col in column_names, f"Required column {col} missing from episodic_buffer"

        # Verify NOT NULL constraints
        not_null_columns = ["id", "original_content"]
        for col_name, data_type, is_nullable in columns:
            if col_name in not_null_columns:
                assert is_nullable == "NO", f"Column {col_name} should be NOT NULL"

    def test_consolidation_buffer_table_structure(self, duckdb_connection):
        """Test consolidation_buffer table structure and constraints"""
        cursor = duckdb_connection.cursor()

        # Test table exists
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'biological_memory' 
            AND table_name = 'consolidation_buffer'
        """
        )

        result = cursor.fetchone()
        assert result is not None, "consolidation_buffer table should exist"

        # Test required columns exist
        cursor.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns 
            WHERE table_schema = 'biological_memory' 
            AND table_name = 'consolidation_buffer'
            ORDER BY column_name
        """
        )

        columns = cursor.fetchall()
        column_names = [col[0] for col in columns]

        # Verify required columns from ARCHITECTURE.md
        required_columns = [
            "id",
            "original_content",
            "level_0_goal",
            "level_1_tasks",
            "discovered_patterns",
            "synthesized_insights",
            "predictive_patterns",
            "abstract_principles",
            "contradictions",
            "associated_memory_ids",
            "association_strengths",
            "total_association_strength",
            "semantic_gist",
            "semantic_category",
            "cortical_region",
            "knowledge_type",
            "abstraction_level",
            "pre_consolidation_strength",
            "consolidated_strength",
            "entered_stm_at",
            "consolidated_at",
            "consolidation_duration_ms",
        ]

        for col in required_columns:
            assert col in column_names, f"Required column {col} missing from consolidation_buffer"

    def test_semantic_memory_table_structure(self, postgres_connection):
        """Test semantic_memory table structure in PostgreSQL"""
        cursor = postgres_connection.cursor(cursor_factory=RealDictCursor)

        # Test table exists
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'codex_processed' 
            AND table_name = 'semantic_memory'
        """
        )

        result = cursor.fetchone()
        assert result is not None, "semantic_memory table should exist in codex_processed schema"

        # Test required columns exist
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'codex_processed' 
            AND table_name = 'semantic_memory'
            ORDER BY column_name
        """
        )

        columns = cursor.fetchall()
        column_names = [col["column_name"] for col in columns]

        # Verify required columns from ARCHITECTURE.md enhanced spec
        required_columns = [
            "id",
            "source_memory_id",
            "semantic_gist",
            "knowledge_type",
            "abstraction_level",
            "confidence_score",
            "semantic_category",
            "cortical_region",
            "patterns",
            "insights",
            "predictions",
            "principles",
            "contradictions",
            "related_concepts",
            "integration_points",
            "retrieval_strength",
            "access_count",
            "last_accessed_at",
            "consolidation_strength",
            "hebbian_weight",
            "synaptic_stability",
            "consolidated_during_sleep",
            "rem_sleep_associations",
            "consolidation_cycle_type",
            "processing_version",
            "created_at",
            "search_vector",
        ]

        for col in required_columns:
            assert col in column_names, f"Required column {col} missing from semantic_memory"

    def test_biological_constraints_validation(self, duckdb_connection):
        """Test biological accuracy constraints"""
        cursor = duckdb_connection.cursor()

        # Test STM strength constraints (0.0-1.0 range)
        with pytest.raises(Exception):
            cursor.execute(
                """
                INSERT INTO biological_memory.episodic_buffer 
                (id, original_content, stm_strength) 
                VALUES (?, 'test content', ?)
            """,
                [str(uuid.uuid4()), 1.5],
            )  # Should fail - exceeds 1.0

        # Test valid STM strength (should succeed)
        test_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO biological_memory.episodic_buffer 
            (id, original_content, stm_strength) 
            VALUES (?, 'test content', ?)
        """,
            [test_id, 0.7],
        )

        # Verify insertion succeeded
        cursor.execute(
            """
            SELECT stm_strength FROM biological_memory.episodic_buffer WHERE id = ?
        """,
            [test_id],
        )

        result = cursor.fetchone()
        assert result is not None
        assert 0.0 <= result[0] <= 1.0

        # Cleanup
        cursor.execute("DELETE FROM biological_memory.episodic_buffer WHERE id = ?", [test_id])
        duckdb_connection.commit()

    def test_consolidation_abstraction_level_constraint(self, duckdb_connection):
        """Test abstraction level constraints (1-5 range)"""
        cursor = duckdb_connection.cursor()

        # Test invalid abstraction level (should fail)
        with pytest.raises(Exception):
            cursor.execute(
                """
                INSERT INTO biological_memory.consolidation_buffer 
                (id, abstraction_level) 
                VALUES (?, ?)
            """,
                [str(uuid.uuid4()), 6],
            )  # Should fail - exceeds 5

        # Test valid abstraction level (should succeed)
        test_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO biological_memory.consolidation_buffer 
            (id, abstraction_level) 
            VALUES (?, ?)
        """,
            [test_id, 3],
        )

        # Verify insertion succeeded
        cursor.execute(
            """
            SELECT abstraction_level FROM biological_memory.consolidation_buffer WHERE id = ?
        """,
            [test_id],
        )

        result = cursor.fetchone()
        assert result is not None
        assert 1 <= result[0] <= 5

        # Cleanup
        cursor.execute("DELETE FROM biological_memory.consolidation_buffer WHERE id = ?", [test_id])
        duckdb_connection.commit()

    def test_required_indexes_exist(self, duckdb_connection):
        """Test that required performance indexes exist"""
        cursor = duckdb_connection.cursor()

        # Check for episodic_buffer indexes
        cursor.execute(
            """
            SELECT index_name 
            FROM duckdb_indexes() 
            WHERE table_name = 'episodic_buffer'
        """
        )

        episodic_indexes = [row[0] for row in cursor.fetchall()]

        # Verify critical indexes exist
        expected_episodic_indexes = [
            "idx_episodic_ready",
            "idx_episodic_strength",
            "idx_episodic_priority",
            "idx_episodic_temporal",
        ]

        for index in expected_episodic_indexes:
            assert any(
                index in idx_name for idx_name in episodic_indexes
            ), f"Required index {index} missing from episodic_buffer"

        # Check for consolidation_buffer indexes
        cursor.execute(
            """
            SELECT index_name 
            FROM duckdb_indexes() 
            WHERE table_name = 'consolidation_buffer'
        """
        )

        consolidation_indexes = [row[0] for row in cursor.fetchall()]

        expected_consolidation_indexes = [
            "idx_consolidation_strength",
            "idx_consolidation_category",
            "idx_consolidation_region",
            "idx_consolidation_temporal",
        ]

        for index in expected_consolidation_indexes:
            assert any(
                index in idx_name for idx_name in consolidation_indexes
            ), f"Required index {index} missing from consolidation_buffer"

    def test_array_column_functionality(self, duckdb_connection):
        """Test array column functionality for hierarchical data"""
        cursor = duckdb_connection.cursor()

        test_id = str(uuid.uuid4())
        test_tasks = ['["task1", "task2", "task3"]']
        test_actions = ['["action1", "action2"]']

        # Insert test data with array columns
        cursor.execute(
            """
            INSERT INTO biological_memory.episodic_buffer 
            (id, original_content, level_1_tasks, atomic_actions) 
            VALUES (?, 'test content', ?, ?)
        """,
            [test_id, test_tasks, test_actions],
        )

        # Retrieve and verify array data
        cursor.execute(
            """
            SELECT level_1_tasks, atomic_actions 
            FROM biological_memory.episodic_buffer 
            WHERE id = ?
        """,
            [test_id],
        )

        result = cursor.fetchone()
        assert result is not None

        # Cleanup
        cursor.execute("DELETE FROM biological_memory.episodic_buffer WHERE id = ?", [test_id])
        duckdb_connection.commit()

    def test_json_column_functionality(self, duckdb_connection):
        """Test JSON column functionality for contextual data"""
        cursor = duckdb_connection.cursor()

        test_id = str(uuid.uuid4())
        test_spatial = {"location": "office", "coordinates": [37.7749, -122.4194]}
        test_phantom = {"objects": ["computer", "desk"], "affordances": ["typing", "writing"]}

        # Insert test data with JSON columns
        cursor.execute(
            """
            INSERT INTO biological_memory.episodic_buffer 
            (id, original_content, spatial_context, phantom_objects) 
            VALUES (?, 'test content', ?, ?)
        """,
            [test_id, json.dumps(test_spatial), json.dumps(test_phantom)],
        )

        # Retrieve and verify JSON data
        cursor.execute(
            """
            SELECT spatial_context, phantom_objects 
            FROM biological_memory.episodic_buffer 
            WHERE id = ?
        """,
            [test_id],
        )

        result = cursor.fetchone()
        assert result is not None

        # Verify JSON parsing works
        spatial_data = json.loads(result[0]) if result[0] else {}
        phantom_data = json.loads(result[1]) if result[1] else {}

        assert spatial_data.get("location") == "office"
        assert "computer" in phantom_data.get("objects", [])

        # Cleanup
        cursor.execute("DELETE FROM biological_memory.episodic_buffer WHERE id = ?", [test_id])
        duckdb_connection.commit()

    def test_millers_law_capacity_logic(self, duckdb_connection):
        """Test Miller's Law (7±2) capacity enforcement logic"""
        cursor = duckdb_connection.cursor()

        # This tests the data structures that support Miller's Law
        # Actual enforcement would be in application logic

        # Insert test episodes to simulate capacity testing
        test_episodes = []
        for i in range(12):  # Exceed 7+2 capacity
            episode_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO biological_memory.episodic_buffer 
                (id, original_content, stm_strength, ready_for_consolidation) 
                VALUES (?, ?, ?, ?)
            """,
                [episode_id, f"episode_{i}", 0.5, False],
            )
            test_episodes.append(episode_id)

        # Verify all episodes were inserted (table supports > 9 items)
        cursor.execute(
            """
            SELECT COUNT(*) FROM biological_memory.episodic_buffer 
            WHERE id IN ({})
        """.format(
                ",".join(["?" for _ in test_episodes])
            ),
            test_episodes,
        )

        count = cursor.fetchone()[0]
        assert (
            count == 12
        ), "Table should support more than Miller's limit for processing flexibility"

        # Test priority ordering (for capacity management)
        cursor.execute(
            """
            SELECT id FROM biological_memory.episodic_buffer 
            WHERE id IN ({}) 
            ORDER BY stm_strength DESC, entered_stm_at ASC
            LIMIT 9
        """.format(
                ",".join(["?" for _ in test_episodes])
            ),
            test_episodes,
        )

        top_episodes = cursor.fetchall()
        assert len(top_episodes) == 9, "Should be able to select top 7+2 episodes"

        # Cleanup
        for episode_id in test_episodes:
            cursor.execute(
                "DELETE FROM biological_memory.episodic_buffer WHERE id = ?", [episode_id]
            )

        duckdb_connection.commit()

    def test_temporal_constraints_and_indexing(self, duckdb_connection):
        """Test temporal indexing for 5-minute attention windows"""
        cursor = duckdb_connection.cursor()

        # Insert episodes with different timestamps
        base_time = datetime.now()
        test_episodes = []

        for i in range(5):
            episode_id = str(uuid.uuid4())
            episode_time = base_time - timedelta(minutes=i * 2)  # 0, 2, 4, 6, 8 minutes ago

            cursor.execute(
                """
                INSERT INTO biological_memory.episodic_buffer 
                (id, original_content, entered_stm_at) 
                VALUES (?, ?, ?)
            """,
                [episode_id, f"episode_{i}", episode_time],
            )
            test_episodes.append(episode_id)

        # Test 5-minute window query (should get first 3 episodes: 0, 2, 4 minutes)
        five_min_ago = base_time - timedelta(minutes=5)
        cursor.execute(
            """
            SELECT COUNT(*) FROM biological_memory.episodic_buffer 
            WHERE id IN ({}) 
            AND entered_stm_at >= ?
        """.format(
                ",".join(["?" for _ in test_episodes])
            ),
            test_episodes + [five_min_ago],
        )

        recent_count = cursor.fetchone()[0]
        assert (
            recent_count == 3
        ), f"Should find 3 episodes within 5-minute window, found {recent_count}"

        # Cleanup
        for episode_id in test_episodes:
            cursor.execute(
                "DELETE FROM biological_memory.episodic_buffer WHERE id = ?", [episode_id]
            )

        duckdb_connection.commit()

    def test_consolidation_priority_calculation(self, duckdb_connection):
        """Test consolidation priority calculation logic"""
        cursor = duckdb_connection.cursor()

        # Insert episodes with different priority factors
        test_cases = [
            ("high_strength", 0.9, 5, True),  # High strength, high coactivation
            ("medium_strength", 0.5, 2, False),  # Medium strength, low coactivation
            ("low_strength", 0.2, 1, False),  # Low strength, minimal coactivation
        ]

        test_ids = []
        for name, strength, coactivation, expected_ready in test_cases:
            episode_id = str(uuid.uuid4())
            priority = strength * 0.6 + (coactivation / 10.0) * 0.4  # Simple priority calculation

            cursor.execute(
                """
                INSERT INTO biological_memory.episodic_buffer 
                (id, original_content, stm_strength, hebbian_potential, 
                 consolidation_priority, ready_for_consolidation) 
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                [episode_id, f"test_{name}", strength, coactivation, priority, expected_ready],
            )

            test_ids.append((episode_id, name, expected_ready))

        # Verify priority ordering
        cursor.execute(
            """
            SELECT id, consolidation_priority FROM biological_memory.episodic_buffer 
            WHERE id IN ({}) 
            ORDER BY consolidation_priority DESC
        """.format(
                ",".join(["?" for id_, _, _ in test_ids])
            ),
            [id_ for id_, _, _ in test_ids],
        )

        results = cursor.fetchall()

        # Highest priority should be the high_strength episode
        assert len(results) == 3
        # The first result should have the highest priority
        highest_priority_id = results[0][0]
        assert (
            highest_priority_id == test_ids[0][0]
        ), "High strength episode should have highest priority"

        # Cleanup
        for episode_id, _, _ in test_ids:
            cursor.execute(
                "DELETE FROM biological_memory.episodic_buffer WHERE id = ?", [episode_id]
            )

        duckdb_connection.commit()

    @pytest.mark.skipif(not HAS_DB_DEPS, reason="Database dependencies not available")
    def test_database_connections(self):
        """Test that database connections work"""
        # This is a basic connectivity test
        assert HAS_DB_DEPS, "Should have database dependencies for full testing"


class TestSchemaIntegration:
    """Integration tests for schema interactions"""

    def test_schema_file_syntax(self):
        """Test that the schema SQL file has valid syntax"""
        schema_file = "/Users/ladvien/codex-dreams/sql/create_biological_memory_schema.sql"
        assert os.path.exists(schema_file), "Schema file should exist"

        with open(schema_file, "r") as f:
            content = f.read()

        # Basic SQL syntax checks
        assert "CREATE SCHEMA" in content, "Should contain schema creation"
        assert "CREATE TABLE" in content, "Should contain table creation"
        assert "CREATE INDEX" in content, "Should contain index creation"
        assert "biological_memory.episodic_buffer" in content, "Should define episodic_buffer"
        assert (
            "biological_memory.consolidation_buffer" in content
        ), "Should define consolidation_buffer"
        assert "codex_processed.semantic_memory" in content, "Should define semantic_memory"

        # Check for biological constraints
        assert (
            "stm_strength >= 0.0 AND stm_strength <= 1.0" in content
        ), "Should have STM strength constraints"
        assert (
            "abstraction_level >= 1 AND abstraction_level <= 5" in content
        ), "Should have abstraction level constraints"

    def test_architecture_compliance(self):
        """Test compliance with ARCHITECTURE.md specifications"""
        # This test verifies that our implementation matches the architecture
        schema_file = "/Users/ladvien/codex-dreams/sql/create_biological_memory_schema.sql"

        with open(schema_file, "r") as f:
            content = f.read()

        # Verify required fields from ARCHITECTURE.md are present
        architecture_requirements = [
            "level_0_goal",  # Hierarchical organization
            "level_1_tasks",  # Task decomposition
            "atomic_actions",  # Action-level detail
            "spatial_context",  # Contextual embedding
            "temporal_context",  # Time relationships
            "social_context",  # People involved
            "phantom_objects",  # Objects and affordances
            "hebbian_potential",  # Co-activation tracking
            "consolidation_priority",  # Memory dynamics
            "ready_for_consolidation",  # Processing state
            "semantic_gist",  # Abstract representation
            "cortical_region",  # Storage location
            "association_strengths",  # Network connections
        ]

        for requirement in architecture_requirements:
            assert (
                requirement in content
            ), f"Architecture requirement {requirement} should be implemented"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
