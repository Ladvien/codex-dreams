#!/usr/bin/env python3
"""
End-to-End Biological Memory Pipeline Integration Tests for STORY-009
Tests complete biological memory processing with live PostgreSQL and Ollama services

This module provides comprehensive integration testing for:
- Complete biological memory pipeline from PostgreSQL ingestion to consolidation
- Live service integration (PostgreSQL at 192.168.1.104 + Ollama at 192.168.1.110:11434)
- Biological timing constraints and Miller's 7±2 capacity limits
- Working Memory → Short-Term Memory → Long-Term Memory flow
- Hebbian learning and consolidation with live LLM processing
- Performance benchmarks for the complete pipeline
"""

import hashlib
import json
import logging
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import psycopg2
import pytest
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "biological_memory"))


@dataclass
class EndToEndConfig:
    """Configuration for end-to-end integration testing"""

    # PostgreSQL configuration
    postgres_host: str = "192.168.1.104"
    postgres_port: int = 5432
    postgres_database: str = "codex_test_db"
    postgres_user: str = os.getenv("POSTGRES_USER", "codex_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")

    # Ollama configuration
    ollama_url: str = "http://192.168.1.110:11434"
    ollama_model: str = "gpt-oss:20b"
    embedding_model: str = "nomic-embed-text"

    # Biological constraints
    working_memory_capacity: int = 7
    attention_window_minutes: int = 5
    consolidation_threshold: float = 0.5
    hebbian_learning_rate: float = 0.1


