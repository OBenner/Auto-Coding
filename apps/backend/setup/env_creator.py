"""
.env file creator for Auto Code setup wizard.

Creates a .env configuration file from the .env.example template,
allowing both programmatic configuration and interactive prompts.
"""

import logging
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


class EnvCreationResult(TypedDict):
    """Result of .env file creation."""

    success: bool
    env_path: str
    message: str
    created_new: bool
    backed_up: bool


class EnvConfig(TypedDict, total=False):
    """Configuration values for .env file."""

    # Authentication
    claude_code_oauth_token: str | None
    anthropic_auth_token: str | None

    # Custom API endpoint
    anthropic_base_url: str | None
    no_proxy: str | None
    disable_telemetry: bool | None
    disable_cost_warnings: bool | None
    api_timeout_ms: int | None

    # Model configuration
    auto_build_model: str | None

    # Multi-provider configuration
    ai_engine_provider: str | None
    openai_api_key: str | None
    google_api_key: str | None
    zhipu_api_key: str | None
    openrouter_api_key: str | None
    ollama_base_url: str | None
    litellm_model: str | None

    # Graphiti memory
    graphiti_enabled: bool | None
    graphiti_llm_provider: str | None
    graphiti_embedder_provider: str | None
    anthropic_api_key: str | None
    voyage_api_key: str | None

    # Integrations
    linear_api_key: str | None
    linear_team_id: str | None
    github_token: str | None
    github_owner: str | None
    github_repo: str | None


def create_env_file(
    config: EnvConfig | None = None,
    backup_existing: bool = True,
    force: bool = False,
) -> EnvCreationResult:
    """
    Create a .env file from the template with provided configuration.

    Args:
        config: Dictionary of configuration values to write. If None, creates
                minimal .env with comments only.
        backup_existing: If True, backup existing .env file before overwriting.
        force: If True, overwrite existing .env file without prompting.

    Returns:
        EnvCreationResult: Dictionary containing:
            - success: True if .env was created successfully
            - env_path: Path to the created .env file
            - message: Human-readable result message
            - created_new: True if new file was created, False if overwritten
            - backed_up: True if existing file was backed up

    Example:
        >>> config = {
        ...     'graphiti_enabled': True,
        ...     'graphiti_llm_provider': 'openai',
        ...     'openai_api_key': 'sk-...'
        ... }
        >>> result = create_env_file(config)
        >>> if result['success']:
        ...     print(f".env created at {result['env_path']}")
    """
    try:
        # Get paths
        backend_dir = Path(__file__).parent.parent.resolve()
        env_file = backend_dir / ".env"
        env_example = backend_dir / ".env.example"

        # Check if .env already exists
        created_new = not env_file.exists()
        backed_up = False

        if env_file.exists() and not force:
            logger.warning(f".env file already exists at {env_file}")
            return {
                "success": False,
                "env_path": str(env_file),
                "message": (
                    f".env file already exists at {env_file}\n"
                    "Use force=True to overwrite or backup_existing=True to backup first."
                ),
                "created_new": False,
                "backed_up": False,
            }

        # Backup existing file if requested
        if env_file.exists() and backup_existing:
            backed_up = _backup_env_file(env_file)
            if backed_up:
                logger.info(f"Backed up existing .env to {env_file}.backup")

        # Read template
        if not env_example.exists():
            error_msg = f".env.example template not found at {env_example}"
            logger.error(error_msg)
            return {
                "success": False,
                "env_path": str(env_file),
                "message": error_msg,
                "created_new": False,
                "backed_up": backed_up,
            }

        template_content = env_example.read_text(encoding="utf-8")

        # Generate .env content
        if config:
            env_content = _generate_env_content(template_content, config)
        else:
            # No config provided, use template as-is (all commented)
            env_content = template_content

        # Write .env file
        env_file.write_text(env_content, encoding="utf-8")
        logger.info(f"Created .env file at {env_file}")

        # Build success message
        if created_new:
            message = f"Successfully created .env file at {env_file}"
        else:
            message = f"Successfully updated .env file at {env_file}"
            if backed_up:
                message += f"\nBackup saved to {env_file}.backup"

        return {
            "success": True,
            "env_path": str(env_file),
            "message": message,
            "created_new": created_new,
            "backed_up": backed_up,
        }

    except PermissionError as e:
        error_msg = f"Permission denied when creating .env file: {e}"
        logger.error(error_msg)
        return {
            "success": False,
            "env_path": str(env_file) if "env_file" in locals() else "unknown",
            "message": error_msg,
            "created_new": False,
            "backed_up": False,
        }
    except Exception as e:
        error_msg = f"Failed to create .env file: {e}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "env_path": str(env_file) if "env_file" in locals() else "unknown",
            "message": error_msg,
            "created_new": False,
            "backed_up": False,
        }


