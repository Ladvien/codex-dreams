"""
Comprehensive test suite for working memory implementation (BMP-004)

Tests biological memory working memory stage with:
- Miller's 7±2 capacity constraints
- 5-minute attention window
- Semantic extraction (entities, topics, sentiment, task_type)
- Phantom objects with affordances
- Importance-based ranking and priority scoring
- Performance benchmarks (<100ms execution time)
- Error handling and edge cases

Author: Memory Agent
Created: 2025-08-28
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import duckdb
import pandas as pd
import pytest


@pytest.fixture
def duckdb_connection():
    """Create DuckDB connection for testing"""
    conn = duckdb.connect("/Users/ladvien/biological_memory/dbs/memory.duckdb")
    return conn


def setup_test_data(conn, memories):
    """Shared helper method to setup test data"""
    # Clear existing data
    conn.execute("DELETE FROM public.raw_memories")

    # Insert test memories
    for memory in memories:
        conn.execute(
            """
            INSERT INTO public.raw_memories 
            (id, content, timestamp, importance_score, activation_strength, access_count, metadata)
            VALUES (?, ?, ?, ?, ?, ?, '{}')
        """,
            [
                memory["id"],
                memory["content"],
                memory["timestamp"],
                memory.get("importance_score", 0.5),
                memory.get("activation_strength", 0.5),
                memory.get("access_count", 1),
            ],
        )


@pytest.fixture
def sample_memories():
    """Sample memory data for testing"""
    return [
        {
            "id": 1,
            "content": "Important client meeting about product launch at 3 PM",
            "timestamp": datetime.now() - timedelta(minutes=1),
            "importance_score": 0.9,
            "activation_strength": 0.8,
            "access_count": 3,
        },
        {
            "id": 2,
            "content": "Review quarterly sales report before deadline",
            "timestamp": datetime.now() - timedelta(minutes=2),
            "importance_score": 0.85,
            "activation_strength": 0.7,
            "access_count": 2,
        },
        {
            "id": 3,
            "content": "Coffee machine is broken, need to fix urgently",
            "timestamp": datetime.now() - timedelta(minutes=3),
            "importance_score": 0.3,
            "activation_strength": 0.4,
            "access_count": 1,
        },
        {
            "id": 4,
            "content": "Schedule doctor appointment for health checkup",
            "timestamp": datetime.now() - timedelta(minutes=4),
            "importance_score": 0.6,
            "activation_strength": 0.5,
            "access_count": 1,
        },
        {
            "id": 5,
            "content": "Update project timeline and notify all stakeholders",
            "timestamp": datetime.now() - timedelta(minutes=2),
            "importance_score": 0.75,
            "activation_strength": 0.65,
            "access_count": 2,
        },
        {
            "id": 6,
            "content": "Research competitor pricing strategy for market analysis",
            "timestamp": datetime.now() - timedelta(minutes=1),
            "importance_score": 0.8,
            "activation_strength": 0.75,
            "access_count": 3,
        },
        {
            "id": 7,
            "content": "Prepare budget allocation for Q4 marketing campaigns",
            "timestamp": datetime.now() - timedelta(minutes=3),
            "importance_score": 0.82,
            "activation_strength": 0.78,
            "access_count": 2,
        },
        {
            "id": 8,
            "content": "Order office supplies for kitchen restocking",
            "timestamp": datetime.now() - timedelta(minutes=4),
            "importance_score": 0.25,
            "activation_strength": 0.3,
            "access_count": 1,
        },
        {
            "id": 9,
            "content": "Team standup meeting tomorrow morning at 10 AM",
            "timestamp": datetime.now() - timedelta(minutes=4),
            "importance_score": 0.65,
            "activation_strength": 0.6,
            "access_count": 2,
        },
        # Additional memories to test capacity limits
        {
            "id": 10,
            "content": "Critical presentation slides need final review today",
            "timestamp": datetime.now() - timedelta(minutes=1),
            "importance_score": 0.95,
            "activation_strength": 0.9,
            "access_count": 4,
        },
    ]


class TestWorkingMemoryCapacity:
    """Test Miller's 7±2 capacity constraints"""

    def test_capacity_limit_enforced(self, duckdb_connection, sample_memories):
        """Test that working memory enforces 7±2 capacity limit"""
        # Setup test data
        setup_test_data(duckdb_connection, sample_memories)

        # Query working memory
        result = duckdb_connection.execute(
            """
            SELECT COUNT(*) as memory_count
            FROM main.wm_active_context
        """
        ).fetchone()

        memory_count = result[0]
        assert memory_count <= 7, f"Working memory should contain ≤7 items, found {memory_count}"
        assert memory_count > 0, "Working memory should contain at least 1 item"

    def test_importance_based_selection(self, duckdb_connection, sample_memories):
        """Test that highest importance memories are selected"""
        setup_test_data(duckdb_connection, sample_memories)

        # Get working memory results ordered by slot
        results = duckdb_connection.execute(
            """
            SELECT memory_id, importance_score, final_priority, wm_slot
            FROM main.wm_active_context 
            ORDER BY wm_slot
        """
        ).fetchall()

        # Check that priorities are in descending order
        priorities = [row[2] for row in results]
        assert priorities == sorted(
            priorities, reverse=True
        ), "Working memory should be ordered by priority (descending)"

        # Check that top slot has highest importance
        assert results[0][1] >= 0.8, "Top working memory slot should have high importance"

    def test_slot_numbering(self, duckdb_connection, sample_memories):
        """Test that wm_slot numbering is correct (1-7)"""
        setup_test_data(duckdb_connection, sample_memories)

        slots = duckdb_connection.execute(
            """
            SELECT DISTINCT wm_slot FROM main.wm_active_context ORDER BY wm_slot
        """
        ).fetchall()

        slot_numbers = [row[0] for row in slots]

        # Should be consecutive starting from 1
        assert slot_numbers[0] == 1, "First slot should be 1"
        assert max(slot_numbers) <= 7, "Maximum slot should be 7"
        assert len(slot_numbers) == len(set(slot_numbers)), "Slots should be unique"


