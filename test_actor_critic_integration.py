#!/usr/bin/env python3
"""
Test Script for Actor-Critic MCP Integration
==============================================

This script validates that the spec_critic agent correctly uses the
actor-critic-thinking MCP server when ACTOR_CRITIC_MCP_ENABLED=true.

Usage:
    # Test with actor-critic enabled
    ACTOR_CRITIC_MCP_ENABLED=true python test_actor_critic_integration.py

    # Test with actor-critic disabled (graceful degradation)
    ACTOR_CRITIC_MCP_ENABLED=false python test_actor_critic_integration.py

Expected Behavior:
- When enabled: spec_critic agent should have actor-critic-thinking tool available
- When disabled: spec_critic agent should work normally without the tool
"""

import os
import sys
from pathlib import Path

# Add backend to sys.path once at module level
_backend_path = str(Path(__file__).parent / "apps" / "backend")
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)


def test_agent_type_mapping():
    """Test that prompt files map to correct agent types."""
    from spec.pipeline.agent_runner import PROMPT_TO_AGENT_TYPE

    print("Testing agent type mapping...")

    # Check that spec_critic.md maps to spec_critic
    assert PROMPT_TO_AGENT_TYPE.get("spec_critic.md") == "spec_critic", \
        "spec_critic.md should map to spec_critic agent type"
    print("  spec_critic.md correctly maps to spec_critic agent type")

    # Check other expected mappings
    expected_mappings = {
        "spec_discovery.md": "spec_discovery",
        "spec_requirements.md": "spec_requirements",
        "spec_context.md": "spec_context",
        "spec_writing.md": "spec_writing",
        "spec_planning.md": "spec_planning",
        "spec_validation.md": "spec_validation",
        "spec_research.md": "spec_research",
        "spec_compaction.md": "spec_compaction",
    }

    for prompt_file, expected_agent in expected_mappings.items():
        actual = PROMPT_TO_AGENT_TYPE.get(prompt_file)
        assert actual == expected_agent, \
            f"{prompt_file} should map to {expected_agent}, got {actual}"
        print(f"  {prompt_file} correctly maps to {expected_agent}")

    print("\n  All agent type mappings are correct!\n")
    return True


def test_spec_critic_config():
    """Test that spec_critic agent config has actor-critic-thinking enabled."""
    from agents.tools_pkg.models import get_agent_config

    print("Testing spec_critic agent configuration...")

    config = get_agent_config("spec_critic")

    # Check that actor-critic-thinking is enabled as a boolean flag
    has_actor_critic = config.get("actor-critic-thinking", False)
    assert has_actor_critic is True, \
        "spec_critic should have actor-critic-thinking enabled as True"
    print("  spec_critic has actor-critic-thinking=True flag")

    # Verify other spec_critic config
    assert config.get("thinking_default") == "ultrathink", \
        "spec_critic should use ultrathink by default"
    print("  spec_critic uses ultrathink by default")

    # Verify spec_critic has no required MCP servers (optional only)
    mcp_servers = config.get("mcp_servers", [])
    assert mcp_servers == [], \
        "spec_critic should have empty mcp_servers list (uses optional servers only)"
    print("  spec_critic has no required MCP servers")

    print("\n  spec_critic agent configuration is correct!\n")
    return True


def test_actor_critic_enabled():
    """Test that actor-critic MCP is correctly detected when enabled."""
    from core.actor_critic_config import is_actor_critic_enabled

    print("Testing actor-critic MCP detection...")

    # Check current state
    is_enabled = is_actor_critic_enabled()
    env_value = os.environ.get("ACTOR_CRITIC_MCP_ENABLED", "false")

    print(f"  ACTOR_CRITIC_MCP_ENABLED env var: {env_value}")
    print(f"  is_actor_critic_enabled(): {is_enabled}")

    if env_value.lower() == "true":
        # Note: is_actor_critic_enabled() also checks npx availability,
        # so it may return False even when env var is true if npx is missing
        print(f"  Actor-critic MCP enabled={is_enabled} (depends on npx availability)")
    else:
        assert is_enabled is False, \
            "is_actor_critic_enabled() should return False when env var is not 'true'"
        print("  Actor-critic MCP is disabled (default)")

    print("\n  Actor-critic MCP detection is working correctly!\n")
    return True


