#!/usr/bin/env python3
"""
Optimized transfer script for embeddings from DuckDB to PostgreSQL.
Uses batch processing for 50-100x performance improvement.
"""

import logging
import os
import time
from typing import List, Optional, Tuple

import duckdb
import psycopg2
from psycopg2.extras import execute_values

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Database configurations
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/tmp/memory.duckdb")
POSTGRES_URL = os.getenv("POSTGRES_DB_URL")

# Performance settings
BATCH_SIZE = 500  # Process 500 records at a time
FETCH_SIZE = 10000  # Fetch up to 10k records from DuckDB at once


def connect_duckdb() -> duckdb.DuckDBPyConnection:
    """Connect to DuckDB database"""
    return duckdb.connect(DUCKDB_PATH)


def connect_postgres() -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database"""
    return psycopg2.connect(POSTGRES_URL)


def get_missing_embeddings(pg_conn: psycopg2.extensions.connection) -> List[str]:
    """Get list of memory IDs that don't have embeddings in PostgreSQL"""
    cursor = pg_conn.cursor()
    cursor.execute(
        """
        SELECT id::text
        FROM memories
        WHERE embedding_vector IS NULL
    """
    )
    missing_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return missing_ids


def fetch_embeddings_batch(
    duckdb_conn: duckdb.DuckDBPyConnection, memory_ids: Optional[List[str]] = None
) -> List[Tuple]:
    """Fetch embeddings from DuckDB, optionally filtered by memory IDs"""

    if memory_ids and len(memory_ids) > 0:
        # Convert list to SQL IN clause
        ids_str = ",".join(f"'{id}'" for id in memory_ids)
        query = f"""
        SELECT
            memory_id,
            final_embedding,
            semantic_cluster,
            embedding_magnitude
        FROM main.memory_embeddings
        WHERE memory_id::text IN ({ids_str})
          AND final_embedding IS NOT NULL
        """
    else:
        query = """
        SELECT
            memory_id,
            final_embedding,
            semantic_cluster,
            embedding_magnitude
        FROM main.memory_embeddings
        WHERE final_embedding IS NOT NULL
        ORDER BY created_at DESC
        """

    logger.info(f"Fetching embeddings from DuckDB...")
    start_time = time.time()
    result = duckdb_conn.execute(query).fetchall()
    fetch_time = time.time() - start_time
    logger.info(f"Fetched {len(result)} embeddings in {fetch_time:.2f} seconds")

    return result


def convert_embedding_to_pgvector(embedding: List[float]) -> str:
    """Convert Python list to pgvector format string"""
    if not embedding or len(embedding) != 768:
        raise ValueError(f"Invalid embedding length: {len(embedding) if embedding else 0}")
    return "[" + ",".join(str(float(x)) for x in embedding) + "]"


def create_reduced_embedding(embedding: List[float], target_dim: int = 256) -> str:
    """Create reduced-dimension embedding for performance"""
    if len(embedding) < target_dim:
        raise ValueError(f"Embedding too short for reduction: {len(embedding)}")
    reduced = embedding[:target_dim]
    return "[" + ",".join(str(float(x)) for x in reduced) + "]"


