#!/usr/bin/env python3
"""
Test script to verify connection to codex_db memories table on PostgreSQL server.
This validates that the biological memory pipeline can access the external memories data source.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
import duckdb
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/Users/ladvien/codex-dreams/.env')

def test_postgresql_connection():
    """Test direct PostgreSQL connection to codex_db"""
    print("\n" + "="*60)
    print("Testing PostgreSQL Connection to codex_db")
    print("="*60)
    
    try:
        # Connection parameters from .env
        conn_params = {
            'host': '192.168.1.104',
            'port': 5432,
            'database': 'codex_db',
            'user': 'codex_user',
            'password': 'MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a'
        }
        
        # Attempt connection
        print(f"Connecting to PostgreSQL at {conn_params['host']}:{conn_params['port']}")
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Test query on memories table
        cursor.execute("SELECT COUNT(*) FROM memories")
        count = cursor.fetchone()[0]
        print(f"✅ Successfully connected to codex_db")
        print(f"✅ Found {count} records in memories table")
        
        # Get sample records
        cursor.execute("""
            SELECT id, LEFT(content, 100) as content_preview, created_at 
            FROM memories 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        print("\nSample memories (most recent 5):")
        print("-" * 60)
        for row in cursor.fetchall():
            print(f"ID: {row[0]}")
            print(f"Content: {row[1]}...")
            print(f"Created: {row[2]}")
            print("-" * 60)
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {str(e)}")
        return False

def test_duckdb_postgres_scanner():
    """Test DuckDB postgres_scanner connection to codex_db"""
    print("\n" + "="*60)
    print("Testing DuckDB postgres_scanner Connection")
    print("="*60)
    
    try:
        # Create DuckDB connection
        conn = duckdb.connect(':memory:')
        
        # Install and load postgres_scanner
        print("Installing postgres_scanner extension...")
        conn.execute("INSTALL postgres_scanner")
        conn.execute("LOAD postgres_scanner")
        print("✅ postgres_scanner extension loaded")
        
        # Create secret for PostgreSQL connection
        print("Creating PostgreSQL connection secret...")
        conn.execute("""
            CREATE OR REPLACE SECRET codex_db_connection (
                TYPE POSTGRES,
                HOST '192.168.1.104',
                PORT 5432,
                DATABASE 'codex_db',
                USER 'codex_user',
                PASSWORD 'MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a'
            )
        """)
        print("✅ Connection secret created")
        
        # Attach PostgreSQL database
        print("Attaching PostgreSQL database...")
        conn.execute("ATTACH '' AS codex_db (TYPE POSTGRES, SECRET codex_db_connection)")
        print("✅ PostgreSQL database attached")
        
        # Query memories table through postgres_scanner
        print("Querying memories table through postgres_scanner...")
        result = conn.execute("SELECT COUNT(*) as count FROM codex_db.public.memories").fetchone()
        print(f"✅ Successfully queried memories table: {result[0]} records found")
        
        # Test staging model query pattern
        print("\nTesting staging model query pattern...")
        result = conn.execute("""
            SELECT 
                COUNT(*) as total_memories,
                MIN(created_at) as oldest_memory,
                MAX(created_at) as newest_memory
            FROM codex_db.public.memories
            WHERE content IS NOT NULL
              AND LENGTH(content) > 0
        """).fetchone()
        
        print(f"✅ Staging query successful:")
        print(f"   Total memories: {result[0]}")
        print(f"   Oldest memory: {result[1]}")
        print(f"   Newest memory: {result[2]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ DuckDB postgres_scanner test failed: {str(e)}")
        return False

def test_dbt_source_query():
    """Test the dbt source query pattern"""
    print("\n" + "="*60)
    print("Testing dbt Source Query Pattern")
    print("="*60)
    
    try:
        # This simulates what dbt would do with {{ source('codex_db', 'memories') }}
        conn = duckdb.connect(':memory:')
        
        # Setup postgres_scanner
        conn.execute("INSTALL postgres_scanner")
        conn.execute("LOAD postgres_scanner")
        conn.execute("""
            CREATE OR REPLACE SECRET codex_db_connection (
                TYPE POSTGRES,
                HOST '192.168.1.104',
                PORT 5432,
                DATABASE 'codex_db',
                USER 'codex_user',
                PASSWORD 'MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a'
            )
        """)
        conn.execute("ATTACH '' AS codex_db (TYPE POSTGRES, SECRET codex_db_connection)")
        
        # Test the staging model query
        print("Testing staging model transformation...")
        result = conn.execute("""
            WITH source_memories AS (
                SELECT 
                    id,
                    content,
                    created_at,
                    updated_at,
                    metadata
                FROM codex_db.public.memories
                LIMIT 10
            )
            SELECT 
                id AS memory_id,
                content,
                LEAST(1.0, 
                    EXP(-EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) / (7 * 24 * 3600.0))
                ) AS activation_strength,
                CASE
                    WHEN LENGTH(content) < 50 THEN 'fragment'
                    WHEN LENGTH(content) < 200 THEN 'episode'
                    WHEN LENGTH(content) < 500 THEN 'narrative'
                    ELSE 'document'
                END AS memory_type
            FROM source_memories
            WHERE content IS NOT NULL
        """).fetchall()
        
        print(f"✅ Staging transformation successful: {len(result)} records processed")
        
        if result:
            print("\nSample transformed record:")
            print(f"   Memory ID: {result[0][0]}")
            print(f"   Content: {result[0][1][:100]}...")
            print(f"   Activation Strength: {result[0][2]:.4f}")
            print(f"   Memory Type: {result[0][3]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ dbt source query test failed: {str(e)}")
        return False

def main():
    """Run all connection tests"""
    print("\n" + "#"*60)
    print("# Codex DB Memories Table Connection Test")
    print(f"# Timestamp: {datetime.now().isoformat()}")
    print("#"*60)
    
    results = []
    
    # Test 1: Direct PostgreSQL connection
    results.append(("PostgreSQL Direct Connection", test_postgresql_connection()))
    
    # Test 2: DuckDB postgres_scanner
    results.append(("DuckDB postgres_scanner", test_duckdb_postgres_scanner()))
    
    # Test 3: dbt source query pattern
    results.append(("dbt Source Query Pattern", test_dbt_source_query()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! The memories table is successfully integrated.")
        print("You can now use {{ source('codex_db', 'memories') }} in your dbt models.")
    else:
        print("\n⚠️  Some tests failed. Please check the connection configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()