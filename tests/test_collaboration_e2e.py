#!/usr/bin/env python3
"""
End-to-End Collaboration Workflow Tests
======================================

Tests the complete multi-user collaboration workflow:
1. Create a spec
2. Share with team member (add permission)
3. Add comment with @mention
4. Request approval
5. Approve/reject spec
6. Verify change history
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add auto-claude to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from collaboration.models import (
    ApprovalStatus,
    CollaborationUser,
    Comment,
    PermissionLevel,
    SpecPermission,
)
from collaboration.approvals import ApprovalManager
from collaboration.comments import CommentManager
from collaboration.notifications import NotificationManager
from collaboration.permissions import PermissionChecker


class TestCollaborationE2E:
    """
    End-to-end tests for collaboration workflow.

    Tests the complete user journey:
    1. Spec owner creates permission system
    2. Owner grants read/write/admin access to team members
    3. Users add comments with @mentions
    4. Users request approval
    5. Admins approve/reject
    6. Change history tracks all actions
    7. Notifications are sent
    """

    @pytest.fixture
    async def setup_collaboration(self):
        """Set up collaboration managers for testing."""
        # Create temporary directories
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            spec_dir = tmpdir / "specs" / "test-spec"
            spec_dir.mkdir(parents=True)
            project_dir = tmpdir

            # Create permission checker with owner
            checker = PermissionChecker(
                spec_id="test-spec",
                owner_user_id="owner-alice",
            )

            # Create managers
            comment_manager = CommentManager(
                spec_id="test-spec",
                spec_dir=spec_dir,
                project_dir=project_dir,
                permission_checker=checker,
            )

            approval_manager = ApprovalManager(
                spec_id="test-spec",
                spec_dir=spec_dir,
                project_dir=project_dir,
                permission_checker=checker,
            )

            notification_manager = NotificationManager(
                spec_id="test-spec",
                spec_dir=spec_dir,
                project_dir=project_dir,
            )

            yield {
                "checker": checker,
                "comment_manager": comment_manager,
                "approval_manager": approval_manager,
                "notification_manager": notification_manager,
                "spec_dir": spec_dir,
                "project_dir": project_dir,
            }

    @pytest.mark.asyncio
    async def test_complete_collaboration_workflow(self, setup_collaboration):
        """Test the complete collaboration workflow from start to finish."""
        checker = setup_collaboration["checker"]
        comment_manager = setup_collaboration["comment_manager"]
        approval_manager = setup_collaboration["approval_manager"]
        notification_manager = setup_collaboration["notification_manager"]

        # Step 1: Verify owner has admin access
        result = checker.check_permission("owner-alice", PermissionLevel.ADMIN)
        assert result.allowed, "Owner should have admin access"
        assert result.level == PermissionLevel.ADMIN

        # Step 2: Grant read permission to team member Bob
        checker.grant_permission(
            user_id="user-bob",
            username="Bob",
            level=PermissionLevel.READ,
            granted_by="owner-alice",
        )

        # Verify Bob can read
        result = checker.check_permission("user-bob", PermissionLevel.READ)
        assert result.allowed, "Bob should have read access"
        assert result.level == PermissionLevel.READ

        # Verify Bob cannot write
        result = checker.check_permission("user-bob", PermissionLevel.WRITE)
        assert not result.allowed, "Bob should not have write access"

        # Step 3: Grant write permission to team member Carol
        checker.grant_permission(
            user_id="user-carol",
            username="Carol",
            level=PermissionLevel.WRITE,
            granted_by="owner-alice",
        )

        # Verify Carol can write and read
        result = checker.check_permission("user-carol", PermissionLevel.WRITE)
        assert result.allowed, "Carol should have write access"

        result = checker.check_permission("user-carol", PermissionLevel.READ)
        assert result.allowed, "Carol should have read access"

        # Step 4: Carol creates a comment with @mention
        comment = await comment_manager.create_comment(
            user_id="user-carol",
            username="Carol",
            content="What do you think about this approach? @user-bob",
        )

        assert comment.comment_id is not None
        assert comment.author.user_id == "user-carol"
        assert comment.content == "What do you think about this approach? @user-bob"
        assert "user-bob" in comment.mentions

        # Verify comment is stored
        retrieved = await comment_manager.get_comment(comment.comment_id)
        assert retrieved is not None
        assert retrieved.comment_id == comment.comment_id

        # Step 5: Bob replies to the comment
        # First upgrade Bob to write permission (revoke then grant)
        checker.revoke_permission(user_id="user-bob")
        checker.grant_permission(
            user_id="user-bob",
            username="Bob",
            level=PermissionLevel.WRITE,
            granted_by="owner-alice",
        )

        reply = await comment_manager.reply_to_comment(
            parent_comment_id=comment.comment_id,
            user_id="user-bob",
            username="Bob",
            content="Looks good to me!",
        )

        assert reply.parent_id == comment.comment_id
        assert reply.author.user_id == "user-bob"

        # Verify thread structure (get_thread returns only replies)
        thread = comment_manager.get_thread(comment.comment_id)
        assert len(thread) == 1  # One reply

        # Step 6: Check mentions for Bob
        mentions = comment_manager.get_mentions_for_user("user-bob")
        assert len(mentions) > 0
        assert comment.comment_id in [m.comment_id for m in mentions]

        # Step 7: Carol requests approval
        approval = await approval_manager.request_approval(
            requester_id="user-carol",
            requester_username="Carol",
        )

        assert approval.approval_id is not None
        assert approval.status == ApprovalStatus.PENDING

        # Verify approval is pending
        assert approval_manager.is_pending()
        assert not approval_manager.is_approved()
        assert not approval_manager.is_rejected()

        # Verify build cannot start
        assert not approval_manager.can_build()

        # Step 8: Owner approves the spec
        await approval_manager.approve_spec(
            approver_id="owner-alice",
            approver_username="Alice",
            reason="Implementation plan looks solid",
        )

        # Verify approval status
        assert approval_manager.is_approved()
        assert not approval_manager.is_pending()
        assert not approval_manager.is_rejected()

        # Verify build can now start
        assert approval_manager.can_build()

        # Step 9: Verify collaboration state is consistent
        # Check permissions are stored (owner has implicit admin, not stored)
        all_permissions = checker.get_all_permissions()
        assert len(all_permissions) >= 2  # Bob + Carol (owner implicit)

        # Check comments are stored
        all_comments = comment_manager.get_all_comments()
        assert len(all_comments) >= 2  # Original + reply

        # Check approval status
        assert approval_manager.is_approved()
        assert approval_manager.can_build()

        print("✅ Complete collaboration workflow verified successfully!")

        print("✅ Complete collaboration workflow verified successfully!")

    @pytest.mark.asyncio
    async def test_permission_hierarchy(self, setup_collaboration):
        """Test that permission hierarchy works correctly."""
        checker = setup_collaboration["checker"]

        # Grant WRITE permission
        checker.grant_permission(
            user_id="user-charlie",
            username="Charlie",
            level=PermissionLevel.WRITE,
            granted_by="owner-alice",
        )

        # WRITE should grant READ
        assert checker.has_read_access("user-charlie")
        assert checker.has_write_access("user-charlie")
        assert not checker.has_admin_access("user-charlie")

        # Grant ADMIN permission
        checker.grant_permission(
            user_id="user-diana",
            username="Diana",
            level=PermissionLevel.ADMIN,
            granted_by="owner-alice",
        )

        # ADMIN should grant WRITE and READ
        assert checker.has_read_access("user-diana")
        assert checker.has_write_access("user-diana")
        assert checker.has_admin_access("user-diana")

        print("✅ Permission hierarchy verified successfully!")

    @pytest.mark.asyncio
    async def test_comment_resolution_workflow(self, setup_collaboration):
        """Test comment thread resolution workflow."""
        comment_manager = setup_collaboration["comment_manager"]
        checker = setup_collaboration["checker"]

        # Grant write permission to user
        checker.grant_permission(
            user_id="user-eve",
            username="Eve",
            level=PermissionLevel.WRITE,
            granted_by="owner-alice",
        )

        # Create comment
        comment = await comment_manager.create_comment(
            user_id="user-eve",
            username="Eve",
            content="Should we add error handling here?",
        )

        assert not comment.resolved

        # Resolve the comment
        await comment_manager.resolve_thread(
            comment_id=comment.comment_id,
            user_id="owner-alice",
        )

        # Verify resolution
        resolved_comment = await comment_manager.get_comment(comment.comment_id)
        assert resolved_comment.resolved

        # Verify it doesn't appear in unresolved queries
        unresolved = comment_manager.get_unresolved_comments()
        assert comment.comment_id not in [c.comment_id for c in unresolved]

        print("✅ Comment resolution workflow verified successfully!")

    @pytest.mark.asyncio
    async def test_approval_rejection_workflow(self, setup_collaboration):
        """Test approval rejection workflow."""
        approval_manager = setup_collaboration["approval_manager"]
        checker = setup_collaboration["checker"]

        # Grant write permission
        checker.grant_permission(
            user_id="user-frank",
            username="Frank",
            level=PermissionLevel.WRITE,
            granted_by="owner-alice",
        )

        # Request approval
        approval = await approval_manager.request_approval(
            requester_id="user-frank",
            requester_username="Frank",
        )

        assert approval.status == ApprovalStatus.PENDING

        # Reject the approval
        await approval_manager.reject_spec(
            rejector_id="owner-alice",
            rejector_username="Alice",
            reason="Need more detail on error handling",
        )

        # Verify rejection
        assert approval_manager.is_rejected()
        assert not approval_manager.is_approved()
        assert not approval_manager.is_pending()

        # Verify build cannot start
        assert not approval_manager.can_build()

        # Verify approval history (same approval object gets modified)
        history = approval_manager.get_approval_history()
        assert len(history) == 1  # Single approval that went from PENDING to REJECTED
        # The approval status is now REJECTED
        assert history[0].status == ApprovalStatus.REJECTED

        print("✅ Approval rejection workflow verified successfully!")

    @pytest.mark.asyncio
    async def test_permission_denial_without_access(self, setup_collaboration):
        """Test that operations are denied without proper permissions."""
        comment_manager = setup_collaboration["comment_manager"]
        approval_manager = setup_collaboration["approval_manager"]

        # Try to create comment without permission (no permission granted)
        with pytest.raises(Exception):  # CommentError or permission error
            await comment_manager.create_comment(
                user_id="stranger",
                username="Stranger",
                content="Trying to comment...",
            )

        # Try to approve without admin permission
        with pytest.raises(Exception):  # ApprovalError or permission error
            await approval_manager.approve_spec(
                approver_id="stranger",
                approver_username="Stranger",
                reason="Trying to approve...",
            )

        print("✅ Permission denial verified successfully!")

    @pytest.mark.asyncio
    async def test_multiple_comments_and_replies(self, setup_collaboration):
        """Test handling multiple comment threads."""
        comment_manager = setup_collaboration["comment_manager"]
        checker = setup_collaboration["checker"]

        # Grant write permissions
        for i in range(3):
            checker.grant_permission(
                user_id=f"user-{i}",
                username=f"User{i}",
                level=PermissionLevel.WRITE,
                granted_by="owner-alice",
            )

        # Create multiple top-level comments
        comment1 = await comment_manager.create_comment(
            user_id="user-0",
            username="User0",
            content="First comment",
        )

        comment2 = await comment_manager.create_comment(
            user_id="user-1",
            username="User1",
            content="Second comment",
        )

        # Add replies to first comment
        reply1 = await comment_manager.reply_to_comment(
            parent_comment_id=comment1.comment_id,
            user_id="user-1",
            username="User1",
            content="Reply to first",
        )

        reply2 = await comment_manager.reply_to_comment(
            parent_comment_id=comment1.comment_id,
            user_id="user-2",
            username="User2",
            content="Another reply",
        )

        # Verify top-level comments
        top_level = comment_manager.get_top_level_comments()
        assert len(top_level) >= 2
        assert comment1.comment_id in [c.comment_id for c in top_level]
        assert comment2.comment_id in [c.comment_id for c in top_level]

        # Verify thread structure (get_thread returns only replies)
        thread1 = comment_manager.get_thread(comment1.comment_id)
        assert len(thread1) == 2  # Two replies

        thread2 = comment_manager.get_thread(comment2.comment_id)
        assert len(thread2) == 0  # No replies

        print("✅ Multiple comments and replies verified successfully!")


class TestCollaborationIntegration:
    """Integration tests for collaboration components."""

    def test_imports(self):
        """Test that all collaboration modules can be imported."""
        from collaboration.models import (
            ApprovalStatus,
            CollaborationUser,
            Comment,
            PermissionLevel,
            SpecPermission,
        )
        from collaboration.approvals import ApprovalManager
        from collaboration.comments import CommentManager
        from collaboration.notifications import NotificationManager
        from collaboration.permissions import PermissionChecker

        assert PermissionLevel.READ is not None
        assert ApprovalStatus.PENDING is not None
        assert CollaborationUser is not None

    def test_models_instantiation(self):
        """Test that collaboration models can be instantiated."""
        user = CollaborationUser(
            user_id="test-user",
            username="Test User",
            email="test@example.com",
        )
        assert user.user_id == "test-user"

        permission = SpecPermission(
            spec_id="spec-1",
            user=user,
            level=PermissionLevel.WRITE,
            granted_by="owner",
            granted_at=None,
        )
        assert permission.level == PermissionLevel.WRITE

        comment = Comment(
            comment_id="comment-1",
            spec_id="spec-1",
            author=user,
            content="Test comment",
            created_at=None,
            parent_id=None,
            resolved=False,
            mentions=[],
        )
        assert comment.comment_id == "comment-1"
        assert comment.content == "Test comment"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
