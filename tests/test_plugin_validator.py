#!/usr/bin/env python3
"""
Tests for Plugin Validator
===========================

Tests the plugins/sdk/validator.py module functionality including:
- Plugin directory validation
- Manifest validation
- Implementation file validation
- Version validation
- Permission validation
- Security pattern detection
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from apps.backend.plugins.base import PluginPermission, PluginType
from apps.backend.plugins.sdk.validator import PluginValidator, ValidationResult


@pytest.fixture
def temp_dir():
    """Create temporary directory for test plugins."""
    tmpdir = Path(tempfile.mkdtemp())
    yield tmpdir
    # Cleanup
    if tmpdir.exists():
        shutil.rmtree(tmpdir)


@pytest.fixture
def validator():
    """Create PluginValidator instance."""
    return PluginValidator()


@pytest.fixture
def strict_validator():
    """Create strict PluginValidator instance."""
    return PluginValidator(strict=True)


def create_plugin_dir(base_dir: Path, name: str, manifest: dict = None, impl_content: str = None):
    """Helper to create a plugin directory structure."""
    plugin_dir = base_dir / name
    plugin_dir.mkdir(parents=True)

    # Create manifest
    if manifest is not None:
        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump(manifest, f)

    # Create implementation
    if impl_content is not None:
        (plugin_dir / "agent.py").write_text(impl_content)

    return plugin_dir


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_initialization(self):
        """ValidationResult initializes correctly."""
        result = ValidationResult()
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.info == []

    def test_add_error(self):
        """Adding error marks validation as failed."""
        result = ValidationResult()
        result.add_error("Test error")

        assert result.is_valid is False
        assert "Test error" in result.errors

    def test_add_warning(self):
        """Adding warning does not fail validation."""
        result = ValidationResult()
        result.add_warning("Test warning")

        assert result.is_valid is True
        assert "Test warning" in result.warnings

    def test_add_info(self):
        """Adding info does not fail validation."""
        result = ValidationResult()
        result.add_info("Test info")

        assert result.is_valid is True
        assert "Test info" in result.info

    def test_multiple_errors(self):
        """Can add multiple errors."""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_error("Error 2")

        assert result.is_valid is False
        assert len(result.errors) == 2


class TestValidatorInitialization:
    """Tests for PluginValidator initialization."""

    def test_default_initialization(self):
        """Validator initializes with default settings."""
        validator = PluginValidator()
        assert validator.strict is False

    def test_strict_initialization(self):
        """Validator can be initialized in strict mode."""
        validator = PluginValidator(strict=True)
        assert validator.strict is True


class TestManifestValidation:
    """Tests for manifest file validation."""

    def test_missing_manifest(self, validator, temp_dir):
        """Fails when plugin.json is missing."""
        result = validator.validate_manifest(temp_dir / "nonexistent.json")
        assert result.is_valid is False
        assert any("not found" in error for error in result.errors)

    def test_invalid_json(self, validator, temp_dir):
        """Fails when JSON is invalid."""
        manifest_path = temp_dir / "plugin.json"
        manifest_path.write_text("{invalid json")

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False
        assert any("Invalid JSON" in error for error in result.errors)

    def test_valid_minimal_manifest(self, validator, temp_dir):
        """Validates minimal correct manifest."""
        manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "author": "Test Author",
            "description": "Test plugin",
            "plugin_type": "agent",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is True

    def test_missing_required_fields(self, validator, temp_dir):
        """Fails when required fields are missing."""
        manifest = {
            "name": "test",
            # Missing: version, author, description, plugin_type
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False
        assert any("Missing required fields" in error for error in result.errors)

    def test_unknown_fields_warning(self, validator, temp_dir):
        """Warns about unknown fields."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
            "unknown_field": "value",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert any("Unknown fields" in warning for warning in result.warnings)


