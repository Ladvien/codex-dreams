#!/usr/bin/env python3
"""
Enhanced transfer script for embeddings from DuckDB to PostgreSQL.
Includes support for tag embeddings alongside content embeddings.
Uses batch processing for optimal performance.
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
POSTGRES_URL = os.getenv(
    "POSTGRES_DB_URL",
    os.getenv("POSTGRES_DB_URL"),
)

# Performance settings
BATCH_SIZE = 500  # Process 500 records at a time
FETCH_SIZE = 10000  # Fetch up to 10k records from DuckDB at once


def connect_duckdb() -> duckdb.DuckDBPyConnection:
    """Connect to DuckDB database"""
    return duckdb.connect(DUCKDB_PATH)


def connect_postgres() -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database"""
    return psycopg2.connect(POSTGRES_URL)


def get_missing_embeddings(
    pg_conn: psycopg2.extensions.connection,
) -> Tuple[List[str], List[str]]:
    """Get list of memory IDs that don't have content or tag embeddings in PostgreSQL"""
    cursor = pg_conn.cursor()

    # Get memories missing content embeddings
    cursor.execute(
        """
        SELECT id::text
        FROM memories
        WHERE embedding_vector IS NULL
    """
    )
    missing_content = [row[0] for row in cursor.fetchall()]

    # Get memories with tags but missing tag embeddings
    cursor.execute(
        """
        SELECT id::text
        FROM memories
        WHERE tags IS NOT NULL
        AND array_length(tags, 1) > 0
        AND tag_embedding IS NULL
    """
    )
    missing_tags = [row[0] for row in cursor.fetchall()]

    cursor.close()
    return missing_content, missing_tags


def fetch_embeddings_batch(
    duckdb_conn: duckdb.DuckDBPyConnection,
    content_ids: Optional[List[str]] = None,
    tag_ids: Optional[List[str]] = None,
) -> List[Tuple]:
    """Fetch embeddings from DuckDB, optionally filtered by memory IDs"""

    # Determine which IDs to fetch (union of content and tag missing IDs)
    all_ids = set()
    if content_ids:
        all_ids.update(content_ids)
    if tag_ids:
        all_ids.update(tag_ids)

    if all_ids:
        # Convert set to SQL IN clause
        ids_str = ",".join(f"'{id}'" for id in all_ids)
        query = f"""
        SELECT
            memory_id,
            final_embedding,
            tag_embedding,
            semantic_cluster,
            embedding_magnitude,
            tag_embedding_updated,
            has_tag_embedding
        FROM main.memory_embeddings
        WHERE memory_id::text IN ({ids_str})
        ORDER BY created_at DESC
        """
    else:
        query = """
        SELECT
            memory_id,
            final_embedding,
            tag_embedding,
            semantic_cluster,
            embedding_magnitude,
            tag_embedding_updated,
            has_tag_embedding
        FROM main.memory_embeddings
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
    if not embedding:
        return None
    if len(embedding) != 768:
        raise ValueError(f"Invalid embedding length: {len(embedding)}")
    return "[" + ",".join(str(float(x)) for x in embedding) + "]"


def create_reduced_embedding(embedding: List[float], target_dim: int = 256) -> str:
    """Create reduced-dimension embedding for performance"""
    if not embedding or len(embedding) < target_dim:
        return None
    reduced = embedding[:target_dim]
    return "[" + ",".join(str(float(x)) for x in reduced) + "]"


def transfer_embeddings_batch(
    pg_conn: psycopg2.extensions.connection,
    embeddings_data: List[Tuple],
    missing_content: List[str],
    missing_tags: List[str],
) -> Tuple[int, int]:
    """Transfer embeddings to PostgreSQL using batch processing"""

    if not embeddings_data:
        logger.info("No embeddings to transfer")
        return 0, 0

    cursor = pg_conn.cursor()
    content_updated = 0
    tag_updated = 0
    total_records = len(embeddings_data)
    start_time = time.time()

    logger.info(f"Starting batch transfer of {total_records} embeddings...")
    logger.info(f"  Content embeddings needed: {len(missing_content)}")
    logger.info(f"  Tag embeddings needed: {len(missing_tags)}")

    # Process in batches
    for i in range(0, total_records, BATCH_SIZE):
        batch = embeddings_data[i : i + BATCH_SIZE]
        len(batch)

        # Separate batches for content and tag updates
        content_batch = []
        tag_batch = []

        for row in batch:
            try:
                (
                    memory_id,
                    final_embedding,
                    tag_embedding,
                    semantic_cluster,
                    embedding_magnitude,
                    tag_embedding_updated,
                    has_tag_embedding,
                ) = row
                memory_id_str = str(memory_id)

                # Process content embeddings
                if memory_id_str in missing_content and final_embedding:
                    embedding_vector = convert_embedding_to_pgvector(final_embedding)
                    embedding_reduced = create_reduced_embedding(final_embedding, 256)

                    # Calculate magnitude if not provided
                    if embedding_magnitude is None:
                        embedding_magnitude = sum(x * x for x in final_embedding) ** 0.5

                    content_batch.append(
                        (
                            embedding_vector,
                            embedding_reduced,
                            float(embedding_magnitude),
                            int(semantic_cluster) if semantic_cluster else None,
                            memory_id_str,
                        )
                    )

                # Process tag embeddings
                if memory_id_str in missing_tags and tag_embedding:
                    tag_vector = convert_embedding_to_pgvector(tag_embedding)
                    tag_reduced = create_reduced_embedding(tag_embedding, 256)

                    tag_batch.append(
                        (tag_vector, tag_reduced, tag_embedding_updated, memory_id_str)
                    )

            except Exception as e:
                logger.error(f"Error preparing embeddings for {memory_id}: {str(e)}")
                continue

        # Update content embeddings
        if content_batch:
            content_query = """
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
                content_query,
                content_batch,
                template="(%s, %s, %s, %s, %s)",
                page_size=100,
            )
            content_updated += len(content_batch)

        # Update tag embeddings
        if tag_batch:
            tag_query = """
            UPDATE memories
            SET
                tag_embedding = data.tag_embedding::vector(768),
                tag_embedding_reduced = data.tag_embedding_reduced::vector(256),
                tag_embedding_updated = COALESCE(data.tag_embedding_updated, CURRENT_TIMESTAMP)
            FROM (VALUES %s) AS data(tag_embedding, tag_embedding_reduced, tag_embedding_updated, memory_id)
            WHERE memories.id = data.memory_id::uuid
            """

            execute_values(cursor, tag_query, tag_batch, template="(%s, %s, %s, %s)", page_size=100)
            tag_updated += len(tag_batch)

        # Calculate and display progress
        elapsed_time = time.time() - start_time
        total_processed = content_updated + tag_updated
        records_per_second = total_processed / elapsed_time if elapsed_time > 0 else 0

        if i > 0 and i % (BATCH_SIZE * 5) == 0:  # Log every 5 batches
            logger.info(
                f"Progress: {i}/{total_records} records processed "
                f"({records_per_second:.1f} records/sec) "
                f"Content: {content_updated}, Tags: {tag_updated}"
            )

    # Commit all changes
    pg_conn.commit()
    cursor.close()

    total_time = time.time() - start_time
    final_rate = (content_updated + tag_updated) / total_time if total_time > 0 else 0
    logger.info(
        f"Transfer complete! Content: {content_updated}, Tags: {tag_updated} "
        f"in {total_time:.2f} seconds ({final_rate:.1f} records/sec)"
    )

    return content_updated, tag_updated


