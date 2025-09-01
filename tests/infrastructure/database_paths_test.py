#!/usr/bin/env python3
"""
Database Path Validation Tests - BMP-CRITICAL-004
Tests to ensure no hardcoded database paths exist in the codebase
"""

import os
import re
import pytest
from pathlib import Path
from typing import List, Tuple

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Patterns that indicate hardcoded paths
HARDCODED_PATH_PATTERNS = [
    r'/Users/[^/\s]+',  # Absolute user paths
    r'192\.168\.1\.110',  # Hardcoded Ollama IP
    r'192\.168\.1\.104',  # Hardcoded PostgreSQL IP
]

# Files to exclude from path checks (these may legitimately contain examples)
EXCLUDED_FILES = {
    '.env.example',
    'README.md',
    'CLAUDE.md',
    'BACKLOG.md', 
    'team_chat.md',
    '.git',
    '__pycache__',
    '.pytest_cache',
    'target',  # dbt compiled files
    'database_paths_test.py',  # This test file itself
}

# Extensions of files to check
CHECKED_EXTENSIONS = {'.py', '.sql', '.yml', '.yaml', '.sh', '.env'}


class DatabasePathValidator:
    """Validates that database paths use environment variables instead of hardcoded values"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations = []
    
    def scan_file(self, file_path: Path) -> List[Tuple[int, str, str]]:
        """
        Scan a file for hardcoded paths
        Returns list of (line_number, line_content, violation_pattern)
        """
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    for pattern in HARDCODED_PATH_PATTERNS:
                        if re.search(pattern, line):
                            # Skip lines that are just setting defaults in environment variable calls
                            if 'os.getenv(' in line and ', ' in line:
                                continue
                            # Skip commented examples in config files
                            if line.strip().startswith('#') or line.strip().startswith('--'):
                                continue
                            # Skip test files with mock data (they need hardcoded values for testing)
                            if 'test_' in str(file_path) or '_test' in str(file_path):
                                continue
                            # Skip SQL getenv calls with defaults
                            if 'getenv(' in line and ', ' in line:
                                continue
                            violations.append((line_num, line.strip(), pattern))
        except Exception as e:
            print(f"Warning: Could not scan {file_path}: {e}")
        
        return violations
    
    def scan_directory(self, directory: Path) -> None:
        """Recursively scan directory for hardcoded paths"""
        for item in directory.rglob('*'):
            # Skip excluded files/directories
            if any(excluded in str(item) for excluded in EXCLUDED_FILES):
                continue
            
            # Only check files with relevant extensions
            if item.is_file() and item.suffix in CHECKED_EXTENSIONS:
                file_violations = self.scan_file(item)
                if file_violations:
                    self.violations.append((item, file_violations))
    
    def validate_environment_variable_usage(self) -> List[str]:
        """Check that key files use environment variables properly"""
        issues = []
        
        # Check orchestrator file uses environment variables
        orchestrator_file = self.project_root / 'biological_memory' / 'orchestrate_biological_memory.py'
        if orchestrator_file.exists():
            content = orchestrator_file.read_text()
            
            # Should use DUCKDB_PATH environment variable
            if "os.getenv('DUCKDB_PATH'" not in content:
                issues.append("orchestrate_biological_memory.py should use DUCKDB_PATH environment variable")
            
            # Should use OLLAMA_URL environment variable  
            if "os.getenv('OLLAMA_URL'" not in content:
                issues.append("orchestrate_biological_memory.py should use OLLAMA_URL environment variable")
                
            # Should not have hardcoded localhost fallback for production
            if "192.168.1.110" in content:
                issues.append("orchestrate_biological_memory.py contains hardcoded IP address")
        
        return issues
    
    def generate_report(self) -> str:
        """Generate a detailed report of path validation results"""
        report = ["=" * 60]
        report.append("DATABASE PATH VALIDATION REPORT")
        report.append("=" * 60)
        
        if not self.violations:
            report.append("✅ SUCCESS: No hardcoded database paths found!")
            return "\n".join(report)
        
        report.append(f"❌ FAILURES: Found {len(self.violations)} files with hardcoded paths:")
        report.append("")
        
        for file_path, file_violations in self.violations:
            relative_path = file_path.relative_to(self.project_root)
            report.append(f"📁 {relative_path}")
            for line_num, line_content, pattern in file_violations:
                report.append(f"   Line {line_num}: {line_content}")
                report.append(f"   Pattern: {pattern}")
                report.append("")
        
        report.append("RECOMMENDATIONS:")
        report.append("- Replace hardcoded paths with os.getenv() calls")
        report.append("- Update .env.example with appropriate defaults")
        report.append("- Use relative paths where possible")
        
        return "\n".join(report)


@pytest.fixture
def validator():
    """Create a DatabasePathValidator instance"""
    return DatabasePathValidator(PROJECT_ROOT)


def test_no_hardcoded_database_paths(validator):
    """Test that no files contain hardcoded database paths"""
    validator.scan_directory(PROJECT_ROOT)
    
    if validator.violations:
        report = validator.generate_report()
        pytest.fail(f"Found hardcoded database paths:\n{report}")


def test_environment_variable_usage(validator):
    """Test that key files properly use environment variables"""
    issues = validator.validate_environment_variable_usage()
    
    if issues:
        issue_list = "\n".join(f"- {issue}" for issue in issues)
        pytest.fail(f"Environment variable usage issues:\n{issue_list}")


def test_env_example_has_no_absolute_paths():
    """Test that .env.example doesn't contain hardcoded absolute paths"""
    env_example = PROJECT_ROOT / '.env.example'
    
    if not env_example.exists():
        pytest.skip(".env.example file not found")
    
    content = env_example.read_text()
    lines = content.split('\n')
    
    violations = []
    for line_num, line in enumerate(lines, 1):
        # Skip comments
        if line.strip().startswith('#'):
            continue
        
        # Check for absolute paths that aren't environment-appropriate
        if '/Users/' in line:
            violations.append(f"Line {line_num}: {line}")
    
    if violations:
        violation_list = "\n".join(violations)
        pytest.fail(f".env.example contains absolute paths:\n{violation_list}")


