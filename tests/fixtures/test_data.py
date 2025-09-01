"""
Test data factories for biological memory scenarios.

Provides realistic test data representing different stages of biological
memory processing, from raw sensory input to consolidated long-term memories.
"""

import pytest
import json
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Generator
from pathlib import Path
import os


@pytest.fixture(scope="session")
def test_env_vars() -> Dict[str, str]:
    """Load test environment variables with fallback defaults."""
    return {
        "POSTGRES_DB_URL": os.getenv(
            "TEST_DATABASE_URL", 
            "postgresql://codex_user:test_password@localhost:5432/test_codex_db"
        ),
        "OLLAMA_URL": os.getenv("OLLAMA_URL", "http://localhost:11434"),
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
        "EMBEDDING_MODEL": os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
        "DUCKDB_PATH": os.getenv("DUCKDB_PATH", "./test_biological_memory.duckdb"),
        "MAX_DB_CONNECTIONS": "160",
        "OLLAMA_TIMEOUT": "30",
    }


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(test_env_vars):
    """Set up test environment variables with proper cleanup."""
    original_env = {}

    # Store original values and set test values
    for key, value in test_env_vars.items():
        original_env[key] = os.getenv(key)
        os.environ[key] = value

    yield

    # Restore original values
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


@pytest.fixture(scope="function")
def sample_memory_data():
    """Sample memory data representing typical cognitive activities."""
    return [
        {
            "id": 1,
            "content": "Attended team standup meeting to discuss project progress",
            "timestamp": datetime.now(timezone.utc),
            "metadata": {"source": "calendar", "location": "office", "participants": 5},
        },
        {
            "id": 2,
            "content": "Reviewed code changes and provided feedback on pull request",
            "timestamp": datetime.now(timezone.utc),
            "metadata": {"source": "github", "repository": "project-x", "lines_changed": 247},
        },
        {
            "id": 3,
            "content": "Had lunch with colleague to discuss new architecture proposals",
            "timestamp": datetime.now(timezone.utc),
            "metadata": {"source": "manual", "type": "social", "duration": "45min"},
        },
        {
            "id": 4,
            "content": "Debugged authentication issue in production system",
            "timestamp": datetime.now(timezone.utc),
            "metadata": {"source": "incident", "severity": "high", "resolved": True},
        },
        {
            "id": 5,
            "content": "Researched vector database optimization techniques",
            "timestamp": datetime.now(timezone.utc),
            "metadata": {"source": "learning", "topic": "performance", "articles": 3},
        },
    ]


@pytest.fixture(scope="function")
def working_memory_fixture(test_duckdb, sample_memory_data):
    """Set up working memory test data with Miller's 7±2 constraint."""
    conn = test_duckdb

    # Create working memory view structure
    conn.execute("""
        CREATE TABLE raw_memories (
            id INTEGER,
            content TEXT,
            timestamp TIMESTAMP,
            metadata JSON
        )
    """)

    # Insert sample data (limited to Miller's capacity)
    for i, memory in enumerate(sample_memory_data[:7]):  # Enforce 7±2 limit
        conn.execute("""
            INSERT INTO raw_memories VALUES (?, ?, ?, ?)
        """, (
            memory["id"], 
            memory["content"], 
            memory["timestamp"], 
            json.dumps(memory["metadata"])
        ))

    return conn


