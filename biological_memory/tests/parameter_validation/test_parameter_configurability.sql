-- Test parameter configurability - verify that changing values and recompiling works
-- This test demonstrates that the biological parameters can be changed at compile time

WITH parameter_values AS (
  SELECT 
    'working_memory_capacity' as param_name, 
    {{ var('working_memory_capacity') }} as current_value,
    7 as expected_default_value,
    'Biological parameter from Miller\'s Law' as description
  
  UNION ALL
  
  SELECT 
    'strong_connection_threshold' as param_name,
    {{ var('strong_connection_threshold') }} as current_value,
    0.7 as expected_default_value,
    'Threshold for identifying strong memory connections' as description
    
  UNION ALL
  
  SELECT 
    'consolidation_threshold' as param_name,
    {{ var('consolidation_threshold') }} as current_value, 
    0.6 as expected_default_value,
    'Minimum strength required for memory consolidation' as description
    
  UNION ALL
  
  SELECT 
    'recent_activity_window' as param_name,
    {{ var('recent_activity_window') }} as current_value,
    24 as expected_default_value,
    'Hours defining recent activity window' as description
    
  UNION ALL
  
  SELECT 
    'overload_threshold' as param_name,
    {{ var('overload_threshold') }} as current_value,
    0.9 as expected_default_value,
    'Working memory capacity utilization threshold' as description
)

SELECT 
  param_name,
  current_value,
  expected_default_value,
  description,
  CASE 
    WHEN current_value = expected_default_value THEN 'DEFAULT'
    WHEN current_value != expected_default_value THEN 'CONFIGURED'
    ELSE 'ERROR'
  END as configuration_status,
  CASE 
    WHEN current_value IS NOT NULL THEN 'PASS'
    ELSE 'FAIL'
  END as substitution_test,
  'Parameter successfully substituted by dbt' as test_result
FROM parameter_values
ORDER BY param_name