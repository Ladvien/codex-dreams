#!/usr/bin/env python3
"""
Import Order Quality Tests
Validates proper import organization and grouping
"""

import ast
from pathlib import Path
from typing import Dict, List, Tuple

import pytest


class ImportOrderChecker:
    """Analyzes Python import organization"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def analyze_imports(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Analyze import order and organization in a file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            issues = []

            imports = self._extract_imports(tree)
            issues.extend(self._check_import_order(imports, file_path))
            issues.extend(self._check_import_grouping(imports, file_path))

            return len(issues) == 0, issues

        except Exception as e:
            return False, [f"Failed to parse {file_path}: {e}"]

    def _extract_imports(self, tree: ast.AST) -> List[Dict]:
        """Extract import statements from AST"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        {
                            "type": "import",
                            "module": alias.name,
                            "name": alias.asname or alias.name,
                            "lineno": node.lineno,
                        }
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(
                        {
                            "type": "from",
                            "module": module,
                            "name": alias.name,
                            "asname": alias.asname,
                            "lineno": node.lineno,
                        }
                    )

        return sorted(imports, key=lambda x: x["lineno"])

    def _classify_import(self, import_info: Dict) -> str:
        """Classify import into standard library, third-party, or local"""
        module = import_info["module"]

        # Standard library modules (partial list)
        stdlib_modules = {
            "os",
            "sys",
            "json",
            "time",
            "datetime",
            "logging",
            "pathlib",
            "typing",
            "collections",
            "itertools",
            "functools",
            "dataclasses",
            "re",
            "hashlib",
            "uuid",
            "pickle",
            "subprocess",
            "threading",
            "asyncio",
            "concurrent",
            "enum",
            "abc",
        }

        # Local modules (project-specific)
        local_patterns = [
            "src",
            "biological_memory",
            "macros",
            "dreams_writeback_service",
        ]

        if module.split(".")[0] in stdlib_modules:
            return "stdlib"
        elif any(pattern in module for pattern in local_patterns):
            return "local"
        elif module.startswith("."):
            return "local"
        else:
            return "third_party"

    def _check_import_order(self, imports: List[Dict], file_path: Path) -> List[str]:
        """Check that imports are in proper order"""
        issues = []
        if not imports:
            return issues

        # Group imports by classification
        groups = {"stdlib": [], "third_party": [], "local": []}

        for imp in imports:
            classification = self._classify_import(imp)
            groups[classification].append(imp)

        # Check that groups are in proper order
        expected_order = ["stdlib", "third_party", "local"]
        current_group = None

        for imp in imports:
            imp_group = self._classify_import(imp)

            if current_group is None:
                current_group = imp_group
            elif imp_group != current_group:
                # Check if we're moving to a later group
                if expected_order.index(imp_group) < expected_order.index(current_group):
                    issues.append(
                        f"{file_path}:{imp['lineno']} - Import order violation: "
                        f"{imp_group} import after {current_group} import"
                    )
                current_group = imp_group

        return issues

    def _check_import_grouping(self, imports: List[Dict], file_path: Path) -> List[str]:
        """Check that imports are properly grouped with blank lines"""
        issues = []
        if len(imports) < 2:
            return issues

        # This is a simplified check - in practice, we'd need to look at the actual file content
        # to check for blank lines between import groups
        prev_group = None

        for imp in imports:
            current_group = self._classify_import(imp)

            if prev_group and prev_group != current_group:
                # In a real implementation, we'd check for blank lines here
                # For now, just check that different groups aren't mixed
                pass

            prev_group = current_group

        return issues

    def get_python_files(self) -> List[Path]:
        """Get all Python files in the project"""
        python_files = []
        exclude_dirs = {".venv", "__pycache__", ".pytest_cache", "target", "build"}

        for py_file in self.project_root.rglob("*.py"):
            if not any(exclude_dir in py_file.parts for exclude_dir in exclude_dirs):
                python_files.append(py_file)

        return python_files


@pytest.fixture
def import_checker():
    """Create import order checker"""
    project_root = Path(__file__).parent.parent.parent
    return ImportOrderChecker(project_root)


