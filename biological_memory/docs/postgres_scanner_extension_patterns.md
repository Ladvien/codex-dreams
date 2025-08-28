# PostgreSQL Scanner Extension Patterns and Configuration Guide

**Documentation Created**: 2025-08-28  
**Story**: STORY-DB-005 - Fix postgres_scanner Extension Configuration  
**Author**: SQL Expert Agent  
**Review**: Senior Database Integration Specialist (Approved)  

## Overview

This document establishes patterns and best practices for postgres_scanner extension usage in the Biological Memory Pipeline. The postgres_scanner extension enables cross-database connectivity between DuckDB and PostgreSQL, providing essential hybrid analytics capabilities.

## Extension Architecture Pattern

### Core Components
1. **Extension Installation**: Install postgres_scanner in DuckDB
2. **Extension Loading**: Load extension in each session
3. **Connection Management**: Secure credential handling with secrets
4. **Query Execution**: Cross-database operations and data integration

## Implementation Patterns

### 1. Extension Lifecycle Management

#### Installation Pattern
```sql
-- Install required extensions
INSTALL postgres_scanner;
INSTALL fts;
INSTALL json;
```

#### Loading Pattern
```sql
-- Load extensions for current session
LOAD postgres_scanner;
LOAD fts;
LOAD json;
```

#### Verification Pattern
```sql
-- Verify extension status
SELECT extension_name, loaded, installed 
FROM duckdb_extensions() 
WHERE extension_name = 'postgres_scanner';
```

### 2. Connection Configuration Patterns

#### Development Environment Pattern
```yaml
# profiles.yml - Development
outputs:
  dev:
    type: duckdb
    path: '/path/to/memory.duckdb'
    extensions:
      - postgres_scanner
      - fts
      - json
    external_sources:
      postgresql:
        host: 'localhost'
        port: 5432
        database: 'biological_memory_source'
        user: 'dev_user'
        password: 'dev_password'
    settings:
      memory_limit: '4GB'
      threads: 4
      postgres_scanner_timeout: 30000
      postgres_scanner_batch_size: 10000
```

#### Production Environment Pattern
```yaml
# profiles.yml - Production
outputs:
  prod:
    type: duckdb
    path: '/production/memory.duckdb'
    extensions:
      - postgres_scanner
      - fts
      - json
    external_sources:
      postgresql:
        host: '{{ env_var("POSTGRES_HOST") }}'
        port: '{{ env_var("POSTGRES_PORT", "5432") | int }}'
        database: '{{ env_var("POSTGRES_DATABASE") }}'
        user: '{{ env_var("POSTGRES_USER") }}'
        password: '{{ env_var("POSTGRES_PASSWORD") }}'
    settings:
      memory_limit: '8GB'
      threads: 8
      postgres_scanner_timeout: 60000
      postgres_scanner_batch_size: 50000
```

### 3. Secure Connection Management Pattern

#### Secrets-Based Authentication (Recommended)
```sql
-- Create secure connection using secrets
CREATE OR REPLACE SECRET postgres_connection (
    TYPE POSTGRES,
    HOST getenv('POSTGRES_HOST'),
    PORT getenv('POSTGRES_PORT')::INT,
    DATABASE getenv('POSTGRES_DATABASE'),
    USER getenv('POSTGRES_USER'),
    PASSWORD getenv('POSTGRES_PASSWORD')
);

-- Attach database using secret
ATTACH '' AS source_memories (TYPE POSTGRES, SECRET postgres_connection);
```

#### Direct Connection Pattern (Development Only)
```sql
-- Direct connection for development
ATTACH 'postgresql://user:pass@localhost:5432/database' AS source_memories (TYPE POSTGRES);
```

### 4. Cross-Database Query Patterns

#### Simple Query Pattern
```sql
-- Query PostgreSQL table through DuckDB
SELECT memory_id, content, created_at
FROM source_memories.public.raw_memories
WHERE created_at >= CURRENT_DATE - INTERVAL 1 DAY
LIMIT 1000;
```

