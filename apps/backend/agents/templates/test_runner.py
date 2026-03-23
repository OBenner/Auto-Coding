"""
Template Test Runner
===================

Test runner for validating custom agent templates.

Runs a dry-run test session with a custom template to verify:
- Template configuration is valid
- Client can be created with template settings
- Agent can process a test prompt successfully
- Tools and MCP servers are accessible

This allows users to test templates before publishing them.
"""

import logging
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeSDKClient
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from ui import (
    print_key_value,
    print_status,
)

from .models import AgentTemplate
from .validator import validate_template

logger = logging.getLogger(__name__)


# =============================================================================
# Test Result Models
# =============================================================================


class TemplateTestResult:
    """
    Result of a template test run.

    Attributes:
        success: Whether the test completed successfully
        template_name: Name of the template that was tested
        validation_passed: Whether template validation passed
        validation_errors: List of validation errors (if any)
        client_created: Whether the SDK client was created successfully
        response_received: Whether a response was received from the agent
        agent_response: The agent's response text (if successful)
        usage_metadata: Token usage metadata (input_tokens, output_tokens)
        error: Error message if test failed
        test_prompt: The prompt used for testing
        duration_seconds: Test execution duration in seconds
    """

    def __init__(
        self,
        success: bool,
        template_name: str,
        validation_passed: bool = False,
        validation_errors: list[str] | None = None,
        client_created: bool = False,
        response_received: bool = False,
        agent_response: str | None = None,
        usage_metadata: dict[str, int] | None = None,
        error: str | None = None,
        test_prompt: str = "",
        duration_seconds: float = 0.0,
    ):
        self.success = success
        self.template_name = template_name
        self.validation_passed = validation_passed
        self.validation_errors = validation_errors or []
        self.client_created = client_created
        self.response_received = response_received
        self.agent_response = agent_response
        self.usage_metadata = usage_metadata
        self.error = error
        self.test_prompt = test_prompt
        self.duration_seconds = duration_seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "success": self.success,
            "template_name": self.template_name,
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
            "client_created": self.client_created,
            "response_received": self.response_received,
            "agent_response": self.agent_response,
            "usage_metadata": self.usage_metadata,
            "error": self.error,
            "test_prompt": self.test_prompt,
            "duration_seconds": self.duration_seconds,
        }

    def __repr__(self) -> str:
        """String representation of test result."""
        if self.success:
            return (
                f"TemplateTestResult(success=True, "
                f"template='{self.template_name}', "
                f"response_length={len(self.agent_response) if self.agent_response else 0})"
            )
        return (
            f"TemplateTestResult(success=False, "
            f"template='{self.template_name}', "
            f"error='{self.error}')"
        )


# =============================================================================
# Helper Functions
# =============================================================================


def _extract_usage_metadata(client: Any) -> dict[str, int] | None:
    """Extract usage metadata from client via public API or private fallback.

    Note: the _usage fallback accesses a private attribute and may break
    on SDK upgrades. It is isolated here so future changes are easy to track.
    """
    # Prefer public API
    metadata = getattr(client, "usage_metadata", None)
    if (
        metadata
        and hasattr(metadata, "input_tokens")
        and hasattr(metadata, "output_tokens")
    ):
        return {
            "input_tokens": metadata.input_tokens,
            "output_tokens": metadata.output_tokens,
            "total_tokens": metadata.input_tokens + metadata.output_tokens,
        }
    # Fallback: private _usage dict (fragile, may change with SDK upgrades)
    usage = getattr(client, "_usage", None)
    if isinstance(usage, dict) and "input_tokens" in usage and "output_tokens" in usage:
        debug(
            "test_runner",
            "Using internal _usage fallback for token metadata (may break on SDK upgrade)",
        )
        return {
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "total_tokens": usage["input_tokens"] + usage["output_tokens"],
        }
    return None


# =============================================================================
# Test Runner Functions
# =============================================================================


