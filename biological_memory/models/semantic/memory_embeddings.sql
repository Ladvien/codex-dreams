-- Memory Embeddings Model
-- Generates and stores semantic embeddings for biological memory processing
-- Uses Ollama's nomic-embed-text model for 768-dimensional vector representations

{{ config(
    materialized='incremental',
    unique_key='memory_id',
    on_schema_change='sync_all_columns',
    indexes=[
        {'columns': ['memory_id'], 'unique': true},
        {'columns': ['embedding_model'], 'unique': false},
        {'columns': ['created_at'], 'unique': false},
        {'columns': ['is_processed'], 'unique': false}
    ],
    pre_hook=[
        "SET threads TO 4",
        "SET memory_limit TO '2GB'"
    ],
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_embedding_similarity ON {{ this }} USING HNSW (combined_embedding) WITH (M=16, EF_CONSTRUCTION=64)",
        "ANALYZE {{ this }}"
    ]
) }}

WITH source_memories AS (
    SELECT 
        id as memory_id,
        content,
        context,
        summary,
        timestamp,
        importance_score,
        emotional_valence,
        tags
    FROM {{ ref('raw_memories') }}
    {% if is_incremental() %}
        -- Only process new memories since last run
        WHERE timestamp > (SELECT COALESCE(MAX(created_at), '1970-01-01'::TIMESTAMP) FROM {{ this }})
    {% endif %}
),

-- Generate embeddings via Ollama UDF (User Defined Function)
-- Note: This assumes we'll create a UDF to call Ollama API
embeddings_generated AS (
    SELECT 
        memory_id,
        content,
        context,
        summary,
        timestamp,
        importance_score,
        emotional_valence,
        tags,
        
        -- Generate embeddings for different text components
        -- These would be actual Ollama API calls in production
        {{ generate_embedding('content') }} as content_embedding,
        {{ generate_embedding('summary') }} as summary_embedding,
        {{ generate_embedding('context') }} as context_embedding,
        
        -- Model metadata
        '{{ var("embedding_model") }}' as embedding_model,
        '1.5' as model_version,
        768 as embedding_dimensions
    FROM source_memories
),

-- Combine embeddings with weighted average
combined_embeddings AS (
    SELECT 
        *,
        
        -- Weighted combination of embeddings
        -- Content: 50%, Summary: 30%, Context: 20%
        {{ combine_embeddings(
            'content_embedding', 
            'summary_embedding', 
            'context_embedding',
            weights=[0.5, 0.3, 0.2]
        ) }} as combined_embedding,
        
        -- L2 normalize the combined embedding
        {{ normalize_embedding('combined_embedding') }} as normalized_embedding,
        
        -- Processing metadata
        CURRENT_TIMESTAMP as created_at,
        CURRENT_TIMESTAMP as updated_at,
        TRUE as is_processed,
        FALSE as has_error
        
    FROM embeddings_generated
),

-- Calculate embedding statistics for monitoring
embedding_stats AS (
    SELECT 
        *,
        
        -- Calculate embedding magnitude (should be ~1.0 after normalization)
        {{ vector_magnitude('normalized_embedding') }} as embedding_magnitude,
        
        -- Calculate sparsity (percentage of near-zero values)
        {{ vector_sparsity('normalized_embedding', threshold=0.01) }} as embedding_sparsity,
        
        -- Processing time estimate (milliseconds)
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - timestamp)) * 1000 as processing_time_ms
        
    FROM combined_embeddings
)

SELECT 
    memory_id,
    content,
    context,
    summary,
    
    -- Embeddings
    content_embedding,
    summary_embedding,
    context_embedding,
    combined_embedding,
    normalized_embedding as final_embedding,
    
    -- Model metadata
    embedding_model,
    model_version,
    embedding_dimensions,
    
    -- Quality metrics
    embedding_magnitude,
    embedding_sparsity,
    importance_score,
    emotional_valence,
    
    -- Processing metadata
    created_at,
    updated_at,
    processing_time_ms,
    is_processed,
    has_error,
    
    -- Biological factors for consolidation
    importance_score * emotional_valence as consolidation_priority,
    tags
    
FROM embedding_stats
WHERE normalized_embedding IS NOT NULL
ORDER BY created_at DESC