# Analytics Dashboard Patterns - STORY-CS-004 Implementation Guide

**Document Version**: 1.0  
**Last Updated**: 2025-08-28 20:55:00  
**Author**: Dashboard Fixer Agent (STORY-CS-004)  
**Component**: Analytics Dashboard - Model References

---

## Overview

This document captures the patterns and best practices implemented during STORY-CS-004 for analytics dashboard model references in the biological memory system. It serves as a guide for future dashboard development and maintenance.

## Model Reference Patterns

### Correct Model Reference Mapping

The biological memory system uses the following model reference patterns:

```sql
-- Working Memory Models
FROM {{ ref('wm_active_context') }}           -- ✅ CORRECT
FROM {{ ref('active_memories') }}             -- ❌ INCORRECT (old name)

-- Short-Term Memory Models  
FROM {{ ref('stm_hierarchical_episodes') }}   -- ✅ CORRECT
FROM {{ ref('consolidating_memories') }}      -- ✅ CORRECT

-- Consolidation Models
FROM {{ ref('memory_replay') }}               -- ✅ CORRECT

-- Long-Term Memory Models
FROM {{ ref('stable_memories') }}             -- ✅ CORRECT
FROM {{ ref('ltm_semantic_network') }}        -- ✅ CORRECT

-- Semantic Models
FROM {{ ref('concept_associations') }}        -- ✅ CORRECT

-- Performance Models
FROM {{ ref('optimized_working_memory') }}    -- ✅ CORRECT
FROM {{ ref('memory_partitions') }}           -- ✅ CORRECT
FROM {{ ref('llm_cache_metrics') }}           -- ✅ CORRECT
```

### Model Directory Structure

Models are organized in subdirectories but referenced by filename only:

```
models/
├── analytics/
│   ├── memory_dashboard.sql      → ref('memory_dashboard')
│   └── memory_health.sql         → ref('memory_health')
├── working_memory/
│   └── wm_active_context.sql     → ref('wm_active_context')
├── short_term_memory/
│   ├── stm_hierarchical_episodes.sql → ref('stm_hierarchical_episodes')
│   └── consolidating_memories.sql    → ref('consolidating_memories')
├── consolidation/
│   └── memory_replay.sql         → ref('memory_replay')
├── long_term_memory/
│   └── stable_memories.sql       → ref('stable_memories')
└── semantic/
    └── concept_associations.sql  → ref('concept_associations')
```

**Key Pattern**: Use filename only in `ref()`, not directory path.

## Dashboard Architecture Patterns

### 1. Memory Distribution Analytics

```sql
WITH memory_distribution AS (
    -- Working memory metrics
    SELECT 
        'working_memory' as memory_type,
        COUNT(DISTINCT memory_id) as total_memories,
        AVG(COALESCE(activation_strength, 0.1)) as avg_activation_strength,
        MAX(COALESCE(processed_at, NOW())) as last_updated
    FROM {{ ref('wm_active_context') }}  -- Correct reference
    
    UNION ALL
    
    -- Short-term memory metrics
    SELECT 
        'short_term_memory' as memory_type,
        COUNT(DISTINCT id) as total_memories,
        AVG(COALESCE(stm_strength, 0.1)) as avg_activation_strength,
        MAX(COALESCE(processed_at, NOW())) as last_updated
    FROM {{ ref('stm_hierarchical_episodes') }}
    
    -- Additional memory types...
)
```

**Patterns Applied**:
- ✅ NULL-safe aggregations with `COALESCE()`
- ✅ Consistent column naming across memory types
- ✅ Proper timestamp handling with fallbacks
- ✅ Standardized memory type categorization

### 2. Cross-Memory Analysis Patterns

```sql
WITH all_access_patterns AS (
    -- Collect access patterns from all memory types
    SELECT access_count as access_frequency 
    FROM {{ ref('wm_active_context') }}
    
    UNION ALL
    
    SELECT co_activation_count as access_frequency 
    FROM {{ ref('stm_hierarchical_episodes') }}
    
    UNION ALL  
    
    SELECT access_count as access_frequency 
    FROM {{ ref('stable_memories') }}
)
SELECT 
    AVG(access_frequency) as avg_access_frequency,
    MAX(access_frequency) as max_access_frequency,
    SUM(access_frequency) as total_access_events
FROM all_access_patterns
```

**Patterns Applied**:
- ✅ Consistent column aliases for cross-model compatibility
- ✅ UNION ALL for performance (no need for DISTINCT)
- ✅ Aggregation-friendly data structure

### 3. Error-Resilient Dashboard Patterns

```sql
SELECT 
    -- Safe aggregation with fallbacks
    COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'working_memory'), 0) as total_working_memories,
    
    -- Division by zero protection
    {{ safe_divide('COALESCE(numerator, 0) * 100.0', var('denominator'), '0.0') }} as percentage_metric,
    
    -- NULL-safe calculations
    COALESCE((SELECT AVG(COALESCE(strength, 0.1)) FROM metrics), 0.1) as avg_strength
```

**Patterns Applied**:
- ✅ `COALESCE()` for NULL handling at every level
- ✅ Custom `safe_divide()` macro for division operations  
- ✅ Fallback values that make business sense
- ✅ Nested NULL protection for complex calculations

## Testing Patterns

### Model Reference Validation