def _backup_env_file(env_file: Path) -> bool:
    """
    Backup existing .env file.

    Args:
        env_file: Path to the .env file to backup

    Returns:
        bool: True if backup was successful, False otherwise
    """
    try:
        backup_file = env_file.with_suffix(".env.backup")
        # If backup already exists, append timestamp
        if backup_file.exists():
            from datetime import UTC, datetime

            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            backup_file = env_file.parent / f".env.backup.{timestamp}"

        env_file.rename(backup_file)
        logger.debug(f"Backed up .env to {backup_file}")
        return True
    except Exception as e:
        logger.warning(f"Failed to backup .env file: {e}")
        return False


def _generate_env_content(template: str, config: EnvConfig) -> str:
    """
    Generate .env content from template and configuration.

    Args:
        template: Content of .env.example template
        config: Configuration values to apply

    Returns:
        str: Generated .env file content

    This function intelligently updates the template by:
    1. Uncommenting lines for provided config values
    2. Updating values for uncommented lines
    3. Preserving all comments and structure
    """
    lines = template.split("\n")
    output_lines = []

    # Map config keys to env variable names (snake_case -> UPPER_CASE)
    env_map = {key.upper(): value for key, value in config.items() if value is not None}

    for line in lines:
        stripped = line.strip()

        # Preserve empty lines and pure comments
        if not stripped or stripped.startswith("#"):
            output_lines.append(line)
            continue

        # Check if this is a commented-out variable (e.g., "# VARIABLE=value")
        if stripped.startswith("# ") and "=" in stripped:
            # Extract variable name
            uncommented = stripped[2:].strip()
            var_name = uncommented.split("=")[0].strip()

            # Check if we have a value for this variable
            if var_name in env_map:
                value = env_map[var_name]
                # Format boolean values
                if isinstance(value, bool):
                    value = "true" if value else "false"
                output_lines.append(f"{var_name}={value}")
                continue

        # Check if this is an active variable
        if "=" in stripped:
            var_name = stripped.split("=")[0].strip()

            # Update value if we have a new one
            if var_name in env_map:
                value = env_map[var_name]
                # Format boolean values
                if isinstance(value, bool):
                    value = "true" if value else "false"
                output_lines.append(f"{var_name}={value}")
                continue

        # Preserve line as-is
        output_lines.append(line)

    return "\n".join(output_lines)


def get_env_path() -> str:
    """
    Get the path to the .env file.

    Returns:
        str: Absolute path to the .env file location
    """
    backend_dir = Path(__file__).parent.parent.resolve()
    return str(backend_dir / ".env")


def env_exists() -> bool:
    """
    Check if .env file exists.

    Returns:
        bool: True if .env file exists, False otherwise
    """
    env_file = Path(get_env_path())
    return env_file.exists()


def read_env_value(key: str) -> str | None:
    """
    Read a specific value from the .env file.

    Args:
        key: Environment variable name to read

    Returns:
        str | None: Value if found, None otherwise

    Example:
        >>> api_key = read_env_value('OPENAI_API_KEY')
        >>> if api_key:
        ...     print(f"API key found: {api_key[:10]}...")
    """
    env_file = Path(get_env_path())
    if not env_file.exists():
        return None

    try:
        content = env_file.read_text(encoding="utf-8")
        for line in content.split("\n"):
            stripped = line.strip()
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue
            # Parse key=value
            if "=" in stripped:
                var_name, var_value = stripped.split("=", 1)
                if var_name.strip() == key:
                    return var_value.strip()
        return None
    except Exception as e:
        logger.error(f"Failed to read .env file: {e}")
        return None


def get_minimal_config() -> EnvConfig:
    """
    Get a minimal configuration for Auto Code.

    Returns:
        EnvConfig: Minimal configuration with sensible defaults.
                   Only includes Graphiti enabled with OpenAI provider.
                   User still needs to provide API keys.

    This is useful for the setup wizard to start with minimal required settings.
    """
    return {
        "graphiti_enabled": True,
        "graphiti_llm_provider": "openai",
        "graphiti_embedder_provider": "openai",
        # Note: User still needs to provide OPENAI_API_KEY
    }
