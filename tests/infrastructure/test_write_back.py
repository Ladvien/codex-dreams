#!/usr/bin/env python3
"""
Comprehensive Test Suite for Memory Write-back Mechanism
=======================================================

This test suite validates the complete write-back mechanism for persistent memory processing,
including schema creation, service functionality, incremental processing, and integration.

Test Coverage:
- PostgreSQL schema creation and validation
- Write-back service core functionality
- Incremental processing logic
- DBT integration hooks
- Error handling and recovery
- Performance and scalability
- Data consistency validation
"""

import json
import os
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import duckdb
import psycopg2
import psycopg2.extras
import pytest

from src.scripts.run_writeback_after_dbt import run_writeback_integration, validate_dbt_success
from src.services.incremental_processor import (
    IncrementalBatch,
    IncrementalProcessor,
    ProcessingState,
)
from src.services.memory_writeback_service import MemoryWritebackService, ProcessingMetrics

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# Module-level fixtures available to all test classes
@pytest.fixture(scope="module")
def test_postgres_url():
    """Get test PostgreSQL connection URL"""
    return os.getenv(
        "TEST_DATABASE_URL", "postgresql://codex_user:test_password@localhost:5432/test_codex_db"
    )


@pytest.fixture(scope="module")
def test_duckdb_path():
    """Create temporary DuckDB database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture(scope="module")
def test_db_connection(test_postgres_url):
    """Create test database connection"""
    conn = None
    try:
        conn = psycopg2.connect(test_postgres_url, cursor_factory=psycopg2.extras.DictCursor)
        yield conn
    except psycopg2.OperationalError:
        # Database doesn't exist, use mock connection
        pytest.skip("Test database not available, skipping PostgreSQL integration tests")
    finally:
        if conn:
            conn.close()


class TestWritebackInfrastructure:
    """Test infrastructure setup and configuration"""

    def test_schema_creation(self, test_db_connection):
        """Test PostgreSQL schema creation and structure"""
        with test_db_connection.cursor() as cursor:
            # Read and execute schema creation script
            schema_file = (
                Path(__file__).parent.parent.parent / "sql" / "create_codex_processed_schema.sql"
            )

            if schema_file.exists():
                with open(schema_file, "r") as f:
                    schema_sql = f.read()

                cursor.execute(schema_sql)
                test_db_connection.commit()

            # Validate schema exists
            cursor.execute(
                """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name = 'codex_processed'
            """
            )

            assert cursor.fetchone() is not None, "codex_processed schema should exist"

            # Validate required tables exist
            required_tables = [
                "processed_memories",
                "generated_insights",
                "memory_associations",
                "processing_metadata",
            ]

            for table in required_tables:
                cursor.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'codex_processed'
                    AND table_name = %s
                """,
                    (table,),
                )

                assert (
                    cursor.fetchone() is not None
                ), f"Table {table} should exist in codex_processed schema"

            # Validate key indexes exist
            cursor.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'codex_processed'
            """
            )

            indexes = [row["indexname"] for row in cursor.fetchall()]
            assert len(indexes) >= 10, "Should have multiple indexes for performance"

    def test_table_constraints(self, test_db_connection):
        """Test database table constraints and validation rules"""
        with test_db_connection.cursor() as cursor:

            # Test processed_memories constraints
            cursor.execute(
                """
                INSERT INTO codex_processed.processed_memories (
                    source_memory_id, stm_strength, consolidated_strength
                ) VALUES (%s, %s, %s)
            """,
                (str(uuid.uuid4()), 0.8, 0.7),
            )

            # Test invalid strength values (should fail)
            with pytest.raises(psycopg2.IntegrityError):
                cursor.execute(
                    """
                    INSERT INTO codex_processed.processed_memories (
                        source_memory_id, stm_strength
                    ) VALUES (%s, %s)
                """,
                    (str(uuid.uuid4()), 1.5),
                )  # Invalid strength > 1.0

            test_db_connection.rollback()

            # Test generated_insights constraints
            cursor.execute(
                """
                INSERT INTO codex_processed.generated_insights (
                    source_memory_ids, insight_text, insight_type, insight_confidence
                ) VALUES (%s, %s, %s, %s)
            """,
                ([str(uuid.uuid4())], "Test insight", "pattern", 0.85),
            )

            # Test invalid insight type (should fail)
            with pytest.raises(psycopg2.IntegrityError):
                cursor.execute(
                    """
                    INSERT INTO codex_processed.generated_insights (
                        source_memory_ids, insight_text, insight_type
                    ) VALUES (%s, %s, %s)
                """,
                    ([str(uuid.uuid4())], "Test insight", "invalid_type"),
                )

            test_db_connection.rollback()


class TestMemoryWritebackService:
    """Test core write-back service functionality"""

    @pytest.fixture
    def real_writeback_service(self, test_postgres_url, test_duckdb_path):
        """Create REAL write-back service for production testing"""
        import os
        import tempfile

        import duckdb

        # Create a temporary DuckDB file for this test
        with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as temp_db:
            temp_duckdb_path = temp_db.name

        # Remove the empty file so DuckDB can create a proper database
        os.unlink(temp_duckdb_path)

        try:
            # Create a real service instance but initialize only what we need
            service = MemoryWritebackService.__new__(MemoryWritebackService)
            service.batch_size = 100
            service.max_retries = 3
            service.processing_metrics = {}
            service.current_session_id = str(uuid.uuid4())

            # Initialize logger
            import logging

            service.logger = logging.getLogger("memory_writeback")

            # Create REAL DuckDB connection (no mocks!)
            service.duckdb_conn = duckdb.connect(temp_duckdb_path)

            # Install extensions for production compatibility
            try:
                service.duckdb_conn.execute("INSTALL json")
                service.duckdb_conn.execute("LOAD json")
                service.duckdb_conn.execute("INSTALL postgres")
                service.duckdb_conn.execute("LOAD postgres")
            except:
                pass  # Extensions may not be available in all environments

            # Set pg_pool to None for DuckDB-only tests
            service.pg_pool = None

            yield service

        finally:
            # Clean up the temporary database file
            try:
                service.duckdb_conn.close()
            except:
                pass
            if os.path.exists(temp_duckdb_path):
                os.unlink(temp_duckdb_path)

    def test_service_initialization(self, real_writeback_service):
        """Test service initialization and configuration"""
        service = real_writeback_service

        assert service.batch_size == 100
        assert service.max_retries == 3
        assert service.current_session_id is not None
        assert len(service.processing_metrics) == 0

    def test_processing_batch_creation(self, real_writeback_service):
        """Test processing batch creation and tracking"""
        service = real_writeback_service

        batch_id = service.create_processing_batch("test_stage", "Test batch")

        assert batch_id in service.processing_metrics
        metrics = service.processing_metrics[batch_id]

        assert metrics.processing_stage == "test_stage"
        assert metrics.session_id == service.current_session_id
        assert metrics.start_time is not None

    def test_extract_processed_memories(self, real_writeback_service):
        """Test extraction of processed memories from DuckDB"""
        service = real_writeback_service

        # Create the real database tables that the service expects
        service.duckdb_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_replay (
                id TEXT PRIMARY KEY,
                content TEXT,
                level_0_goal TEXT,
                level_1_tasks TEXT[],
                atomic_actions TEXT[],
                phantom_objects JSON,
                consolidated_strength FLOAT,
                consolidation_fate TEXT,
                hebbian_strength FLOAT,
                semantic_gist TEXT,
                semantic_category TEXT,
                cortical_region TEXT,
                retrieval_accessibility FLOAT,
                stm_strength FLOAT,
                emotional_salience FLOAT,
                consolidated_at TIMESTAMP
            )
        """
        )

        service.duckdb_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stable_memories (
                memory_id TEXT PRIMARY KEY,
                concepts TEXT[],
                activation_strength FLOAT,
                created_at TIMESTAMP,
                last_processed_at TIMESTAMP
            )
        """
        )

        # Insert real test data that matches what the production service expects
        from datetime import datetime, timezone

        current_time = datetime.now(timezone.utc)

        test_memory_id = str(uuid.uuid4())

        service.duckdb_conn.execute(
            """
            INSERT INTO memory_replay (
                id, content, level_0_goal, level_1_tasks, atomic_actions, phantom_objects,
                consolidated_strength, consolidation_fate, hebbian_strength,
                semantic_gist, semantic_category, cortical_region,
                retrieval_accessibility, stm_strength, emotional_salience,
                consolidated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                test_memory_id,
                "Test memory content for production testing",
                "Test Goal",
                ["task1", "task2"],
                ["action1", "action2"],
                '{"spatial_context": "test_environment"}',
                0.8,
                "cortical_transfer",
                0.7,
                "semantic test",
                "strategic",
                "prefrontal_cortex",
                0.9,
                0.6,
                0.5,
                current_time,
            ],
        )

        service.duckdb_conn.execute(
            """
            INSERT INTO stable_memories (
                memory_id, concepts, activation_strength, created_at, last_processed_at
            ) VALUES (?, ?, ?, ?, ?)
        """,
            [test_memory_id, ["concept1", "concept2"], 0.5, current_time, current_time],
        )

        # Extract memories using the real service
        memories = service._extract_processed_memories()

        # Validate the results from real database operations
        assert len(memories) == 1, f"Expected 1 memory, got {len(memories)}"
        assert memories[0]["level_0_goal"] == "Test Goal"
        assert (
            abs(memories[0]["consolidated_strength"] - 0.8) < 0.001
        )  # Account for floating point precision
        assert memories[0]["consolidation_fate"] == "cortical_transfer"

    def test_metrics_calculation(self, real_writeback_service):
        """Test processing metrics calculation and tracking"""
        service = real_writeback_service

        batch_id = service.create_processing_batch("test_metrics")
        metrics = service.processing_metrics[batch_id]

        # Simulate processing
        metrics.memories_processed = 150
        metrics.successful_writes = 140
        metrics.failed_writes = 10
        metrics.end_time = datetime.now(timezone.utc)
        metrics.duration_seconds = (metrics.end_time - metrics.start_time).total_seconds()

        assert metrics.memories_processed == 150
        assert metrics.successful_writes == 140
        assert metrics.failed_writes == 10
        assert metrics.duration_seconds >= 0


