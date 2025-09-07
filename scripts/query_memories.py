#!/usr/bin/env python3
"""
Query tool for accessing biological memory system results.
Provides easy access to stored memories and insights.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

import psycopg2

# Database configuration from environment
DATABASE_URL = os.getenv("POSTGRES_DB_URL")
if not DATABASE_URL:
    raise ValueError("POSTGRES_DB_URL environment variable is required")


def connect_db():
    """Connect to PostgreSQL database."""
    return psycopg2.connect(DATABASE_URL)


def get_recent_memories(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent memories from the database."""
    conn = connect_db()
    cur = conn.cursor()

    query = """
    SELECT
        id,
        content,
        summary,
        context,
        tags,
        created_at,
        updated_at
    FROM memories
    ORDER BY created_at DESC
    LIMIT %s
    """

    cur.execute(query, (limit,))
    columns = [desc[0] for desc in cur.description]
    results = []

    for row in cur.fetchall():
        memory = dict(zip(columns, row))
        # Convert datetime objects to strings
        if memory.get("created_at"):
            memory["created_at"] = memory["created_at"].isoformat()
        if memory.get("updated_at"):
            memory["updated_at"] = memory["updated_at"].isoformat()
        results.append(memory)

    cur.close()
    conn.close()
    return results


def search_memories(search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search memories by content or summary."""
    conn = connect_db()
    cur = conn.cursor()

    query = """
    SELECT
        id,
        content,
        summary,
        context,
        tags,
        created_at
    FROM memories
    WHERE
        content ILIKE %s OR
        summary ILIKE %s OR
        context ILIKE %s
    ORDER BY created_at DESC
    LIMIT %s
    """

    search_pattern = f"%{search_term}%"
    cur.execute(query, (search_pattern, search_pattern, search_pattern, limit))

    columns = [desc[0] for desc in cur.description]
    results = []

    for row in cur.fetchall():
        memory = dict(zip(columns, row))
        if memory.get("created_at"):
            memory["created_at"] = memory["created_at"].isoformat()
        results.append(memory)

    cur.close()
    conn.close()
    return results


def get_memory_stats() -> Dict[str, Any]:
    """Get statistics about stored memories."""
    conn = connect_db()
    cur = conn.cursor()

    stats = {}

    # Total count
    cur.execute("SELECT COUNT(*) FROM memories")
    stats["total_memories"] = cur.fetchone()[0]

    # Date range
    cur.execute("SELECT MIN(created_at), MAX(created_at) FROM memories")
    min_date, max_date = cur.fetchone()
    stats["oldest_memory"] = min_date.isoformat() if min_date else None
    stats["newest_memory"] = max_date.isoformat() if max_date else None

    # Database size
    cur.execute("SELECT pg_size_pretty(pg_database_size('codex_db'))")
    stats["database_size"] = cur.fetchone()[0]

    # Top tags
    cur.execute(
        """
        SELECT tag, COUNT(*) as count
        FROM memories, unnest(tags) as tag
        GROUP BY tag
        ORDER BY count DESC
        LIMIT 10
    """
    )
    stats["top_tags"] = [{"tag": row[0], "count": row[1]} for row in cur.fetchall()]

    cur.close()
    conn.close()
    return stats


def export_memories_to_file(output_file: str = "memories_export.json"):
    """Export all memories to a JSON file."""
    memories = get_recent_memories(limit=1000)  # Get up to 1000 recent memories

    with open(output_file, "w") as f:
        json.dump(
            {
                "export_date": datetime.now().isoformat(),
                "total_memories": len(memories),
                "memories": memories,
            },
            f,
            indent=2,
        )

    print(f"Exported {len(memories)} memories to {output_file}")
    return output_file


def get_dreams_stats() -> Dict[str, Any]:
    """Get statistics from dreams schema."""
    conn = connect_db()
    cur = conn.cursor()

    stats = {}

    # Get memory stage counts
    cur.execute("SELECT * FROM dreams.get_memory_stats()")
    stats["stages"] = []
    for row in cur.fetchall():
        stats["stages"].append(
            {
                "stage": row[0],
                "count": row[1],
                "oldest": row[2].isoformat() if row[2] else None,
                "newest": row[3].isoformat() if row[3] else None,
                "avg_importance": float(row[4]) if row[4] else 0,
            }
        )

    # Get insights count
    cur.execute("SELECT COUNT(*), insight_type FROM dreams.memory_insights GROUP BY insight_type")
    stats["insights"] = {row[1]: row[0] for row in cur.fetchall()}

    # Get semantic network stats
    cur.execute(
        """
        SELECT COUNT(*) as associations,
               AVG(association_strength) as avg_strength,
               MAX(co_activation_count) as max_activations
        FROM dreams.semantic_network
    """
    )
    result = cur.fetchone()
    stats["semantic_network"] = {
        "associations": result[0],
        "avg_strength": float(result[1]) if result[1] else 0,
        "max_activations": result[2] if result[2] else 0,
    }

    cur.close()
    conn.close()
    return stats


def get_current_context() -> List[Dict[str, Any]]:
    """Get current working memory context from dreams schema."""
    conn = connect_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            memory_id,
            content,
            timestamp,
            importance_score,
            task_type,
            entities,
            topics,
            wm_slot
        FROM dreams.current_context
        LIMIT 10
    """
    )

    columns = [desc[0] for desc in cur.description]
    results = []

    for row in cur.fetchall():
        memory = dict(zip(columns, row))
        if memory.get("timestamp"):
            memory["timestamp"] = memory["timestamp"].isoformat()
        results.append(memory)

    cur.close()
    conn.close()
    return results


