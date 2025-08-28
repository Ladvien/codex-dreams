# Biological Memory Pipeline - Codex Dreams

A biologically-inspired memory management system implementing hierarchical episodic memory, spatial representations, and Hebbian consolidation patterns. Built with DuckDB, dbt Core, and Ollama for LLM processing.

## 🧠 System Overview

This system models human cognitive memory systems including:
- **Working Memory**: 5-minute attention window with 7±2 item capacity limits
- **Short-Term Memory**: Hierarchical goal-task-action episodes
- **Memory Consolidation**: Hippocampal replay with Hebbian learning
- **Long-Term Semantic Memory**: Cortical organization and retrieval networks

## 🚀 Environment Setup (BMP-001)

### Prerequisites

- Python 3.11+
- Access to PostgreSQL server (192.168.1.104:5432)
- Access to Ollama server (192.168.1.110:11434) with models:
  - `gpt-oss:20b` (LLM generation)
  - `nomic-embed-text` (embeddings)

### Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-repo/codex-dreams.git
   cd codex-dreams
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   # Or manually install core dependencies:
   pip install psycopg2-binary requests pytest python-dotenv dbt-duckdb
   ```

3. **Configure Environment**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env with your actual values
   nano .env
   ```

### Environment Configuration

The `.env` file must contain these variables:

```bash
# PostgreSQL Connection (192.168.1.104:5432)
POSTGRES_DB_URL="postgresql://username:password@192.168.1.104:5432/database_name"
TEST_DATABASE_URL="postgresql://test_user:test_pass@192.168.1.104:5432/test_database"

# Ollama Configuration (192.168.1.110:11434)
OLLAMA_URL="http://192.168.1.110:11434"
OLLAMA_MODEL="gpt-oss:20b"
EMBEDDING_MODEL="nomic-embed-text"

# Database Configuration
DUCKDB_PATH="/path/to/biological_memory/dbs/memory.duckdb"
MAX_DB_CONNECTIONS=160

# dbt Configuration
DBT_PROFILES_DIR="~/.dbt"
DBT_PROJECT_DIR="/path/to/biological_memory"
```

### Connection Pool Configuration

The system is configured for production load with:
- **MAX_DB_CONNECTIONS**: 160 (32% of PostgreSQL server capacity)
- **Connection Pool Split**: 80 main / 80 background connections
- **Retry Logic**: Exponential backoff with 3 attempts
- **Timeout Handling**: 300s for LLM operations

## 🧪 Testing Environment Setup

### Run Connection Tests

Test all live connections and configuration:

```bash
# Test with live servers (when available)
python3 run_env_tests.py

# Test connection logic with mocks (offline)
python3 -m pytest tests/infrastructure/test_environment_mock.py -v

# Test specific components
PYTHONPATH=$(pwd) python3 -m pytest tests/infrastructure/test_environment.py::test_env_variables_loaded -v
```

### Test Results Validation

Successful tests will validate:
- ✅ All environment variables loaded correctly
- ✅ PostgreSQL connection to 192.168.1.104:5432
- ✅ Connection pool configured for 160 max connections
- ✅ Ollama server accessible at 192.168.1.110:11434
- ✅ Models available: gpt-oss:20b, nomic-embed-text
- ✅ Generation and embedding endpoints working
- ✅ Retry logic with exponential backoff
- ✅ Error handling and graceful degradation

### Network Access Requirements

The live servers require network access to:
```bash
# PostgreSQL Server
192.168.1.104:5432  # Main database server

# Ollama Server  
192.168.1.110:11434 # LLM and embedding service
```

If servers are not accessible (different network), the mock tests will validate connection logic without requiring live endpoints.

## 📊 Connection Monitoring

### Health Check Commands

```bash
# Quick PostgreSQL connection test
python3 -c "
from tests.infrastructure.test_environment import *
config = EnvironmentConfig()
postgres = PostgreSQLConnection(config)
result = postgres.test_connection()
print(f'PostgreSQL: {result[\"status\"]} - {result[\"database\"]} as {result[\"user\"]}')
"

# Quick Ollama connection test  
python3 -c "
from tests.infrastructure.test_environment import *
config = EnvironmentConfig()
ollama = OllamaConnection(config)
result = ollama.test_connection()
print(f'Ollama: {result[\"status\"]} - {len(result[\"available_models\"])} models')
"
```

