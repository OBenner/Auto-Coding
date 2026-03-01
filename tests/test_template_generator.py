"""
Unit tests for Spec Generator
==============================

Tests for SpecGenerator class including spec generation, preview, and validation.
"""

import pytest
import json
from datetime import datetime
from apps.backend.spec.templates.generator import SpecGenerator
from apps.backend.spec.templates.registry import Template


class MockTemplate(Template):
    """Mock template for testing."""

    def generate(self, params):
        """Mock generate method."""
        name = params.get("name", "Unknown")
        return {
            "title": f"Test {name}",
            "description": f"A test spec for {name}",
            "rationale": f"This is needed for {name} functionality",
            "user_stories": [
                f"As a user, I want to use {name}",
                f"As a developer, I want to implement {name}",
            ],
            "acceptance_criteria": [
                f"{name} is implemented",
                f"{name} has tests",
                f"{name} is documented",
            ],
            "technical_details": f"Implementation details for {name}",
            "test_coverage": [
                f"Unit tests for {name}",
                f"Integration tests for {name}",
            ],
        }


class TestSpecGenerator:
    """Tests for SpecGenerator class."""

    @pytest.fixture
    def mock_template(self):
        """Create a mock template for testing."""
        return MockTemplate(
            name="test_template",
            description="Test template",
            category="test",
            parameters={
                "name": {"type": str, "required": True},
                "optional_field": {"type": str, "required": False},
            },
        )

    @pytest.fixture
    def generator(self, mock_template):
        """Create a SpecGenerator instance."""
        return SpecGenerator(mock_template)

    def test_initialization(self, mock_template):
        """Test SpecGenerator can be initialized with a template."""
        generator = SpecGenerator(mock_template)

        assert generator.template == mock_template

    def test_generate_spec_valid_params(self, generator, tmp_path):
        """Test generating a spec with valid parameters."""
        params = {"name": "UserAuth"}
        spec_dir = tmp_path / "test_spec"

        result = generator.generate_spec(params, spec_dir)

        # Check result structure
        assert "title" in result
        assert "description" in result
        assert "acceptance_criteria" in result
        assert "metadata" in result

        # Check content
        assert result["title"] == "Test UserAuth"
        assert "UserAuth" in result["description"]
        assert len(result["acceptance_criteria"]) == 3

    def test_generate_spec_with_metadata(self, generator, tmp_path):
        """Test generated spec includes metadata."""
        params = {"name": "Feature"}
        spec_dir = tmp_path / "test_spec"

        result = generator.generate_spec(params, spec_dir)

        # Check metadata
        assert "metadata" in result
        metadata = result["metadata"]
        assert metadata["template"] == "test_template"
        assert metadata["template_category"] == "test"
        assert "generated_at" in metadata
        assert metadata["parameters"] == params

        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(metadata["generated_at"])
        except ValueError:
            pytest.fail("generated_at is not a valid ISO timestamp")

    def test_generate_spec_saves_files(self, generator, tmp_path):
        """Test spec generation saves files to disk."""
        params = {"name": "Feature"}
        spec_dir = tmp_path / "test_spec"

        generator.generate_spec(params, spec_dir)

        # Check files were created
        assert spec_dir.exists()
        assert (spec_dir / "spec.md").exists()
        assert (spec_dir / "template_metadata.json").exists()

    def test_generate_spec_creates_directory(self, generator, tmp_path):
        """Test spec generation creates directory if it doesn't exist."""
        params = {"name": "Feature"}
        spec_dir = tmp_path / "nested" / "test_spec"

        assert not spec_dir.exists()

        generator.generate_spec(params, spec_dir)

        assert spec_dir.exists()

    def test_generate_spec_invalid_params(self, generator):
        """Test generating spec with invalid params raises error."""
        # Missing required parameter 'name'
        params = {}

        with pytest.raises(ValueError, match="Invalid parameters"):
            generator.generate_spec(params)

    def test_generate_spec_without_saving(self, generator):
        """Test generating spec without saving to disk."""
        params = {"name": "Feature"}

        result = generator.generate_spec(params, spec_dir=None)

        # Should have result but no files saved
        assert "title" in result
        assert "metadata" in result

    def test_preview_spec(self, generator):
        """Test previewing a spec without saving."""
        params = {"name": "UserAuth"}

        preview = generator.preview_spec(params)

        # Should return markdown string
        assert isinstance(preview, str)
        assert "# Test UserAuth" in preview
        assert "UserAuth" in preview

    def test_preview_spec_has_all_sections(self, generator):
        """Test preview includes all spec sections."""
        params = {"name": "Feature"}

        preview = generator.preview_spec(params)

        # Check for all major sections
        assert "# Test Feature" in preview
        assert "## Rationale" in preview
        assert "## User Stories" in preview
        assert "## Acceptance Criteria" in preview
        assert "## Technical Details" in preview
        assert "## Test Coverage Requirements" in preview

    def test_format_spec_markdown_title(self, generator):
        """Test markdown formatting includes title."""
        spec_content = {
            "title": "Test Feature",
            "description": "A test feature",
            "acceptance_criteria": ["Criterion 1"],
        }

        markdown = generator._format_spec_markdown(spec_content)

        assert "# Test Feature" in markdown

    def test_format_spec_markdown_user_stories(self, generator):
        """Test markdown formatting for user stories."""
        spec_content = {
            "title": "Test",
            "user_stories": ["Story 1", "Story 2", "Story 3"],
            "acceptance_criteria": ["Criterion 1"],
        }

        markdown = generator._format_spec_markdown(spec_content)

        assert "## User Stories" in markdown
        assert "- Story 1" in markdown
        assert "- Story 2" in markdown
        assert "- Story 3" in markdown

    def test_format_spec_markdown_acceptance_criteria(self, generator):
        """Test markdown formatting for acceptance criteria."""
        spec_content = {
            "title": "Test",
            "acceptance_criteria": ["Criterion 1", "Criterion 2"],
        }

        markdown = generator._format_spec_markdown(spec_content)

        assert "## Acceptance Criteria" in markdown
        assert "- [ ] Criterion 1" in markdown
        assert "- [ ] Criterion 2" in markdown

    def test_format_spec_markdown_test_coverage(self, generator):
        """Test markdown formatting for test coverage."""
        spec_content = {
            "title": "Test",
            "test_coverage": ["Unit tests", "Integration tests", "E2E tests"],
            "acceptance_criteria": ["Criterion 1"],
        }

        markdown = generator._format_spec_markdown(spec_content)

        assert "## Test Coverage Requirements" in markdown
        assert "- Unit tests" in markdown
        assert "- Integration tests" in markdown
        assert "- E2E tests" in markdown

    def test_validate_generated_spec_valid(self, generator):
        """Test validating a valid spec."""
        spec_content = {
            "title": "Test Feature",
            "description": "A test feature",
            "acceptance_criteria": ["Criterion 1", "Criterion 2"],
        }

        errors = generator.validate_generated_spec(spec_content)

        assert len(errors) == 0

    def test_validate_generated_spec_missing_title(self, generator):
        """Test validation catches missing title."""
        spec_content = {
            "description": "A test feature",
            "acceptance_criteria": ["Criterion 1"],
        }

        errors = generator.validate_generated_spec(spec_content)

        assert len(errors) == 1
        assert "title" in errors[0].lower()

    def test_validate_generated_spec_missing_description(self, generator):
        """Test validation catches missing description."""
        spec_content = {
            "title": "Test Feature",
            "acceptance_criteria": ["Criterion 1"],
        }

        errors = generator.validate_generated_spec(spec_content)

        assert len(errors) == 1
        assert "description" in errors[0].lower()

    def test_validate_generated_spec_missing_acceptance_criteria(self, generator):
        """Test validation catches missing acceptance criteria."""
        spec_content = {
            "title": "Test Feature",
            "description": "A test feature",
        }

        errors = generator.validate_generated_spec(spec_content)

        assert len(errors) == 1
        assert "acceptance_criteria" in errors[0].lower()

    def test_validate_generated_spec_empty_acceptance_criteria(self, generator):
        """Test validation catches empty acceptance criteria."""
        spec_content = {
            "title": "Test Feature",
            "description": "A test feature",
            "acceptance_criteria": [],
        }

        errors = generator.validate_generated_spec(spec_content)

        # Empty list triggers both "missing/falsy" and "cannot be empty" checks
        assert len(errors) == 2
        assert any("acceptance_criteria" in e.lower() for e in errors)

    def test_validate_generated_spec_invalid_acceptance_criteria_type(self, generator):
        """Test validation catches invalid acceptance criteria type."""
        spec_content = {
            "title": "Test Feature",
            "description": "A test feature",
            "acceptance_criteria": "Not a list",
        }

        errors = generator.validate_generated_spec(spec_content)

        assert len(errors) == 1
        assert "acceptance_criteria" in errors[0].lower()
        assert "list" in errors[0].lower()

    def test_saved_metadata_file_format(self, generator, tmp_path):
        """Test metadata file is saved in correct JSON format."""
        params = {"name": "Feature"}
        spec_dir = tmp_path / "test_spec"

        generator.generate_spec(params, spec_dir)

        metadata_file = spec_dir / "template_metadata.json"
        with open(metadata_file, encoding="utf-8") as f:
            metadata = json.load(f)

        # Verify structure
        assert "template" in metadata
        assert "template_category" in metadata
        assert "generated_at" in metadata
        assert "parameters" in metadata
        assert metadata["parameters"] == params

    def test_saved_spec_file_readable(self, generator, tmp_path):
        """Test spec.md file is saved and readable."""
        params = {"name": "Feature"}
        spec_dir = tmp_path / "test_spec"

        generator.generate_spec(params, spec_dir)

        spec_file = spec_dir / "spec.md"
        with open(spec_file, encoding="utf-8") as f:
            content = f.read()

        # Verify content
        assert "# Test Feature" in content
        assert "## Rationale" in content
        assert "## Acceptance Criteria" in content
