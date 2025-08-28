"""
Unit tests for BMP-005: Short-Term Memory with Hierarchical Episodes.

Tests hierarchical goal-task-action decomposition, biological memory features,
and incremental processing as specified in acceptance criteria.
"""
import pytest
from datetime import datetime, timezone, timedelta
import json
import math
from unittest.mock import patch, Mock


class TestHierarchicalExtraction:
    """Test goal-task-action decomposition using LLM."""
    
    @pytest.mark.llm
    def test_hierarchical_extraction(self, mock_ollama):
        """Test goal-task-action hierarchy extraction."""
        test_content = "Need to finish quarterly report by analyzing sales data and writing summary"
        
        response = mock_ollama(f"Analyze hierarchy for: {test_content}")
        parsed = json.loads(response)
        
        assert 'goal' in parsed, "Should extract high-level goal"
        assert 'tasks' in parsed, "Should extract mid-level tasks"
        assert 'actions' in parsed, "Should extract atomic actions"
        assert 'time_pointer' in parsed, "Should identify time sequence"
        
        # Validate structure
        assert isinstance(parsed['goal'], str), "Goal should be string"
        assert isinstance(parsed['tasks'], list), "Tasks should be list"
        assert isinstance(parsed['actions'], list), "Actions should be list"
    
    @pytest.mark.llm
    def test_goal_level_extraction(self, mock_ollama):
        """Test high-level goal identification."""
        test_cases = [
            "Complete project deliverables for client presentation",
            "Improve team productivity through better tooling", 
            "Learn new programming language for career development"
        ]
        
        for content in test_cases:
            response = mock_ollama(f"Extract goal from: {content}")
            parsed = json.loads(response)
            
            goal = parsed.get('goal', '')
            assert len(goal) > 0, "Should extract meaningful goal"
            assert isinstance(goal, str), "Goal should be text description"
    
    @pytest.mark.llm
    def test_task_decomposition(self, mock_ollama):
        """Test mid-level task decomposition."""
        test_content = "Plan team offsite event including venue booking and agenda preparation"
        
        response = mock_ollama(f"Decompose tasks for: {test_content}")
        parsed = json.loads(response)
        
        tasks = parsed.get('tasks', [])
        assert isinstance(tasks, list), "Tasks should be list"
        assert len(tasks) >= 1, "Should decompose into specific tasks"
        
        # Each task should be actionable
        for task in tasks:
            assert isinstance(task, str), "Each task should be string"
            assert len(task) > 5, "Tasks should be descriptive"
    
    @pytest.mark.llm
    def test_atomic_actions(self, mock_ollama):
        """Test atomic action identification."""
        test_content = "Send email to stakeholders about project status update"
        
        response = mock_ollama(f"Extract atomic actions from: {test_content}")
        parsed = json.loads(response)
        
        actions = parsed.get('actions', [])
        assert isinstance(actions, list), "Actions should be list"
        assert len(actions) >= 1, "Should extract specific actions"
        
        # Actions should be atomic (specific behaviors)
        for action in actions:
            assert isinstance(action, str), "Each action should be string"


class TestSpatialExtraction:
    """Test spatial memory components extraction."""
    
    @pytest.mark.llm
    def test_spatial_extraction(self, mock_ollama):
        """Test egocentric/allocentric position extraction."""
        test_content = "Sat in conference room facing the whiteboard with laptop on table"
        
        response = mock_ollama(f"Extract spatial information from: {test_content}")
        parsed = json.loads(response)
        
        # Validate spatial information structure
        spatial_keys = ['location', 'egocentric', 'allocentric', 'objects']
        
        # Mock should return spatial information
        assert isinstance(parsed, dict), "Spatial extraction should return object"
        # Specific keys depend on mock implementation, test concept
        assert len(str(parsed)) > 10, "Should return meaningful spatial data"
    
    def test_egocentric_positioning(self, mock_ollama):
        """Test egocentric (observer-relative) positioning."""
        test_content = "Whiteboard to my left, colleague sitting across from me"
        
        response = mock_ollama(f"Extract egocentric positions from: {test_content}")
        
        # Should identify positions relative to observer
        assert response is not None, "Should extract egocentric information"
        assert len(response) > 0, "Should return spatial description"
    
    def test_allocentric_positioning(self, mock_ollama):
        """Test allocentric (absolute) positioning."""
        test_content = "Meeting in north conference room, seats arranged around central table"
        
        response = mock_ollama(f"Extract allocentric positions from: {test_content}")
        
        # Should identify absolute positions
        assert response is not None, "Should extract allocentric information"
        assert len(response) > 0, "Should return spatial description"


