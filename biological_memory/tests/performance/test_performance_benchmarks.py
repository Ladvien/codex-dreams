"""
Performance Benchmarking Suite for BMP-MEDIUM-009
Tests and validates <50ms average query response times
Comprehensive performance regression testing
"""

import time
import statistics
import pytest
import duckdb
from pathlib import Path
import json
from typing import List, Dict, Any


class PerformanceBenchmarker:
    """Comprehensive performance benchmarking for biological memory queries"""
    
    def __init__(self, db_path: str = "dbs/memory.duckdb"):
        self.db_path = Path(db_path)
        self.target_ms = 50.0  # Target <50ms average query response time
        self.performance_results = []
        
    def setup_performance_monitoring(self):
        """Initialize performance monitoring infrastructure"""
        conn = duckdb.connect(str(self.db_path))
        
        # Load performance configuration
        perf_config_path = Path("duckdb_performance_config.sql")
        if perf_config_path.exists():
            with open(perf_config_path) as f:
                conn.execute(f.read())
        
        return conn
    
    def benchmark_query(self, conn: duckdb.DuckDBPyConnection, 
                       query: str, query_name: str, query_type: str,
                       iterations: int = 10) -> Dict[str, Any]:
        """Benchmark a single query with multiple iterations"""
        execution_times = []
        
        # Warm up query (exclude from measurements)
        try:
            conn.execute(query)
        except Exception as e:
            return {
                'query_name': query_name,
                'query_type': query_type,
                'status': 'FAILED',
                'error': str(e),
                'avg_time_ms': float('inf')
            }
        
        # Execute benchmark iterations
        for i in range(iterations):
            start_time = time.perf_counter()
            try:
                result = conn.execute(query)
                rows = result.fetchall()
                end_time = time.perf_counter()
                
                execution_time_ms = (end_time - start_time) * 1000
                execution_times.append(execution_time_ms)
                
                # Log to performance_benchmarks table
                conn.execute("""
                    INSERT INTO performance_benchmarks 
                    (query_type, query_name, execution_time_ms, rows_processed, target_time_ms)
                    VALUES (?, ?, ?, ?, ?)
                """, (query_type, query_name, execution_time_ms, len(rows), self.target_ms))
                
            except Exception as e:
                return {
                    'query_name': query_name,
                    'query_type': query_type,
                    'status': 'FAILED',
                    'error': str(e),
                    'avg_time_ms': float('inf')
                }
        
        # Calculate statistics
        avg_time = statistics.mean(execution_times)
        median_time = statistics.median(execution_times)
        p95_time = sorted(execution_times)[int(0.95 * len(execution_times))]
        
        return {
            'query_name': query_name,
            'query_type': query_type,
            'status': 'SUCCESS',
            'avg_time_ms': avg_time,
            'median_time_ms': median_time,
            'p95_time_ms': p95_time,
            'min_time_ms': min(execution_times),
            'max_time_ms': max(execution_times),
            'iterations': iterations,
            'meets_target': avg_time <= self.target_ms
        }


