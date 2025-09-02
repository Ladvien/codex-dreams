#!/usr/bin/env python3
"""
Setup DuckDB Test Database
Creates and configures a DuckDB database for testing with necessary extensions
"""

import os
import sys
from pathlib import Path

import duckdb


def setup_test_duckdb():
    """Setup DuckDB test database with extensions and PostgreSQL connection"""

    # Load test environment
    test_db_path = "./test_biological_memory.duckdb"
    test_postgres_url = os.getenv(
        "TEST_DATABASE_URL", "postgresql://codex_user:test_password@localhost:5432/test_codex_db"
    )

    print(f"Creating test DuckDB database at: {test_db_path}")

    # Remove existing test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    # Create new test database
    conn = duckdb.connect(test_db_path)

    try:
        # Install and load required extensions
        print("Installing DuckDB extensions...")
        extensions = ["postgres_scanner", "httpfs", "json"]

        for ext in extensions:
            try:
                conn.execute(f"INSTALL {ext};")
                conn.execute(f"LOAD {ext};")
                print(f"  ✓ {ext} extension loaded")
            except Exception as e:
                print(f"  ⚠ {ext} extension failed: {e}")

        # Create PostgreSQL connection using direct ATTACH
        print("\nConfiguring PostgreSQL connection...")

        # Parse connection URL for parameters
        # Format: postgresql://user:password@host:port/database
        import re

        match = re.match(r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", test_postgres_url)
        if match:
            user, password, host, port, database = match.groups()
            attach_string = (
                f"host={host} port={port} dbname={database} user={user} password={password}"
            )
        else:
            # Fallback to default test values
            attach_string = "host=localhost port=5432 dbname=test_codex_db user=codex_user password=test_password"

        # Attach PostgreSQL database
        conn.execute(f"ATTACH '{attach_string}' AS postgres_db (TYPE postgres);")
        print("  ✓ PostgreSQL database attached")

        # Verify connection by querying test data
        result = conn.execute(
            """
            SELECT COUNT(*) as count
            FROM postgres_db.public.memories
            WHERE content LIKE 'Test memory%'
        """
        ).fetchone()
        print(f"  ✓ Found {result[0]} test memories in PostgreSQL")

        # Create test performance table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS performance_benchmarks (
                benchmark_id VARCHAR PRIMARY KEY DEFAULT ('perf_' || gen_random_uuid()),
                query_type VARCHAR NOT NULL,
                query_name VARCHAR NOT NULL,
                execution_time_ms DOUBLE NOT NULL,
                rows_processed INTEGER,
                target_time_ms DOUBLE DEFAULT 50.0,
                memory_usage_mb DOUBLE,
                cpu_usage_percent DOUBLE,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        print("  ✓ Performance benchmarks table created")

        # Create LLM cache table for testing
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_cache (
                cache_key VARCHAR PRIMARY KEY,
                prompt TEXT,
                response TEXT,
                model VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        print("  ✓ LLM cache table created")

        print("\n✅ Test DuckDB database setup complete!")

    except Exception as e:
        print(f"\n❌ Error setting up test DuckDB: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Load test environment if .env.test exists
    if os.path.exists(".env.test"):
        from dotenv import load_dotenv

        load_dotenv(".env.test")
        print("Loaded .env.test configuration")

    setup_test_duckdb()