class TestPluginNameValidation:
    """Tests for plugin name validation in manifest."""

    def test_valid_names(self, validator, temp_dir):
        """Accepts valid plugin names."""
        valid_names = ["test", "my-plugin", "my_plugin", "plugin123"]

        for name in valid_names:
            manifest = {
                "name": name,
                "version": "1.0.0",
                "author": "Test",
                "description": "Test",
                "plugin_type": "agent",
            }
            manifest_path = temp_dir / f"{name}.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f)

            result = validator.validate_manifest(manifest_path)
            assert result.is_valid is True

    def test_empty_name(self, validator, temp_dir):
        """Rejects empty name."""
        manifest = {
            "name": "",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False
        assert any("cannot be empty" in error for error in result.errors)

    def test_invalid_characters(self, validator, temp_dir):
        """Rejects names with invalid characters."""
        manifest = {
            "name": "my plugin",  # space
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False
        assert any("Invalid plugin name" in error for error in result.errors)

    def test_long_name_warning(self, validator, temp_dir):
        """Warns about very long names."""
        long_name = "a" * 60
        manifest = {
            "name": long_name,
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert any("very long" in warning for warning in result.warnings)

    def test_non_string_name(self, validator, temp_dir):
        """Rejects non-string name."""
        manifest = {
            "name": 123,
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False
        assert any("must be a string" in error for error in result.errors)


class TestVersionValidation:
    """Tests for version validation."""

    def test_valid_versions(self, validator, temp_dir):
        """Accepts valid semantic versions."""
        valid_versions = ["1.0.0", "2.1.3", "0.0.1", "1.0.0-beta", "2.1.0-alpha.1"]

        for version in valid_versions:
            manifest = {
                "name": "test",
                "version": version,
                "author": "Test",
                "description": "Test",
                "plugin_type": "agent",
            }
            manifest_path = temp_dir / f"v{version.replace('.', '_')}.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f)

            result = validator.validate_manifest(manifest_path)
            assert result.is_valid is True

    def test_invalid_version(self, validator, temp_dir):
        """Rejects invalid version strings."""
        manifest = {
            "name": "test",
            "version": "not-a-version",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False
        assert any("Invalid version" in error for error in result.errors)

    def test_non_string_version(self, validator, temp_dir):
        """Rejects non-string version."""
        manifest = {
            "name": "test",
            "version": 1.0,
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False


class TestPluginTypeValidation:
    """Tests for plugin type validation."""

    def test_valid_types(self, validator, temp_dir):
        """Accepts valid plugin types."""
        valid_types = ["agent", "integration", "ui"]

        for plugin_type in valid_types:
            manifest = {
                "name": "test",
                "version": "1.0.0",
                "author": "Test",
                "description": "Test",
                "plugin_type": plugin_type,
            }
            manifest_path = temp_dir / f"{plugin_type}.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f)

            result = validator.validate_manifest(manifest_path)
            assert result.is_valid is True

    def test_invalid_type(self, validator, temp_dir):
        """Rejects invalid plugin type."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "invalid",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False
        assert any("Invalid plugin type" in error for error in result.errors)

    def test_non_string_type(self, validator, temp_dir):
        """Rejects non-string plugin type."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": 123,
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False


class TestAutoClaudeVersionValidation:
    """Tests for auto_claude_version validation."""

    def test_valid_version_specifiers(self, validator, temp_dir):
        """Accepts valid PEP 440 version specifiers."""
        valid_specs = [">=1.0.0", ">=2.0,<3.0", "~=1.4", "==2.8.0"]

        for spec in valid_specs:
            manifest = {
                "name": "test",
                "version": "1.0.0",
                "author": "Test",
                "description": "Test",
                "plugin_type": "agent",
                "auto_claude_version": spec,
            }
            manifest_path = temp_dir / f"spec_{hash(spec)}.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f)

            result = validator.validate_manifest(manifest_path)
            assert result.is_valid is True

    def test_invalid_version_specifier(self, validator, temp_dir):
        """Rejects invalid version specifiers."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
            "auto_claude_version": "invalid spec",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False
        assert any("Invalid version specifier" in error for error in result.errors)


class TestPermissionsValidation:
    """Tests for required_permissions validation."""

    def test_valid_permissions(self, validator, temp_dir):
        """Accepts valid permissions."""
        valid_perms = ["network_access", "access_secrets", "execute_commands"]

        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
            "required_permissions": valid_perms,
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is True

    def test_invalid_permission(self, validator, temp_dir):
        """Rejects invalid permission."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
            "required_permissions": ["invalid_permission"],
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False
        assert any("Invalid permission" in error for error in result.errors)

    def test_non_list_permissions(self, validator, temp_dir):
        """Rejects non-list permissions."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
            "required_permissions": "network_access",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False

    def test_overly_broad_permissions_warning(self, validator, temp_dir):
        """Warns when all permissions are requested."""
        all_perms = [p.value for p in PluginPermission]
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
            "required_permissions": all_perms,
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert any("all available permissions" in warning for warning in result.warnings)


class TestDependenciesValidation:
    """Tests for dependencies validation."""

    def test_valid_dependencies(self, validator, temp_dir):
        """Accepts valid dependency list."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
            "dependencies": ["plugin1", "plugin-2", "plugin_3"],
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is True

    def test_invalid_dependency_name(self, validator, temp_dir):
        """Rejects invalid dependency names."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
            "dependencies": ["invalid name"],  # space not allowed
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False

    def test_non_list_dependencies(self, validator, temp_dir):
        """Rejects non-list dependencies."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
            "dependencies": "plugin1",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert result.is_valid is False


class TestImplementationValidation:
    """Tests for implementation file validation."""

    def test_agent_implementation_exists(self, validator, temp_dir):
        """Validates that agent.py exists for agent plugins."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        (plugin_dir / "agent.py").write_text("class TestPlugin: pass")

        result = validator.validate_implementation(plugin_dir, PluginType.AGENT)
        assert result.is_valid is True

    def test_integration_implementation_exists(self, validator, temp_dir):
        """Validates that integration.py exists for integration plugins."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        (plugin_dir / "integration.py").write_text("class TestPlugin: pass")

        result = validator.validate_implementation(plugin_dir, PluginType.INTEGRATION)
        assert result.is_valid is True

    def test_ui_implementation_exists(self, validator, temp_dir):
        """Validates that ui.py exists for UI plugins."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        (plugin_dir / "ui.py").write_text("class TestPlugin: pass")

        result = validator.validate_implementation(plugin_dir, PluginType.UI)
        assert result.is_valid is True

    def test_fallback_to_plugin_py(self, validator, temp_dir):
        """Falls back to plugin.py if type-specific file missing."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.py").write_text("class TestPlugin: pass")

        result = validator.validate_implementation(plugin_dir, PluginType.AGENT)
        assert result.is_valid is True
        assert any("plugin.py" in info for info in result.info)

    def test_fallback_to_init_py(self, validator, temp_dir):
        """Falls back to __init__.py if other files missing."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        (plugin_dir / "__init__.py").write_text("class TestPlugin: pass")

        result = validator.validate_implementation(plugin_dir, PluginType.AGENT)
        assert result.is_valid is True
        assert any("__init__.py" in info for info in result.info)

    def test_missing_implementation(self, validator, temp_dir):
        """Fails when no implementation file found."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()

        result = validator.validate_implementation(plugin_dir, PluginType.AGENT)
        assert result.is_valid is False
        assert any("not found" in error for error in result.errors)

    def test_syntax_error_detection(self, validator, temp_dir):
        """Detects Python syntax errors."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        (plugin_dir / "agent.py").write_text("def invalid( syntax")

        result = validator.validate_implementation(plugin_dir, PluginType.AGENT)
        assert result.is_valid is False
        assert any("Syntax error" in error for error in result.errors)

    def test_valid_python_syntax(self, validator, temp_dir):
        """Accepts valid Python code."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        code = """
class TestPlugin:
    def __init__(self):
        pass
"""
        (plugin_dir / "agent.py").write_text(code)

        result = validator.validate_implementation(plugin_dir, PluginType.AGENT)
        assert result.is_valid is True
        assert any("valid Python syntax" in info for info in result.info)


class TestSecurityPatternDetection:
    """Tests for dangerous pattern detection."""

    def test_eval_warning(self, validator, temp_dir):
        """Warns about eval() usage."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        code = """
def dangerous():
    result = eval(user_input)
"""
        (plugin_dir / "agent.py").write_text(code)

        result = validator.validate_implementation(plugin_dir, PluginType.AGENT)
        assert any("eval()" in warning for warning in result.warnings)

    def test_exec_warning(self, validator, temp_dir):
        """Warns about exec() usage."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        code = """
def dangerous():
    exec(user_code)
"""
        (plugin_dir / "agent.py").write_text(code)

        result = validator.validate_implementation(plugin_dir, PluginType.AGENT)
        assert any("exec()" in warning for warning in result.warnings)

    def test_os_system_warning(self, validator, temp_dir):
        """Warns about os.system() usage."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        code = """
import os
def dangerous():
    os.system("rm -rf /")
"""
        (plugin_dir / "agent.py").write_text(code)

        result = validator.validate_implementation(plugin_dir, PluginType.AGENT)
        assert any("os.system()" in warning for warning in result.warnings)

    def test_subprocess_shell_warning(self, validator, temp_dir):
        """Warns about subprocess with shell=True."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        code = """
import subprocess
def dangerous():
    subprocess.call("command", shell=True)
"""
        (plugin_dir / "agent.py").write_text(code)

        result = validator.validate_implementation(plugin_dir, PluginType.AGENT)
        assert any("shell=True" in warning for warning in result.warnings)

    def test_no_warnings_for_safe_code(self, validator, temp_dir):
        """No warnings for safe code."""
        plugin_dir = temp_dir / "test"
        plugin_dir.mkdir()
        code = """
class SafePlugin:
    def safe_method(self):
        return "safe"
"""
        (plugin_dir / "agent.py").write_text(code)

        result = validator.validate_implementation(plugin_dir, PluginType.AGENT)
        assert len(result.warnings) == 0


class TestPluginDirectoryValidation:
    """Tests for full plugin directory validation."""

    def test_valid_plugin_directory(self, validator, temp_dir):
        """Validates complete valid plugin."""
        manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
        }
        impl_code = """
class TestPlugin:
    pass
"""
        plugin_dir = create_plugin_dir(temp_dir, "test", manifest, impl_code)
        (plugin_dir / "README.md").write_text("# Test Plugin")

        result = validator.validate_plugin_dir(plugin_dir)
        assert result.is_valid is True

    def test_nonexistent_directory(self, validator, temp_dir):
        """Fails for nonexistent directory."""
        result = validator.validate_plugin_dir(temp_dir / "nonexistent")
        assert result.is_valid is False
        assert any("does not exist" in error for error in result.errors)

    def test_not_a_directory(self, validator, temp_dir):
        """Fails when path is not a directory."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("not a directory")

        result = validator.validate_plugin_dir(file_path)
        assert result.is_valid is False
        assert any("not a directory" in error for error in result.errors)

    def test_missing_readme_warning(self, validator, temp_dir):
        """Warns when README.md is missing."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
        }
        impl_code = "class Test: pass"
        plugin_dir = create_plugin_dir(temp_dir, "test", manifest, impl_code)

        result = validator.validate_plugin_dir(plugin_dir)
        assert any("README.md" in warning for warning in result.warnings)


class TestStrictMode:
    """Tests for strict validation mode."""

    def test_warnings_become_errors_in_strict_mode(self, strict_validator, temp_dir):
        """Strict mode converts warnings to errors."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
            "unknown_field": "value",
        }
        impl_code = "class Test: pass"
        plugin_dir = create_plugin_dir(temp_dir, "test", manifest, impl_code)

        result = strict_validator.validate_plugin_dir(plugin_dir)
        assert result.is_valid is False
        assert any("[STRICT]" in error for error in result.errors)

    def test_normal_mode_allows_warnings(self, validator, temp_dir):
        """Normal mode allows warnings."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
            "unknown_field": "value",
        }
        impl_code = "class Test: pass"
        plugin_dir = create_plugin_dir(temp_dir, "test", manifest, impl_code)

        result = validator.validate_plugin_dir(plugin_dir)
        assert result.is_valid is True
        assert len(result.warnings) > 0


class TestRecommendedFields:
    """Tests for recommended optional fields."""

    def test_missing_license_info(self, validator, temp_dir):
        """Suggests adding license field."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert any("license" in info.lower() for info in result.info)

    def test_missing_homepage_info(self, validator, temp_dir):
        """Suggests adding homepage field."""
        manifest = {
            "name": "test",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "plugin_type": "agent",
        }
        manifest_path = temp_dir / "plugin.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        result = validator.validate_manifest(manifest_path)
        assert any("homepage" in info.lower() for info in result.info)
