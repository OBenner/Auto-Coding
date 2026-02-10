#!/usr/bin/env python3
"""
Tests for Automated Test Generation Pipeline
=============================================

Tests the complete test generation pipeline including:
- Code analysis (AST-based function/class extraction)
- Test generator agent functionality
- Test validation logic
- End-to-end integration flow
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Store original modules for cleanup
_original_modules = {}
_mocked_module_names = [
    'claude_code_sdk',
    'claude_code_sdk.types',
    'claude_agent_sdk',
    'claude_agent_sdk.types',
]

for name in _mocked_module_names:
    if name in sys.modules:
        _original_modules[name] = sys.modules[name]

# Mock Claude SDK before importing test generation modules
mock_code_sdk = MagicMock()
mock_code_sdk.ClaudeSDKClient = MagicMock()
mock_code_sdk.ClaudeCodeOptions = MagicMock()
mock_code_types = MagicMock()
mock_code_types.HookMatcher = MagicMock()
sys.modules['claude_code_sdk'] = mock_code_sdk
sys.modules['claude_code_sdk.types'] = mock_code_types

mock_agent_sdk = MagicMock()
mock_agent_sdk.ClaudeSDKClient = MagicMock()
mock_agent_sdk.ClaudeCodeOptions = MagicMock()
mock_agent_types = MagicMock()
mock_agent_types.HookMatcher = MagicMock()
sys.modules['claude_agent_sdk'] = mock_agent_sdk
sys.modules['claude_agent_sdk.types'] = mock_agent_types

# Import test generation modules
from analysis.code_analyzer import CodeAnalyzer, FunctionInfo, ClassInfo
from agents.test_generator import validate_generated_tests, run_test_generator_session


# Cleanup fixture to restore original modules after all tests
@pytest.fixture(scope="module", autouse=True)
def cleanup_mocked_modules():
    """Restore original modules after all tests in this module complete."""
    yield  # Run all tests first
    # Cleanup: restore original modules or remove mocks
    for name in _mocked_module_names:
        if name in _original_modules:
            sys.modules[name] = _original_modules[name]
        elif name in sys.modules:
            del sys.modules[name]


# =============================================================================
# SAMPLE CODE FIXTURES
# =============================================================================

@pytest.fixture
def sample_python_module(temp_dir: Path) -> Path:
    """Create a sample Python module with testable functions."""
    module_content = '''"""
Sample Calculator Module
========================

Simple calculator for testing automated test generation.
"""

from typing import Union


def add(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b


def divide(a: float, b: float) -> float:
    """Divide two numbers.

    Args:
        a: Numerator
        b: Denominator

    Returns:
        Result of division

    Raises:
        ValueError: If b is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def is_even(n: int) -> bool:
    """Check if a number is even.

    Args:
        n: Number to check

    Returns:
        True if even, False otherwise
    """
    return n % 2 == 0


class Calculator:
    """A simple calculator class."""

    def __init__(self, precision: int = 2):
        """Initialize calculator with precision.

        Args:
            precision: Number of decimal places for rounding
        """
        self.precision = precision
        self.history = []

    def calculate(self, operation: str, a: float, b: float) -> float:
        """Perform a calculation.

        Args:
            operation: Operation to perform (+, -, *, /)
            a: First operand
            b: Second operand

        Returns:
            Result of calculation

        Raises:
            ValueError: If operation is invalid
        """
        if operation == "+":
            result = a + b
        elif operation == "-":
            result = a - b
        elif operation == "*":
            result = a * b
        elif operation == "/":
            if b == 0:
                raise ValueError("Cannot divide by zero")
            result = a / b
        else:
            raise ValueError(f"Invalid operation: {operation}")

        self.history.append((operation, a, b, result))
        return round(result, self.precision)

    def clear_history(self) -> None:
        """Clear calculation history."""
        self.history = []
'''

    module_file = temp_dir / "calculator.py"
    module_file.write_text(module_content)
    return module_file


@pytest.fixture
def sample_test_file(temp_dir: Path) -> Path:
    """Create a sample test file for validation testing."""
    test_content = '''"""
Tests for Calculator Module
============================

Generated tests for the calculator module.
"""

