-- =============================================================================
-- Dreams Schema: Processed Biological Memory Storage
-- =============================================================================
-- This schema stores all processed outputs from the biological memory pipeline
-- making them accessible for querying, analysis, and integration
-- =============================================================================

-- Create the dreams schema
CREATE SCHEMA IF NOT EXISTS dreams;

-- Grant permissions
GRANT USAGE ON SCHEMA dreams TO codex_user;
GRANT CREATE ON SCHEMA dreams TO codex_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA dreams TO codex_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA dreams TO codex_user;

-- =============================================================================
-- Working Memory: Active 5-minute attention window
-- =============================================================================
CREATE TABLE IF NOT EXISTS dreams.working_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL REFERENCES public.memories(id),
    
    -- Core content
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB,
    
    -- Semantic extraction
    entities TEXT[],
    topics TEXT[],
    sentiment VARCHAR(20),
    importance_score FLOAT,
    task_type VARCHAR(20), -- goal/task/action/observation
    phantom_objects JSONB,  -- Embodied cognition objects
    
    -- Working memory dynamics
    working_memory_strength FLOAT,
    recency_boost FLOAT,
    task_urgency_modifier FLOAT,
    final_priority FLOAT,
    wm_slot INTEGER, -- Miller's 7±2 position
    
    -- Biological features
    activation_strength FLOAT,
    access_count INTEGER DEFAULT 0,
    age_seconds INTEGER,
    hebbian_strength FLOAT,
    
    -- Metadata
    memory_type VARCHAR(50) DEFAULT 'working_memory',
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    snapshot_id UUID DEFAULT gen_random_uuid(), -- Groups snapshots together
    
    -- Indexes for performance
    CONSTRAINT unique_memory_snapshot UNIQUE(memory_id, snapshot_id)
);

CREATE INDEX idx_wm_timestamp ON dreams.working_memory(timestamp DESC);
CREATE INDEX idx_wm_priority ON dreams.working_memory(final_priority DESC);
CREATE INDEX idx_wm_snapshot ON dreams.working_memory(snapshot_id, processed_at DESC);

-- =============================================================================
-- Short-Term Memory: Hierarchical episodic memories
-- =============================================================================
CREATE TABLE IF NOT EXISTS dreams.short_term_episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL REFERENCES public.memories(id),
    
    -- Core content
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Hierarchical decomposition
    level_0_goal TEXT,
    level_1_tasks TEXT[],
    level_2_subtasks TEXT[],
    atomic_actions TEXT[],
    
    -- Spatial memory
    spatial_context JSONB, -- Egocentric and allocentric representations
    location_data JSONB,
    
    -- Biological features
    stm_strength FLOAT,
    recency_factor FLOAT,
    emotional_salience FLOAT,
    co_activation_count INTEGER DEFAULT 0,
    ready_for_consolidation BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    episode_type VARCHAR(50),
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    consolidation_attempts INTEGER DEFAULT 0,
    last_consolidation_attempt TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_stm_timestamp ON dreams.short_term_episodes(timestamp DESC);
CREATE INDEX idx_stm_consolidation ON dreams.short_term_episodes(ready_for_consolidation, stm_strength DESC);

-- =============================================================================
-- Long-Term Memory: Stable consolidated memories
-- =============================================================================
CREATE TABLE IF NOT EXISTS dreams.long_term_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL REFERENCES public.memories(id),
    
    -- Core content
    content TEXT NOT NULL,
    semantic_gist TEXT, -- Core meaning/insight
    
    -- Semantic features
    concepts TEXT[],
    knowledge_type VARCHAR(50), -- procedural/declarative/conditional
    abstraction_level INTEGER, -- 1-5 scale
    confidence_score FLOAT,
    
    -- Memory network
    semantic_associations INTEGER DEFAULT 0,
    avg_association_strength FLOAT,
    network_centrality FLOAT,
    clustering_coefficient FLOAT,
    
    -- Stability metrics
    stability_score FLOAT,
    importance_score FLOAT,
    retrieval_strength FLOAT,
    forgetting_rate FLOAT,
    
    -- Access patterns
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    access_rate_per_hour FLOAT,
    
    -- Consolidation metadata
    consolidated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    consolidation_source VARCHAR(50), -- sleep/wake/replay
    memory_age_at_consolidation INTEGER -- seconds
);

