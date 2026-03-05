"""
Plugin Validator
================

Validates plugin structure, manifest, and implementation.

This module provides utilities for validating plugins during development
and before loading. It checks for common errors, security issues, and
ensures plugins follow the required structure.

Example:
    ```python
    from plugins.sdk.validator import PluginValidator, ValidationResult

    # Validate plugin directory
    validator = PluginValidator()
    result = validator.validate_plugin_dir(Path("./plugins/user/my-plugin"))

    if result.is_valid:
        print("✅ Plugin is valid!")
    else:
        print("❌ Validation errors:")
        for error in result.errors:
            print(f"  - {error}")
        print("⚠️ Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    # Validate manifest only
    result = validator.validate_manifest(manifest_path)
    ```
"""

from __future__ import annotations

import ast
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from ..base import PluginPermission, PluginType

logger = logging.getLogger(__name__)

# Import debug utilities - wrapped with source module name for CodeQL compliance
_SOURCE = "plugins.sdk.validator"
try:
    from debug import (
        debug as _raw_debug,
    )
    from debug import (
        debug_error as _raw_debug_error,
    )
    from debug import (
        debug_success as _raw_debug_success,
    )
    from debug import (
        debug_verbose as _raw_debug_verbose,
    )
    from debug import (
        debug_warning as _raw_debug_warning,
    )
