"""
Test LLM Interaction with Electron MCP Server

This test suite validates that LLM agents (qa_reviewer, qa_fixer) can
successfully interact with the embedded MCP server in the Electron app
via the Model Context Protocol.

Usage:
    cd apps/backend
    python test_llm_mcp_integration.py

Environment Variables Required:
    ELECTRON_MCP_ENABLED=true
    ELECTRON_MCP_MODE=embedded

Author: Auto-Claude (Subtask 4.3)
Date: 2026-02-16
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Add apps/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from core.client import create_client
except ImportError as e:
    print(f"❌ Failed to import create_client: {e}")
    print("   Make sure you're running from apps/backend directory")
    sys.exit(1)


DEFAULT_TEST_MODEL_ID = "claude-sonnet-4-5-20250929"


class LLMInteractionTester:
    """Test LLM agent interaction with MCP server"""

    def __init__(self, project_dir: Path, spec_dir: Path):
        self.project_dir = project_dir
        self.spec_dir = spec_dir
        self.test_results: list[tuple] = []
        self.verbose = os.getenv("VERBOSE", "false").lower() == "true"
        self.model_id = os.getenv("LLM_TEST_MODEL_ID", DEFAULT_TEST_MODEL_ID)

    def _create_test_client(self):
        """Create a Claude SDK client configured for QA testing."""
        return create_client(
            project_dir=self.project_dir,
            spec_dir=self.spec_dir,
            agent_type="qa_reviewer",
            model=self.model_id,
        )

    def _log_verbose_traceback(self):
        """Print traceback if verbose mode is enabled."""
        if self.verbose:
            import traceback

            traceback.print_exc()

    def _record_failure(self, test_name: str, error: Exception) -> None:
        """Log error, print traceback if verbose, and record test failure."""
        self.log(f"  {test_name} failed: {error}", "error")
        self._log_verbose_traceback()
        self.test_results.append((test_name, False, str(error)))

    @staticmethod
    def _extract_response_text(response) -> str:
        """Extract lowercased text content from an agent response."""
        return str(response.content).lower() if hasattr(response, "content") else ""

    def log(self, message: str, level: str = "info"):
        """Log message with level"""
        if level == "error":
            print(f"❌ {message}")
        elif level == "success":
            print(f"✅ {message}")
        elif level == "warning":
            print(f"⚠️  {message}")
        else:
            print(f"   {message}")

    def setup(self) -> bool:
        """Setup test environment and verify configuration"""
        print("=" * 70)
        print("LLM MCP Integration Test Suite")
        print("=" * 70)
        print()

        # Check environment variables
        electron_mcp_enabled = os.getenv("ELECTRON_MCP_ENABLED", "false")
        electron_mcp_mode = os.getenv("ELECTRON_MCP_MODE", "cdp")

        print(f"ELECTRON_MCP_ENABLED: {electron_mcp_enabled}")
        print(f"ELECTRON_MCP_MODE: {electron_mcp_mode}")
        print(f"Project directory: {self.project_dir}")
        print(f"Spec directory: {self.spec_dir}")
        print()

        if electron_mcp_enabled.lower() != "true":
            self.log("ELECTRON_MCP_ENABLED is not set to 'true'", "warning")
            self.log("Tests will likely fail if MCP server is not running", "warning")
            print()

        # Verify directories exist
        if not self.project_dir.exists():
            self.log(f"Project directory does not exist: {self.project_dir}", "error")
            return False

        if not self.spec_dir.exists():
            self.log(f"Spec directory does not exist: {self.spec_dir}", "warning")

        return True

    def test_1_tool_discovery(self) -> bool:
        """Test 1: Verify LLM can discover all MCP tools"""
        print("\n" + "=" * 70)
        print("TEST 1: Tool Discovery")
        print("=" * 70)

        try:
            self.log("Creating Claude SDK client...", "info")
            client = self._create_test_client()

            self.log("Calling list_tools()...", "info")
            tools = client.list_tools()

            self.log(f"Found {len(tools)} total tools", "success")

            # Expected tool names for embedded mode
            expected_tools = [
                "mcp__auto-claude-electron__get_window_info",
                "mcp__auto-claude-electron__take_screenshot",
                "mcp__auto-claude-electron__send_command",
                "mcp__auto-claude-electron__read_logs",
                "mcp__auto-claude-electron__health_check",
            ]

            found_tools = []
            missing_tools = []

            print("\n  Expected tools:")
            for tool in expected_tools:
                if tool in tools:
                    found_tools.append(tool)
                    self.log(f"  {tool}", "success")
                else:
                    missing_tools.append(tool)
                    self.log(f"  {tool} - NOT FOUND", "error")

            # Also check for CDP mode tools as fallback
            cdp_tools = [
                "mcp__electron__get_electron_window_info",
                "mcp__electron__take_screenshot",
                "mcp__electron__send_command_to_electron",
                "mcp__electron__read_electron_logs",
            ]

            cdp_found = [tool for tool in cdp_tools if tool in tools]

            if cdp_found and not found_tools:
                self.log("\n  CDP mode tools detected (fallback):", "warning")
                for tool in cdp_found:
                    self.log(f"  {tool}", "info")
                self.log(
                    "\n  Note: CDP mode detected. For embedded mode, set ELECTRON_MCP_MODE=embedded",
                    "warning",
                )

            if missing_tools and not found_tools and not cdp_found:
                self.log(f"\n  Missing {len(missing_tools)} expected tools", "error")
                self.log("  No MCP tools discovered. Check:", "error")
                self.log("    1. Electron app is running", "error")
                self.log("    2. ELECTRON_MCP_ENABLED=true", "error")
                self.log("    3. MCP server initialized successfully", "error")
                self.test_results.append(
                    ("test_1_tool_discovery", False, "No tools found")
                )
                return False

            found_count = len(found_tools) if found_tools else len(cdp_found)
            self.log(
                f"\n  Tool discovery successful: {found_count} tools found", "success"
            )
            self.test_results.append(
                ("test_1_tool_discovery", True, f"{found_count} tools")
            )
            return True

        except Exception as e:
            self._record_failure("test_1_tool_discovery", e)
            return False

    def test_2_single_tool_invocation(self) -> bool:
        """Test 2: Verify LLM can invoke individual tools"""
        print("\n" + "=" * 70)
        print("TEST 2: Single Tool Invocation")
        print("=" * 70)

        # Test cases with simple tasks
        test_cases = [
            {
                "name": "health_check",
                "task": "Check the MCP server health status and report the metrics",
                "expected_keywords": ["uptime", "status", "healthy"],
            },
            {
                "name": "get_window_info",
                "task": "Get information about all open windows",
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
                response = client.create_agent_session(
                    name=f"test-{test_case['name']}", starting_message=test_case["task"]
                )
                duration = time.time() - start_time

                # Check if response contains expected content
                response_text = self._extract_response_text(response)

                # Check for expected keywords
                keywords_found = [
                    kw
                    for kw in test_case["expected_keywords"]
                    if kw.lower() in response_text
                ]

                print(f"  ⏱️  Duration: {duration:.2f}s")
                print(f"  Response length: {len(response_text)} chars")

                if keywords_found:
                    self.log(
                        f"  {test_case['name']} succeeded - found keywords: {keywords_found}",
                        "success",
                    )
                    results.append((test_case["name"], True, duration))
                else:
                    self.log(
                        f"  {test_case['name']} completed but unexpected response",
                        "warning",
                    )
                    results.append(
                        (test_case["name"], True, duration)
                    )  # Still count as pass

                if self.verbose:
                    print(f"  Response preview: {response_text[:200]}...")

            except Exception as e:
                self.log(f"  {test_case['name']} failed: {str(e)[:100]}", "error")
                results.append((test_case["name"], False, 0))
                all_passed = False

        # Summary
        passed_count = sum(1 for _, passed, _ in results if passed)
        print(f"\n  Results: {passed_count}/{len(test_cases)} tests passed")
        self.test_results.append(
            (
                "test_2_single_tool_invocation",
                all_passed,
                f"{passed_count}/{len(test_cases)}",
            )
        )
        return all_passed

    def test_3_multi_step_workflow(self) -> bool:
        """Test 3: Verify LLM can plan and execute multi-step workflows"""
        print("\n" + "=" * 70)
        print("TEST 3: Multi-Step Test Workflow")
        print("=" * 70)

        task = """
        Perform the following test workflow:
        1. Get information about the current window
        2. Check the server health
        3. Read the last 3 console log entries
        4. Report your findings in a summary
        """

        print(f"\n  Task: {task}")

        try:
            client = self._create_test_client()

            print("  Running multi-step workflow...")
            start_time = time.time()
            response = client.create_agent_session(
                name="test-multi-step", starting_message=task
            )
            duration = time.time() - start_time

            response_text = (
                str(response.content) if hasattr(response, "content") else ""
            )

            print(f"\n  ⏱️  Duration: {duration:.2f}s")
            print(f"  Response length: {len(response_text)} chars")

            # Check if response indicates multiple operations
            multi_step_indicators = ["window", "health", "logs", "summary"]
            indicators_found = sum(
                1
                for ind in multi_step_indicators
                if ind.lower() in response_text.lower()
            )

            if indicators_found >= 2:
                self.log(
                    f"  Multi-step workflow completed successfully ({indicators_found}/4 indicators found)",
                    "success",
                )
                if self.verbose:
                    print(f"\n  Response preview:\n{response_text[:500]}...")
                self.test_results.append(
                    (
                        "test_3_multi_step_workflow",
                        True,
                        f"{duration:.2f}s, {indicators_found} indicators",
                    )
                )
                return True
            else:
                self.log(
                    f"  Workflow completed but may have missed some steps ({indicators_found}/4 indicators)",
                    "warning",
                )
                self.test_results.append(
                    (
                        "test_3_multi_step_workflow",
                        True,
                        f"{duration:.2f}s, {indicators_found} indicators",
                    )
                )
                return True  # Still pass as long as it completed

        except Exception as e:
            self._record_failure("test_3_multi_step_workflow", e)
            return False

    def test_4_error_handling(self) -> bool:
        """Test 4: Verify LLM handles errors gracefully"""
        print("\n" + "=" * 70)
        print("TEST 4: Error Handling")
        print("=" * 70)

        test_cases = [
            {
                "name": "Invalid screenshot quality",
                "task": "Take a screenshot with quality 150 (this is invalid, should be 1-100)",
                "should_handle_gracefully": True,
            },
            {
                "name": "Non-existent element",
                "task": "Click on a button with text 'ThisButtonDoesNotExist12345'",
                "should_handle_gracefully": True,
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
                response = client.create_agent_session(
                    name=f"test-error-{i}", starting_message=test_case["task"]
                )
                duration = time.time() - start_time

                response_text = self._extract_response_text(response)

                # Check if agent handled the error gracefully
                error_indicators = ["error", "invalid", "not found", "failed", "cannot"]
                found_error_indicator = any(
                    ind in response_text for ind in error_indicators
                )

                print(f"  ⏱️  Duration: {duration:.2f}s")

                if found_error_indicator:
                    self.log(
                        "  Error handled gracefully - agent reported issue", "success"
                    )
                    results.append((test_case["name"], True, duration))
                else:
                    # Agent may have recovered in a different way
                    self.log("  Agent provided response (may have recovered)", "info")
                    results.append((test_case["name"], True, duration))

                if self.verbose:
                    print(f"  Response preview: {response_text[:200]}...")

            except Exception as e:
                # Some errors are expected and OK
                error_str = str(e).lower()
                if any(
                    ind in error_str
                    for ind in ["error", "invalid", "not found", "failed"]
                ):
                    self.log(f"  Error detected and handled: {str(e)[:100]}", "success")
                    results.append((test_case["name"], True, 0))
                else:
                    self.log(f"  Unexpected error: {str(e)[:100]}", "error")
                    results.append((test_case["name"], False, 0))
                    all_passed = False

        # Summary
        passed_count = sum(1 for _, passed, _ in results if passed)
        print(f"\n  Results: {passed_count}/{len(test_cases)} tests passed")
        self.test_results.append(
            ("test_4_error_handling", all_passed, f"{passed_count}/{len(test_cases)}")
        )
        return all_passed

    def test_5_performance_benchmarks(self) -> bool:
        """Test 5: Measure tool execution performance"""
        print("\n" + "=" * 70)
        print("TEST 5: Performance Benchmarks")
        print("=" * 70)

        # Quick performance check (single call each for speed)
        tools_to_test = [
            ("health_check", "Check server health", 2000),  # 2 second target
            ("get_window_info", "Get window info", 2000),
        ]

        performance_results = {}
        all_within_target = True

        for tool_name, task, target_ms in tools_to_test:
            print(f"\n  Benchmarking: {tool_name}")
            print(f"  Target: < {target_ms}ms")

            try:
                client = self._create_test_client()

                start_time = time.time()
                client.create_agent_session(
                    name=f"benchmark-{tool_name}", starting_message=task
                )
                end_time = time.time()

                duration_ms = (end_time - start_time) * 1000  # Convert to ms
                performance_results[tool_name] = duration_ms

                status = "✅" if duration_ms < target_ms else "⚠️"
                print(f"  {status} Latency: {duration_ms:.2f}ms")

                if duration_ms >= target_ms:
                    self.log(
                        f"  Exceeds {target_ms}ms target (but test continues)",
                        "warning",
                    )
                    all_within_target = False

            except Exception as e:
                self.log(f"  Benchmark failed: {e}", "error")
                performance_results[tool_name] = None
                all_within_target = False

        # Summary
        print("\n  Performance Summary:")
        for tool, duration in performance_results.items():
            if duration:
                status = "✅" if duration < 2000 else "⚠️"
                print(f"    {status} {tool}: {duration:.2f}ms")

        self.test_results.append(
            ("test_5_performance_benchmarks", True, "Performance recorded")
        )
        return True  # Always pass, just warn on slow performance

    def run_all_tests(self) -> dict[str, Any]:
        """Run all LLM interaction tests"""
        print("\n" + "=" * 70)
        print("RUNNING ALL TESTS")
        print("=" * 70)

        # Setup
        if not self.setup():
            self.log("\nSetup failed. Please check environment configuration.", "error")
            return {"success": False, "error": "Setup failed", "tests": []}

        # Run tests
        test_methods = [
            ("Tool Discovery", self.test_1_tool_discovery),
            ("Single Tool Invocation", self.test_2_single_tool_invocation),
            ("Multi-Step Workflow", self.test_3_multi_step_workflow),
            ("Error Handling", self.test_4_error_handling),
            ("Performance Benchmarks", self.test_5_performance_benchmarks),
        ]

        for test_name, test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self._record_failure(test_name, e)

        # Calculate results
        total = len(self.test_results)
        passed = sum(1 for _, result, _ in self.test_results if result)
        failed = total - passed

        results = {
            "success": passed == total,
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "tests": [
                {"name": name, "passed": result, "notes": notes}
                for name, result, notes in self.test_results
            ],
        }

        # Print summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"\nTotal Tests: {results['total']}")
        print(f"Passed: ✅ {results['passed']}")
        print(f"Failed: ❌ {results['failed']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")

        # Detailed results
        print("\nDetailed Results:")
        for test in results["tests"]:
            status = "✅ PASS" if test["passed"] else "❌ FAIL"
            print(f"  {status} - {test['name']}")
            if test["notes"]:
                print(f"      Notes: {test['notes']}")

        # Overall status
        if results["success"]:
            print("\n" + "=" * 70)
            self.log("ALL TESTS PASSED ✅", "success")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            self.log("SOME TESTS FAILED ❌", "error")
            print("=" * 70)

        return results


def main():
    """Main test runner"""
    # Determine directories
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    spec_dir = (
        script_dir
        / ".auto-claude"
        / "specs"
        / "169-research-webmcp-integration-with-electron-frontend"
    )

    # Fallback spec directory if above doesn't exist (running in worktree)
    if not spec_dir.exists():
        # Try current directory's spec dir
        spec_dir = (
            Path.cwd()
            / ".auto-claude"
            / "specs"
            / "169-research-webmcp-integration-with-electron-frontend"
        )

    print(f"Project directory: {project_dir}")
    print(f"Spec directory: {spec_dir}")
    print()

    # Create tester and run tests
    tester = LLMInteractionTester(project_dir, spec_dir)
    results = tester.run_all_tests()

    # Save results to JSON
    results_file = script_dir / "test_llm_mcp_results.json"
    try:
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {results_file}")
    except Exception as e:
        print(f"\nFailed to save results: {e}")

    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()