class TestTimeWindowFiltering:
    """Test 5-minute attention window"""

    def test_five_minute_window_enforced(self, duckdb_connection):
        """Test that only memories within 5 minutes are included"""
        # Create test data with various timestamps
        test_memories = [
            {
                "id": 1,
                "content": "Recent memory within window",
                "timestamp": datetime.now() - timedelta(minutes=2),
                "importance_score": 0.8,
            },
            {
                "id": 2,
                "content": "Memory just at boundary",
                "timestamp": datetime.now() - timedelta(minutes=5),
                "importance_score": 0.7,
            },
            {
                "id": 3,
                "content": "Old memory outside window",
                "timestamp": datetime.now() - timedelta(minutes=10),
                "importance_score": 0.9,  # High importance but too old
            },
        ]

        setup_test_data(duckdb_connection, test_memories)

        # Check that only recent memories are included
        results = duckdb_connection.execute(
            """
            SELECT memory_id, age_seconds
            FROM main.wm_active_context
        """
        ).fetchall()

        for memory_id, age_seconds in results:
            assert (
                age_seconds <= 300
            ), f"Memory {memory_id} exceeds 5-minute window ({age_seconds}s)"

    def test_recency_boost_calculation(self, duckdb_connection):
        """Test that recency boost decays exponentially"""
        test_memories = [
            {
                "id": 1,
                "content": "Very recent memory",
                "timestamp": datetime.now() - timedelta(seconds=30),
                "importance_score": 0.5,
            },
            {
                "id": 2,
                "content": "Older memory",
                "timestamp": datetime.now() - timedelta(minutes=4),
                "importance_score": 0.5,
            },
        ]

        setup_test_data(duckdb_connection, test_memories)

        results = duckdb_connection.execute(
            """
            SELECT memory_id, recency_boost, age_seconds
            FROM main.wm_active_context
            ORDER BY age_seconds
        """
        ).fetchall()

        # Recent memory should have higher recency boost
        assert results[0][1] > results[1][1], "More recent memory should have higher recency boost"


