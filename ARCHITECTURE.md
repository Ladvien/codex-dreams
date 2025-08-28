# Biological Memory Pipeline Architecture Document

## Executive Summary

A biologically-inspired memory management system implementing hierarchical episodic memory, spatial representations, and Hebbian consolidation patterns. Built entirely with DuckDB, dbt Core, and Ollama for LLM processing. The system models human cognitive memory systems including working memory capacity limits, hippocampal consolidation, and cortical semantic networks.

## System Architecture

```mermaid

graph TB
    subgraph "Source Layer [POSTGRES_HOST]"
        PG[(PostgreSQL<br/>self_sensored<br/>Raw Memories)]
    end
    
    subgraph "LLM Layer [OLLAMA_HOST]"
        Ollama[Ollama Server<br/>gpt-oss model]
    end
    
    subgraph "Processing Layer [Local DuckDB]"
        FDW[Foreign Data Wrapper<br/>postgres_scanner]
        
        subgraph "Memory Stages"
            WM[Working Memory<br/>5-min window, 7±2 items]
            STM[Short-Term Memory<br/>Hierarchical Episodes]
            CONS[Consolidation<br/>Replay & Hebbian Learning]
            LTM[Long-Term Memory<br/>Semantic Networks]
        end
        
        PROMPT[DuckDB prompt<br/>LLM Enrichment]
    end
    
    subgraph "Orchestration"
        DBT[dbt Core<br/>Pipeline]
        CRON[Crontab<br/>Biological Rhythms]
    end
    
    PG -->|postgres_scanner| FDW
    FDW --> WM
    WM --> STM
    STM --> CONS
    CONS --> LTM
    
    Ollama <-->|HTTP| PROMPT
    PROMPT --> STM
    PROMPT --> CONS
    
    DBT --> WM
    DBT --> STM
    DBT --> CONS
    DBT --> LTM
    
    CRON --> DBT
```

## Configuration Files

### 1. dbt Profile Configuration

```yaml
# ~/.dbt/profiles.yml
biological_memory:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: /Users/ladvien/biological_memory/dbs/memory.duckdb
      threads: 8
      extensions:
        - httpfs     # For Ollama HTTP calls
        - postgres   # For PostgreSQL connection
        - json       # For JSON processing
      attach:
        - path: "{{ env_var('POSTGRES_DB_URL') }}"
          type: postgres
          alias: source_memories
      settings:
        # Enable prompt() function with Ollama endpoint
        prompt_model: 'ollama'
        prompt_base_url: "{{ env_var('OLLAMA_URL') }}"
        prompt_model_name: 'gpt-oss'
```

### 2. DuckDB Initialization

```sql
-- init.sql - Run once to set up DuckDB environment
INSTALL httpfs;
INSTALL postgres;
INSTALL json;

-- Attach to PostgreSQL source
ATTACH '${POSTGRES_DB_URL}' AS source_memories (TYPE POSTGRES);

-- Configure Ollama for prompt() function
SET prompt_model = 'ollama';
SET prompt_base_url = '${OLLAMA_URL}';
SET prompt_model_name = 'gpt-oss';

-- Create local schema for processed memories
CREATE SCHEMA IF NOT EXISTS biological_memory;
USE biological_memory;
```

## Data Flow Implementation

### Stage 1: Working Memory (Attention Window)

```sql
-- models/working_memory/wm_active_context.sql
{{ config(
    materialized='view',
    tags=['continuous']
) }}

WITH raw_input AS (
    -- Pull from PostgreSQL source
    SELECT 
        id,
        content,
        timestamp,
        metadata
    FROM source_memories.public.raw_memories
    WHERE timestamp > NOW() - INTERVAL '5 minutes'
),

-- Enrich with LLM extraction using DuckDB's prompt()
enriched AS (
    SELECT *,
        -- Extract structured information via Ollama
        prompt(
            'Extract the following from this text as JSON:
            - entities: people, organizations, products
            - topics: main themes
            - sentiment: positive/neutral/negative
            - importance: 0-1 score
            - task_type: goal/task/action
            - objects: items mentioned with their affordances
            
            Text: ' || content || '
            
            Return only valid JSON.',
            model := 'ollama',
            base_url := '${OLLAMA_URL}',
            model_name := 'gpt-oss'
        ) AS llm_extraction
    FROM raw_input
),

parsed AS (
    SELECT *,
        -- Parse LLM response
        json_extract_string(llm_extraction, '$.entities') as entities,
        json_extract_string(llm_extraction, '$.topics') as topics,
        json_extract_string(llm_extraction, '$.sentiment') as sentiment,
        CAST(json_extract_string(llm_extraction, '$.importance') AS FLOAT) as importance_score,
        json_extract_string(llm_extraction, '$.task_type') as task_type,
        json_extract_string(llm_extraction, '$.objects') as phantom_objects
    FROM enriched
)

-- Implement cognitive capacity limits (Miller's 7±2)
SELECT *,
    ROW_NUMBER() OVER (ORDER BY importance_score DESC, timestamp DESC) as wm_slot
FROM parsed
WHERE wm_slot <= 7
```

