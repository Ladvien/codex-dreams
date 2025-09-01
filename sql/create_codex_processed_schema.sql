-- Create codex_processed schema for storing processed memory results from DuckDB
-- This schema contains the write-back mechanism for biological memory processing pipeline

-- Create the schema for processed memory results
CREATE SCHEMA IF NOT EXISTS codex_processed;

-- Set search path to include both schemas
SET search_path = codex_processed, public;

-- ================================================================
-- PROCESSED MEMORIES TABLE
-- Stores enhanced memory data with biological processing results
-- ================================================================
CREATE TABLE IF NOT EXISTS codex_processed.processed_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_memory_id UUID NOT NULL REFERENCES public.memories(id) ON DELETE CASCADE,
    
    -- Memory hierarchy from short-term memory processing
    level_0_goal TEXT,
    level_1_tasks TEXT[],
    level_2_actions TEXT[],
    phantom_objects JSONB,
    
    -- Biological memory processing results
    stm_strength NUMERIC(5,3) DEFAULT 0.0 CHECK (stm_strength >= 0.0 AND stm_strength <= 1.0),
    emotional_salience NUMERIC(5,3) DEFAULT 0.0 CHECK (emotional_salience >= 0.0 AND emotional_salience <= 1.0),
    recency_factor NUMERIC(5,3) DEFAULT 1.0 CHECK (recency_factor >= 0.0 AND recency_factor <= 1.0),
    
    -- Consolidation results
    consolidated_strength NUMERIC(5,3) DEFAULT 0.0 CHECK (consolidated_strength >= 0.0 AND consolidated_strength <= 1.0),
    consolidation_fate TEXT CHECK (consolidation_fate IN ('cortical_transfer', 'hippocampal_retention', 'gradual_forgetting', 'rapid_forgetting')),
    hebbian_strength NUMERIC(5,3) DEFAULT 0.0,
    
    -- Semantic processing results
    concepts TEXT[],
    semantic_gist TEXT,
    semantic_category TEXT,
    cortical_region TEXT,
    
    -- Retrieval and accessibility
    retrieval_accessibility NUMERIC(5,3) DEFAULT 0.0 CHECK (retrieval_accessibility >= 0.0 AND retrieval_accessibility <= 1.0),
    memory_status TEXT DEFAULT 'processed' CHECK (memory_status IN ('processed', 'consolidated', 'archived')),
    
    -- Processing metadata
    processing_stage TEXT DEFAULT 'complete' CHECK (processing_stage IN ('working_memory', 'short_term', 'consolidation', 'long_term', 'complete')),
    processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    processing_version TEXT DEFAULT '1.0.0',
    
    -- Quality metrics
    processing_quality_score NUMERIC(5,3) DEFAULT 0.0 CHECK (processing_quality_score >= 0.0 AND processing_quality_score <= 1.0),
    confidence_score NUMERIC(5,3) DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    
    CONSTRAINT fk_processed_memories_source FOREIGN KEY (source_memory_id) REFERENCES public.memories(id)
);

-- ================================================================
-- GENERATED INSIGHTS TABLE  
-- Stores AI-generated insights and analysis from memory processing
-- ================================================================
CREATE TABLE IF NOT EXISTS codex_processed.generated_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_memory_ids UUID[] NOT NULL, -- Can reference multiple memories
    
    -- Insight content and classification
    insight_text TEXT NOT NULL,
    insight_type TEXT NOT NULL CHECK (insight_type IN ('pattern', 'connection', 'trend', 'anomaly', 'prediction', 'summary')),
    insight_category TEXT CHECK (insight_category IN ('strategic', 'operational', 'behavioral', 'temporal', 'semantic', 'creative')),
    
    -- LLM processing metadata
    llm_model TEXT DEFAULT 'gpt-oss:20b',
    llm_temperature NUMERIC(3,2) DEFAULT 0.7,
    llm_prompt_template TEXT,
    
    -- Quality and confidence metrics
    insight_confidence NUMERIC(5,3) DEFAULT 0.0 CHECK (insight_confidence >= 0.0 AND insight_confidence <= 1.0),
    novelty_score NUMERIC(5,3) DEFAULT 0.0 CHECK (novelty_score >= 0.0 AND novelty_score <= 1.0),
    relevance_score NUMERIC(5,3) DEFAULT 0.0 CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
    
    -- Suggested tags and connections
    suggested_tags TEXT[],
    related_concepts TEXT[],
    
    -- Processing metadata
    generated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    processing_duration_ms INTEGER,
    insight_status TEXT DEFAULT 'active' CHECK (insight_status IN ('active', 'archived', 'superseded')),
    
    -- Validation and feedback
    human_validated BOOLEAN DEFAULT FALSE,
    validation_feedback TEXT,
    validated_at TIMESTAMPTZ,
    validated_by TEXT
);

