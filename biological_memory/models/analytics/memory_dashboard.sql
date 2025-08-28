{#
  Memory Analytics Dashboard Model
  Materialized as VIEW for real-time analytics and monitoring
  
  Provides comprehensive metrics for biological memory system performance
  Used for monitoring, debugging, and system optimization
#}

{{ config(
    materialized='view',
    tags=['analytics', 'dashboard', 'monitoring']
) }}

WITH memory_type_stats AS (
  SELECT 
    memory_type,
    COUNT(*) as memory_count,
    AVG(activation_strength) as avg_activation,
    STDDEV(activation_strength) as activation_stddev,
    MIN(activation_strength) as min_activation,
    MAX(activation_strength) as max_activation,
    AVG(access_count) as avg_access_count,
    SUM(access_count) as total_accesses,
    AVG({{ safe_divide(memory_age_seconds('created_at'), '3600.0', '0.0') }}) as avg_age_hours
  FROM (
    SELECT memory_id, 'working_memory' as memory_type, activation_strength, 
           access_count, created_at FROM {{ ref('active_memories') }}
    UNION ALL
    SELECT memory_id, 'short_term_memory' as memory_type, activation_strength,
           access_count, created_at FROM {{ ref('consolidating_memories') }}
    UNION ALL  
    SELECT memory_id, memory_type, activation_strength, access_count, created_at 
    FROM {{ ref('stable_memories') }}
  ) all_memories
  GROUP BY memory_type
),

consolidation_metrics AS (
  SELECT 
    COUNT(*) as total_consolidating,
    COUNT(CASE WHEN consolidation_priority > 0.7 THEN 1 END) as high_priority_count,
    AVG(consolidation_priority) as avg_consolidation_priority,
    AVG(interference_score) as avg_interference,
    COUNT(DISTINCT consolidation_batch) as active_batches
  FROM {{ ref('consolidating_memories') }}
),

semantic_network_stats AS (
  SELECT 
    COUNT(*) as total_associations,
    COUNT(DISTINCT source_concept) as unique_source_concepts,
    COUNT(DISTINCT target_concept) as unique_target_concepts,
    AVG(association_strength) as avg_association_strength,
    COUNT(CASE WHEN association_quality = 'strong_semantic' THEN 1 END) as strong_semantic_count,
    COUNT(CASE WHEN association_quality = 'strong_temporal' THEN 1 END) as strong_temporal_count,
    COUNT(CASE WHEN recent_co_occurrences > 0 THEN 1 END) as recent_activity_count
  FROM {{ ref('concept_associations') }}
),

system_health_metrics AS (
  SELECT
    -- Memory capacity utilization
    {{ safe_divide('(SELECT memory_count FROM memory_type_stats WHERE memory_type = \'working_memory\')', var('working_memory_capacity') ~ '.0', '0.0') }} as working_memory_utilization,
    
    -- Consolidation efficiency
    COALESCE(cm.total_consolidating / NULLIF(
      (SELECT memory_count FROM memory_type_stats WHERE memory_type = 'working_memory'), 0
    ), 0) as consolidation_ratio,
    
    -- Network connectivity
    COALESCE(sns.total_associations / NULLIF(
      POWER(sns.unique_source_concepts + sns.unique_target_concepts, 2), 0
    ), 0) as network_density,
    
    -- System stability indicators
    (SELECT activation_stddev FROM memory_type_stats WHERE memory_type = 'long_term_memory') 
    as ltm_stability,
    
    -- Learning rate indicators  
    COALESCE(sns.recent_activity_count / NULLIF(sns.total_associations, 0), 0) 
    as recent_learning_rate
    
  FROM consolidation_metrics cm
  CROSS JOIN semantic_network_stats sns
),

performance_trends AS (
  SELECT 
    DATE_TRUNC('hour', created_at) as hour_bucket,
    memory_type,
    COUNT(*) as memories_created,
    AVG(activation_strength) as avg_hourly_activation
  FROM (
    SELECT memory_id, 'working_memory' as memory_type, activation_strength, created_at 
    FROM {{ ref('active_memories') }}
    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 HOURS'
    UNION ALL
    SELECT memory_id, 'short_term_memory' as memory_type, activation_strength, created_at
    FROM {{ ref('consolidating_memories') }}  
    WHERE consolidated_at > CURRENT_TIMESTAMP - INTERVAL '24 HOURS'
    UNION ALL
    SELECT memory_id, memory_type, activation_strength, created_at
    FROM {{ ref('stable_memories') }}
    WHERE last_processed_at > CURRENT_TIMESTAMP - INTERVAL '24 HOURS'
  ) recent_memories
  GROUP BY DATE_TRUNC('hour', created_at), memory_type
)

SELECT 
  -- System overview
  CURRENT_TIMESTAMP as dashboard_updated_at,
  
  -- Memory type statistics
  (SELECT json_agg(row_to_json(memory_type_stats)) FROM memory_type_stats) as memory_type_stats,
  
  -- Consolidation metrics
  cm.total_consolidating,
  cm.high_priority_count,
  cm.avg_consolidation_priority,
  cm.avg_interference,
  cm.active_batches,
  
  -- Semantic network metrics
  sns.total_associations,
  sns.unique_source_concepts + sns.unique_target_concepts as total_unique_concepts,
  sns.avg_association_strength,
  sns.strong_semantic_count,
  sns.strong_temporal_count,
  sns.recent_activity_count,
  
  -- System health indicators
  shm.working_memory_utilization,
  shm.consolidation_ratio,
  shm.network_density,
  shm.ltm_stability,
  shm.recent_learning_rate,
  
  -- Performance trends (last 24 hours)
  (SELECT json_agg(row_to_json(performance_trends) ORDER BY hour_bucket DESC) 
   FROM performance_trends) as hourly_trends,
  
  -- Health status assessment
  CASE 
    WHEN shm.working_memory_utilization > 0.9 THEN 'OVERLOADED'
    WHEN shm.consolidation_ratio > 2.0 THEN 'CONSOLIDATION_BACKLOG' 
    WHEN shm.ltm_stability < 0.1 THEN 'UNSTABLE'
    WHEN shm.recent_learning_rate < 0.1 THEN 'LOW_ACTIVITY'
    WHEN shm.network_density < 0.01 THEN 'SPARSE_NETWORK'
    ELSE 'HEALTHY'
  END as system_health_status,
  
  -- Recommendations
  CASE 
    WHEN shm.working_memory_utilization > 0.9 
    THEN 'Increase consolidation frequency'
    WHEN shm.consolidation_ratio > 2.0
    THEN 'Optimize batch processing size'
    WHEN shm.network_density < 0.01
    THEN 'Strengthen semantic associations'
    WHEN shm.recent_learning_rate < 0.1
    THEN 'Increase learning stimulus'
    ELSE 'System operating normally'
  END as optimization_recommendation

FROM consolidation_metrics cm
CROSS JOIN semantic_network_stats sns  
CROSS JOIN system_health_metrics shm
