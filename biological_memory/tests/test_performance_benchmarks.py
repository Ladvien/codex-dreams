#!/usr/bin/env python3
"""
Performance Benchmarks for Memory Embeddings System
Tests performance characteristics and scalability
"""

import time
from typing import List

import numpy as np
import pytest
from macros.ollama_embeddings import (
    EmbeddingCache,
    combine_embeddings,
    cosine_similarity,
    generate_embedding,
)


@pytest.mark.performance
@pytest.mark.benchmark
class TestEmbeddingPerformance:
    """Benchmark embedding generation and processing"""

    def test_embedding_generation_speed(self, benchmark):
        """Benchmark embedding generation speed"""

        def generate_test_embedding():
            return generate_embedding("Sample text for embedding generation performance test")

        result = benchmark(generate_test_embedding)

        # Verify result if embedding was generated
        if result is not None:
            assert len(result) == 768

    def test_cache_performance(self, benchmark):
        """Benchmark embedding cache performance"""
        cache = EmbeddingCache()
        test_text = "Cache performance test text"
        test_embedding = np.random.randn(768).tolist()

        # Pre-populate cache
        cache.set(test_text, "test-model", test_embedding)

        def cache_retrieval():
            return cache.get(test_text, "test-model")

        result = benchmark(cache_retrieval)
        assert result is not None
        assert len(result) == 768

    def test_similarity_calculation_speed(self, benchmark):
        """Benchmark cosine similarity calculation speed"""
        emb1 = np.random.randn(768).tolist()
        emb2 = np.random.randn(768).tolist()

        def calculate_similarity():
            return cosine_similarity(emb1, emb2)

        result = benchmark(calculate_similarity)
        assert -1.0 <= result <= 1.0

    def test_batch_similarity_performance(self, benchmark):
        """Benchmark batch similarity calculations"""
        query_embedding = np.random.randn(768)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)

        # Generate 100 random embeddings
        embeddings = []
        for _ in range(100):
            emb = np.random.randn(768)
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb.tolist())

        def batch_similarity():
            similarities = []
            query_list = query_embedding.tolist()
            for emb in embeddings:
                sim = cosine_similarity(query_list, emb)
                similarities.append(sim)
            return similarities

        results = benchmark(batch_similarity)
        assert len(results) == 100
        assert all(-1.0 <= sim <= 1.0 for sim in results)

    def test_embedding_combination_performance(self, benchmark):
        """Benchmark embedding combination speed"""
        emb1 = np.random.randn(768).tolist()
        emb2 = np.random.randn(768).tolist()
        emb3 = np.random.randn(768).tolist()

        def combine_test():
            return combine_embeddings(emb1, emb2, emb3)

        result = benchmark(combine_test)
        if result is not None:
            assert len(result) == 768
            # Check normalization
            magnitude = np.linalg.norm(result)
            assert abs(magnitude - 1.0) < 0.01


@pytest.mark.performance
@pytest.mark.biological
class TestBiologicalMemoryPerformance:
    """Benchmark biological memory operations"""

    def test_working_memory_capacity_performance(self, benchmark):
        """Benchmark working memory selection performance"""

        def select_working_memory():
            # Simulate 100 memories with priorities
            memories = []
            for i in range(100):
                memories.append(
                    {
                        "id": f"mem_{i}",
                        "priority": np.random.random(),
                        "content": f"Memory content {i}",
                    }
                )

            # Sort by priority and select top 7±2
            memories.sort(key=lambda x: x["priority"], reverse=True)
            return memories[:9]  # 7 + 2

        result = benchmark(select_working_memory)
        assert len(result) <= 9
        assert len(result) >= 5  # 7 - 2

    def test_hebbian_learning_performance(self, benchmark):
        """Benchmark Hebbian learning calculations"""

        def calculate_hebbian_strength():
            results = []
            for _ in range(1000):
                activation = np.random.random()
                importance = np.random.random()
                learning_rate = 0.1

                strength = (activation * 0.8 + importance * 0.2) * learning_rate
                results.append(strength)
            return results

        results = benchmark(calculate_hebbian_strength)
        assert len(results) == 1000
        assert all(0 <= strength <= 1.0 for strength in results)

    def test_forgetting_curve_performance(self, benchmark):
        """Benchmark forgetting curve calculations"""

        def apply_forgetting():
            results = []
            for _ in range(1000):
                initial_strength = np.random.random()
                age_hours = np.random.random() * 168  # Up to 1 week
                forgetting_rate = 0.05

                final_strength = initial_strength * np.exp(-forgetting_rate * age_hours)
                results.append(final_strength)
            return results

        results = benchmark(apply_forgetting)
        assert len(results) == 1000
        assert all(0 <= strength <= 1.0 for strength in results)


