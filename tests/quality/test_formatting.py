#!/usr/bin/env python3
"""
Test code formatting compliance with Black and overall code quality standards
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest


def get_python_files() -> List[Path]:
    """Get all Python files in the project"""
    project_dir = Path(__file__).parent.parent.parent
    python_files = []

    # Include both src and biological_memory directories
    directories = [
        project_dir / "src",
        project_dir / "biological_memory",
        project_dir / "tests",
    ]

    for directory in directories:
        if directory.exists():
            for root, dirs, files in os.walk(directory):
                # Skip __pycache__ and .git directories
                dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", ".venv", "venv"]]

                for file in files:
                    if file.endswith(".py"):
                        python_files.append(Path(root) / file)

    return python_files


class TestFormatting:
    """Test code formatting compliance"""

    def test_black_formatting(self):
        """Ensure all Python files comply with Black formatting"""
        python_files = get_python_files()
        assert len(python_files) > 0, "No Python files found"

        # Run black in check mode
        cmd = [
            sys.executable,
            "-m",
            "black",
            "--check",
            "--diff",
            "--line-length=100",
        ] + [str(f) for f in python_files]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                print(f"\nBlack formatting issues found:")
                print(result.stdout)
                if result.stderr:
                    print(f"Errors: {result.stderr}")

                pytest.fail(
                    f"Black formatting check failed. Run 'python -m black --line-length=100 .' to fix."
                )

        except subprocess.TimeoutExpired:
            pytest.fail("Black formatting check timed out")
        except FileNotFoundError:
            pytest.skip("Black not installed")

    def test_line_length_compliance(self):
        """Ensure no lines exceed the maximum length"""
        max_line_length = 250  # Accommodates complex SQL queries with JSON operations
        violations = []

        python_files = get_python_files()

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        # Remove trailing newline for length check
                        line_content = line.rstrip("\n\r")

                        if len(line_content) > max_line_length:
                            violations.append(
                                {
                                    "file": str(file_path),
                                    "line": line_num,
                                    "length": len(line_content),
                                    "content": (
                                        line_content[:50] + "..."
                                        if len(line_content) > 50
                                        else line_content
                                    ),
                                }
                            )

            except Exception as e:
                pytest.fail(f"Failed to check line length in {file_path}: {e}")

        if violations:
            print(f"\nLine length violations (max {max_line_length} chars):")
            for v in violations:
                print(f"  {v['file']}:{v['line']} ({v['length']} chars): {v['content']}")

        assert len(violations) == 0, (
            f"Found {len(violations)} lines exceeding {max_line_length} characters. "
            "Run Black formatting to fix most issues."
        )

    def test_no_trailing_whitespace(self):
        """Ensure no files have trailing whitespace"""
        violations = []
        python_files = get_python_files()

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if line.rstrip("\n\r") != line.rstrip():
                            violations.append({"file": str(file_path), "line": line_num})

            except Exception as e:
                pytest.fail(f"Failed to check trailing whitespace in {file_path}: {e}")

        if violations:
            print(f"\nTrailing whitespace violations:")
            for v in violations:
                print(f"  {v['file']}:{v['line']}")

        assert len(violations) == 0, (
            f"Found {len(violations)} lines with trailing whitespace. "
            "Run 'pre-commit run trailing-whitespace --all-files' to fix."
        )

    def test_proper_indentation(self):
        """Ensure no tab characters (Black handles space indentation)"""
        violations = []
        python_files = get_python_files()

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        # Only check for tab characters (Black handles the rest)
                        if "\t" in line:
                            violations.append(
                                {
                                    "file": str(file_path),
                                    "line": line_num,
                                    "issue": "contains tabs",
                                }
                            )

            except Exception as e:
                pytest.fail(f"Failed to check indentation in {file_path}: {e}")

        if violations:
            print(f"\nIndentation violations:")
            for v in violations:
                print(f"  {v['file']}:{v['line']} - {v['issue']}")

        assert len(violations) == 0, (
            f"Found {len(violations)} indentation violations. "
            "Use spaces for indentation, no tabs."
        )

    def test_file_endings(self):
        """Ensure files end with a single newline"""
        violations = []
        python_files = get_python_files()

        for file_path in python_files:
            try:
                with open(file_path, "rb") as f:
                    content = f.read()

                    if len(content) == 0:
                        continue  # Empty files are okay

                    # Check if file ends with exactly one newline
                    if not content.endswith(b"\n"):
                        violations.append(
                            {"file": str(file_path), "issue": "missing final newline"}
                        )
                    elif content.endswith(b"\n\n"):
                        violations.append(
                            {"file": str(file_path), "issue": "multiple final newlines"}
                        )

            except Exception as e:
                pytest.fail(f"Failed to check file endings in {file_path}: {e}")

        if violations:
            print(f"\nFile ending violations:")
            for v in violations:
                print(f"  {v['file']} - {v['issue']}")

        assert len(violations) == 0, (
            f"Found {len(violations)} file ending violations. "
            "Files should end with exactly one newline."
        )

    def test_encoding_consistency(self):
        """Ensure all files use UTF-8 encoding"""
        violations = []
        python_files = get_python_files()

        for file_path in python_files:
            try:
                # Try to read file as UTF-8
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for BOM (Byte Order Mark)
                if content.startswith("\ufeff"):
                    violations.append({"file": str(file_path), "issue": "contains UTF-8 BOM"})

            except UnicodeDecodeError:
                violations.append({"file": str(file_path), "issue": "not valid UTF-8"})
            except Exception as e:
                pytest.fail(f"Failed to check encoding in {file_path}: {e}")

        if violations:
            print(f"\nEncoding violations:")
            for v in violations:
                print(f"  {v['file']} - {v['issue']}")

        assert len(violations) == 0, (
            f"Found {len(violations)} encoding violations. "
            "All files should use UTF-8 encoding without BOM."
        )

    def test_docstring_presence(self):
        """Ensure important functions have docstrings"""
        python_files = get_python_files()
        missing_docstrings = []

        # Focus on source files only
        src_files = [f for f in python_files if "/src/" in str(f)]

        for file_path in src_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                import ast

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Skip private functions and special methods for
                        # docstring requirement
                        if node.name.startswith("_"):
                            continue

                        # Check if function has docstring
                        has_docstring = (
                            node.body
                            and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                            and isinstance(node.body[0].value.value, str)
                        )

                        if not has_docstring:
                            missing_docstrings.append(f"{file_path.name}::{node.name}")

            except Exception as e:
                pytest.fail(f"Failed to check docstrings in {file_path}: {e}")

        # Allow some missing docstrings, but flag excessive cases
        max_allowed_missing = 10

        if len(missing_docstrings) > max_allowed_missing:
            print(f"\nFunctions missing docstrings:")
            for func in missing_docstrings:
                print(f"  - {func}")

            pytest.fail(
                f"Found {len(missing_docstrings)} functions without docstrings, "
                f"but maximum {max_allowed_missing} allowed. "
                "Consider adding docstrings to improve code documentation."
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
