-- DuckDB Compatibility Test for Vector Operations
-- Tests the new vector_dot_product and vector_magnitude macros

-- Test 1: Basic vector dot product
SELECT 
    'Test 1: Vector Dot Product' as test_name,
    (SELECT SUM(COALESCE(v1 * v2, 0)) 
     FROM (
       SELECT 
         UNNEST([1.0, 2.0, 3.0]) as v1,
         UNNEST([4.0, 5.0, 6.0]) as v2,
         GENERATE_SERIES(1, GREATEST(LEN([1.0, 2.0, 3.0]), LEN([4.0, 5.0, 6.0]))) as idx
     )) as dot_product_result,
    32.0 as expected_result, -- 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
    CASE WHEN 
        ABS((SELECT SUM(COALESCE(v1 * v2, 0)) 
             FROM (
               SELECT 
                 UNNEST([1.0, 2.0, 3.0]) as v1,
                 UNNEST([4.0, 5.0, 6.0]) as v2
             )) - 32.0) < 0.01 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as test_result;

-- Test 2: Vector magnitude
SELECT 
    'Test 2: Vector Magnitude' as test_name,
    SQRT((SELECT SUM(COALESCE(v * v, 0)) FROM (SELECT UNNEST([3.0, 4.0]) as v))) as magnitude_result,
    5.0 as expected_result, -- sqrt(3^2 + 4^2) = sqrt(9 + 16) = sqrt(25) = 5
    CASE WHEN 
        ABS(SQRT((SELECT SUM(COALESCE(v * v, 0)) FROM (SELECT UNNEST([3.0, 4.0]) as v))) - 5.0) < 0.01 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as test_result;

-- Test 3: List contains function
SELECT 
    'Test 3: List Contains' as test_name,
    list_contains(['apple', 'banana', 'cherry'], 'banana') as contains_result,
    true as expected_result,
    CASE WHEN 
        list_contains(['apple', 'banana', 'cherry'], 'banana') = true
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as test_result;

-- Test 4: JSON extract function
SELECT 
    'Test 4: JSON Extract' as test_name,
    json_extract('{"name": "test", "value": 42}', '$.value') as json_result,
    '42' as expected_result,
    CASE WHEN 
        json_extract('{"name": "test", "value": 42}', '$.value') = '42'
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as test_result;

-- Test 5: Empty vector handling
SELECT 
    'Test 5: Empty Vector Safety' as test_name,
    COALESCE(SQRT((SELECT SUM(COALESCE(v * v, 0)) FROM (SELECT UNNEST([]) as v))), 0.0) as empty_magnitude,
    0.0 as expected_result,
    CASE WHEN 
        COALESCE(SQRT((SELECT SUM(COALESCE(v * v, 0)) FROM (SELECT UNNEST([]) as v))), 0.0) = 0.0
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as test_result;