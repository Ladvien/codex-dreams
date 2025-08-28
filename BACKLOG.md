# Biological Memory Pipeline - Jira Stories

## Epic: Biological Memory Pipeline Implementation

### Live Resources Configuration (from .env)
- **PostgreSQL Host**: 192.168.1.104:5432
- **Ollama Host**: 192.168.1.110:11434
- **LLM Model**: gpt-oss:20b
- **Embedding Model**: nomic-embed-text
- **Database**: As configured in POSTGRES_DB_URL

---

## Track 1: Infrastructure & Foundation (Can Start Immediately)

### BMP-001: Environment Setup and Configuration
**Type**: Story  
**Priority**: Critical  
**Story Points**: 5  
**Assigned Agent**: Infrastructure Agent  
**Sprint**: 1  

**Description**:
Set up the foundational environment configuration, connection management, and project structure for the biological memory pipeline using the provided .env.example template.

**Acceptance Criteria**:
- [ ] `.env` file created from `.env.example` with all required variables configured
- [ ] POSTGRES_DB_URL set with credentials for 192.168.1.104:5432
- [ ] OLLAMA_URL set to http://192.168.1.110:11434
- [ ] OLLAMA_MODEL configured as "gpt-oss:20b"
- [ ] EMBEDDING_MODEL set to "nomic-embed-text"
- [ ] DUCKDB_PATH configured for local DuckDB storage
- [ ] MAX_DB_CONNECTIONS set to 160 for production pool
- [ ] TEST_DATABASE_URL configured with separate test database
- [ ] All environment variables successfully loaded and validated

**Test Requirements**:
```python
# tests/infrastructure/test_environment.py
def test_env_variables_loaded():
    assert os.getenv('POSTGRES_DB_URL') is not None
    assert os.getenv('OLLAMA_URL') == 'http://192.168.1.110:11434'
    assert os.getenv('OLLAMA_MODEL') == 'gpt-oss:20b'
    assert os.getenv('EMBEDDING_MODEL') == 'nomic-embed-text'
    assert os.getenv('DUCKDB_PATH') is not None

def test_postgres_connection():
    # Verify connection to 192.168.1.104:5432 using POSTGRES_DB_URL
    
def test_ollama_connection():
    # Verify connection to 192.168.1.110:11434
    # Test both embedding and generation endpoints
    
def test_connection_pool_configuration():
    # Verify MAX_DB_CONNECTIONS is properly configured
```

**Definition of Done**:
- [ ] All connections successfully tested against live resources
- [ ] Environment configuration documented in README
- [ ] All tests passing with >90% coverage
- [ ] Code reviewed by senior engineer
- [ ] .env.example updated with any new variables

---

### BMP-002: DuckDB Extension and Configuration Setup
**Type**: Story  
**Priority**: High  
**Story Points**: 3  
**Assigned Agent**: Database Agent  
**Sprint**: 1

**Description**:
Install and configure all required DuckDB extensions and establish connection mechanisms for PostgreSQL and Ollama integration.

**Acceptance Criteria**:
- [ ] DuckDB initialized at path specified in DUCKDB_PATH
- [ ] httpfs extension installed and configured for Ollama HTTP calls
- [ ] postgres extension installed with connection using POSTGRES_DB_URL
- [ ] json extension configured for JSON processing
- [ ] Foreign Data Wrapper established using POSTGRES_DB_URL
- [ ] prompt() function configured with OLLAMA_URL and OLLAMA_MODEL
- [ ] Connection retry logic implemented with exponential backoff
- [ ] Connection pooling respects MAX_DB_CONNECTIONS limit

**Test Requirements**:
```python
# tests/database/test_duckdb_extensions.py
def test_duckdb_initialization():
    # Verify DuckDB created at DUCKDB_PATH location
    
def test_httpfs_extension():
    # Verify HTTP calls to Ollama at OLLAMA_URL
    
def test_postgres_scanner():
    # Test PostgreSQL data access via POSTGRES_DB_URL
    
def test_prompt_function():
    # Validate LLM integration with gpt-oss:20b model
    
def test_embedding_function():
    # Test embedding generation with nomic-embed-text
    
def test_connection_resilience():
    # Test retry logic and error handling
```

**Definition of Done**:
- [ ] All extensions loaded successfully
- [ ] Cross-database queries working
- [ ] LLM prompts returning valid responses from gpt-oss:20b
- [ ] Embeddings generated successfully with nomic-embed-text
- [ ] Performance benchmarks documented
- [ ] All tests passing