def check_tag_embedding_health(pg_conn: psycopg2.extensions.connection) -> None:
    """Check and report tag embedding health"""
    cursor = pg_conn.cursor()

    cursor.execute("SELECT * FROM public.tag_embedding_stats")
    stats = cursor.fetchone()

    if stats:
        total, with_tags, with_embeddings, missing, coverage, earliest, latest = stats
        logger.info("=== Tag Embedding Health ===")
        logger.info(f"Total memories: {total}")
        logger.info(f"Memories with tags: {with_tags}")
        logger.info(f"Tag embeddings coverage: {coverage}% ({with_embeddings}/{with_tags})")
        logger.info(f"Missing tag embeddings: {missing}")
        logger.info(f"Earliest tag embedding: {earliest}")
        logger.info(f"Latest tag embedding: {latest}")

        # Get detailed health check
        cursor.execute("SELECT * FROM public.check_tag_embedding_health()")
        health_checks = cursor.fetchall()
        for check_name, status, details in health_checks:
            logger.info(f"{check_name}: {status} - {details}")

    cursor.close()


def main():
    """Main function to orchestrate the transfer"""

    logger.info("=== Enhanced Embeddings Transfer: DuckDB → PostgreSQL ===")

    # Connect to databases
    try:
        duckdb_conn = connect_duckdb()
        pg_conn = connect_postgres()
    except Exception as e:
        logger.error(f"Failed to connect to databases: {str(e)}")
        return

    # Check for missing embeddings
    logger.info("Checking for memories without embeddings...")
    missing_content, missing_tags = get_missing_embeddings(pg_conn)

    logger.info(f"Missing content embeddings: {len(missing_content)}")
    logger.info(f"Missing tag embeddings: {len(missing_tags)}")

    if missing_content or missing_tags:
        # Fetch embeddings from DuckDB
        embeddings_data = fetch_embeddings_batch(duckdb_conn, missing_content, missing_tags)

        if embeddings_data:
            # Transfer the missing embeddings
            content_count, tag_count = transfer_embeddings_batch(
                pg_conn, embeddings_data, missing_content, missing_tags
            )
            logger.info(
                f"Successfully transferred {content_count} content and {tag_count} tag embeddings"
            )
        else:
            logger.warning("No embeddings found in DuckDB for the missing memories")
    else:
        logger.info("All memories have their required embeddings!")

        # Optional: Check if there are any newer embeddings in DuckDB
        logger.info("Checking for updated embeddings in DuckDB...")
        all_embeddings = fetch_embeddings_batch(duckdb_conn)

        if all_embeddings:
            response = input(
                f"Found {len(all_embeddings)} total embeddings in DuckDB. " f"Transfer all? (y/n): "
            )
            if response.lower() == "y":
                # Get all IDs for a full refresh
                cursor = pg_conn.cursor()
                cursor.execute("SELECT id::text FROM memories")
                all_ids = [row[0] for row in cursor.fetchall()]
                cursor.close()

                content_count, tag_count = transfer_embeddings_batch(
                    pg_conn, all_embeddings, all_ids, all_ids
                )
                logger.info(
                    f"Successfully transferred {content_count} content and {tag_count} tag embeddings"
                )

    # Show tag embedding health
    check_tag_embedding_health(pg_conn)

    # Cleanup
    duckdb_conn.close()
    pg_conn.close()

    logger.info("=== Transfer Complete ===")


if __name__ == "__main__":
    main()
