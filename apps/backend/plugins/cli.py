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
import sys
from pathlib import Path

# Handle both direct execution and module import
try:
    from .base import PluginType
    from .registry import PluginRegistry
except ImportError:
    from base import PluginType
    from registry import PluginRegistry

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
    """Enable a plugin (placeholder)."""
    print(f"Enable command for '{args.plugin_name}' - to be implemented in subtask-1-3")
    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    """Disable a plugin (placeholder)."""
    print(f"Disable command for '{args.plugin_name}' - to be implemented in subtask-1-3")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    """Install a plugin (placeholder)."""
    if args.path:
        print(f"Install from path '{args.path}' - to be implemented in subtask-1-4")
    else:
        print(f"Install from URL '{args.url}' - to be implemented in phase-3")
    return 0


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