---

### BMP-003: dbt Project Configuration
**Type**: Story  
**Priority**: High  
**Story Points**: 5  
**Assigned Agent**: Analytics Agent  
**Sprint**: 1

**Description**:
Set up dbt project configuration with profiles, project structure, and custom macros for biological memory processing.

**Acceptance Criteria**:
- [ ] dbt profile configured in DBT_PROFILES_DIR location
- [ ] DuckDB connection configured with DUCKDB_PATH
- [ ] PostgreSQL attachment configured using POSTGRES_DB_URL
- [ ] Ollama prompt settings using OLLAMA_URL and OLLAMA_MODEL
- [ ] Project structure created at DBT_PROJECT_DIR
- [ ] All biological parameters configured as dbt variables
- [ ] Custom macros implemented for Hebbian learning
- [ ] Model materializations properly configured

**Test Requirements**:
```python
# tests/dbt/test_dbt_configuration.py
def test_dbt_profile_exists():
    # Verify profile at DBT_PROFILES_DIR
    
def test_dbt_connection():
    # Test dbt can connect to DuckDB and PostgreSQL
    
def test_dbt_variables():
    # Verify all biological parameters accessible
    
def test_custom_macros():
    # Test Hebbian strength calculation
    # Test synaptic homeostasis
    # Test association strengthening
    
def test_dbt_debug():
    # Run dbt debug successfully
```

**Definition of Done**:
- [ ] dbt debug runs successfully
- [ ] All connections validated
- [ ] Macros tested and documented
- [ ] dbt docs generated
- [ ] All tests passing

---

## Track 2: Memory Stage Implementation (Depends on Track 1)

### BMP-004: Working Memory Implementation
**Type**: Story  
**Priority**: High  
**Story Points**: 8  
**Assigned Agent**: Memory Agent  
**Sprint**: 2

**Description**:
Implement the working memory stage with 5-minute attention window and capacity limits following Miller's 7±2 rule.

**Acceptance Criteria**:
- [ ] Connection to PostgreSQL source via POSTGRES_DB_URL
- [ ] 5-minute sliding window for recent memories
- [ ] LLM extraction using Ollama prompt() with gpt-oss:20b
- [ ] Entity, topic, and sentiment extraction working
- [ ] Importance scoring (0-1) implemented
- [ ] Task type classification functional
- [ ] Phantom objects extraction with affordances
- [ ] Capacity limit enforced (7±2 items)
- [ ] View materialization optimized for continuous updates

**Test Requirements**:
```python
# tests/memory/test_working_memory.py
def test_postgres_source_connection():
    # Verify data pull from POSTGRES_DB_URL source
    
def test_time_window():
    # Test 5-minute window filtering
    
def test_llm_extraction():
    # Verify extraction with gpt-oss:20b model
    
def test_capacity_limits():
    # Test Miller's 7±2 enforcement
    
def test_importance_scoring():
    # Validate importance calculation
    
def test_phantom_objects():
    # Test object affordance extraction
```

**Definition of Done**:
- [ ] Model runs successfully with dbt run
- [ ] All extractions produce valid JSON
- [ ] Performance under 100ms for view refresh
- [ ] Tests cover all extraction types
- [ ] Documentation includes example outputs

---

### BMP-005: Short-Term Memory with Hierarchical Episodes
**Type**: Story  
**Priority**: High  
**Story Points**: 10  
**Assigned Agent**: Memory Agent  
**Sprint**: 2

**Description**:
Build short-term memory with hierarchical goal-task-action decomposition and biological memory features.

**Acceptance Criteria**:
- [ ] Incremental materialization configured
- [ ] Hierarchical extraction using Ollama LLM
- [ ] Goal-task-action hierarchy properly structured
- [ ] Spatial memory components extracted
- [ ] Recency factor calculation implemented
- [ ] Emotional salience scoring functional
- [ ] Hebbian co-activation counting working
- [ ] Consolidation readiness flags set correctly
- [ ] Proper handling of incremental updates

**Test Requirements**:
```python
# tests/memory/test_short_term_memory.py
def test_hierarchical_extraction():
    # Test goal-task-action decomposition
    
def test_spatial_extraction():
    # Verify egocentric/allocentric positions
    
def test_decay_calculation():
    # Test exponential decay formula
    
def test_emotional_salience():
    # Validate sentiment-based scoring
    
def test_hebbian_potential():
    # Test co-activation counting
    
def test_consolidation_readiness():
    # Verify consolidation flag logic
    
def test_incremental_processing():
    # Test incremental update handling
```

