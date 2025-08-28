-- Test biological parameter validation and proper variable substitution
-- Validates that all biological parameters are within realistic ranges

SELECT 
  'working_memory_capacity' as parameter_name,
  {{ var('working_memory_capacity') }} as parameter_value,
  CASE 
    WHEN {{ var('working_memory_capacity') }} BETWEEN 5 AND 9 THEN 'PASS'
    ELSE 'FAIL' 
  END as validation_result,
  'Miller\'s Law: working memory should be 7±2 items' as validation_rule

UNION ALL

SELECT 
  'strong_connection_threshold' as parameter_name,
  {{ var('strong_connection_threshold') }} as parameter_value,
  CASE 
    WHEN {{ var('strong_connection_threshold') }} BETWEEN 0.6 AND 0.9 THEN 'PASS'
    ELSE 'FAIL' 
  END as validation_result,
  'Strong connections should be between 0.6 and 0.9' as validation_rule

UNION ALL

SELECT 
  'medium_quality_threshold' as parameter_name,
  {{ var('medium_quality_threshold') }} as parameter_value,
  CASE 
    WHEN {{ var('medium_quality_threshold') }} BETWEEN 0.4 AND 0.8 THEN 'PASS'
    ELSE 'FAIL' 
  END as validation_result,
  'Medium quality threshold should be between 0.4 and 0.8' as validation_rule

UNION ALL

SELECT 
  'high_quality_threshold' as parameter_name,
  {{ var('high_quality_threshold') }} as parameter_value,
  CASE 
    WHEN {{ var('high_quality_threshold') }} BETWEEN 0.7 AND 0.95 THEN 'PASS'
    ELSE 'FAIL' 
  END as validation_result,
  'High quality threshold should be between 0.7 and 0.95' as validation_rule

UNION ALL

SELECT 
  'consolidation_threshold' as parameter_name,
  {{ var('consolidation_threshold') }} as parameter_value,
  CASE 
    WHEN {{ var('consolidation_threshold') }} BETWEEN 0.5 AND 0.8 THEN 'PASS'
    ELSE 'FAIL' 
  END as validation_result,
  'Consolidation threshold should be between 0.5 and 0.8' as validation_rule

UNION ALL

SELECT 
  'weak_memory_decay_factor' as parameter_name,
  {{ var('weak_memory_decay_factor') }} as parameter_value,
  CASE 
    WHEN {{ var('weak_memory_decay_factor') }} BETWEEN 0.5 AND 0.9 THEN 'PASS'
    ELSE 'FAIL' 
  END as validation_result,
  'Weak memory decay factor should be between 0.5 and 0.9' as validation_rule

UNION ALL

SELECT 
  'strong_memory_boost_factor' as parameter_name,
  {{ var('strong_memory_boost_factor') }} as parameter_value,
  CASE 
    WHEN {{ var('strong_memory_boost_factor') }} BETWEEN 1.1 AND 1.5 THEN 'PASS'
    ELSE 'FAIL' 
  END as validation_result,
  'Strong memory boost factor should be between 1.1 and 1.5' as validation_rule

UNION ALL

SELECT 
  'recent_activity_window' as parameter_name,
  {{ var('recent_activity_window') }} as parameter_value,
  CASE 
    WHEN {{ var('recent_activity_window') }} BETWEEN 12 AND 48 THEN 'PASS'
    ELSE 'FAIL' 
  END as validation_result,
  'Recent activity window should be between 12 and 48 hours' as validation_rule

UNION ALL

SELECT 
  'creativity_temperature' as parameter_name,
  {{ var('creativity_temperature') }} as parameter_value,
  CASE 
    WHEN {{ var('creativity_temperature') }} BETWEEN 0.3 AND 1.0 THEN 'PASS'
    ELSE 'FAIL' 
  END as validation_result,
  'Creativity temperature should be between 0.3 and 1.0' as validation_rule

UNION ALL

SELECT 
  'parameter_coverage' as parameter_name,
  CAST(COUNT(*) as FLOAT) as parameter_value,
  CASE 
    WHEN COUNT(*) >= 9 THEN 'PASS'
    ELSE 'FAIL' 
  END as validation_result,
  'Should have at least 9 biological parameters defined' as validation_rule
FROM (
  SELECT 1 WHERE {{ var('working_memory_capacity') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('strong_connection_threshold') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('medium_quality_threshold') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('high_quality_threshold') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('consolidation_threshold') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('weak_memory_decay_factor') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('strong_memory_boost_factor') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('recent_activity_window') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('creativity_temperature') }} IS NOT NULL
)