-- ================================================================
-- MEMORY ASSOCIATIONS TABLE
-- Stores discovered connections and associations between memories
-- ================================================================
CREATE TABLE IF NOT EXISTS codex_processed.memory_associations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_memory_id UUID NOT NULL REFERENCES public.memories(id) ON DELETE CASCADE,
    target_memory_id UUID NOT NULL REFERENCES public.memories(id) ON DELETE CASCADE,
    
    -- Association metadata
    association_type TEXT NOT NULL CHECK (association_type IN ('semantic', 'temporal', 'causal', 'hierarchical', 'creative', 'concept_based')),
    association_strength NUMERIC(5,3) NOT NULL CHECK (association_strength >= 0.0 AND association_strength <= 1.0),
    
    -- Semantic similarity and connection details
    semantic_similarity NUMERIC(5,3) DEFAULT 0.0 CHECK (semantic_similarity >= 0.0 AND semantic_similarity <= 1.0),
    co_occurrence_count INTEGER DEFAULT 1,
    shared_concepts TEXT[],
    connection_reason TEXT,
    
    -- Biological learning parameters
    hebbian_weight NUMERIC(5,3) DEFAULT 0.1,
    synaptic_strength NUMERIC(5,3) DEFAULT 0.0 CHECK (synaptic_strength >= 0.0 AND synaptic_strength <= 1.0),
    forward_strength NUMERIC(5,3) DEFAULT 0.0,
    backward_strength NUMERIC(5,3) DEFAULT 0.0,
    
    -- Quality and temporal factors
    association_quality TEXT CHECK (association_quality IN ('strong_semantic', 'strong_temporal', 'strong_frequency', 'moderate', 'weak')),
    recent_co_occurrences INTEGER DEFAULT 0,
    weekly_co_occurrences INTEGER DEFAULT 0,
    
    -- Processing and maintenance
    discovered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_strengthened_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    decay_rate NUMERIC(5,3) DEFAULT 0.05,
    last_activated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_memory_assoc_source FOREIGN KEY (source_memory_id) REFERENCES public.memories(id),
    CONSTRAINT fk_memory_assoc_target FOREIGN KEY (target_memory_id) REFERENCES public.memories(id),
    CONSTRAINT no_self_reference CHECK (source_memory_id != target_memory_id)
);

-- ================================================================
-- PROCESSING METADATA TABLE
-- Tracks pipeline processing status, performance, and metadata
-- ================================================================
CREATE TABLE IF NOT EXISTS codex_processed.processing_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Processing session identification
    processing_session_id UUID DEFAULT gen_random_uuid(),
    batch_id TEXT NOT NULL,
    processing_stage TEXT NOT NULL CHECK (processing_stage IN ('working_memory', 'short_term_memory', 'consolidation', 'long_term_memory', 'insights', 'complete')),
    
    -- Memory processing scope
    source_memory_ids UUID[],
    total_memories_processed INTEGER DEFAULT 0,
    successful_processing_count INTEGER DEFAULT 0,
    failed_processing_count INTEGER DEFAULT 0,
    
    -- Performance metrics
    processing_start_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    processing_end_time TIMESTAMPTZ,
    processing_duration_seconds NUMERIC(10,3),
    average_memory_processing_time_ms NUMERIC(8,2),
    
    -- Resource utilization
    peak_memory_usage_mb NUMERIC(10,2),
    llm_calls_made INTEGER DEFAULT 0,
    llm_total_duration_ms INTEGER DEFAULT 0,
    dbt_models_executed TEXT[],
    
    -- Quality and validation metrics
    processing_quality_score NUMERIC(5,3) DEFAULT 0.0 CHECK (processing_quality_score >= 0.0 AND processing_quality_score <= 1.0),
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    error_messages TEXT[],
    
    -- Configuration used
    dbt_vars_used JSONB,
    model_versions JSONB,
    environment_config JSONB,
    
    -- Status tracking
    processing_status TEXT DEFAULT 'running' CHECK (processing_status IN ('started', 'running', 'completed', 'failed', 'partial')),
    completion_percentage NUMERIC(5,2) DEFAULT 0.0 CHECK (completion_percentage >= 0.0 AND completion_percentage <= 100.0),
    
    -- Biological rhythm context
    consolidation_cycle_type TEXT CHECK (consolidation_cycle_type IN ('continuous', 'rapid', 'hourly', 'deep_sleep', 'rem_sleep', 'weekly')),
    circadian_phase TEXT CHECK (circadian_phase IN ('wake', 'light_sleep', 'deep_sleep', 'rem_sleep')),
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- INDEXES FOR PERFORMANCE OPTIMIZATION
-- ================================================================

-- Primary lookup indexes
CREATE INDEX IF NOT EXISTS idx_processed_memories_source_id ON codex_processed.processed_memories(source_memory_id);
CREATE INDEX IF NOT EXISTS idx_processed_memories_strength ON codex_processed.processed_memories(consolidated_strength DESC, processed_at DESC);
CREATE INDEX IF NOT EXISTS idx_processed_memories_status ON codex_processed.processed_memories(memory_status, processing_stage);
CREATE INDEX IF NOT EXISTS idx_processed_memories_processed_at ON codex_processed.processed_memories(processed_at DESC);

