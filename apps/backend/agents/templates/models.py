"""
Agent Template Models
=====================

Data models for custom agent templates.

AgentTemplate defines the schema for custom agent configurations, including:
- Custom system prompts
- Tool set selection
- MCP server configuration
- Versioning and metadata
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AgentTemplate:
    """
    Custom agent configuration template.

    Represents a user-defined agent configuration with custom prompts,
    tool selections, and behaviors.

    Attributes:
        name: Unique template identifier (e.g., "documentation-agent")
        description: Human-readable description of the template's purpose
        category: Template category (e.g., 'testing', 'documentation', 'security')
        version: Semantic version string (e.g., "1.0.0")
        custom_prompt: Custom system prompt for the agent
        tools: List of tool names to enable (e.g., ["Read", "Write", "Bash"])
        mcp_servers: List of MCP server names to enable (e.g., ["context7", "graphiti"])
        author: Template author/creator
        tags: List of searchable tags
        created_at: Template creation timestamp (ISO 8601 format)
        updated_at: Last update timestamp (ISO 8601 format)
        thinking_level: Default thinking level ("none", "low", "medium", "high", "ultrathink")
        parameters: Custom parameters with types and defaults
    """

    name: str
    description: str
    category: str
    version: str = "1.0.0"
    custom_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    author: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    thinking_level: str = "medium"
    parameters: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """
        Validate template configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate required fields
        if not self.name or not self.name.strip():
            errors.append("Template name is required")
        elif not self._is_valid_name(self.name):
            errors.append(
                "Template name must be lowercase alphanumeric with hyphens only"
            )

        if not self.description or not self.description.strip():
            errors.append("Template description is required")

        if not self.category or not self.category.strip():
            errors.append("Template category is required")

        # Validate version format (semantic versioning)
        if not self._is_valid_version(self.version):
            errors.append(
                f"Invalid version format: {self.version}. Expected semantic versioning (e.g., 1.0.0)"
            )

        # Validate thinking level
        valid_thinking_levels = ["none", "low", "medium", "high", "ultrathink"]
        if self.thinking_level not in valid_thinking_levels:
            errors.append(
                f"Invalid thinking_level: {self.thinking_level}. Must be one of {valid_thinking_levels}"
            )

        # Validate custom prompt
        if self.custom_prompt and len(self.custom_prompt.strip()) < 20:
            errors.append("Custom prompt must be at least 20 characters if provided")

        # Validate tools list
        if not isinstance(self.tools, list):
            errors.append("Tools must be a list")
        # Validate MCP servers list
        if not isinstance(self.mcp_servers, list):
            errors.append("MCP servers must be a list")

        return errors

    def _is_valid_name(self, name: str) -> bool:
        """
        Check if template name is valid.

        Valid names are lowercase alphanumeric with hyphens.

        Args:
            name: Template name to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"
        return bool(re.match(pattern, name))

    def _is_valid_version(self, version: str) -> bool:
        """
        Check if version follows semantic versioning.

        Args:
            version: Version string to validate

        Returns:
            True if valid semantic version, False otherwise
        """
        import re

        # Semantic versioning pattern: MAJOR.MINOR.PATCH (with optional pre-release/build)
        pattern = r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
        return bool(re.match(pattern, version))

    def to_dict(self) -> dict[str, Any]:
        """
        Convert template to dictionary format.

        Returns:
            Dictionary representation of the template
        """
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "custom_prompt": self.custom_prompt,
            "tools": self.tools,
            "mcp_servers": self.mcp_servers,
            "author": self.author,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "thinking_level": self.thinking_level,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentTemplate":
        """
        Create template from dictionary.

        Args:
            data: Dictionary with template data

        Returns:
            AgentTemplate instance
        """
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", ""),
            version=data.get("version", "1.0.0"),
            custom_prompt=data.get("custom_prompt", ""),
            tools=data.get("tools", []),
            mcp_servers=data.get("mcp_servers", []),
            author=data.get("author", ""),
            tags=data.get("tags", []),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=data.get("updated_at", datetime.now(UTC).isoformat()),
            thinking_level=data.get("thinking_level", "medium"),
            parameters=data.get("parameters", {}),
        )

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.now(UTC).isoformat()
