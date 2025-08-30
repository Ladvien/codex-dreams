# Data Model & Entity Relationship Documentation

## Overview

The Codex Dreams biological memory system implements a sophisticated data pipeline that models human cognitive memory processes through a PostgreSQL → DuckDB → PostgreSQL architecture.

## Entity Relationship Diagram

```mermaid
erDiagram
    MEMORIES ||--o{ INSIGHTS : "generates"
    MEMORIES ||--o{ MEMORY_STATS : "tracks"
    MEMORIES ||--o{ WORKING_MEMORY : "feeds_into"
    WORKING_MEMORY ||--o{ SHORT_TERM_MEMORY : "progresses_to"
    SHORT_TERM_MEMORY ||--o{ MEMORY_CONSOLIDATION : "consolidates_into"
    MEMORY_CONSOLIDATION ||--o{ LONG_TERM_MEMORY : "becomes"
    
    MEMORIES {
        uuid id PK "Primary key"
        text content "Memory content"
        varchar content_hash UK "Unique hash"
        text_array tags "Associated tags"
        memory_tier tier "Current memory tier"
        text summary "LLM-generated summary"
        jsonb context "Additional context"
        timestamptz created_at "Creation timestamp"
        timestamptz updated_at "Last update"
    }
    
    INSIGHTS {
        uuid id PK "Primary key"
        text content "Insight content"
        insight_type type "pattern|connection|learning"
        float confidence_score "0.0-1.0"
        uuid_array source_memory_ids FK "Source memories"
        jsonb metadata "Processing metadata"
        text_array tags "Generated tags"
        memory_tier tier "Quality tier"
        timestamptz created_at "Creation timestamp"
        timestamptz updated_at "Last update"
        float feedback_score "User feedback"
        int version "Version number"
    }
    
    MEMORY_STATS {
        text key PK "Statistic key"
        float value "Statistic value"
        timestamptz timestamp "Measurement time"
    }
    
    WORKING_MEMORY {
        uuid memory_id FK "Memory ID"
        int attention_rank "1-7 (Miller limit)"
        float activation_strength "Current activation"
        timestamptz entry_time "Entry timestamp"
        boolean in_focus "Currently active"
    }
    
    SHORT_TERM_MEMORY {
        uuid memory_id FK "Memory ID"
        uuid episode_id "Hierarchical episode"
        int hierarchy_level "0:goal, 1:task, 2:action"
        jsonb spatial_context "Egocentric/allocentric"
        float decay_rate "Memory decay factor"
        timestamptz episode_start "Episode beginning"
        timestamptz episode_end "Episode completion"
    }
    
    MEMORY_CONSOLIDATION {
        uuid memory_id FK "Memory ID"
        float hebbian_strength "Synaptic strength"
        int replay_count "Replay iterations"
        jsonb associated_patterns "Related memories"
        float consolidation_score "Transfer threshold"
        text semantic_gist "Extracted meaning"
        timestamptz consolidation_time "Processing time"
    }
    
    LONG_TERM_MEMORY {
        uuid memory_id FK "Memory ID"
        text semantic_category "Cortical region"
        float stability_score "Long-term stability"
        jsonb network_connections "Semantic network"
        float centrality_score "Network importance"
        int retrieval_count "Access frequency"
        timestamptz last_retrieval "Last accessed"
    }
```

## Data Flow Architecture

```mermaid
graph TB
    subgraph "PostgreSQL (Source)"
        PG_MEM[memories table]
        PG_INS[insights table]
        PG_STATS[memory_stats table]
    end
    
    subgraph "DuckDB (Processing)"
        subgraph "Stage 1: Working Memory"
            WM_CTX[wm_active_context]
            WM_ATT[wm_attention_gate]
            WM_CAP[wm_capacity_management]
        end
        
        subgraph "Stage 2: Short-Term Memory"
            STM_EP[stm_hierarchical_episodes]
            STM_SP[stm_spatial_binding]
            STM_DEC[stm_decay_modeling]
        end
        
        subgraph "Stage 3: Consolidation"
            CON_REP[memory_replay]
            CON_HEB[hebbian_strengthening]
            CON_FOR[competitive_forgetting]
        end
        
        subgraph "Stage 4: Long-Term Memory"
            LTM_SEM[semantic_networks]
            LTM_CRT[cortical_organization]
            LTM_STB[stable_memories]
        end
    end
    
    subgraph "Ollama LLM"
        LLM_ENR[Entity Extraction]
        LLM_TOP[Topic Analysis]
        LLM_INS[Insight Generation]
    end
    
    PG_MEM --> WM_CTX
    WM_CTX --> WM_ATT --> WM_CAP
    WM_CAP --> STM_EP
    STM_EP --> STM_SP --> STM_DEC
    STM_DEC --> CON_REP
    CON_REP --> CON_HEB --> CON_FOR
    CON_FOR --> LTM_SEM
    LTM_SEM --> LTM_CRT --> LTM_STB
    
    WM_CTX -.-> LLM_ENR
    STM_EP -.-> LLM_TOP
    LTM_STB -.-> LLM_INS
    
    LLM_INS --> PG_INS
    LTM_STB --> PG_MEM
```