async def run_template_test(
    template: AgentTemplate,
    test_prompt: str,
    project_dir: Path | None = None,
    timeout_seconds: int = 120,
) -> TemplateTestResult:
    """
    Run a test of a custom agent template.

    This function:
    1. Validates the template configuration
    2. Creates a Claude SDK client with template settings
    3. Sends a test prompt to the agent
    4. Collects the response and usage metadata
    5. Returns detailed test results

    Args:
        template: AgentTemplate instance to test
        test_prompt: Prompt to send to the agent for testing
        project_dir: Project directory (uses current dir if None)
        timeout_seconds: Maximum time to wait for response (default: 120s)

    Returns:
        TemplateTestResult with test outcome and details
    """
    import time

    from core.client import create_client

    start_time = time.time()
    template_name = template.name

    debug_section("test_runner", f"Testing Template: {template_name}")
    debug(
        "test_runner",
        "Starting template test",
        template=template_name,
        prompt_length=len(test_prompt),
        prompt_preview=test_prompt[:200] + "..."
        if len(test_prompt) > 200
        else test_prompt,
    )

    print_status(f"Testing template: {template_name}", "info")

    # Step 1: Validate template
    print("  [1/4] Validating template configuration...")
    validation_passed, validation_errors = validate_template(template)

    if not validation_passed:
        debug_error(
            "test_runner",
            "Template validation failed",
            errors=validation_errors,
        )
        print_status("Template validation failed", "error")
        for error in validation_errors:
            print(f"    - {error}")

        duration = time.time() - start_time
        return TemplateTestResult(
            success=False,
            template_name=template_name,
            validation_passed=False,
            validation_errors=validation_errors,
            error="Template validation failed",
            test_prompt=test_prompt,
            duration_seconds=duration,
        )

    debug_success("test_runner", "Template validation passed")
    print_status("Validation passed", "success")

    # Step 2: Create client with template configuration
    print("  [2/4] Creating SDK client with template...")

    # Use project_dir or current working directory
    if project_dir is None:
        project_dir = Path.cwd()

    try:
        client = create_client(
            project_dir=project_dir,
            spec_dir=project_dir,  # Use project_dir as spec_dir for template testing
            model="claude-sonnet-4-5-20250929",
            agent_type="custom",  # Use custom agent type for templates
            custom_template=template,  # Pass custom template configuration
        )
        debug_success("test_runner", "SDK client created successfully")
        print_status("Client created", "success")
    except Exception as e:
        debug_error(
            "test_runner",
            "Failed to create SDK client",
            error=str(e),
            exception_type=type(e).__name__,
        )
        print_status(f"Failed to create client: {e}", "error")

        duration = time.time() - start_time
        return TemplateTestResult(
            success=False,
            template_name=template_name,
            validation_passed=True,
            validation_errors=[],
            client_created=False,
            error=f"Failed to create client: {e}",
            test_prompt=test_prompt,
            duration_seconds=duration,
        )

    # Step 3: Run test session
    print("  [3/4] Running test session...")

    try:
        async with client:
            # Send test query
            debug("test_runner", "Sending test query to agent...")
            await client.query(test_prompt)
            debug_success("test_runner", "Test query sent")

            # Collect response
            response_text = ""
            message_count = 0
            debug("test_runner", "Collecting agent response...")

            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                message_count += 1
                debug_detailed(
                    "test_runner",
                    f"Received message #{message_count}",
                    msg_type=msg_type,
                )

                # Extract text from AssistantMessage
                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        block_type = type(block).__name__
                        if block_type == "TextBlock" and hasattr(block, "text"):
                            response_text += block.text
                            # Print response preview (first 500 chars)
                            if len(response_text) <= 500:
                                print(block.text, end="", flush=True)

        print()  # New line after response

        if not response_text:
            debug_error("test_runner", "No response received from agent")
            print_status("No response received", "error")

            duration = time.time() - start_time
            return TemplateTestResult(
                success=False,
                template_name=template_name,
                validation_passed=True,
                validation_errors=[],
                client_created=True,
                response_received=False,
                error="No response received from agent",
                test_prompt=test_prompt,
                duration_seconds=duration,
            )

        debug_success(
            "test_runner",
            "Response received",
            response_length=len(response_text),
            message_count=message_count,
        )
        print_status("Response received", "success")

    except Exception as e:
        debug_error(
            "test_runner",
            "Error during test session",
            error=str(e),
            exception_type=type(e).__name__,
        )
        print_status(f"Test session error: {e}", "error")

        duration = time.time() - start_time
        return TemplateTestResult(
            success=False,
            template_name=template_name,
            validation_passed=True,
            validation_errors=[],
            client_created=True,
            response_received=False,
            error=f"Test session error: {e}",
            test_prompt=test_prompt,
            duration_seconds=duration,
        )

    # Step 4: Extract usage metadata
    print("  [4/4] Extracting usage metadata...")

    usage_metadata = None
    try:
        usage_metadata = _extract_usage_metadata(client)
        if usage_metadata:
            debug_success(
                "test_runner",
                "Usage metadata extracted",
                input_tokens=usage_metadata["input_tokens"],
                output_tokens=usage_metadata["output_tokens"],
            )
            print_key_value(
                "Token usage",
                f"{usage_metadata['input_tokens']} in, {usage_metadata['output_tokens']} out",
            )
    except Exception as e:
        debug(
            "test_runner",
            "Could not extract usage metadata",
            error=str(e),
        )

    # Test completed successfully
    duration = time.time() - start_time
    print_status(f"Test completed in {duration:.2f}s", "success")

    return TemplateTestResult(
        success=True,
        template_name=template_name,
        validation_passed=True,
        validation_errors=[],
        client_created=True,
        response_received=True,
        agent_response=response_text,
        usage_metadata=usage_metadata,
        test_prompt=test_prompt,
        duration_seconds=duration,
    )