-- Insight discovery indexes
CREATE INDEX IF NOT EXISTS idx_generated_insights_memory_ids ON codex_processed.generated_insights USING GIN(source_memory_ids);
CREATE INDEX IF NOT EXISTS idx_generated_insights_type ON codex_processed.generated_insights(insight_type, insight_category);
CREATE INDEX IF NOT EXISTS idx_generated_insights_confidence ON codex_processed.generated_insights(insight_confidence DESC, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_insights_tags ON codex_processed.generated_insights USING GIN(suggested_tags);

-- Association graph indexes  
CREATE INDEX IF NOT EXISTS idx_memory_assoc_source ON codex_processed.memory_associations(source_memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_assoc_target ON codex_processed.memory_associations(target_memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_assoc_strength ON codex_processed.memory_associations(association_strength DESC, last_activated_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_assoc_type_quality ON codex_processed.memory_associations(association_type, association_quality);
CREATE INDEX IF NOT EXISTS idx_memory_assoc_concepts ON codex_processed.memory_associations USING GIN(shared_concepts);

-- Processing tracking indexes
CREATE INDEX IF NOT EXISTS idx_processing_meta_session ON codex_processed.processing_metadata(processing_session_id);
CREATE INDEX IF NOT EXISTS idx_processing_meta_batch ON codex_processed.processing_metadata(batch_id);
CREATE INDEX IF NOT EXISTS idx_processing_meta_stage_status ON codex_processed.processing_metadata(processing_stage, processing_status);
CREATE INDEX IF NOT EXISTS idx_processing_meta_time ON codex_processed.processing_metadata(processing_start_time DESC);

-- ================================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMP UPDATES
-- ================================================================

-- Update timestamp trigger for processed_memories
CREATE OR REPLACE FUNCTION update_last_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_processed_memories_updated_at
    BEFORE UPDATE ON codex_processed.processed_memories
    FOR EACH ROW
    EXECUTE FUNCTION update_last_updated_at();

CREATE TRIGGER trigger_processing_metadata_updated_at
    BEFORE UPDATE ON codex_processed.processing_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_last_updated_at();

-- ================================================================
-- VIEWS FOR COMMON QUERIES
-- ================================================================

-- Recent processing activity view
CREATE OR REPLACE VIEW codex_processed.recent_processing_activity AS
SELECT 
    pm.batch_id,
    pm.processing_stage,
    pm.processing_status,
    pm.total_memories_processed,
    pm.processing_duration_seconds,
    pm.processing_quality_score,
    pm.created_at
FROM codex_processed.processing_metadata pm
WHERE pm.created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
ORDER BY pm.created_at DESC;

-- High-quality insights view
CREATE OR REPLACE VIEW codex_processed.high_quality_insights AS
SELECT 
    gi.id,
    gi.insight_text,
    gi.insight_type,
    gi.insight_category,
    gi.insight_confidence,
    gi.novelty_score,
    gi.relevance_score,
    gi.suggested_tags,
    gi.generated_at
FROM codex_processed.generated_insights gi
WHERE gi.insight_confidence >= 0.7
  AND gi.relevance_score >= 0.6
  AND gi.insight_status = 'active'
ORDER BY gi.insight_confidence DESC, gi.novelty_score DESC;

-- Strong memory associations view  
CREATE OR REPLACE VIEW codex_processed.strong_associations AS
SELECT 
    ma.source_memory_id,
    ma.target_memory_id,
    ma.association_type,
    ma.association_strength,
    ma.association_quality,
    ma.shared_concepts,
    ma.connection_reason,
    ma.last_activated_at
FROM codex_processed.memory_associations ma
WHERE ma.association_strength >= 0.7
  AND ma.association_quality IN ('strong_semantic', 'strong_temporal', 'strong_frequency')
ORDER BY ma.association_strength DESC;

-- Grant appropriate permissions
GRANT USAGE ON SCHEMA codex_processed TO codex_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA codex_processed TO codex_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA codex_processed TO codex_user;
GRANT SELECT ON ALL VIEWS IN SCHEMA codex_processed TO codex_user;

COMMENT ON SCHEMA codex_processed IS 'Schema for storing processed biological memory results from DuckDB pipeline';
COMMENT ON TABLE codex_processed.processed_memories IS 'Enhanced memory data with biological processing results including consolidation and semantic analysis';
COMMENT ON TABLE codex_processed.generated_insights IS 'AI-generated insights and patterns discovered through memory analysis';
COMMENT ON TABLE codex_processed.memory_associations IS 'Discovered connections and relationships between memories with biological learning parameters';
COMMENT ON TABLE codex_processed.processing_metadata IS 'Pipeline processing tracking, performance metrics, and execution metadata';