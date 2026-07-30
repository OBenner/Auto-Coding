"""
Spec Generator
==============

Generates specification documents from templates and parameters.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .placeholders import PlaceholderParser
from .registry import Template


class SpecGenerator:
    """Generates spec documents from templates."""

    def __init__(self, template: Template):
        """
        Initialize the spec generator.

        Args:
            template: Template to use for generation
        """
        self.template = template
        self.placeholder_parser = PlaceholderParser()

    def generate_spec(
        self, params: dict[str, Any], spec_dir: Path | None = None
    ) -> dict[str, Any]:
        """
        Generate a complete spec document from template parameters.

        Args:
            params: User-provided parameter values
            spec_dir: Optional directory to save the spec to

        Returns:
            Dictionary containing the generated spec content
        """
        # Validate parameters
        validation_errors = self.template.validate_params(params)
        if validation_errors:
            raise ValueError(f"Invalid parameters: {', '.join(validation_errors)}")

        # Generate spec content from template
        spec_content = self.template.generate(params)

        # Replace placeholders in spec content
        spec_content = self._replace_placeholders_in_content(spec_content, params)

        # Add metadata
        spec_content["metadata"] = {
            "template": self.template.name,
            "template_category": self.template.category,
            "generated_at": datetime.now().isoformat(),
            "parameters": params,
        }

        # Save to disk if spec_dir provided
        if spec_dir:
            self._save_spec(spec_content, spec_dir)

        return spec_content

    def preview_spec(self, params: dict[str, Any]) -> str:
        """
        Generate a preview of the spec document without saving.

        Args:
            params: User-provided parameter values

        Returns:
            Markdown-formatted preview of the spec
        """
        spec_content = self.generate_spec(params)
        return self._format_spec_markdown(spec_content)

    def _save_spec(self, spec_content: dict[str, Any], spec_dir: Path) -> None:
        """
        Save generated spec to disk.

        Args:
            spec_content: Generated spec content
            spec_dir: Directory to save the spec to
        """
        spec_dir.mkdir(parents=True, exist_ok=True)

        # Save spec.md
        spec_md = self._format_spec_markdown(spec_content)
        spec_file = spec_dir / "spec.md"
        with open(spec_file, "w", encoding="utf-8") as f:
            f.write(spec_md)

        # Save metadata
        metadata_file = spec_dir / "template_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(spec_content.get("metadata", {}), f, indent=2)

    def _format_spec_markdown(self, spec_content: dict[str, Any]) -> str:
        """
        Format spec content as markdown.

        Args:
            spec_content: Generated spec content

        Returns:
            Markdown-formatted spec document
        """
        lines = []

        # Title
        title = spec_content.get("title", "Generated Spec")
        lines.append(f"# {title}\n")

        # Description
        if "description" in spec_content:
            lines.append(f"{spec_content['description']}\n")

        # Rationale
        if "rationale" in spec_content:
            lines.append("## Rationale\n")
            lines.append(f"{spec_content['rationale']}\n")

        # User Stories
        if "user_stories" in spec_content:
            lines.append("## User Stories\n")
            for story in spec_content["user_stories"]:
                lines.append(f"- {story}")
            lines.append("")

        # Acceptance Criteria
        if "acceptance_criteria" in spec_content:
            lines.append("## Acceptance Criteria\n")
            for criterion in spec_content["acceptance_criteria"]:
                lines.append(f"- [ ] {criterion}")
            lines.append("")

        # Technical Details
        if "technical_details" in spec_content:
            lines.append("## Technical Details\n")
            lines.append(f"{spec_content['technical_details']}\n")

        # Test Coverage Requirements
        if "test_coverage" in spec_content:
            lines.append("## Test Coverage Requirements\n")
            for requirement in spec_content["test_coverage"]:
                lines.append(f"- {requirement}")
            lines.append("")

        return "\n".join(lines)

    def validate_generated_spec(self, spec_content: dict[str, Any]) -> list[str]:
        """
        Validate that generated spec contains required sections.

        Args:
            spec_content: Generated spec content

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        required_fields = ["title", "description", "acceptance_criteria"]

        for field in required_fields:
            if field not in spec_content or not spec_content[field]:
                errors.append(f"Missing required field: {field}")

        # Validate acceptance criteria is a non-empty list
        if "acceptance_criteria" in spec_content:
            if not isinstance(spec_content["acceptance_criteria"], list):
                errors.append("acceptance_criteria must be a list")
            elif len(spec_content["acceptance_criteria"]) == 0:
                errors.append("acceptance_criteria cannot be empty")

        return errors

    def _replace_placeholders_in_content(
        self, content: Any, values: dict[str, Any]
    ) -> Any:
        """
        Recursively replace placeholders in spec content.

        Args:
            content: Content to process (can be dict, list, str, or other)
            values: Dictionary of placeholder values

        Returns:
            Content with placeholders replaced
        """
        if isinstance(content, str):
            # Replace placeholders in string
            try:
                return self.placeholder_parser.replace(content, values)
            except ValueError:
                # If placeholder replacement fails, return original string
                # This allows templates to have optional placeholders
                return content
        elif isinstance(content, dict):
            # Recursively process dictionary values
            return {
                key: self._replace_placeholders_in_content(value, values)
                for key, value in content.items()
            }
        elif isinstance(content, list):
            # Recursively process list items
            return [
                self._replace_placeholders_in_content(item, values) for item in content
            ]
        else:
            # Return other types unchanged
            return content
