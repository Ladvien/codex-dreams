# SQL Infrastructure Scripts

This directory contains database setup and infrastructure scripts for the Codex Dreams biological memory system. These are **one-time setup scripts**, not part of the regular dbt data transformation pipeline.

## Directory Structure

### `/setup/` - Database Initialization
Scripts to set up the initial database structure before running dbt models.

- **`create_dreams_schema.sql`** (389 lines) - Creates the main `dreams` schema with all tables for biological memory storage
  - Working memory, episodes, long-term memory, semantic networks
  - Run first to establish the target schema for dbt write-back services

- **`test_connection.sql`** (32 lines) - Basic PostgreSQL connection setup and testing
- **`test_postgres_connection.sql`** (32 lines) - Connection validation utilities

### `/optimization/` - Performance & Tuning
Scripts to optimize database performance after initial setup.

- **`postgresql_vector_optimization.sql`** (450 lines) - Performance tuning for semantic networks
  - pgvector extension setup for vector similarity searches
  - Composite indexes for biological memory access patterns
  - Query optimization for <50ms target performance

- **`duckdb_connection_manager.sql`** (120 lines) - External connection management for DuckDB
  - PostgreSQL connection via postgres_scanner
  - Ollama API connection configuration
  - Environment variable integration

### `/migration/` - Schema Evolution
Scripts for database schema changes and migrations.

- **`consolidate_schemas.sql`** (167 lines) - Migrates legacy `codex_processed` schema to `dreams`
  - Creates compatibility views for backward compatibility
  - Part of ongoing schema consolidation effort

### `/archive/` - Legacy/Superseded Scripts
Archived scripts that are no longer actively used but preserved for reference.

## Setup Sequence

1. **Initial Database Setup**:
   ```bash
   psql -f sql/setup/create_dreams_schema.sql $POSTGRES_DB_URL
   ```

2. **Test Connections**:
   ```bash
   psql -f sql/setup/test_postgres_connection.sql $POSTGRES_DB_URL
   ```

3. **Performance Optimization** (after dbt models are working):
   ```bash
   psql -f sql/optimization/postgresql_vector_optimization.sql $POSTGRES_DB_URL
   ```

4. **Schema Migration** (if upgrading from legacy schemas):
   ```bash
   psql -f sql/migration/consolidate_schemas.sql $POSTGRES_DB_URL
   ```

## Integration with dbt

These scripts prepare the database infrastructure that dbt models depend on:

- **Infrastructure → dbt**: SQL scripts create schemas, dbt models transform data
- **Write-back services**: dbt models output to tables created by these scripts
- **Connection setup**: DuckDB connections configured here, used by dbt profiles

## Environment Variables Required

Make sure these are set in your `.env` file before running setup scripts:

- `POSTGRES_DB_URL` - PostgreSQL connection string
- `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` - Individual components
- `OLLAMA_URL` - Ollama server endpoint for LLM integration

## Notes

- Run setup scripts **once** during initial deployment
- Optimization scripts can be re-run as needed for performance tuning
- Migration scripts are typically one-time operations during upgrades
- Archive directory contains legacy code for reference only