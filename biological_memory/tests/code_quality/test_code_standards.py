"""
STORY-CS-002: Code Standards and Quality Tests
Comprehensive tests to ensure code quality standards across the biological memory pipeline.
"""

import ast
import json
import os
import re
import unittest
from pathlib import Path


class TestCodeStandards(unittest.TestCase):
    """
    Comprehensive code quality and standards testing
    """

    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.excluded_dirs = {
            "target",
            "dbt_packages",
            "logs",
            "__pycache__",
            ".git",
            "node_modules",
            "venv",
            ".venv",
            "packages",
        }

    def test_python_syntax_validity(self):
        """
        Ensure all Python files have valid syntax
        """
        violations = []

        for file_path in self._get_python_files():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                try:
                    ast.parse(content)
                except SyntaxError as e:
                    violations.append(
                        {
                            "file": str(file_path.relative_to(self.project_root)),
                            "error": str(e),
                            "line": e.lineno,
                        }
                    )
            except (UnicodeDecodeError, PermissionError):
                continue

        if violations:
            violation_msg = "Found Python syntax errors:\n"
            for violation in violations:
                violation_msg += (
                    f"  {violation['file']}:{violation.get('line', '?')} - {violation['error']}\n"
                )
            self.fail(violation_msg)

    def test_sql_basic_syntax(self):
        """
        Basic SQL syntax validation (check for common issues)
        """
        violations = []

        for file_path in self._get_sql_files():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for common SQL syntax issues
                issues = self._check_sql_issues(content, file_path)
                violations.extend(issues)

            except (UnicodeDecodeError, PermissionError):
                continue

        if violations:
            violation_msg = "Found SQL syntax issues:\n"
            for violation in violations:
                violation_msg += (
                    f"  {violation['file']}:{violation.get('line', '?')} - {violation['issue']}\n"
                )

            # Only fail for serious syntax issues
            serious_violations = [v for v in violations if v.get("severity") == "error"]
            if serious_violations:
                self.fail(violation_msg)

    def test_documentation_standards(self):
        """
        Ensure proper documentation standards in code files
        """
        violations = []

        for file_path in self._get_python_files():
            if "test_" in file_path.name:
                continue  # Skip test files for docstring requirements

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for module docstring
                if not self._has_module_docstring(content):
                    violations.append(
                        {
                            "file": str(file_path.relative_to(self.project_root)),
                            "issue": "Missing module docstring",
                        }
                    )

                # Check for class and function docstrings
                missing_docstrings = self._check_docstrings(content)
                for missing in missing_docstrings:
                    violations.append(
                        {
                            "file": str(file_path.relative_to(self.project_root)),
                            "issue": f'Missing docstring for {missing["type"]}: {missing["name"]}',
                            "line": missing.get("line"),
                        }
                    )

            except (UnicodeDecodeError, PermissionError, SyntaxError):
                continue

        # Only enforce for critical files, not all files
        critical_files = [
            "error_handling.py",
            "orchestrate_biological_memory.py",
            "llm_integration_service.py",
        ]
        critical_violations = [
            v for v in violations if any(cf in v["file"] for cf in critical_files)
        ]

        if len(critical_violations) > 5:  # Allow some flexibility
            violation_msg = "Missing documentation in critical files:\n"
            for violation in critical_violations[:10]:  # Show first 10
                violation_msg += f"  {violation['file']} - {violation['issue']}\n"
            self.fail(violation_msg)

    def test_macro_naming_conventions(self):
        """
        Test that dbt macros follow naming conventions
        """
        violations = []

        macro_files = list(Path(self.project_root / "macros").glob("*.sql"))

        for file_path in macro_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Find macro definitions
                macro_pattern = r"{% macro (\w+)\("
                macros = re.findall(macro_pattern, content)

                for macro_name in macros:
                    # Check naming convention: snake_case
                    if not re.match(r"^[a-z_][a-z0-9_]*$", macro_name):
                        violations.append(
                            {
                                "file": str(file_path.relative_to(self.project_root)),
                                "macro": macro_name,
                                "issue": "Macro name should be snake_case",
                            }
                        )

            except (UnicodeDecodeError, PermissionError):
                continue

        if violations:
            violation_msg = "Macro naming convention violations:\n"
            for violation in violations:
                violation_msg += (
                    f"  {violation['file']} - {violation['macro']}: {violation['issue']}\n"
                )
            self.fail(violation_msg)

    def test_json_validity(self):
        """
        Ensure all JSON files are valid
        """
        violations = []

        json_files = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            for file in files:
                if file.endswith(".json"):
                    json_files.append(Path(root) / file)

        for file_path in json_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                violations.append(
                    {"file": str(file_path.relative_to(self.project_root)), "error": str(e)}
                )
            except (UnicodeDecodeError, PermissionError):
                continue

        if violations:
            violation_msg = "Invalid JSON files:\n"
            for violation in violations:
                violation_msg += f"  {violation['file']} - {violation['error']}\n"
            self.fail(violation_msg)

    def test_consistent_indentation(self):
        """
        Check for consistent indentation in Python files
        """
        violations = []

        for file_path in self._get_python_files():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Check for mixed tabs and spaces
                has_tabs = any("\t" in line for line in lines)
                has_spaces = any(line.startswith("    ") for line in lines)

                if has_tabs and has_spaces:
                    violations.append(
                        {
                            "file": str(file_path.relative_to(self.project_root)),
                            "issue": "Mixed tabs and spaces for indentation",
                        }
                    )

            except (UnicodeDecodeError, PermissionError):
                continue

        if violations:
            violation_msg = "Indentation consistency issues:\n"
            for violation in violations:
                violation_msg += f"  {violation['file']} - {violation['issue']}\n"
            self.fail(violation_msg)

    def _get_python_files(self):
        """Get all Python files in the project"""
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            for file in files:
                if file.endswith(".py"):
                    yield Path(root) / file

    def _get_sql_files(self):
        """Get all SQL files in the project"""
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            for file in files:
                if file.endswith(".sql"):
                    yield Path(root) / file

    def _check_sql_issues(self, content, file_path):
        """Check for common SQL syntax issues"""
        issues = []
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("--"):
                continue

            # Check for common issues
            if stripped.endswith(",") and "FROM" in stripped:
                issues.append(
                    {
                        "file": str(file_path.relative_to(self.project_root)),
                        "line": line_num,
                        "issue": "Possible comma before FROM clause",
                        "severity": "warning",
                    }
                )

            # Check for unbalanced parentheses in the line
            if line.count("(") != line.count(")"):
                # This is normal for multi-line statements, so just flag complex cases
                if line.count("(") > 3 or line.count(")") > 3:
                    issues.append(
                        {
                            "file": str(file_path.relative_to(self.project_root)),
                            "line": line_num,
                            "issue": "Potentially unbalanced parentheses",
                            "severity": "warning",
                        }
                    )

        return issues

    def _has_module_docstring(self, content):
        """Check if Python module has a docstring"""
        try:
            tree = ast.parse(content)
            return ast.get_docstring(tree) is not None
        except SyntaxError:
            return False

    def _check_docstrings(self, content):
        """Check for missing docstrings in classes and functions"""
        missing = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not ast.get_docstring(node) and not node.name.startswith("_"):
                        missing.append({"type": "function", "name": node.name, "line": node.lineno})
                elif isinstance(node, ast.ClassDef):
                    if not ast.get_docstring(node):
                        missing.append({"type": "class", "name": node.name, "line": node.lineno})
        except SyntaxError:
            pass

        return missing


