"""
Unit tests for Template Library
================================

Tests for TemplateLibrary operations including search, filter, and template management.
"""

import pytest
from pathlib import Path
from apps.backend.spec.templates.library import TemplateLibrary, suggest_templates
from apps.backend.spec.templates.registry import Template


class MockTemplate(Template):
    """Mock template for testing."""

    def generate(self, params):
        """Mock generate method."""
        return {
            "title": f"Test {params.get('name', 'Unknown')}",
            "description": "Test description",
            "acceptance_criteria": ["Test criterion"],
        }


class TestTemplateLibrary:
    """Tests for TemplateLibrary class."""

    @pytest.fixture
    def temp_templates_dir(self, tmp_path):
        """Create a temporary directory for custom templates."""
        templates_dir = tmp_path / "custom_templates"
        templates_dir.mkdir()
        return templates_dir

    def test_initialization_with_builtin_templates(self):
        """Test TemplateLibrary initializes with builtin templates."""
        library = TemplateLibrary()

        templates = library.list_templates()
        # Should have 25+ builtin templates
        assert len(templates) >= 25

    def test_initialization_with_custom_dir(self, temp_templates_dir):
        """Test TemplateLibrary can be initialized with custom templates directory."""
        library = TemplateLibrary(custom_templates_dir=temp_templates_dir)

        assert library.custom_templates_dir == temp_templates_dir

    def test_get_template_by_name(self):
        """Test retrieving a template by name."""
        library = TemplateLibrary()

        template = library.get_template("crud_api")
        assert template is not None
        assert template.name == "crud_api"

    def test_get_template_not_found(self):
        """Test get_template returns None for non-existent template."""
        library = TemplateLibrary()

        template = library.get_template("nonexistent_template")
        assert template is None

    def test_list_all_templates(self):
        """Test listing all templates."""
        library = TemplateLibrary()

        templates = library.list_templates()
        assert len(templates) > 0
        assert isinstance(templates, list)
        assert all(isinstance(t, dict) for t in templates)

    def test_list_templates_info_structure(self):
        """Test template info dictionaries have correct structure."""
        library = TemplateLibrary()

        templates = library.list_templates()
        template = templates[0]

        # Check required fields
        assert "name" in template
        assert "description" in template
        assert "category" in template
        assert "parameters" in template

    def test_list_templates_by_category(self):
        """Test filtering templates by category."""
        library = TemplateLibrary()

        # Get all API templates
        api_templates = library.list_templates(category="api")
        assert len(api_templates) > 0
        assert all(t["category"] == "api" for t in api_templates)

        # Get all UI templates
        ui_templates = library.list_templates(category="ui")
        assert len(ui_templates) > 0
        assert all(t["category"] == "ui" for t in ui_templates)

    def test_get_categories(self):
        """Test getting all available categories."""
        library = TemplateLibrary()

        categories = library.get_categories()
        assert len(categories) > 0
        assert "api" in categories
        assert "ui" in categories
        assert "database" in categories

    def test_search_templates_by_name(self):
        """Test searching templates by name."""
        library = TemplateLibrary()

        # Search for CRUD API
        results = library.search_templates("crud")
        assert len(results) > 0
        assert any("crud" in t["name"].lower() for t in results)

    def test_search_templates_by_description(self):
        """Test searching templates by description."""
        library = TemplateLibrary()

        # Search for authentication
        results = library.search_templates("authentication")
        assert len(results) > 0

    def test_search_templates_case_insensitive(self):
        """Test search is case-insensitive."""
        library = TemplateLibrary()

        results_lower = library.search_templates("api")
        results_upper = library.search_templates("API")
        results_mixed = library.search_templates("Api")

        # All should return same results
        assert len(results_lower) == len(results_upper) == len(results_mixed)

    def test_search_templates_no_matches(self):
        """Test search with no matches returns empty list."""
        library = TemplateLibrary()

        results = library.search_templates("xyznonexistent123")
        assert len(results) == 0

    def test_preview_template_valid(self):
        """Test previewing a template generates markdown."""
        library = TemplateLibrary()

        preview = library.preview_template(
            "crud_api",
            {
                "resource_name": "User",
                "resource_name_plural": "Users",
                "fields": ["name", "email"],
            },
        )

        assert preview is not None
        assert isinstance(preview, str)
        assert "User CRUD API" in preview
        assert "# User CRUD API" in preview

    def test_preview_template_not_found(self):
        """Test preview returns None for non-existent template."""
        library = TemplateLibrary()

        preview = library.preview_template("nonexistent_template", {})
        assert preview is None

    def test_create_spec_from_template_valid(self, tmp_path):
        """Test creating a spec from a template."""
        library = TemplateLibrary()
        spec_dir = tmp_path / "test_spec"

        result = library.create_spec_from_template(
            "crud_api",
            {
                "resource_name": "Product",
                "resource_name_plural": "Products",
                "fields": ["name", "price", "description"],
            },
            spec_dir,
        )

        # Check result structure
        assert "title" in result
        assert "description" in result
        assert "acceptance_criteria" in result
        assert "metadata" in result

        # Check files were created
        assert (spec_dir / "spec.md").exists()
        assert (spec_dir / "template_metadata.json").exists()

    def test_create_spec_from_template_not_found(self, tmp_path):
        """Test creating spec from non-existent template raises error."""
        library = TemplateLibrary()
        spec_dir = tmp_path / "test_spec"

        with pytest.raises(ValueError, match="Template not found"):
            library.create_spec_from_template("nonexistent_template", {}, spec_dir)

    def test_create_spec_from_template_invalid_params(self, tmp_path):
        """Test creating spec with invalid params raises error."""
        library = TemplateLibrary()
        spec_dir = tmp_path / "test_spec"

        # Missing required parameters
        with pytest.raises(ValueError, match="Invalid parameters"):
            library.create_spec_from_template(
                "crud_api",
                {},  # Missing required params
                spec_dir,
            )


