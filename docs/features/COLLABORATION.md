# Multi-User Spec Collaboration

Auto Code's collaboration system enables team members to work together on specs with role-based access control, threaded discussions, approval workflows, and comprehensive change tracking.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Key Benefits](#key-benefits)
- [Quick Start](#quick-start)
- [Core Components](#core-components)
- [Permission System](#permission-system)
- [Comment Threads](#comment-threads)
- [Approval Workflow](#approval-workflow)
- [Change History](#change-history)
- [Integration](#integration)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)

## Overview

The collaboration system extends Auto Code from a single-developer tool to a team platform by enabling **multi-user spec collaboration** with enterprise-grade access control, communication, and approval workflows.

### What It Does

- **Role-based access control** - Share specs with team members (READ/WRITE/ADMIN permissions)
- **Threaded discussions** - Comment threads with @mentions and reply threading
- **Approval workflows** - Require spec approval before builds can proceed
- **Change tracking** - Complete audit trail of who modified what and when
- **Real-time updates** - Event channels for live collaboration updates
- **Notification system** - @mention notifications and workflow status updates

### Key Benefits

✅ **Team workflows** - Tech leads can review and approve specs before builds start
✅ **Knowledge sharing** - Developers can provide feedback through comments and discussions
✅ **Access control** - Granular permissions prevent unauthorized modifications
✅ **Accountability** - Change history shows exactly who changed what and when
✅ **Process enforcement** - Approval gates prevent premature builds
✅ **Communication** - @mentions notify team members of important discussions

## Architecture

The collaboration system uses a layered architecture with backend business logic, persistent storage via Graphiti, IPC communication, and React UI components.

```
┌────────────────────────────────────────────────────────────┐
│                  Frontend UI Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Permissions  │  │   Comments   │  │  Approvals   │    │
│  │    Panel     │  │   Thread     │  │  Workflow    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴────────┐
                    │  IPC Layer     │
                    │  (Electron)    │
                    └───────┬────────┘
                            │
┌────────────────────────────────────────────────────────────┐
│                  Backend Logic Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Permission │  │    Comment   │  │   Approval   │    │
│  │   Checker    │  │   Manager    │  │   Manager    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌──────────────┐                                          │
│  │ Notification │                                          │
│  │   Manager    │                                          │
│  └──────────────┘                                          │
└────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴────────┐
                    │  Storage Layer │
                    │   (Graphiti)   │
                    └────────────────┘
```

### Data Flow

1. **User Action** → Frontend component triggers IPC call
2. **IPC Handler** → Calls Python backend module via subprocess
3. **Backend Logic** → PermissionChecker validates access
4. **Business Operation** → Manager performs action (add comment, approve, etc.)
5. **Persistence** → Graphiti stores data in knowledge graph
6. **Notifications** → NotificationManager creates notifications
7. **Event Emission** → Real-time events sent to frontend
8. **UI Update** → Components refresh with new data

## Quick Start

### Enable Collaboration on a Spec

```typescript
// In TaskDetailView, navigate to Collaboration tab
// 1. Add team member with permissions
// 2. Start discussion with comments
// 3. Request approval when ready
// 4. Wait for admin approval
// 5. Build can proceed
```

### Basic Permission Management

```python
from apps.backend.collaboration.permissions import PermissionChecker, PermissionLevel

# Initialize permission checker
checker = PermissionChecker(
    spec_id="001-feature",
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path(".")
)

# Add team member with WRITE permission
await checker.add_permission(
    user_id="alice",
    username="Alice Johnson",
    level=PermissionLevel.WRITE
)

# Check if user can approve
can_approve = await checker.check_permission(
    user_id="alice",
    required_level=PermissionLevel.ADMIN
)
```

### Create Comment Thread

```python
from apps.backend.collaboration.comments import CommentManager

manager = CommentManager(
    spec_id="001-feature",
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("."),
    permission_checker=checker
)

# Create top-level comment with @mention
comment = await manager.create_comment(
    user_id="alice",
    username="Alice",
    content="This approach looks good! @bob what do you think?"
)

# Reply to comment
reply = await manager.reply_to_comment(
    parent_comment_id=comment.comment_id,
    user_id="bob",
    username="Bob",
    content="Agreed! Let's proceed."
)

# Resolve thread
await manager.resolve_thread(comment.comment_id, user_id="alice")
```

### Request Approval

```python
from apps.backend.collaboration.approvals import ApprovalManager

approval_manager = ApprovalManager(
    spec_id="001-feature",
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("."),
    permission_checker=checker
)

# Request approval
await approval_manager.request_approval(
    requester_id="alice",
    requester_name="Alice"
)

# Admin approves
await approval_manager.approve_spec(
    admin_id="admin",
    admin_name="Admin",
    reason="Design looks solid, ready to implement"
)

# Check if build can proceed
can_build = await approval_manager.can_build()
# Returns: True
```

## Core Components

### Backend Modules

| Module | Location | Purpose |
|--------|----------|---------|
| **Data Models** | `apps/backend/collaboration/models.py` | User, Permission, Comment, Approval, Notification data structures |
| **PermissionChecker** | `apps/backend/collaboration/permissions.py` | Role-based access control (READ/WRITE/ADMIN) |
| **CommentManager** | `apps/backend/collaboration/comments.py` | Threaded comment management with @mentions |
| **ApprovalManager** | `apps/backend/collaboration/approvals.py` | Approval workflow state machine |
| **NotificationManager** | `apps/backend/collaboration/notifications.py` | @mentions and change history tracking |

### Frontend Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **PermissionsPanel** | `apps/frontend/src/renderer/components/collaboration/PermissionsPanel.tsx` | UI for managing team access |
| **CommentThread** | `apps/frontend/src/renderer/components/collaboration/CommentThread.tsx` | Threaded discussion interface |
| **ApprovalWorkflow** | `apps/frontend/src/renderer/components/collaboration/ApprovalWorkflow.tsx` | Approval request and status UI |

### IPC Channels

| Channel | Purpose | Handler |
|---------|---------|---------|
| `collaboration:permissions:get` | Get spec permissions | `collaboration-handlers.ts` |
| `collaboration:permissions:add` | Add team member | `collaboration-handlers.ts` |
| `collaboration:permissions:update` | Update permission level | `collaboration-handlers.ts` |
| `collaboration:permissions:remove` | Remove team member | `collaboration-handlers.ts` |
| `collaboration:comments:get` | Get spec comments | `collaboration-handlers.ts` |
| `collaboration:comments:create` | Create comment | `collaboration-handlers.ts` |
| `collaboration:comments:reply` | Reply to comment | `collaboration-handlers.ts` |
| `collaboration:comments:resolve` | Resolve thread | `collaboration-handlers.ts` |
| `collaboration:approvals:get` | Get approval status | `collaboration-handlers.ts` |
| `collaboration:approvals:request` | Request approval | `collaboration-handlers.ts` |
| `collaboration:approvals:approve` | Approve spec | `collaboration-handlers.ts` |
| `collaboration:approvals:reject` | Reject spec | `collaboration-handlers.ts` |

## Permission System

### Permission Levels

```python
class PermissionLevel(Enum):
    READ = "read"       # View spec, comments, approvals
    WRITE = "write"     # All READ permissions + add comments, request approval
    ADMIN = "admin"     # All WRITE permissions + approve/reject, manage permissions
```

### Permission Hierarchy

```
ADMIN (highest)
  ├─ Approve/reject specs
  ├─ Add/remove/update permissions
  ├─ All WRITE permissions
  └─ All READ permissions

WRITE
  ├─ Add comments
  ├─ Reply to comments
  ├─ Request approval
  ├─ Resolve own comments
  └─ All READ permissions

READ (lowest)
  ├─ View spec
  ├─ View comments
  ├─ View approval status
  └─ View change history
```

### Access Control Examples

```python
# Only admins can approve
if not await checker.check_permission(user_id, PermissionLevel.ADMIN):
    raise PermissionError("Only admins can approve specs")

# Write permission required for comments
if not await checker.check_permission(user_id, PermissionLevel.WRITE):
    raise PermissionError("Write permission required to add comments")

# Owner automatically has all permissions
# Owner is defined as the user who created the spec
is_owner = await checker.is_owner(user_id)
```

## Comment Threads

### Thread Structure

Comments support threaded replies with unlimited nesting:

```
┌─ Top-level comment by Alice
│  "This approach looks good!"
│  └─ Reply by Bob
│     "I agree, let's proceed"
│     └─ Reply by Alice
│        "Great, I'll start implementation"
│
└─ Top-level comment by Charlie
   "Have we considered error handling?"
   └─ Reply by Bob
      "Good point, added to requirements"
```

### @Mentions

Automatic @mention extraction and notification:

```python
# Mentions are automatically extracted from content
comment = await manager.create_comment(
    user_id="alice",
    username="Alice",
    content="@bob @charlie Please review this approach"
# Extracted mentions: ["bob", "charlie"]
)

# NotificationManager sends notifications to mentioned users
```

### Comment Resolution

Threads can be resolved when consensus is reached:

```python
# Resolve a thread (marks it as complete)
await manager.resolve_thread(
    comment_id="comment-123",
    user_id="alice",  # Only author or admin can resolve
    resolved_reason="Implemented suggested changes"
)
```

## Approval Workflow

### Approval States

```python
class ApprovalStatus(Enum):
    NONE = "none"           # No approval requested
    PENDING = "pending"     # Approval requested, awaiting review
    APPROVED = "approved"   # Spec approved, builds can proceed
    REJECTED = "rejected"   # Spec rejected, fixes needed
```

### Approval Flow

```
┌─────────────┐
│   NONE      │  Initial state - no approval workflow started
└──────┬──────┘
       │ request_approval()
       ▼
┌─────────────┐
│  PENDING    │  Approval requested, waiting for admin review
└──────┬──────┘
       │
       ├─────────────┐
       │             │
       ▼             ▼
┌─────────────┐  ┌─────────────┐
│  APPROVED   │  │  REJECTED   │
│             │  │  + reason   │
└─────────────┘  └─────────────┘
       │
       │ rejected → Request approval again
       │
       ▼
┌─────────────┐
│  PENDING    │  Back to pending state
└─────────────┘
```

### Build Gate

```python
# Check if builds are allowed
can_build = await approval_manager.can_build()

# Returns False if:
# - No approval status (NONE)
# - Approval pending (PENDING)
# - Approval rejected (REJECTED)

# Returns True only if:
# - Status is APPROVED
# - Or no approval required (spec owner working alone)
```

### Approval History

Complete audit trail of all approval decisions:

```python
history = await approval_manager.get_approval_history()
# Returns:
# [
#   {
#     "status": "PENDING",
#     "timestamp": "2026-02-13T18:00:00Z",
#     "requester": "alice",
#     "requester_name": "Alice Johnson"
#   },
#   {
#     "status": "APPROVED",
#     "timestamp": "2026-02-13T18:30:00Z",
#     "admin": "admin",
#     "admin_name": "Admin User",
#     "reason": "Design approved, ready to implement"
#   }
# ]
```

## Change History

### Tracked Changes

All collaboration actions are tracked in change history:

- **Permission changes** - Add, update, remove team member
- **Comment actions** - Create, reply, resolve
- **Approval actions** - Request, approve, reject
- **Notification events** - @mentions, status changes

### Audit Trail

```python
from apps.backend.collaboration.notifications import NotificationManager

notif_manager = NotificationManager(
    spec_id="001-feature",
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path(".")
)

# Get complete change history
history = await notif_manager.get_change_history()

# Returns chronological list of all changes:
# [
#   {
#     "change_type": "permission_added",
#     "timestamp": "2026-02-13T17:00:00Z",
#     "actor": "owner",
#     "actor_name": "Owner User",
#     "details": {
#       "target_user": "alice",
#       "permission_level": "WRITE"
#     }
#   },
#   {
#     "change_type": "comment_created",
#     "timestamp": "2026-02-13T17:30:00Z",
#     "actor": "alice",
#     "actor_name": "Alice Johnson",
#     "details": {
#       "comment_id": "comment-123",
#       "content": "This looks good!"
#     }
#   },
#   ...
# ]
```

## Integration

### TaskDetailView Integration

The collaboration system is integrated into the frontend via the TaskDetailView component:

```typescript
// apps/frontend/src/renderer/components/task-detail/TaskDetailView.tsx

<Tabs defaultValue="details" className="w-full">
  <TabsList>
    <TabsTrigger value="details">Details</TabsTrigger>
    <TabsTrigger value="collaboration">Collaboration</TabsTrigger>
    {/* ... other tabs ... */}
  </TabsList>

  <TabsContent value="collaboration">
    <ScrollArea className="h-full">
      {/* Permissions Panel */}
      <PermissionsPanel specId={task.specId} />

      <Separator />

      {/* Comment Threads */}
      <CommentThread specId={task.specId} />

      <Separator />

      {/* Approval Workflow */}
      <ApprovalWorkflow specId={task.specId} />
    </ScrollArea>
  </TabsContent>
</Tabs>
```

### Graphiti Storage Integration

Collaboration data is persisted using Graphiti knowledge graph episodes:

```python
# Episode types for collaboration
EPISODE_TYPE_COMMENT = "comment"
EPISODE_TYPE_APPROVAL = "approval"

# Each comment, approval, permission change creates an episode
# Episode metadata includes:
# - spec_id
# - user_id
# - action_type
# - timestamp
# - relevant data (comment content, approval status, etc.)
```

## API Reference

### PermissionChecker

```python
class PermissionChecker:
    """Role-based access control for spec collaboration"""

    async def add_permission(
        self,
        user_id: str,
        username: str,
        level: PermissionLevel
    ) -> SpecPermission:
        """Add team member with specified permission level"""

    async def update_permission(
        self,
        user_id: str,
        level: PermissionLevel
    ) -> SpecPermission:
        """Update existing user's permission level"""

    async def remove_permission(self, user_id: str) -> None:
        """Remove user from spec"""

    async def check_permission(
        self,
        user_id: str,
        required_level: PermissionLevel
    ) -> bool:
        """Check if user has required permission level"""

    async def get_permissions(self) -> list[SpecPermission]:
        """Get all permissions for spec"""

    async def is_owner(self, user_id: str) -> bool:
        """Check if user is spec owner"""
```

### CommentManager

```python
class CommentManager:
    """Threaded comment management with @mentions"""

    async def create_comment(
        self,
        user_id: str,
        username: str,
        content: str
    ) -> Comment:
        """Create top-level comment"""

    async def reply_to_comment(
        self,
        parent_comment_id: str,
        user_id: str,
        username: str,
        content: str
    ) -> Comment:
        """Reply to existing comment"""

    async def update_comment(
        self,
        comment_id: str,
        user_id: str,
        content: str
    ) -> Comment:
        """Update comment content"""

    async def delete_comment(
        self,
        comment_id: str,
        user_id: str
    ) -> None:
        """Delete comment"""

    async def resolve_thread(
        self,
        comment_id: str,
        user_id: str,
        resolved_reason: str = ""
    ) -> None:
        """Resolve comment thread"""

    async def get_comments(
        self,
        include_resolved: bool = True
    ) -> list[Comment]:
        """Get all comments for spec"""
```

### ApprovalManager

```python
class ApprovalManager:
    """Approval workflow management"""

    async def request_approval(
        self,
        requester_id: str,
        requester_name: str
    ) -> Approval:
        """Request approval from admins"""

    async def approve_spec(
        self,
        admin_id: str,
        admin_name: str,
        reason: str = ""
    ) -> Approval:
        """Approve spec for builds"""

    async def reject_spec(
        self,
        admin_id: str,
        admin_name: str,
        reason: str
    ) -> Approval:
        """Reject spec with reason"""

    async def get_approval_status(self) -> Approval:
        """Get current approval status"""

    async def can_build(self) -> bool:
        """Check if spec is approved for builds"""

    async def get_approval_history(self) -> list[dict]:
        """Get complete approval history"""
```

### NotificationManager

```python
class NotificationManager:
    """Notifications and change history tracking"""

    async def get_notifications(
        self,
        user_id: str
    ) -> list[Notification]:
        """Get user's notifications"""

    async def mark_notification_read(
        self,
        notification_id: str,
        user_id: str
    ) -> None:
        """Mark notification as read"""

    async def mark_all_read(self, user_id: str) -> None:
        """Mark all notifications as read"""

    async def get_change_history(
        self,
        limit: int = 100
    ) -> list[ChangeRecord]:
        """Get change history for spec"""
```

## Usage Examples

### Example 1: Team Review Workflow

```python
# 1. Tech lead adds team members
await checker.add_permission("dev1", "Developer One", PermissionLevel.WRITE)
await checker.add_permission("dev2", "Developer Two", PermissionLevel.WRITE)

# 2. Developers leave feedback
await comment_manager.create_comment(
    user_id="dev1",
    username="Developer One",
    content="The API design looks solid. @dev2 what do you think about the error handling?"
)

# 3. Discussion continues with replies
await comment_manager.reply_to_comment(
    parent_comment_id="comment-123",
    user_id="dev2",
    username="Developer Two",
    content="Good point. We should add retry logic for network failures."
)

# 4. Dev1 addresses the feedback
await comment_manager.reply_to_comment(
    parent_comment_id="comment-123",
    user_id="dev1",
    username="Developer One",
    content="Added retry logic in the latest revision. Ready for review."
)

# 5. Dev1 requests approval
await approval_manager.request_approval("dev1", "Developer One")

# 6. Tech lead approves
await approval_manager.approve_spec(
    admin_id="lead",
    admin_name="Tech Lead",
    reason="All feedback addressed, approved for implementation"
)

# 7. Builds can now proceed
if await approval_manager.can_build():
    print("Spec approved, starting build...")
```

### Example 2: Permission Denial

```python
# User with READ permission tries to add comment
try:
    await comment_manager.create_comment(
        user_id="readonly_user",
        username="Read Only User",
        content="Can I add a comment?"
    )
except PermissionError as e:
    print(f"Access denied: {e}")
    # Output: Access denied: WRITE permission required

# User with WRITE permission tries to approve
try:
    await approval_manager.approve_spec(
        admin_id="write_user",
        admin_name="Write User",
        reason="I think this is ready"
    )
except PermissionError as e:
    print(f"Access denied: {e}")
    # Output: Access denied: ADMIN permission required
```

### Example 3: Change History Audit

```python
# Get complete audit trail
history = await notif_manager.get_change_history()

print(f"Total changes: {len(history)}")
for change in history:
    print(f"{change['timestamp']} - {change['actor_name']} - {change['change_type']}")

# Output:
# 2026-02-13T17:00:00Z - Owner User - permission_added
# 2026-02-13T17:05:00Z - Developer One - comment_created
# 2026-02-13T17:10:00Z - Developer Two - comment_created
# 2026-02-13T17:15:00Z - Developer One - approval_requested
# 2026-02-13T17:20:00Z - Tech Lead - approval_approved
```

## Configuration

### Graphiti Schema

Collaboration requires two new episode types in Graphiti schema:

```python
# apps/backend/integrations/graphiti/queries_pkg/schema.py

EPISODE_TYPE_COMMENT = "comment"
EPISODE_TYPE_APPROVAL = "approval"
```

These are automatically created during schema initialization.

### Storage Location

Collaboration data is stored in Graphiti knowledge graph under the spec's group ID:

- **Project mode**: Shared across all specs in the same project
- **Spec mode**: Isolated per spec

```python
# Default: Project mode (shared)
memory = GraphitiMemory(
    spec_dir=spec_dir,
    project_dir=project_dir,
    group_id_mode="project"  # Collaboration data shared across project
)
```

### Permissions Cache

PermissionChecker implements caching to avoid repeated Graphiti queries:

```python
# Cache TTL: 5 minutes (default)
# Cache size: 100 entries (LRU eviction)

# Custom cache configuration
checker = PermissionChecker(
    spec_id="001-feature",
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("."),
    cache_ttl_seconds=300,  # 5 minutes
    cache_size=100
)
```

---

## Summary

The multi-user collaboration system transforms Auto Code from a solo tool to a team platform by providing:

✅ **Enterprise-grade access control** with role-based permissions
✅ **Threaded discussions** with @mentions and reply threading
✅ **Approval workflows** to enforce review processes
✅ **Complete audit trails** for accountability and compliance
✅ **Real-time updates** through event-driven architecture
✅ **Persistent storage** via Graphiti knowledge graph integration

For implementation details, see:
- Backend modules: `apps/backend/collaboration/`
- Frontend components: `apps/frontend/src/renderer/components/collaboration/`
- IPC handlers: `apps/frontend/src/main/ipc-handlers/collaboration-handlers.ts`
- End-to-end tests: `tests/test_collaboration_e2e.py`
