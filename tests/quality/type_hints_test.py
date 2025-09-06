#!/usr/bin/env python3
"""
Type Hints Quality Tests
Validates that all Python files have proper type annotations
"""

import ast
import os
from pathlib import Path
from typing import List, Set, Tuple

import pytest


class TypeHintChecker:
    """Analyzes Python files for type annotation completeness"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def get_python_files(self, exclude_patterns: List[str] = None) -> List[Path]:
        """Get all Python files in the project"""
        exclude_patterns = exclude_patterns or [
            "__pycache__",
            ".pytest_cache",
            "venv",
            ".venv",
            "target",
            "build"
        ]
        
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def analyze_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Analyze a file for type annotations"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            issues = []
            
            # Check functions and methods
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    issues.extend(self._check_function_annotations(node, file_path))
            
            return len(issues) == 0, issues
        
        except Exception as e:
            return False, [f"Failed to parse {file_path}: {e}"]
    
    def _check_function_annotations(self, node: ast.FunctionDef, file_path: Path) -> List[str]:
        """Check function for proper type annotations"""
        issues = []
        
        # Skip test functions, dunder methods, and some special cases
        if (node.name.startswith('test_') or 
            node.name.startswith('__') or 
            node.name in ['main', 'setUp', 'tearDown']):
            return issues
        
        # Check return type annotation
        if node.returns is None and node.name not in ['__init__']:
            issues.append(f"{file_path}:{node.lineno} - Function '{node.name}' missing return type annotation")
        
        # Check parameter annotations (skip 'self' and 'cls')
        for arg in node.args.args:
            if arg.arg not in ['self', 'cls'] and arg.annotation is None:
                issues.append(f"{file_path}:{node.lineno} - Parameter '{arg.arg}' in '{node.name}' missing type annotation")
        
        return issues


@pytest.fixture
def type_checker():
    """Create type hint checker"""
    project_root = Path(__file__).parent.parent.parent
    return TypeHintChecker(project_root)


class TestTypeHints:
    """Test type annotation completeness"""
    
    def test_src_directory_type_hints(self, type_checker):
        """Test that src/ files have proper type hints"""
        src_files = [
            f for f in type_checker.get_python_files()
            if 'src/' in str(f)
        ]
        
        failed_files = []
        all_issues = []
        
        for file_path in src_files:
            has_types, issues = type_checker.analyze_file(file_path)
            if not has_types:
                failed_files.append(str(file_path))
                all_issues.extend(issues)
        
        if failed_files:
            issue_summary = '\n'.join(all_issues[:20])  # Show first 20 issues
            pytest.fail(
                f"Type annotation issues found in {len(failed_files)} src/ files:\n"
                f"{issue_summary}\n"
                f"{'...' if len(all_issues) > 20 else ''}"
            )
    
    def test_biological_memory_type_hints(self, type_checker):
        """Test that biological_memory/ Python files have proper type hints"""
        bio_files = [
            f for f in type_checker.get_python_files()
            if 'biological_memory/' in str(f) and f.suffix == '.py'
        ]
        
        failed_files = []
        all_issues = []
        
        for file_path in bio_files:
            has_types, issues = type_checker.analyze_file(file_path)
            if not has_types:
                failed_files.append(str(file_path))
                all_issues.extend(issues)
        
        if failed_files:
            issue_summary = '\n'.join(all_issues[:15])  # Show first 15 issues
            pytest.fail(
                f"Type annotation issues found in {len(failed_files)} biological_memory/ files:\n"
                f"{issue_summary}\n"
                f"{'...' if len(all_issues) > 15 else ''}"
            )
    
    def test_critical_functions_have_types(self, type_checker):
        """Test that critical biological functions have complete type annotations"""
        critical_patterns = [
            'generate_embedding',
            'consolidate_memory',
            'hebbian_learning',
            'calculate_similarity',
            'process_memory'
        ]
        
        all_files = type_checker.get_python_files()
        missing_types = []
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in critical_patterns:
                    if pattern in content:
                        has_types, issues = type_checker.analyze_file(file_path)
                        if not has_types:
                            function_issues = [i for i in issues if pattern in i]
                            if function_issues:
                                missing_types.extend(function_issues)
            
            except Exception:
                continue  # Skip files that can't be read
        
        if missing_types:
            assert False, f"Critical biological functions missing type hints:\n" + '\n'.join(missing_types[:10])
    
    def test_complex_types_properly_imported(self, type_checker):
        """Test that complex types are properly imported from typing"""
        all_files = type_checker.get_python_files()
        import_issues = []
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if complex types are used without proper imports
                has_list_type = 'List[' in content
                has_dict_type = 'Dict[' in content
                has_optional_type = 'Optional[' in content
                has_union_type = 'Union[' in content
                
                has_typing_import = 'from typing import' in content
                
                if (has_list_type or has_dict_type or has_optional_type or has_union_type) and not has_typing_import:
                    import_issues.append(f"{file_path} uses complex types but missing typing import")
                    
            except Exception:
                continue
        
        if import_issues:
            assert False, f"Files using complex types without proper imports:\n" + '\n'.join(import_issues[:5])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])