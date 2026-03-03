"""
File Templates Plugin
=====================

Example integration plugin that demonstrates:
- File template management (built-in + custom)
- MCP tool creation for creating files from templates
- Template variable substitution
- Configuration for custom template directories

This plugin provides agents with tools to create files from templates,
reducing boilerplate and ensuring consistency across the codebase.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from plugins.base import PluginMetadata
from plugins.sdk.integration import IntegrationContext, IntegrationPlugin

logger = logging.getLogger(__name__)


# Built-in templates
BUILTIN_TEMPLATES = {
    "react-component": {
        "name": "React Functional Component",
        "description": "React functional component with TypeScript",
        "extension": ".tsx",
        "variables": ["ComponentName", "author"],
        "template": """import React from 'react';

interface {{ComponentName}}Props {
  // Add your props here
}

/**
 * {{ComponentName}} component
 *
 * @author {{author}}
 * @created {{timestamp}}
 */
export const {{ComponentName}}: React.FC<{{ComponentName}}Props> = (props) => {
  return (
    <div className="{{component-name}}">
      <h1>{{ComponentName}}</h1>
    </div>
  );
};
""",
    },
    "python-module": {
        "name": "Python Module",
        "description": "Python module with class and docstrings",
        "extension": ".py",
        "variables": ["ModuleName", "ClassName", "author"],
        "template": '''"""
{{ModuleName}} Module
{'=' * (len('{{ModuleName}}') + 7)}

{{description}}

Author: {{author}}
Created: {{timestamp}}
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class {{ClassName}}:
    """
    {{ClassName}} class.

    Add your class description here.
    """

    def __init__(self):
        """Initialize {{ClassName}}."""
        logger.debug("{{ClassName}} initialized")

    def process(self, data: Any) -> Any:
        """
        Process data.

        Args:
            data: Input data to process

        Returns:
            Processed data
        """
        logger.info("Processing data in {{ClassName}}")
        return data
''',
    },
    "typescript-interface": {
        "name": "TypeScript Interface",
        "description": "TypeScript interface definition",
        "extension": ".ts",
        "variables": ["InterfaceName", "author"],
        "template": """/**
 * {{InterfaceName}} interface
 *
 * {{description}}
 *
 * @author {{author}}
 * @created {{timestamp}}
 */
export interface {{InterfaceName}} {
  id: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
  // Add your properties here
}

/**
 * Create a new {{InterfaceName}} instance
 */
export function create{{InterfaceName}}(
  data: Partial<{{InterfaceName}}>
): {{InterfaceName}} {
  return {
    id: data.id || '',
    name: data.name || '',
    createdAt: data.createdAt || new Date(),
    updatedAt: data.updatedAt || new Date(),
    ...data,
  };
}
""",
    },
    "pytest-test": {
        "name": "Pytest Test File",
        "description": "Python test file using pytest",
        "extension": ".py",
        "variables": ["ModuleName", "author"],
        "template": '''"""
Test suite for {{ModuleName}}

Author: {{author}}
Created: {{timestamp}}
"""

from __future__ import annotations

import pytest

# Import the module/class to test
# from {{module_name}} import {{ClassName}}


class Test{{ModuleName}}:
    """Test suite for {{ModuleName}}."""

    @pytest.fixture
    def setup(self):
        """Set up test fixtures."""
        # Add your setup code here
        pass

    def test_basic_functionality(self, setup):
        """Test basic functionality."""
        # Arrange
        # Add your test setup

        # Act
        # Call the function/method to test

        # Assert
        # Verify the expected behavior
        assert True, "Replace with actual test"

    def test_error_handling(self, setup):
        """Test error handling."""
        # Test that errors are handled correctly
        with pytest.raises(ValueError):
            # Code that should raise ValueError
            pass
