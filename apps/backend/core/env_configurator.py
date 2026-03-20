"""
Environment Configurator
========================

Handles .env file setup with interactive prompts for environment variables.
"""

import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EnvVariable:
    """Represents a single environment variable with metadata."""

    def __init__(
        self,
        name: str,
        value: str | None = None,
        description: str | None = None,
        required: bool = False,
        section: str | None = None,
    ):
        """
        Initialize an environment variable.

        Args:
            name: Variable name (e.g., "CLAUDE_CODE_OAUTH_TOKEN")
            value: Default value (None if not set)
            description: Human-readable description
            required: Whether this variable is required
            section: Section header this variable belongs to
        """
        self.name = name
        self.value = value
        self.description = description
        self.required = required
        self.section = section


class EnvConfigurator:
    """Manages environment configuration from .env.example to .env."""

    def __init__(self, project_dir: Path):
        """
        Initialize the environment configurator.

        Args:
            project_dir: Root directory of the project
        """
        self.project_dir = Path(project_dir)
        self.backend_dir = self.project_dir / "apps" / "backend"
        self.env_example = self.backend_dir / ".env.example"
        self.env_file = self.backend_dir / ".env"

    def parse_env_example(self) -> list[EnvVariable]:
        """
        Parse .env.example file to extract variables and metadata.

        Returns:
            List of EnvVariable objects

        Raises:
            FileNotFoundError: If .env.example does not exist
        """
        if not self.env_example.exists():
            raise FileNotFoundError(
                f".env.example not found at {self.env_example}\n"
                "Expected location: apps/backend/.env.example"
            )

        variables: list[EnvVariable] = []
        current_section: str | None = None
        current_description: list[str] = []

        with open(self.env_example, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip()

                # Section headers (e.g., "# AUTHENTICATION (REQUIRED)")
                if line.startswith("# ====="):
                    continue
                if line.startswith("#") and line.endswith("="):
                    # Next line will be section header
                    continue
                if line.startswith("#") and "(" in line and ")" in line:
                    current_section = line.lstrip("# ").strip()
                    current_description = []
                    continue

                # Comment lines (descriptions)
                if line.startswith("#"):
                    comment = line.lstrip("#").strip()
                    if comment:
                        current_description.append(comment)
                    continue

                # Empty lines reset description
                if not line.strip():
                    current_description = []
                    continue

                # Variable assignment (e.g., "VAR_NAME=value")
                if "=" in line and not line.startswith("#"):
                    # Check if it's a commented-out variable
                    is_commented = line.lstrip().startswith("#")
                    clean_line = line.lstrip("#").strip()

                    parts = clean_line.split("=", 1)
                    var_name = parts[0].strip()
                    var_value = parts[1].strip() if len(parts) > 1 else None

                    # Determine if required based on section
                    required = (
                        current_section is not None and "REQUIRED" in current_section
                    )

                    # Join description lines
                    description = (
                        " ".join(current_description) if current_description else None
                    )

                    variables.append(
                        EnvVariable(
                            name=var_name,
                            value=var_value if not is_commented else None,
                            description=description,
                            required=required,
                            section=current_section,
                        )
                    )

                    # Reset description after variable
                    current_description = []

        return variables

    def get_existing_env_values(self) -> dict[str, str]:
        """
        Read existing .env file and return current values.

        Returns:
            Dictionary mapping variable names to values
        """
        if not self.env_file.exists():
            return {}

        env_values: dict[str, str] = {}

        with open(self.env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse variable assignment
                if "=" in line:
                    parts = line.split("=", 1)
                    var_name = parts[0].strip()
                    var_value = parts[1].strip() if len(parts) > 1 else ""
                    env_values[var_name] = var_value

        return env_values

    def prompt_for_value(
        self, var: EnvVariable, existing_value: str | None = None
    ) -> str | None:
        """
        Prompt user for environment variable value.

        Args:
            var: Environment variable to prompt for
            existing_value: Current value from .env (if exists)

        Returns:
            User-provided value, or None to skip
        """
        # Show section header if new section
        if var.section:
            print(f"\n{var.section}")
            print("-" * len(var.section))

        # Show description
        if var.description:
            print(f"\n{var.description}")

        # Show current value if exists
        if existing_value:
            print(f"Current value: {existing_value}")

        # Show default from .env.example
        if var.value and var.value != existing_value:
            print(f"Default: {var.value}")

        # Prompt for input
        required_marker = " (REQUIRED)" if var.required else ""
        prompt = f"{var.name}{required_marker}: "

        try:
            user_input = input(prompt).strip()

            # Return existing value if user pressed enter without input
            if not user_input:
                return existing_value or var.value

            return user_input

        except (KeyboardInterrupt, EOFError):
            print("\n\nConfiguration cancelled by user")
            return None

    def create_env_file(
        self, interactive: bool = True, dry_run: bool = False
    ) -> dict[str, Any]:
        """
        Create or update .env file from .env.example.

        Args:
            interactive: If True, prompt user for values. If False, use defaults.
            dry_run: If True, don't write files, just report what would happen

        Returns:
            Dictionary with configuration results:
            - success: bool
            - variables_configured: int
            - errors: list of error messages
        """
        result: dict[str, Any] = {
            "success": False,
            "variables_configured": 0,
            "errors": [],
        }

        try:
            # Parse .env.example
            variables = self.parse_env_example()

            # Get existing values
            existing_values = self.get_existing_env_values()

            # Collect new values
            new_env_content: list[str] = []
            current_section: str | None = None
            configured_count = 0

            for var in variables:
                # Add section header if new section
                if var.section and var.section != current_section:
                    new_env_content.append(
                        f"\n# {'=' * 77}\n# {var.section}\n# {'=' * 77}\n"
                    )
                    current_section = var.section

                # Get value (prompt or use existing/default)
                if interactive and var.required:
                    value = self.prompt_for_value(var, existing_values.get(var.name))
                    if value is None:
                        result["errors"].append(
                            f"Configuration cancelled at {var.name}"
                        )
                        return result
                else:
                    # Non-interactive: use existing value, or default, or leave commented
                    value = existing_values.get(var.name) or var.value

                # Add to file content
                if var.description:
                    # Add description as comment
                    wrapped_desc = self._wrap_comment(var.description)
                    new_env_content.append(wrapped_desc)

                if value:
                    new_env_content.append(f"{var.name}={value}\n")
                    configured_count += 1
                else:
                    # Leave commented out if no value
                    new_env_content.append(f"# {var.name}=\n")

            # Write file (unless dry-run)
            if dry_run:
                print("\n[DRY RUN] Would write to .env:")
                print("".join(new_env_content[:500]))  # Show first 500 chars
                if len(new_env_content) > 500:
                    print("... (truncated)")
            else:
                with open(self.env_file, "w", encoding="utf-8") as f:
                    f.write("".join(new_env_content))
                logger.info(f"Created .env file at {self.env_file}")

            result["success"] = True
            result["variables_configured"] = configured_count

        except FileNotFoundError as e:
            result["errors"].append(str(e))
        except Exception as e:
            result["errors"].append(f"Unexpected error: {e}")
            logger.exception("Error creating .env file")

        return result

    def validate_required_vars(self) -> dict[str, Any]:
        """
        Validate that required environment variables are set.

        Returns:
            Dictionary with validation results:
            - valid: bool
            - missing_required: list of missing variable names
            - warnings: list of warning messages
        """
        result: dict[str, Any] = {
            "valid": True,
            "missing_required": [],
            "warnings": [],
        }

        try:
            variables = self.parse_env_example()
            existing_values = self.get_existing_env_values()

            for var in variables:
                if var.required:
                    value = existing_values.get(var.name)
                    if not value:
                        result["valid"] = False
                        result["missing_required"].append(var.name)

        except Exception as e:
            result["warnings"].append(f"Validation error: {e}")
            logger.exception("Error validating environment variables")

        return result

    def _wrap_comment(self, text: str, width: int = 80) -> str:
        """
        Wrap comment text to specified width.

        Args:
            text: Text to wrap
            width: Maximum line width (default: 80)

        Returns:
            Wrapped text with # prefix on each line
        """
        words = text.split()
        lines: list[str] = []
        current_line: list[str] = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > width - 2:  # -2 for "# "
                if current_line:
                    lines.append("# " + " ".join(current_line))
                current_line = [word]
                current_length = word_length
            else:
                current_line.append(word)
                current_length += word_length

        if current_line:
            lines.append("# " + " ".join(current_line))

        return "\n".join(lines) + "\n"


def setup_env(
    project_dir: Path, interactive: bool = True, dry_run: bool = False
) -> bool:
    """
    Set up environment configuration for the project.

    Args:
        project_dir: Root directory of the project
        interactive: If True, prompt user for values
        dry_run: If True, don't write files

    Returns:
        True if successful, False otherwise
    """
    configurator = EnvConfigurator(project_dir)

    # Create .env file
    result = configurator.create_env_file(interactive=interactive, dry_run=dry_run)

    if not result["success"]:
        print("\nEnvironment configuration failed:")
        for error in result["errors"]:
            print(f"  - {error}")
        return False

    # Validate required variables
    if not dry_run:
        validation = configurator.validate_required_vars()
        if not validation["valid"]:
            print("\nWarning: Missing required environment variables:")
            for var_name in validation["missing_required"]:
                print(f"  - {var_name}")
            print("\nRun setup again to configure missing variables.")
            return False

    print(
        f"\n✓ Environment configured ({result['variables_configured']} variables set)"
    )
    return True
