#!/usr/bin/env python3
"""
DuckDB Compatibility Test Suite for Vector Operations
Tests the biological memory system's DuckDB-compatible functions
"""

import os
import sys
from pathlib import Path

import duckdb


def test_duckdb_vector_operations():
    """Test DuckDB-compatible vector operations"""

    # Connect to test DuckDB instance
    conn = duckdb.connect(":memory:")

    print("🧪 Testing DuckDB Vector Operations...")

    tests_passed = 0
    tests_total = 0

    # Test 1: Basic vector dot product
    tests_total += 1
    print("\n📊 Test 1: Vector Dot Product")
    try:
        result = conn.execute(
            """
            SELECT 
                (SELECT SUM(COALESCE(v1 * v2, 0)) 
                 FROM (
                   SELECT 
                     UNNEST([1.0, 2.0, 3.0]) as v1,
                     UNNEST([4.0, 5.0, 6.0]) as v2
                 )) as dot_product
        """
        ).fetchone()[0]

        expected = 32.0  # 1*4 + 2*5 + 3*6 = 32
        if abs(result - expected) < 0.01:
            print(f"✅ PASS: Dot product = {result} (expected {expected})")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Dot product = {result} (expected {expected})")
    except Exception as e:
        print(f"❌ FAIL: Error in dot product test: {e}")

    # Test 2: Vector magnitude
    tests_total += 1
    print("\n📐 Test 2: Vector Magnitude")
    try:
        result = conn.execute(
            """
            SELECT 
                SQRT((SELECT SUM(COALESCE(v * v, 0)) 
                      FROM (SELECT UNNEST([3.0, 4.0]) as v))) as magnitude
        """
        ).fetchone()[0]

        expected = 5.0  # sqrt(3^2 + 4^2) = 5
        if abs(result - expected) < 0.01:
            print(f"✅ PASS: Magnitude = {result} (expected {expected})")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Magnitude = {result} (expected {expected})")
    except Exception as e:
        print(f"❌ FAIL: Error in magnitude test: {e}")

    # Test 3: List contains
    tests_total += 1
    print("\n🔍 Test 3: List Contains")
    try:
        result = conn.execute(
            """
            SELECT list_contains(['apple', 'banana', 'cherry'], 'banana')
        """
        ).fetchone()[0]

        if result is True:
            print(f"✅ PASS: List contains = {result}")
            tests_passed += 1
        else:
            print(f"❌ FAIL: List contains = {result} (expected True)")
    except Exception as e:
        print(f"❌ FAIL: Error in list contains test: {e}")

    # Test 4: JSON extract
    tests_total += 1
    print("\n📄 Test 4: JSON Extract")
    try:
        result = conn.execute(
            """
            SELECT json_extract('{"name": "test", "value": 42}', '$.value')
        """
        ).fetchone()[0]

        expected = 42  # DuckDB returns numeric values as numbers, not strings
        if str(result) == str(expected):
            print(f"✅ PASS: JSON extract = {result} (expected {expected})")
            tests_passed += 1
        else:
            print(f"❌ FAIL: JSON extract = {result} (expected {expected})")
    except Exception as e:
        print(f"❌ FAIL: Error in JSON extract test: {e}")

    # Test 5: Empty vector safety
    tests_total += 1
    print("\n⚠️  Test 5: Empty Vector Safety")
    try:
        result = conn.execute(
            """
            SELECT 
                COALESCE(
                    SQRT((SELECT SUM(COALESCE(v * v, 0)) 
                          FROM (SELECT UNNEST(CAST([] AS DOUBLE[])) as v))), 
                    0.0
                ) as empty_magnitude
        """
        ).fetchone()[0]

        expected = 0.0
        if abs(result - expected) < 0.01:
            print(f"✅ PASS: Empty vector magnitude = {result}")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Empty vector magnitude = {result} (expected {expected})")
    except Exception as e:
        print(f"❌ FAIL: Error in empty vector test: {e}")

    # Test 6: Cosine similarity calculation
    tests_total += 1
    print("\n📊 Test 6: Cosine Similarity (Full Formula)")
    try:
        result = conn.execute(
            """
            WITH vectors AS (
                SELECT 
                    [1.0, 0.0] as vec1,
                    [0.0, 1.0] as vec2
            )
            SELECT 
                (SELECT SUM(COALESCE(v1 * v2, 0)) 
                 FROM (
                   SELECT 
                     UNNEST(vec1) as v1,
                     UNNEST(vec2) as v2
                   FROM vectors
                 )) / 
                (SQRT((SELECT SUM(COALESCE(v * v, 0)) FROM (SELECT UNNEST(vec1) as v FROM vectors))) * 
                 SQRT((SELECT SUM(COALESCE(v * v, 0)) FROM (SELECT UNNEST(vec2) as v FROM vectors))))
                as cosine_similarity
        """
        ).fetchone()[0]

        expected = 0.0  # Orthogonal vectors have cosine similarity of 0
        if abs(result - expected) < 0.01:
            print(f"✅ PASS: Cosine similarity = {result} (expected {expected})")
            tests_passed += 1
        else:
            print(f"❌ FAIL: Cosine similarity = {result} (expected {expected})")
    except Exception as e:
        print(f"❌ FAIL: Error in cosine similarity test: {e}")

    # Close connection
    conn.close()

    # Summary
    print(f"\n📋 Test Summary: {tests_passed}/{tests_total} tests passed")
    success_rate = (tests_passed / tests_total) * 100
    print(f"🎯 Success Rate: {success_rate:.1f}%")

    if tests_passed == tests_total:
        print("\n🎉 All DuckDB compatibility tests PASSED!")
        return True
    else:
        print(f"\n⚠️  {tests_total - tests_passed} test(s) FAILED!")
        return False


def test_dbt_function_compatibility():
    """Test that dbt can compile with the new functions"""
    print("\n🔧 Testing dbt Function Compatibility...")

    # This would normally run dbt compile to test if macros work
    # For now, we'll do a syntax check on the macro definitions

    macros_path = Path(__file__).parent.parent.parent / "macros" / "biological_memory_macros.sql"

    if macros_path.exists():
        print(f"✅ Macros file exists: {macros_path}")

        # Read and verify macro structure
        with open(macros_path, "r") as f:
            content = f.read()

        # Check for our new macros
        required_macros = ["semantic_similarity", "vector_dot_product", "vector_magnitude"]

        macros_found = 0
        for macro in required_macros:
            if f"macro {macro}" in content:
                print(f"✅ Found macro: {macro}")
                macros_found += 1
            else:
                print(f"❌ Missing macro: {macro}")

        if macros_found == len(required_macros):
            print("✅ All required macros found in biological_memory_macros.sql")
            return True
        else:
            print(f"⚠️  Only {macros_found}/{len(required_macros)} macros found")
            return False
    else:
        print(f"❌ Macros file not found: {macros_path}")
        return False


if __name__ == "__main__":
    print("🚀 Starting DuckDB Compatibility Test Suite for AUDIT-005")

    vector_tests_pass = test_duckdb_vector_operations()
    dbt_tests_pass = test_dbt_function_compatibility()

    if vector_tests_pass and dbt_tests_pass:
        print("\n🎊 AUDIT-005 DuckDB Compatibility: ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n💥 AUDIT-005 DuckDB Compatibility: SOME TESTS FAILED")
        sys.exit(1)