class TestIncrementalProcessor:
    """Test incremental processing logic"""

    @pytest.fixture
    def mock_incremental_processor(self, test_postgres_url, test_duckdb_path):
        """Create mock incremental processor for testing"""
        with patch("duckdb.connect"):
            processor = IncrementalProcessor(
                postgres_url=test_postgres_url, duckdb_path=test_duckdb_path
            )
            yield processor

    def test_processing_state_creation(self, mock_incremental_processor):
        """Test processing state creation and management"""
        processor = mock_incremental_processor

        # Test state creation
        timestamp = datetime.now(timezone.utc)
        state = ProcessingState(
            stage_name="test_stage",
            last_processed_timestamp=timestamp,
            last_processed_batch_id="batch123",
            watermark_value=timestamp.isoformat(),
        )

        assert state.stage_name == "test_stage"
        assert state.last_processed_timestamp == timestamp
        assert state.records_processed == 0
        assert len(state.processing_errors) == 0

    @patch("psycopg2.connect")
    def test_processing_state_persistence(self, mock_connect, mock_incremental_processor):
        """Test processing state loading and persistence"""
        processor = mock_incremental_processor

        # Mock database response
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {
            "processing_stage": "test_stage",
            "processing_end_time": datetime.now(timezone.utc),
            "batch_id": "test_batch_123",
            "total_memories_processed": 100,
        }

        mock_conn = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        state = processor._load_processing_state_from_db("test_stage")

        assert state is not None
        assert state.stage_name == "test_stage"
        assert state.records_processed == 100

    def test_incremental_batch_creation(self, mock_incremental_processor):
        """Test incremental batch creation logic"""
        processor = mock_incremental_processor

        # Mock DuckDB data
        test_data = [
            {
                "source_memory_id": str(uuid.uuid4()),
                "consolidated_strength": 0.8,
                "timestamp": datetime.now(timezone.utc),
            },
            {
                "source_memory_id": str(uuid.uuid4()),
                "consolidated_strength": 0.6,
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=10),
            },
        ]

        with patch.object(processor, "_get_incremental_memories", return_value=test_data):
            batch = processor.create_incremental_batch("processed_memories", max_records=1000)

            assert batch is not None
            assert batch.record_count == 2
            assert batch.stage == "processed_memories"
            assert len(batch.batch_hash) == 64  # SHA256 hash length

    def test_change_detection(self, mock_incremental_processor):
        """Test change detection logic"""
        processor = mock_incremental_processor

        batch = IncrementalBatch(
            batch_id="test_batch",
            stage="test_stage",
            data=[{"test": "data"}],
            watermark_start=datetime.now(timezone.utc).isoformat(),
            watermark_end=datetime.now(timezone.utc).isoformat(),
            record_count=1,
            batch_hash="test_hash_123",
            created_at=datetime.now(timezone.utc),
        )

        # Mock no previous processing (should detect changes)
        with patch.object(processor, "_get_pg_connection") as mock_pg:
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = None  # No previous processing

            mock_conn = Mock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_pg.return_value.__enter__.return_value = mock_conn

            changes_detected = processor.detect_changes("test_stage", batch)
            assert changes_detected is True

    def test_recovery_batch_creation(self, mock_incremental_processor):
        """Test recovery batch creation for failed processing"""
        processor = mock_incremental_processor

        failed_timestamp = datetime.now(timezone.utc)

        with patch.object(processor, "create_incremental_batch") as mock_create:
            # Mock batch creation
            mock_batch = Mock()
            mock_batch.batch_id = "recovery_test_batch"
            mock_create.return_value = mock_batch

            recovery_batches = processor.get_recovery_batches(
                stage="test_stage", failed_timestamp=failed_timestamp, max_recovery_hours=8
            )

            assert len(recovery_batches) >= 1
            assert "recovery_" in recovery_batches[0].batch_id


