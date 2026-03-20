"""
Unit tests for Template Import/Export
======================================

Tests for the template import/export module including:
- Template export to JSON dictionaries
- Template import from JSON dictionaries
- Round-trip export/import preservation
- File-based import/export
- Parameter serialization/deserialization
- TemplateLibrary integration
- Validation during import
"""

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from apps.backend.spec.templates.io import (
    CustomTemplate,
    export_template,
    export_template_to_file,
    import_template,
    import_template_from_file,
    _serialize_parameters,
    _deserialize_parameters,
)
from apps.backend.spec.templates.library import TemplateLibrary
from apps.backend.spec.templates.registry import Template


# =============================================================================
# Test Fixtures
# =============================================================================


class MockTemplate(Template):
    """Mock template for testing."""

    def __init__(
        self,
        name: str = "test_template",
        description: str = "Test template description",
        category: str = "testing",
        parameters: dict[str, Any] | None = None,
        placeholders: list[str] | None = None,
    ):
        super().__init__(
            name=name,
            description=description,
            category=category,
            parameters=parameters or {},
            placeholders=placeholders or [],
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate mock content."""
        return {
            "title": f"Feature: {params.get('name', 'Default')}",
            "description": "Mock template content",
        }


@pytest.fixture
def simple_template():
    """Create a simple template for testing."""
    return MockTemplate(
        name="simple_template",
        description="A simple test template",
        category="testing",
    )


@pytest.fixture
def template_with_placeholders():
    """Create a template with placeholders."""
    return MockTemplate(
        name="placeholder_template",
        description="Template with placeholders",
        category="api",
        placeholders=["PROJECT_NAME", "AUTHOR", "VERSION"],
    )


@pytest.fixture
def template_with_parameters():
    """Create a template with parameters."""
    return MockTemplate(
        name="param_template",
        description="Template with parameters",
        category="database",
        parameters={
            "entity_name": {"type": str, "default": "User", "required": True},
            "include_timestamps": {"type": bool, "default": True},
            "max_items": {"type": int, "default": 100},
            "tags": {"type": list, "default": ["tag1", "tag2"]},
        },
    )


@pytest.fixture
def custom_template():
    """Create a CustomTemplate instance."""
    return CustomTemplate(
        name="custom_template",
        description="Custom template with content",
        category="ui",
        parameters={
            "component_name": {"type": str, "required": True},
        },
        placeholders=["PROJECT_NAME"],
        template_content={
            "title": "{{PROJECT_NAME}} Component",
            "description": "Custom component",
        },
    )


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Test Export Functionality
# =============================================================================


class TestExportTemplate:
    """Tests for export_template() function."""

    def test_export_simple_template(self, simple_template):
        """Export a simple template with basic fields."""
        data = export_template(simple_template)

        assert data["name"] == "simple_template"
        assert data["description"] == "A simple test template"
        assert data["category"] == "testing"
        assert data["parameters"] == {}
        assert data["placeholders"] == []
        assert data["_export_version"] == "1.0"

    def test_export_template_with_placeholders(self, template_with_placeholders):
        """Export template with placeholders."""
        data = export_template(template_with_placeholders)

        assert data["name"] == "placeholder_template"
        assert data["placeholders"] == ["PROJECT_NAME", "AUTHOR", "VERSION"]

    def test_export_template_with_parameters(self, template_with_parameters):
        """Export template with parameters."""
        data = export_template(template_with_parameters)

        assert data["name"] == "param_template"
        assert "parameters" in data
        assert "entity_name" in data["parameters"]
        assert data["parameters"]["entity_name"]["type"] == "str"
        assert data["parameters"]["entity_name"]["default"] == "User"

    def test_export_custom_template(self, custom_template):
        """Export CustomTemplate includes template_content."""
        data = export_template(custom_template)

        assert data["name"] == "custom_template"
        assert "template_content" in data
        assert data["template_content"]["title"] == "{{PROJECT_NAME}} Component"

    def test_export_version_included(self, simple_template):
        """Export includes version info."""
        data = export_template(simple_template)

        assert "_export_version" in data
        assert data["_export_version"] == "1.0"

    def test_export_preserves_all_fields(self):
        """Export preserves all template fields."""
        template = MockTemplate(
            name="comprehensive",
            description="Comprehensive template",
            category="testing",
            parameters={
                "param1": {"type": str, "default": "value1"},
                "param2": {"type": int, "default": 42},
            },
            placeholders=["PLACEHOLDER1", "PLACEHOLDER2"],
        )
        data = export_template(template)

        assert data["name"] == "comprehensive"
        assert data["description"] == "Comprehensive template"
        assert data["category"] == "testing"
        assert len(data["parameters"]) == 2
        assert len(data["placeholders"]) == 2


# =============================================================================
# Test Import Functionality
# =============================================================================


class TestImportTemplate:
    """Tests for import_template() function."""

    def test_import_minimal_template(self):
        """Import minimal valid template."""
        data = {
            "name": "minimal",
            "description": "Minimal template",
            "category": "testing",
        }
        template = import_template(data)

        assert template.name == "minimal"
        assert template.description == "Minimal template"
        assert template.category == "testing"
        assert template.parameters == {}
        assert template.placeholders == []

    def test_import_template_with_placeholders(self):
        """Import template with placeholders."""
        data = {
            "name": "with_placeholders",
            "description": "Template with placeholders",
            "category": "api",
            "placeholders": ["PROJECT_NAME", "AUTHOR"],
        }
        template = import_template(data)

        assert template.placeholders == ["PROJECT_NAME", "AUTHOR"]

    def test_import_template_with_parameters(self):
        """Import template with parameters."""
        data = {
            "name": "with_params",
            "description": "Template with parameters",
            "category": "database",
            "parameters": {
                "entity_name": {"type": "str", "default": "User"},
                "enabled": {"type": "bool", "default": True},
            },
        }
        template = import_template(data)

        assert "entity_name" in template.parameters
        assert template.parameters["entity_name"]["type"] == str
        assert template.parameters["entity_name"]["default"] == "User"

    def test_import_template_with_content(self):
        """Import template with template_content."""
        data = {
            "name": "with_content",
            "description": "Template with content",
            "category": "ui",
            "template_content": {
                "title": "Test",
                "description": "Content",
            },
        }
        template = import_template(data)

        assert isinstance(template, CustomTemplate)
        assert template.template_content["title"] == "Test"

    def test_import_missing_required_field(self):
        """Import fails when required field is missing."""
        data = {
            "description": "Missing name field",
            "category": "testing",
        }

        with pytest.raises(ValueError) as exc_info:
            import_template(data)

        assert "missing required fields" in str(exc_info.value).lower()
        assert "name" in str(exc_info.value).lower()

    def test_import_missing_multiple_required_fields(self):
        """Import fails when multiple required fields are missing."""
        data = {
            "name": "only_name",
        }

        with pytest.raises(ValueError) as exc_info:
            import_template(data)

        assert "missing required fields" in str(exc_info.value).lower()

    def test_import_with_old_export_version(self):
        """Import with older export version logs warning but succeeds."""
        data = {
            "name": "old_version",
            "description": "Template from old version",
            "category": "testing",
            "_export_version": "0.9",
        }

        # Should still import successfully (with warning logged)
        template = import_template(data)
        assert template.name == "old_version"

    def test_import_defaults_optional_fields(self):
        """Import provides defaults for optional fields."""
        data = {
            "name": "minimal",
            "description": "Minimal template",
            "category": "testing",
            # No parameters or placeholders
        }
        template = import_template(data)

        assert template.parameters == {}
        assert template.placeholders == []
        assert template.template_content == {}


# =============================================================================
# Test Round-Trip Export/Import
# =============================================================================


class TestRoundTripExportImport:
    """Tests for round-trip export/import preservation."""

    def test_round_trip_simple_template(self, simple_template):
        """Simple template survives round-trip."""
        exported = export_template(simple_template)
        imported = import_template(exported)

        assert imported.name == simple_template.name
        assert imported.description == simple_template.description
        assert imported.category == simple_template.category

    def test_round_trip_preserves_placeholders(self, template_with_placeholders):
        """Placeholders preserved in round-trip."""
        exported = export_template(template_with_placeholders)
        imported = import_template(exported)

        assert imported.placeholders == template_with_placeholders.placeholders

    def test_round_trip_preserves_parameters(self, template_with_parameters):
        """Parameters preserved in round-trip."""
        exported = export_template(template_with_parameters)
        imported = import_template(exported)

        assert "entity_name" in imported.parameters
        assert imported.parameters["entity_name"]["type"] == str
        assert imported.parameters["entity_name"]["default"] == "User"
        assert imported.parameters["entity_name"]["required"] is True

    def test_round_trip_preserves_template_content(self, custom_template):
        """Template content preserved in round-trip."""
        exported = export_template(custom_template)
        imported = import_template(exported)

        assert isinstance(imported, CustomTemplate)
        assert imported.template_content == custom_template.template_content

    def test_round_trip_preserves_all_parameter_types(self):
        """All parameter types preserved in round-trip."""
        template = MockTemplate(
            name="all_types",
            description="Template with all parameter types",
            category="testing",
            parameters={
                "str_param": {"type": str, "default": "value"},
                "int_param": {"type": int, "default": 42},
                "float_param": {"type": float, "default": 3.14},
                "bool_param": {"type": bool, "default": True},
                "list_param": {"type": list, "default": [1, 2, 3]},
                "dict_param": {"type": dict, "default": {"key": "value"}},
            },
        )

        exported = export_template(template)
        imported = import_template(exported)

        assert imported.parameters["str_param"]["type"] == str
        assert imported.parameters["int_param"]["type"] == int
        assert imported.parameters["float_param"]["type"] == float
        assert imported.parameters["bool_param"]["type"] == bool
        assert imported.parameters["list_param"]["type"] == list
        assert imported.parameters["dict_param"]["type"] == dict


# =============================================================================
# Test Parameter Serialization
# =============================================================================


class TestParameterSerialization:
    """Tests for _serialize_parameters() function."""

    def test_serialize_empty_parameters(self):
        """Serialize empty parameters."""
        result = _serialize_parameters({})
        assert result == {}

    def test_serialize_string_type(self):
        """Serialize string type to 'str'."""
        params = {"name": {"type": str, "default": "value"}}
        result = _serialize_parameters(params)

        assert result["name"]["type"] == "str"
        assert result["name"]["default"] == "value"

    def test_serialize_all_basic_types(self):
        """Serialize all basic Python types."""
        params = {
            "str_param": {"type": str},
            "int_param": {"type": int},
            "float_param": {"type": float},
            "bool_param": {"type": bool},
            "list_param": {"type": list},
            "dict_param": {"type": dict},
        }
        result = _serialize_parameters(params)

        assert result["str_param"]["type"] == "str"
        assert result["int_param"]["type"] == "int"
        assert result["float_param"]["type"] == "float"
        assert result["bool_param"]["type"] == "bool"
        assert result["list_param"]["type"] == "list"
        assert result["dict_param"]["type"] == "dict"

    def test_serialize_preserves_other_fields(self):
        """Serialize preserves non-type fields."""
        params = {
            "param": {
                "type": str,
                "default": "value",
                "required": True,
                "description": "A parameter",
            }
        }
        result = _serialize_parameters(params)

        assert result["param"]["default"] == "value"
        assert result["param"]["required"] is True
        assert result["param"]["description"] == "A parameter"

    def test_serialize_already_string_type(self):
        """Serialize handles already-string type."""
        params = {"param": {"type": "str"}}
        result = _serialize_parameters(params)

        assert result["param"]["type"] == "str"


# =============================================================================
# Test Parameter Deserialization
# =============================================================================


class TestParameterDeserialization:
    """Tests for _deserialize_parameters() function."""

    def test_deserialize_empty_parameters(self):
        """Deserialize empty parameters."""
        result = _deserialize_parameters({})
        assert result == {}

    def test_deserialize_string_type(self):
        """Deserialize 'str' to str type."""
        params = {"name": {"type": "str", "default": "value"}}
        result = _deserialize_parameters(params)

        assert result["name"]["type"] == str
        assert result["name"]["default"] == "value"

    def test_deserialize_all_basic_types(self):
        """Deserialize all basic type strings."""
        params = {
            "str_param": {"type": "str"},
            "int_param": {"type": "int"},
            "float_param": {"type": "float"},
            "bool_param": {"type": "bool"},
            "list_param": {"type": "list"},
            "dict_param": {"type": "dict"},
        }
        result = _deserialize_parameters(params)

        assert result["str_param"]["type"] == str
        assert result["int_param"]["type"] == int
        assert result["float_param"]["type"] == float
        assert result["bool_param"]["type"] == bool
        assert result["list_param"]["type"] == list
        assert result["dict_param"]["type"] == dict

    def test_deserialize_preserves_other_fields(self):
        """Deserialize preserves non-type fields."""
        params = {
            "param": {
                "type": "str",
                "default": "value",
                "required": True,
                "description": "A parameter",
            }
        }
        result = _deserialize_parameters(params)

        assert result["param"]["default"] == "value"
        assert result["param"]["required"] is True
        assert result["param"]["description"] == "A parameter"

    def test_deserialize_unknown_type_string(self):
        """Deserialize unknown type string keeps as-is."""
        params = {"param": {"type": "custom_type"}}
        result = _deserialize_parameters(params)

        # Should keep as-is if not in mapping
        assert result["param"]["type"] == "custom_type"

    def test_deserialize_already_python_type(self):
        """Deserialize handles already-Python type."""
        params = {"param": {"type": str}}
        result = _deserialize_parameters(params)

        # Should remain as Python type
        assert result["param"]["type"] == str


# =============================================================================
# Test File Import/Export
# =============================================================================


class TestFileImportExport:
    """Tests for file-based import/export functions."""

    def test_export_to_file(self, simple_template, temp_dir):
        """Export template to JSON file."""
        file_path = temp_dir / "template.json"
        export_template_to_file(simple_template, str(file_path))

        assert file_path.exists()
        with open(file_path) as f:
            data = json.load(f)

        assert data["name"] == "simple_template"
        assert data["description"] == "A simple test template"

    def test_export_to_file_creates_directory(self, simple_template, temp_dir):
        """Export creates parent directories if needed."""
        file_path = temp_dir / "nested" / "dir" / "template.json"
        export_template_to_file(simple_template, str(file_path))

        assert file_path.exists()

    def test_import_from_file(self, simple_template, temp_dir):
        """Import template from JSON file."""
        file_path = temp_dir / "template.json"

        # First export
        export_template_to_file(simple_template, str(file_path))

        # Then import
        imported = import_template_from_file(str(file_path))

        assert imported.name == simple_template.name
        assert imported.description == simple_template.description

    def test_import_from_nonexistent_file(self, temp_dir):
        """Import from nonexistent file raises error."""
        file_path = temp_dir / "nonexistent.json"

        with pytest.raises(FileNotFoundError) as exc_info:
            import_template_from_file(str(file_path))

        assert "not found" in str(exc_info.value).lower()

    def test_import_from_invalid_json(self, temp_dir):
        """Import from invalid JSON raises error."""
        file_path = temp_dir / "invalid.json"
        file_path.write_text("{ invalid json }")

        with pytest.raises(ValueError) as exc_info:
            import_template_from_file(str(file_path))

        assert "invalid json" in str(exc_info.value).lower()

    def test_file_round_trip(self, template_with_parameters, temp_dir):
        """File export/import round-trip preserves data."""
        file_path = temp_dir / "template.json"

        # Export
        export_template_to_file(template_with_parameters, str(file_path))

        # Import
        imported = import_template_from_file(str(file_path))

        assert imported.name == template_with_parameters.name
        assert imported.description == template_with_parameters.description
        assert imported.parameters["entity_name"]["type"] == str


# =============================================================================
# Test TemplateLibrary Integration
# =============================================================================


class TestTemplateLibraryIntegration:
    """Tests for TemplateLibrary import/export methods."""

    @pytest.fixture
    def library(self, temp_dir):
        """Create a TemplateLibrary instance."""
        return TemplateLibrary(custom_templates_dir=temp_dir)

    def test_library_export_template(self, library):
        """TemplateLibrary.export_template() exports template."""
        # Library has built-in templates, use one of those
        # or register a test template
        template = MockTemplate(name="test_export", description="Test export template")
        library.registry.register(template)

        data = library.export_template("test_export")

        assert data["name"] == "test_export"
        assert data["description"] == "Test export template"

    def test_library_export_nonexistent_template(self, library):
        """Export nonexistent template raises error."""
        with pytest.raises(ValueError) as exc_info:
            library.export_template("nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_library_import_template_data(self, library):
        """TemplateLibrary.import_template_data() imports and validates."""
        data = {
            "name": "imported_template",
            "description": "Imported template description",
            "category": "testing",
            "parameters": {},
            "placeholders": [],
        }

        template = library.import_template_data(data)

        assert template.name == "imported_template"
        # Should be registered in library
        assert library.get_template("imported_template") is not None

    def test_library_import_invalid_template(self, library):
        """Import invalid template raises error."""
        data = {
            "name": "",  # Invalid: empty name
            "description": "Valid description",
            "category": "testing",
        }

        with pytest.raises(ValueError) as exc_info:
            library.import_template_data(data)

        assert "validation failed" in str(exc_info.value).lower()

    def test_library_export_template_file(self, library, temp_dir):
        """TemplateLibrary.export_template_file() exports to file."""
        template = MockTemplate(name="file_export", description="File export test template")
        library.registry.register(template)

        file_path = temp_dir / "exported.json"
        library.export_template_file("file_export", file_path)

        assert file_path.exists()
        with open(file_path) as f:
            data = json.load(f)
        assert data["name"] == "file_export"

    def test_library_import_template_file(self, library, temp_dir):
        """TemplateLibrary.import_template_file() imports from file."""
        # Create a valid template file
        data = {
            "name": "file_imported",
            "description": "Imported from file template",
            "category": "testing",
            "parameters": {},
            "placeholders": [],
        }
        file_path = temp_dir / "import.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        template = library.import_template_file(file_path)

        assert template.name == "file_imported"
        # Should be registered
        assert library.get_template("file_imported") is not None

    def test_library_import_file_with_validation_error(self, library, temp_dir):
        """Import file with validation error raises error."""
        # Create an invalid template file
        data = {
            "name": "Invalid Name",  # Invalid: contains uppercase/spaces
            "description": "x",  # Invalid: too short
            "category": "testing",
        }
        file_path = temp_dir / "invalid.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        with pytest.raises(ValueError) as exc_info:
            library.import_template_file(file_path)

        assert "validation failed" in str(exc_info.value).lower()


# =============================================================================
# Test CustomTemplate
# =============================================================================


class TestCustomTemplate:
    """Tests for CustomTemplate class."""

    def test_custom_template_initialization(self):
        """CustomTemplate initializes correctly."""
        template = CustomTemplate(
            name="custom",
            description="Custom template",
            category="ui",
            parameters={"param": {"type": str}},
            placeholders=["PLACEHOLDER"],
            template_content={"title": "Content"},
        )

        assert template.name == "custom"
        assert template.description == "Custom template"
        assert template.category == "ui"
        assert template.template_content == {"title": "Content"}

    def test_custom_template_generate(self):
        """CustomTemplate.generate() returns template content."""
        template = CustomTemplate(
            name="custom",
            description="Custom template",
            category="ui",
            parameters={},
            template_content={"title": "Test", "description": "Content"},
        )

        result = template.generate({})

        assert result["title"] == "Test"
        assert result["description"] == "Content"

    def test_custom_template_default_content(self):
        """CustomTemplate with no content defaults to empty dict."""
        template = CustomTemplate(
            name="custom",
            description="Custom template",
            category="ui",
            parameters={},
        )

        assert template.template_content == {}


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_export_template_with_none_placeholders(self):
        """Export template with None placeholders."""
        template = MockTemplate(
            name="no_placeholders",
            description="Template without placeholders",
            category="testing",
            placeholders=None,
        )

        data = export_template(template)
        # Should default to empty list
        assert data["placeholders"] == []

    def test_export_template_with_empty_parameters(self):
        """Export template with empty parameters dict."""
        template = MockTemplate(
            name="no_params",
            description="Template without parameters",
            category="testing",
            parameters={},
        )

        data = export_template(template)
        assert data["parameters"] == {}

    def test_import_template_with_extra_fields(self):
        """Import ignores extra fields (forward compatibility)."""
        data = {
            "name": "with_extras",
            "description": "Template with extra fields",
            "category": "testing",
            "_future_field": "future_value",
        }

        # Should import successfully, ignoring unknown fields
        template = import_template(data)
        assert template.name == "with_extras"

    def test_round_trip_with_unicode(self):
        """Round-trip preserves unicode characters."""
        template = MockTemplate(
            name="unicode_template",
            description="Template with unicode: José García ñ é ü",
            category="testing",
        )

        exported = export_template(template)
        imported = import_template(exported)

        assert imported.description == template.description

    def test_round_trip_with_special_characters(self):
        """Round-trip preserves special characters."""
        template = MockTemplate(
            name="special_chars",
            description="Template with special chars: & < > \" '",
            category="testing",
        )

        exported = export_template(template)
        imported = import_template(exported)

        assert imported.description == template.description

    def test_export_import_very_long_description(self):
        """Export/import handles very long descriptions."""
        long_description = "A" * 10000
        template = MockTemplate(
            name="long_desc",
            description=long_description,
            category="testing",
        )

        exported = export_template(template)
        imported = import_template(exported)

        assert imported.description == long_description

    def test_export_import_many_placeholders(self):
        """Export/import handles many placeholders."""
        many_placeholders = [f"PLACEHOLDER_{i}" for i in range(100)]
        template = MockTemplate(
            name="many_placeholders",
            description="Template with many placeholders",
            category="testing",
            placeholders=many_placeholders,
        )

        exported = export_template(template)
        imported = import_template(exported)

        assert imported.placeholders == many_placeholders

    def test_export_import_complex_parameter_defaults(self):
        """Export/import handles complex default values."""
        template = MockTemplate(
            name="complex_defaults",
            description="Template with complex defaults",
            category="testing",
            parameters={
                "list_param": {"type": list, "default": [1, 2, {"nested": "value"}]},
                "dict_param": {
                    "type": dict,
                    "default": {"key1": "value1", "key2": ["list", "items"]},
                },
            },
        )

        exported = export_template(template)
        imported = import_template(exported)

        assert imported.parameters["list_param"]["default"] == [
            1,
            2,
            {"nested": "value"},
        ]
        assert imported.parameters["dict_param"]["default"] == {
            "key1": "value1",
            "key2": ["list", "items"],
        }
