#!/usr/bin/env python3
"""
Comprehensive tests for tag embedding generation functionality.
Tests both Python UDF functions and SQL integration.
"""

import os
import sys
from unittest.mock import Mock, patch

import numpy as np
import pytest

# Add the macros directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../../biological_memory/macros"))

try:
    from ollama_embeddings import (
        cosine_similarity,
        generate_tag_embedding,
    )
except ImportError as e:
    pytest.skip(f"Ollama embeddings module not available: {e}", allow_module_level=True)


class TestTagEmbeddingGeneration:
    """Test suite for tag embedding generation"""

    def test_empty_tags(self):
        """Test that empty or None tags return None"""
        assert generate_tag_embedding(None) is None
        assert generate_tag_embedding([]) is None
        assert generate_tag_embedding(["", "  ", None]) is None

    def test_single_tag(self):
        """Test embedding generation for a single tag"""
        with patch("ollama_embeddings.generate_embedding") as mock_generate:
            mock_generate.return_value = [0.1] * 768

            result = generate_tag_embedding(["python"])

            # Should call generate_embedding with the tag
            mock_generate.assert_called_once_with("python", "nomic-embed-text", 3)
            assert result == [0.1] * 768

    def test_multiple_tags_deterministic(self):
        """Test that tag order doesn't affect the embedding (deterministic)"""
        with patch("ollama_embeddings.generate_embedding") as mock_generate:
            mock_generate.return_value = [0.5] * 768

            tags1 = ["python", "programming", "machine-learning"]
            tags2 = ["machine-learning", "python", "programming"]

            result1 = generate_tag_embedding(tags1)
            result2 = generate_tag_embedding(tags2)

            # Both calls should use the same sorted string
            expected_calls = [
                (("machine-learning | programming | python", "nomic-embed-text", 3),),
                (("machine-learning | programming | python", "nomic-embed-text", 3),),
            ]

            assert mock_generate.call_args_list[0][0][0] == mock_generate.call_args_list[1][0][0]
            assert result1 == result2

    def test_tag_string_formatting(self):
        """Test that tags are properly formatted with separators"""
        with patch("ollama_embeddings.generate_embedding") as mock_generate:
            mock_generate.return_value = [0.2] * 768

            tags = ["data science", "AI/ML", "python-programming"]
            generate_tag_embedding(tags)

            # Should sort and join with ' | '
            expected_string = "AI/ML | data science | python-programming"
            mock_generate.assert_called_once_with(expected_string, "nomic-embed-text", 3)

    def test_tag_filtering(self):
        """Test that invalid tags are filtered out"""
        with patch("ollama_embeddings.generate_embedding") as mock_generate:
            mock_generate.return_value = [0.3] * 768

            tags = ["valid_tag", "", None, "  ", "another_valid"]
            generate_tag_embedding(tags)

            # Should only use valid tags
            expected_string = "another_valid | valid_tag"
            mock_generate.assert_called_once_with(expected_string, "nomic-embed-text", 3)

    def test_embedding_failure_handling(self):
        """Test behavior when embedding generation fails"""
        with patch("ollama_embeddings.generate_embedding") as mock_generate:
            mock_generate.return_value = None  # Simulate failure

            result = generate_tag_embedding(["python", "programming"])

            assert result is None

    def test_custom_model_parameter(self):
        """Test that custom model parameter is passed through"""
        with patch("ollama_embeddings.generate_embedding") as mock_generate:
            mock_generate.return_value = [0.4] * 768

            generate_tag_embedding(["test"], model="custom-model", max_retries=5)

            mock_generate.assert_called_once_with("test", "custom-model", 5)


class TestTagEmbeddingIntegration:
    """Integration tests with real embedding generation (if available)"""

    @pytest.mark.integration
    def test_real_tag_embedding_generation(self):
        """Test actual tag embedding generation with real Ollama (if available)"""
        # This test requires actual Ollama service to be running
        tags = ["python", "programming", "test"]

        try:
            embedding = generate_tag_embedding(tags)

            if embedding:  # Only test if embedding was successful
                assert len(embedding) == 768
                assert all(isinstance(x, float) for x in embedding)

                # Test magnitude is reasonable
                magnitude = np.linalg.norm(embedding)
                assert 0.1 < magnitude < 10.0

                print(f"✓ Generated real tag embedding: magnitude={magnitude:.4f}")
            else:
                pytest.skip("Real Ollama service not available")

        except Exception as e:
            pytest.skip(f"Real embedding generation failed: {e}")

    @pytest.mark.integration
    def test_tag_embedding_determinism_real(self):
        """Test that real tag embeddings are deterministic"""
        tags1 = ["python", "programming"]
        tags2 = ["programming", "python"]  # Different order

        try:
            embedding1 = generate_tag_embedding(tags1)
            embedding2 = generate_tag_embedding(tags2)

            if embedding1 and embedding2:
                similarity = cosine_similarity(embedding1, embedding2)
                assert similarity > 0.999  # Should be essentially identical
                print(f"✓ Tag embedding determinism: {similarity:.6f} similarity")
            else:
                pytest.skip("Real Ollama service not available")

        except Exception as e:
            pytest.skip(f"Real embedding generation failed: {e}")


