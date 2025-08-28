-- ====================================
-- DIVISION SAFETY TESTS - AUDIT-004 
-- ====================================
-- Comprehensive division by zero protection tests
-- Architecture Guardian Agent - Senior SQL Safety Engineer Review
-- Created: 2025-08-28

-- Test 1: Safe_divide macro with zero denominator
SELECT 
    -- Test case: Normal division
    {{ safe_divide('10.0', '2.0', '0.0') }} as normal_division_result,
    
    -- Test case: Division by zero (should return default)
    {{ safe_divide('10.0', '0', '999.0') }} as zero_division_result,
    
    -- Test case: Division by null (should return default)  
    {{ safe_divide('10.0', 'NULL', '888.0') }} as null_division_result,
    
    -- Test case: Null numerator (should return default)
    {{ safe_divide('NULL', '2.0', '777.0') }} as null_numerator_result,
    
    -- Test case: Both null (should return default)
    {{ safe_divide('NULL', 'NULL', '666.0') }} as both_null_result;

-- Test 2: Memory age calculations
WITH test_memory_ages AS (
    SELECT 
        CURRENT_TIMESTAMP as created_normal,
        CURRENT_TIMESTAMP as created_zero_age,
        NULL as created_null
)
SELECT 
    -- Normal case
    {{ safe_divide(memory_age_seconds('created_normal'), '3600.0', '0.0') }} as normal_age_hours,
    
    -- Zero age case  
    {{ safe_divide(memory_age_seconds('created_zero_age'), '3600.0', '0.0') }} as zero_age_hours,
    
    -- Null case
    {{ safe_divide(memory_age_seconds('created_null'), '3600.0', '999.0') }} as null_age_hours
FROM test_memory_ages;

-- Test 3: Normalization safety (semantic associations)
WITH test_associations AS (
    SELECT 
        10 as normal_associations,
        0 as zero_associations, 
        NULL as null_associations
)
SELECT
    -- Normal case: 10 associations / 10.0 = 1.0
    {{ safe_divide('normal_associations', '10.0', '0.0') }} as normal_norm,
    
    -- Zero associations: 0 / 10.0 = 0.0  
    {{ safe_divide('zero_associations', '10.0', '0.0') }} as zero_norm,
    
    -- Null associations: NULL / 10.0 = default
    {{ safe_divide('null_associations', '10.0', '0.0') }} as null_norm,
    
    -- Division by zero denominator
    {{ safe_divide('normal_associations', '0.0', '999.0') }} as div_by_zero
FROM test_associations;

-- Test 4: Co-activation count safety
WITH test_coactivation AS (
    SELECT 
        5 as normal_count,
        0 as zero_count,
        NULL as null_count
)
SELECT
    -- Normal: 5 / 10.0 = 0.5
    {{ safe_divide('normal_count', '10.0', '0.0') }} as normal_coactivation,
    
    -- Zero: 0 / 10.0 = 0.0
    {{ safe_divide('zero_count', '10.0', '0.0') }} as zero_coactivation,
    
    -- Null: NULL / 10.0 = default
    {{ safe_divide('null_count', '10.0', '0.0') }} as null_coactivation,
    
    -- Division by zero
    {{ safe_divide('normal_count', '0', '999.0') }} as div_zero_coactivation
FROM test_coactivation;

-- Test 5: Recency factor safety
WITH test_recency AS (
    SELECT 
        3600 as normal_seconds,    -- 1 hour
        0 as zero_seconds,        -- Just created
        NULL as null_seconds      -- Invalid time
)
SELECT
    -- Normal recency: exp(-3600/3600) = exp(-1) ≈ 0.368
    EXP(-{{ safe_divide('normal_seconds', '3600.0', '0.0') }}) as normal_recency,
    
    -- Zero seconds: exp(-0/3600) = exp(0) = 1.0
    EXP(-{{ safe_divide('zero_seconds', '3600.0', '0.0') }}) as zero_recency,
    
    -- Null seconds: exp(-default/3600) 
    EXP(-{{ safe_divide('null_seconds', '3600.0', '1.0') }}) as null_recency,
    
    -- Division by zero time constant (should use default)
    EXP(-{{ safe_divide('normal_seconds', '0.0', '1.0') }}) as div_zero_recency
FROM test_recency;

