"""
Unit tests for Template Registry
=================================

Tests for Template base class and TemplateRegistry singleton.
"""

import pytest
from apps.backend.spec.templates.registry import Template, TemplateRegistry


class MockTemplate(Template):
    """Mock template for testing."""

    def generate(self, params):
        """Mock generate method."""
        return {
            "title": f"Test {params.get('name', 'Unknown')}",
            "description": "Test description",
            "acceptance_criteria": ["Test criterion"],
        }


class TestTemplateBase:
    """Tests for the Template base class."""

    def test_template_instantiation(self):
        """Test Template can be instantiated with required fields."""
        template = MockTemplate(
            name="test_template",
            description="A test template",
            category="test",
            parameters={
                "name": {"type": str, "required": True},
                "count": {"type": int, "required": False, "default": 10},
            },
        )

        assert template.name == "test_template"
        assert template.description == "A test template"
        assert template.category == "test"
        assert len(template.parameters) == 2

    def test_validate_params_required_fields(self):
        """Test parameter validation catches missing required fields."""
        template = MockTemplate(
            name="test_template",
            description="Test",
            category="test",
            parameters={
                "required_field": {"type": str, "required": True},
                "optional_field": {"type": str, "required": False},
            },
        )

        # Missing required field
        errors = template.validate_params({})
        assert len(errors) == 1
        assert "required_field" in errors[0]

        # With required field
        errors = template.validate_params({"required_field": "value"})
        assert len(errors) == 0

    def test_validate_params_type_checking(self):
        """Test parameter validation checks types."""
        template = MockTemplate(
            name="test_template",
            description="Test",
            category="test",
            parameters={
                "name": {"type": str, "required": True},
                "count": {"type": int, "required": False},
            },
        )

        # Correct types
        errors = template.validate_params({"name": "test", "count": 5})
        assert len(errors) == 0

        # Wrong type for count
        errors = template.validate_params({"name": "test", "count": "five"})
        assert len(errors) == 1
        assert "count" in errors[0]

    def test_validate_params_optional_fields(self):
        """Test optional parameters don't cause validation errors."""
        template = MockTemplate(
            name="test_template",
            description="Test",
            category="test",
            parameters={
                "required_field": {"type": str, "required": True},
                "optional_field": {"type": str, "required": False},
            },
        )

        # Only required field provided
        errors = template.validate_params({"required_field": "value"})
        assert len(errors) == 0

    def test_generate_method_abstract(self):
        """Test that Template.generate is abstract and must be implemented."""
        # MockTemplate implements generate, so it can be instantiated
        template = MockTemplate(
            name="test", description="Test", category="test", parameters={}
        )
        assert callable(template.generate)

        # Calling generate on a properly implemented template should work
        result = template.generate({"name": "TestName"})
        assert "title" in result
        assert result["title"] == "Test TestName"


class TestTemplateRegistry:
    """Tests for the TemplateRegistry singleton."""

    @pytest.fixture(autouse=True)
    def clear_registry(self):
        """Clear the registry before each test."""
        registry = TemplateRegistry()
        registry.clear()
        yield
        registry.clear()

    def test_singleton_pattern(self):
        """Test TemplateRegistry follows singleton pattern."""
        registry1 = TemplateRegistry()
        registry2 = TemplateRegistry()

        assert registry1 is registry2
        assert id(registry1) == id(registry2)

    def test_register_template(self):
        """Test registering a template."""
        registry = TemplateRegistry()
        template = MockTemplate(
            name="test_template",
            description="Test",
            category="test",
            parameters={},
        )

        registry.register(template)

        retrieved = registry.get("test_template")
        assert retrieved is not None
        assert retrieved.name == "test_template"

    def test_get_template_not_found(self):
        """Test getting a non-existent template returns None."""
        registry = TemplateRegistry()

        result = registry.get("nonexistent_template")
        assert result is None

    def test_list_all_templates(self):
        """Test listing all registered templates."""
        registry = TemplateRegistry()

        template1 = MockTemplate(
            name="template1", description="Test 1", category="test", parameters={}
        )
        template2 = MockTemplate(
            name="template2", description="Test 2", category="other", parameters={}
        )

        registry.register(template1)
        registry.register(template2)

        all_templates = registry.list_all()
        assert len(all_templates) == 2
        assert any(t.name == "template1" for t in all_templates)
        assert any(t.name == "template2" for t in all_templates)

    def test_list_by_category(self):
        """Test listing templates by category."""
        registry = TemplateRegistry()

        template1 = MockTemplate(
            name="template1", description="Test 1", category="api", parameters={}
        )
        template2 = MockTemplate(
            name="template2", description="Test 2", category="api", parameters={}
        )
        template3 = MockTemplate(
            name="template3", description="Test 3", category="ui", parameters={}
        )

        registry.register(template1)
        registry.register(template2)
        registry.register(template3)

        api_templates = registry.list_by_category("api")
        assert len(api_templates) == 2
        assert all(t.category == "api" for t in api_templates)

        ui_templates = registry.list_by_category("ui")
        assert len(ui_templates) == 1
        assert ui_templates[0].category == "ui"

    def test_get_categories(self):
        """Test getting all unique categories."""
        registry = TemplateRegistry()

        template1 = MockTemplate(
            name="template1", description="Test 1", category="api", parameters={}
        )
        template2 = MockTemplate(
            name="template2", description="Test 2", category="ui", parameters={}
        )
        template3 = MockTemplate(
            name="template3", description="Test 3", category="api", parameters={}
        )

        registry.register(template1)
        registry.register(template2)
        registry.register(template3)

        categories = registry.get_categories()
        assert len(categories) == 2
        assert "api" in categories
        assert "ui" in categories

    def test_clear_registry(self):
        """Test clearing the registry."""
        registry = TemplateRegistry()

        template = MockTemplate(
            name="test_template", description="Test", category="test", parameters={}
        )
        registry.register(template)
        assert len(registry.list_all()) == 1

        registry.clear()
        assert len(registry.list_all()) == 0

    def test_overwrite_existing_template(self):
        """Test that registering a template with same name overwrites."""
        registry = TemplateRegistry()

        template1 = MockTemplate(
            name="test_template",
            description="First description",
            category="test",
            parameters={},
        )
        template2 = MockTemplate(
            name="test_template",
            description="Second description",
            category="test",
            parameters={},
        )

        registry.register(template1)
        registry.register(template2)

        retrieved = registry.get("test_template")
        assert retrieved.description == "Second description"

        # Should only have one template
        assert len(registry.list_all()) == 1
