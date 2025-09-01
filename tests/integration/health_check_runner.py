#!/usr/bin/env python3
"""
Integration Test Health Check Runner for STORY-009
Comprehensive health checks before running integration tests

This module provides:
- Pre-test health checks for all live services
- Automated test data cleanup and validation
- Integration test orchestration with failure handling
- Service availability monitoring and reporting
- Performance baseline validation
"""

import os
import sys
import time
import json
import logging
import traceback
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import requests
import psycopg2
import duckdb

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class ServiceHealth:
    """Health status for a service"""
    name: str
    available: bool
    response_time_ms: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class IntegrationTestConfig:
    """Configuration for integration tests"""
    postgres_host: str = "192.168.1.104"
    postgres_port: int = 5432
    postgres_database: str = "codex_test_db"
    postgres_user: str = os.getenv("POSTGRES_USER", "codex_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")
    
    ollama_url: str = "http://192.168.1.110:11434"
    ollama_model: str = "gpt-oss:20b"
    ollama_embedding_model: str = "nomic-embed-text"
    
    # Health check timeouts
    postgres_timeout: int = 10
    ollama_timeout: int = 10
    
    # Test configuration
    cleanup_test_data: bool = True
    run_performance_tests: bool = True
    require_all_services: bool = False  # Set to True for production


