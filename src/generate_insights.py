#!/usr/bin/env python3
"""
MVP Insights Generator
Processes memories through Ollama and writes insights back to PostgreSQL
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List

import duckdb
import psycopg2
import requests
from psycopg2.extras import Json, register_uuid

# Register UUID adapter for psycopg2
register_uuid()

# Configuration from environment - no hardcoded credentials
POSTGRES_URL = os.getenv("POSTGRES_DB_URL")
if not POSTGRES_URL:
    raise ValueError("POSTGRES_DB_URL environment variable is required")

# Validate that default/insecure passwords are not being used
if (
    "defaultpassword" in POSTGRES_URL
    or "password" in POSTGRES_URL.split("://")[1].split("@")[0].split(":")[1]
):
    raise ValueError(
        "Default or insecure password detected. Please use a secure password in POSTGRES_DB_URL"
    )
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/Users/ladvien/biological_memory/dbs/memory.duckdb")


def call_ollama(prompt: str, temperature: float = 0.7, max_tokens: int = 150) -> str:
    """Call Ollama API to generate text"""
    try:
        print(f"  → Calling Ollama at {OLLAMA_URL} with model {OLLAMA_MODEL}")
        print(f"    Prompt length: {len(prompt)} chars, max_tokens: {max_tokens}")

        start_time = datetime.now()
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=120,  # Increased from 30 to 120 seconds for larger models
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"    Response received in {elapsed:.1f} seconds")

        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "").strip()
            print(f"    Generated {len(response_text)} chars")
            return response_text
        else:
            print(f"  ✗ Ollama API error: {response.status_code}")
            print(f"    Response: {response.text[:200]}")
            return ""
    except requests.exceptions.Timeout:
        print(f"  ✗ Ollama request timed out after 120 seconds")
        print(f"    Consider using a smaller model or increasing timeout")
        return ""
    except Exception as e:
        print(f"  ✗ Error calling Ollama: {e}")
        return ""


def extract_tags(content: str) -> List[str]:
    """Extract tags from content using Ollama"""
    prompt = f"List 3-5 keywords from: {content}\n\nKeywords:"

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

    # Try to generate insight with LLM
    insight_prompt = f"""Given this memory: {context}

What is the key insight or pattern? (1-2 sentences):"""

    insight_content = call_ollama(insight_prompt, temperature=0.7, max_tokens=100)

    # If LLM fails, use rule-based fallback
    if not insight_content or len(insight_content) < 10:
        print("  ⚠ Using fallback insight generation (LLM response empty)")

        # Create more meaningful fallback insights based on content analysis
        content_lower = content.lower()

        if "test" in content_lower or "debug" in content_lower:
            insight_content = f"Testing activity detected: {content[:80]}..."
            insight_type = "testing"
        elif "error" in content_lower or "fix" in content_lower:
            insight_content = f"Error handling or debugging pattern observed in: {content[:60]}..."
            insight_type = "debugging"
        elif "create" in content_lower or "new" in content_lower:
            insight_content = f"Creation or initialization pattern detected: {content[:70]}..."
            insight_type = "creation"
        elif "update" in content_lower or "change" in content_lower:
            insight_content = f"Modification pattern identified in: {content[:70]}..."
            insight_type = "modification"
        elif "learn" in content_lower or "understand" in content_lower:
            insight_content = f"Learning process captured: {content[:80]}..."
            insight_type = "learning"
        else:
            # Generic fallback
            insight_content = f"Memory captured: {content[:100]}..."
            insight_type = "pattern"
    else:
        # LLM succeeded, determine type from content
        insight_type = "pattern"  # Default
        if related_memories is not None and len(related_memories) > 1:
            insight_type = "connection"
        elif "learn" in content.lower() or "understand" in content.lower():
            insight_type = "learning"

    # Extract tags (with fallback if LLM fails)
    tags = extract_tags(content)
    if not tags:
        # Fallback tag extraction using simple keyword analysis
        print("  ⚠ Using fallback tag extraction")
        words = content.lower().split()
        # Filter for meaningful words (longer than 3 chars, not common words)
        common_words = {
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "from",
            "have",
            "will",
            "been",
            "after",
        }
        tags = []
        for word in words:
            clean_word = "".join(c for c in word if c.isalnum())
            if len(clean_word) > 3 and clean_word not in common_words and clean_word not in tags:
                tags.append(clean_word)
                if len(tags) >= 5:
                    break

    return {
        "content": insight_content,
        "type": insight_type,
        "tags": tags,
        "confidence": 0.7 if insight_content else 0.3,  # Lower confidence for fallback
    }


def process_memories() -> None:
    """Main processing function"""

    print("=" * 60)
    print("Starting MVP Insights Generation...")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  PostgreSQL: {POSTGRES_URL.split('@')[1] if '@' in POSTGRES_URL else POSTGRES_URL}")
    print(f"  Ollama: {OLLAMA_URL}")
    print(f"  Model: {OLLAMA_MODEL}")
    print(f"  DuckDB: {DUCKDB_PATH}")
    print()

    # Connect to DuckDB
    print("Connecting to DuckDB...")
    duck_conn = duckdb.connect(DUCKDB_PATH)

    # Attach PostgreSQL codex_db database (this is the source database for dbt models)
    duck_conn.execute(
        f"""
        ATTACH '{POSTGRES_URL}' AS codex_db (TYPE postgres)
    """
    )
    print(f"Attached codex_db from: {POSTGRES_URL}")

    # Get memories to process from PostgreSQL via DuckDB
    print("Fetching memories to process from codex_db...")
    memories_df = duck_conn.execute(
        """
        SELECT 
            id as memory_id,
            content,
            tags,
            summary,
            context
        FROM codex_db.public.memories
        WHERE content IS NOT NULL
        ORDER BY created_at DESC
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

    for idx, row in memories_df.iterrows():
        memory_id = row["memory_id"]
        content = row["content"]
        # For now, we don't have related memories in the base table
        # This would come from a more sophisticated biological memory analysis
        related_memories = []

        print(f"\n[{idx + 1}/{len(memories_df)}] Processing memory {str(memory_id)[:8]}...")
        print(
            f"  Content preview: {content[:100]}..."
            if len(content) > 100
            else f"  Content: {content}"
        )

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


def main() -> None:
    """Main entry point for the script"""
    process_memories()


if __name__ == "__main__":
    main()
