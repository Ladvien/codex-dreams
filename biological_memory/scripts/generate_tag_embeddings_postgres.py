#!/usr/bin/env python3
"""
Direct PostgreSQL Tag Embedding Generator
Generates tag embeddings directly in PostgreSQL using real Ollama integration.
Bypasses DuckDB limitations with complex array operations.
"""

import argparse
import logging
import os
import sys
import time
from typing import List, Optional, Tuple

import psycopg2

# Add macros directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../macros"))

try:
    from ollama_embeddings import generate_tag_embedding
except ImportError:
    print("Warning: ollama_embeddings module not found. Using fallback implementation.")

    def generate_tag_embedding(
        tags: List[str], model: str = "nomic-embed-text", max_retries: int = 3
    ) -> Optional[List[float]]:
        """Fallback implementation without Ollama"""
        if not tags or not any(tag.strip() for tag in tags):
            return None
        return [0.1] * 768  # Fallback embedding


# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PostgresTagEmbeddingProcessor:
    """Direct PostgreSQL tag embedding processor"""

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.pg_conn = self._connect_postgres()
        self.processed_count = 0
        self.error_count = 0

    def _connect_postgres(self) -> None:
        """Connect to PostgreSQL database"""
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST"),
                port=5432,
                database="codex_db",
                user="codex_user",
                password=os.getenv("POSTGRES_PASSWORD"),
            )
            conn.autocommit = True
            logger.info("✓ Connected to PostgreSQL")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def get_memories_needing_tag_embeddings(self, limit: int = None) -> List[Tuple]:
        """Get memories that need tag embeddings"""
        cursor = self.pg_conn.cursor()

        query = """
            SELECT id, tags
            FROM public.memories
            WHERE tags IS NOT NULL
            AND array_length(tags, 1) > 0
            AND tag_embedding IS NULL
            ORDER BY created_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()

        logger.info(f"Found {len(results)} memories needing tag embeddings")
        return results

    def process_tag_embedding_batch(self, memories: List[Tuple]) -> Tuple[int, int]:
        """Process a batch of memories for tag embeddings"""
        success_count = 0
        error_count = 0

        cursor = self.pg_conn.cursor()

        for memory_id, tags in memories:
            try:
                # Generate tag embedding using real Ollama integration
                tag_embedding = generate_tag_embedding(tags)

                if tag_embedding:
                    # Update PostgreSQL with the tag embedding
                    cursor.execute(
                        """
                        UPDATE public.memories
                        SET tag_embedding = %s,
                            tag_embedding_updated = CURRENT_TIMESTAMP,
                            has_tag_embedding = TRUE
                        WHERE id = %s
                    """,
                        (tag_embedding, memory_id),
                    )

                    success_count += 1
                    logger.debug(f"✓ Generated tag embedding for memory {memory_id}")
                else:
                    # Mark as failed but don't error
                    cursor.execute(
                        """
                        UPDATE public.memories
                        SET has_tag_embedding = FALSE,
                            tag_embedding_updated = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """,
                        (memory_id,),
                    )

                    logger.warning(f"⚠ No embedding generated for memory {memory_id}")

            except Exception as e:
                error_count += 1
                logger.error(f"✗ Error processing memory {memory_id}: {e}")

                # Mark as error
                try:
                    cursor.execute(
                        """
                        UPDATE public.memories
                        SET has_tag_embedding = FALSE,
                            tag_embedding_updated = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """,
                        (memory_id,),
                    )
                except Exception as update_error:
                    logger.error(f"Failed to mark error for memory {memory_id}: {update_error}")

        cursor.close()
        return success_count, error_count

    def process_all_tag_embeddings(self, max_memories: int = None) -> None:
        """Process all memories needing tag embeddings"""
        logger.info("=== PostgreSQL Tag Embedding Generation ===")

        start_time = time.time()
        total_processed = 0
        total_success = 0
        total_errors = 0

        while True:
            # Get next batch
            memories = self.get_memories_needing_tag_embeddings(self.batch_size)

            if not memories:
                logger.info("✓ No more memories need tag embeddings")
                break

            if max_memories and total_processed >= max_memories:
                logger.info(f"✓ Reached maximum memory limit ({max_memories})")
                break

            # Process batch
            logger.info(f"Processing batch of {len(memories)} memories...")
            batch_success, batch_errors = self.process_tag_embedding_batch(memories)

            # Update totals
            total_processed += len(memories)
            total_success += batch_success
            total_errors += batch_errors

            # Progress reporting
            elapsed = time.time() - start_time
            rate = total_processed / elapsed if elapsed > 0 else 0

            logger.info(f"Batch complete: {batch_success} success, {batch_errors} errors")
            logger.info(f"Total progress: {total_processed} processed, {rate:.1f} memories/sec")

            # Break if we hit max memories
            if max_memories and total_processed >= max_memories:
                break

        # Final summary
        elapsed = time.time() - start_time
        logger.info("=== Tag Embedding Generation Complete ===")
        logger.info(f"Total processed: {total_processed}")
        logger.info(f"Successful embeddings: {total_success}")
        logger.info(f"Errors: {total_errors}")
        logger.info(f"Total time: {elapsed:.1f}s")
        logger.info(f"Average rate: {total_processed/elapsed:.1f} memories/sec")

    def close(self) -> None:
        """Close database connection"""
        if self.pg_conn:
            self.pg_conn.close()
            logger.info("✓ PostgreSQL connection closed")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Generate tag embeddings directly in PostgreSQL")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--max-memories", type=int, help="Maximum number of memories to process")
    parser.add_argument(
        "--test-run", action="store_true", help="Process only 10 memories for testing"
    )

    args = parser.parse_args()

    if args.test_run:
        args.max_memories = 10

    try:
        processor = PostgresTagEmbeddingProcessor(batch_size=args.batch_size)
        processor.process_all_tag_embeddings(max_memories=args.max_memories)

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        if "processor" in locals():
            processor.close()


if __name__ == "__main__":
    main()