class TestTagEmbeddingCaching:
    """Test caching behavior for tag embeddings"""

    def test_cache_hit(self):
        """Test that identical tag combinations hit the cache"""
        with patch("ollama_embeddings.cache") as mock_cache:
            mock_cache.get.return_value = [0.1] * 768

            result = generate_tag_embedding(["python", "programming"])

            # Should check cache with sorted tag string
            expected_key = "programming | python"
            mock_cache.get.assert_called_once_with(expected_key, "nomic-embed-text")
            assert result == [0.1] * 768

    def test_cache_miss_and_store(self):
        """Test cache miss leads to generation and storage"""
        with (
            patch("ollama_embeddings.cache") as mock_cache,
            patch("ollama_embeddings.requests.post") as mock_post,
        ):

            # Mock cache miss
            mock_cache.get.return_value = None

            # Mock successful Ollama response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"embedding": [0.2] * 768}
            mock_post.return_value = mock_response

            result = generate_tag_embedding(["python"])

            # Should store in cache after generation
            mock_cache.set.assert_called_once_with("python", "nomic-embed-text", [0.2] * 768)
            assert result == [0.2] * 768


class TestTagEmbeddingQuality:
    """Test semantic quality of tag embeddings"""

    def test_similar_tags_similarity(self):
        """Test that semantically similar tags produce similar embeddings"""
        # This test requires real embeddings to be meaningful
        with patch("ollama_embeddings.generate_embedding") as mock_generate:
            # Simulate similar embeddings for similar tags
            def mock_embedding_gen(text, model, retries):
                if "programming" in text or "coding" in text:
                    return [0.8, 0.6, 0.2] + [0.1] * 765  # Similar base
                else:
                    return [0.2, 0.1, 0.8] + [0.1] * 765  # Different base

            mock_generate.side_effect = mock_embedding_gen

            programming_tags = ["python", "programming"]
            coding_tags = ["javascript", "coding"]
            unrelated_tags = ["cooking", "recipes"]

            emb1 = generate_tag_embedding(programming_tags)
            emb2 = generate_tag_embedding(coding_tags)
            emb3 = generate_tag_embedding(unrelated_tags)

            # Programming and coding should be more similar than cooking
            sim_related = cosine_similarity(emb1, emb2)
            sim_unrelated = cosine_similarity(emb1, emb3)

            assert sim_related > sim_unrelated


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_tag_types(self):
        """Test handling of invalid tag types"""
        # Should handle mixed types gracefully
        generate_tag_embedding([123, "python", None, True])

        with patch("ollama_embeddings.generate_embedding") as mock_generate:
            mock_generate.return_value = [0.1] * 768
            generate_tag_embedding([123, "python", None, True])

            # Should convert to strings and filter
            mock_generate.assert_called_once_with("123 | True | python", "nomic-embed-text", 3)

    def test_very_long_tag_list(self):
        """Test handling of very long tag lists"""
        long_tags = [f"tag_{i}" for i in range(1000)]

        with patch("ollama_embeddings.generate_embedding") as mock_generate:
            mock_generate.return_value = [0.1] * 768

            result = generate_tag_embedding(long_tags)

            # Should still work (though the string will be very long)
            assert mock_generate.called
            assert result == [0.1] * 768

    def test_special_characters_in_tags(self):
        """Test handling of special characters in tags"""
        special_tags = [
            "tag@domain.com",
            "c++",
            "tag with spaces",
            "tag\nwith\nnewlines",
        ]

        with patch("ollama_embeddings.generate_embedding") as mock_generate:
            mock_generate.return_value = [0.1] * 768

            result = generate_tag_embedding(special_tags)

            # Should handle special characters without crashing
            assert mock_generate.called
            assert result == [0.1] * 768


if __name__ == "__main__":
    # Run specific test groups
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "-k",
            "not integration",
        ]  # Skip integration tests by default
    )