class IntegrationHealthChecker:
    """Comprehensive health checker for integration tests"""
    
    def __init__(self, config: Optional[IntegrationTestConfig] = None):
        self.config = config or IntegrationTestConfig()
        self.health_results = []
        self.test_cleanup_items = []
        
    def check_postgresql_health(self) -> ServiceHealth:
        """Check PostgreSQL service health"""
        logger.info(f"Checking PostgreSQL health at {self.config.postgres_host}:{self.config.postgres_port}")
        
        start_time = time.perf_counter()
        
        try:
            # Test basic connectivity
            conn = psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_database,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
                connect_timeout=self.config.postgres_timeout
            )
            
            with conn.cursor() as cursor:
                # Test basic operations
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                
                cursor.execute("SELECT current_user, current_database()")
                user, database = cursor.fetchone()
                
                # Test table creation permissions
                test_table = f"health_check_{int(time.time())}"
                cursor.execute(f"CREATE TABLE {test_table} (id INTEGER)")
                cursor.execute(f"INSERT INTO {test_table} VALUES (1)")
                cursor.execute(f"SELECT COUNT(*) FROM {test_table}")
                test_count = cursor.fetchone()[0]
                cursor.execute(f"DROP TABLE {test_table}")
                
                # Test JSONB support
                cursor.execute("SELECT '{\"test\": true}'::JSONB")
                
                # Test performance baseline
                perf_start = time.perf_counter()
                cursor.execute("SELECT generate_series(1, 100)")
                cursor.fetchall()
                perf_time = (time.perf_counter() - perf_start) * 1000
            
            conn.close()
            response_time = (time.perf_counter() - start_time) * 1000
            
            return ServiceHealth(
                name="PostgreSQL",
                available=True,
                response_time_ms=response_time,
                details={
                    "version": version[:100],
                    "user": user,
                    "database": database,
                    "table_operations": test_count == 1,
                    "jsonb_support": True,
                    "performance_baseline_ms": perf_time
                }
            )
            
        except Exception as e:
            response_time = (time.perf_counter() - start_time) * 1000
            error_msg = f"PostgreSQL health check failed: {str(e)}"
            logger.error(error_msg)
            
            return ServiceHealth(
                name="PostgreSQL",
                available=False,
                response_time_ms=response_time,
                error_message=error_msg
            )
    
    def check_ollama_health(self) -> ServiceHealth:
        """Check Ollama service health"""
        logger.info(f"Checking Ollama health at {self.config.ollama_url}")
        
        start_time = time.perf_counter()
        
        try:
            # Test service availability
            response = requests.get(
                f"{self.config.ollama_url}/api/tags",
                timeout=self.config.ollama_timeout
            )
            response.raise_for_status()
            
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
            
            # Test model availability
            primary_model_available = any(self.config.ollama_model in model for model in available_models)
            embedding_model_available = any(self.config.ollama_embedding_model in model for model in available_models)
            
            # Test basic generation if models are available
            generation_successful = False
            generation_time_ms = 0
            
            if available_models:
                test_model = available_models[0]  # Use first available model
                
                gen_start = time.perf_counter()
                gen_response = requests.post(
                    f"{self.config.ollama_url}/api/generate",
                    json={
                        "model": test_model,
                        "prompt": "Health check: respond with 'OK'",
                        "stream": False
                    },
                    timeout=15
                )
                
                if gen_response.ok:
                    gen_data = gen_response.json()
                    generation_successful = "response" in gen_data
                    generation_time_ms = (time.perf_counter() - gen_start) * 1000
            
            response_time = (time.perf_counter() - start_time) * 1000
            
            return ServiceHealth(
                name="Ollama",
                available=True,
                response_time_ms=response_time,
                details={
                    "total_models": len(available_models),
                    "available_models": available_models[:5],  # First 5
                    "primary_model_available": primary_model_available,
                    "embedding_model_available": embedding_model_available,
                    "generation_test": generation_successful,
                    "generation_time_ms": generation_time_ms
                }
            )
            
        except Exception as e:
            response_time = (time.perf_counter() - start_time) * 1000
            error_msg = f"Ollama health check failed: {str(e)}"
            logger.warning(error_msg)  # Warning, not error, as this is optional
            
            return ServiceHealth(
                name="Ollama",
                available=False,
                response_time_ms=response_time,
                error_message=error_msg
            )
    
    def check_duckdb_health(self) -> ServiceHealth:
        """Check DuckDB and extensions health"""
        logger.info("Checking DuckDB and extensions health")
        
        start_time = time.perf_counter()
        
        try:
            # Create temporary DuckDB
            temp_db = tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False)
            temp_db.close()
            
            conn = duckdb.connect(temp_db.name)
            
            # Test extension loading
            extensions_loaded = {}
            required_extensions = ['postgres', 'json', 'httpfs']
            
            for ext in required_extensions:
                try:
                    conn.execute(f"LOAD {ext}")
                    extensions_loaded[ext] = True
                except Exception as e:
                    extensions_loaded[ext] = False
                    logger.warning(f"Extension {ext} failed to load: {e}")
            
            # Test PostgreSQL integration if available
            postgres_integration = False
            if extensions_loaded.get('postgres', False):
                try:
                    # Only test if PostgreSQL is available
                    postgres_url = f"postgresql://{self.config.postgres_user}:{self.config.postgres_password}@{self.config.postgres_host}:{self.config.postgres_port}/{self.config.postgres_database}"
                    conn.execute(f"ATTACH '{postgres_url}' AS pg_test (TYPE postgres)")
                    conn.execute("SELECT 1")
                    postgres_integration = True
                except Exception as e:
                    logger.warning(f"DuckDB-PostgreSQL integration test failed: {e}")
            
            # Test basic operations
            conn.execute("CREATE TABLE test_table (id INTEGER, data TEXT)")
            conn.execute("INSERT INTO test_table VALUES (1, 'test')")
            result = conn.execute("SELECT COUNT(*) FROM test_table").fetchall()
            basic_operations = result[0][0] == 1
            
            conn.close()
            Path(temp_db.name).unlink()
            
            response_time = (time.perf_counter() - start_time) * 1000
            
            return ServiceHealth(
                name="DuckDB",
                available=True,
                response_time_ms=response_time,
                details={
                    "extensions_loaded": extensions_loaded,
                    "postgres_integration": postgres_integration,
                    "basic_operations": basic_operations
                }
            )
            
        except Exception as e:
            response_time = (time.perf_counter() - start_time) * 1000
            error_msg = f"DuckDB health check failed: {str(e)}"
            logger.error(error_msg)
            
            return ServiceHealth(
                name="DuckDB",
                available=False,
                response_time_ms=response_time,
                error_message=error_msg
            )
    
    def check_environment_health(self) -> ServiceHealth:
        """Check environment configuration health"""
        logger.info("Checking environment configuration")
        
        start_time = time.perf_counter()
        
        issues = []
        config_status = {}
        
        # Check required environment variables
        required_vars = {
            'POSTGRES_PASSWORD': self.config.postgres_password,
        }
        
        optional_vars = {
            'POSTGRES_USER': self.config.postgres_user,
            'OLLAMA_URL': self.config.ollama_url,
        }
        
        for var_name, var_value in required_vars.items():
            if not var_value or var_value in ['', 'GENERATE_SECURE_PASSWORD_HERE']:
                issues.append(f"Missing or default value for {var_name}")
                config_status[var_name] = "MISSING/DEFAULT"
            else:
                config_status[var_name] = "SET"
        
        for var_name, var_value in optional_vars.items():
            config_status[var_name] = "SET" if var_value else "DEFAULT"
        
        # Check Python environment
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # Check required packages
        required_packages = ['psycopg2', 'duckdb', 'requests', 'pytest']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
                issues.append(f"Missing package: {package}")
        
        response_time = (time.perf_counter() - start_time) * 1000
        
        return ServiceHealth(
            name="Environment",
            available=len(issues) == 0,
            response_time_ms=response_time,
            error_message="; ".join(issues) if issues else None,
            details={
                "python_version": python_version,
                "environment_variables": config_status,
                "missing_packages": missing_packages,
                "issues_found": len(issues)
            }
        )
    
    def run_all_health_checks(self) -> List[ServiceHealth]:
        """Run all health checks and return results"""
        logger.info("Starting comprehensive health checks for integration tests")
        
        health_checks = [
            self.check_environment_health,
            self.check_duckdb_health,
            self.check_postgresql_health,
            self.check_ollama_health,
        ]
        
        results = []
        for check_func in health_checks:
            try:
                result = check_func()
                results.append(result)
                
                if result.available:
                    logger.info(f"✅ {result.name}: OK ({result.response_time_ms:.1f}ms)")
                else:
                    logger.warning(f"❌ {result.name}: FAILED ({result.error_message})")
                    
            except Exception as e:
                logger.error(f"Health check failed for {check_func.__name__}: {e}")
                results.append(ServiceHealth(
                    name=check_func.__name__.replace('check_', '').replace('_health', ''),
                    available=False,
                    response_time_ms=0,
                    error_message=f"Health check exception: {str(e)}"
                ))
        
        self.health_results = results
        return results
    
    def cleanup_test_data(self):
        """Clean up any test data created during health checks"""
        if not self.config.cleanup_test_data:
            return
            
        logger.info("Cleaning up health check test data")
        
        try:
            # Clean up PostgreSQL test schemas/tables
            with psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_database,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
                connect_timeout=5
            ) as conn:
                with conn.cursor() as cursor:
                    # Drop any health check tables/schemas
                    cursor.execute("""
                        SELECT schemaname, tablename 
                        FROM pg_tables 
                        WHERE schemaname LIKE '%test%' OR tablename LIKE '%health_check%'
                    """)
                    
                    test_objects = cursor.fetchall()
                    for schema, table in test_objects:
                        try:
                            cursor.execute(f"DROP TABLE IF EXISTS {schema}.{table} CASCADE")
                        except Exception as e:
                            logger.warning(f"Failed to drop test table {schema}.{table}: {e}")
            
            logger.info("Test data cleanup completed")
            
        except Exception as e:
            logger.warning(f"Test data cleanup failed: {e}")
    
    def generate_health_report(self) -> str:
        """Generate a comprehensive health report"""
        if not self.health_results:
            return "No health check results available"
        
        report_lines = [
            "",
            "="*80,
            "INTEGRATION TEST HEALTH CHECK REPORT",
            "="*80,
            f"Timestamp: {datetime.now(timezone.utc).isoformat()}",
            f"Configuration: {self.config.postgres_host}:{self.config.postgres_port} + {self.config.ollama_url}",
            ""
        ]
        
        # Service status summary
        available_services = [r for r in self.health_results if r.available]
        unavailable_services = [r for r in self.health_results if not r.available]
        
        report_lines.extend([
            "SERVICE STATUS:",
            "-" * 15,
            f"✅ Available: {len(available_services)}/{len(self.health_results)} services",
            f"❌ Unavailable: {len(unavailable_services)} services",
            ""
        ])
        
        # Detailed service reports
        for service in self.health_results:
            status_icon = "✅" if service.available else "❌"
            report_lines.extend([
                f"{status_icon} {service.name}:",
                f"   Status: {'AVAILABLE' if service.available else 'UNAVAILABLE'}",
                f"   Response Time: {service.response_time_ms:.1f}ms"
            ])
            
            if service.error_message:
                report_lines.append(f"   Error: {service.error_message}")
            
            if service.details:
                for key, value in service.details.items():
                    if isinstance(value, (list, dict)):
                        report_lines.append(f"   {key}: {json.dumps(value, indent=2)}")
                    else:
                        report_lines.append(f"   {key}: {value}")
            
            report_lines.append("")
        
        # Overall assessment
        critical_services = ["Environment", "DuckDB", "PostgreSQL"]
        critical_available = all(
            any(s.name == critical and s.available for s in self.health_results)
            for critical in critical_services
        )
        
        optional_services = ["Ollama"]
        optional_status = {
            service: any(s.name == service and s.available for s in self.health_results)
            for service in optional_services
        }
        
        report_lines.extend([
            "INTEGRATION TEST READINESS:",
            "-" * 28,
            f"Critical Services: {'🟢 READY' if critical_available else '🔴 NOT READY'}",
            f"Optional Services: {json.dumps(optional_status, indent=2)}",
            ""
        ])
        
        if critical_available:
            report_lines.append("🎉 INTEGRATION TESTS CAN PROCEED")
        else:
            report_lines.append("⚠️  INTEGRATION TESTS SHOULD NOT RUN")
            report_lines.append("   Fix critical service issues before running tests")
        
        report_lines.extend(["", "="*80, ""])
        
        return "\n".join(report_lines)
    
    def should_run_integration_tests(self) -> Tuple[bool, List[str]]:
        """Determine if integration tests should run based on health checks"""
        if not self.health_results:
            return False, ["No health check results available"]
        
        blocking_issues = []
        warnings = []
        
        # Check critical services
        env_health = next((s for s in self.health_results if s.name == "Environment"), None)
        if not env_health or not env_health.available:
            blocking_issues.append("Environment configuration issues")
        
        duckdb_health = next((s for s in self.health_results if s.name == "DuckDB"), None)
        if not duckdb_health or not duckdb_health.available:
            blocking_issues.append("DuckDB not available")
        
        postgres_health = next((s for s in self.health_results if s.name == "PostgreSQL"), None)
        if not postgres_health or not postgres_health.available:
            if self.config.require_all_services:
                blocking_issues.append("PostgreSQL not available (required)")
            else:
                warnings.append("PostgreSQL not available (some tests will be skipped)")
        
        # Check optional services
        ollama_health = next((s for s in self.health_results if s.name == "Ollama"), None)
        if not ollama_health or not ollama_health.available:
            if self.config.require_all_services:
                blocking_issues.append("Ollama not available (required)")
            else:
                warnings.append("Ollama not available (some tests will use mocks)")
        
        can_run = len(blocking_issues) == 0
        
        all_issues = blocking_issues + warnings
        return can_run, all_issues


