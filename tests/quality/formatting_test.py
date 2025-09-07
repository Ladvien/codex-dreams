#!/usr/bin/env python3
"""
Code Formatting Quality Tests
Validates Black and import formatting compliance
"""

import subprocess
from pathlib import Path
from typing import List, Tuple

import pytest


class FormattingChecker:
    """Checks code formatting compliance"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def check_black_formatting(self, paths: List[str] = None) -> Tuple[bool, str]:
        """Check if code follows Black formatting"""
        if paths is None:
            paths = ["src/", "biological_memory/"]

        cmd = ["black", "--check", "--diff", "--line-length=100"] + paths

        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)

            return result.returncode == 0, result.stderr or result.stdout

        except FileNotFoundError:
            return False, "Black not found. Install with: pip install black"
        except Exception as e:
            return False, f"Error running Black: {e}"

    def check_isort_formatting(self, paths: List[str] = None) -> Tuple[bool, str]:
        """Check if imports are properly sorted with isort"""
        if paths is None:
            paths = ["src/", "biological_memory/"]

        cmd = ["isort", "--check-only", "--diff"] + paths

        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)

            return result.returncode == 0, result.stderr or result.stdout

        except FileNotFoundError:
            return False, "isort not found. Install with: pip install isort"
        except Exception as e:
            return False, f"Error running isort: {e}"

    def check_line_lengths(self, max_length: int = 100) -> Tuple[bool, List[str]]:
        """Check for lines exceeding maximum length"""
        violations = []

        for py_file in self.project_root.rglob("*.py"):
            # Skip certain directories
            if any(part in py_file.parts for part in [".venv", "__pycache__", ".pytest_cache"]):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, 1):
                        if len(line.rstrip()) > max_length:
                            violations.append(
                                f"{py_file}:{line_no} - Line too long ({len(line.rstrip())} > {max_length})"
                            )
            except Exception:
                continue  # Skip files that can't be read

        return len(violations) == 0, violations


@pytest.fixture
def formatter():
    """Create formatting checker"""
    project_root = Path(__file__).parent.parent.parent
    return FormattingChecker(project_root)


class TestCodeFormatting:
    """Test code formatting standards"""

    def test_black_formatting_compliance(self, formatter):
        """Test that all Python code follows Black formatting"""
        is_formatted, output = formatter.check_black_formatting()

        if not is_formatted:
            pytest.fail(
                f"Code not formatted according to Black standards:\n"
                f"{output}\n\n"
                f"Run: black src/ biological_memory/ --line-length=100"
            )

    def test_import_sorting_compliance(self, formatter):
        """Test that all imports are properly sorted with isort"""
        is_sorted, output = formatter.check_isort_formatting()

        if not is_sorted:
            pytest.fail(
                f"Imports not sorted according to isort standards:\n"
                f"{output}\n\n"
                f"Run: isort src/ biological_memory/"
            )

    def test_line_length_compliance(self, formatter):
        """Test that no lines exceed maximum length"""
        compliant, violations = formatter.check_line_lengths(max_length=100)

        if not compliant:
            # Show first 10 violations
            violation_summary = "\n".join(violations[:10])
            pytest.fail(
                f"Found {len(violations)} line length violations:\n"
                f"{violation_summary}\n"
                f"{'...' if len(violations) > 10 else ''}"
            )

    def test_no_trailing_whitespace(self, formatter):
        """Test that there's no trailing whitespace"""
        violations = []

        for py_file in formatter.project_root.rglob("*.py"):
            if any(part in py_file.parts for part in [".venv", "__pycache__", ".pytest_cache"]):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, 1):
                        if line.rstrip() != line.rstrip("\n"):
                            violations.append(f"{py_file}:{line_no} - Trailing whitespace")
            except Exception:
                continue

        if violations:
            violation_summary = "\n".join(violations[:10])
            pytest.fail(
                f"Found {len(violations)} trailing whitespace violations:\n"
                f"{violation_summary}\n"
                f"{'...' if len(violations) > 10 else ''}"
            )

    def test_consistent_indentation(self, formatter):
        """Test that indentation is consistent (4 spaces)"""
        violations = []

        for py_file in formatter.project_root.rglob("*.py"):
            if any(part in py_file.parts for part in [".venv", "__pycache__", ".pytest_cache"]):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, 1):
                        if line.startswith("\t"):
                            violations.append(
                                f"{py_file}:{line_no} - Tab character used instead of spaces"
                            )
                        elif line.startswith(" "):
                            leading_spaces = len(line) - len(line.lstrip(" "))
                            if leading_spaces % 4 != 0:
                                violations.append(
                                    f"{py_file}:{line_no} - Inconsistent indentation ({leading_spaces} spaces)"
                                )
            except Exception:
                continue

        if violations:
            violation_summary = "\n".join(violations[:10])
            pytest.fail(
                f"Found {len(violations)} indentation violations:\n"
                f"{violation_summary}\n"
                f"{'...' if len(violations) > 10 else ''}"
            )

    def test_docstring_formatting(self, formatter):
        """Test that docstrings follow consistent formatting"""
        violations = []

        for py_file in formatter.project_root.rglob("*.py"):
            if any(part in py_file.parts for part in [".venv", "__pycache__", ".pytest_cache"]):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                    for i, line in enumerate(lines, 1):
                        # Check for inconsistent docstring quotes
                        if '"""' in line and "'''" in line:
                            violations.append(f"{py_file}:{i} - Mixed docstring quote styles")

                        # Check for single-line docstrings using triple quotes incorrectly
                        if (
                            line.strip().startswith('"""')
                            and line.strip().endswith('"""')
                            and len(line.strip()) > 6
                        ):
                            # This is actually correct for single-line docstrings
                            pass

            except Exception:
                continue

        # Only fail if there are significant violations
        if violations:
            violation_summary = "\n".join(violations[:5])
            pytest.fail(
                f"Found {len(violations)} docstring formatting issues:\n"
                f"{violation_summary}\n"
                f"{'...' if len(violations) > 5 else ''}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
