/**
 * Collaboration IPC handlers
 *
 * Handlers for multi-user spec collaboration including:
 * - Permissions: Role-based access control (read/write/admin)
 * - Comments: Threaded discussions with @mentions
 * - Approvals: Spec review and approval workflow
 * - Notifications: @mentions and approval status changes
 * - Change history: Audit trail of spec modifications
 *
 * These handlers call Python backend collaboration modules via subprocess.
 */

import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import path from 'path';
import { projectStore } from '../project-store';
import { runPythonSubprocess } from './github/utils/subprocess-runner';
import { getRunnerEnv } from './github/utils/runner-env';
import type { BrowserWindow } from 'electron';
import { findTaskAndProject } from './task/shared';

/**
 * Helper to get the backend directory path
 */
function getBackendDir(): string {
  const projectRoot = path.resolve(__dirname, '../../../..');
  return path.join(projectRoot, 'apps', 'backend');
}

/**
 * Helper to get Python executable path and environment
 */
async function getPythonEnv(_projectPath: string): Promise<{ pythonPath: string; env: Record<string, string> }> {
  const env = await getRunnerEnv();
  const pythonPath = 'python';
  return { pythonPath, env };
}

// ========================================
// Shared Helpers
// ========================================

/**
 * Build Python script args with standard boilerplate (import sys, json, sys.path.insert).
 */
function buildCollabScript(backendDir: string, pythonCode: string): string[] {
  return [
    '-c',
    `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

${pythonCode}
    `
  ];
}

/**
 * Run a Python collaboration subprocess, parse JSON stdout, and return an IPCResult.
 */
async function runCollabPython(
  pythonPath: string,
  backendDir: string,
  env: Record<string, string>,
  pythonCode: string,
  errorLabel: string
): Promise<IPCResult> {
  const args = buildCollabScript(backendDir, pythonCode);

  const { promise } = runPythonSubprocess({
    pythonPath,
    args,
    cwd: backendDir,
    env
  });

  const result = await promise;

  if (!result.success || result.exitCode !== 0) {
    console.error(`[${errorLabel}] Python subprocess failed:`, result.error);
    return { success: false, error: result.error || `Failed: ${errorLabel}` };
  }

  const data = result.stdout.trim() ? JSON.parse(result.stdout.trim()) : null;
  return { success: true, data };
}

/**
 * Resolve spec context: find task+project, get Python env, backend dir.
 * Returns null if context cannot be resolved (error already returned).
 */
async function resolveSpecContext(specId: string) {
  const { task, project } = await findTaskAndProject(specId);
  if (!task || !project) return null;

  const { pythonPath, env } = await getPythonEnv(project.path);
  const backendDir = getBackendDir();
  return { task, project, pythonPath, env, backendDir };
}

/**
 * Resolve project context (no specId needed, uses first project).
 * Returns null if no project found.
 */
async function resolveProjectContext() {
  const projects = projectStore.getProjects();
  const project = projects[0];
  if (!project) return null;

  const { pythonPath, env } = await getPythonEnv(project.path);
  const backendDir = getBackendDir();
  return { project, pythonPath, env, backendDir };
}

/**
 * Wrap a handler with standard try/catch error handling.
 */
