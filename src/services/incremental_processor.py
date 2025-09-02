#!/usr/bin/env python3
"""
Incremental Processing Logic for Memory Write-back
=================================================

This module handles incremental data processing to ensure only new or changed
data is transferred from DuckDB to PostgreSQL, optimizing performance and
reducing redundant processing.

Key Features:
- Timestamp-based incremental processing
- Change detection using checksums/hashes
- State management for processing watermarks
- Configurable processing windows
- Recovery from partial failures
"""

import hashlib
import json
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generator, List, Optional, Set

import duckdb
import pandas as pd
import psycopg2
import psycopg2.extras


@dataclass
class ProcessingState:
    """Tracks the state of incremental processing"""

    stage_name: str
    last_processed_timestamp: datetime
    last_processed_batch_id: str
    watermark_value: str  # Timestamp or hash for tracking progress
    records_processed: int = 0
    processing_errors: List[str] = None

    def __post_init__(self):
        if self.processing_errors is None:
            self.processing_errors = []


@dataclass
class IncrementalBatch:
    """Represents a batch of data for incremental processing"""

    batch_id: str
    stage: str
    data: List[Dict[str, Any]]
    watermark_start: str
    watermark_end: str
    record_count: int
    batch_hash: str
    created_at: datetime


class IncrementalProcessor:
    """
    Manages incremental processing logic for memory write-back operations

    This processor ensures efficient data transfer by only processing new or
    changed data since the last successful run, using various strategies
    including timestamp tracking, content hashing, and state persistence.
    """

    def __init__(
        self, postgres_url: str = None, duckdb_path: str = None, default_lookback_hours: int = 24
    ):
        """
        Initialize the incremental processor

        Args:
            postgres_url: PostgreSQL connection string
            duckdb_path: Path to DuckDB database
            default_lookback_hours: Default lookback window for processing
        """
        self.postgres_url = postgres_url or os.getenv("POSTGRES_DB_URL")
        self.duckdb_path = duckdb_path or os.getenv("DUCKDB_PATH")
        self.default_lookback_hours = default_lookback_hours

        self.logger = logging.getLogger("incremental_processor")

        # Initialize connections
        self.duckdb_conn = duckdb.connect(self.duckdb_path) if self.duckdb_path else None
        self.pg_conn_params = (
            self._parse_postgres_url(self.postgres_url) if self.postgres_url else None
        )

        # Processing state cache
        self.processing_states: Dict[str, ProcessingState] = {}

        self.logger.info("Incremental processor initialized")

    def _parse_postgres_url(self, url: str) -> Dict[str, str]:
        """Parse PostgreSQL connection URL into parameters"""
        try:
            import urllib.parse

            parsed = urllib.parse.urlparse(url)
            return {
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "database": parsed.path.lstrip("/"),
                "user": parsed.username,
                "password": parsed.password,
            }
        except Exception as e:
            self.logger.error(f"Failed to parse PostgreSQL URL: {e}")
            raise

    @contextmanager
    def _get_pg_connection(self) -> Generator[Any, None, None]:
        """Get PostgreSQL connection with automatic cleanup"""
        conn = None
        try:
            conn = psycopg2.connect(
                **self.pg_conn_params, cursor_factory=psycopg2.extras.DictCursor
            )
            yield conn
        finally:
            if conn:
                conn.close()

    def get_processing_state(self, stage_name: str) -> Optional[ProcessingState]:
        """
        Retrieve the current processing state for a stage

        Args:
            stage_name: Name of the processing stage

        Returns:
            ProcessingState object or None if not found
        """
        if stage_name in self.processing_states:
            return self.processing_states[stage_name]

        # Load from PostgreSQL if not in cache
        return self._load_processing_state_from_db(stage_name)

    def _load_processing_state_from_db(self, stage_name: str) -> Optional[ProcessingState]:
        """Load processing state from PostgreSQL metadata table"""
        query = """
        SELECT
            processing_stage,
            processing_end_time,
            batch_id,
            total_memories_processed
        FROM codex_processed.processing_metadata
        WHERE processing_stage = %s
          AND processing_status = 'completed'
        ORDER BY processing_end_time DESC
        LIMIT 1
        """

        try:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (stage_name,))
                    row = cursor.fetchone()

                    if row:
                        state = ProcessingState(
                            stage_name=row["processing_stage"],
                            last_processed_timestamp=row["processing_end_time"],
                            last_processed_batch_id=row["batch_id"],
                            watermark_value=row["processing_end_time"].isoformat(),
                            records_processed=row["total_memories_processed"],
                        )

                        self.processing_states[stage_name] = state
                        self.logger.info(
                            f"Loaded processing state for {stage_name}: last processed {state.last_processed_timestamp}"
                        )
                        return state

                    else:
                        self.logger.info(f"No previous processing state found for {stage_name}")
                        return None

        except Exception as e:
            self.logger.error(f"Failed to load processing state for {stage_name}: {e}")
            return None

    def create_incremental_batch(
        self, stage: str, since_timestamp: datetime = None, max_records: int = 10000
    ) -> Optional[IncrementalBatch]:
        """
        Create an incremental batch of data for processing

        Args:
            stage: Processing stage name
            since_timestamp: Process records since this timestamp
            max_records: Maximum records to include in batch

        Returns:
            IncrementalBatch object or None if no new data
        """
        if not since_timestamp:
            state = self.get_processing_state(stage)
            if state:
                since_timestamp = state.last_processed_timestamp
            else:
                # First run - look back default window
                since_timestamp = datetime.now(timezone.utc) - timedelta(
                    hours=self.default_lookback_hours
                )

        # Get incremental data based on stage
        if stage == "processed_memories":
            data = self._get_incremental_memories(since_timestamp, max_records)
        elif stage == "generated_insights":
            data = self._get_incremental_insights(since_timestamp, max_records)
        elif stage == "memory_associations":
            data = self._get_incremental_associations(since_timestamp, max_records)
        else:
            self.logger.error(f"Unknown processing stage: {stage}")
            return None

        if not data:
            self.logger.info(f"No new data found for stage {stage} since {since_timestamp}")
            return None

        # Create batch metadata
        batch_id = f"{stage}_{int(datetime.now(timezone.utc).timestamp())}_{len(data)}"
        watermark_start = since_timestamp.isoformat()
        watermark_end = max(item.get("timestamp", since_timestamp) for item in data).isoformat()

        # Calculate content hash for change detection
        content_str = json.dumps(data, sort_keys=True, default=str)
        batch_hash = hashlib.sha256(content_str.encode()).hexdigest()

        batch = IncrementalBatch(
            batch_id=batch_id,
            stage=stage,
            data=data,
            watermark_start=watermark_start,
            watermark_end=watermark_end,
            record_count=len(data),
            batch_hash=batch_hash,
            created_at=datetime.now(timezone.utc),
        )

        self.logger.info(
            f"Created incremental batch {batch_id} with {len(data)} records for {stage}"
        )
        return batch

    def _get_incremental_memories(
        self, since_timestamp: datetime, max_records: int
    ) -> List[Dict[str, Any]]:
        """Get incremental processed memories from DuckDB"""
        query = f"""
        WITH recent_consolidations AS (
            SELECT
                id as source_memory_id,
                level_0_goal,
                level_1_tasks,
                atomic_actions as level_2_actions,
                phantom_objects,
                consolidated_strength,
                consolidation_fate,
                hebbian_strength,
                semantic_gist,
                semantic_category,
                cortical_region,
                retrieval_accessibility,
                stm_strength,
                emotional_salience,
                consolidated_at as timestamp
            FROM memory_replay
            WHERE consolidated_at > '{since_timestamp.isoformat()}'
            ORDER BY consolidated_at DESC
            LIMIT {max_records}
        )

        SELECT
            *,
            -- Add content hash for change detection
            md5(CONCAT(
                COALESCE(level_0_goal, ''),
                COALESCE(CAST(consolidated_strength AS STRING), '0'),
                COALESCE(consolidation_fate, ''),
                COALESCE(semantic_gist, '')
            )) as content_hash
        FROM recent_consolidations
        """

        try:
            result = self.duckdb_conn.execute(query).fetchall()
            columns = [desc[0] for desc in self.duckdb_conn.description]

            memories = []
            for row in result:
                memory_dict = dict(zip(columns, row))
                # Convert timestamps to datetime objects
                if memory_dict.get("timestamp"):
                    memory_dict["timestamp"] = pd.to_datetime(memory_dict["timestamp"])
                memories.append(memory_dict)

            return memories

        except Exception as e:
            self.logger.error(f"Failed to get incremental memories: {e}")
            return []

    def _get_incremental_insights(
        self, since_timestamp: datetime, max_records: int
    ) -> List[Dict[str, Any]]:
        """Get incremental insights from DuckDB MVP model"""
        query = f"""
        SELECT
            memory_id,
            content,
            suggested_tags,
            related_memories,
            connection_count,
            created_at as timestamp,
            -- Generate insight content hash
            md5(CONCAT(
                COALESCE(content, ''),
                COALESCE(CAST(connection_count AS STRING), '0'),
                COALESCE(array_to_string(suggested_tags, ','), '')
            )) as content_hash
        FROM mvp_memory_insights
        WHERE created_at > '{since_timestamp.isoformat()}'
        ORDER BY created_at DESC
        LIMIT {max_records}
        """

        try:
            result = self.duckdb_conn.execute(query).fetchall()
            columns = [desc[0] for desc in self.duckdb_conn.description]

            insights = []
            for row in result:
                insight_dict = dict(zip(columns, row))
                if insight_dict.get("timestamp"):
                    insight_dict["timestamp"] = pd.to_datetime(insight_dict["timestamp"])
                insights.append(insight_dict)

            return insights

        except Exception as e:
            self.logger.error(f"Failed to get incremental insights: {e}")
            return []

    def _get_incremental_associations(
        self, since_timestamp: datetime, max_records: int
    ) -> List[Dict[str, Any]]:
        """Get incremental associations from DuckDB semantic model"""
        query = f"""
        SELECT
            source_concept,
            target_concept,
            association_strength,
            co_occurrence_count,
            semantic_similarity,
            association_quality,
            last_updated_at as timestamp,
            -- Content hash for association
            md5(CONCAT(
                source_concept,
                target_concept,
                COALESCE(CAST(association_strength AS STRING), '0'),
                COALESCE(association_quality, '')
            )) as content_hash
        FROM concept_associations
        WHERE last_updated_at > '{since_timestamp.isoformat()}'
        ORDER BY association_strength DESC
        LIMIT {max_records}
        """

        try:
            result = self.duckdb_conn.execute(query).fetchall()
            columns = [desc[0] for desc in self.duckdb_conn.description]

            associations = []
            for row in result:
                assoc_dict = dict(zip(columns, row))
                if assoc_dict.get("timestamp"):
                    assoc_dict["timestamp"] = pd.to_datetime(assoc_dict["timestamp"])
                associations.append(assoc_dict)

            return associations

        except Exception as e:
            self.logger.error(f"Failed to get incremental associations: {e}")
            return []

    def detect_changes(self, stage: str, new_batch: IncrementalBatch) -> bool:
        """
        Detect if there are actual changes in the data

        Args:
            stage: Processing stage name
            new_batch: New batch to compare

        Returns:
            True if changes detected, False otherwise
        """
        # Check if we've processed this exact content before
        previous_hash_query = """
        SELECT batch_id, processing_end_time
        FROM codex_processed.processing_metadata
        WHERE processing_stage = %s
          AND environment_config->>'batch_hash' = %s
        ORDER BY processing_end_time DESC
        LIMIT 1
        """

        try:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(previous_hash_query, (stage, new_batch.batch_hash))
                    result = cursor.fetchone()

                    if result:
                        self.logger.info(
                            f"Content hash {new_batch.batch_hash[:8]} already processed for {stage} at {result['processing_end_time']}"
                        )
                        return False

                    # Check for partial overlap - if we have some records with same timestamp but different content
                    overlap_query = """
                    SELECT COUNT(*)
                    FROM codex_processed.processing_metadata
                    WHERE processing_stage = %s
                      AND processing_end_time >= %s
                      AND processing_end_time <= %s
                    """

                    cursor.execute(
                        overlap_query, (stage, new_batch.watermark_start, new_batch.watermark_end)
                    )
                    overlap_count = cursor.fetchone()[0]

                    if overlap_count > 0:
                        self.logger.warning(
                            f"Found {overlap_count} overlapping processing windows for {stage}"
                        )
                        # Could implement more sophisticated overlap detection here

                    return True

        except Exception as e:
            self.logger.error(f"Failed to detect changes for {stage}: {e}")
            # Assume changes exist if we can't check
            return True

    def update_processing_state(
        self,
        stage: str,
        batch: IncrementalBatch,
        success: bool,
        records_processed: Optional[int] = None,
    ) -> None:
        """
        Update processing state after batch completion

        Args:
            stage: Processing stage name
            batch: Completed batch
            success: Whether processing was successful
            records_processed: Number of records successfully processed
        """
        if success:
            state = ProcessingState(
                stage_name=stage,
                last_processed_timestamp=datetime.fromisoformat(
                    batch.watermark_end.replace("Z", "+00:00")
                ),
                last_processed_batch_id=batch.batch_id,
                watermark_value=batch.watermark_end,
                records_processed=records_processed or batch.record_count,
            )

            self.processing_states[stage] = state
            self.logger.info(
                f"Updated processing state for {stage}: watermark={state.watermark_value}"
            )
        else:
            self.logger.error(f"Processing failed for batch {batch.batch_id} in stage {stage}")

    def get_recovery_batches(
        self, stage: str, failed_timestamp: datetime, max_recovery_hours: int = 72
    ) -> List[IncrementalBatch]:
        """
        Get batches for recovery processing after a failure

        Args:
            stage: Processing stage name
            failed_timestamp: Timestamp when processing failed
            max_recovery_hours: Maximum hours to look back for recovery

        Returns:
            List of recovery batches
        """
        recovery_start = failed_timestamp - timedelta(hours=max_recovery_hours)

        self.logger.info(
            f"Creating recovery batches for {stage} from {recovery_start} to {failed_timestamp}"
        )

        # Create smaller batches for recovery to avoid large failures
        recovery_batches = []
        current_time = recovery_start
        batch_window = timedelta(hours=4)  # 4-hour recovery windows

        while current_time < failed_timestamp:
            next_time = min(current_time + batch_window, failed_timestamp)

            batch = self.create_incremental_batch(
                stage=stage,
                since_timestamp=current_time,
                max_records=1000,  # Smaller batches for recovery
            )

            if batch:
                batch.batch_id = f"recovery_{batch.batch_id}"
                recovery_batches.append(batch)

            current_time = next_time

        self.logger.info(f"Created {len(recovery_batches)} recovery batches for {stage}")
        return recovery_batches

    def optimize_processing_window(self, stage: str) -> Dict[str, Any]:
        """
        Analyze processing patterns to optimize batch windows

        Args:
            stage: Processing stage name

        Returns:
            Dictionary with optimization recommendations
        """
        analysis_query = """
        SELECT
            processing_stage,
            AVG(total_memories_processed) as avg_batch_size,
            AVG(processing_duration_seconds) as avg_duration,
            MAX(processing_duration_seconds) as max_duration,
            MIN(processing_duration_seconds) as min_duration,
            COUNT(*) as batch_count,
            SUM(CASE WHEN processing_status = 'failed' THEN 1 ELSE 0 END) as failure_count
        FROM codex_processed.processing_metadata
        WHERE processing_stage = %s
          AND processing_start_time > CURRENT_TIMESTAMP - INTERVAL '30 days'
        GROUP BY processing_stage
        """

        try:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(analysis_query, (stage,))
                    result = cursor.fetchone()

                    if result:
                        optimization = {
                            "stage": stage,
                            "current_avg_batch_size": (
                                float(result["avg_batch_size"]) if result["avg_batch_size"] else 0
                            ),
                            "current_avg_duration": (
                                float(result["avg_duration"]) if result["avg_duration"] else 0
                            ),
                            "failure_rate": (
                                float(result["failure_count"]) / float(result["batch_count"])
                                if result["batch_count"] > 0
                                else 0
                            ),
                            "total_batches": result["batch_count"],
                            "recommendations": [],
                        }

                        # Generate recommendations
                        if optimization["failure_rate"] > 0.1:  # More than 10% failure rate
                            optimization["recommendations"].append(
                                {
                                    "type": "reduce_batch_size",
                                    "reason": f"High failure rate ({optimization['failure_rate']:.1%})",
                                    "suggested_batch_size": max(
                                        500, int(optimization["current_avg_batch_size"] * 0.7)
                                    ),
                                }
                            )

                        if optimization["current_avg_duration"] > 300:  # More than 5 minutes
                            optimization["recommendations"].append(
                                {
                                    "type": "optimize_performance",
                                    "reason": f"Long processing time ({optimization['current_avg_duration']:.1f}s)",
                                    "suggested_actions": [
                                        "increase_parallelism",
                                        "optimize_queries",
                                        "add_indexes",
                                    ],
                                }
                            )

                        if optimization["current_avg_batch_size"] < 100:
                            optimization["recommendations"].append(
                                {
                                    "type": "increase_batch_size",
                                    "reason": "Small batch sizes may be inefficient",
                                    "suggested_batch_size": min(
                                        2000, int(optimization["current_avg_batch_size"] * 2)
                                    ),
                                }
                            )

                        return optimization
                    else:
                        return {
                            "stage": stage,
                            "message": "No historical data available for optimization",
                            "recommendations": [{"type": "baseline", "suggested_batch_size": 1000}],
                        }

        except Exception as e:
            self.logger.error(f"Failed to optimize processing window for {stage}: {e}")
            return {"stage": stage, "error": str(e)}

    def cleanup_old_metadata(self, retention_days: int = 90) -> None:
        """
        Clean up old processing metadata to prevent table bloat

        Args:
            retention_days: Days of metadata to retain
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        cleanup_query = """
        DELETE FROM codex_processed.processing_metadata
        WHERE processing_start_time < %s
          AND processing_status IN ('completed', 'failed')
        """

        try:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(cleanup_query, (cutoff_date,))
                    deleted_count = cursor.rowcount
                    conn.commit()

                    self.logger.info(f"Cleaned up {deleted_count} old processing metadata records")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old metadata: {e}")

    def close(self) -> None:
        """Close database connections"""
        if self.duckdb_conn:
            self.duckdb_conn.close()
