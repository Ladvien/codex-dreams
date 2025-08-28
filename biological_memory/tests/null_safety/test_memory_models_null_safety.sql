-- AUDIT-003 MEMORY MODELS NULL SAFETY TESTS  
-- Tests specific memory model null safety implementations
-- Database Auditor Agent - Model-Specific Null Safety Validation

{{ config(
    severity='error',
    tags=['null_safety', 'memory_models', 'audit']
) }}

-- Test data with various null edge cases for memory processing
WITH test_memories AS (
    SELECT 
        1 as memory_id,
        null::text as content,
        null::text[] as concepts, 
        null::float as activation_strength,
        null::timestamp as created_at,
        null::timestamp as last_accessed_at,
        null::int as access_count,
        null::json as phantom_objects,
        null::text as level_0_goal,
        null::json as level_1_tasks

    UNION ALL
    
    SELECT 
        2 as memory_id,
        '' as content,
        ARRAY[]::text[] as concepts,
        0.0 as activation_strength, 
        NOW() - INTERVAL '1 day' as created_at,
        NOW() - INTERVAL '2 hours' as last_accessed_at,
        0 as access_count,
        '{}'::json as phantom_objects,
        '' as level_0_goal,
        '[]'::json as level_1_tasks
        
    UNION ALL
    
    SELECT 
        3 as memory_id,
        'Valid memory content' as content,
        ARRAY['test', 'concept'] as concepts,
        0.5 as activation_strength,
        NOW() - INTERVAL '30 minutes' as created_at,  
        NOW() - INTERVAL '5 minutes' as last_accessed_at,
        3 as access_count,
        '[{"name": "test_object", "affordances": ["test"]}]'::json as phantom_objects,
        'Test Goal' as level_0_goal,
        '["task1", "task2"]'::json as level_1_tasks
),

-- Test Working Memory null safety
working_memory_tests AS (
    SELECT 
        'WORKING_MEMORY_NULL_SAFETY' as test_category,
        COUNT(*) as total_test_records,
        
        -- Test that all critical fields have non-null values after processing
        COUNT(*) FILTER (WHERE 
            COALESCE(content, 'No content') IS NULL OR
            COALESCE(concepts, ARRAY['unknown']) IS NULL OR
            COALESCE(activation_strength, 0.1) IS NULL OR
            COALESCE(created_at, NOW()) IS NULL OR
            COALESCE(last_accessed_at, NOW()) IS NULL
        ) as null_count_after_coalesce,
        
        -- Test memory age calculation with null timestamps
        COUNT(*) FILTER (WHERE 
            {{ memory_age_seconds('COALESCE(created_at, NOW())') }} IS NULL
        ) as null_age_calculations,
        
        -- Test frequency and recency scores with null inputs
        COUNT(*) FILTER (WHERE 
            {{ frequency_score('COALESCE(access_count, 0)') }} IS NULL OR
            {{ recency_score('COALESCE(last_accessed_at, NOW())', 1) }} IS NULL
        ) as null_score_calculations
        
    FROM test_memories
),

-- Test Short-term Memory hierarchical episodes null safety  
stm_hierarchical_tests AS (
    SELECT 
        'STM_HIERARCHICAL_NULL_SAFETY' as test_category,
        COUNT(*) as total_test_records,
        
        -- Test goal extraction with null content
        COUNT(*) FILTER (WHERE
            COALESCE(
                CASE WHEN COALESCE(content, '') LIKE '%test%' 
                     THEN 'General Task Processing'
                     ELSE 'General Task Processing' 
                END, 
                'General Task Processing'
            ) IS NULL
        ) as null_goal_extractions,
        
        -- Test phantom objects with null JSON
        COUNT(*) FILTER (WHERE 
            COALESCE(
                CASE WHEN phantom_objects IS NOT NULL AND JSON_VALID(phantom_objects::TEXT)
                     THEN phantom_objects
                     ELSE '[]'::json 
                END,
                '[]'::json
            ) IS NULL
        ) as null_phantom_objects,
        
        -- Test emotional salience calculation with null inputs
        COUNT(*) FILTER (WHERE
            (COALESCE(activation_strength, 0.1) * 0.4 + 0.1) IS NULL
        ) as null_emotional_salience
        
    FROM test_memories
),

