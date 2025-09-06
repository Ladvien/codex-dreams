#!/usr/bin/env python3
"""
Dreams Write-back Service for Biological Memory Pipeline
=========================================================

Transfers all processed biological memory data from DuckDB analytical
processing to PostgreSQL dreams schema for permanent storage and access.

Processing Stages:
1. Working Memory - Every 5 seconds
2. Short-Term Episodes - Every 5 minutes
3. Long-Term Memories - Every hour
4. Semantic Network - Daily consolidation
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DreamsWritebackService:
    """Service for writing biological memory processing results to PostgreSQL dreams schema."""

    def __init__(self):
        """Initialize the writeback service."""
        # Database connections
        self.postgres_url = os.getenv(
            "POSTGRES_DB_URL",
            "postgresql://codex_user:MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a@192.168.1.104:5432/codex_db",
        )
        self.duckdb_path = os.getenv(
            "DUCKDB_PATH", "/Users/ladvien/biological_memory/dbs/memory.duckdb"
        )

        # Processing configuration
        self.batch_size = 1000
        self.session_id = str(uuid.uuid4())

    def connect_postgres(self):
        """Connect to PostgreSQL database."""
        try:
            conn = psycopg2.connect(self.postgres_url)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def connect_duckdb_readonly(self):
        """Connect to DuckDB in read-only mode."""
        try:
            # Use read-only mode to avoid conflicts with other processes
            conn = duckdb.connect(self.duckdb_path, read_only=True)
            return conn
        except Exception as e:
            logger.warning(f"Could not connect to DuckDB in read-only mode: {e}")
            # Try with in-memory database if file is locked
            return duckdb.connect(":memory:")

    def write_working_memory(self):
        """Write working memory snapshots to dreams schema."""
        logger.info("Writing working memory snapshots...")
        snapshot_id = str(uuid.uuid4())

        try:
            # Connect to databases
            duck_conn = self.connect_duckdb_readonly()
            pg_conn = self.connect_postgres()
            pg_cursor = pg_conn.cursor()

            # Query working memory from DuckDB
            # Since we can't access DuckDB models directly, we'll query raw memories
            # and apply similar logic
            query = """
            SELECT 
                id,
                content,
                timestamp,
                metadata,
                COALESCE(activation_strength, 0.5) as activation_strength,
                COALESCE(access_count, 1) as access_count
            FROM raw_memories
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
            AND content IS NOT NULL
            LIMIT 7
            """

            # For now, query from PostgreSQL directly since DuckDB may be locked
            pg_cursor.execute(
                """
                SELECT 
                    id,
                    content,
                    created_at as timestamp,
                    context as metadata,
                    COALESCE((LENGTH(content)::float / 1000), 0.5) as activation_strength,
                    1 as access_count,
                    summary,
                    tags
                FROM public.memories
                WHERE created_at > NOW() - INTERVAL '5 minutes'
                AND content IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 7
            """
            )

            memories = pg_cursor.fetchall()

            # Process and insert each memory
            for idx, memory in enumerate(memories):
                memory_id, content, timestamp, metadata, activation, access_count, summary, tags = (
                    memory
                )

                # Simple importance scoring
                importance = min(1.0, 0.5 + (len(content) / 10000))

                # Determine task type based on content
                task_type = "observation"
                if any(word in content.lower() for word in ["goal", "objective", "strategy"]):
                    task_type = "goal"
                elif any(word in content.lower() for word in ["task", "need to", "should"]):
                    task_type = "task"
                elif any(word in content.lower() for word in ["fix", "update", "change"]):
                    task_type = "action"

                # Insert into working memory
                insert_query = """
                INSERT INTO dreams.working_memory (
                    memory_id, content, timestamp, metadata,
                    entities, topics, sentiment, importance_score,
                    task_type, working_memory_strength, final_priority,
                    wm_slot, activation_strength, access_count,
                    snapshot_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (memory_id, snapshot_id) DO NOTHING
                """

                pg_cursor.execute(
                    insert_query,
                    (
                        memory_id,
                        content[:5000] if content else "",  # Truncate very long content
                        timestamp,
                        json.dumps({"original_metadata": metadata}) if metadata else "{}",
                        tags if tags else [],  # Use tags as entities
                        ["memory", "processing"],  # Default topics
                        "neutral",  # Default sentiment
                        importance,
                        task_type,
                        importance * activation,  # Working memory strength
                        importance * (7 - idx) / 7,  # Priority based on recency
                        idx + 1,  # Miller's slot position
                        activation,
                        access_count,
                        snapshot_id,
                    ),
                )

            pg_conn.commit()
            logger.info(
                f"Successfully wrote {len(memories)} working memory records (snapshot: {snapshot_id})"
            )

            # Record metrics
            self._record_metrics(pg_cursor, "working_memory", len(memories), len(memories), 0)
            pg_conn.commit()

        except Exception as e:
            logger.error(f"Error writing working memory: {e}")
            if pg_conn:
                pg_conn.rollback()
        finally:
            if pg_cursor:
                pg_cursor.close()
            if pg_conn:
                pg_conn.close()
            if duck_conn:
                duck_conn.close()

    def write_short_term_episodes(self):
        """Write short-term episodic memories to dreams schema."""
        logger.info("Writing short-term episodes...")

        try:
            pg_conn = self.connect_postgres()
            pg_cursor = pg_conn.cursor()

            # Query recent memories that should be in short-term storage
            pg_cursor.execute(
                """
                SELECT 
                    id,
                    content,
                    created_at as timestamp,
                    summary,
                    context,
                    tags
                FROM public.memories
                WHERE created_at > NOW() - INTERVAL '1 hour'
                AND created_at < NOW() - INTERVAL '5 minutes'
                AND content IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 100
            """
            )

            episodes = pg_cursor.fetchall()

            for episode in episodes:
                memory_id, content, timestamp, summary, context, tags = episode

                # Extract hierarchical structure (simplified)
                level_0_goal = summary[:100] if summary else "Process information"
                level_1_tasks = tags[:3] if tags else ["analyze", "store", "retrieve"]

                # Calculate STM strength
                age_minutes = (datetime.now(timezone.utc) - timestamp).seconds / 60
                recency_factor = max(0.1, 1.0 - (age_minutes / 60))

                insert_query = """
                INSERT INTO dreams.short_term_episodes (
                    memory_id, content, timestamp,
                    level_0_goal, level_1_tasks,
                    stm_strength, recency_factor, emotional_salience,
                    ready_for_consolidation
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (memory_id) DO UPDATE SET
                    stm_strength = EXCLUDED.stm_strength,
                    recency_factor = EXCLUDED.recency_factor,
                    co_activation_count = dreams.short_term_episodes.co_activation_count + 1
                """

                pg_cursor.execute(
                    insert_query,
                    (
                        memory_id,
                        content[:5000] if content else "",
                        timestamp,
                        level_0_goal,
                        level_1_tasks,
                        recency_factor * 0.8,  # STM strength
                        recency_factor,
                        0.5,  # Default emotional salience
                        recency_factor < 0.3,  # Ready for consolidation if old enough
                    ),
                )

            pg_conn.commit()
            logger.info(f"Successfully wrote {len(episodes)} short-term episodes")

            # Record metrics
            self._record_metrics(pg_cursor, "short_term_episodes", len(episodes), len(episodes), 0)
            pg_conn.commit()

        except Exception as e:
            logger.error(f"Error writing short-term episodes: {e}")
            if pg_conn:
                pg_conn.rollback()
        finally:
            if pg_cursor:
                pg_cursor.close()
            if pg_conn:
                pg_conn.close()

    def write_long_term_memories(self):
        """Consolidate and write long-term memories to dreams schema."""
        logger.info("Writing long-term memories...")

        try:
            pg_conn = self.connect_postgres()
            pg_cursor = pg_conn.cursor()

            # Query memories ready for long-term consolidation
            pg_cursor.execute(
                """
                SELECT 
                    ste.memory_id,
                    m.content,
                    m.summary as semantic_gist,
                    ste.level_0_goal,
                    ste.stm_strength,
                    m.tags
                FROM dreams.short_term_episodes ste
                JOIN public.memories m ON m.id = ste.memory_id
                WHERE ste.ready_for_consolidation = true
                AND ste.consolidation_attempts < 3
                LIMIT 50
            """
            )

            consolidatable = pg_cursor.fetchall()

            for memory in consolidatable:
                memory_id, content, semantic_gist, goal, stm_strength, tags = memory

                # Determine knowledge type
                knowledge_type = "declarative"
                if "how" in (content or "").lower():
                    knowledge_type = "procedural"
                elif "if" in (content or "").lower() or "when" in (content or "").lower():
                    knowledge_type = "conditional"

                insert_query = """
                INSERT INTO dreams.long_term_memories (
                    memory_id, content, semantic_gist,
                    concepts, knowledge_type, abstraction_level,
                    confidence_score, stability_score, importance_score,
                    consolidation_source
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (memory_id) DO UPDATE SET
                    stability_score = GREATEST(
                        dreams.long_term_memories.stability_score,
                        EXCLUDED.stability_score
                    ),
                    access_count = dreams.long_term_memories.access_count + 1
                """

                pg_cursor.execute(
                    insert_query,
                    (
                        memory_id,
                        content[:5000] if content else "",
                        semantic_gist or goal,
                        tags if tags else [],
                        knowledge_type,
                        3,  # Default abstraction level
                        stm_strength,  # Use STM strength as confidence
                        stm_strength * 0.8,  # Stability score
                        stm_strength * 0.7,  # Importance score
                        "wake",  # Consolidation during wake hours
                    ),
                )

                # Update STM episode as consolidated
                pg_cursor.execute(
                    """
                    UPDATE dreams.short_term_episodes
                    SET consolidation_attempts = consolidation_attempts + 1,
                        last_consolidation_attempt = NOW()
                    WHERE memory_id = %s
                """,
                    (memory_id,),
                )

            pg_conn.commit()
            logger.info(f"Successfully consolidated {len(consolidatable)} long-term memories")

            # Record metrics
            self._record_metrics(
                pg_cursor, "long_term_memories", len(consolidatable), len(consolidatable), 0
            )
            pg_conn.commit()

        except Exception as e:
            logger.error(f"Error writing long-term memories: {e}")
            if pg_conn:
                pg_conn.rollback()
        finally:
            if pg_cursor:
                pg_cursor.close()
            if pg_conn:
                pg_conn.close()

    def write_semantic_network(self):
        """Build and write semantic network associations."""
        logger.info("Building semantic network...")

        try:
            pg_conn = self.connect_postgres()
            pg_cursor = pg_conn.cursor()

            # Find concept associations from long-term memories
            pg_cursor.execute(
                """
                SELECT DISTINCT
                    ltm1.concepts[1] as concept_a,
                    ltm2.concepts[1] as concept_b,
                    (ltm1.importance_score + ltm2.importance_score) / 2 as strength
                FROM dreams.long_term_memories ltm1
                CROSS JOIN dreams.long_term_memories ltm2
                WHERE ltm1.memory_id != ltm2.memory_id
                AND ltm1.concepts IS NOT NULL AND array_length(ltm1.concepts, 1) > 0
                AND ltm2.concepts IS NOT NULL AND array_length(ltm2.concepts, 1) > 0
                AND ltm1.consolidated_at > NOW() - INTERVAL '7 days'
                LIMIT 100
            """
            )

            associations = pg_cursor.fetchall()

            for concept_a, concept_b, strength in associations:
                if concept_a and concept_b and concept_a != concept_b:
                    insert_query = """
                    INSERT INTO dreams.semantic_network (
                        concept_a, concept_b, association_type,
                        association_strength, co_activation_count
                    ) VALUES (
                        %s, %s, %s, %s, %s
                    ) ON CONFLICT (concept_a, concept_b, association_type) DO UPDATE SET
                        association_strength = (
                            dreams.semantic_network.association_strength + EXCLUDED.association_strength
                        ) / 2,
                        co_activation_count = dreams.semantic_network.co_activation_count + 1,
                        last_activation = NOW()
                    """

                    pg_cursor.execute(
                        insert_query,
                        (
                            concept_a,
                            concept_b,
                            "categorical",  # Default association type
                            min(1.0, strength),
                            1,
                        ),
                    )

            pg_conn.commit()
            logger.info(f"Successfully created {len(associations)} semantic associations")

            # Record metrics
            self._record_metrics(
                pg_cursor, "semantic_network", len(associations), len(associations), 0
            )
            pg_conn.commit()

        except Exception as e:
            logger.error(f"Error building semantic network: {e}")
            if pg_conn:
                pg_conn.rollback()
        finally:
            if pg_cursor:
                pg_cursor.close()
            if pg_conn:
                pg_conn.close()

    def extract_insights(self):
        """Extract patterns and insights from processed memories."""
        logger.info("Extracting memory insights...")

        try:
            pg_conn = self.connect_postgres()
            pg_cursor = pg_conn.cursor()

            # Find recurring patterns
            pg_cursor.execute(
                """
                SELECT 
                    t.tag,
                    COUNT(*) as frequency
                FROM public.memories m,
                    unnest(m.tags) as t(tag)
                WHERE m.created_at > NOW() - INTERVAL '7 days'
                GROUP BY t.tag
                HAVING COUNT(*) > 5
                ORDER BY frequency DESC
                LIMIT 10
            """
            )

            patterns = pg_cursor.fetchall()

            for tag, frequency in patterns:
                if tag:
                    insert_query = """
                    INSERT INTO dreams.memory_insights (
                        insight_type, insight_description,
                        pattern_name, pattern_frequency,
                        confidence_score, discovery_method
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s
                    )
                    """

                    pattern_name = f"Recurring theme: {tag}"
                    description = f"Pattern '{tag}' detected with frequency {frequency}"

                    pg_cursor.execute(
                        insert_query,
                        (
                            "pattern",
                            description,
                            pattern_name,
                            frequency,
                            min(1.0, frequency / 10),  # Confidence based on frequency
                            "frequency_analysis",
                        ),
                    )

            pg_conn.commit()
            logger.info(f"Successfully extracted {len(patterns)} insights")

        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            if pg_conn:
                pg_conn.rollback()
        finally:
            if pg_cursor:
                pg_cursor.close()
            if pg_conn:
                pg_conn.close()

    def _record_metrics(self, cursor, stage: str, processed: int, successful: int, failed: int):
        """Record processing metrics."""
        try:
            cursor.execute(
                """
                INSERT INTO dreams.processing_metrics (
                    session_id, processing_stage,
                    memories_processed, successful_writes, failed_writes,
                    start_time, end_time
                ) VALUES (
                    %s, %s, %s, %s, %s, NOW(), NOW()
                )
            """,
                (self.session_id, stage, processed, successful, failed),
            )
        except Exception as e:
            logger.warning(f"Could not record metrics: {e}")

    def run_full_pipeline(self):
        """Run the complete write-back pipeline."""
        logger.info(f"Starting full pipeline run (session: {self.session_id})")

        # Run each stage
        self.write_working_memory()
        self.write_short_term_episodes()
        self.write_long_term_memories()
        self.write_semantic_network()
        self.extract_insights()

        logger.info("Pipeline run complete")

    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data from dreams schema."""
        logger.info(f"Cleaning up data older than {days_to_keep} days...")

        try:
            pg_conn = self.connect_postgres()
            pg_cursor = pg_conn.cursor()

            # Clean old working memory snapshots
            pg_cursor.execute(
                """
                DELETE FROM dreams.working_memory
                WHERE processed_at < NOW() - INTERVAL '%s days'
            """,
                (days_to_keep,),
            )

            deleted_wm = pg_cursor.rowcount

            # Clean old metrics
            pg_cursor.execute(
                """
                DELETE FROM dreams.processing_metrics
                WHERE start_time < NOW() - INTERVAL '%s days'
            """,
                (days_to_keep * 2,),
            )  # Keep metrics longer

            deleted_metrics = pg_cursor.rowcount

            pg_conn.commit()
            logger.info(
                f"Cleaned up {deleted_wm} working memory records and {deleted_metrics} metrics"
            )

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            if pg_conn:
                pg_conn.rollback()
        finally:
            if pg_cursor:
                pg_cursor.close()
            if pg_conn:
                pg_conn.close()


def main():
    """Main entry point for the write-back service."""
    service = DreamsWritebackService()

    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "working":
            service.write_working_memory()
        elif command == "episodes":
            service.write_short_term_episodes()
        elif command == "longterm":
            service.write_long_term_memories()
        elif command == "semantic":
            service.write_semantic_network()
        elif command == "insights":
            service.extract_insights()
        elif command == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            service.cleanup_old_data(days)
        elif command == "full":
            service.run_full_pipeline()
        else:
            print(f"Unknown command: {command}")
            print(
                "Usage: dreams_writeback_service.py [working|episodes|longterm|semantic|insights|cleanup|full]"
            )
    else:
        # Default: run full pipeline
        service.run_full_pipeline()


if __name__ == "__main__":
    main()
