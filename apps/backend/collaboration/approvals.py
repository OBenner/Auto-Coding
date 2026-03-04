#!/usr/bin/env python3
"""
Approval Workflow Management
=============================

Manages approval workflows for multi-user spec collaboration.

Key features:
- Request approval before builds start
- Approve/reject specs with reasons
- Track approval history and decisions
- Admin-only approval operations
- Permission-based access control
- Graphiti storage integration

Usage:
    manager = ApprovalManager(
        spec_id="001-feature",
        spec_dir=Path(".auto-claude/specs/001-feature"),
        project_dir=Path("."),
        permission_checker=checker
    )

    # Request approval
    approval = await manager.request_approval(
        requester_id="alice",
        requester_username="Alice"
    )

    # Approve the spec (admin only)
    await manager.approve_spec(
        approver_id="bob",
        approver_username="Bob",
        reason="Implementation looks solid"
    )

    # Check if spec is approved
    if manager.is_approved():
        # Build can proceed
        pass
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from integrations.graphiti.queries_pkg.schema import EPISODE_TYPE_APPROVAL

from .base import CollaborationManagerBase
from .models import Approval, ApprovalStatus, CollaborationUser, PermissionLevel
from .permissions import PermissionChecker

logger = logging.getLogger(__name__)


class ApprovalError(Exception):
    """Raised when approval operations fail."""

    pass


class ApprovalManager(CollaborationManagerBase):
    """
    Manages approval workflows for spec collaboration.

    Provides approval operations with permission checks and Graphiti storage.

    Features:
    - Request approval before builds
    - Approve/reject specs (admin only)
    - Track approval history
    - Get current approval status
    - Permission-based access control
    - Persistent storage via Graphiti

    Usage:
        manager = ApprovalManager(
            spec_id="001-feature",
            spec_dir=Path(".auto-claude/specs/001-feature"),
            project_dir=Path("."),
            permission_checker=checker
        )

        # Request approval (requires WRITE permission)
        approval = await manager.request_approval(
            requester_id="alice",
            requester_username="Alice"
        )

        # Approve spec (requires ADMIN permission)
        await manager.approve_spec(
            approver_id="bob",
            approver_username="Bob",
            reason="Looks good!"
        )

        # Check if approved
        if manager.is_approved():
            # Build can start
            pass
    """

    _manager_name = "approval"

    def __init__(
        self,
        spec_id: str,
        spec_dir: Path,
        project_dir: Path,
        permission_checker: PermissionChecker | None = None,
    ):
        """
        Initialize approval manager for a spec.

        Args:
            spec_id: Spec identifier (e.g., "001-feature-name")
            spec_dir: Path to spec directory (for Graphiti storage)
            project_dir: Project root directory
            permission_checker: Optional permission checker (for access control)
        """
        super().__init__(spec_id, spec_dir, project_dir, permission_checker)

        # In-memory approval cache: approval_id -> Approval
        self._approvals: dict[str, Approval] = {}

        # Current active approval request (only one can be active)
        self._current_approval_id: str | None = None

        logger.info(f"Initialized approval manager for spec {spec_id}")

    async def request_approval(
        self,
        requester_id: str,
        requester_username: str,
        email: str | None = None,
    ) -> Approval:
        """
        Request approval for the spec.

        Creates a pending approval that must be approved/rejected
        by an admin before builds can start.

        Args:
            requester_id: User requesting approval
            requester_username: Display name
            email: Optional user email

        Returns:
            Created Approval object with PENDING status

        Raises:
            ApprovalError: If permission denied or request fails
        """
        # Check write permission
        self._require_permission(requester_id, PermissionLevel.WRITE, ApprovalError)

        # Check if there's already a pending approval
        if self._current_approval_id:
            current = self._approvals.get(self._current_approval_id)
            if current and current.is_pending():
                raise ApprovalError(
                    f"Approval already pending (ID: {self._current_approval_id})"
                )

        # Create approval request (approver is None until a decision is made)
        approval = Approval(
            approval_id=str(uuid.uuid4()),
            spec_id=self.spec_id,
            requester=CollaborationUser(
                user_id=requester_id, username=requester_username, email=email
            ),
            status=ApprovalStatus.PENDING,
            approver=None,
        )

        # Store in cache
        self._approvals[approval.approval_id] = approval
        self._current_approval_id = approval.approval_id

        logger.info(
            f"Created approval request {approval.approval_id} "
            f"by requester {requester_id} for spec {self.spec_id}"
        )
        logger.debug(f"Approval requester username: {requester_username}")

        # Persist to Graphiti
        if self._memory_available:
            await self._store_approval_in_graphiti(approval, action="requested")

        return approval

    async def approve_spec(
        self,
        approver_id: str,
        approver_username: str,
        reason: str | None = None,
        email: str | None = None,
    ) -> Approval:
        """
        Approve the spec (admin only).

        Marks the current pending approval as approved, allowing builds to proceed.

        Args:
            approver_id: User approving the spec
            approver_username: Display name
            reason: Optional reason for approval
            email: Optional user email

        Returns:
            Approved Approval object

        Raises:
            ApprovalError: If no pending approval, permission denied, or operation fails
        """
        # Check admin permission
        self._require_permission(approver_id, PermissionLevel.ADMIN, ApprovalError)

        # Check if there's a pending approval
        if not self._current_approval_id:
            raise ApprovalError("No approval request to approve")

        approval = self._approvals.get(self._current_approval_id)
        if not approval:
            raise ApprovalError(f"Approval {self._current_approval_id} not found")

        if not approval.is_pending():
            raise ApprovalError(f"Approval already {approval.status.value}")

        # Update approval
        approval.approver = CollaborationUser(
            user_id=approver_id, username=approver_username, email=email
        )
        approval.approve(reason)

        logger.info(
            f"Spec {self.spec_id} approved by user {approver_id}: "
            f"{reason or 'No reason provided'}"
        )
        logger.debug(f"Approver username: {approver_username}")

        # Persist to Graphiti
        if self._memory_available:
            await self._store_approval_in_graphiti(approval, action="approved")

        return approval

    async def reject_spec(
        self,
        rejector_id: str,
        rejector_username: str,
        reason: str | None = None,
        email: str | None = None,
    ) -> Approval:
        """
        Reject the spec (admin only).

        Marks the current pending approval as rejected, blocking builds.

        Args:
            rejector_id: User rejecting the spec
            rejector_username: Display name
            reason: Optional reason for rejection
            email: Optional user email

        Returns:
            Rejected Approval object

        Raises:
            ApprovalError: If no pending approval, permission denied, or operation fails
        """
        # Check admin permission
        self._require_permission(rejector_id, PermissionLevel.ADMIN, ApprovalError)

        # Check if there's a pending approval
        if not self._current_approval_id:
            raise ApprovalError("No approval request to reject")

        approval = self._approvals.get(self._current_approval_id)
        if not approval:
            raise ApprovalError(f"Approval {self._current_approval_id} not found")

        if not approval.is_pending():
            raise ApprovalError(f"Approval already {approval.status.value}")

        # Update approval
        approval.approver = CollaborationUser(
            user_id=rejector_id, username=rejector_username, email=email
        )
        approval.reject(reason)

        logger.info(
            f"Spec {self.spec_id} rejected by user {rejector_id}: "
            f"{reason or 'No reason provided'}"
        )
        logger.debug(f"Rejector username: {rejector_username}")

        # Persist to Graphiti
        if self._memory_available:
            await self._store_approval_in_graphiti(approval, action="rejected")

        return approval

    def get_current_approval(self) -> Approval | None:
        """
        Get the current active approval.

        Returns:
            Current Approval object if exists, None otherwise
        """
        if not self._current_approval_id:
            return None

        return self._approvals.get(self._current_approval_id)

    def get_approval_status(self) -> ApprovalStatus | None:
        """
        Get the current approval status.

        Returns:
            ApprovalStatus if there's an approval, None if no approval exists
        """
        approval = self.get_current_approval()
        return approval.status if approval else None

    def is_pending(self) -> bool:
        """
        Check if there's a pending approval.

        Returns:
            True if approval is pending review
        """
        approval = self.get_current_approval()
        return approval.is_pending() if approval else False

    def is_approved(self) -> bool:
        """
        Check if the spec is approved.

        Returns:
            True if spec is approved and builds can proceed
        """
        approval = self.get_current_approval()
        return approval.is_approved() if approval else False

    def is_rejected(self) -> bool:
        """
        Check if the spec is rejected.

        Returns:
            True if spec is rejected and needs revision
        """
        approval = self.get_current_approval()
        return approval.is_rejected() if approval else False

    def can_build(self) -> bool:
        """
        Check if builds can proceed.

        Builds can proceed if:
        - No approval workflow is active (default allow), OR
        - Spec is explicitly approved

        Returns:
            True if builds are allowed
        """
        approval = self.get_current_approval()

        # No approval workflow = builds allowed by default
        if not approval:
            return True

        # Otherwise, must be explicitly approved
        return approval.is_approved()

    def get_approval_history(self) -> list[Approval]:
        """
        Get all approval records for this spec (sorted by creation time).

        Returns:
            List of all Approval objects, newest first
        """
        approvals = list(self._approvals.values())
        # Sort by created_at timestamp (newest first)
        approvals.sort(key=lambda a: a.created_at, reverse=True)
        return approvals

    def get_approval_count(self) -> dict[str, int]:
        """
        Get count of approvals by status.

        Returns:
            Dict with counts: {"pending": N, "approved": N, "rejected": N}
        """
        counts = {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
        }

        for approval in self._approvals.values():
            counts[approval.status.value] += 1

        return counts

    async def _store_approval_in_graphiti(
        self, approval: Approval, action: str
    ) -> bool:
        """
        Store an approval in Graphiti as an episode.

        Args:
            approval: Approval to store
            action: Action performed (e.g., "requested", "approved", "rejected")

        Returns:
            True if stored successfully
        """
        actor = approval.approver or approval.requester
        return await self._store_episode_in_graphiti(
            episode_name=f"approval_{approval.approval_id}_{action}",
            episode_content={
                "type": EPISODE_TYPE_APPROVAL,
                "spec_id": self.spec_id,
                "approval_id": approval.approval_id,
                "requester_id": approval.requester.user_id,
                "approver_id": approval.approver.user_id if approval.approver else None,
                "status": approval.status.value,
                "reason": approval.reason,
                "action": action,
                "created_at": approval.created_at,
                "reviewed_at": approval.reviewed_at,
            },
            source_description=(
                f"Approval {action} for spec {self.spec_id} by user {actor.user_id}"
            ),
            operation_name="store_approval_in_graphiti",
            approval_id=approval.approval_id,
            action=action,
        )
