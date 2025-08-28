-- Comprehensive Biological Accuracy Test Suite
-- BMP-MEDIUM-008: Biological Parameter Enforcement
-- Tests all biological parameters for neuroscientific accuracy

-- Miller's Law (7±2) Working Memory Capacity Test
SELECT 
  'millers_law_enforcement' as test_name,
  {{ var('working_memory_capacity') }} as current_value,
  CASE 
    WHEN {{ var('working_memory_capacity') }} BETWEEN 5 AND 9 THEN 'PASS'
    ELSE 'FAIL' 
  END as test_result,
  'Working memory capacity must be 7±2 items (Miller, 1956)' as biological_justification,
  CASE 
    WHEN {{ var('working_memory_capacity') }} < 5 THEN 'Too low: Below cognitive limits'
    WHEN {{ var('working_memory_capacity') }} > 9 THEN 'Too high: Exceeds biological capacity'
    ELSE 'Within biological range'
  END as validation_details

UNION ALL

-- Short-term Memory Duration (15-30 seconds typical)
SELECT 
  'stm_duration_validation' as test_name,
  {{ var('short_term_memory_duration') }} as current_value,
  CASE 
    WHEN {{ var('short_term_memory_duration') }} BETWEEN 15 AND 60 THEN 'PASS'
    ELSE 'FAIL' 
  END as test_result,
  'STM duration 15-60 seconds without rehearsal (Baddeley & Hitch, 1974)' as biological_justification,
  CASE 
    WHEN {{ var('short_term_memory_duration') }} < 15 THEN 'Too short: Below neurological minimum'
    WHEN {{ var('short_term_memory_duration') }} > 60 THEN 'Too long: Exceeds STM window'
    ELSE 'Biologically plausible'
  END as validation_details

UNION ALL

-- Hebbian Learning Rate (0.001-0.1 for biological realism)
SELECT 
  'hebbian_learning_rate' as test_name,
  {{ var('hebbian_learning_rate') }} as current_value,
  CASE 
    WHEN {{ var('hebbian_learning_rate') }} BETWEEN 0.001 AND 0.1 THEN 'PASS'
    ELSE 'FAIL' 
  END as test_result,
  'Learning rate 0.001-0.1 for stable LTP induction (Bliss & Collingridge, 1993)' as biological_justification,
  CASE 
    WHEN {{ var('hebbian_learning_rate') }} < 0.001 THEN 'Too slow: Insufficient for plasticity'
    WHEN {{ var('hebbian_learning_rate') }} > 0.1 THEN 'Too fast: Risk of runaway potentiation'
    ELSE 'Biologically realistic'
  END as validation_details

UNION ALL

-- Synaptic Decay Rate (should be slower than learning)
SELECT 
  'synaptic_decay_balance' as test_name,
  {{ var('synaptic_decay_rate') }} as current_value,
  CASE 
    WHEN {{ var('synaptic_decay_rate') }} < {{ var('hebbian_learning_rate') }} 
         AND {{ var('synaptic_decay_rate') }} > 0 THEN 'PASS'
    ELSE 'FAIL' 
  END as test_result,
  'Decay rate must be slower than learning for memory stability' as biological_justification,
  CASE 
    WHEN {{ var('synaptic_decay_rate') }} >= {{ var('hebbian_learning_rate') }} 
         THEN 'Too fast: Learning cannot overcome decay'
    WHEN {{ var('synaptic_decay_rate') }} <= 0 THEN 'Invalid: Must be positive'
    ELSE 'Balanced learning/decay ratio'
  END as validation_details

UNION ALL

-- Homeostasis Target (0.2-0.8 for network stability)
SELECT 
  'synaptic_homeostasis_target' as test_name,
  {{ var('homeostasis_target') }} as current_value,
  CASE 
    WHEN {{ var('homeostasis_target') }} BETWEEN 0.2 AND 0.8 THEN 'PASS'
    ELSE 'FAIL' 
  END as test_result,
  'Homeostatic target 0.2-0.8 prevents saturation/silence (Turrigiano, 2008)' as biological_justification,
  CASE 
    WHEN {{ var('homeostasis_target') }} < 0.2 THEN 'Too low: Risk of silent networks'
    WHEN {{ var('homeostasis_target') }} > 0.8 THEN 'Too high: Risk of saturation'
    ELSE 'Homeostatic balance maintained'
  END as validation_details

UNION ALL

