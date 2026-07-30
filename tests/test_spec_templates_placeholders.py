"""
Unit tests for Placeholder Parser
==================================

Tests for the PlaceholderParser class including:
- Placeholder extraction from text
- Placeholder value validation
- Placeholder replacement
- Common placeholder utilities
- Placeholder name validation
"""

import pytest

from apps.backend.spec.templates.placeholders import PlaceholderParser


class TestPlaceholderExtraction:
    """Tests for placeholder extraction from text."""

    @pytest.fixture
    def parser(self):
        """Create a PlaceholderParser instance."""
        return PlaceholderParser()

    def test_extract_single_placeholder(self, parser):
        """Extract a single placeholder from text."""
        text = "Hello {{NAME}}"
        result = parser.extract_placeholders(text)

        assert result == ["NAME"]

    def test_extract_multiple_placeholders(self, parser):
        """Extract multiple placeholders from text."""
        text = "Hello {{NAME}}, welcome to {{PROJECT_NAME}}"
        result = parser.extract_placeholders(text)

        assert result == ["NAME", "PROJECT_NAME"]

    def test_extract_duplicate_placeholders(self, parser):
        """Extract unique placeholders when duplicates exist."""
        text = "{{NAME}} and {{EMAIL}} and {{NAME}} again"
        result = parser.extract_placeholders(text)

        # Should return unique placeholders in order of first appearance
        assert result == ["NAME", "EMAIL"]

    def test_extract_no_placeholders(self, parser):
        """Return empty list when no placeholders found."""
        text = "No placeholders here"
        result = parser.extract_placeholders(text)

        assert result == []

    def test_extract_from_empty_string(self, parser):
        """Handle empty string input."""
        result = parser.extract_placeholders("")

        assert result == []

    def test_extract_from_none(self, parser):
        """Handle None input."""
        result = parser.extract_placeholders(None)

        assert result == []

    def test_extract_placeholder_with_numbers(self, parser):
        """Extract placeholders with numbers."""
        text = "User {{USER_ID_123}} logged in"
        result = parser.extract_placeholders(text)

        assert result == ["USER_ID_123"]

    def test_extract_placeholder_with_underscores(self, parser):
        """Extract placeholders with multiple underscores."""
        text = "{{PROJECT_NAME_VERSION_2}}"
        result = parser.extract_placeholders(text)

        assert result == ["PROJECT_NAME_VERSION_2"]

    def test_ignore_lowercase_placeholders(self, parser):
        """Ignore lowercase text in braces (not valid placeholders)."""
        text = "{{name}} is not a valid placeholder"
        result = parser.extract_placeholders(text)

        # Lowercase placeholders are not valid according to the pattern
        assert result == []

    def test_ignore_mixed_case_placeholders(self, parser):
        """Ignore mixed case placeholders."""
        text = "{{ProjectName}} is not valid"
        result = parser.extract_placeholders(text)

        assert result == []

    def test_extract_from_multiline_text(self, parser):
        """Extract placeholders from multiline text."""
        text = """
        Project: {{PROJECT_NAME}}
        Author: {{AUTHOR}}
        Version: {{VERSION}}
        """
        result = parser.extract_placeholders(text)

        assert result == ["PROJECT_NAME", "AUTHOR", "VERSION"]


class TestPlaceholderValidation:
    """Tests for placeholder value validation."""

    @pytest.fixture
    def parser(self):
        """Create a PlaceholderParser instance."""
        return PlaceholderParser()

    def test_validate_all_values_present(self, parser):
        """Validation passes when all values are present."""
        placeholders = ["NAME", "EMAIL"]
        values = {"NAME": "John Doe", "EMAIL": "john@example.com"}

        errors = parser.validate_values(placeholders, values)

        assert errors == []

    def test_validate_missing_value(self, parser):
        """Validation fails when a value is missing."""
        placeholders = ["NAME", "EMAIL"]
        values = {"NAME": "John Doe"}

        errors = parser.validate_values(placeholders, values)

        assert len(errors) == 1
        assert "Missing value for placeholder: EMAIL" in errors

    def test_validate_multiple_missing_values(self, parser):
        """Validation fails with multiple missing values."""
        placeholders = ["NAME", "EMAIL", "PHONE"]
        values = {"NAME": "John Doe"}

        errors = parser.validate_values(placeholders, values)

        assert len(errors) == 2
        assert any("EMAIL" in error for error in errors)
        assert any("PHONE" in error for error in errors)

    def test_validate_empty_string_value(self, parser):
        """Validation fails when value is empty string."""
        placeholders = ["NAME"]
        values = {"NAME": ""}

        errors = parser.validate_values(placeholders, values)

        assert len(errors) == 1
        assert "Empty value for placeholder: NAME" in errors

    def test_validate_none_value(self, parser):
        """Validation fails when value is None."""
        placeholders = ["NAME"]
        values = {"NAME": None}

        errors = parser.validate_values(placeholders, values)

        assert len(errors) == 1
        assert "Empty value for placeholder: NAME" in errors

    def test_validate_no_placeholders(self, parser):
        """Validation passes when no placeholders required."""
        placeholders = []
        values = {}

        errors = parser.validate_values(placeholders, values)

        assert errors == []

    def test_validate_extra_values_ignored(self, parser):
        """Extra values in the dict are ignored."""
        placeholders = ["NAME"]
        values = {"NAME": "John", "EMAIL": "john@example.com", "EXTRA": "value"}

        errors = parser.validate_values(placeholders, values)

        assert errors == []


