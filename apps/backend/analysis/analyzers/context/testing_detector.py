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
    JEST_LIBS = ["jest", "@jest/globals", "ts-jest", "@types/jest"]
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

    # Combined E2E testing libraries
    E2E_LIBS = PLAYWRIGHT_LIBS + CYPRESS_LIBS + PUPPETEER_LIBS + SELENIUM_LIBS

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
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Extract package name from requirement spec
                # Handles: package==1.0, package>=1.0, package~=1.0, package
                pkg_name = line.split(">=")[0].split("==")[0].split("~=")[0].split("<=")[0].split()[0]
                if pkg_name:
                    all_deps.add(pkg_name)

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
        pytest_found = False
        for lib in self.PYTEST_LIBS:
            if lib in all_deps:
                if not pytest_found:
                    testing_info["frameworks"].append("pytest")
                    pytest_found = True
                testing_info["libraries"].append(lib)

        # Check for unittest
        unittest_found = False
        for lib in self.UNITTEST_LIBS:
            if lib in all_deps:
                if not unittest_found:
                    testing_info["frameworks"].append("unittest")
                    unittest_found = True
                testing_info["libraries"].append(lib)

        # Check for nose
        nose_found = False
        for lib in self.NOSE_LIBS:
            if lib in all_deps:
                if not nose_found:
                    testing_info["frameworks"].append("nose")
                    nose_found = True
                testing_info["libraries"].append(lib)

        # Check for doctest
        doctest_found = False
        for lib in self.DOCTEST_LIBS:
            if lib in all_deps:
                if not doctest_found:
                    testing_info["frameworks"].append("doctest")
                    doctest_found = True
                testing_info["libraries"].append(lib)

        # Check for hypothesis
        hypothesis_found = False
        for lib in self.HYPOTHESIS_LIBS:
            if lib in all_deps:
                if not hypothesis_found:
                    testing_info["frameworks"].append("hypothesis")
                    hypothesis_found = True
                testing_info["libraries"].append(lib)

    def _detect_js_frameworks(
        self, all_deps: set[str], testing_info: dict[str, Any]
    ) -> None:
        """Detect JavaScript/TypeScript testing frameworks."""
        # Check for jest
        jest_found = False
        for lib in self.JEST_LIBS:
            if lib in all_deps:
                if not jest_found:
                    testing_info["frameworks"].append("jest")
                    jest_found = True
                testing_info["libraries"].append(lib)

        # Check for vitest
        vitest_found = False
        for lib in self.VITEST_LIBS:
            if lib in all_deps:
                if not vitest_found:
                    testing_info["frameworks"].append("vitest")
                    vitest_found = True
                testing_info["libraries"].append(lib)

        # Check for mocha
        mocha_found = False
        for lib in self.MOCHA_LIBS:
            if lib in all_deps:
                if not mocha_found:
                    testing_info["frameworks"].append("mocha")
                    mocha_found = True
                testing_info["libraries"].append(lib)

        # Check for jasmine
        jasmine_found = False
        for lib in self.JASMINE_LIBS:
            if lib in all_deps:
                if not jasmine_found:
                    testing_info["frameworks"].append("jasmine")
                    jasmine_found = True
                testing_info["libraries"].append(lib)

        # Check for ava
        ava_found = False
        for lib in self.AVA_LIBS:
            if lib in all_deps:
                if not ava_found:
                    testing_info["frameworks"].append("ava")
                    ava_found = True
                testing_info["libraries"].append(lib)

    def _detect_e2e_frameworks(
        self, all_deps: set[str], testing_info: dict[str, Any]
    ) -> None:
        """Detect E2E testing frameworks."""
        # Check for playwright
        playwright_found = False
        for lib in self.PLAYWRIGHT_LIBS:
            if lib in all_deps:
                if not playwright_found:
                    testing_info["frameworks"].append("playwright")
                    playwright_found = True
                testing_info["libraries"].append(lib)

        # Check for cypress
        cypress_found = False
        for lib in self.CYPRESS_LIBS:
            if lib in all_deps:
                if not cypress_found:
                    testing_info["frameworks"].append("cypress")
                    cypress_found = True
                testing_info["libraries"].append(lib)

        # Check for puppeteer
        puppeteer_found = False
        for lib in self.PUPPETEER_LIBS:
            if lib in all_deps:
                if not puppeteer_found:
                    testing_info["frameworks"].append("puppeteer")
                    puppeteer_found = True
                testing_info["libraries"].append(lib)

        # Check for selenium
        selenium_found = False
        for lib in self.SELENIUM_LIBS:
            if lib in all_deps:
                if not selenium_found:
                    testing_info["frameworks"].append("selenium")
                    selenium_found = True
                testing_info["libraries"].append(lib)

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
