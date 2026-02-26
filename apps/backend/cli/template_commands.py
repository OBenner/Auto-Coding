"""
Template Commands
=================

CLI commands for managing agent templates (list, test, validate).
"""

import argparse
import json
import sys
from pathlib import Path

from agents.templates.models import AgentTemplate
from agents.templates.storage import load_template, load_templates
from agents.templates.validator import validate_template


def list_templates_command(project_dir: Path, format: str = "table") -> None:
    """
    List all custom agent templates.

    Args:
        project_dir: Project root directory
        format: Output format ('table' or 'json')
    """
    templates = load_templates(project_dir)

    if not templates:
        if format == "json":
            print(json.dumps({"templates": [], "count": 0}))
        else:
            print("\nNo custom templates found.")
            print(
                "\nCreate your first template using the UI or by creating a JSON file"
            )
            print("in .auto-claude/templates/")
        return

    if format == "json":
        # JSON output for programmatic use
        output = {
            "templates": [t.to_dict() for t in templates],
            "count": len(templates),
        }
        print(json.dumps(output, indent=2))
    else:
        # Table output for human consumption
        print("\n" + "=" * 80)
        print("  CUSTOM AGENT TEMPLATES")
        print("=" * 80)
        print()

        # Group by category
        categories: dict[str, list[AgentTemplate]] = {}
        for template in templates:
            cat = template.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(template)

        # Print templates grouped by category
        for cat_name, cat_templates in sorted(categories.items()):
            print(f"  {cat_name}")
            print(f"  {'-' * 80}")

            for template in sorted(cat_templates, key=lambda t: t.name):
                version_str = f"v{template.version}" if template.version else ""
                author_str = f" by {template.author}" if template.author else ""

                print(f"    • {template.name} {version_str}{author_str}")
                if template.description:
                    # Wrap description if too long
                    desc = template.description
                    if len(desc) > 68:
                        desc = desc[:68] + "..."
                    print(f"      {desc}")

                # Show tools and MCP servers
                tool_count = len(template.tools)
                mcp_count = len(template.mcp_servers)
                info_parts = []
                if tool_count:
                    info_parts.append(f"{tool_count} tool(s)")
                if mcp_count:
                    info_parts.append(f"{mcp_count} MCP server(s)")
                if template.tags:
                    info_parts.append(f"Tags: {', '.join(template.tags)}")

                if info_parts:
                    print(f"      {' | '.join(info_parts)}")
                print()

        print("-" * 80)
        print()
        print(f"Total: {len(templates)} template(s)")
        print()