def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("Biological Memory Query Tool")
        print("Usage:")
        print("  python query_memories.py recent [limit]     - Get recent memories")
        print("  python query_memories.py search <term>       - Search memories")
        print("  python query_memories.py stats               - Get memory statistics")
        print("  python query_memories.py export [filename]   - Export memories to JSON")
        print("  python query_memories.py dreams              - Get dreams schema statistics")
        print("  python query_memories.py context             - Get current working memory")
        sys.exit(1)

    command = sys.argv[1]

    if command == "recent":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        memories = get_recent_memories(limit)
        print(f"\n=== Recent {limit} Memories ===\n")
        for mem in memories:
            print(f"ID: {mem['id'][:8]}...")
            print(f"Created: {mem['created_at']}")
            print(f"Summary: {mem['summary'][:150]}...")
            if mem.get("tags"):
                print(f"Tags: {', '.join(mem['tags'])}")
            print("-" * 80)

    elif command == "search":
        if len(sys.argv) < 3:
            print("Error: Search term required")
            sys.exit(1)
        search_term = " ".join(sys.argv[2:])
        memories = search_memories(search_term)
        print(f"\n=== Search Results for '{search_term}' ===\n")
        for mem in memories:
            print(f"ID: {mem['id'][:8]}...")
            print(f"Summary: {mem['summary'][:150]}...")
            print(f"Context: {mem['context'][:100]}...")
            print("-" * 80)

    elif command == "stats":
        stats = get_memory_stats()
        print("\n=== Memory Database Statistics ===\n")
        print(f"Total Memories: {stats['total_memories']:,}")
        print(f"Database Size: {stats['database_size']}")
        print(f"Oldest Memory: {stats['oldest_memory']}")
        print(f"Newest Memory: {stats['newest_memory']}")
        if stats["top_tags"]:
            print("\nTop Tags:")
            for tag_info in stats["top_tags"]:
                print(f"  - {tag_info['tag']}: {tag_info['count']} occurrences")

    elif command == "export":
        filename = sys.argv[2] if len(sys.argv) > 2 else "memories_export.json"
        export_memories_to_file(filename)

    elif command == "dreams":
        stats = get_dreams_stats()
        print("\n=== Dreams Schema Statistics ===\n")
        print("Memory Stages:")
        for stage in stats["stages"]:
            print(f"  {stage['stage']}: {stage['count']} records")
            if stage["newest"]:
                print(f"    Latest: {stage['newest']}")
            if stage["avg_importance"]:
                print(f"    Avg Importance: {stage['avg_importance']:.3f}")

        if stats["insights"]:
            print("\nInsights:")
            for insight_type, count in stats["insights"].items():
                print(f"  {insight_type}: {count}")

        print(f"\nSemantic Network:")
        print(f"  Associations: {stats['semantic_network']['associations']}")
        print(f"  Avg Strength: {stats['semantic_network']['avg_strength']:.3f}")

    elif command == "context":
        context = get_current_context()
        print("\n=== Current Working Memory Context ===\n")
        for mem in context:
            print(f"Slot {mem.get('wm_slot', '?')}: {mem.get('task_type', 'unknown')}")
            print(f"  Content: {mem['content'][:100]}...")
            print(f"  Importance: {mem.get('importance_score', 0):.3f}")
            if mem.get("entities"):
                print(f"  Entities: {', '.join(mem['entities'])}")
            print("-" * 60)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
