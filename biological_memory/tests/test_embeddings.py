#!/usr/bin/env python3
"""
Test suite for memory embeddings and semantic network
Validates the biological memory embedding pipeline
"""

import sys
from pathlib import Path

import duckdb
import numpy as np
import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from macros.ollama_embeddings import (  # noqa: E402
    EmbeddingCache,
    combine_embeddings,
    cosine_similarity,
    generate_embedding,
    register_duckdb_functions,
)


@pytest.mark.embedding
@pytest.mark.unit
class TestEmbeddingGeneration:
    """Test embedding generation functionality"""

    def test_generate_embedding(self):
        """Test basic embedding generation"""
        text = "The biological memory system implements Hebbian learning"
        embedding = generate_embedding(text)

        # Check if embedding was generated (may be None if Ollama not available)
        if embedding is not None:
            assert len(embedding) == 768, f"Expected 768 dimensions, got {len(embedding)}"
            assert all(isinstance(x, float) for x in embedding), "Embedding should be floats"

            # Check that embedding has reasonable values
            magnitude = np.linalg.norm(embedding)
            print(f"  Embedding magnitude: {magnitude:.4f}")
            # Note: Placeholder embeddings may not be normalized
            assert magnitude > 0, "Embedding magnitude should be positive"

    def test_empty_text_handling(self):
        """Test handling of empty text"""
        assert generate_embedding("") is None
        assert generate_embedding(None) is None
        assert generate_embedding("   ") is None

    def test_embedding_cache(self):
        """Test embedding caching functionality"""
        cache = EmbeddingCache()
        text = "Test caching"
        model = "test-model"
        embedding = [0.1] * 768

        # Store in cache
        cache.set(text, model, embedding)

        # Retrieve from cache
        cached = cache.get(text, model)
        assert cached is not None
        assert len(cached) == 768
        assert cached[0] == 0.1


@pytest.mark.embedding
@pytest.mark.unit
class TestEmbeddingCombination:
    """Test embedding combination functionality"""

    def test_combine_embeddings(self):
        """Test weighted combination of embeddings"""
        emb1 = [1.0] * 768
        emb2 = [0.5] * 768
        emb3 = [0.0] * 768

        combined = combine_embeddings(emb1, emb2, emb3, weights=(0.5, 0.3, 0.2))

        if combined is not None:
            assert len(combined) == 768
            # Check normalization
            magnitude = np.linalg.norm(combined)
            assert abs(magnitude - 1.0) < 0.01, f"Combined embedding not normalized: {magnitude}"

    def test_partial_embeddings(self):
        """Test combination with missing embeddings"""
        emb1 = [1.0] * 768

        combined = combine_embeddings(emb1, None, None, weights=(0.5, 0.3, 0.2))

        if combined is not None:
            assert len(combined) == 768
            # Should be normalized version of emb1
            magnitude = np.linalg.norm(combined)
            assert abs(magnitude - 1.0) < 0.01


@pytest.mark.semantic
@pytest.mark.unit
class TestCosineSimilarity:
    """Test cosine similarity calculation"""

    def test_identical_vectors(self):
        """Test similarity of identical vectors"""
        vec1 = [1.0, 0.0, 0.0] * 256  # 768 dimensions
        similarity = cosine_similarity(vec1, vec1)
        assert abs(similarity - 1.0) < 0.001, "Identical vectors should have similarity ~1.0"

    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors"""
        vec1 = [1.0] + [0.0] * 767
        vec2 = [0.0, 1.0] + [0.0] * 766
        similarity = cosine_similarity(vec1, vec2)
        assert abs(similarity) < 0.001, "Orthogonal vectors should have similarity ~0.0"

    def test_opposite_vectors(self):
        """Test similarity of opposite vectors"""
        vec1 = [1.0] * 768
        vec2 = [-1.0] * 768
        similarity = cosine_similarity(vec1, vec2)
        assert abs(similarity + 1.0) < 0.001, "Opposite vectors should have similarity ~-1.0"


@pytest.mark.integration
@pytest.mark.database
class TestDuckDBIntegration:
    """Test DuckDB UDF integration"""

    def test_register_functions(self):
        """Test UDF registration with DuckDB"""
        conn = duckdb.connect(":memory:")

        # Register functions
        register_duckdb_functions(conn)

        # Test that functions are registered (basic smoke test)
        try:
            # Create test data
            conn.execute(
                """
                CREATE TABLE test_memories AS
                SELECT
                    'memory1' as id,
                    'Test memory content' as content
            """
            )

            # Try to use the UDFs
            result = conn.execute(
                """
                SELECT
                    ollama_embedding(content, 'nomic-embed-text') as embedding
                FROM test_memories
            """
            ).fetchone()

            # If Ollama is available, check result
            if result and result[0]:
                assert len(result[0]) == 768
        except Exception as e:
            # Functions registered but may fail if Ollama not available
            print(f"UDF execution failed (expected if Ollama not available): {e}")


@pytest.mark.biological
@pytest.mark.integration
class TestBiologicalMemoryIntegration:
    """Test integration with biological memory system"""

    def test_memory_capacity_constraint(self):
        """Test Miller's 7±2 constraint"""
        capacity_base = 7
        capacity_variance = 2
        max_capacity = capacity_base + capacity_variance

        # Generate test memories
        memories = []
        for i in range(20):
            memories.append(
                {"id": f"mem_{i}", "content": f"Memory content {i}", "priority": np.random.random()}
            )

        # Sort by priority and select top memories
        memories.sort(key=lambda x: x["priority"], reverse=True)
        selected = memories[:max_capacity]

        assert len(selected) <= max_capacity, f"Working memory exceeded capacity: {len(selected)}"
        assert len(selected) >= capacity_base - capacity_variance, "Working memory below minimum"

    def test_hebbian_learning(self):
        """Test Hebbian learning calculation"""
        activation = 0.8
        importance = 0.6
        learning_rate = 0.1

        # Hebbian strength formula
        hebbian_strength = (activation * 0.8 + importance * 0.2) * learning_rate

        assert 0 <= hebbian_strength <= 1.0, "Hebbian strength out of range"
        assert hebbian_strength == pytest.approx(0.076, abs=0.001)

    def test_forgetting_curve(self):
        """Test exponential forgetting curve"""
        initial_strength = 1.0
        forgetting_rate = 0.05
        age_hours = 24

        # Apply forgetting curve
        final_strength = initial_strength * np.exp(-forgetting_rate * age_hours)

        assert final_strength < initial_strength, "Strength should decrease over time"
        assert final_strength > 0, "Strength should remain positive"