def transfer_embeddings_batch(
    pg_conn: psycopg2.extensions.connection, embeddings_data: List[Tuple]
) -> int:
    """Transfer embeddings to PostgreSQL using batch processing"""

    if not embeddings_data:
        logger.info("No embeddings to transfer")
        return 0

    cursor = pg_conn.cursor()
    transferred_count = 0
    total_records = len(embeddings_data)
    start_time = time.time()

    logger.info(f"Starting batch transfer of {total_records} embeddings...")

    # Process in batches
    for i in range(0, total_records, BATCH_SIZE):
        batch = embeddings_data[i : i + BATCH_SIZE]
        len(batch)

        # Prepare batch data for execute_values
        batch_data = []
        for row in batch:
            try:
                memory_id, final_embedding, semantic_cluster, embedding_magnitude = row

                # Convert embeddings
                embedding_vector = convert_embedding_to_pgvector(final_embedding)
                embedding_reduced = create_reduced_embedding(final_embedding, 256)

                # Calculate magnitude if not provided
                if embedding_magnitude is None:
                    embedding_magnitude = sum(x * x for x in final_embedding) ** 0.5

                batch_data.append(
                    (
                        embedding_vector,
                        embedding_reduced,
                        float(embedding_magnitude),
                        int(semantic_cluster) if semantic_cluster else None,
                        str(memory_id),
                    )
                )

            except Exception as e:
                logger.error(f"Error preparing embedding for {memory_id}: {str(e)}")
                continue

        if batch_data:
            # Use execute_values for batch update
            update_query = """
            UPDATE memories
            SET
                embedding_vector = data.embedding_vector::vector(768),
                embedding_reduced = data.embedding_reduced::vector(256),
                vector_magnitude = data.vector_magnitude,
                semantic_cluster = data.semantic_cluster,
                last_embedding_update = CURRENT_TIMESTAMP
            FROM (VALUES %s) AS data(embedding_vector, embedding_reduced, vector_magnitude, semantic_cluster, memory_id)
            WHERE memories.id = data.memory_id::uuid
            """

            execute_values(
                cursor,
                update_query,
                batch_data,
                template="(%s, %s, %s, %s, %s)",
                page_size=100,
            )

            transferred_count += len(batch_data)

            # Calculate and display progress
            elapsed_time = time.time() - start_time
            records_per_second = transferred_count / elapsed_time if elapsed_time > 0 else 0
            eta_seconds = (
                (total_records - transferred_count) / records_per_second
                if records_per_second > 0
                else 0
            )

            logger.info(
                f"Transferred {transferred_count}/{total_records} embeddings "
                f"({records_per_second:.1f} records/sec, ETA: {eta_seconds:.1f}s)"
            )

    # Commit all changes
    pg_conn.commit()
    cursor.close()

    total_time = time.time() - start_time
    final_rate = transferred_count / total_time if total_time > 0 else 0
    logger.info(
        f"Transfer complete! Updated {transferred_count} memories in {total_time:.2f} seconds "
        f"({final_rate:.1f} records/sec)"
    )

    return transferred_count


def main():
    """Main function to orchestrate the transfer"""

    logger.info("=== Optimized Embeddings Transfer: DuckDB → PostgreSQL ===")

    # Connect to databases
    try:
        duckdb_conn = connect_duckdb()
        pg_conn = connect_postgres()
    except Exception as e:
        logger.error(f"Failed to connect to databases: {str(e)}")
        return

    # Check for missing embeddings
    logger.info("Checking for memories without embeddings...")
    missing_ids = get_missing_embeddings(pg_conn)

    if missing_ids:
        logger.info(f"Found {len(missing_ids)} memories without embeddings")

        # Fetch only the missing embeddings from DuckDB
        embeddings_data = fetch_embeddings_batch(duckdb_conn, missing_ids)

        if embeddings_data:
            # Transfer the missing embeddings
            transferred = transfer_embeddings_batch(pg_conn, embeddings_data)
            logger.info(f"Successfully transferred {transferred} missing embeddings")
        else:
            logger.warning("No embeddings found in DuckDB for the missing memories")
    else:
        logger.info("All memories already have embeddings!")

        # Optional: Check if there are any newer embeddings in DuckDB
        logger.info("Checking for updated embeddings in DuckDB...")
        all_embeddings = fetch_embeddings_batch(duckdb_conn)

        if all_embeddings:
            response = input(
                f"Found {len(all_embeddings)} total embeddings in DuckDB. " f"Transfer all? (y/n): "
            )
            if response.lower() == "y":
                transferred = transfer_embeddings_batch(pg_conn, all_embeddings)
                logger.info(f"Successfully transferred {transferred} embeddings")

    # Cleanup
    duckdb_conn.close()
    pg_conn.close()

    logger.info("=== Transfer Complete ===")


if __name__ == "__main__":
    main()
