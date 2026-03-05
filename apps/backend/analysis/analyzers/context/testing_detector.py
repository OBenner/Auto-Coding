"""
Testing Framework Detector Module
==================================

Detects testing frameworks and patterns:
- Python testing frameworks (pytest, unittest, nose2, doctest, hypothesis)
- JavaScript/TypeScript testing frameworks (jest, vitest, mocha, jasmine, ava)
- E2E testing frameworks (playwright, cypress, puppeteer, selenium)
- Test configuration files (pytest.ini, jest.config.js, vitest.config.ts)
- Test directories (tests/, test/, __tests__, spec/, e2e/)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import BaseAnalyzer


class TestingDetector(BaseAnalyzer):
    """Detects testing frameworks and patterns."""

    # Python testing libraries
    PYTEST_LIBS = ["pytest", "pytest-cov", "pytest-asyncio", "pytest-django", "pytest-mock"]
    UNITTEST_LIBS = ["unittest", "unittest2"]
    NOSE_LIBS = ["nose", "nose2"]
    DOCTEST_LIBS = ["doctest"]
    HYPOTHESIS_LIBS = ["hypothesis"]

    # JavaScript/TypeScript testing libraries
    JEST_LIBS = ["jest", "@jest/globals", "ts-jest"]
    VITEST_LIBS = ["vitest", "@vitest/ui"]
    MOCHA_LIBS = ["mocha", "chai", "@types/mocha"]
    JASMINE_LIBS = ["jasmine", "@types/jasmine"]
    AVA_LIBS = ["ava"]

    # Combined JS/TS testing libraries
    JS_LIBS = JEST_LIBS + VITEST_LIBS + MOCHA_LIBS + JASMINE_LIBS + AVA_LIBS

    # E2E testing libraries
    PLAYWRIGHT_LIBS = ["playwright", "@playwright/test"]
    CYPRESS_LIBS = ["cypress"]
    PUPPETEER_LIBS = ["puppeteer"]
    SELENIUM_LIBS = ["selenium"]

    # Test configuration files
    CONFIG_FILES = [
        "pytest.ini",
        "pyproject.toml",
        "setup.cfg",
        "tox.ini",
        "jest.config.js",
        "jest.config.ts",
        "vitest.config.js",
        "vitest.config.ts",
        "playwright.config.ts",
        "playwright.config.js",
        "cypress.config.js",
        "cypress.config.ts",
        ".mocharc.js",
        ".mocharc.json",
        ".mocharc.yml",
    ]

    # Test directories
    TEST_DIRS = [
        "tests",
        "test",
        "__tests__",
        "spec",
        "specs",
        "e2e",
        "e2e-tests",
        "integration",
        "test-integration",
    ]

    def __init__(self, path: Path, analysis: dict[str, Any]):
        super().__init__(path)
        self.analysis = analysis

    def detect(self) -> None:
        """
        Detect testing frameworks and patterns.

        Detects: Python frameworks (pytest, unittest), JS/TS frameworks (jest, vitest),
        E2E frameworks (playwright, cypress), config files, and test directories.
        """
        testing_info = {
            "frameworks": [],
            "libraries": [],
            "config_files": [],
            "test_directories": [],
        }

        # Get all dependencies
        all_deps = self._get_all_dependencies()

        # Detect Python testing frameworks
        self._detect_python_frameworks(all_deps, testing_info)

        # Detect JavaScript/TypeScript testing frameworks
        self._detect_js_frameworks(all_deps, testing_info)

        # Detect E2E testing frameworks
        self._detect_e2e_frameworks(all_deps, testing_info)

        # Find test configuration files
        testing_info["config_files"] = self._find_config_files()

        # Find test directories
        testing_info["test_directories"] = self._find_test_directories()

        # Remove duplicates from frameworks
        testing_info["frameworks"] = list(set(testing_info["frameworks"]))

        if testing_info["frameworks"] or testing_info["config_files"] or testing_info["test_directories"]:
            self.analysis["testing"] = testing_info

    def _get_all_dependencies(self) -> set[str]:
        """Extract all dependencies from Python and Node.js projects."""
        all_deps = set()

        # Python dependencies
        if self._exists("requirements.txt"):
            content = self._read_file("requirements.txt")
            all_deps.update(content.splitlines())

        # Node.js dependencies
        pkg = self._read_json("package.json")
        if pkg:
            all_deps.update(pkg.get("dependencies", {}).keys())
            all_deps.update(pkg.get("devDependencies", {}).keys())

        return all_deps

    def _detect_python_frameworks(
        self, all_deps: set[str], testing_info: dict[str, Any]
    ) -> None:
        """Detect Python testing frameworks."""
        # Check for pytest
        for lib in self.PYTEST_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("pytest")
                testing_info["libraries"].append(lib)
                break

        # Check for unittest
        for lib in self.UNITTEST_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("unittest")
                testing_info["libraries"].append(lib)
                break

        # Check for nose
        for lib in self.NOSE_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("nose")
                testing_info["libraries"].append(lib)
                break

        # Check for doctest
        for lib in self.DOCTEST_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("doctest")
                testing_info["libraries"].append(lib)
                break

        # Check for hypothesis
        for lib in self.HYPOTHESIS_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("hypothesis")
                testing_info["libraries"].append(lib)
                break

    def _detect_js_frameworks(
        self, all_deps: set[str], testing_info: dict[str, Any]
    ) -> None:
        """Detect JavaScript/TypeScript testing frameworks."""
        # Check for jest
        for lib in self.JEST_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("jest")
                testing_info["libraries"].append(lib)
                break

        # Check for vitest
        for lib in self.VITEST_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("vitest")
                testing_info["libraries"].append(lib)
                break

        # Check for mocha
        for lib in self.MOCHA_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("mocha")
                testing_info["libraries"].append(lib)
                break

        # Check for jasmine
        for lib in self.JASMINE_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("jasmine")
                testing_info["libraries"].append(lib)
                break

        # Check for ava
        for lib in self.AVA_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("ava")
                testing_info["libraries"].append(lib)
                break

    def _detect_e2e_frameworks(
        self, all_deps: set[str], testing_info: dict[str, Any]
    ) -> None:
        """Detect E2E testing frameworks."""
        # Check for playwright
        for lib in self.PLAYWRIGHT_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("playwright")
                testing_info["libraries"].append(lib)
                break

        # Check for cypress
        for lib in self.CYPRESS_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("cypress")
                testing_info["libraries"].append(lib)
                break

        # Check for puppeteer
        for lib in self.PUPPETEER_LIBS:
            if lib in all_deps:
                testing_info["frameworks"].append("puppeteer")
                testing_info["libraries"].append(lib)
                break

    def _find_config_files(self) -> list[str]:
        """Find test configuration files."""
        found_configs = []
        for config_file in self.CONFIG_FILES:
            if self._exists(config_file):
                found_configs.append(config_file)
        return found_configs

    def _find_test_directories(self) -> list[str]:
        """Find test directories."""
        found_dirs = []
        for test_dir in self.TEST_DIRS:
            if self._exists(test_dir):
                # Check if it's a directory
                if (self.path / test_dir).is_dir():
                    found_dirs.append(test_dir)
        return found_dirs
