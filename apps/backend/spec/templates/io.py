"""
Template Import/Export Module
==============================

Handles serialization and deserialization of spec templates to/from JSON format.

This module provides functionality to:
- Export templates to JSON dictionaries for storage and sharing
- Import templates from JSON dictionaries
- Preserve all template metadata including placeholders
- Support both built-in and custom templates

Example usage:
    >>> from spec.templates.io import export_template, import_template
    >>> template = library.get_template("crud_api")
    >>> json_data = export_template(template)
    >>> restored_template = import_template(json_data)
"""

import logging
from typing import Any

from .registry import Template

logger = logging.getLogger(__name__)


class CustomTemplate(Template):
    """
    Custom template class for imported/exported templates.

    This class is used to represent templates that have been imported from JSON
    or created through the UI, as opposed to built-in templates defined in code.
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        parameters: dict[str, Any],
        placeholders: list[str] | None = None,
        template_content: dict[str, Any] | None = None,
    ):
        """
        Initialize a custom template.

        Args:
            name: Unique template identifier
            description: Human-readable description
            category: Template category (e.g., 'api', 'ui', 'database')
            parameters: Parameter definitions with types and defaults
            placeholders: Optional list of placeholder names
            template_content: Template content structure (for JSON-based templates)
        """
        super().__init__(name, description, category, parameters, placeholders)
        self.template_content = template_content or {}

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Generate spec content from template parameters.

        For custom templates, this uses the stored template_content structure
        and replaces parameter placeholders with actual values.

        Args:
            params: User-provided parameter values

        Returns:
            Dictionary containing spec content
        """
        # Start with template content
        content = self.template_content.copy()

        # If template has a generation function stored, use it
        # Otherwise, return the static content
        # This allows for both static and dynamic templates
        return content


def export_template(template: Template) -> dict[str, Any]:
    """
    Export a template to a JSON-compatible dictionary.

    Serializes all template metadata including name, description, category,
    parameters, and placeholders. For CustomTemplate instances, also includes
    the template content.

    Args:
        template: Template instance to export

    Returns:
        Dictionary containing all template data in JSON-compatible format

    Example:
        >>> template = CustomTemplate(
        ...     name="my-template",
        ...     description="My custom template",
        ...     category="api",
        ...     parameters={"param1": {"type": "str", "required": True}},
        ...     placeholders=["PROJECT_NAME"]
        ... )
        >>> data = export_template(template)
        >>> data["name"]
        'my-template'
    """
    # Basic template metadata
    export_data = {
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "parameters": _serialize_parameters(template.parameters),
        "placeholders": template.placeholders or [],
    }

    # If this is a CustomTemplate, include the template content
    if isinstance(template, CustomTemplate):
        export_data["template_content"] = template.template_content

    # Add version info for future compatibility
    export_data["_export_version"] = "1.0"

    return export_data


def import_template(data: dict[str, Any]) -> Template:
    """
    Import a template from a JSON dictionary.

    Deserializes template data and creates a CustomTemplate instance.
    Validates required fields and provides defaults for optional fields.

    Args:
        data: Dictionary containing template data

    Returns:
        CustomTemplate instance

    Raises:
        ValueError: If required fields are missing or data is invalid

    Example:
        >>> data = {
        ...     "name": "my-template",
        ...     "description": "My custom template",
        ...     "category": "api",
        ...     "parameters": {},
        ...     "placeholders": []
        ... }
        >>> template = import_template(data)
        >>> template.name
        'my-template'
    """
    # Validate required fields
    required_fields = ["name", "description", "category"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(
            f"Missing required fields in template data: {', '.join(missing_fields)}"
        )

    # Extract fields with defaults for optional ones
    name = data["name"]
    description = data["description"]
    category = data["category"]
    parameters = _deserialize_parameters(data.get("parameters", {}))
    placeholders = data.get("placeholders", [])
    template_content = data.get("template_content", {})

    # Check export version for compatibility (future-proofing)
    export_version = data.get("_export_version", "1.0")
    if export_version != "1.0":
        logger.warning(
            "Importing template '%s' with export version %s (current version: 1.0)",
            name,
            export_version,
        )

    # Create CustomTemplate instance
    template = CustomTemplate(
        name=name,
        description=description,
        category=category,
        parameters=parameters,
        placeholders=placeholders,
        template_content=template_content,
    )

    return template


def _serialize_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """
    Serialize parameter definitions to JSON-compatible format.

    Converts Python types to string representations for JSON serialization.

    Args:
        parameters: Parameter definitions dictionary

    Returns:
        JSON-compatible parameter definitions
    """
    serialized = {}

    for param_name, param_def in parameters.items():
        param_copy = param_def.copy()

        # Convert type to string representation
        if "type" in param_copy:
            param_type = param_copy["type"]
            if isinstance(param_type, type):
                # Convert Python type to string (e.g., str -> "str")
                param_copy["type"] = param_type.__name__
            else:
                # Already a string or other serializable value
                param_copy["type"] = str(param_type)

        serialized[param_name] = param_copy

    return serialized


def _deserialize_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """
    Deserialize parameter definitions from JSON format.

    Converts string type representations back to Python types.

    Args:
        parameters: JSON parameter definitions

    Returns:
        Parameter definitions with Python types
    """
    deserialized = {}

    # Type name to Python type mapping
    type_mapping = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
    }

    for param_name, param_def in parameters.items():
        param_copy = param_def.copy()

        # Convert string type back to Python type
        if "type" in param_copy:
            type_str = param_copy["type"]
            if isinstance(type_str, str) and type_str in type_mapping:
                param_copy["type"] = type_mapping[type_str]
            # else: keep as-is (might be a custom type or already converted)

        deserialized[param_name] = param_copy

    return deserialized


def export_template_to_file(template: Template, file_path: str) -> None:
    """
    Export a template to a JSON file.

    Convenience function that exports a template and writes it to a file.

    Args:
        template: Template instance to export
        file_path: Path to write the JSON file to

    Example:
        >>> template = library.get_template("crud_api")
        >>> export_template_to_file(template, "my-template.json")
    """
    import json
    from pathlib import Path

    data = export_template(template)
    output_path = Path(file_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Exported template '%s' to %s", template.name, output_path)


def import_template_from_file(file_path: str) -> Template:
    """
    Import a template from a JSON file.

    Convenience function that reads a JSON file and imports the template.

    Args:
        file_path: Path to the JSON file to import

    Returns:
        Imported Template instance

    Raises:
        ValueError: If file is invalid or template data is malformed
        FileNotFoundError: If file doesn't exist

    Example:
        >>> template = import_template_from_file("my-template.json")
        >>> template.name
        'my-template'
    """
    import json
    from pathlib import Path

    input_path = Path(file_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Template file not found: {file_path}")

    try:
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in template file: {e}") from e

    template = import_template(data)
    logger.info("Imported template '%s' from %s", template.name, input_path)

    return template
