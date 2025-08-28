# Biological Memory Parameter Management Patterns

## Overview

This document describes the parameter management patterns implemented in the Biological Memory Pipeline. All biological parameters have been extracted from hardcoded values and made configurable via dbt variables.

## Parameter Categories

### 1. Core Biological Parameters

These parameters control the fundamental biological memory processes:

- `working_memory_capacity: 7` - Miller's Law (7±2 items)
- `short_term_memory_duration: 30` - Duration in seconds
- `long_term_memory_threshold: 0.7` - Activation strength threshold

### 2. Memory Strength and Quality Thresholds

Control memory classification and quality assessment:

- `strong_connection_threshold: 0.7` - Strong memory connections
- `medium_quality_threshold: 0.6` - Medium quality memories  
- `high_quality_threshold: 0.8` - High quality memories
- `consolidation_threshold: 0.6` - Minimum for consolidation
- `stability_threshold: 0.5` - Basic stability requirement
- `overload_threshold: 0.9` - Working memory overload

### 3. Memory Decay and Strengthening Factors

Control how memories strengthen or decay over time:

- `weak_memory_decay_factor: 0.8` - Decay rate for weak memories
- `strong_memory_boost_factor: 1.2` - Boost rate for strong memories
- `gradual_forgetting_rate: 0.9` - Rate of gradual memory loss
- `default_decay_factor: 0.7` - Standard decay rate

### 4. Creative and Semantic Association Parameters

Control creative memory associations and semantic processing:

- `plausibility_threshold: 0.6` - Minimum plausibility for associations
- `novelty_score_threshold: 0.5` - Minimum novelty for creative associations
- `creativity_temperature: 0.7` - LLM temperature for creative tasks

### 5. Temporal Windows

Define time windows for memory processing:

- `recent_activity_window: 24` - Recent activity classification (hours)
- `short_processing_window: 1` - Short-term processing window (hours)
- `weekly_memory_window: 168` - 7 days in hours
- `monthly_memory_window: 720` - 30 days in hours
- `memory_cleanup_window: 24` - Hours before cleanup

## Usage Patterns

### 1. Basic Variable Substitution

Replace hardcoded values with dbt variables:

```sql
-- Before (hardcoded)
WHERE activation_strength > 0.7

-- After (parameterized)
WHERE activation_strength > {{ var('strong_connection_threshold') }}
```

### 2. Safe Default Values

Use COALESCE for backward compatibility:

```sql
-- Before
COALESCE({{ var('working_memory_capacity') }}, 7) as capacity

-- After (now all variables have defaults in dbt_project.yml)
{{ var('working_memory_capacity') }} as capacity
```

### 3. Interval Parameterization

Convert hardcoded time intervals to variable hours:

```sql
-- Before
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 HOURS'

-- After  
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '{{ var('recent_activity_window') }} HOURS'
```

### 4. Biological Realism Validation

Add validation in macros to ensure biological accuracy:

```sql
{% if var('hebbian_learning_rate') > var('stability_threshold') %}
  {{ log("WARNING: Hebbian learning rate exceeds biological realism", info=true) }}
{% endif %}
```

## Configuration Examples

### Development Configuration

For testing and development, use more lenient thresholds:

```yaml
vars:
  strong_connection_threshold: 0.6  # Lower threshold
  consolidation_threshold: 0.5      # Easier consolidation
  recent_activity_window: 12        # Shorter time windows
```

### Production Configuration

For production, use more realistic biological parameters:

```yaml
vars:
  strong_connection_threshold: 0.8  # Higher threshold
  consolidation_threshold: 0.7      # Stricter consolidation  
  recent_activity_window: 24        # Longer time windows
```

### Research Configuration

For research scenarios, use adjustable parameters:

```yaml
vars:
  working_memory_capacity: 5        # Test Miller's Law variations
  creativity_temperature: 1.0      # Maximum creativity
  weak_memory_decay_factor: 0.6    # Faster decay for experiments
```

## Testing and Validation

### Parameter Validation Tests

Use the provided validation tests to ensure parameter integrity:

```bash
dbt test --select test_biological_parameter_validation
dbt test --select test_parameter_configurability
```

### Runtime Validation

The system includes runtime validation in macros:

- Hebbian learning rate bounds checking
- Homeostasis target range validation
- Connection threshold validation warnings

## Migration Guide

### From Hardcoded to Parameterized

1. **Identify hardcoded values** in your SQL
2. **Add corresponding variables** to dbt_project.yml
3. **Replace hardcoded values** with `{{ var('parameter_name') }}`
4. **Test compilation** to ensure substitution works
5. **Add validation tests** for parameter ranges
6. **Document biological significance** of each parameter

### Example Migration

```sql
-- Step 1: Identify hardcoded value
WHEN memory_strength > 0.7 THEN 'strong'

-- Step 2: Add to dbt_project.yml
vars:
  strong_connection_threshold: 0.7

-- Step 3: Replace hardcoded value  
WHEN memory_strength > {{ var('strong_connection_threshold') }} THEN 'strong'

-- Step 4: Add validation
{% if var('strong_connection_threshold') > 1.0 %}
  {{ log("ERROR: Strength threshold cannot exceed 1.0", info=true) }}
{% endif %}
```

## Best Practices

1. **Always provide default values** in dbt_project.yml
2. **Use biologically meaningful names** for parameters
3. **Add validation ranges** to prevent invalid configurations  
4. **Document biological significance** of each parameter
5. **Group related parameters** logically in configuration
6. **Test parameter changes** thoroughly before production
7. **Version control parameter changes** with clear commit messages

## Benefits

- **Configurability**: Easy to adjust for different scenarios
- **Biological Realism**: Parameters can be tuned to match research
- **Testability**: Different configurations for development and production
- **Maintainability**: No need to modify SQL for parameter changes
- **Documentation**: Clear mapping between parameters and biological concepts
- **Validation**: Built-in checks for parameter validity

## Future Enhancements

- Dynamic parameter adjustment based on system performance
- Machine learning optimization of biological parameters
- A/B testing framework for parameter configurations  
- Real-time parameter monitoring and alerting
- Integration with biological research databases for parameter validation