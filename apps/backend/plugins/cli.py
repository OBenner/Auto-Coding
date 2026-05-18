#!/usr/bin/env python3
"""
Plugin Management CLI
======================

Command-line interface for managing Auto Claude plugins.

Supports plugin lifecycle operations:
- List plugins with filtering
- Enable/disable plugins
- Install plugins from local or remote sources
- View plugin information

Usage:
    python plugins/cli.py list
    python plugins/cli.py list --type agent
    python plugins/cli.py enable <plugin-name>
    python plugins/cli.py disable <plugin-name>
    python plugins/cli.py install --path <path>
    python plugins/cli.py install --url <git-url>
    python plugins/cli.py info <plugin-name>
"""

import argparse
import json
import logging
import shutil
import sys
import tempfile
from collections import deque
from collections.abc import Iterator
from pathlib import Path

# Add parent directories to path for direct execution (must be before imports)
_cli_file_path = Path(__file__).resolve()
_plugins_dir = _cli_file_path.parent
_backend_dir = _plugins_dir.parent

if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
if str(_plugins_dir) not in sys.path:
    sys.path.insert(0, str(_plugins_dir))

# Handle both direct execution and module import
if __name__ == "__main__":
    # Direct execution - use absolute imports
    from plugins.base import PluginType
    from plugins.loader import PluginLoader, PluginLoadError, PluginValidationError
    from plugins.registry import PluginRegistry
else:
    # Module import - use relative imports
    try:
        from .base import PluginType
        from .loader import PluginLoader, PluginLoadError, PluginValidationError
        from .registry import PluginRegistry
    except ImportError:
        from plugins.base import PluginType
        from plugins.loader import PluginLoader, PluginLoadError, PluginValidationError
        from plugins.registry import PluginRegistry

# Import git utilities
from core.git_executable import run_git

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    """Add the common machine-readable output flag to a subcommand parser."""
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON on stdout",
    )


def _wants_json(args: argparse.Namespace) -> bool:
    """Return True when a command should emit JSON output."""
    return getattr(args, "json", False) is True


def _emit_json(payload: dict) -> None:
    """Print a JSON payload for frontend and automation callers."""
    print(json.dumps(payload, ensure_ascii=False))


def _enum_value(value):
    """Serialize enum-like values without coupling to a concrete enum class."""
    return value.value if hasattr(value, "value") else value


def _string_value(value, default: str = "") -> str:
    """Return a string value, ignoring mock sentinels and unset attributes."""
    return value if isinstance(value, str) else default


def _optional_string_value(value) -> str | None:
    """Return an optional string value, ignoring mock sentinels."""
    return value if isinstance(value, str) else None


def _metadata_to_dict(plugin) -> dict:
    """Serialize plugin metadata robustly for real plugins and test doubles."""
    metadata = getattr(plugin, "metadata", None)
    if metadata is not None:
        to_dict = getattr(metadata, "to_dict", None)
        if callable(to_dict):
            serialized = to_dict()
            if isinstance(serialized, dict):
                return serialized

    raw_permissions = (
        getattr(metadata, "required_permissions", []) if metadata is not None else []
    )
    permissions = raw_permissions if isinstance(raw_permissions, list) else []
    raw_dependencies = (
        getattr(metadata, "dependencies", []) if metadata is not None else []
    )
    raw_capabilities = (
        getattr(metadata, "capabilities", []) if metadata is not None else []
    )
    capabilities = raw_capabilities if isinstance(raw_capabilities, list) else []

    return {
        "name": _string_value(getattr(plugin, "name", "")),
        "version": _string_value(getattr(plugin, "version", "")),
        "author": _string_value(getattr(metadata, "author", ""))
        if metadata is not None
        else "",
        "description": _string_value(getattr(metadata, "description", ""))
        if metadata is not None
        else "",
        "plugin_type": _enum_value(getattr(plugin, "plugin_type", "")),
        "required_permissions": [
            _enum_value(permission)
            for permission in permissions
            if isinstance(permission, str) or hasattr(permission, "value")
        ],
        "dependencies": raw_dependencies if isinstance(raw_dependencies, list) else [],
        "capabilities": [
            _enum_value(capability)
            for capability in capabilities
            if isinstance(capability, str) or hasattr(capability, "value")
        ],
        "homepage": _optional_string_value(getattr(metadata, "homepage", None))
        if metadata is not None
        else None,
        "license": _optional_string_value(getattr(metadata, "license", None))
        if metadata is not None
        else None,
    }


