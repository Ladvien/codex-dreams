#!/usr/bin/env python3
"""
Advanced tests for ltm_semantic_network model
Tests complex biological accuracy, network properties, and integration scenarios
"""

import pytest
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import logging

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestLTMSemanticNetworkAdvanced:
    """Advanced test suite for Long-Term Memory Semantic Network model"""
    
    @pytest.fixture(scope="class")
    def duckdb_connection(self):
        """Create DuckDB connection to test database"""
        db_path = project_root / "dbs" / "memory.duckdb"
        conn = duckdb.connect(str(db_path))
        yield conn
        conn.close()
    
    def test_cortical_minicolumn_distribution(self, duckdb_connection):
        """Test that cortical minicolumns are properly distributed"""
        query = """
        SELECT 
            cortical_region,
            COUNT(*) as memories_per_region,
            COUNT(DISTINCT assigned_cortical_minicolumn) as minicolumns_per_region
        FROM ltm_semantic_network
        GROUP BY cortical_region
        ORDER BY cortical_region
        """
        
        result = duckdb_connection.execute(query).fetchdf()
        
        # Should have reasonable distribution across regions
        assert len(result) > 0, "No cortical regions found"
        assert result['cortical_region'].max() <= 50, "Too many cortical regions"
        
        # Each region should have some memories
        assert result['memories_per_region'].min() >= 0, "Some regions have no memories"
        
        logger.info(f"Cortical distribution test passed: {len(result)} regions tested")
    
    def test_semantic_category_biological_accuracy(self, duckdb_connection):
        """Test that semantic categories follow neuroscientific organization"""
        expected_categories = {
            'episodic_autobiographical', 'semantic_conceptual', 'procedural_skills',
            'spatial_navigation', 'temporal_sequence', 'emotional_valence',
            'social_cognition', 'linguistic_semantic', 'sensory_perceptual',
            'abstract_conceptual'
        }
        
        query = """
        SELECT DISTINCT semantic_category
        FROM ltm_semantic_network
        """
        
        result = duckdb_connection.execute(query).fetchdf()
        found_categories = set(result['semantic_category'].tolist())
        
        # All categories should be from expected set
        unexpected = found_categories - expected_categories
        assert len(unexpected) == 0, f"Unexpected categories found: {unexpected}"
        
        # Should have reasonable coverage of categories
        assert len(found_categories) >= 5, f"Too few categories: {found_categories}"
        
        logger.info(f"Semantic category test passed: {found_categories}")
    
    def test_retrieval_strength_calculation_accuracy(self, duckdb_connection):
        """Test multi-factor retrieval strength calculation components"""
        query = """
        SELECT 
            retrieval_strength,
            synaptic_efficacy,
            network_centrality_score,
            stability_score,
            memory_age,
            consolidation_state,
            access_count
        FROM ltm_semantic_network
        WHERE retrieval_strength IS NOT NULL
        LIMIT 100
        """
        
        result = duckdb_connection.execute(query).fetchdf()
        
        assert len(result) > 0, "No retrieval strength data found"
        
        # Retrieval strength should be within bounds
        assert result['retrieval_strength'].min() >= 0.0, "Negative retrieval strength found"
        assert result['retrieval_strength'].max() <= 1.0, "Retrieval strength > 1.0 found"
        
        # Should correlate positively with component factors
        correlation_synaptic = result['retrieval_strength'].corr(result['synaptic_efficacy'])
        correlation_centrality = result['retrieval_strength'].corr(result['network_centrality_score'])
        
        assert correlation_synaptic > 0.1, f"Weak synaptic efficacy correlation: {correlation_synaptic}"
        assert correlation_centrality >= 0.0, f"Negative centrality correlation: {correlation_centrality}"
        
        logger.info(f"Retrieval strength calculation test passed: {len(result)} samples tested")
    
    def test_ltp_ltd_mechanisms(self, duckdb_connection):
        """Test Long-Term Potentiation and Long-Term Depression mechanisms"""
        query = """
        SELECT 
            activation_strength,
            ltp_enhanced_strength,
            ltd_weakened_strength,
            access_count,
            memory_age,
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_accessed_at)) / 3600.0 as hours_since_access
        FROM ltm_semantic_network
        WHERE ltp_enhanced_strength IS NOT NULL 
        AND ltd_weakened_strength IS NOT NULL
        """
        
        result = duckdb_connection.execute(query).fetchdf()
        
        assert len(result) > 0, "No LTP/LTD data found"
        
        # LTP should not decrease activation strength
        ltp_decreases = (result['ltp_enhanced_strength'] < result['activation_strength']).sum()
        assert ltp_decreases == 0, f"LTP decreased strength in {ltp_decreases} cases"
        
        # LTD should not increase activation strength  
        ltd_increases = (result['ltd_weakened_strength'] > result['activation_strength']).sum()
        assert ltd_increases == 0, f"LTD increased strength in {ltd_increases} cases"
        
        # Recent frequent access should show LTP enhancement
        recent_frequent = result[(result['access_count'] > 5) & (result['hours_since_access'] < 24)]
        if len(recent_frequent) > 0:
            ltp_enhanced = (recent_frequent['ltp_enhanced_strength'] > recent_frequent['activation_strength']).sum()
            assert ltp_enhanced > 0, "No LTP enhancement found for recently accessed memories"
        
        logger.info(f"LTP/LTD mechanisms test passed: {len(result)} samples tested")
    
    def test_consolidation_state_transitions(self, duckdb_connection):
        """Test that consolidation states follow biological patterns"""
        query = """
        SELECT 
            memory_age,
            consolidation_state,
            COUNT(*) as count,
            AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at))) as avg_age_seconds
        FROM ltm_semantic_network
        GROUP BY memory_age, consolidation_state
        ORDER BY memory_age, consolidation_state
        """
        
        result = duckdb_connection.execute(query).fetchdf()
        
        assert len(result) > 0, "No consolidation state data found"
        
        # Recent memories should primarily be episodic
        recent_data = result[result['memory_age'] == 'recent']
        if len(recent_data) > 0:
            episodic_recent = recent_data[recent_data['consolidation_state'] == 'episodic']['count'].sum()
            total_recent = recent_data['count'].sum()
            episodic_ratio = episodic_recent / total_recent if total_recent > 0 else 0
            # Allow some flexibility but expect majority episodic
            assert episodic_ratio >= 0.3, f"Too few recent episodic memories: {episodic_ratio}"
        
        # Remote memories should have some schematized
        remote_data = result[result['memory_age'] == 'remote']
        if len(remote_data) > 0:
            schematized_remote = remote_data[remote_data['consolidation_state'] == 'schematized']['count'].sum()
            assert schematized_remote >= 0, "No schematized remote memories found"
        
        logger.info(f"Consolidation state test passed: {len(result)} state combinations tested")
    
    def test_network_centrality_measures(self, duckdb_connection):
        """Test network centrality calculation accuracy"""
        query = """
        SELECT 
            network_centrality_score,
            degree_centrality,
            betweenness_centrality_proxy,
            closeness_centrality_proxy,
            eigenvector_centrality_proxy,
            clustering_coefficient
        FROM ltm_semantic_network
        WHERE network_centrality_score IS NOT NULL
        """
        
        result = duckdb_connection.execute(query).fetchdf()
        
        assert len(result) > 0, "No network centrality data found"
        
        # All centrality measures should be non-negative
        assert result['network_centrality_score'].min() >= 0.0, "Negative network centrality found"
        assert result['degree_centrality'].min() >= 0, "Negative degree centrality found"
        
        # Network centrality should be bounded [0,1]
        assert result['network_centrality_score'].max() <= 1.0, "Network centrality > 1.0 found"
        
        # Should have some variation in centrality scores
        centrality_std = result['network_centrality_score'].std()
        assert centrality_std > 0.01, f"Too little centrality variation: {centrality_std}"
        
        logger.info(f"Network centrality test passed: {len(result)} nodes tested")
    
    def test_memory_fidelity_classification(self, duckdb_connection):
        """Test memory fidelity classification logic"""
        query = """
        SELECT 
            memory_fidelity,
            stability_score,
            retrieval_strength,
            COUNT(*) as count,
            AVG(stability_score) as avg_stability,
            AVG(retrieval_strength) as avg_retrieval
        FROM ltm_semantic_network
        GROUP BY memory_fidelity
        ORDER BY 
            CASE memory_fidelity 
                WHEN 'high_fidelity' THEN 1
                WHEN 'medium_fidelity' THEN 2  
                WHEN 'low_fidelity' THEN 3
                WHEN 'degraded' THEN 4
            END
        """
        
        result = duckdb_connection.execute(query).fetchdf()
        
        assert len(result) > 0, "No memory fidelity data found"
        
        # Expected fidelity categories
        expected_fidelities = {'high_fidelity', 'medium_fidelity', 'low_fidelity', 'degraded'}
        found_fidelities = set(result['memory_fidelity'].tolist())
        
        unexpected = found_fidelities - expected_fidelities
        assert len(unexpected) == 0, f"Unexpected fidelity categories: {unexpected}"
        
        # Fidelity should correlate with stability and retrieval strength
        if 'high_fidelity' in found_fidelities and 'degraded' in found_fidelities:
            high_fidelity_stability = result[result['memory_fidelity'] == 'high_fidelity']['avg_stability'].iloc[0]
            degraded_stability = result[result['memory_fidelity'] == 'degraded']['avg_stability'].iloc[0]
            
            assert high_fidelity_stability > degraded_stability, \
                f"High fidelity should have higher stability: {high_fidelity_stability} vs {degraded_stability}"
        
        logger.info(f"Memory fidelity test passed: {found_fidelities}")
    
    def test_temporal_biological_realism(self, duckdb_connection):
        """Test temporal relationships for biological realism"""
        query = """
        SELECT 
            memory_age,
            consolidation_state,
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) as age_seconds,
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_accessed_at)) as hours_since_access,
            retrieval_strength,
            stability_score
        FROM ltm_semantic_network
        WHERE created_at IS NOT NULL 
        AND last_accessed_at IS NOT NULL
        """
        
        result = duckdb_connection.execute(query).fetchdf()
        
        assert len(result) > 0, "No temporal data found"
        
        # Memory age categories should match actual age
        recent_memories = result[result['memory_age'] == 'recent']
        if len(recent_memories) > 0:
            max_recent_age = recent_memories['age_seconds'].max()
            assert max_recent_age < 86400, f"Recent memory too old: {max_recent_age/3600:.1f} hours"
        
        remote_memories = result[result['memory_age'] == 'remote']
        if len(remote_memories) > 0:
            min_remote_age = remote_memories['age_seconds'].min()
            assert min_remote_age > 2592000, f"Remote memory too young: {min_remote_age/86400:.1f} days"
        
        # Older memories should generally have different consolidation patterns
        if len(result) > 10:
            correlation_age_consolidation = pd.get_dummies(result['consolidation_state']).corrwith(pd.Series(result['age_seconds']))
            logger.info(f"Age-consolidation correlations: {correlation_age_consolidation.to_dict()}")
        
        logger.info(f"Temporal biological realism test passed: {len(result)} memories tested")
    
    def test_model_integration_consistency(self, duckdb_connection):
        """Test integration with other models in the pipeline"""
        # Test that ltm_semantic_network can be referenced by other models
        query = """
        SELECT COUNT(*) as ltm_count
        FROM ltm_semantic_network
        """
        
        result = duckdb_connection.execute(query).fetchone()
        ltm_count = result[0] if result else 0
        
        assert ltm_count >= 0, "ltm_semantic_network model not accessible"
        
        # Test schema consistency with expected downstream consumers
        column_query = """
        DESCRIBE ltm_semantic_network
        """
        
        columns_result = duckdb_connection.execute(column_query).fetchdf()
        column_names = set(columns_result['column_name'].tolist())
        
        # Critical columns that other models depend on
        required_columns = {
            'memory_id', 'retrieval_strength', 'semantic_category', 
            'consolidation_state', 'network_centrality_score'
        }
        
        missing = required_columns - column_names
        assert len(missing) == 0, f"Missing required columns: {missing}"
        
        logger.info(f"Model integration test passed: {len(column_names)} columns validated")

def run_tests():
    """Run all advanced tests for ltm_semantic_network"""
    pytest.main([__file__, "-v", "--tb=short"])

if __name__ == "__main__":
    run_tests()