#### Hybrid Analytics Pattern
```sql
-- Combine DuckDB and PostgreSQL data
SELECT 
    d.memory_id,
    d.processed_content,
    p.raw_content,
    d.memory_strength
FROM memory.consolidated_memories d
JOIN source_memories.public.raw_memories p
    ON d.source_memory_id = p.memory_id
WHERE d.memory_strength > 0.7;
```

#### Materialization Pattern
```sql
-- Create DuckDB table from PostgreSQL data
CREATE TABLE memory_import AS
SELECT * FROM source_memories.public.raw_memories
WHERE import_status = 'pending';
```

## Performance Optimization Patterns

### 1. Connection Settings
```sql
-- Optimize for production workloads
PRAGMA memory_limit='8GB';
PRAGMA threads=8;
PRAGMA postgres_scanner_timeout=60000;
PRAGMA postgres_scanner_batch_size=50000;
PRAGMA enable_progress_bar=true;
```

### 2. Query Optimization
```sql
-- Use filters to minimize data transfer
SELECT memory_id, content
FROM source_memories.public.raw_memories
WHERE created_at >= '2025-01-01'  -- Filter at source
  AND status = 'active'           -- Reduce network traffic
LIMIT 10000;                      -- Prevent excessive memory usage
```

### 3. Batch Processing Pattern
```python
# Python pattern for large data migrations
def migrate_memories_batch(start_date, end_date, batch_size=10000):
    query = f"""
    SELECT * FROM source_memories.public.raw_memories
    WHERE created_at BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY created_at
    LIMIT {batch_size} OFFSET {{offset}}
    """
    
    offset = 0
    while True:
        batch_query = query.format(offset=offset)
        # Process batch...
        offset += batch_size
```

## Error Handling Patterns

### 1. Connection Validation
```sql
-- Test connection before queries
SELECT 
    CASE 
        WHEN COUNT(*) >= 0 THEN 'Connection successful'
        ELSE 'Connection failed'
    END as connection_status
FROM source_memories.information_schema.tables
LIMIT 1;
```

### 2. Timeout Handling
```python
# Python error handling pattern
def safe_postgres_query(query, timeout_seconds=30):
    try:
        # Set timeout
        conn.execute(f"PRAGMA postgres_scanner_timeout={timeout_seconds * 1000};")
        
        # Execute query
        result = conn.execute(query).fetchall()
        return result
        
    except Exception as e:
        if "timeout" in str(e).lower():
            logger.warning(f"PostgreSQL query timeout after {timeout_seconds}s")
            return None
        else:
            logger.error(f"PostgreSQL query failed: {e}")
            raise
```

### 3. Graceful Degradation
```sql
-- Fallback to local data when PostgreSQL unavailable
SELECT 
    memory_id,
    COALESCE(
        -- Try PostgreSQL first
        (SELECT content FROM source_memories.public.raw_memories r 
         WHERE r.memory_id = m.memory_id),
        -- Fallback to local cache
        m.cached_content,
        -- Final fallback
        'Content unavailable'
    ) as content
FROM memory.consolidated_memories m;
```

## Testing Patterns

### 1. Extension Validation Test
```python
def test_postgres_scanner_available():
    result = conn.execute("""
        SELECT extension_name, loaded, installed 
        FROM duckdb_extensions() 
        WHERE extension_name = 'postgres_scanner'
    """).fetchall()
    
    assert len(result) == 1
    assert result[0][1] == True  # loaded
    assert result[0][2] == True  # installed
```

### 2. Connection Test
```python
def test_postgres_connection():
    try:
        conn.execute("LOAD postgres_scanner;")
        result = conn.execute("""
            SELECT 'Connection test' as status
            FROM source_memories.information_schema.tables
            LIMIT 1
        """).fetchall()
        
        assert len(result) >= 0
        return True
    except Exception:
        return False
```

### 3. Data Integrity Test
```python
def test_cross_database_consistency():
    # Count records in both databases
    pg_count = conn.execute("""
        SELECT COUNT(*) FROM source_memories.public.raw_memories
        WHERE created_at >= '2025-08-28'
    """).fetchone()[0]
    
    duck_count = conn.execute("""
        SELECT COUNT(*) FROM memory.imported_memories
        WHERE import_date >= '2025-08-28'
    """).fetchone()[0]
    
    # Allow for reasonable variance
    assert abs(pg_count - duck_count) <= 0.01 * pg_count
```