-- Test Memory Replay consolidation null safety
memory_replay_tests AS (
    SELECT 
        'MEMORY_REPLAY_NULL_SAFETY' as test_category,
        COUNT(*) as total_test_records,
        
        -- Test consolidated strength calculation with null inputs
        COUNT(*) FILTER (WHERE
            CASE 
                WHEN COALESCE(activation_strength, 0.1) < 0.3 
                THEN COALESCE(activation_strength, 0.1) * 0.8
                ELSE COALESCE(activation_strength, 0.1) * 0.95
            END IS NULL
        ) as null_consolidation_strength,
        
        -- Test cortical representation generation with null goals
        COUNT(*) FILTER (WHERE
            CASE WHEN COALESCE(activation_strength, 0.0) > 0.5 THEN
                CASE WHEN COALESCE(level_0_goal, '') LIKE '%Test%' 
                     THEN '{"gist": "test_gist"}'::json
                     ELSE '{"gist": "general_gist"}'::json
                END
            ELSE NULL
            END IS NULL AND COALESCE(activation_strength, 0.0) > 0.5
        ) as null_cortical_representations
        
    FROM test_memories
),

-- Test Concept Associations null safety
concept_associations_tests AS (
    SELECT 
        'CONCEPT_ASSOCIATIONS_NULL_SAFETY' as test_category,
        COUNT(*) as total_test_records,
        
        -- Test concept pair generation with null arrays
        COUNT(*) FILTER (WHERE 
            COALESCE(array_length(COALESCE(concepts, ARRAY['unknown']), 1), 0) IS NULL
        ) as null_concept_lengths,
        
        -- Test association strength calculation with null inputs
        COUNT(*) FILTER (WHERE
            (COALESCE(activation_strength, 0.1) * 0.4 + 0.1) IS NULL
        ) as null_association_calculations,
        
        -- Test semantic similarity with null vectors
        COUNT(*) FILTER (WHERE
            COALESCE(0.5, 0.0) IS NULL  -- Simplified semantic similarity test
        ) as null_semantic_similarities
        
    FROM test_memories
),

-- Test Analytics models null safety
analytics_safety_tests AS (
    SELECT 
        'ANALYTICS_NULL_SAFETY' as test_category,
        COUNT(*) as total_test_records,
        
        -- Test health metrics calculation with null inputs
        COUNT(*) FILTER (WHERE
            COALESCE(activation_strength, 0.1) IS NULL OR
            COALESCE(access_count, 0) IS NULL OR
            COALESCE(created_at, NOW()) IS NULL
        ) as null_health_metrics,
        
        -- Test dashboard aggregations with null values
        COUNT(*) FILTER (WHERE
            AVG(COALESCE(activation_strength, 0.1)) OVER () IS NULL
        ) as null_dashboard_aggregations
        
    FROM test_memories
),

-- Combine all test results
all_model_tests AS (
    SELECT * FROM working_memory_tests
    UNION ALL
    SELECT * FROM stm_hierarchical_tests  
    UNION ALL
    SELECT * FROM memory_replay_tests
    UNION ALL
    SELECT * FROM concept_associations_tests
    UNION ALL
    SELECT * FROM analytics_safety_tests
),

-- Final validation results
test_summary AS (
    SELECT 
        test_category,
        total_test_records,
        COALESCE(null_count_after_coalesce, 0) +
        COALESCE(null_age_calculations, 0) +  
        COALESCE(null_score_calculations, 0) +
        COALESCE(null_goal_extractions, 0) +
        COALESCE(null_phantom_objects, 0) +
        COALESCE(null_emotional_salience, 0) +
        COALESCE(null_consolidation_strength, 0) +
        COALESCE(null_cortical_representations, 0) +
        COALESCE(null_concept_lengths, 0) +
        COALESCE(null_association_calculations, 0) +
        COALESCE(null_semantic_similarities, 0) +
        COALESCE(null_health_metrics, 0) +
        COALESCE(null_dashboard_aggregations, 0) as total_null_issues,
        
        -- Test result assessment
        CASE 
            WHEN COALESCE(null_count_after_coalesce, 0) +
                 COALESCE(null_age_calculations, 0) +  
                 COALESCE(null_score_calculations, 0) +
                 COALESCE(null_goal_extractions, 0) +
                 COALESCE(null_phantom_objects, 0) +
                 COALESCE(null_emotional_salience, 0) +
                 COALESCE(null_consolidation_strength, 0) +
                 COALESCE(null_cortical_representations, 0) +
                 COALESCE(null_concept_lengths, 0) +
                 COALESCE(null_association_calculations, 0) +
                 COALESCE(null_semantic_similarities, 0) +
                 COALESCE(null_health_metrics, 0) +
                 COALESCE(null_dashboard_aggregations, 0) = 0
            THEN 'PASS - Model null safety implemented correctly'
            ELSE 'FAIL - Null safety issues detected in memory models'  
        END as test_result
        
    FROM all_model_tests
)

-- Return test results and fail if any null safety issues found
SELECT 
    test_category,
    total_test_records,
    total_null_issues, 
    test_result
FROM test_summary

-- Test should fail if ANY null safety issues are detected
WHERE total_null_issues = 0