''',
    },
    "api-endpoint": {
        "name": "FastAPI Endpoint",
        "description": "FastAPI endpoint with request/response models",
        "extension": ".py",
        "variables": ["ResourceName", "author"],
        "template": '''"""
{{ResourceName}} API Endpoint

Author: {{author}}
Created: {{timestamp}}
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/{{resource-name}}", tags=["{{resource-name}}"])


class {{ResourceName}}Request(BaseModel):
    """Request model for {{ResourceName}}."""
    name: str
    description: str


class {{ResourceName}}Response(BaseModel):
    """Response model for {{ResourceName}}."""
    id: str
    name: str
    description: str
    created_at: str


@router.post("/", response_model={{ResourceName}}Response, status_code=status.HTTP_201_CREATED)
async def create_{{resource_name}}(request: {{ResourceName}}Request) -> {{ResourceName}}Response:
    """
    Create a new {{resource_name}}.

    Args:
        request: {{ResourceName}} creation request

    Returns:
        Created {{resource_name}}
    """
    logger.info(f"Creating {{resource_name}}: {request.name}")

    # Add your creation logic here

    return {{ResourceName}}Response(
        id="generated-id",
        name=request.name,
        description=request.description,
        created_at=str(datetime.now()),
    )


@router.get("/", response_model=List[{{ResourceName}}Response])
async def list_{{resource_name}}s() -> List[{{ResourceName}}Response]:
    """
    List all {{resource_name}}s.

    Returns:
        List of {{resource_name}}s
    """
    logger.info("Listing {{resource_name}}s")

    # Add your list logic here

    return []


@router.get("/{id}", response_model={{ResourceName}}Response)
async def get_{{resource_name}}(id: str) -> {{ResourceName}}Response:
    """
    Get a {{resource_name}} by ID.

    Args:
        id: {{ResourceName}} ID

    Returns:
        {{ResourceName}} details

    Raises:
        HTTPException: If {{resource_name}} not found
    """
    logger.info(f"Getting {{resource_name}}: {id}")

    # Add your get logic here

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{{ResourceName}} {id} not found"
    )
''',
    },
}


class FileTemplatesPlugin(IntegrationPlugin):
    """
    File templates integration plugin.

    Provides MCP tools for agents to create files from templates with
    variable substitution. Supports both built-in templates and custom
    user-defined templates.

    Configuration:
        FILE_TEMPLATES_DIR: Optional directory for custom templates

    MCP Tools:
        - list_templates: List available templates
        - get_template_info: Get details about a specific template
        - create_from_template: Create a file from a template
    """

    def __init__(self, metadata: PluginMetadata):
        """Initialize file templates plugin."""
        super().__init__(metadata)
        self.custom_templates: dict[str, dict] = {}
        logger.debug("FileTemplatesPlugin initialized")

    def on_load(self) -> None:
        """
        Called when plugin is loaded.

        Loads custom templates if a custom template directory is configured.
        """
        logger.info("file-templates: Plugin loaded")

        # Check for custom templates directory
        custom_dir = self.get_config_value("FILE_TEMPLATES_DIR")
        if custom_dir:
            logger.info(f"file-templates: Custom templates directory: {custom_dir}")
            self._load_custom_templates(Path(custom_dir))

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        logger.info("file-templates: Plugin enabled")
        logger.info(
            f"file-templates: {len(BUILTIN_TEMPLATES)} built-in templates available"
        )
        if self.custom_templates:
            logger.info(
                f"file-templates: {len(self.custom_templates)} custom templates loaded"
            )

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        logger.info("file-templates: Plugin disabled")

    def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        logger.info("file-templates: Plugin unloaded")
        self.custom_templates.clear()

    def _load_custom_templates(self, templates_dir: Path) -> None:
        """
        Load custom templates from directory.

        Args:
            templates_dir: Directory containing custom template JSON files
        """
        if not templates_dir.exists():
            logger.warning(f"Custom templates directory not found: {templates_dir}")
            return

        for template_file in templates_dir.glob("*.json"):
            try:
                with open(template_file, encoding="utf-8") as f:
                    template_data = json.load(f)
                    template_id = template_file.stem
                    self.custom_templates[template_id] = template_data
                    logger.debug(f"Loaded custom template: {template_id}")
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Failed to load template {template_file}: {e}")

    def _get_all_templates(self) -> dict[str, dict]:
        """Get all templates (built-in + custom)."""
        return {**BUILTIN_TEMPLATES, **self.custom_templates}

    def _substitute_variables(self, template: str, variables: dict[str, str]) -> str:
        """
        Substitute variables in template.

        Supports:
        - {{VariableName}}: Direct substitution
        - {{variable-name}}: Kebab-case conversion
        - {{variable_name}}: Snake-case conversion

        Args:
            template: Template string with {{variable}} placeholders
            variables: Dictionary of variable values

        Returns:
            Template with variables substituted
        """
        result = template

        # Add automatic variables
        auto_vars = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "year": str(datetime.now().year),
        }
        all_vars = {**auto_vars, **variables}

        # Substitute direct variables
        for var_name, var_value in all_vars.items():
            result = result.replace(f"{{{{{var_name}}}}}", var_value)

        # Generate case variations
        for var_name, var_value in all_vars.items():
            # Kebab-case: MyComponent -> my-component
            kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", var_value).lower()
            result = result.replace(f"{{{{{var_name}-name}}}}", kebab)

            # Snake-case: MyComponent -> my_component
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", var_value).lower()
            result = result.replace(f"{{{{{var_name}_name}}}}", snake)

        return result

    def create_mcp_tools(self, context: IntegrationContext) -> list:
        """
        Create MCP tools for file templates.

        Tools:
        - list_templates: List available templates
        - get_template_info: Get template details
        - create_from_template: Create file from template

        Args:
            context: Integration context

        Returns:
            List of MCP tool functions
        """

        def list_templates() -> str:
            """
            List all available file templates.

            Returns a formatted list of template IDs, names, and descriptions
            that can be used to create files.

            Returns:
                Formatted string with template information
            """
            templates = self._get_all_templates()

            if not templates:
                return "No templates available"

            lines = ["Available File Templates:", "=" * 40, ""]
            for template_id, template_data in templates.items():
                name = template_data.get("name", template_id)
                desc = template_data.get("description", "No description")
                ext = template_data.get("extension", "")
                lines.append(f"• {template_id} ({ext})")
                lines.append(f"  {name}")
                lines.append(f"  {desc}")
                lines.append("")

            logger.info("Listed file templates")
            return "\n".join(lines)

        def get_template_info(template_id: str) -> str:
            """
            Get detailed information about a specific template.

            Args:
                template_id: ID of the template to inspect

            Returns:
                Detailed template information including required variables
            """
            templates = self._get_all_templates()

            if template_id not in templates:
                available = ", ".join(templates.keys())
                return f"Template '{template_id}' not found. Available: {available}"

            template_data = templates[template_id]
            lines = [
                f"Template: {template_id}",
                "=" * 40,
                f"Name: {template_data.get('name', template_id)}",
                f"Description: {template_data.get('description', 'No description')}",
                f"Extension: {template_data.get('extension', 'N/A')}",
                "",
                "Required Variables:",
            ]

            for var in template_data.get("variables", []):
                lines.append(f"  • {var}")

            lines.extend(
                [
                    "",
                    "Automatic Variables:",
                    "  • timestamp - Current timestamp",
                    "  • date - Current date",
                    "  • year - Current year",
                    "",
                    "Note: Variables support auto-conversion:",
                    "  {{VarName}} → direct value",
                    "  {{var-name}} → kebab-case",
                    "  {{var_name}} → snake-case",
                ]
            )

            logger.info(f"Retrieved template info: {template_id}")
            return "\n".join(lines)

        def create_from_template(
            template_id: str, file_path: str, variables: str
        ) -> str:
            """
            Create a file from a template with variable substitution.

            Args:
                template_id: ID of the template to use
                file_path: Path where the file should be created (relative to project)
                variables: JSON string with variable values (e.g., '{"ComponentName": "MyButton", "author": "John"}')

            Returns:
                Success/error message with file creation details
            """
            templates = self._get_all_templates()

            if template_id not in templates:
                available = ", ".join(templates.keys())
                return (
                    f"Error: Template '{template_id}' not found. Available: {available}"
                )

            # Parse variables
            try:
                var_dict = json.loads(variables) if variables else {}
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON for variables: {e}"

            template_data = templates[template_id]
            template_content = template_data.get("template", "")

            # Check required variables
            required_vars = template_data.get("variables", [])
            missing_vars = [v for v in required_vars if v not in var_dict]
            if missing_vars:
                return f"Error: Missing required variables: {', '.join(missing_vars)}"

            # Substitute variables
            try:
                content = self._substitute_variables(template_content, var_dict)
            except Exception as e:
                return f"Error: Variable substitution failed: {e}"

            # Create file
            target_path = context.project_dir / file_path
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)

                logger.info(f"Created file from template: {file_path} ({template_id})")
                return f"Success: Created {file_path} from template '{template_id}'"

            except (OSError, UnicodeEncodeError) as e:
                return f"Error: Failed to create file: {e}"

        return [list_templates, get_template_info, create_from_template]

    def is_available(self) -> bool:
        """Check if the integration is available."""
        return self.is_enabled
