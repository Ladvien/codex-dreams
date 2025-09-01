#!/usr/bin/env python3
"""
Pytest configuration and test fixtures for biological memory tests

This file provides test setup, fixtures, and configuration for the biological memory
test suite. It creates mock data and test database setups to match the actual model
architecture, resolving STORY-CS-003 test suite architecture mismatches.

Key Features:
- DuckDB test database setup with proper schema
- Mock source data for ltm_semantic_network model testing  
- Test data generation matching biological memory patterns
- Integration test fixtures for model validation
"""

import pytest
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
import logging
from datetime import datetime, timedelta
import uuid
import os

# Load test environment file if it exists
test_env_path = Path(__file__).parent.parent.parent / '.env.test'
if test_env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(test_env_path)
    
# Setup logging for test diagnostics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration constants
TEST_DB_NAME = "test_memory.duckdb"
CORTICAL_MINICOLUMNS = 100  # Reduced for testing
CORTICAL_REGIONS = 10       # Reduced for testing
SEMANTIC_CATEGORIES = [
    'episodic_autobiographical', 'semantic_conceptual', 'procedural_skills',
    'spatial_navigation', 'temporal_sequence', 'emotional_valence',
    'social_cognition', 'linguistic_semantic', 'sensory_perceptual',
    'abstract_conceptual'
]

@pytest.fixture(scope="session")  
def test_db_path():
    """Create a temporary test database path"""
    test_dir = Path(tempfile.mkdtemp())
    db_path = test_dir / TEST_DB_NAME
    yield str(db_path)
    # Cleanup after all tests
    shutil.rmtree(test_dir, ignore_errors=True)

@pytest.fixture(scope="session")
def duckdb_test_connection(test_db_path):
    """Create DuckDB test connection with proper extensions and schemas"""
    conn = duckdb.connect(str(test_db_path))
    
    # Install required extensions
    try:
        conn.execute("INSTALL httpfs; LOAD httpfs;")
        conn.execute("INSTALL json; LOAD json;") 
        conn.execute("INSTALL fts; LOAD fts;")
    except Exception as e:
        logger.warning(f"Extension installation warning: {e}")
    
    # Create test schemas
    conn.execute("CREATE SCHEMA IF NOT EXISTS main;")
    conn.execute("CREATE SCHEMA IF NOT EXISTS public;")
    
    yield conn
    conn.close()

@pytest.fixture(scope="session")
def mock_source_data(duckdb_test_connection):
    """
    Create mock source data tables for testing ltm_semantic_network model
    
    This fixture creates the source tables that ltm_semantic_network depends on:
    - consolidating_memories (from short-term memory consolidation)  
    - semantic_associations (network connectivity data)
    - network_centrality (graph analysis results)
    """
    conn = duckdb_test_connection
    
    # Create mock consolidating_memories data (core dependency)
    consolidating_memories_data = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(200):  # Generate 200 test memories
        memory_age_days = np.random.exponential(10)  # Exponential distribution
        created_at = base_time + timedelta(days=memory_age_days)
        last_accessed = created_at + timedelta(hours=np.random.exponential(24))
        
        # Generate realistic memory content with semantic concepts
        semantic_category = np.random.choice(SEMANTIC_CATEGORIES)
        concept_mappings = {
            'episodic_autobiographical': ['personal', 'experience', 'myself', 'remember'],
            'semantic_conceptual': ['concept', 'knowledge', 'fact', 'understanding'],
            'procedural_skills': ['skill', 'procedure', 'how-to', 'method'],
            'spatial_navigation': ['location', 'place', 'direction', 'map'],
            'temporal_sequence': ['time', 'sequence', 'order', 'chronology'],
            'emotional_valence': ['emotion', 'feeling', 'mood', 'sentiment'],
            'social_cognition': ['social', 'people', 'interaction', 'relationship'],
            'linguistic_semantic': ['language', 'word', 'meaning', 'communication'],
            'sensory_perceptual': ['visual', 'sensory', 'perception', 'sensation'],
            'abstract_conceptual': ['abstract', 'theory', 'idea', 'concept']
        }
        
        concepts = concept_mappings[semantic_category][:np.random.randint(2, 5)]
        content = f"Memory {i}: {semantic_category} content involving {', '.join(concepts)}"
        
        consolidating_memories_data.append({
            'memory_id': f"mem_{i:04d}",
            'content': content,
            'concepts': concepts,
            'activation_strength': np.random.beta(2, 5),  # Skewed towards lower values
            'created_at': created_at,
            'last_accessed_at': last_accessed,
            'access_count': max(1, int(np.random.poisson(5))),
            'memory_type': np.random.choice(['episodic', 'semantic', 'procedural']),
            'hebbian_strength': np.random.beta(3, 7),
            'consolidation_priority': np.random.beta(2, 8),
            'consolidated_at': created_at + timedelta(minutes=np.random.randint(15, 1440))
        })
    
    consolidating_df = pd.DataFrame(consolidating_memories_data)
    conn.execute("DROP TABLE IF EXISTS consolidating_memories;")
    conn.execute("""
        CREATE TABLE consolidating_memories AS 
        SELECT * FROM consolidating_df
    """)
    
    # Create mock semantic_associations table
    semantic_associations_data = []
    for memory_id in consolidating_df['memory_id'].sample(100):  # Associations for 100 memories
        semantic_associations_data.append({
            'memory_id': memory_id,
            'association_count': np.random.poisson(8),
            'avg_association_strength': np.random.beta(2, 5),
            'max_association_strength': np.random.beta(5, 3),
            'target_category': np.random.choice(SEMANTIC_CATEGORIES)
        })
    
    semantic_df = pd.DataFrame(semantic_associations_data)
    conn.execute("DROP TABLE IF EXISTS semantic_associations;")
    conn.execute("""
        CREATE TABLE semantic_associations AS
        SELECT * FROM semantic_df  
    """)
    
    # Create mock network_centrality table  
    network_centrality_data = []
    for memory_id in consolidating_df['memory_id'].sample(80):  # Centrality for 80 memories
        network_centrality_data.append({
            'memory_id': memory_id,
            'centrality_score': np.random.beta(2, 8),
            'clustering_coefficient': np.random.beta(3, 7)
        })
    
    centrality_df = pd.DataFrame(network_centrality_data)  
    conn.execute("DROP TABLE IF EXISTS network_centrality;")
    conn.execute("""
        CREATE TABLE network_centrality AS
        SELECT * FROM centrality_df
    """)
    
    logger.info(f"Created mock source data: {len(consolidating_df)} memories, "
                f"{len(semantic_df)} associations, {len(centrality_df)} centrality records")
    
    return {
        'consolidating_memories': len(consolidating_df),
        'semantic_associations': len(semantic_df), 
        'network_centrality': len(centrality_df)
    }

