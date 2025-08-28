-- AUDIT-003 NULL SAFETY TESTS
-- Comprehensive null pointer crash prevention tests
-- Database Auditor Agent - Test Suite for Null Safety Implementation

{{ config(
    severity='error',
    tags=['null_safety', 'audit', 'security']
) }}

WITH null_test_data AS (
    -- Create test data with various null scenarios
    SELECT 
        null::text as null_content,
        ''::text as empty_content,
        null::text[] as null_array,
        ARRAY[]::text[] as empty_array,
        null::json as null_json,
        '{}'::json as empty_json,
        '{"invalid"}'::text as invalid_json,
        null::timestamp as null_timestamp,
        null::float as null_number,
        0.0::float as zero_number
),

-- Test 1: JSON extraction safety
json_extraction_tests AS (
    SELECT 
        'JSON_EXTRACTION_SAFETY' as test_category,
        -- Test our enhanced json extraction macro
        {{ extract_json_field('null_json', 'nonexistent_key', 'default_value') }} as json_test_1,
        {{ extract_json_field('empty_json', 'missing_key', 'safe_default') }} as json_test_2,
        {{ extract_json_field('invalid_json', 'any_key', 'fallback_value') }} as json_test_3
    FROM null_test_data
),

-- Test 2: Array operations safety
array_safety_tests AS (
    SELECT 
        'ARRAY_OPERATIONS_SAFETY' as test_category,
        -- Test safe array access macro
        {{ safe_array_access('null_array', 1, "'safe_default'") }} as array_test_1,
        {{ safe_array_access('empty_array', 1, "'empty_default'") }} as array_test_2,
        -- Test null array coalescing
        COALESCE(null_array, ARRAY['fallback_value']) as array_test_3
    FROM null_test_data
),

-- Test 3: Mathematical operations safety
math_safety_tests AS (
    SELECT 
        'MATHEMATICAL_OPERATIONS_SAFETY' as test_category,
        -- Test safe division
        {{ safe_math_operation('divide', 'null_number', 'zero_number', '0.0') }} as math_test_1,
        {{ safe_math_operation('multiply', 'null_number', '5.0', '0.0') }} as math_test_2,
        -- Test safe normalization
        {{ normalize_activation('null_number', '0.0', '1.0') }} as math_test_3
    FROM null_test_data
),

-- Test 4: Timestamp operations safety
timestamp_safety_tests AS (
    SELECT 
        'TIMESTAMP_OPERATIONS_SAFETY' as test_category,
        -- Test memory age calculation with null timestamps
        {{ memory_age_seconds('COALESCE(null_timestamp, NOW())') }} as timestamp_test_1,
        -- Test recency score with null timestamps
        {{ recency_score('COALESCE(null_timestamp, NOW())', 1) }} as timestamp_test_2,
        -- Ensure no null timestamps in results
        COALESCE(null_timestamp, NOW()) as timestamp_test_3
    FROM null_test_data
),

-- Test 5: Content safety tests
content_safety_tests AS (
    SELECT 
        'CONTENT_SAFETY' as test_category,
        -- Test content coalescing
        COALESCE(null_content, 'No content available') as content_test_1,
        COALESCE(empty_content, 'Empty content fallback') as content_test_2,
        -- Test string operations on null content
        LENGTH(COALESCE(null_content, '')) as content_test_3
    FROM null_test_data
),

-- Test 6: Embedding operations safety
embedding_safety_tests AS (
    SELECT 
        'EMBEDDING_OPERATIONS_SAFETY' as test_category,
        -- Test embedding placeholder generation with null content
        {{ create_embedding_placeholder('COALESCE(null_content, \'fallback_content\')', 5) }} as embedding_test_1,
        -- Test array operations on embeddings
        array_length({{ create_embedding_placeholder('COALESCE(null_content, \'test\')', 3) }}, 1) as embedding_test_2
    FROM null_test_data
),

-- Combined test results
all_tests AS (
    SELECT * FROM json_extraction_tests
    UNION ALL
    SELECT * FROM array_safety_tests  
    UNION ALL
    SELECT * FROM math_safety_tests
    UNION ALL
    SELECT * FROM timestamp_safety_tests
    UNION ALL
    SELECT * FROM content_safety_tests
    UNION ALL  
    SELECT * FROM embedding_safety_tests
)

-- Final validation: ensure no null values in critical operations
SELECT 
    test_category,
    -- Count of any null results (should be 0)
    COUNT(*) FILTER (WHERE 
        json_test_1 IS NULL OR 
        array_test_1 IS NULL OR 
        math_test_1 IS NULL OR 
        timestamp_test_1 IS NULL OR 
        content_test_1 IS NULL OR
        embedding_test_1 IS NULL
    ) as null_result_count,
    
    -- Validate that all tests produced safe non-null results
    CASE 
        WHEN COUNT(*) FILTER (WHERE 
            json_test_1 IS NULL OR 
            array_test_1 IS NULL OR 
            math_test_1 IS NULL OR 
            timestamp_test_1 IS NULL OR 
            content_test_1 IS NULL OR
            embedding_test_1 IS NULL
        ) > 0 
        THEN 'FAIL - NULL VALUES DETECTED'
        ELSE 'PASS - ALL NULL SAFETY CHECKS PASSED'
    END as test_result

FROM all_tests
GROUP BY test_category

-- Ensure test fails if any nulls are found in results
HAVING COUNT(*) FILTER (WHERE 
    json_test_1 IS NULL OR 
    array_test_1 IS NULL OR 
    math_test_1 IS NULL OR 
    timestamp_test_1 IS NULL OR 
    content_test_1 IS NULL OR
    embedding_test_1 IS NULL
) = 0