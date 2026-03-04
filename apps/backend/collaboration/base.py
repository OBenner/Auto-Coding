#!/usr/bin/env python3
"""
Collaboration Manager Base Class
==================================

Shared base for ApprovalManager, CommentManager, and NotificationManager.

Provides:
- Common initialization (spec_id, spec_dir, project_dir, Graphiti memory)
- Graphiti memory setup via initialize()
- Graphiti episode storage helper
- Permission check helper

This eliminates duplication across the three collaboration managers.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.sentry import capture_exception
from integrations.graphiti.memory import GraphitiMemory, get_graphiti_memory

from .models import PermissionLevel
from .permissions import PermissionChecker

logger = logging.getLogger(__name__)


class CollaborationManagerBase:
    """
    Base class for collaboration managers.

    Provides shared Graphiti memory initialization, episode storage,
    and permission checking logic.
    """

    # Subclasses should set this for log messages (e.g., "approval", "comment")
    _manager_name: str = "collaboration"

    def __init__(
        self,
        spec_id: str,
        spec_dir: Path,
        project_dir: Path,
        permission_checker: PermissionChecker | None = None,
    ):
        """
        Initialize base collaboration manager.

        Args:
            spec_id: Spec identifier (e.g., "001-feature-name")
            spec_dir: Path to spec directory (for Graphiti storage)
            project_dir: Project root directory
            permission_checker: Optional permission checker (for access control)
        """
        self.spec_id = spec_id
        self.spec_dir = spec_dir
        self.project_dir = project_dir
        self.permission_checker = permission_checker

        # Graphiti memory for persistent storage
        self._memory: GraphitiMemory | None = None
        self._memory_available = False

    async def initialize(self) -> bool:
        """
        Initialize Graphiti memory for persistent storage.

        Returns:
            True if initialization succeeded (or Graphiti not enabled)
        """
        try:
            self._memory = get_graphiti_memory(
                spec_dir=self.spec_dir,
                project_dir=self.project_dir,
            )

            if self._memory.is_enabled:
                self._memory_available = await self._memory.initialize()

                if self._memory_available:
                    logger.info(
                        f"{self._manager_name.capitalize()} manager initialized "
                        f"with Graphiti storage (group: {self._memory.group_id})"
                    )
                else:
                    logger.warning(
                        f"Graphiti initialization failed - "
                        f"{self._manager_name}s will not persist"
                    )
            else:
                logger.info(
                    f"Graphiti not enabled - {self._manager_name}s will not persist"
                )

            return (not self._memory.is_enabled) or self._memory_available

        except Exception as e:
            logger.warning(f"Failed to initialize Graphiti memory: {e}")
            capture_exception(
                e,
                operation=f"{self._manager_name}_manager_initialize",
                spec_id=self.spec_id,
            )
            self._memory_available = False
            return False

    def _require_permission(
        self,
        user_id: str,
        required_level: PermissionLevel,
        error_class: type[Exception],
    ) -> None:
        """
        Check permission and raise if denied.

        Args:
            user_id: User to check
            required_level: Minimum required permission level
            error_class: Exception class to raise on denial

        Raises:
            error_class: If permission check fails
        """
        if not self.permission_checker:
            return

        result = self.permission_checker.check_permission(user_id, required_level)
        if not result.allowed:
            raise error_class(
                f"Permission denied: {result.reason or f'no {required_level.value} access'}"
            )

    async def _store_episode_in_graphiti(
        self,
        episode_name: str,
        episode_content: dict[str, Any],
        source_description: str,
        operation_name: str,
        **extra_capture_kwargs: Any,
    ) -> bool:
        """
        Store an episode in Graphiti.

        Args:
            episode_name: Unique episode name
            episode_content: Content dict to store as JSON
            source_description: Human-readable description
            operation_name: Operation name for error tracking
            **extra_capture_kwargs: Extra kwargs for capture_exception

        Returns:
            True if stored successfully
        """
        if not self._memory or not self._memory_available:
            return False

        try:
            from graphiti_core.nodes import EpisodeType

            await self._memory.client.graphiti.add_episode(
                name=episode_name,
                episode_body=json.dumps(episode_content),
                source=EpisodeType.text,
                source_description=source_description,
                reference_time=datetime.now(UTC),
                group_id=self._memory.group_id,
            )

            logger.debug(f"Stored episode '{episode_name}' in Graphiti")
            return True

        except Exception as e:
            logger.warning(f"Failed to store in Graphiti ({operation_name}): {e}")
            capture_exception(
                e,
                operation=operation_name,
                spec_id=self.spec_id,
                **extra_capture_kwargs,
            )
            return False
