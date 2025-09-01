{#
  Optimized Long-Term Memory Semantic Network Model (BMP-012)
  
  Performance optimizations:
  - Adaptive cortical clustering instead of static minicolumn generation
  - Optimized vector similarity operations with caching  
  - Batch processing for vector operations
  - Incremental materialization support
  - Connection pooling optimizations
  - Performance monitoring integration
  
  Target: <50ms query performance for semantic similarity operations
#}

{{ config(
    materialized='incremental',
    unique_key='memory_id',
    on_schema_change='sync_all_columns',
    tags=['long_term_memory', 'semantic_network', 'optimized', 'cortical'],
    pre_hook=[
        '{{ create_vector_magnitude_cache() }}',
        '{{ create_vector_performance_tables() }}'
    ],
    post_hook=[
        '{{ create_cortical_indexes() }}',
        '{{ update_performance_metrics("semantic_network_build") }}'
    ]
) }}

-- Performance optimization: Only process memories ready for long-term storage
{% if is_incremental() %}
    {% set incremental_filter %}
        WHERE (consolidated_at > (SELECT COALESCE(MAX(consolidated_at), '1900-01-01'::TIMESTAMP) FROM {{ this }})
               OR last_accessed_at > (SELECT COALESCE(MAX(last_accessed_at), '1900-01-01'::TIMESTAMP) FROM {{ this }}))
    {% endset %}
{% else %}
    {% set incremental_filter = "" %}
{% endif %}

-- Step 1: Biologically-accurate cortical minicolumn architecture
WITH biological_minicolumns AS (
  {{ biological_cortical_clustering(
    "SELECT memory_id, 
            COALESCE(embedding_vector, " ~ create_real_embedding('content', 256) ~ ") as embedding,
            content, concepts, memory_type
     FROM " ~ ref('consolidating_memories') ~ " cm
     WHERE activation_strength > " ~ var('long_term_memory_threshold') ~ "
       AND consolidation_priority > " ~ var('consolidation_threshold') ~ "
       AND " ~ memory_age_seconds('cm.created_at') ~ " > 900" ~ incremental_filter
  ) }}
),

-- Step 2: High-performance memory processing with vector caching
optimized_memories AS (
  SELECT 
    cm.memory_id,
    cm.content,
    cm.concepts,
    cm.activation_strength,
    cm.created_at,
    cm.last_accessed_at,
    cm.access_count,
    cm.memory_type,
    cm.consolidated_at,
    cm.hebbian_strength,
    cm.consolidation_priority,
    
    -- Biological cortical assignment with lateral inhibition
    bmc.cortical_minicolumn_id,
    bmc.cortical_region,
    bmc.semantic_classification,
    bmc.cortical_activation,
    bmc.column_competition_factor,
    bmc.lateral_inhibition_strength,
    bmc.cortical_hierarchy_level,
    
    -- Optimized memory age calculation
    CASE 
      WHEN {{ memory_age_seconds('created_at') }} < 86400 THEN 'recent'
      WHEN {{ memory_age_seconds('created_at') }} < 604800 THEN 'week_old'
      WHEN {{ memory_age_seconds('created_at') }} < 2592000 THEN 'month_old'
      ELSE 'remote'
    END as memory_age,
    
    -- Biological consolidation states
    CASE
      WHEN {{ memory_age_seconds('created_at') }} < 86400 AND 
           cm.consolidation_priority > {{ var('high_quality_threshold') }} THEN 'episodic'
      WHEN {{ memory_age_seconds('created_at') }} < 2592000 AND 
           cm.hebbian_strength > {{ var('consolidation_threshold') }} THEN 'consolidating'
      WHEN {{ memory_age_seconds('created_at') }} >= 2592000 AND 
           cm.activation_strength > {{ var('long_term_memory_threshold') }} THEN 'schematized'
      ELSE 'episodic'
    END as consolidation_state,
    
    -- Cache embedding vector for performance
    COALESCE(cm.embedding_vector, {{ create_real_embedding('cm.content', 256) }}) as cached_embedding,
    
    -- Biologically-informed semantic category with cortical specialization
    CASE 
      WHEN bmc.cortical_region = 'prefrontal_cortex' THEN 'executive_control'
      WHEN bmc.cortical_region = 'temporal_cortex' THEN 'semantic_linguistic'
      WHEN bmc.cortical_region = 'primary_motor_cortex' THEN 'motor_procedural'
      WHEN bmc.cortical_region = 'parietal_cortex' THEN 'spatial_attention'
      WHEN bmc.cortical_region = 'visual_cortex' THEN 'visual_perceptual'
      WHEN bmc.cortical_region = 'auditory_cortex' THEN 'auditory_linguistic'
      WHEN bmc.cortical_region = 'somatosensory_cortex' THEN 'tactile_proprioceptive'
      WHEN bmc.cortical_region = 'cingulate_cortex' THEN 'emotional_motivational'
      WHEN bmc.cortical_region = 'hippocampal_cortex' THEN 'episodic_memory'
      WHEN bmc.cortical_region = 'association_cortex' THEN 'multimodal_integration'
      ELSE 'abstract_conceptual'
    END as semantic_category
    
  FROM {{ ref('consolidating_memories') }} cm
  JOIN biological_minicolumns bmc ON cm.memory_id = bmc.memory_id
  WHERE 
    cm.activation_strength > {{ var('long_term_memory_threshold') }}
    AND cm.consolidation_priority > {{ var('consolidation_threshold') }}
    AND {{ memory_age_seconds('cm.created_at') }} > 900
    {{ incremental_filter }}
),

-- Step 3: Biologically-accurate network centrality with cortical organization
network_centrality_optimized AS (
  {{ cortical_network_centrality(
    "SELECT memory_id, cortical_region, cortical_minicolumn_id, 
            cached_embedding as embedding, cortical_activation, 
            cortical_hierarchy_level, lateral_inhibition_strength
     FROM optimized_memories"
  ) }}
),

-- Step 3a: Enhanced centrality integration with biological constraints
biological_centrality_integration AS (
  SELECT 
    om.*,
    nco.normalized_degree_centrality as degree_centrality,
    nco.normalized_betweenness_centrality as betweenness_centrality_proxy,
    nco.normalized_closeness_centrality as closeness_centrality_proxy,
    nco.normalized_eigenvector_centrality as eigenvector_centrality_proxy,
    nco.cortical_clustering_coefficient as clustering_coefficient,
    nco.biological_network_centrality as network_centrality_score,
    
    -- Biological activation modulation
    om.cortical_activation * nco.biological_network_centrality as modulated_centrality,
    
    -- Lateral inhibition effects on centrality
    GREATEST(0.1, nco.biological_network_centrality * (1.0 - om.lateral_inhibition_strength * 0.4)) as inhibited_centrality
    
  FROM optimized_memories om
  JOIN network_centrality_optimized nco ON om.memory_id = nco.memory_id
),

-- Step 4: Biologically-enhanced synaptic plasticity with cortical modulation
synaptic_plasticity_optimized AS (
  SELECT 
    bci.*,
    
    -- LTP: Enhanced with performance optimization
    CASE 
      WHEN nco.access_count > 5 AND 
           {{ memory_age_seconds('nco.last_accessed_at') }} < 86400 THEN
        LEAST(1.0, nco.activation_strength * (1.0 + {{ var('hebbian_learning_rate') }}))
      ELSE nco.activation_strength
    END as ltp_enhanced_strength,
    
    -- LTD: Optimized forgetting calculation
    CASE 
      WHEN nco.access_count < 3 AND nco.memory_age = 'remote' AND
           {{ memory_age_seconds('nco.last_accessed_at') }} > 604800 THEN
        GREATEST(0.1, nco.activation_strength * (1.0 - {{ var('synaptic_decay_rate') }}))
      ELSE nco.activation_strength  
    END as ltd_weakened_strength,
    
    -- Optimized synaptic efficacy calculation
    LEAST(1.0, GREATEST(0.1, 
      bci.activation_strength * bci.cortical_activation * 
      (1.0 + {{ var('hebbian_learning_rate') }} * 
       CASE WHEN bci.access_count > 5 AND {{ memory_age_seconds('bci.last_accessed_at') }} < 86400 
            THEN 1.0 ELSE 0.0 END) *
      (1.0 - {{ var('synaptic_decay_rate') }} * 
       CASE WHEN bci.access_count < 3 AND bci.memory_age = 'remote' AND {{ memory_age_seconds('bci.last_accessed_at') }} > 604800
            THEN (1.0 + bci.lateral_inhibition_strength) ELSE 1.0 END)
    )) as synaptic_efficacy,
    
    -- Metaplasticity factor
    EXP(-{{ safe_divide('bci.access_count', '10.0', '1.0') }}) * (1.0 - bci.lateral_inhibition_strength * 0.2) as metaplasticity_factor
    
  FROM biological_centrality_integration bci
),

-- Step 5: High-performance retrieval strength calculation
retrieval_strength_optimized AS (
  SELECT 
    spo.*,
    
    -- Multi-factor retrieval strength with optimized weighting
    (
      spo.synaptic_efficacy * 0.35 +  -- Increased weight for biological accuracy
      spo.network_centrality_score * 0.25 +
      EXP(-{{ safe_divide(memory_age_seconds('spo.last_accessed_at'), '604800.0', '1.0') }}) * 0.20 +
      LEAST(1.0, LOG(GREATEST(1, spo.access_count)) / LOG(50)) * 0.20  -- Optimized frequency calculation
    ) as retrieval_strength,
    
    -- Optimized retrieval probability with sigmoid function
    1.0 / (1.0 + EXP(-5.0 * (
      (spo.synaptic_efficacy * 0.35 +
       spo.network_centrality_score * 0.25 +
       EXP(-{{ safe_divide(memory_age_seconds('spo.last_accessed_at'), '604800.0', '1.0') }}) * 0.20 +
       LEAST(1.0, LOG(GREATEST(1, spo.access_count)) / LOG(50)) * 0.20
      ) - {{ var('homeostasis_target') }}
    ))) as retrieval_probability,
    
    -- Memory stability score for long-term persistence
    (
      spo.synaptic_efficacy * 0.4 +
      spo.network_centrality_score * 0.35 +  -- Increased network importance
      CASE 
        WHEN spo.consolidation_state = 'schematized' THEN 0.25
        WHEN spo.consolidation_state = 'consolidating' THEN 0.15
        ELSE 0.1
      END
    ) as stability_score
    
  FROM synaptic_plasticity_optimized spo
),

-- Step 6: Final optimized semantic network
final_optimized_network AS (
  SELECT 
    -- Memory identification
    rso.memory_id,
    rso.content,
    rso.concepts,
    
    -- Adaptive cortical architecture
    rso.cortical_minicolumn_id,
    rso.cortical_region,
    rso.semantic_category,
    
    -- Temporal organization
    rso.created_at,
    rso.last_accessed_at,
    rso.access_count,
    rso.memory_age,
    rso.consolidation_state,
    
    -- Optimized synaptic properties
    rso.synaptic_efficacy as activation_strength,
    rso.ltp_enhanced_strength,
    rso.ltd_weakened_strength,
    rso.metaplasticity_factor,
    
    -- Performance-optimized network properties
    LEAST(50, rso.degree_centrality) as degree_centrality,  -- Cap for performance
    rso.betweenness_centrality_proxy,
    rso.closeness_centrality_proxy,
    rso.eigenvector_centrality_proxy,
    rso.clustering_coefficient,
    rso.network_centrality_score,
    
    -- Optimized retrieval properties
    rso.retrieval_strength,
    rso.retrieval_probability,
    rso.stability_score,
    
    -- Biological metrics
    rso.hebbian_strength,
    rso.consolidation_priority,
    rso.consolidated_at,
    
    -- Performance-optimized memory quality classification
    CASE 
      WHEN rso.stability_score > {{ var('high_quality_threshold') }} AND 
           rso.retrieval_strength > {{ var('strong_connection_threshold') }} THEN 'high_fidelity'
      WHEN rso.stability_score > {{ var('medium_quality_threshold') }} AND 
           rso.retrieval_strength > {{ var('consolidation_threshold') }} THEN 'medium_fidelity'
      WHEN rso.stability_score > 0.3 AND rso.retrieval_strength > 0.2 THEN 'low_fidelity'
      ELSE 'degraded'
    END as memory_fidelity,
    
    -- Cached embedding for future performance
    rso.cached_embedding,
    
    -- Performance tracking
    CURRENT_TIMESTAMP as last_processed_at,
    CURRENT_TIMESTAMP as semantic_network_updated_at
    
  FROM retrieval_strength_optimized rso
  WHERE rso.retrieval_strength > 0.15  -- Optimized threshold for performance
)

-- Final SELECT with performance optimization
SELECT * FROM final_optimized_network
ORDER BY 
  retrieval_strength DESC,
  network_centrality_score DESC,
  stability_score DESC
LIMIT CASE 
  WHEN '{{ var("performance_mode") }}' = 'high' THEN 10000  -- Performance limit
  ELSE 50000  -- Standard limit
END