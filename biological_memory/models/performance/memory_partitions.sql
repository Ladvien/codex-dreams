{# 
  Monthly Memory Partitions - BMP-012 Performance Optimization
  Creates partitioned views for improved query performance on temporal data
#}

{{ config(
    materialized='ephemeral',
    tags=['partitioning', 'performance'],
    post_hook='{{ create_monthly_partitions("raw_memories", "created_at") }}'
) }}

-- Current month partition for high-performance queries
WITH current_month_memories AS (
  SELECT *
  FROM {{ source('codex_db', 'memories') }}
  WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_TIMESTAMP)
),

previous_month_memories AS (
  SELECT *
  FROM {{ source('codex_db', 'memories') }}
  WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_TIMESTAMP) - INTERVAL '1 MONTH'
),

partition_metadata AS (
  SELECT 
    'current_month' as partition_name,
    COUNT(*) as record_count,
    MIN(created_at) as earliest_timestamp,
    MAX(created_at) as latest_timestamp,
    AVG(activation_strength) as avg_activation
  FROM current_month_memories
  
  UNION ALL
  
  SELECT 
    'previous_month' as partition_name,
    COUNT(*) as record_count,
    MIN(created_at) as earliest_timestamp,
    MAX(created_at) as latest_timestamp,
    AVG(activation_strength) as avg_activation
  FROM previous_month_memories
)

SELECT 
  partition_name,
  record_count,
  earliest_timestamp,
  latest_timestamp,
  avg_activation,
  CURRENT_TIMESTAMP as analyzed_at
FROM partition_metadata