"""
Migration Planner Module
========================

Creates and manages migration plans for framework, library, and language migrations.
Supports incremental migration strategies with checkpoints and rollback capability.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from analysis.analyzers.context.migrations_detector import MigrationsDetector


class MigrationComplexity(Enum):
    """Migration complexity levels for effort estimation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MigrationType(Enum):
    """Supported migration types."""

    REACT_CLASS_TO_HOOKS = "react_class_to_hooks"
    PYTHON_2_TO_3 = "python_2_to_3"
    DJANGO_UPGRADE = "django_upgrade"
    NODE_UPGRADE = "node_upgrade"
    TYPESCRIPT_MIGRATION = "typescript_migration"
    DATABASE_MIGRATION = "database_migration"
    FRAMEWORK_UPGRADE = "framework_upgrade"
    LIBRARY_REPLACEMENT = "library_replacement"
    CUSTOM = "custom"


@dataclass
class MigrationPhase:
    """Represents a single phase in a migration plan."""

    id: str
    name: str
    description: str
    complexity: MigrationComplexity
    dependencies: list[str] = field(default_factory=list)
    files_to_migrate: list[str] = field(default_factory=list)
    validation_criteria: list[str] = field(default_factory=list)
    rollback_strategy: str = ""
    estimated_changes: int = 0


@dataclass
class MigrationCheckpoint:
    """Defines a validation checkpoint in the migration."""

    id: str
    phase_id: str
    name: str
    validation_steps: list[str]
    success_criteria: list[str]
    rollback_command: str


