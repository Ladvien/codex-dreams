# Biological Memory Pipeline - New Stories from Code Audit

## 🚨 Epic 2: Critical Production Fixes - Architecture Compliance

**Status**: OPEN  
**Created**: 2025-08-29  
**Priority**: CRITICAL  
**Purpose**: Address critical gaps between ARCHITECTURE.md specification and implementation discovered during comprehensive parallel agent code audit

### Audit Team
- 🔍 **Code Scout Agent** - Deep file inspection (247 files scanned)
- 📊 **Database Auditor** - Database and dbt review (11 SQL models + configs)
- 🧠 **ML Systems Agent** - LLM integration audit (15 core files)
- 🏗️ **Architecture Guardian** - ARCHITECTURE.md compliance validation
- 📝 **Story Coordinator** - Jira story creation and prioritization

---

## 🔴 CRITICAL PRIORITY STORIES (Production Blockers)

### STORY-DB-001: Implement Missing ltm_semantic_network.sql Model
**Type**: Story  
**Priority**: CRITICAL - BLOCKS ALL  
**Story Points**: 8  
**Epic**: Database Architecture Compliance  

**Description**:
Create complete ltm_semantic_network.sql model per ARCHITECTURE.md lines 381-473. This is the centerpiece of long-term memory consolidation and is referenced 47+ times throughout codebase.

**Acceptance Criteria**:
- [ ] Implement semantic graph with cortical column organization (1000 minicolumns)
- [ ] Add network centrality measures and retrieval mechanisms
- [ ] Include proper indexing strategy (btree on semantic_category, cortical_region, retrieval_strength)
- [ ] Implement long-term potentiation/depression algorithms
- [ ] Add memory age categories (recent/week_old/month_old/remote)
- [ ] Implement consolidation state tracking (episodic/consolidating/schematized)
- [ ] Add multi-factor retrieval strength calculation
- [ ] Validate against ARCHITECTURE.md specifications

**Test Requirements**:
```sql
-- Verify cortical organization
SELECT COUNT(DISTINCT minicolumn_id) = 1000 FROM ltm_semantic_network;
-- Verify retrieval mechanisms
SELECT * FROM ltm_semantic_network WHERE retrieval_strength > 0.7;
-- Test semantic similarity calculations
```

**Files to Create/Modify**:
- `/biological_memory/models/long_term/ltm_semantic_network.sql`
- Update references in 47+ locations

**Dependencies**: None  
**Blocking**: All long-term memory functionality, analytics dashboard, integration tests

---

### STORY-DB-002: Fix Database Name and Source Configuration
**Type**: Story  
**Priority**: CRITICAL  
**Story Points**: 3  
**Epic**: Data Source Integration  

**Description**:
Critical database name mismatch - architecture specifies 'self_sensored', implementation uses 'codex_db'. Pipeline cannot access source data.

**Acceptance Criteria**:
- [ ] Update all references from 'codex_db' to 'self_sensored' per ARCHITECTURE.md line 562
- [ ] Update sources.yml to correct database name
- [ ] Fix PostgreSQL connection strings in all configurations
- [ ] Update test configurations to match
- [ ] Verify source data connectivity with correct database

**Files to Modify**:
- `/biological_memory/models/sources.yml`
- All environment configurations
- Test files with database references

**Dependencies**: None  
**Impact**: ENTIRE PIPELINE CANNOT ACCESS DATA

---

### STORY-DB-003: Create Missing profiles.yml Configuration
**Type**: Story  
**Priority**: CRITICAL  
**Story Points**: 5  
**Epic**: Environment Setup  

**Description**:
profiles.yml is completely missing - only example exists. dbt cannot run without this.

**Acceptance Criteria**:
- [ ] Create ~/.dbt/profiles.yml with complete DuckDB configuration
- [ ] Add PostgreSQL attachment via postgres_scanner extension
- [ ] Configure Ollama prompt() function settings:
  - prompt_model: 'ollama'
  - prompt_base_url: '{{ env_var('OLLAMA_URL') }}'
  - prompt_model_name: 'gpt-oss'