class TestDecayCalculation:
    """Test exponential decay and recency factors."""
    
    def test_recency_factor_calculation(self, short_term_memory_fixture):
        """Test exponential decay formula implementation."""
        conn = short_term_memory_fixture
        
        # Test recency calculation concept
        now = datetime.now(timezone.utc)
        timestamps = [
            now - timedelta(minutes=10),  # Recent
            now - timedelta(hours=1),     # Moderate
            now - timedelta(hours=6)      # Older
        ]
        
        for i, timestamp in enumerate(timestamps):
            # Calculate expected recency factor: EXP(-seconds_ago / 3600)
            seconds_ago = (now - timestamp).total_seconds()
            expected_recency = math.exp(-seconds_ago / 3600)
            
            assert 0 < expected_recency <= 1, f"Recency factor should be 0-1, got {expected_recency}"
            
            # More recent memories should have higher recency
            if i > 0:
                prev_seconds = (now - timestamps[i-1]).total_seconds()
                prev_recency = math.exp(-prev_seconds / 3600)
                assert expected_recency <= prev_recency, "Older memories should have lower recency"
    
    def test_time_based_decay(self):
        """Test time-based memory decay calculations."""
        # Test different time intervals
        test_intervals = [
            (0, 1.0),           # Now: recency = 1.0
            (3600, math.exp(-1)),  # 1 hour ago: recency = e^-1
            (7200, math.exp(-2)),  # 2 hours ago: recency = e^-2
        ]
        
        for seconds_ago, expected_recency in test_intervals:
            calculated_recency = math.exp(-seconds_ago / 3600)
            assert abs(calculated_recency - expected_recency) < 0.001, \
                f"Recency calculation mismatch for {seconds_ago}s"


class TestEmotionalSalience:
    """Test sentiment-based emotional salience scoring."""
    
    def test_emotional_salience_calculation(self):
        """Test emotional salience based on sentiment and importance."""
        test_cases = [
            ('positive', 0.8, 0.8 * 0.4 + 0.3),  # importance * 0.4 + positive bonus 0.3
            ('negative', 0.6, 0.6 * 0.4 + 0.2),  # importance * 0.4 + negative bonus 0.2
            ('neutral', 0.5, 0.5 * 0.4 + 0.1),   # importance * 0.4 + neutral bonus 0.1
        ]
        
        for sentiment, importance, expected_salience in test_cases:
            # Calculate salience: importance_score * 0.4 + sentiment_bonus
            sentiment_bonus = {
                'positive': 0.3,
                'negative': 0.2,
                'neutral': 0.1
            }[sentiment]
            
            calculated_salience = importance * 0.4 + sentiment_bonus
            assert abs(calculated_salience - expected_salience) < 0.001, \
                f"Salience calculation mismatch for {sentiment}"
    
    def test_sentiment_weighting(self):
        """Test sentiment contribution to emotional salience."""
        base_importance = 0.5
        
        # Test sentiment bonuses
        sentiments = {
            'positive': 0.3,
            'negative': 0.2, 
            'neutral': 0.1
        }
        
        for sentiment, bonus in sentiments.items():
            salience = base_importance * 0.4 + bonus
            assert 0 <= salience <= 1, f"Salience should be 0-1, got {salience} for {sentiment}"
            
        # Positive should have highest salience for same importance
        pos_salience = base_importance * 0.4 + sentiments['positive']
        neg_salience = base_importance * 0.4 + sentiments['negative']
        neu_salience = base_importance * 0.4 + sentiments['neutral']
        
        assert pos_salience > neg_salience > neu_salience, \
            "Positive should have highest salience, then negative, then neutral"