-- Consolidation Window (12-48 hours for systems consolidation)
SELECT 
  'consolidation_window_timing' as test_name,
  {{ var('consolidation_window_hours') }} as current_value,
  CASE 
    WHEN {{ var('consolidation_window_hours') }} BETWEEN 12 AND 48 THEN 'PASS'
    ELSE 'FAIL' 
  END as test_result,
  'Systems consolidation 12-48 hours (Squire & Alvarez, 1995)' as biological_justification,
  CASE 
    WHEN {{ var('consolidation_window_hours') }} < 12 THEN 'Too short: Insufficient consolidation time'
    WHEN {{ var('consolidation_window_hours') }} > 48 THEN 'Too long: Exceeds consolidation window'
    ELSE 'Matches consolidation timeline'
  END as validation_details

UNION ALL

-- LTD/LTP Threshold Separation (proper metaplasticity)
SELECT 
  'ltp_ltd_threshold_separation' as test_name,
  ROUND(({{ var('high_quality_threshold') }} - {{ var('medium_quality_threshold') }}) * 100) as current_value,
  CASE 
    WHEN ({{ var('high_quality_threshold') }} - {{ var('medium_quality_threshold') }}) BETWEEN 0.1 AND 0.3 THEN 'PASS'
    ELSE 'FAIL' 
  END as test_result,
  'LTP/LTD threshold gap 10-30% for metaplasticity (Abraham, 2008)' as biological_justification,
  CASE 
    WHEN ({{ var('high_quality_threshold') }} - {{ var('medium_quality_threshold') }}) < 0.1 
         THEN 'Too narrow: Insufficient separation for metaplasticity'
    WHEN ({{ var('high_quality_threshold') }} - {{ var('medium_quality_threshold') }}) > 0.3 
         THEN 'Too wide: May prevent intermediate plasticity'
    ELSE 'Appropriate metaplasticity range'
  END as validation_details

UNION ALL

-- REM Sleep Creativity Factor (0.5-1.2 for creative enhancement)
SELECT 
  'rem_creativity_factor' as test_name,
  {{ var('rem_creativity_factor') }} as current_value,
  CASE 
    WHEN {{ var('rem_creativity_factor') }} BETWEEN 0.5 AND 1.2 THEN 'PASS'
    ELSE 'FAIL' 
  END as test_result,
  'REM creativity 0.5-1.2x for novel associations (Walker, 2009)' as biological_justification,
  CASE 
    WHEN {{ var('rem_creativity_factor') }} < 0.5 THEN 'Too low: Insufficient creative enhancement'
    WHEN {{ var('rem_creativity_factor') }} > 1.2 THEN 'Too high: Unrealistic creativity boost'
    ELSE 'REM-like creative enhancement'
  END as validation_details

UNION ALL

-- Working Memory Overload Threshold (>0.85 for biological realism)
SELECT 
  'working_memory_overload' as test_name,
  {{ var('overload_threshold') }} as current_value,
  CASE 
    WHEN {{ var('overload_threshold') }} BETWEEN 0.85 AND 0.95 THEN 'PASS'
    ELSE 'FAIL' 
  END as test_result,
  'WM overload >85% for cognitive load effects (Sweller, 1988)' as biological_justification,
  CASE 
    WHEN {{ var('overload_threshold') }} < 0.85 THEN 'Too low: Premature overload detection'
    WHEN {{ var('overload_threshold') }} > 0.95 THEN 'Too high: May miss overload conditions'
    ELSE 'Realistic cognitive load threshold'
  END as validation_details

UNION ALL

-- Parameter Coverage Test (ensure all critical parameters defined)
SELECT 
  'biological_parameter_coverage' as test_name,
  COUNT(*) as current_value,
  CASE 
    WHEN COUNT(*) >= 15 THEN 'PASS'
    ELSE 'FAIL' 
  END as test_result,
  'Complete biological parameter coverage for realistic behavior' as biological_justification,
  CASE 
    WHEN COUNT(*) < 15 THEN 'Incomplete: Missing critical biological parameters'
    ELSE 'Comprehensive biological parameter set'
  END as validation_details
FROM (
  -- Count all defined biological parameters
  SELECT 1 WHERE {{ var('working_memory_capacity') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('short_term_memory_duration') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('long_term_memory_threshold') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('hebbian_learning_rate') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('synaptic_decay_rate') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('homeostasis_target') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('plasticity_threshold') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('consolidation_threshold') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('consolidation_window_hours') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('high_quality_threshold') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('medium_quality_threshold') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('overload_threshold') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('rem_creativity_factor') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('weak_connection_threshold') }} IS NOT NULL
  UNION ALL SELECT 1 WHERE {{ var('strong_connection_threshold') }} IS NOT NULL
)

ORDER BY 
  CASE test_result 
    WHEN 'FAIL' THEN 1 
    ELSE 2 
  END,
  test_name