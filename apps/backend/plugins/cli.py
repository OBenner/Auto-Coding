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
import logging
import shutil
import sys
import tempfile
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

    # Install command
    install_parser = subparsers.add_parser(
        "install",
        help="Install a plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    install_source = install_parser.add_mutually_exclusive_group(required=True)
    install_source.add_argument(
        "--path",
        help="Local path to plugin directory",
    )
    install_source.add_argument(
        "--url",
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
            print("No plugins found.")
            return 0

        # Calculate column widths
        max_name_len = max(len(p.name) for p in plugins)
        max_type_len = max(len(p.plugin_type.value) for p in plugins)
        name_width = max(max_name_len, 20)  # Minimum width for header
        type_width = max(max_type_len, 12)  # Minimum width for header

        # Print header
        print(f"{'Name':<{name_width}}  {'Type':<{type_width}}  {'Version':<10}  {'Status':<10}  {'Description'}")
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
        print(f"Plugin '{args.plugin_name}' enabled successfully")
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
    # Handle local path installation
    if args.path:
        return _install_from_path(args.path, args.force, args.dry_run)

    # Handle remote URL installation
    if args.url:
        return _install_from_url(args.url, args.force, args.dry_run)

    logger.error("Either --path or --url must be specified")
    return 1


def _install_from_path(source_path: str, force: bool, dry_run: bool = False) -> int:
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
        # Resolve source path
        source_dir = Path(source_path).resolve()

        # Verify source directory exists
        if not source_dir.exists():
            logger.error(f"Source path not found: {source_path}")
            return 1

        if not source_dir.is_dir():
            logger.error(f"Source path is not a directory: {source_path}")
            return 1

        logger.info(f"Installing plugin from: {source_dir}")

        # Create loader to validate plugin and get user plugins directory
        loader = PluginLoader()

        # Validate plugin by loading metadata
        try:
            metadata = loader._load_metadata(source_dir)
            logger.info(f"Found plugin: {metadata.name} v{metadata.version}")
        except PluginValidationError as e:
            logger.error(f"Invalid plugin: {e}")
            return 1

        # Determine target directory
        target_dir = loader.user_plugins_dir / metadata.name

        # Dry run mode - stop here
        if dry_run:
            print(f"[DRY RUN] Would install plugin: {metadata.name} v{metadata.version}")
            print(f"  Source: {source_dir}")
            print(f"  Target: {target_dir}")
            print(f"  Description: {metadata.description}")
            return 0

        # Check if plugin already exists
        if target_dir.exists():
            if not force:
                logger.error(
                    f"Plugin '{metadata.name}' already installed at {target_dir}. "
                    "Use --force to overwrite."
                )
                return 1
            logger.warning(f"Removing existing plugin: {target_dir}")
            shutil.rmtree(target_dir)

        # Copy plugin to user plugins directory
        logger.info(f"Installing to: {target_dir}")
        try:
            shutil.copytree(source_dir, target_dir)
            logger.info(f"Copied plugin files to: {target_dir}")
        except Exception as e:
            logger.error(f"Failed to copy plugin: {e}")
            return 1

        # Validate the installed plugin
        try:
            installed_metadata = loader._load_metadata(target_dir)
            if installed_metadata.name != metadata.name:
                logger.error("Plugin name mismatch after installation")
                shutil.rmtree(target_dir)
                return 1
        except PluginValidationError as e:
            logger.error(f"Validation failed after installation: {e}")
            shutil.rmtree(target_dir)
            return 1

        # Success
        print(f"✓ Plugin '{metadata.name}' v{metadata.version} installed successfully")
        print(f"  Location: {target_dir}")
        print(f"  Description: {metadata.description}")
        print(f"\nEnable the plugin with: python plugins/cli.py enable {metadata.name}")

        return 0

    except PluginLoadError as e:
        logger.error(f"Failed to load plugin: {e}")
        return 1
    except Exception as e:
        logger.error(f"Installation failed: {e}")
        return 1


def _install_from_url(git_url: str, force: bool, dry_run: bool = False) -> int:
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
        return _install_from_path(str(temp_dir), force, dry_run)

    except Exception as e:
        logger.error(f"Installation from URL failed: {e}")
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
    """Show plugin information (placeholder)."""
    print(f"Info command for '{args.plugin_name}' - to be implemented")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    """Uninstall a plugin (placeholder)."""
    print(f"Uninstall command for '{args.plugin_name}' - to be implemented")
    return 0


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