@pytest.fixture(scope="session")
def ltm_semantic_network_table(duckdb_test_connection, mock_source_data):
    """
    Create ltm_semantic_network test table matching model structure
    
    This is Line 89 equivalent - creates the actual model table structure
    that integration tests expect, resolving the architecture mismatch.
    """
    conn = duckdb_test_connection
    
    # Create the ltm_semantic_network table structure matching the actual model
    conn.execute("DROP TABLE IF EXISTS ltm_semantic_network;")
    
    # Execute a simplified version of the ltm_semantic_network model logic
    ltm_creation_sql = """
    CREATE TABLE ltm_semantic_network AS
    WITH cortical_minicolumns AS (
      SELECT 
        ROW_NUMBER() OVER (ORDER BY RANDOM()) as cortical_minicolumn_id,
        FLOOR((ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) / 10) + 1 as cortical_region,
        CASE 
          WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 10 < 1 THEN 'episodic_autobiographical'
          WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 10 < 2 THEN 'semantic_conceptual'
          WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 10 < 3 THEN 'procedural_skills'
          WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 10 < 4 THEN 'spatial_navigation'
          WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 10 < 5 THEN 'temporal_sequence'
          WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 10 < 6 THEN 'emotional_valence'
          WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 10 < 7 THEN 'social_cognition'
          WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 10 < 8 THEN 'linguistic_semantic'
          WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 10 < 9 THEN 'sensory_perceptual'
          ELSE 'abstract_conceptual'
        END as semantic_category,
        RANDOM() as baseline_activation,
        CURRENT_TIMESTAMP as minicolumn_initialized_at
      FROM GENERATE_SERIES(1, {}) as minicolumn_series
    ),
    
    consolidated_memories AS (
      SELECT 
        cm.*,
        (SELECT mc.cortical_minicolumn_id 
         FROM cortical_minicolumns mc
         WHERE RANDOM() < 0.1 -- Random assignment for testing
         LIMIT 1) as assigned_cortical_minicolumn,
        
        CASE 
          WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - cm.created_at::TIMESTAMP)) < 86400 THEN 'recent'
          WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - cm.created_at::TIMESTAMP)) < 604800 THEN 'week_old'  
          WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - cm.created_at::TIMESTAMP)) < 2592000 THEN 'month_old'
          ELSE 'remote'
        END as memory_age,
        
        CASE
          WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - cm.created_at::TIMESTAMP)) < 86400 AND 
               cm.consolidation_priority > 0.7 THEN 'episodic'
          WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - cm.created_at::TIMESTAMP)) < 2592000 AND 
               cm.hebbian_strength > 0.5 THEN 'consolidating'
          WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - cm.created_at::TIMESTAMP)) >= 2592000 AND 
               cm.activation_strength > 0.3 THEN 'schematized'
          ELSE 'episodic'
        END as consolidation_state,
        
        -- Determine semantic category from content
        CASE 
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%personal%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%experience%' THEN 'episodic_autobiographical'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%concept%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%knowledge%' THEN 'semantic_conceptual'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%skill%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%procedure%' THEN 'procedural_skills'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%location%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%place%' THEN 'spatial_navigation'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%time%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%sequence%' THEN 'temporal_sequence'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%emotion%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%feeling%' THEN 'emotional_valence'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%social%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%people%' THEN 'social_cognition'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%language%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%word%' THEN 'linguistic_semantic'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%visual%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') LIKE '%sensory%' THEN 'sensory_perceptual'
          ELSE 'abstract_conceptual'
        END as semantic_category
        
      FROM consolidating_memories cm
      WHERE cm.activation_strength > 0.1
    ),
    
    network_centrality_cte AS (
      SELECT 
        cm.*,
        mc.cortical_region,
        
        COALESCE(sa.association_count, 0) as degree_centrality,
        COALESCE((SELECT COUNT(*) FROM semantic_associations sa2 
                  WHERE sa2.memory_id = cm.memory_id), 0) as betweenness_centrality_proxy,
        COALESCE(sa.avg_association_strength, 0.0) as closeness_centrality_proxy,
        COALESCE(sa.max_association_strength, 0.0) * COALESCE(sa.association_count, 0) / 50.0 as eigenvector_centrality_proxy,
        COALESCE(nc.clustering_coefficient, 0.0) as clustering_coefficient,
        
        -- Network centrality composite score
        LEAST(1.0, (
          COALESCE(sa.association_count, 0) / 20.0 * 0.25 +
          COALESCE(sa.avg_association_strength, 0.0) * 0.25 + 
          COALESCE(sa.max_association_strength, 0.0) * 0.25 +
          COALESCE(nc.clustering_coefficient, 0.0) * 0.25
        )) as network_centrality_score
        
      FROM consolidated_memories cm
      LEFT JOIN cortical_minicolumns mc ON cm.assigned_cortical_minicolumn = mc.cortical_minicolumn_id
      LEFT JOIN semantic_associations sa ON cm.memory_id = sa.memory_id
      LEFT JOIN network_centrality nc ON cm.memory_id = nc.memory_id
    ),
    
    synaptic_plasticity AS (
      SELECT 
        nc.*,
        
        -- LTP: Strengthen frequently accessed memories
        CASE 
          WHEN nc.access_count > 5 AND 
               EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - nc.last_accessed_at::TIMESTAMP)) < 86400 THEN
            LEAST(1.0, nc.activation_strength * 1.2)
          ELSE nc.activation_strength
        END as ltp_enhanced_strength,
        
        -- LTD: Weaken rarely accessed remote memories  
        CASE 
          WHEN nc.access_count < 3 AND nc.memory_age = 'remote' AND
               EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - nc.last_accessed_at::TIMESTAMP)) > 604800 THEN
            GREATEST(0.1, nc.activation_strength * 0.8)
          ELSE nc.activation_strength  
        END as ltd_weakened_strength,
        
        -- Combined synaptic efficacy
        LEAST(1.0, GREATEST(0.1, nc.activation_strength)) as synaptic_efficacy,
        
        -- Metaplasticity factor
        EXP(-nc.access_count / 10.0) as metaplasticity_factor
        
      FROM network_centrality_cte nc
    ),
    
    final_ltm AS (
      SELECT 
        sp.*,
        
        -- Multi-factor retrieval strength (bounded 0-1)
        LEAST(1.0, GREATEST(0.0, 
          sp.synaptic_efficacy * 0.30 +
          sp.network_centrality_score * 0.25 +
          EXP(-EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - sp.last_accessed_at::TIMESTAMP)) / 604800.0) * 0.20 +
          LOG(GREATEST(1, sp.access_count)) / LOG(100) * 0.15 +
          CASE 
            WHEN sp.consolidation_state = 'schematized' THEN 1.0
            WHEN sp.consolidation_state = 'consolidating' THEN 0.8
            WHEN sp.consolidation_state = 'episodic' THEN 0.6
            ELSE 0.5
          END * 0.10
        )) as retrieval_strength,
         
        -- Retrieval probability with sigmoid
        1.0 / (1.0 + EXP(-(sp.synaptic_efficacy - 0.5))) as retrieval_probability,
        
        -- Stability score for persistence
        (sp.synaptic_efficacy * 0.4 +
         sp.network_centrality_score * 0.3 +
         CASE 
           WHEN sp.consolidation_state = 'schematized' THEN 0.3
           WHEN sp.consolidation_state = 'consolidating' THEN 0.2
           ELSE 0.1
         END) as stability_score,
         
        -- Memory fidelity classification
        CASE 
          WHEN sp.synaptic_efficacy > 0.8 AND sp.network_centrality_score > 0.7 THEN 'high_fidelity'
          WHEN sp.synaptic_efficacy > 0.6 AND sp.network_centrality_score > 0.5 THEN 'medium_fidelity'
          WHEN sp.synaptic_efficacy > 0.4 AND sp.network_centrality_score > 0.3 THEN 'low_fidelity'
          ELSE 'degraded'
        END as memory_fidelity,
        
        CURRENT_TIMESTAMP as last_processed_at,
        CURRENT_TIMESTAMP as semantic_network_updated_at
        
      FROM synaptic_plasticity sp
      WHERE sp.synaptic_efficacy > 0.1
    )
    
    SELECT * FROM final_ltm
    ORDER BY retrieval_strength DESC, network_centrality_score DESC
    """.format(CORTICAL_MINICOLUMNS)
    
    conn.execute(ltm_creation_sql)
    
    # Verify table creation and get row count
    result = conn.execute("SELECT COUNT(*) FROM ltm_semantic_network").fetchone()
    row_count = result[0] if result else 0
    
    logger.info(f"Created ltm_semantic_network test table with {row_count} rows")
    
    # Verify table schema matches expectations
    schema_result = conn.execute("DESCRIBE ltm_semantic_network").fetchdf()
    logger.info(f"ltm_semantic_network schema: {len(schema_result)} columns")
    
    return row_count