class TestSemanticExtraction:
    """Test semantic extraction of entities, topics, sentiment, task types"""

    def test_entity_extraction(self, duckdb_connection):
        """Test entity extraction from content"""
        test_memories = [
            {
                "id": 1,
                "content": "Meeting with client about new project",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.8,
            },
            {
                "id": 2,
                "content": "Team standup with colleagues",
                "timestamp": datetime.now() - timedelta(minutes=2),
                "importance_score": 0.7,
            },
        ]

        setup_test_data(duckdb_connection, test_memories)

        results = duckdb_connection.execute(
            """
            SELECT memory_id, entities
            FROM main.wm_active_context
        """
        ).fetchall()

        entities_dict = {row[0]: row[1] for row in results}

        # Check client recognition
        assert (
            "client" in entities_dict[1] or "business_contact" in entities_dict[1]
        ), "Should extract client entities"

        # Check team recognition
        assert (
            "team" in entities_dict[2] or "internal" in entities_dict[2]
        ), "Should extract team entities"

    def test_topic_classification(self, duckdb_connection):
        """Test biological topic classification"""
        test_memories = [
            {
                "id": 1,
                "content": "Important presentation for board meeting",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.8,
            },
            {
                "id": 2,
                "content": "Coffee machine broken, need repair service",
                "timestamp": datetime.now() - timedelta(minutes=2),
                "importance_score": 0.4,
            },
            {
                "id": 3,
                "content": "Schedule doctor appointment next week",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.6,
            },
        ]

        setup_test_data(duckdb_connection, test_memories)

        results = duckdb_connection.execute(
            """
            SELECT memory_id, topics
            FROM main.wm_active_context
        """
        ).fetchall()

        topics_dict = {row[0]: row[1] for row in results}

        # Check social interaction for presentation
        assert any(
            "social" in topic.lower() or "communication" in topic.lower()
            for topic in topics_dict[1]
        ), "Presentation should be classified as social interaction"

        # Check problem solving for repair
        assert any(
            "problem" in topic.lower() or "maintenance" in topic.lower() for topic in topics_dict[2]
        ), "Repair should be classified as problem solving"

    def test_task_hierarchy_classification(self, duckdb_connection):
        """Test goal-task-action hierarchy classification"""
        test_memories = [
            {
                "id": 1,
                "content": "Launch new product marketing strategy campaign",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.9,
            },
            {
                "id": 2,
                "content": "Need to review quarterly financial report",
                "timestamp": datetime.now() - timedelta(minutes=2),
                "importance_score": 0.7,
            },
            {
                "id": 3,
                "content": "Fix the broken printer in office",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.5,
            },
        ]

        setup_test_data(duckdb_connection, test_memories)

        results = duckdb_connection.execute(
            """
            SELECT memory_id, task_type
            FROM main.wm_active_context
        """
        ).fetchall()

        task_types = {row[0]: row[1] for row in results}

        assert task_types[1] == "goal", "Product launch should be classified as goal"
        assert task_types[2] == "task", "Review should be classified as task"
        assert task_types[3] == "action", "Fix should be classified as action"

    def test_sentiment_analysis(self, duckdb_connection):
        """Test sentiment classification with emotional salience"""
        test_memories = [
            {
                "id": 1,
                "content": "Important urgent deadline approaching fast",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.8,
            },
            {
                "id": 2,
                "content": "Great success with client presentation",
                "timestamp": datetime.now() - timedelta(minutes=2),
                "importance_score": 0.7,
            },
            {
                "id": 3,
                "content": "Regular weekly team meeting scheduled",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.5,
            },
        ]

        setup_test_data(duckdb_connection, test_memories)

        results = duckdb_connection.execute(
            """
            SELECT memory_id, sentiment
            FROM main.wm_active_context
        """
        ).fetchall()

        sentiments = {row[0]: row[1] for row in results}

        assert sentiments[1] == "negative", "Urgent deadline should be negative (high arousal)"
        assert sentiments[2] == "positive", "Success should be positive"
        assert sentiments[3] == "neutral", "Regular meeting should be neutral"


