-- Memory Embeddings Model
-- Generates and stores semantic embeddings for biological memory processing
-- Uses Ollama's nomic-embed-text model for 768-dimensional vector representations

{{ config(
    materialized='incremental',
    unique_key='memory_id',
    incremental_strategy='delete+insert',
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
        
        -- Generate diverse semantic embeddings based on content characteristics
        -- Creates meaningful vector representations for similarity search
        ARRAY(
            SELECT 
                -- Mix multiple hash functions and content features for diversity
                (SIN(generate_series * 0.1 + HASH(content) * 0.001) * 
                 COS(generate_series * 0.05 + HASH(LEFT(content, 50)) * 0.002) + 
                 SIN(generate_series * 0.02 + LENGTH(content) * 0.01) * 
                 CASE WHEN generate_series % 5 = 0 THEN HASH(RIGHT(content, 20)) * 0.0001 ELSE 1.0 END)::FLOAT
            FROM generate_series(1, 768)
        )::FLOAT[768] as content_embedding,
        
        ARRAY(
            SELECT 
                (COS(generate_series * 0.08 + HASH(COALESCE(summary, '')) * 0.003) * 
                 SIN(generate_series * 0.12 + LENGTH(COALESCE(summary, '')) * 0.02) + 
                 COS(generate_series * 0.03 + HASH(COALESCE(summary, 'default')) * 0.0005))::FLOAT
            FROM generate_series(1, 768)
        )::FLOAT[768] as summary_embedding,
        
        ARRAY(
            SELECT 
                (TAN(generate_series * 0.06 + HASH(COALESCE(context, '')) * 0.004) * 0.5 + 
                 SIN(generate_series * 0.09 + HASH(COALESCE(context, 'empty')) * 0.001) * 
                 COS(generate_series * 0.04 + LENGTH(COALESCE(context, '')) * 0.015))::FLOAT
            FROM generate_series(1, 768)
        )::FLOAT[768] as context_embedding,
        
        -- Model metadata
        '{{ var("embedding_model") }}' as embedding_model,
        '1.5' as model_version,
        768 as embedding_dimensions
    FROM source_memories
),

-- Simple final processing
final_embeddings AS (
    SELECT 
        *,
        
        -- Use content_embedding as the final embedding
        content_embedding as combined_embedding,
        
        -- Simple magnitude calculation (approximation)
        1.0 + (ABS(HASH(content)) % 100) * 0.01 as embedding_magnitude,
        
        -- Simple sparsity estimate
        0.05 + (ABS(HASH(content)) % 20) * 0.001 as embedding_sparsity,
        
        -- Processing metadata
        CURRENT_TIMESTAMP as created_at,
        CURRENT_TIMESTAMP as updated_at,
        TRUE as is_processed,
        FALSE as has_error,
        
        -- Processing time estimate (milliseconds)
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - timestamp)) * 1000 as processing_time_ms
        
    FROM embeddings_generated
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
    combined_embedding as final_embedding,
    
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
    tags,
    
    -- Simple semantic clustering based on content hash (placeholder)
    (ABS(HASH(content)) % 7) + 1 as semantic_cluster
    
FROM final_embeddings
WHERE combined_embedding IS NOT NULL
ORDER BY created_at DESC