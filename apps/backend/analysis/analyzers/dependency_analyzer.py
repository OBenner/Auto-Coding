"""
Dependency Analyzer Module
===========================

Analyzes dependency updates for risk assessment and batching recommendations.
Integrates with DependencyScanner results to provide intelligent update strategies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .base import BaseAnalyzer

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class UpdateBatch:
    """
    Represents a batch of compatible dependency updates.

    Attributes:
        batch_id: Unique identifier for this batch
        update_type: Type of updates in this batch (major, minor, patch)
        ecosystem: Package ecosystem (python, npm, etc.)
        packages: List of package names in this batch
        risk_level: Overall risk level for this batch
        is_security_batch: Whether this batch contains security updates
        priority: Priority score (higher = more urgent)
        notes: Additional notes about this batch
    """

    batch_id: str
    update_type: str
    ecosystem: str
    packages: list[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high
    is_security_batch: bool = False
    priority: int = 0
    notes: str = ""


@dataclass
class DependencyRiskAssessment:
    """
    Risk assessment for a single dependency update.

    Attributes:
        package_name: Name of the package
        current_version: Current version
        target_version: Target version to update to
        update_type: Type of update (major, minor, patch)
        risk_level: Assessed risk level (low, medium, high)
        risk_factors: List of identified risk factors
        breaking_change_probability: Probability of breaking changes (0.0-1.0)
        recommended_action: Recommended action (update, defer, test_first, etc.)
        notes: Additional notes about this assessment
    """

    package_name: str
    current_version: str
    target_version: str
    update_type: str
    risk_level: str = "medium"
    risk_factors: list[str] = field(default_factory=list)
    breaking_change_probability: float = 0.5
    recommended_action: str = "test_first"
    notes: str = ""


# =============================================================================
# DEPENDENCY ANALYZER
# =============================================================================


class DependencyAnalyzer(BaseAnalyzer):
    """
    Analyzes dependency updates for risk assessment and batching.

    Integrates with DependencyScanner results to provide:
    - Risk classification for each update
    - Update batching recommendations
    - Breaking change probability assessment
    - Priority scoring for updates
    """

    def __init__(self, path: Path, analysis: dict[str, Any] | None = None):
        """
        Initialize the dependency analyzer.

        Args:
            path: Path to the project directory
            analysis: Optional analysis dict to populate with results
        """
        super().__init__(path)
        self.analysis = analysis if analysis is not None else {}

    def analyze_update_risk(
        self,
        package_name: str,
        current_version: str,
        target_version: str,
        ecosystem: str,
    ) -> DependencyRiskAssessment:
        """
        Analyze the risk of updating a single dependency.

        Provides:
        - Risk level classification (low, medium, high)
        - Breaking change probability estimation
        - Risk factors identification
        - Recommended action

        Args:
            package_name: Name of the package
            current_version: Current version
            target_version: Target version to update to
            ecosystem: Package ecosystem (python, npm, etc.)

        Returns:
            DependencyRiskAssessment with detailed risk analysis
        """
        # Classify update type based on semantic versioning
        update_type = self._classify_update_type(current_version, target_version)

        # Initialize risk factors
        risk_factors = []

        # Determine risk level and breaking change probability based on update type
        if update_type == "patch":
            risk_level = "low"
            breaking_change_probability = 0.1
            recommended_action = "update"
            risk_factors.append("Patch update - typically backwards compatible")

        elif update_type == "minor":
            risk_level = "medium"
            breaking_change_probability = 0.3
            recommended_action = "test_first"
            risk_factors.append("Minor update - may include new features")
            risk_factors.append("Review changelog for deprecations")

        elif update_type == "major":
            risk_level = "high"
            breaking_change_probability = 0.8
            recommended_action = "defer"
            risk_factors.append("Major update - likely contains breaking changes")
            risk_factors.append("Requires careful review and testing")
            risk_factors.append("May need code changes to adapt")

        else:  # unknown
            risk_level = "medium"
            breaking_change_probability = 0.5
            recommended_action = "test_first"
            risk_factors.append("Unable to determine update type")
            risk_factors.append("Version format may not follow semver")

        # Add ecosystem-specific risk factors
        if ecosystem == "python" and package_name in [
            "django",
            "flask",
            "fastapi",
            "sqlalchemy",
            "pytest",
        ]:
            risk_factors.append("Core framework dependency - requires thorough testing")
            breaking_change_probability = min(breaking_change_probability + 0.1, 1.0)

        elif ecosystem == "npm" and package_name in [
            "react",
            "vue",
            "angular",
            "express",
            "next",
            "typescript",
        ]:
            risk_factors.append("Core framework dependency - requires thorough testing")
            breaking_change_probability = min(breaking_change_probability + 0.1, 1.0)

        # Build notes
        notes = f"{update_type.capitalize()} update from {current_version} to {target_version}"
        if risk_level == "high":
            notes += ". Recommend reviewing release notes and creating a separate branch for testing."
        elif risk_level == "medium":
            notes += ". Test in development environment before merging."

        return DependencyRiskAssessment(
            package_name=package_name,
            current_version=current_version,
            target_version=target_version,
            update_type=update_type,
            risk_level=risk_level,
            risk_factors=risk_factors,
            breaking_change_probability=breaking_change_probability,
            recommended_action=recommended_action,
            notes=notes,
        )

    def batch_updates(self, updates: list[dict[str, Any]]) -> list[UpdateBatch]:
        """
        Group compatible updates into batches.

        Groups updates by:
        - Update type (major, minor, patch) and ecosystem
        - Security updates are separated into dedicated batches
        - Priority scoring based on severity and update type

        Strategy:
        - Security updates get their own batches (highest priority)
        - Patch updates are batched together (low risk, can be combined)
        - Minor updates are batched by ecosystem (medium risk)
        - Major updates are kept in separate batches (high risk, requires careful review)

        Args:
            updates: List of update dictionaries (from DependencyScanner)

        Returns:
            List of UpdateBatch objects, ordered by priority (highest first)
        """
        if not updates:
            return []

        batches: list[UpdateBatch] = []
        batch_counter = 0

        # Group updates by category for batching
        security_updates_by_ecosystem: dict[str, list[dict[str, Any]]] = {}
        patch_updates_by_ecosystem: dict[str, list[dict[str, Any]]] = {}
        minor_updates_by_ecosystem: dict[str, list[dict[str, Any]]] = {}
        major_updates: list[dict[str, Any]] = []
        unknown_updates_by_ecosystem: dict[str, list[dict[str, Any]]] = {}

        # Categorize updates
        for update in updates:
            ecosystem = update.get("ecosystem", "unknown")
            update_type = update.get("update_type", "unknown")
            is_security = update.get("is_security", False)

            if is_security:
                security_updates_by_ecosystem.setdefault(ecosystem, []).append(update)

            elif update_type == "patch":
                patch_updates_by_ecosystem.setdefault(ecosystem, []).append(update)

            elif update_type == "minor":
                minor_updates_by_ecosystem.setdefault(ecosystem, []).append(update)

            elif update_type == "major":
                major_updates.append(update)

            else:
                # Unknown update types (non-semver versions)
                unknown_updates_by_ecosystem.setdefault(ecosystem, []).append(update)

        # Create security update batches (highest priority)
        for ecosystem, sec_updates in security_updates_by_ecosystem.items():
            batch_counter += 1

            # Calculate overall severity for the batch
            severities = [u.get("severity") for u in sec_updates if u.get("severity")]
            if "critical" in severities:
                max_severity = "critical"
            elif "high" in severities:
                max_severity = "high"
            elif "medium" in severities:
                max_severity = "medium"
            else:
                max_severity = "low"

            # Calculate priority for the batch
            avg_priority = sum(
                self.get_update_priority(
                    u.get("name", ""),
                    u.get("update_type", ""),
                    True,
                    u.get("severity"),
                )
                for u in sec_updates
            ) // len(sec_updates)

            batch = UpdateBatch(
                batch_id=f"security-{ecosystem}-{batch_counter}",
                update_type="security",
                ecosystem=ecosystem,
                packages=[u.get("name", "") for u in sec_updates],
                risk_level="high",
                is_security_batch=True,
                priority=avg_priority,
                notes=f"Security updates for {len(sec_updates)} {ecosystem} package(s). "
                f"Max severity: {max_severity}. Recommend immediate update and testing.",
            )
            batches.append(batch)

        # Create patch update batches (low risk, can be combined)
        for ecosystem, patch_updates_list in patch_updates_by_ecosystem.items():
            batch_counter += 1

            avg_priority = sum(
                self.get_update_priority(
                    u.get("name", ""),
                    u.get("update_type", ""),
                    False,
                )
                for u in patch_updates_list
            ) // max(len(patch_updates_list), 1)

            batch = UpdateBatch(
                batch_id=f"patch-{ecosystem}-{batch_counter}",
                update_type="patch",
                ecosystem=ecosystem,
                packages=[u.get("name", "") for u in patch_updates_list],
                risk_level="low",
                is_security_batch=False,
                priority=avg_priority,
                notes=f"Patch updates for {len(patch_updates_list)} {ecosystem} package(s). "
                f"Low risk - typically backwards compatible. Safe to batch together.",
            )
            batches.append(batch)

        # Create minor update batches (medium risk)
        for ecosystem, minor_updates_list in minor_updates_by_ecosystem.items():
            batch_counter += 1

            avg_priority = sum(
                self.get_update_priority(
                    u.get("name", ""),
                    u.get("update_type", ""),
                    False,
                )
                for u in minor_updates_list
            ) // max(len(minor_updates_list), 1)

            batch = UpdateBatch(
                batch_id=f"minor-{ecosystem}-{batch_counter}",
                update_type="minor",
                ecosystem=ecosystem,
                packages=[u.get("name", "") for u in minor_updates_list],
                risk_level="medium",
                is_security_batch=False,
                priority=avg_priority,
                notes=f"Minor updates for {len(minor_updates_list)} {ecosystem} package(s). "
                f"Medium risk - may include new features. Test in development environment.",
            )
            batches.append(batch)

        # Create individual batches for major updates (high risk, one per package)
        for major_update in major_updates:
            batch_counter += 1
            ecosystem = major_update.get("ecosystem", "unknown")
            package_name = major_update.get("name", "unknown")

            priority = self.get_update_priority(
                package_name,
                "major",
                False,
            )

            batch = UpdateBatch(
                batch_id=f"major-{ecosystem}-{package_name}-{batch_counter}",
                update_type="major",
                ecosystem=ecosystem,
                packages=[package_name],
                risk_level="high",
                is_security_batch=False,
                priority=priority,
                notes=f"Major update for {package_name} ({major_update.get('current_version')} → "
                f"{major_update.get('latest_version')}). High risk - likely contains breaking changes. "
                f"Review release notes and test in separate branch.",
            )
            batches.append(batch)

        # Create batches for unknown update types (conservative default)
        for ecosystem, unknown_list in unknown_updates_by_ecosystem.items():
            batch_counter += 1

            avg_priority = sum(
                self.get_update_priority(
                    u.get("name", ""),
                    u.get("update_type", ""),
                    False,
                )
                for u in unknown_list
            ) // max(len(unknown_list), 1)

            batch = UpdateBatch(
                batch_id=f"unknown-{ecosystem}-{batch_counter}",
                update_type="unknown",
                ecosystem=ecosystem,
                packages=[u.get("name", "") for u in unknown_list],
                risk_level="medium",
                is_security_batch=False,
                priority=avg_priority,
                notes=f"Updates with non-semver versions for {len(unknown_list)} "
                f"{ecosystem} package(s). Review changelog before applying.",
            )
            batches.append(batch)

        # Sort batches by priority (highest first)
        batches.sort(key=lambda b: b.priority, reverse=True)

        return batches

    def get_update_priority(
        self,
        package_name: str,
        update_type: str,
        is_security: bool,
        severity: str | None = None,
    ) -> int:
        """
        Calculate priority score for a dependency update.

        Priority factors:
        - Security updates (highest priority)
        - CVE severity
        - Update type (patch > minor > major)
        - Known issues with current version

        Args:
            package_name: Name of the package
            update_type: Type of update (major, minor, patch)
            is_security: Whether this is a security update
            severity: CVE severity if applicable

        Returns:
            Priority score (0-100, higher = more urgent)
        """
        priority = 0

        # Security updates get highest priority
        if is_security:
            priority += 50
            # Add severity bonus
            if severity == "critical":
                priority += 30
            elif severity == "high":
                priority += 20
            elif severity == "medium":
                priority += 10

        # Update type priority (patch > minor > major)
        if update_type == "patch":
            priority += 15
        elif update_type == "minor":
            priority += 10
        elif update_type == "major":
            priority += 5

        return min(priority, 100)  # Cap at 100

    def _classify_update_type(self, current: str, latest: str) -> str:
        """
        Classify update type based on semantic versioning.

        Args:
            current: Current version string
            latest: Latest version string

        Returns:
            Update type: "major", "minor", "patch", or "unknown"
        """
        try:
            # Remove 'v' prefix if present
            current = current.lstrip("v")
            latest = latest.lstrip("v")

            # Parse version numbers
            current_parts = [int(x) for x in current.split(".")[:3]]
            latest_parts = [int(x) for x in latest.split(".")[:3]]

            # Pad to 3 parts if needed
            while len(current_parts) < 3:
                current_parts.append(0)
            while len(latest_parts) < 3:
                latest_parts.append(0)

            # Compare versions
            if latest_parts[0] > current_parts[0]:
                return "major"
            elif latest_parts[1] > current_parts[1]:
                return "minor"
            elif latest_parts[2] > current_parts[2]:
                return "patch"
            else:
                return "unknown"
        except (ValueError, IndexError):
            # If version parsing fails, default to unknown
            return "unknown"

    def get_analysis_summary(self) -> dict[str, Any]:
        """
        Get a summary of the dependency analysis.

        Returns:
            Dictionary with analysis summary
        """
        return {
            "analyzer": "DependencyAnalyzer",
            "project_path": str(self.path),
            "analysis": self.analysis,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def analyze_dependency_update(
    project_path: Path,
    package_name: str,
    current_version: str,
    target_version: str,
    ecosystem: str,
) -> DependencyRiskAssessment:
    """
    Convenience function to analyze a single dependency update.

    Args:
        project_path: Path to the project directory
        package_name: Name of the package
        current_version: Current version
        target_version: Target version to update to
        ecosystem: Package ecosystem (python, npm, etc.)

    Returns:
        DependencyRiskAssessment with risk analysis
    """
    analyzer = DependencyAnalyzer(project_path)
    return analyzer.analyze_update_risk(
        package_name, current_version, target_version, ecosystem
    )


def batch_dependency_updates(
    project_path: Path, updates: list[dict[str, Any]]
) -> list[UpdateBatch]:
    """
    Convenience function to batch dependency updates.

    Args:
        project_path: Path to the project directory
        updates: List of update dictionaries (from DependencyScanner)

    Returns:
        List of UpdateBatch objects
    """
    analyzer = DependencyAnalyzer(project_path)
    return analyzer.batch_updates(updates)
