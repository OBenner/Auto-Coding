"""
Prompt Loader Module
====================

Provides generic agent prompt loading functionality.
"""

from pathlib import Path

# Directory containing prompt files
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def get_agent_prompt(agent_name: str) -> str:
    """
    Load a prompt file for a specific agent.

    Args:
        agent_name: Name of the agent (e.g., "test_generator", "coder", "planner")

    Returns:
        The prompt content as a string

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    prompt_file = PROMPTS_DIR / f"{agent_name}.md"

    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_file}\n"
            f"Make sure prompts/{agent_name}.md exists."
        )

    return prompt_file.read_text(encoding="utf-8")


def get_prompt_with_context(agent_name: str, context: dict) -> str:
    """
    Load a prompt and inject context variables.

    Args:
        agent_name: Name of the agent
        context: Dictionary of variables to inject (e.g., {"spec_dir": "/path/to/spec"})

    Returns:
        The prompt content with context variables replaced
    """
    prompt = get_agent_prompt(agent_name)

    # Replace {{variable}} placeholders with context values
    for key, value in context.items():
        placeholder = "{{" + key + "}}"
        prompt = prompt.replace(placeholder, str(value))

    return prompt
