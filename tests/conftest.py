"""
Test configuration and fixtures for Biological Memory Pipeline tests.
Provides database connections, Ollama mocks, and test data fixtures.
"""
import os
import pytest
import tempfile
import duckdb
from unittest.mock import Mock, patch
from typing import Generator, Dict, Any
import json
from datetime import datetime, timezone


@pytest.fixture(scope="session")
def test_env_vars() -> Dict[str, str]:
    """Load test environment variables."""
    return {
        'POSTGRES_DB_URL': os.getenv('TEST_DATABASE_URL', 'postgresql://test:test@localhost:5432/test_biological_memory'),
        'OLLAMA_URL': 'http://localhost:11434',
        'OLLAMA_MODEL': 'gpt-oss:20b',
        'EMBEDDING_MODEL': 'nomic-embed-text',
        'DUCKDB_PATH': '/tmp/test_memory.duckdb',
        'MAX_DB_CONNECTIONS': '160',
        'OLLAMA_TIMEOUT': '300'
    }


@pytest.fixture(scope="function")
def test_duckdb() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Create isolated test DuckDB instance."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.duckdb') as f:
        db_path = f.name
    
    # Make sure the file is removed if it exists
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    conn = duckdb.connect(db_path)
    
    # Install required extensions
    try:
        conn.execute("INSTALL json")
        conn.execute("LOAD json")
    except Exception:
        pass  # Extension might already be installed
    
    yield conn
    
    conn.close()
    os.unlink(db_path)


