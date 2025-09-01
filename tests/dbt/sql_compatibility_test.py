#!/usr/bin/env python3
"""
SQL Compatibility Test for DuckDB vs PostgreSQL
Tests to ensure no PostgreSQL-specific syntax remains in dbt project files
Part of STORY-DBT-010: DuckDB SQL Compatibility & Post-hook Fixes
"""

import os
import re
import pytest
from pathlib import Path

# Test configuration
DBT_PROJECT_DIR = Path(__file__).parent.parent.parent / "biological_memory"
MACROS_DIR = DBT_PROJECT_DIR / "macros"
MODELS_DIR = DBT_PROJECT_DIR / "models"

# PostgreSQL-specific patterns that should not exist in DuckDB-compatible code
POSTGRESQL_PATTERNS = {
    "gin_index": r"USING\s+gin\s*\(",
    "vacuum_analyze": r"VACUUM\s+ANALYZE",
    "analyze_table": r"ANALYZE\s+\{\{.*?\}\}",
    "refresh_materialized_view": r"REFRESH\s+MATERIALIZED\s+VIEW",
    "fts_index": r"USING\s+fts\s*\(",
    "postgresql_interval": r"INTERVAL\s+'[^']*'\s+SECOND",  # Some interval formats
    "create_extension": r"CREATE\s+EXTENSION",
    "pg_stat_functions": r"pg_stat_",
    "current_setting": r"current_setting\s*\(",
    "set_config": r"set_config\s*\(",
}

# Allowed exceptions (commented out lines)
COMMENT_PATTERN = r"^\s*--"

def get_all_sql_files():
    """Get all SQL files from the dbt project"""
    sql_files = []
    
    # Get dbt_project.yml
    project_yml = DBT_PROJECT_DIR / "dbt_project.yml"
    if project_yml.exists():
        sql_files.append(project_yml)
    
    # Get all SQL files from macros and models
    for directory in [MACROS_DIR, MODELS_DIR]:
        if directory.exists():
            sql_files.extend(directory.rglob("*.sql"))
    
    return sql_files