class TestSuggestTemplates:
    """Tests for template suggestion functionality."""

    def test_suggest_templates_with_task_description(self, tmp_path):
        """Test suggesting templates based on task description."""
        # Create a minimal project directory
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        suggestions = suggest_templates(
            project_dir,
            task_description="Create a REST API for user management",
            use_project_analysis=False,
        )

        assert len(suggestions) > 0
        assert all(isinstance(s, dict) for s in suggestions)
        assert all("name" in s and "reason" in s and "relevance" in s for s in suggestions)

        # Should suggest crud_api for API-related task
        template_names = [s["name"] for s in suggestions]
        assert "crud_api" in template_names

    def test_suggest_templates_api_keywords(self, tmp_path):
        """Test template suggestions for API-related keywords."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        suggestions = suggest_templates(
            project_dir,
            task_description="Build REST API endpoints",
            use_project_analysis=False,
        )

        template_names = [s["name"] for s in suggestions]
        assert "crud_api" in template_names or "api_integration" in template_names

    def test_suggest_templates_auth_keywords(self, tmp_path):
        """Test template suggestions for authentication keywords."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        suggestions = suggest_templates(
            project_dir,
            task_description="Add user login and JWT authentication",
            use_project_analysis=False,
        )

        template_names = [s["name"] for s in suggestions]
        assert "authentication" in template_names

    def test_suggest_templates_database_keywords(self, tmp_path):
        """Test template suggestions for database keywords."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        suggestions = suggest_templates(
            project_dir,
            task_description="Create database migration for new table",
            use_project_analysis=False,
        )

        template_names = [s["name"] for s in suggestions]
        assert "database_migration" in template_names

    def test_suggest_templates_ui_keywords(self, tmp_path):
        """Test template suggestions for UI keywords."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        suggestions = suggest_templates(
            project_dir,
            task_description="Build React component for user profile",
            use_project_analysis=False,
        )

        template_names = [s["name"] for s in suggestions]
        assert "ui_component" in template_names

    def test_suggest_templates_sorted_by_relevance(self, tmp_path):
        """Test suggestions are sorted by relevance score."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        suggestions = suggest_templates(
            project_dir,
            task_description="Create CRUD API with authentication",
            use_project_analysis=False,
        )

        # Check that relevance scores are in descending order
        relevance_scores = [s["relevance"] for s in suggestions]
        assert relevance_scores == sorted(relevance_scores, reverse=True)

    def test_suggest_templates_max_10_results(self, tmp_path):
        """Test suggestions are limited to top 10 results."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        suggestions = suggest_templates(
            project_dir,
            task_description="Create API authentication database migration UI component",
            use_project_analysis=False,
        )

        # Should return at most 10 suggestions
        assert len(suggestions) <= 10

    def test_suggest_templates_empty_description(self, tmp_path):
        """Test suggesting templates with no task description."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        suggestions = suggest_templates(
            project_dir,
            task_description="",
            use_project_analysis=False,
        )

        # Should still return suggestions (empty list or project-based suggestions)
        assert isinstance(suggestions, list)
