#!/usr/bin/env python3
"""
Unit tests for Refactoring Generator Agent
==========================================

Tests the refactoring_generator module including validate_generated_refactorings()
and the session function signature.
"""

# IMPORTANT: This sys.path manipulation must happen BEFORE importing pytest
# to ensure we import from the actual backend module, not tests.context
import sys
from pathlib import Path


def _configure_sys_path() -> None:
    """Configure sys.path to import from the actual backend module."""
    for td in [p for p in sys.path if "tests" in p]:
        if td in sys.path:
            sys.path.remove(td)
    backend_root = Path(__file__).parent.parent
    sys.path.insert(0, str(backend_root))


_configure_sys_path()

import importlib
import importlib.util
import inspect
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


def _load_refactoring_generator() -> ModuleType:
    """Load refactoring_generator module directly, bypassing agents/__init__.py."""
    backend_root = Path(__file__).parent.parent
    module_path = backend_root / "agents" / "refactoring_generator.py"

    # Build a complete set of mocks needed for the module and its imports
    mock_task_logger = MagicMock()
    mock_task_logger.LogPhase = MagicMock()
    mock_ui = MagicMock()
    mock_generator_base = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "task_logger": mock_task_logger,
            "task_logger.decision_models": MagicMock(),
            "ui": mock_ui,
            "agents._generator_base": mock_generator_base,
        },
    ):
        spec = importlib.util.spec_from_file_location(
            "agents.refactoring_generator", module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class TestRefactoringGeneratorImports:
    """Test that the refactoring_generator module imports correctly."""

    def test_module_importable(self):
        """Test that the refactoring_generator module can be loaded."""
        rg = _load_refactoring_generator()
        assert rg is not None

    def test_validate_generated_refactorings_exists(self):
        """Test that validate_generated_refactorings is exported from the module."""
        rg = _load_refactoring_generator()
        assert hasattr(rg, "validate_generated_refactorings")
        assert callable(rg.validate_generated_refactorings)

    def test_run_refactoring_generator_session_exists(self):
        """Test that run_refactoring_generator_session is exported from the module."""
        rg = _load_refactoring_generator()
        assert hasattr(rg, "run_refactoring_generator_session")
        assert callable(rg.run_refactoring_generator_session)


class TestValidateGeneratedRefactorings:
    """Test suite for validate_generated_refactorings()."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load module and extract validate function before each test."""
        rg = _load_refactoring_generator()
        self.validate = rg.validate_generated_refactorings

    def test_empty_file_list_returns_false(self, tmp_path):
        """Test that empty file list returns False."""
        result = self.validate([], tmp_path)
        assert result is False

    def test_nonexistent_file_returns_false(self, tmp_path):
        """Test that a missing file causes validation to return False."""
        missing_file = Path("apps/backend/nonexistent_module.py")
        result = self.validate([missing_file], tmp_path)
        assert result is False

    def test_valid_python_file_returns_true(self, tmp_path):
        """Test that a valid Python file returns True."""
        py_file = tmp_path / "valid_module.py"
        py_file.write_text("def foo():\n    return 42\n", encoding="utf-8")
        relative_path = py_file.relative_to(tmp_path)
        result = self.validate([relative_path], tmp_path)
        assert result is True

    def test_empty_file_content_returns_false(self, tmp_path):
        """Test that an empty file returns False."""
        empty_file = tmp_path / "empty_module.py"
        empty_file.write_text("", encoding="utf-8")
        relative_path = empty_file.relative_to(tmp_path)
        result = self.validate([relative_path], tmp_path)
        assert result is False

    def test_whitespace_only_file_returns_false(self, tmp_path):
        """Test that a whitespace-only file returns False."""
        ws_file = tmp_path / "whitespace.py"
        ws_file.write_text("   \n\n  \t  \n", encoding="utf-8")
        relative_path = ws_file.relative_to(tmp_path)
        result = self.validate([relative_path], tmp_path)
        assert result is False

    def test_invalid_python_syntax_returns_false(self, tmp_path):
        """Test that a Python file with syntax errors returns False."""
        bad_file = tmp_path / "bad_syntax.py"
        bad_file.write_text("def foo(\n    return 42\n", encoding="utf-8")
        relative_path = bad_file.relative_to(tmp_path)
        result = self.validate([relative_path], tmp_path)
        assert result is False

    def test_non_python_file_valid_content_returns_true(self, tmp_path):
        """Test that a non-Python file with valid content returns True."""
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Some refactoring notes here.\n", encoding="utf-8")
        relative_path = txt_file.relative_to(tmp_path)
        result = self.validate([relative_path], tmp_path)
        assert result is True

    def test_multiple_valid_files_returns_true(self, tmp_path):
        """Test that multiple valid files all pass validation."""
        files = []
        for i in range(3):
            py_file = tmp_path / f"module_{i}.py"
            py_file.write_text(
                f"def func_{i}():\n    return {i}\n", encoding="utf-8"
            )
            files.append(py_file.relative_to(tmp_path))

        result = self.validate(files, tmp_path)
        assert result is True

    def test_one_invalid_among_valid_returns_false(self, tmp_path):
        """Test that one invalid file among valid ones causes False."""
        valid_file = tmp_path / "valid.py"
        valid_file.write_text("x = 1\n", encoding="utf-8")

        invalid_file = tmp_path / "invalid.py"
        invalid_file.write_text("def broken(\n    pass\n", encoding="utf-8")

        result = self.validate(
            [
                valid_file.relative_to(tmp_path),
                invalid_file.relative_to(tmp_path),
            ],
            tmp_path,
        )
        assert result is False

    def test_valid_complex_python_file_returns_true(self, tmp_path):
        """Test that a complex valid Python file passes validation."""
        complex_code = '''"""Module docstring."""

import os
from typing import Any


class MyClass:
    """A class."""

    def __init__(self, value: int) -> None:
        self.value = value

    def process(self, data: Any) -> str:
        """Process data."""
        if data is None:
            return "none"
        return str(data)


def helper(x: int, y: int) -> int:
    """Helper function."""
    return x + y
'''
        py_file = tmp_path / "complex_module.py"
        py_file.write_text(complex_code, encoding="utf-8")
        relative_path = py_file.relative_to(tmp_path)
        result = self.validate([relative_path], tmp_path)
        assert result is True


class TestRunRefactoringGeneratorSessionSignature:
    """Test the signature and async nature of run_refactoring_generator_session."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load module and extract session function before each test."""
        rg = _load_refactoring_generator()
        self.run_session = rg.run_refactoring_generator_session

    def test_is_coroutine_function(self):
        """Test that run_refactoring_generator_session is an async function."""
        import asyncio

        assert asyncio.iscoroutinefunction(self.run_session)

    def test_signature_has_project_dir(self):
        """Test that the function accepts project_dir parameter."""
        sig = inspect.signature(self.run_session)
        assert "project_dir" in sig.parameters

    def test_signature_has_spec_dir(self):
        """Test that the function accepts spec_dir parameter."""
        sig = inspect.signature(self.run_session)
        assert "spec_dir" in sig.parameters

    def test_signature_has_analysis_results(self):
        """Test that the function accepts analysis_results parameter."""
        sig = inspect.signature(self.run_session)
        assert "analysis_results" in sig.parameters

    def test_signature_has_optional_model(self):
        """Test that the function accepts optional model parameter defaulting to None."""
        sig = inspect.signature(self.run_session)
        assert "model" in sig.parameters
        assert sig.parameters["model"].default is None

    def test_signature_has_optional_max_thinking_tokens(self):
        """Test that max_thinking_tokens parameter defaults to None."""
        sig = inspect.signature(self.run_session)
        assert "max_thinking_tokens" in sig.parameters
        assert sig.parameters["max_thinking_tokens"].default is None

    def test_signature_has_optional_verbose(self):
        """Test that verbose parameter defaults to False."""
        sig = inspect.signature(self.run_session)
        assert "verbose" in sig.parameters
        assert sig.parameters["verbose"].default is False

    def test_all_required_parameters_present(self):
        """Test that all required parameters are present in the signature."""
        sig = inspect.signature(self.run_session)
        params = sig.parameters
        required = {
            name
            for name, p in params.items()
            if p.default is inspect.Parameter.empty
        }
        assert "project_dir" in required
        assert "spec_dir" in required
        assert "analysis_results" in required

    def test_parameter_count(self):
        """Test that the function has exactly 6 parameters."""
        sig = inspect.signature(self.run_session)
        assert len(sig.parameters) == 6