-- Test 6: Performance metrics safety (cache hit rates)
WITH test_cache_stats AS (
    SELECT 
        100 as total_requests,
        80 as cache_hits,
        0 as zero_requests,
        NULL as null_requests
)
SELECT
    -- Normal hit rate: 80/100 = 0.8 = 80%
    {{ safe_divide('cache_hits * 100.0', 'total_requests', '0.0') }} as normal_hit_rate,
    
    -- Zero requests: 80/0 = default (avoid division by zero)
    {{ safe_divide('cache_hits * 100.0', 'zero_requests', '0.0') }} as zero_requests_rate,
    
    -- Null requests: 80/NULL = default
    {{ safe_divide('cache_hits * 100.0', 'null_requests', '0.0') }} as null_requests_rate
FROM test_cache_stats;

-- Test 7: Memory utilization safety
WITH test_utilization AS (
    SELECT 
        7 as current_memories,
        7 as capacity_normal,
        0 as capacity_zero,
        NULL as capacity_null
)
SELECT
    -- Normal: 7/7 = 1.0 = 100% utilization
    {{ safe_divide('current_memories * 100.0', 'capacity_normal', '0.0') }} as normal_utilization,
    
    -- Zero capacity: 7/0 = default (prevent division by zero)
    {{ safe_divide('current_memories * 100.0', 'capacity_zero', '0.0') }} as zero_capacity_util,
    
    -- Null capacity: 7/NULL = default
    {{ safe_divide('current_memories * 100.0', 'capacity_null', '0.0') }} as null_capacity_util
FROM test_utilization;

-- Test 8: Complex nested calculations safety
WITH test_complex AS (
    SELECT 
        10.0 as activation,
        5.0 as associations,
        0.0 as zero_val,
        NULL as null_val
)
SELECT
    -- Complex calculation with multiple divisions
    (
        LEAST(1.0, {{ safe_divide('activation', '10.0', '0.1') }}) * 0.3 +
        LEAST(1.0, {{ safe_divide('associations', '10.0', '0.0') }}) * 0.2 +
        {{ safe_divide('activation', 'GREATEST(associations, 1.0)', '0.1') }} * 0.5
    ) as complex_safe_calculation,
    
    -- Same calculation with zero values (should not crash)
    (
        LEAST(1.0, {{ safe_divide('zero_val', '10.0', '0.1') }}) * 0.3 +
        LEAST(1.0, {{ safe_divide('zero_val', '10.0', '0.0') }}) * 0.2 +
        {{ safe_divide('zero_val', 'GREATEST(zero_val, 1.0)', '0.1') }} * 0.5
    ) as complex_zero_calculation,
    
    -- Same calculation with null values (should not crash) 
    (
        LEAST(1.0, {{ safe_divide('null_val', '10.0', '0.1') }}) * 0.3 +
        LEAST(1.0, {{ safe_divide('null_val', '10.0', '0.0') }}) * 0.2 +
        {{ safe_divide('null_val', 'GREATEST(COALESCE(null_val, 0), 1.0)', '0.1') }} * 0.5
    ) as complex_null_calculation
FROM test_complex;

-- Test 9: Batch processing safety
WITH test_batches AS (
    SELECT 
        generate_series(1, 100) as row_id
)
SELECT
    row_id,
    -- Normal batch calculation
    CEIL({{ safe_divide('row_id * 1.0', '10', '1') }}) as normal_batch,
    
    -- Zero batch size (should use default)
    CEIL({{ safe_divide('row_id * 1.0', '0', '1') }}) as zero_batch_size
FROM test_batches
LIMIT 5;

-- Test 10: Logarithmic safety in frequency calculations
WITH test_frequency AS (
    SELECT 
        100 as high_access,
        1 as single_access, 
        0 as zero_access
)
SELECT
    -- Normal frequency score
    {{ safe_divide('LN(1 + high_access)', 'LN(1 + 100)', '0.0') }} as high_freq_score,
    
    -- Single access 
    {{ safe_divide('LN(1 + single_access)', 'LN(1 + 100)', '0.0') }} as single_freq_score,
    
    -- Zero access (LN(1) = 0, so 0/LN(101) = 0)
    {{ safe_divide('LN(1 + zero_access)', 'LN(1 + 100)', '0.0') }} as zero_freq_score
FROM test_frequency;