class MigrationPlanner:
    """
    Plans and manages code migrations with incremental steps and checkpoints.

    Analyzes codebase to identify migration opportunities, creates structured
    migration plans with phases, estimates effort, and defines rollback strategies.
    """

    def __init__(self, project_dir: Path):
        """
        Initialize migration planner for a project.

        Args:
            project_dir: Root directory of the project to migrate
        """
        self.project_dir = Path(project_dir).resolve()
        self.phases: list[MigrationPhase] = []
        self.checkpoints: list[MigrationCheckpoint] = []

    def analyze_project(self) -> dict[str, Any]:
        """
        Analyze project to understand current state and migration needs.

        Returns:
            Dictionary with:
            - framework_info: Detected frameworks and versions
            - migration_setup: Existing migration tools (if any)
            - code_patterns: Detected patterns that may need migration
            - complexity_estimate: Overall migration complexity
        """
        analysis: dict[str, Any] = {}

        # Detect existing migration setup
        detector = MigrationsDetector(self.project_dir, analysis)
        detector.detect()

        # Analyze for common migration patterns
        patterns = self._detect_migration_patterns()

        return {
            "framework_info": self._detect_frameworks(),
            "migration_setup": analysis.get("migrations"),
            "code_patterns": patterns,
            "complexity_estimate": self._estimate_overall_complexity(patterns),
        }

    def create_plan(
        self,
        migration_type: MigrationType,
        target_version: str | None = None,
        incremental: bool = True,
    ) -> dict[str, Any]:
        """
        Create a structured migration plan for a specific migration type.

        Args:
            migration_type: Type of migration to plan
            target_version: Target framework/library version (optional)
            incremental: Whether to create incremental phases (default: True)

        Returns:
            Dictionary with:
            - phases: List of migration phases
            - checkpoints: List of validation checkpoints
            - total_estimated_changes: Estimated number of changes
            - rollback_strategy: Overall rollback approach
        """
        # Clear existing plan
        self.phases = []
        self.checkpoints = []

        # Create migration-specific plan
        if migration_type == MigrationType.REACT_CLASS_TO_HOOKS:
            self._plan_react_hooks_migration()
        elif migration_type == MigrationType.PYTHON_2_TO_3:
            self._plan_python_2_to_3_migration()
        elif migration_type == MigrationType.DJANGO_UPGRADE:
            self._plan_django_upgrade(target_version)
        elif migration_type == MigrationType.TYPESCRIPT_MIGRATION:
            self._plan_typescript_migration()
        elif migration_type == MigrationType.FRAMEWORK_UPGRADE:
            self._plan_framework_upgrade(target_version)
        else:
            self._plan_generic_migration()

        # Create checkpoints for each phase
        self._generate_checkpoints()

        total_changes = sum(phase.estimated_changes for phase in self.phases)

        return {
            "migration_type": migration_type.value,
            "target_version": target_version,
            "phases": [self._phase_to_dict(p) for p in self.phases],
            "checkpoints": [self._checkpoint_to_dict(c) for c in self.checkpoints],
            "total_estimated_changes": total_changes,
            "rollback_strategy": self._get_rollback_strategy(),
        }

    def _detect_frameworks(self) -> dict[str, Any]:
        """Detect frameworks and their versions in the project."""
        frameworks = {}

        # Check for Node.js projects
        package_json = self.project_dir / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }

                # Detect React
                if "react" in deps:
                    frameworks["react"] = deps["react"]

                # Detect Next.js
                if "next" in deps:
                    frameworks["next"] = deps["next"]

                # Detect Vue
                if "vue" in deps:
                    frameworks["vue"] = deps["vue"]

                # Detect Node version
                if "engines" in data and "node" in data["engines"]:
                    frameworks["node"] = data["engines"]["node"]

            except (json.JSONDecodeError, OSError):
                pass  # Skip malformed or unreadable package.json

        # Check for Python projects
        requirements_txt = self.project_dir / "requirements.txt"
        if requirements_txt.exists():
            try:
                content = requirements_txt.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # Extract package name and version
                    match = re.match(r"([a-zA-Z0-9\-_]+)[>=<~!]=+(.+)", line)
                    if match:
                        package, version = match.groups()
                        package_lower = package.lower()

                        if package_lower == "django":
                            frameworks["django"] = version
                        elif package_lower == "flask":
                            frameworks["flask"] = version
                        elif package_lower == "fastapi":
                            frameworks["fastapi"] = version

            except OSError:
                pass  # Skip unreadable requirements.txt

        return frameworks

    def _detect_migration_patterns(self) -> dict[str, Any]:
        """Detect code patterns that may need migration."""
        patterns = {
            "react_class_components": 0,
            "python2_patterns": 0,
            "deprecated_imports": 0,
            "old_api_calls": 0,
        }

        # Detect React class components
        for file in self.project_dir.rglob("*.jsx"):
            try:
                content = file.read_text(encoding="utf-8")
                patterns["react_class_components"] += len(
                    re.findall(r"class\s+\w+\s+extends\s+(React\.)?Component", content)
                )
            except Exception:
                continue

        for file in self.project_dir.rglob("*.tsx"):
            try:
                content = file.read_text(encoding="utf-8")
                patterns["react_class_components"] += len(
                    re.findall(r"class\s+\w+\s+extends\s+(React\.)?Component", content)
                )
            except Exception:
                continue

        # Detect Python 2 patterns
        for file in self.project_dir.rglob("*.py"):
            try:
                content = file.read_text(encoding="utf-8")
                # Look for Python 2 specific patterns
                patterns["python2_patterns"] += len(
                    re.findall(
                        r"print\s+[^\(]|xrange\(|unicode\(|\.iteritems\(", content
                    )
                )
            except Exception:
                continue

        return patterns

    def _estimate_overall_complexity(
        self, patterns: dict[str, Any]
    ) -> MigrationComplexity:
        """Estimate overall migration complexity based on detected patterns."""
        total_changes = sum(v for v in patterns.values() if isinstance(v, int))

        if total_changes == 0:
            return MigrationComplexity.LOW
        elif total_changes < 50:
            return MigrationComplexity.MEDIUM
        elif total_changes < 200:
            return MigrationComplexity.HIGH
        else:
            return MigrationComplexity.CRITICAL

    def _plan_react_hooks_migration(self) -> None:
        """Plan React class components to hooks migration."""
        self.phases = [
            MigrationPhase(
                id="phase-1",
                name="Foundation Setup",
                description="Set up hooks infrastructure and compatibility layer",
                complexity=MigrationComplexity.LOW,
                dependencies=[],
                validation_criteria=[
                    "All existing tests pass",
                    "No ESLint errors",
                    "Builds successfully",
                ],
                rollback_strategy="Git reset to baseline checkpoint",
                estimated_changes=5,
            ),
            MigrationPhase(
                id="phase-2",
                name="Migrate Leaf Components",
                description="Convert components with no dependencies to hooks",
                complexity=MigrationComplexity.MEDIUM,
                dependencies=["phase-1"],
                validation_criteria=[
                    "Component tests pass",
                    "No prop-types warnings",
                    "Renders correctly",
                ],
                rollback_strategy="Restore files from checkpoint-1",
                estimated_changes=20,
            ),
            MigrationPhase(
                id="phase-3",
                name="Migrate Parent Components",
                description="Convert components that depend on migrated components",
                complexity=MigrationComplexity.MEDIUM,
                dependencies=["phase-2"],
                validation_criteria=[
                    "Integration tests pass",
                    "State management works",
                    "Effects trigger correctly",
                ],
                rollback_strategy="Restore files from checkpoint-2",
                estimated_changes=30,
            ),
            MigrationPhase(
                id="phase-4",
                name="Remove Compatibility Layer",
                description="Clean up compatibility code and update patterns",
                complexity=MigrationComplexity.LOW,
                dependencies=["phase-3"],
                validation_criteria=[
                    "All tests pass",
                    "No deprecated warnings",
                    "Code coverage maintained",
                ],
                rollback_strategy="Restore files from checkpoint-3",
                estimated_changes=10,
            ),
        ]

    def _plan_python_2_to_3_migration(self) -> None:
        """Plan Python 2 to Python 3 migration."""
        self.phases = [
            MigrationPhase(
                id="phase-1",
                name="Print Statements",
                description="Convert print statements to print() functions",
                complexity=MigrationComplexity.LOW,
                dependencies=[],
                validation_criteria=[
                    "All Python files have valid syntax",
                    "Tests pass",
                ],
                rollback_strategy="Git reset to baseline",
                estimated_changes=50,
            ),
            MigrationPhase(
                id="phase-2",
                name="Import Changes",
                description="Update imports for Python 3 compatibility",
                complexity=MigrationComplexity.MEDIUM,
                dependencies=["phase-1"],
                validation_criteria=[
                    "No import errors",
                    "Tests pass",
                ],
                rollback_strategy="Restore from checkpoint-1",
                estimated_changes=30,
            ),
            MigrationPhase(
                id="phase-3",
                name="String/Unicode Handling",
                description="Update string and unicode handling for Python 3",
                complexity=MigrationComplexity.HIGH,
                dependencies=["phase-2"],
                validation_criteria=[
                    "Encoding tests pass",
                    "No unicode errors",
                ],
                rollback_strategy="Restore from checkpoint-2",
                estimated_changes=40,
            ),
            MigrationPhase(
                id="phase-4",
                name="Dict Methods",
                description="Update dict methods (iteritems -> items, etc.)",
                complexity=MigrationComplexity.MEDIUM,
                dependencies=["phase-3"],
                validation_criteria=[
                    "All tests pass",
                    "Performance maintained",
                ],
                rollback_strategy="Restore from checkpoint-3",
                estimated_changes=25,
            ),
        ]

    def _plan_django_upgrade(self, target_version: str | None) -> None:
        """Plan Django version upgrade."""
        self.phases = [
            MigrationPhase(
                id="phase-1",
                name="Update Dependencies",
                description="Update Django and related packages",
                complexity=MigrationComplexity.LOW,
                dependencies=[],
                validation_criteria=[
                    "Dependencies install successfully",
                    "No version conflicts",
                ],
                rollback_strategy="Restore requirements.txt from checkpoint-0",
                estimated_changes=5,
            ),
            MigrationPhase(
                id="phase-2",
                name="Settings and Middleware",
                description="Update Django settings and middleware configuration",
                complexity=MigrationComplexity.MEDIUM,
                dependencies=["phase-1"],
                validation_criteria=[
                    "Server starts successfully",
                    "No deprecation warnings",
                ],
                rollback_strategy="Restore settings.py from checkpoint-1",
                estimated_changes=15,
            ),
            MigrationPhase(
                id="phase-3",
                name="URL Patterns",
                description="Update URL patterns to new syntax",
                complexity=MigrationComplexity.MEDIUM,
                dependencies=["phase-2"],
                validation_criteria=[
                    "All URLs resolve",
                    "Routing tests pass",
                ],
                rollback_strategy="Restore urls.py files from checkpoint-2",
                estimated_changes=20,
            ),
            MigrationPhase(
                id="phase-4",
                name="Models and Migrations",
                description="Update models and run new migrations",
                complexity=MigrationComplexity.HIGH,
                dependencies=["phase-3"],
                validation_criteria=[
                    "Migrations apply successfully",
                    "Model tests pass",
                    "Database schema correct",
                ],
                rollback_strategy="Restore models and rollback migrations",
                estimated_changes=30,
            ),
        ]

    def _plan_typescript_migration(self) -> None:
        """Plan JavaScript to TypeScript migration."""
        self.phases = [
            MigrationPhase(
                id="phase-1",
                name="TypeScript Setup",
                description="Configure TypeScript and type definitions",
                complexity=MigrationComplexity.LOW,
                dependencies=[],
                validation_criteria=[
                    "TypeScript compiles",
                    "Type definitions installed",
                ],
                rollback_strategy="Remove tsconfig.json and type packages",
                estimated_changes=5,
            ),
            MigrationPhase(
                id="phase-2",
                name="Migrate Utilities",
                description="Convert utility files to TypeScript",
                complexity=MigrationComplexity.MEDIUM,
                dependencies=["phase-1"],
                validation_criteria=[
                    "No type errors",
                    "Tests pass",
                ],
                rollback_strategy="Restore .js files from checkpoint-1",
                estimated_changes=25,
            ),
            MigrationPhase(
                id="phase-3",
                name="Migrate Components",
                description="Convert components to TypeScript",
                complexity=MigrationComplexity.HIGH,
                dependencies=["phase-2"],
                validation_criteria=[
                    "Type checking passes",
                    "Component tests pass",
                ],
                rollback_strategy="Restore component files from checkpoint-2",
                estimated_changes=50,
            ),
        ]

    def _plan_framework_upgrade(self, target_version: str | None) -> None:
        """Plan generic framework version upgrade."""
        self.phases = [
            MigrationPhase(
                id="phase-1",
                name="Dependency Update",
                description=f"Update framework to {target_version or 'latest version'}",
                complexity=MigrationComplexity.MEDIUM,
                dependencies=[],
                validation_criteria=[
                    "Dependencies resolve",
                    "Build succeeds",
                ],
                rollback_strategy="Restore package files from baseline",
                estimated_changes=10,
            ),
            MigrationPhase(
                id="phase-2",
                name="API Updates",
                description="Update deprecated API calls to new patterns",
                complexity=MigrationComplexity.HIGH,
                dependencies=["phase-1"],
                validation_criteria=[
                    "No deprecation warnings",
                    "Tests pass",
                ],
                rollback_strategy="Restore code files from checkpoint-1",
                estimated_changes=40,
            ),
        ]

    def _plan_generic_migration(self) -> None:
        """Plan generic custom migration."""
        self.phases = [
            MigrationPhase(
                id="phase-1",
                name="Analysis and Planning",
                description="Analyze codebase and create detailed migration plan",
                complexity=MigrationComplexity.LOW,
                dependencies=[],
                validation_criteria=[
                    "Migration plan documented",
                    "Risks identified",
                ],
                rollback_strategy="N/A - planning phase",
                estimated_changes=0,
            ),
            MigrationPhase(
                id="phase-2",
                name="Incremental Implementation",
                description="Implement changes incrementally with validation",
                complexity=MigrationComplexity.MEDIUM,
                dependencies=["phase-1"],
                validation_criteria=[
                    "Tests pass at each step",
                    "No regressions",
                ],
                rollback_strategy="Restore from previous checkpoint",
                estimated_changes=50,
            ),
        ]

    def _generate_checkpoints(self) -> None:
        """Generate validation checkpoints for each phase."""
        self.checkpoints = []

        for i, phase in enumerate(self.phases):
            checkpoint = MigrationCheckpoint(
                id=f"checkpoint-{i + 1}",
                phase_id=phase.id,
                name=f"Checkpoint after {phase.name}",
                validation_steps=[
                    "Run test suite",
                    "Check for build errors",
                    "Verify no regressions",
                ],
                success_criteria=phase.validation_criteria,
                rollback_command=f".migration-checkpoints/rollback/checkpoint-{i + 1}.sh",
            )
            self.checkpoints.append(checkpoint)

    def _get_rollback_strategy(self) -> str:
        """Get overall rollback strategy description."""
        return (
            "Each phase creates a git checkpoint with rollback script. "
            "To rollback, run the checkpoint rollback script from "
            ".migration-checkpoints/rollback/ directory. "
            "All checkpoints are ordered and can be rolled back sequentially."
        )

    def _phase_to_dict(self, phase: MigrationPhase) -> dict[str, Any]:
        """Convert MigrationPhase to dictionary."""
        return {
            "id": phase.id,
            "name": phase.name,
            "description": phase.description,
            "complexity": phase.complexity.value,
            "dependencies": phase.dependencies,
            "files_to_migrate": phase.files_to_migrate,
            "validation_criteria": phase.validation_criteria,
            "rollback_strategy": phase.rollback_strategy,
            "estimated_changes": phase.estimated_changes,
        }

    def _checkpoint_to_dict(self, checkpoint: MigrationCheckpoint) -> dict[str, Any]:
        """Convert MigrationCheckpoint to dictionary."""
        return {
            "id": checkpoint.id,
            "phase_id": checkpoint.phase_id,
            "name": checkpoint.name,
            "validation_steps": checkpoint.validation_steps,
            "success_criteria": checkpoint.success_criteria,
            "rollback_command": checkpoint.rollback_command,
        }
