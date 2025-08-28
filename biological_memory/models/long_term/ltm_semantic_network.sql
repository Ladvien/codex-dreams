{#
  Long-Term Memory Semantic Network Model
  
  This model implements the centerpiece of biological long-term memory processing,
  modeling a semantic network with cortical minicolumn architecture based on 
  neuroscientific principles of memory consolidation and retrieval.
  
  Key Features:
  - 1000 cortical minicolumns semantic graph structure
  - Network centrality measures for retrieval optimization
  - Long-term potentiation (LTP) and long-term depression (LTD) algorithms
  - Biologically accurate memory age categories
  - Consolidation states reflecting episodic to semantic transition
  - Multi-factor retrieval strength calculation
  
  Biological Basis:
  - Based on cortical minicolumn organization (Mountcastle, 1997)
  - Implements Hebbian learning principles (Hebb, 1949)
  - Models hippocampal-cortical consolidation (McClelland et al., 1995)
  - Incorporates synaptic homeostasis (Turrigiano, 2008)
#}

{{ config(
    materialized='table',
    tags=['long_term_memory', 'semantic_network', 'production', 'cortical'],
    post_hook=[
        '{{ create_cortical_indexes() }}',
        '{{ calculate_network_metrics() }}'
    ]
) }}

-- Step 1: Generate cortical minicolumn architecture (1000 minicolumns)
WITH cortical_minicolumns AS (
  SELECT 
    -- Generate 1000 cortical minicolumns as semantic processing units
    CAST(ROW_NUMBER() OVER (ORDER BY RANDOM()) AS INTEGER) as cortical_minicolumn_id,
    -- Organize into 50 cortical regions with 20 minicolumns each
    FLOOR((ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) / 20) + 1 as cortical_region,
    -- Assign semantic categories based on neuroscientific organization
    CASE 
      WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 1000 < 100 THEN 'episodic_autobiographical'
      WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 1000 < 200 THEN 'semantic_conceptual'
      WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 1000 < 300 THEN 'procedural_skills'
      WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 1000 < 400 THEN 'spatial_navigation'
      WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 1000 < 500 THEN 'temporal_sequence'
      WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 1000 < 600 THEN 'emotional_valence'
      WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 1000 < 700 THEN 'social_cognition'
      WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 1000 < 800 THEN 'linguistic_semantic'
      WHEN (ROW_NUMBER() OVER (ORDER BY RANDOM()) - 1) % 1000 < 900 THEN 'sensory_perceptual'
      ELSE 'abstract_conceptual'
    END as semantic_category,
    -- Minicolumn activation patterns
    RANDOM() as baseline_activation,
    CURRENT_TIMESTAMP as minicolumn_initialized_at
  FROM GENERATE_SERIES(1, 1000) as minicolumn_series
),

-- Step 2: Consolidate memories from STM and assign to cortical minicolumns
consolidated_memories AS (
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
    
    -- Assign memory to appropriate cortical minicolumn based on semantic content
    (
      SELECT mc.cortical_minicolumn_id 
      FROM cortical_minicolumns mc
      WHERE mc.semantic_category = 
        CASE 
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%personal%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%experience%' THEN 'episodic_autobiographical'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%concept%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%knowledge%' THEN 'semantic_conceptual'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%skill%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%procedure%' THEN 'procedural_skills'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%location%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%place%' THEN 'spatial_navigation'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%time%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%sequence%' THEN 'temporal_sequence'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%emotion%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%feeling%' THEN 'emotional_valence'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%social%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%people%' THEN 'social_cognition'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%language%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%word%' THEN 'linguistic_semantic'
          WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%visual%' OR 
               ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%sensory%' THEN 'sensory_perceptual'
          ELSE 'abstract_conceptual'
        END
      ORDER BY RANDOM()
      LIMIT 1
    ) as assigned_cortical_minicolumn,
    
    -- Calculate memory age categories based on temporal dynamics
    CASE 
      WHEN {{ memory_age_seconds('created_at') }} < 86400 THEN 'recent'          -- < 1 day
      WHEN {{ memory_age_seconds('created_at') }} < 604800 THEN 'week_old'       -- < 1 week  
      WHEN {{ memory_age_seconds('created_at') }} < 2592000 THEN 'month_old'     -- < 30 days
      ELSE 'remote'                                                              -- > 30 days
    END as memory_age,
    
    -- Consolidation states based on biological memory transitions
    CASE
      WHEN {{ memory_age_seconds('created_at') }} < 86400 AND 
           cm.consolidation_priority > {{ var('high_quality_threshold') }} THEN 'episodic'
      WHEN {{ memory_age_seconds('created_at') }} < 2592000 AND 
           cm.hebbian_strength > {{ var('consolidation_threshold') }} THEN 'consolidating'
      WHEN {{ memory_age_seconds('created_at') }} >= 2592000 AND 
           cm.activation_strength > {{ var('long_term_memory_threshold') }} THEN 'schematized'
      ELSE 'episodic'
    END as consolidation_state,
    
    -- Extract semantic category for cortical assignment
    CASE 
      WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%personal%' OR 
           ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%experience%' THEN 'episodic_autobiographical'
      WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%concept%' OR 
           ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%knowledge%' THEN 'semantic_conceptual'
      WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%skill%' OR 
           ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%procedure%' THEN 'procedural_skills'
      WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%location%' OR 
           ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%place%' THEN 'spatial_navigation'
      WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%time%' OR 
           ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%sequence%' THEN 'temporal_sequence'
      WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%emotion%' OR 
           ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%feeling%' THEN 'emotional_valence'
      WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%social%' OR 
           ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%people%' THEN 'social_cognition'
      WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%language%' OR 
           ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%word%' THEN 'linguistic_semantic'
      WHEN ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%visual%' OR 
           ARRAY_TO_STRING(cm.concepts, ' ') ILIKE '%sensory%' THEN 'sensory_perceptual'
      ELSE 'abstract_conceptual'
    END as semantic_category
    
  FROM {{ ref('consolidating_memories') }} cm
  WHERE 
    -- Only memories that meet long-term storage criteria
    cm.activation_strength > {{ var('long_term_memory_threshold') }}
    AND cm.consolidation_priority > {{ var('consolidation_threshold') }}
    AND {{ memory_age_seconds('cm.created_at') }} > 900  -- At least 15 minutes old for initial consolidation
),

-- Step 3: Calculate network centrality measures for retrieval optimization
network_centrality AS (
  SELECT 
    cm.*,
    mc.cortical_region,
    
    -- Degree centrality: Number of semantic associations
    COALESCE(sa.association_count, 0) as degree_centrality,
    
    -- Betweenness centrality proxy: Memories bridging different semantic categories
    COALESCE(
      (SELECT COUNT(DISTINCT target_category) 
       FROM {{ source('self_sensored', 'semantic_associations') }} cross_cat
       WHERE cross_cat.memory_id = cm.memory_id 
       AND cross_cat.target_category != cm.semantic_category), 
      0
    ) as betweenness_centrality_proxy,
    
    -- Closeness centrality proxy: Average association strength to other memories
    COALESCE(sa.avg_association_strength, 0.0) as closeness_centrality_proxy,
    
    -- Eigenvector centrality proxy: Connected to highly connected memories
    COALESCE(sa.max_association_strength, 0.0) * 
    COALESCE(sa.association_count, 0) / 100.0 as eigenvector_centrality_proxy,
    
    -- Clustering coefficient: Local network density
    COALESCE(nc.clustering_coefficient, 0.0) as clustering_coefficient,
    
    -- Network centrality composite score (0.0-1.0)
    LEAST(1.0, (
      COALESCE(sa.association_count, 0) / 50.0 * 0.25 +  -- Degree (max 50 associations)
      COALESCE(sa.avg_association_strength, 0.0) * 0.25 + -- Closeness proxy
      COALESCE(sa.max_association_strength, 0.0) * 0.25 + -- Eigenvector proxy  
      COALESCE(nc.clustering_coefficient, 0.0) * 0.25     -- Local clustering
    )) as network_centrality_score
    
  FROM consolidated_memories cm
  LEFT JOIN cortical_minicolumns mc ON cm.assigned_cortical_minicolumn = mc.cortical_minicolumn_id
  LEFT JOIN {{ source('self_sensored', 'semantic_associations') }} sa ON cm.memory_id = sa.memory_id
  LEFT JOIN {{ source('self_sensored', 'network_centrality') }} nc ON cm.memory_id = nc.memory_id
),

-- Step 4: Implement Long-Term Potentiation (LTP) and Long-Term Depression (LTD)
synaptic_plasticity AS (
  SELECT 
    nc.*,
    
    -- LTP: Strengthen frequently accessed memories within temporal windows  
    CASE 
      WHEN nc.access_count > 5 AND 
           {{ memory_age_seconds('nc.last_accessed_at') }} < 86400 THEN -- Recent frequent access
        LEAST(1.0, nc.activation_strength * (1.0 + {{ var('hebbian_learning_rate') }}))
      ELSE nc.activation_strength
    END as ltp_enhanced_strength,
    
    -- LTD: Weaken rarely accessed remote memories (forgetting)
    CASE 
      WHEN nc.access_count < 3 AND nc.memory_age = 'remote' AND
           {{ memory_age_seconds('nc.last_accessed_at') }} > 604800 THEN -- Rarely accessed old memories
        GREATEST(0.1, nc.activation_strength * (1.0 - {{ var('synaptic_decay_rate') }}))
      ELSE nc.activation_strength  
    END as ltd_weakened_strength,
    
    -- Synaptic efficacy: Combined LTP/LTD effects
    LEAST(1.0, GREATEST(0.1, 
      nc.activation_strength * 
      (1.0 + {{ var('hebbian_learning_rate') }} * 
       CASE WHEN nc.access_count > 5 AND {{ memory_age_seconds('nc.last_accessed_at') }} < 86400 
            THEN 1.0 ELSE 0.0 END) *
      (1.0 - {{ var('synaptic_decay_rate') }} * 
       CASE WHEN nc.access_count < 3 AND nc.memory_age = 'remote' AND {{ memory_age_seconds('nc.last_accessed_at') }} > 604800
            THEN 1.0 ELSE 0.0 END)
    )) as synaptic_efficacy,
    
    -- Metaplasticity: History-dependent plasticity changes
    EXP(-{{ safe_divide('nc.access_count', '10.0', '1.0') }}) as metaplasticity_factor
  FROM network_centrality nc
),

-- Step 5: Calculate multi-factor retrieval strength
retrieval_strength_calculation AS (
  SELECT 
    sp.*,
    
    -- Multi-factor retrieval strength based on biological principles
    (
      -- Base synaptic efficacy (30% weight)
      sp.synaptic_efficacy * 0.30 +
      
      -- Network centrality importance (25% weight)  
      sp.network_centrality_score * 0.25 +
      
      -- Recency effect with biological decay (20% weight)
      EXP(-{{ safe_divide(memory_age_seconds('sp.last_accessed_at'), '604800.0', '1.0') }}) * 0.20 +
      
      -- Frequency effect with logarithmic scaling (15% weight)
      LOG(GREATEST(1, sp.access_count)) / LOG(100) * 0.15 +
      
      -- Consolidation state modifier (10% weight)
      CASE 
        WHEN sp.consolidation_state = 'schematized' THEN 1.0
        WHEN sp.consolidation_state = 'consolidating' THEN 0.8
        WHEN sp.consolidation_state = 'episodic' THEN 0.6
        ELSE 0.5
      END * 0.10
    ) as retrieval_strength,
    
    -- Retrieval probability based on biological activation function
    1.0 / (1.0 + EXP(-(
      (sp.synaptic_efficacy * 0.30 +
       sp.network_centrality_score * 0.25 +
       EXP(-{{ safe_divide(memory_age_seconds('sp.last_accessed_at'), '604800.0', '1.0') }}) * 0.20 +
       LOG(GREATEST(1, sp.access_count)) / LOG(100) * 0.15 +
       CASE 
         WHEN sp.consolidation_state = 'schematized' THEN 1.0
         WHEN sp.consolidation_state = 'consolidating' THEN 0.8
         WHEN sp.consolidation_state = 'episodic' THEN 0.6
         ELSE 0.5
       END * 0.10
      ) - {{ var('homeostasis_target') }}
    ))) as retrieval_probability,
    
    -- Memory stability score for long-term persistence
    (
      sp.synaptic_efficacy * 0.4 +
      sp.network_centrality_score * 0.3 +
      CASE 
        WHEN sp.consolidation_state = 'schematized' THEN 0.3
        WHEN sp.consolidation_state = 'consolidating' THEN 0.2
        ELSE 0.1
      END
    ) as stability_score
  FROM synaptic_plasticity sp
),

-- Step 6: Final semantic network with cortical organization
final_semantic_network AS (
  SELECT 
    -- Memory identification
    rsc.memory_id,
    rsc.content,
    rsc.concepts,
    
    -- Cortical architecture
    rsc.assigned_cortical_minicolumn,
    rsc.cortical_region,
    rsc.semantic_category,
    
    -- Temporal organization
    rsc.created_at,
    rsc.last_accessed_at,
    rsc.access_count,
    rsc.memory_age,
    rsc.consolidation_state,
    
    -- Synaptic properties
    rsc.synaptic_efficacy as activation_strength,
    rsc.ltp_enhanced_strength,
    rsc.ltd_weakened_strength,
    rsc.metaplasticity_factor,
    
    -- Network properties
    rsc.degree_centrality,
    rsc.betweenness_centrality_proxy,
    rsc.closeness_centrality_proxy,
    rsc.eigenvector_centrality_proxy,
    rsc.clustering_coefficient,
    rsc.network_centrality_score,
    
    -- Retrieval properties
    rsc.retrieval_strength,
    rsc.retrieval_probability,
    rsc.stability_score,
    
    -- Biological metrics
    rsc.hebbian_strength,
    rsc.consolidation_priority,
    rsc.consolidated_at,
    
    -- Memory quality classification
    CASE 
      WHEN rsc.stability_score > {{ var('high_quality_threshold') }} AND 
           rsc.retrieval_strength > {{ var('strong_connection_threshold') }} THEN 'high_fidelity'
      WHEN rsc.stability_score > {{ var('medium_quality_threshold') }} AND 
           rsc.retrieval_strength > {{ var('consolidation_threshold') }} THEN 'medium_fidelity'
      WHEN rsc.stability_score > 0.4 AND 
           rsc.retrieval_strength > 0.3 THEN 'low_fidelity'
      ELSE 'degraded'
    END as memory_fidelity,
    
    -- System timestamps
    CURRENT_TIMESTAMP as last_processed_at,
    CURRENT_TIMESTAMP as semantic_network_updated_at
    
  FROM retrieval_strength_calculation rsc
  WHERE rsc.retrieval_strength > 0.1  -- Only store memories with meaningful retrieval strength
)

-- Final SELECT: Complete Long-Term Memory Semantic Network
SELECT * FROM final_semantic_network
ORDER BY 
  retrieval_strength DESC,
  network_centrality_score DESC,
  stability_score DESC,
  last_accessed_at DESC