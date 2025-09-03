#!/usr/bin/env python3
"""
Ollama Embedding Generation for Biological Memory System
Provides DuckDB UDF integration for semantic embeddings
"""

import hashlib
import logging
import os
import pickle
import time
from pathlib import Path
from typing import List, Optional, Tuple
import warnings

import duckdb
import numpy as np
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.1.110:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_DIMENSIONS = 768
CACHE_DIR = Path(os.getenv("EMBEDDING_CACHE_DIR", "./embedding_cache"))

# Create cache directory
CACHE_DIR.mkdir(exist_ok=True)


class EmbeddingCache:
    """Simple file-based cache for embeddings to avoid redundant API calls"""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir

    def _get_cache_key(self, text: str, model: str) -> str:
        """Generate cache key from text and model"""
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Retrieve cached embedding if exists"""
        try:
            cache_key = self._get_cache_key(text, model)
            cache_file = self.cache_dir / f"{cache_key}.pkl"

            if cache_file.exists():
                try:
                    with open(cache_file, "rb") as f:
                        embedding = pickle.load(f)
                        # Validate embedding format
                        if isinstance(embedding, list) and len(embedding) == EMBEDDING_DIMENSIONS:
                            return embedding
                        else:
                            logger.warning(f"Invalid cached embedding format for {cache_key[:8]}...")
                            cache_file.unlink()  # Remove corrupted cache
                except (pickle.PickleError, EOFError, ValueError) as e:
                    logger.warning(f"Cache corruption detected: {e}")
                    try:
                        cache_file.unlink()  # Remove corrupted cache
                    except OSError:
                        pass
        except Exception as e:
            logger.error(f"Unexpected error accessing cache: {e}")
        
        return None

    def set(self, text: str, model: str, embedding: List[float]):
        """Store embedding in cache"""
        try:
            # Validate input
            if not isinstance(embedding, list) or len(embedding) != EMBEDDING_DIMENSIONS:
                logger.warning(f"Invalid embedding dimensions: {len(embedding) if isinstance(embedding, list) else 'not list'}")
                return
            
            # Validate embedding values
            if not all(isinstance(x, (int, float)) and not np.isnan(x) and not np.isinf(x) for x in embedding):
                logger.warning("Invalid embedding values detected (NaN or Inf)")
                return

            cache_key = self._get_cache_key(text, model)
            cache_file = self.cache_dir / f"{cache_key}.pkl"

            # Ensure cache directory exists
            self.cache_dir.mkdir(exist_ok=True)

            # Atomic write to prevent corruption
            temp_file = cache_file.with_suffix('.tmp')
            try:
                with open(temp_file, "wb") as f:
                    pickle.dump(embedding, f)
                temp_file.replace(cache_file)  # Atomic move
                logger.debug(f"Cached embedding for {cache_key[:8]}...")
            except Exception as e:
                logger.error(f"Failed to write cache file: {e}")
                if temp_file.exists():
                    temp_file.unlink()
        except Exception as e:
            logger.error(f"Failed to cache embedding: {e}")


# Initialize cache
cache = EmbeddingCache()


def generate_embedding(text: str, model: str = EMBEDDING_MODEL, max_retries: int = 3) -> Optional[List[float]]:
    """
    Generate embedding for text using Ollama API with comprehensive error handling

    Args:
        text: Text to embed
        model: Embedding model name
        max_retries: Maximum number of retry attempts

    Returns:
        List of floats representing the embedding vector, or None if failed
    """
    if not text or not isinstance(text, str) or not text.strip():
        logger.debug("Empty or invalid text provided for embedding")
        return None

    # Sanitize and truncate text
    text = text.strip()[:8000]  # Limit text length to prevent API issues

    # Check cache first
    try:
        cached = cache.get(text, model)
        if cached is not None:
            logger.debug(f"Retrieved embedding from cache for model {model}")
            return cached
    except Exception as e:
        logger.warning(f"Cache lookup failed: {e}")

    # Try to generate embedding with retries
    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempting to generate embedding (attempt {attempt + 1}/{max_retries})")
            
            response = requests.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=30 + (attempt * 10),  # Increasing timeout on retries
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    embedding = data.get("embedding", [])

                    # Validate response format
                    if not isinstance(embedding, list):
                        logger.error(f"Invalid response format: embedding is not a list")
                        continue

                    if not embedding:
                        logger.error(f"Empty embedding received from API")
                        continue

                    # Validate dimensions and fix if necessary
                    if len(embedding) != EMBEDDING_DIMENSIONS:
                        logger.warning(f"Expected {EMBEDDING_DIMENSIONS} dimensions, got {len(embedding)}")
                        if len(embedding) < EMBEDDING_DIMENSIONS:
                            # Pad with small random values instead of zeros
                            padding = np.random.normal(0, 0.01, EMBEDDING_DIMENSIONS - len(embedding)).tolist()
                            embedding.extend(padding)
                        else:
                            embedding = embedding[:EMBEDDING_DIMENSIONS]

                    # Validate embedding values
                    if not all(isinstance(x, (int, float)) and not np.isnan(x) and not np.isinf(x) for x in embedding):
                        logger.error("Invalid embedding values detected (NaN, Inf, or non-numeric)")
                        continue

                    # Ensure embedding has reasonable magnitude
                    magnitude = np.linalg.norm(embedding)
                    if magnitude == 0:
                        logger.error("Zero-magnitude embedding received")
                        continue
                    
                    if magnitude > 100:  # Suspiciously large magnitude
                        logger.warning(f"Large embedding magnitude detected: {magnitude:.2f}")
                        # Normalize to reasonable scale
                        embedding = (np.array(embedding) / magnitude).tolist()

                    # Cache the successful result
                    try:
                        cache.set(text, model, embedding)
                    except Exception as e:
                        logger.warning(f"Failed to cache embedding: {e}")

                    logger.info(f"Successfully generated {len(embedding)}-dim embedding")
                    return embedding

                except (ValueError, KeyError, TypeError) as e:
                    logger.error(f"JSON parsing/validation error: {e}")
                    continue

            elif response.status_code == 404:
                logger.error(f"Model '{model}' not found. Available models may need to be pulled.")
                break  # Don't retry for model not found
            elif response.status_code == 503:
                logger.warning(f"Ollama service unavailable (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                logger.error(f"Ollama API error {response.status_code}: {response.text[:200]}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue

        except requests.exceptions.Timeout as e:
            logger.warning(f"Request timeout (attempt {attempt + 1}): {e}")
            continue
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error (attempt {attempt + 1}): {e}")
            continue
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception (attempt {attempt + 1}): {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")
            continue

    logger.error(f"Failed to generate embedding after {max_retries} attempts")
    return None


def combine_embeddings(
    content_emb: Optional[List[float]],
    summary_emb: Optional[List[float]],
    context_emb: Optional[List[float]],
    weights: Tuple[float, float, float] = (0.5, 0.3, 0.2),
) -> Optional[List[float]]:
    """
    Create weighted combination of embeddings

    Args:
        content_emb: Content embedding
        summary_emb: Summary embedding
        context_emb: Context embedding
        weights: Weights for (content, summary, context)

    Returns:
        Combined embedding vector
    """
    embeddings = []
    active_weights = []

    if content_emb:
        embeddings.append(np.array(content_emb))
        active_weights.append(weights[0])
    if summary_emb:
        embeddings.append(np.array(summary_emb))
        active_weights.append(weights[1])
    if context_emb:
        embeddings.append(np.array(context_emb))
        active_weights.append(weights[2])

    if not embeddings:
        return None

    # Normalize weights
    total_weight = sum(active_weights)
    normalized_weights = [w / total_weight for w in active_weights]

    # Weighted average
    combined = sum(emb * weight for emb, weight in zip(embeddings, normalized_weights))

    # L2 normalize
    norm = np.linalg.norm(combined)
    if norm > 0:
        combined = combined / norm

    return combined.tolist()


def cosine_similarity(emb1: List[float], emb2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings

    Args:
        emb1: First embedding vector
        emb2: Second embedding vector

    Returns:
        Similarity score between -1 and 1
    """
    if not emb1 or not emb2:
        return 0.0

    vec1 = np.array(emb1)
    vec2 = np.array(emb2)

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def register_duckdb_functions(conn: duckdb.DuckDBPyConnection):
    """
    Register UDFs with DuckDB for use in SQL queries

    Args:
        conn: DuckDB connection
    """
    try:
        # Register embedding generation function
        conn.create_function("ollama_embedding", generate_embedding, [str, str], "FLOAT[]")

        # Register embedding combination function
        conn.create_function(
            "combine_embeddings_udf",
            combine_embeddings,
            ["FLOAT[]", "FLOAT[]", "FLOAT[]", "FLOAT[]"],
            "FLOAT[]",
        )

        # Register cosine similarity function
        conn.create_function(
            "cosine_similarity_udf", cosine_similarity, ["FLOAT[]", "FLOAT[]"], "FLOAT"
        )

        print("✓ Ollama embedding UDFs registered with DuckDB")
    except Exception as e:
        print(f"Warning: Could not register UDFs with DuckDB: {e}")
        # Fall back to SQL-based placeholders


def test_embedding_generation():
    """Test embedding generation with sample text"""
    test_text = "The quick brown fox jumps over the lazy dog"
    print(f"Testing embedding generation for: '{test_text}'")

    embedding = generate_embedding(test_text)
    if embedding:
        print(f"✓ Generated {len(embedding)}-dimensional embedding")
        print(f"  Magnitude: {np.linalg.norm(embedding):.4f}")
        print(f"  First 5 values: {embedding[:5]}")
    else:
        print("✗ Failed to generate embedding")


if __name__ == "__main__":
    # Test embedding generation
    test_embedding_generation()

    # Example DuckDB integration
    conn = duckdb.connect()
    register_duckdb_functions(conn)

    # Test in SQL
    result = conn.execute(
        """
        SELECT ollama_embedding('test text', 'nomic-embed-text') as embedding
    """
    ).fetchone()

    if result and result[0]:
        print(f"✓ DuckDB UDF test successful: {len(result[0])}-dim embedding")
    else:
        print("✗ DuckDB UDF test failed")