class TestBiologicalMemoryPerformance:
    """Performance test suite for biological memory system"""
    
    @pytest.fixture
    def benchmarker(self):
        return PerformanceBenchmarker()
    
    @pytest.fixture
    def db_connection(self, benchmarker):
        return benchmarker.setup_performance_monitoring()
    
    def test_working_memory_performance(self, benchmarker, db_connection):
        """Test working memory query performance - Most critical path"""
        query = """
        WITH current_working_set AS (
          SELECT memory_id, content, concepts, activation_strength, created_at,
                 last_accessed_at, access_count, memory_type
          FROM raw_memories
          WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '30 SECONDS'
            AND activation_strength > 0.6
            AND access_count >= 2
        ),
        ranked_memories AS (
          SELECT *, 
            ROW_NUMBER() OVER (ORDER BY activation_strength DESC, created_at DESC) as memory_rank
          FROM current_working_set
        )
        SELECT * FROM ranked_memories WHERE memory_rank <= 7
        """
        
        result = benchmarker.benchmark_query(
            db_connection, query, "working_memory_active_context", "working_memory"
        )
        
        # Assert performance target
        assert result['status'] == 'SUCCESS', f"Working memory query failed: {result.get('error')}"
        assert result['avg_time_ms'] <= 50.0, f"Working memory average time {result['avg_time_ms']:.2f}ms exceeds 50ms target"
        assert result['p95_time_ms'] <= 100.0, f"Working memory P95 time {result['p95_time_ms']:.2f}ms exceeds 100ms limit"
    
    def test_semantic_similarity_performance(self, benchmarker, db_connection):
        """Test semantic similarity calculations - Performance intensive"""
        query = """
        WITH concept_pairs AS (
          SELECT 
            r1.memory_id as source_id,
            r2.memory_id as target_id,
            r1.concepts as source_concepts,
            r2.concepts as target_concepts
          FROM raw_memories r1
          CROSS JOIN raw_memories r2
          WHERE r1.memory_id != r2.memory_id
          LIMIT 25  -- Limit for performance testing
        )
        SELECT 
          source_id,
          target_id,
          -- Simplified similarity calculation for testing
          CASE 
            WHEN source_concepts = target_concepts THEN 1.0
            WHEN JSON_ARRAY_LENGTH(source_concepts) > 0 AND JSON_ARRAY_LENGTH(target_concepts) > 0
              THEN 0.5  -- Placeholder similarity
            ELSE 0.0
          END as similarity_score
        FROM concept_pairs
        ORDER BY similarity_score DESC
        """
        
        result = benchmarker.benchmark_query(
            db_connection, query, "semantic_similarity_calculation", "semantic"
        )
        
        assert result['status'] == 'SUCCESS', f"Semantic similarity query failed: {result.get('error')}"
        assert result['avg_time_ms'] <= 200.0, f"Semantic similarity average time {result['avg_time_ms']:.2f}ms exceeds 200ms limit"
    
    def test_memory_consolidation_performance(self, benchmarker, db_connection):
        """Test memory consolidation batch processing"""
        query = """
        WITH consolidation_batch AS (
          SELECT 
            memory_id,
            content,
            activation_strength,
            CASE 
              WHEN activation_strength > 0.7 THEN activation_strength * 1.2
              WHEN activation_strength < 0.4 THEN activation_strength * 0.8
              ELSE activation_strength
            END as consolidated_strength
          FROM raw_memories
          WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '1 HOUR'
        )
        SELECT 
          COUNT(*) as memories_processed,
          AVG(consolidated_strength) as avg_consolidated_strength,
          COUNT(CASE WHEN consolidated_strength > 0.7 THEN 1 END) as strong_memories,
          COUNT(CASE WHEN consolidated_strength < 0.3 THEN 1 END) as weak_memories
        FROM consolidation_batch
        """
        
        result = benchmarker.benchmark_query(
            db_connection, query, "memory_consolidation_batch", "consolidation"
        )
        
        assert result['status'] == 'SUCCESS', f"Memory consolidation query failed: {result.get('error')}"
        assert result['avg_time_ms'] <= 150.0, f"Memory consolidation average time {result['avg_time_ms']:.2f}ms exceeds 150ms limit"
    
    def test_analytics_dashboard_performance(self, benchmarker, db_connection):
        """Test analytics dashboard queries for real-time monitoring"""
        query = """
        SELECT 
          memory_type,
          COUNT(*) as memory_count,
          AVG(activation_strength) as avg_activation,
          MAX(created_at) as most_recent,
          COUNT(CASE WHEN access_count > 5 THEN 1 END) as frequently_accessed
        FROM raw_memories
        WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 HOURS'
        GROUP BY memory_type
        ORDER BY memory_count DESC
        """
        
        result = benchmarker.benchmark_query(
            db_connection, query, "analytics_dashboard_summary", "analytics"
        )
        
        assert result['status'] == 'SUCCESS', f"Analytics dashboard query failed: {result.get('error')}"
        assert result['avg_time_ms'] <= 50.0, f"Analytics dashboard average time {result['avg_time_ms']:.2f}ms exceeds 50ms target"
    
    def test_llm_cache_performance(self, benchmarker, db_connection):
        """Test LLM cache lookup performance - Critical for AI operations"""
        query = """
        WITH cache_stats AS (
          SELECT 
            COUNT(*) as total_cached,
            COUNT(DISTINCT prompt_text) as unique_prompts,
            AVG(access_count) as avg_access_count,
            MAX(last_accessed_at) as most_recent_access
          FROM llm_response_cache
          WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '1 HOUR'
        ),
        cache_lookup_test AS (
          SELECT 
            prompt_hash,
            response_text,
            access_count,
            CASE WHEN access_count > 1 THEN 'CACHE_HIT' ELSE 'CACHE_MISS' END as cache_result
          FROM llm_response_cache
          ORDER BY last_accessed_at DESC
          LIMIT 100
        )
        SELECT 
          cs.*,
          COUNT(clt.prompt_hash) as lookup_test_count,
          SUM(CASE WHEN clt.cache_result = 'CACHE_HIT' THEN 1 ELSE 0 END) as cache_hits
        FROM cache_stats cs
        CROSS JOIN cache_lookup_test clt
        GROUP BY cs.total_cached, cs.unique_prompts, cs.avg_access_count, cs.most_recent_access
        """
        
        result = benchmarker.benchmark_query(
            db_connection, query, "llm_cache_lookup", "caching"
        )
        
        assert result['status'] == 'SUCCESS', f"LLM cache lookup query failed: {result.get('error')}"
        assert result['avg_time_ms'] <= 25.0, f"LLM cache lookup average time {result['avg_time_ms']:.2f}ms exceeds 25ms target"
    
    def test_comprehensive_performance_regression(self, benchmarker, db_connection):
        """Comprehensive performance regression test suite"""
        all_benchmarks = []
        
        # Critical path queries that must meet <50ms target
        critical_queries = [
            ("SELECT COUNT(*) FROM raw_memories", "basic_count", "basic"),
            ("SELECT * FROM raw_memories ORDER BY created_at DESC LIMIT 10", "recent_memories", "basic"),
            ("SELECT memory_type, COUNT(*) FROM raw_memories GROUP BY memory_type", "memory_type_summary", "analytics")
        ]
        
        for query, name, query_type in critical_queries:
            result = benchmarker.benchmark_query(db_connection, query, name, query_type, iterations=20)
            all_benchmarks.append(result)
        
        # Assert overall system performance
        successful_queries = [b for b in all_benchmarks if b['status'] == 'SUCCESS']
        avg_system_performance = statistics.mean([b['avg_time_ms'] for b in successful_queries])
        
        assert len(successful_queries) == len(all_benchmarks), "Some queries failed during regression testing"
        assert avg_system_performance <= 50.0, f"System average performance {avg_system_performance:.2f}ms exceeds 50ms target"
        
        # Log overall performance results
        db_connection.execute("""
            INSERT INTO performance_benchmarks 
            (query_type, query_name, execution_time_ms, target_time_ms)
            VALUES ('system', 'overall_regression_test', ?, ?)
        """, (avg_system_performance, 50.0))
    
    def test_memory_intensive_operations(self, benchmarker, db_connection):
        """Test performance under memory-intensive operations"""
        query = """
        WITH memory_intensive AS (
          SELECT 
            r1.*,
            -- Simulate memory-intensive calculation
            STRING_AGG(r2.content, ' | ') OVER (ORDER BY r1.created_at ROWS 2 PRECEDING) as context_window
          FROM raw_memories r1
          LEFT JOIN raw_memories r2 ON r1.memory_type = r2.memory_type
          ORDER BY r1.created_at DESC
        )
        SELECT 
          memory_id,
          LENGTH(context_window) as context_length,
          activation_strength
        FROM memory_intensive
        LIMIT 50
        """
        
        result = benchmarker.benchmark_query(
            db_connection, query, "memory_intensive_context_window", "memory_intensive"
        )
        
        assert result['status'] == 'SUCCESS', f"Memory intensive query failed: {result.get('error')}"
        assert result['avg_time_ms'] <= 300.0, f"Memory intensive average time {result['avg_time_ms']:.2f}ms exceeds 300ms limit"


if __name__ == "__main__":
    # Run performance benchmarks directly
    benchmarker = PerformanceBenchmarker()
    conn = benchmarker.setup_performance_monitoring()
    
    # Run basic performance test
    test_class = TestBiologicalMemoryPerformance()
    test_class.test_working_memory_performance(benchmarker, conn)
    
    print("Performance benchmarking completed successfully!")
    print(f"Target: <{benchmarker.target_ms}ms average query response time")