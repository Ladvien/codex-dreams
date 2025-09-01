#!/usr/bin/env python3
"""
MVP Insights Generator
Processes memories through Ollama and writes insights back to PostgreSQL
"""

import os
import json
import requests
import psycopg2
from psycopg2.extras import Json, register_uuid
import duckdb
from datetime import datetime
import uuid
from typing import List, Dict, Any

# Register UUID adapter for psycopg2
register_uuid()

# Configuration from environment
POSTGRES_URL = os.getenv("POSTGRES_DB_URL", "postgresql://ladvien@localhost:5432/codex")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/Users/ladvien/biological_memory/dbs/memory.duckdb")


def call_ollama(prompt: str, temperature: float = 0.7, max_tokens: int = 150) -> str:
    """Call Ollama API to generate text"""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
        else:
            print(f"Ollama API error: {response.status_code}")
            return ""
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return ""


def extract_tags(content: str) -> List[str]:
    """Extract tags from content using Ollama"""
    prompt = f"Extract 3-5 single-word tags from this text. Return only the tags separated by commas, nothing else: {content}"

    response = call_ollama(prompt, temperature=0.3, max_tokens=50)

    # Clean and split tags
    if response:
        tags = [tag.strip().lower() for tag in response.split(",")]
        # Filter out empty or too long tags
        tags = [tag for tag in tags if tag and len(tag) < 20 and tag.replace("-", "").isalnum()]
        return tags[:5]  # Max 5 tags
    return []


def generate_insight(content: str, related_memories: List[str] = None) -> Dict[str, Any]:
    """Generate an insight from memory content"""

    # Build context with related memories if available
    context = content
    if related_memories is not None and len(related_memories) > 0:
        context += (
            f"\n\nRelated memories exist with IDs: {', '.join(map(str, related_memories[:3]))}"
        )

    # Generate insight
    insight_prompt = f"""Analyze this memory and generate a brief insight about patterns, themes, or important observations.
Be concise and specific (max 2 sentences):

Memory: {context}

Insight:"""

    insight_content = call_ollama(insight_prompt, temperature=0.7, max_tokens=100)

    if not insight_content or len(insight_content) < 10:
        # Fallback to simple pattern detection
        insight_content = f"Memory recorded about: {content[:100]}..."

    # Extract tags
    tags = extract_tags(content)

    # Determine insight type based on content
    insight_type = "pattern"  # Default
    if related_memories is not None and len(related_memories) > 1:
        insight_type = "connection"
    elif "learn" in content.lower() or "understand" in content.lower():
        insight_type = "learning"

    return {
        "content": insight_content,
        "type": insight_type,
        "tags": tags,
        "confidence": 0.7,  # Default confidence for MVP
    }


def process_memories():
    """Main processing function"""

    print("Starting MVP Insights Generation...")

    # Connect to DuckDB
    duck_conn = duckdb.connect(DUCKDB_PATH)

    # Attach PostgreSQL codex_db database (this is the source database for dbt models)
    duck_conn.execute(
        f"""
        ATTACH '{POSTGRES_URL}' AS codex_db (TYPE postgres)
    """
    )
    print(f"Attached codex_db from: {POSTGRES_URL}")

    # Get memories to process
    print("Fetching memories from DuckDB view...")
    memories_df = duck_conn.execute(
        """
        SELECT 
            memory_id,
            content,
            suggested_tags,
            related_memories,
            connection_count
        FROM mvp_memory_insights
        LIMIT 10
    """
    ).fetchdf()

    print(f"Found {len(memories_df)} memories to process")

    # Connect to PostgreSQL codex_db for writing insights
    print(f"Connecting to codex_db: {POSTGRES_URL}")
    pg_conn = psycopg2.connect(POSTGRES_URL)
    pg_cursor = pg_conn.cursor()

    # Verify we're writing to the correct database
    pg_cursor.execute("SELECT current_database(), current_schema();")
    db_name, schema_name = pg_cursor.fetchone()
    print(f"Connected to database: {db_name}, schema: {schema_name}")

    insights_generated = 0

    for _, row in memories_df.iterrows():
        memory_id = row["memory_id"]
        content = row["content"]
        related_memories = (
            row["related_memories"]
            if row["related_memories"] is not None and len(row["related_memories"]) > 0
            else []
        )

        print(f"\nProcessing memory {str(memory_id)[:8]}...")

        # Generate insight
        insight = generate_insight(content, related_memories)

        if insight["content"]:
            # Prepare insight record
            insight_id = str(uuid.uuid4())

            # Insert into codex_db.public.insights table
            try:
                pg_cursor.execute(
                    """
                    INSERT INTO public.insights (
                        id, content, insight_type, confidence_score,
                        source_memory_ids, metadata, tags, tier,
                        created_at, updated_at, feedback_score, version
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO NOTHING
                """,
                    (
                        insight_id,
                        insight["content"],
                        insight["type"],
                        insight["confidence"],
                        [memory_id],  # source_memory_ids as array (keep as UUID)
                        Json(
                            {
                                "model": OLLAMA_MODEL,
                                "generated_at": datetime.now().isoformat(),
                                "pipeline": "mvp_insights",
                                "related_memories": (
                                    [str(m) for m in related_memories[:5]]
                                    if related_memories is not None and len(related_memories) > 0
                                    else []
                                ),
                            }
                        ),
                        insight["tags"],
                        "working",
                        datetime.now(),
                        datetime.now(),
                        0.0,
                        1,
                    ),
                )

                insights_generated += 1
                print(f"✓ Generated insight: {insight['content'][:80]}...")
                print(f"  Tags: {', '.join(insight['tags'])}")

            except Exception as e:
                print(f"Error inserting insight: {e}")
                pg_conn.rollback()
                continue

    # Commit changes
    pg_conn.commit()

    print(f"\n✅ Successfully generated {insights_generated} insights")

    # Clean up
    pg_cursor.close()
    pg_conn.close()
    duck_conn.close()


def main():
    """Main entry point for the script"""
    process_memories()


if __name__ == "__main__":
    main()
