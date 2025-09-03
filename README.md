# Codex Dreams

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A computational model of human memory systems implementing biologically-accurate cognitive processes through modern data infrastructure.

> **⚠️ Development Notice**  
> This project was developed through iterative AI-assisted "vibe coding" - building functionality through natural language descriptions rather than traditional software design. While the system is functional and thoroughly tested, expect unconventional patterns and treat as experimental. Extensive development environment testing recommended before any production use.

## Overview

Codex Dreams models the human memory formation process through four interconnected stages that mirror biological cognition:

**Working Memory** enforces Miller's 7±2 capacity constraint with 5-minute attention windows, processing incoming information with cognitive load limitations that match human psychology research.

**Short-Term Memory** organizes experiences into hierarchical episodes (goal→task→action) with spatial-temporal binding, implementing the episodic memory structures documented in cognitive neuroscience literature.

**Memory Consolidation** simulates hippocampal replay through Hebbian learning mathematics (`learning_rate * pre_strength * post_strength`), strengthening associations between co-activated memories according to biological timing patterns.

**Long-Term Memory** creates semantic networks through vector embeddings and relationship graphs, organizing knowledge into cortical-style hierarchies with biologically-informed retrieval mechanisms.

The system processes real memory data through this pipeline, providing both a research platform for testing memory theories and a practical tool for understanding how biological memory systems could be implemented computationally.

## Architecture

```mermaid
graph TD
    A[PostgreSQL: Raw Memories] -->|postgres_scanner| B[DuckDB Analytics Engine]
    B -->|Stage 1| C[Working Memory<br/>Miller's 7±2, 5-min windows]
    C -->|Stage 2| D[Short-Term Episodes<br/>Goal-task-action hierarchies]
    D -->|Stage 3| E[Consolidation<br/>Hebbian learning, threshold 0.5]
    E -->|Stage 4| F[Long-Term Semantic<br/>Vector networks, retrieval paths]
    
    G[Ollama LLM<br/>Entity extraction & embeddings] -->|Enrichment| C
    G -->|Analysis| D
    G -->|Semantic processing| E
    
    H[Write-back Services<br/>Real-time persistence] -->|Results| I[Dreams Schema<br/>Queryable memory structures]
    
    F -->|Consolidated knowledge| H
    E -->|Strengthened associations| H
    D -->|Episode structures| H
    C -->|Working snapshots| H
```

## What Makes This Interesting

**Biological Fidelity**: Implementation validates against foundational research including Miller (1956) on working memory capacity, Hebb (1949) on synaptic plasticity, and McGaugh (2000) on memory consolidation. The system enforces cognitive constraints that match human limitations and timing patterns.

**Real-Time Processing**: Unlike static models, this processes actual memory streams with sub-millisecond response times. The system handles continuous memory ingestion while maintaining biological timing constraints for each processing stage.

**Hybrid Architecture**: Combines DuckDB's analytical capabilities for complex memory transformations with PostgreSQL's reliability for persistent storage. The result is a system that can perform sophisticated cognitive modeling at scale while maintaining data integrity.

**Production Implementation**: Rather than academic proof-of-concept, this is built for operational use with comprehensive error handling, performance optimization, and monitoring. It processes thousands of memories per minute while maintaining biological accuracy.

## Key Components

### Memory Processing Pipeline
- **17+ dbt models** implementing each memory stage with biological parameters
- **Incremental processing** for real-time memory flow with proper temporal windowing  
- **Biological timing** enforcement matching human cognitive research findings
- **Vector embedding** generation through local Ollama LLM integration

### Data Architecture  
- **Dreams Schema** with 6 core tables representing different memory stages and types
- **Write-back services** ensuring processed memories persist for analysis and retrieval
- **Optimization layers** including specialized indexes and materialized views for query performance
- **Cross-database integration** connecting analytical processing with operational storage

### Testing & Validation
- **1,555+ test files** covering biological accuracy, performance benchmarks, and integration scenarios
- **Neuroscience validation** tests ensuring mathematical models match published research
- **Performance testing** with sub-100ms requirements matching biological timing constraints
- **End-to-end validation** of complete memory formation cycles

## Quick Start

```bash
# Installation
git clone https://github.com/Ladvien/codex-dreams.git
cd codex-dreams
pip install -e .

# Configuration (edit with your details)
cp .env.example .env

# Core services needed
# - PostgreSQL database for source/target data  
# - Ollama server with gpt-oss:20b and nomic-embed-text models
# - 8GB+ RAM for memory consolidation processing

# Initialize and run
dbt run --profiles-dir ./biological_memory
python query_memories.py --dreams-stats
```

### Essential Configuration
```bash
# .env file
POSTGRES_DB_URL=postgresql://user:pass@host:5432/codex_db
OLLAMA_URL=http://localhost:11434
DUCKDB_PATH=./biological_memory/dbs/memory.duckdb
```

## Use Cases

**Memory Research**: Test theories about human memory formation, consolidation, and retrieval using computational models that enforce biological constraints.

**Cognitive Modeling**: Build systems that process information using human-like memory limitations and timing patterns rather than traditional database approaches.

**Knowledge Management**: Implement memory systems that organize information hierarchically and associatively, mimicking how humans naturally structure knowledge.

**AI System Design**: Create AI agents with memory systems that follow biological patterns, potentially leading to more human-like reasoning and learning behaviors.

## Development

### Project Structure
```
src/services/          # Core processing services (LLM, write-back, orchestration)
sql/                   # Database schemas and optimization scripts  
biological_memory/     # dbt models implementing memory stages
tests/                 # Comprehensive test suite with biological validation
```

### Key Commands
```bash
# Run complete memory pipeline
dbt run --profiles-dir ./biological_memory

# Test biological accuracy 
pytest tests/biological/ -v

# Performance benchmarks
pytest tests/performance/ --benchmark-only

# Memory system health check
python -m src.monitoring.biological_parameter_monitor
```

### Biological Parameters
The system exposes key parameters for experimentation:
```yaml
# biological_memory/dbt_project.yml
vars:
  working_memory_capacity: 7        # Miller's 7±2 limit
  consolidation_threshold: 0.5      # Strength needed for long-term storage
  hebbian_learning_rate: 0.1        # Synaptic strengthening rate
  forgetting_rate: 0.05            # Memory decay over time
```

## Documentation

- **Architecture Details**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Database Schema**: [docs/DREAMS_SCHEMA.md](docs/DREAMS_SCHEMA.md) 
- **Biological Models**: See dbt documentation with `dbt docs serve`
- **API Reference**: Docstrings throughout source code with type hints

## Contributing

This project bridges neuroscience research with data engineering. Contributions welcome from:
- **Cognitive scientists** interested in computational memory models
- **Data engineers** working on novel database architectures  
- **ML researchers** exploring biologically-inspired AI systems
- **Systems developers** building human-like reasoning capabilities

## License

GNU General Public License v3.0 - see [LICENSE](LICENSE)

---

*Memory is not a recording device but a reconstructive process. This system explores what that means computationally.*