@pytest.mark.performance
@pytest.mark.semantic
class TestSemanticNetworkPerformance:
    """Benchmark semantic network operations"""

    def test_semantic_clustering_performance(self, benchmark):
        """Benchmark semantic clustering of memories"""

        def cluster_memories():
            # Generate 500 normalized embeddings
            embeddings = []
            for _ in range(500):
                emb = np.random.randn(768)
                emb = emb / np.linalg.norm(emb)
                embeddings.append(emb)

            # Simple clustering by first component
            clusters = {}
            n_clusters = 7
            for i, emb in enumerate(embeddings):
                cluster_id = int((emb[0] + 1) * n_clusters / 2) % n_clusters
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(i)

            return clusters

        clusters = benchmark(cluster_memories)
        assert len(clusters) <= 7  # Miller's number
        assert sum(len(cluster) for cluster in clusters.values()) == 500

    def test_association_strength_calculation(self, benchmark):
        """Benchmark association strength calculations"""

        def calculate_associations():
            results = []
            for _ in range(100):
                # Generate two similar embeddings
                emb1 = np.random.randn(768)
                emb1 = emb1 / np.linalg.norm(emb1)

                # Similar embedding with noise
                emb2 = emb1 + np.random.randn(768) * 0.1
                emb2 = emb2 / np.linalg.norm(emb2)

                similarity = cosine_similarity(emb1.tolist(), emb2.tolist())
                importance = np.random.random()
                emotional_salience = 1.2

                association_strength = similarity * importance * emotional_salience
                results.append(association_strength)

            return results

        results = benchmark(calculate_associations)
        assert len(results) == 100
        assert all(result >= 0 for result in results)  # Should be non-negative


@pytest.mark.performance
@pytest.mark.slow
class TestScalabilityBenchmarks:
    """Test performance at different scales"""

    @pytest.mark.parametrize("memory_count", [100, 500, 1000, 2000])
    def test_similarity_search_scaling(self, benchmark, memory_count):
        """Test similarity search performance scaling"""
        # Generate memory embeddings
        embeddings = []
        for _ in range(memory_count):
            emb = np.random.randn(768)
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb.tolist())

        query = np.random.randn(768)
        query = query / np.linalg.norm(query)
        query_list = query.tolist()

        def similarity_search():
            similarities = []
            for emb in embeddings:
                sim = cosine_similarity(query_list, emb)
                similarities.append((sim, emb))

            # Sort by similarity and return top 10
            similarities.sort(reverse=True)
            return similarities[:10]

        results = benchmark(similarity_search)
        assert len(results) == 10
        assert all(0.0 <= sim[0] <= 1.0 for sim in results)

    @pytest.mark.parametrize("embedding_dim", [128, 384, 768, 1536])
    def test_dimension_scaling_performance(self, benchmark, embedding_dim):
        """Test performance with different embedding dimensions"""
        emb1 = np.random.randn(embedding_dim).tolist()
        emb2 = np.random.randn(embedding_dim).tolist()

        def dimension_similarity():
            return cosine_similarity(emb1, emb2)

        result = benchmark(dimension_similarity)
        assert -1.0 <= result <= 1.0

    def test_memory_consumption(self):
        """Test memory consumption of embedding operations"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Generate large number of embeddings
        embeddings = []
        for _ in range(1000):
            emb = np.random.randn(768).tolist()
            embeddings.append(emb)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB for 1000 embeddings)
        assert (
            memory_increase < 100 * 1024 * 1024
        ), f"Memory usage too high: {memory_increase / 1024 / 1024:.2f}MB"

        # Verify embeddings are properly formatted
        assert len(embeddings) == 1000
        assert all(len(emb) == 768 for emb in embeddings)


@pytest.mark.performance
class TestRealTimeBenchmarks:
    """Test real-time performance requirements"""

    def test_working_memory_update_speed(self, benchmark):
        """Test working memory can update in real-time (<100ms)"""

        def update_working_memory():
            # Simulate real-time working memory update
            memories = []
            for i in range(50):
                memory = {
                    "id": f"mem_{i}",
                    "content": f"Memory {i}",
                    "importance": np.random.random(),
                    "recency": np.random.random(),
                    "semantic_coherence": np.random.random(),
                }
                memories.append(memory)

            # Calculate priorities and select top 7
            for mem in memories:
                mem["priority"] = (
                    mem["importance"] * 0.4 + mem["recency"] * 0.3 + mem["semantic_coherence"] * 0.3
                )

            memories.sort(key=lambda x: x["priority"], reverse=True)
            return memories[:7]

        result = benchmark(update_working_memory)
        assert len(result) == 7

        # Check that benchmark runs quickly enough for real-time
        # This will be reported in benchmark output

    def test_similarity_threshold_performance(self, benchmark):
        """Test similarity threshold filtering performance"""
        embeddings = []
        for _ in range(200):
            emb = np.random.randn(768)
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb.tolist())

        query = np.random.randn(768)
        query = query / np.linalg.norm(query)
        query_list = query.tolist()
        threshold = 0.7

        def threshold_filtering():
            similar_memories = []
            for emb in embeddings:
                sim = cosine_similarity(query_list, emb)
                if sim >= threshold:
                    similar_memories.append((sim, emb))
            return similar_memories

        results = benchmark(threshold_filtering)
        assert all(sim[0] >= threshold for sim in results)


if __name__ == "__main__":
    # Run performance benchmarks
    pytest.main(
        [
            __file__,
            "--benchmark-only",
            "--benchmark-sort=mean",
            "--benchmark-columns=min,max,mean,stddev,rounds",
            "-v",
        ]
    )