class TestPlaceholderReplacement:
    """Tests for placeholder replacement in text."""

    @pytest.fixture
    def parser(self):
        """Create a PlaceholderParser instance."""
        return PlaceholderParser()

    def test_replace_single_placeholder(self, parser):
        """Replace a single placeholder."""
        text = "Hello {{NAME}}"
        values = {"NAME": "World"}

        result = parser.replace(text, values)

        assert result == "Hello World"

    def test_replace_multiple_placeholders(self, parser):
        """Replace multiple placeholders."""
        text = "Hello {{NAME}}, welcome to {{PROJECT_NAME}}"
        values = {"NAME": "John", "PROJECT_NAME": "Auto Claude"}

        result = parser.replace(text, values)

        assert result == "Hello John, welcome to Auto Claude"

    def test_replace_duplicate_placeholders(self, parser):
        """Replace duplicate placeholders."""
        text = "{{NAME}} and {{NAME}} again"
        values = {"NAME": "John"}

        result = parser.replace(text, values)

        assert result == "John and John again"

    def test_replace_with_numeric_value(self, parser):
        """Replace placeholder with numeric value."""
        text = "Version {{VERSION}}"
        values = {"VERSION": 2}

        result = parser.replace(text, values)

        assert result == "Version 2"

    def test_replace_empty_text(self, parser):
        """Handle empty text."""
        result = parser.replace("", {"NAME": "John"})

        assert result == ""

    def test_replace_none_text(self, parser):
        """Handle None text."""
        result = parser.replace(None, {"NAME": "John"})

        assert result is None

    def test_replace_no_placeholders(self, parser):
        """Handle text with no placeholders."""
        text = "No placeholders here"
        values = {"NAME": "John"}

        result = parser.replace(text, values)

        assert result == text

    def test_replace_missing_value_raises_error(self, parser):
        """Raise ValueError when required value is missing."""
        text = "Hello {{NAME}}"
        values = {}

        with pytest.raises(ValueError) as exc_info:
            parser.replace(text, values)

        assert "Placeholder validation failed" in str(exc_info.value)
        assert "Missing value for placeholder: NAME" in str(exc_info.value)

    def test_replace_empty_value_raises_error(self, parser):
        """Raise ValueError when value is empty."""
        text = "Hello {{NAME}}"
        values = {"NAME": ""}

        with pytest.raises(ValueError) as exc_info:
            parser.replace(text, values)

        assert "Empty value for placeholder: NAME" in str(exc_info.value)

    def test_replace_multiline_text(self, parser):
        """Replace placeholders in multiline text."""
        text = """
        Project: {{PROJECT_NAME}}
        Author: {{AUTHOR}}
        Version: {{VERSION}}
        """
        values = {"PROJECT_NAME": "Auto Claude", "AUTHOR": "John Doe", "VERSION": "1.0"}

        result = parser.replace(text, values)

        assert "Project: Auto Claude" in result
        assert "Author: John Doe" in result
        assert "Version: 1.0" in result

    def test_replace_extra_values_ignored(self, parser):
        """Extra values don't affect replacement."""
        text = "Hello {{NAME}}"
        values = {"NAME": "John", "EMAIL": "john@example.com"}

        result = parser.replace(text, values)

        assert result == "Hello John"