function collabHandler(
  label: string,
  fn: (...args: unknown[]) => Promise<IPCResult>
): (...args: unknown[]) => Promise<IPCResult> {
  return async (...args: unknown[]) => {
    try {
      return await fn(...args);
    } catch (error) {
      console.error(`[${label}] Error:`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  };
}

/**
 * Register collaboration IPC handlers
 */
export function registerCollaborationHandlers(getMainWindow: () => BrowserWindow | null): void {
  // ========================================
  // Permission Handlers
  // ========================================

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_PERMISSIONS_GET,
    collabHandler('COLLABORATION_PERMISSIONS_GET', async (_, specId: string) => {
      console.warn('[IPC] COLLABORATION_PERMISSIONS_GET called for spec:', specId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      return runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify('')})

memory = get_graphiti_memory(None, Path(${JSON.stringify(ctx.project.path)}))

# Get permissions from Graphiti
permissions = memory.get_permissions(spec_id)

# Convert to list of dicts for JSON serialization
result = []
for perm in permissions:
    result.append({
        'user_id': perm.user.user_id,
        'username': perm.user.username,
        'email': perm.user.email,
        'level': perm.level.value,
        'granted_by': perm.granted_by,
        'granted_at': perm.granted_at
    })

print(json.dumps(result))
      `, 'COLLABORATION_PERMISSIONS_GET');
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_PERMISSIONS_ADD,
    collabHandler('COLLABORATION_PERMISSIONS_ADD', async (
      _,
      specId: string,
      userId: string,
      username: string,
      level: string,
      grantedBy: string,
      email?: string
    ) => {
      console.warn('[IPC] COLLABORATION_PERMISSIONS_ADD called for spec:', specId, 'user:', username);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      return runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from collaboration.models import CollaborationUser, PermissionLevel
from collaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})

memory = get_graphiti_memory(None, project_dir)

# Create user and grant permission
user = CollaborationUser(
    user_id=${JSON.stringify(userId)},
    username=${JSON.stringify(username)},
    email=${JSON.stringify(email)}
)

level = PermissionLevel(${JSON.stringify(level)})
checker = PermissionChecker(spec_id=spec_id)
permission = checker.grant_permission(
    user_id=user.user_id,
    username=user.username,
    level=level,
    granted_by=${JSON.stringify(grantedBy)},
    email=user.email
)

# Save to Graphiti
memory.save_permission(permission)

print(json.dumps({
    'user_id': permission.user.user_id,
    'username': permission.user.username,
    'level': permission.level.value,
    'granted_by': permission.granted_by,
    'granted_at': permission.granted_at
}))
      `, 'COLLABORATION_PERMISSIONS_ADD');
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_PERMISSIONS_UPDATE,
    collabHandler('COLLABORATION_PERMISSIONS_UPDATE', async (
      _,
      specId: string,
      userId: string,
      newLevel: string
    ) => {
      console.warn('[IPC] COLLABORATION_PERMISSIONS_UPDATE called for spec:', specId, 'user:', userId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      return runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from collaboration.models import PermissionLevel
from collaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
user_id = ${JSON.stringify(userId)}
new_level = PermissionLevel(${JSON.stringify(newLevel)})
project_dir = Path(${JSON.stringify(ctx.project.path)})

memory = get_graphiti_memory(None, project_dir)

# Revoke old permission and grant new one
checker = PermissionChecker(spec_id=spec_id)
checker.revoke_permission(user_id)
new_permission = checker.grant_permission(
    user_id=user_id,
    username=user_id,  # Will be updated on retrieval
    level=new_level,
    granted_by='system'
)

# Save to Graphiti
memory.save_permission(new_permission)

print(json.dumps({
    'user_id': new_permission.user.user_id,
    'level': new_permission.level.value
}))
      `, 'COLLABORATION_PERMISSIONS_UPDATE');
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_PERMISSIONS_REMOVE,
    collabHandler('COLLABORATION_PERMISSIONS_REMOVE', async (
      _,
      specId: string,
      userId: string
    ) => {
      console.warn('[IPC] COLLABORATION_PERMISSIONS_REMOVE called for spec:', specId, 'user:', userId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      return runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from collaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
user_id = ${JSON.stringify(userId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})

memory = get_graphiti_memory(None, project_dir)

# Revoke permission
checker = PermissionChecker(spec_id=spec_id)
revoked = checker.revoke_permission(user_id)

# Remove from Graphiti
memory.revoke_permission(spec_id, user_id)

print(json.dumps({ 'revoked': revoked }))
      `, 'COLLABORATION_PERMISSIONS_REMOVE');
    })
  );

  // ========================================
  // Comment Handlers
  // ========================================

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_GET,
    collabHandler('COLLABORATION_COMMENTS_GET', async (_, specId: string) => {
      console.warn('[IPC] COLLABORATION_COMMENTS_GET called for spec:', specId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      return runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})

memory = get_graphiti_memory(None, project_dir)

# Get comments from Graphiti
comments = memory.get_comments(spec_id)

# Convert to list of dicts
result = []
for comment in comments:
    result.append({
        'comment_id': comment.comment_id,
        'spec_id': comment.spec_id,
        'author': {
            'user_id': comment.author.user_id,
            'username': comment.author.username,
            'email': comment.author.email
        },
        'content': comment.content,
        'created_at': comment.created_at,
        'parent_id': comment.parent_id,
        'mentions': comment.mentions,
        'resolved': comment.resolved,
        'updated_at': comment.updated_at
    })

print(json.dumps(result))
      `, 'COLLABORATION_COMMENTS_GET');
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_CREATE,
    collabHandler('COLLABORATION_COMMENTS_CREATE', async (
      _,
      specId: string,
      userId: string,
      username: string,
      content: string,
      parentId?: string
    ) => {
      console.warn('[IPC] COLLABORATION_COMMENTS_CREATE called for spec:', specId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      const ipcResult = await runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from collaboration.models import CollaborationUser, Comment
from collaboration.comments import CommentManager
from collaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})
parent_id = ${JSON.stringify(parentId)}

memory = get_graphiti_memory(None, project_dir)
permission_checker = PermissionChecker(spec_id=spec_id)
manager = CommentManager(spec_id=spec_id, spec_dir=project_dir / 'specs' / spec_id, project_dir=project_dir, permission_checker=permission_checker)

user = CollaborationUser(user_id=${JSON.stringify(userId)}, username=${JSON.stringify(username)})

if parent_id:
    # Reply to comment
    comment = await manager.reply_to_comment(
        parent_comment_id=parent_id,
        user_id=user.user_id,
        username=user.username,
        content=${JSON.stringify(content)}
    )
else:
    # Top-level comment
    comment = await manager.create_comment(
        user_id=user.user_id,
        username=user.username,
        content=${JSON.stringify(content)}
    )

# Convert to dict
result = {
    'comment_id': comment.comment_id,
    'spec_id': comment.spec_id,
    'author': {
        'user_id': comment.author.user_id,
        'username': comment.author.username
    },
    'content': comment.content,
    'created_at': comment.created_at,
    'parent_id': comment.parent_id,
    'mentions': comment.mentions,
    'resolved': comment.resolved
}

print(json.dumps(result))
      `, 'COLLABORATION_COMMENTS_CREATE');

      if (ipcResult.success) {
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_COMMENT_ADDED, { specId, comment: ipcResult.data });
        }
      }

      return ipcResult;
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_UPDATE,
    collabHandler('COLLABORATION_COMMENTS_UPDATE', async (
      _,
      specId: string,
      commentId: string,
      newContent: string
    ) => {
      console.warn('[IPC] COLLABORATION_COMMENTS_UPDATE called for comment:', commentId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      return runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
comment_id = ${JSON.stringify(commentId)}
new_content = ${JSON.stringify(newContent)}
project_dir = Path(${JSON.stringify(ctx.project.path)})

memory = get_graphiti_memory(None, project_dir)

# Update comment
comment = memory.get_comment(comment_id)
comment.content = new_content
comment.mark_edited()

# Save to Graphiti
memory.update_comment(comment)

result = {
    'comment_id': comment.comment_id,
    'content': comment.content,
    'updated_at': comment.updated_at
}

print(json.dumps(result))
      `, 'COLLABORATION_COMMENTS_UPDATE');
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_DELETE,
    collabHandler('COLLABORATION_COMMENTS_DELETE', async (
      _,
      specId: string,
      commentId: string
    ) => {
      console.warn('[IPC] COLLABORATION_COMMENTS_DELETE called for comment:', commentId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      const ipcResult = await runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
comment_id = ${JSON.stringify(commentId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})

memory = get_graphiti_memory(None, project_dir)

# Delete comment
memory.delete_comment(comment_id)

print(json.dumps({ 'deleted': True }))
      `, 'COLLABORATION_COMMENTS_DELETE');

      if (ipcResult.success) return { success: true };
      return ipcResult;
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_RESOLVE,
    collabHandler('COLLABORATION_COMMENTS_RESOLVE', async (
      _,
      specId: string,
      commentId: string
    ) => {
      console.warn('[IPC] COLLABORATION_COMMENTS_RESOLVE called for comment:', commentId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      return runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
comment_id = ${JSON.stringify(commentId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})

memory = get_graphiti_memory(None, project_dir)

# Resolve thread
comment = memory.get_comment(comment_id)
comment.mark_resolved()

# Save to Graphiti
memory.update_comment(comment)

print(json.dumps({
    'comment_id': comment.comment_id,
    'resolved': comment.resolved
}))
      `, 'COLLABORATION_COMMENTS_RESOLVE');
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_REPLY,
    collabHandler('COLLABORATION_COMMENTS_REPLY', async (
      _,
      specId: string,
      parentCommentId: string,
      userId: string,
      username: string,
      content: string
    ) => {
      console.warn('[IPC] COLLABORATION_COMMENTS_REPLY called for comment:', parentCommentId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      const ipcResult = await runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from collaboration.models import CollaborationUser
from collaboration.comments import CommentManager
from collaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
parent_comment_id = ${JSON.stringify(parentCommentId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})

memory = get_graphiti_memory(None, project_dir)
permission_checker = PermissionChecker(spec_id=spec_id)
manager = CommentManager(spec_id=spec_id, spec_dir=project_dir / 'specs' / spec_id, project_dir=project_dir, permission_checker=permission_checker)

user = CollaborationUser(user_id=${JSON.stringify(userId)}, username=${JSON.stringify(username)})

reply = await manager.reply_to_comment(
    parent_comment_id=parent_comment_id,
    user_id=user.user_id,
    username=user.username,
    content=${JSON.stringify(content)}
)

# Convert to dict
result = {
    'comment_id': reply.comment_id,
    'spec_id': reply.spec_id,
    'author': {
        'user_id': reply.author.user_id,
        'username': reply.author.username
    },
    'content': reply.content,
    'created_at': reply.created_at,
    'parent_id': reply.parent_id,
    'mentions': reply.mentions
}

print(json.dumps(result))
      `, 'COLLABORATION_COMMENTS_REPLY');

      if (ipcResult.success) {
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_COMMENT_ADDED, { specId, comment: ipcResult.data });
        }
      }

      return ipcResult;
    })
  );

  // ========================================
  // Approval Handlers
  // ========================================

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_APPROVALS_GET,
    collabHandler('COLLABORATION_APPROVALS_GET', async (_, specId: string) => {
      console.warn('[IPC] COLLABORATION_APPROVALS_GET called for spec:', specId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      return runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})

memory = get_graphiti_memory(None, project_dir)

# Get approval status
approval = memory.get_approval(spec_id)

if approval:
    result = {
        'approval_id': approval.approval_id,
        'spec_id': approval.spec_id,
        'approver': {
            'user_id': approval.approver.user_id,
            'username': approval.approver.username
        },
        'status': approval.status.value,
        'reason': approval.reason,
        'created_at': approval.created_at,
        'reviewed_at': approval.reviewed_at
    }
else:
    result = None

print(json.dumps(result))
      `, 'COLLABORATION_APPROVALS_GET');
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_APPROVALS_REQUEST,
    collabHandler('COLLABORATION_APPROVALS_REQUEST', async (
      _,
      specId: string,
      userId: string,
      username: string
    ) => {
      console.warn('[IPC] COLLABORATION_APPROVALS_REQUEST called for spec:', specId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      const ipcResult = await runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from collaboration.models import CollaborationUser
from collaboration.approvals import ApprovalManager
from collaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})

memory = get_graphiti_memory(None, project_dir)
permission_checker = PermissionChecker(spec_id=spec_id)
manager = ApprovalManager(spec_id=spec_id, spec_dir=project_dir / 'specs' / spec_id, project_dir=project_dir, permission_checker=permission_checker)

user = CollaborationUser(user_id=${JSON.stringify(userId)}, username=${JSON.stringify(username)})

approval = await manager.request_approval(requester_id=user.user_id, requester_username=user.username)

# Convert to dict
result = {
    'approval_id': approval.approval_id,
    'spec_id': approval.spec_id,
    'status': approval.status.value,
    'created_at': approval.created_at
}
if approval.requester:
    result['requester'] = {
        'user_id': approval.requester.user_id,
        'username': approval.requester.username
    }

print(json.dumps(result))
      `, 'COLLABORATION_APPROVALS_REQUEST');

      if (ipcResult.success) {
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_APPROVAL_STATUS_CHANGED, { specId, approval: ipcResult.data });
        }
      }

      return ipcResult;
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_APPROVALS_APPROVE,
    collabHandler('COLLABORATION_APPROVALS_APPROVE', async (
      _,
      specId: string,
      approverId: string,
      approverUsername: string,
      reason?: string
    ) => {
      console.warn('[IPC] COLLABORATION_APPROVALS_APPROVE called for spec:', specId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      const ipcResult = await runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from collaboration.models import CollaborationUser
from collaboration.approvals import ApprovalManager
from collaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})
reason = ${JSON.stringify(reason)}

memory = get_graphiti_memory(None, project_dir)
permission_checker = PermissionChecker(spec_id=spec_id)
manager = ApprovalManager(spec_id=spec_id, spec_dir=project_dir / 'specs' / spec_id, project_dir=project_dir, permission_checker=permission_checker)

approver = CollaborationUser(user_id=${JSON.stringify(approverId)}, username=${JSON.stringify(approverUsername)})

await manager.approve_spec(approver_id=approver.user_id, approver_username=approver.username, reason=reason)

# Get updated approval
approval = memory.get_approval(spec_id)

result = {
    'approval_id': approval.approval_id,
    'status': approval.status.value,
    'reviewed_at': approval.reviewed_at
}

print(json.dumps(result))
      `, 'COLLABORATION_APPROVALS_APPROVE');

      if (ipcResult.success) {
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_APPROVAL_STATUS_CHANGED, { specId, approval: ipcResult.data });
        }
      }

      return ipcResult;
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_APPROVALS_REJECT,
    collabHandler('COLLABORATION_APPROVALS_REJECT', async (
      _,
      specId: string,
      approverId: string,
      approverUsername: string,
      reason?: string
    ) => {
      console.warn('[IPC] COLLABORATION_APPROVALS_REJECT called for spec:', specId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      const ipcResult = await runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from collaboration.models import CollaborationUser
from collaboration.approvals import ApprovalManager
from collaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})
reason = ${JSON.stringify(reason)}

memory = get_graphiti_memory(None, project_dir)
permission_checker = PermissionChecker(spec_id=spec_id)
manager = ApprovalManager(spec_id=spec_id, spec_dir=project_dir / 'specs' / spec_id, project_dir=project_dir, permission_checker=permission_checker)

approver = CollaborationUser(user_id=${JSON.stringify(approverId)}, username=${JSON.stringify(approverUsername)})

await manager.reject_spec(approver_id=approver.user_id, approver_username=approver.username, reason=reason)

# Get updated approval
approval = memory.get_approval(spec_id)

result = {
    'approval_id': approval.approval_id,
    'status': approval.status.value,
    'reviewed_at': approval.reviewed_at
}

print(json.dumps(result))
      `, 'COLLABORATION_APPROVALS_REJECT');

      if (ipcResult.success) {
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_APPROVAL_STATUS_CHANGED, { specId, approval: ipcResult.data });
        }
      }

      return ipcResult;
    })
  );

  // ========================================
  // Notification Handlers
  // ========================================

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_NOTIFICATIONS_GET,
    collabHandler('COLLABORATION_NOTIFICATIONS_GET', async (_, userId: string) => {
      console.warn('[IPC] COLLABORATION_NOTIFICATIONS_GET called for user:', userId);
      const ctx = await resolveProjectContext();
      if (!ctx) return { success: false, error: 'No projects found' };

      return runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
user_id = ${JSON.stringify(userId)}

# Collect notifications from all projects
# For now, return empty list - notification retrieval would need project context
result = []

print(json.dumps(result))
      `, 'COLLABORATION_NOTIFICATIONS_GET');
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_NOTIFICATIONS_MARK_READ,
    collabHandler('COLLABORATION_NOTIFICATIONS_MARK_READ', async (
      _,
      notificationId: string
    ) => {
      console.warn('[IPC] COLLABORATION_NOTIFICATIONS_MARK_READ called for notification:', notificationId);
      const ctx = await resolveProjectContext();
      if (!ctx) return { success: false, error: 'No projects found' };

      const ipcResult = await runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
notification_id = ${JSON.stringify(notificationId)}

# Mark notification as read
# This would be implemented in NotificationManager
result = { 'marked': True }

print(json.dumps(result))
      `, 'COLLABORATION_NOTIFICATIONS_MARK_READ');

      if (ipcResult.success) return { success: true };
      return ipcResult;
    })
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_NOTIFICATIONS_MARK_ALL_READ,
    collabHandler('COLLABORATION_NOTIFICATIONS_MARK_ALL_READ', async (_, userId: string) => {
      console.warn('[IPC] COLLABORATION_NOTIFICATIONS_MARK_ALL_READ called for user:', userId);
      const ctx = await resolveProjectContext();
      if (!ctx) return { success: false, error: 'No projects found' };

      const ipcResult = await runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
user_id = ${JSON.stringify(userId)}

# Mark all notifications as read
# This would be implemented in NotificationManager
result = { 'marked': True }

print(json.dumps(result))
      `, 'COLLABORATION_NOTIFICATIONS_MARK_ALL_READ');

      if (ipcResult.success) return { success: true };
      return ipcResult;
    })
  );

  // ========================================
  // Change History Handlers
  // ========================================

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_CHANGE_HISTORY_GET,
    collabHandler('COLLABORATION_CHANGE_HISTORY_GET', async (_, specId: string) => {
      console.warn('[IPC] COLLABORATION_CHANGE_HISTORY_GET called for spec:', specId);
      const ctx = await resolveSpecContext(specId);
      if (!ctx) return { success: false, error: 'Task or project not found' };

      return runCollabPython(ctx.pythonPath, ctx.backendDir, ctx.env, `
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(ctx.project.path)})

memory = get_graphiti_memory(None, project_dir)

# Get change history from Graphiti
changes = memory.get_change_history(spec_id)

# Convert to list of dicts
result = []
for change in changes:
    result.append({
        'timestamp': change.get('timestamp'),
        'user_id': change.get('user_id'),
        'username': change.get('username'),
        'action': change.get('action'),
        'details': change.get('details')
    })

print(json.dumps(result))
      `, 'COLLABORATION_CHANGE_HISTORY_GET');
    })
  );

  console.warn('[IPC] Collaboration handlers registered successfully');
}
