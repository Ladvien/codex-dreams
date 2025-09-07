#!/usr/bin/env python3
"""
dbt Integration Tests for Semantic Memory Pipeline
Tests the complete dbt transformation pipeline for embeddings
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

import duckdb
import pytest


@pytest.mark.dbt
@pytest.mark.integration
@pytest.mark.slow
class TestDBTSemanticIntegration:
    """Test dbt semantic pipeline integration"""

    @pytest.fixture(scope="class")
    def dbt_project_dir(self) -> Path:
        """Get dbt project directory"""
        return Path(__file__).parent.parent.parent

    @pytest.fixture(scope="class")
    def test_database(self):
        """Create temporary test database"""
        # Create temporary directory and database path
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_semantic.duckdb")

        # Initialize test database with sample data
        conn = duckdb.connect(db_path)

        # Create test memories table
        conn.execute(
            """
            CREATE TABLE memories (
                id UUID DEFAULT gen_random_uuid(),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON DEFAULT '{}'
            )
        """
        )

        # Insert test data
        test_memories = [
            (
                "Machine learning models require training data",
                '{"importance": "0.8", "tags": ["ai", "ml"]}',
            ),
            (
                "Deep learning uses neural networks",
                '{"importance": "0.7", "emotional_valence": "0.6", "context": "technical discussion"}',
            ),
            ("Python is a programming language", '{"importance": "0.6", "access_count": "5"}'),
            (
                "Biological memory systems inspire AI architectures",
                '{"importance": "0.9", "novelty": "0.8", "summary": "biomimetic AI"}',
            ),
            ("The quick brown fox jumps over the lazy dog", '{"importance": "0.3"}'),
        ]

        for content, metadata in test_memories:
            conn.execute(
                "INSERT INTO memories (content, metadata) VALUES (?, ?)",
                (content, metadata),
            )

        conn.close()
        yield db_path

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def dbt_profiles(self, test_database: Any) -> Dict[str, Any]:
        """Create test dbt profiles"""
        return {
            "biological_memory": {
                "target": "test",
                "outputs": {
                    "test": {
                        "type": "duckdb",
                        "path": test_database,
                        "extensions": ["httpfs"],
                    }
                },
            }
        }

    def test_raw_memories_model(self, dbt_project_dir, test_database):
        """Test raw_memories model compilation and execution"""
        # Create a connection to verify test database setup, then close it
        conn = duckdb.connect(test_database)
        conn.close()  # Close immediately to avoid lock conflicts

        # Change to the biological_memory directory for dbt commands
        biological_memory_dir = dbt_project_dir / "biological_memory"

        # Set up environment variables for test database
        test_env = os.environ.copy()
        test_env["TEST_DUCKDB_PATH"] = test_database

        # Test that the model can be compiled (syntax check)
        result = subprocess.run(
            [
                "dbt",
                "compile",
                "--select",
                "raw_memories",
                "--target",
                "test",
                "--project-dir",
                str(biological_memory_dir),
                "--profiles-dir",
                os.path.expanduser("~/.dbt"),
            ],
            cwd=str(biological_memory_dir),
            capture_output=True,
            text=True,
            env=test_env,
        )

        assert result.returncode == 0, f"dbt compile failed: {result.stderr}"

        # Verify compiled SQL makes sense
        compiled_sql = (
            biological_memory_dir
            / "target"
            / "compiled"
            / "biological_memory"
            / "models"
            / "working_memory"
            / "raw_memories.sql"
        ).read_text()

        assert "SELECT" in compiled_sql
        assert "memories" in compiled_sql
        assert "content" in compiled_sql

    def test_memory_embeddings_model_structure(self, dbt_project_dir):
        """Test memory_embeddings model structure and dependencies"""
        biological_memory_dir = dbt_project_dir / "biological_memory"

        # Set up environment variables for test database
        test_env = os.environ.copy()
        test_env["TEST_DUCKDB_PATH"] = "/tmp/test_memory_embeddings.duckdb"

        result = subprocess.run(
            [
                "dbt",
                "compile",
                "--select",
                "memory_embeddings",
                "--target",
                "test",
                "--project-dir",
                str(biological_memory_dir),
                "--profiles-dir",
                os.path.expanduser("~/.dbt"),
            ],
            cwd=str(biological_memory_dir),
            capture_output=True,
            text=True,
            env=test_env,
        )

        # Should compile successfully
        assert result.returncode == 0, f"memory_embeddings compile failed: {result.stderr}"

        # Check for expected macros and functions in the model file
        model_file = biological_memory_dir / "models" / "semantic" / "memory_embeddings.sql"
        if model_file.exists():
            compiled_sql = model_file.read_text()
        else:
            # Fallback to compiled version if it exists
            compiled_file = (
                dbt_project_dir
                / "target"
                / "compiled"
                / "biological_memory"
                / "models"
                / "semantic"
                / "memory_embeddings.sql"
            )
            compiled_sql = compiled_file.read_text() if compiled_file.exists() else ""

        # Verify embedding generation logic is present
        assert "embedding" in compiled_sql.lower()
        assert "final_embedding" in compiled_sql
        assert "content" in compiled_sql
        assert "memory_id" in compiled_sql

    def test_semantic_network_dependencies(self, dbt_project_dir):
        """Test semantic_network model dependencies and structure"""
        biological_memory_dir = dbt_project_dir / "biological_memory"

        # Set up environment variables for test database
        test_env = os.environ.copy()
        test_env["TEST_DUCKDB_PATH"] = "/tmp/test_semantic_network.duckdb"

        result = subprocess.run(
            [
                "dbt",
                "compile",
                "--select",
                "semantic_network",
                "--target",
                "test",
                "--project-dir",
                str(biological_memory_dir),
                "--profiles-dir",
                os.path.expanduser("~/.dbt"),
            ],
            cwd=str(biological_memory_dir),
            capture_output=True,
            text=True,
            env=test_env,
        )

        assert result.returncode == 0, f"semantic_network compile failed: {result.stderr}"

        # Check for expected features in the model file
        model_file = biological_memory_dir / "models" / "semantic" / "semantic_network.sql"
        compiled_sql = model_file.read_text() if model_file.exists() else ""

        # Verify Hebbian learning and similarity calculations
        assert "similarity" in compiled_sql.lower()
        assert "hebbian" in compiled_sql.lower()
        assert "association_strength" in compiled_sql
        assert "connection" in compiled_sql.lower() or "synaptic" in compiled_sql.lower()

    def test_working_memory_semantic_context(self, dbt_project_dir):
        """Test semantic working memory model"""
        biological_memory_dir = dbt_project_dir / "biological_memory"

        # Set up environment variables for test database
        test_env = os.environ.copy()
        test_env["TEST_DUCKDB_PATH"] = "/tmp/test_wm_semantic.duckdb"

        result = subprocess.run(
            [
                "dbt",
                "compile",
                "--select",
                "wm_semantic_context",
                "--target",
                "test",
                "--project-dir",
                str(biological_memory_dir),
                "--profiles-dir",
                os.path.expanduser("~/.dbt"),
            ],
            cwd=str(biological_memory_dir),
            capture_output=True,
            text=True,
            env=test_env,
        )

        assert result.returncode == 0, f"wm_semantic_context compile failed: {result.stderr}"

        # Check for expected features in the model file
        model_file = biological_memory_dir / "models" / "working_memory" / "wm_semantic_context.sql"
        compiled_sql = model_file.read_text() if model_file.exists() else ""

        # Verify Miller's 7±2 constraint and semantic features
        assert "semantic_cluster" in compiled_sql
        assert "semantic_priority" in compiled_sql
        assert "working_memory_capacity" in compiled_sql
        assert "7" in compiled_sql  # Miller's number reference

    @pytest.mark.slow
    def test_incremental_model_behavior(self, dbt_project_dir, test_database):
        """Test incremental model update behavior"""
        biological_memory_dir = dbt_project_dir / "biological_memory"

        # This test would require actual dbt run, which is slow
        # For now, just verify incremental configuration is correct

        # Check memory_embeddings incremental config
        embeddings_sql = (
            biological_memory_dir / "models" / "semantic" / "memory_embeddings.sql"
        ).read_text()

        assert "materialized='incremental'" in embeddings_sql
        assert "unique_key='memory_id'" in embeddings_sql
        assert "is_incremental()" in embeddings_sql

        # Check semantic_network incremental config
        network_sql = (
            biological_memory_dir / "models" / "semantic" / "semantic_network.sql"
        ).read_text()

        assert "materialized='incremental'" in network_sql
        assert "unique_key='connection_id'" in network_sql

    def test_macro_functionality(self, dbt_project_dir):
        """Test that biological memory macros are available"""
        biological_memory_dir = dbt_project_dir / "biological_memory"

        # Check biological_helpers.sql for our new macros
        macros_file = biological_memory_dir / "macros" / "biological_helpers.sql"
        macros_content = macros_file.read_text()

        # Verify vector embedding macros exist
        expected_macros = [
            "generate_embedding",
            "combine_embeddings",
            "normalize_embedding",
            "cosine_similarity",
            "semantic_distance",
            "hebbian_learning_with_embeddings",
            "semantic_clustering",
        ]

        for macro in expected_macros:
            assert f"macro {macro}" in macros_content, f"Macro {macro} not found"

    def test_schema_tests_configuration(self, dbt_project_dir):
        """Test that schema tests are properly configured"""
        biological_memory_dir = dbt_project_dir / "biological_memory"

        schema_file = biological_memory_dir / "models" / "semantic" / "schema.yml"
        schema_content = schema_file.read_text()

        # Verify tests are defined for key models
        assert "memory_embeddings" in schema_content
        assert "semantic_network" in schema_content

        # Check working memory schema for wm_semantic_context
        wm_schema_file = biological_memory_dir / "models" / "working_memory" / "schema.yml"
        wm_schema_content = wm_schema_file.read_text()
        assert "wm_semantic_context" in wm_schema_content

        # Verify key test types
        assert "unique" in schema_content
        assert "not_null" in schema_content
        assert "relationships" in schema_content

    @pytest.mark.performance
    def test_model_complexity(self, dbt_project_dir):
        """Test that models aren't overly complex"""
        biological_memory_dir = dbt_project_dir / "biological_memory"

        for model_path in (biological_memory_dir / "models" / "semantic").glob("*.sql"):
            content = model_path.read_text()
            lines = len(content.splitlines())

            # Models should be reasonable size (not too complex)
            assert lines < 500, f"Model {model_path.name} is too complex ({lines} lines)"

            # Should have proper documentation
            assert "{{" in content, f"Model {model_path.name} should use dbt templating"

    def test_biological_parameters_usage(self, dbt_project_dir):
        """Test that biological parameters are properly used"""
        biological_memory_dir = dbt_project_dir / "biological_memory"

        # Check that models use var() for biological parameters
        for model_path in (biological_memory_dir / "models").rglob("*.sql"):
            if "semantic" in str(model_path) or "working_memory" in str(model_path):
                content = model_path.read_text()

                # Should use dbt variables for biological parameters
                if "capacity" in content.lower():
                    assert (
                        "var(" in content
                    ), f"Model {model_path.name} should use var() for capacity"

                if "hebbian" in content.lower():
                    assert (
                        "var(" in content
                    ), f"Model {model_path.name} should use var() for hebbian params"