```python
def test_working_memory_model_reference(self, test_db):
    """Test that working memory model reference is correct."""
    
    # Test that the correct table exists and has data
    result = test_db.execute("""
        SELECT COUNT(*) as memory_count,
               AVG(activation_strength) as avg_strength
        FROM wm_active_context
    """).fetchone()
    
    assert result[0] > 0, "Working memory table should contain test data"
    assert result[1] > 0, "Average activation strength should be positive"
    
    # Test that old table name doesn't exist
    with pytest.raises(Exception):
        test_db.execute("SELECT COUNT(*) FROM active_memories")
```

### Dashboard Compilation Testing

```python
def test_dashboard_compilation_success(self, test_db):
    """Test that analytics dashboard views can be compiled successfully."""
    
    views_to_test = [
        ("memory_distribution_view", "SELECT 'working_memory' as memory_type..."),
        ("consolidation_metrics_view", "SELECT COUNT(*) as total_consolidating..."),
    ]
    
    for view_name, view_sql in views_to_test:
        try:
            test_db.execute(f"CREATE VIEW {view_name} AS {view_sql}")
            result = test_db.execute(f"SELECT * FROM {view_name}").fetchone()
            # Compilation successful
        except Exception as e:
            pytest.fail(f"Failed to compile {view_name}: {e}")
```

**Testing Patterns**:
- ✅ Isolated database testing for reliable validation
- ✅ Both positive and negative test cases
- ✅ Comprehensive edge case coverage
- ✅ Error message validation for debugging

## Performance Patterns

### Materialization Strategies

```yaml
models:
  biological_memory:
    analytics:
      +materialized: view  # Real-time analytics
      +tags: ["analytics", "dashboard"]
      
    working_memory:
      +materialized: view  # Fast, temporary data
      
    long_term_memory:
      +materialized: table  # Stable, indexed data
      +post-hook: "{{ create_memory_indexes() }}"
```

### Query Optimization Patterns

```sql
-- Use appropriate JOINs for dashboard aggregation
FROM memory_age_analysis ma
CROSS JOIN consolidation_metrics cm  -- Small result sets
CROSS JOIN semantic_diversity sd
CROSS JOIN access_frequency_stats afs
CROSS JOIN system_performance sp

-- Efficient filtering for time-based queries  
WHERE {{ memory_age_seconds('created_at') }} > {{ var('consolidation_threshold') }}
  AND activation_strength > {{ var('plasticity_threshold') }}
```

## Biological Memory Constraints

### Biological Parameter Validation

```sql
-- Miller's 7±2 working memory capacity
{{ var('working_memory_capacity') }} = 7

-- Strength values bounded 0-1
LEAST(1.0, GREATEST(0.0, calculated_strength)) as bounded_strength

-- Biological time windows (seconds/hours)
{{ var('short_term_memory_duration') }} = 30  -- seconds
{{ var('weekly_memory_window') }} = 168        -- hours
{{ var('monthly_memory_window') }} = 720       -- hours
```

### Health Status Assessment Patterns

```sql
CASE 
    WHEN wm_utilization_pct > {{ var('overload_threshold') }} * 100 THEN 'OVERLOADED'
    WHEN consolidation_success_rate < 50 THEN 'CONSOLIDATION_ISSUES'
    WHEN semantic_diversity < 3 THEN 'LOW_SEMANTIC_DIVERSITY'
    WHEN avg_consolidation_strength < 0.3 THEN 'WEAK_CONSOLIDATION'
    WHEN avg_access_frequency < 1.0 THEN 'LOW_ACTIVITY'
    WHEN recent_memories = 0 THEN 'NO_RECENT_ACTIVITY'
    ELSE 'HEALTHY'
END as system_health_status
```

## Troubleshooting Guide

### Common Model Reference Issues

1. **"table missing" warnings**
   - Check that model name matches filename exactly
   - Verify model exists in correct subdirectory
   - Ensure dbt can parse the referenced model

2. **Compilation errors**
   - Run `dbt parse` to identify syntax issues
   - Check for circular dependencies between models
   - Validate macro references and variable usage

3. **Empty dashboard metrics**
   - Verify base tables contain data
   - Check WHERE clause conditions aren't too restrictive
   - Ensure aggregation logic handles NULL values properly

### Debug Commands

```bash
# Test model parsing
export OLLAMA_URL="http://localhost:11434"
dbt parse --partial-parse

# Compile specific models
dbt compile --select memory_health memory_dashboard

# Run tests
pytest tests/analytics/test_dashboard_model_references.py -v

# Check model dependencies
dbt list --select +memory_health --output json
```

## Migration Checklist

When updating dashboard model references:

- [ ] Identify all model references in analytics SQL files
- [ ] Verify actual model names match file structure
- [ ] Update references to use correct model names  
- [ ] Test compilation with `dbt parse`
- [ ] Run comprehensive test suite
- [ ] Update documentation with new patterns
- [ ] Perform self-review as Senior Analytics Engineer
- [ ] Deploy with monitoring enabled

## Future Enhancement Patterns

### Scalability Considerations
- Implement incremental refresh for large datasets
- Add partitioning strategies for time-series data
- Consider materialized views for frequently accessed metrics

### Monitoring Integration
- Add performance threshold alerting
- Implement dashboard health checks
- Create operational runbooks for common issues

### Documentation Standards
- Maintain up-to-date model reference mappings
- Document biological constraints and business rules
- Keep troubleshooting guides current with system changes

---

**Pattern Documentation Complete**: 2025-08-28 20:55:00  
**Next Review**: Quarterly or after significant model structure changes

This documentation serves as the definitive guide for analytics dashboard model references and should be updated whenever the underlying model structure changes.