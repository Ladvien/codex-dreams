# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a memory pipeline architecture project designed to be a high-performance, privacy-first memory management system using Rust, DuckDB, dbt Core, and local LLM processing via Ollama. The system captures, enriches, and analyzes unstructured memory data through a robust data pipeline while maintaining complete data sovereignty.

## Current State

This repository is in the initial planning phase. Only the architecture documentation exists - no actual implementation has been started. The ARCHITECTURE.md file contains comprehensive design specifications for:

- Rust-based microservices (API server, memory processor, scheduler)
- DuckDB for analytical storage with dbt transformations
- Ollama integration for local LLM processing
- GraphQL API for querying
- Docker-based deployment architecture

## Architecture Components

The system is designed as a microservices architecture with these main components:

1. **Data Collection Layer**: Rust API server, CLI tool, file system watcher
2. **Processing Layer**: Message queue, memory processor, Ollama server  
3. **Storage Layer**: DuckDB analytical store, vector store (Qdrant)
4. **Transformation Layer**: dbt Core models, Rust scheduler
5. **Query Layer**: GraphQL API, search service

## Environment Configuration

The system requires these environment variables for secure operation:

```bash
# PostgreSQL connection with credentials
export POSTGRES_DB_URL="postgresql://username:password@host:port/database"

# Ollama server endpoint  
export OLLAMA_URL="http://ollama-host:11434"
```

## Development Setup (Planned)

Based on the architecture document, the intended development setup includes:

```bash
# Set environment variables first
export POSTGRES_DB_URL="postgresql://user:pass@host:5432/db"
export OLLAMA_URL="http://ollama-host:11434"

# Install Python dependencies for dbt
python -m venv venv
source venv/bin/activate
pip install dbt-core dbt-duckdb

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull gpt-oss

# Setup DuckDB (when implemented)
duckdb memory.duckdb < init.sql

# Test connections
dbt debug

# Run pipeline
dbt run
```

## Technology Stack

- **Backend**: Rust with Actix-Web, async-graphql, tokio
- **Database**: DuckDB for analytics, Qdrant for vector storage
- **LLM**: Ollama with local models for privacy
- **Data Pipeline**: dbt Core for transformations
- **Containerization**: Docker Compose
- **License**: GPL v3

## Next Steps for Implementation

Based on the architecture, the implementation should start with:

1. Setting up the basic Rust project structure with Cargo.toml
2. Implementing the core data structures (RawMemory, ExtractedMemory)
3. Creating the basic API server with memory ingestion endpoints
4. Setting up DuckDB schema and migrations
5. Integrating Ollama for LLM processing
6. Building the dbt models for data transformation

## Performance Targets

The architecture specifies these performance benchmarks:
- Memory Ingestion: 10,000/sec at 5ms p99 latency
- LLM Processing: 100/sec at 500ms p99 latency
- Vector Search: 1,000/sec at 10ms p99 latency
- GraphQL Query: 5,000/sec at 20ms p99 latency