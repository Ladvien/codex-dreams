#!/bin/bash
# DBT Post-Hook Write-back Integration Script
# This script is called by dbt post-hooks to trigger memory write-back

set -e

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
WRITEBACK_SCRIPT="/Users/ladvien/codex-dreams/src/scripts/run_writeback_after_dbt.py"
DBT_TARGET_DIR="${DBT_TARGET_DIR:-./target}"
LOG_FILE="/tmp/dbt_writeback_$(date +%Y%m%d_%H%M%S).log"

echo "$(date): Starting dbt post-hook write-back integration" >> "$LOG_FILE"

# Check if dbt run was successful
if [ -f "$DBT_TARGET_DIR/run_results.json" ]; then
    # Run write-back with dbt results validation
    python3 "$WRITEBACK_SCRIPT" \
        --dbt-results "$DBT_TARGET_DIR/run_results.json" \
        --incremental \
        --batch-size 1000 \
        --log-level INFO >> "$LOG_FILE" 2>&1
else
    echo "$(date): No dbt results file found, running basic write-back" >> "$LOG_FILE"
    
    # Run write-back without validation
    python3 "$WRITEBACK_SCRIPT" \
        --incremental \
        --batch-size 1000 \
        --log-level INFO >> "$LOG_FILE" 2>&1
fi

echo "$(date): DBT post-hook write-back completed" >> "$LOG_FILE"
