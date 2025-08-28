{#
  Memory Health Analytics View - BMP-011
  
  Real-time monitoring and health assessment of biological memory system.
  Provides comprehensive metrics for memory distribution, performance, and system health.
  
  Key Features:
  - Memory distribution metrics across working, short-term, and long-term memory
  - Retrieval strength averages and biological health indicators
  - Semantic diversity and cortical distribution monitoring
  - System performance benchmarks and alerting thresholds
  - Real-time consolidation efficiency tracking
#}

{{ config(
    materialized='view',
    tags=['analytics', 'memory_health', 'monitoring', 'real_time']
) }}

WITH memory_distribution AS (
    -- Memory counts and distribution across memory types
    SELECT 
        'working_memory' as memory_type,
        COUNT(DISTINCT memory_id) as total_memories,
        AVG(COALESCE(activation_strength, 0.1)) as avg_activation_strength,
        AVG(COALESCE(hebbian_strength, 0.1)) as avg_hebbian_strength,
        MAX(COALESCE(processed_at, NOW())) as last_updated
    FROM {{ ref('active_memories') }}
    
    UNION ALL
    
    SELECT 
        'short_term_memory' as memory_type,
        COUNT(DISTINCT id) as total_memories,
        AVG(COALESCE(stm_strength, 0.1)) as avg_activation_strength,
        AVG(COALESCE(hebbian_potential, 0.1)) as avg_hebbian_strength,
        MAX(COALESCE(processed_at, NOW())) as last_updated
    FROM {{ ref('stm_hierarchical_episodes') }}
    
    UNION ALL
    
    SELECT 
        'consolidating_memory' as memory_type,
        COUNT(DISTINCT id) as total_memories,
        AVG(COALESCE(consolidated_strength, 0.1)) as avg_activation_strength,
        AVG(COALESCE(hebbian_strength, 0.1)) as avg_hebbian_strength,
        MAX(COALESCE(consolidated_at, NOW())) as last_updated
    FROM {{ ref('memory_replay') }}
    WHERE consolidation_fate IN ('cortical_transfer', 'hippocampal_retention')
    
    UNION ALL
    
    SELECT 
        'long_term_memory' as memory_type,
        COUNT(DISTINCT memory_id) as total_memories,
        AVG(COALESCE(stability_score, 0.1)) as avg_activation_strength,
        AVG(COALESCE(hebbian_strength, 0.1)) as avg_hebbian_strength,
        MAX(COALESCE(last_processed_at, NOW())) as last_updated
    FROM {{ ref('stable_memories') }}
),

memory_age_analysis AS (
    -- Analyze memory age distribution for health assessment
    SELECT 
        COUNT(CASE WHEN age_category = 'recent' THEN 1 END) as recent_memories,
        COUNT(CASE WHEN age_category = 'week_old' THEN 1 END) as week_old_memories,
        COUNT(CASE WHEN age_category = 'month_old' THEN 1 END) as month_old_memories,
        COUNT(CASE WHEN age_category = 'remote' THEN 1 END) as remote_memories,
        COUNT(*) as total_classified_memories
    FROM (
        -- Working memory (always recent)
        SELECT 'recent' as age_category
        FROM {{ ref('active_memories') }}
        
        UNION ALL
        
        -- Short-term memory
        SELECT 
            CASE 
                WHEN {{ memory_age_seconds('timestamp') }} <= 86400 THEN 'recent'  -- 1 day
                WHEN {{ memory_age_seconds('timestamp') }} <= 604800 THEN 'week_old'  -- 7 days
                WHEN {{ memory_age_seconds('timestamp') }} <= 2592000 THEN 'month_old'  -- 30 days
                ELSE 'remote'
            END as age_category
        FROM {{ ref('stm_hierarchical_episodes') }}
        
        UNION ALL
        
        -- Long-term memory
        SELECT 
            CASE 
                WHEN {{ memory_age_seconds('created_at') }} <= 86400 THEN 'recent'
                WHEN {{ memory_age_seconds('created_at') }} <= 604800 THEN 'week_old'
                WHEN {{ memory_age_seconds('created_at') }} <= 2592000 THEN 'month_old'
                ELSE 'remote'
            END as age_category
        FROM {{ ref('stable_memories') }}
    ) all_memories
),

consolidation_metrics AS (
    -- Consolidation efficiency and health metrics
    SELECT 
        COUNT(*) as total_consolidating,
        COUNT(CASE WHEN consolidation_fate = 'cortical_transfer' THEN 1 END) as cortical_transfers,
        COUNT(CASE WHEN consolidation_fate = 'hippocampal_retention' THEN 1 END) as hippocampal_retentions,
        COUNT(CASE WHEN consolidation_fate = 'gradual_forgetting' THEN 1 END) as gradual_forgetting,
        COUNT(CASE WHEN consolidation_fate = 'rapid_forgetting' THEN 1 END) as rapid_forgetting,
        AVG(consolidated_strength) as avg_consolidation_strength,
        AVG(replay_strength) as avg_replay_strength,
        AVG(cortical_integration_strength) as avg_cortical_integration,
        MAX(consolidated_at) as last_consolidation,
        MIN(consolidated_at) as oldest_consolidation
    FROM {{ ref('memory_replay') }}
),

semantic_diversity AS (
    -- Measure semantic richness and diversity
    SELECT 
        COUNT(DISTINCT semantic_category) as unique_semantic_categories,
        COUNT(DISTINCT cortical_region) as cortical_distribution,
        AVG(retrieval_accessibility) as avg_retrieval_strength,
        COUNT(DISTINCT level_0_goal) as unique_goal_categories,
        COUNT(*) as total_semantic_memories
    FROM {{ ref('memory_replay') }}
    WHERE semantic_category IS NOT NULL
),

access_frequency_stats AS (
    -- Access patterns and frequency analysis
    SELECT 
        AVG(access_frequency) as avg_access_frequency,
        STDDEV(access_frequency) as access_frequency_stddev,
        MAX(access_frequency) as max_access_frequency,
        COUNT(CASE WHEN access_frequency >= 3 THEN 1 END) as highly_accessed_memories,
        SUM(access_frequency) as total_access_events
    FROM (
        SELECT access_count as access_frequency FROM {{ ref('active_memories') }}
        UNION ALL
        SELECT co_activation_count as access_frequency FROM {{ ref('stm_hierarchical_episodes') }}
        UNION ALL  
        SELECT access_count as access_frequency FROM {{ ref('stable_memories') }}
    ) all_access_patterns
),

system_performance AS (
    -- System-wide performance and capacity metrics  
    SELECT 
        -- Working memory capacity utilization (Miller's 7±2) - NULL SAFE
        COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'working_memory'), 0) as wm_current_load,
        COALESCE({{ var('working_memory_capacity') }}, 7) as wm_max_capacity,
        {{ safe_divide('COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = \'working_memory\'), 0) * 100.0', 'COALESCE(' ~ var('working_memory_capacity') ~ ', 7)', '0.0') }} as wm_utilization_pct,
        
        -- Short-term memory processing efficiency - NULL SAFE
        COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'short_term_memory'), 0) as stm_current_count,
        
        -- Long-term memory stability - NULL SAFE
        COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'long_term_memory'), 0) as ltm_stable_count,
        
        -- Consolidation efficiency ratio - NULL SAFE
        COALESCE(
            COALESCE((SELECT COALESCE(cortical_transfers, 0) + COALESCE(hippocampal_retentions, 0) FROM consolidation_metrics), 0) * 100.0 /
            NULLIF(COALESCE((SELECT total_consolidating FROM consolidation_metrics), 1), 0), 
            0.0
        ) as consolidation_success_rate
)