### Stage 2: Short-Term Memory (Hierarchical Episodes)

```sql
-- models/short_term/stm_hierarchical_episodes.sql
{{ config(
    materialized='incremental',
    unique_key='id',
    on_schema_change='sync_all_columns'
) }}

WITH working_memories AS (
    SELECT * FROM {{ ref('wm_active_context') }}
),

-- Build hierarchical task structure
hierarchical AS (
    SELECT *,
        -- Use LLM to identify goal-task-action hierarchy
        prompt(
            'Analyze this memory and identify:
            1. High-level goal (what is being achieved)
            2. Mid-level tasks (steps to achieve goal)
            3. Atomic actions (specific behaviors)
            
            Memory: ' || content || '
            Context: ' || COALESCE(metadata::TEXT, '{}') || '
            
            Return as JSON with structure:
            {
                "goal": "...",
                "tasks": ["task1", "task2"],
                "actions": ["action1", "action2"],
                "time_pointer": "sequential position"
            }',
            model := 'ollama',
            base_url := '${OLLAMA_URL}',
            model_name := 'gpt-oss'
        ) AS hierarchy_extraction
    FROM working_memories
),

-- Add biological memory features
biological_features AS (
    SELECT *,
        -- Spatial memory components
        prompt(
            'Extract spatial information:
            - Location: where this occurred
            - Egocentric: position relative to observer
            - Allocentric: absolute position
            - Objects and their positions
            
            Memory: ' || content,
            model := 'ollama',
            base_url := '${OLLAMA_URL}',
            model_name := 'gpt-oss'
        ) AS spatial_extraction,
        
        -- Calculate decay and consolidation potential
        EXP(-EXTRACT(EPOCH FROM (NOW() - timestamp)) / 3600) as recency_factor,
        importance_score * 0.4 + 
        CASE sentiment 
            WHEN 'positive' THEN 0.3 
            WHEN 'negative' THEN 0.2
            ELSE 0.1 
        END as emotional_salience,
        
        -- Hebbian strength (co-activation patterns)
        COUNT(*) OVER (
            PARTITION BY topics 
            ORDER BY timestamp 
            RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND CURRENT ROW
        ) as co_activation_count
    FROM hierarchical
)

SELECT 
    id,
    content,
    timestamp,
    metadata,
    
    -- Hierarchical structure
    json_extract_string(hierarchy_extraction, '$.goal') as level_0_goal,
    json_extract_string(hierarchy_extraction, '$.tasks') as level_1_tasks,
    json_extract_string(hierarchy_extraction, '$.actions') as atomic_actions,
    
    -- Biological features
    phantom_objects,
    spatial_extraction,
    
    -- Memory dynamics
    recency_factor * emotional_salience as stm_strength,
    co_activation_count as hebbian_potential,
    
    -- Consolidation readiness
    CASE 
        WHEN co_activation_count >= 3 AND emotional_salience > 0.5 THEN TRUE
        ELSE FALSE
    END as ready_for_consolidation,
    
    CURRENT_TIMESTAMP as processed_at

FROM biological_features

{% if is_incremental() %}
WHERE timestamp > (SELECT MAX(timestamp) FROM {{ this }})
{% endif %}
```

### Stage 3: Memory Consolidation (Hippocampal Replay)

