#!/usr/bin/env python3
"""
Real Embeddings Validation Test Suite
Tests for validating 384-dimension real semantic embeddings vs MD5 placeholders

This test suite validates:
- nomic-embed-text integration with Ollama
- 384-dimension embedding generation
- Semantic similarity accuracy vs MD5 hashes  
- Performance improvements over hash-based vectors
- Matryoshka representation learning dimension flexibility
"""

import pytest
import json
import numpy as np
import duckdb
import logging
from pathlib import Path
import time
from typing import List, Dict, Tuple
import sys
import os

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from llm_integration_service import initialize_llm_service, get_llm_service


class TestRealEmbeddingsValidation:
    """Test suite for real semantic embeddings validation"""
    
    @pytest.fixture(scope="class")
    def duckdb_connection(self):
        """Create DuckDB connection with embedding functions registered"""
        conn = duckdb.connect(":memory:")
        
        # Register LLM functions including embeddings
        try:
            from llm_integration_service import register_llm_functions
            initialize_llm_service()
            register_llm_functions(conn)
        except Exception as e:
            pytest.skip(f"Could not register LLM functions: {e}")
        
        yield conn
        conn.close()
    
    @pytest.fixture
    def test_concepts(self) -> List[str]:
        """Sample concepts for semantic similarity testing"""
        return [
            "artificial intelligence",
            "machine learning", 
            "neural networks",
            "data science",
            "cooking recipes",
            "automotive repair", 
            "financial planning",
            "medical diagnosis",
            "software engineering",
            "biological memory"
        ]
    
    def test_nomic_embed_text_integration(self, duckdb_connection):
        """Test nomic-embed-text model integration and response format"""
        # Test basic embedding generation
        result = duckdb_connection.execute("""
            SELECT llm_generate_embedding('artificial intelligence', 'nomic-embed-text', 384) as embedding
        """).fetchone()
        
        assert result is not None, "Embedding generation returned no result"
        embedding = result[0]
        
        assert isinstance(embedding, list), f"Expected list, got {type(embedding)}"
        assert len(embedding) == 384, f"Expected 384 dimensions, got {len(embedding)}"
        assert all(isinstance(x, (int, float)) for x in embedding), "All embedding values should be numeric"
        
        # Test that embedding is not all zeros (indicates successful generation)
        non_zero_count = sum(1 for x in embedding if abs(x) > 1e-6)
        assert non_zero_count > 0, "Embedding should not be all zeros"
        
    def test_embedding_dimension_flexibility(self, duckdb_connection):
        """Test Matryoshka representation learning dimension flexibility"""
        test_text = "biological memory processing system"
        
        # Test different dimensions
        dimensions = [384, 256, 128, 64]
        embeddings = {}
        
        for dim in dimensions:
            result = duckdb_connection.execute("""
                SELECT llm_generate_embedding(?, 'nomic-embed-text', ?) as embedding
            """, [test_text, dim]).fetchone()
            
            assert result is not None
            embedding = result[0]
            assert len(embedding) == dim, f"Expected {dim} dimensions, got {len(embedding)}"
            embeddings[dim] = embedding
            
        # Verify that smaller dimensions are truncations of larger ones
        # (Due to Matryoshka representation learning)
        assert embeddings[64] == embeddings[384][:64], "64-dim should be truncation of 384-dim"
        assert embeddings[128] == embeddings[384][:128], "128-dim should be truncation of 384-dim"
        assert embeddings[256] == embeddings[384][:256], "256-dim should be truncation of 384-dim"
    
    def test_semantic_similarity_accuracy(self, duckdb_connection, test_concepts):
        """Test real embeddings produce meaningful semantic similarities"""
        # Generate embeddings for all test concepts
        embeddings = {}
        for concept in test_concepts:
            result = duckdb_connection.execute("""
                SELECT llm_generate_embedding(?, 'nomic-embed-text', 384) as embedding
            """, [concept]).fetchone()
            
            assert result is not None
            embeddings[concept] = np.array(result[0])
        
        # Calculate cosine similarities
        similarities = {}
        for i, concept1 in enumerate(test_concepts):
            for j, concept2 in enumerate(test_concepts[i+1:], i+1):
                vec1 = embeddings[concept1]
                vec2 = embeddings[concept2]
                
                # Cosine similarity
                cosine_sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                similarities[(concept1, concept2)] = cosine_sim
        
        # Verify semantic relationships
        # AI-related concepts should be more similar to each other
        ai_concepts = ["artificial intelligence", "machine learning", "neural networks", "data science"]
        non_ai_concepts = ["cooking recipes", "automotive repair", "financial planning"]
        
        # AI concept pairs should have higher similarity than AI-nonAI pairs
        ai_ai_similarities = []
        ai_nonai_similarities = []
        
        for (c1, c2), sim in similarities.items():
            if c1 in ai_concepts and c2 in ai_concepts:
                ai_ai_similarities.append(sim)
            elif (c1 in ai_concepts and c2 in non_ai_concepts) or (c1 in non_ai_concepts and c2 in ai_concepts):
                ai_nonai_similarities.append(sim)
        
        if ai_ai_similarities and ai_nonai_similarities:
            avg_ai_ai = np.mean(ai_ai_similarities)
            avg_ai_nonai = np.mean(ai_nonai_similarities)
            
            assert avg_ai_ai > avg_ai_nonai, f"AI concepts should be more similar to each other (AI-AI: {avg_ai_ai:.3f}, AI-nonAI: {avg_ai_nonai:.3f})"
    
    def test_md5_vs_real_embeddings_comparison(self, duckdb_connection):
        """Compare MD5 hash-based fake embeddings vs real embeddings"""
        test_concepts = ["machine learning", "artificial intelligence", "data science"]
        
        # Generate both types of embeddings
        md5_embeddings = {}
        real_embeddings = {}
        
        for concept in test_concepts:
            # Generate MD5-based fake embedding (placeholder)
            md5_hash_values = []
            for i in range(384):
                hash_val = hash(f"{concept}{i}") % 10000 / 10000.0
                md5_hash_values.append(abs(hash_val))
            md5_embeddings[concept] = np.array(md5_hash_values)
            
            # Generate real embedding
            result = duckdb_connection.execute("""
                SELECT llm_generate_embedding(?, 'nomic-embed-text', 384) as embedding
            """, [concept]).fetchone()
            real_embeddings[concept] = np.array(result[0])
        
        # Calculate similarities
        concepts_list = list(test_concepts)
        md5_similarities = []
        real_similarities = []
        
        for i in range(len(concepts_list)):
            for j in range(i+1, len(concepts_list)):
                c1, c2 = concepts_list[i], concepts_list[j]
                
                # MD5 similarity
                md5_sim = np.dot(md5_embeddings[c1], md5_embeddings[c2]) / (
                    np.linalg.norm(md5_embeddings[c1]) * np.linalg.norm(md5_embeddings[c2])
                )
                md5_similarities.append(md5_sim)
                
                # Real similarity
                real_sim = np.dot(real_embeddings[c1], real_embeddings[c2]) / (
                    np.linalg.norm(real_embeddings[c1]) * np.linalg.norm(real_embeddings[c2])
                )
                real_similarities.append(real_sim)
        
        # Real embeddings should show higher similarity for related concepts
        # MD5 similarities should be essentially random
        real_avg = np.mean(real_similarities)
        md5_avg = np.mean(md5_similarities) 
        
        # Real embeddings should capture semantic relationships better
        # For related concepts (ML, AI, Data Science), real similarity should be higher
        assert real_avg > 0.5, f"Related concepts should have high real similarity: {real_avg:.3f}"
        assert abs(md5_avg) < 0.3, f"MD5 similarities should be near random (close to 0): {md5_avg:.3f}"
        
        logging.info(f"Real embedding average similarity: {real_avg:.3f}")
        logging.info(f"MD5 hash average similarity: {md5_avg:.3f}")
        logging.info(f"Semantic improvement ratio: {real_avg / max(abs(md5_avg), 0.001):.2f}x")
    
    def test_embedding_performance(self, duckdb_connection):
        """Test embedding generation performance"""
        test_text = "This is a test text for performance measurement of embedding generation"
        
        # Measure embedding generation time
        start_time = time.time()
        result = duckdb_connection.execute("""
            SELECT llm_generate_embedding(?, 'nomic-embed-text', 384) as embedding
        """, [test_text]).fetchone()
        end_time = time.time()
        
        generation_time = end_time - start_time
        
        assert result is not None
        assert len(result[0]) == 384
        
        # Performance should be reasonable (under 5 seconds for single embedding)
        assert generation_time < 5.0, f"Embedding generation took {generation_time:.2f}s (should be under 5s)"
        
        logging.info(f"Embedding generation time: {generation_time:.3f}s")
    
    def test_embedding_consistency(self, duckdb_connection):
        """Test that embeddings are consistent across multiple calls"""
        test_text = "consistent embedding test"
        
        # Generate same embedding multiple times
        embeddings = []
        for _ in range(3):
            result = duckdb_connection.execute("""
                SELECT llm_generate_embedding(?, 'nomic-embed-text', 384) as embedding
            """, [test_text]).fetchone()
            embeddings.append(np.array(result[0]))
        
        # Embeddings should be identical or very similar (allowing for small numerical differences)
        for i in range(1, len(embeddings)):
            similarity = np.dot(embeddings[0], embeddings[i]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[i])
            )
            assert similarity > 0.99, f"Embeddings should be consistent across calls: {similarity:.4f}"
    
    def test_null_and_empty_text_handling(self, duckdb_connection):
        """Test handling of null and empty text inputs"""
        # Test empty string
        result = duckdb_connection.execute("""
            SELECT llm_generate_embedding('', 'nomic-embed-text', 384) as embedding
        """).fetchone()
        
        assert result is not None
        assert len(result[0]) == 384
        
        # Test very short text
        result = duckdb_connection.execute("""
            SELECT llm_generate_embedding('a', 'nomic-embed-text', 384) as embedding
        """).fetchone()
        
        assert result is not None
        assert len(result[0]) == 384
    
    @pytest.mark.skipif(not os.getenv('OLLAMA_URL'), reason="OLLAMA_URL not set")
    def test_ollama_service_health(self):
        """Test Ollama service connectivity and nomic-embed-text model availability"""
        service = get_llm_service()
        assert service is not None, "LLM service should be initialized"
        
        health = service.health_check()
        assert health['status'] == 'healthy', f"Ollama service should be healthy: {health}"
        
        # Check if nomic-embed-text model is available
        # Note: This might not work with all Ollama versions
        logging.info(f"Ollama service health: {json.dumps(health, indent=2)}")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])