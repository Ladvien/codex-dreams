#!/bin/bash

# Biological Memory System Health Monitor
# Checks system health and reports on memory processing status

set -e

# Load environment variables
if [ -f "$(dirname "$0")/../.env" ]; then
    source "$(dirname "$0")/../.env"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Health status tracking
HEALTH_STATUS="HEALTHY"
WARNINGS=0
ERRORS=0

# Print colored output
print_status() {
    local status=$1
    local message=$2

    case $status in
        "OK")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠${NC} $message"
            WARNINGS=$((WARNINGS + 1))
            [ "$HEALTH_STATUS" = "HEALTHY" ] && HEALTH_STATUS="WARNING"
            ;;
        "ERROR")
            echo -e "${RED}✗${NC} $message"
            ERRORS=$((ERRORS + 1))
            HEALTH_STATUS="CRITICAL"
            ;;
        *)
            echo "  $message"
            ;;
    esac
}

echo "========================================="
echo "Biological Memory System Health Check"
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="
echo

# Check PostgreSQL
echo "PostgreSQL Database:"
if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" > /dev/null 2>&1; then
    print_status "OK" "PostgreSQL is accessible"

    # Get memory statistics
    TOTAL_MEMORIES=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM public.memories" | tr -d ' ')
    WITH_CONTENT_EMB=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM public.memories WHERE embedding IS NOT NULL" | tr -d ' ')
    WITH_TAG_EMB=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM public.memories WHERE tag_embedding IS NOT NULL" | tr -d ' ')
    MISSING_TAG_EMB=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM public.memories WHERE tags IS NOT NULL AND array_length(tags, 1) > 0 AND tag_embedding IS NULL" | tr -d ' ')

    print_status "" "Total memories: $TOTAL_MEMORIES"
    print_status "" "With content embeddings: $WITH_CONTENT_EMB ($(( WITH_CONTENT_EMB * 100 / TOTAL_MEMORIES ))%)"
    print_status "" "With tag embeddings: $WITH_TAG_EMB ($(( WITH_TAG_EMB * 100 / TOTAL_MEMORIES ))%)"

    if [ "$MISSING_TAG_EMB" -gt 100 ]; then
        print_status "WARNING" "$MISSING_TAG_EMB memories need tag embeddings"
    fi
else
    print_status "ERROR" "PostgreSQL is not accessible"
fi
echo

