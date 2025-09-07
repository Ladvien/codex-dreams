#!/bin/bash

# Biological Memory Pipeline Orchestrator
# Implements biological rhythms for memory consolidation
# Based on human cognitive cycles and neuroscience research

set -e

# Load environment variables
if [ -f "$(dirname "$0")/../.env" ]; then
    source "$(dirname "$0")/../.env"
fi

# Configuration
PROJECT_DIR="${DBT_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
PROFILES_DIR="${DBT_PROFILES_DIR:-$PROJECT_DIR}"
LOG_DIR="${PROJECT_DIR}/logs/biological_rhythms"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RHYTHM_TYPE="${1:-continuous}"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/${RHYTHM_TYPE}_${TIMESTAMP}.log"
}

# Health check function
health_check() {
    log "Performing health check..."

    # Check DuckDB availability
    if ! duckdb "$DUCKDB_PATH" -c "SELECT 'DuckDB is healthy'" > /dev/null 2>&1; then
        log "ERROR: DuckDB is not accessible"
        exit 1
    fi

    # Check PostgreSQL connection
    if ! PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" > /dev/null 2>&1; then
        log "ERROR: PostgreSQL is not accessible"
        exit 1
    fi

    # Check Ollama service
    if ! curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        log "WARNING: Ollama service is not accessible (embeddings will use fallback)"
    fi

    log "Health check passed"
}

# Run dbt models based on rhythm type
run_dbt_models() {
    local models="$1"
    local full_refresh="${2:-false}"

    cd "$PROJECT_DIR"

    if [ "$full_refresh" = "true" ]; then
        log "Running dbt models with full refresh: $models"
        dbt run --profiles-dir "$PROFILES_DIR" --select "$models" --full-refresh >> "$LOG_DIR/${RHYTHM_TYPE}_${TIMESTAMP}.log" 2>&1
    else
        log "Running dbt models incrementally: $models"
        dbt run --profiles-dir "$PROFILES_DIR" --select "$models" >> "$LOG_DIR/${RHYTHM_TYPE}_${TIMESTAMP}.log" 2>&1
    fi

    if [ $? -eq 0 ]; then
        log "dbt models completed successfully"
    else
        log "ERROR: dbt models failed"
        exit 1
    fi
}

# Generate tag embeddings if needed
generate_tag_embeddings() {
    log "Checking for memories needing tag embeddings..."

    COUNT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SELECT COUNT(*) FROM public.memories WHERE tags IS NOT NULL AND array_length(tags, 1) > 0 AND tag_embedding IS NULL")

    if [ "$COUNT" -gt 0 ]; then
        log "Found $COUNT memories needing tag embeddings"
        python3 "$PROJECT_DIR/scripts/generate_tag_embeddings_postgres.py" --batch-size 100 >> "$LOG_DIR/${RHYTHM_TYPE}_${TIMESTAMP}.log" 2>&1
    else
        log "All memories have tag embeddings"
    fi
}

# Main pipeline execution
main() {
    log "========================================="
    log "Starting biological memory pipeline"
    log "Rhythm type: $RHYTHM_TYPE"
    log "========================================="

    # Perform health check
    health_check

    case "$RHYTHM_TYPE" in
        continuous)
            # Working memory updates (every 5 minutes)
            log "Processing working memory (5-minute window)"
            run_dbt_models "raw_memories"
            generate_tag_embeddings
            ;;

        rapid)
            # Short-term memory updates (every 30 minutes)
            log "Processing short-term memory consolidation"
            run_dbt_models "raw_memories memory_embeddings"
            generate_tag_embeddings
            ;;

        hourly)
            # Memory consolidation (every hour)
            log "Processing hourly memory consolidation"
            run_dbt_models "raw_memories memory_embeddings semantic_network"
            generate_tag_embeddings
            ;;

        deep_sleep)
            # Major consolidation (3 AM daily)
            log "Processing deep sleep consolidation"
            run_dbt_models "raw_memories memory_embeddings semantic_network" "true"
            generate_tag_embeddings

            # Clean up old logs
            find "$LOG_DIR" -name "*.log" -mtime +7 -delete
            log "Cleaned up logs older than 7 days"
            ;;

        rem_sleep)
            # Creative associations (90-minute cycles at night)
            log "Processing REM sleep creative associations"
            run_dbt_models "semantic_network"
            ;;

        weekly)
            # Synaptic homeostasis (Sunday 3 AM)
            log "Processing weekly synaptic homeostasis"

            # Full pipeline refresh
            run_dbt_models "raw_memories memory_embeddings semantic_network" "true"
            generate_tag_embeddings

            # Vacuum and analyze PostgreSQL
            log "Optimizing PostgreSQL database..."
            PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "VACUUM ANALYZE public.memories"

            # Clean up old logs
            find "$LOG_DIR" -name "*.log" -mtime +30 -delete
            log "Cleaned up logs older than 30 days"
            ;;

        *)
            log "ERROR: Unknown rhythm type: $RHYTHM_TYPE"
            echo "Usage: $0 {continuous|rapid|hourly|deep_sleep|rem_sleep|weekly}"
            exit 1
            ;;
    esac

    log "Pipeline completed successfully"
    log "========================================="

    # Report memory statistics
    TOTAL_MEMORIES=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM public.memories")
    WITH_EMBEDDINGS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM public.memories WHERE content_embedding IS NOT NULL")
    WITH_TAG_EMBEDDINGS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM public.memories WHERE tag_embedding IS NOT NULL")

    log "Memory Statistics:"
    log "  Total memories: $TOTAL_MEMORIES"
    log "  With content embeddings: $WITH_EMBEDDINGS"
    log "  With tag embeddings: $WITH_TAG_EMBEDDINGS"
}

# Run the main function
main