CREATE INDEX idx_ltm_concepts ON dreams.long_term_memories USING GIN(concepts);
CREATE INDEX idx_ltm_importance ON dreams.long_term_memories(importance_score DESC);
CREATE INDEX idx_ltm_stability ON dreams.long_term_memories(stability_score DESC);

-- =============================================================================
-- Semantic Network: Knowledge graph associations
-- =============================================================================
CREATE TABLE IF NOT EXISTS dreams.semantic_network (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Association structure
    concept_a TEXT NOT NULL,
    concept_b TEXT NOT NULL,
    association_type VARCHAR(50), -- causal/temporal/spatial/categorical
    association_strength FLOAT NOT NULL,
    
    -- Hebbian learning
    co_activation_count INTEGER DEFAULT 1,
    last_activation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    learning_rate FLOAT DEFAULT 0.1,
    
    -- Network metrics
    edge_weight FLOAT,
    bidirectional BOOLEAN DEFAULT FALSE,
    path_length INTEGER,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique associations
    CONSTRAINT unique_association UNIQUE(concept_a, concept_b, association_type)
);

CREATE INDEX idx_sn_concepts ON dreams.semantic_network(concept_a, concept_b);
CREATE INDEX idx_sn_strength ON dreams.semantic_network(association_strength DESC);

-- =============================================================================
-- Memory Insights: Extracted patterns and predictions
-- =============================================================================
CREATE TABLE IF NOT EXISTS dreams.memory_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Insight identification
    insight_type VARCHAR(50), -- pattern/prediction/principle/anomaly
    confidence_score FLOAT,
    
    -- Content
    insight_description TEXT NOT NULL,
    supporting_evidence JSONB, -- Memory IDs and excerpts
    
    -- Patterns discovered
    pattern_name VARCHAR(100),
    pattern_frequency INTEGER,
    pattern_examples TEXT[],
    
    -- Predictions made
    prediction_target VARCHAR(100),
    prediction_value TEXT,
    prediction_confidence FLOAT,
    prediction_timeframe VARCHAR(50),
    
    -- Validation
    validated BOOLEAN DEFAULT FALSE,
    validation_score FLOAT,
    validation_date TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    discovery_method VARCHAR(50),
    related_memories UUID[]
);

CREATE INDEX idx_insights_type ON dreams.memory_insights(insight_type, confidence_score DESC);
CREATE INDEX idx_insights_discovered ON dreams.memory_insights(discovered_at DESC);

-- =============================================================================
-- Processing Metrics: Performance and health tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS dreams.processing_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Session identification
    session_id UUID NOT NULL,
    batch_id UUID,
    processing_stage VARCHAR(50) NOT NULL,
    
    -- Performance metrics
    memories_processed INTEGER DEFAULT 0,
    successful_writes INTEGER DEFAULT 0,
    failed_writes INTEGER DEFAULT 0,
    processing_time_ms INTEGER,
    
    -- Resource usage
    duckdb_memory_mb FLOAT,
    postgres_connections INTEGER,
    cpu_percent FLOAT,
    
    -- Data quality
    data_quality_score FLOAT,
    validation_errors INTEGER DEFAULT 0,
    warnings TEXT[],
    
    -- Timestamps
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    processing_version VARCHAR(20),
    hostname VARCHAR(100),
    error_messages TEXT[]
);

CREATE INDEX idx_metrics_session ON dreams.processing_metrics(session_id, start_time DESC);
CREATE INDEX idx_metrics_stage ON dreams.processing_metrics(processing_stage, start_time DESC);

-- =============================================================================
-- Views for Easy Access
-- =============================================================================

