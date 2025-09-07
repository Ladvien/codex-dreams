#!/usr/bin/env python3
"""
Populate Dreams Schema with Historical Data
===========================================

This script processes ALL historical memories and populates the dreams schema
with the complete biological memory pipeline stages.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2
import psycopg2.extras

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class HistoricalDreamsPopulator:
    """Populate dreams schema with all historical memory data."""

    def __init__(self) -> None:
        self.postgres_url = os.getenv(
            "POSTGRES_DB_URL",
            os.getenv("POSTGRES_DB_URL"),
        )
        self.session_id = str(uuid.uuid4())
        self.batch_size = 500

    def connect_postgres(self) -> Any:
        """Connect to PostgreSQL."""
        return psycopg2.connect(self.postgres_url)

    def populate_working_memory_historical(self) -> None:
        """Populate working memory with historical snapshots."""
        logger.info("Populating working memory with historical data...")

        pg_conn = self.connect_postgres()
        pg_cursor = pg_conn.cursor()

        try:
            # Get all unique days with memories
            pg_cursor.execute(
                """
                SELECT DISTINCT DATE(created_at) as day
                FROM public.memories
                ORDER BY day
            """
            )
            days = [row[0] for row in pg_cursor.fetchall()]

            total_processed = 0

            for day in days:
                # Create snapshots for each hour of the day
                for hour in range(24):
                    snapshot_id = str(uuid.uuid4())
                    snapshot_time = datetime.combine(day, datetime.min.time().replace(hour=hour))

                    # Get top 7 memories for this hour window
                    pg_cursor.execute(
                        """
                        SELECT
                            id,
                            content,
                            created_at as timestamp,
                            context,
                            summary,
                            tags,
                            LENGTH(content) as content_length
                        FROM public.memories
                        WHERE created_at >= %s AND created_at < %s
                        AND content IS NOT NULL
                        ORDER BY created_at DESC
                        LIMIT 7
                    """,
                        (snapshot_time, snapshot_time + timedelta(hours=1)),
                    )

                    memories = pg_cursor.fetchall()

                    if not memories:
                        continue

                    # Insert each memory into working memory
                    for idx, memory in enumerate(memories):
                        (
                            memory_id,
                            content,
                            timestamp,
                            context,
                            summary,
                            tags,
                            content_length,
                        ) = memory

                        # Calculate importance based on content length and position
                        importance = min(1.0, 0.3 + (content_length / 10000) + (7 - idx) * 0.1)

                        # Determine task type
                        task_type = "observation"
                        content_lower = (content or "").lower()
                        if any(word in content_lower for word in ["goal", "objective", "plan"]):
                            task_type = "goal"
                        elif any(word in content_lower for word in ["task", "need", "should"]):
                            task_type = "task"
                        elif any(word in content_lower for word in ["fix", "update", "change"]):
                            task_type = "action"

                        # Insert into working memory
                        pg_cursor.execute(
                            """
                            INSERT INTO dreams.working_memory (
                                memory_id, content, timestamp, metadata,
                                entities, topics, sentiment, importance_score,
                                task_type, working_memory_strength, final_priority,
                                wm_slot, activation_strength, snapshot_id, processed_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            ) ON CONFLICT (memory_id, snapshot_id) DO NOTHING
                        """,
                            (
                                memory_id,
                                content[:5000] if content else "",
                                timestamp,
                                json.dumps({"context": context}) if context else "{}",
                                tags[:10] if tags else [],  # Entities from tags
                                ["memory", "processing"],  # Default topics
                                "neutral",
                                importance,
                                task_type,
                                importance * 0.8,  # Working memory strength
                                importance * (7 - idx) / 7,  # Priority by position
                                idx + 1,  # Miller's slot
                                0.5 + (content_length / 20000),  # Activation strength
                                snapshot_id,
                                snapshot_time,  # Use historical time
                            ),
                        )

                        total_processed += 1

                    if total_processed % 100 == 0:
                        pg_conn.commit()
                        logger.info(f"Processed {total_processed} working memory records...")

            pg_conn.commit()
            logger.info(f"Successfully populated {total_processed} working memory records")

        except Exception as e:
            logger.error(f"Error populating working memory: {e}")
            pg_conn.rollback()
        finally:
            pg_cursor.close()
            pg_conn.close()

    def populate_short_term_episodes(self) -> None:
        """Populate short-term episodes from all memories."""
        logger.info("Populating short-term episodes...")

        pg_conn = self.connect_postgres()
        pg_cursor = pg_conn.cursor()

        try:
            # Get all memories older than 5 minutes
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
                WHERE created_at < NOW() - INTERVAL '5 minutes'
                AND content IS NOT NULL
                ORDER BY created_at DESC
            """
            )

            memories = pg_cursor.fetchall()
            logger.info(f"Processing {len(memories)} memories for short-term episodes...")

            for idx, memory in enumerate(memories):
                memory_id, content, timestamp, summary, context, tags = memory

                # Extract hierarchical structure
                level_0_goal = summary[:200] if summary else "Process information"
                level_1_tasks = tags[:5] if tags else ["analyze", "understand", "store"]
                level_2_subtasks = [f"sub_{task}" for task in level_1_tasks[:3]]

                # Calculate STM strength based on age
                age_days = (datetime.now(timezone.utc) - timestamp).days
                recency_factor = max(0.1, 1.0 - (age_days / 30))  # Decay over 30 days
                stm_strength = recency_factor * 0.7

                # Emotional salience (random for historical data)
                emotional_salience = 0.5 + (hash(str(memory_id)) % 50) / 100

                # Insert into short-term episodes
                pg_cursor.execute(
                    """
                    INSERT INTO dreams.short_term_episodes (
                        memory_id, content, timestamp,
                        level_0_goal, level_1_tasks, level_2_subtasks,
                        stm_strength, recency_factor, emotional_salience,
                        ready_for_consolidation, processed_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (memory_id) DO UPDATE SET
                        stm_strength = EXCLUDED.stm_strength,
                        recency_factor = EXCLUDED.recency_factor,
                        co_activation_count = dreams.short_term_episodes.co_activation_count + 1
                """,
                    (
                        memory_id,
                        content[:5000] if content else "",
                        timestamp,
                        level_0_goal,
                        level_1_tasks,
                        level_2_subtasks,
                        stm_strength,
                        recency_factor,
                        emotional_salience,
                        recency_factor < 0.5,  # Ready for consolidation if older
                        timestamp + timedelta(minutes=30),  # Processed 30 min after creation
                    ),
                )

                if (idx + 1) % 100 == 0:
                    pg_conn.commit()
                    logger.info(f"Processed {idx + 1} short-term episodes...")

            pg_conn.commit()
            logger.info(f"Successfully populated {len(memories)} short-term episodes")

        except Exception as e:
            logger.error(f"Error populating short-term episodes: {e}")
            pg_conn.rollback()
        finally:
            pg_cursor.close()
            pg_conn.close()

    def populate_long_term_memories(self) -> None:
        """Consolidate older memories into long-term storage."""
        logger.info("Populating long-term memories...")

        pg_conn = self.connect_postgres()
        pg_cursor = pg_conn.cursor()

        try:
            # Get episodes ready for consolidation
            pg_cursor.execute(
                """
                SELECT
                    ste.memory_id,
                    m.content,
                    m.summary,
                    ste.level_0_goal,
                    ste.stm_strength,
                    m.tags,
                    ste.timestamp
                FROM dreams.short_term_episodes ste
                JOIN public.memories m ON m.id = ste.memory_id
                WHERE ste.ready_for_consolidation = true
                AND ste.stm_strength > 0.3
            """
            )

            consolidatable = pg_cursor.fetchall()
            logger.info(f"Consolidating {len(consolidatable)} memories to long-term storage...")

            for idx, memory in enumerate(consolidatable):
                memory_id, content, summary, goal, stm_strength, tags, timestamp = memory

                # Determine knowledge type based on content
                knowledge_type = "declarative"
                content_lower = (content or "").lower()
                if "how to" in content_lower or "steps" in content_lower:
                    knowledge_type = "procedural"
                elif "if" in content_lower or "when" in content_lower:
                    knowledge_type = "conditional"

                # Calculate scores
                stability_score = stm_strength * 0.8
                importance_score = stm_strength * 0.7
                retrieval_strength = stm_strength * 0.6

                # Insert into long-term memories
                pg_cursor.execute(
                    """
                    INSERT INTO dreams.long_term_memories (
                        memory_id, content, semantic_gist,
                        concepts, knowledge_type, abstraction_level,
                        confidence_score, stability_score, importance_score,
                        retrieval_strength, consolidation_source,
                        consolidated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (memory_id) DO UPDATE SET
                        stability_score = GREATEST(
                            dreams.long_term_memories.stability_score,
                            EXCLUDED.stability_score
                        ),
                        access_count = dreams.long_term_memories.access_count + 1
                """,
                    (
                        memory_id,
                        content[:5000] if content else "",
                        summary or goal,
                        tags[:10] if tags else [],
                        knowledge_type,
                        3,  # Default abstraction level
                        stm_strength,
                        stability_score,
                        importance_score,
                        retrieval_strength,
                        "historical",  # Consolidation source
                        timestamp + timedelta(hours=6),  # Consolidated 6 hours after creation
                    ),
                )

                if (idx + 1) % 100 == 0:
                    pg_conn.commit()
                    logger.info(f"Consolidated {idx + 1} long-term memories...")

            pg_conn.commit()
            logger.info(f"Successfully populated {len(consolidatable)} long-term memories")

        except Exception as e:
            logger.error(f"Error populating long-term memories: {e}")
            pg_conn.rollback()
        finally:
            pg_cursor.close()
            pg_conn.close()

    def build_semantic_network(self) -> None:
        """Build semantic network from consolidated memories."""
        logger.info("Building semantic network...")

        pg_conn = self.connect_postgres()
        pg_cursor = pg_conn.cursor()

        try:
            # Find concept pairs from memories with shared tags
            pg_cursor.execute(
                """
                WITH concept_pairs AS (
                    SELECT DISTINCT
                        t1.tag as concept_a,
                        t2.tag as concept_b,
                        COUNT(*) OVER (PARTITION BY t1.tag, t2.tag) as co_occurrence
                    FROM public.memories m1,
                        unnest(m1.tags) as t1(tag),
                        public.memories m2,
                        unnest(m2.tags) as t2(tag)
                    WHERE m1.id != m2.id
                    AND t1.tag != t2.tag
                    AND t1.tag < t2.tag  -- Avoid duplicates
                    LIMIT 5000
                )
                SELECT concept_a, concept_b, co_occurrence
                FROM concept_pairs
                WHERE co_occurrence > 2
                ORDER BY co_occurrence DESC
                LIMIT 1000
            """
            )

            associations = pg_cursor.fetchall()
            logger.info(f"Creating {len(associations)} semantic associations...")

            for concept_a, concept_b, co_occurrence in associations:
                if concept_a and concept_b:
                    # Calculate association strength based on co-occurrence
                    strength = min(1.0, co_occurrence / 100)

                    pg_cursor.execute(
                        """
                        INSERT INTO dreams.semantic_network (
                            concept_a, concept_b, association_type,
                            association_strength, co_activation_count,
                            edge_weight
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (concept_a, concept_b, association_type) DO UPDATE SET
                            association_strength = (
                                dreams.semantic_network.association_strength + EXCLUDED.association_strength
                            ) / 2,
                            co_activation_count = dreams.semantic_network.co_activation_count + EXCLUDED.co_activation_count
                    """,
                        (
                            concept_a,
                            concept_b,
                            "co-occurrence",  # Association type
                            strength,
                            co_occurrence,
                            strength,  # Edge weight same as strength
                        ),
                    )

            pg_conn.commit()
            logger.info(f"Successfully created {len(associations)} semantic associations")

            # Also build associations from long-term memory concepts
            pg_cursor.execute(
                """
                SELECT memory_id, concepts, importance_score
                FROM dreams.long_term_memories
                WHERE concepts IS NOT NULL AND array_length(concepts, 1) > 1
                LIMIT 1000
            """
            )

            ltm_memories = pg_cursor.fetchall()
            association_count = 0

            for memory_id, concepts, importance in ltm_memories:
                # Create associations between concepts in same memory
                for i in range(len(concepts)):
                    for j in range(i + 1, min(i + 3, len(concepts))):  # Limit associations
                        if concepts[i] and concepts[j]:
                            pg_cursor.execute(
                                """
                                INSERT INTO dreams.semantic_network (
                                    concept_a, concept_b, association_type,
                                    association_strength
                                ) VALUES (
                                    %s, %s, %s, %s
                                ) ON CONFLICT (concept_a, concept_b, association_type) DO UPDATE SET
                                    association_strength = GREATEST(
                                        dreams.semantic_network.association_strength,
                                        EXCLUDED.association_strength
                                    ),
                                    co_activation_count = dreams.semantic_network.co_activation_count + 1
                            """,
                                (
                                    (concepts[i] if concepts[i] < concepts[j] else concepts[j]),
                                    (concepts[j] if concepts[i] < concepts[j] else concepts[i]),
                                    "semantic",
                                    importance,
                                ),
                            )
                            association_count += 1

            pg_conn.commit()
            logger.info(f"Created {association_count} additional semantic associations from LTM")

        except Exception as e:
            logger.error(f"Error building semantic network: {e}")
            pg_conn.rollback()
        finally:
            pg_cursor.close()
            pg_conn.close()

    def run_full_population(self) -> None:
        """Run complete historical data population."""
        logger.info("=" * 60)
        logger.info("Starting full historical data population...")
        logger.info(f"Session ID: {self.session_id}")
        logger.info("=" * 60)

        # Run each stage
        self.populate_working_memory_historical()
        self.populate_short_term_episodes()
        self.populate_long_term_memories()
        self.build_semantic_network()

        # Show final statistics
        self.show_statistics()

        logger.info("=" * 60)
        logger.info("Historical data population complete!")
        logger.info("=" * 60)

    def show_statistics(self) -> None:
        """Display final statistics."""
        pg_conn = self.connect_postgres()
        pg_cursor = pg_conn.cursor()

        try:
            pg_cursor.execute("SELECT * FROM dreams.get_memory_stats()")
            stats = pg_cursor.fetchall()

            logger.info("\nFinal Dreams Schema Statistics:")
            logger.info("-" * 40)
            for stage, count, oldest, newest, avg_imp in stats:
                logger.info(f"{stage:20s}: {count:6d} records")
                if oldest:
                    logger.info(f"  Date range: {oldest.date()} to {newest.date()}")
                    if avg_imp:
                        logger.info(f"  Avg importance: {avg_imp:.3f}")

            # Semantic network stats
            pg_cursor.execute("SELECT COUNT(*) FROM dreams.semantic_network")
            network_count = pg_cursor.fetchone()[0]
            logger.info(f"semantic_network     : {network_count:6d} associations")

            # Insights stats
            pg_cursor.execute("SELECT COUNT(*) FROM dreams.memory_insights")
            insights_count = pg_cursor.fetchone()[0]
            logger.info(f"memory_insights      : {insights_count:6d} patterns")

        finally:
            pg_cursor.close()
            pg_conn.close()


def main() -> None:
    """Main entry point."""
    populator = HistoricalDreamsPopulator()
    populator.run_full_population()


if __name__ == "__main__":
    main()