SELECT 
    -- Dashboard metadata
    CURRENT_TIMESTAMP as dashboard_updated_at,
    'biological_memory_health' as system_name,
    '1.0.0' as version,
    
    -- Memory distribution metrics - NULL SAFE
    COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'working_memory'), 0) as total_working_memories,
    COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'short_term_memory'), 0) as total_short_term_memories,
    COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'consolidating_memory'), 0) as total_consolidating_memories,
    COALESCE((SELECT total_memories FROM memory_distribution WHERE memory_type = 'long_term_memory'), 0) as total_long_term_memories,
    
    -- Memory age distribution
    ma.recent_memories,
    ma.week_old_memories,
    ma.month_old_memories,
    ma.remote_memories,
    ma.total_classified_memories,
    
    -- Biological health indicators - NULL SAFE
    COALESCE((SELECT AVG(COALESCE(avg_activation_strength, 0.1)) FROM memory_distribution), 0.1) as avg_system_activation,
    COALESCE((SELECT AVG(COALESCE(avg_hebbian_strength, 0.1)) FROM memory_distribution WHERE avg_hebbian_strength IS NOT NULL), 0.1) as avg_hebbian_strength,
    
    -- Consolidation health metrics - NULL SAFE
    COALESCE(cm.total_consolidating, 0) as total_consolidating,
    COALESCE(cm.cortical_transfers, 0) as cortical_transfers,
    COALESCE(cm.hippocampal_retentions, 0) as hippocampal_retentions,
    COALESCE(cm.avg_consolidation_strength, 0.1) as avg_consolidation_strength,
    COALESCE(cm.avg_replay_strength, 0.1) as avg_replay_strength,
    COALESCE(cm.avg_cortical_integration, 0.1) as avg_cortical_integration,
    COALESCE(cm.last_consolidation, NOW()) as last_consolidation,
    
    -- Semantic diversity metrics
    COALESCE(sd.unique_semantic_categories, 0) as semantic_category_diversity,
    COALESCE(sd.cortical_distribution, 0) as cortical_region_distribution,
    COALESCE(sd.avg_retrieval_strength, 0.0) as avg_retrieval_strength,
    COALESCE(sd.unique_goal_categories, 0) as goal_category_diversity,
    
    -- Access frequency statistics - NULL SAFE
    COALESCE(afs.avg_access_frequency, 0.0) as avg_access_frequency,
    COALESCE(afs.max_access_frequency, 0) as max_access_frequency,
    COALESCE(afs.highly_accessed_memories, 0) as highly_accessed_memories,
    COALESCE(afs.total_access_events, 0) as total_access_events,
    
    -- System performance metrics - NULL SAFE
    COALESCE(sp.wm_current_load, 0) as wm_current_load,
    COALESCE(sp.wm_max_capacity, 7) as wm_max_capacity,
    COALESCE(sp.wm_utilization_pct, 0.0) as wm_utilization_pct,
    COALESCE(sp.stm_current_count, 0) as stm_current_count,
    COALESCE(sp.ltm_stable_count, 0) as ltm_stable_count,
    COALESCE(sp.consolidation_success_rate, 0.0) as consolidation_success_rate,
    
    -- Health status assessment
    CASE 
        WHEN sp.wm_utilization_pct > 90 THEN 'OVERLOADED'
        WHEN sp.consolidation_success_rate < 50 THEN 'CONSOLIDATION_ISSUES'
        WHEN COALESCE(sd.semantic_category_diversity, 0) < 3 THEN 'LOW_SEMANTIC_DIVERSITY'
        WHEN cm.avg_consolidation_strength < 0.3 THEN 'WEAK_CONSOLIDATION'
        WHEN afs.avg_access_frequency < 1.0 THEN 'LOW_ACTIVITY'
        WHEN ma.recent_memories = 0 THEN 'NO_RECENT_ACTIVITY'
        ELSE 'HEALTHY'
    END as system_health_status,
    
    -- Performance alerting thresholds
    CASE 
        WHEN sp.wm_utilization_pct > 85 THEN 'WARNING: Working memory near capacity'
        WHEN sp.consolidation_success_rate < 60 THEN 'WARNING: Low consolidation efficiency'
        WHEN cm.avg_consolidation_strength < 0.4 THEN 'WARNING: Weak memory consolidation'
        WHEN afs.avg_access_frequency < 0.5 THEN 'INFO: Low system activity'
        ELSE 'System operating within normal parameters'
    END as performance_alert,
    
    -- Optimization recommendations
    CASE 
        WHEN sp.wm_utilization_pct > 90 
        THEN 'Increase consolidation frequency to reduce working memory load'
        WHEN sp.consolidation_success_rate < 50
        THEN 'Review consolidation thresholds and replay mechanisms'
        WHEN COALESCE(sd.semantic_category_diversity, 0) < 3
        THEN 'Enhance semantic association learning for better diversity'
        WHEN cm.avg_consolidation_strength < 0.3
        THEN 'Adjust Hebbian learning parameters for stronger consolidation'
        WHEN afs.avg_access_frequency < 1.0
        THEN 'System activity low - consider memory activation stimuli'
        ELSE 'System performing optimally'
    END as optimization_recommendation,
    
    -- BMP-007 Integration Status (for future enhancement)
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ltm_semantic_network')
        THEN 'BMP-007 semantic network model not yet available - using consolidation data'
        ELSE 'Full semantic network integration active'
    END as ltm_integration_status,
    
    -- Biological rhythm indicators
    EXTRACT(HOUR FROM CURRENT_TIMESTAMP) as current_hour,
    CASE 
        WHEN EXTRACT(HOUR FROM CURRENT_TIMESTAMP) BETWEEN 6 AND 22 THEN 'wake_hours'
        WHEN EXTRACT(HOUR FROM CURRENT_TIMESTAMP) BETWEEN 2 AND 4 THEN 'deep_consolidation_window'
        ELSE 'sleep_hours'
    END as circadian_phase

FROM memory_age_analysis ma
CROSS JOIN consolidation_metrics cm
CROSS JOIN semantic_diversity sd
CROSS JOIN access_frequency_stats afs
CROSS JOIN system_performance sp