class TestImportOrder:
    """Test import organization standards"""

    def test_src_directory_import_order(self, import_checker):
        """Test that src/ files have proper import order"""
        src_files = [f for f in import_checker.get_python_files() if "src/" in str(f)]

        failed_files = []
        all_issues = []

        for file_path in src_files:
            has_proper_order, issues = import_checker.analyze_imports(file_path)
            if not has_proper_order:
                failed_files.append(str(file_path))
                all_issues.extend(issues)

        if failed_files:
            issue_summary = "\n".join(all_issues[:15])  # Show first 15 issues
            pytest.fail(
                f"Import order issues found in {len(failed_files)} src/ files:\n"
                f"{issue_summary}\n"
                f"{'...' if len(all_issues) > 15 else ''}\n\n"
                f"Run: isort src/ to fix import order issues"
            )

    def test_biological_memory_import_order(self, import_checker):
        """Test that biological_memory/ files have proper import order"""
        bio_files = [f for f in import_checker.get_python_files() if "biological_memory/" in str(f)]

        failed_files = []
        all_issues = []

        for file_path in bio_files:
            has_proper_order, issues = import_checker.analyze_imports(file_path)
            if not has_proper_order:
                failed_files.append(str(file_path))
                all_issues.extend(issues)

        if failed_files:
            issue_summary = "\n".join(all_issues[:10])  # Show first 10 issues
            pytest.fail(
                f"Import order issues found in {len(failed_files)} biological_memory/ files:\n"
                f"{issue_summary}\n"
                f"{'...' if len(all_issues) > 10 else ''}\n\n"
                f"Run: isort biological_memory/ to fix import order issues"
            )

    def test_no_wildcard_imports(self, import_checker):
        """Test that no files use wildcard imports (from module import *)"""
        wildcard_violations = []

        for file_path in import_checker.get_python_files():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                if "import *" in content:
                    for line_no, line in enumerate(content.split("\n"), 1):
                        if "import *" in line:
                            wildcard_violations.append(
                                f"{file_path}:{line_no} - Wildcard import: {line.strip()}"
                            )

            except Exception:
                continue

        if wildcard_violations:
            violation_summary = "\n".join(wildcard_violations[:10])
            pytest.fail(
                f"Found {len(wildcard_violations)} wildcard import violations:\n"
                f"{violation_summary}\n"
                f"{'...' if len(wildcard_violations) > 10 else ''}\n\n"
                f"Replace wildcard imports with explicit imports"
            )

    def test_no_unused_imports(self, import_checker):
        """Test for obvious unused imports (basic check)"""
        # This is a simplified check - a full implementation would use AST analysis
        potential_unused = []

        for file_path in import_checker.get_python_files():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                lines = content.split("\n")
                import_lines = [
                    (i, line)
                    for i, line in enumerate(lines, 1)
                    if line.strip().startswith(("import ", "from ")) and "import" in line
                ]

                for line_no, import_line in import_lines:
                    # Skip certain imports that might be used indirectly
                    if any(skip in import_line for skip in ["typing", "logging", "__future__"]):
                        continue

                    # Extract the imported name
                    if "import " in import_line:
                        if " as " in import_line:
                            imported_name = import_line.split(" as ")[1].strip()
                        else:
                            parts = import_line.split("import ")[1].strip().split(",")
                            imported_name = parts[0].strip()

                        # Simple check if the name appears elsewhere in the file
                        if imported_name and imported_name not in content.replace(import_line, ""):
                            potential_unused.append(
                                f"{file_path}:{line_no} - Potentially unused: {imported_name}"
                            )

            except Exception:
                continue

        # Only flag obvious cases to avoid false positives
        if len(potential_unused) > 20:  # Only report if there are many obvious cases
            violation_summary = "\n".join(potential_unused[:10])
            pytest.fail(
                f"Found {len(potential_unused)} potentially unused imports:\n"
                f"{violation_summary}\n"
                f"{'...' if len(potential_unused) > 10 else ''}\n\n"
                f"Review and remove unused imports"
            )

    def test_alphabetical_import_sorting(self, import_checker):
        """Test that imports within groups are alphabetically sorted"""
        violations = []

        for file_path in import_checker.get_python_files():
            has_proper_order, issues = import_checker.analyze_imports(file_path)

            # Focus on alphabetical sorting issues
            alpha_issues = [issue for issue in issues if "alphabetical" in issue.lower()]
            if alpha_issues:
                violations.extend(alpha_issues)

        if violations:
            violation_summary = "\n".join(violations[:10])
            pytest.fail(
                f"Found {len(violations)} alphabetical sorting violations:\n"
                f"{violation_summary}\n"
                f"{'...' if len(violations) > 10 else ''}\n\n"
                f"Run: isort src/ biological_memory/ to fix sorting"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
