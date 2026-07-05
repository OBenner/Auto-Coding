#!/usr/bin/env python3
"""
Test Discovery Module
=====================

Detects test frameworks, test commands, and test directories in a project.
This module analyzes project configuration files to discover how tests
should be run.

The test discovery results are used by:
- QA Agent: To determine what test commands to run
- Test Creator: To know what framework to use when creating tests
- Planner: To include correct test commands in verification strategy

Usage:
    from test_discovery import TestDiscovery

    discovery = TestDiscovery()
    result = discovery.discover(project_dir)

    print(f"Test frameworks: {result['frameworks']}")
    print(f"Test command: {result['test_command']}")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class TestFramework:
    """
    Represents a detected test framework.

    Attributes:
        name: Name of the framework (e.g., "pytest", "jest", "vitest")
        type: Type of testing (unit, integration, e2e, all)
        command: Command to run tests
        config_file: Configuration file if found
        version: Version if detected
        coverage_command: Command for coverage if available
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    name: str
    type: str  # unit, integration, e2e, all
    command: str
    config_file: str | None = None
    version: str | None = None
    coverage_command: str | None = None


@dataclass
class TestDiscoveryResult:
    """
    Result of test framework discovery.

    Attributes:
        frameworks: List of detected test frameworks
        test_command: Primary test command to run
        test_directories: Discovered test directories
        package_manager: Detected package manager
        has_tests: Whether any test files were found
        coverage_command: Command for coverage if available
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    frameworks: list[TestFramework] = field(default_factory=list)
    test_command: str = ""
    test_directories: list[str] = field(default_factory=list)
    package_manager: str = ""
    has_tests: bool = False
    coverage_command: str | None = None


# =============================================================================
# FRAMEWORK DETECTORS
# =============================================================================


# Pattern-based framework detection
FRAMEWORK_PATTERNS = {
    # JavaScript/TypeScript
    "jest": {
        "config_files": [
            "jest.config.js",
            "jest.config.ts",
            "jest.config.mjs",
            "jest.config.cjs",
        ],
        "package_key": "jest",
        "type": "unit",
        "command": "npx jest",
        "coverage_command": "npx jest --coverage",
    },
    "vitest": {
        "config_files": ["vitest.config.js", "vitest.config.ts", "vitest.config.mjs"],
        "package_key": "vitest",
        "type": "unit",
        "command": "npx vitest run",
        "coverage_command": "npx vitest run --coverage",
    },
    "mocha": {
        "config_files": [
            ".mocharc.js",
            ".mocharc.json",
            ".mocharc.yaml",
            ".mocharc.yml",
        ],
        "package_key": "mocha",
        "type": "unit",
        "command": "npx mocha",
        "coverage_command": "npx nyc mocha",
    },
    "playwright": {
        "config_files": ["playwright.config.js", "playwright.config.ts"],
        "package_key": "@playwright/test",
        "type": "e2e",
        "command": "npx playwright test",
        "coverage_command": None,
    },
    "cypress": {
        "config_files": ["cypress.config.js", "cypress.config.ts", "cypress.json"],
        "package_key": "cypress",
        "type": "e2e",
        "command": "npx cypress run",
        "coverage_command": None,
    },
    # Python
    "pytest": {
        "config_files": ["pytest.ini", "pyproject.toml", "setup.cfg", "conftest.py"],
        "pyproject_key": "pytest",
        "requirements_key": "pytest",
        "type": "all",
        "command": "pytest",
        "coverage_command": "pytest --cov",
    },
    "unittest": {
        "config_files": [],
        "type": "unit",
        "command": "python -m unittest discover",
        "coverage_command": "coverage run -m unittest discover",
    },
    # Rust
    "cargo_test": {
        "config_files": ["Cargo.toml"],
        "type": "all",
        "command": "cargo test",
        "coverage_command": "cargo tarpaulin",
    },
    # Go
    "go_test": {
        "config_files": ["go.mod"],
        "type": "all",
        "command": "go test ./...",
        "coverage_command": "go test -cover ./...",
    },
    # Ruby
    "rspec": {
        "config_files": [".rspec", "spec/spec_helper.rb"],
        "gemfile_key": "rspec",
        "type": "all",
        "command": "bundle exec rspec",
        "coverage_command": "bundle exec rspec --format documentation",
    },
    "minitest": {
        "config_files": [],
        "gemfile_key": "minitest",
        "type": "unit",
        "command": "bundle exec rake test",
        "coverage_command": None,
    },
    # Java/Kotlin (JVM)
    "maven": {
        "config_files": ["pom.xml"],
        "type": "all",
        "command": "mvn test",
        "coverage_command": None,
    },
    "gradle": {
        "config_files": ["build.gradle", "build.gradle.kts"],
        "type": "all",
        "command": "gradle test",
        "coverage_command": None,
    },
    # Scala
    "sbt": {
        "config_files": ["build.sbt"],
        "type": "all",
        "command": "sbt test",
        "coverage_command": None,
    },
    # C#/.NET
    "dotnet_test": {
        "config_files": [],
        "type": "all",
        "command": "dotnet test",
        "coverage_command": 'dotnet test --collect:"XPlat Code Coverage"',
    },
    # C/C++
    "ctest": {
        "config_files": ["CMakeLists.txt"],
        "type": "all",
        "command": "ctest --test-dir build --output-on-failure",
        "coverage_command": None,
    },
    "make_test": {
        "config_files": ["Makefile"],
        "type": "all",
        "command": "make test",
        "coverage_command": None,
    },
    # PHP
    "phpunit": {
        "config_files": ["phpunit.xml", "phpunit.xml.dist"],
        "type": "all",
        "command": "vendor/bin/phpunit",
        "coverage_command": None,
    },
    # Elixir
    "mix_test": {
        "config_files": ["mix.exs"],
        "type": "all",
        "command": "mix test",
        "coverage_command": "mix test --cover",
    },
    # Swift
    "swift_test": {
        "config_files": ["Package.swift"],
        "type": "all",
        "command": "swift test",
        "coverage_command": "swift test --enable-code-coverage",
    },
    # Dart/Flutter
    "dart_test": {
        "config_files": ["pubspec.yaml"],
        "type": "all",
        "command": "dart test",
        "coverage_command": None,
    },
    "flutter_test": {
        "config_files": ["pubspec.yaml"],
        "type": "all",
        "command": "flutter test",
        "coverage_command": "flutter test --coverage",
    },
    # Zig
    "zig_test": {
        "config_files": ["build.zig"],
        "type": "all",
        "command": "zig build test",
        "coverage_command": None,
    },
    # Haskell
    "stack_test": {
        "config_files": ["stack.yaml"],
        "type": "all",
        "command": "stack test",
        "coverage_command": None,
    },
    "cabal_test": {
        "config_files": ["cabal.project"],
        "type": "all",
        "command": "cabal test",
        "coverage_command": None,
    },
}


# =============================================================================
# TEST DISCOVERY
# =============================================================================


class TestDiscovery:
    """
    Discovers test frameworks and configurations in a project.

    Analyzes:
    - Package files (package.json, pyproject.toml, Cargo.toml, etc.)
    - Configuration files (jest.config.js, pytest.ini, etc.)
    - Directory structure (tests/, spec/, __tests__/)
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    def __init__(self) -> None:
        """Initialize the test discovery."""
        self._cache: dict[str, TestDiscoveryResult] = {}

    def discover(self, project_dir: Path) -> TestDiscoveryResult:
        """
        Discover test frameworks and configuration in the project.

        Args:
            project_dir: Path to the project root

        Returns:
            TestDiscoveryResult with detected frameworks and commands
        """
        project_dir = Path(project_dir)
        cache_key = str(project_dir.resolve())

        if cache_key in self._cache:
            return self._cache[cache_key]

        result = TestDiscoveryResult()

        # Detect package manager
        result.package_manager = self._detect_package_manager(project_dir)

        # Discover frameworks based on project type
        if (project_dir / "package.json").exists():
            self._discover_js_frameworks(project_dir, result)

        # Check for Python project indicators
        python_indicators = [
            project_dir / "pyproject.toml",
            project_dir / "requirements.txt",
            project_dir / "setup.py",
            project_dir / "pytest.ini",
            project_dir / "conftest.py",
            project_dir / "tests" / "conftest.py",
        ]
        if any(p.exists() for p in python_indicators):
            self._discover_python_frameworks(project_dir, result)

        if (project_dir / "Cargo.toml").exists():
            self._discover_rust_frameworks(project_dir, result)
        if (project_dir / "go.mod").exists():
            self._discover_go_frameworks(project_dir, result)
        if (project_dir / "Gemfile").exists():
            self._discover_ruby_frameworks(project_dir, result)

        # Additional language ecosystems (each method checks its own markers)
        self._discover_jvm_frameworks(project_dir, result)
        self._discover_sbt_frameworks(project_dir, result)
        self._discover_dotnet_frameworks(project_dir, result)
        self._discover_c_cpp_frameworks(project_dir, result)
        self._discover_php_frameworks(project_dir, result)
        self._discover_elixir_frameworks(project_dir, result)
        self._discover_swift_frameworks(project_dir, result)
        self._discover_dart_frameworks(project_dir, result)
        self._discover_zig_frameworks(project_dir, result)
        self._discover_haskell_frameworks(project_dir, result)

        # Find test directories
        result.test_directories = self._find_test_directories(project_dir)

        # Check if tests exist
        result.has_tests = self._has_test_files(project_dir, result.test_directories)

        # Set primary test command
        if result.frameworks:
            result.test_command = result.frameworks[0].command

        # Set coverage command from first framework that has one
        if not result.coverage_command:
            for framework in result.frameworks:
                if framework.coverage_command:
                    result.coverage_command = framework.coverage_command
                    break

        self._cache[cache_key] = result
        return result

    def _detect_package_manager(self, project_dir: Path) -> str:
        """Detect the package manager used by the project."""
        if (project_dir / "pnpm-lock.yaml").exists():
            return "pnpm"
        if (project_dir / "yarn.lock").exists():
            return "yarn"
        if (project_dir / "package-lock.json").exists():
            return "npm"
        if (project_dir / "bun.lockb").exists() or (project_dir / "bun.lock").exists():
            return "bun"
        if (project_dir / "uv.lock").exists():
            return "uv"
        if (project_dir / "poetry.lock").exists():
            return "poetry"
        if (project_dir / "Pipfile.lock").exists():
            return "pipenv"
        if (project_dir / "Cargo.lock").exists():
            return "cargo"
        if (project_dir / "go.sum").exists():
            return "go"
        if (project_dir / "Gemfile.lock").exists():
            return "bundler"
        return ""

    def _discover_js_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover JavaScript/TypeScript test frameworks."""
        package_json = project_dir / "package.json"
        if not package_json.exists():
            return

        try:
            with open(package_json, encoding="utf-8") as f:
                pkg = json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return

        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}
        scripts = pkg.get("scripts", {})

        # Check for test frameworks in dependencies
        for name, pattern in FRAMEWORK_PATTERNS.items():
            if "package_key" not in pattern:
                continue

            if pattern["package_key"] in all_deps:
                # Check for config file
                config_file = None
                for cf in pattern.get("config_files", []):
                    if (project_dir / cf).exists():
                        config_file = cf
                        break

                # Get version
                version = all_deps.get(pattern["package_key"], "")
                if version.startswith("^") or version.startswith("~"):
                    version = version[1:]

                # Determine command - prefer npm scripts if available
                command = pattern["command"]
                if "test" in scripts and pattern["package_key"] in scripts.get(
                    "test", ""
                ):
                    command = f"{result.package_manager or 'npm'} test"

                result.frameworks.append(
                    TestFramework(
                        name=name,
                        type=pattern["type"],
                        command=command,
                        config_file=config_file,
                        version=version,
                        coverage_command=pattern.get("coverage_command"),
                    )
                )

        # Check npm scripts for test commands
        if not result.frameworks and "test" in scripts:
            test_script = scripts["test"]
            if (
                test_script
                and test_script != 'echo "Error: no test specified" && exit 1'
            ):
                # Try to infer framework from script
                framework_name = "npm_test"
                framework_type = "unit"

                if "jest" in test_script:
                    framework_name = "jest"
                elif "vitest" in test_script:
                    framework_name = "vitest"
                elif "mocha" in test_script:
                    framework_name = "mocha"
                elif "playwright" in test_script:
                    framework_name = "playwright"
                    framework_type = "e2e"
                elif "cypress" in test_script:
                    framework_name = "cypress"
                    framework_type = "e2e"

                result.frameworks.append(
                    TestFramework(
                        name=framework_name,
                        type=framework_type,
                        command=f"{result.package_manager or 'npm'} test",
                        config_file=None,
                    )
                )

    def _discover_python_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover Python test frameworks."""
        # Check for pytest.ini first (explicit pytest config)
        if (project_dir / "pytest.ini").exists():
            if not any(f.name == "pytest" for f in result.frameworks):
                result.frameworks.append(
                    TestFramework(
                        name="pytest",
                        type="all",
                        command="pytest",
                        config_file="pytest.ini",
                    )
                )

        # Check pyproject.toml
        pyproject = project_dir / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")

            # Check for pytest
            if "pytest" in content:
                if not any(f.name == "pytest" for f in result.frameworks):
                    config_file = (
                        "pyproject.toml" if "[tool.pytest" in content else None
                    )
                    result.frameworks.append(
                        TestFramework(
                            name="pytest",
                            type="all",
                            command="pytest",
                            config_file=config_file,
                        )
                    )

        # Check requirements.txt
        requirements = project_dir / "requirements.txt"
        if requirements.exists():
            content = requirements.read_text(encoding="utf-8").lower()
            if "pytest" in content and not any(
                f.name == "pytest" for f in result.frameworks
            ):
                result.frameworks.append(
                    TestFramework(
                        name="pytest",
                        type="all",
                        command="pytest",
                        config_file=None,
                    )
                )

        # Check for conftest.py (pytest marker)
        conftest_root = project_dir / "conftest.py"
        conftest_tests = project_dir / "tests" / "conftest.py"
        if conftest_root.exists() or conftest_tests.exists():
            if not any(f.name == "pytest" for f in result.frameworks):
                result.frameworks.append(
                    TestFramework(
                        name="pytest",
                        type="all",
                        command="pytest",
                        config_file="conftest.py",
                    )
                )

        # Fall back to unittest if test files exist but no framework detected
        if not result.frameworks:
            test_dirs = self._find_test_directories(project_dir)
            if test_dirs:
                result.frameworks.append(
                    TestFramework(
                        name="unittest",
                        type="unit",
                        command="python -m unittest discover",
                        config_file=None,
                    )
                )

    def _discover_rust_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover Rust test frameworks."""
        cargo_toml = project_dir / "Cargo.toml"
        if cargo_toml.exists():
            result.frameworks.append(
                TestFramework(
                    name="cargo_test",
                    type="all",
                    command="cargo test",
                    config_file="Cargo.toml",
                )
            )

    def _discover_go_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover Go test frameworks."""
        go_mod = project_dir / "go.mod"
        if go_mod.exists():
            result.frameworks.append(
                TestFramework(
                    name="go_test",
                    type="all",
                    command="go test ./...",
                    config_file="go.mod",
                )
            )

    def _discover_ruby_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover Ruby test frameworks."""
        gemfile = project_dir / "Gemfile"
        if not gemfile.exists():
            return

        content = gemfile.read_text(encoding="utf-8").lower()

        if "rspec" in content or (project_dir / ".rspec").exists():
            result.frameworks.append(
                TestFramework(
                    name="rspec",
                    type="all",
                    command="bundle exec rspec",
                    config_file=".rspec" if (project_dir / ".rspec").exists() else None,
                )
            )
        elif "minitest" in content:
            result.frameworks.append(
                TestFramework(
                    name="minitest",
                    type="unit",
                    command="bundle exec rake test",
                    config_file=None,
                )
            )

    def _discover_jvm_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover JVM (Maven/Gradle) test setups."""
        if (project_dir / "pom.xml").exists():
            result.frameworks.append(
                TestFramework(
                    name="maven",
                    type="all",
                    command="mvn test",
                    config_file="pom.xml",
                )
            )

        gradle_config = next(
            (
                f
                for f in ("build.gradle", "build.gradle.kts")
                if (project_dir / f).exists()
            ),
            None,
        )
        if gradle_config:
            # Prefer the wrapper when the project ships one
            command = (
                "./gradlew test"
                if (project_dir / "gradlew").exists()
                else "gradle test"
            )
            result.frameworks.append(
                TestFramework(
                    name="gradle",
                    type="all",
                    command=command,
                    config_file=gradle_config,
                )
            )

    def _discover_sbt_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover Scala (sbt) test setups."""
        if (project_dir / "build.sbt").exists():
            result.frameworks.append(
                TestFramework(
                    name="sbt",
                    type="all",
                    command="sbt test",
                    config_file="build.sbt",
                )
            )

    def _discover_dotnet_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover .NET test setups from solution/project files."""
        candidates = (
            list(project_dir.glob("*.sln"))
            + list(project_dir.glob("*.csproj"))
            + list(project_dir.glob("*/*.csproj"))
        )
        if candidates:
            result.frameworks.append(
                TestFramework(
                    name="dotnet_test",
                    type="all",
                    command="dotnet test",
                    config_file=str(candidates[0].relative_to(project_dir)),
                    coverage_command='dotnet test --collect:"XPlat Code Coverage"',
                )
            )

    def _discover_c_cpp_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover C/C++ test setups (CTest, Makefile test targets)."""
        cmake_file = project_dir / "CMakeLists.txt"
        if cmake_file.exists():
            try:
                content = cmake_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                content = ""
            if any(
                marker in content
                for marker in ("enable_testing", "add_test", "include(CTest")
            ):
                result.frameworks.append(
                    TestFramework(
                        name="ctest",
                        type="all",
                        command="ctest --test-dir build --output-on-failure",
                        config_file="CMakeLists.txt",
                    )
                )
                return

        makefile = project_dir / "Makefile"
        if makefile.exists():
            try:
                content = makefile.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                content = ""
            for target in ("test", "check"):
                if re.search(rf"^{target}\s*:", content, re.MULTILINE):
                    result.frameworks.append(
                        TestFramework(
                            name="make_test",
                            type="all",
                            command=f"make {target}",
                            config_file="Makefile",
                        )
                    )
                    break

    def _discover_php_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover PHP test frameworks (PHPUnit)."""
        config_file = next(
            (
                f
                for f in ("phpunit.xml", "phpunit.xml.dist")
                if (project_dir / f).exists()
            ),
            None,
        )

        has_phpunit_dep = False
        composer_json = (project_dir / "composer.json").resolve()
        # Only read composer.json if it did not resolve (e.g. via symlink)
        # outside the project directory
        if composer_json.exists() and composer_json.is_relative_to(
            project_dir.resolve()
        ):
            try:
                with open(composer_json, encoding="utf-8") as f:
                    composer = json.load(f)
                deps = {
                    **composer.get("require", {}),
                    **composer.get("require-dev", {}),
                }
                has_phpunit_dep = "phpunit/phpunit" in deps
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                pass

        if config_file or has_phpunit_dep:
            result.frameworks.append(
                TestFramework(
                    name="phpunit",
                    type="all",
                    command="vendor/bin/phpunit",
                    config_file=config_file,
                )
            )

    def _discover_elixir_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover Elixir test setups (ExUnit via mix)."""
        if (project_dir / "mix.exs").exists():
            result.frameworks.append(
                TestFramework(
                    name="mix_test",
                    type="all",
                    command="mix test",
                    config_file="mix.exs",
                    coverage_command="mix test --cover",
                )
            )

    def _discover_swift_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover Swift Package Manager test setups."""
        if (project_dir / "Package.swift").exists():
            result.frameworks.append(
                TestFramework(
                    name="swift_test",
                    type="all",
                    command="swift test",
                    config_file="Package.swift",
                    coverage_command="swift test --enable-code-coverage",
                )
            )

    def _discover_dart_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover Dart/Flutter test setups."""
        pubspec = project_dir / "pubspec.yaml"
        if not pubspec.exists():
            return

        try:
            content = pubspec.read_text(encoding="utf-8").lower()
        except (OSError, UnicodeDecodeError):
            content = ""

        if "flutter" in content:
            result.frameworks.append(
                TestFramework(
                    name="flutter_test",
                    type="all",
                    command="flutter test",
                    config_file="pubspec.yaml",
                    coverage_command="flutter test --coverage",
                )
            )
        else:
            result.frameworks.append(
                TestFramework(
                    name="dart_test",
                    type="all",
                    command="dart test",
                    config_file="pubspec.yaml",
                )
            )

    def _discover_zig_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover Zig test setups."""
        if (project_dir / "build.zig").exists():
            result.frameworks.append(
                TestFramework(
                    name="zig_test",
                    type="all",
                    command="zig build test",
                    config_file="build.zig",
                )
            )

    def _discover_haskell_frameworks(
        self, project_dir: Path, result: TestDiscoveryResult
    ) -> None:
        """Discover Haskell test setups (stack or cabal)."""
        if (project_dir / "stack.yaml").exists():
            result.frameworks.append(
                TestFramework(
                    name="stack_test",
                    type="all",
                    command="stack test",
                    config_file="stack.yaml",
                )
            )
        elif (project_dir / "cabal.project").exists() or list(
            project_dir.glob("*.cabal")
        ):
            result.frameworks.append(
                TestFramework(
                    name="cabal_test",
                    type="all",
                    command="cabal test",
                    config_file=None,
                )
            )

    def _find_test_directories(self, project_dir: Path) -> list[str]:
        """Find test directories in the project."""
        test_dir_patterns = [
            "tests",
            "test",
            "spec",
            "__tests__",
            "specs",
            "test_*",
        ]

        found_dirs = []
        for pattern in test_dir_patterns:
            if pattern.endswith("*"):
                # Glob pattern
                for d in project_dir.glob(pattern):
                    if d.is_dir():
                        found_dirs.append(str(d.relative_to(project_dir)))
            else:
                # Exact name
                test_dir = project_dir / pattern
                if test_dir.is_dir():
                    found_dirs.append(pattern)

        return found_dirs

    def _has_test_files(self, project_dir: Path, test_directories: list[str]) -> bool:
        """Check if any test files exist."""
        test_file_patterns = [
            "**/test_*.py",
            "**/*_test.py",
            "**/*.test.js",
            "**/*.test.ts",
            "**/*.test.tsx",
            "**/*.spec.js",
            "**/*.spec.ts",
            "**/*.spec.tsx",
            "**/test_*.go",
            "**/*_test.go",
            "**/*_test.rs",
            "**/spec/**/*_spec.rb",
            "**/*Test.java",
            "**/*Test.kt",
            "**/*Tests.cs",
            "**/*Test.php",
            "**/*_test.exs",
            "**/*_test.dart",
            "**/*Tests.swift",
            "**/*_test.cpp",
            "**/*_test.cc",
        ]

        # Check in test directories
        for test_dir in test_directories:
            test_path = project_dir / test_dir
            if test_path.exists():
                for pattern in test_file_patterns:
                    if list(test_path.glob(pattern.replace("**/", ""))):
                        return True

        # Check project-wide
        for pattern in test_file_patterns:
            if list(project_dir.glob(pattern)):
                return True

        return False

    def to_dict(self, result: TestDiscoveryResult) -> dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "frameworks": [
                {
                    "name": f.name,
                    "type": f.type,
                    "command": f.command,
                    "config_file": f.config_file,
                    "version": f.version,
                    "coverage_command": f.coverage_command,
                }
                for f in result.frameworks
            ],
            "test_command": result.test_command,
            "test_directories": result.test_directories,
            "package_manager": result.package_manager,
            "has_tests": result.has_tests,
            "coverage_command": result.coverage_command,
        }

    def clear_cache(self) -> None:
        """Clear the internal cache."""
        self._cache.clear()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def discover_tests(project_dir: Path) -> TestDiscoveryResult:
    """
    Convenience function to discover tests in a project.

    Args:
        project_dir: Path to project root

    Returns:
        TestDiscoveryResult with detected frameworks
    """
    discovery = TestDiscovery()
    return discovery.discover(project_dir)