import pytest
from calculator import add, divide, is_even, Calculator


class TestAddFunction:
    """Tests for add() function."""

    def test_add_positive_numbers(self):
        """Add two positive numbers."""
        assert add(2, 3) == 5

    def test_add_negative_numbers(self):
        """Add two negative numbers."""
        assert add(-2, -3) == -5

    def test_add_zero(self):
        """Add with zero."""
        assert add(5, 0) == 5


class TestDivideFunction:
    """Tests for divide() function."""

    def test_divide_positive_numbers(self):
        """Divide two positive numbers."""
        assert divide(6, 2) == 3.0

    def test_divide_by_zero_raises_error(self):
        """Dividing by zero raises ValueError."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(5, 0)


class TestIsEvenFunction:
    """Tests for is_even() function."""

    def test_even_number_returns_true(self):
        """Even numbers return True."""
        assert is_even(4) is True

    def test_odd_number_returns_false(self):
        """Odd numbers return False."""
        assert is_even(3) is False


class TestCalculatorClass:
    """Tests for Calculator class."""

    def test_calculator_initialization(self):
        """Calculator initializes with default precision."""
        calc = Calculator()
        assert calc.precision == 2
        assert calc.history == []

    def test_calculate_addition(self):
        """Calculator can add numbers."""
        calc = Calculator()
        result = calc.calculate("+", 2, 3)
        assert result == 5.0

    def test_calculate_division_by_zero(self):
        """Calculator raises error on division by zero."""
        calc = Calculator()
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            calc.calculate("/", 5, 0)

    def test_calculate_invalid_operation(self):
        """Calculator raises error on invalid operation."""
        calc = Calculator()
        with pytest.raises(ValueError, match="Invalid operation"):
            calc.calculate("^", 2, 3)

    def test_clear_history(self):
        """Calculator can clear history."""
        calc = Calculator()
        calc.calculate("+", 2, 3)
        calc.clear_history()
        assert calc.history == []
'''

    test_file = temp_dir / "test_calculator.py"
    test_file.write_text(test_content)
    return test_file


# =============================================================================
# CODE ANALYZER TESTS
# =============================================================================

class TestCodeAnalyzer:
    """Tests for CodeAnalyzer class."""

    def test_analyzer_initialization(self):
        """CodeAnalyzer initializes correctly."""
        analyzer = CodeAnalyzer()
        assert analyzer is not None

    def test_analyze_file_extracts_functions(self, sample_python_module: Path):
        """Analyzer extracts standalone functions from Python file."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(sample_python_module)

        assert "functions" in result
        assert len(result["functions"]) >= 3

        # Check function names
        function_names = [f["name"] for f in result["functions"]]
        assert "add" in function_names
        assert "divide" in function_names
        assert "is_even" in function_names

    def test_analyze_file_extracts_classes(self, sample_python_module: Path):
        """Analyzer extracts classes from Python file."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(sample_python_module)

        assert "classes" in result
        assert len(result["classes"]) >= 1

        # Check class names
        class_names = [c["name"] for c in result["classes"]]
        assert "Calculator" in class_names

    def test_analyze_file_extracts_methods(self, sample_python_module: Path):
        """Analyzer extracts methods from classes."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(sample_python_module)

        # Find Calculator class
        calculator_class = None
        for cls in result["classes"]:
            if cls["name"] == "Calculator":
                calculator_class = cls
                break

        assert calculator_class is not None
        assert "methods" in calculator_class

        # Check method names
        method_names = [m["name"] for m in calculator_class["methods"]]
        assert "__init__" in method_names
        assert "calculate" in method_names
        assert "clear_history" in method_names

    def test_analyze_file_extracts_docstrings(self, sample_python_module: Path):
        """Analyzer extracts docstrings from functions."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(sample_python_module)

        # Find add function
        add_function = None
        for func in result["functions"]:
            if func["name"] == "add":
                add_function = func
                break

        assert add_function is not None
        assert "docstring" in add_function
        assert add_function["docstring"] is not None
        assert "Add two numbers" in add_function["docstring"]

    def test_analyze_file_detects_edge_cases(self, sample_python_module: Path):
        """Analyzer detects edge case patterns."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(sample_python_module)

        assert "edge_cases" in result

        # Should detect error handling (raise ValueError)
        edge_case_types = [ec["type"] for ec in result["edge_cases"]]
        assert "error_raising" in edge_case_types

    def test_analyze_file_handles_missing_file(self, temp_dir: Path):
        """Analyzer handles missing file gracefully."""
        analyzer = CodeAnalyzer()
        missing_file = temp_dir / "nonexistent.py"

        # Should raise FileNotFoundError or return error structure
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_file(missing_file)

    def test_analyze_file_returns_file_path(self, sample_python_module: Path):
        """Analyzer includes file path in result."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(sample_python_module)

        assert "file_path" in result
        assert result["file_path"] == str(sample_python_module)


# =============================================================================
# TEST VALIDATION TESTS
# =============================================================================

class TestTestValidation:
    """Tests for test validation logic."""

    def test_validate_generated_tests_valid_syntax(
        self, sample_python_module: Path, sample_test_file: Path, temp_dir: Path
    ):
        """validate_generated_tests accepts syntactically correct tests."""
        test_files = [sample_test_file.relative_to(temp_dir)]
        result = validate_generated_tests(test_files, temp_dir)

        # Should pass syntax validation
        assert result is True

    def test_validate_generated_tests_invalid_syntax(self, temp_dir: Path):
        """validate_generated_tests rejects invalid syntax."""
        # Create test file with syntax error
        invalid_test = temp_dir / "test_invalid.py"
        invalid_test.write_text("def test_something(\n    pass  # Missing closing paren")

        test_files = [invalid_test.relative_to(temp_dir)]
        result = validate_generated_tests(test_files, temp_dir)

        assert result is False

    def test_validate_generated_tests_empty_list(self, temp_dir: Path):
        """validate_generated_tests handles empty test file list."""
        result = validate_generated_tests([], temp_dir)

        assert result is False

    def test_validate_generated_tests_missing_file(self, temp_dir: Path):
        """validate_generated_tests handles missing test file."""
        missing_file = Path("test_missing.py")
        result = validate_generated_tests([missing_file], temp_dir)

        assert result is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestTestGenerationPipeline:
    """Integration tests for the complete test generation pipeline."""

    def test_end_to_end_analysis_to_validation(
        self, sample_python_module: Path, sample_test_file: Path, temp_dir: Path
    ):
        """Complete pipeline: analyze code -> validate generated tests."""
        # Step 1: Analyze the code
        analyzer = CodeAnalyzer()
        analysis_result = analyzer.analyze_file(sample_python_module)

        # Verify analysis results
        assert "functions" in analysis_result
        assert "classes" in analysis_result
        assert len(analysis_result["functions"]) >= 3
        assert len(analysis_result["classes"]) >= 1

        # Step 2: Simulate test generation (we have pre-written tests)
        # In real pipeline, test_generator agent would create these
        test_files = [sample_test_file.relative_to(temp_dir)]

        # Step 3: Validate generated tests
        validation_result = validate_generated_tests(test_files, temp_dir)

        assert validation_result is True

    def test_pipeline_handles_multiple_files(
        self, sample_python_module: Path, temp_dir: Path
    ):
        """Pipeline can analyze multiple Python files."""
        # Create second module
        module2_content = '''
def helper_function(x):
    """A helper function."""
    return x * 2

class Helper:
    """A helper class."""

    def process(self, data):
        """Process data."""
        return data
'''
        module2 = temp_dir / "helper.py"
        module2.write_text(module2_content)

        # Analyze both modules
        analyzer = CodeAnalyzer()
        result1 = analyzer.analyze_file(sample_python_module)
        result2 = analyzer.analyze_file(module2)

        # Combine results
        all_functions = result1["functions"] + result2["functions"]
        all_classes = result1["classes"] + result2["classes"]

        assert len(all_functions) >= 4  # 3 from calculator + 1 from helper
        assert len(all_classes) >= 2    # Calculator + Helper

    def test_pipeline_detects_complex_edge_cases(self, temp_dir: Path):
        """Pipeline detects various edge case patterns."""
        complex_module = temp_dir / "complex.py"
        complex_content = '''
def validate_input(data):
    """Validate input data."""
    if data is None:
        raise ValueError("Data cannot be None")

    if not isinstance(data, dict):
        raise TypeError("Data must be a dict")

    if len(data) == 0:
        return False

    if "required_field" not in data:
        raise KeyError("Missing required field")

    return True
'''
        complex_module.write_text(complex_content)

        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(complex_module)

        # Should detect multiple edge cases
        assert "edge_cases" in result
        assert len(result["edge_cases"]) >= 3

        edge_case_types = [ec["type"] for ec in result["edge_cases"]]
        assert "boundary_condition" in edge_case_types
        assert "type_validation" in edge_case_types
        assert "error_raising" in edge_case_types

    def test_analysis_result_structure_for_test_generation(
        self, sample_python_module: Path
    ):
        """Analysis result has all required fields for test generation."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(sample_python_module)

        # Required top-level fields
        assert "file_path" in result
        assert "functions" in result
        assert "classes" in result
        assert "edge_cases" in result

        # Function structure
        if result["functions"]:
            func = result["functions"][0]
            assert "name" in func
            assert "lineno" in func
            assert "args" in func
            assert "docstring" in func

        # Class structure
        if result["classes"]:
            cls = result["classes"][0]
            assert "name" in cls
            assert "lineno" in cls
            assert "methods" in cls
            assert "docstring" in cls

    def test_test_naming_conventions(self, sample_test_file: Path):
        """Generated tests follow pytest naming conventions."""
        content = sample_test_file.read_text()

        # File should start with test_
        assert sample_test_file.name.startswith("test_")

        # Should import pytest
        assert "import pytest" in content

        # Should have test classes (Test*)
        assert "class Test" in content

        # Should have test methods (test_*)
        assert "def test_" in content

    def test_test_coverage_patterns(self, sample_test_file: Path):
        """Generated tests include various coverage patterns."""
        content = sample_test_file.read_text()

        # Should test normal cases
        assert "test_add_positive_numbers" in content

        # Should test edge cases
        assert "test_divide_by_zero" in content

        # Should use pytest.raises for exceptions
        assert "pytest.raises" in content

        # Should test class initialization
        assert "test_calculator_initialization" in content