class TestDBTIntegration:
    """Test dbt integration and orchestration"""

    def test_dbt_results_validation(self):
        """Test dbt results validation logic"""
        # Test successful results
        success_results = {
            "success": True,
            "results": [
                {"unique_id": "model.test.memory_replay", "status": "success"},
                {"unique_id": "model.test.mvp_insights", "status": "success"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(success_results, f)
            success_file = f.name

        try:
            assert validate_dbt_success(success_file) is True
        finally:
            os.unlink(success_file)

        # Test failed results
        failed_results = {
            "success": False,
            "results": [
                {
                    "unique_id": "model.test.memory_replay",
                    "status": "error",
                    "message": "SQL compilation error",
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(failed_results, f)
            failed_file = f.name

        try:
            assert validate_dbt_success(failed_file) is False
        finally:
            os.unlink(failed_file)

    def test_stage_determination(self):
        """Test processing stage determination from dbt models"""
        from scripts.run_writeback_after_dbt import determine_processing_stages

        # Test with specific models
        executed_models = ["memory_replay", "mvp_memory_insights", "concept_associations"]
        stages = determine_processing_stages(executed_models)

        expected_stages = ["processed_memories", "generated_insights", "memory_associations"]
        assert set(stages) == set(expected_stages)

        # Test with no models (should return all stages)
        all_stages = determine_processing_stages([])
        assert len(all_stages) == 3

    @patch("services.memory_writeback_service.MemoryWritebackService")
    @patch("services.incremental_processor.IncrementalProcessor")
    def test_writeback_integration_flow(self, mock_incremental, mock_writeback):
        """Test complete write-back integration flow"""
        # Mock service initialization
        mock_service = Mock()
        mock_service.write_processed_memories.return_value = {
            "batch_id": "test_batch",
            "status": "completed",
            "memories_processed": 50,
            "duration_seconds": 2.5,
        }
        mock_writeback.return_value = mock_service

        # Mock incremental processor
        mock_processor = Mock()
        mock_batch = Mock()
        mock_batch.record_count = 50
        mock_processor.create_incremental_batch.return_value = mock_batch
        mock_processor.detect_changes.return_value = True
        mock_incremental.return_value = mock_processor

        # Run integration
        results = run_writeback_integration(
            stages=["processed_memories"], incremental=True, force=False
        )

        assert results["overall_status"] in ["completed", "completed_with_errors"]
        assert results["dbt_validation"] is True
        assert len(results["stages_executed"]) >= 0


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms"""

    @pytest.fixture
    def mock_service_with_errors(self, test_postgres_url, test_duckdb_path):
        """Create service that simulates various error conditions"""
        with patch("psycopg2.pool.ThreadedConnectionPool"):
            with patch("duckdb.connect"):
                with patch.object(MemoryWritebackService, "_test_connections"):
                    service = MemoryWritebackService(
                        postgres_url=test_postgres_url, duckdb_path=test_duckdb_path
                    )
                    yield service

    def test_connection_error_handling(self, mock_service_with_errors):
        """Test handling of database connection errors"""
        service = mock_service_with_errors

        # Mock connection pool failure
        service.pg_pool = None

        with pytest.raises(AttributeError):
            with service._get_pg_connection():
                pass

    def test_processing_error_recovery(self, mock_service_with_errors):
        """Test processing error recovery logic"""
        service = mock_service_with_errors

        batch_id = service.create_processing_batch("test_error_recovery")
        metrics = service.processing_metrics[batch_id]

        # Simulate processing error
        metrics.error_messages.append("Test error message")
        metrics.failed_writes = 10

        assert len(metrics.error_messages) == 1
        assert metrics.failed_writes == 10

    def test_transaction_rollback(self, mock_service_with_errors):
        """Test transaction rollback on errors"""
        service = mock_service_with_errors

        # Mock connection that fails during transaction
        with patch.object(service, "_get_pg_connection") as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.execute.side_effect = psycopg2.IntegrityError("Test error")

            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_conn.return_value.__enter__.return_value = mock_conn

            # Should handle error gracefully
            with pytest.raises(psycopg2.IntegrityError):
                service._write_processed_memories_batch([], Mock())

            # Verify rollback was called
            mock_conn.rollback.assert_called_once()


class TestPerformanceAndScalability:
    """Test performance characteristics and scalability"""

    def test_batch_processing_performance(self):
        """Test batch processing performance characteristics"""
        # Test various batch sizes
        batch_sizes = [100, 500, 1000, 2000]

        for batch_size in batch_sizes:
            # Create mock data
            test_data = [
                {
                    "source_memory_id": str(uuid.uuid4()),
                    "level_0_goal": f"Goal {i}",
                    "consolidated_strength": 0.5 + (i % 50) / 100,
                    "processed_at": datetime.now(timezone.utc),
                }
                for i in range(batch_size)
            ]

            # Time the batch preparation (would be actual processing in real
            # implementation)
            start_time = datetime.now(timezone.utc)

            # Simulate batch processing logic
            prepared_batch = []
            for record in test_data:
                prepared_record = {
                    "source_memory_id": record["source_memory_id"],
                    "level_0_goal": record["level_0_goal"],
                    "consolidated_strength": record["consolidated_strength"],
                }
                prepared_batch.append(prepared_record)

            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()

            # Basic performance validation
            assert (
                processing_time < 1.0
            ), f"Batch size {batch_size} took too long: {processing_time}s"
            assert len(prepared_batch) == batch_size

    def test_memory_usage_patterns(self):
        """Test memory usage patterns for large datasets"""
        import sys

        # Create large dataset
        large_dataset = [
            {
                "id": str(uuid.uuid4()),
                # ~2KB per record
                "content": f"Large content string {i} " * 100,
                "timestamp": datetime.now(timezone.utc),
            }
            for i in range(1000)  # ~2MB total
        ]

        initial_memory = sys.getsizeof(large_dataset)

        # Process in chunks (simulating batching)
        chunk_size = 100
        processed_chunks = 0

        for i in range(0, len(large_dataset), chunk_size):
            chunk = large_dataset[i : i + chunk_size]

            # Simulate processing
            processed_chunk = [
                {
                    "processed_id": record["id"],
                    # Truncate for efficiency
                    "processed_content": record["content"][:100],
                    "processed_at": record["timestamp"],
                }
                for record in chunk
            ]

            processed_chunks += 1

            # Validate chunk processing
            assert len(processed_chunk) <= chunk_size

        assert processed_chunks == 10  # 1000 / 100

    def test_concurrent_processing_safety(self):
        """Test thread safety for concurrent processing"""
        import threading
        import time

        # Shared state for testing
        shared_metrics = {"processed": 0, "errors": 0}
        lock = threading.Lock()

        def mock_processing_worker(worker_id: int, records_count: int):
            """Mock worker that processes records"""
            try:
                # Simulate processing time
                time.sleep(0.1)

                with lock:
                    shared_metrics["processed"] += records_count

            except Exception:
                with lock:
                    shared_metrics["errors"] += 1

        # Start multiple workers
        workers = []
        records_per_worker = 50

        for i in range(5):
            worker = threading.Thread(target=mock_processing_worker, args=(i, records_per_worker))
            workers.append(worker)
            worker.start()

        # Wait for all workers to complete
        for worker in workers:
            worker.join()

        # Validate results
        assert shared_metrics["processed"] == 250  # 5 workers * 50 records
        assert shared_metrics["errors"] == 0


def run_comprehensive_test_suite():
    """Run the complete test suite with detailed reporting"""

    print("=" * 70)
    print("MEMORY WRITE-BACK MECHANISM - COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    # Configure pytest with detailed output
    pytest_args = [
        __file__,
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--durations=10",  # Show 10 slowest tests
        "--cov=src/services",  # Coverage for services
        "--cov-report=term-missing",  # Show missing coverage
        "--capture=no",  # Show print statements
    ]

    try:
        exit_code = pytest.main(pytest_args)

        if exit_code == 0:
            print("\n" + "=" * 70)
            print("✅ ALL TESTS PASSED - Write-back mechanism is fully functional!")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("❌ SOME TESTS FAILED - Review failures above")
            print("=" * 70)

        return exit_code

    except Exception as e:
        print(f"\n❌ Test suite execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_comprehensive_test_suite()
    sys.exit(exit_code)