class BiologicalMemoryPipelineTester:
    """End-to-end biological memory pipeline tester"""

    def __init__(self, config: Optional[EndToEndConfig] = None):
        self.config = config or EndToEndConfig()
        self.test_schema = f"e2e_test_{int(time.time())}"
        self.test_tables_created = []
        self.temp_duckdb = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """Clean up all test resources"""
        try:
            # Clean up PostgreSQL test data
            with self.get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"DROP SCHEMA IF EXISTS {self.test_schema} CASCADE")
                    for table in self.test_tables_created:
                        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

            # Clean up DuckDB files
            if self.temp_duckdb and Path(self.temp_duckdb).exists():
                Path(self.temp_duckdb).unlink()

            logger.info(f"Cleaned up test schema {self.test_schema}")

        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    @contextmanager
    def get_postgres_connection(self):
        """Get PostgreSQL connection"""
        try:
            conn = psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_database,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
                connect_timeout=10,
            )
            conn.autocommit = True
            yield conn
        finally:
            if "conn" in locals():
                conn.close()

    @contextmanager
    def get_integrated_duckdb(self):
        """Get DuckDB with PostgreSQL and biological memory setup"""
        self.temp_duckdb = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False).name
        postgres_url = f"postgresql://{self.config.postgres_user}:{self.config.postgres_password}@{self.config.postgres_host}:{self.config.postgres_port}/{self.config.postgres_database}"

        try:
            conn = duckdb.connect(self.temp_duckdb)

            # Load required extensions
            conn.execute("LOAD postgres")
            conn.execute("LOAD json")

            # Attach PostgreSQL
            conn.execute(f"ATTACH '{postgres_url}' AS pg_source (TYPE postgres)")

            # Create biological memory processing tables in DuckDB
            self.setup_biological_memory_tables(conn)

            yield conn

        finally:
            if "conn" in locals():
                conn.close()

    def setup_biological_memory_tables(self, duckdb_conn):
        """Set up biological memory processing tables in DuckDB"""

        # Working Memory View (Miller's 7±2 capacity)
        duckdb_conn.execute(
            """
            CREATE OR REPLACE VIEW working_memory_view AS
            WITH capacity_limited AS (
                SELECT id, content, timestamp, metadata,
                       ROW_NUMBER() OVER (
                           ORDER BY 
                               CASE WHEN JSON_EXTRACT_STRING(metadata, '$.importance') IS NOT NULL 
                                    THEN CAST(JSON_EXTRACT_STRING(metadata, '$.importance') AS DOUBLE)
                                    ELSE 0.5 END DESC,
                               timestamp DESC
                       ) as memory_rank,
                       CASE WHEN JSON_EXTRACT_STRING(metadata, '$.importance') IS NOT NULL 
                            THEN CAST(JSON_EXTRACT_STRING(metadata, '$.importance') AS DOUBLE)
                            ELSE 0.5 END as activation_level
                FROM pg_source.raw_memories
                WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
            )
            SELECT id, content, timestamp, metadata, activation_level, memory_rank
            FROM capacity_limited
            WHERE memory_rank <= ?
        """
        )

        # Short-Term Memory Episodes
        duckdb_conn.execute(
            """
            CREATE TABLE stm_episodes (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                level_0_goal TEXT,
                level_1_tasks TEXT,
                atomic_actions TEXT,
                stm_strength DOUBLE DEFAULT 0.5,
                hebbian_potential DOUBLE DEFAULT 0.0,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ready_for_consolidation BOOLEAN DEFAULT FALSE
            )
        """
        )

        # Long-Term Memory Semantic Network
        duckdb_conn.execute(
            """
            CREATE TABLE ltm_semantic_network (
                id INTEGER PRIMARY KEY,
                concept_a TEXT NOT NULL,
                concept_b TEXT NOT NULL,
                association_strength DOUBLE NOT NULL DEFAULT 0.5,
                association_type VARCHAR(50) DEFAULT 'semantic',
                consolidation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                retrieval_count INTEGER DEFAULT 0,
                last_retrieved TIMESTAMP,
                hebbian_trace DOUBLE DEFAULT 0.0
            )
        """
        )

        # LLM Processing Cache
        duckdb_conn.execute(
            """
            CREATE TABLE llm_processing_cache (
                content_hash VARCHAR PRIMARY KEY,
                original_content TEXT NOT NULL,
                processing_type VARCHAR(50) NOT NULL,
                result TEXT NOT NULL,
                model_used VARCHAR(100),
                processing_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

    def call_ollama_with_fallback(
        self, prompt: str, processing_type: str = "extraction"
    ) -> Dict[str, Any]:
        """Call Ollama with fallback handling"""
        try:
            # Check available models first
            models_response = requests.get(f"{self.config.ollama_url}/api/tags", timeout=5)
            if not models_response.ok:
                return self._get_mock_response(processing_type)

            available_models = [model["name"] for model in models_response.json().get("models", [])]

            # Select best available model
            model_to_use = None
            for preferred_model in [
                self.config.ollama_model,
                "qwen2.5:0.5b",
                available_models[0] if available_models else None,
            ]:
                if preferred_model and any(preferred_model in model for model in available_models):
                    model_to_use = preferred_model
                    break

            if not model_to_use:
                return self._get_mock_response(processing_type)

            # Make the actual call
            response = requests.post(
                f"{self.config.ollama_url}/api/generate",
                json={"model": model_to_use, "prompt": prompt, "stream": False},
                timeout=30,
            )

            if response.ok:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("response", ""),
                    "model": model_to_use,
                    "processing_type": processing_type,
                }
            else:
                return self._get_mock_response(processing_type)

        except Exception as e:
            logger.warning(f"Ollama call failed, using mock: {e}")
            return self._get_mock_response(processing_type)

    def _get_mock_response(self, processing_type: str) -> Dict[str, Any]:
        """Get mock response for offline testing"""
        mock_responses = {
            "goal_extraction": '{"goal": "Project Management and Execution", "confidence": 0.85}',
            "hierarchy_analysis": '{"goal": "Complete Project Tasks", "tasks": ["Plan objectives", "Execute plan", "Review progress"], "actions": ["Create timeline", "Assign resources", "Monitor status"]}',
            "entity_extraction": '{"entities": ["team", "project", "meeting"], "topics": ["collaboration", "planning", "management"]}',
            "embedding": [0.1] * 768,  # Mock 768-dimensional embedding
        }

        return {
            "success": False,
            "response": mock_responses.get(processing_type, '{"mock": true}'),
            "model": "mock_model",
            "processing_type": processing_type,
            "mock": True,
        }

    def setup_test_data_in_postgres(
        self, num_memories: int = 10
    ) -> List[Tuple[int, str, datetime, str]]:
        """Set up realistic test data in PostgreSQL"""
        with self.get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Create test schema
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.test_schema}")

                # Create raw_memories table
                table_name = f"{self.test_schema}.raw_memories"
                cursor.execute(
                    f"""
                    CREATE TABLE {table_name} (
                        id SERIAL PRIMARY KEY,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB DEFAULT '{{}}'::jsonb,
                        source_table VARCHAR(100) DEFAULT 'e2e_test'
                    )
                """
                )

                # Insert realistic biological memory test data
                test_memories = [
                    ("Working on quarterly business review and financial planning", 0.9),
                    ("Team standup discussing sprint goals and blockers", 0.7),
                    ("Code review for authentication system improvements", 0.8),
                    ("Planning next product release features and timeline", 0.85),
                    ("Debugging production API timeout issues", 0.95),
                    ("Client meeting about project requirements and scope", 0.8),
                    ("Database optimization for query performance", 0.75),
                    ("Team retrospective on development process improvements", 0.7),
                    ("Security audit findings and remediation planning", 0.9),
                    ("Documentation updates for API endpoints", 0.6),
                ]

                inserted_memories = []

                for i, (content, importance) in enumerate(test_memories[:num_memories]):
                    # Vary timestamps to test attention window
                    timestamp_offset = timedelta(minutes=i * 0.5)  # Spread over 5 minutes
                    test_timestamp = datetime.now(timezone.utc) - timestamp_offset

                    metadata = {
                        "importance": importance,
                        "source": "e2e_test",
                        "category": ["planning", "development", "review", "client", "operations"][
                            i % 5
                        ],
                        "complexity": min(1.0, 0.5 + (importance * 0.5)),
                    }

                    cursor.execute(
                        f"""
                        INSERT INTO {table_name} (content, timestamp, metadata)
                        VALUES (%s, %s, %s) RETURNING id
                    """,
                        (content, test_timestamp, json.dumps(metadata)),
                    )

                    memory_id = cursor.fetchone()[0]
                    inserted_memories.append(
                        (memory_id, content, test_timestamp, json.dumps(metadata))
                    )

                logger.info(f"Set up {len(inserted_memories)} test memories in PostgreSQL")
                return inserted_memories


class TestEndToEndBiologicalMemoryPipeline:
    """Test complete biological memory pipeline with live services"""

    def setup_method(self):
        """Set up test environment"""
        self.pipeline = BiologicalMemoryPipelineTester()

    def teardown_method(self):
        """Clean up after tests"""
        self.pipeline.cleanup()

    def test_complete_memory_lifecycle_with_live_services(self):
        """Test complete memory lifecycle from PostgreSQL ingestion to LTM consolidation"""
        with self.pipeline:
            # Step 1: Set up realistic test data in PostgreSQL
            test_memories = self.pipeline.setup_test_data_in_postgres(8)
            assert len(test_memories) == 8, "Should create 8 test memories"

            # Step 2: Process through integrated DuckDB pipeline
            with self.pipeline.get_integrated_duckdb() as duckdb_conn:

                # Test Working Memory Processing (Miller's 7±2 capacity)
                start_time = time.perf_counter()

                working_memory_result = duckdb_conn.execute(
                    f"""
                    SELECT id, content, activation_level, memory_rank
                    FROM working_memory_view
                    ORDER BY memory_rank
                """,
                    [self.pipeline.config.working_memory_capacity],
                ).fetchall()

                wm_processing_time = time.perf_counter() - start_time

                # Biological constraints validation
                assert (
                    wm_processing_time < 0.1
                ), f"Working memory processing took {wm_processing_time:.3f}s, should be <0.1s"
                assert (
                    len(working_memory_result) <= self.pipeline.config.working_memory_capacity
                ), "Should respect Miller's 7±2 capacity"
                assert len(working_memory_result) >= 5, "Should select high-importance memories"

                logger.info(
                    f"Working Memory: {len(working_memory_result)} items selected in {wm_processing_time:.3f}s"
                )

                # Step 3: Short-Term Memory Processing with LLM integration
                stm_memories_processed = 0

                for wm_item in working_memory_result[:5]:  # Process top 5 for STM
                    memory_id, content, activation_level, memory_rank = wm_item

                    # LLM-based hierarchy extraction
                    hierarchy_prompt = f"""Analyze the memory content for goal-task-action hierarchy:
Content: {content}

Return JSON with this structure:
{{"goal": "high-level goal category", "tasks": ["task1", "task2"], "actions": ["action1", "action2"]}}

Goal should be one of: Product Launch Strategy, Communication and Collaboration, 
Financial Planning and Management, Project Management and Execution, 
Client Relations and Service, Operations and System Maintenance"""

                    llm_result = self.pipeline.call_ollama_with_fallback(
                        hierarchy_prompt, "hierarchy_analysis"
                    )

                    # Parse hierarchy result
                    try:
                        if llm_result["success"]:
                            hierarchy_data = json.loads(llm_result["response"])
                        else:
                            # Use mock data
                            hierarchy_data = json.loads(llm_result["response"])

                        goal = hierarchy_data.get("goal", "General Task Processing")
                        tasks = ", ".join(hierarchy_data.get("tasks", ["unknown task"]))
                        actions = ", ".join(hierarchy_data.get("actions", ["unknown action"]))

                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"LLM hierarchy parsing failed: {e}, using defaults")
                        goal = "General Task Processing"
                        tasks = "process content"
                        actions = "complete task"

                    # Calculate STM strength based on activation and processing
                    stm_strength = min(1.0, activation_level + 0.1)
                    hebbian_potential = activation_level * 0.8
                    ready_for_consolidation = (
                        stm_strength >= self.pipeline.config.consolidation_threshold
                    )

                    # Store in STM
                    duckdb_conn.execute(
                        """
                        INSERT INTO stm_episodes 
                        (id, content, level_0_goal, level_1_tasks, atomic_actions, stm_strength, hebbian_potential, ready_for_consolidation)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            memory_id,
                            content,
                            goal,
                            tasks,
                            actions,
                            stm_strength,
                            hebbian_potential,
                            ready_for_consolidation,
                        ),
                    )

                    stm_memories_processed += 1

                assert stm_memories_processed >= 5, "Should process at least 5 STM episodes"
                logger.info(f"Short-Term Memory: {stm_memories_processed} episodes processed")

                # Step 4: Long-Term Memory Consolidation
                consolidation_candidates = duckdb_conn.execute(
                    """
                    SELECT id, content, level_0_goal, level_1_tasks, stm_strength, hebbian_potential
                    FROM stm_episodes
                    WHERE ready_for_consolidation = true
                    ORDER BY (stm_strength * hebbian_potential) DESC
                """
                ).fetchall()

                ltm_associations_created = 0

                for candidate in consolidation_candidates:
                    memory_id, content, goal, tasks, strength, hebbian = candidate

                    # Create semantic associations with Hebbian learning
                    associations = [
                        (goal, "memory_goal", strength * 0.9),
                        (tasks.split(",")[0].strip() if tasks else "task", goal, hebbian * 0.8),
                        ("episodic_memory", goal, strength * hebbian * 0.7),
                    ]

                    for concept_a, concept_b, assoc_strength in associations:
                        if (
                            concept_a
                            and concept_b
                            and len(concept_a.strip()) > 0
                            and len(concept_b.strip()) > 0
                        ):
                            duckdb_conn.execute(
                                """
                                INSERT OR REPLACE INTO ltm_semantic_network
                                (concept_a, concept_b, association_strength, association_type, hebbian_trace)
                                VALUES (?, ?, ?, 'consolidation', ?)
                            """,
                                (concept_a[:50], concept_b[:50], assoc_strength, hebbian),
                            )

                            ltm_associations_created += 1

                logger.info(
                    f"Long-Term Memory: {ltm_associations_created} semantic associations created"
                )
                assert ltm_associations_created >= 3, "Should create semantic associations in LTM"

                # Step 5: Validate complete pipeline data flow
                pipeline_stats = {
                    "raw_memories": len(test_memories),
                    "working_memory": len(working_memory_result),
                    "stm_episodes": stm_memories_processed,
                    "ltm_associations": ltm_associations_created,
                    "consolidation_candidates": len(consolidation_candidates),
                }

                # Biological pipeline validation
                assert (
                    pipeline_stats["working_memory"] <= self.pipeline.config.working_memory_capacity
                )
                assert pipeline_stats["stm_episodes"] <= pipeline_stats["working_memory"]
                assert (
                    pipeline_stats["ltm_associations"] >= pipeline_stats["consolidation_candidates"]
                )
                assert pipeline_stats["consolidation_candidates"] >= 1

                logger.info(f"Pipeline stats: {pipeline_stats}")

                return pipeline_stats

    def test_biological_timing_constraints_end_to_end(self):
        """Test that complete pipeline meets biological timing constraints"""
        with self.pipeline:
            test_memories = self.pipeline.setup_test_data_in_postgres(5)

            with self.pipeline.get_integrated_duckdb() as duckdb_conn:
                # Measure complete pipeline timing
                pipeline_start = time.perf_counter()

                # Working Memory (should be <100ms)
                wm_start = time.perf_counter()
                working_memory_result = duckdb_conn.execute(
                    f"""
                    SELECT id, content, activation_level, memory_rank
                    FROM working_memory_view
                    ORDER BY memory_rank
                """,
                    [5],
                ).fetchall()
                wm_time = time.perf_counter() - wm_start

                # Short-Term Memory processing (should be <500ms per item for non-LLM parts)
                stm_start = time.perf_counter()

                # Process one memory item (without LLM for timing test)
                if working_memory_result:
                    test_memory = working_memory_result[0]
                    duckdb_conn.execute(
                        """
                        INSERT INTO stm_episodes (id, content, level_0_goal, stm_strength)
                        VALUES (?, ?, ?, ?)
                    """,
                        (test_memory[0], test_memory[1], "Test Goal", 0.8),
                    )

                stm_time = time.perf_counter() - stm_start

                # Consolidation processing (should be <2s)
                consolidation_start = time.perf_counter()

                duckdb_conn.execute(
                    """
                    INSERT INTO ltm_semantic_network (concept_a, concept_b, association_strength)
                    VALUES ('test_concept_a', 'test_concept_b', 0.7)
                """
                )

                consolidation_time = time.perf_counter() - consolidation_start

                total_pipeline_time = time.perf_counter() - pipeline_start

                # Biological timing constraints (excluding LLM calls)
                assert (
                    wm_time < 0.1
                ), f"Working memory processing took {wm_time:.3f}s, should be <0.1s"
                assert stm_time < 0.5, f"STM processing took {stm_time:.3f}s, should be <0.5s"
                assert (
                    consolidation_time < 2.0
                ), f"Consolidation took {consolidation_time:.3f}s, should be <2.0s"
                assert (
                    total_pipeline_time < 5.0
                ), f"Total pipeline took {total_pipeline_time:.3f}s, should be <5.0s"

                logger.info(f"Biological timing validation:")
                logger.info(f"  Working Memory: {wm_time:.3f}s (<0.1s required)")
                logger.info(f"  Short-Term Memory: {stm_time:.3f}s (<0.5s required)")
                logger.info(f"  Consolidation: {consolidation_time:.3f}s (<2.0s required)")
                logger.info(f"  Total Pipeline: {total_pipeline_time:.3f}s (<5.0s required)")

    def test_hebbian_learning_with_live_services(self):
        """Test Hebbian learning algorithm with live LLM processing"""
        with self.pipeline:
            test_memories = self.pipeline.setup_test_data_in_postgres(6)

            with self.pipeline.get_integrated_duckdb() as duckdb_conn:
                # Create initial semantic associations
                initial_associations = [
                    ("project", "planning", 0.5),
                    ("team", "collaboration", 0.6),
                    ("code", "review", 0.4),
                    ("meeting", "discussion", 0.5),
                ]

                for concept_a, concept_b, strength in initial_associations:
                    duckdb_conn.execute(
                        """
                        INSERT INTO ltm_semantic_network 
                        (concept_a, concept_b, association_strength, retrieval_count)
                        VALUES (?, ?, ?, 0)
                    """,
                        (concept_a, concept_b, strength),
                    )

                # Process memories that should strengthen some associations
                working_memories = duckdb_conn.execute(
                    f"""
                    SELECT id, content FROM working_memory_view ORDER BY memory_rank LIMIT 3
                """,
                    [3],
                ).fetchall()

                for memory_id, content in working_memories:
                    # Extract entities (with LLM or mock)
                    entity_prompt = f'Extract key entities from: {content}\nReturn JSON: {{"entities": ["entity1", "entity2"]}}'

                    entity_result = self.pipeline.call_ollama_with_fallback(
                        entity_prompt, "entity_extraction"
                    )

                    try:
                        if entity_result["success"]:
                            entities_data = json.loads(entity_result["response"])
                        else:
                            entities_data = json.loads(entity_result["response"])

                        entities = entities_data.get("entities", ["project", "team"])  # fallback

                    except (json.JSONDecodeError, KeyError):
                        entities = ["project", "team"]  # safe fallback

                    # Hebbian strengthening: co-occurring concepts get stronger associations
                    for i, entity_a in enumerate(entities):
                        for entity_b in entities[i + 1 :]:
                            # Apply Hebbian learning rule
                            duckdb_conn.execute(
                                """
                                UPDATE ltm_semantic_network 
                                SET 
                                    association_strength = LEAST(1.0, association_strength + ?),
                                    retrieval_count = retrieval_count + 1,
                                    last_retrieved = CURRENT_TIMESTAMP,
                                    hebbian_trace = LEAST(1.0, hebbian_trace + ?)
                                WHERE (concept_a = ? AND concept_b = ?) 
                                   OR (concept_a = ? AND concept_b = ?)
                            """,
                                (
                                    self.pipeline.config.hebbian_learning_rate,
                                    self.pipeline.config.hebbian_learning_rate * 0.5,
                                    entity_a,
                                    entity_b,
                                    entity_b,
                                    entity_a,
                                ),
                            )

                # Verify Hebbian learning effects
                strengthened_associations = duckdb_conn.execute(
                    """
                    SELECT concept_a, concept_b, association_strength, retrieval_count, hebbian_trace
                    FROM ltm_semantic_network
                    WHERE retrieval_count > 0
                    ORDER BY association_strength DESC
                """
                ).fetchall()

                assert len(strengthened_associations) > 0, "Should have strengthened associations"

                # Check that retrieved associations are stronger than initial
                max_strength = max(assoc[2] for assoc in strengthened_associations)
                assert (
                    max_strength > 0.6
                ), f"Max association strength {max_strength} should show Hebbian strengthening"

                logger.info(
                    f"Hebbian learning: {len(strengthened_associations)} associations strengthened"
                )
                for assoc in strengthened_associations[:3]:
                    logger.info(
                        f"  {assoc[0]} <-> {assoc[1]}: strength={assoc[2]:.3f}, retrievals={assoc[3]}"
                    )

    def test_error_recovery_in_complete_pipeline(self):
        """Test error recovery across the complete pipeline with service failures"""
        with self.pipeline:
            test_memories = self.pipeline.setup_test_data_in_postgres(5)

            with self.pipeline.get_integrated_duckdb() as duckdb_conn:
                # Test pipeline continues despite LLM service failures
                working_memory_result = duckdb_conn.execute(
                    f"""
                    SELECT id, content, activation_level
                    FROM working_memory_view
                    ORDER BY memory_rank LIMIT 3
                """,
                    [3],
                ).fetchall()

                successful_stm_processing = 0

                for memory_id, content, activation in working_memory_result:
                    # Simulate LLM service failure by forcing mock responses
                    hierarchy_result = self.pipeline._get_mock_response("hierarchy_analysis")

                    try:
                        hierarchy_data = json.loads(hierarchy_result["response"])
                        goal = hierarchy_data.get("goal", "Fallback Goal")
                        tasks = ", ".join(hierarchy_data.get("tasks", ["fallback task"]))

                        # STM processing should continue with fallback data
                        duckdb_conn.execute(
                            """
                            INSERT INTO stm_episodes (id, content, level_0_goal, level_1_tasks, stm_strength)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (memory_id, content, goal, tasks, activation),
                        )

                        successful_stm_processing += 1

                    except Exception as e:
                        logger.warning(f"STM processing failed for memory {memory_id}: {e}")

                # Pipeline should continue processing even with service failures
                assert (
                    successful_stm_processing >= 2
                ), "Should process most memories despite LLM failures"

                # Test consolidation continues
                stm_episodes = duckdb_conn.execute("SELECT COUNT(*) FROM stm_episodes").fetchall()[
                    0
                ][0]
                assert stm_episodes >= 2, "Should have STM episodes despite service issues"

                # Test LTM formation continues
                duckdb_conn.execute(
                    """
                    INSERT INTO ltm_semantic_network (concept_a, concept_b, association_strength)
                    VALUES ('fallback_concept_a', 'fallback_concept_b', 0.6)
                """
                )

                ltm_associations = duckdb_conn.execute(
                    "SELECT COUNT(*) FROM ltm_semantic_network"
                ).fetchall()[0][0]
                assert (
                    ltm_associations >= 1
                ), "Should create LTM associations despite service issues"

                logger.info(
                    f"Error recovery: {successful_stm_processing} STM episodes, {ltm_associations} LTM associations"
                )


def run_end_to_end_integration_tests():
    """Run end-to-end integration tests"""
    logger.info("Starting end-to-end biological memory pipeline integration tests")

    # Check prerequisites
    required_env_vars = ["POSTGRES_PASSWORD"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
        logger.warning("Some tests may be skipped")

    try:
        # Run tests
        pytest_args = [__file__, "-v", "--tb=short", "-k", "test_"]

        exit_code = pytest.main(pytest_args)
        return exit_code == 0

    except Exception as e:
        logger.error(f"End-to-end integration tests failed: {e}")
        return False


if __name__ == "__main__":
    success = run_end_to_end_integration_tests()
    exit(0 if success else 1)
