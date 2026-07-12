#!/usr/bin/env python3
"""
Tests for ServiceAnalyzer testing detection.

Verifies that service analysis (which feeds project_index.json consumed by
coder/QA prompts) surfaces test commands discovered by TestDiscovery for
all supported ecosystems, not just JS/Python.
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analysis.analyzers import ServiceAnalyzer


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestServiceAnalyzerTesting:
    """Tests for _detect_testing via TestDiscovery."""

    def test_python_service_gets_test_commands(self, temp_dir):
        """Python service surfaces pytest command and targeted template."""
        (temp_dir / "requirements.txt").write_text("pytest\n")
        (temp_dir / "tests").mkdir()

        analyzer = ServiceAnalyzer(temp_dir, "backend")
        analyzer._detect_testing()

        assert analyzer.analysis["testing"] == "pytest"
        assert analyzer.analysis["test_command"] == "pytest"
        assert analyzer.analysis["targeted_test_command"] == "pytest {target}"
        assert analyzer.analysis["test_directory"] == "tests"

    def test_gradle_service_gets_test_commands(self, temp_dir):
        """JVM/Gradle service surfaces gradle test commands."""
        (temp_dir / "build.gradle.kts").write_text('plugins { kotlin("jvm") }')
        (temp_dir / "gradlew").write_text("#!/bin/sh")

        analyzer = ServiceAnalyzer(temp_dir, "api")
        analyzer._detect_testing()

        assert analyzer.analysis["testing"] == "gradle"
        assert analyzer.analysis["test_command"] == "./gradlew test"
        assert (
            analyzer.analysis["targeted_test_command"]
            == "./gradlew test --tests {target}"
        )

    def test_js_service_separates_unit_and_e2e(self, temp_dir):
        """JS service reports unit and e2e frameworks separately."""
        (temp_dir / "package.json").write_text(
            '{"devDependencies": {"vitest": "^1.0.0", "cypress": "^13.0.0"}}'
        )

        analyzer = ServiceAnalyzer(temp_dir, "frontend")
        analyzer._detect_testing()

        assert analyzer.analysis["testing"] == "vitest"
        assert analyzer.analysis["e2e_testing"] == "cypress"

    def test_service_without_tests_has_no_test_command(self, temp_dir):
        """Service without test setup gets no test keys."""
        (temp_dir / "main.zig").write_text("pub fn main() void {}")

        analyzer = ServiceAnalyzer(temp_dir, "tool")
        analyzer._detect_testing()

        assert "test_command" not in analyzer.analysis
        assert "targeted_test_command" not in analyzer.analysis