-- Current working memory context (latest snapshot)
CREATE OR REPLACE VIEW dreams.current_context AS
WITH latest_snapshot AS (
    SELECT MAX(snapshot_id) as snapshot_id
    FROM dreams.working_memory
    WHERE processed_at > NOW() - INTERVAL '10 minutes'
)
SELECT wm.*
FROM dreams.working_memory wm
JOIN latest_snapshot ls ON wm.snapshot_id = ls.snapshot_id
ORDER BY wm.final_priority DESC;

-- Recent episodic memories (last 24 hours)
CREATE OR REPLACE VIEW dreams.recent_episodes AS
SELECT *
FROM dreams.short_term_episodes
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Knowledge graph view
CREATE OR REPLACE VIEW dreams.knowledge_graph AS
SELECT 
    sn.*,
    ltm_a.semantic_gist as concept_a_meaning,
    ltm_b.semantic_gist as concept_b_meaning
FROM dreams.semantic_network sn
LEFT JOIN dreams.long_term_memories ltm_a 
    ON ltm_a.concepts @> ARRAY[sn.concept_a]
LEFT JOIN dreams.long_term_memories ltm_b
    ON ltm_b.concepts @> ARRAY[sn.concept_b]
ORDER BY sn.association_strength DESC;

-- Memory timeline view
CREATE OR REPLACE VIEW dreams.memory_timeline AS
SELECT 
    'working' as stage,
    memory_id,
    content,
    timestamp,
    importance_score,
    processed_at
FROM dreams.working_memory
UNION ALL
SELECT 
    'short_term' as stage,
    memory_id,
    content,
    timestamp,
    emotional_salience as importance_score,
    processed_at
FROM dreams.short_term_episodes
UNION ALL
SELECT 
    'long_term' as stage,
    memory_id,
    content,
    consolidated_at as timestamp,
    importance_score,
    consolidated_at as processed_at
FROM dreams.long_term_memories
ORDER BY timestamp DESC;

-- =============================================================================
-- Functions for Data Management
-- =============================================================================

-- Function to clean old working memory snapshots
CREATE OR REPLACE FUNCTION dreams.cleanup_old_snapshots()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM dreams.working_memory
    WHERE processed_at < NOW() - INTERVAL '7 days'
    AND snapshot_id NOT IN (
        SELECT DISTINCT snapshot_id 
        FROM dreams.working_memory 
        WHERE processed_at > NOW() - INTERVAL '7 days'
    );
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get memory statistics
CREATE OR REPLACE FUNCTION dreams.get_memory_stats()
RETURNS TABLE(
    stage VARCHAR,
    record_count BIGINT,
    oldest_record TIMESTAMP WITH TIME ZONE,
    newest_record TIMESTAMP WITH TIME ZONE,
    avg_importance FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'working_memory'::VARCHAR as stage,
        COUNT(*) as record_count,
        MIN(timestamp) as oldest_record,
        MAX(timestamp) as newest_record,
        AVG(importance_score) as avg_importance
    FROM dreams.working_memory
    UNION ALL
    SELECT 
        'short_term_episodes'::VARCHAR,
        COUNT(*),
        MIN(timestamp),
        MAX(timestamp),
        AVG(emotional_salience)
    FROM dreams.short_term_episodes
    UNION ALL
    SELECT 
        'long_term_memories'::VARCHAR,
        COUNT(*),
        MIN(consolidated_at),
        MAX(consolidated_at),
        AVG(importance_score)
    FROM dreams.long_term_memories;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON SCHEMA dreams IS 'Processed biological memory storage from DuckDB analytical pipeline';
COMMENT ON TABLE dreams.working_memory IS 'Active working memory snapshots with 5-minute attention window';
COMMENT ON TABLE dreams.short_term_episodes IS 'Hierarchical episodic memories awaiting consolidation';
COMMENT ON TABLE dreams.long_term_memories IS 'Stable consolidated memories with semantic enrichment';
COMMENT ON TABLE dreams.semantic_network IS 'Knowledge graph of concept associations';
COMMENT ON TABLE dreams.memory_insights IS 'Extracted patterns, predictions, and principles';
COMMENT ON TABLE dreams.processing_metrics IS 'Performance and health metrics for the pipeline';