- [ ] Add required DuckDB extensions (httpfs, postgres, json)
- [ ] Validate `dbt debug` passes successfully
- [ ] Test connection to both PostgreSQL and Ollama

**Dependencies**: Environment variables must be set

---

### STORY-DB-004: Enable LLM Integration - Replace All TODOs
**Type**: Story  
**Priority**: CRITICAL  
**Story Points**: 8  
**Epic**: LLM Integration  

**Description**:
ALL LLM functionality is missing - 100% of prompt() calls are TODO comments. System operates as rule-based processor instead of biologically accurate LLM pipeline.

**Acceptance Criteria**:
- [ ] Configure DuckDB prompt() function with Ollama endpoint
- [ ] Replace ALL "TODO: Replace with LLM" comments with actual prompt() calls:
  - stm_hierarchical_episodes.sql Line 33
  - memory_replay.sql Line 44
  - biological_memory_macros.sql Line 227
- [ ] Implement proper JSON response parsing
- [ ] Add timeout handling (300s limit)
- [ ] Test semantic extraction with gpt-oss:20b model
- [ ] Validate biological memory enrichment

**Files with TODOs**:
```
/biological_memory/models/short_term_memory/stm_hierarchical_episodes.sql
/biological_memory/models/consolidation/memory_replay.sql
/biological_memory/macros/biological_memory_macros.sql
```

**Dependencies**: STORY-DB-003 (profiles.yml)

---

### STORY-DB-005: Fix postgres_scanner Extension Configuration
**Type**: Story  
**Priority**: HIGH  
**Story Points**: 2  
**Epic**: Database Configuration  

**Description**:
Architecture specifies `postgres_scanner` extension but implementation uses `postgres`. Foreign Data Wrapper may fail.

**Acceptance Criteria**:
- [ ] Replace 'postgres' with 'postgres_scanner' in all configurations
- [ ] Update profiles.yml.example
- [ ] Update setup_duckdb.sql
- [ ] Test PostgreSQL connectivity with correct extension
- [ ] Validate cross-database queries work

---

## 🔐 SECURITY STORIES

### STORY-CS-001: Security Hardening - Credential Exposure Prevention
**Type**: Security Story  
**Priority**: HIGH  
**Story Points**: 5  
**Epic**: Security Hardening  

**Description**:
Error contexts may leak connection strings and credentials in logs (identified in BMP-013_SECURITY_REVIEW.md).

**Acceptance Criteria**:
- [ ] Implement credential sanitization in error_handling.py Line 284
- [ ] Add PII redaction in all error contexts
- [ ] Complete security hardening test implementations
- [ ] Add log sanitization middleware
- [ ] Review ALL logging for sensitive data exposure
- [ ] Implement secret masking patterns

**Security Requirements**:
- No credentials in logs
- No connection strings in error messages
- Sanitized stack traces
- Secure error reporting

---

## 🟡 MEDIUM PRIORITY STORIES

### STORY-DB-006: Rename Working Memory Model to Match Architecture
**Type**: Story  
**Priority**: MEDIUM  
**Story Points**: 3  
**Epic**: Architecture Alignment  

**Description**:
Working memory model named incorrectly - should be wm_active_context.sql not active_memories.sql.

**Acceptance Criteria**:
- [ ] Rename active_memories.sql to wm_active_context.sql
- [ ] Update all model references throughout codebase
- [ ] Update test fixtures
- [ ] Validate model runs with new name

---

### STORY-CS-002: Remove Dead Code and TODO Placeholders
**Type**: Technical Debt  
**Priority**: MEDIUM  
**Story Points**: 3  
**Epic**: Code Quality  

**Description**:
19 TODO comments and unused placeholder functions creating maintenance overhead.

**Acceptance Criteria**:
- [ ] Remove or implement all 19 TODO comments
- [ ] Remove unused placeholder functions in utility_macros.sql
- [ ] Clean up rule-based placeholder code
- [ ] Add code quality checks to prevent new TODOs

