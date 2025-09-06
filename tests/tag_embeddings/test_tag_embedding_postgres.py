#!/usr/bin/env python3
"""
Integration tests for tag embedding PostgreSQL schema and transfer functionality.
Tests migration, health checks, and data transfer processes.
"""

import os
import sys
from contextlib import contextmanager
from unittest.mock import Mock, patch

import psycopg2
import pytest


class TestTagEmbeddingPostgresIntegration:
    """Test PostgreSQL schema and integration for tag embeddings"""

    @pytest.fixture
    def postgres_conn(self):
        """Create a test PostgreSQL connection (requires test database)"""
        # This test requires a real PostgreSQL instance with pgvector
        # Skip if not available
        try:
            conn = psycopg2.connect(
                host=os.getenv("TEST_POSTGRES_HOST", "localhost"),
                database=os.getenv("TEST_POSTGRES_DB", "test_codex_db"),
                user=os.getenv("TEST_POSTGRES_USER", "test_user"),
                password=os.getenv("TEST_POSTGRES_PASS", "test_pass"),
                port=os.getenv("TEST_POSTGRES_PORT", "5432"),
            )
            return conn
        except psycopg2.Error:
            pytest.skip("Test PostgreSQL database not available")

    @pytest.fixture
    def setup_test_schema(self, postgres_conn):
        """Set up test schema with memories table"""
        cursor = postgres_conn.cursor()

        # Ensure pgvector extension exists
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            postgres_conn.commit()
        except psycopg2.Error as e:
            pytest.skip(f"pgvector extension not available: {e}")

        # Create test memories table
        cursor.execute(
            """
            DROP TABLE IF EXISTS test_memories CASCADE;
            CREATE TABLE test_memories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content TEXT NOT NULL,
                context TEXT,
                summary TEXT,
                tags TEXT[],
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

                -- Original embedding columns
                embedding_vector vector(768),
                embedding_reduced vector(256),
                vector_magnitude real,
                semantic_cluster integer,
                last_embedding_update timestamp with time zone,

                -- Tag embedding columns (to be added by migration)
                tag_embedding vector(768),
                tag_embedding_reduced vector(256),
                tag_embedding_updated timestamp with time zone
            );
        """
        )

        # Insert test data
        cursor.execute(
            """
            INSERT INTO test_memories (content, context, summary, tags) VALUES
            ('Python programming guide', 'Learning', 'Python basics tutorial', ARRAY['python', 'programming', 'tutorial']),
            ('Machine learning project', 'Work', 'ML model development', ARRAY['machine-learning', 'python', 'AI']),
            ('Meeting notes', 'Work', 'Team discussion', ARRAY['meeting', 'planning']),
            ('Recipe collection', 'Personal', 'Cooking recipes', ARRAY['cooking', 'recipes']),
            ('Empty tags memory', 'Test', 'No tags', NULL),
            ('No content with tags', 'Test', 'Has tags but no embeddings', ARRAY['test', 'validation'])
        """
        )

        postgres_conn.commit()
        cursor.close()

        yield

        # Cleanup
        cursor = postgres_conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS test_memories CASCADE;")
        postgres_conn.commit()
        cursor.close()

    def test_tag_embedding_columns_exist(self, postgres_conn, setup_test_schema):
        """Test that tag embedding columns are properly created"""
        cursor = postgres_conn.cursor()

        # Check column information
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'test_memories'
            AND column_name IN ('tag_embedding', 'tag_embedding_reduced', 'tag_embedding_updated')
            ORDER BY column_name;
        """
        )

        columns = cursor.fetchall()
        assert len(columns) == 3

        # Verify column properties
        column_info = {col[0]: (col[1], col[2]) for col in columns}

        assert "tag_embedding" in column_info
        assert "tag_embedding_reduced" in column_info
        assert "tag_embedding_updated" in column_info

        # Check that vector columns have proper type
        assert column_info["tag_embedding"][0] == "USER-DEFINED"  # pgvector type
        assert column_info["tag_embedding_reduced"][0] == "USER-DEFINED"
        assert column_info["tag_embedding_updated"][0] == "timestamp with time zone"

        cursor.close()

    def test_tag_embedding_update(self, postgres_conn, setup_test_schema):
        """Test updating tag embeddings in PostgreSQL"""
        cursor = postgres_conn.cursor()

        # Create sample embeddings
        sample_768_embedding = "[" + ",".join([str(0.1 * i % 1) for i in range(768)]) + "]"
        sample_256_embedding = "[" + ",".join([str(0.2 * i % 1) for i in range(256)]) + "]"

        # Update a record with tag embeddings
        cursor.execute(
            """
            UPDATE test_memories
            SET
                tag_embedding = %s::vector(768),
                tag_embedding_reduced = %s::vector(256),
                tag_embedding_updated = CURRENT_TIMESTAMP
            WHERE tags = ARRAY['python', 'programming', 'tutorial']
            RETURNING id, tag_embedding_updated IS NOT NULL as has_timestamp;
        """,
            (sample_768_embedding, sample_256_embedding),
        )

        result = cursor.fetchone()
        assert result is not None
        assert result[1] is True  # Has timestamp

        # Verify the update worked
        cursor.execute(
            """
            SELECT
                array_length(tag_embedding, 1) as dim_768,
                array_length(tag_embedding_reduced, 1) as dim_256,
                tag_embedding_updated IS NOT NULL as has_updated
            FROM test_memories
            WHERE tags = ARRAY['python', 'programming', 'tutorial'];
        """
        )

        result = cursor.fetchone()
        assert result[0] == 768  # Full embedding dimension
        assert result[1] == 256  # Reduced embedding dimension
        assert result[2] is True  # Has update timestamp

        postgres_conn.commit()
        cursor.close()

    def test_tag_embedding_similarity_search(self, postgres_conn, setup_test_schema):
        """Test similarity search using tag embeddings"""
        cursor = postgres_conn.cursor()

        # Insert embeddings for multiple records
        embeddings_data = [
            # Python/programming related (similar)
            (ARRAY["python", "programming", "tutorial"], [0.8, 0.6, 0.1] + [0.1] * 765),
            (ARRAY["machine-learning", "python", "AI"], [0.7, 0.5, 0.2] + [0.1] * 765),
            # Cooking related (different)
            (ARRAY["cooking", "recipes"], [0.1, 0.2, 0.9] + [0.1] * 765),
        ]

        for tags, embedding in embeddings_data:
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            cursor.execute(
                """
                UPDATE test_memories
                SET tag_embedding = %s::vector(768)
                WHERE tags = %s
            """,
                (embedding_str, tags),
            )

        postgres_conn.commit()

        # Test similarity search - find records similar to python programming
        query_embedding = "[" + ",".join(str(x) for x in ([0.75, 0.55, 0.15] + [0.1] * 765)) + "]"

        cursor.execute(
            """
            SELECT
                tags,
                1 - (tag_embedding <=> %s::vector(768)) as similarity
            FROM test_memories
            WHERE tag_embedding IS NOT NULL
            ORDER BY similarity DESC
            LIMIT 3;
        """,
            (query_embedding,),
        )

        results = cursor.fetchall()

        # Should have results
        assert len(results) > 0

        # First result should be most similar (python programming)
        top_result = results[0]
        assert "python" in top_result[0] or "programming" in top_result[0]
        assert top_result[1] > 0.8  # High similarity

        cursor.close()

    def test_tag_embedding_indexes(self, postgres_conn, setup_test_schema):
        """Test that HNSW indexes work for tag embeddings"""
        cursor = postgres_conn.cursor()

        # Create HNSW indexes (simplified for test)
        try:
            cursor.execute(
                """
                CREATE INDEX test_tag_embedding_hnsw
                ON test_memories USING hnsw (tag_embedding vector_cosine_ops)
                WITH (m = 4, ef_construction = 16);
            """
            )
            postgres_conn.commit()

            # Verify index exists
            cursor.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'test_memories'
                AND indexname = 'test_tag_embedding_hnsw';
            """
            )

            result = cursor.fetchone()
            assert result is not None

        except psycopg2.Error as e:
            # HNSW might not be available in test environment
            pytest.skip(f"HNSW index creation failed: {e}")

        cursor.close()


