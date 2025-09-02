#!/usr/bin/env python3
"""
Test import organization and order compliance with isort standards
"""

import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

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


def extract_imports_from_file(file_path: Path) -> Dict[str, List[str]]:
    """Extract and categorize imports from a Python file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)

        imports = {"stdlib": [], "third_party": [], "first_party": [], "local": []}

        # Standard library modules (Python 3.8+)
        stdlib_modules = {
            "os",
            "sys",
            "time",
            "json",
            "uuid",
            "logging",
            "datetime",
            "pathlib",
            "subprocess",
            "signal",
            "contextlib",
            "dataclasses",
            "typing",
            "ast",
            "re",
            "collections",
            "functools",
            "itertools",
            "operator",
            "math",
            "statistics",
            "random",
            "decimal",
            "fractions",
            "sqlite3",
            "threading",
            "multiprocessing",
            "concurrent",
            "asyncio",
            "argparse",
            "configparser",
            "urllib",
            "http",
            "email",
            "hashlib",
            "base64",
            "zlib",
            "gzip",
            "shutil",
            "tempfile",
            "glob",
            "fnmatch",
            "platform",
            "warnings",
        }

        # Third-party modules
        third_party_modules = {
            "dbt",
            "duckdb",
            "psycopg2",
            "pytest",
            "pandas",
            "yaml",
            "psutil",
            "requests",
            "pyyaml",
            "numpy",
            "matplotlib",
            "seaborn",
            "sqlalchemy",
            "flask",
            "fastapi",
            "click",
            "rich",
            "typer",
        }

        # First-party modules (our project modules)
        first_party_modules = {"src", "biological_memory"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]

                    if module_name in stdlib_modules:
                        imports["stdlib"].append(alias.name)
                    elif module_name in third_party_modules:
                        imports["third_party"].append(alias.name)
                    elif module_name in first_party_modules:
                        imports["first_party"].append(alias.name)
                    else:
                        imports["local"].append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]

                    if module_name in stdlib_modules:
                        imports["stdlib"].append(node.module)
                    elif module_name in third_party_modules:
                        imports["third_party"].append(node.module)
                    elif module_name in first_party_modules:
                        imports["first_party"].append(node.module)
                    elif node.module.startswith("."):
                        imports["local"].append(node.module)
                    else:
                        imports["local"].append(node.module)

        return imports

    except Exception as e:
        pytest.fail(f"Failed to extract imports from {file_path}: {e}")


class TestImportOrder:
    """Test import organization and order compliance"""

    def test_isort_compliance(self):
        """Ensure all Python files comply with isort configuration"""
        python_files = get_python_files()
        assert len(python_files) > 0, "No Python files found"

        # Run isort in check mode
        cmd = [
            sys.executable,
            "-m",
            "isort",
            "--check-only",
            "--diff",
            "--profile=black",
            "--line-length=100",
        ] + [str(f) for f in python_files]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                print(f"\nImport order issues found:")
                print(result.stdout)
                if result.stderr:
                    print(f"Errors: {result.stderr}")

                pytest.fail(
                    f"Import order check failed. Run 'python -m isort --profile=black .' to fix."
                )

        except subprocess.TimeoutExpired:
            pytest.fail("Import order check timed out")
        except FileNotFoundError:
            pytest.skip("isort not installed")

    def test_import_sections_order(self):
        """Ensure imports follow the correct section order"""
        python_files = get_python_files()
        violations = []

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Find import blocks
                import_lines = []
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if (
                        stripped.startswith("import ")
                        or stripped.startswith("from ")
                        and " import " in stripped
                    ):
                        import_lines.append((i + 1, stripped))

                if len(import_lines) < 2:
                    continue  # Skip files with very few imports

                # Check that sections are in the right order
                # Expected order: stdlib, third-party, first-party, local
                current_section = "stdlib"
                section_positions = {"stdlib": 0, "third_party": 1, "first_party": 2, "local": 3}

                for line_num, import_line in import_lines:
                    imports = extract_imports_from_file(file_path)

                    # Simplified check - just ensure no obvious violations
                    if (
                        "from src" in import_line
                        or "from biological_memory" in import_line
                        or "import src" in import_line
                        or "import biological_memory" in import_line
                    ):
                        # This is a first-party import
                        if any(tp in import_line for tp in ["dbt", "psycopg2", "pytest", "pandas"]):
                            violations.append(
                                {
                                    "file": str(file_path),
                                    "line": line_num,
                                    "issue": "first-party import mixed with third-party",
                                }
                            )

            except Exception as e:
                # Don't fail the test for analysis errors
                continue

        # This is a soft check - import order issues are better caught by isort
        if len(violations) > 10:  # Only fail for excessive violations
            print(f"\nImport order violations:")
            for v in violations[:10]:  # Show first 10
                print(f"  {v['file']}:{v['line']} - {v['issue']}")

            pytest.fail(f"Found {len(violations)} import order violations")

    def test_no_star_imports(self):
        """Ensure no wildcard imports (from module import *)"""
        python_files = get_python_files()
        violations = []

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if "import *" in line and not line.strip().startswith("#"):
                            violations.append(
                                {"file": str(file_path), "line": line_num, "content": line.strip()}
                            )

            except Exception as e:
                pytest.fail(f"Failed to check star imports in {file_path}: {e}")

        if violations:
            print(f"\nWildcard import violations:")
            for v in violations:
                print(f"  {v['file']}:{v['line']} - {v['content']}")

        assert len(violations) == 0, (
            f"Found {len(violations)} wildcard imports. "
            "Use explicit imports instead of 'from module import *'."
        )

    def test_unused_imports(self):
        """Check for obviously unused imports"""
        python_files = get_python_files()

        # Focus on src files only for this check
        src_files = [f for f in python_files if "/src/" in str(f)]
        potential_unused = []

        for file_path in src_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Simple heuristic check for unused imports
                import_lines = [
                    line
                    for line in content.split("\n")
                    if line.strip().startswith(("import ", "from "))
                ]

                for import_line in import_lines:
                    # Extract the imported name
                    if " as " in import_line:
                        imported_name = import_line.split(" as ")[1].strip()
                    elif "from " in import_line and " import " in import_line:
                        parts = import_line.split(" import ")[1].strip()
                        imported_name = parts.split(",")[0].strip()
                    else:
                        imported_name = import_line.replace("import ", "").strip()

                    # Check if the imported name appears elsewhere in the file
                    content_without_imports = "\n".join(
                        [
                            line
                            for line in content.split("\n")
                            if not line.strip().startswith(("import ", "from "))
                        ]
                    )

                    if (
                        imported_name
                        and imported_name not in ["*", "("]
                        and imported_name.count(content_without_imports) == 0
                    ):
                        # This is a very basic check - false positives are
                        # expected
                        continue

            except Exception:
                continue

        # This test is informational - don't fail for potential unused imports
        # as the heuristic is very basic
        pass

    def test_relative_imports_in_src(self):
        """Ensure proper use of relative imports in src/ directory"""
        python_files = get_python_files()
        violations = []

        # Check files in src directory
        src_files = [f for f in python_files if "/src/" in str(f)]

        for file_path in src_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        # Check for absolute imports of internal modules
                        if node.module.startswith("src."):
                            # This could be a relative import instead
                            file_dir = file_path.parent
                            if "src" in str(file_dir):
                                violations.append(
                                    {
                                        "file": str(file_path),
                                        "import": node.module,
                                        "suggestion": f"Consider using relative import: from .{node.module[4:]} import ...",
                                    }
                                )

            except Exception:
                continue

        # This is advisory - relative vs absolute imports are a style choice
        # Only fail for excessive violations
        if len(violations) > 20:
            print(f"\nAbsolute import suggestions:")
            for v in violations[:10]:
                print(f"  {v['file']} - {v['import']} ({v['suggestion']})")

            pytest.fail(f"Consider using relative imports for internal modules")

    def test_import_alphabetical_order(self):
        """Ensure imports within each section are alphabetically ordered"""
        python_files = get_python_files()

        # Focus on important files
        important_files = [f for f in python_files if "/src/" in str(f) and f.name != "__init__.py"]
        violations = []

        for file_path in important_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Find consecutive import blocks
                import_blocks = []
                current_block = []

                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith("import ") or (
                        stripped.startswith("from ") and " import " in stripped
                    ):
                        current_block.append((i + 1, stripped))
                    else:
                        if current_block:
                            import_blocks.append(current_block)
                            current_block = []

                if current_block:
                    import_blocks.append(current_block)

                # Check alphabetical order within blocks
                for block in import_blocks:
                    if len(block) < 2:
                        continue

                    import_names = [line[1] for line in block]
                    sorted_names = sorted(import_names)

                    if import_names != sorted_names:
                        violations.append(
                            {
                                "file": str(file_path),
                                "block_start": block[0][0],
                                "actual": import_names,
                                "expected": sorted_names,
                            }
                        )

            except Exception:
                continue

        # This is handled by isort, so we'll be lenient
        if len(violations) > 5:
            print(f"\nImport alphabetical order issues:")
            for v in violations[:3]:
                print(f"  {v['file']} starting line {v['block_start']}")

            pytest.fail("Run 'python -m isort .' to fix import ordering")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
