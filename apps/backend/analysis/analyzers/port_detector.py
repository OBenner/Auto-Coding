"""
Port Detector Module
====================

Detects application ports from multiple sources including entry points,
environment files, Docker Compose, configuration files, and scripts.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import BaseAnalyzer

# Compiled regex patterns for port detection
# Entry point patterns
PATTERN_UVICORN_RUN = re.compile(r"uvicorn\.run\([^)]*port\s*=\s*(\d+)")
PATTERN_APP_RUN = re.compile(r"\.run\([^)]*port\s*=\s*(\d+)")
PATTERN_PORT_ASSIGNMENT = re.compile(r"^\s*[Pp][Oo][Rr][Tt]\s*=\s*(\d+)", re.MULTILINE)
PATTERN_GETENV_PORT = re.compile(r'getenv\(\s*["\']PORT["\']\s*,\s*(\d+)')
PATTERN_ENVIRON_GET_PORT = re.compile(r'environ\.get\(\s*["\']PORT["\']\s*,\s*(\d+)')
PATTERN_APP_LISTEN = re.compile(r"\.listen\(\s*(\d+)")
PATTERN_JS_PORT_ASSIGNMENT = re.compile(
    r"(?:const|let|var)\s+[Pp][Oo][Rr][Tt]\s*=\s*(\d+)"
)
PATTERN_PROCESS_ENV_PORT = re.compile(r"process\.env\.PORT\s*\|\|\s*(\d+)")
PATTERN_PROCESS_ENV_PORT_NUMBER = re.compile(
    r"Number\(process\.env\.PORT\)\s*\|\|\s*(\d+)"
)
PATTERN_GO_PORT = re.compile(r':\s*(\d+)(?:["\s]|$)')
PATTERN_RUST_BIND = re.compile(r'\.bind\(["\'][\d.]+:(\d+)')

# Environment file patterns
PATTERN_ENV_PORT = re.compile(r"^\s*PORT\s*=\s*(\d+)", re.MULTILINE)
PATTERN_ENV_API_PORT = re.compile(r"^\s*API_PORT\s*=\s*(\d+)", re.MULTILINE)
PATTERN_ENV_SERVER_PORT = re.compile(r"^\s*SERVER_PORT\s*=\s*(\d+)", re.MULTILINE)
PATTERN_ENV_APP_PORT = re.compile(r"^\s*APP_PORT\s*=\s*(\d+)", re.MULTILINE)

# Docker compose patterns
PATTERN_DOCKER_PORT_MAPPING = re.compile(r'^\s*-\s*["\']?(\d+):\d+["\']?')
PATTERN_DOCKER_SERVICE = re.compile(r"^\s*\w+\s*:")
PATTERN_DOCKER_PORTS = re.compile(r"ports:")

# Config file patterns
PATTERN_CONFIG_PORT_ASSIGNMENT = re.compile(r"[Pp][Oo][Rr][Tt]\s*=\s*(\d+)")
PATTERN_CONFIG_JSON_PORT = re.compile(r'["\']port["\']\s*:\s*(\d+)')

# Package.json script patterns
PATTERN_SCRIPT_P_FLAG = re.compile(r"-p\s+(\d+)")
PATTERN_SCRIPT_PORT_FLAG = re.compile(r"--port\s+(\d+)")
PATTERN_SCRIPT_PORT_ENV = re.compile(r"PORT=(\d+)")


class PortDetector(BaseAnalyzer):
    """Detects application ports from various configuration sources."""

    def __init__(self, path: Path, analysis: dict[str, Any]):
        super().__init__(path)
        self.analysis = analysis

    def detect_port_from_sources(self, default_port: int) -> int:
        """
        Robustly detect the actual port by checking multiple sources.

        Checks in order of priority:
        1. Entry point files (app.py, main.py, etc.) for uvicorn.run(), app.run(), etc.
        2. Environment files (.env, .env.local, .env.development)
        3. Docker Compose port mappings
        4. Configuration files (config.py, settings.py, etc.)
        5. Package.json scripts (for Node.js)
        6. Makefile/shell scripts
        7. Falls back to default_port if nothing found

        Args:
            default_port: The framework's conventional default port

        Returns:
            Detected port or default_port if not found
        """
        # 1. Check entry point files for explicit port definitions
        port = self._detect_port_in_entry_points()
        if port:
            return port

        # 2. Check environment files
        port = self._detect_port_in_env_files()
        if port:
            return port

        # 3. Check Docker Compose
        port = self._detect_port_in_docker_compose()
        if port:
            return port

        # 4. Check configuration files
        port = self._detect_port_in_config_files()
        if port:
            return port

        # 5. Check package.json scripts (for Node.js)
        if self.analysis.get("language") in ["JavaScript", "TypeScript"]:
            port = self._detect_port_in_package_scripts()
            if port:
                return port

        # 6. Check Makefile/shell scripts
        port = self._detect_port_in_scripts()
        if port:
            return port

        # Fall back to default
        return default_port

    def _detect_port_in_entry_points(self) -> int | None:
        """Detect port in entry point files."""
        entry_files = [
            "app.py",
            "main.py",
            "server.py",
            "__main__.py",
            "asgi.py",
            "wsgi.py",
            "src/app.py",
            "src/main.py",
            "src/server.py",
            "index.js",
            "index.ts",
            "server.js",
            "server.ts",
            "main.js",
            "main.ts",
            "src/index.js",
            "src/index.ts",
            "src/server.js",
            "src/server.ts",
            "main.go",
            "cmd/main.go",
            "src/main.rs",
        ]

        # Compiled patterns to search for ports
        patterns = [
            PATTERN_UVICORN_RUN,
            PATTERN_APP_RUN,
            PATTERN_PORT_ASSIGNMENT,
            PATTERN_GETENV_PORT,
            PATTERN_ENVIRON_GET_PORT,
            PATTERN_APP_LISTEN,
            PATTERN_JS_PORT_ASSIGNMENT,
            PATTERN_PROCESS_ENV_PORT,
            PATTERN_PROCESS_ENV_PORT_NUMBER,
            PATTERN_GO_PORT,
            PATTERN_RUST_BIND,
        ]

        for entry_file in entry_files:
            content = self._read_file(entry_file)
            if not content:
                continue

            for pattern in patterns:
                matches = pattern.findall(content)
                if matches:
                    # Return the first valid port found
                    for match in matches:
                        try:
                            port = int(match)
                            if 1000 <= port <= 65535:  # Valid port range
                                return port
                        except ValueError:
                            continue

        return None

    def _detect_port_in_env_files(self) -> int | None:
        """Detect port in environment files."""
        env_files = [
            ".env",
            ".env.local",
            ".env.development",
            ".env.dev",
            "config/.env",
            "config/.env.local",
            "../.env",
        ]

        patterns = [
            PATTERN_ENV_PORT,
            PATTERN_ENV_API_PORT,
            PATTERN_ENV_SERVER_PORT,
            PATTERN_ENV_APP_PORT,
        ]

        for env_file in env_files:
            content = self._read_file(env_file)
            if not content:
                continue

            for pattern in patterns:
                matches = pattern.findall(content)
                if matches:
                    try:
                        port = int(matches[0])
                        if 1000 <= port <= 65535:
                            return port
                    except ValueError:
                        continue

        return None

    def _detect_port_in_docker_compose(self) -> int | None:
        """Detect port from docker-compose.yml mappings."""
        compose_files = [
            "docker-compose.yml",
            "docker-compose.yaml",
            "../docker-compose.yml",
            "../docker-compose.yaml",
        ]

        service_name = self.path.name.lower()

        for compose_file in compose_files:
            content = self._read_file(compose_file)
            if not content:
                continue

            # Look for port mappings like "8050:8000" or "8050:8050"
            # Match the service name if possible
            service_pattern = re.compile(rf"^\s*{re.escape(service_name)}\s*:")

            in_service = False
            in_ports = False

            for line in content.split("\n"):
                # Check if we're in the right service block
                if service_pattern.match(line):
                    in_service = True
                    continue

                # Check if we hit another service
                if (
                    in_service
                    and PATTERN_DOCKER_SERVICE.match(line)
                    and "ports:" not in line
                ):
                    in_service = False
                    in_ports = False
                    continue

                # Check if we're in the ports section
                if in_service and "ports:" in line:
                    in_ports = True
                    continue

                # Extract port mapping
                if in_ports:
                    match = PATTERN_DOCKER_PORT_MAPPING.match(line)
                    if match:
                        try:
                            port = int(match.group(1))
                            if 1000 <= port <= 65535:
                                return port
                        except ValueError:
                            continue

        return None

    def _detect_port_in_config_files(self) -> int | None:
        """Detect port in configuration files."""
        config_files = [
            "config.py",
            "settings.py",
            "config/settings.py",
            "src/config.py",
            "config.json",
            "settings.json",
            "config/config.json",
            "config.toml",
            "settings.toml",
        ]

        for config_file in config_files:
            content = self._read_file(config_file)
            if not content:
                continue

            # Python config patterns
            patterns = [
                PATTERN_CONFIG_PORT_ASSIGNMENT,
                PATTERN_CONFIG_JSON_PORT,
            ]

            for pattern in patterns:
                matches = pattern.findall(content)
                if matches:
                    try:
                        port = int(matches[0])
                        if 1000 <= port <= 65535:
                            return port
                    except ValueError:
                        continue

        return None

    def _detect_port_in_package_scripts(self) -> int | None:
        """Detect port in package.json scripts."""
        pkg = self._read_json("package.json")
        if not pkg:
            return None

        scripts = pkg.get("scripts", {})

        # Look for port specifications in scripts
        # e.g., "dev": "next dev -p 3001"
        # e.g., "start": "node server.js --port 8050"
        patterns = [
            PATTERN_SCRIPT_P_FLAG,
            PATTERN_SCRIPT_PORT_FLAG,
            PATTERN_SCRIPT_PORT_ENV,
        ]

        for script in scripts.values():
            if not isinstance(script, str):
                continue

            for pattern in patterns:
                matches = pattern.findall(script)
                if matches:
                    try:
                        port = int(matches[0])
                        if 1000 <= port <= 65535:
                            return port
                    except ValueError:
                        continue

        return None

    def _detect_port_in_scripts(self) -> int | None:
        """Detect port in Makefile or shell scripts."""
        script_files = ["Makefile", "start.sh", "run.sh", "dev.sh"]

        patterns = [
            PATTERN_SCRIPT_PORT_ENV,
            PATTERN_SCRIPT_PORT_FLAG,
            PATTERN_SCRIPT_P_FLAG,
        ]

        for script_file in script_files:
            content = self._read_file(script_file)
            if not content:
                continue

            for pattern in patterns:
                matches = pattern.findall(content)
                if matches:
                    try:
                        port = int(matches[0])
                        if 1000 <= port <= 65535:
                            return port
                    except ValueError:
                        continue

        return None