def create_test_prompt(
    template: AgentTemplate,
    custom_instructions: str | None = None,
) -> str:
    """
        Create a test prompt for template testing.

        Generates a test prompt that exercises the template's configuration:
    - Tests if the agent understands its custom prompt
    - Verifies tool awareness
    - Checks if MCP servers are accessible

        Args:
            template: AgentTemplate instance being tested
            custom_instructions: Optional custom test instructions

        Returns:
            Test prompt string
    """
    custom_prompt = template.custom_prompt or ""
    tools = template.tools or []
    custom_prompt_line = (
        "Custom Prompt: " + custom_prompt[:200] + "..."
        if len(custom_prompt) > 200
        else "Custom Prompt: " + custom_prompt
        if custom_prompt
        else "No custom prompt (using base agent behavior)"
    )

    base_prompt = f"""You are testing a custom agent template called '{template.name}'.

Template Configuration:
- Category: {template.category}
- Tools: {", ".join(tools)}
- MCP Servers: {", ".join(template.mcp_servers) if template.mcp_servers else "None"}
- Thinking Level: {template.thinking_level}

{custom_prompt_line}

Please respond with:
1. Confirm you understand your role and configuration
2. List the tools you have access to
3. Describe your custom instructions (if any)
4. Confirm you are ready to help with tasks

Keep your response brief and focused on confirming your setup."""

    if custom_instructions:
        base_prompt += f"\n\nAdditional Test Instructions:\n{custom_instructions}"

    return base_prompt


# =============================================================================
# Convenience Functions
# =============================================================================


async def quick_test(
    template: AgentTemplate,
    test_message: str = "Hello, please confirm your configuration",
    project_dir: Path | None = None,
) -> bool:
    """
    Quick test a template - returns True/False for success.

    Convenience function for simple template testing. Use run_template_test()
    for detailed results.

    Args:
        template: AgentTemplate instance to test
        test_message: Simple test message (default: "Hello, please confirm your configuration")
        project_dir: Project directory (uses current dir if None)

    Returns:
        True if test succeeded, False otherwise
    """
    result = await run_template_test(
        template=template,
        test_prompt=test_message,
        project_dir=project_dir,
    )
    return result.success