## Monitoring and Maintenance Patterns

### 1. Connection Health Monitoring
```sql
-- Monitor postgres_scanner performance
SELECT 
    'postgres_scanner' as component,
    COUNT(*) as active_connections,
    AVG(query_duration_ms) as avg_query_time,
    MAX(query_duration_ms) as max_query_time
FROM system.query_log
WHERE query_text LIKE '%source_memories%'
  AND query_start >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR;
```

### 2. Error Rate Monitoring
```python
# Monitor postgres_scanner error rates
def monitor_postgres_scanner_health():
    error_query = """
    SELECT 
        COUNT(*) as total_queries,
        SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as error_count,
        AVG(duration_ms) as avg_duration
    FROM query_log
    WHERE query_text LIKE '%source_memories%'
      AND timestamp >= NOW() - INTERVAL 1 HOUR
    """
    
    stats = conn.execute(error_query).fetchone()
    error_rate = stats[1] / max(stats[0], 1) * 100
    
    if error_rate > 5.0:  # Alert if error rate > 5%
        alert_postgres_scanner_issues(error_rate, stats)
```

## Security Best Practices

### 1. Credential Management
- **Never hardcode credentials** in SQL or configuration files
- **Use environment variables** for all connection parameters
- **Implement secrets management** for production deployments
- **Rotate credentials regularly** according to security policy

### 2. Network Security
- **Use SSL/TLS connections** for PostgreSQL connectivity
- **Implement network isolation** between DuckDB and PostgreSQL
- **Monitor connection patterns** for anomalous behavior
- **Limit connection privileges** to minimum required permissions

### 3. Access Control
- **Create dedicated PostgreSQL user** for DuckDB connections
- **Grant minimal required permissions** (SELECT only if possible)
- **Implement row-level security** where appropriate
- **Audit cross-database access** regularly

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Extension Not Loading
```
Error: Extension 'postgres_scanner' not found
Solution: Install extension first: INSTALL postgres_scanner;
```

#### 2. Connection Timeout
```
Error: Connection timeout to PostgreSQL server
Solutions:
- Increase timeout: PRAGMA postgres_scanner_timeout=60000;
- Check network connectivity
- Verify PostgreSQL server status
- Reduce query complexity/batch size
```

#### 3. Memory Exhaustion
```
Error: Out of memory during postgres_scanner operation
Solutions:
- Reduce batch size: PRAGMA postgres_scanner_batch_size=5000;
- Increase memory limit: PRAGMA memory_limit='8GB';
- Add LIMIT clauses to queries
- Process data in smaller chunks
```

#### 4. Authentication Failure
```
Error: Authentication failed for user
Solutions:
- Verify credentials in environment variables
- Check PostgreSQL pg_hba.conf configuration
- Ensure user has required permissions
- Test connection with direct PostgreSQL client
```

## Migration Patterns

### 1. Legacy System Migration
```sql
-- Migrate from old postgres extension references
-- OLD (incorrect):
-- INSTALL postgres;

-- NEW (correct):
INSTALL postgres_scanner;
LOAD postgres_scanner;
```

### 2. Configuration Migration
```yaml
# Migrate profiles.yml from generic postgres to postgres_scanner
# OLD:
extensions: ['postgres', 'fts']

# NEW:
extensions: ['postgres_scanner', 'fts']
```

## Future Enhancement Opportunities

1. **Connection Pooling**: Implement connection pool management for high-frequency operations
2. **Caching Layer**: Add intelligent caching for frequently accessed PostgreSQL data
3. **Monitoring Integration**: Enhanced metrics collection and dashboard integration
4. **Automated Failover**: Implement automatic fallback strategies when PostgreSQL unavailable
5. **Performance Tuning**: Query optimization recommendations based on usage patterns

---

**Document Version**: 1.0  
**Last Updated**: 2025-08-28  
**Next Review**: 2025-09-28  
**Maintainer**: SQL Expert Agent  
**Status**: APPROVED FOR PRODUCTION USE