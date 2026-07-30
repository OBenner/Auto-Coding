"""
Template Library
================

Template library manager for browsing, searching, and managing templates.
"""

import json
import logging
from pathlib import Path
from typing import Any

from .generator import SpecGenerator
from .io import (
    export_template as io_export_template,
    export_template_to_file,
    import_template as io_import_template,
    import_template_from_file,
)
from .registry import Template, TemplateRegistry
from .validator import validate_template

logger = logging.getLogger(__name__)


class TemplateLibrary:
    """Manages the template library and provides search/filter capabilities."""

    def __init__(self, custom_templates_dir: Path | None = None):
        """
        Initialize the template library.

        Args:
            custom_templates_dir: Optional directory for custom user templates
        """
        self.registry = TemplateRegistry()
        self.custom_templates_dir = custom_templates_dir

        # Register built-in templates
        from .builtin import register_builtin_templates

        register_builtin_templates(self.registry)

        # Load custom templates if directory provided
        if custom_templates_dir:
            self._load_custom_templates()

    def get_template(self, name: str) -> Template | None:
        """
        Get a template by name.

        Args:
            name: Template name

        Returns:
            Template instance or None if not found
        """
        return self.registry.get(name)

    def list_templates(
        self, category: str | None = None, tags: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        List available templates with optional filtering.

        Args:
            category: Optional category filter
            tags: Optional tag filters

        Returns:
            List of template info dictionaries
        """
        if category:
            templates = self.registry.list_by_category(category)
        else:
            templates = self.registry.list_all()

        # Convert to info dictionaries
        template_info = []
        for template in templates:
            info = {
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "parameters": template.parameters,
            }
            template_info.append(info)

        # Filter by tags if provided
        if tags:
            template_info = [
                t
                for t in template_info
                if any(
                    tag in t.get("tags", []) for tag in tags
                )  # Templates can optionally have tags
            ]

        return template_info

    def get_categories(self) -> list[str]:
        """
        Get all available template categories.

        Returns:
            List of category names
        """
        return self.registry.get_categories()

    def search_templates(self, query: str) -> list[dict[str, Any]]:
        """
        Search templates by name or description.

        Args:
            query: Search query string

        Returns:
            List of matching template info dictionaries
        """
        all_templates = self.list_templates()
        query_lower = query.lower()

        matches = []
        for template in all_templates:
            if (
                query_lower in template["name"].lower()
                or query_lower in template["description"].lower()
            ):
                matches.append(template)

        return matches

    def create_spec_from_template(
        self, template_name: str, params: dict[str, Any], spec_dir: Path
    ) -> dict[str, Any]:
        """
        Create a spec from a template.

        Validates the template before generation to ensure security and correctness.

        Args:
            template_name: Name of the template to use
            params: Template parameters
            spec_dir: Directory to save the spec to

        Returns:
            Generated spec content

        Raises:
            ValueError: If template not found, validation fails, or parameters invalid
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        # Validate template before using it to generate specs
        is_valid, errors = self.validate(template, strict=True)
        if not is_valid:
            error_msg = f"Template '{template_name}' validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            logger.error("Failed to create spec from template '%s': %s", template_name, error_msg)
            raise ValueError(error_msg)

        generator = SpecGenerator(template)
        return generator.generate_spec(params, spec_dir)

    def preview_template(
        self, template_name: str, params: dict[str, Any]
    ) -> str | None:
        """
        Preview a spec without saving it.

        Args:
            template_name: Name of the template to preview
            params: Template parameters

        Returns:
            Markdown preview of the spec or None if template not found
        """
        template = self.get_template(template_name)
        if not template:
            return None

        generator = SpecGenerator(template)
        return generator.preview_spec(params)

    def export_template(self, template_name: str) -> dict[str, Any]:
        """
        Export a template to a JSON-compatible dictionary.

        Args:
            template_name: Name of the template to export

        Returns:
            Dictionary containing all template data

        Raises:
            ValueError: If template not found

        Example:
            >>> library = TemplateLibrary()
            >>> data = library.export_template("crud_api")
            >>> data["name"]
            'crud_api'
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        return io_export_template(template)

    def import_template_data(self, data: dict[str, Any]) -> Template:
        """
        Import a template from a JSON dictionary.

        Validates the template before adding it to the library.

        Args:
            data: Dictionary containing template data

        Returns:
            Imported Template instance

        Raises:
            ValueError: If template data is invalid or validation fails

        Example:
            >>> library = TemplateLibrary()
            >>> data = {
            ...     "name": "my-template",
            ...     "description": "My custom template",
            ...     "category": "api",
            ...     "parameters": {},
            ...     "placeholders": []
            ... }
            >>> template = library.import_template_data(data)
            >>> template.name
            'my-template'
        """
        # Import template using io module
        template = io_import_template(data)

        # Validate before adding to library
        is_valid, errors = self.validate(template, strict=True)
        if not is_valid:
            error_msg = f"Imported template '{template.name}' validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            logger.error("Failed to import template: %s", error_msg)
            raise ValueError(error_msg)

        # Add to registry
        self.registry.register(template)
        logger.info("Successfully imported template '%s'", template.name)

        return template

    def export_template_file(self, template_name: str, file_path: Path | str) -> None:
        """
        Export a template to a JSON file.

        Args:
            template_name: Name of the template to export
            file_path: Path to write the JSON file to

        Raises:
            ValueError: If template not found

        Example:
            >>> library = TemplateLibrary()
            >>> library.export_template_file("crud_api", "my-template.json")
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        export_template_to_file(template, str(file_path))
        logger.info("Exported template '%s' to %s", template_name, file_path)

    def import_template_file(self, file_path: Path | str) -> Template:
        """
        Import a template from a JSON file.

        Validates the template before adding it to the library.

        Args:
            file_path: Path to the JSON file to import

        Returns:
            Imported Template instance

        Raises:
            ValueError: If file is invalid, template data is malformed, or validation fails
            FileNotFoundError: If file doesn't exist

        Example:
            >>> library = TemplateLibrary()
            >>> template = library.import_template_file("my-template.json")
            >>> template.name
            'my-template'
        """
        # Import template from file using io module
        template = import_template_from_file(str(file_path))

        # Validate before adding to library
        is_valid, errors = self.validate(template, strict=True)
        if not is_valid:
            error_msg = f"Imported template '{template.name}' validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            logger.error("Failed to import template from %s: %s", file_path, error_msg)
            raise ValueError(error_msg)

        # Add to registry
        self.registry.register(template)
        logger.info("Successfully imported template '%s' from %s", template.name, file_path)

        return template

    def validate(self, template: Template, strict: bool = True) -> tuple[bool, list[str]]:
        """
        Validate a template for security and correctness.

        Performs comprehensive validation including:
        - Basic field validation (name, description, category)
        - Parameter validation (types, required fields)
        - Placeholder validation (proper format, no duplicates)
        - Content safety (no injection attacks)
        - Generated content validation

        Args:
            template: Template instance to validate
            strict: If True, fail on warnings. If False, allow warnings.

        Returns:
            Tuple of (is_valid, list_of_errors)
            - is_valid: True if template passes all checks
            - list_of_errors: List of error/warning messages (empty if valid)
        """
        return validate_template(template, strict=strict)

    def save_custom_template(self, template: Template) -> None:
        """
        Save a custom user-created template.

        Validates the template before saving to ensure it meets security
        and correctness requirements.

        Args:
            template: Template to save

        Raises:
            ValueError: If template validation fails
        """
        # Validate template before saving
        is_valid, errors = self.validate(template, strict=True)
        if not is_valid:
            error_msg = "Template validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            logger.error("Failed to save template '%s': %s", template.name, error_msg)
            raise ValueError(error_msg)

        self.registry.register(template)

        if self.custom_templates_dir:
            self.custom_templates_dir.mkdir(parents=True, exist_ok=True)
            template_file = self.custom_templates_dir / f"{template.name}.json"

            # Use io module for export
            export_template_to_file(template, str(template_file))

            logger.info("Successfully saved custom template '%s' to %s", template.name, template_file)

    def _load_custom_templates(self) -> None:
        """Load custom templates from disk."""
        if not self.custom_templates_dir or not self.custom_templates_dir.exists():
            return

        for template_file in self.custom_templates_dir.glob("*.json"):
            try:
                # Use io module to import template
                template = import_template_from_file(str(template_file))
                self.registry.register(template)
                logger.info("Loaded custom template '%s' from %s", template.name, template_file)
            except Exception as e:
                # Skip invalid template files
                logger.warning("Failed to load template from %s: %s", template_file, e)


def suggest_templates(
    project_dir: Path, task_description: str = "", use_project_analysis: bool = True
) -> list[dict[str, Any]]:
    """
    Suggest templates based on project analysis and task description.

    Args:
        project_dir: Project directory to analyze
        task_description: User's task description (optional)
        use_project_analysis: Whether to use project analysis (default: True)

    Returns:
        List of template suggestion dictionaries with name, reason, and relevance score
    """
    from analysis.analyzers import analyze_project

    suggestions = {}  # Use dict to track relevance scores

    # Analyze project if enabled
    project_analysis = None
    if use_project_analysis:
        try:
            project_analysis = analyze_project(project_dir, output_file=None)
        except Exception:
            # Fallback to keyword-based if analysis fails
            pass

    # Get suggestions from project analysis
    if project_analysis:
        services = project_analysis.get("services", {})

        for service_name, service_data in services.items():
            language = (service_data.get("language") or "").lower()
            framework = (service_data.get("framework") or "").lower()
            service_type = (service_data.get("type") or "").lower()
            databases = service_data.get("databases") or []
            has_auth = service_data.get("auth_patterns") or {}
            has_routes = service_data.get("routes") or []

            # Backend service suggestions
            if service_type == "backend":
                if has_routes:
                    _add_suggestion(
                        suggestions,
                        "crud_api",
                        f"Backend service with {len(has_routes)} routes detected",
                        0.8,
                    )
                if databases:
                    _add_suggestion(
                        suggestions,
                        "database_migration",
                        f"Uses {', '.join(databases)} database(s)",
                        0.7,
                    )
                if not has_auth:
                    _add_suggestion(
                        suggestions,
                        "authentication",
                        "Backend service without authentication",
                        0.6,
                    )
                _add_suggestion(
                    suggestions,
                    "logging_system",
                    f"Backend service ({framework or language})",
                    0.5,
                )

            # Frontend service suggestions
            if service_type == "frontend":
                _add_suggestion(
                    suggestions,
                    "ui_component",
                    f"Frontend service ({framework or language})",
                    0.8,
                )
                _add_suggestion(
                    suggestions,
                    "dashboard_widget",
                    "Frontend project detected",
                    0.6,
                )
                _add_suggestion(
                    suggestions, "settings_page", "Frontend project detected", 0.5
                )

            # Framework-specific suggestions
            if framework:
                if any(
                    fw in framework
                    for fw in ["fastapi", "flask", "django", "express", "nest"]
                ):
                    _add_suggestion(
                        suggestions,
                        "api_integration",
                        f"REST API framework ({framework})",
                        0.7,
                    )
                if any(fw in framework for fw in ["react", "vue", "angular", "svelte"]):
                    _add_suggestion(
                        suggestions,
                        "ui_component",
                        f"Component-based framework ({framework})",
                        0.8,
                    )

            # Database-specific suggestions
            if databases:
                _add_suggestion(
                    suggestions,
                    "export_data",
                    f"Project uses {', '.join(databases)}",
                    0.5,
                )
                _add_suggestion(
                    suggestions,
                    "import_data",
                    f"Project uses {', '.join(databases)}",
                    0.5,
                )

        # Infrastructure suggestions
        infrastructure = project_analysis.get("infrastructure", {})
        if infrastructure.get("docker"):
            _add_suggestion(
                suggestions,
                "ci_cd_pipeline",
                "Docker infrastructure detected",
                0.6,
            )
        if infrastructure.get("cicd"):
            _add_suggestion(
                suggestions,
                "monitoring_dashboard",
                "CI/CD pipeline detected",
                0.5,
            )

    # Analyze task description for keywords
    if task_description:
        task_lower = task_description.lower()

        # API-related keywords
        if any(
            keyword in task_lower
            for keyword in ["api", "endpoint", "rest", "graphql", "crud"]
        ):
            _add_suggestion(
                suggestions,
                "crud_api",
                "Task mentions API/endpoints",
                0.9,
            )

        # Authentication keywords
        if any(
            keyword in task_lower
            for keyword in ["auth", "login", "signup", "jwt", "oauth", "token"]
        ):
            _add_suggestion(
                suggestions,
                "authentication",
                "Task mentions authentication",
                0.9,
            )

        # Database keywords
        if any(
            keyword in task_lower
            for keyword in [
                "database",
                "migration",
                "schema",
                "table",
                "model",
                "sql",
            ]
        ):
            _add_suggestion(
                suggestions,
                "database_migration",
                "Task mentions database changes",
                0.9,
            )

        # UI keywords
        if any(
            keyword in task_lower
            for keyword in [
                "component",
                "ui",
                "frontend",
                "react",
                "vue",
                "button",
                "form",
                "page",
            ]
        ):
            _add_suggestion(
                suggestions,
                "ui_component",
                "Task mentions UI components",
                0.9,
            )

        # File handling keywords
        if any(
            keyword in task_lower
            for keyword in ["upload", "file", "image", "attachment", "document"]
        ):
            _add_suggestion(
                suggestions,
                "file_upload",
                "Task mentions file handling",
                0.9,
            )

        # Search keywords
        if any(
            keyword in task_lower
            for keyword in ["search", "filter", "find", "query", "elasticsearch"]
        ):
            _add_suggestion(
                suggestions,
                "search_feature",
                "Task mentions search functionality",
                0.9,
            )

        # Pagination keywords
        if any(
            keyword in task_lower
            for keyword in ["pagination", "paging", "page", "infinite scroll"]
        ):
            _add_suggestion(
                suggestions,
                "pagination",
                "Task mentions pagination",
                0.9,
            )

        # Caching keywords
        if any(
            keyword in task_lower
            for keyword in ["cache", "caching", "redis", "memcached", "performance"]
        ):
            _add_suggestion(
                suggestions,
                "caching",
                "Task mentions caching",
                0.9,
            )

        # Notification keywords
        if any(
            keyword in task_lower
            for keyword in [
                "email",
                "notification",
                "alert",
                "notify",
                "send",
                "mail",
            ]
        ):
            _add_suggestion(
                suggestions,
                "email_notifications",
                "Task mentions notifications",
                0.9,
            )

        # PDF keywords
        if any(keyword in task_lower for keyword in ["pdf", "report", "invoice"]):
            _add_suggestion(
                suggestions,
                "pdf_generation",
                "Task mentions PDF generation",
                0.9,
            )

        # Data export/import keywords
        if any(
            keyword in task_lower
            for keyword in ["export", "download", "csv", "excel", "xlsx"]
        ):
            _add_suggestion(
                suggestions,
                "export_data",
                "Task mentions data export",
                0.9,
            )
        if any(keyword in task_lower for keyword in ["import", "upload", "csv"]):
            _add_suggestion(
                suggestions,
                "import_data",
                "Task mentions data import",
                0.9,
            )

        # User management keywords
        if any(
            keyword in task_lower
            for keyword in ["user", "profile", "account", "settings"]
        ):
            _add_suggestion(
                suggestions,
                "user_profile",
                "Task mentions user management",
                0.8,
            )

        # Admin keywords
        if any(
            keyword in task_lower
            for keyword in ["admin", "dashboard", "management", "control"]
        ):
            _add_suggestion(
                suggestions,
                "admin_panel",
                "Task mentions admin functionality",
                0.8,
            )

        # Testing keywords
        if any(
            keyword in task_lower
            for keyword in ["test", "testing", "spec", "unit", "coverage"]
        ):
            _add_suggestion(
                suggestions,
                "test_suite",
                "Task mentions testing",
                0.9,
            )

        # Documentation keywords
        if any(
            keyword in task_lower
            for keyword in ["docs", "documentation", "readme", "guide"]
        ):
            _add_suggestion(
                suggestions,
                "documentation",
                "Task mentions documentation",
                0.9,
            )

        # Logging keywords
        if any(
            keyword in task_lower
            for keyword in ["log", "logging", "debug", "trace", "audit"]
        ):
            _add_suggestion(
                suggestions,
                "logging_system",
                "Task mentions logging",
                0.9,
            )

        # Error handling keywords
        if any(
            keyword in task_lower
            for keyword in ["error", "exception", "handling", "recovery"]
        ):
            _add_suggestion(
                suggestions,
                "error_handling",
                "Task mentions error handling",
                0.9,
            )

        # Performance keywords
        if any(
            keyword in task_lower
            for keyword in [
                "performance",
                "optimize",
                "speed",
                "slow",
                "fast",
                "improve",
            ]
        ):
            _add_suggestion(
                suggestions,
                "performance_optimization",
                "Task mentions performance",
                0.9,
            )

        # Security keywords
        if any(
            keyword in task_lower
            for keyword in ["security", "audit", "vulnerability", "secure"]
        ):
            _add_suggestion(
                suggestions,
                "security_audit",
                "Task mentions security",
                0.9,
            )

        # CI/CD keywords
        if any(
            keyword in task_lower
            for keyword in [
                "ci",
                "cd",
                "pipeline",
                "deploy",
                "github actions",
                "jenkins",
            ]
        ):
            _add_suggestion(
                suggestions,
                "ci_cd_pipeline",
                "Task mentions CI/CD",
                0.9,
            )

        # Monitoring keywords
        if any(
            keyword in task_lower
            for keyword in ["monitor", "monitoring", "metrics", "observability"]
        ):
            _add_suggestion(
                suggestions,
                "monitoring_dashboard",
                "Task mentions monitoring",
                0.9,
            )

    # Convert to list and sort by relevance
    result = sorted(
        [
            {"name": name, "reason": reason, "relevance": score}
            for name, (reason, score) in suggestions.items()
        ],
        key=lambda x: x["relevance"],
        reverse=True,
    )

    # Return top 10 suggestions
    return result[:10]


def _add_suggestion(
    suggestions: dict[str, tuple], template_name: str, reason: str, score: float
) -> None:
    """
    Add or update a template suggestion with the highest relevance score.

    Args:
        suggestions: Dictionary of suggestions to update
        template_name: Name of the template
        reason: Reason for the suggestion
        score: Relevance score (0.0 to 1.0)
    """
    if template_name in suggestions:
        existing_reason, existing_score = suggestions[template_name]
        if score > existing_score:
            suggestions[template_name] = (reason, score)
    else:
        suggestions[template_name] = (reason, score)
