#!/usr/bin/env python3
"""
Cleanup script for test schemas in PostgreSQL.
This script removes any test schemas created during testing that weren't properly cleaned up.
"""

import os
import psycopg2
import logging
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_postgres_connection():
    """Get PostgreSQL connection from environment or use defaults."""
    postgres_url = os.getenv('POSTGRES_DB_URL', '')
    
    if postgres_url:
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', postgres_url)
        if match:
            return psycopg2.connect(
                user=match.group(1),
                password=match.group(2),
                host=match.group(3),
                port=int(match.group(4)),
                database=match.group(5)
            )
    
    # Fallback to localhost
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'codex_db'),
        user=os.getenv('POSTGRES_USER', os.getenv('USER')),
        password=os.getenv('POSTGRES_PASSWORD', '')
    )


def list_test_schemas(conn) -> List[str]:
    """List all test schemas in the database."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name LIKE 'test_schema_%'
            ORDER BY schema_name
        """)
        return [row[0] for row in cur.fetchall()]


def drop_test_schemas(conn, schemas: List[str], dry_run: bool = False):
    """Drop the specified test schemas."""
    if not schemas:
        logger.info("No test schemas found to clean up.")
        return
    
    logger.info(f"Found {len(schemas)} test schema(s) to clean up:")
    for schema in schemas:
        logger.info(f"  - {schema}")
    
    if dry_run:
        logger.info("DRY RUN: Would drop these schemas but not executing.")
        return
    
    with conn.cursor() as cur:
        for schema in schemas:
            try:
                logger.info(f"Dropping schema: {schema}")
                cur.execute(f"DROP SCHEMA {schema} CASCADE")
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to drop schema {schema}: {e}")
                conn.rollback()


def cleanup_test_schemas(dry_run: bool = False):
    """Main cleanup function."""
    try:
        logger.info("Connecting to PostgreSQL...")
        conn = get_postgres_connection()
        
        logger.info("Searching for test schemas...")
        test_schemas = list_test_schemas(conn)
        
        drop_test_schemas(conn, test_schemas, dry_run)
        
        conn.close()
        logger.info("Cleanup complete.")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up test schemas from PostgreSQL")
    parser.add_argument('--dry-run', action='store_true', 
                        help="Show what would be deleted without actually deleting")
    args = parser.parse_args()
    
    cleanup_test_schemas(dry_run=args.dry_run)