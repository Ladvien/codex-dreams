-- Raw Memories Source Table
-- Base memories from PostgreSQL/DuckDB source for biological processing
-- This model serves as the entry point for the 4-stage memory pipeline

{{ config(
    materialized='view'
) }}

SELECT
    -- Core memory fields
    id,
    content,
    created_at as timestamp,

    -- Memory metadata
    COALESCE(metadata->>'importance', '0.5')::FLOAT as importance_score,
    COALESCE(metadata->>'activation', '0.5')::FLOAT as activation_strength,
    COALESCE(metadata->>'access_count', '0')::INTEGER as access_count,
    metadata,

    -- Biological memory attributes
    COALESCE(metadata->>'emotional_valence', '0.0')::FLOAT as emotional_valence,
    COALESCE(metadata->>'novelty', '0.5')::FLOAT as novelty_score,

    -- Context for semantic processing
    COALESCE(metadata->>'context', '')::TEXT as context,
    COALESCE(metadata->>'summary', '')::TEXT as summary,

    -- Tags for categorization
    tags

FROM (
    -- Source from PostgreSQL using DuckDB's postgres_scanner with full connection string
    SELECT * FROM postgres_scan(
        '{{ var("postgres_url") }}',
        'public',
        'memories'
    )
) as source_memories
WHERE content IS NOT NULL
  AND TRIM(content) != ''