**Definition of Done**:
- [ ] Incremental processing working correctly
- [ ] Hierarchy extraction validated
- [ ] All biological features calculated
- [ ] Performance benchmarked
- [ ] Integration tests passing

---

### BMP-006: Memory Consolidation and Hippocampal Replay
**Type**: Story  
**Priority**: High  
**Story Points**: 12  
**Assigned Agent**: Consolidation Agent  
**Sprint**: 3

**Description**:
Implement memory consolidation with hippocampal replay simulation and pattern completion.

**Acceptance Criteria**:
- [ ] Replay cycles with pattern completion via LLM
- [ ] Related memory identification working
- [ ] Semantic associations discovered
- [ ] Causal relationships extracted
- [ ] Predictive patterns identified
- [ ] Hebbian strengthening (1.1x factor) applied
- [ ] Competitive forgetting (0.8x weak, 1.2x strong)
- [ ] Cortical transfer for strong memories (>0.5)
- [ ] Semantic gist generation functional
- [ ] Memory pool configuration (10GB)

**Test Requirements**:
```python
# tests/consolidation/test_memory_replay.py
def test_replay_associations():
    # Test pattern completion via LLM
    
def test_hebbian_strengthening():
    # Verify weight updates
    
def test_forgetting_mechanism():
    # Test competitive memory decay
    
def test_cortical_transfer():
    # Validate semantic abstraction
    
def test_memory_pool_usage():
    # Monitor memory consumption
    
def test_consolidation_thresholds():
    # Test strength thresholds
```

**Definition of Done**:
- [ ] Consolidation pipeline functional
- [ ] Memory strengthening verified
- [ ] Forgetting curves validated
- [ ] Performance under 1s per batch
- [ ] Memory usage optimized

---

### BMP-007: Long-Term Semantic Memory Network
**Type**: Story  
**Priority**: High  
**Story Points**: 10  
**Assigned Agent**: Semantic Agent  
**Sprint**: 3

**Description**:
Create long-term semantic memory with cortical organization and retrieval mechanisms.

**Acceptance Criteria**:
- [ ] Semantic graph construction with similarity scores
- [ ] Cortical column organization (1000 minicolumns)
- [ ] Within-column competition ranking
- [ ] Long-term potentiation/depression modeling
- [ ] Access frequency tracking
- [ ] Retrieval strength calculation (multi-factor)
- [ ] Memory age categorization
- [ ] Consolidation state tracking
- [ ] B-tree indexes on key columns
- [ ] Full table materialization

**Test Requirements**:
```python
# tests/memory/test_semantic_network.py
def test_semantic_similarity():
    # Test LLM similarity scoring
    
def test_cortical_organization():
    # Verify column structure
    
def test_competition_ranking():
    # Test within-column competition
    
def test_retrieval_strength():
    # Validate multi-factor calculation
    
def test_memory_categorization():
    # Test age and state categories
    
def test_index_performance():
    # Benchmark query performance
```

**Definition of Done**:
- [ ] Semantic network fully operational
- [ ] Indexes improving query performance
- [ ] Retrieval mechanisms validated
- [ ] Cortical organization verified
- [ ] All tests passing

---

## Track 3: Biological Rhythms & Orchestration (Depends on Track 2)

### BMP-008: Crontab Schedule Implementation
**Type**: Story  
**Priority**: Medium  
**Story Points**: 5  
**Assigned Agent**: Orchestration Agent  
**Sprint**: 4

**Description**:
Implement biological rhythm scheduling mimicking sleep-wake cycles and memory consolidation patterns.

**Acceptance Criteria**:
- [ ] Working memory updates every 5 seconds (6am-10pm)
- [ ] STM updates every 5 minutes
- [ ] Hourly consolidation runs
- [ ] Deep consolidation (2-4 AM daily)
- [ ] REM sleep simulation (90-min cycles at night)
- [ ] Weekly synaptic homeostasis (Sunday 3 AM)
- [ ] All schedules respect biological timing
- [ ] Error handling and recovery mechanisms

