#!/usr/bin/env python3
"""
Tests for Testing Framework Detector
=====================================

Tests the testing_detector.py module functionality including:
- Python testing framework detection (pytest, unittest, nose2, doctest, hypothesis)
- JavaScript/TypeScript testing framework detection (jest, vitest, mocha, jasmine, ava)
- E2E testing framework detection (playwright, cypress, puppeteer, selenium)
- Test configuration file detection (pytest.ini, jest.config.js, vitest.config.ts)
- Test directory detection (tests/, test/, __tests__, spec/, e2e/)
"""

import json
from pathlib import Path

from analysis.analyzers.context.testing_detector import TestingDetector


class TestTestingDetectorInitialization:
    """Tests for TestingDetector initialization."""

    def test_init_with_path_and_analysis(self, temp_dir: Path):
        """Initializes with path and analysis dict."""
        analysis = {}
        detector = TestingDetector(temp_dir, analysis)

        assert detector.path == temp_dir.resolve()
        assert detector.analysis is analysis


class TestPythonDetection:
    """Tests for Python testing framework detection."""

    def test_detects_pytest_from_requirements(self, temp_dir: Path):
        """Detects pytest from requirements.txt."""
        (temp_dir / "requirements.txt").write_text("pytest>=7.0\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "testing" in analysis
        assert "pytest" in analysis["testing"]["frameworks"]
        assert "pytest" in analysis["testing"]["libraries"]

    def test_detects_pytest_with_plugins(self, temp_dir: Path):
        """Detects pytest with plugins."""
        (temp_dir / "requirements.txt").write_text("pytest-cov\npytest-asyncio\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "pytest" in analysis["testing"]["frameworks"]
        assert "pytest-cov" in analysis["testing"]["libraries"]

    def test_detects_unittest(self, temp_dir: Path):
        """Detects unittest."""
        # unittest is built-in, so we detect from the library name
        (temp_dir / "requirements.txt").write_text("unittest2\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "unittest" in analysis["testing"]["frameworks"]
        assert "unittest2" in analysis["testing"]["libraries"]

    def test_detects_nose2(self, temp_dir: Path):
        """Detects nose testing framework."""
        (temp_dir / "requirements.txt").write_text("nose2\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "nose" in analysis["testing"]["frameworks"]
        assert "nose2" in analysis["testing"]["libraries"]

    def test_detects_doctest(self, temp_dir: Path):
        """Detects doctest."""
        # doctest is built-in, so we detect from the library name
        (temp_dir / "requirements.txt").write_text("doctest\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "doctest" in analysis["testing"]["frameworks"]
        assert "doctest" in analysis["testing"]["libraries"]

    def test_detects_hypothesis(self, temp_dir: Path):
        """Detects Hypothesis testing framework."""
        (temp_dir / "requirements.txt").write_text("hypothesis\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "hypothesis" in analysis["testing"]["frameworks"]
        assert "hypothesis" in analysis["testing"]["libraries"]

    def test_detects_multiple_python_frameworks(self, temp_dir: Path):
        """Detects multiple Python testing frameworks."""
        (temp_dir / "requirements.txt").write_text("pytest\nhypothesis\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "pytest" in analysis["testing"]["frameworks"]
        assert "hypothesis" in analysis["testing"]["frameworks"]


class TestJavaScriptDetection:
    """Tests for JavaScript/TypeScript testing framework detection."""

    def test_detects_jest(self, temp_dir: Path):
        """Detects Jest testing framework."""
        pkg = {"dependencies": {"jest": "^29.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "testing" in analysis
        assert "jest" in analysis["testing"]["frameworks"]
        assert "jest" in analysis["testing"]["libraries"]

    def test_detects_jest_with_types(self, temp_dir: Path):
        """Detects Jest with TypeScript support."""
        pkg = {"devDependencies": {"ts-jest": "^29.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "jest" in analysis["testing"]["frameworks"]
        assert "ts-jest" in analysis["testing"]["libraries"]

    def test_detects_vitest(self, temp_dir: Path):
        """Detects Vitest testing framework."""
        pkg = {"devDependencies": {"vitest": "^1.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "vitest" in analysis["testing"]["frameworks"]
        assert "vitest" in analysis["testing"]["libraries"]

    def test_detects_mocha(self, temp_dir: Path):
        """Detects Mocha testing framework."""
        pkg = {"devDependencies": {"mocha": "^10.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "mocha" in analysis["testing"]["frameworks"]
        assert "mocha" in analysis["testing"]["libraries"]

    def test_detects_mocha_with_chai(self, temp_dir: Path):
        """Detects Mocha with Chai assertion library."""
        pkg = {"devDependencies": {"mocha": "^10.0.0", "chai": "^4.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "mocha" in analysis["testing"]["frameworks"]
        assert "chai" in analysis["testing"]["libraries"]

    def test_detects_jasmine(self, temp_dir: Path):
        """Detects Jasmine testing framework."""
        pkg = {"devDependencies": {"jasmine": "^5.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "jasmine" in analysis["testing"]["frameworks"]
        assert "jasmine" in analysis["testing"]["libraries"]

    def test_detects_ava(self, temp_dir: Path):
        """Detects AVA testing framework."""
        pkg = {"devDependencies": {"ava": "^6.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "ava" in analysis["testing"]["frameworks"]
        assert "ava" in analysis["testing"]["libraries"]

    def test_detects_multiple_js_frameworks(self, temp_dir: Path):
        """Detects multiple JS testing frameworks."""
        pkg = {"devDependencies": {"jest": "^29.0.0", "vitest": "^1.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "jest" in analysis["testing"]["frameworks"]
        assert "vitest" in analysis["testing"]["frameworks"]


class TestE2EDetection:
    """Tests for E2E testing framework detection."""

    def test_detects_playwright(self, temp_dir: Path):
        """Detects Playwright E2E framework."""
        pkg = {"devDependencies": {"@playwright/test": "^1.40.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "testing" in analysis
        assert "playwright" in analysis["testing"]["frameworks"]
        assert "@playwright/test" in analysis["testing"]["libraries"]

    def test_detects_playwright_python(self, temp_dir: Path):
        """Detects Playwright for Python."""
        (temp_dir / "requirements.txt").write_text("playwright\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "playwright" in analysis["testing"]["frameworks"]
        assert "playwright" in analysis["testing"]["libraries"]

    def test_detects_cypress(self, temp_dir: Path):
        """Detects Cypress E2E framework."""
        pkg = {"devDependencies": {"cypress": "^13.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "cypress" in analysis["testing"]["frameworks"]
        assert "cypress" in analysis["testing"]["libraries"]

    def test_detects_puppeteer(self, temp_dir: Path):
        """Detects Puppeteer E2E framework."""
        pkg = {"devDependencies": {"puppeteer": "^21.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "puppeteer" in analysis["testing"]["frameworks"]
        assert "puppeteer" in analysis["testing"]["libraries"]

    def test_detects_selenium(self, temp_dir: Path):
        """Detects Selenium E2E framework."""
        (temp_dir / "requirements.txt").write_text("selenium\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "selenium" in analysis["testing"]["frameworks"]
        assert "selenium" in analysis["testing"]["libraries"]

    def test_detects_multiple_e2e_frameworks(self, temp_dir: Path):
        """Detects multiple E2E testing frameworks."""
        pkg = {"devDependencies": {"@playwright/test": "^1.40.0", "cypress": "^13.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "playwright" in analysis["testing"]["frameworks"]
        assert "cypress" in analysis["testing"]["frameworks"]


class TestConfigDetection:
    """Tests for test configuration file detection."""

    def test_detects_pytest_ini(self, temp_dir: Path):
        """Detects pytest.ini configuration file."""
        (temp_dir / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "testing" in analysis
        assert "pytest.ini" in analysis["testing"]["config_files"]

    def test_detects_pyproject_toml(self, temp_dir: Path):
        """Detects pyproject.toml configuration file."""
        (temp_dir / "pyproject.toml").write_text("[tool.pytest]\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "pyproject.toml" in analysis["testing"]["config_files"]

    def test_detects_setup_cfg(self, temp_dir: Path):
        """Detects setup.cfg configuration file."""
        (temp_dir / "setup.cfg").write_text("[tool:pytest]\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "setup.cfg" in analysis["testing"]["config_files"]

    def test_detects_tox_ini(self, temp_dir: Path):
        """Detects tox.ini configuration file."""
        (temp_dir / "tox.ini").write_text("[tox]\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "tox.ini" in analysis["testing"]["config_files"]

    def test_detects_jest_config_js(self, temp_dir: Path):
        """Detects jest.config.js configuration file."""
        (temp_dir / "jest.config.js").write_text("module.exports = {};\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "jest.config.js" in analysis["testing"]["config_files"]

    def test_detects_jest_config_ts(self, temp_dir: Path):
        """Detects jest.config.ts configuration file."""
        (temp_dir / "jest.config.ts").write_text("export default {};\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "jest.config.ts" in analysis["testing"]["config_files"]

    def test_detects_vitest_config_js(self, temp_dir: Path):
        """Detects vitest.config.js configuration file."""
        (temp_dir / "vitest.config.js").write_text("export default {};\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "vitest.config.js" in analysis["testing"]["config_files"]

    def test_detects_vitest_config_ts(self, temp_dir: Path):
        """Detects vitest.config.ts configuration file."""
        (temp_dir / "vitest.config.ts").write_text("export default {};\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "vitest.config.ts" in analysis["testing"]["config_files"]

    def test_detects_playwright_config_ts(self, temp_dir: Path):
        """Detects playwright.config.ts configuration file."""
        (temp_dir / "playwright.config.ts").write_text("export default {};\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "playwright.config.ts" in analysis["testing"]["config_files"]

    def test_detects_playwright_config_js(self, temp_dir: Path):
        """Detects playwright.config.js configuration file."""
        (temp_dir / "playwright.config.js").write_text("module.exports = {};\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "playwright.config.js" in analysis["testing"]["config_files"]

    def test_detects_cypress_config_js(self, temp_dir: Path):
        """Detects cypress.config.js configuration file."""
        (temp_dir / "cypress.config.js").write_text("export default {};\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "cypress.config.js" in analysis["testing"]["config_files"]

    def test_detects_cypress_config_ts(self, temp_dir: Path):
        """Detects cypress.config.ts configuration file."""
        (temp_dir / "cypress.config.ts").write_text("export default {};\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "cypress.config.ts" in analysis["testing"]["config_files"]

    def test_detects_mocha_rc_js(self, temp_dir: Path):
        """Detects .mocharc.js configuration file."""
        (temp_dir / ".mocharc.js").write_text("module.exports = {};\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert ".mocharc.js" in analysis["testing"]["config_files"]

    def test_detects_mocha_rc_json(self, temp_dir: Path):
        """Detects .mocharc.json configuration file."""
        (temp_dir / ".mocharc.json").write_text("{}\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert ".mocharc.json" in analysis["testing"]["config_files"]

    def test_detects_multiple_configs(self, temp_dir: Path):
        """Detects multiple configuration files."""
        (temp_dir / "pytest.ini").write_text("[pytest]\n")
        (temp_dir / "jest.config.js").write_text("{}\n")
        (temp_dir / "vitest.config.ts").write_text("{}\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "pytest.ini" in analysis["testing"]["config_files"]
        assert "jest.config.js" in analysis["testing"]["config_files"]
        assert "vitest.config.ts" in analysis["testing"]["config_files"]


class TestDirectoryDetection:
    """Tests for test directory detection."""

    def test_detects_tests_directory(self, temp_dir: Path):
        """Detects tests/ directory."""
        (temp_dir / "tests").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "testing" in analysis
        assert "tests" in analysis["testing"]["test_directories"]

    def test_detects_test_directory(self, temp_dir: Path):
        """Detects test/ directory."""
        (temp_dir / "test").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "test" in analysis["testing"]["test_directories"]

    def test_detects_double_underscore_tests(self, temp_dir: Path):
        """Detects __tests__ directory."""
        (temp_dir / "__tests__").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "__tests__" in analysis["testing"]["test_directories"]

    def test_detects_spec_directory(self, temp_dir: Path):
        """Detects spec/ directory."""
        (temp_dir / "spec").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "spec" in analysis["testing"]["test_directories"]

    def test_detects_specs_directory(self, temp_dir: Path):
        """Detects specs/ directory."""
        (temp_dir / "specs").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "specs" in analysis["testing"]["test_directories"]

    def test_detects_e2e_directory(self, temp_dir: Path):
        """Detects e2e/ directory."""
        (temp_dir / "e2e").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "e2e" in analysis["testing"]["test_directories"]

    def test_detects_e2e_tests_directory(self, temp_dir: Path):
        """Detects e2e-tests/ directory."""
        (temp_dir / "e2e-tests").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "e2e-tests" in analysis["testing"]["test_directories"]

    def test_detects_integration_directory(self, temp_dir: Path):
        """Detects integration/ directory."""
        (temp_dir / "integration").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "integration" in analysis["testing"]["test_directories"]

    def test_detects_test_integration_directory(self, temp_dir: Path):
        """Detects test-integration/ directory."""
        (temp_dir / "test-integration").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "test-integration" in analysis["testing"]["test_directories"]

    def test_detects_multiple_test_directories(self, temp_dir: Path):
        """Detects multiple test directories."""
        (temp_dir / "tests").mkdir()
        (temp_dir / "__tests__").mkdir()
        (temp_dir / "e2e").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "tests" in analysis["testing"]["test_directories"]
        assert "__tests__" in analysis["testing"]["test_directories"]
        assert "e2e" in analysis["testing"]["test_directories"]

    def test_ignores_file_named_tests(self, temp_dir: Path):
        """Ignores a file named tests (not a directory)."""
        (temp_dir / "tests").write_text("not a directory")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        # Should not be in test_directories since it's a file, not a directory
        assert "tests" not in analysis["testing"].get("test_directories", [])


class TestCompleteDetection:
    """Tests for complete testing detection scenarios."""

    def test_python_project_with_pytest(self, temp_dir: Path):
        """Complete detection of Python project with pytest."""
        (temp_dir / "requirements.txt").write_text("pytest\npytest-cov\n")
        (temp_dir / "pytest.ini").write_text("[pytest]\n")
        (temp_dir / "tests").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "pytest" in analysis["testing"]["frameworks"]
        assert "pytest" in analysis["testing"]["libraries"]
        assert "pytest-cov" in analysis["testing"]["libraries"]
        assert "pytest.ini" in analysis["testing"]["config_files"]
        assert "tests" in analysis["testing"]["test_directories"]

    def test_javascript_project_with_jest(self, temp_dir: Path):
        """Complete detection of JavaScript project with Jest."""
        pkg = {
            "devDependencies": {
                "jest": "^29.0.0",
                "@types/jest": "^29.0.0"
            }
        }
        (temp_dir / "package.json").write_text(json.dumps(pkg))
        (temp_dir / "jest.config.js").write_text("{}\n")
        (temp_dir / "__tests__").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "jest" in analysis["testing"]["frameworks"]
        assert "jest" in analysis["testing"]["libraries"]
        assert "@types/jest" in analysis["testing"]["libraries"]
        assert "jest.config.js" in analysis["testing"]["config_files"]
        assert "__tests__" in analysis["testing"]["test_directories"]

    def test_typescript_project_with_vitest_and_playwright(self, temp_dir: Path):
        """Complete detection of TypeScript project with Vitest and Playwright."""
        pkg = {
            "devDependencies": {
                "vitest": "^1.0.0",
                "@vitest/ui": "^1.0.0",
                "@playwright/test": "^1.40.0"
            }
        }
        (temp_dir / "package.json").write_text(json.dumps(pkg))
        (temp_dir / "vitest.config.ts").write_text("{}\n")
        (temp_dir / "playwright.config.ts").write_text("{}\n")
        (temp_dir / "tests").mkdir()
        (temp_dir / "e2e").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        assert "vitest" in analysis["testing"]["frameworks"]
        assert "playwright" in analysis["testing"]["frameworks"]
        assert "vitest.config.ts" in analysis["testing"]["config_files"]
        assert "playwright.config.ts" in analysis["testing"]["config_files"]
        assert "tests" in analysis["testing"]["test_directories"]
        assert "e2e" in analysis["testing"]["test_directories"]

    def test_mixed_python_and_javascript_project(self, temp_dir: Path):
        """Detection of project with both Python and JavaScript tests."""
        (temp_dir / "requirements.txt").write_text("pytest\n")
        pkg = {"devDependencies": {"jest": "^29.0.0"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))
        (temp_dir / "pytest.ini").write_text("[pytest]\n")
        (temp_dir / "jest.config.js").write_text("{}\n")
        (temp_dir / "tests").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        # Should detect both Python and JavaScript testing frameworks
        assert "pytest" in analysis["testing"]["frameworks"]
        assert "jest" in analysis["testing"]["frameworks"]
        assert "pytest.ini" in analysis["testing"]["config_files"]
        assert "jest.config.js" in analysis["testing"]["config_files"]

    def test_project_with_only_test_directories(self, temp_dir: Path):
        """Detection of project with only test directories (no frameworks)."""
        (temp_dir / "tests").mkdir()
        (temp_dir / "integration").mkdir()

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        # Should detect test directories even without frameworks
        assert "testing" in analysis
        assert "tests" in analysis["testing"]["test_directories"]
        assert "integration" in analysis["testing"]["test_directories"]

    def test_no_testing_infrastructure(self, temp_dir: Path):
        """Project with no testing infrastructure."""
        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        # Should not add testing key if nothing detected
        assert "testing" not in analysis

    def test_duplicate_frameworks_removed(self, temp_dir: Path):
        """Duplicate framework names are removed."""
        (temp_dir / "requirements.txt").write_text("pytest\npytest-cov\n")

        analysis = {}
        detector = TestingDetector(temp_dir, analysis)
        detector.detect()

        # Frameworks should be unique
        frameworks = analysis["testing"]["frameworks"]
        assert len(frameworks) == len(set(frameworks))


class TestConstants:
    """Tests for TestingDetector constants."""

    def test_pytest_libs_constant(self):
        """PYTEST_LIBS constant is defined."""
        assert hasattr(TestingDetector, "PYTEST_LIBS")
        assert "pytest" in TestingDetector.PYTEST_LIBS
        assert "pytest-cov" in TestingDetector.PYTEST_LIBS

    def test_jest_libs_constant(self):
        """JEST_LIBS constant is defined."""
        assert hasattr(TestingDetector, "JEST_LIBS")
        assert "jest" in TestingDetector.JEST_LIBS
        assert "@jest/globals" in TestingDetector.JEST_LIBS

    def test_js_libs_constant(self):
        """JS_LIBS constant includes all JS frameworks."""
        assert hasattr(TestingDetector, "JS_LIBS")
        assert "jest" in TestingDetector.JS_LIBS
        assert "vitest" in TestingDetector.JS_LIBS
        assert "mocha" in TestingDetector.JS_LIBS

    def test_e2e_libs_constant(self):
        """E2E_LIBS constant includes all E2E frameworks."""
        assert hasattr(TestingDetector, "E2E_LIBS")
        assert "playwright" in TestingDetector.E2E_LIBS
        assert "@playwright/test" in TestingDetector.E2E_LIBS
        assert "cypress" in TestingDetector.E2E_LIBS

    def test_config_files_constant(self):
        """CONFIG_FILES constant includes all config files."""
        assert hasattr(TestingDetector, "CONFIG_FILES")
        assert "pytest.ini" in TestingDetector.CONFIG_FILES
        assert "jest.config.js" in TestingDetector.CONFIG_FILES
        assert "vitest.config.ts" in TestingDetector.CONFIG_FILES
        assert "playwright.config.ts" in TestingDetector.CONFIG_FILES

    def test_test_dirs_constant(self):
        """TEST_DIRS constant includes all test directories."""
        assert hasattr(TestingDetector, "TEST_DIRS")
        assert "tests" in TestingDetector.TEST_DIRS
        assert "test" in TestingDetector.TEST_DIRS
        assert "__tests__" in TestingDetector.TEST_DIRS
        assert "e2e" in TestingDetector.TEST_DIRS