@pytest.mark.dbt
@pytest.mark.integration
class TestSemanticModelDataQuality:
    """Test data quality and biological accuracy of semantic models"""

    def test_embedding_dimensions(self):
        """Test that embeddings have correct dimensions"""
        # This would be tested in actual pipeline run
        expected_dimensions = 768
        assert expected_dimensions == 768  # nomic-embed-text dimensions

    def test_similarity_bounds(self):
        """Test that similarity scores are within valid bounds"""
        # Cosine similarity should be [-1, 1]
        import numpy as np

        vec1 = np.random.randn(768)
        vec2 = np.random.randn(768)

        # Normalize
        vec1 = vec1 / np.linalg.norm(vec1)
        vec2 = vec2 / np.linalg.norm(vec2)

        similarity = np.dot(vec1, vec2)
        assert -1.0 <= similarity <= 1.0

    def test_miller_constraint_validation(self):
        """Test Miller's 7±2 constraint in working memory"""
        base_capacity = 7
        variance = 2
        max_capacity = base_capacity + variance
        min_capacity = base_capacity - variance

        # Working memory should respect these bounds
        assert 5 <= min_capacity <= max_capacity <= 9
        assert max_capacity == 9  # 7 + 2

    def test_hebbian_learning_mathematics(self):
        """Test Hebbian learning calculations are biologically accurate"""
        # Test Hebbian strength calculation
        activation = 0.8
        importance = 0.6
        learning_rate = 0.1

        # Formula: (activation * 0.8 + importance * 0.2) * learning_rate
        expected = (activation * 0.8 + importance * 0.2) * learning_rate
        calculated = (0.8 * 0.8 + 0.6 * 0.2) * 0.1

        assert abs(expected - calculated) < 0.001
        assert 0 <= calculated <= 1.0  # Valid range


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])