**Test Requirements**:
```python
# tests/orchestration/test_cron_schedule.py
def test_cron_syntax():
    # Validate all cron expressions
    
def test_schedule_coverage():
    # Verify 24-hour coverage
    
def test_biological_timing():
    # Test wake/sleep cycle adherence
    
def test_job_execution():
    # Mock job runs successfully
    
def test_error_recovery():
    # Test failure handling
```

**Definition of Done**:
- [ ] Crontab installed and configured
- [ ] All schedules active
- [ ] Monitoring in place
- [ ] Documentation complete
- [ ] Tests passing

---

### BMP-009: Custom Biological Macros
**Type**: Story  
**Priority**: Medium  
**Story Points**: 7  
**Assigned Agent**: Algorithm Agent  
**Sprint**: 4

**Description**:
Develop custom dbt macros for biological memory processes including Hebbian learning and synaptic homeostasis.

**Acceptance Criteria**:
- [ ] calculate_hebbian_strength() macro functional
- [ ] Co-activation counting accurate
- [ ] Learning rate (0.1) properly applied
- [ ] synaptic_homeostasis() macro working
- [ ] Weekly rescaling prevents runaway potentiation
- [ ] Weak connection pruning (< 0.01)
- [ ] strengthen_associations() for REM sleep
- [ ] Creative linking via LLM prompts
- [ ] All macros parameterized via dbt vars

**Test Requirements**:
```python
# tests/macros/test_biological_macros.py
def test_hebbian_calculation():
    # Verify Hebbian learning formula
    
def test_coactivation_window():
    # Test 5-minute activation window
    
def test_synaptic_rescaling():
    # Validate homeostasis normalization
    
def test_connection_pruning():
    # Test weak connection removal
    
def test_creative_associations():
    # Verify REM-like associations
    
def test_macro_parameters():
    # Test variable substitution
```

**Definition of Done**:
- [ ] All macros implemented
- [ ] Mathematical accuracy verified
- [ ] Performance optimized
- [ ] Documentation complete
- [ ] Integration tested

---

## Track 4: Testing & Monitoring (Parallel with other tracks)

### BMP-010: Comprehensive Test Suite
**Type**: Story  
**Priority**: High  
**Story Points**: 10  
**Assigned Agent**: QA Agent  
**Sprint**: 2-4 (Continuous)

**Description**:
Develop comprehensive test suite following test file naming convention (src file + _test suffix).

**Acceptance Criteria**:
- [ ] Test directory mirrors src structure
- [ ] All test files use _test suffix naming
- [ ] Unit tests for all functions
- [ ] Integration tests for data pipelines
- [ ] Performance benchmarks established
- [ ] Test database using TEST_DATABASE_URL
- [ ] Mock Ollama responses for offline testing
- [ ] Coverage reports generated
- [ ] CI/CD pipeline configured

**Test Requirements**:
```python
# tests/test_suite_validation.py
def test_directory_structure():
    # Verify test files mirror src
    
def test_naming_convention():
    # Check all tests use _test suffix
    
def test_coverage_threshold():
    # Ensure >90% code coverage
    
def test_database_isolation():
    # Verify test DB separation
    
def test_mock_functionality():
    # Validate Ollama mocks
```

**Definition of Done**:
- [ ] All src files have corresponding tests
- [ ] Coverage >90%
- [ ] Tests run in <5 minutes
- [ ] CI/CD pipeline green
- [ ] Documentation complete

---

### BMP-011: Memory Health Analytics Dashboard
**Type**: Story  
**Priority**: Medium  
**Story Points**: 6  
**Assigned Agent**: Analytics Agent  
**Sprint**: 4

**Description**:
Create monitoring and analytics views for memory system health and performance.

**Acceptance Criteria**:
- [ ] Memory distribution metrics calculated
- [ ] Retrieval strength averages tracked
- [ ] Semantic diversity measured
- [ ] Cortical distribution monitored
- [ ] Access frequency statistics
- [ ] Consolidation timing tracked
- [ ] System performance metrics
- [ ] View refreshes efficiently
- [ ] Alerting thresholds defined

**Test Requirements**:
```python
# tests/analytics/test_memory_health.py
def test_distribution_metrics():
    # Verify memory counts by age
    
def test_health_indicators():
    # Test biological health metrics
    
def test_performance_metrics():
    # Validate system performance
    
def test_view_efficiency():
    # Benchmark view refresh time
    
def test_alerting_logic():
    # Test threshold triggers
```

