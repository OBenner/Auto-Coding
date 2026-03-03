"""
Plugin Discovery & Loading
===========================

Discovers, validates, and loads plugins from plugin directories.

This module handles plugin discovery by scanning configured directories,
validating plugin.json manifest files, dynamically loading plugin modules,
and initializing plugin instances with proper sandboxing.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import logging
import re
import sys
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion

from .base import PluginBase, PluginMetadata, PluginType
from .isolation import PluginSandbox, ResourceLimits

# Configure logging
logger = logging.getLogger(__name__)

# Import debug utilities - wrapped with source module name for CodeQL compliance
_SOURCE = "plugins.loader"
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


class PluginLoadError(Exception):
    """Raised when a plugin fails to load."""

    pass


class PluginValidationError(Exception):
    """Raised when plugin manifest validation fails."""

    pass


class PluginLoader:
    """
    Discovers and loads plugins from configured directories.

    The loader scans plugin directories, validates manifests, loads modules,
    and initializes plugin instances. It supports both user-installed and
    system plugins.

    Plugin directory structure:
        plugin_name/
            plugin.json      # Required: Plugin manifest
            plugin.py        # Required: Plugin implementation (or __init__.py)
            README.md        # Optional: Documentation
            ...              # Optional: Additional files

    Example:
        >>> from plugins.loader import PluginLoader
        >>> loader = PluginLoader()
        >>> plugins = loader.discover_plugins()
        >>> for plugin in plugins:
        ...     print(f"Found: {plugin.name} v{plugin.version}")
        >>>
        >>> # Load specific plugin
        >>> plugin = loader.load_plugin(Path("path/to/plugin"))
        >>> plugin.on_load()
        >>> plugin.on_enable()
    """

    def __init__(
        self,
        user_plugins_dir: Path | None = None,
        system_plugins_dir: Path | None = None,
        default_limits: ResourceLimits | None = None,
    ):
        """
        Initialize plugin loader.

        Args:
            user_plugins_dir: Directory containing user-installed plugins
            system_plugins_dir: Directory containing system/built-in plugins
            default_limits: Default resource limits for plugin sandboxing
        """
        # Default plugin directories relative to backend root
        if user_plugins_dir is None:
            user_plugins_dir = Path.cwd() / ".auto-claude" / "plugins" / "user"
        if system_plugins_dir is None:
            system_plugins_dir = Path(__file__).parent.parent / "plugins" / "system"

        self.user_plugins_dir = Path(user_plugins_dir)
        self.system_plugins_dir = Path(system_plugins_dir)
        self.default_limits = default_limits or ResourceLimits()

        # Ensure directories exist
        self.user_plugins_dir.mkdir(parents=True, exist_ok=True)
        self.system_plugins_dir.mkdir(parents=True, exist_ok=True)

        logger.debug("PluginLoader initialized:")
        debug_verbose("loader", f"  User plugins: {self.user_plugins_dir}")
        debug_verbose("loader", f"  System plugins: {self.system_plugins_dir}")
        debug_verbose("loader", f"  Default limits: {self.default_limits.to_dict()}")

    @staticmethod
    def _get_auto_claude_version() -> str:
        """
        Get the current Auto Claude version from package.json.

        Returns:
            Version string (e.g., "3.0.0")

        Raises:
            FileNotFoundError: If package.json not found
            ValueError: If version cannot be parsed
        """
        # Navigate from plugins/loader.py -> backend/ -> root/
        root_dir = Path(__file__).parent.parent.parent.parent
        package_json = root_dir / "package.json"

        if not package_json.exists():
            raise FileNotFoundError(
                f"package.json not found at {package_json}. Cannot determine Auto Claude version."
            )

        try:
            with open(package_json, encoding="utf-8") as f:
                data = json.load(f)
            version = data.get("version")
            if not version:
                raise ValueError("No 'version' field in package.json")
            return version
        except Exception as e:
            raise ValueError(f"Failed to read version from package.json: {e}") from e

    def _check_version_compatibility(
        self,
        plugin_name: str,
        required_version: str | None,
    ) -> tuple[bool, str | None]:
        """
        Check if plugin's version requirement is compatible with current Auto Claude version.

        Supports various version specifier formats:
        - Exact: "3.0.0"
        - Comparison: ">=2.8.0", ">3.0.0", "<=3.5.0"
        - Range: ">=2.8.0,<4.0.0"
        - Caret: "^3.0.0" (compatible with 3.x.x, not 4.0.0)
        - Tilde: "~3.0.0" (compatible with 3.0.x, not 3.1.0)

        Args:
            plugin_name: Name of the plugin being checked
            required_version: Version requirement string from plugin.json

        Returns:
            Tuple of (is_compatible, error_message)
            - is_compatible: True if compatible or no requirement specified
            - error_message: None if compatible, error string if incompatible

        Example:
            >>> loader = PluginLoader()
            >>> loader._check_version_compatibility("my-plugin", ">=2.8.0")
            (True, None)
            >>> loader._check_version_compatibility("my-plugin", ">=4.0.0")
            (False, "Plugin 'my-plugin' requires Auto Claude >=4.0.0, but current version is 3.0.0")
        """
        # No requirement specified - always compatible
        if not required_version:
            debug_verbose(
                "loader",
                f"Plugin '{plugin_name}' has no version requirement - compatible"
            )
            return True, None

        try:
            # Get current Auto Claude version
            current_version = self._get_auto_claude_version()
            current = Version(current_version)

            # Parse version requirement
            # Handle caret (^) and tilde (~) syntax by converting to specifier format
            version_spec = required_version.strip()

            if version_spec.startswith("^"):
                # Caret: ^3.0.0 means >=3.0.0,<4.0.0
                base_version = version_spec[1:]
                parts = Version(base_version).release
                if len(parts) >= 2:
                    major = parts[0]
                    version_spec = f">={base_version},<{major + 1}.0.0"
                else:
                    version_spec = f">={base_version}"

            elif version_spec.startswith("~"):
                # Tilde: ~3.0.0 means >=3.0.0,<3.1.0
                base_version = version_spec[1:]
                parts = Version(base_version).release
                if len(parts) >= 2:
                    major, minor = parts[0], parts[1]
                    version_spec = f">={base_version},<{major}.{minor + 1}.0"
                else:
                    version_spec = f">={base_version}"

            # Use SpecifierSet for comparison
            specifier = SpecifierSet(version_spec)

            if current in specifier:
                debug_verbose(
                    "loader",
                    f"Plugin '{plugin_name}' version requirement '{required_version}' "
                    f"is compatible with Auto Claude {current_version}"
                )
                return True, None
            else:
                error_msg = (
                    f"Plugin '{plugin_name}' requires Auto Claude {required_version}, "
                    f"but current version is {current_version}"
                )
                debug_warning("loader", error_msg)
                return False, error_msg

        except InvalidVersion as e:
            error_msg = (
                f"Plugin '{plugin_name}' has invalid version requirement '{required_version}': {e}"
            )
            logger.warning(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = (
                f"Failed to check version compatibility for plugin '{plugin_name}': {e}"
            )
            logger.warning(error_msg)
            return False, error_msg

    def discover_plugins(self) -> list[PluginMetadata]:
        """
        Discover all plugins in configured directories.

        Scans both user and system plugin directories, validates manifests,
        and returns metadata for all valid plugins found.

        Returns:
            List of PluginMetadata for all discovered plugins

        Raises:
            PluginValidationError: If manifest validation fails
        """
        discovered = []

        _debug("Discovering plugins...")

        # Scan system plugins first (can be overridden by user plugins)
        if self.system_plugins_dir.exists():
            _debug_verbose(f"Scanning system plugins: {self.system_plugins_dir}")
            for plugin_dir in self.system_plugins_dir.iterdir():
                if plugin_dir.is_dir():
                    try:
                        metadata = self._load_metadata(plugin_dir)

                        # Check version compatibility (non-blocking for discovery)
                        is_compatible, error_msg = self._check_version_compatibility(
                            metadata.name,
                            metadata.auto_claude_version
                        )
                        if not is_compatible:
                            debug_warning(
                                "loader",
                                f"  Found incompatible system plugin {plugin_dir.name}: {error_msg}"
                            )
                            logger.warning(
                                f"System plugin {plugin_dir.name} is incompatible: {error_msg}"
                            )

                        discovered.append(metadata)
                        _debug_verbose(f"  Found: {metadata.name} v{metadata.version}")
                    except Exception as e:
                        _debug_warning(
                            f"  Skipping invalid system plugin {plugin_dir.name}: {e}"
                        )
                        logger.warning(
                            f"Failed to load system plugin {plugin_dir.name}: {e}"
                        )

        # Scan user plugins (can override system plugins)
        if self.user_plugins_dir.exists():
            _debug_verbose(f"Scanning user plugins: {self.user_plugins_dir}")
            for plugin_dir in self.user_plugins_dir.iterdir():
                if plugin_dir.is_dir():
                    try:
                        metadata = self._load_metadata(plugin_dir)

                        # Check version compatibility (non-blocking for discovery)
                        is_compatible, error_msg = self._check_version_compatibility(
                            metadata.name,
                            metadata.auto_claude_version
                        )
                        if not is_compatible:
                            debug_warning(
                                "loader",
                                f"  Found incompatible user plugin {plugin_dir.name}: {error_msg}"
                            )
                            logger.warning(
                                f"User plugin {plugin_dir.name} is incompatible: {error_msg}"
                            )

                        # Check for duplicates (user plugin overrides system)
                        existing = next(
                            (p for p in discovered if p.name == metadata.name), None
                        )
                        if existing:
                            _debug_warning(
                                f"  User plugin '{metadata.name}' overrides system plugin"
                            )
                            discovered.remove(existing)
                        discovered.append(metadata)
                        _debug_verbose(f"  Found: {metadata.name} v{metadata.version}")
                    except Exception as e:
                        _debug_warning(
                            f"  Skipping invalid user plugin {plugin_dir.name}: {e}"
                        )
                        logger.warning(
                            f"Failed to load user plugin {plugin_dir.name}: {e}"
                        )

        _debug_success(f"Discovered {len(discovered)} plugins")
        return discovered

    def load_plugin(
        self,
        plugin_dir: Path,
        project_dir: Path | None = None,
        limits: ResourceLimits | None = None,
    ) -> PluginBase:
        """
        Load a plugin from a directory.

        Validates the manifest, imports the plugin module, instantiates
        the plugin class, and prepares it for use with sandboxing.

        Args:
            plugin_dir: Directory containing the plugin
            project_dir: Project directory to grant plugin access to
            limits: Resource limits for plugin execution (uses default if None)

        Returns:
            Initialized plugin instance

        Raises:
            PluginLoadError: If plugin loading fails
            PluginValidationError: If manifest validation fails
        """
        plugin_dir = Path(plugin_dir).resolve()

        if not plugin_dir.exists():
            raise PluginLoadError(f"Plugin directory not found: {plugin_dir}")

        _debug(f"Loading plugin from: {plugin_dir}")

        # Load and validate manifest
        try:
            metadata = self._load_metadata(plugin_dir)
            _debug_verbose(f"  Loaded metadata: {metadata.name} v{metadata.version}")
        except Exception as e:
            raise PluginValidationError(f"Invalid plugin manifest: {e}") from e

        # Check version compatibility
        is_compatible, error_msg = self._check_version_compatibility(
            metadata.name,
            metadata.auto_claude_version
        )
        if not is_compatible:
            raise PluginValidationError(error_msg)

        # Find plugin module (plugin.py or __init__.py)
        module_path = self._find_plugin_module(plugin_dir)
        if not module_path:
            raise PluginLoadError(
                f"Plugin module not found: Expected {plugin_dir}/plugin.py or {plugin_dir}/__init__.py"
            )

        _debug_verbose(f"  Loading module: {module_path}")

        # Dynamically import plugin module
        try:
            plugin_class = self._import_plugin_module(
                module_path, metadata.name, plugin_dir
            )
        except Exception as e:
            raise PluginLoadError(f"Failed to import plugin module: {e}") from e

        # Instantiate plugin
        try:
            plugin = plugin_class(metadata)
            _debug_verbose(f"  Instantiated plugin class: {plugin_class.__name__}")
        except Exception as e:
            raise PluginLoadError(f"Failed to instantiate plugin: {e}") from e

        # Set up sandbox for plugin execution
        allowed_dirs = [plugin_dir]
        if project_dir:
            allowed_dirs.append(Path(project_dir).resolve())

        plugin._sandbox = PluginSandbox(
            plugin_dir=plugin_dir,
            allowed_dirs=allowed_dirs,
            limits=limits or self.default_limits,
        )
        _debug_verbose(f"  Configured sandbox with {len(allowed_dirs)} allowed dirs")

        _debug_success(f"Loaded plugin: {metadata.name} v{metadata.version}")
        return plugin

    def validate_plugin_security(self, plugin_dir: Path) -> tuple[bool, list[str]]:
        """
        Perform security validation on plugin files.

        Checks for:
        - Python syntax errors
        - Suspicious imports (subprocess, os.system, eval, exec)
        - Potential secrets in code
        - Malicious code patterns

        Args:
            plugin_dir: Directory containing the plugin

        Returns:
            Tuple of (is_safe, warnings) where is_safe is True if plugin passes
            all security checks, and warnings is a list of security concerns found
        """
        warnings = []
        is_safe = True

        debug_verbose("security", f"Validating security for plugin in: {plugin_dir}")

        # Find all Python files in plugin directory
        python_files = list(plugin_dir.rglob("*.py"))

        if not python_files:
            warnings.append("No Python files found in plugin directory")
            is_safe = False
            return is_safe, warnings

        # Check each Python file
        for py_file in python_files:
            # Skip __pycache__ and hidden files
            if "__pycache__" in str(py_file) or py_file.name.startswith("."):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception as e:
                warnings.append(f"Failed to read {py_file.name}: {e}")
                is_safe = False
                continue

            # 1. Validate Python syntax
            try:
                ast.parse(content)
            except SyntaxError as e:
                warnings.append(f"Syntax error in {py_file.name} (line {e.lineno}): {e.msg}")
                is_safe = False
                continue

            # 2. Check for suspicious imports
            suspicious_imports = self._check_suspicious_imports(content, py_file.name)
            if suspicious_imports:
                warnings.extend(suspicious_imports)
                # Note: Suspicious imports are warnings, not blockers

            # 3. Check for dangerous function calls
            dangerous_calls = self._check_dangerous_calls(content, py_file.name)
            if dangerous_calls:
                warnings.extend(dangerous_calls)
                is_safe = False  # Block plugins with dangerous calls

            # 4. Check for hardcoded secrets (using patterns from scan_secrets)
            secret_warnings = self._check_for_secrets(content, py_file.name)
            if secret_warnings:
                warnings.extend(secret_warnings)
                is_safe = False  # Block plugins with hardcoded secrets

        if not warnings:
            debug_success("security", "Plugin passed all security checks")
        else:
            debug_warning("security", f"Found {len(warnings)} security concerns")
            for warning in warnings:
                debug_warning("security", f"  - {warning}")

        return is_safe, warnings

    def _check_suspicious_imports(self, content: str, filename: str) -> list[str]:
        """Check for suspicious imports that may indicate malicious behavior."""
        warnings = []

        # Patterns for suspicious imports
        suspicious_patterns = [
            (r"import\s+subprocess", "Imports subprocess module (shell command execution)"),
            (r"from\s+subprocess\s+import", "Imports from subprocess module"),
            (r"import\s+os\b", "Imports os module (filesystem access)"),
            (r"from\s+os\s+import", "Imports from os module"),
            (r"import\s+socket", "Imports socket module (network access)"),
            (r"from\s+socket\s+import", "Imports from socket module"),
            (r"import\s+requests", "Imports requests module (HTTP requests)"),
            (r"import\s+urllib", "Imports urllib module (HTTP requests)"),
        ]

        for pattern, description in suspicious_patterns:
            if re.search(pattern, content):
                warnings.append(f"{filename}: {description}")

        return warnings

    def _check_dangerous_calls(self, content: str, filename: str) -> list[str]:
        """Check for dangerous function calls that should block plugin installation."""
        warnings = []

        # Patterns for dangerous function calls (these block installation)
        dangerous_patterns = [
            (r"\beval\s*\(", "Uses eval() - arbitrary code execution risk"),
            (r"\bexec\s*\(", "Uses exec() - arbitrary code execution risk"),
            (r"\bcompile\s*\(", "Uses compile() - code compilation risk"),
            (r"\b__import__\s*\(", "Uses __import__() - dynamic import risk"),
            (r"os\.system\s*\(", "Uses os.system() - shell command execution"),
            (r"os\.popen\s*\(", "Uses os.popen() - shell command execution"),
            (r"subprocess\.call\s*\(", "Uses subprocess.call() - command execution"),
            (r"subprocess\.run\s*\(", "Uses subprocess.run() - command execution"),
            (r"subprocess\.Popen\s*\(", "Uses subprocess.Popen() - command execution"),
        ]

        for pattern, description in dangerous_patterns:
            if re.search(pattern, content):
                warnings.append(f"{filename}: {description}")

        return warnings

    def _check_for_secrets(self, content: str, filename: str) -> list[str]:
        """Check for hardcoded secrets using patterns from scan_secrets module."""
        warnings = []

        # Service-specific patterns (subset of most common ones)
        secret_patterns = [
            (r"sk-[a-zA-Z0-9]{20,}", "Anthropic/OpenAI-style API key"),
            (r"sk-ant-[a-zA-Z0-9-]{20,}", "Anthropic API key"),
            (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
            (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
            (r"AIza[0-9A-Za-z_-]{35}", "Google API Key"),
            # Generic patterns
            (r'(?:api[_-]?key|apikey|api_secret)\s*[:=]\s*["\']([a-zA-Z0-9_-]{32,})["\']',
             "API key assignment"),
            (r'(?:access[_-]?token|auth[_-]?token)\s*[:=]\s*["\']([a-zA-Z0-9_-]{32,})["\']',
             "Token assignment"),
            (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Private key"),
        ]

        # False positive patterns (don't flag these)
        false_positive_patterns = [
            r"process\.env\.",
            r"os\.environ",
            r"os\.getenv",
            r"your[-_]?api[-_]?key",
            r"xxx+",
            r"placeholder",
            r"example",
            r"<[A-Z_]+>",
        ]

        lines = content.splitlines()
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            # Check for secrets
            for pattern, description in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Check if it's a false positive
                    is_false_positive = False
                    for fp_pattern in false_positive_patterns:
                        if re.search(fp_pattern, line, re.IGNORECASE):
                            is_false_positive = True
                            break

                    if not is_false_positive:
                        warnings.append(
                            f"{filename} (line {line_num}): Potential {description}"
                        )

        return warnings

    def _load_metadata(self, plugin_dir: Path) -> PluginMetadata:
        """
        Load and validate plugin metadata from plugin.json.

        Args:
            plugin_dir: Directory containing plugin.json

        Returns:
            Validated PluginMetadata instance

        Raises:
            PluginValidationError: If manifest is missing or invalid
        """
        manifest_path = plugin_dir / "plugin.json"

        if not manifest_path.exists():
            raise PluginValidationError(f"Missing plugin.json in {plugin_dir.name}")

        try:
            with open(manifest_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise PluginValidationError(f"Invalid JSON in plugin.json: {e}") from e
        except Exception as e:
            raise PluginValidationError(f"Failed to read plugin.json: {e}") from e

        # Validate required fields
        required_fields = ["name", "version", "author", "description", "plugin_type"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise PluginValidationError(
                f"Missing required fields in plugin.json: {', '.join(missing)}"
            )

        # Validate plugin_type
        try:
            PluginType(data["plugin_type"])
        except ValueError as e:
            raise PluginValidationError(
                f"Invalid plugin_type '{data['plugin_type']}'. "
                f"Must be one of: {', '.join([t.value for t in PluginType])}"
            ) from e

        # Create metadata
        try:
            metadata = PluginMetadata.from_dict(data)
        except Exception as e:
            raise PluginValidationError(f"Invalid plugin metadata: {e}") from e

        return metadata

    def _find_plugin_module(self, plugin_dir: Path) -> Path | None:
        """
        Find plugin module file (plugin.py or __init__.py).

        Args:
            plugin_dir: Directory containing the plugin

        Returns:
            Path to plugin module or None if not found
        """
        # Try plugin.py first
        plugin_py = plugin_dir / "plugin.py"
        if plugin_py.exists():
            return plugin_py

        # Try __init__.py (package-style plugin)
        init_py = plugin_dir / "__init__.py"
        if init_py.exists():
            return init_py

        return None

    def _import_plugin_module(
        self,
        module_path: Path,
        plugin_name: str,
        plugin_dir: Path,
    ) -> type[PluginBase]:
        """
        Dynamically import plugin module and extract plugin class.

        Args:
            module_path: Path to plugin module file
            plugin_name: Name of the plugin (for module naming)
            plugin_dir: Plugin directory path

        Returns:
            Plugin class (subclass of PluginBase)

        Raises:
            PluginLoadError: If module import fails or plugin class not found
        """
        # Create unique module name to avoid conflicts
        module_name = f"auto_claude_plugin_{plugin_name.replace('-', '_')}"

        # Add plugin directory to Python path temporarily
        plugin_dir_str = str(plugin_dir)
        if plugin_dir_str not in sys.path:
            sys.path.insert(0, plugin_dir_str)

        try:
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise PluginLoadError(f"Failed to create module spec for {module_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find plugin class (must be PluginBase subclass)
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PluginBase)
                    and attr is not PluginBase
                ):
                    plugin_class = attr
                    break

            if plugin_class is None:
                raise PluginLoadError(
                    f"No PluginBase subclass found in {module_path.name}"
                )

            return plugin_class

        except Exception as e:
            raise PluginLoadError(f"Failed to import plugin module: {e}") from e
        finally:
            # Clean up sys.path
            if plugin_dir_str in sys.path:
                sys.path.remove(plugin_dir_str)


def discover_plugins(
    user_plugins_dir: Path | None = None,
    system_plugins_dir: Path | None = None,
) -> list[PluginMetadata]:
    """
    Convenience function to discover all plugins.

    Creates a PluginLoader instance and discovers plugins in both
    user and system directories.

    Args:
        user_plugins_dir: Directory containing user-installed plugins (optional)
        system_plugins_dir: Directory containing system/built-in plugins (optional)

    Returns:
        List of PluginMetadata for all discovered plugins

    Example:
        >>> from plugins.loader import discover_plugins
        >>> plugins = discover_plugins()
        >>> for plugin in plugins:
        ...     print(f"{plugin.name}: {plugin.description}")
    """
    loader = PluginLoader(
        user_plugins_dir=user_plugins_dir,
        system_plugins_dir=system_plugins_dir,
    )
    return loader.discover_plugins()
