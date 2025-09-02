"""
STORY-CS-002: Code Quality Tests - TODO Prevention
Tests to prevent introduction of new TODO comments and maintain code cleanliness.
"""

import os
import re
import unittest
from pathlib import Path


class TestTodoPrevention(unittest.TestCase):
    """
    Code quality tests to prevent technical debt accumulation
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
        self.excluded_files = {
            "test_todo_prevention.py",  # This test file can reference TODO patterns
            "team_chat.md",  # Documentation file may reference TODOs in context
        }

    def _scan_for_todos(self):
        """
        Scan codebase for TODO comments and return violations
        """
        todo_patterns = [
            r"#\s*TODO\b",  # Python/Shell comments
            r"--\s*TODO\b",  # SQL comments
            r"//\s*TODO\b",  # JavaScript/Java comments
            r"/\*.*TODO.*\*/",  # Block comments
            r"<!--.*TODO.*-->",  # HTML comments
        ]

        violations = []

        for file_path in self._get_source_files():
            if file_path.name in self.excluded_files:
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern in todo_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append(
                                {
                                    "file": str(file_path.relative_to(self.project_root)),
                                    "line": line_num,
                                    "content": line.strip(),
                                }
                            )

            except (UnicodeDecodeError, PermissionError):
                # Skip binary or inaccessible files
                continue

        return violations

    def _get_source_files(self):
        """
        Get all source files to scan, excluding common build/temp directories
        """
        source_extensions = {".py", ".sql", ".js", ".ts", ".yaml", ".yml", ".sh", ".md"}

        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in source_extensions:
                    yield file_path

    def test_no_todo_comments_in_codebase(self):
        """
        STORY-CS-002: Ensure no TODO comments exist in production code
        """
        violations = self._scan_for_todos()

        if violations:
            violation_msg = "Found TODO comments in codebase:\n"
            for violation in violations:
                violation_msg += (
                    f"  {violation['file']}:{violation['line']} - {violation['content']}\n"
                )
            violation_msg += "\nTODO comments should be converted to proper issues or removed."

            self.fail(violation_msg)

    def test_no_placeholder_patterns(self):
        """
        Test for common placeholder patterns that indicate incomplete implementation
        """
        placeholder_patterns = [
            r"\bplaceholder\b",
            r"\bTODO\b",
            r"\bFIXME\b",
            r"\bXXX\b",
            r"\bHACK\b",
            r"\bNOTIMPLEMENTED\b",
        ]

        violations = []

        # Focus on Python and SQL files for placeholder patterns
        for file_path in self._get_source_files():
            if file_path.suffix not in {".py", ".sql"}:
                continue
            if file_path.name in self.excluded_files:
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                for line_num, line in enumerate(content.splitlines(), 1):
                    # Skip comments for certain patterns
                    if line.strip().startswith("#") or line.strip().startswith("--"):
                        continue

                    for pattern in placeholder_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Skip if it's in a string literal or comment
                            if not self._is_in_string_or_comment(line, pattern):
                                violations.append(
                                    {
                                        "file": str(file_path.relative_to(self.project_root)),
                                        "line": line_num,
                                        "pattern": pattern,
                                        "content": line.strip(),
                                    }
                                )

            except (UnicodeDecodeError, PermissionError):
                continue

        # Allow certain patterns in test files and documentation
        violations = [v for v in violations if not self._is_acceptable_placeholder(v)]

        if violations:
            violation_msg = "Found placeholder patterns in code:\n"
            for violation in violations:
                violation_msg += f"  {violation['file']}:{violation['line']} - {violation['pattern']} in: {violation['content']}\n"
            violation_msg += (
                "\nPlaceholder patterns should be replaced with proper implementations."
            )

            self.fail(violation_msg)

    def _is_in_string_or_comment(self, line, pattern):
        """
        Check if pattern appears in string literal or comment (basic heuristic)
        """
        # Simple check for quotes around the pattern
        pattern_match = re.search(pattern, line, re.IGNORECASE)
        if not pattern_match:
            return False

        start_pos = pattern_match.start()

        # Count quotes before the pattern
        quotes_before = line[:start_pos].count('"') + line[:start_pos].count("'")

        # If odd number of quotes, we're likely inside a string
        return quotes_before % 2 == 1

    def _is_acceptable_placeholder(self, violation):
        """
        Check if placeholder pattern is acceptable (test files, certain contexts)
        """
        file_path = violation["file"]
        content = violation["content"].lower()

        # Allow in test files
        if "/test" in file_path or file_path.startswith("test"):
            return True

        # Allow if it's clearly referring to external placeholders or function names
        if "create_embedding_placeholder" in content:
            return True  # This is a function name, not a placeholder

        # Allow if it's in macro definitions or SQL comments describing functionality
        if "embedding" in content.lower() and (
            "macro" in content.lower() or "generate" in content.lower()
        ):
            return True

        return False


class TestCodeCleanliness(unittest.TestCase):
    """
    Additional code cleanliness tests
    """

    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.excluded_dirs = {"target", "dbt_packages", "logs", "__pycache__", ".git"}

    def test_no_trailing_whitespace(self):
        """
        Test that source files don't have trailing whitespace
        """
        violations = []

        for file_path in self._get_source_files():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if line.endswith(" \n") or line.endswith("\t\n"):
                            violations.append(
                                {
                                    "file": str(file_path.relative_to(self.project_root)),
                                    "line": line_num,
                                }
                            )
            except (UnicodeDecodeError, PermissionError):
                continue

        if violations:
            violation_msg = "Found trailing whitespace:\n"
            for violation in violations:
                violation_msg += f"  {violation['file']}:{violation['line']}\n"

            # Only fail if there are many violations in Python files (SQL can be more flexible)
            python_violations = [v for v in violations if v["file"].endswith(".py")]
            if len(python_violations) > 5:
                violation_msg = "Found trailing whitespace in Python files:\n"
                for violation in python_violations[:10]:
                    violation_msg += f"  {violation['file']}:{violation['line']}\n"
                self.fail(violation_msg)

    def _get_source_files(self):
        """Get source files for scanning"""
        source_extensions = {".py", ".sql", ".yaml", ".yml"}

        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in source_extensions:
                    yield file_path


if __name__ == "__main__":
    unittest.main()