def run_integration_test_suite_with_health_checks():
    """Run the complete integration test suite with health checks"""
    health_checker = IntegrationHealthChecker()
    
    try:
        # Run health checks
        logger.info("Running pre-test health checks...")
        health_results = health_checker.run_all_health_checks()
        
        # Generate and display health report
        health_report = health_checker.generate_health_report()
        print(health_report)
        
        # Determine if tests should run
        can_run, issues = health_checker.should_run_integration_tests()
        
        if not can_run:
            logger.error("❌ Integration tests cannot run due to critical issues:")
            for issue in issues:
                logger.error(f"   - {issue}")
            return False
        
        if issues:
            logger.warning("⚠️  Some services unavailable, but tests can proceed:")
            for issue in issues:
                logger.warning(f"   - {issue}")
        
        # Run the integration tests
        logger.info("🚀 Starting integration test execution...")
        
        test_modules = [
            "tests/integration/postgres_integration_test.py",
            "tests/integration/ollama_integration_test.py", 
            "tests/integration/end_to_end_memory_test.py",
            "tests/integration/performance_benchmark_test.py"
        ]
        
        all_tests_passed = True
        
        for test_module in test_modules:
            test_path = project_root / test_module
            
            if not test_path.exists():
                logger.warning(f"Test module not found: {test_module}")
                continue
            
            logger.info(f"Running {test_module}...")
            
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    str(test_path),
                    "-v",
                    "--tb=short",
                    "--maxfail=5"  # Stop after 5 failures
                ], 
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per module
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ {test_module} passed")
                else:
                    logger.error(f"❌ {test_module} failed")
                    logger.error(f"STDOUT: {result.stdout}")
                    logger.error(f"STDERR: {result.stderr}")
                    all_tests_passed = False
                    
            except subprocess.TimeoutExpired:
                logger.error(f"❌ {test_module} timed out")
                all_tests_passed = False
                
            except Exception as e:
                logger.error(f"❌ {test_module} failed with exception: {e}")
                all_tests_passed = False
        
        # Final cleanup
        health_checker.cleanup_test_data()
        
        # Summary
        if all_tests_passed:
            logger.info("🎉 All integration tests passed successfully!")
        else:
            logger.error("❌ Some integration tests failed")
        
        return all_tests_passed
        
    except Exception as e:
        logger.error(f"Integration test suite failed: {e}")
        logger.error(traceback.format_exc())
        return False
    
    finally:
        # Ensure cleanup runs
        try:
            health_checker.cleanup_test_data()
        except Exception as e:
            logger.warning(f"Final cleanup failed: {e}")


if __name__ == "__main__":
    success = run_integration_test_suite_with_health_checks()
    exit(0 if success else 1)