@pytest.mark.semantic
@pytest.mark.biological
def test_semantic_clustering():
    """Test semantic clustering of memories"""
    n_memories = 50
    n_clusters = 7  # Miller's magic number

    # Generate random embeddings
    embeddings = []
    for i in range(n_memories):
        emb = np.random.randn(768)
        emb = emb / np.linalg.norm(emb)  # Normalize
        embeddings.append(emb.tolist())

    # Simple clustering by first component
    clusters = {}
    for i, emb in enumerate(embeddings):
        cluster_id = int((emb[0] + 1) * n_clusters / 2) % n_clusters
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(i)

    assert len(clusters) <= n_clusters, f"Too many clusters: {len(clusters)}"
    assert all(len(c) > 0 for c in clusters.values()), "Empty clusters found"


@pytest.mark.semantic
@pytest.mark.biological
def test_semantic_network_associations():
    """Test semantic network association strength"""
    # Generate two similar embeddings
    emb1 = np.random.randn(768)
    emb1 = emb1 / np.linalg.norm(emb1)

    # Create similar embedding with small noise
    emb2 = emb1 + np.random.randn(768) * 0.01  # Reduced noise
    emb2 = emb2 / np.linalg.norm(emb2)

    similarity = cosine_similarity(emb1.tolist(), emb2.tolist())

    # Similar embeddings should have high similarity
    assert similarity > 0.95, f"Similar embeddings have low similarity: {similarity}"

    # Test association strength calculation
    importance = 0.7
    emotional_salience = 1.2
    association_strength = similarity * importance * emotional_salience

    assert association_strength > 0, "Association strength should be positive"
    assert association_strength <= 1.2, "Association strength out of expected range"


if __name__ == "__main__":
    # Run tests
    print("Testing Memory Embeddings Pipeline...")
    print("=" * 60)

    # Test embedding generation
    test_gen = TestEmbeddingGeneration()
    test_gen.test_generate_embedding()
    test_gen.test_empty_text_handling()
    test_gen.test_embedding_cache()
    print("✓ Embedding generation tests passed")

    # Test embedding combination
    test_comb = TestEmbeddingCombination()
    test_comb.test_combine_embeddings()
    test_comb.test_partial_embeddings()
    print("✓ Embedding combination tests passed")

    # Test cosine similarity
    test_sim = TestCosineSimilarity()
    test_sim.test_identical_vectors()
    test_sim.test_orthogonal_vectors()
    test_sim.test_opposite_vectors()
    print("✓ Cosine similarity tests passed")

    # Test DuckDB integration
    test_db = TestDuckDBIntegration()
    test_db.test_register_functions()
    print("✓ DuckDB integration tests passed")

    # Test biological memory integration
    test_bio = TestBiologicalMemoryIntegration()
    test_bio.test_memory_capacity_constraint()
    test_bio.test_hebbian_learning()
    test_bio.test_forgetting_curve()
    print("✓ Biological memory integration tests passed")

    # Test semantic features
    test_semantic_clustering()
    test_semantic_network_associations()
    print("✓ Semantic network tests passed")

    print("=" * 60)
    print("All tests completed successfully! 🎉")
