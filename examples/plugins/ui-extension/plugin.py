"""
UI Extension Example Plugin
============================

Example plugin demonstrating UI extension capabilities:
- Custom dashboard widget with project statistics
- IPC handlers for frontend-backend communication
- State management and data caching
- React component integration
"""

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from apps.backend.plugins.base import PluginMetadata
from apps.backend.plugins.sdk.ui import (
    UIComponentDefinition,
    UIContext,
    UIExtensionPoint,
    UIPlugin,
)

logger = logging.getLogger(__name__)


class ProjectStatsPlugin(UIPlugin):
    """
    UI plugin that provides a dashboard widget showing project statistics.

    Features:
    - Shows spec count (total, completed, pending, in-progress)
    - Displays last build timestamp
    - Calculates success rate
    - Caches data for performance
    - Provides real-time updates via IPC
    """

    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.stats_cache = {}
        self.last_update = None

    def on_load(self):
        """Called when plugin is loaded."""
        logger.info(f"{self.name}: Plugin loaded")

    def on_enable(self):
        """Called when plugin is enabled."""
        logger.info(f"{self.name}: Plugin enabled - dashboard widget will appear")

    def on_disable(self):
        """Called when plugin is disabled."""
        logger.info(f"{self.name}: Plugin disabled")
        self.stats_cache.clear()

    def on_unload(self):
        """Called when plugin is unloaded."""
        logger.info(f"{self.name}: Plugin unloaded")
        self.stats_cache.clear()

    def get_ui_components(self, context: UIContext) -> list[UIComponentDefinition]:
        """
        Register UI components for this plugin.

        Returns a dashboard widget that displays project statistics.
        """
        return [
            UIComponentDefinition(
                id="project-stats-widget",
                extension_point=UIExtensionPoint.DASHBOARD,
                title="Project Statistics",
                icon="chart-bar",
                component_path="ui-component.tsx",
                order=10,
                props={
                    "refreshInterval": 30000,  # Refresh every 30 seconds
                    "showCharts": True,
                },
            )
        ]

    def register_ipc_handlers(self, context: UIContext) -> dict[str, Callable]:
        """
        Register IPC handlers for frontend communication.

        Provides handlers for:
        - Getting project statistics
        - Refreshing cached data
        """

        def get_project_stats(event, project_dir: str):
            """
            Get project statistics for the dashboard widget.

            Args:
                event: IPC event
                project_dir: Path to project directory

            Returns:
                Dictionary with project statistics
            """
            try:
                stats = self._calculate_stats(Path(project_dir))
                return {
                    "success": True,
                    "data": stats,
                }
            except Exception as e:
                logger.error(f"Failed to get project stats: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                }

        def refresh_stats(event, project_dir: str):
            """
            Force refresh of cached statistics.

            Args:
                event: IPC event
                project_dir: Path to project directory

            Returns:
                Success status and refreshed data
            """
            try:
                # Clear cache to force recalculation
                cache_key = str(project_dir)
                if cache_key in self.stats_cache:
                    del self.stats_cache[cache_key]

                stats = self._calculate_stats(Path(project_dir))
                return {
                    "success": True,
                    "data": stats,
                    "message": "Statistics refreshed successfully",
                }
            except Exception as e:
                logger.error(f"Failed to refresh stats: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                }

        # Return IPC channel mappings
        return {
            f"{self.name}:get-stats": get_project_stats,
            f"{self.name}:refresh-stats": refresh_stats,
        }

    def _calculate_stats(self, project_dir: Path) -> dict[str, Any]:
        """
        Calculate project statistics by analyzing .auto-claude directory.

        Args:
            project_dir: Path to project directory

        Returns:
            Dictionary with statistics
        """
        cache_key = str(project_dir)

        # Return cached data if available and recent
        if cache_key in self.stats_cache:
            logger.debug(f"{self.name}: Returning cached stats")
            return self.stats_cache[cache_key]

        logger.info(f"{self.name}: Calculating project stats for {project_dir}")

        # Initialize stats
        stats = {
            "totalSpecs": 0,
            "completedSpecs": 0,
            "pendingSpecs": 0,
            "inProgressSpecs": 0,
            "failedSpecs": 0,
            "successRate": 0.0,
            "lastBuildTime": None,
            "averageBuildTime": None,
        }

        # Find specs directory
        specs_dir = project_dir / ".auto-claude" / "specs"
        if not specs_dir.exists():
            logger.warning(f"{self.name}: Specs directory not found at {specs_dir}")
            return stats

        # Analyze each spec
        for spec_path in specs_dir.iterdir():
            if not spec_path.is_dir():
                continue

            stats["totalSpecs"] += 1

            # Check implementation plan for status
            plan_file = spec_path / "implementation_plan.json"
            if plan_file.exists():
                try:
                    with open(plan_file, encoding="utf-8") as f:
                        plan = json.load(f)
                        status = plan.get("status", "pending")

                        if status == "completed":
                            stats["completedSpecs"] += 1
                        elif status == "in_progress":
                            stats["inProgressSpecs"] += 1
                        elif status == "failed":
                            stats["failedSpecs"] += 1
                        else:
                            stats["pendingSpecs"] += 1
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Failed to read plan for {spec_path.name}: {e}")
                    stats["pendingSpecs"] += 1
            else:
                stats["pendingSpecs"] += 1

        # Calculate success rate
        if stats["totalSpecs"] > 0:
            stats["successRate"] = round(
                (stats["completedSpecs"] / stats["totalSpecs"]) * 100, 1
            )

        # Cache the results
        self.stats_cache[cache_key] = stats

        return stats

    def on_frontend_ready(self, context: UIContext) -> None:
        """
        Called when frontend is ready.

        Pre-calculate stats for better initial load performance.
        """
        logger.info(f"{self.name}: Frontend ready, pre-calculating stats")
        try:
            self._calculate_stats(context.project_dir)
        except Exception as e:
            logger.error(f"Failed to pre-calculate stats: {e}", exc_info=True)

    def on_window_focus(self, context: UIContext, focused: bool) -> None:
        """
        Called when window gains/loses focus.

        Refresh stats when window regains focus to show latest data.
        """
        if focused:
            logger.debug(f"{self.name}: Window focused, clearing cache for fresh data")
            self.stats_cache.clear()