@pytest.fixture(scope="function")
def short_term_memory_fixture(test_duckdb, sample_memory_data):
    """Set up short-term memory test data with hierarchical episodes."""
    conn = test_duckdb

    # Create STM table structure
    conn.execute("""
        CREATE TABLE stm_hierarchical_episodes (
            id INTEGER,
            content TEXT,
            timestamp TIMESTAMP,
            metadata JSON,
            level_0_goal TEXT,
            level_1_tasks TEXT,
            atomic_actions TEXT,
            phantom_objects TEXT,
            spatial_extraction TEXT,
            stm_strength FLOAT,
            hebbian_potential INTEGER,
            ready_for_consolidation BOOLEAN,
            processed_at TIMESTAMP
        )
    """)

    # Insert processed memories with realistic hierarchical structure
    for i, memory in enumerate(sample_memory_data):
        conn.execute("""
            INSERT INTO stm_hierarchical_episodes VALUES 
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory["id"],
            memory["content"],
            memory["timestamp"],
            json.dumps(memory["metadata"]),
            f"Professional development goal {i+1}",
            f"Execute task: {memory['content'][:30]}...",
            f"Actions: observe, process, respond",
            json.dumps(["computer", "documents", "people"]),
            json.dumps({"location": "office", "spatial_context": "work_environment"}),
            0.5 + (i * 0.1),  # Increasing strength
            i + 1,
            i >= 2,  # Mark later memories for consolidation
            datetime.now(timezone.utc),
        ))

    return conn


@pytest.fixture(scope="function")
def hebbian_learning_data(biological_memory_schema):
    """Generate test data for Hebbian learning algorithms."""
    conn = biological_memory_schema

    # Insert test associations with realistic Hebbian parameters
    test_associations = [
        ("meeting", "collaboration", 0.85, "semantic"),
        ("code", "review", 0.92, "procedural"),
        ("project", "planning", 0.78, "functional"),
        ("team", "discussion", 0.73, "social"),
        ("task", "completion", 0.88, "goal_oriented"),
        ("memory", "consolidation", 0.95, "biological"),
        ("learning", "adaptation", 0.81, "cognitive"),
        ("debugging", "problem_solving", 0.89, "analytical"),
        ("architecture", "design", 0.87, "conceptual"),
        ("performance", "optimization", 0.83, "technical"),
    ]

    for concept_a, concept_b, strength, assoc_type in test_associations:
        conn.execute("""
            INSERT INTO ltm_semantic_network 
            (concept_a, concept_b, association_strength, association_type, consolidation_timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (concept_a, concept_b, strength, assoc_type, datetime.now(timezone.utc)))

    return conn


@pytest.fixture(scope="function")
def memory_lifecycle_data(biological_memory_schema):
    """Generate data representing complete memory lifecycle from sensory to LTM."""
    conn = biological_memory_schema

    # Stage 1: Raw memories (sensory input)
    raw_memories = [
        "Attended daily standup meeting at 9am",
        "Reviewed pull request for authentication feature",
        "Had productive discussion with team lead about architecture",
        "Completed user story implementation and testing",
        "Participated in sprint retrospective meeting",
        "Researched new database optimization techniques",
        "Fixed critical bug in payment processing system",
    ]

    for i, memory in enumerate(raw_memories):
        conn.execute("""
            INSERT INTO raw_memories (id, content, metadata)
            VALUES (?, ?, ?)
        """, (
            i + 1, 
            memory, 
            json.dumps({
                "source": "daily_work", 
                "importance": 0.7 + (i * 0.05),
                "emotional_valence": "positive" if i % 2 == 0 else "neutral"
            })
        ))

    # Stage 2: Working memory (Miller's 7±2)
    for i in range(min(7, len(raw_memories))):
        conn.execute("""
            INSERT INTO working_memory_view 
            (id, content, activation_level, miller_capacity_position)
            VALUES (?, ?, ?, ?)
        """, (i + 1, raw_memories[i], 0.8 - (i * 0.1), i + 1))

    # Stage 3: Short-term memory processing
    stm_processed = [
        ("Daily team coordination", "Attend standup, provide updates", "Listen, speak, take notes"),
        ("Code quality assurance", "Review code changes", "Read, analyze, comment"),
        ("Architecture planning", "Discuss system design", "Think, propose, document"),
        ("Feature development", "Implement user story", "Code, test, debug"),
        ("Process improvement", "Participate in retrospective", "Reflect, suggest, plan"),
    ]

    for i, (goal, tasks, actions) in enumerate(stm_processed):
        if i < len(raw_memories):
            conn.execute("""
                INSERT INTO stm_hierarchical_episodes
                (id, content, level_0_goal, level_1_tasks, atomic_actions, stm_strength, 
                 hebbian_potential, ready_for_consolidation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                i + 1, raw_memories[i], goal, tasks, actions, 
                0.6 + (i * 0.15), i + 2, i >= 2
            ))

    return conn


@pytest.fixture(scope="function")
def performance_test_data(biological_memory_schema):
    """Generate large dataset for performance testing."""
    conn = biological_memory_schema

    # Generate 1000 memories for performance testing
    random.seed(42)  # Deterministic for testing

    memory_templates = [
        "Meeting with {person} about {topic}",
        "Worked on {project} implementing {feature}",
        "Code review for {component} with {feedback}",
        "Planning session for {initiative} scheduled {when}",
        "Bug fix in {system} affecting {functionality}",
        "Research on {technology} for {application}",
        "Discussion with {stakeholder} regarding {requirement}",
        "Testing {module} with {test_type} scenarios",
        "Documentation update for {process} including {detail}",
        "Training session on {skill} with {outcome}",
    ]

    for i in range(1000):
        template = random.choice(memory_templates)
        content = template.format(
            person=f"Person{i%20}",
            topic=f"Topic{i%15}",
            project=f"Project{i%10}",
            feature=f"Feature{i%25}",
            component=f"Component{i%12}",
            feedback=f"Feedback{i%8}",
            initiative=f"Initiative{i%7}",
            when=f"Week{i%4}",
            system=f"System{i%6}",
            functionality=f"Function{i%18}",
            technology=f"Technology{i%14}",
            application=f"Application{i%16}",
            stakeholder=f"Stakeholder{i%9}",
            requirement=f"Requirement{i%11}",
            module=f"Module{i%13}",
            test_type=f"TestType{i%5}",
            process=f"Process{i%17}",
            detail=f"Detail{i%19}",
            skill=f"Skill{i%21}",
            outcome=f"Outcome{i%22}",
        )

        conn.execute("""
            INSERT INTO raw_memories (id, content, metadata)
            VALUES (?, ?, ?)
        """, (
            i + 1,
            content,
            json.dumps({
                "batch": i // 100, 
                "importance": random.uniform(0.3, 0.9),
                "complexity": random.choice(["low", "medium", "high"]),
                "domain": random.choice(["technical", "social", "creative", "analytical"])
            }),
        ))

    return conn


@pytest.fixture(scope="function")
def performance_benchmark():
    """Performance benchmark utilities for testing execution speed."""
    import time

    class BenchmarkTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end_time = time.perf_counter()

        @property
        def elapsed(self) -> float:
            """Return elapsed time in seconds."""
            return self.end_time - self.start_time if self.end_time else 0
        
        @property
        def elapsed_ms(self) -> float:
            """Return elapsed time in milliseconds."""
            return self.elapsed * 1000

    return BenchmarkTimer


class MemoryDataFactory:
    """Factory class for generating realistic biological memory test data."""
    
    @staticmethod
    def create_working_memory_batch(size: int = 7) -> List[Dict[str, Any]]:
        """Create a batch of working memory entries respecting Miller's 7±2."""
        if size > 9:
            size = 9  # Enforce upper bound of Miller's rule
        
        activities = [
            "attended team meeting",
            "reviewed code changes", 
            "debugged production issue",
            "planned project milestone",
            "researched new technology",
            "mentored junior developer",
            "documented system architecture",
            "analyzed performance metrics",
            "coordinated with stakeholders"
        ]
        
        return [
            {
                "id": i + 1,
                "content": activities[i % len(activities)],
                "activation_level": 1.0 - (i * 0.1),
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=i*5),
                "miller_position": i + 1
            }
            for i in range(size)
        ]
    
    @staticmethod
    def create_hebbian_associations(count: int = 10) -> List[Dict[str, Any]]:
        """Create realistic Hebbian learning associations."""
        concept_pairs = [
            ("meeting", "collaboration", "semantic"),
            ("code", "logic", "procedural"), 
            ("bug", "debugging", "causal"),
            ("project", "planning", "functional"),
            ("team", "communication", "social"),
            ("learning", "memory", "cognitive"),
            ("performance", "optimization", "technical"),
            ("architecture", "design", "structural"),
            ("testing", "validation", "procedural"),
            ("documentation", "knowledge", "informational")
        ]
        
        return [
            {
                "concept_a": pair[0],
                "concept_b": pair[1],
                "association_type": pair[2],
                "strength": random.uniform(0.6, 0.95),
                "co_activation_count": random.randint(1, 50),
                "timestamp": datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 168))
            }
            for pair in concept_pairs[:count]
        ]


@pytest.fixture(scope="function")
def memory_data_factory():
    """Provide memory data factory for dynamic test data generation."""
    return MemoryDataFactory()