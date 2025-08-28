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
            'entities': ['person', 'organization'],
            'topics': ['meeting', 'planning'],
            'sentiment': 'positive',
            'importance': 0.8,
            'task_type': 'goal',
            'objects': ['laptop', 'notebook']
        },
        'hierarchy': {
            'goal': 'Complete project milestone',
            'tasks': ['Review requirements', 'Plan implementation'],
            'actions': ['Open document', 'Take notes'],
            'time_pointer': 'sequential'
        },
        'spatial': {
            'location': 'conference room',
            'egocentric': 'in front of me',
            'allocentric': 'north wall',
            'objects': [{'name': 'whiteboard', 'position': 'wall'}]
        },
        'associations': [
            {'concept': 'collaboration', 'strength': 0.9},
            {'concept': 'productivity', 'strength': 0.7}
        ],
        'semantic_gist': 'Team planning session for project milestone with collaborative discussion',
        'category': 'work_meeting',
        'region': 'prefrontal_cortex',
        'similarity': 0.85,
        'creative_link': 'Both involve problem-solving and creative thinking'
    }
    
    def mock_prompt(prompt_text: str, **kwargs) -> str:
        """Mock the DuckDB prompt() function with realistic responses."""
        if 'extract' in prompt_text.lower():
            return json.dumps(mock_responses['extraction'])
        elif 'hierarchy' in prompt_text.lower() or 'goal' in prompt_text.lower():
            return json.dumps(mock_responses['hierarchy'])
        elif 'spatial' in prompt_text.lower():
            return json.dumps(mock_responses['spatial'])
        elif 'association' in prompt_text.lower():
            return json.dumps(mock_responses['associations'])
        elif 'gist' in prompt_text.lower() or 'summary' in prompt_text.lower():
            return json.dumps({
                'gist': mock_responses['semantic_gist'],
                'category': mock_responses['category'],
                'region': mock_responses['region']
            })
        elif 'similarity' in prompt_text.lower():
            return str(mock_responses['similarity'])
        elif 'creative' in prompt_text.lower():
            return mock_responses['creative_link']
        else:
            return json.dumps({'response': 'Generic mock response'})
    
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


# Test data constants
TEST_MEMORY_CAPACITY = 7  # Miller's 7±2
TEST_STM_DURATION = 30  # minutes
TEST_CONSOLIDATION_THRESHOLD = 0.5
TEST_HEBBIAN_RATE = 0.1
TEST_FORGETTING_RATE = 0.05