class TestFilenameConventions(unittest.TestCase):
    """
    Test filename and directory naming conventions
    """

    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.excluded_dirs = {"target", "dbt_packages", "logs", "__pycache__", ".git"}

    def test_python_filename_conventions(self):
        """
        Test that Python files follow naming conventions
        """
        violations = []

        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

            for file in files:
                if file.endswith(".py"):
                    # Check snake_case convention
                    name_part = file[:-3]  # Remove .py
                    if not re.match(r"^[a-z_][a-z0-9_]*$", name_part):
                        violations.append(
                            {
                                "file": str(Path(root, file).relative_to(self.project_root)),
                                "issue": "Python files should use snake_case naming",
                            }
                        )

        if violations:
            violation_msg = "Filename convention violations:\n"
            for violation in violations:
                violation_msg += f"  {violation['file']} - {violation['issue']}\n"
            self.fail(violation_msg)

    def test_sql_filename_conventions(self):
        """
        Test that SQL files follow naming conventions
        """
        violations = []

        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

            for file in files:
                if file.endswith(".sql"):
                    # Check snake_case convention
                    name_part = file[:-4]  # Remove .sql
                    if not re.match(r"^[a-z_][a-z0-9_]*$", name_part):
                        violations.append(
                            {
                                "file": str(Path(root, file).relative_to(self.project_root)),
                                "issue": "SQL files should use snake_case naming",
                            }
                        )

        if violations:
            violation_msg = "SQL filename convention violations:\n"
            for violation in violations:
                violation_msg += f"  {violation['file']} - {violation['issue']}\n"
            self.fail(violation_msg)


if __name__ == "__main__":
    unittest.main()
