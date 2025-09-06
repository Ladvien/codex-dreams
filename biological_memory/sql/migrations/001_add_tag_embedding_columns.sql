-- Migration: Add Tag Embedding Support to memories table
-- Description: Extends the memories table with tag embedding columns for semantic search
-- Created: 2025-09-06
-- Dependencies: pgvector extension must be installed

-- Check if pgvector extension is available
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE EXCEPTION 'pgvector extension is not installed. Please install it first: CREATE EXTENSION vector;';
    END IF;
END
$$;

-- Add tag embedding columns to memories table (non-destructive)
ALTER TABLE public.memories
ADD COLUMN IF NOT EXISTS tag_embedding vector(768),
ADD COLUMN IF NOT EXISTS tag_embedding_reduced vector(256),
ADD COLUMN IF NOT EXISTS tag_embedding_updated timestamp with time zone;

-- Add comment documentation for the new columns
COMMENT ON COLUMN public.memories.tag_embedding IS 'Semantic embedding of memory tags using nomic-embed-text model (768 dimensions)';
COMMENT ON COLUMN public.memories.tag_embedding_reduced IS 'Dimensionality-reduced tag embedding for fast similarity search (256 dimensions)';
COMMENT ON COLUMN public.memories.tag_embedding_updated IS 'Timestamp when tag embedding was last generated or updated';

-- Create optimized HNSW indexes for tag similarity search
-- These indexes use lower parameters than content embeddings since tag embeddings are typically simpler
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_tag_embedding_hnsw
ON public.memories USING hnsw (tag_embedding vector_cosine_ops)
WITH (m = 8, ef_construction = 64);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_tag_embedding_reduced_hnsw
ON public.memories USING hnsw (tag_embedding_reduced vector_cosine_ops)
WITH (m = 6, ef_construction = 32);

-- Add index on tag embedding update timestamp for monitoring freshness
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_tag_embedding_updated
ON public.memories (tag_embedding_updated)
WHERE tag_embedding_updated IS NOT NULL;

-- Add partial index for memories that have tags but no tag embeddings (for processing monitoring)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_missing_tag_embeddings
ON public.memories (created_at)
WHERE tags IS NOT NULL
AND array_length(tags, 1) > 0
AND tag_embedding IS NULL;

-- Create a view for tag embedding statistics (helpful for monitoring)
CREATE OR REPLACE VIEW public.tag_embedding_stats AS
SELECT
    COUNT(*) as total_memories,
    COUNT(*) FILTER (WHERE tags IS NOT NULL AND array_length(tags, 1) > 0) as memories_with_tags,
    COUNT(*) FILTER (WHERE tag_embedding IS NOT NULL) as memories_with_tag_embeddings,
    COUNT(*) FILTER (WHERE tags IS NOT NULL AND array_length(tags, 1) > 0 AND tag_embedding IS NULL) as missing_tag_embeddings,
    ROUND(
        (COUNT(*) FILTER (WHERE tag_embedding IS NOT NULL)::FLOAT /
         NULLIF(COUNT(*) FILTER (WHERE tags IS NOT NULL AND array_length(tags, 1) > 0), 0)) * 100,
        2
    ) as tag_embedding_coverage_percent,
    MIN(tag_embedding_updated) as earliest_tag_embedding,
    MAX(tag_embedding_updated) as latest_tag_embedding
FROM public.memories;

COMMENT ON VIEW public.tag_embedding_stats IS 'Statistics view for monitoring tag embedding coverage and freshness';

-- Function to check tag embedding health
CREATE OR REPLACE FUNCTION public.check_tag_embedding_health()
RETURNS TABLE (
    check_name text,
    status text,
    details text
) AS $$
BEGIN
    -- Check overall coverage
    RETURN QUERY
    WITH stats AS (SELECT * FROM public.tag_embedding_stats)
    SELECT
        'coverage'::text,
        CASE
            WHEN s.tag_embedding_coverage_percent >= 95 THEN 'healthy'
            WHEN s.tag_embedding_coverage_percent >= 80 THEN 'degraded'
            ELSE 'unhealthy'
        END::text,
        format('%s%% of tagged memories have embeddings (%s/%s)',
               s.tag_embedding_coverage_percent,
               s.memories_with_tag_embeddings,
               s.memories_with_tags)::text
    FROM stats s;

    -- Check freshness
    RETURN QUERY
    SELECT
        'freshness'::text,
        CASE
            WHEN MAX(tag_embedding_updated) > NOW() - INTERVAL '24 hours' THEN 'healthy'
            WHEN MAX(tag_embedding_updated) > NOW() - INTERVAL '72 hours' THEN 'degraded'
            ELSE 'stale'
        END::text,
        format('Latest tag embedding: %s', MAX(tag_embedding_updated))::text
    FROM public.memories
    WHERE tag_embedding_updated IS NOT NULL;

    -- Check for backlog
    RETURN QUERY
    SELECT
        'processing_backlog'::text,
        CASE
            WHEN COUNT(*) = 0 THEN 'healthy'
            WHEN COUNT(*) < 100 THEN 'manageable'
            ELSE 'backlogged'
        END::text,
        format('%s memories with tags need tag embeddings', COUNT(*))::text
    FROM public.memories
    WHERE tags IS NOT NULL
    AND array_length(tags, 1) > 0
    AND tag_embedding IS NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION public.check_tag_embedding_health() IS 'Health check function for tag embedding processing';

-- Log the migration completion
DO $$
BEGIN
    RAISE NOTICE 'Tag embedding migration completed successfully';
    RAISE NOTICE 'Added columns: tag_embedding, tag_embedding_reduced, tag_embedding_updated';
    RAISE NOTICE 'Created HNSW indexes for tag similarity search';
    RAISE NOTICE 'Created monitoring views and functions';
    RAISE NOTICE 'To check health: SELECT * FROM public.check_tag_embedding_health();';
    RAISE NOTICE 'To monitor coverage: SELECT * FROM public.tag_embedding_stats;';
END;
$$;
