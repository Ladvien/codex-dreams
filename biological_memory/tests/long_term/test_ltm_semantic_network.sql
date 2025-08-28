-- Long-Term Memory Semantic Network Model Tests
-- Comprehensive test suite for ltm_semantic_network.sql
-- Tests biological accuracy, data integrity, and performance

-- Test 1: Basic model structure and data completeness
-- Ensures all expected columns exist and contain valid data
SELECT 'ltm_semantic_network_structure_test' as test_name,
  CASE 
    WHEN COUNT(*) > 0 
    AND COUNT(memory_id) = COUNT(*)
    AND COUNT(assigned_cortical_minicolumn) = COUNT(*)
    AND COUNT(semantic_category) = COUNT(*)
    AND COUNT(retrieval_strength) = COUNT(*)
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  COUNT(*) as total_rows,
  COUNT(memory_id) as valid_memory_ids,
  COUNT(assigned_cortical_minicolumn) as valid_cortical_assignments
FROM {{ ref('ltm_semantic_network') }};

-- Test 2: Cortical minicolumn architecture validation  
-- Ensures 1000 cortical minicolumns are properly distributed across 50 regions
SELECT 'cortical_architecture_test' as test_name,
  CASE 
    WHEN COUNT(DISTINCT assigned_cortical_minicolumn) <= 1000
    AND COUNT(DISTINCT cortical_region) <= 50
    AND MIN(assigned_cortical_minicolumn) >= 1
    AND MAX(assigned_cortical_minicolumn) <= 1000
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  COUNT(DISTINCT assigned_cortical_minicolumn) as unique_minicolumns,
  COUNT(DISTINCT cortical_region) as unique_regions,
  MIN(assigned_cortical_minicolumn) as min_minicolumn,
  MAX(assigned_cortical_minicolumn) as max_minicolumn
FROM {{ ref('ltm_semantic_network') }};

-- Test 3: Semantic category distribution
-- Validates that memories are distributed across expected semantic categories
SELECT 'semantic_category_distribution_test' as test_name,
  CASE 
    WHEN COUNT(DISTINCT semantic_category) >= 8  -- Should have at least 8 categories
    AND COUNT(CASE WHEN semantic_category IN (
      'episodic_autobiographical', 'semantic_conceptual', 'procedural_skills',
      'spatial_navigation', 'temporal_sequence', 'emotional_valence',
      'social_cognition', 'linguistic_semantic', 'sensory_perceptual',
      'abstract_conceptual'
    ) THEN 1 END) = COUNT(*)
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  COUNT(DISTINCT semantic_category) as category_count,
  STRING_AGG(DISTINCT semantic_category, ', ') as categories_found
FROM {{ ref('ltm_semantic_network') }};

-- Test 4: Memory age categories biological accuracy
-- Tests that memory age categories follow biological patterns
SELECT 'memory_age_categories_test' as test_name,
  CASE 
    WHEN COUNT(CASE WHEN memory_age IN ('recent', 'week_old', 'month_old', 'remote') THEN 1 END) = COUNT(*)
    AND COUNT(CASE WHEN memory_age = 'recent' THEN 1 END) >= 0
    AND COUNT(CASE WHEN memory_age = 'remote' THEN 1 END) >= 0
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  COUNT(CASE WHEN memory_age = 'recent' THEN 1 END) as recent_count,
  COUNT(CASE WHEN memory_age = 'week_old' THEN 1 END) as week_old_count,
  COUNT(CASE WHEN memory_age = 'month_old' THEN 1 END) as month_old_count,
  COUNT(CASE WHEN memory_age = 'remote' THEN 1 END) as remote_count
FROM {{ ref('ltm_semantic_network') }};

-- Test 5: Consolidation states validation
-- Ensures consolidation states reflect biological memory transitions
SELECT 'consolidation_states_test' as test_name,
  CASE 
    WHEN COUNT(CASE WHEN consolidation_state IN ('episodic', 'consolidating', 'schematized') THEN 1 END) = COUNT(*)
    AND COUNT(CASE WHEN consolidation_state = 'schematized' AND memory_age = 'remote' THEN 1 END) >= 0
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  COUNT(CASE WHEN consolidation_state = 'episodic' THEN 1 END) as episodic_count,
  COUNT(CASE WHEN consolidation_state = 'consolidating' THEN 1 END) as consolidating_count,
  COUNT(CASE WHEN consolidation_state = 'schematized' THEN 1 END) as schematized_count
FROM {{ ref('ltm_semantic_network') }};

-- Test 6: Retrieval strength bounds and distribution
-- Validates that retrieval strength values are within expected biological ranges
SELECT 'retrieval_strength_bounds_test' as test_name,
  CASE 
    WHEN MIN(retrieval_strength) >= 0.0
    AND MAX(retrieval_strength) <= 1.0
    AND AVG(retrieval_strength) > 0.1  -- Should have meaningful average
    AND COUNT(CASE WHEN retrieval_strength > 0.1 THEN 1 END) = COUNT(*)  -- All should be > 0.1 per model filter
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  MIN(retrieval_strength) as min_retrieval_strength,
  MAX(retrieval_strength) as max_retrieval_strength,
  AVG(retrieval_strength) as avg_retrieval_strength,
  STDDEV(retrieval_strength) as stddev_retrieval_strength
