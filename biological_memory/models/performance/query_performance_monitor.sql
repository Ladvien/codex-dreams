{# 
  Real-time Query Performance Monitor - BMP-MEDIUM-009
  Monitors all biological memory queries for <50ms target performance
  Tracks query patterns, execution times, and optimization opportunities
#}

{{ config(
    materialized='ephemeral',
    tags=['performance_monitoring', 'real_time'],
    post_hook='{{ log("Performance monitoring active - Target: <50ms queries", info=true) }}'
) }}

-- Real-time query performance metrics
WITH current_performance AS (
  SELECT 
    query_type,
    query_name,
    AVG(execution_time_ms) as avg_execution_time,
    MIN(execution_time_ms) as min_execution_time,
    MAX(execution_time_ms) as max_execution_time,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY execution_time_ms) as median_execution_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms) as p95_execution_time,
    COUNT(*) as query_count,
    SUM(CASE WHEN execution_time_ms <= 50.0 THEN 1 ELSE 0 END) as queries_under_target,
    AVG(CASE WHEN memory_usage_mb IS NOT NULL THEN memory_usage_mb ELSE 0 END) as avg_memory_mb,
    AVG(CASE WHEN cpu_usage_percent IS NOT NULL THEN cpu_usage_percent ELSE 0 END) as avg_cpu_percent
  FROM performance_benchmarks
  WHERE executed_at > CURRENT_TIMESTAMP - INTERVAL '1 HOUR'
  GROUP BY query_type, query_name
),

performance_ratings AS (
  SELECT *,
    CASE 
      WHEN avg_execution_time <= 25.0 THEN 'EXCELLENT'
      WHEN avg_execution_time <= 50.0 THEN 'GOOD'
      WHEN avg_execution_time <= 100.0 THEN 'FAIR'
      WHEN avg_execution_time <= 250.0 THEN 'NEEDS_IMPROVEMENT'
      ELSE 'CRITICAL'
    END as performance_rating,
    
    ROUND({{ safe_divide('queries_under_target * 100.0', 'query_count', '0.0') }}, 2) as target_success_rate,
    
    CASE 
      WHEN {{ safe_divide('queries_under_target * 100.0', 'query_count', '0.0') }} >= 95.0 THEN 'MEETING_SLA'
      WHEN {{ safe_divide('queries_under_target * 100.0', 'query_count', '0.0') }} >= 90.0 THEN 'NEAR_SLA'
      WHEN {{ safe_divide('queries_under_target * 100.0', 'query_count', '0.0') }} >= 80.0 THEN 'BELOW_SLA'
      ELSE 'FAILING_SLA'
    END as sla_status
  FROM current_performance
)

SELECT 
  query_type,
  query_name,
  avg_execution_time,
  median_execution_time,
  p95_execution_time,
  query_count,
  target_success_rate,
  performance_rating,
  sla_status,
  avg_memory_mb,
  avg_cpu_percent,
  
  -- Performance improvement recommendations
  CASE 
    WHEN avg_execution_time > 100.0 AND avg_memory_mb > 1000.0 
      THEN 'OPTIMIZE_MEMORY_USAGE'
    WHEN avg_execution_time > 100.0 AND query_type = 'working_memory'
      THEN 'CONSIDER_EPHEMERAL_MATERIALIZATION'
    WHEN avg_execution_time > 250.0 AND query_type = 'semantic'
      THEN 'ADD_SIMILARITY_INDEXES'
    WHEN avg_execution_time > 50.0 AND query_type = 'consolidation'
      THEN 'OPTIMIZE_BATCH_SIZE'
    WHEN target_success_rate < 90.0
      THEN 'REQUIRES_IMMEDIATE_OPTIMIZATION'
    ELSE 'PERFORMANCE_ACCEPTABLE'
  END as optimization_recommendation,
  
  CURRENT_TIMESTAMP as metrics_generated_at
  
FROM performance_ratings
ORDER BY 
  CASE performance_rating
    WHEN 'CRITICAL' THEN 1
    WHEN 'NEEDS_IMPROVEMENT' THEN 2
    WHEN 'FAIR' THEN 3
    WHEN 'GOOD' THEN 4
    WHEN 'EXCELLENT' THEN 5
  END,
  avg_execution_time DESC