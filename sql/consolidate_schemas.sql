-- =============================================================================
-- Schema Consolidation: Merge codex_processed into dreams
-- =============================================================================
-- The codex_processed and dreams schemas serve the same purpose - storing
-- processed biological memory results. This script consolidates them into
-- the dreams schema for simplicity.
-- =============================================================================

-- Step 1: Ensure dreams schema has all necessary tables from codex_processed design
-- The dreams schema already has better versions of these tables:
-- - codex_processed.processed_memories -> dreams.long_term_memories
-- - codex_processed.memory_associations -> dreams.semantic_network
-- - codex_processed.generated_insights -> dreams.memory_insights
-- - codex_processed.processing_metadata -> dreams.processing_metrics

-- Step 2: Create compatibility views in dreams schema for backward compatibility
CREATE OR REPLACE VIEW dreams.processed_memories AS
SELECT 
    id,
    memory_id as source_memory_id,
    content,
    semantic_gist,
    concepts as discovered_concepts,
    knowledge_type,
    confidence_score,
    importance_score as relevance_score,
    consolidated_at as processed_at
FROM dreams.long_term_memories;

CREATE OR REPLACE VIEW dreams.memory_associations AS
SELECT 
    id,
    concept_a,
    concept_b,
    association_strength,
    association_type,
    co_activation_count as frequency,
    created_at as discovered_at
FROM dreams.semantic_network;

CREATE OR REPLACE VIEW dreams.generated_insights AS
SELECT 
    id,
    insight_type,
    insight_description as insight_text,
    confidence_score,
    pattern_name,
    discovered_at as generated_at
FROM dreams.memory_insights;

CREATE OR REPLACE VIEW dreams.processing_metadata AS
SELECT 
    id,
    session_id,
    processing_stage,
    memories_processed as total_processed,
    successful_writes,
    failed_writes,
    start_time,
    end_time
FROM dreams.processing_metrics;

-- Step 3: Grant permissions on new views
GRANT SELECT ON ALL TABLES IN SCHEMA dreams TO codex_user;
GRANT SELECT ON dreams.processed_memories TO codex_user;
GRANT SELECT ON dreams.memory_associations TO codex_user;
GRANT SELECT ON dreams.generated_insights TO codex_user;
GRANT SELECT ON dreams.processing_metadata TO codex_user;

-- Step 4: Create the semantic_memory table from original architecture (if needed)
-- This provides the high-level knowledge store originally envisioned
CREATE TABLE IF NOT EXISTS dreams.semantic_memory (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_memory_id UUID NOT NULL REFERENCES public.memories(id),

    -- Semantic content (what we learned)
    semantic_gist TEXT NOT NULL,
    knowledge_type VARCHAR(50),      -- procedural/declarative/conditional
    abstraction_level INTEGER,       -- How abstract (1-5)
    confidence_score FLOAT,

    -- Categorization
    semantic_category VARCHAR(100),  -- Domain of knowledge
    cortical_region VARCHAR(50),     -- Metaphorical brain region

    -- Discovered knowledge
    patterns TEXT[],                 -- Recurring patterns found
    insights TEXT[],                 -- Key insights extracted
    predictions TEXT[],              -- Predictive rules learned
    principles TEXT[],               -- Abstract principles
    contradictions TEXT[],           -- Noted exceptions

    -- Knowledge graph connections
    related_concepts TEXT[],         -- Connected ideas
    integration_points TEXT[],       -- How this connects to existing knowledge

    -- Retrieval optimization
    retrieval_strength FLOAT,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    processing_version VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Full-text search
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english',
            semantic_gist || ' ' ||
            COALESCE(array_to_string(patterns, ' '), '') || ' ' ||
            COALESCE(array_to_string(insights, ' '), '')
        )
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_semantic_memory_search ON dreams.semantic_memory USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_semantic_memory_source ON dreams.semantic_memory(source_memory_id);
CREATE INDEX IF NOT EXISTS idx_semantic_memory_category ON dreams.semantic_memory(semantic_category);

-- Step 5: Drop the redundant codex_processed schema (only if empty)
DO $$
DECLARE
    table_count INTEGER;
    data_count INTEGER;
BEGIN
    -- Check if schema exists and count tables
    SELECT COUNT(*)
    INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'codex_processed';
    
    -- Check if any tables have data
    SELECT SUM(row_count)
    INTO data_count
    FROM (
        SELECT COUNT(*) as row_count FROM codex_processed.processed_memories
        UNION ALL
        SELECT COUNT(*) FROM codex_processed.memory_associations
        UNION ALL
        SELECT COUNT(*) FROM codex_processed.generated_insights
        UNION ALL
        SELECT COUNT(*) FROM codex_processed.processing_metadata
    ) counts;
    
    -- Only drop if empty
    IF table_count > 0 AND (data_count IS NULL OR data_count = 0) THEN
        DROP SCHEMA IF EXISTS codex_processed CASCADE;
        RAISE NOTICE 'Dropped empty codex_processed schema';
    ELSIF data_count > 0 THEN
        RAISE NOTICE 'codex_processed schema contains data - not dropping';
    ELSE
        RAISE NOTICE 'codex_processed schema does not exist';
    END IF;
END $$;

-- Step 6: Update comments for documentation
COMMENT ON SCHEMA dreams IS 'Unified schema for all processed biological memory data (consolidated from codex_processed)';
COMMENT ON VIEW dreams.processed_memories IS 'Compatibility view for legacy codex_processed.processed_memories';
COMMENT ON VIEW dreams.memory_associations IS 'Compatibility view for legacy codex_processed.memory_associations';
COMMENT ON VIEW dreams.generated_insights IS 'Compatibility view for legacy codex_processed.generated_insights';
COMMENT ON VIEW dreams.processing_metadata IS 'Compatibility view for legacy codex_processed.processing_metadata';
COMMENT ON TABLE dreams.semantic_memory IS 'High-level semantic knowledge store from original architecture';

-- Summary of consolidation:
-- 1. biological_memory schema - KEPT for dbt source data
-- 2. codex_processed schema - DROPPED (merged into dreams)
-- 3. dreams schema - PRIMARY schema for all processed memory data