# =============================================================================
# TEST GENERATOR SESSION TESTS
# =============================================================================

class TestRunTestGeneratorSession:
    """Tests for run_test_generator_session orchestration function."""

    @pytest.mark.asyncio
    async def test_successful_test_generation(self, temp_dir: Path, monkeypatch):
        """run_test_generator_session successfully generates and validates tests."""
        # Setup directories
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)

        # Create a mock generated test file
        test_file = tests_dir / "test_generated.py"
        test_file.write_text("def test_example(): pass")

        # Mock dependencies
        mock_client = MagicMock()
        mock_client.create_agent_session = AsyncMock(return_value={"success": True})

        def mock_create_client(**kwargs):
            return mock_client

        monkeypatch.setattr("agents.test_generator.create_client", mock_create_client)
        monkeypatch.setattr("agents.test_generator.get_agent_prompt", lambda x: "test prompt")
        monkeypatch.setattr("agents.test_generator.get_task_logger", lambda x: MagicMock())
        monkeypatch.setattr("agents.test_generator.get_phase_model", lambda x, y: "claude-sonnet-4")
        monkeypatch.setattr("agents.test_generator.get_phase_thinking_budget", lambda x, y: None)
        monkeypatch.setattr("agents.test_generator.validate_generated_tests", lambda x, y, z: True)

        # Mock UI functions to suppress output
        monkeypatch.setattr("agents.test_generator.print_status", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.print_key_value", lambda *args, **kwargs: None)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.box", lambda *args, **kwargs: "")

        # Execute
        analysis = {"functions": [{"name": "test_func"}], "classes": []}
        result = await run_test_generator_session(
            project_dir, spec_dir, analysis, model="claude-sonnet-4"
        )

        # Verify
        assert result["success"] is True
        assert len(result["generated_files"]) == 1
        assert "test_generated.py" in result["generated_files"][0]
        assert result["error"] is None

        # Verify client was created with correct parameters
        mock_create_client_calls = [
            call for call in monkeypatch._setattr
            if hasattr(call, '__name__') and call.__name__ == 'mock_create_client'
        ]

    @pytest.mark.asyncio
    async def test_no_tests_directory(self, temp_dir: Path, monkeypatch):
        """run_test_generator_session handles missing tests/ directory."""
        # Setup directories (no tests/ directory)
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        project_dir.mkdir(parents=True)

        # Mock dependencies
        mock_client = MagicMock()
        mock_client.create_agent_session = AsyncMock(return_value={"success": True})

        monkeypatch.setattr("agents.test_generator.create_client", lambda **kwargs: mock_client)
        monkeypatch.setattr("agents.test_generator.get_agent_prompt", lambda x: "test prompt")
        monkeypatch.setattr("agents.test_generator.get_task_logger", lambda x: MagicMock())
        monkeypatch.setattr("agents.test_generator.get_phase_model", lambda x, y: "claude-sonnet-4")
        monkeypatch.setattr("agents.test_generator.get_phase_thinking_budget", lambda x, y: None)

        # Mock UI functions
        monkeypatch.setattr("agents.test_generator.print_status", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.print_key_value", lambda *args, **kwargs: None)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.box", lambda *args, **kwargs: "")

        # Execute
        analysis = {"functions": [], "classes": []}
        result = await run_test_generator_session(project_dir, spec_dir, analysis)

        # Verify failure due to missing tests/ directory
        assert result["success"] is False
        assert result["error"] == "tests/ directory not found"
        assert len(result["generated_files"]) == 0

    @pytest.mark.asyncio
    async def test_no_tests_generated(self, temp_dir: Path, monkeypatch):
        """run_test_generator_session handles case where no test files are created."""
        # Setup directories
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)
        # tests/ directory exists but is empty

        # Mock dependencies
        mock_client = MagicMock()
        mock_client.create_agent_session = AsyncMock(return_value={"success": True})

        monkeypatch.setattr("agents.test_generator.create_client", lambda **kwargs: mock_client)
        monkeypatch.setattr("agents.test_generator.get_agent_prompt", lambda x: "test prompt")
        monkeypatch.setattr("agents.test_generator.get_task_logger", lambda x: MagicMock())
        monkeypatch.setattr("agents.test_generator.get_phase_model", lambda x, y: "claude-sonnet-4")
        monkeypatch.setattr("agents.test_generator.get_phase_thinking_budget", lambda x, y: None)

        # Mock UI functions
        monkeypatch.setattr("agents.test_generator.print_status", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.print_key_value", lambda *args, **kwargs: None)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.box", lambda *args, **kwargs: "")

        # Execute
        analysis = {"functions": [], "classes": []}
        result = await run_test_generator_session(project_dir, spec_dir, analysis)

        # Verify failure due to no generated tests
        assert result["success"] is False
        assert result["error"] == "No test files generated"
        assert len(result["generated_files"]) == 0

    @pytest.mark.asyncio
    async def test_validation_failure(self, temp_dir: Path, monkeypatch):
        """run_test_generator_session handles test validation failures."""
        # Setup directories
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)

        # Create a test file (will be validated as invalid)
        test_file = tests_dir / "test_invalid.py"
        test_file.write_text("def test_bad(): pass")

        # Mock dependencies
        mock_client = MagicMock()
        mock_client.create_agent_session = AsyncMock(return_value={"success": True})

        monkeypatch.setattr("agents.test_generator.create_client", lambda **kwargs: mock_client)
        monkeypatch.setattr("agents.test_generator.get_agent_prompt", lambda x: "test prompt")
        monkeypatch.setattr("agents.test_generator.get_task_logger", lambda x: MagicMock())
        monkeypatch.setattr("agents.test_generator.get_phase_model", lambda x, y: "claude-sonnet-4")
        monkeypatch.setattr("agents.test_generator.get_phase_thinking_budget", lambda x, y: None)
        monkeypatch.setattr("agents.test_generator.validate_generated_tests", lambda x, y, z: False)  # Force failure

        # Mock UI functions
        monkeypatch.setattr("agents.test_generator.print_status", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.print_key_value", lambda *args, **kwargs: None)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.box", lambda *args, **kwargs: "")

        # Execute
        analysis = {"functions": [], "classes": []}
        result = await run_test_generator_session(project_dir, spec_dir, analysis)

        # Verify validation failure is reported
        assert result["success"] is False
        assert result["error"] == "Test validation failed"
        assert len(result["generated_files"]) == 1

    @pytest.mark.asyncio
    async def test_client_creation_failure(self, temp_dir: Path, monkeypatch):
        """run_test_generator_session handles SDK client creation errors."""
        # Setup directories
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"

        # Mock create_client to raise exception
        def mock_create_client_error(**kwargs):
            raise RuntimeError("Failed to authenticate")

        monkeypatch.setattr("agents.test_generator.create_client", mock_create_client_error)
        monkeypatch.setattr("agents.test_generator.get_agent_prompt", lambda x: "test prompt")
        monkeypatch.setattr("agents.test_generator.get_task_logger", lambda x: MagicMock())
        monkeypatch.setattr("agents.test_generator.get_phase_model", lambda x, y: "claude-sonnet-4")
        monkeypatch.setattr("agents.test_generator.get_phase_thinking_budget", lambda x, y: None)

        # Mock UI functions
        monkeypatch.setattr("agents.test_generator.print_status", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.print_key_value", lambda *args, **kwargs: None)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.box", lambda *args, **kwargs: "")

        # Execute
        analysis = {"functions": [], "classes": []}
        result = await run_test_generator_session(project_dir, spec_dir, analysis)

        # Verify error is captured
        assert result["success"] is False
        assert "Failed to create Claude SDK client" in result["error"]
        assert len(result["generated_files"]) == 0

    @pytest.mark.asyncio
    async def test_prompt_loading_failure(self, temp_dir: Path, monkeypatch):
        """run_test_generator_session handles prompt loading errors."""
        # Setup directories
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"

        # Mock get_agent_prompt to raise exception
        def mock_get_agent_prompt_error(name):
            raise FileNotFoundError("Prompt file not found")

        monkeypatch.setattr("agents.test_generator.get_agent_prompt", mock_get_agent_prompt_error)
        monkeypatch.setattr("agents.test_generator.get_task_logger", lambda x: MagicMock())
        monkeypatch.setattr("agents.test_generator.get_phase_model", lambda x, y: "claude-sonnet-4")
        monkeypatch.setattr("agents.test_generator.get_phase_thinking_budget", lambda x, y: None)

        # Mock UI functions
        monkeypatch.setattr("agents.test_generator.print_status", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.print_key_value", lambda *args, **kwargs: None)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.box", lambda *args, **kwargs: "")

        # Execute
        analysis = {"functions": [], "classes": []}
        result = await run_test_generator_session(project_dir, spec_dir, analysis)

        # Verify error is captured
        assert result["success"] is False
        assert "Failed to load test_generator prompt" in result["error"]
        assert len(result["generated_files"]) == 0

    @pytest.mark.asyncio
    async def test_agent_session_exception(self, temp_dir: Path, monkeypatch):
        """run_test_generator_session handles agent session exceptions."""
        # Setup directories
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"

        # Mock client with failing create_agent_session
        mock_client = MagicMock()
        mock_client.create_agent_session = AsyncMock(side_effect=RuntimeError("API Error"))

        monkeypatch.setattr("agents.test_generator.create_client", lambda **kwargs: mock_client)
        monkeypatch.setattr("agents.test_generator.get_agent_prompt", lambda x: "test prompt")
        monkeypatch.setattr("agents.test_generator.get_task_logger", lambda x: MagicMock())
        monkeypatch.setattr("agents.test_generator.get_phase_model", lambda x, y: "claude-sonnet-4")
        monkeypatch.setattr("agents.test_generator.get_phase_thinking_budget", lambda x, y: None)

        # Mock UI functions
        monkeypatch.setattr("agents.test_generator.print_status", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.print_key_value", lambda *args, **kwargs: None)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.box", lambda *args, **kwargs: "")

        # Execute
        analysis = {"functions": [], "classes": []}
        result = await run_test_generator_session(project_dir, spec_dir, analysis)

        # Verify error is captured
        assert result["success"] is False
        assert "Test Generator Agent session failed" in result["error"]
        assert len(result["generated_files"]) == 0

    @pytest.mark.asyncio
    async def test_multiple_test_files_generated(self, temp_dir: Path, monkeypatch):
        """run_test_generator_session handles multiple generated test files."""
        # Setup directories
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)

        # Create multiple mock test files
        (tests_dir / "test_module_a.py").write_text("def test_a(): pass")
        (tests_dir / "test_module_b.py").write_text("def test_b(): pass")
        (tests_dir / "test_utils.py").write_text("def test_utils(): pass")

        # Mock dependencies
        mock_client = MagicMock()
        mock_client.create_agent_session = AsyncMock(return_value={"success": True})

        monkeypatch.setattr("agents.test_generator.create_client", lambda **kwargs: mock_client)
        monkeypatch.setattr("agents.test_generator.get_agent_prompt", lambda x: "test prompt")
        monkeypatch.setattr("agents.test_generator.get_task_logger", lambda x: MagicMock())
        monkeypatch.setattr("agents.test_generator.get_phase_model", lambda x, y: "claude-sonnet-4")
        monkeypatch.setattr("agents.test_generator.get_phase_thinking_budget", lambda x, y: None)
        monkeypatch.setattr("agents.test_generator.validate_generated_tests", lambda x, y, z: True)

        # Mock UI functions
        monkeypatch.setattr("agents.test_generator.print_status", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.print_key_value", lambda *args, **kwargs: None)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.box", lambda *args, **kwargs: "")

        # Execute
        analysis = {"functions": [], "classes": []}
        result = await run_test_generator_session(project_dir, spec_dir, analysis)

        # Verify all test files are found
        assert result["success"] is True
        assert len(result["generated_files"]) == 3
        assert result["error"] is None

        # Verify all expected files are in the list
        file_names = [str(f) for f in result["generated_files"]]
        assert any("test_module_a.py" in f for f in file_names)
        assert any("test_module_b.py" in f for f in file_names)
        assert any("test_utils.py" in f for f in file_names)

    @pytest.mark.asyncio
    async def test_custom_model_and_thinking_budget(self, temp_dir: Path, monkeypatch):
        """run_test_generator_session respects custom model and thinking budget."""
        # Setup directories
        project_dir = temp_dir / "project"
        spec_dir = temp_dir / "spec"
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_custom.py").write_text("def test_custom(): pass")

        # Track create_client calls
        client_kwargs = {}

        def mock_create_client(**kwargs):
            client_kwargs.update(kwargs)
            mock_client = MagicMock()
            mock_client.create_agent_session = AsyncMock(return_value={"success": True})
            return mock_client

        monkeypatch.setattr("agents.test_generator.create_client", mock_create_client)
        monkeypatch.setattr("agents.test_generator.get_agent_prompt", lambda x: "test prompt")
        monkeypatch.setattr("agents.test_generator.get_task_logger", lambda x: MagicMock())
        monkeypatch.setattr("agents.test_generator.validate_generated_tests", lambda x, y, z: True)

        # Mock UI functions
        monkeypatch.setattr("agents.test_generator.print_status", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.print_key_value", lambda *args, **kwargs: None)
        monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
        monkeypatch.setattr("agents.test_generator.box", lambda *args, **kwargs: "")

        # Execute with custom parameters
        analysis = {"functions": [], "classes": []}
        result = await run_test_generator_session(
            project_dir,
            spec_dir,
            analysis,
            model="claude-opus-4",
            max_thinking_tokens=10000,
        )

        # Verify custom parameters were passed to create_client
        assert result["success"] is True
        assert client_kwargs["model"] == "claude-opus-4"
        assert client_kwargs["max_thinking_tokens"] == 10000
        assert client_kwargs["agent_type"] == "test_generator"
