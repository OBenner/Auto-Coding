"""
Placeholder Parser and Validator
=================================

Handles parsing, validation, and replacement of {{PLACEHOLDER}} syntax in templates.
"""

import re
from typing import Any


class PlaceholderParser:
    """Parser and validator for template placeholders."""

    # Common placeholder names and their descriptions
    COMMON_PLACEHOLDERS = {
        "PROJECT_NAME": "Name of the project",
        "AUTHOR": "Author name",
        "VERSION": "Version number",
        "DESCRIPTION": "Project description",
        "EMAIL": "Contact email address",
        "LICENSE": "License type",
        "REPOSITORY": "Repository URL",
        "DATE": "Current date",
        "YEAR": "Current year",
        "ORGANIZATION": "Organization name",
    }

    def __init__(self):
        """Initialize the placeholder parser."""
        # Pattern to match {{PLACEHOLDER}} syntax
        self.pattern = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")

    def extract_placeholders(self, text: str) -> list[str]:
        """
        Extract all placeholders from text.

        Args:
            text: Text containing placeholders

        Returns:
            List of unique placeholder names (without braces)

        Example:
            >>> parser = PlaceholderParser()
            >>> parser.extract_placeholders("Hello {{NAME}}, welcome to {{PROJECT_NAME}}")
            ['NAME', 'PROJECT_NAME']
        """
        if not text:
            return []

        matches = self.pattern.findall(text)
        # Return unique placeholders in order of first appearance
        seen = set()
        result = []
        for match in matches:
            if match not in seen:
                seen.add(match)
                result.append(match)
        return result

    def validate_values(
        self, placeholders: list[str], values: dict[str, Any]
    ) -> list[str]:
        """
        Validate that all required placeholders have values.

        Args:
            placeholders: List of placeholder names to validate
            values: Dictionary of placeholder values

        Returns:
            List of validation error messages (empty if valid)

        Example:
            >>> parser = PlaceholderParser()
            >>> parser.validate_values(['NAME', 'EMAIL'], {'NAME': 'John'})
            ['Missing value for placeholder: EMAIL']
        """
        errors = []

        for placeholder in placeholders:
            if placeholder not in values:
                errors.append(f"Missing value for placeholder: {placeholder}")
            elif values[placeholder] is None or values[placeholder] == "":
                errors.append(f"Empty value for placeholder: {placeholder}")

        return errors

    def replace(self, text: str, values: dict[str, Any]) -> str:
        """
        Replace placeholders in text with provided values.

        Args:
            text: Text containing placeholders
            values: Dictionary mapping placeholder names to values

        Returns:
            Text with placeholders replaced

        Raises:
            ValueError: If required placeholders are missing values

        Example:
            >>> parser = PlaceholderParser()
            >>> parser.replace("Hello {{NAME}}", {"NAME": "World"})
            'Hello World'
        """
        if not text:
            return text

        # Extract placeholders from text
        placeholders = self.extract_placeholders(text)

        # Validate values
        errors = self.validate_values(placeholders, values)
        if errors:
            raise ValueError(f"Placeholder validation failed: {', '.join(errors)}")

        # Replace placeholders
        result = text
        for placeholder, value in values.items():
            pattern = f"{{{{{placeholder}}}}}"
            result = result.replace(pattern, str(value))

        return result

    def get_placeholder_info(self, placeholder: str) -> dict[str, str] | None:
        """
        Get information about a common placeholder.

        Args:
            placeholder: Placeholder name

        Returns:
            Dictionary with placeholder info or None if not a common placeholder

        Example:
            >>> parser = PlaceholderParser()
            >>> info = parser.get_placeholder_info("PROJECT_NAME")
            >>> info["description"]
            'Name of the project'
        """
        if placeholder in self.COMMON_PLACEHOLDERS:
            return {
                "name": placeholder,
                "description": self.COMMON_PLACEHOLDERS[placeholder],
            }
        return None

    def get_all_common_placeholders(self) -> list[dict[str, str]]:
        """
        Get information about all common placeholders.

        Returns:
            List of dictionaries with placeholder info

        Example:
            >>> parser = PlaceholderParser()
            >>> placeholders = parser.get_all_common_placeholders()
            >>> len(placeholders) > 0
            True
        """
        return [
            {"name": name, "description": desc}
            for name, desc in self.COMMON_PLACEHOLDERS.items()
        ]

    def suggest_placeholders(self, text: str) -> list[dict[str, str]]:
        """
        Suggest common placeholders based on text content.

        Args:
            text: Text to analyze

        Returns:
            List of suggested placeholder dictionaries

        Example:
            >>> parser = PlaceholderParser()
            >>> suggestions = parser.suggest_placeholders("project name author")
            >>> any(s["name"] == "PROJECT_NAME" for s in suggestions)
            True
        """
        if not text:
            return []

        text_lower = text.lower()
        suggestions = []

        # Check for keywords related to common placeholders
        keyword_mapping = {
            "PROJECT_NAME": ["project", "name", "app", "application"],
            "AUTHOR": ["author", "developer", "creator", "maintainer"],
            "VERSION": ["version", "release", "v1", "v2"],
            "DESCRIPTION": ["description", "summary", "overview"],
            "EMAIL": ["email", "contact", "mail"],
            "LICENSE": ["license", "mit", "apache", "gpl"],
            "REPOSITORY": ["repo", "repository", "github", "gitlab"],
            "DATE": ["date", "created", "timestamp"],
            "YEAR": ["year", "copyright"],
            "ORGANIZATION": ["organization", "company", "org", "team"],
        }

        for placeholder, keywords in keyword_mapping.items():
            if any(keyword in text_lower for keyword in keywords):
                info = self.get_placeholder_info(placeholder)
                if info:
                    suggestions.append(info)

        return suggestions

    def is_valid_placeholder_name(self, name: str) -> bool:
        """
        Check if a placeholder name is valid.

        Valid placeholder names:
        - Start with uppercase letter or underscore
        - Contain only uppercase letters, numbers, and underscores
        - Examples: NAME, PROJECT_NAME, USER_ID_123

        Args:
            name: Placeholder name to validate

        Returns:
            True if valid, False otherwise

        Example:
            >>> parser = PlaceholderParser()
            >>> parser.is_valid_placeholder_name("PROJECT_NAME")
            True
            >>> parser.is_valid_placeholder_name("project_name")
            False
        """
        if not name:
            return False

        # Must match pattern: start with A-Z or _, then A-Z, 0-9, or _
        pattern = re.compile(r"^[A-Z_][A-Z0-9_]*$")
        return bool(pattern.match(name))