# Parametrized fixtures for test data variations
@pytest.fixture(params=['high_quality', 'medium_quality', 'low_quality'])
def memory_quality_filter(request):
    """Fixture providing different memory quality thresholds for testing"""
    quality_thresholds = {
        'high_quality': 0.8,
        'medium_quality': 0.5, 
        'low_quality': 0.2
    }
    return quality_thresholds[request.param]

@pytest.fixture(params=SEMANTIC_CATEGORIES[:5])  # Test subset of categories
def semantic_category_filter(request):
    """Fixture providing different semantic categories for focused testing"""
    return request.param

# Test configuration and custom markers
def pytest_configure(config):
    """Configure pytest with custom markers for biological memory tests"""
    config.addinivalue_line(
        "markers", 
        "biological_accuracy: mark test as checking biological accuracy"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test requiring full setup"
    )
    config.addinivalue_line(
        "markers", 
        "performance: mark test as performance/timing validation"
    )

# Test utilities for biological memory validation
def assert_biological_bounds(value, min_val=0.0, max_val=1.0, name="value"):
    """Assert that a biological parameter is within expected bounds"""
    assert min_val <= value <= max_val, f"{name} {value} outside biological bounds [{min_val}, {max_val}]"

def assert_temporal_consistency(created_at, accessed_at, processed_at=None):
    """Assert temporal relationships make biological sense"""
    assert created_at <= accessed_at, "Memory cannot be accessed before creation"
    if processed_at:
        assert created_at <= processed_at, "Memory cannot be processed before creation"

