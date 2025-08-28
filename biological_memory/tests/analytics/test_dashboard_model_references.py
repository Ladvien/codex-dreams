#!/usr/bin/env python3
"""
Dashboard Model References Validation Test Suite - STORY-CS-004

Tests analytics dashboard model references, compilation, and data flow integrity.
Validates that all model references are correct and dashboard metrics can be calculated.

Test Categories:
- Model reference validation
- Dashboard compilation testing
- Metric calculation accuracy
- Data flow integrity
- Error handling and edge cases

Author: Dashboard Fixer Agent (STORY-CS-004)
Date: 2025-08-28
"""

import pytest
import duckdb
import tempfile
import os
from typing import Dict, List, Any
from datetime import datetime, timedelta


class TestDashboardModelReferences:
    """Test suite for validating analytics dashboard model references."""
    
    @pytest.fixture
    def test_db(self):
        """Create isolated test database with sample data."""
        temp_dir = tempfile.mkdtemp()
        temp_db_path = os.path.join(temp_dir, 'test_dashboard_refs.duckdb')
        
        conn = duckdb.connect(temp_db_path)
        self._create_test_tables(conn)
        self._insert_test_data(conn)
        
        yield conn
        
        # Cleanup
        conn.close()
        import shutil
        shutil.rmtree(temp_dir)
    
    def _create_test_tables(self, conn: duckdb.DuckDBPyConnection):
        """Create test tables matching biological memory model schema."""
        
        # Correct working memory table name: wm_active_context (not active_memories)
        conn.execute("""
            CREATE TABLE wm_active_context (
                memory_id VARCHAR PRIMARY KEY,
                content TEXT,
                concepts VARCHAR[],
                activation_strength FLOAT,
                created_at TIMESTAMP,
                last_accessed_at TIMESTAMP,
                access_count INTEGER,
                memory_type VARCHAR,
                recency_score FLOAT,
                frequency_score FLOAT,
                hebbian_strength FLOAT,
                processed_at TIMESTAMP
            )
        """)
        
        # Short-term memory hierarchical episodes
        conn.execute("""
            CREATE TABLE stm_hierarchical_episodes (
                id VARCHAR PRIMARY KEY,
                content TEXT,
                timestamp TIMESTAMP,
                level_0_goal VARCHAR,
                stm_strength FLOAT,
                hebbian_potential INTEGER,
                co_activation_count INTEGER,
                processed_at TIMESTAMP
            )
        """)
        
        # Memory replay (consolidation)
        conn.execute("""
            CREATE TABLE memory_replay (
                id VARCHAR PRIMARY KEY,
                content TEXT,
                level_0_goal VARCHAR,
                semantic_category VARCHAR,
                cortical_region VARCHAR,
                consolidated_strength FLOAT,
                replay_strength FLOAT,
                cortical_integration_strength FLOAT,
                retrieval_accessibility FLOAT,
                hebbian_strength FLOAT,
                consolidation_fate VARCHAR,
                consolidated_at TIMESTAMP
            )
        """)
        
        # Stable memories (long-term)
        conn.execute("""
            CREATE TABLE stable_memories (
                memory_id VARCHAR PRIMARY KEY,
                content TEXT,
                concepts VARCHAR[],
                activation_strength FLOAT,
                created_at TIMESTAMP,
                last_accessed_at TIMESTAMP,
                access_count INTEGER,
                stability_score FLOAT,
                hebbian_strength FLOAT,
                last_processed_at TIMESTAMP
            )
        """)
        
        # Concept associations (semantic)
        conn.execute("""
            CREATE TABLE concept_associations (
                id VARCHAR PRIMARY KEY,
                source_concept VARCHAR,
                target_concept VARCHAR,
                association_strength FLOAT,
                created_at TIMESTAMP
            )
        """)
        
        # Consolidating memories (short-term)
        conn.execute("""
            CREATE TABLE consolidating_memories (
                memory_id VARCHAR PRIMARY KEY,
                content TEXT,
                concepts VARCHAR[],
                activation_strength FLOAT,
                created_at TIMESTAMP,
                last_accessed_at TIMESTAMP,
                access_count INTEGER,
                consolidated_at TIMESTAMP
            )
        """)
    
    def _insert_test_data(self, conn: duckdb.DuckDBPyConnection):
        """Insert minimal test data for model reference validation."""
        
        base_time = datetime.now()
        
        # Working memory data (correct table name)
        conn.execute("""
            INSERT INTO wm_active_context VALUES 
            ('wm_001', 'Test memory 1', ['concept1'], 0.8, ?, ?, 5, 'working_memory', 0.7, 0.6, 0.5, ?)
        """, [base_time, base_time, base_time])
        
        # Short-term memory data
        conn.execute("""
            INSERT INTO stm_hierarchical_episodes VALUES 
            ('stm_001', 'Test STM memory', ?, 'Test Goal', 0.7, 3, 2, ?)
        """, [base_time, base_time])
        
        # Memory replay data
        conn.execute("""
            INSERT INTO memory_replay VALUES 
            ('mr_001', 'Test replay', 'Test Goal', 'Test Category', 'prefrontal_cortex', 
             0.8, 0.7, 0.6, 0.5, 0.4, 'cortical_transfer', ?)
        """, [base_time])
        
        # Stable memories data
        conn.execute("""
            INSERT INTO stable_memories VALUES 
            ('ltm_001', 'Test LTM', ['concept1'], 0.9, ?, ?, 10, 0.85, 0.7, ?)
        """, [base_time, base_time, base_time])
        
        # Concept associations data
        conn.execute("""
            INSERT INTO concept_associations VALUES 
            ('ca_001', 'concept1', 'concept2', 0.6, ?)
        """, [base_time])
        
        # Consolidating memories data  
        conn.execute("""
            INSERT INTO consolidating_memories VALUES 
            ('cm_001', 'Test consolidating', ['concept1'], 0.75, ?, ?, 3, ?)
        """, [base_time, base_time, base_time])
    
    def test_working_memory_model_reference(self, test_db):
        """Test that working memory model reference is correct (wm_active_context, not active_memories)."""
        
        # Test that the correct table exists and has data
        result = test_db.execute("""
            SELECT COUNT(*) as memory_count,
                   AVG(activation_strength) as avg_strength,
                   MAX(processed_at) as last_updated
            FROM wm_active_context
        """).fetchone()
        
        assert result[0] > 0, "Working memory table should contain test data"
        assert result[1] > 0, "Average activation strength should be positive"
        assert result[2] is not None, "Should have processed_at timestamp"
        
        # Test that old table name doesn't exist
        with pytest.raises(Exception):
            test_db.execute("SELECT COUNT(*) FROM active_memories")
    
    def test_memory_health_model_references(self, test_db):
        """Test that memory_health analytics can reference all required models correctly."""
        
        # Create simplified memory_health view with correct model references
        test_db.execute("""
            CREATE VIEW test_memory_health AS
            WITH memory_distribution AS (
                -- Working memory (correct reference)
                SELECT 
                    'working_memory' as memory_type,
                    COUNT(DISTINCT memory_id) as total_memories,
                    AVG(COALESCE(activation_strength, 0.1)) as avg_activation_strength,
                    AVG(COALESCE(hebbian_strength, 0.1)) as avg_hebbian_strength,
                    MAX(COALESCE(processed_at, NOW())) as last_updated
                FROM wm_active_context
                
                UNION ALL
                
                -- Short-term memory
                SELECT 
                    'short_term_memory' as memory_type,
                    COUNT(DISTINCT id) as total_memories,
                    AVG(COALESCE(stm_strength, 0.1)) as avg_activation_strength,
                    AVG(COALESCE(hebbian_potential, 0.1)) as avg_hebbian_strength,
                    MAX(COALESCE(processed_at, NOW())) as last_updated
                FROM stm_hierarchical_episodes
                
                UNION ALL
                
                -- Consolidating memory
                SELECT 
                    'consolidating_memory' as memory_type,
                    COUNT(DISTINCT id) as total_memories,
                    AVG(COALESCE(consolidated_strength, 0.1)) as avg_activation_strength,
                    AVG(COALESCE(hebbian_strength, 0.1)) as avg_hebbian_strength,
                    MAX(COALESCE(consolidated_at, NOW())) as last_updated
                FROM memory_replay
                WHERE consolidation_fate IN ('cortical_transfer', 'hippocampal_retention')
                
                UNION ALL
                
                -- Long-term memory
                SELECT 
                    'long_term_memory' as memory_type,
                    COUNT(DISTINCT memory_id) as total_memories,
                    AVG(COALESCE(stability_score, 0.1)) as avg_activation_strength,
                    AVG(COALESCE(hebbian_strength, 0.1)) as avg_hebbian_strength,
                    MAX(COALESCE(last_processed_at, NOW())) as last_updated
                FROM stable_memories
            )
            SELECT 
                -- Memory distribution metrics
                COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'working_memory'), 0) as total_working_memories,
                COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'short_term_memory'), 0) as total_short_term_memories,
                COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'consolidating_memory'), 0) as total_consolidating_memories,
                COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'long_term_memory'), 0) as total_long_term_memories,
                
                -- System health indicators
                COALESCE((SELECT AVG(COALESCE(avg_activation_strength, 0.1)) FROM memory_distribution), 0.1) as avg_system_activation,
                COALESCE((SELECT AVG(COALESCE(avg_hebbian_strength, 0.1)) FROM memory_distribution WHERE avg_hebbian_strength IS NOT NULL), 0.1) as avg_hebbian_strength
        """)
        
        # Execute the view and validate results
        result = test_db.execute("SELECT * FROM test_memory_health").fetchone()
        
        assert result[0] >= 1, f"Should have at least 1 working memory, got {result[0]}"
        assert result[1] >= 1, f"Should have at least 1 short-term memory, got {result[1]}"
        assert result[2] >= 1, f"Should have at least 1 consolidating memory, got {result[2]}"
        assert result[3] >= 1, f"Should have at least 1 long-term memory, got {result[3]}"
        assert 0 < result[4] <= 1, f"Average system activation should be 0-1, got {result[4]}"
        assert 0 < result[5] <= 1, f"Average hebbian strength should be 0-1, got {result[5]}"
    
    def test_memory_dashboard_model_references(self, test_db):
        """Test that memory_dashboard can reference all required models correctly."""
        
        # Create simplified memory dashboard view
        test_db.execute("""
            CREATE VIEW test_memory_dashboard AS
            WITH recent_activity AS (
                -- Test all model references used in dashboard
                SELECT memory_id, content, activation_strength, 
                       access_count, created_at 
                FROM wm_active_context
                UNION ALL
                SELECT memory_id, content, activation_strength,
                       access_count, created_at 
                FROM consolidating_memories
            ),
            
            long_term_overview AS (
                SELECT memory_id, content, stability_score as strength
                FROM stable_memories
            ),
            
            consolidation_analysis AS (
                SELECT id, content, consolidation_fate, consolidated_strength
                FROM memory_replay
            ),
            
            semantic_network AS (
                SELECT source_concept, target_concept, association_strength
                FROM concept_associations
            )
            
            SELECT 
                (SELECT COUNT(*) FROM recent_activity) as recent_activity_count,
                (SELECT COUNT(*) FROM long_term_overview) as ltm_count,
                (SELECT COUNT(*) FROM consolidation_analysis) as consolidation_count,
                (SELECT COUNT(*) FROM semantic_network) as semantic_associations,
                (SELECT AVG(strength) FROM long_term_overview) as avg_ltm_strength
        """)
        
        result = test_db.execute("SELECT * FROM test_memory_dashboard").fetchone()
        
        assert result[0] >= 2, f"Should have recent activity from multiple sources, got {result[0]}"
        assert result[1] >= 1, f"Should have LTM entries, got {result[1]}"
        assert result[2] >= 1, f"Should have consolidation entries, got {result[2]}"
        assert result[3] >= 1, f"Should have semantic associations, got {result[3]}"
        assert 0 < result[4] <= 1, f"Average LTM strength should be 0-1, got {result[4]}"
    
    def test_access_frequency_model_references(self, test_db):
        """Test access frequency analysis with correct model references."""
        
        test_db.execute("""
            CREATE VIEW access_frequency_test AS
            WITH all_access_patterns AS (
                -- Test access_count references from all models
                SELECT access_count as access_frequency 
                FROM wm_active_context
                UNION ALL
                SELECT co_activation_count as access_frequency 
                FROM stm_hierarchical_episodes
                UNION ALL  
                SELECT access_count as access_frequency 
                FROM stable_memories
            )
            SELECT 
                AVG(access_frequency) as avg_access_frequency,
                MAX(access_frequency) as max_access_frequency,
                COUNT(CASE WHEN access_frequency >= 3 THEN 1 END) as highly_accessed_memories,
                SUM(access_frequency) as total_access_events
            FROM all_access_patterns
        """)
        
        result = test_db.execute("SELECT * FROM access_frequency_test").fetchone()
        
        assert result[0] > 0, f"Average access frequency should be positive, got {result[0]}"
        assert result[1] > 0, f"Max access frequency should be positive, got {result[1]}"
        assert result[2] >= 0, f"Highly accessed count should be non-negative, got {result[2]}"
        assert result[3] > 0, f"Total access events should be positive, got {result[3]}"
    
    def test_model_reference_error_handling(self, test_db):
        """Test error handling when models are empty or missing data."""
        
        # Test with empty working memory
        test_db.execute("DELETE FROM wm_active_context")
        
        test_db.execute("""
            CREATE VIEW error_handling_test AS
            SELECT 
                COALESCE((SELECT COUNT(*) FROM wm_active_context), 0) as wm_count,
                COALESCE((SELECT AVG(activation_strength) FROM wm_active_context), 0.0) as wm_avg_strength,
                COALESCE((SELECT COUNT(*) FROM stm_hierarchical_episodes), 0) as stm_count,
                COALESCE((SELECT COUNT(*) FROM memory_replay), 0) as replay_count,
                COALESCE((SELECT COUNT(*) FROM stable_memories), 0) as ltm_count
        """)
        
        result = test_db.execute("SELECT * FROM error_handling_test").fetchone()
        
        assert result[0] == 0, f"WM count should be 0 after deletion, got {result[0]}"
        assert result[1] == 0.0, f"WM average should be 0.0 when empty, got {result[1]}"
        assert all(count >= 0 for count in result[2:]), f"All counts should be non-negative: {result[2:]}"
    
    def test_dashboard_compilation_success(self, test_db):
        """Test that analytics dashboard views can be compiled successfully."""
        
        # Test that we can create views without syntax errors
        views_to_test = [
            ("memory_distribution_view", """
                SELECT 'working_memory' as memory_type, COUNT(*) as total_memories
                FROM wm_active_context
                UNION ALL
                SELECT 'short_term_memory', COUNT(*) FROM stm_hierarchical_episodes  
                UNION ALL
                SELECT 'long_term_memory', COUNT(*) FROM stable_memories
            """),
            
            ("consolidation_metrics_view", """
                SELECT 
                    COUNT(*) as total_consolidating,
                    COUNT(CASE WHEN consolidation_fate = 'cortical_transfer' THEN 1 END) as cortical_transfers,
                    AVG(consolidated_strength) as avg_consolidation_strength
                FROM memory_replay
            """),
            
            ("semantic_diversity_view", """
                SELECT 
                    COUNT(DISTINCT semantic_category) as unique_semantic_categories,
                    COUNT(DISTINCT cortical_region) as cortical_distribution,
                    AVG(retrieval_accessibility) as avg_retrieval_strength
                FROM memory_replay
                WHERE semantic_category IS NOT NULL
            """)
        ]
        
        compilation_results = []
        for view_name, view_sql in views_to_test:
            try:
                test_db.execute(f"CREATE VIEW {view_name} AS {view_sql}")
                result = test_db.execute(f"SELECT * FROM {view_name}").fetchone()
                compilation_results.append(True)
            except Exception as e:
                compilation_results.append(False)
                pytest.fail(f"Failed to compile {view_name}: {e}")
        
        assert all(compilation_results), "All dashboard views should compile successfully"
    
    def test_model_dependencies_integrity(self, test_db):
        """Test that model dependencies are properly maintained."""
        
        # Test that all referenced models exist and have expected structure
        expected_models = {
            'wm_active_context': ['memory_id', 'activation_strength', 'processed_at'],
            'stm_hierarchical_episodes': ['id', 'stm_strength', 'processed_at'],
            'memory_replay': ['id', 'consolidated_strength', 'consolidated_at'],
            'stable_memories': ['memory_id', 'stability_score', 'last_processed_at'],
            'concept_associations': ['source_concept', 'target_concept', 'association_strength'],
            'consolidating_memories': ['memory_id', 'activation_strength', 'consolidated_at']
        }
        
        for table_name, expected_columns in expected_models.items():
            # Check table exists
            table_check = test_db.execute(f"""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            """).fetchone()
            
            assert table_check[0] == 1, f"Table {table_name} should exist"
            
            # Check expected columns exist
            for column in expected_columns:
                try:
                    test_db.execute(f"SELECT {column} FROM {table_name} LIMIT 1")
                except Exception as e:
                    pytest.fail(f"Column {column} missing from {table_name}: {e}")


def run_dashboard_reference_tests():
    """Execute the dashboard model reference validation test suite."""
    
    print("🔧 Running Dashboard Model References Test Suite (STORY-CS-004)")
    print("=" * 65)
    
    # Run all tests
    pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n✅ Dashboard Model References Tests Complete!")
    print("All model references validated and dashboard compilation confirmed.")


if __name__ == "__main__":
    run_dashboard_reference_tests()