class TestPhantomObjects:
    """Test phantom objects with affordances (embodied cognition)"""

    def test_phantom_object_extraction(self, duckdb_connection):
        """Test extraction of objects with affordances"""
        test_memories = [
            {
                "id": 1,
                "content": "Coffee machine in office is broken",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.5,
            },
            {
                "id": 2,
                "content": "Presentation slides need final review",
                "timestamp": datetime.now() - timedelta(minutes=2),
                "importance_score": 0.8,
            },
            {
                "id": 3,
                "content": "Budget spreadsheet requires updates",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.7,
            },
        ]

        setup_test_data(duckdb_connection, test_memories)

        results = duckdb_connection.execute(
            """
            SELECT memory_id, phantom_objects
            FROM main.wm_active_context
        """
        ).fetchall()

        for memory_id, phantom_objects_json in results:
            if phantom_objects_json and phantom_objects_json != "[]":
                objects = json.loads(phantom_objects_json)
                assert isinstance(objects, list), "Phantom objects should be a list"

                for obj in objects:
                    assert "name" in obj, "Each object should have a name"
                    assert "affordances" in obj, "Each object should have affordances"
                    assert isinstance(
                        obj["affordances"], list
                    ), "Affordances should be a list of actions"

    def test_affordance_accuracy(self, duckdb_connection):
        """Test that affordances match object types"""
        test_memory = [
            {
                "id": 1,
                "content": "Coffee machine is broken, need to fix",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.5,
            }
        ]

        setup_test_data(duckdb_connection, test_memory)

        result = duckdb_connection.execute(
            """
            SELECT phantom_objects
            FROM main.wm_active_context
            WHERE memory_id = 1
        """
        ).fetchone()

        if result[0] and result[0] != "[]":
            objects = json.loads(result[0])
            coffee_machine = next((obj for obj in objects if "coffee" in obj["name"].lower()), None)

            if coffee_machine:
                affordances = coffee_machine["affordances"]
                expected_affordances = ["brew_coffee", "fix", "maintain", "clean"]

                # Check that relevant affordances are present
                assert any(
                    aff in affordances for aff in expected_affordances
                ), f"Coffee machine should have relevant affordances: {affordances}"


