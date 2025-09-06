#!/usr/bin/env python3
"""
Transfer Memory Embeddings from DuckDB to PostgreSQL with pgvector
Bridges the computational DuckDB pipeline with PostgreSQL pgvector storage
"""

import logging
import os
import time
from typing import List, Tuple

import duckdb
import psycopg2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configurations
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/tmp/memory.duckdb")
POSTGRES_URL = (
    "postgresql://codex_user:MZSfXiLr5uR3QYbRwv2vTzi22SvFkj4a@192.168.1.104:5432/codex_db"
)


def connect_duckdb() -> duckdb.DuckDBPyConnection:
    """Connect to DuckDB database"""
    return duckdb.connect(DUCKDB_PATH)


def connect_postgres() -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database"""
    return psycopg2.connect(POSTGRES_URL)


def extract_embeddings_from_duckdb(conn: duckdb.DuckDBPyConnection) -> List[Tuple]:
    """Extract embeddings data from DuckDB memory_embeddings table"""
    query = """
    SELECT 
        memory_id,
        content,
        context,
        summary,
        final_embedding,
        semantic_cluster,
        embedding_magnitude,
        created_at,
        updated_at
    FROM main.memory_embeddings 
    WHERE final_embedding IS NOT NULL 
      AND semantic_cluster IS NOT NULL
    ORDER BY updated_at DESC
    """

    logger.info("Extracting embeddings from DuckDB...")
    result = conn.execute(query).fetchall()
    logger.info(f"Extracted {len(result)} memory embeddings from DuckDB")
    return result


def convert_embedding_to_pgvector(embedding: List[float]) -> str:
    """Convert Python list to pgvector format string"""
    if not embedding or len(embedding) != 768:
        raise ValueError(f"Invalid embedding length: {len(embedding) if embedding else 0}")

    # Format as pgvector string: '[1.0,2.0,3.0,...]'
    return "[" + ",".join(str(float(x)) for x in embedding) + "]"


def create_reduced_embedding(embedding: List[float], target_dim: int = 256) -> str:
    """Create reduced-dimension embedding for performance"""
    if len(embedding) < target_dim:
        raise ValueError(f"Embedding too short for reduction: {len(embedding)}")

    reduced = embedding[:target_dim]
    return "[" + ",".join(str(float(x)) for x in reduced) + "]"


def calculate_vector_magnitude(embedding: List[float]) -> float:
    """Calculate L2 norm of embedding vector"""
    return sum(x * x for x in embedding) ** 0.5


def transfer_embeddings_to_postgres(
    duckdb_data: List[Tuple], pg_conn: psycopg2.extensions.connection
) -> int:
    """Transfer embeddings to PostgreSQL memories table"""

    cursor = pg_conn.cursor()
    transferred_count = 0

    logger.info(f"Starting transfer of {len(duckdb_data)} embeddings to PostgreSQL...")

    for row in duckdb_data:
        try:
            (
                memory_id,
                content,
                context,
                summary,
                final_embedding,
                semantic_cluster,
                embedding_magnitude,
                created_at,
                updated_at,
            ) = row

            # Convert DuckDB embedding to pgvector format
            embedding_vector = convert_embedding_to_pgvector(final_embedding)
            embedding_reduced = create_reduced_embedding(final_embedding, 256)

            # Calculate magnitude if not provided
            if embedding_magnitude is None:
                embedding_magnitude = calculate_vector_magnitude(final_embedding)

            # Update PostgreSQL memories table
            update_query = """
            UPDATE memories 
            SET 
                embedding_vector = %s::vector(768),
                embedding_reduced = %s::vector(256),
                vector_magnitude = %s,
                semantic_cluster = %s,
                last_embedding_update = CURRENT_TIMESTAMP
            WHERE id = %s::uuid
            """

            cursor.execute(
                update_query,
                (
                    embedding_vector,
                    embedding_reduced,
                    embedding_magnitude,
                    semantic_cluster,
                    str(memory_id),
                ),
            )

            transferred_count += 1

            if transferred_count % 100 == 0:
                logger.info(f"Transferred {transferred_count}/{len(duckdb_data)} embeddings...")
                pg_conn.commit()  # Commit in batches

        except Exception as e:
            logger.error(f"Error transferring memory {memory_id}: {str(e)}")
            continue

    # Final commit
    pg_conn.commit()
    cursor.close()

    logger.info(f"Transfer complete! Updated {transferred_count} memories with embeddings")
    return transferred_count


def create_pgvector_indexes(pg_conn: psycopg2.extensions.connection):
    """Create HNSW indexes for fast similarity search"""
    cursor = pg_conn.cursor()

    logger.info("Creating pgvector HNSW indexes...")

    # Create indexes for fast similarity search
    index_queries = [
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_embedding_hnsw
        ON memories USING hnsw (embedding_vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """,
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_embedding_reduced_hnsw  
        ON memories USING hnsw (embedding_reduced vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """,
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_semantic_cluster
        ON memories (semantic_cluster)
        WHERE semantic_cluster IS NOT NULL
        """,
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_vector_magnitude
        ON memories (vector_magnitude DESC)
        WHERE vector_magnitude IS NOT NULL
        """,
    ]

    for query in index_queries:
        try:
            cursor.execute(query)
            pg_conn.commit()
            logger.info("Index created successfully")
        except Exception as e:
            logger.warning(f"Index creation warning: {str(e)}")
            pg_conn.rollback()

    cursor.close()


def verify_transfer_quality(pg_conn: psycopg2.extensions.connection) -> dict:
    """Verify the quality of transferred embeddings"""
    cursor = pg_conn.cursor()

    # Quality checks
    queries = {
        "total_memories": "SELECT COUNT(*) FROM memories",
        "memories_with_embeddings": "SELECT COUNT(*) FROM memories WHERE embedding_vector IS NOT NULL",
        "memories_with_clusters": "SELECT COUNT(*) FROM memories WHERE semantic_cluster IS NOT NULL",
        "avg_vector_magnitude": "SELECT AVG(vector_magnitude) FROM memories WHERE vector_magnitude IS NOT NULL",
        "cluster_distribution": """
            SELECT semantic_cluster, COUNT(*) 
            FROM memories 
            WHERE semantic_cluster IS NOT NULL 
            GROUP BY semantic_cluster 
            ORDER BY semantic_cluster
        """,
    }

    results = {}
    for name, query in queries.items():
        cursor.execute(query)
        if name == "cluster_distribution":
            results[name] = cursor.fetchall()
        else:
            results[name] = cursor.fetchone()[0]

    cursor.close()

    # Log quality metrics
    logger.info("=== Transfer Quality Report ===")
    logger.info(f"Total memories: {results['total_memories']}")
    logger.info(f"Memories with embeddings: {results['memories_with_embeddings']}")
    logger.info(f"Memories with clusters: {results['memories_with_clusters']}")
    logger.info(f"Average vector magnitude: {results['avg_vector_magnitude']:.4f}")
    logger.info("Cluster distribution:")
    for cluster, count in results["cluster_distribution"]:
        logger.info(f"  Cluster {cluster}: {count} memories")

    return results


def main():
    """Main transfer orchestration"""
    start_time = time.time()

    logger.info("=== Starting Embeddings Transfer: DuckDB → PostgreSQL ===")

    try:
        # Connect to databases
        logger.info("Connecting to databases...")
        duckdb_conn = connect_duckdb()
        postgres_conn = connect_postgres()

        # Extract embeddings from DuckDB
        embeddings_data = extract_embeddings_from_duckdb(duckdb_conn)

        if not embeddings_data:
            logger.warning("No embeddings found in DuckDB. Run memory_embeddings model first.")
            return

        # Transfer to PostgreSQL
        transferred_count = transfer_embeddings_to_postgres(embeddings_data, postgres_conn)

        # Create performance indexes
        create_pgvector_indexes(postgres_conn)

        # Verify transfer quality
        quality_report = verify_transfer_quality(postgres_conn)

        # Close connections
        duckdb_conn.close()
        postgres_conn.close()

        elapsed_time = time.time() - start_time
        logger.info(f"=== Transfer Complete! ===")
        logger.info(f"Transferred {transferred_count} embeddings in {elapsed_time:.2f} seconds")
        logger.info(f"Embeddings now available in PostgreSQL with pgvector!")

    except Exception as e:
        logger.error(f"Transfer failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