def generate_test_memory_id():
    """Generate unique test memory ID"""
    return f"test_{uuid.uuid4().hex[:8]}"

# Session cleanup
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_environment():
    """Automatic cleanup of test environment after session"""
    yield
    # Clean up any test schemas that were created
    try:
        import psycopg2
        postgres_url = os.getenv('POSTGRES_DB_URL', '')
        
        if postgres_url:
            import re
            match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', postgres_url)
            if match:
                conn = psycopg2.connect(
                    user=match.group(1),
                    password=match.group(2),
                    host=match.group(3),
                    port=int(match.group(4)),
                    database=match.group(5)
                )
            else:
                conn = psycopg2.connect(
                    host='localhost',
                    database='codex_db'
                )
        else:
            conn = psycopg2.connect(
                host='localhost',
                database='codex_db'
            )
        
        with conn.cursor() as cur:
            # Find all test schemas
            cur.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name LIKE 'test_schema_%'
            """)
            test_schemas = cur.fetchall()
            
            # Drop each test schema
            for (schema_name,) in test_schemas:
                logger.info(f"Cleaning up test schema: {schema_name}")
                cur.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            
            conn.commit()
        
        conn.close()
        logger.info(f"Cleaned up {len(test_schemas)} test schema(s)")
    except Exception as e:
        logger.warning(f"Failed to clean up test schemas: {e}")
    
    logger.info("Test session cleanup completed")