class TestPlaceholderInfo:
    """Tests for placeholder information utilities."""

    @pytest.fixture
    def parser(self):
        """Create a PlaceholderParser instance."""
        return PlaceholderParser()

    def test_get_common_placeholder_info(self, parser):
        """Get information for a common placeholder."""
        info = parser.get_placeholder_info("PROJECT_NAME")

        assert info is not None
        assert info["name"] == "PROJECT_NAME"
        assert "description" in info
        assert len(info["description"]) > 0

    def test_get_unknown_placeholder_info(self, parser):
        """Return None for unknown placeholder."""
        info = parser.get_placeholder_info("UNKNOWN_PLACEHOLDER")

        assert info is None

    def test_get_all_common_placeholders(self, parser):
        """Get all common placeholders."""
        placeholders = parser.get_all_common_placeholders()

        assert len(placeholders) > 0
        assert all("name" in p for p in placeholders)
        assert all("description" in p for p in placeholders)

        # Check for expected common placeholders
        names = [p["name"] for p in placeholders]
        assert "PROJECT_NAME" in names
        assert "AUTHOR" in names
        assert "VERSION" in names

    def test_common_placeholders_have_descriptions(self, parser):
        """All common placeholders have descriptions."""
        placeholders = parser.get_all_common_placeholders()

        for placeholder in placeholders:
            assert len(placeholder["description"]) > 0


class TestPlaceholderSuggestions:
    """Tests for placeholder suggestion functionality."""

    @pytest.fixture
    def parser(self):
        """Create a PlaceholderParser instance."""
        return PlaceholderParser()

    def test_suggest_project_name(self, parser):
        """Suggest PROJECT_NAME when text mentions project."""
        text = "This is a project about building software"
        suggestions = parser.suggest_placeholders(text)

        names = [s["name"] for s in suggestions]
        assert "PROJECT_NAME" in names

    def test_suggest_author(self, parser):
        """Suggest AUTHOR when text mentions author."""
        text = "Written by the author"
        suggestions = parser.suggest_placeholders(text)

        names = [s["name"] for s in suggestions]
        assert "AUTHOR" in names

    def test_suggest_version(self, parser):
        """Suggest VERSION when text mentions version."""
        text = "Version 2.0 release"
        suggestions = parser.suggest_placeholders(text)

        names = [s["name"] for s in suggestions]
        assert "VERSION" in names

    def test_suggest_email(self, parser):
        """Suggest EMAIL when text mentions email."""
        text = "Contact us via email"
        suggestions = parser.suggest_placeholders(text)

        names = [s["name"] for s in suggestions]
        assert "EMAIL" in names

    def test_suggest_license(self, parser):
        """Suggest LICENSE when text mentions license."""
        text = "This is licensed under MIT"
        suggestions = parser.suggest_placeholders(text)

        names = [s["name"] for s in suggestions]
        assert "LICENSE" in names

    def test_suggest_repository(self, parser):
        """Suggest REPOSITORY when text mentions repo."""
        text = "Check out the GitHub repository"
        suggestions = parser.suggest_placeholders(text)

        names = [s["name"] for s in suggestions]
        assert "REPOSITORY" in names

    def test_suggest_empty_text(self, parser):
        """Return empty list for empty text."""
        suggestions = parser.suggest_placeholders("")

        assert suggestions == []

    def test_suggest_none_text(self, parser):
        """Return empty list for None text."""
        suggestions = parser.suggest_placeholders(None)

        assert suggestions == []

    def test_suggest_no_matches(self, parser):
        """Return empty list when no keywords match."""
        text = "xyz abc def"
        suggestions = parser.suggest_placeholders(text)

        assert suggestions == []

    def test_suggest_multiple_placeholders(self, parser):
        """Suggest multiple placeholders when multiple keywords match."""
        text = "Project created by author in 2024"
        suggestions = parser.suggest_placeholders(text)

        names = [s["name"] for s in suggestions]
        assert len(names) >= 2
        assert "PROJECT_NAME" in names or "AUTHOR" in names