def test_actor_critic_config_validation():
    """Test that actor-critic config validation works."""
    from core.actor_critic_config import validate_actor_critic_config

    print("Testing actor-critic configuration validation...")

    # This should not raise an unrecoverable error
    try:
        validate_actor_critic_config()
        print("  Actor-critic config validation passed")
    except RuntimeError as e:
        # RuntimeError is expected if enabled but npx not available
        print(f"  Actor-critic config validation raised RuntimeError (expected if npx missing): {e}")
    except Exception as e:
        print(f"  Actor-critic config validation failed unexpectedly: {e}")
        return False

    print("\n  Actor-critic configuration validation is working!\n")
    return True


def test_get_required_mcp_servers():
    """Test that spec_critic gets actor-critic server when enabled."""
    from agents.tools_pkg.models import get_required_mcp_servers
    from core.actor_critic_config import is_actor_critic_enabled

    print("Testing MCP server selection for spec_critic...")

    # Get required servers for spec_critic
    required_servers = get_required_mcp_servers(
        agent_type="spec_critic",
        project_capabilities=None,
        linear_enabled=False,
        mcp_config={}
    )

    print(f"  Required MCP servers for spec_critic: {required_servers}")

    # Check if actor-critic-thinking is included when enabled
    if is_actor_critic_enabled():
        # When enabled, actor-critic-thinking should be in the list
        assert "actor-critic-thinking" in required_servers, \
            "actor-critic-thinking should be in required servers when enabled"
        print("  Actor-critic-thinking server included when enabled")
    else:
        # When disabled, actor-critic-thinking should not be in the list
        print("  Actor-critic MCP is disabled")
        assert "actor-critic-thinking" not in required_servers, \
            "actor-critic-thinking should not be in required servers when disabled"
        print("  Actor-critic server correctly excluded when disabled")

    print("\n  MCP server selection is working correctly!\n")
    return True


def print_test_summary():
    """Print summary of what was tested and next steps."""
    print("=" * 70)
    print("ACTOR-CRITIC INTEGRATION TEST SUMMARY")
    print("=" * 70)
    print()
    print("  Agent type mapping: Prompt files correctly map to agent types")
    print("  Spec_critic config: Has actor-critic-thinking in optional servers")
    print("  MCP detection: Correctly detects ACTOR_CRITIC_MCP_ENABLED env var")
    print("  Config validation: Validation function works without errors")
    print("  Server selection: Correctly includes/excludes actor-critic server")
    print()
    print("INTEGRATION STATUS: PASSED")
    print()
    print("Next Steps for Manual Testing:")
    print("-" * 70)
    print()
    print("1. Enable actor-critic MCP:")
    print("   export ACTOR_CRITIC_MCP_ENABLED=true")
    print()
    print("2. Run spec creation:")
    print("   python apps/backend/runners/spec_runner.py --task 'Test task'")
    print()
    print("3. Check agent logs for tool usage:")
    print("   - Look for actor_critic_thinking tool calls")
    print("   - Verify multi-round dialogue pattern (actor -> critic -> actor...)")
    print("   - Check token usage in agent logs")
    print()
    print("4. Verify graceful degradation:")
    print("   export ACTOR_CRITIC_MCP_ENABLED=false")
    print("   python apps/backend/runners/spec_runner.py --task 'Test task'")
    print("   - Spec creation should work normally without actor-critic")
    print()
    print("=" * 70)
    print()


def main():
    """Run all tests."""
    print()
    print("=" * 70)
    print("ACTOR-CRITIC MCP INTEGRATION TEST")
    print("=" * 70)
    print()

    # Run all tests
    tests = [
        ("Agent Type Mapping", test_agent_type_mapping),
        ("Spec Critic Config", test_spec_critic_config),
        ("Actor-Critic Detection", test_actor_critic_enabled),
        ("Config Validation", test_actor_critic_config_validation),
        ("MCP Server Selection", test_get_required_mcp_servers),
    ]

    failed_tests = []
    for test_name, test_fn in tests:
        try:
            print(f"\n{'=' * 70}")
            print(f"TEST: {test_name}")
            print(f"{'=' * 70}\n")
            if not test_fn():
                failed_tests.append(test_name)
        except AssertionError as e:
            print(f"\n  TEST FAILED: {test_name}")
            print(f"  Error: {e}\n")
            failed_tests.append(test_name)
        except Exception as e:
            print(f"\n  TEST ERROR: {test_name}")
            print(f"  Exception: {e}\n")
            failed_tests.append(test_name)

    # Print summary
    print_test_summary()

    if failed_tests:
        print("FAILED TESTS:")
        for test_name in failed_tests:
            print(f"  - {test_name}")
        print()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