# Check DuckDB
echo "DuckDB Database:"
if [ -f "$DUCKDB_PATH" ]; then
    if duckdb "$DUCKDB_PATH" -c "SELECT 'healthy'" > /dev/null 2>&1; then
        print_status "OK" "DuckDB is accessible"

        # Check table existence
        TABLES=$(duckdb "$DUCKDB_PATH" -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'main'" -noheader -csv)
        print_status "" "Tables in DuckDB: $TABLES"
    else
        print_status "ERROR" "DuckDB file exists but is not accessible"
    fi
else
    print_status "WARNING" "DuckDB file does not exist at $DUCKDB_PATH"
fi
echo

# Check Ollama Service
echo "Ollama Service:"
if curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    print_status "OK" "Ollama service is accessible at $OLLAMA_URL"

    # Check if embedding model is available
    if curl -s "$OLLAMA_URL/api/tags" | grep -q "$EMBEDDING_MODEL"; then
        print_status "OK" "Embedding model '$EMBEDDING_MODEL' is available"
    else
        print_status "WARNING" "Embedding model '$EMBEDDING_MODEL' not found"
    fi
else
    print_status "WARNING" "Ollama service is not accessible (embeddings will use fallback)"
fi
echo

# Check dbt Installation
echo "dbt Installation:"
if command -v dbt &> /dev/null; then
    DBT_VERSION=$(dbt --version | grep "installed version" | cut -d: -f2 | tr -d ' ')
    print_status "OK" "dbt is installed (version: $DBT_VERSION)"

    # Check dbt project
    if [ -f "$DBT_PROJECT_DIR/dbt_project.yml" ]; then
        print_status "OK" "dbt project found at $DBT_PROJECT_DIR"
    else
        print_status "ERROR" "dbt project not found at $DBT_PROJECT_DIR"
    fi
else
    print_status "ERROR" "dbt is not installed"
fi
echo

# Check Cron Jobs
echo "Biological Rhythms (Cron):"
CRON_COUNT=$(crontab -l 2>/dev/null | grep -c "run_pipeline.sh" || true)
if [ "$CRON_COUNT" -gt 0 ]; then
    print_status "OK" "$CRON_COUNT biological rhythm cron jobs configured"

    # Show next scheduled run times
    echo "  Next scheduled runs:"
    crontab -l | grep "run_pipeline.sh" | while read -r line; do
        if [[ ! "$line" =~ ^# ]]; then
            SCHEDULE=$(echo "$line" | awk '{print $1, $2, $3, $4, $5}')
            RHYTHM=$(echo "$line" | grep -oP 'run_pipeline.sh \K\w+')
            echo "    - $RHYTHM: $SCHEDULE"
        fi
    done
else
    print_status "WARNING" "No biological rhythm cron jobs configured"
fi
echo

# Check Recent Pipeline Runs
echo "Recent Pipeline Activity:"
LOG_DIR="${PROJECT_DIR}/logs/biological_rhythms"
if [ -d "$LOG_DIR" ]; then
    RECENT_LOGS=$(find "$LOG_DIR" -name "*.log" -mtime -1 | wc -l | tr -d ' ')
    if [ "$RECENT_LOGS" -gt 0 ]; then
        print_status "OK" "$RECENT_LOGS pipeline runs in last 24 hours"

        # Show last run status
        LAST_LOG=$(ls -t "$LOG_DIR"/*.log 2>/dev/null | head -1)
        if [ -n "$LAST_LOG" ]; then
            LAST_RUN_TIME=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$LAST_LOG" 2>/dev/null || stat -c "%y" "$LAST_LOG" 2>/dev/null | cut -d. -f1)
            LAST_STATUS=$(grep -E "(completed successfully|ERROR)" "$LAST_LOG" | tail -1)
            echo "  Last run: $LAST_RUN_TIME"
            if echo "$LAST_STATUS" | grep -q "successfully"; then
                print_status "" "Last run completed successfully"
            elif echo "$LAST_STATUS" | grep -q "ERROR"; then
                print_status "WARNING" "Last run had errors"
            fi
        fi
    else
        print_status "WARNING" "No pipeline runs in last 24 hours"
    fi
else
    print_status "WARNING" "Log directory does not exist"
fi
echo

# Check Disk Space
echo "System Resources:"
DISK_USAGE=$(df -h "$PROJECT_DIR" | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 80 ]; then
    print_status "OK" "Disk usage: ${DISK_USAGE}%"
elif [ "$DISK_USAGE" -lt 90 ]; then
    print_status "WARNING" "Disk usage high: ${DISK_USAGE}%"
else
    print_status "ERROR" "Disk usage critical: ${DISK_USAGE}%"
fi

# Check Python dependencies
if python3 -c "import psycopg2, requests, dbt" 2>/dev/null; then
    print_status "OK" "Required Python packages installed"
else
    print_status "WARNING" "Some Python packages may be missing"
fi
echo

# Summary
echo "========================================="
echo "Health Check Summary:"
if [ "$ERRORS" -gt 0 ]; then
    echo -e "${RED}Status: CRITICAL${NC}"
    echo "Errors: $ERRORS"
    echo "Warnings: $WARNINGS"
    exit 2
elif [ "$WARNINGS" -gt 0 ]; then
    echo -e "${YELLOW}Status: WARNING${NC}"
    echo "Warnings: $WARNINGS"
    exit 1
else
    echo -e "${GREEN}Status: HEALTHY${NC}"
    echo "All systems operational"
    exit 0
fi