@pytest.fixture(scope="function") 
def mock_ollama():
    """Mock Ollama responses for offline testing."""
    mock_responses = {
        'extraction': {
            'entities': ['person', 'organization', 'location', 'task'],
            'topics': ['meeting', 'planning', 'collaboration', 'decision_making'],
            'sentiment': 'positive',
            'importance': 0.8,
            'task_type': 'goal',
            'objects': ['laptop', 'notebook', 'whiteboard', 'documents'],
            'temporal_markers': ['today', 'next week', 'deadline'],
            'emotional_context': 'focused_productive'
        },
        'hierarchy': {
            'goal': 'Complete project milestone',
            'tasks': ['Review requirements', 'Plan implementation', 'Coordinate team'],
            'actions': ['Open document', 'Take notes', 'Schedule follow-up'],
            'time_pointer': 'sequential',
            'dependencies': ['approval needed', 'resource allocation'],
            'priority_level': 'high'
        },
        'spatial': {
            'location': 'conference room',
            'egocentric': 'in front of me',
            'allocentric': 'north wall',
            'objects': [
                {'name': 'whiteboard', 'position': 'wall', 'distance': 'near'},
                {'name': 'projector', 'position': 'ceiling', 'distance': 'above'},
                {'name': 'table', 'position': 'center', 'distance': 'immediate'}
            ],
            'spatial_relationships': ['adjacent_to_door', 'facing_screen'],
            'environmental_context': 'indoor_meeting_space'
        },
        'associations': [
            {'concept': 'collaboration', 'strength': 0.9, 'type': 'semantic'},
            {'concept': 'productivity', 'strength': 0.7, 'type': 'functional'},
            {'concept': 'teamwork', 'strength': 0.85, 'type': 'social'},
            {'concept': 'planning', 'strength': 0.75, 'type': 'procedural'}
        ],
        'semantic_gist': 'Team planning session for project milestone with collaborative discussion',
        'category': 'work_meeting',
        'subcategory': 'project_planning',
        'region': 'prefrontal_cortex',
        'confidence': 0.92,
        'similarity': 0.85,
        'creative_link': 'Both involve problem-solving and creative thinking',
        'consolidation_potential': 0.78,
        'retrieval_cues': ['team', 'project', 'milestone', 'planning'],
        'memory_strength': 0.65,
        'forgetting_curve_position': 0.3
    }
    
    def mock_prompt(prompt_text: str, **kwargs) -> str:
        """Mock the DuckDB prompt() function with realistic responses."""
        prompt_lower = prompt_text.lower()
        
        if 'extract' in prompt_lower or 'entities' in prompt_lower:
            return json.dumps(mock_responses['extraction'])
        elif 'hierarchy' in prompt_lower or 'goal' in prompt_lower or 'task' in prompt_lower:
            return json.dumps(mock_responses['hierarchy'])
        elif 'spatial' in prompt_lower or 'location' in prompt_lower:
            return json.dumps(mock_responses['spatial'])
        elif 'association' in prompt_lower or 'relate' in prompt_lower:
            return json.dumps(mock_responses['associations'])
        elif 'gist' in prompt_lower or 'summary' in prompt_lower or 'summarize' in prompt_lower:
            return json.dumps({
                'gist': mock_responses['semantic_gist'],
                'category': mock_responses['category'],
                'subcategory': mock_responses['subcategory'],
                'region': mock_responses['region'],
                'confidence': mock_responses['confidence']
            })
        elif 'similarity' in prompt_lower or 'compare' in prompt_lower:
            return str(mock_responses['similarity'])
        elif 'creative' in prompt_lower or 'connect' in prompt_lower:
            return mock_responses['creative_link']
        elif 'consolidation' in prompt_lower or 'consolidate' in prompt_lower:
            return json.dumps({
                'consolidation_potential': mock_responses['consolidation_potential'],
                'memory_strength': mock_responses['memory_strength'],
                'retrieval_cues': mock_responses['retrieval_cues']
            })
        elif 'forget' in prompt_lower or 'decay' in prompt_lower:
            return json.dumps({
                'forgetting_curve_position': mock_responses['forgetting_curve_position'],
                'retention_probability': 0.7,
                'decay_rate': 0.05
            })
        elif 'embed' in prompt_lower or 'vector' in prompt_lower:
            # Mock embedding vector (384 dimensions for nomic-embed-text)
            import random
            random.seed(hash(prompt_text) % 2147483647)  # Deterministic based on prompt
            embedding = [random.uniform(-1, 1) for _ in range(384)]
            return json.dumps({'embedding': embedding})
        else:
            return json.dumps({
                'response': 'Generic mock response',
                'prompt_type': 'unknown',
                'confidence': 0.5
            })
    
    with patch('duckdb.DuckDBPyConnection.execute') as mock_execute:
        # Configure mock to handle prompt() function calls
        def side_effect(query: str):
            if 'prompt(' in query:
                return Mock(fetchall=lambda: [(mock_prompt(query),)])
            else:
                return Mock(fetchall=lambda: [])
        
        mock_execute.side_effect = side_effect
        yield mock_prompt


@pytest.fixture(scope="function")
def sample_memory_data():
    """Sample memory data for testing."""
    return [
        {
            'id': 1,
            'content': 'Attended team standup meeting to discuss project progress',
            'timestamp': datetime.now(timezone.utc),
            'metadata': {'source': 'calendar', 'location': 'office'}
        },
        {
            'id': 2, 
            'content': 'Reviewed code changes and provided feedback on pull request',
            'timestamp': datetime.now(timezone.utc),
            'metadata': {'source': 'github', 'repository': 'project-x'}
        },
        {
            'id': 3,
            'content': 'Had lunch with colleague to discuss new architecture proposals',
            'timestamp': datetime.now(timezone.utc),
            'metadata': {'source': 'manual', 'type': 'social'}
        }
    ]


@pytest.fixture(scope="function")
def working_memory_fixture(test_duckdb, sample_memory_data):
    """Set up working memory test data."""
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
    
    # Insert sample data
    for memory in sample_memory_data:
        conn.execute("""
            INSERT INTO raw_memories VALUES (?, ?, ?, ?)
        """, (memory['id'], memory['content'], memory['timestamp'], json.dumps(memory['metadata'])))
    
    return conn