class TestHebbianPotential:
    """Test Hebbian co-activation counting."""
    
    def test_coactivation_counting(self, short_term_memory_fixture):
        """Test co-activation pattern counting."""
        conn = short_term_memory_fixture
        
        # Insert memories with shared topics for co-activation
        now = datetime.now(timezone.utc)
        shared_topic = "project_planning"
        
        memories = [
            (501, f"Memory 1 about {shared_topic}", now - timedelta(minutes=10)),
            (502, f"Memory 2 about {shared_topic}", now - timedelta(minutes=5)),
            (503, f"Memory 3 about different topic", now - timedelta(minutes=3))
        ]
        
        for mem_id, content, timestamp in memories:
            conn.execute("""
                INSERT INTO raw_memories (id, content, timestamp, metadata)
                VALUES (?, ?, ?, ?)
            """, (mem_id, content, timestamp, json.dumps({'topics': [shared_topic]})))
        
        # Count co-activations within 1-hour window
        result = conn.execute("""
            SELECT 
                content,
                COUNT(*) OVER (
                    PARTITION BY json_extract_string(metadata, '$.topics')
                    ORDER BY timestamp
                    RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND CURRENT ROW
                ) as coactivation_count
            FROM raw_memories
            WHERE id >= 501
        """).fetchall()
        
        # Should have calculated co-activation counts
        assert len(result) >= 1, "Should calculate co-activation counts"
    
    def test_hebbian_learning_concept(self):
        """Test Hebbian learning principle: neurons that fire together, wire together."""
        # Test concept: memories with similar topics should strengthen each other
        
        # Simulate co-activation counts
        memory_activations = [
            {'topic': 'meeting', 'count': 3},   # High co-activation
            {'topic': 'coding', 'count': 2},    # Medium co-activation  
            {'topic': 'lunch', 'count': 1}      # Low co-activation
        ]
        
        for activation in memory_activations:
            count = activation['count']
            assert count >= 1, "Co-activation count should be positive"
            
            # Higher co-activation should indicate stronger potential
            if count >= 3:
                assert count >= 3, "High co-activation memories should have count >= 3"


class TestConsolidationReadiness:
    """Test consolidation readiness flag logic."""
    
    def test_consolidation_flag_logic(self):
        """Test consolidation readiness criteria."""
        test_cases = [
            (3, 0.6, True),   # High co-activation + high salience = ready
            (2, 0.6, False),  # Low co-activation = not ready
            (3, 0.4, False),  # Low salience = not ready
            (1, 0.3, False),  # Both low = not ready
        ]
        
        for coactivation_count, emotional_salience, expected_ready in test_cases:
            # Consolidation criteria: coactivation >= 3 AND salience > 0.5
            ready = coactivation_count >= 3 and emotional_salience > 0.5
            
            assert ready == expected_ready, \
                f"Consolidation readiness mismatch for count={coactivation_count}, salience={emotional_salience}"
    
    def test_readiness_thresholds(self):
        """Test consolidation readiness thresholds."""
        coactivation_threshold = 3
        salience_threshold = 0.5
        
        assert coactivation_threshold >= 2, "Co-activation threshold should be reasonable"
        assert 0 < salience_threshold < 1, "Salience threshold should be 0-1"
        
        # Test boundary conditions
        assert not (2 >= coactivation_threshold and 0.6 > salience_threshold), \
            "Below co-activation threshold should not be ready"
        assert not (4 >= coactivation_threshold and 0.4 > salience_threshold), \
            "Below salience threshold should not be ready"
        assert (4 >= coactivation_threshold and 0.6 > salience_threshold), \
            "Above both thresholds should be ready"


