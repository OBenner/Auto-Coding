"""
Runner for test_2_single_tool_invocation only.
Tests health_check and get_window_info tools.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path


async def main():
    """Run only test_2_single_tool_invocation"""
    # Determine directories
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent

    # Look for spec dir in worktree structure
    cwd = Path.cwd()
    spec_dir = (
        cwd
        / ".auto-claude"
        / "specs"
        / "175-run-manual-ui-testing-validation-33-scenarios-docu"
    )

    if not spec_dir.exists():
        # Create temp spec dir if needed
        spec_dir = script_dir / ".temp_spec"
        spec_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("Running TEST 2: Single Tool Invocation")
    print("=" * 70)
    print(f"Project directory: {project_dir}")
    print(f"Spec directory: {spec_dir}")
    print(f"ELECTRON_MCP_ENABLED: {os.getenv('ELECTRON_MCP_ENABLED', 'not set')}")
    print(f"ELECTRON_MCP_MODE: {os.getenv('ELECTRON_MCP_MODE', 'not set')}")
    print()

    # Import in specific order to avoid circular import
    try:
        from agents.tools_pkg import AGENT_CONFIGS  # noqa: F401

        print("✅ agents.tools_pkg imported")
    except ImportError as e:
        print(f"❌ Failed to import agents.tools_pkg: {e}")
        sys.exit(1)

    try:
        from core.auth import get_auth_token  # noqa: F401
        from core.platform import is_windows  # noqa: F401
        from security import bash_security_hook  # noqa: F401

        print("✅ Core dependencies imported")
    except ImportError as e:
        print(f"❌ Failed to import dependencies: {e}")
        sys.exit(1)

    try:
        import core.client as client_module

        create_client = client_module.create_client
        print("✅ core.client imported")
    except ImportError as e:
        print(f"❌ Failed to import core.client: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\nCreating tester instance...")

    class SimpleTester:
        """Simplified tester for test_2"""

        def __init__(self, project_dir, spec_dir):
            self.project_dir = project_dir
            self.spec_dir = spec_dir
            self.test_results = []
            self.verbose = os.getenv("VERBOSE", "false").lower() == "true"
            self.model_id = os.getenv("LLM_TEST_MODEL_ID", "claude-sonnet-4-5-20250929")

        def _create_test_client(self):
            return create_client(
                project_dir=self.project_dir,
                spec_dir=self.spec_dir,
                agent_type="qa_reviewer",
                model=self.model_id,
            )

        async def _run_agent_query(self, client, task):
            """Run a query and collect response."""
            response_text = ""
            async with client:
                await client.query(task)
                async for msg in client.receive_response():
                    msg_type = type(msg).__name__
                    if hasattr(msg, "content"):
                        response_text += str(msg.content)
                    elif hasattr(msg, "text"):
                        response_text += str(msg.text)
            return response_text

        async def test_2_single_tool_invocation(self):
            """Test 2: Verify LLM can invoke individual tools"""
            print("\n" + "=" * 70)
            print("TEST 2: Single Tool Invocation")
            print("=" * 70)

            test_cases = [
                {
                    "name": "health_check",
                    "task": "Check the MCP server health status using the health_check tool and report the metrics including uptime and status.",
                    "expected_keywords": ["uptime", "status", "healthy"],
                },
                {
                    "name": "get_window_info",
                    "task": "Get information about all open windows using the get_window_info tool. Report window id and title.",
                    "expected_keywords": ["window", "id", "title"],
                },
            ]

            all_passed = True
            results = []

            for i, test_case in enumerate(test_cases, 1):
                print(f"\n  Test {i}/{len(test_cases)}: {test_case['name']}")
                print(f"  Task: {test_case['task']}")

                try:
                    client = self._create_test_client()

                    start_time = time.time()
                    response_text = await self._run_agent_query(
                        client, test_case["task"]
                    )
                    duration = time.time() - start_time

                    response_lower = response_text.lower()

                    # Check for expected keywords
                    keywords_found = [
                        kw
                        for kw in test_case["expected_keywords"]
                        if kw.lower() in response_lower
                    ]

                    print(f"  ⏱️  Duration: {duration:.2f}s")
                    print(f"  Response length: {len(response_text)} chars")

                    if keywords_found:
                        print(
                            f"  ✅ {test_case['name']} succeeded - found keywords: {keywords_found}"
                        )
                        results.append(
                            (test_case["name"], True, duration, keywords_found)
                        )
                    else:
                        print(
                            f"  ⚠️ {test_case['name']} completed but expected keywords not found"
                        )
                        print(f"     Expected: {test_case['expected_keywords']}")
                        results.append((test_case["name"], False, duration, []))
                        all_passed = False

                    if self.verbose:
                        print(f"  Response preview: {response_text[:500]}...")

                except Exception as e:
                    print(f"  ❌ {test_case['name']} failed: {str(e)[:200]}")
                    results.append((test_case["name"], False, 0, []))
                    all_passed = False
                    if self.verbose:
                        import traceback

                        traceback.print_exc()

            # Summary
            passed_count = sum(1 for _, passed, _, _ in results if passed)
            print(f"\n  Results: {passed_count}/{len(test_cases)} tests passed")
            self.test_results = results
            return all_passed, results

    # Run the test
    tester = SimpleTester(project_dir, spec_dir)

    try:
        result, details = await tester.test_2_single_tool_invocation()
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback

        traceback.print_exc()
        result = False
        details = []

    # Print results
    print("\n" + "=" * 70)
    print("TEST 2 RESULTS")
    print("=" * 70)

    for test_name, passed, duration, keywords in details:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {test_name} ({duration:.2f}s)")
        if keywords:
            print(f"      Keywords found: {keywords}")

    # Save results to JSON
    results = {
        "test_name": "test_2_single_tool_invocation",
        "subtask_id": "subtask-2-2",
        "description": "Run test_2_single_tool_invocation - health_check and get_window_info",
        "success": result,
        "tests": [
            {
                "name": name,
                "passed": passed,
                "duration_seconds": duration,
                "keywords_found": keywords,
            }
            for name, passed, duration, keywords in details
        ],
        "verification": {
            "expected": ["uptime", "status", "window id", "title"],
            "result": "PASS" if result else "FAIL",
        },
    }

    results_file = script_dir / "test_2_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