def validate_template_command(
    project_dir: Path, template_name: str, strict: bool = True
) -> None:
    """
    Validate a template for security and correctness.

    Args:
        project_dir: Project root directory
        template_name: Name of the template to validate
        strict: If True, fail on warnings. If False, allow warnings.
    """
    # Load template from disk
    template = load_template(template_name, project_dir)

    if not template:
        print(f"\n✗ Template not found: {template_name}")
        print(f"\nLooked in: {project_dir / '.auto-claude' / 'templates'}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print(f"  VALIDATING TEMPLATE: {template_name}")
    print("=" * 80)
    print()

    # Run validation
    is_valid, errors = validate_template(template, strict=strict)

    if is_valid:
        print("✓ Template is valid!")
        print()

        # Show summary
        print("Summary:")
        print(f"  Name: {template.name}")
        print(f"  Version: {template.version}")
        print(f"  Category: {template.category}")
        print(f"  Tools: {len(template.tools)}")
        print(f"  MCP Servers: {len(template.mcp_servers)}")
        print(f"  Thinking Level: {template.thinking_level}")
        print()

        # Show tool list
        if template.tools:
            print(f"  Tools enabled: {', '.join(sorted(template.tools))}")
            print()

        # Show MCP servers
        if template.mcp_servers:
            print(f"  MCP servers: {', '.join(sorted(template.mcp_servers))}")
            print()

        print("-" * 80)
        print()
        sys.exit(0)
    else:
        print("✗ Template validation failed!")
        print()

        # Show errors
        print("Errors:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        print()

        print("-" * 80)
        print()
        sys.exit(1)


def test_template_command(
    project_dir: Path, template_name: str, test_prompt: str | None = None
) -> None:
    """
    Test a template by creating a dry-run agent session.

    Args:
        project_dir: Project root directory
        template_name: Name of the template to test
        test_prompt: Optional test prompt (if not provided, will use interactive mode)
    """
    # Load template from disk
    template = load_template(template_name, project_dir)

    if not template:
        print(f"\n✗ Template not found: {template_name}")
        print(f"\nLooked in: {project_dir / '.auto-claude' / 'templates'}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print(f"  TESTING TEMPLATE: {template_name}")
    print("=" * 80)
    print()

    # Validate first
    is_valid, errors = validate_template(template, strict=False)
    if not is_valid:
        print("✗ Template validation failed! Cannot test invalid template.")
        print()
        print("Errors:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        print()
        print("Fix these errors before testing.")
        print()
        sys.exit(1)

    print("✓ Template passed validation")
    print()

    # Show template configuration
    print("Template Configuration:")
    print(f"  Name: {template.name}")
    print(f"  Description: {template.description}")
    print(f"  Category: {template.category}")
    print(f"  Version: {template.version}")
    print(f"  Thinking Level: {template.thinking_level}")
    print()

    if template.tools:
        print(f"  Tools: {', '.join(sorted(template.tools))}")
        print()

    if template.mcp_servers:
        print(f"  MCP Servers: {', '.join(sorted(template.mcp_servers))}")
        print()

    if template.custom_prompt:
        prompt_preview = template.custom_prompt[:200]
        if len(template.custom_prompt) > 200:
            prompt_preview += "..."
        print("  Custom Prompt Preview:")
        for line in prompt_preview.split("\n"):
            print(f"    {line}")
        print()

    # Get test prompt if not provided
    if not test_prompt:
        print("Enter a test prompt for the agent (or press Ctrl+C to cancel):")
        print()
        try:
            test_prompt = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nCancelled.")
            sys.exit(0)

        if not test_prompt:
            print("\nNo test prompt provided. Exiting.")
            sys.exit(0)

    print("-" * 80)
    print()
    print("NOTE: Full template testing with agent session requires integration")
    print("      with the agent execution system. This command validates the")
    print("      template configuration and shows what would be used.")
    print()
    print("To use this template in a real build:")
    print(f"  1. Select '{template.name}' in the UI task creation wizard")
    print(
        f"  2. Or use it programmatically via create_client(template='{template.name}')"
    )
    print()
    print("-" * 80)
    print()


def show_template_info_command(project_dir: Path, template_name: str) -> None:
    """
    Show detailed information about a specific template.

    Args:
        project_dir: Project root directory
        template_name: Name of the template to show
    """
    template = load_template(template_name, project_dir)

    if not template:
        print(f"\n✗ Template not found: {template_name}")
        print(f"\nLooked in: {project_dir / '.auto-claude' / 'templates'}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print(f"  TEMPLATE: {template.name}")
    print("=" * 80)
    print()

    # Basic info
    print(f"Name: {template.name}")
    print(f"Description: {template.description}")
    print(f"Category: {template.category}")
    print(f"Version: {template.version}")
    print()

    if template.author:
        print(f"Author: {template.author}")
        print()

    if template.tags:
        print(f"Tags: {', '.join(template.tags)}")
        print()

    # Configuration
    print("Configuration:")
    print(f"  Thinking Level: {template.thinking_level}")
    print(f"  Tools: {len(template.tools)}")
    if template.tools:
        for tool in sorted(template.tools):
            print(f"    - {tool}")
    print()

    print(f"  MCP Servers: {len(template.mcp_servers)}")
    if template.mcp_servers:
        for server in sorted(template.mcp_servers):
            print(f"    - {server}")
    print()

    # Custom prompt
    if template.custom_prompt:
        print("Custom Prompt:")
        print("-" * 80)
        print(template.custom_prompt)
        print("-" * 80)
        print()
    else:
        print("Custom Prompt: (none - uses default agent behavior)")
        print()

    # Parameters
    if template.parameters:
        print("Parameters:")
        for param_name, param_value in template.parameters.items():
            print(f"  {param_name}: {param_value}")
        print()

    # Metadata
    print("Metadata:")
    print(f"  Created: {template.created_at}")
    print(f"  Updated: {template.updated_at}")
    print()

    print("-" * 80)
    print()


def _ensure_backend_in_path() -> None:
    """Add the backend directory to sys.path if not already present."""
    _parent_dir = str(Path(__file__).parent.parent)
    if _parent_dir not in sys.path:
        sys.path.insert(0, _parent_dir)


def main():
    """Main entry point for template CLI commands."""
    _ensure_backend_in_path()

    parser = argparse.ArgumentParser(
        description="Manage custom agent templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all templates
  python template_commands.py list

  # List templates in JSON format
  python template_commands.py list --format json

  # Validate a template
  python template_commands.py validate my-template

  # Test a template
  python template_commands.py test my-template

  # Show template details
  python template_commands.py info my-template
        """,
    )

    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List command
    list_parser = subparsers.add_parser("list", help="List all templates")
    list_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate a template for security and correctness"
    )
    validate_parser.add_argument("template_name", help="Template name to validate")
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Fail on warnings (default: true)",
    )
    validate_parser.add_argument(
        "--no-strict",
        dest="strict",
        action="store_false",
        help="Allow warnings",
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Test a template with dry-run")
    test_parser.add_argument("template_name", help="Template name to test")
    test_parser.add_argument(
        "--prompt",
        help="Test prompt (if not provided, will prompt interactively)",
    )

    # Info command
    info_parser = subparsers.add_parser(
        "info", help="Show detailed information about a template"
    )
    info_parser.add_argument("template_name", help="Template name to show")

    args = parser.parse_args()

    # Show help if no command specified
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Execute command
    project_dir = args.project_dir.resolve()

    if args.command == "list":
        list_templates_command(project_dir, format=args.format)
    elif args.command == "validate":
        validate_template_command(project_dir, args.template_name, strict=args.strict)
    elif args.command == "test":
        test_template_command(project_dir, args.template_name, test_prompt=args.prompt)
    elif args.command == "info":
        show_template_info_command(project_dir, args.template_name)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