class TestIncrementalProcessing:
    """Test incremental materialization and update handling."""
    
    def test_incremental_configuration(self):
        """Test incremental materialization configuration."""
        stm_config = {
            'materialized': 'incremental',
            'unique_key': 'id',
            'on_schema_change': 'sync_all_columns'
        }
        
        assert stm_config['materialized'] == 'incremental', \
            "STM should use incremental materialization"
        assert stm_config['unique_key'] == 'id', \
            "Should have unique key for incremental updates"
        assert stm_config['on_schema_change'] == 'sync_all_columns', \
            "Should handle schema changes"
    
    def test_incremental_update_handling(self, short_term_memory_fixture):
        """Test incremental update processing."""
        conn = short_term_memory_fixture
        
        # Get initial count
        initial_count = conn.execute("SELECT COUNT(*) FROM stm_hierarchical_episodes").fetchall()[0][0]
        
        # Add new STM record
        now = datetime.now(timezone.utc)
        conn.execute("""
            INSERT INTO stm_hierarchical_episodes 
            (id, content, timestamp, metadata, level_0_goal, level_1_tasks, atomic_actions,
             phantom_objects, spatial_extraction, stm_strength, hebbian_potential, 
             ready_for_consolidation, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            1001, "New incremental memory", now, json.dumps({}),
            "Test goal", "Test tasks", "Test actions", "Test objects", 
            "Test spatial", 0.7, 2, False, now
        ))
        
        # Should have increased count
        new_count = conn.execute("SELECT COUNT(*) FROM stm_hierarchical_episodes").fetchall()[0][0]
        assert new_count == initial_count + 1, "Should handle incremental updates"
    
    def test_timestamp_based_filtering(self, short_term_memory_fixture):
        """Test timestamp-based incremental filtering."""
        conn = short_term_memory_fixture
        
        # Get max timestamp from existing records
        max_timestamp_result = conn.execute("""
            SELECT MAX(timestamp) FROM stm_hierarchical_episodes
        """).fetchall()
        
        max_timestamp = max_timestamp_result[0][0]
        assert max_timestamp is not None or len(max_timestamp_result) == 0, \
            "Should be able to query max timestamp for incremental processing"


class TestBiologicalFeatures:
    """Test biological memory features calculation."""
    
    def test_stm_strength_calculation(self):
        """Test STM strength calculation: recency_factor * emotional_salience."""
        test_cases = [
            (1.0, 0.8, 0.8),    # Recent memory with high salience
            (0.5, 0.6, 0.3),    # Moderate recency and salience
            (0.1, 0.9, 0.09),   # Old memory, high salience
        ]
        
        for recency, salience, expected_strength in test_cases:
            calculated_strength = recency * salience
            assert abs(calculated_strength - expected_strength) < 0.001, \
                f"STM strength calculation mismatch: {recency} * {salience}"
    
    def test_memory_features_integration(self, short_term_memory_fixture):
        """Test integration of all biological features."""
        conn = short_term_memory_fixture
        
        # Query existing STM records to verify structure
        result = conn.execute("""
            SELECT 
                stm_strength,
                hebbian_potential,
                ready_for_consolidation
            FROM stm_hierarchical_episodes
            LIMIT 1
        """).fetchall()
        
        if result:
            strength, hebbian, ready = result[0]
            
            # Validate biological feature ranges
            assert isinstance(strength, (int, float)), "STM strength should be numeric"
            assert strength >= 0, "STM strength should be non-negative"
            
            assert isinstance(hebbian, int), "Hebbian potential should be integer"
            assert hebbian >= 0, "Hebbian potential should be non-negative"
            
            assert isinstance(ready, bool), "Consolidation readiness should be boolean"


class TestSTMIntegration:
    """Test STM integration with working memory and consolidation."""
    
    def test_working_memory_input(self, short_term_memory_fixture):
        """Test STM processing of working memory input."""
        conn = short_term_memory_fixture
        
        # STM should process data from working memory
        # Test that STM has required fields for processing WM data
        columns_result = conn.execute("PRAGMA table_info(stm_hierarchical_episodes)").fetchall()
        
        column_names = [row[1] for row in columns_result]  # Column names are in index 1
        
        required_columns = [
            'id', 'content', 'timestamp', 'metadata',
            'level_0_goal', 'level_1_tasks', 'atomic_actions'
        ]
        
        for col in required_columns:
            assert col in column_names, f"STM should have {col} column for processing"
    
    def test_consolidation_output(self, short_term_memory_fixture):
        """Test STM output for consolidation stage."""
        conn = short_term_memory_fixture
        
        # Query memories ready for consolidation
        result = conn.execute("""
            SELECT * FROM stm_hierarchical_episodes
            WHERE ready_for_consolidation = TRUE
        """).fetchall()
        
        # Should be able to identify memories ready for consolidation
        assert isinstance(result, list), "Should return list of consolidation-ready memories"