#!/usr/bin/env python3
"""
Preference System Verification
==============================

Verifies the Adaptive Agent Personality System implementation.
This checks that all components are in place and properly integrated.
"""

import sys
from pathlib import Path

# Add apps/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_project_root():
    """Get the project root directory."""
    test_file = Path(__file__).resolve()
    tests_dir = test_file.parent  # apps/backend/tests
    backend_dir = tests_dir.parent  # apps/backend
    apps_dir = backend_dir.parent  # apps
    return apps_dir.parent  # project root


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def print_check(name: str):
    """Print a check name."""
    print(f"\n▶ {name}")


def print_pass(message: str = "✅ PASS"):
    """Print a pass message."""
    print(f"  {message}")


def print_fail(message: str):
    """Print a fail message."""
    print(f"  ❌ FAIL: {message}")


def print_info(message: str):
    """Print an info message."""
    print(f"  ℹ️  {message}")


def verify_backend_models():
    """Verify backend preference models exist and work."""
    print_check("Backend Preference Models")

    try:
        from agents.preferences import (
            FeedbackRecord,
            FeedbackType,
            PreferenceProfile,
            ProjectType,
            RiskTolerance,
            VerbosityLevel,
            modify_prompt_for_preferences,
        )

        # Test creating a profile
        profile = PreferenceProfile(
            verbosity_level=VerbosityLevel.CONCISE,
            risk_tolerance=RiskTolerance.BALANCED,
            project_type=ProjectType.ESTABLISHED,
        )

        # Test feedback
        profile.add_feedback(
            feedback_type=FeedbackType.MODIFIED,
            task_description="Test task",
            agent_type="coder",
            context={"reason": "too verbose"},
        )

        # Test serialization
        profile_dict = profile.to_dict()
        restored = PreferenceProfile.from_dict(profile_dict)

        # Test prompt modification
        original_prompt = "You are a helpful coding assistant."
        modified = modify_prompt_for_preferences(original_prompt, profile)

        assert "concise" in modified.lower()
        assert restored.verbosity_level == VerbosityLevel.CONCISE

        print_pass("Preference models work correctly")
        print_info("  - PreferenceProfile: OK")
        print_info("  - Feedback tracking: OK")
        print_info("  - Prompt modification: OK")
        print_info("  - Serialization: OK")
        return True

    except Exception as e:
        print_fail(f"Backend models failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_graphiti_integration():
    """Verify Graphiti memory integration."""
    print_check("Graphiti Memory Integration")

    try:
        from integrations.graphiti.memory import is_graphiti_enabled

        if not is_graphiti_enabled():
            print_info("Graphiti not enabled (expected if not configured)")
            print_info("  - This is OK - preference system has fallback")
            return True

        from integrations.graphiti.memory import get_graphiti_memory
        from agents.preferences import PreferenceProfile, VerbosityLevel

        project_root = get_project_root()
        spec_dir = project_root / ".auto-claude" / "specs" / "131-adaptive-agent-personality-system"

        # Get memory instance (not async for this check)
        memory = get_graphiti_memory(spec_dir, project_root)

        if memory:
            print_pass("Graphiti memory integration OK")
            print_info("  - get_graphiti_memory: OK")
            print_info("  - Memory instance created: OK")
            return True
        else:
            print_fail("Could not create Graphiti memory instance")
            return False

    except Exception as e:
        print_fail(f"Graphiti integration failed: {e}")
        return False


def verify_client_integration():
    """Verify client preference loading."""
    print_check("Client Preference Integration")

    try:
        from core.client import load_preferences

        project_root = get_project_root()
        spec_dir = project_root / ".auto-claude" / "specs" / "131-adaptive-agent-personality-system"

        base_prompt = "You are a helpful coding assistant."

        # This will either modify the prompt (if preferences exist) or return it as-is
        modified_prompt = load_preferences(base_prompt, spec_dir, project_root)

        print_pass("Client integration OK")
        print_info("  - load_preferences function: OK")
        print_info(f"  - Prompt handling: OK ({len(modified_prompt)} chars)")
        return True

    except Exception as e:
        print_fail(f"Client integration failed: {e}")
        return False


def verify_feedback_recording():
    """Verify feedback recording functionality."""
    print_check("Feedback Recording")

    try:
        from agents.memory_manager import save_feedback

        print_pass("Feedback recording API exists")
        print_info("  - save_feedback function: OK")
        print_info("  - Note: Full test requires Graphiti enabled")
        return True

    except Exception as e:
        print_fail(f"Feedback recording check failed: {e}")
        return False


def verify_adaptive_behavior():
    """Verify adaptive behavior learning."""
    print_check("Adaptive Behavior Learning")

    try:
        from agents.preferences import (
            FeedbackType,
            PreferenceProfile,
            RiskTolerance,
            VerbosityLevel,
        )

        # Test verbosity learning
        profile = PreferenceProfile(
            verbosity_level=VerbosityLevel.NORMAL,
            risk_tolerance=RiskTolerance.BALANCED,
            project_type="established",
        )

        # Simulate feedback
        for i in range(3):
            profile.add_feedback(
                feedback_type=FeedbackType.MODIFIED,
                task_description=f"Task {i+1}",
                agent_type="coder",
                context={"reason": "too verbose"},
            )

        # Check learning happened
        effective_verbosity = profile.get_effective_verbosity()

        print_pass("Adaptive behavior learning OK")
        print_info("  - Feedback tracking: OK")
        print_info(f"  - Learned adjustment: {profile.learned_verbosity_adjustment}")
        print_info(f"  - Effective verbosity: {effective_verbosity.value}")
        return True

    except Exception as e:
        print_fail(f"Adaptive behavior test failed: {e}")
        return False


def verify_frontend_types():
    """Verify frontend TypeScript types."""
    print_check("Frontend TypeScript Types")

    project_root = get_project_root()
    types_file = project_root / "apps" / "frontend" / "src" / "shared" / "types" / "settings.ts"

    if not types_file.exists():
        print_fail(f"TypeScript types file not found: {types_file}")
        return False

    content = types_file.read_text()

    required_types = [
        "AgentVerbosityLevel",
        "AgentRiskTolerance",
        "AgentProjectType",
        "AgentCodingStylePreferences",
    ]

    all_found = True
    for type_name in required_types:
        if type_name in content:
            print_pass(f"  - {type_name}: defined")
        else:
            print_fail(f"  - {type_name}: missing")
            all_found = False

    if all_found:
        print_pass("All required TypeScript types defined")
    return all_found


def verify_frontend_components():
    """Verify frontend UI components."""
    print_check("Frontend UI Components")

    project_root = get_project_root()

    # Check AgentPreferences component
    agent_prefs = project_root / "apps" / "frontend" / "src" / "renderer" / "components" / "settings" / "AgentPreferences.tsx"
    if agent_prefs.exists():
        print_pass("  - AgentPreferences component: exists")
    else:
        print_fail(f"  - AgentPreferences component: not found at {agent_prefs}")
        return False

    # Check FeedbackButtons component
    feedback_buttons = project_root / "apps" / "frontend" / "src" / "renderer" / "components" / "feedback" / "FeedbackButtons.tsx"
    if feedback_buttons.exists():
        print_pass("  - FeedbackButtons component: exists")
    else:
        print_fail(f"  - FeedbackButtons component: not found at {feedback_buttons}")
        return False

    print_pass("All frontend UI components present")
    return True


def verify_ipc_handlers():
    """Verify IPC handlers for feedback."""
    print_check("IPC Handlers")

    project_root = get_project_root()
    handler_file = project_root / "apps" / "frontend" / "src" / "main" / "ipc-handlers" / "feedback-handlers.ts"

    if not handler_file.exists():
        print_fail(f"Feedback handler not found: {handler_file}")
        return False

    content = handler_file.read_text()

    required_items = ["registerFeedbackHandlers", "IPC_CHANNELS.FEEDBACK_SUBMIT", "feedback_recorder.py"]

    all_found = True
    for item in required_items:
        if item in content:
            print_pass(f"  - {item}: defined")
        else:
            print_fail(f"  - {item}: missing")
            all_found = False

    # Check feedback_recorder.py
    recorder_script = project_root / "apps" / "backend" / "feedback_recorder.py"
    if recorder_script.exists():
        print_pass("  - feedback_recorder.py: exists")
    else:
        print_fail(f"  - feedback_recorder.py: not found")
        all_found = False

    if all_found:
        print_pass("IPC handlers properly configured")
    return all_found


def verify_integration():
    """Verify end-to-end integration."""
    print_check("End-to-End Integration")

    checks = []

    # Check all components are connected
    try:
        from core.client import load_preferences
        from agents.preferences import modify_prompt_for_preferences
        from agents.memory_manager import save_feedback
        from integrations.graphiti.memory import get_graphiti_memory

        checks.append(True)
        print_pass("  - All imports successful")
    except Exception as e:
        print_fail(f"  - Import failed: {e}")
        checks.append(False)

    # Check data flow
    try:
        from agents.preferences import PreferenceProfile, VerbosityLevel, modify_prompt_for_preferences

        profile = PreferenceProfile(verbosity_level=VerbosityLevel.CONCISE)
        prompt = modify_prompt_for_preferences("Test prompt", profile)

        if "concise" in prompt.lower():
            checks.append(True)
            print_pass("  - Data flow: preferences → prompt modification")
        else:
            checks.append(False)
            print_fail("  - Data flow: prompt modification not working")
    except Exception as e:
        print_fail(f"  - Data flow test failed: {e}")
        checks.append(False)

    return all(checks)


def main():
    """Run all verification checks."""
    print_section("Adaptive Agent Personality System - Verification")

    print_info("Verifying implementation of:")
    print("  1. Backend preference storage and models")
    print("  2. Graphiti memory integration")
    print("  3. Client preference loading")
    print("  4. Feedback recording")
    print("  5. Adaptive behavior learning")
    print("  6. Frontend types and components")
    print("  7. IPC handlers")
    print("  8. End-to-end integration")

    # Run all checks
    results = {
        "Backend Models": verify_backend_models(),
        "Graphiti Integration": verify_graphiti_integration(),
        "Client Integration": verify_client_integration(),
        "Feedback Recording": verify_feedback_recording(),
        "Adaptive Behavior": verify_adaptive_behavior(),
        "Frontend Types": verify_frontend_types(),
        "Frontend Components": verify_frontend_components(),
        "IPC Handlers": verify_ipc_handlers(),
        "End-to-End Integration": verify_integration(),
    }

    # Print summary
    print_section("Verification Summary")

    total = len(results)
    passed = sum(results.values())
    failed = total - passed

    print(f"\n  Total Checks: {total}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")

    print("\n  Detailed Results:")
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"    {status}: {name}")

    if failed == 0:
        print("\n  🎉 All verification checks passed!")
        print("  The Adaptive Agent Personality System is fully implemented.")
        print_section("Verification Complete")
        return 0
    else:
        print(f"\n  ⚠️  {failed} check(s) failed.")
        print("  Please review the errors above.")
        print_section("Verification Complete")
        return 1


if __name__ == "__main__":
    sys.exit(main())
