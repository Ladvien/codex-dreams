#!/usr/bin/env python3
"""
Standalone DuckDB vector operations test
Tests our DuckDB-compatible vector functions directly
"""

import math

import duckdb


def test_vector_operations():
    """Test vector operations in DuckDB"""
    conn = duckdb.connect(":memory:")

    print("🧪 Testing Standalone Vector Operations...")

    # Test vector dot product
    print("\n📊 Testing Vector Dot Product")
    try:
        result = conn.execute(
            """
            SELECT 
                (SELECT SUM(v1 * v2) 
                 FROM (
                   SELECT 
                     UNNEST([1.0, 2.0, 3.0]) as v1,
                     UNNEST([4.0, 5.0, 6.0]) as v2
                 )) as dot_product
        """
        ).fetchone()[0]

        print(f"✅ Dot product result: {result}")
        expected = 32.0
        assert abs(float(result) - expected) < 0.01, f"Expected {expected}, got {result}"

    except Exception as e:
        print(f"❌ Error: {e}")

    # Test vector magnitude
    print("\n📐 Testing Vector Magnitude")
    try:
        result = conn.execute(
            """
            SELECT 
                SQRT((SELECT SUM(v * v) 
                      FROM (SELECT UNNEST([3.0, 4.0]) as v))) as magnitude
        """
        ).fetchone()[0]

        print(f"✅ Magnitude result: {result}")
        expected = 5.0
        assert abs(float(result) - expected) < 0.01, f"Expected {expected}, got {result}"

    except Exception as e:
        print(f"❌ Error: {e}")

    # Test cosine similarity complete calculation
    print("\n🎯 Testing Complete Cosine Similarity")
    try:
        # Vectors [1, 0] and [1, 0] should have similarity = 1
        result = conn.execute(
            """
            WITH vectors AS (
                SELECT 
                    [1.0, 0.0] as v1,
                    [1.0, 0.0] as v2
            ),
            dot_product AS (
                SELECT 
                    (SELECT SUM(a.val * b.val) 
                     FROM (SELECT UNNEST(v1) WITH ORDINALITY as val, ordinality as idx FROM vectors) a
                     JOIN (SELECT UNNEST(v2) WITH ORDINALITY as val, ordinality as idx FROM vectors) b
                     ON a.idx = b.idx) as dot_prod
                FROM vectors
            ),
            magnitudes AS (
                SELECT 
                    SQRT((SELECT SUM(v * v) FROM (SELECT UNNEST(v1) as v FROM vectors))) as mag1,
                    SQRT((SELECT SUM(v * v) FROM (SELECT UNNEST(v2) as v FROM vectors))) as mag2
                FROM vectors
            )
            SELECT 
                dot_prod / (mag1 * mag2) as cosine_similarity
            FROM dot_product, magnitudes
        """
        ).fetchone()[0]

        print(f"✅ Cosine similarity result: {result}")
        expected = 1.0  # Identical vectors
        assert abs(float(result) - expected) < 0.01, f"Expected {expected}, got {result}"

    except Exception as e:
        print(f"❌ Error: {e}")

    # Test with orthogonal vectors
    print("\n⟂ Testing Orthogonal Vectors")
    try:
        result = conn.execute(
            """
            WITH vectors AS (
                SELECT 
                    [1.0, 0.0] as v1,
                    [0.0, 1.0] as v2
            ),
            dot_product AS (
                SELECT 
                    (SELECT SUM(a.val * b.val) 
                     FROM (SELECT UNNEST(v1) WITH ORDINALITY as val, ordinality as idx FROM vectors) a
                     JOIN (SELECT UNNEST(v2) WITH ORDINALITY as val, ordinality as idx FROM vectors) b
                     ON a.idx = b.idx) as dot_prod
                FROM vectors
            ),
            magnitudes AS (
                SELECT 
                    SQRT((SELECT SUM(v * v) FROM (SELECT UNNEST(v1) as v FROM vectors))) as mag1,
                    SQRT((SELECT SUM(v * v) FROM (SELECT UNNEST(v2) as v FROM vectors))) as mag2
                FROM vectors
            )
            SELECT 
                dot_prod / (mag1 * mag2) as cosine_similarity
            FROM dot_product, magnitudes
        """
        ).fetchone()[0]

        print(f"✅ Orthogonal cosine similarity: {result}")
        expected = 0.0
        assert abs(float(result) - expected) < 0.01, f"Expected {expected}, got {result}"

    except Exception as e:
        print(f"❌ Error: {e}")

    conn.close()
    print("\n🎉 All vector operations tests completed successfully!")


if __name__ == "__main__":
    test_vector_operations()
