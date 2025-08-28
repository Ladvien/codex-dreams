{# 
  Biological Memory Processing Macros
  Advanced dbt macros implementing biological memory algorithms
  
  These macros implement core biological memory processes:
  - Hebbian learning strength calculation
  - Synaptic homeostasis maintenance  
  - Association strengthening
  - Memory consolidation logic
#}

{# Enhanced Hebbian learning strength with temporal co-activation counting #}
{% macro calculate_hebbian_strength() %}
  {# 
    Advanced Hebbian learning implementation:
    - Co-activation counting within 5-minute temporal windows
    - Proper learning rate application (0.1 default)
    - Prevents runaway potentiation with normalization
    - Updates consolidated memories based on STM co-activation patterns
  #}
  
  {# Biological parameter validation #}
  {% if var('hebbian_learning_rate') > 0.5 %}
    {{ log("WARNING: Hebbian learning rate exceeds biological realism (>0.5): " ~ var('hebbian_learning_rate'), info=true) }}
  {% endif %}
  
  {% if var('hebbian_learning_rate') < 0.01 %}
    {{ log("WARNING: Hebbian learning rate may be too low for effective learning (<0.01): " ~ var('hebbian_learning_rate'), info=true) }}
  {% endif %}
  
  -- Step 1: Calculate co-activation patterns within 5-minute windows
  WITH coactivation AS (
    SELECT 
      a.id as pre_id,
      b.id as post_id,
      COUNT(*) as coactivation_count,
      AVG(EXTRACT(EPOCH FROM (b.timestamp - a.timestamp))) as avg_delay_seconds,
      COUNT(DISTINCT a.semantic_category) as shared_categories
    FROM {{ ref('stm_hierarchical_episodes') }} a
    JOIN {{ ref('stm_hierarchical_episodes') }} b
      ON a.semantic_category = b.semantic_category
      AND b.timestamp BETWEEN a.timestamp AND a.timestamp + INTERVAL '5 minutes'
      AND a.id != b.id  -- Prevent self-connections
    GROUP BY a.id, b.id
    HAVING COUNT(*) >= 1  -- At least one co-activation event
  ),
  
  -- Step 2: Calculate Hebbian strength updates
  hebbian_updates AS (
    SELECT 
      COALESCE(c.pre_id, c.post_id) as memory_id,
      AVG(c.coactivation_count) as avg_coactivation,
      MAX(c.coactivation_count) as max_coactivation,
      COUNT(*) as total_connections,
      
      -- Hebbian strength calculation: ΔW = η × coactivation × (1 - current_strength)
      AVG(
        {{ var('hebbian_learning_rate') }} * 
        LEAST(c.coactivation_count, 10.0) / 10.0 *  -- Normalize to prevent saturation
        (1.0 - COALESCE(m.consolidated_strength, 0.1))  -- Prevent runaway potentiation
      ) as hebbian_delta
    FROM coactivation c
    LEFT JOIN {{ ref('memory_replay') }} m ON (m.id = c.pre_id OR m.id = c.post_id)
    GROUP BY COALESCE(c.pre_id, c.post_id)
  )
  
  -- Step 3: Update consolidated strength with Hebbian learning
  UPDATE {{ ref('memory_replay') }} m
  SET 
    consolidated_strength = LEAST(1.0, 
      consolidated_strength * (1 + COALESCE(h.hebbian_delta, 0))
    ),
    hebbian_strength = COALESCE(h.avg_coactivation, 0),
    last_hebbian_update = CURRENT_TIMESTAMP
  FROM hebbian_updates h
  WHERE m.id = h.memory_id
    AND h.hebbian_delta > 0.001;  -- Only update meaningful changes
    
  {{ log("Hebbian learning applied to " ~ run_query("SELECT COUNT(*) FROM hebbian_updates")[0][0] ~ " memory connections", info=true) }}
{% endmacro %}

{# Advanced synaptic homeostasis for network stability and pruning #}
{% macro synaptic_homeostasis() %}
  {#
    Comprehensive synaptic homeostasis implementation:
    - Weekly normalization to prevent runaway potentiation
    - Weak connection pruning (< 0.01 threshold)
    - Network stability maintenance via scaling
    - Biologically accurate homeostatic plasticity
  #}
  
  {# Parameter validation for biological realism #}
  {% if var('homeostasis_target') > 0.8 or var('homeostasis_target') < 0.2 %}
    {{ log("WARNING: Homeostasis target outside biological range (0.2-0.8): " ~ var('homeostasis_target'), info=true) }}
  {% endif %}
  
  {% if var('weak_connection_threshold') > 0.05 %}
    {{ log("WARNING: Weak connection threshold may be too high for realistic pruning: " ~ var('weak_connection_threshold'), info=true) }}
  {% endif %}
  
  {# Check if required relations exist #}
  {% set ltm_relation = ref('ltm_semantic_network') %}
  {% if not ltm_relation %}
    {{ log("ERROR: ltm_semantic_network relation not found - skipping homeostasis", info=true) }}
    {{ return('') }}
  {% endif %}
  
  -- Step 1: Calculate current network statistics
  WITH network_stats AS (
    SELECT 
      COUNT(*) as total_connections,
      AVG(retrieval_strength) as mean_strength,
      STDDEV(retrieval_strength) as std_strength,
      PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY retrieval_strength) as median_strength,
      MAX(retrieval_strength) as max_strength,
      MIN(retrieval_strength) as min_strength
    FROM {{ ref('ltm_semantic_network') }}
    WHERE retrieval_strength > 0
  ),
  
  -- Step 2: Identify connections for homeostatic scaling
  scaling_targets AS (
    SELECT 
      *,
      ns.mean_strength,
      -- Calculate scaling factor to normalize around target (0.5)
      CASE 
        WHEN ns.mean_strength > {{ var('homeostasis_target') }} * 1.5 THEN
          {{ var('homeostasis_target') }} / NULLIF(ns.mean_strength, 0)  -- Scale down
        WHEN ns.mean_strength < {{ var('homeostasis_target') }} * 0.5 THEN  
          {{ var('homeostasis_target') }} / NULLIF(ns.mean_strength, 0)  -- Scale up
        ELSE 1.0  -- No scaling needed
      END as scaling_factor,
      
      -- Identify weak connections for pruning
      CASE WHEN retrieval_strength < {{ var('weak_connection_threshold') }} THEN TRUE
           ELSE FALSE END as prune_connection
    FROM {{ ref('ltm_semantic_network') }} ltm
    CROSS JOIN network_stats ns
  )
  
  -- Step 3: Apply homeostatic scaling to prevent runaway potentiation
  UPDATE {{ ref('ltm_semantic_network') }}
  SET 
    retrieval_strength = LEAST(1.0, GREATEST(0.0,
      retrieval_strength * scaling_factor * 
      (1.0 + {{ var('homeostasis_adjustment_rate') }} * 
       ({{ var('homeostasis_target') }} - retrieval_strength))
    )),
    last_homeostasis_at = CURRENT_TIMESTAMP
  FROM scaling_targets st
  WHERE ltm_semantic_network.id = st.id
    AND st.scaling_factor != 1.0;
  
  -- Step 4: Prune weak synaptic connections to maintain network efficiency  
  DELETE FROM {{ ref('ltm_semantic_network') }}
  WHERE retrieval_strength < {{ var('weak_connection_threshold') }}
    AND memory_age = 'remote'
    AND access_frequency < 2;  -- Only prune rarely accessed weak connections
    
  -- Step 5: Log homeostasis results
  {% if execute %}
    {% set pruned_count_query %}
      SELECT COUNT(*) FROM {{ ref('ltm_semantic_network') }}
      WHERE retrieval_strength < {{ var('weak_connection_threshold') }}
    {% endset %}
    {% set results = run_query(pruned_count_query) %}
    {% if results %}
      {{ log("Synaptic homeostasis completed - Weak connections remaining: " ~ results[0][0], info=true) }}
    {% endif %}
  {% endif %}
  
  -- Step 6: Update network health metrics
  CREATE OR REPLACE VIEW biological_memory.network_health AS
  SELECT 
    COUNT(*) as total_synapses,
    AVG(retrieval_strength) as avg_strength,
    COUNT(CASE WHEN retrieval_strength > 0.7 THEN 1 END) as strong_connections,
    COUNT(CASE WHEN retrieval_strength < 0.1 THEN 1 END) as weak_connections,
    MAX(last_homeostasis_at) as last_homeostasis,
    CURRENT_TIMESTAMP as health_check_at
  FROM {{ ref('ltm_semantic_network') }};
  
  {{ log("Synaptic homeostasis completed - Network rebalanced and pruned", info=true) }}
{% endmacro %}

{# REM-sleep-like creative association strengthening with LLM integration #}
{% macro strengthen_associations() %}
  {#
    Advanced association strengthening simulating REM sleep:
    - Random memory pair selection for novel connections
    - LLM-based creative linking for distant associations  
    - Biologically plausible creative connection discovery
    - Integration with existing semantic networks
  #}
  
  {% if execute %}
    {{ log("Starting REM-sleep-like creative association strengthening", info=true) }}
  {% endif %}
  
  -- Step 1: Select random memory pairs for creative linking (REM-like process)
  WITH dream_memory_pairs AS (
    SELECT 
      a.id as memory_a_id,
      b.id as memory_b_id,
      a.semantic_gist as gist_a,
      b.semantic_gist as gist_b,
      a.semantic_category as category_a,
      b.semantic_category as category_b,
      a.consolidated_strength as strength_a,
      b.consolidated_strength as strength_b
    FROM {{ ref('ltm_semantic_network') }} a
    CROSS JOIN {{ ref('ltm_semantic_network') }} b
    WHERE a.id < b.id  -- Prevent duplicate pairs
      AND a.semantic_category != b.semantic_category  -- Focus on distant associations
      AND a.consolidated_strength > 0.3  -- Only consider moderately strong memories
      AND b.consolidated_strength > 0.3
      AND RANDOM() < 0.001  -- Random selection (0.1% of all pairs)
    ORDER BY RANDOM()
    LIMIT {{ var('rem_association_batch_size') }}  -- Limit computational load
  ),
  
  -- Step 2: Generate creative links using rule-based patterns (LLM placeholder)
  creative_connections AS (
    SELECT 
      *,
      -- LLM-enhanced creative linking with REM-like association generation
      COALESCE(
        TRY_CAST(
          prompt(
            'gpt-oss',
            'Generate a creative association between these two memory concepts. ' ||
            'Memory A (category: ' || category_a || '): ' || LEFT(gist_a, 100) || '. ' ||
            'Memory B (category: ' || category_b || '): ' || LEFT(gist_b, 100) || '. ' ||
            'Find novel connections that could lead to insights. Return JSON with keys: ' ||
            'creative_link (string describing the connection), connection_type (string), ' ||
            'novelty_score (0-1 float), plausibility (0-1 float).',
            'http://{{ env_var("OLLAMA_URL") }}',
            300
          )::VARCHAR AS JSON
        ),
        -- Fallback to rule-based creative associations
        CASE 
          WHEN (category_a = 'work_meeting' AND category_b = 'financial_planning') THEN
            '{"creative_link": "Strategic business alignment between team coordination and resource allocation", 
              "connection_type": "strategic_synthesis", "novelty_score": 0.8, "plausibility": 0.9}'
          WHEN (category_a = 'technical_procedures' AND category_b = 'social_cognition') THEN
            '{"creative_link": "Human-centered technical design bridging systematic processes with user empathy", 
              "connection_type": "human_technology_interface", "novelty_score": 0.7, "plausibility": 0.8}'
          ELSE 
            '{"creative_link": "Cross-domain pattern recognition connecting diverse cognitive processes", 
              "connection_type": "general_synthesis", "novelty_score": 0.5, "plausibility": 0.7}'
        END::JSON
      ) as creative_association,
      
      -- Calculate creative association strength
      (strength_a * 0.4 + strength_b * 0.4 + 
       (CASE WHEN category_a != category_b THEN 0.2 ELSE 0.0 END)  -- Novelty bonus
      ) * {{ var('rem_creativity_factor') }} as creative_strength
    FROM dream_memory_pairs
    WHERE gist_a IS NOT NULL AND gist_b IS NOT NULL
  ),
  
  -- Step 3: Filter for high-quality creative connections
  validated_connections AS (
    SELECT 
      *,
      CAST(json_extract_string(creative_association, '$.novelty_score') AS FLOAT) as novelty_score,
      CAST(json_extract_string(creative_association, '$.plausibility') AS FLOAT) as plausibility_score,
      json_extract_string(creative_association, '$.connection_type') as connection_type
    FROM creative_connections
    WHERE creative_strength > {{ var('creative_connection_threshold') }}
      AND CAST(json_extract_string(creative_association, '$.plausibility') AS FLOAT) > 0.6
  )
  
  -- Step 4: Insert novel creative associations into semantic network
  INSERT INTO biological_memory.creative_associations (
    source_memory_id,
    target_memory_id,
    source_gist,
    target_gist,
    creative_link_description,
    connection_type,
    association_strength,
    novelty_score,
    plausibility_score,
    discovery_method,
    created_during_rem,
    created_at
  )
  SELECT 
    memory_a_id,
    memory_b_id,
    gist_a,
    gist_b,
    json_extract_string(creative_association, '$.creative_link'),
    connection_type,
    creative_strength,
    novelty_score,
    plausibility_score,
    'rem_sleep_simulation',
    TRUE,
    CURRENT_TIMESTAMP
  FROM validated_connections;
  
  -- Step 5: Strengthen existing associations based on recent usage
  UPDATE biological_memory.memory_associations 
  SET 
    association_strength = LEAST(1.0, 
      association_strength * (1.0 + {{ var('association_strengthening_rate') }})
    ),
    last_strengthened_at = CURRENT_TIMESTAMP
  WHERE last_accessed_at > CURRENT_TIMESTAMP - INTERVAL '{{ var('consolidation_window_hours') }} HOURS'
    AND association_strength > 0.1;
  
  {% if execute %}
    {% set creative_count_query %}
      SELECT COUNT(*) FROM validated_connections
    {% endset %}
    {% set results = run_query(creative_count_query) %}
    {% if results %}
      {{ log("REM-sleep simulation: " ~ results[0][0] ~ " novel creative connections discovered", info=true) }}
    {% endif %}
  {% endif %}
  
  {{ log("Association strengthening completed - Novel connections and existing reinforcement applied", info=true) }}
{% endmacro %}

{# Calculate memory statistics for monitoring #}
{% macro calculate_memory_stats(memory_type) %}
  {# Post-hook macro to calculate and log memory statistics #}
  {% if execute %}
    {% set stats_query %}
      SELECT 
        COUNT(*) as total_memories,
        AVG(activation_strength) as avg_activation,
        MAX(activation_strength) as max_activation,
        COUNT(CASE WHEN activation_strength > {{ var('long_term_memory_threshold') }} THEN 1 END) as long_term_count
      FROM {{ this }}
    {% endset %}
    
    {% set results = run_query(stats_query) %}
    {% if results %}
      {% for row in results %}
        {{ log(memory_type ~ " stats - Total: " ~ row[0] ~ ", Avg Activation: " ~ row[1] ~ ", LTM Count: " ~ row[3], info=true) }}
      {% endfor %}
    {% endif %}
  {% endif %}
{% endmacro %}

{# Create optimized indexes for memory tables #}
{% macro create_memory_indexes() %}
  {# Post-hook macro to create performance indexes #}
  {% if execute %}
    {{ log("Creating optimized indexes for memory table", info=true) }}
  {% endif %}
  
  {% set index_statements = [
    "CREATE INDEX IF NOT EXISTS idx_" ~ this.name ~ "_activation ON " ~ this ~ " (activation_strength DESC)",
    "CREATE INDEX IF NOT EXISTS idx_" ~ this.name ~ "_timestamp ON " ~ this ~ " (created_at, last_accessed_at)",
    "CREATE INDEX IF NOT EXISTS idx_" ~ this.name ~ "_type ON " ~ this ~ " (memory_type)",
    "CREATE INDEX IF NOT EXISTS idx_" ~ this.name ~ "_concepts ON " ~ this ~ " USING GIN(concepts)"
  ] %}
  
  {% for statement in index_statements %}
    {{ statement }};
  {% endfor %}
{% endmacro %}

{# Update semantic knowledge graph connections #}
{% macro update_semantic_graph() %}
  {# Post-hook macro to maintain semantic relationship graph #}
  {% if execute %}
    {{ log("Updating semantic knowledge graph", info=true) }}
  {% endif %}
  
  -- Refresh materialized view of semantic connections
  REFRESH MATERIALIZED VIEW IF EXISTS {{ this.schema }}.semantic_graph_view;
  
  -- Update graph centrality measures
  UPDATE {{ this.schema }}.semantic_concepts 
  SET 
    centrality_score = (
      SELECT COUNT(*) * 1.0 / (SELECT COUNT(*) FROM {{ this.schema }}.semantic_concepts)
      FROM {{ this.schema }}.memory_associations ma
      WHERE ma.source_concept = semantic_concepts.concept_id 
         OR ma.target_concept = semantic_concepts.concept_id
    ),
    last_updated_at = CURRENT_TIMESTAMP;
{% endmacro %}

{# Decay unused synaptic connections over time #}
{% macro synaptic_decay(connection_table, decay_rate) %}
  {# Apply synaptic decay to unused connections #}
  UPDATE {{ connection_table }}
  SET 
    connection_strength = GREATEST(0.0,
      connection_strength * (1.0 - {{ decay_rate }})
    ),
    last_decayed_at = CURRENT_TIMESTAMP
  WHERE last_accessed_at < CURRENT_TIMESTAMP - INTERVAL '24 HOURS'
    AND connection_strength > 0.01  -- Only decay non-trivial connections
{% endmacro %}

{# Generate memory consolidation batch #}
{% macro get_consolidation_batch(batch_size) %}
  {# Select memories for consolidation based on biological criteria #}
  (
    SELECT memory_id, content, activation_strength, memory_type
    FROM {{ ref('working_memory') }}
    WHERE activation_strength > {{ var('plasticity_threshold') }}
      AND created_at > CURRENT_TIMESTAMP - INTERVAL '{{ var('short_term_memory_duration') }} SECONDS'
    ORDER BY activation_strength DESC, frequency_accessed DESC
    LIMIT {{ batch_size }}
  )
{% endmacro %}

{# Implement memory interference patterns #}
{% macro calculate_interference(similarity_score, time_difference) %}
  {# Calculate retroactive and proactive interference #}
  {# Higher similarity and closer timing = more interference #}
  (
    {{ similarity_score }} * EXP(-{{ time_difference }} / 3600.0)  -- Exponential decay over hours
  )
{% endmacro %}

{# Semantic similarity using vector operations #}
{% macro semantic_similarity(vector1, vector2) %}
  {# Calculate cosine similarity between semantic vectors #}
  {# Returns value between -1 and 1, where 1 is identical #}
  (
    array_dot_product({{ vector1 }}, {{ vector2 }}) / 
    (array_magnitude({{ vector1 }}) * array_magnitude({{ vector2 }}))
  )
{% endmacro %}