def read_file_content(file_path):
    """Read file content, handling both text and SQL files"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        pytest.fail(f"Could not read file {file_path}: {e}")

def is_commented_line(line):
    """Check if a line is commented out"""
    return bool(re.match(COMMENT_PATTERN, line))

class TestSQLCompatibility:
    """Test suite for SQL compatibility verification"""
    
    def test_project_structure_exists(self):
        """Verify the dbt project structure exists"""
        assert DBT_PROJECT_DIR.exists(), f"DBT project directory not found: {DBT_PROJECT_DIR}"
        assert MACROS_DIR.exists(), f"Macros directory not found: {MACROS_DIR}"
        
    def test_no_gin_indexes(self):
        """Test that no PostgreSQL GIN indexes remain uncommented"""
        violations = []
        
        for file_path in get_all_sql_files():
            content = read_file_content(file_path)
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                if re.search(POSTGRESQL_PATTERNS["gin_index"], line, re.IGNORECASE):
                    if not is_commented_line(line):
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'content': line.strip(),
                            'issue': 'Uncommented GIN index syntax'
                        })
        
        if violations:
            error_msg = "Found PostgreSQL GIN index syntax:\n"
            for v in violations:
                error_msg += f"  {v['file']}:{v['line']} - {v['content']}\n"
            pytest.fail(error_msg)
    
    def test_no_vacuum_analyze(self):
        """Test that no VACUUM ANALYZE commands remain uncommented"""
        violations = []
        
        for file_path in get_all_sql_files():
            content = read_file_content(file_path)
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                if re.search(POSTGRESQL_PATTERNS["vacuum_analyze"], line, re.IGNORECASE):
                    if not is_commented_line(line):
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'content': line.strip(),
                            'issue': 'Uncommented VACUUM ANALYZE syntax'
                        })
        
        if violations:
            error_msg = "Found PostgreSQL VACUUM ANALYZE syntax:\n"
            for v in violations:
                error_msg += f"  {v['file']}:{v['line']} - {v['content']}\n"
            pytest.fail(error_msg)
    
    def test_no_analyze_statements(self):
        """Test that no standalone ANALYZE statements remain uncommented"""
        violations = []
        
        for file_path in get_all_sql_files():
            content = read_file_content(file_path)
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                if re.search(POSTGRESQL_PATTERNS["analyze_table"], line, re.IGNORECASE):
                    if not is_commented_line(line):
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'content': line.strip(),
                            'issue': 'Uncommented ANALYZE statement'
                        })
        
        if violations:
            error_msg = "Found PostgreSQL ANALYZE statements:\n"
            for v in violations:
                error_msg += f"  {v['file']}:{v['line']} - {v['content']}\n"
            pytest.fail(error_msg)
    
    def test_no_refresh_materialized_view(self):
        """Test that no REFRESH MATERIALIZED VIEW statements remain uncommented"""
        violations = []
        
        for file_path in get_all_sql_files():
            content = read_file_content(file_path)
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                if re.search(POSTGRESQL_PATTERNS["refresh_materialized_view"], line, re.IGNORECASE):
                    if not is_commented_line(line):
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'content': line.strip(),
                            'issue': 'Uncommented REFRESH MATERIALIZED VIEW'
                        })
        
        if violations:
            error_msg = "Found PostgreSQL REFRESH MATERIALIZED VIEW syntax:\n"
            for v in violations:
                error_msg += f"  {v['file']}:{v['line']} - {v['content']}\n"
            pytest.fail(error_msg)
    
    def test_no_fts_indexes(self):
        """Test that no PostgreSQL FTS indexes remain uncommented"""
        violations = []
        
        for file_path in get_all_sql_files():
            content = read_file_content(file_path)
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                if re.search(POSTGRESQL_PATTERNS["fts_index"], line, re.IGNORECASE):
                    if not is_commented_line(line):
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'content': line.strip(),
                            'issue': 'Uncommented FTS index syntax'
                        })
        
        if violations:
            error_msg = "Found PostgreSQL FTS index syntax:\n"
            for v in violations:
                error_msg += f"  {v['file']}:{v['line']} - {v['content']}\n"
            pytest.fail(error_msg)
    
    def test_duckdb_compatible_patterns(self):
        """Test that DuckDB-compatible alternatives are being used"""
        compatible_patterns = {
            "regular_indexes": r"CREATE\s+INDEX.*ON.*\([^)]+\)",
            "duckdb_settings": r"SET\s+(memory_limit|threads|enable_)",
            "standard_sql": r"(SELECT|FROM|WHERE|JOIN|GROUP BY|ORDER BY)",
        }
        
        found_compatible = False
        
        for file_path in get_all_sql_files():
            content = read_file_content(file_path)
            
            for pattern_name, pattern in compatible_patterns.items():
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    found_compatible = True
                    break
        
        assert found_compatible, "No DuckDB-compatible patterns found in SQL files"
    
    def test_comments_explain_postgresql_removals(self):
        """Test that removed PostgreSQL features have explanatory comments"""
        required_explanations = [
            "PostgreSQL",
            "DuckDB",
            "not supported",
            "compatibility"
        ]
        
        comment_files = []
        
        for file_path in get_all_sql_files():
            content = read_file_content(file_path)
            lines = content.split('\n')
            
            for line in lines:
                if is_commented_line(line):
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in ["gin", "vacuum", "analyze", "refresh materialized"]):
                        # This is a comment about removed PostgreSQL features
                        if any(explanation in line_lower for explanation in required_explanations):
                            comment_files.append(file_path)
                            break
        
        assert comment_files, "Found PostgreSQL-related comments but missing explanatory text about DuckDB compatibility"
    
    def test_file_integrity(self):
        """Test that all modified files are valid and readable"""
        for file_path in get_all_sql_files():
            content = read_file_content(file_path)
            assert content is not None, f"Could not read content from {file_path}"
            assert len(content) > 0, f"File appears to be empty: {file_path}"

def test_comprehensive_postgresql_removal():
    """Comprehensive test to ensure all PostgreSQL-specific syntax is properly handled"""
    all_violations = []
    
    for file_path in get_all_sql_files():
        content = read_file_content(file_path)
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip commented lines
            if is_commented_line(line):
                continue
                
            # Check for any PostgreSQL-specific patterns
            for pattern_name, pattern in POSTGRESQL_PATTERNS.items():
                if re.search(pattern, line, re.IGNORECASE):
                    all_violations.append({
                        'file': file_path,
                        'line': line_num,
                        'content': line.strip(),
                        'pattern': pattern_name,
                        'issue': f'Uncommented PostgreSQL-specific syntax: {pattern_name}'
                    })
    
    if all_violations:
        error_msg = "Found PostgreSQL-specific syntax that needs to be commented out or removed:\n"
        for v in all_violations:
            error_msg += f"  {v['file']}:{v['line']} [{v['pattern']}] - {v['content']}\n"
        pytest.fail(error_msg)

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])