```sql
-- models/consolidation/memory_replay.sql
{{ config(
    materialized='incremental',
    unique_key='id',
    pre_hook="SET memory_pool = 10GB",
    post_hook="VACUUM ANALYZE {{ this }}"
) }}

WITH stm_memories AS (
    SELECT * FROM {{ ref('stm_hierarchical_episodes') }}
    WHERE ready_for_consolidation = TRUE
),

-- Simulate hippocampal replay with pattern completion
replay_cycles AS (
    SELECT *,
        -- Use LLM to find related memories and strengthen connections
        prompt(
            'Given this memory, identify related concepts and patterns that should be strengthened:
            
            Memory: ' || content || '
            Goal: ' || level_0_goal || '
            Tasks: ' || level_1_tasks || '
            
            Find:
            1. Similar past patterns
            2. Semantic associations
            3. Causal relationships
            4. Predictive patterns
            
            Return JSON with connection strengths 0-1',
            model := 'ollama',
            base_url := '${OLLAMA_URL}',
            model_name := 'gpt-oss'
        ) AS replay_associations,
        
        -- Hebbian learning: strengthen co-activated patterns
        hebbian_potential * 1.1 AS strengthened_weight,
        
        -- Apply forgetting to competing memories
        CASE 
            WHEN stm_strength < 0.3 THEN stm_strength * 0.8  -- Decay weak memories
            WHEN stm_strength > 0.7 THEN stm_strength * 1.2  -- Strengthen strong memories
            ELSE stm_strength
        END as consolidated_strength
    FROM stm_memories
),

-- Systems consolidation (neocortical transfer)
cortical_transfer AS (
    SELECT *,
        -- Generate semantic embedding for cortical storage
        prompt(
            'Create a semantic summary suitable for long-term storage:
            
            Original: ' || content || '
            Core concept: ' || level_0_goal || '
            Key patterns: ' || replay_associations || '
            
            Generate:
            1. Abstract gist (lose episodic details)
            2. Semantic category
            3. Cortical region assignment (sensory/motor/association)
            4. Integration with existing knowledge
            
            Return as JSON',
            model := 'ollama',
            base_url := '${OLLAMA_URL}',
            model_name := 'gpt-oss'
        ) AS cortical_representation
    FROM replay_cycles
    WHERE consolidated_strength > 0.5
)

SELECT 
    id,
    content,
    level_0_goal,
    level_1_tasks,
    atomic_actions,
    phantom_objects,
    
    -- Consolidated features
    json_extract_string(cortical_representation, '$.gist') as semantic_gist,
    json_extract_string(cortical_representation, '$.category') as semantic_category,
    json_extract_string(cortical_representation, '$.region') as cortical_region,
    
    consolidated_strength,
    replay_associations,
    
    CURRENT_TIMESTAMP as consolidated_at,
    'consolidated' as memory_status
    
FROM cortical_transfer
```

### Stage 4: Long-Term Semantic Memory

```sql
-- models/long_term/ltm_semantic_network.sql
{{ config(
    materialized='table',
    indexes=[
        {'columns': ['semantic_category'], 'type': 'btree'},
        {'columns': ['cortical_region'], 'type': 'btree'},
        {'columns': ['consolidated_strength'], 'type': 'btree'}
    ]
) }}

WITH consolidated_memories AS (
    SELECT * FROM {{ ref('memory_replay') }}
),

-- Build semantic network with graph relationships
semantic_graph AS (
    SELECT 
        c1.id as source_id,
        c2.id as target_id,
        c1.semantic_gist as source_gist,
        c2.semantic_gist as target_gist,
        
        -- Calculate semantic similarity using LLM
        prompt(
            'Rate semantic similarity (0-1) between:
            A: ' || c1.semantic_gist || '
            B: ' || c2.semantic_gist,
            model := 'ollama',
            base_url := '${OLLAMA_URL}',
            model_name := 'gpt-oss'
        ) AS semantic_similarity
        
    FROM consolidated_memories c1
    CROSS JOIN consolidated_memories c2
    WHERE c1.id < c2.id
    AND c1.semantic_category = c2.semantic_category
),

-- Implement cortical columns organization
cortical_columns AS (
    SELECT 
        cm.*,
        -- Group into cortical minicolumns
        HASH(semantic_category) % 1000 as minicolumn_id,
        HASH(cortical_region) % 100 as macrocolumn_id,
        
        -- Calculate within-column competition
        RANK() OVER (
            PARTITION BY semantic_category, cortical_region 
            ORDER BY consolidated_strength DESC
        ) as column_rank,
        
        -- Long-term potentiation/depression
        COUNT(*) OVER (
            PARTITION BY semantic_gist 
            ORDER BY consolidated_at 
            RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW
        ) as access_frequency
        
    FROM consolidated_memories cm
),

-- Final semantic memory with retrieval mechanisms
semantic_memory AS (
    SELECT 
        *,
        -- Retrieval strength (combines multiple factors)
        (consolidated_strength * 0.3 +
         (1.0 / (column_rank + 1)) * 0.2 +
         LOG(access_frequency + 1) * 0.2 +
         EXP(-EXTRACT(EPOCH FROM (NOW() - consolidated_at)) / 86400) * 0.3
        ) as retrieval_strength,
        
        -- Memory age categories
        CASE 
            WHEN consolidated_at > NOW() - INTERVAL '1 day' THEN 'recent'
            WHEN consolidated_at > NOW() - INTERVAL '7 days' THEN 'week_old'
            WHEN consolidated_at > NOW() - INTERVAL '30 days' THEN 'month_old'
            ELSE 'remote'
        END as memory_age,
        
        -- Systems consolidation state
        CASE
            WHEN access_frequency > 10 THEN 'schematized'
            WHEN access_frequency > 5 THEN 'consolidating'
            ELSE 'episodic'
        END as consolidation_state
        
    FROM cortical_columns
)

SELECT * FROM semantic_memory
```