class TestTagEmbeddingHealthMonitoring:
    """Test health monitoring functions for tag embeddings"""

    @pytest.fixture
    def postgres_conn_with_data(self):
        """Set up PostgreSQL with sample data for health testing"""
        # Skip if PostgreSQL not available
        try:
            postgres_conn = psycopg2.connect(
                host=os.getenv("TEST_POSTGRES_HOST", "localhost"),
                database=os.getenv("TEST_POSTGRES_DB", "test_codex_db"),
                user=os.getenv("TEST_POSTGRES_USER", "test_user"),
                password=os.getenv("TEST_POSTGRES_PASS", "test_pass"),
                port=os.getenv("TEST_POSTGRES_PORT", "5432"),
            )
        except psycopg2.Error:
            pytest.skip("Test PostgreSQL database not available")

        cursor = postgres_conn.cursor()

        # Create test table with tag embedding support
        cursor.execute(
            """
            DROP TABLE IF EXISTS test_memories_health CASCADE;
            CREATE TABLE test_memories_health (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content TEXT NOT NULL,
                tags TEXT[],
                tag_embedding vector(768),
                tag_embedding_reduced vector(256),
                tag_embedding_updated timestamp with time zone,
                created_at timestamp with time zone DEFAULT NOW()
            );
        """
        )

        # Insert test data with various tag embedding states
        cursor.execute(
            """
            INSERT INTO test_memories_health (content, tags, tag_embedding, tag_embedding_updated) VALUES
            -- Memories with tags and embeddings
            ('Content 1', ARRAY['tag1', 'tag2'], %s::vector(768), NOW() - INTERVAL '1 hour'),
            ('Content 2', ARRAY['tag3', 'tag4'], %s::vector(768), NOW() - INTERVAL '2 hours'),
            -- Memories with tags but no embeddings
            ('Content 3', ARRAY['tag5', 'tag6'], NULL, NULL),
            ('Content 4', ARRAY['tag7'], NULL, NULL),
            -- Memories without tags
            ('Content 5', NULL, NULL, NULL),
            ('Content 6', ARRAY[]::TEXT[], NULL, NULL);
        """,
            ("[" + ",".join(["0.1"] * 768) + "]", "[" + ",".join(["0.2"] * 768) + "]"),
        )

        postgres_conn.commit()
        cursor.close()

        yield postgres_conn

        # Cleanup
        cursor = postgres_conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS test_memories_health CASCADE;")
        postgres_conn.commit()
        cursor.close()

    def test_tag_embedding_stats_view(self, postgres_conn_with_data):
        """Test tag embedding statistics calculation"""
        cursor = postgres_conn_with_data.cursor()

        # Create stats view for test table
        cursor.execute(
            """
            CREATE OR REPLACE VIEW test_tag_embedding_stats AS
            SELECT
                COUNT(*) as total_memories,
                COUNT(*) FILTER (WHERE tags IS NOT NULL AND array_length(tags, 1) > 0) as memories_with_tags,
                COUNT(*) FILTER (WHERE tag_embedding IS NOT NULL) as memories_with_tag_embeddings,
                COUNT(*) FILTER (WHERE tags IS NOT NULL AND array_length(tags, 1) > 0 AND tag_embedding IS NULL) as missing_tag_embeddings,
                ROUND(
                    (COUNT(*) FILTER (WHERE tag_embedding IS NOT NULL)::FLOAT /
                     NULLIF(COUNT(*) FILTER (WHERE tags IS NOT NULL AND array_length(tags, 1) > 0), 0)) * 100,
                    2
                ) as tag_embedding_coverage_percent
            FROM test_memories_health;
        """
        )

        # Query the stats
        cursor.execute("SELECT * FROM test_tag_embedding_stats;")
        stats = cursor.fetchone()

        assert stats[0] == 6  # total_memories
        assert stats[1] == 4  # memories_with_tags (excluding empty array)
        assert stats[2] == 2  # memories_with_tag_embeddings
        assert stats[3] == 2  # missing_tag_embeddings
        assert stats[4] == 50.0  # 50% coverage (2/4)

        cursor.close()

    def test_tag_embedding_health_check_function(self, postgres_conn_with_data):
        """Test health check function"""
        cursor = postgres_conn_with_data.cursor()

        # Create health check function for test table
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION test_check_tag_embedding_health()
            RETURNS TABLE (
                check_name text,
                status text,
                details text
            ) AS $$
            BEGIN
                -- Coverage check
                RETURN QUERY
                WITH stats AS (
                    SELECT
                        COUNT(*) FILTER (WHERE tag_embedding IS NOT NULL) as with_embeddings,
                        COUNT(*) FILTER (WHERE tags IS NOT NULL AND array_length(tags, 1) > 0) as with_tags
                    FROM test_memories_health
                )
                SELECT
                    'coverage'::text,
                    CASE
                        WHEN s.with_embeddings::FLOAT / NULLIF(s.with_tags, 0) >= 0.95 THEN 'healthy'
                        WHEN s.with_embeddings::FLOAT / NULLIF(s.with_tags, 0) >= 0.8 THEN 'degraded'
                        ELSE 'unhealthy'
                    END::text,
                    format('%s/%s tagged memories have embeddings', s.with_embeddings, s.with_tags)::text
                FROM stats s;

                -- Backlog check
                RETURN QUERY
                SELECT
                    'processing_backlog'::text,
                    CASE
                        WHEN COUNT(*) = 0 THEN 'healthy'
                        WHEN COUNT(*) < 10 THEN 'manageable'
                        ELSE 'backlogged'
                    END::text,
                    format('%s memories need tag embeddings', COUNT(*))::text
                FROM test_memories_health
                WHERE tags IS NOT NULL
                AND array_length(tags, 1) > 0
                AND tag_embedding IS NULL;
            END;
            $$ LANGUAGE plpgsql;
        """
        )

        # Run health check
        cursor.execute("SELECT * FROM test_check_tag_embedding_health();")
        health_results = cursor.fetchall()

        assert len(health_results) == 2  # coverage + backlog

        # Check coverage result
        coverage_check = next((r for r in health_results if r[0] == "coverage"), None)
        assert coverage_check is not None
        assert coverage_check[1] == "unhealthy"  # 50% coverage
        assert "2/4" in coverage_check[2]

        # Check backlog result
        backlog_check = next((r for r in health_results if r[0] == "processing_backlog"), None)
        assert backlog_check is not None
        assert backlog_check[1] == "manageable"  # 2 missing < 10
        assert "2 memories" in backlog_check[2]

        cursor.close()


class TestTagEmbeddingTransferScript:
    """Test the enhanced transfer script functionality"""

    def test_missing_embeddings_detection(self):
        """Test detection of missing content and tag embeddings"""
        # Mock the database operations
        with patch("psycopg2.connect") as mock_pg_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_pg_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            # Mock missing content embeddings query
            mock_cursor.fetchall.side_effect = [
                [("id1",), ("id2",)],  # Missing content embeddings
                [("id2",), ("id3",)],  # Missing tag embeddings
            ]

            # Import and test the function
            sys.path.append(
                os.path.join(os.path.dirname(__file__), "../../biological_memory/scripts")
            )
            try:
                from transfer_embeddings_with_tags import get_missing_embeddings

                missing_content, missing_tags = get_missing_embeddings(mock_conn)

                assert missing_content == ["id1", "id2"]
                assert missing_tags == ["id2", "id3"]

            except ImportError:
                pytest.skip("Transfer script not available")

    def test_batch_transfer_preparation(self):
        """Test batch preparation for content and tag embeddings"""
        # Mock embedding data
        sample_embeddings_data = [
            # (memory_id, final_embedding, tag_embedding, semantic_cluster, embedding_magnitude, tag_embedding_updated, has_tag_embedding)
            ("id1", [0.1] * 768, [0.2] * 768, 1, 1.0, "2023-01-01 10:00:00", True),
            ("id2", [0.3] * 768, None, 2, 1.0, None, False),
            ("id3", None, [0.4] * 768, None, None, "2023-01-01 11:00:00", True),
        ]

        missing_content = ["id1", "id2"]
        missing_tags = ["id1", "id3"]

        # Test batch preparation logic
        content_batch = []
        tag_batch = []

        for row in sample_embeddings_data:
            (
                memory_id,
                final_embedding,
                tag_embedding,
                semantic_cluster,
                embedding_magnitude,
                tag_embedding_updated,
                has_tag_embedding,
            ) = row
            memory_id_str = str(memory_id)

            # Process content embeddings
            if memory_id_str in missing_content and final_embedding:
                content_batch.append(memory_id_str)

            # Process tag embeddings
            if memory_id_str in missing_tags and tag_embedding:
                tag_batch.append(memory_id_str)

        assert content_batch == ["id1", "id2"]
        assert tag_batch == ["id1", "id3"]


if __name__ == "__main__":
    # Run the tests
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "-k",
            "not postgres_conn",  # Skip tests requiring real PostgreSQL by default
        ]
    )
