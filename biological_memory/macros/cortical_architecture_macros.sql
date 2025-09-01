{#
  Biologically-Accurate Cortical Minicolumn Architecture (BMP-MEM-005)
  
  Research Foundation:
  - Mountcastle (1997): Cortical columns as fundamental units (80-120 neurons)
  - Felleman & Van Essen (1991): Cortical hierarchy and connectivity patterns
  - Douglas & Martin (2004): Lateral inhibition mechanisms in cortical columns
  - Brodmann (1909): Cytoarchitectonic areas of the human cortex
  
  Optimizations:
  - Semantic-based cortical region assignment using Brodmann areas
  - Biological minicolumn size constraints (80-120 neurons per column)
  - Lateral inhibition and column competition mechanisms
  - Cortical connectivity matrices based on anatomical research
  - Network centrality calculations reflecting biological organization
#}

{# Biologically-accurate cortical minicolumn architecture (Mountcastle 1997, Felleman & Van Essen 1991) #}
{% macro biological_cortical_clustering(memory_vectors, target_clusters=1000, max_iterations=50) %}
  {# Biologically-informed cortical minicolumn clustering with Brodmann area organization #}
  WITH semantic_feature_extraction AS (
    SELECT 
      memory_id,
      embedding,
      content,
      concepts,
      memory_type,
      ARRAY_LENGTH(embedding, 1) as vector_dimensions,
      
      -- Extract semantic features for cortical region assignment (Felleman & Van Essen 1991)
      CASE 
        WHEN LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%action%' 
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%movement%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%motor%' THEN 'motor_semantic'
        WHEN LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%visual%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%see%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%image%' THEN 'visual_semantic'
        WHEN LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%sound%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%hear%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%audio%' THEN 'auditory_semantic'
        WHEN LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%space%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%location%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%where%' THEN 'spatial_semantic'
        WHEN LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%touch%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%feel%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%sensation%' THEN 'somatosensory_semantic'
        WHEN LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%emotion%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%feeling%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%mood%' THEN 'limbic_semantic'
        WHEN LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%plan%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%decision%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%goal%' THEN 'executive_semantic'
        WHEN LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%word%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%language%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%speak%' THEN 'language_semantic'
        WHEN LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%memory%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%remember%'
             OR LOWER(content || ' ' || COALESCE(concepts, '')) LIKE '%past%' THEN 'temporal_semantic'
        ELSE 'association_semantic'
      END as semantic_classification
      
    FROM ({{ memory_vectors }})
    WHERE ARRAY_LENGTH(embedding, 1) > 0
  ),
  
  -- Biologically-informed cortical region assignment based on Brodmann areas
  cortical_region_assignment AS (
    SELECT 
      sfe.*,
      -- Map semantic features to biologically-accurate cortical regions
      CASE sfe.semantic_classification
        WHEN 'motor_semantic' THEN 'primary_motor_cortex'      -- Brodmann areas 4, 6
        WHEN 'visual_semantic' THEN 'visual_cortex'            -- Brodmann areas 17, 18, 19
        WHEN 'auditory_semantic' THEN 'auditory_cortex'        -- Brodmann areas 41, 42
        WHEN 'spatial_semantic' THEN 'parietal_cortex'         -- Brodmann areas 5, 7, 39, 40
        WHEN 'somatosensory_semantic' THEN 'somatosensory_cortex' -- Brodmann areas 1, 2, 3
        WHEN 'limbic_semantic' THEN 'cingulate_cortex'         -- Brodmann areas 24, 32
        WHEN 'executive_semantic' THEN 'prefrontal_cortex'     -- Brodmann areas 9, 10, 11, 46
        WHEN 'language_semantic' THEN 'temporal_cortex'        -- Brodmann areas 22, 37, 39
        WHEN 'temporal_semantic' THEN 'hippocampal_cortex'     -- Hippocampal formation
        ELSE 'association_cortex'                              -- Brodmann areas 20, 21, 37
      END as biological_cortical_region,
      
      -- Minicolumn assignment within cortical regions (80-120 neurons per Mountcastle 1997)
      ROW_NUMBER() OVER (
        PARTITION BY semantic_classification 
        ORDER BY {{ fast_cosine_similarity('embedding', 'embedding') }} DESC
      ) as region_column_id
      
    FROM semantic_feature_extraction sfe
  ),
  
  -- Biological minicolumn size constraints (Mountcastle 1997)
  minicolumn_size_optimization AS (
    SELECT 
      cra.*,
      -- Ensure minicolumns stay within biological size limits (80-120 neurons)
      CASE 
        WHEN region_column_id > 120 THEN 
          ((region_column_id - 1) % 120) + 1  -- Wrap to create new minicolumns
        ELSE region_column_id
      END as biological_minicolumn_id,
      
      -- Calculate final cortical minicolumn ID with biological organization
      CASE cra.biological_cortical_region
        WHEN 'prefrontal_cortex' THEN ((region_column_id - 1) % 120) + 1
        WHEN 'temporal_cortex' THEN ((region_column_id - 1) % 120) + 121
        WHEN 'parietal_cortex' THEN ((region_column_id - 1) % 120) + 241
        WHEN 'visual_cortex' THEN ((region_column_id - 1) % 120) + 361
        WHEN 'primary_motor_cortex' THEN ((region_column_id - 1) % 120) + 481
        WHEN 'somatosensory_cortex' THEN ((region_column_id - 1) % 120) + 601
        WHEN 'auditory_cortex' THEN ((region_column_id - 1) % 120) + 721
        WHEN 'cingulate_cortex' THEN ((region_column_id - 1) % 120) + 841
        WHEN 'hippocampal_cortex' THEN ((region_column_id - 1) % 120) + 961
        ELSE ((region_column_id - 1) % 120) + 881  -- association_cortex
      END as cortical_minicolumn_id
      
    FROM cortical_region_assignment cra
  ),
  
  -- Lateral inhibition and column competition (Douglas & Martin 2004)
  lateral_inhibition AS (
    SELECT 
      mso.*,
      
      -- Calculate lateral inhibition strength based on nearby minicolumns
      COALESCE((
        SELECT AVG({{ fast_cosine_similarity('mso.embedding', 'mso2.embedding') }})
        FROM minicolumn_size_optimization mso2
        WHERE mso2.memory_id != mso.memory_id
          AND mso2.biological_cortical_region = mso.biological_cortical_region
          AND ABS(mso2.cortical_minicolumn_id - mso.cortical_minicolumn_id) <= 3  -- Adjacent columns
      ), 0.0) as lateral_inhibition_strength,
      
      -- Column competition factor (higher similarity = more competition)
      1.0 - LEAST(0.8, COALESCE((
        SELECT MAX({{ fast_cosine_similarity('mso.embedding', 'mso2.embedding') }})
        FROM minicolumn_size_optimization mso2
        WHERE mso2.memory_id != mso.memory_id
          AND mso2.biological_cortical_region = mso.biological_cortical_region
          AND ABS(mso2.cortical_minicolumn_id - mso.cortical_minicolumn_id) <= 5
      ), 0.0)) as column_competition_factor
      
    FROM minicolumn_size_optimization mso
  )
  
  SELECT 
    memory_id,
    cortical_minicolumn_id,
    biological_cortical_region as cortical_region,
    semantic_classification,
    biological_minicolumn_id,
    
    -- Biological activation with lateral inhibition
    GREATEST(0.1, 1.0 - (lateral_inhibition_strength * 0.3)) as cortical_activation,
    column_competition_factor,
    lateral_inhibition_strength,
    
    -- Cortical hierarchy level (Felleman & Van Essen 1991)
    CASE biological_cortical_region
      WHEN 'visual_cortex' THEN 1         -- Primary sensory
      WHEN 'auditory_cortex' THEN 1       -- Primary sensory
      WHEN 'somatosensory_cortex' THEN 1  -- Primary sensory
      WHEN 'primary_motor_cortex' THEN 2  -- Primary motor
      WHEN 'parietal_cortex' THEN 3       -- Secondary association
      WHEN 'temporal_cortex' THEN 3       -- Secondary association
      WHEN 'association_cortex' THEN 4    -- Higher-order association
      WHEN 'prefrontal_cortex' THEN 5     -- Executive control
      WHEN 'cingulate_cortex' THEN 4      -- Limbic association
      WHEN 'hippocampal_cortex' THEN 5    -- Memory formation
      ELSE 3
    END as cortical_hierarchy_level,
    
    embedding
  FROM lateral_inhibition
  ORDER BY biological_cortical_region, cortical_minicolumn_id
{% endmacro %}

{# Biologically-accurate cortical connectivity matrix (Felleman & Van Essen 1991) #}
{% macro cortical_connectivity_matrix(source_region, target_region) %}
  {# Define biological connectivity patterns between cortical regions #}
  CASE 
    -- Visual pathway connections
    WHEN '{{ source_region }}' = 'visual_cortex' AND '{{ target_region }}' = 'parietal_cortex' THEN 0.8  -- Dorsal stream
    WHEN '{{ source_region }}' = 'visual_cortex' AND '{{ target_region }}' = 'temporal_cortex' THEN 0.9   -- Ventral stream
    WHEN '{{ source_region }}' = 'visual_cortex' AND '{{ target_region }}' = 'prefrontal_cortex' THEN 0.6
    
    -- Auditory pathway connections
    WHEN '{{ source_region }}' = 'auditory_cortex' AND '{{ target_region }}' = 'temporal_cortex' THEN 0.9
    WHEN '{{ source_region }}' = 'auditory_cortex' AND '{{ target_region }}' = 'prefrontal_cortex' THEN 0.7
    
    -- Somatosensory pathway connections
    WHEN '{{ source_region }}' = 'somatosensory_cortex' AND '{{ target_region }}' = 'parietal_cortex' THEN 0.9
    WHEN '{{ source_region }}' = 'somatosensory_cortex' AND '{{ target_region }}' = 'primary_motor_cortex' THEN 0.8
    
    -- Motor pathway connections
    WHEN '{{ source_region }}' = 'primary_motor_cortex' AND '{{ target_region }}' = 'prefrontal_cortex' THEN 0.8
    WHEN '{{ source_region }}' = 'primary_motor_cortex' AND '{{ target_region }}' = 'parietal_cortex' THEN 0.7
    
    -- Prefrontal connections (executive control)
    WHEN '{{ source_region }}' = 'prefrontal_cortex' AND '{{ target_region }}' = 'cingulate_cortex' THEN 0.8
    WHEN '{{ source_region }}' = 'prefrontal_cortex' AND '{{ target_region }}' = 'hippocampal_cortex' THEN 0.7
    
    -- Temporal lobe connections (memory)
    WHEN '{{ source_region }}' = 'temporal_cortex' AND '{{ target_region }}' = 'hippocampal_cortex' THEN 0.9
    WHEN '{{ source_region }}' = 'temporal_cortex' AND '{{ target_region }}' = 'prefrontal_cortex' THEN 0.7
    
    -- Parietal connections (spatial processing)
    WHEN '{{ source_region }}' = 'parietal_cortex' AND '{{ target_region }}' = 'prefrontal_cortex' THEN 0.8
    WHEN '{{ source_region }}' = 'parietal_cortex' AND '{{ target_region }}' = 'cingulate_cortex' THEN 0.6
    
    -- Hippocampal connections (memory formation)
    WHEN '{{ source_region }}' = 'hippocampal_cortex' AND '{{ target_region }}' = 'prefrontal_cortex' THEN 0.8
    WHEN '{{ source_region }}' = 'hippocampal_cortex' AND '{{ target_region }}' = 'cingulate_cortex' THEN 0.7
    
    -- Cingulate connections (emotional processing)
    WHEN '{{ source_region }}' = 'cingulate_cortex' AND '{{ target_region }}' = 'hippocampal_cortex' THEN 0.8
    WHEN '{{ source_region }}' = 'cingulate_cortex' AND '{{ target_region }}' = 'prefrontal_cortex' THEN 0.9
    
    -- Association cortex connections
    WHEN '{{ source_region }}' = 'association_cortex' THEN 0.5  -- Moderate connections to all regions
    WHEN '{{ target_region }}' = 'association_cortex' THEN 0.5
    
    -- Same region connections (within-region connectivity)
    WHEN '{{ source_region }}' = '{{ target_region }}' THEN 0.9
    
    -- Default weak connections
    ELSE 0.3
  END
{% endmacro %}

{# Biologically-accurate network centrality with cortical organization #}
{% macro cortical_network_centrality(memory_data, centrality_type='degree') %}
  {# Calculate network centrality considering biological cortical connectivity #}
  WITH cortical_connections AS (
    SELECT 
      m1.memory_id as source_memory,
      m2.memory_id as target_memory,
      m1.cortical_region as source_region,
      m2.cortical_region as target_region,
      m1.cortical_minicolumn_id as source_column,
      m2.cortical_minicolumn_id as target_column,
      
      -- Biological connection strength based on cortical connectivity
      {{ cortical_connectivity_matrix('m1.cortical_region', 'm2.cortical_region') }} as biological_connection_strength,
      
      -- Semantic similarity weighted by biological connectivity
      {{ fast_cosine_similarity('m1.embedding', 'm2.embedding') }} * 
      {{ cortical_connectivity_matrix('m1.cortical_region', 'm2.cortical_region') }} as weighted_similarity,
      
      -- Distance-based attenuation for lateral connections
      CASE 
        WHEN m1.cortical_region = m2.cortical_region THEN
          EXP(-0.1 * ABS(m1.cortical_minicolumn_id - m2.cortical_minicolumn_id))  -- Lateral distance decay
        ELSE 1.0  -- Inter-regional connections not distance-dependent
      END as spatial_attenuation
      
    FROM ({{ memory_data }}) m1
    CROSS JOIN ({{ memory_data }}) m2
    WHERE m1.memory_id != m2.memory_id
      AND {{ fast_cosine_similarity('m1.embedding', 'm2.embedding') }} > 0.3  -- Performance threshold
  ),
  
  centrality_calculations AS (
    SELECT 
      cc.source_memory,
      cc.source_region,
      cc.source_column,
      
      -- Biologically-informed degree centrality
      COUNT(CASE WHEN cc.weighted_similarity * cc.spatial_attenuation > 0.5 THEN 1 END) as bio_degree_centrality,
      
      -- Betweenness centrality proxy (inter-regional bridging)
      COUNT(DISTINCT cc.target_region) as region_bridging_centrality,
      
      -- Closeness centrality with biological weighting
      AVG(cc.weighted_similarity * cc.spatial_attenuation) as bio_closeness_centrality,
      
      -- Eigenvector centrality approximation with cortical hierarchy
      SUM(cc.weighted_similarity * cc.biological_connection_strength * cc.spatial_attenuation) as bio_eigenvector_centrality,
      
      -- Cortical clustering coefficient (local connectivity density)
      (
        SELECT COUNT(*) 
        FROM cortical_connections cc2
        WHERE cc2.source_memory IN (
          SELECT target_memory FROM cortical_connections cc3 
          WHERE cc3.source_memory = cc.source_memory 
            AND cc3.weighted_similarity * cc3.spatial_attenuation > 0.5
        )
        AND cc2.target_memory IN (
          SELECT target_memory FROM cortical_connections cc4
          WHERE cc4.source_memory = cc.source_memory 
            AND cc4.weighted_similarity * cc4.spatial_attenuation > 0.5
        )
        AND cc2.source_memory != cc2.target_memory
      ) / GREATEST(1, POWER(bio_degree_centrality, 2) - bio_degree_centrality) as cortical_clustering_coefficient
      
    FROM cortical_connections cc
    GROUP BY cc.source_memory, cc.source_region, cc.source_column
  )
  
  SELECT 
    source_memory as memory_id,
    source_region as cortical_region,
    source_column as cortical_minicolumn_id,
    
    -- Normalized biological centrality measures
    LEAST(1.0, bio_degree_centrality / 50.0) as normalized_degree_centrality,
    LEAST(1.0, region_bridging_centrality / 10.0) as normalized_betweenness_centrality,
    LEAST(1.0, bio_closeness_centrality) as normalized_closeness_centrality,
    LEAST(1.0, bio_eigenvector_centrality / 5.0) as normalized_eigenvector_centrality,
    LEAST(1.0, COALESCE(cortical_clustering_coefficient, 0.0)) as cortical_clustering_coefficient,
    
    -- Composite biological network centrality
    (
      LEAST(1.0, bio_degree_centrality / 50.0) * 0.3 +
      LEAST(1.0, region_bridging_centrality / 10.0) * 0.25 +
      LEAST(1.0, bio_closeness_centrality) * 0.25 +
      LEAST(1.0, bio_eigenvector_centrality / 5.0) * 0.2
    ) as biological_network_centrality
    
  FROM centrality_calculations
{% endmacro %}

{# Create cortical architecture performance indexes #}
{% macro create_cortical_indexes() %}
  -- Biological cortical region index
  CREATE INDEX IF NOT EXISTS idx_cortical_region_minicolumn 
  ON {{ this }} (cortical_region, cortical_minicolumn_id);
  
  -- Semantic classification index
  CREATE INDEX IF NOT EXISTS idx_semantic_classification 
  ON {{ this }} (semantic_classification);
  
  -- Cortical activation index for performance
  CREATE INDEX IF NOT EXISTS idx_cortical_activation 
  ON {{ this }} (cortical_activation DESC);
  
  -- Cortical hierarchy level index
  CREATE INDEX IF NOT EXISTS idx_cortical_hierarchy 
  ON {{ this }} (cortical_hierarchy_level, cortical_region);
  
  -- Biological network centrality index
  CREATE INDEX IF NOT EXISTS idx_biological_network_centrality 
  ON {{ this }} (biological_network_centrality DESC);
  
  -- Lateral inhibition performance index
  CREATE INDEX IF NOT EXISTS idx_lateral_inhibition 
  ON {{ this }} (cortical_region, lateral_inhibition_strength);
  
  {{ log("Cortical architecture performance indexes created", info=true) }}
{% endmacro %}

{# Validate cortical architecture against biological constraints #}
{% macro validate_cortical_constraints() %}
  {# Validate that cortical organization meets biological accuracy requirements #}
  WITH cortical_validation AS (
    SELECT 
      cortical_region,
      COUNT(*) as total_memories,
      COUNT(DISTINCT cortical_minicolumn_id) as unique_minicolumns,
      AVG(cortical_activation) as avg_activation,
      AVG(lateral_inhibition_strength) as avg_lateral_inhibition,
      AVG(column_competition_factor) as avg_competition,
      
      -- Validate Mountcastle constraints (80-120 memories per minicolumn)
      CASE 
        WHEN COUNT(*) / COUNT(DISTINCT cortical_minicolumn_id) BETWEEN 80 AND 120 THEN 'VALID'
        ELSE 'INVALID_SIZE'
      END as minicolumn_size_validation,
      
      -- Validate cortical hierarchy constraints
      CASE 
        WHEN cortical_hierarchy_level BETWEEN 1 AND 5 THEN 'VALID'
        ELSE 'INVALID_HIERARCHY'
      END as hierarchy_validation
      
    FROM {{ this }}
    GROUP BY cortical_region, cortical_hierarchy_level
  )
  
  SELECT 
    cortical_region,
    total_memories,
    unique_minicolumns,
    ROUND(avg_activation, 3) as avg_cortical_activation,
    ROUND(avg_lateral_inhibition, 3) as avg_lateral_inhibition,
    ROUND(avg_competition, 3) as avg_column_competition,
    minicolumn_size_validation,
    hierarchy_validation,
    
    -- Overall biological accuracy score
    CASE 
      WHEN minicolumn_size_validation = 'VALID' 
           AND hierarchy_validation = 'VALID'
           AND avg_activation BETWEEN 0.3 AND 0.9
           AND avg_lateral_inhibition BETWEEN 0.1 AND 0.7 THEN 'BIOLOGICALLY_ACCURATE'
      ELSE 'NEEDS_OPTIMIZATION'
    END as biological_accuracy_status
    
  FROM cortical_validation
  ORDER BY cortical_hierarchy_level, cortical_region;
  
  {{ log("Cortical biological constraint validation completed", info=true) }}
{% endmacro %}