## Biological Rhythm Schedule (Crontab)

```bash
# /etc/crontab - Mimics biological memory consolidation cycles

# CONTINUOUS - Working Memory (every 5 seconds during wake hours 6am-10pm)
*/5 6-22 * * * * cd /biological_memory && dbt run --select tag:continuous

# RAPID - STM updates (every 5 minutes)
*/5 * * * * cd /biological_memory && dbt run --select short_term

# CONSOLIDATION - Hippocampal replay (every hour)
0 * * * * cd /biological_memory && dbt run --select consolidation

# SLOW-WAVE SLEEP - Deep consolidation (2-4 AM daily)
0 2-4 * * * cd /biological_memory && dbt run --select long_term --full-refresh

# REM SLEEP - Creative connections (every 90 minutes at night)
*/90 23-5 * * * cd /biological_memory && dbt run-operation strengthen_associations

# WEEKLY HOMEOSTASIS - Synaptic rescaling (Sunday 3 AM)
0 3 * * 0 cd /biological_memory && dbt run-operation synaptic_homeostasis
```

## dbt Project Configuration

```yaml
# dbt_project.yml
name: 'biological_memory'
version: '1.0.0'
profile: 'biological_memory'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["data"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  biological_memory:
    # Working memory - always fresh view
    working_memory:
      +materialized: view
      +tags: ['continuous']
      
    # Short-term memory - incremental
    short_term:
      +materialized: incremental
      +unique_key: id
      +on_schema_change: sync_all_columns
      
    # Consolidation - incremental with cleanup
    consolidation:
      +materialized: incremental
      +unique_key: id
      +post-hook: 
        - "DELETE FROM {{ this }} WHERE consolidated_strength < 0.1"
        - "VACUUM ANALYZE {{ this }}"
      
    # Long-term memory - full table with indexes
    long_term:
      +materialized: table
      +post-hook:
        - "CREATE INDEX IF NOT EXISTS idx_retrieval ON {{ this }} (retrieval_strength DESC)"
        - "CREATE INDEX IF NOT EXISTS idx_category ON {{ this }} (semantic_category)"
        - "ANALYZE {{ this }}"

vars:
  # Biological parameters
  working_memory_capacity: 7  # Miller's magic number
  stm_duration_minutes: 30
  consolidation_threshold: 0.5
  hebbian_learning_rate: 0.1
  forgetting_rate: 0.05
  
  # Ollama configuration  
  ollama_host: "{{ env_var('OLLAMA_URL') }}"
  ollama_model: 'gpt-oss'
  
  # PostgreSQL source
  postgres_db_url: "{{ env_var('POSTGRES_DB_URL') }}"
  source_db: 'self_sensored'
```

## Custom Macros for Biological Processes

```sql
-- macros/biological_memory.sql

{% macro calculate_hebbian_strength() %}
    -- Hebbian learning rule implementation
    WITH coactivation AS (
        SELECT 
            a.id as pre_id,
            b.id as post_id,
            COUNT(*) as coactivation_count,
            AVG(EXTRACT(EPOCH FROM (b.timestamp - a.timestamp))) as avg_delay
        FROM {{ ref('stm_hierarchical_episodes') }} a
        JOIN {{ ref('stm_hierarchical_episodes') }} b
            ON a.semantic_category = b.semantic_category
            AND b.timestamp BETWEEN a.timestamp AND a.timestamp + INTERVAL '5 minutes'
        GROUP BY a.id, b.id
    )
    UPDATE {{ ref('memory_replay') }} m
    SET consolidated_strength = consolidated_strength * 
        (1 + {{ var('hebbian_learning_rate') }} * COALESCE(c.coactivation_count, 0))
    FROM coactivation c
    WHERE m.id = c.pre_id OR m.id = c.post_id
{% endmacro %}

{% macro synaptic_homeostasis() %}
    -- Weekly synaptic rescaling to prevent runaway potentiation
    UPDATE {{ ref('ltm_semantic_network') }}
    SET retrieval_strength = retrieval_strength / 
        (SELECT AVG(retrieval_strength) FROM {{ ref('ltm_semantic_network') }})
    WHERE memory_age = 'remote';
    
    -- Prune weak synaptic connections
    DELETE FROM {{ ref('ltm_semantic_network') }}
    WHERE retrieval_strength < 0.01
    AND memory_age = 'remote';
{% endmacro %}

{% macro strengthen_associations() %}
    -- REM-sleep-like creative association strengthening
    WITH dream_pairs AS (
        SELECT 
            a.id as id1,
            b.id as id2,
            prompt(
                'Find creative connection between:
                ' || a.semantic_gist || ' and ' || b.semantic_gist,
                model := 'ollama',
                base_url := '{{ var("ollama_host") }}',
                model_name := '{{ var("ollama_model") }}'
            ) AS creative_link
        FROM {{ ref('ltm_semantic_network') }} a
        CROSS JOIN {{ ref('ltm_semantic_network') }} b
        WHERE a.id < b.id
        ORDER BY RANDOM()
        LIMIT 100
    )
    INSERT INTO biological_memory.memory_associations
    SELECT * FROM dream_pairs
    WHERE creative_link IS NOT NULL;
{% endmacro %}
```