def test_required_environment_variables_documented():
    """Test that all required environment variables are documented in .env.example"""
    env_example = PROJECT_ROOT / '.env.example'
    
    if not env_example.exists():
        pytest.skip(".env.example file not found")
    
    content = env_example.read_text()
    
    required_vars = [
        'DUCKDB_PATH',
        'OLLAMA_URL',
        'POSTGRES_DB_URL',
        'LLM_CACHE_PATH'
    ]
    
    missing_vars = []
    for var in required_vars:
        if var not in content:
            missing_vars.append(var)
    
    if missing_vars:
        missing_list = "\n".join(f"- {var}" for var in missing_vars)
        pytest.fail(f"Required environment variables not documented in .env.example:\n{missing_list}")


def test_orchestrator_constructor_uses_env_vars():
    """Test that orchestrator constructor properly uses environment variables"""
    orchestrator_file = PROJECT_ROOT / 'biological_memory' / 'orchestrate_biological_memory.py'
    
    if not orchestrator_file.exists():
        pytest.skip("orchestrate_biological_memory.py not found")
    
    content = orchestrator_file.read_text()
    
    # Should have environment variable validation
    assert '_validate_environment_variables' in content, "Orchestrator should validate environment variables"
    
    # Should use DBT_PROJECT_DIR for base path
    assert "os.getenv('DBT_PROJECT_DIR'" in content, "Orchestrator should use DBT_PROJECT_DIR environment variable"
    
    # Should use DUCKDB_PATH
    assert "os.getenv('DUCKDB_PATH'" in content, "Orchestrator should use DUCKDB_PATH environment variable"


if __name__ == "__main__":
    # Run validation manually
    validator = DatabasePathValidator(PROJECT_ROOT)
    validator.scan_directory(PROJECT_ROOT)
    print(validator.generate_report())
    
    # Check environment variable usage
    issues = validator.validate_environment_variable_usage()
    if issues:
        print("\nEnvironment Variable Issues:")
        for issue in issues:
            print(f"- {issue}")