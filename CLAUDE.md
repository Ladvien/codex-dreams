# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a biologically-inspired memory management system implementing hierarchical episodic memory, spatial representations, and Hebbian consolidation patterns. Built entirely with DuckDB, dbt Core, and Ollama for LLM processing. The system models human cognitive memory systems including working memory capacity limits, hippocampal consolidation, and cortical semantic networks.

## Current State

This repository is in the initial planning phase. Only the architecture documentation exists - no actual implementation has been started. The ARCHITECTURE.md file contains comprehensive design specifications for a biological memory pipeline that processes memories through stages mimicking human cognitive processes.

## Architecture Components

The system implements a hierarchical memory pipeline with these stages:

1. **Working Memory**: 5-minute attention window with Miller's 7±2 capacity limit
2. **Short-Term Memory**: Hierarchical episodes with goal-task-action decomposition  
3. **Memory Consolidation**: Hippocampal replay with Hebbian learning
4. **Long-Term Memory**: Semantic networks with cortical organization

## Environment Configuration

The system uses environment variables for configuration:

```bash
# Copy and configure environment file
cp .env.example .env
# Edit .env with your database and server details
```

Required variables (see `.env.example`):
- `POSTGRES_DB_URL`: PostgreSQL connection string (source data at 192.168.1.104)
- `OLLAMA_URL`: Ollama server endpoint (192.168.1.110:11434)
- `OLLAMA_MODEL`: LLM model name (gpt-oss:20b)
- `EMBEDDING_MODEL`: Embedding model (nomic-embed-text)
- `DUCKDB_PATH`: Local DuckDB database path
- `DBT_PROJECT_DIR`: dbt project directory
- `DBT_PROFILES_DIR`: dbt profiles location

## Development Setup (Planned)

Based on the architecture document, the intended development setup includes:

```bash
# Configure environment variables
cp .env.example .env
# Edit .env with your actual values
source .env

# Install Python dependencies for dbt
python -m venv venv
source venv/bin/activate
pip install dbt-core dbt-duckdb

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull gpt-oss:20b
ollama pull nomic-embed-text

# Setup DuckDB with extensions
duckdb $DUCKDB_PATH < init.sql

# Test connections
dbt debug

# Run initial pipeline
dbt run

# Setup biological rhythm scheduling
crontab -e
# Add cron jobs for memory consolidation cycles
```

## Technology Stack

- **Database**: DuckDB for analytical processing
- **Source Data**: PostgreSQL via postgres_scanner extension
- **LLM Processing**: Ollama with local models (gpt-oss:20b)
- **Embeddings**: nomic-embed-text via Ollama
- **Transformation**: dbt Core for SQL-based transformations
- **Orchestration**: Crontab for biological rhythm scheduling
- **Extensions**: httpfs, postgres, json for DuckDB
- **License**: GPL v3

## Memory Processing Stages

### Stage 1: Working Memory
- Pulls raw memories from PostgreSQL source
- Enriches with LLM extraction (entities, topics, sentiment)
- Implements cognitive capacity limits (7±2 items)
- 5-minute sliding window

### Stage 2: Short-Term Memory  
- Builds hierarchical task structures
- Extracts spatial information (egocentric/allocentric)
- Calculates decay and emotional salience
- Tracks Hebbian co-activation patterns

### Stage 3: Memory Consolidation
- Simulates hippocampal replay
- Strengthens associated patterns
- Applies forgetting to weak memories
- Transfers to cortical storage

### Stage 4: Long-Term Memory
- Builds semantic networks
- Organizes into cortical columns
- Implements retrieval mechanisms
- Manages memory age categories

## Biological Rhythms

The system implements natural memory consolidation cycles:
- **Continuous**: Working memory updates (every 5 seconds during wake hours)
- **Rapid**: Short-term memory updates (every 5 minutes)
- **Hourly**: Memory consolidation
- **Deep Sleep**: Major consolidation (2-4 AM daily)
- **REM Sleep**: Creative associations (90-minute cycles at night)
- **Weekly**: Synaptic homeostasis (Sunday 3 AM)

## Next Steps for Implementation

Based on the architecture, the implementation should start with:

1. Setting up DuckDB with required extensions
2. Creating the dbt project structure with proper profiles
3. Implementing working memory models with LLM enrichment
4. Building hierarchical episode extraction
5. Developing consolidation mechanisms
6. Creating semantic network models
7. Setting up cron-based orchestration

## Performance Targets

The architecture specifies these biological constraints:
- Working Memory: 7±2 items maximum
- Attention Window: 5-minute sliding window
- Consolidation Threshold: 0.5 strength minimum
- Hebbian Learning Rate: 0.1
- Forgetting Rate: 0.05
- Retrieval Decay: Exponential over time

## Key Biological Parameters

Configurable via dbt variables:
- `working_memory_capacity`: 7 (Miller's magic number)
- `stm_duration_minutes`: 30
- `consolidation_threshold`: 0.5  
- `hebbian_learning_rate`: 0.1
- `forgetting_rate`: 0.05

## Testing Approach

All test files should:
- Mirror the src directory structure
- Use `_test` suffix naming convention
- Connect to TEST_DATABASE_URL for isolation
- Mock Ollama responses for offline testing
- Achieve >90% code coverage