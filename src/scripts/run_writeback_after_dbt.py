#!/usr/bin/env python3
"""
DBT Post-Processing Write-back Integration
==========================================

This script integrates the memory write-back service with dbt post-processing hooks
to automatically persist processed results to PostgreSQL after successful dbt runs.

Integration points:
- dbt post-hook execution
- Orchestration workflow integration
- Error handling and recovery
- Performance monitoring
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.incremental_processor import IncrementalProcessor
from services.memory_writeback_service import MemoryWritebackService


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Setup logging for the script"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("/tmp/dbt_writeback.log", mode="a")],
    )
    return logging.getLogger("dbt_writeback")


def validate_dbt_success(dbt_result_path: str = None) -> bool:
    """
    Validate that dbt run completed successfully

    Args:
        dbt_result_path: Path to dbt run results file

    Returns:
        True if dbt run was successful
    """
    if not dbt_result_path or not os.path.exists(dbt_result_path):
        # If no results file, assume success (for backwards compatibility)
        return True

    try:
        with open(dbt_result_path, "r") as f:
            results = json.load(f)

        # Check overall success
        success = results.get("success", False)
        failed_nodes = [
            node for node in results.get("results", []) if node.get("status") != "success"
        ]

        if not success or failed_nodes:
            logging.error(f"dbt run failed with {len(failed_nodes)} failed nodes")
            for node in failed_nodes:
                logging.error(f"Failed node: {node.get('unique_id')} - {node.get('message')}")
            return False

        return True

    except Exception as e:
        logging.error(f"Failed to validate dbt results: {e}")
        return False


def determine_processing_stages(dbt_models_executed: list = None) -> list:
    """
    Determine which write-back stages to run based on executed dbt models

    Args:
        dbt_models_executed: List of dbt model names that were executed

    Returns:
        List of processing stages to execute
    """
    if not dbt_models_executed:
        # If no model list provided, run full cycle
        return ["processed_memories", "generated_insights", "memory_associations"]

    stages = []

    # Map dbt models to write-back stages
    model_stage_mapping = {
        "memory_replay": "processed_memories",
        "consolidating_memories": "processed_memories",
        "stable_memories": "processed_memories",
        "mvp_memory_insights": "generated_insights",
        "mvp_insights_generator": "generated_insights",
        "concept_associations": "memory_associations",
        "ltm_semantic_network": "memory_associations",
    }

    executed_stages = set()
    for model in dbt_models_executed:
        stage = model_stage_mapping.get(model)
        if stage:
            executed_stages.add(stage)

    return (
        list(executed_stages)
        if executed_stages
        else ["processed_memories", "generated_insights", "memory_associations"]
    )


def run_writeback_integration(
    stages: list = None,
    incremental: bool = True,
    batch_size: int = 1000,
    dbt_results_path: str = None,
    force: bool = False,
) -> dict:
    """
    Run the complete write-back integration

    Args:
        stages: List of processing stages to run
        incremental: Whether to use incremental processing
        batch_size: Batch size for processing
        dbt_results_path: Path to dbt results file
        force: Force processing even if no new data

    Returns:
        Dictionary with processing results
    """
    logger = setup_logging()

    start_time = datetime.now(timezone.utc)
    results = {
        "integration_start": start_time,
        "dbt_validation": False,
        "stages_executed": [],
        "total_records_processed": 0,
        "total_errors": 0,
        "overall_status": "running",
    }

    try:
        # 1. Validate dbt run success
        if not force and not validate_dbt_success(dbt_results_path):
            results["overall_status"] = "skipped"
            results["message"] = "dbt run was not successful, skipping write-back"
            logger.warning("Skipping write-back due to failed dbt run")
            return results

        results["dbt_validation"] = True

        # 2. Determine processing stages
        if not stages:
            stages = determine_processing_stages()

        logger.info(f"Starting write-back integration for stages: {stages}")

        # 3. Initialize services
        writeback_service = MemoryWritebackService(batch_size=batch_size)

        if incremental:
            incremental_processor = IncrementalProcessor()

        # 4. Execute write-back for each stage
        for stage in stages:
            stage_start = datetime.now(timezone.utc)

            try:
                if incremental:
                    # Use incremental processing
                    batch = incremental_processor.create_incremental_batch(
                        stage=stage, max_records=batch_size
                    )

                    if not batch and not force:
                        logger.info(f"No new data for stage {stage}, skipping")
                        continue

                    if batch and not incremental_processor.detect_changes(stage, batch):
                        logger.info(f"No changes detected for stage {stage}, skipping")
                        continue

                # Execute write-back for the stage
                if stage == "processed_memories":
                    stage_result = writeback_service.write_processed_memories()
                elif stage == "generated_insights":
                    stage_result = writeback_service.write_generated_insights()
                elif stage == "memory_associations":
                    stage_result = writeback_service.write_memory_associations()
                else:
                    logger.error(f"Unknown stage: {stage}")
                    continue

                # Update results
                results["stages_executed"].append(
                    {
                        "stage": stage,
                        "status": stage_result.get("status", "completed"),
                        "records_processed": stage_result.get("memories_processed", 0)
                        + stage_result.get("insights_generated", 0)
                        + stage_result.get("associations_created", 0),
                        "duration_seconds": stage_result.get("duration_seconds", 0),
                        "batch_id": stage_result.get("batch_id"),
                    }
                )

                results["total_records_processed"] += (
                    stage_result.get("memories_processed", 0)
                    + stage_result.get("insights_generated", 0)
                    + stage_result.get("associations_created", 0)
                )

                # Update incremental processing state
                if incremental and batch:
                    incremental_processor.update_processing_state(
                        stage=stage,
                        batch=batch,
                        success=True,
                        records_processed=stage_result.get(
                            "memories_processed", batch.record_count
                        ),
                    )

                # Write processing metadata
                writeback_service.write_processing_metadata(
                    batch_id=stage_result.get("batch_id"),
                    additional_metadata={
                        "integration_run": True,
                        "dbt_triggered": True,
                        "stage_duration_seconds": (
                            datetime.now(timezone.utc) - stage_start
                        ).total_seconds(),
                    },
                )

                logger.info(f"Completed write-back for stage {stage}")

            except Exception as e:
                results["total_errors"] += 1
                logger.error(f"Failed to process stage {stage}: {e}")

                # Update processing state for failure if using incremental
                if incremental and "batch" in locals():
                    incremental_processor.update_processing_state(
                        stage=stage, batch=batch, success=False
                    )

        # 5. Calculate final results
        results["integration_end"] = datetime.now(timezone.utc)
        results["total_duration_seconds"] = (
            results["integration_end"] - start_time
        ).total_seconds()
        results["overall_status"] = (
            "completed" if results["total_errors"] == 0 else "completed_with_errors"
        )

        # 6. Cleanup
        writeback_service.cleanup()
        if incremental:
            incremental_processor.close()

        logger.info(
            f"Write-back integration completed: {results['total_records_processed']} records processed in {results['total_duration_seconds']:.2f}s"
        )

        return results

    except Exception as e:
        results["overall_status"] = "failed"
        results["error"] = str(e)
        logger.error(f"Write-back integration failed: {e}")
        raise


def create_dbt_hook_script(output_path: str = None):
    """
    Create a shell script for dbt post-hook integration

    Args:
        output_path: Path where to write the hook script
    """
    if not output_path:
        output_path = "/Users/ladvien/codex-dreams/scripts/dbt_post_hook_writeback.sh"

    hook_script = f"""#!/bin/bash