@pytest.fixture(scope="function") 
def short_term_memory_fixture(test_duckdb, sample_memory_data):
    """Set up short-term memory test data."""
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
    
    # Insert processed memories
    for i, memory in enumerate(sample_memory_data):
        conn.execute("""
            INSERT INTO stm_hierarchical_episodes VALUES 
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory['id'], memory['content'], memory['timestamp'], json.dumps(memory['metadata']),
            f'Goal {i+1}', f'Tasks for goal {i+1}', f'Actions for goal {i+1}',
            'objects', 'spatial_info', 0.5 + i*0.1, i+1, i%2==0,
            datetime.now(timezone.utc)
        ))
    
    return conn


@pytest.fixture(scope="function")
def performance_benchmark():
    """Performance benchmark utilities."""
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
            return self.end_time - self.start_time if self.end_time else 0
    
    return BenchmarkTimer


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(test_env_vars):
    """Set up test environment variables."""
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
def mock_http_requests():
    """Mock HTTP requests to Ollama server."""
    import responses
    
    @responses.activate
    def _mock_requests():
        # Mock embedding endpoint
        responses.add(
            responses.POST,
            'http://localhost:11434/api/embeddings',
            json={'embedding': [0.1, 0.2, 0.3] * 128},  # Mock 384-dim embedding
            status=200
        )
        
        # Mock generation endpoint
        responses.add(
            responses.POST, 
            'http://localhost:11434/api/generate',
            json={'response': 'Mock LLM response'},
            status=200
        )
        
        return responses
    
    return _mock_requests


@pytest.fixture(scope="function")
def test_postgres_connection(test_env_vars):
    """Create isolated PostgreSQL test connection."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    # Connect to test database
    test_db_url = test_env_vars['POSTGRES_DB_URL']
    
    try:
        conn = psycopg2.connect(test_db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Create test schema if it doesn't exist
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS test_schema")
        
        yield conn
        
        # Cleanup: Drop test schema after test
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS test_schema CASCADE")
        
        conn.close()
    except Exception:
        # If PostgreSQL connection fails, yield None (tests can check and skip)
        yield None


@pytest.fixture(scope="function")
def isolated_test_db(test_duckdb, test_postgres_connection):
    """Provide both DuckDB and PostgreSQL isolated test connections."""
    return {
        'duckdb': test_duckdb,
        'postgres': test_postgres_connection
    }


@pytest.fixture(scope="function")
def biological_memory_schema(test_duckdb):
    """Set up complete biological memory schema for testing."""
    conn = test_duckdb
    
    # Create all required tables for biological memory testing
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_memories (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON,
            processed BOOLEAN DEFAULT FALSE
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS working_memory_view (
            id INTEGER PRIMARY KEY,
            content TEXT,
            activation_level FLOAT DEFAULT 0.5,
            timestamp TIMESTAMP,
            miller_capacity_position INTEGER CHECK (miller_capacity_position <= 7)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stm_hierarchical_episodes (
            id INTEGER PRIMARY KEY,
            content TEXT,
            level_0_goal TEXT,
            level_1_tasks TEXT,
            atomic_actions TEXT,
            phantom_objects TEXT,
            spatial_extraction TEXT,
            stm_strength FLOAT DEFAULT 0.0,
            hebbian_potential INTEGER DEFAULT 0,
            ready_for_consolidation BOOLEAN DEFAULT FALSE,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ltm_semantic_network (
            id INTEGER PRIMARY KEY,
            concept_a TEXT,
            concept_b TEXT,
            association_strength FLOAT,
            association_type TEXT,
            consolidation_timestamp TIMESTAMP,
            retrieval_count INTEGER DEFAULT 0
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_metrics (
            id INTEGER PRIMARY KEY,
            metric_name TEXT,
            metric_value FLOAT,
            measurement_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    return conn


@pytest.fixture(scope="function")
def hebbian_learning_data(biological_memory_schema):
    """Generate test data for Hebbian learning algorithms."""
    conn = biological_memory_schema
    
    # Insert test associations with realistic Hebbian parameters
    test_associations = [
        ('meeting', 'collaboration', 0.85, 'semantic'),
        ('code', 'review', 0.92, 'procedural'),
        ('project', 'planning', 0.78, 'functional'),
        ('team', 'discussion', 0.73, 'social'),
        ('task', 'completion', 0.88, 'goal_oriented'),
        ('memory', 'consolidation', 0.95, 'biological'),
        ('learning', 'adaptation', 0.81, 'cognitive')
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
    """Generate data representing complete memory lifecycle."""
    conn = biological_memory_schema
    
    # Stage 1: Raw memories (sensory input)
    raw_memories = [
        "Attended daily standup meeting at 9am",
        "Reviewed pull request for authentication feature", 
        "Had productive discussion with team lead about architecture",
        "Completed user story implementation and testing",
        "Participated in sprint retrospective meeting"
    ]
    
    for i, memory in enumerate(raw_memories):
        conn.execute("""
            INSERT INTO raw_memories (id, content, metadata)
            VALUES (?, ?, ?)
        """, (i+1, memory, json.dumps({'source': 'daily_work', 'importance': 0.7 + i*0.05})))
    
    # Stage 2: Working memory (Miller's 7±2)
    for i in range(min(7, len(raw_memories))):
        conn.execute("""
            INSERT INTO working_memory_view 
            (id, content, activation_level, miller_capacity_position)
            VALUES (?, ?, ?, ?)
        """, (i+1, raw_memories[i], 0.8 - i*0.1, i+1))
    
    # Stage 3: Short-term memory processing
    stm_processed = [
        ("Daily team coordination", "Attend standup, provide updates", "Listen, speak, take notes"),
        ("Code quality assurance", "Review code changes", "Read, analyze, comment"),
        ("Architecture planning", "Discuss system design", "Think, propose, document")
    ]
    
    for i, (goal, tasks, actions) in enumerate(stm_processed):
        conn.execute("""
            INSERT INTO stm_hierarchical_episodes
            (id, content, level_0_goal, level_1_tasks, atomic_actions, stm_strength, hebbian_potential, ready_for_consolidation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (i+1, raw_memories[i], goal, tasks, actions, 0.6 + i*0.15, i+2, i >= 1))
    
    return conn


@pytest.fixture(scope="function")
def performance_test_data(biological_memory_schema):
    """Generate large dataset for performance testing."""
    conn = biological_memory_schema
    
    # Generate 1000 memories for performance testing
    import random
    random.seed(42)  # Deterministic for testing
    
    memory_templates = [
        "Meeting with {person} about {topic}",
        "Worked on {project} implementing {feature}",
        "Code review for {component} with {feedback}",
        "Planning session for {initiative} scheduled {when}",
        "Bug fix in {system} affecting {functionality}"
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
            functionality=f"Function{i%18}"
        )
        
        conn.execute("""
            INSERT INTO raw_memories (id, content, metadata)
            VALUES (?, ?, ?)
        """, (i+1, content, json.dumps({'batch': i//100, 'importance': random.uniform(0.3, 0.9)})))
    
    return conn


# Test data constants
TEST_MEMORY_CAPACITY = 7  # Miller's 7±2
TEST_STM_DURATION = 30  # minutes
TEST_CONSOLIDATION_THRESHOLD = 0.5
TEST_HEBBIAN_RATE = 0.1
TEST_FORGETTING_RATE = 0.05


# Session-level cleanup
@pytest.fixture(scope="session", autouse=True)
def cleanup_session():
    """Clean up test schemas after all tests complete."""
    yield
    
    # Clean up any leftover test schemas
    try:
        import psycopg2
        import os
        
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            database=os.getenv('POSTGRES_DB', 'codex_db'),
            user=os.getenv('POSTGRES_USER', os.getenv('USER')),
            password=os.getenv('POSTGRES_PASSWORD', '')
        )
        
        with conn.cursor() as cur:
            # Find and drop all test schemas
            cur.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name LIKE 'test_schema_%'
            """)
            schemas = cur.fetchall()
            
            for (schema,) in schemas:
                cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            
            conn.commit()
        
        conn.close()
        
        if schemas:
            print(f"\nCleaned up {len(schemas)} test schema(s)")
    except Exception as e:
        print(f"\nWarning: Could not clean up test schemas: {e}")