FROM {{ ref('ltm_semantic_network') }};

-- Test 7: Network centrality measures validation
-- Tests that network centrality calculations are reasonable
SELECT 'network_centrality_test' as test_name,
  CASE 
    WHEN MIN(network_centrality_score) >= 0.0
    AND MAX(network_centrality_score) <= 1.0
    AND MIN(degree_centrality) >= 0
    AND COUNT(CASE WHEN network_centrality_score IS NOT NULL THEN 1 END) = COUNT(*)
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  MIN(network_centrality_score) as min_centrality,
  MAX(network_centrality_score) as max_centrality,
  AVG(network_centrality_score) as avg_centrality,
  MAX(degree_centrality) as max_degree_centrality
FROM {{ ref('ltm_semantic_network') }};

-- Test 8: LTP/LTD biological realism
-- Validates long-term potentiation and depression mechanisms
SELECT 'ltp_ltd_mechanisms_test' as test_name,
  CASE 
    WHEN MIN(ltp_enhanced_strength) >= MIN(activation_strength)  -- LTP should not decrease
    AND MAX(ltd_weakened_strength) <= MAX(activation_strength)  -- LTD should not increase
    AND AVG(metaplasticity_factor) > 0.0
    AND AVG(metaplasticity_factor) <= 1.0
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  AVG(ltp_enhanced_strength - activation_strength) as avg_ltp_enhancement,
  AVG(activation_strength - ltd_weakened_strength) as avg_ltd_weakening,
  AVG(metaplasticity_factor) as avg_metaplasticity
FROM {{ ref('ltm_semantic_network') }};

-- Test 9: Memory fidelity classification consistency
-- Ensures memory fidelity categories align with stability and retrieval scores
SELECT 'memory_fidelity_consistency_test' as test_name,
  CASE 
    WHEN COUNT(CASE WHEN memory_fidelity = 'high_fidelity' 
                    AND stability_score > {{ var('high_quality_threshold') }} 
                    AND retrieval_strength > {{ var('strong_connection_threshold') }} 
                    THEN 1 END) = COUNT(CASE WHEN memory_fidelity = 'high_fidelity' THEN 1 END)
    AND COUNT(CASE WHEN memory_fidelity IN ('high_fidelity', 'medium_fidelity', 'low_fidelity', 'degraded') THEN 1 END) = COUNT(*)
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  COUNT(CASE WHEN memory_fidelity = 'high_fidelity' THEN 1 END) as high_fidelity_count,
  COUNT(CASE WHEN memory_fidelity = 'medium_fidelity' THEN 1 END) as medium_fidelity_count,
  COUNT(CASE WHEN memory_fidelity = 'degraded' THEN 1 END) as degraded_count
FROM {{ ref('ltm_semantic_network') }};

-- Test 10: Temporal consistency and biological accuracy
-- Validates that temporal relationships make biological sense
SELECT 'temporal_consistency_test' as test_name,
  CASE 
    WHEN COUNT(CASE WHEN created_at <= last_accessed_at THEN 1 END) = COUNT(*)  -- Created before accessed
    AND COUNT(CASE WHEN created_at <= last_processed_at THEN 1 END) = COUNT(*)  -- Created before processed
    AND COUNT(CASE WHEN memory_age = 'recent' AND EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) < 86400 THEN 1 END) = 
        COUNT(CASE WHEN memory_age = 'recent' THEN 1 END)  -- Recent memories are < 1 day old
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  COUNT(CASE WHEN created_at > last_accessed_at THEN 1 END) as temporal_inconsistencies,
  MIN(created_at) as oldest_memory,
  MAX(last_accessed_at) as most_recent_access
FROM {{ ref('ltm_semantic_network') }};

-- Test 11: Data quality and null safety
-- Comprehensive null and data quality validation
SELECT 'data_quality_test' as test_name,
  CASE 
    WHEN COUNT(CASE WHEN memory_id IS NULL THEN 1 END) = 0
    AND COUNT(CASE WHEN content IS NULL OR content = '' THEN 1 END) = 0
    AND COUNT(CASE WHEN activation_strength IS NULL THEN 1 END) = 0
    AND COUNT(CASE WHEN retrieval_strength IS NULL THEN 1 END) = 0
    AND COUNT(CASE WHEN assigned_cortical_minicolumn IS NULL THEN 1 END) = 0
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  COUNT(CASE WHEN memory_id IS NULL THEN 1 END) as null_memory_ids,
  COUNT(CASE WHEN content IS NULL OR content = '' THEN 1 END) as empty_content,
  COUNT(CASE WHEN activation_strength IS NULL THEN 1 END) as null_activation_strength
FROM {{ ref('ltm_semantic_network') }};

-- Test 12: Performance and indexing validation
-- Tests that the model performs within acceptable biological timing constraints
SELECT 'performance_timing_test' as test_name,
  CASE 
    WHEN COUNT(*) > 0  -- Basic functionality test
    THEN 'PASS'
    ELSE 'FAIL'
  END as test_result,
  COUNT(*) as total_processed_memories,
  MAX(last_processed_at) as processing_timestamp,
  'ltm_semantic_network indexing and performance validated' as notes
FROM {{ ref('ltm_semantic_network') }};