def _permission_diff_for_plugin(plugin) -> dict:
    """Build the permission/capability diff shown before or after enablement."""
    metadata = getattr(plugin, "metadata", None)
    raw_permissions = (
        getattr(metadata, "required_permissions", []) if metadata is not None else []
    )
    raw_capabilities = (
        getattr(metadata, "capabilities", []) if metadata is not None else []
    )
    permissions = raw_permissions if isinstance(raw_permissions, list) else []
    capabilities = raw_capabilities if isinstance(raw_capabilities, list) else []
    permission_values = [
        _enum_value(permission)
        for permission in permissions
        if isinstance(permission, str) or hasattr(permission, "value")
    ]
    capability_values = [
        _enum_value(capability)
        for capability in capabilities
        if isinstance(capability, str) or hasattr(capability, "value")
    ]
    currently_enabled = bool(getattr(plugin, "is_enabled", False))

    return {
        "plugin_name": _string_value(getattr(plugin, "name", "")),
        "required_permissions": permission_values,
        "capabilities": capability_values,
        "added_permissions": [] if currently_enabled else permission_values,
        "added_capabilities": [] if currently_enabled else capability_values,
        "currently_enabled": currently_enabled,
        "would_enable": not currently_enabled,
    }


def _plugin_dir_for(registry: PluginRegistry, plugin) -> str:
    """Return the best-known installation directory for a plugin."""
    name = getattr(plugin, "name", "")
    loader = getattr(registry, "loader", None)
    user_plugins_dir = getattr(loader, "user_plugins_dir", None)
    system_plugins_dir = getattr(loader, "system_plugins_dir", None)

    if user_plugins_dir is not None:
        user_plugin_dir = Path(user_plugins_dir) / name
        if user_plugin_dir.exists():
            return str(user_plugin_dir)

    if system_plugins_dir is not None:
        return str(Path(system_plugins_dir) / name)

    plugin_dir = getattr(plugin, "plugin_dir", "")
    return str(plugin_dir) if isinstance(plugin_dir, (str, Path)) else ""