---

### STORY-CS-003: Fix Test Suite Architecture Mismatches
**Type**: Story  
**Priority**: HIGH  
**Story Points**: 5  
**Epic**: Test Infrastructure  

**Description**:
Test suite expects architecture models that don't exist - 12+ tests will fail.

**Acceptance Criteria**:
- [ ] Update conftest.py Line 89 to match actual models
- [ ] Fix 12 references to ltm_semantic_network in integration tests
- [ ] Align test data structure with implementation
- [ ] Ensure all integration tests pass

---

### STORY-DB-007: Fix Crontab Schedule Timing
**Type**: Story  
**Priority**: MEDIUM  
**Story Points**: 2  
**Epic**: Biological Accuracy  

**Description**:
Working memory refresh is 12x slower than biological specification.

**Acceptance Criteria**:
- [ ] Update working memory cron from 1 minute to 5 seconds
- [ ] Validate performance at 5-second intervals
- [ ] Test system load with correct timing

---

### STORY-CS-004: Fix Analytics Dashboard Model References
**Type**: Story  
**Priority**: LOW  
**Story Points**: 2  
**Epic**: Analytics  

**Description**:
Analytics dashboard shows incorrect warnings due to missing model references.

**Acceptance Criteria**:
- [ ] Update memory_health.sql Line 15
- [ ] Fix "table missing" warnings
- [ ] Validate dashboard with correct models

---

### STORY-DB-008: Replace MD5 Fake Embeddings with Real Vectors
**Type**: Story  
**Priority**: HIGH  
**Story Points**: 5  
**Epic**: LLM Integration  

**Description**:
System uses MD5 hash-based fake vectors instead of real embeddings from nomic-embed-text model.

**Acceptance Criteria**:
- [ ] Implement real embedding generation with nomic-embed-text
- [ ] Replace MD5-based vectors in utility_macros.sql
- [ ] Update concept_associations.sql to use real embeddings
- [ ] Validate semantic similarity with actual vectors
- [ ] Test 384-dimension embeddings vs 128-dimension hashes

---

## 📊 Story Summary

### Critical Priority (Must Fix for Production)
- 5 stories blocking all functionality
- Estimated: 26 story points
- Timeline: 1-2 weeks with focused effort

### High Priority (Security & Testing)
- 3 stories for security and test infrastructure
- Estimated: 12 story points
- Timeline: 3-5 days

### Medium Priority (Quality & Compliance)
- 4 stories for code quality and architecture alignment
- Estimated: 12 story points
- Timeline: 1 week

### Total Effort
- **12 New Stories** identified by parallel agent audit
- **50 Total Story Points**
- **Estimated Timeline**: 2-3 weeks to production readiness

### Resolution Priority Order
1. STORY-DB-002 (Database name) - Unblocks data access
2. STORY-DB-003 (profiles.yml) - Enables dbt to run
3. STORY-DB-001 (ltm_semantic_network) - Unblocks core functionality
4. STORY-DB-004 (LLM integration) - Enables biological accuracy
5. STORY-CS-001 (Security) - Prevents credential exposure
6. Remaining stories in parallel

---

## Agent Collaboration Success Metrics

### Audit Coverage
- **247 files** scanned by Code Scout Agent
- **15 core files** analyzed by ML Systems Agent  
- **11 SQL models** reviewed by Database Auditor
- **100% architecture** validated by Architecture Guardian
- **12 stories** created by Story Coordinator

### Cross-Validation
- ✅ All agents confirmed missing ltm_semantic_network.sql
- ✅ All agents verified LLM integration is 0%
- ✅ Database name mismatch validated by 3 agents
- ✅ Security risks confirmed by Code Scout and ML Systems

### Key Discovery
**The biological memory pipeline has excellent infrastructure but is missing 100% of its LLM functionality, operating as a rule-based system with fake embeddings instead of the specified biologically accurate AI-enhanced memory processor.**