**Definition of Done**:
- [ ] All metrics calculating correctly
- [ ] Dashboard views created
- [ ] Performance optimized
- [ ] Alerts configured
- [ ] Documentation complete

---

## Track 5: Performance & Optimization (After MVP)

### BMP-012: Performance Optimization
**Type**: Story  
**Priority**: Medium  
**Story Points**: 8  
**Assigned Agent**: Performance Agent  
**Sprint**: 5

**Description**:
Optimize system performance through partitioning, caching, and batch processing.

**Acceptance Criteria**:
- [ ] Monthly partitioning implemented
- [ ] LLM response caching functional
- [ ] Batch processing for multiple memories
- [ ] Connection pooling optimized (160 connections)
- [ ] Incremental processing refined
- [ ] Query performance <100ms
- [ ] Index strategy optimized
- [ ] Memory usage under control

**Test Requirements**:
```python
# tests/performance/test_optimization.py
def test_partition_performance():
    # Benchmark partitioned queries
    
def test_cache_hit_rate():
    # Measure cache effectiveness
    
def test_batch_efficiency():
    # Compare batch vs individual
    
def test_connection_pool():
    # Monitor pool utilization
    
def test_query_performance():
    # Validate <100ms target
```

**Definition of Done**:
- [ ] Performance targets met
- [ ] Resource usage optimized
- [ ] Benchmarks documented
- [ ] Monitoring in place
- [ ] Tests passing

---

### BMP-013: Error Handling and Recovery
**Type**: Story  
**Priority**: High  
**Story Points**: 7  
**Assigned Agent**: Reliability Agent  
**Sprint**: 5

**Description**:
Implement comprehensive error handling, retry logic, and recovery mechanisms.

**Acceptance Criteria**:
- [ ] Connection failure handling with retry
- [ ] LLM timeout handling (300s limit)
- [ ] Malformed JSON recovery
- [ ] Transaction rollback on failure
- [ ] Dead letter queue for failed memories
- [ ] Circuit breaker pattern (if MCP_CIRCUIT_BREAKER_ENABLED)
- [ ] Graceful degradation modes
- [ ] Error logging with context

**Test Requirements**:
```python
# tests/reliability/test_error_handling.py
def test_connection_retry():
    # Test exponential backoff
    
def test_llm_timeout():
    # Verify timeout handling
    
def test_json_recovery():
    # Test malformed response handling
    
def test_transaction_rollback():
    # Verify data consistency
    
def test_circuit_breaker():
    # Test circuit breaker pattern
```

**Definition of Done**:
- [ ] All error paths handled
- [ ] Recovery mechanisms tested
- [ ] Logging comprehensive
- [ ] Documentation complete
- [ ] Integration tested

---

## Definition of Done (Global)

For all stories:
1. **Code Quality**
   - [ ] Code follows project style guide
   - [ ] No linting errors
   - [ ] Type hints where applicable
   - [ ] Comments for complex logic

2. **Testing**
   - [ ] Unit tests written and passing
   - [ ] Integration tests where applicable
   - [ ] Test coverage >90%
   - [ ] Tests use TEST_DATABASE_URL

3. **Documentation**
   - [ ] README updated
   - [ ] API documentation complete
   - [ ] Configuration documented
   - [ ] Example usage provided

4. **Review**
   - [ ] Code reviewed by peer
   - [ ] Architectural review if needed
   - [ ] Security review for credentials
   - [ ] Performance review

5. **Deployment**
   - [ ] Migration scripts created
   - [ ] Rollback plan documented
   - [ ] Monitoring configured
   - [ ] Alerts set up

## Parallel Work Streams

**Stream 1 (Infrastructure)**: BMP-001, BMP-002, BMP-003
- Can start immediately
- Foundation for all other work

**Stream 2 (Memory Stages)**: BMP-004, BMP-005, BMP-006, BMP-007
- Depends on Stream 1
- Can be worked in sequence

**Stream 3 (Orchestration)**: BMP-008, BMP-009
- Depends on Stream 2
- Focus on automation

**Stream 4 (Quality)**: BMP-010, BMP-011
- Can start with Stream 1
- Continuous throughout

**Stream 5 (Optimization)**: BMP-012, BMP-013
- After MVP completion
- Performance and reliability focus

## Success Metrics

- All tests passing with >90% coverage
- Query performance <100ms
- Memory consolidation <1s per batch
- System uptime >99.9%
- Successful end-to-end memory lifecycle
- Live resource connections stable
- All biological rhythms functioning