class TestPlaceholderNameValidation:
    """Tests for placeholder name validation."""

    @pytest.fixture
    def parser(self):
        """Create a PlaceholderParser instance."""
        return PlaceholderParser()

    def test_valid_uppercase_name(self, parser):
        """Validate uppercase placeholder name."""
        assert parser.is_valid_placeholder_name("NAME") is True

    def test_valid_name_with_underscores(self, parser):
        """Validate placeholder name with underscores."""
        assert parser.is_valid_placeholder_name("PROJECT_NAME") is True

    def test_valid_name_with_numbers(self, parser):
        """Validate placeholder name with numbers."""
        assert parser.is_valid_placeholder_name("USER_ID_123") is True

    def test_valid_name_starting_with_underscore(self, parser):
        """Validate placeholder name starting with underscore."""
        assert parser.is_valid_placeholder_name("_PRIVATE") is True

    def test_invalid_lowercase_name(self, parser):
        """Invalidate lowercase placeholder name."""
        assert parser.is_valid_placeholder_name("name") is False

    def test_invalid_mixed_case_name(self, parser):
        """Invalidate mixed case placeholder name."""
        assert parser.is_valid_placeholder_name("ProjectName") is False

    def test_invalid_name_starting_with_number(self, parser):
        """Invalidate placeholder name starting with number."""
        assert parser.is_valid_placeholder_name("123_NAME") is False

    def test_invalid_name_with_special_chars(self, parser):
        """Invalidate placeholder name with special characters."""
        assert parser.is_valid_placeholder_name("NAME-WITH-DASHES") is False
        assert parser.is_valid_placeholder_name("NAME.WITH.DOTS") is False
        assert parser.is_valid_placeholder_name("NAME WITH SPACES") is False

    def test_invalid_empty_name(self, parser):
        """Invalidate empty placeholder name."""
        assert parser.is_valid_placeholder_name("") is False

    def test_invalid_none_name(self, parser):
        """Invalidate None placeholder name."""
        assert parser.is_valid_placeholder_name(None) is False


class TestPlaceholderPattern:
    """Tests for the placeholder regex pattern."""

    @pytest.fixture
    def parser(self):
        """Create a PlaceholderParser instance."""
        return PlaceholderParser()

    def test_pattern_matches_valid_placeholder(self, parser):
        """Pattern matches valid placeholder syntax."""
        match = parser.pattern.search("{{NAME}}")

        assert match is not None
        assert match.group(1) == "NAME"

    def test_pattern_extracts_placeholder_name(self, parser):
        """Pattern extracts placeholder name without braces."""
        matches = parser.pattern.findall("Hello {{NAME}}, {{EMAIL}}")

        assert matches == ["NAME", "EMAIL"]

    def test_pattern_ignores_single_braces(self, parser):
        """Pattern ignores single braces."""
        matches = parser.pattern.findall("{NAME}")

        assert matches == []

    def test_pattern_ignores_mismatched_braces(self, parser):
        """Pattern ignores mismatched braces."""
        matches = parser.pattern.findall("{{NAME} or {NAME}}")

        assert matches == []

    def test_pattern_requires_uppercase(self, parser):
        """Pattern requires uppercase placeholder names."""
        matches = parser.pattern.findall("{{name}}")

        assert matches == []


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.fixture
    def parser(self):
        """Create a PlaceholderParser instance."""
        return PlaceholderParser()

    def test_placeholder_at_start_of_text(self, parser):
        """Handle placeholder at the start of text."""
        text = "{{NAME}} is the first thing"
        result = parser.replace(text, {"NAME": "John"})

        assert result == "John is the first thing"

    def test_placeholder_at_end_of_text(self, parser):
        """Handle placeholder at the end of text."""
        text = "The last thing is {{NAME}}"
        result = parser.replace(text, {"NAME": "John"})

        assert result == "The last thing is John"

    def test_adjacent_placeholders(self, parser):
        """Handle adjacent placeholders without spaces."""
        text = "{{FIRST}}{{LAST}}"
        result = parser.replace(text, {"FIRST": "Hello", "LAST": "World"})

        assert result == "HelloWorld"

    def test_placeholder_with_special_chars_in_value(self, parser):
        """Handle special characters in replacement values."""
        text = "Project: {{NAME}}"
        result = parser.replace(text, {"NAME": "Test & Demo (v1.0)"})

        assert result == "Project: Test & Demo (v1.0)"

    def test_placeholder_with_unicode_value(self, parser):
        """Handle unicode characters in replacement values."""
        text = "Author: {{AUTHOR}}"
        result = parser.replace(text, {"AUTHOR": "José García"})

        assert result == "Author: José García"

    def test_very_long_placeholder_name(self, parser):
        """Handle very long placeholder names."""
        long_name = "A" * 100
        text = f"{{{{{long_name}}}}}"
        placeholders = parser.extract_placeholders(text)

        assert placeholders == [long_name]

    def test_placeholder_in_json_like_text(self, parser):
        """Handle placeholders in JSON-like structures."""
        text = '{"name": "{{NAME}}", "email": "{{EMAIL}}"}'
        result = parser.replace(text, {"NAME": "John", "EMAIL": "john@example.com"})

        assert result == '{"name": "John", "email": "john@example.com"}'