def _plugin_to_json(plugin, registry: PluginRegistry) -> dict:
    """Convert a plugin instance to the frontend PluginInfo wire shape."""
    metadata = _metadata_to_dict(plugin)
    metadata["name"] = metadata.get("name") or _string_value(
        getattr(plugin, "name", "")
    )
    metadata["version"] = metadata.get("version") or _string_value(
        getattr(plugin, "version", "")
    )
    metadata["plugin_type"] = metadata.get("plugin_type") or _enum_value(
        getattr(plugin, "plugin_type", "")
    )
    metadata["description"] = metadata.get("description") or getattr(
        getattr(plugin, "metadata", None),
        "description",
        "",
    )

    return {
        "metadata": metadata,
        "status": "enabled" if getattr(plugin, "is_enabled", False) else "disabled",
        "plugin_dir": _plugin_dir_for(registry, plugin),
    }


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for plugin CLI."""
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Plugin Management CLI for Auto Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                    List all plugins
  %(prog)s list --type agent       List only agent plugins
  %(prog)s enable my-plugin        Enable a plugin
  %(prog)s disable my-plugin       Disable a plugin
  %(prog)s install --path .        Install from local path
  %(prog)s install --url https://github.com/user/plugin.git
  %(prog)s info my-plugin          Show plugin details
  %(prog)s health --json           Inspect plugin manifests and directories
        """,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="Available Commands",
        description="Plugin management commands",
        required=True,
    )

    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List installed plugins",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    list_parser.add_argument(
        "--type",
        choices=["agent", "integration", "ui", "all"],
        default="all",
        help="Filter by plugin type (default: all)",
    )
    list_parser.add_argument(
        "--enabled-only",
        action="store_true",
        help="Show only enabled plugins",
    )
    _add_json_flag(list_parser)

    # Enable command
    enable_parser = subparsers.add_parser(
        "enable",
        help="Enable a plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    enable_parser.add_argument(
        "plugin_name",
        help="Name of the plugin to enable",
    )
    _add_json_flag(enable_parser)

    # Disable command
    disable_parser = subparsers.add_parser(
        "disable",
        help="Disable a plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    disable_parser.add_argument(
        "plugin_name",
        help="Name of the plugin to disable",
    )
    _add_json_flag(disable_parser)

    # Install command
    install_parser = subparsers.add_parser(
        "install",
        help="Install a plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    install_source = install_parser.add_mutually_exclusive_group(required=True)
    install_source.add_argument(
        "--path",
        "--from-directory",
        dest="path",
        help="Local path to plugin directory",
    )
    install_source.add_argument(
        "--url",
        "--from-url",
        dest="url",
        help="Git URL to remote plugin repository",
    )
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing plugin if it exists",
    )
    install_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate plugin without installing",
    )
    _add_json_flag(install_parser)

    # Info command
    info_parser = subparsers.add_parser(
        "info",
        help="Show plugin information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    info_parser.add_argument(
        "plugin_name",
        help="Name of the plugin",
    )
    _add_json_flag(info_parser)

    # Uninstall command
    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="Uninstall a plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    uninstall_parser.add_argument(
        "plugin_name",
        help="Name of the plugin to uninstall",
    )
    uninstall_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    _add_json_flag(uninstall_parser)

    # Health command
    health_parser = subparsers.add_parser(
        "health",
        help="Inspect plugin directories and manifests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_json_flag(health_parser)

    # Permission diff command
    permission_diff_parser = subparsers.add_parser(
        "permission-diff",
        help="Show permissions and capabilities a plugin would enable",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    permission_diff_parser.add_argument(
        "plugin_name",
        help="Name of the plugin to inspect",
    )
    _add_json_flag(permission_diff_parser)

    # Trace command
    traces_parser = subparsers.add_parser(
        "traces",
        help="Read recent project plugin trace events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    traces_parser.add_argument(
        "--plugin",
        help="Optional plugin name to filter traces",
    )
    traces_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum trace events to return (default: 50)",
    )
    _add_json_flag(traces_parser)

    # Runtime context preview command
    preview_parser = subparsers.add_parser(
        "preview-context",
        help="Preview enabled agent plugin prompt augmentations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    preview_parser.add_argument(
        "--agent-type",
        default="coder",
        help="Agent phase/type to preview (default: coder)",
    )
    preview_parser.add_argument(
        "--spec-dir",
        help="Spec directory to use for preview context",
    )
    preview_parser.add_argument(
        "--task",
        default="",
        help="Optional task text for plugin selection",
    )
    preview_parser.add_argument(
        "--file",
        dest="files",
        action="append",
        default=[],
        help="Project-relative file path to include in preview context",
    )
    _add_json_flag(preview_parser)

    return parser


def cmd_list(args: argparse.Namespace) -> int:
    """
    List installed plugins with optional filtering.

    Args:
        args: Parsed command-line arguments

    Returns:
        0 on success, 1 on error
    """
    try:
        # Get plugin registry instance
        registry = PluginRegistry.get_instance()

        # Ensure plugins are loaded
        if not registry.list_plugins():
            logger.info("Loading plugins...")
            registry.load_all_plugins()

        # Parse type filter
        plugin_type = None
        if args.type != "all":
            type_map = {
                "agent": PluginType.AGENT,
                "integration": PluginType.INTEGRATION,
                "ui": PluginType.UI,
            }
            plugin_type = type_map.get(args.type)

        # Get filtered plugins
        plugins = registry.list_plugins(
            plugin_type=plugin_type,
            enabled_only=args.enabled_only,
        )

        # Display results
        if not plugins:
            if _wants_json(args):
                _emit_json({"success": True, "plugins": []})
                return 0
            print("No plugins found.")
            return 0

        if _wants_json(args):
            _emit_json(
                {
                    "success": True,
                    "plugins": [
                        _plugin_to_json(plugin, registry) for plugin in plugins
                    ],
                }
            )
            return 0

        # Calculate column widths
        max_name_len = max(len(p.name) for p in plugins)
        max_type_len = max(len(p.plugin_type.value) for p in plugins)
        name_width = max(max_name_len, 20)  # Minimum width for header
        type_width = max(max_type_len, 12)  # Minimum width for header

        # Print header
        print(
            f"{'Name':<{name_width}}  {'Type':<{type_width}}  {'Version':<10}  {'Status':<10}  {'Description'}"
        )
        print("-" * (name_width + type_width + 10 + 10 + 40))

        # Print plugins
        for plugin in plugins:
            status = "enabled" if plugin.is_enabled else "disabled"
            print(
                f"{plugin.name:<{name_width}}  "
                f"{plugin.plugin_type.value:<{type_width}}  "
                f"{plugin.version:<10}  "
                f"{status:<10}  "
                f"{plugin.metadata.description}"
            )

        # Print summary
        print(f"\nTotal: {len(plugins)} plugin(s)")
        if args.enabled_only:
            print("Showing enabled plugins only")
        elif args.type != "all":
            print(f"Showing {args.type} plugins only")

        return 0

    except Exception as e:
        logger.error(f"Failed to list plugins: {e}")
        return 1


def cmd_enable(args: argparse.Namespace) -> int:
    """
    Enable a plugin.

    Args:
        args: Parsed command-line arguments

    Returns:
        0 on success, 1 on error
    """
    try:
        # Get plugin registry instance
        registry = PluginRegistry.get_instance()

        # Ensure plugins are loaded
        if not registry.list_plugins():
            logger.info("Loading plugins...")
            registry.load_all_plugins()

        # Check if plugin exists
        plugin = registry.get_plugin(args.plugin_name)
        if plugin is None:
            logger.error(f"Plugin not found: {args.plugin_name}")
            return 1

        # Enable plugin
        registry.enable_plugin(args.plugin_name)

        # Confirm success
        permission_diff = _permission_diff_for_plugin(plugin)
        if _wants_json(args):
            _emit_json(
                {
                    "success": True,
                    "plugin_name": args.plugin_name,
                    "permission_diff": permission_diff,
                }
            )
            return 0
        print(f"Plugin '{args.plugin_name}' enabled successfully")
        if permission_diff["required_permissions"]:
            print(
                "  Permissions: " + ", ".join(permission_diff["required_permissions"])
            )
        if permission_diff["capabilities"]:
            print("  Capabilities: " + ", ".join(permission_diff["capabilities"]))
        return 0

    except KeyError as e:
        logger.error(f"Plugin not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"Failed to enable plugin '{args.plugin_name}': {e}")
        return 1


def cmd_disable(args: argparse.Namespace) -> int:
    """
    Disable a plugin.

    Args:
        args: Parsed command-line arguments

    Returns:
        0 on success, 1 on error
    """
    try:
        # Get plugin registry instance
        registry = PluginRegistry.get_instance()

        # Ensure plugins are loaded
        if not registry.list_plugins():
            logger.info("Loading plugins...")
            registry.load_all_plugins()

        # Check if plugin exists
        plugin = registry.get_plugin(args.plugin_name)
        if plugin is None:
            logger.error(f"Plugin not found: {args.plugin_name}")
            return 1

        # Disable plugin
        registry.disable_plugin(args.plugin_name)

        # Confirm success
        if _wants_json(args):
            _emit_json({"success": True, "plugin_name": args.plugin_name})
            return 0
        print(f"Plugin '{args.plugin_name}' disabled successfully")
        return 0

    except KeyError as e:
        logger.error(f"Plugin not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"Failed to disable plugin '{args.plugin_name}': {e}")
        return 1


def cmd_install(args: argparse.Namespace) -> int:
    """
    Install a plugin from local path or remote URL.

    Args:
        args: Parsed command-line arguments

    Returns:
        0 on success, 1 on error
    """
    json_output = _wants_json(args)

    # Handle local path installation
    if args.path:
        return _install_from_path(args.path, args.force, args.dry_run, json_output)

    # Handle remote URL installation
    if args.url:
        return _install_from_url(args.url, args.force, args.dry_run, json_output)

    logger.error("Either --path or --url must be specified")
    return 1


def _resolve_plugin_source(source_path: str) -> Path | None:
    """Resolve and validate the local plugin source directory."""
    source_dir = Path(source_path).resolve()
    if not source_dir.exists():
        logger.error(f"Source path not found: {source_path}")
        return None
    if not source_dir.is_dir():
        logger.error(f"Source path is not a directory: {source_path}")
        return None
    return source_dir


def _load_plugin_metadata(loader: PluginLoader, source_dir: Path):
    """Load plugin metadata and emit a user-facing validation error on failure."""
    try:
        metadata = loader._load_metadata(source_dir)
    except PluginValidationError as e:
        logger.error(f"Invalid plugin: {e}")
        return None

    logger.info(f"Found plugin: {metadata.name} v{metadata.version}")
    return metadata


def _print_security_warnings(warnings: list[str], json_output: bool) -> None:
    """Show local security warnings for human CLI callers."""
    if not warnings or json_output:
        return

    print("\n⚠️  Security warnings detected:")
    print("=" * 60)
    for warning in warnings:
        print(f"  • {warning}")
    print("=" * 60)
    print("\nNote: Plugin has security warnings but is not blocked.")
    print("Review the warnings above before enabling this plugin.\n")


def _log_blocking_security_failure(warnings: list[str]) -> None:
    logger.error(
        "\n❌ Plugin failed security validation and cannot be installed.\n"
        "Security issues detected:\n" + "\n".join(f"  - {w}" for w in warnings)
    )


def _emit_install_dry_run(
    metadata,
    source_dir: Path,
    target_dir: Path,
    warnings: list[str],
    json_output: bool,
) -> None:
    if json_output:
        _emit_json(
            {
                "success": True,
                "dry_run": True,
                "plugin": metadata.to_dict(),
                "target": str(target_dir),
                "warnings": warnings,
            }
        )
        return

    print(f"[DRY RUN] Would install plugin: {metadata.name} v{metadata.version}")
    print(f"  Source: {source_dir}")
    print(f"  Target: {target_dir}")
    print(f"  Description: {metadata.description}")


def _prepare_plugin_target(target_dir: Path, plugin_name: str, force: bool) -> bool:
    if not target_dir.exists():
        return True
    if not force:
        logger.error(
            f"Plugin '{plugin_name}' already installed at {target_dir}. "
            "Use --force to overwrite."
        )
        return False

    logger.warning(f"Removing existing plugin: {target_dir}")
    shutil.rmtree(target_dir)
    return True


def _copy_plugin_files(source_dir: Path, target_dir: Path) -> bool:
    logger.info(f"Installing to: {target_dir}")
    try:
        shutil.copytree(source_dir, target_dir)
    except Exception:
        logger.exception("Failed to copy plugin")
        return False

    logger.info(f"Copied plugin files to: {target_dir}")
    return True


def _validate_installed_plugin(
    loader: PluginLoader, target_dir: Path, expected_name: str
) -> bool:
    try:
        installed_metadata = loader._load_metadata(target_dir)
    except PluginValidationError as e:
        logger.error(f"Validation failed after installation: {e}")
        shutil.rmtree(target_dir)
        return False

    if installed_metadata.name == expected_name:
        return True

    logger.error("Plugin name mismatch after installation")
    shutil.rmtree(target_dir)
    return False


def _emit_install_success(
    metadata, target_dir: Path, warnings: list[str], json_output: bool
) -> None:
    if json_output:
        _emit_json(
            {
                "success": True,
                "plugin": metadata.to_dict(),
                "target": str(target_dir),
                "warnings": warnings,
            }
        )
        return

    print(f"✓ Plugin '{metadata.name}' v{metadata.version} installed successfully")
    print(f"  Location: {target_dir}")
    print(f"  Description: {metadata.description}")
    print(f"\nEnable the plugin with: python plugins/cli.py enable {metadata.name}")


def _install_from_path(
    source_path: str,
    force: bool,
    dry_run: bool = False,
    json_output: bool = False,
) -> int:
    """
    Install a plugin from a local directory path.

    Validates the plugin, copies it to the user plugins directory,
    and confirms successful installation.

    Args:
        source_path: Path to plugin directory
        force: If True, overwrite existing plugin

    Returns:
        0 on success, 1 on error
    """
    try:
        source_dir = _resolve_plugin_source(source_path)
        if source_dir is None:
            return 1

        logger.info(f"Installing plugin from: {source_dir}")
        loader = PluginLoader()
        metadata = _load_plugin_metadata(loader, source_dir)
        if metadata is None:
            return 1

        logger.info("Performing security validation...")
        is_safe, warnings = loader.validate_plugin_security(source_dir)
        _print_security_warnings(warnings, json_output)

        if not is_safe:
            _log_blocking_security_failure(warnings)
            return 1

        target_dir = loader.user_plugins_dir / metadata.name

        if dry_run:
            _emit_install_dry_run(
                metadata, source_dir, target_dir, warnings, json_output
            )
            return 0

        if not _prepare_plugin_target(target_dir, metadata.name, force):
            return 1

        if not _copy_plugin_files(source_dir, target_dir):
            return 1

        if not _validate_installed_plugin(loader, target_dir, metadata.name):
            return 1

        _emit_install_success(metadata, target_dir, warnings, json_output)
        return 0

    except PluginLoadError as e:
        logger.error(f"Failed to load plugin: {e}")
        return 1
    except Exception:
        logger.exception("Installation failed")
        return 1


def _install_from_url(
    git_url: str,
    force: bool,
    dry_run: bool = False,
    json_output: bool = False,
) -> int:
    """
    Install a plugin from a remote git repository.

    Clones the repository to a temporary directory, validates it,
    and installs it to the user plugins directory.

    Args:
        git_url: Git URL to clone from
        force: If True, overwrite existing plugin
        dry_run: If True, validate without installing

    Returns:
        0 on success, 1 on error
    """
    temp_dir = None
    try:
        # Create temporary directory for cloning
        temp_dir = Path(tempfile.mkdtemp(prefix="plugin_install_"))
        logger.info(f"Cloning plugin from: {git_url}")

        # Clone the repository
        result = run_git(
            ["clone", git_url, str(temp_dir)],
            timeout=120,  # 2 minutes for clone operation
        )

        if result.returncode != 0:
            logger.error(f"Failed to clone repository: {result.stderr}")
            return 1

        logger.info("Repository cloned successfully")

        # Install from the cloned directory
        return _install_from_path(str(temp_dir), force, dry_run, json_output)

    except Exception:
        logger.exception("Installation from URL failed")
        return 1
    finally:
        # Clean up temporary directory
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory: {e}")


def cmd_info(args: argparse.Namespace) -> int:
    """Show plugin information."""
    try:
        registry = PluginRegistry.get_instance()
        if not registry.list_plugins():
            registry.load_all_plugins()

        plugin = registry.get_plugin(args.plugin_name)
        if plugin is None:
            logger.error(f"Plugin not found: {args.plugin_name}")
            return 1

        payload = _plugin_to_json(plugin, registry)
        if _wants_json(args):
            _emit_json({"success": True, "plugin": payload})
        else:
            metadata = payload["metadata"]
            print(f"Name: {metadata['name']}")
            print(f"Version: {metadata['version']}")
            print(f"Type: {metadata['plugin_type']}")
            print(f"Status: {payload['status']}")
            print(f"Description: {metadata['description']}")
        return 0
    except Exception:
        logger.exception("Failed to show plugin '%s'", args.plugin_name)
        return 1


def cmd_uninstall(args: argparse.Namespace) -> int:
    """Uninstall a user plugin."""
    try:
        registry = PluginRegistry.get_instance()
        if not registry.list_plugins():
            registry.load_all_plugins()

        plugin = registry.get_plugin(args.plugin_name)
        if plugin is None:
            logger.error(f"Plugin not found: {args.plugin_name}")
            return 1

        target_dir = registry.loader.user_plugins_dir / args.plugin_name
        if not target_dir.exists():
            logger.error(
                f"Plugin '{args.plugin_name}' is not installed as a user plugin"
            )
            return 1

        registry.unload_plugin(args.plugin_name)
        shutil.rmtree(target_dir)

        if _wants_json(args):
            _emit_json({"success": True, "plugin_name": args.plugin_name})
        else:
            print(f"Plugin '{args.plugin_name}' uninstalled successfully")
        return 0
    except Exception:
        logger.exception("Failed to uninstall plugin '%s'", args.plugin_name)
        return 1


def _iter_plugin_candidate_dirs(loader: PluginLoader):
    """Yield plugin candidate directories without importing plugin code."""
    roots = [
        ("system", loader.system_plugins_dir),
        ("user", loader.user_plugins_dir),
    ]
    for source, root_dir in roots:
        if not root_dir.exists():
            continue
        for plugin_dir in sorted(root_dir.iterdir(), key=lambda path: path.name):
            if plugin_dir.is_dir():
                yield source, plugin_dir


def _diagnostic_issue(
    severity: str,
    code: str,
    message: str,
    plugin_dir: Path | None = None,
    plugin_name: str | None = None,
    source: str | None = None,
    details: dict | None = None,
) -> dict:
    """Create a stable machine-readable diagnostic issue."""
    issue = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if plugin_dir is not None:
        issue["plugin_dir"] = str(plugin_dir)
    if plugin_name is not None:
        issue["plugin_name"] = plugin_name
    if source is not None:
        issue["source"] = source
    if details:
        issue["details"] = details
    return issue


def _inspect_plugin_dir(
    loader: PluginLoader,
    source: str,
    plugin_dir: Path,
) -> tuple[dict | None, list[dict]]:
    """Inspect one plugin directory through manifest and static security checks."""
    try:
        metadata = loader._load_metadata(plugin_dir)
    except PluginValidationError as e:
        return None, [
            _diagnostic_issue(
                "error",
                "invalid_manifest",
                str(e),
                plugin_dir=plugin_dir,
                source=source,
            )
        ]

    is_safe, warnings = loader.validate_plugin_security(plugin_dir)
    security_issues = [
        _diagnostic_issue(
            "error" if not is_safe else "warning",
            "security_warning",
            warning,
            plugin_dir=plugin_dir,
            plugin_name=metadata.name,
            source=source,
        )
        for warning in warnings
    ]
    entry = {
        "name": metadata.name,
        "version": metadata.version,
        "plugin_type": metadata.plugin_type.value,
        "source": source,
        "plugin_dir": str(plugin_dir),
        "manifest_status": "valid",
        "metadata": metadata.to_dict(),
        "security": {
            "safe": is_safe,
            "warnings": warnings,
        },
        "issues": security_issues,
    }
    return entry, security_issues


def _duplicate_plugin_issues(plugins: list[dict]) -> list[dict]:
    """Return duplicate-name diagnostics for discovered plugin manifests."""
    by_name: dict[str, list[dict]] = {}
    for plugin in plugins:
        by_name.setdefault(plugin["name"], []).append(plugin)

    issues = []
    for name, matches in sorted(by_name.items()):
        if len(matches) < 2:
            continue
        issues.append(
            _diagnostic_issue(
                "warning",
                "duplicate_plugin_name",
                f"Multiple plugin manifests declare '{name}'",
                plugin_name=name,
                details={
                    "plugin_dirs": [plugin["plugin_dir"] for plugin in matches],
                    "sources": [plugin["source"] for plugin in matches],
                },
            )
        )
    return issues


def _build_plugin_diagnostics(loader: PluginLoader) -> dict:
    """Build plugin diagnostics without executing plugin implementation modules."""
    plugins: list[dict] = []
    issues: list[dict] = []
    invalid_plugins = 0

    for source, plugin_dir in _iter_plugin_candidate_dirs(loader):
        plugin, plugin_issues = _inspect_plugin_dir(loader, source, plugin_dir)
        if plugin is None:
            invalid_plugins += 1
            issues.extend(plugin_issues)
            continue
        plugins.append(plugin)
        issues.extend(plugin_issues)

    duplicate_issues = _duplicate_plugin_issues(plugins)
    issues.extend(duplicate_issues)

    return {
        "directories": {
            "user_plugins_dir": str(loader.user_plugins_dir),
            "system_plugins_dir": str(loader.system_plugins_dir),
        },
        "summary": {
            "total_entries": len(plugins) + invalid_plugins,
            "valid_plugins": len(plugins),
            "invalid_plugins": invalid_plugins,
            "security_warnings": sum(
                1 for plugin in plugins if plugin["security"]["warnings"]
            ),
            "duplicate_names": len(duplicate_issues),
        },
        "plugins": plugins,
        "issues": issues,
    }


def cmd_health(args: argparse.Namespace) -> int:
    """Inspect plugin directories, manifests, and static security diagnostics."""
    try:
        loader = PluginLoader()
        diagnostics = _build_plugin_diagnostics(loader)

        if _wants_json(args):
            _emit_json({"success": True, "diagnostics": diagnostics})
            return 0

        summary = diagnostics["summary"]
        print("Plugin health")
        print(f"  Valid plugins: {summary['valid_plugins']}")
        print(f"  Invalid plugins: {summary['invalid_plugins']}")
        print(f"  Security warnings: {summary['security_warnings']}")
        print(f"  Duplicate names: {summary['duplicate_names']}")
        return 0
    except Exception:
        logger.exception("Failed to inspect plugin health")
        return 1


def _load_registry_with_plugins() -> PluginRegistry:
    """Return a registry with plugins loaded."""
    registry = PluginRegistry.get_instance()
    if not registry.list_plugins():
        registry.load_all_plugins()
    return registry


def cmd_permission_diff(args: argparse.Namespace) -> int:
    """Show permission and capability diff for a plugin."""
    try:
        registry = _load_registry_with_plugins()
        plugin = registry.get_plugin(args.plugin_name)
        if plugin is None:
            logger.error(f"Plugin not found: {args.plugin_name}")
            return 1

        permission_diff = _permission_diff_for_plugin(plugin)
        if _wants_json(args):
            _emit_json({"success": True, "permission_diff": permission_diff})
            return 0

        print(f"Plugin: {args.plugin_name}")
        print(
            "Permissions: "
            + (", ".join(permission_diff["required_permissions"]) or "none")
        )
        print("Capabilities: " + (", ".join(permission_diff["capabilities"]) or "none"))
        print(f"Currently enabled: {permission_diff['currently_enabled']}")
        return 0
    except Exception:
        logger.exception("Failed to inspect plugin permission diff")
        return 1


def _parse_trace_line(line: str, source: str) -> dict | None:
    """Parse one plugin trace JSONL record."""
    stripped = line.strip()
    if not stripped:
        return None

    try:
        event = json.loads(stripped)
    except json.JSONDecodeError:
        event = {"raw": stripped}
    if not isinstance(event, dict):
        event = {"value": event}
    event.setdefault("source", source)
    return event


def _iter_trace_file_events(
    path: Path,
    *,
    plugin_name: str | None = None,
    limit: int | None = None,
) -> Iterator[dict]:
    """Yield recent trace events from one JSONL file, newest first."""
    maxlen = limit if limit is not None and limit > 0 else None
    recent_events: deque[dict] = deque(maxlen=maxlen)
    with path.open(encoding="utf-8") as trace_file:
        for line in trace_file:
            event = _parse_trace_line(line, path.name)
            if event is None:
                continue
            if plugin_name is not None and event.get("plugin") != plugin_name:
                continue
            recent_events.append(event)

    while recent_events:
        yield recent_events.pop()


def _trace_events(trace_dir: Path, plugin_name: str | None, limit: int) -> list[dict]:
    """Read JSONL trace events from project plugin trace files."""
    if not trace_dir.exists():
        return []

    safe_limit = max(0, min(int(limit), 500))
    if safe_limit == 0:
        return []

    events: list[dict] = []
    for path in sorted(trace_dir.glob("*.jsonl"), reverse=True):
        remaining = safe_limit - len(events)
        if remaining <= 0:
            break
        for event in _iter_trace_file_events(
            path,
            plugin_name=plugin_name,
            limit=remaining,
        ):
            events.append(event)
            if len(events) >= safe_limit:
                return list(reversed(events))

    return list(reversed(events))


def cmd_traces(args: argparse.Namespace) -> int:
    """Read recent project plugin trace events."""
    try:
        trace_dir = Path.cwd() / ".auto-claude" / "plugin_traces"
        traces = _trace_events(trace_dir, args.plugin, args.limit)
        payload = {
            "success": True,
            "trace_dir": str(trace_dir),
            "plugin": args.plugin,
            "traces": traces,
        }
        if _wants_json(args):
            _emit_json(payload)
            return 0

        for event in traces:
            print(json.dumps(event, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception:
        logger.exception("Failed to read plugin traces")
        return 1


def cmd_preview_context(args: argparse.Namespace) -> int:
    """Preview enabled agent plugin prompt augmentations."""
    try:
        from plugins.runtime import (
            append_prompt_augmentations,
            build_agent_context,
            collect_prompt_augmentations,
            load_enabled_runtime_plugins,
        )

        project_dir = Path.cwd()
        plugins = load_enabled_runtime_plugins(project_dir)
        spec_dir = (
            Path(args.spec_dir)
            if args.spec_dir
            else project_dir / ".auto-claude" / "plugin-preview"
        )
        metadata = {
            "agent_type": args.agent_type,
            "task": args.task,
            "files": list(args.files or []),
        }
        context = build_agent_context(
            project_dir=project_dir,
            spec_dir=spec_dir,
            agent_type=args.agent_type,
            metadata=metadata,
        )
        contributions = collect_prompt_augmentations(plugins, context)
        preview = append_prompt_augmentations("", contributions).strip()
        payload = {
            "success": True,
            "agent_type": args.agent_type,
            "spec_dir": str(spec_dir),
            "contributions": [
                {
                    "plugin_name": contribution.plugin_name,
                    "capabilities": contribution.capabilities,
                    "text": contribution.text,
                }
                for contribution in contributions
            ],
            "preview": preview,
        }

        if _wants_json(args):
            _emit_json(payload)
            return 0

        print(preview)
        return 0
    except Exception:
        logger.exception("Failed to preview plugin runtime context")
        return 1


def main() -> int:
    """Main entry point for plugin CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Map commands to handler functions
    commands = {
        "list": cmd_list,
        "enable": cmd_enable,
        "disable": cmd_disable,
        "install": cmd_install,
        "info": cmd_info,
        "uninstall": cmd_uninstall,
        "health": cmd_health,
        "permission-diff": cmd_permission_diff,
        "traces": cmd_traces,
        "preview-context": cmd_preview_context,
    }

    # Execute command
    handler = commands.get(args.command)
    if handler:
        return handler(args)

    # Should not reach here due to argparse validation
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