# DBT Post-Hook Write-back Integration Script
# This script is called by dbt post-hooks to trigger memory write-back

set -e

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" &> /dev/null && pwd )"
WRITEBACK_SCRIPT="{Path(__file__).absolute()}"
DBT_TARGET_DIR="${{DBT_TARGET_DIR:-./target}}"
LOG_FILE="/tmp/dbt_writeback_$(date +%Y%m%d_%H%M%S).log"

echo "$(date): Starting dbt post-hook write-back integration" >> "$LOG_FILE"

# Check if dbt run was successful
if [ -f "$DBT_TARGET_DIR/run_results.json" ]; then
    # Run write-back with dbt results validation
    python3 "$WRITEBACK_SCRIPT" \\
        --dbt-results "$DBT_TARGET_DIR/run_results.json" \\
        --incremental \\
        --batch-size 1000 \\
        --log-level INFO >> "$LOG_FILE" 2>&1
else
    echo "$(date): No dbt results file found, running basic write-back" >> "$LOG_FILE"
    
    # Run write-back without validation
    python3 "$WRITEBACK_SCRIPT" \\
        --incremental \\
        --batch-size 1000 \\
        --log-level INFO >> "$LOG_FILE" 2>&1
fi

echo "$(date): DBT post-hook write-back completed" >> "$LOG_FILE"
"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(hook_script)

    # Make script executable
    os.chmod(output_path, 0o755)

    print(f"Created dbt post-hook script at: {output_path}")

    return output_path


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="DBT Write-back Integration")
    parser.add_argument(
        "--stages",
        nargs="*",
        choices=["processed_memories", "generated_insights", "memory_associations"],
        help="Processing stages to run",
    )
    parser.add_argument(
        "--incremental", action="store_true", default=True, help="Use incremental processing"
    )
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for processing")
    parser.add_argument("--dbt-results", help="Path to dbt run results JSON file")
    parser.add_argument("--force", action="store_true", help="Force processing even if no new data")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--create-hook-script", help="Create dbt post-hook shell script at specified path"
    )

    args = parser.parse_args()

    # Create hook script if requested
    if args.create_hook_script:
        create_dbt_hook_script(args.create_hook_script)
        return

    try:
        # Run write-back integration
        results = run_writeback_integration(
            stages=args.stages,
            incremental=args.incremental,
            batch_size=args.batch_size,
            dbt_results_path=args.dbt_results,
            force=args.force,
        )

        print(json.dumps(results, indent=2, default=str))

        # Exit with error code if processing failed
        if results.get("overall_status") == "failed":
            sys.exit(1)
        elif results.get("total_errors", 0) > 0:
            sys.exit(2)  # Completed with errors
        else:
            sys.exit(0)  # Success

    except Exception as e:
        print(f"Write-back integration failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