## Table Purposes & Biological Mapping

### PostgreSQL Tables (Persistent Storage)

#### `memories`
- **Purpose**: Primary storage for all memory records
- **Biological Analog**: Hippocampal memory traces
- **Key Features**:
  - Unique content hashing prevents duplicates
  - Tier system tracks memory progression
  - Tags enable semantic categorization
  - Timestamps track temporal dynamics

#### `insights`
- **Purpose**: Stores generated insights from memory processing
- **Biological Analog**: Prefrontal cortex abstractions
- **Key Features**:
  - Links to source memories via foreign keys
  - Confidence scoring for quality assessment
  - Metadata preserves processing context
  - Version tracking for insight evolution

#### `memory_stats`
- **Purpose**: System health and performance metrics
- **Biological Analog**: Homeostatic monitoring
- **Key Features**:
  - Real-time performance tracking
  - Memory system health indicators
  - Processing throughput metrics

### DuckDB Processing Stages

#### Stage 1: Working Memory Models
- **Purpose**: Implements attention and capacity limits
- **Biological Analog**: Prefrontal cortex working memory
- **Key Models**:
  - `wm_active_context`: Current attention focus
  - `wm_attention_gate`: Filtering mechanism
  - `wm_capacity_management`: Miller's 7±2 enforcement

#### Stage 2: Short-Term Memory Models
- **Purpose**: Hierarchical episode construction
- **Biological Analog**: Hippocampal episodic binding
- **Key Models**:
  - `stm_hierarchical_episodes`: Goal-task-action decomposition
  - `stm_spatial_binding`: Egocentric/allocentric representations
  - `stm_decay_modeling`: Temporal decay functions

#### Stage 3: Consolidation Models
- **Purpose**: Memory strengthening and transfer
- **Biological Analog**: Sleep-dependent consolidation
- **Key Models**:
  - `memory_replay`: Hippocampal replay simulation
  - `hebbian_strengthening`: Synaptic plasticity
  - `competitive_forgetting`: Weak memory elimination

#### Stage 4: Long-Term Memory Models
- **Purpose**: Semantic organization and retrieval
- **Biological Analog**: Cortical memory storage
- **Key Models**:
  - `semantic_networks`: Conceptual relationships
  - `cortical_organization`: Regional categorization
  - `stable_memories`: Permanent storage

## Key Relationships

### Memory Progression
```
memories → working_memory → short_term_memory → consolidation → long_term_memory
```

### Insight Generation
```
memories + consolidation → Ollama LLM → insights
```

### Biological Parameters
- **Working Memory Capacity**: 7±2 items (Miller's Law)
- **Short-Term Duration**: 30 seconds
- **Consolidation Threshold**: 0.6 strength
- **Hebbian Learning Rate**: 0.1
- **Forgetting Rate**: 0.05

## Data Integrity & Constraints

### Primary Keys
- All tables use UUID primary keys for distributed compatibility
- Content hashing provides natural unique constraints

### Foreign Key Relationships
- `insights.source_memory_ids[]` → `memories.id`
- All processing stages reference `memories.id`

### Cascading Operations
- Memory deletion cascades through all processing stages
- Insight generation preserves source memory references

## Performance Considerations

### Indexes
- GIN indexes on array columns (tags, source_memory_ids)
- B-tree indexes on timestamps for temporal queries
- Hash indexes on content_hash for duplicate detection

### Materialization Strategy
- Working memory: Ephemeral (real-time)
- Short-term memory: Views (dynamic)
- Consolidation: Incremental tables (efficient updates)
- Long-term memory: Tables (persistent)

## Missing Components (Identified Gaps)

1. **User Feedback Loop**: No mechanism to incorporate user ratings
2. **Memory Retrieval API**: No documented query interface
3. **Conflict Resolution**: No handling for contradictory memories
4. **Privacy Controls**: No PII detection or redaction
5. **Multi-User Support**: Single-user system currently

## Recommendations

### Immediate Priority
1. Create visual ERD diagrams in documentation
2. Add API documentation for memory operations
3. Implement user feedback mechanisms

### Future Enhancements
1. Add memory conflict resolution
2. Implement privacy controls
3. Design multi-user architecture
4. Add memory export/import capabilities

---

*Generated: 2025-08-30*
*Status: Initial documentation - requires validation with implementation*