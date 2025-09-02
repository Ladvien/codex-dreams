#!/usr/bin/env python3
"""
Test type hint coverage across the codebase
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest


def get_python_files() -> List[Path]:
    """Get all Python files in the src directory"""
    src_dir = Path(__file__).parent.parent.parent / "src"
    python_files = []

    for root, dirs, files in os.walk(src_dir):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    return python_files


def analyze_function_type_hints(file_path: Path) -> Dict[str, bool]:
    """Analyze type hints for all functions in a Python file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)

        function_type_hints = {}

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = f"{file_path.name}::{node.name}"

                # Check if function has type hints
                has_return_annotation = node.returns is not None
                has_arg_annotations = all(
                    arg.annotation is not None
                    for arg in node.args.args
                    if arg.arg != "self" and arg.arg != "cls"
                )

                # Consider function properly typed if it has return annotation
                # and all non-self/cls arguments are typed
                is_properly_typed = has_return_annotation and has_arg_annotations

                # Special cases for certain functions that don't need return types
                special_functions = {"__init__", "__enter__", "__exit__", "__post_init__"}
                if node.name in special_functions:
                    # These functions only need parameter annotations
                    is_properly_typed = has_arg_annotations

                function_type_hints[func_name] = is_properly_typed

        return function_type_hints

    except Exception as e:
        pytest.fail(f"Failed to analyze {file_path}: {e}")


class TestTypeHints:
    """Test type hint coverage and compliance"""

    def test_all_src_files_have_type_hints(self):
        """Ensure all functions in src/ directory have proper type hints"""
        python_files = get_python_files()
        assert len(python_files) > 0, "No Python files found in src/ directory"

        untyped_functions = []
        total_functions = 0
        typed_functions = 0

        for file_path in python_files:
            function_hints = analyze_function_type_hints(file_path)

            for func_name, is_typed in function_hints.items():
                total_functions += 1
                if is_typed:
                    typed_functions += 1
                else:
                    untyped_functions.append(func_name)

        # Calculate coverage percentage
        if total_functions > 0:
            coverage_percentage = (typed_functions / total_functions) * 100
        else:
            coverage_percentage = 100

        print(f"\nType Hint Coverage Report:")
        print(f"Total functions: {total_functions}")
        print(f"Typed functions: {typed_functions}")
        print(f"Coverage: {coverage_percentage:.1f}%")

        if untyped_functions:
            print(f"\nUntyped functions:")
            for func in untyped_functions:
                print(f"  - {func}")

        # Require at least 90% type hint coverage
        assert coverage_percentage >= 90, (
            f"Type hint coverage is {coverage_percentage:.1f}%, "
            f"but at least 90% is required. "
            f"Functions missing type hints: {untyped_functions}"
        )

    def test_important_functions_are_fully_typed(self):
        """Ensure critical functions have complete type annotations"""
        important_files = [
            "src/codex_service.py",
            "src/codex_config.py",
            "src/codex_scheduler.py",
            "src/services/memory_writeback_service.py",
            "src/infrastructure/environment.py",
        ]

        for file_path_str in important_files:
            file_path = Path(__file__).parent.parent.parent / file_path_str
            if not file_path.exists():
                continue

            function_hints = analyze_function_type_hints(file_path)

            untyped_in_file = [
                func_name for func_name, is_typed in function_hints.items() if not is_typed
            ]

            assert (
                len(untyped_in_file) == 0
            ), f"Critical file {file_path_str} has untyped functions: {untyped_in_file}"

    def test_typing_imports_present(self):
        """Ensure files with type hints import from typing module"""
        python_files = get_python_files()

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check if file uses type hints (has annotations)
                tree = ast.parse(content)
                has_type_annotations = False

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.returns is not None or any(
                            arg.annotation for arg in node.args.args
                        ):
                            has_type_annotations = True
                            break

                # If file has type annotations, it should import from typing
                if has_type_annotations:
                    has_typing_import = (
                        "from typing import" in content or "import typing" in content
                    )

                    assert (
                        has_typing_import
                    ), f"File {file_path} uses type annotations but doesn't import from typing"

            except Exception as e:
                pytest.fail(f"Failed to check typing imports in {file_path}: {e}")

    def test_no_any_type_usage(self):
        """Ensure code doesn't overuse 'Any' type (which defeats the purpose)"""
        python_files = get_python_files()

        any_usage_count = 0
        files_with_any = []

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Count occurrences of 'Any' type
                any_count = content.count(": Any") + content.count("-> Any")
                if any_count > 0:
                    any_usage_count += any_count
                    files_with_any.append((file_path.name, any_count))

            except Exception as e:
                pytest.fail(f"Failed to check Any usage in {file_path}: {e}")

        # Allow some usage of Any, but not excessive
        max_allowed_any = 5  # Allow up to 5 Any usages across the entire codebase

        assert any_usage_count <= max_allowed_any, (
            f"Found {any_usage_count} usages of 'Any' type, but maximum {max_allowed_any} allowed. "
            f"Files with Any: {files_with_any}. Consider using more specific types."
        )

    @pytest.mark.parametrize(
        "file_name",
        [
            "codex_service.py",
            "codex_config.py",
            "codex_scheduler.py",
            "memory_writeback_service.py",
        ],
    )
    def test_specific_file_type_coverage(self, file_name: str):
        """Test specific important files have 100% type coverage"""
        src_dir = Path(__file__).parent.parent.parent / "src"

        # Find the file in any subdirectory
        file_path = None
        for root, dirs, files in os.walk(src_dir):
            if file_name in files:
                file_path = Path(root) / file_name
                break

        if file_path is None:
            pytest.skip(f"File {file_name} not found")

        function_hints = analyze_function_type_hints(file_path)

        if not function_hints:
            pytest.skip(f"No functions found in {file_name}")

        untyped_functions = [
            func_name for func_name, is_typed in function_hints.items() if not is_typed
        ]

        coverage = len(function_hints) - len(untyped_functions)
        coverage_pct = (coverage / len(function_hints)) * 100 if function_hints else 100

        assert len(untyped_functions) == 0, (
            f"File {file_name} has {len(untyped_functions)} untyped functions "
            f"(coverage: {coverage_pct:.1f}%): {untyped_functions}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