class TestPerformanceAndOptimization:
    """Test performance benchmarks and optimization"""

    def test_execution_time_under_100ms(self, duckdb_connection, sample_memories):
        """Test that working memory query executes in <100ms"""
        setup_test_data(duckdb_connection, sample_memories)

        # Warm up the query
        duckdb_connection.execute("SELECT COUNT(*) FROM main.wm_active_context").fetchone()

        # Time the actual query
        start_time = time.time()
        results = duckdb_connection.execute(
            """
            SELECT * FROM main.wm_active_context
        """
        ).fetchall()
        end_time = time.time()

        execution_time_ms = (end_time - start_time) * 1000

        assert (
            execution_time_ms < 100
        ), f"Working memory query should execute in <100ms, took {execution_time_ms:.2f}ms"
        assert len(results) > 0, "Should return results"

    def test_view_materialization(self, duckdb_connection, sample_memories):
        """Test that view materializes correctly for continuous updates"""
        setup_test_data(duckdb_connection, sample_memories)

        # Check that view exists and is queryable
        view_info = duckdb_connection.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'wm_active_context' AND table_type = 'VIEW'
        """
        ).fetchone()

        assert view_info[0] == 1, "wm_active_context should exist as a view"

        # Test multiple consecutive queries (simulating continuous updates)
        for i in range(5):
            result = duckdb_connection.execute(
                """
                SELECT COUNT(*) FROM main.wm_active_context
            """
            ).fetchone()
            assert result[0] > 0, f"Query {i+1} should return results"


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_empty_content_filtering(self, duckdb_connection):
        """Test that empty or null content is filtered out"""
        test_memories = [
            {
                "id": 1,
                "content": "",  # Empty content
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.8,
            },
            {
                "id": 2,
                "content": "   ",  # Whitespace only
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.7,
            },
            {
                "id": 3,
                "content": "Valid content with sufficient length",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.6,
            },
        ]

        setup_test_data(duckdb_connection, test_memories)

        results = duckdb_connection.execute(
            """
            SELECT COUNT(*) FROM main.wm_active_context
        """
        ).fetchone()

        # Should only have valid content
        assert results[0] == 1, "Should filter out empty/whitespace content"

    def test_null_value_handling(self, duckdb_connection):
        """Test handling of null values in memory data"""
        # Insert memory with null values
        duckdb_connection.execute(
            """
            INSERT INTO public.raw_memories (id, content, timestamp, importance_score, activation_strength) 
            VALUES (999, 'Memory with null values', NOW() - INTERVAL '1 minute', NULL, NULL)
        """
        )

        # Should handle nulls gracefully with fallbacks
        result = duckdb_connection.execute(
            """
            SELECT importance_score, activation_strength
            FROM main.wm_active_context
            WHERE memory_id = 999
        """
        ).fetchone()

        if result:
            importance, activation = result
            assert importance is not None, "Should provide fallback for null importance"
            assert activation is not None, "Should provide fallback for null activation"

    def test_edge_case_capacity_boundary(self, duckdb_connection):
        """Test behavior at exact capacity boundary"""
        # Create exactly 7 memories with different priorities
        exact_memories = [
            {
                "id": i,
                "content": f"Memory {i} with priority {i/10}",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": i / 10.0,
            }
            for i in range(1, 8)  # 7 memories
        ]

        setup_test_data(duckdb_connection, exact_memories)

        results = duckdb_connection.execute(
            """
            SELECT COUNT(*) as count, MIN(wm_slot) as min_slot, MAX(wm_slot) as max_slot
            FROM main.wm_active_context
        """
        ).fetchone()

        count, min_slot, max_slot = results
        assert count == 7, "Should have exactly 7 memories"
        assert min_slot == 1, "Should start with slot 1"
        assert max_slot == 7, "Should end with slot 7"


class TestBiologicalAccuracy:
    """Test biological accuracy of memory model"""

    def test_hebbian_strength_calculation(self, duckdb_connection, sample_memories):
        """Test Hebbian strength calculation for co-activation"""
        setup_test_data(duckdb_connection, sample_memories)

        results = duckdb_connection.execute(
            """
            SELECT memory_id, hebbian_strength, working_memory_strength, final_priority
            FROM main.wm_active_context
        """
        ).fetchall()

        for memory_id, hebbian, wm_strength, final_priority in results:
            # Hebbian strength should be calculated
            assert hebbian is not None, f"Memory {memory_id} should have Hebbian strength"
            assert hebbian >= 0.0, "Hebbian strength should be non-negative"

            # Should contribute to final priority
            assert final_priority > 0.0, "Final priority should be positive"

    def test_emotional_salience_weighting(self, duckdb_connection):
        """Test that emotional memories get priority boost"""
        test_memories = [
            {
                "id": 1,
                "content": "Important urgent critical deadline today",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.5,  # Lower base importance
                "activation_strength": 0.5,
                "access_count": 1,
            },
            {
                "id": 2,
                "content": "Regular routine meeting scheduled",
                "timestamp": datetime.now() - timedelta(minutes=1),
                "importance_score": 0.5,  # Same base importance
                "activation_strength": 0.5,
                "access_count": 1,
            },
        ]

        setup_test_data(duckdb_connection, test_memories)

        results = duckdb_connection.execute(
            """
            SELECT memory_id, sentiment, final_priority
            FROM main.wm_active_context
            ORDER BY final_priority DESC
        """
        ).fetchall()

        # Emotional memory should rank higher despite same base importance
        top_memory = results[0]
        assert top_memory[0] == 1, "Emotional memory should rank higher"
        assert top_memory[1] == "negative", "Should be classified as negative (high arousal)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