def get_test_command(project_dir: Path) -> str:
    """
    Get the primary test command for a project.

    Args:
        project_dir: Path to project root

    Returns:
        Test command string, or empty string if not found
    """
    discovery = TestDiscovery()
    result = discovery.discover(project_dir)
    return result.test_command


def get_test_frameworks(project_dir: Path) -> list[str]:
    """
    Get list of test framework names in a project.

    Args:
        project_dir: Path to project root

    Returns:
        List of framework names
    """
    discovery = TestDiscovery()
    result = discovery.discover(project_dir)
    return [f.name for f in result.frameworks]


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Discover test frameworks")
    parser.add_argument("project_dir", type=Path, help="Path to project root")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    discovery = TestDiscovery()
    result = discovery.discover(args.project_dir)

    if args.json:
        print(json.dumps(discovery.to_dict(result), indent=2))
    else:
        print(f"Package Manager: {result.package_manager or 'unknown'}")
        print(f"Has Tests: {result.has_tests}")
        print(f"Test Command: {result.test_command or 'none'}")
        print(f"Test Directories: {', '.join(result.test_directories) or 'none'}")
        print(f"Coverage Command: {result.coverage_command or 'none'}")
        print(f"\nFrameworks ({len(result.frameworks)}):")
        for f in result.frameworks:
            print(f"  - {f.name} ({f.type})")
            print(f"    Command: {f.command}")
            if f.config_file:
                print(f"    Config: {f.config_file}")
            if f.version:
                print(f"    Version: {f.version}")


if __name__ == "__main__":
    main()