except ImportError:

    def _raw_debug(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_error(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_success(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_verbose(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_warning(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""


def _debug(msg: str, **kwargs) -> None:
    """Debug log with source module."""
    _raw_debug(_SOURCE, msg, **kwargs)


def _debug_verbose(msg: str, **kwargs) -> None:
    """Verbose debug log with source module."""
    _raw_debug_verbose(_SOURCE, msg, **kwargs)


def _debug_success(msg: str, **kwargs) -> None:
    """Success debug log with source module."""
    _raw_debug_success(_SOURCE, msg, **kwargs)


def _debug_error(msg: str, **kwargs) -> None:
    """Error debug log with source module."""
    _raw_debug_error(_SOURCE, msg, **kwargs)


def _debug_warning(msg: str, **kwargs) -> None:
    """Warning debug log with source module."""
    _raw_debug_warning(_SOURCE, msg, **kwargs)


@dataclass
class ValidationResult:
    """
    Result of plugin validation.

    Attributes:
        is_valid: True if plugin passed validation
        errors: Critical errors that prevent plugin from loading
        warnings: Non-critical issues that should be addressed
        info: Informational messages about the plugin
    """

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add an error and mark validation as failed."""
        self.errors.append(message)
        self.is_valid = False
        _debug_error(f"Validation error: {message}")

    def add_warning(self, message: str) -> None:
        """Add a warning without failing validation."""
        self.warnings.append(message)
        _debug_warning(f"Validation warning: {message}")

    def add_info(self, message: str) -> None:
        """Add informational message."""
        self.info.append(message)
        _debug_verbose(f"Validation info: {message}")


class PluginValidator:
    """
    Validates plugin structure and manifest.

    This class provides comprehensive validation for plugins, checking:
    - Manifest file structure and required fields
    - Plugin directory structure
    - Implementation file existence and basic syntax
    - Version compatibility
    - Security issues (permissions, dangerous patterns)
    - Best practices compliance

    Example:
        >>> validator = PluginValidator()
        >>> result = validator.validate_plugin_dir(plugin_path)
        >>> if not result.is_valid:
        ...     for error in result.errors:
        ...         print(f"Error: {error}")
    """

    # Required manifest fields
    REQUIRED_MANIFEST_FIELDS = {
        "name",
        "version",
        "author",
        "description",
        "plugin_type",
    }

    # Optional manifest fields
    OPTIONAL_MANIFEST_FIELDS = {
        "auto_claude_version",
        "required_permissions",
        "dependencies",
        "homepage",
        "license",
    }

    # Valid plugin name pattern (alphanumeric, hyphens, underscores)
    PLUGIN_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")

    # Dangerous Python patterns to warn about
    DANGEROUS_PATTERNS = [
        (r"\beval\(", "eval() can execute arbitrary code - avoid if possible"),
        (r"\bexec\(", "exec() can execute arbitrary code - avoid if possible"),
        (r"\b__import__\(", "Dynamic imports can be dangerous - use import statements"),
        (r"\bos\.system\(", "os.system() is unsafe - use subprocess with proper validation"),
        (r"\bsubprocess\.call\([^)]*shell=True", "shell=True in subprocess is dangerous"),
    ]

    def __init__(self, strict: bool = False):
        """
        Initialize plugin validator.

        Args:
            strict: If True, warnings are treated as errors
        """
        self.strict = strict
        logger.debug(f"PluginValidator initialized (strict={strict})")

    def validate_plugin_dir(self, plugin_dir: Path) -> ValidationResult:
        """
        Validate entire plugin directory.

        Checks:
        - Directory exists
        - plugin.json exists and is valid
        - Implementation file exists
        - Basic syntax validation
        - Security checks

        Args:
            plugin_dir: Path to plugin directory

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult()
        _debug(f"Validating plugin directory: {plugin_dir}")

        # Check directory exists
        if not plugin_dir.exists():
            result.add_error(f"Plugin directory does not exist: {plugin_dir}")
            return result

        if not plugin_dir.is_dir():
            result.add_error(f"Path is not a directory: {plugin_dir}")
            return result

        # Validate manifest
        manifest_path = plugin_dir / "plugin.json"
        manifest_result = self.validate_manifest(manifest_path)
        result.errors.extend(manifest_result.errors)
        result.warnings.extend(manifest_result.warnings)
        result.info.extend(manifest_result.info)
        result.is_valid = result.is_valid and manifest_result.is_valid

        if not manifest_result.is_valid:
            return result

        # Load manifest to get plugin type
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            plugin_type = PluginType(manifest["plugin_type"])
        except Exception as e:
            result.add_error(f"Failed to load manifest: {e}")
            return result

        # Validate implementation file
        impl_result = self.validate_implementation(plugin_dir, plugin_type)
        result.errors.extend(impl_result.errors)
        result.warnings.extend(impl_result.warnings)
        result.info.extend(impl_result.info)
        result.is_valid = result.is_valid and impl_result.is_valid

        # Check for README
        if not (plugin_dir / "README.md").exists():
            result.add_warning("No README.md found - consider adding documentation")

        # Convert warnings to errors in strict mode
        if self.strict and result.warnings:
            for warning in result.warnings:
                result.add_error(f"[STRICT] {warning}")
            result.warnings.clear()

        if result.is_valid:
            _debug_success(f"Plugin validation passed: {plugin_dir.name}")
        else:
            _debug_error(f"Plugin validation failed: {plugin_dir.name}")

        return result

    def validate_manifest(self, manifest_path: Path) -> ValidationResult:
        """
        Validate plugin.json manifest file.

        Checks:
        - File exists and is valid JSON
        - All required fields present
        - Field types correct
        - Values valid (version format, plugin type, etc.)

        Args:
            manifest_path: Path to plugin.json file

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult()
        _debug(f"Validating manifest: {manifest_path}")

        # Check file exists
        if not manifest_path.exists():
            result.add_error("plugin.json not found")
            return result

        # Load and parse JSON
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON in plugin.json: {e}")
            return result
        except Exception as e:
            result.add_error(f"Failed to read plugin.json: {e}")
            return result

        # Check required fields
        missing_fields = self.REQUIRED_MANIFEST_FIELDS - set(manifest.keys())
        if missing_fields:
            result.add_error(
                f"Missing required fields in plugin.json: {', '.join(sorted(missing_fields))}"
            )

        # Check for unknown fields
        all_valid_fields = self.REQUIRED_MANIFEST_FIELDS | self.OPTIONAL_MANIFEST_FIELDS
        unknown_fields = set(manifest.keys()) - all_valid_fields
        if unknown_fields:
            result.add_warning(
                f"Unknown fields in plugin.json: {', '.join(sorted(unknown_fields))}"
            )

        # Validate name
        if "name" in manifest:
            name_result = self._validate_plugin_name(manifest["name"])
            result.errors.extend(name_result.errors)
            result.warnings.extend(name_result.warnings)

        # Validate version
        if "version" in manifest:
            version_result = self._validate_version(manifest["version"])
            result.errors.extend(version_result.errors)
            result.warnings.extend(version_result.warnings)

        # Validate plugin_type
        if "plugin_type" in manifest:
            type_result = self._validate_plugin_type(manifest["plugin_type"])
            result.errors.extend(type_result.errors)
            result.warnings.extend(type_result.warnings)

        # Validate auto_claude_version if present
        if "auto_claude_version" in manifest:
            ac_version_result = self._validate_auto_claude_version(
                manifest["auto_claude_version"]
            )
            result.errors.extend(ac_version_result.errors)
            result.warnings.extend(ac_version_result.warnings)

        # Validate required_permissions if present
        if "required_permissions" in manifest:
            perms_result = self._validate_permissions(manifest["required_permissions"])
            result.errors.extend(perms_result.errors)
            result.warnings.extend(perms_result.warnings)

        # Validate dependencies if present
        if "dependencies" in manifest:
            deps_result = self._validate_dependencies(manifest["dependencies"])
            result.errors.extend(deps_result.errors)
            result.warnings.extend(deps_result.warnings)

        # Check for recommended optional fields
        if "license" not in manifest:
            result.add_info("Consider adding 'license' field to plugin.json")

        if "homepage" not in manifest:
            result.add_info("Consider adding 'homepage' field to plugin.json")

        result.is_valid = len(result.errors) == 0
        return result

    def validate_implementation(
        self, plugin_dir: Path, plugin_type: PluginType
    ) -> ValidationResult:
        """
        Validate plugin implementation file.

        Checks:
        - Implementation file exists (agent.py, integration.py, or ui.py)
        - File has valid Python syntax
        - Basic security checks

        Args:
            plugin_dir: Path to plugin directory
            plugin_type: Type of plugin

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult()

        # Determine expected implementation file
        if plugin_type == PluginType.AGENT:
            impl_file = "agent.py"
        elif plugin_type == PluginType.INTEGRATION:
            impl_file = "integration.py"
        else:  # UI
            impl_file = "ui.py"

        impl_path = plugin_dir / impl_file

        # Check implementation file exists
        if not impl_path.exists():
            # Also check for plugin.py or __init__.py as fallback
            if (plugin_dir / "plugin.py").exists():
                impl_path = plugin_dir / "plugin.py"
                result.add_info(f"Using plugin.py instead of {impl_file}")
            elif (plugin_dir / "__init__.py").exists():
                impl_path = plugin_dir / "__init__.py"
                result.add_info(f"Using __init__.py instead of {impl_file}")
            else:
                result.add_error(
                    f"Implementation file not found: {impl_file} "
                    f"(also checked plugin.py and __init__.py)"
                )
                return result

        # Validate Python syntax
        try:
            with open(impl_path, encoding="utf-8") as f:
                code = f.read()

            ast.parse(code)
            result.add_info(f"✓ {impl_path.name} has valid Python syntax")

            # Security checks
            security_result = self._check_security_patterns(code, impl_path.name)
            result.warnings.extend(security_result.warnings)

        except SyntaxError as e:
            result.add_error(
                f"Syntax error in {impl_path.name} at line {e.lineno}: {e.msg}"
            )
        except Exception as e:
            result.add_error(f"Failed to validate {impl_path.name}: {e}")

        result.is_valid = len(result.errors) == 0
        return result

    def _validate_plugin_name(self, name: Any) -> ValidationResult:
        """Validate plugin name."""
        result = ValidationResult()

        if not isinstance(name, str):
            result.add_error(f"Plugin name must be a string, got {type(name).__name__}")
            return result

        if not name:
            result.add_error("Plugin name cannot be empty")
            return result

        if not self.PLUGIN_NAME_PATTERN.match(name):
            result.add_error(
                f"Invalid plugin name '{name}'. "
                f"Must contain only alphanumeric characters, hyphens, and underscores, "
                f"and start with an alphanumeric character."
            )

        if len(name) > 50:
            result.add_warning(
                f"Plugin name '{name}' is very long ({len(name)} chars). "
                f"Consider using a shorter name."
            )

        result.is_valid = len(result.errors) == 0
        return result

    def _validate_version(self, version: Any) -> ValidationResult:
        """Validate version string."""
        result = ValidationResult()

        if not isinstance(version, str):
            result.add_error(
                f"Version must be a string, got {type(version).__name__}"
            )
            return result

        try:
            Version(version)
            result.add_info(f"✓ Valid version: {version}")
        except InvalidVersion:
            result.add_error(
                f"Invalid version string '{version}'. "
                f"Use semantic versioning (e.g., '1.0.0', '2.1.3-beta')"
            )

        result.is_valid = len(result.errors) == 0
        return result

    def _validate_plugin_type(self, plugin_type: Any) -> ValidationResult:
        """Validate plugin type."""
        result = ValidationResult()

        if not isinstance(plugin_type, str):
            result.add_error(
                f"Plugin type must be a string, got {type(plugin_type).__name__}"
            )
            return result

        try:
            PluginType(plugin_type)
            result.add_info(f"✓ Valid plugin type: {plugin_type}")
        except ValueError:
            valid_types = [t.value for t in PluginType]
            result.add_error(
                f"Invalid plugin type '{plugin_type}'. "
                f"Must be one of: {', '.join(valid_types)}"
            )

        result.is_valid = len(result.errors) == 0
        return result

    def _validate_auto_claude_version(self, version_spec: Any) -> ValidationResult:
        """Validate Auto Claude version specifier."""
        result = ValidationResult()

        if not isinstance(version_spec, str):
            result.add_error(
                f"auto_claude_version must be a string, got {type(version_spec).__name__}"
            )
            return result

        try:
            SpecifierSet(version_spec)
            result.add_info(f"✓ Valid version specifier: {version_spec}")
        except InvalidSpecifier:
            result.add_error(
                f"Invalid version specifier '{version_spec}'. "
                f"Use PEP 440 format (e.g., '>=1.0.0', '>=2.0,<3.0')"
            )

        result.is_valid = len(result.errors) == 0
        return result

    def _validate_permissions(self, permissions: Any) -> ValidationResult:
        """Validate required_permissions list."""
        result = ValidationResult()

        if not isinstance(permissions, list):
            result.add_error(
                f"required_permissions must be a list, got {type(permissions).__name__}"
            )
            return result

        for perm in permissions:
            if not isinstance(perm, str):
                result.add_error(
                    f"Permission must be a string, got {type(perm).__name__}: {perm}"
                )
                continue

            try:
                PluginPermission(perm)
            except ValueError:
                valid_perms = [p.value for p in PluginPermission]
                result.add_error(
                    f"Invalid permission '{perm}'. "
                    f"Must be one of: {', '.join(valid_perms)}"
                )

        # Check for overly broad permissions
        if len(permissions) == len(PluginPermission):
            result.add_warning(
                "Plugin requests all available permissions. "
                "Consider limiting to only what's needed."
            )

        result.is_valid = len(result.errors) == 0
        return result

    def _validate_dependencies(self, dependencies: Any) -> ValidationResult:
        """Validate dependencies list."""
        result = ValidationResult()

        if not isinstance(dependencies, list):
            result.add_error(
                f"dependencies must be a list, got {type(dependencies).__name__}"
            )
            return result

        for dep in dependencies:
            if not isinstance(dep, str):
                result.add_error(
                    f"Dependency must be a string, got {type(dep).__name__}: {dep}"
                )
                continue

            # Validate dependency name format
            dep_name_result = self._validate_plugin_name(dep)
            if not dep_name_result.is_valid:
                result.add_error(f"Invalid dependency name '{dep}': {dep_name_result.errors[0]}")

        # Check for circular dependencies (self-dependency)
        # Note: Full circular dependency detection would require loading other plugins

        result.is_valid = len(result.errors) == 0
        return result

    def _check_security_patterns(self, code: str, filename: str) -> ValidationResult:
        """Check for dangerous security patterns in code."""
        result = ValidationResult()

        for pattern, warning in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                result.add_warning(f"{filename}: {warning}")

        return result
