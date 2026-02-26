"""
Unit tests for signature_parser module.

Tests the function signature parsing functionality for semantic analysis.
"""

import pytest

from merge.signature_parser import (
    _extract_parameter_names,
    _split_parameters,
    get_signature_fingerprint,
    parse_function_signature,
    signatures_match,
)


class TestParseFunctionSignature:
    """Tests for parse_function_signature function."""

    def test_basic_function(self):
        """Test parsing basic function without type hints."""
        sig = parse_function_signature("def foo():")
        assert sig.name == "foo"
        assert sig.params == []
        assert sig.return_type == ""

    def test_function_with_params(self):
        """Test parsing function with parameters."""
        sig = parse_function_signature("def bar(x, y):")
        assert sig.name == "bar"
        assert sig.params == ["x", "y"]
        assert sig.return_type == ""

    def test_function_with_type_hints(self):
        """Test parsing function with type hints."""
        sig = parse_function_signature("def foo(x: int, y: str) -> bool:")
        assert sig.name == "foo"
        assert sig.params == ["x", "y"]
        assert sig.return_type == "bool"

    def test_async_function(self):
        """Test parsing async function."""
        sig = parse_function_signature("async def fetch_data(url):")
        assert sig.name == "fetch_data"
        assert sig.params == ["url"]
        assert sig.return_type == ""

    def test_function_with_defaults(self):
        """Test parsing function with default values."""
        sig = parse_function_signature("def connect(host='localhost', port=8080):")
        assert sig.name == "connect"
        assert sig.params == ["host", "port"]
        assert sig.return_type == ""

    def test_function_with_args_kwargs(self):
        """Test parsing function with *args and **kwargs."""
        sig = parse_function_signature("def func(*args, **kwargs):")
        assert sig.name == "func"
        assert sig.params == ["args", "kwargs"]
        assert sig.return_type == ""

    def test_function_with_complex_types(self):
        """Test parsing function with complex type hints."""
        sig = parse_function_signature("def process(items: list[str]) -> dict[str, int]:")
        assert sig.name == "process"
        assert sig.params == ["items"]
        assert sig.return_type == "dict[str, int]"

    def test_method_with_self(self):
        """Test parsing class method with self parameter."""
        sig = parse_function_signature("def method(self, value):")
        assert sig.name == "method"
        assert sig.params == ["self", "value"]
        assert sig.return_type == ""

    def test_classmethod_with_cls(self):
        """Test parsing classmethod with cls parameter."""
        sig = parse_function_signature("def create(cls, **options):")
        assert sig.name == "create"
        assert sig.params == ["cls", "options"]
        assert sig.return_type == ""

    def test_invalid_signature_empty(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            parse_function_signature("")

    def test_invalid_signature_format(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            parse_function_signature("not a function signature")


class TestExtractParameterNames:
    """Tests for _extract_parameter_names helper function."""

    def test_empty_params(self):
        """Test with empty parameter string."""
        assert _extract_parameter_names("") == []

    def test_single_param(self):
        """Test with single parameter."""
        assert _extract_parameter_names("x") == ["x"]

    def test_multiple_params(self):
        """Test with multiple parameters."""
        assert _extract_parameter_names("x, y, z") == ["x", "y", "z"]

    def test_params_with_type_hints(self):
        """Test parameters with type hints."""
        assert _extract_parameter_names("x: int, y: str") == ["x", "y"]

    def test_params_with_defaults(self):
        """Test parameters with default values."""
        assert _extract_parameter_names("x=1, y='test'") == ["x", "y"]

    def test_mixed_params(self):
        """Test parameters with type hints and defaults."""
        assert _extract_parameter_names("x: int = 0, y: str = ''") == ["x", "y"]

    def test_varargs(self):
        """Test *args parameter."""
        assert _extract_parameter_names("*args") == ["args"]

    def test_kwargs(self):
        """Test **kwargs parameter."""
        assert _extract_parameter_names("**kwargs") == ["kwargs"]

    def test_mixed_args_kwargs(self):
        """Test mix of regular, *args, and **kwargs."""
        result = _extract_parameter_names("x, *args, y, **kwargs")
        assert result == ["x", "args", "y", "kwargs"]


class TestSplitParameters:
    """Tests for _split_parameters helper function."""

    def test_empty_string(self):
        """Test with empty string."""
        assert _split_parameters("") == []

    def test_single_param(self):
        """Test with single parameter."""
        assert _split_parameters("x") == ["x"]

    def test_multiple_params(self):
        """Test with multiple parameters."""
        assert _split_parameters("x, y, z") == ["x", "y", "z"]

    def test_nested_generics(self):
        """Test parameters with nested generic types."""
        result = _split_parameters("items: Dict[str, int], name: str")
        assert result == ["items: Dict[str, int]", "name: str"]

    def test_complex_nesting(self):
        """Test complex nested types."""
        result = _split_parameters("data: List[Tuple[str, int]], flag: bool")
        assert result == ["data: List[Tuple[str, int]]", "flag: bool"]


class TestGetSignatureFingerprint:
    """Tests for get_signature_fingerprint function."""

    def test_basic_fingerprint(self):
        """Test fingerprint generation for basic function."""
        fp = get_signature_fingerprint("def foo(x, y):")
        assert fp == "foo:2"

    def test_with_type_hints(self):
        """Test fingerprint with type hints."""
        fp = get_signature_fingerprint("def bar(a: int, b: str, c: bool):")
        assert fp == "bar:3"

    def test_no_params(self):
        """Test fingerprint for parameterless function."""
        fp = get_signature_fingerprint("def no_params():")
        assert fp == "no_params:0"

    def test_ignores_return_type(self):
        """Test that fingerprint ignores return type."""
        fp1 = get_signature_fingerprint("def func(x):")
        fp2 = get_signature_fingerprint("def func(x) -> int:")
        assert fp1 == fp2


class TestSignaturesMatch:
    """Tests for signatures_match function."""

    def test_identical_signatures(self):
        """Test that identical signatures match."""
        sig1 = "def foo(x, y):"
        sig2 = "def foo(x, y):"
        assert signatures_match(sig1, sig2)

    def test_same_name_and_param_count(self):
        """Test signatures with same name and param count match."""
        sig1 = "def foo(a, b):"
        sig2 = "def foo(x, y):"
        assert signatures_match(sig1, sig2)

    def test_different_names(self):
        """Test that different names don't match."""
        sig1 = "def foo(x):"
        sig2 = "def bar(x):"
        assert not signatures_match(sig1, sig2)

    def test_different_param_counts(self):
        """Test that different param counts don't match."""
        sig1 = "def foo(x):"
        sig2 = "def foo(x, y):"
        assert not signatures_match(sig1, sig2)

    def test_invalid_signature(self):
        """Test that invalid signatures don't match."""
        sig1 = "def foo(x):"
        sig2 = "not a signature"
        assert not signatures_match(sig1, sig2)

    def test_type_hints_ignored(self):
        """Test that type hints don't affect matching."""
        sig1 = "def foo(x: int, y: str):"
        sig2 = "def foo(a, b):"
        assert signatures_match(sig1, sig2)