### Performance Metrics

Expected performance benchmarks:
- **PostgreSQL Connection**: < 100ms
- **Connection Pool Setup**: < 500ms
- **Ollama Health Check**: < 2s
- **LLM Generation**: 10-60s (depending on model/prompt)
- **Embedding Generation**: 1-5s

## 🔧 Troubleshooting

### Common Issues

1. **Connection Timeout to PostgreSQL**
   ```bash
   # Check network connectivity
   ping 192.168.1.104
   telnet 192.168.1.104 5432
   
   # Verify credentials in .env
   psql -h 192.168.1.104 -U codex_user -d codex_db
   ```

2. **Ollama Server Unreachable**
   ```bash
   # Check Ollama server status
   curl http://192.168.1.110:11434/api/tags
   
   # Verify models are pulled
   curl http://192.168.1.110:11434/api/tags | jq '.models[].name'
   ```

3. **Missing Models on Ollama**
   ```bash
   # Pull required models on Ollama server
   ollama pull gpt-oss:20b
   ollama pull nomic-embed-text
   ```

4. **Connection Pool Exhaustion**
   ```bash
   # Check active PostgreSQL connections
   psql -h 192.168.1.104 -U codex_user -d codex_db -c "
   SELECT count(*), state FROM pg_stat_activity 
   WHERE datname = 'codex_db' GROUP BY state;
   "
   ```

### Environment Validation

Run the comprehensive environment validation:

```bash
# Full test suite with detailed output
python3 run_env_tests.py 2>&1 | tee environment_test_results.log

# Check test results
echo "Test Summary:"
echo "============="
grep -E "(✅|❌)" environment_test_results.log
```

## 📁 Project Structure

```
codex-dreams/
├── .env                    # Environment configuration (not in git)
├── .env.example           # Environment template
├── README.md              # This file
├── run_env_tests.py       # Environment test runner
├── tests/
│   ├── __init__.py
│   └── infrastructure/
│       ├── __init__.py
│       ├── test_environment.py      # Live connection tests
│       └── test_environment_mock.py # Mock connection tests
├── BACKLOG.md             # Epic user stories
├── ARCHITECTURE.md        # Technical architecture
└── team_chat.md           # Agent communication log
```

## 🔗 Integration Points

### PostgreSQL Source Data
- **Database**: codex_db on 192.168.1.104:5432
- **Table**: raw_memories (expected schema)
- **Access**: Read-only via postgres_scanner DuckDB extension

### Ollama LLM Services
- **Base URL**: http://192.168.1.110:11434
- **Generation Model**: gpt-oss:20b
- **Embedding Model**: nomic-embed-text
- **API Endpoints**: /api/generate, /api/embeddings

### DuckDB Local Storage
- **Path**: Configured in DUCKDB_PATH
- **Extensions**: httpfs, postgres, json
- **Purpose**: Local processing and pipeline materialization

## 📈 Next Steps

After successful BMP-001 environment setup:

1. **BMP-002**: DuckDB Extension and Configuration Setup
2. **BMP-003**: dbt Project Configuration  
3. **BMP-004**: Working Memory Implementation
4. **BMP-005**: Short-Term Memory with Hierarchical Episodes

See `BACKLOG.md` for complete epic breakdown.

## 🛡️ Security Notes

- Never commit `.env` file to version control
- PostgreSQL credentials are stored in environment variables only
- Test database uses separate credentials from production
- Connection pooling prevents resource exhaustion attacks
- Retry logic includes exponential backoff to prevent DoS

## 📝 Logging and Monitoring

All connection tests include:
- Structured logging with timestamps
- Performance metrics collection
- Error context and stack traces
- Retry attempt logging
- Connection pool utilization metrics

Monitor logs for:
- Connection failures or timeouts
- Model unavailability warnings
- Pool exhaustion alerts
- Performance degradation

---

**BMP-001 Status**: ✅ COMPLETED  
**Environment**: Validated and ready for biological memory pipeline implementation  
**Last Updated**: 2025-08-28 00:52:25 UTC