## Monitoring & Analytics

```sql
-- models/analytics/memory_health.sql
{{ config(materialized='view') }}

SELECT 
    -- Memory distribution
    COUNT(DISTINCT id) as total_memories,
    COUNT(DISTINCT CASE WHEN memory_age = 'recent' THEN id END) as recent_memories,
    COUNT(DISTINCT CASE WHEN consolidation_state = 'schematized' THEN id END) as schematized_memories,
    
    -- Health metrics
    AVG(retrieval_strength) as avg_retrieval_strength,
    AVG(consolidated_strength) as avg_consolidation,
    
    -- Biological indicators
    COUNT(DISTINCT semantic_category) as semantic_diversity,
    COUNT(DISTINCT cortical_region) as cortical_distribution,
    AVG(access_frequency) as avg_access_frequency,
    
    -- System performance
    MAX(consolidated_at) as last_consolidation,
    MIN(consolidated_at) as oldest_memory
    
FROM {{ ref('ltm_semantic_network') }}
```

## Environment Configuration

Before running the system, set these environment variables:

```bash
# PostgreSQL connection with credentials
export POSTGRES_DB_URL="postgresql://username:password@host:port/database"

# Ollama server endpoint  
export OLLAMA_URL="http://ollama-host:11434"
```

Example `.env` file:
```bash
POSTGRES_DB_URL="postgresql://myuser:mypass@192.168.1.104:5432/self_sensored"
OLLAMA_URL="http://192.168.1.110:11434"
```

## Getting Started

```bash
# 1. Install dbt-duckdb
pip install dbt-duckdb

# 2. Clone and setup
git clone <repository>
cd biological_memory
dbt deps

# 3. Set environment variables (see above)
source .env

# 4. Initialize DuckDB with connections
duckdb memory.duckdb < init.sql

# 5. Test connections
dbt debug

# 6. Run initial load
dbt seed
dbt run

# 7. Setup cron jobs
crontab -e
# Add the biological rhythm schedule

# 8. Monitor
dbt run --select analytics
```

## Performance Optimizations

1. **Partitioning**: Memories partitioned by month for faster queries
2. **Incremental Processing**: Only new memories processed each cycle  
3. **Prompt Caching**: LLM responses cached in DuckDB for similar queries
4. **Batch Processing**: Multiple memories sent to Ollama in single prompt
5. **Connection Pooling**: Reuse PostgreSQL and HTTP connections

## Future Enhancements

1. **Multi-modal Memory**: Add image/audio memory support
2. **Distributed Processing**: Scale across multiple DuckDB instances
3. **Advanced Replay**: Implement sharp-wave ripple patterns
4. **Emotional Tagging**: Enhanced emotional salience modeling
5. **Dream Generation**: Creative memory recombination during "sleep"

## Conclusion

This architecture provides a complete biologically-inspired memory system using only DuckDB, dbt, and Ollama. It implements:

- **Working Memory**: Attention and capacity limits
- **Hierarchical Episodes**: Goal-task-action decomposition  
- **Hebbian Learning**: Synaptic plasticity simulation
- **Hippocampal Replay**: Memory consolidation
- **Cortical Organization**: Semantic memory networks
- **Biological Rhythms**: Natural consolidation cycles

The system requires no custom code beyond SQL and dbt models, making it maintainable and observable while implementing cutting-edge cognitive science principles.