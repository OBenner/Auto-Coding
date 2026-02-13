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
import { IPC_CHANNELS, AUTO_BUILD_PATHS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import path from 'path';
import { promises as fsPromises } from 'fs';
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
async function getPythonEnv(projectPath: string): Promise<{ pythonPath: string; env: Record<string, string> }> {
  const env = await getRunnerEnv();
  const pythonPath = 'python';
  return { pythonPath, env };
}

/**
 * Check if a file exists
 */
async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fsPromises.access(filePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Register collaboration IPC handlers
 */
export function registerCollaborationHandlers(getMainWindow: () => BrowserWindow | null): void {
  // ========================================
  // Permission Handlers
  // ========================================

  /**
   * Get all permissions for a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_PERMISSIONS_GET,
    async (_, specId: string): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_PERMISSIONS_GET called for spec:', specId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(project.path)})

memory = get_graphiti_memory(None, project_dir)

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
          `
        ];

        const { promise } = runPythonSubprocess<{ permissions: unknown[] }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_PERMISSIONS_GET] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to get permissions' };
        }

        const permissions = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_PERMISSIONS_GET returning', permissions.length, 'permissions');

        return { success: true, data: permissions };
      } catch (error) {
        console.error('[COLLABORATION_PERMISSIONS_GET] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Add a user to spec with role
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_PERMISSIONS_ADD,
    async (
      _,
      specId: string,
      userId: string,
      username: string,
      level: string,
      grantedBy: string,
      email?: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_PERMISSIONS_ADD called for spec:', specId, 'user:', username);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from colaboration.models import CollaborationUser, PermissionLevel
from colaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(project.path)})

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
          `
        ];

        const { promise } = runPythonSubprocess<{ permission: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_PERMISSIONS_ADD] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to add permission' };
        }

        const permission = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_PERMISSIONS_ADD success');

        return { success: true, data: permission };
      } catch (error) {
        console.error('[COLLABORATION_PERMISSIONS_ADD] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Update user's role on spec
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_PERMISSIONS_UPDATE,
    async (
      _,
      specId: string,
      userId: string,
      newLevel: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_PERMISSIONS_UPDATE called for spec:', specId, 'user:', userId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from colaboration.models import PermissionLevel
from colaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
user_id = ${JSON.stringify(userId)}
new_level = PermissionLevel(${JSON.stringify(newLevel)})
project_dir = Path(${JSON.stringify(project.path)})

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
          `
        ];

        const { promise } = runPythonSubprocess<{ permission: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_PERMISSIONS_UPDATE] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to update permission' };
        }

        const permission = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_PERMISSIONS_UPDATE success');

        return { success: true, data: permission };
      } catch (error) {
        console.error('[COLLABORATION_PERMISSIONS_UPDATE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Remove user from spec
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_PERMISSIONS_REMOVE,
    async (
      _,
      specId: string,
      userId: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_PERMISSIONS_REMOVE called for spec:', specId, 'user:', userId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from colaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
user_id = ${JSON.stringify(userId)}
project_dir = Path(${JSON.stringify(project.path)})

memory = get_graphiti_memory(None, project_dir)

# Revoke permission
checker = PermissionChecker(spec_id=spec_id)
revoked = checker.revoke_permission(user_id)

# Remove from Graphiti
memory.revoke_permission(spec_id, user_id)

print(json.dumps({ 'revoked': revoked }))
          `
        ];

        const { promise } = runPythonSubprocess<{ result: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_PERMISSIONS_REMOVE] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to remove permission' };
        }

        console.warn('[IPC] COLLABORATION_PERMISSIONS_REMOVE success');

        return { success: true };
      } catch (error) {
        console.error('[COLLABORATION_PERMISSIONS_REMOVE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  // ========================================
  // Comment Handlers
  // ========================================

  /**
   * Get all comments for a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_GET,
    async (_, specId: string): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_COMMENTS_GET called for spec:', specId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(project.path)})

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
          `
        ];

        const { promise } = runPythonSubprocess<{ comments: unknown[] }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_COMMENTS_GET] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to get comments' };
        }

        const comments = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_COMMENTS_GET returning', comments.length, 'comments');

        return { success: true, data: comments };
      } catch (error) {
        console.error('[COLLABORATION_COMMENTS_GET] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Create a new comment
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_CREATE,
    async (
      _,
      specId: string,
      userId: string,
      username: string,
      content: string,
      parentId?: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_COMMENTS_CREATE called for spec:', specId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from colaboration.models import CollaborationUser, Comment
from colaboration.comments import CommentManager
from colaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(project.path)})
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
          `
        ];

        const { promise } = runPythonSubprocess<{ comment: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_COMMENTS_CREATE] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to create comment' };
        }

        const comment = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_COMMENTS_CREATE success');

        // Emit event for real-time updates
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_COMMENT_ADDED, { specId, comment });
        }

        return { success: true, data: comment };
      } catch (error) {
        console.error('[COLLABORATION_COMMENTS_CREATE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Update existing comment
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_UPDATE,
    async (
      _,
      specId: string,
      commentId: string,
      newContent: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_COMMENTS_UPDATE called for comment:', commentId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
comment_id = ${JSON.stringify(commentId)}
new_content = ${JSON.stringify(newContent)}
project_dir = Path(${JSON.stringify(project.path)})

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
          `
        ];

        const { promise } = runPythonSubprocess<{ comment: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_COMMENTS_UPDATE] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to update comment' };
        }

        const comment = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_COMMENTS_UPDATE success');

        return { success: true, data: comment };
      } catch (error) {
        console.error('[COLLABORATION_COMMENTS_UPDATE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Delete a comment
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_DELETE,
    async (
      _,
      specId: string,
      commentId: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_COMMENTS_DELETE called for comment:', commentId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
comment_id = ${JSON.stringify(commentId)}
project_dir = Path(${JSON.stringify(project.path)})

memory = get_graphiti_memory(None, project_dir)

# Delete comment
memory.delete_comment(comment_id)

print(json.dumps({ 'deleted': True }))
          `
        ];

        const { promise } = runPythonSubprocess<{ result: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_COMMENTS_DELETE] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to delete comment' };
        }

        console.warn('[IPC] COLLABORATION_COMMENTS_DELETE success');

        return { success: true };
      } catch (error) {
        console.error('[COLLABORATION_COMMENTS_DELETE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Resolve a comment thread
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_RESOLVE,
    async (
      _,
      specId: string,
      commentId: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_COMMENTS_RESOLVE called for comment:', commentId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
comment_id = ${JSON.stringify(commentId)}
project_dir = Path(${JSON.stringify(project.path)})

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
          `
        ];

        const { promise } = runPythonSubprocess<{ comment: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_COMMENTS_RESOLVE] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to resolve comment' };
        }

        const comment = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_COMMENTS_RESOLVE success');

        return { success: true, data: comment };
      } catch (error) {
        console.error('[COLLABORATION_COMMENTS_RESOLVE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Reply to a comment
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_REPLY,
    async (
      _,
      specId: string,
      parentCommentId: string,
      userId: string,
      username: string,
      content: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_COMMENTS_REPLY called for comment:', parentCommentId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from colaboration.models import CollaborationUser
from colaboration.comments import CommentManager
from colaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
parent_comment_id = ${JSON.stringify(parentCommentId)}
project_dir = Path(${JSON.stringify(project.path)})

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
          `
        ];

        const { promise } = runPythonSubprocess<{ comment: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_COMMENTS_REPLY] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to reply to comment' };
        }

        const comment = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_COMMENTS_REPLY success');

        // Emit event for real-time updates
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_COMMENT_ADDED, { specId, comment });
        }

        return { success: true, data: comment };
      } catch (error) {
        console.error('[COLLABORATION_COMMENTS_REPLY] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  // ========================================
  // Approval Handlers
  // ========================================

  /**
   * Get approval status for a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_APPROVALS_GET,
    async (_, specId: string): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_APPROVALS_GET called for spec:', specId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(project.path)})

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
          `
        ];

        const { promise } = runPythonSubprocess<{ approval: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_APPROVALS_GET] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to get approval status' };
        }

        const approval = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_APPROVALS_GET returning approval:', approval);

        return { success: true, data: approval };
      } catch (error) {
        console.error('[COLLABORATION_APPROVALS_GET] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Request approval for a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_APPROVALS_REQUEST,
    async (
      _,
      specId: string,
      userId: string,
      username: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_APPROVALS_REQUEST called for spec:', specId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from colaboration.models import CollaborationUser
from colaboration.approvals import ApprovalManager
from colaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(project.path)})

memory = get_graphiti_memory(None, project_dir)
permission_checker = PermissionChecker(spec_id=spec_id)
manager = ApprovalManager(spec_id=spec_id, spec_dir=project_dir / 'specs' / spec_id, project_dir=project_dir, permission_checker=permission_checker)

user = CollaborationUser(user_id=${JSON.stringify(userId)}, username=${JSON.stringify(username)})

approval = await manager.request_approval(requester_id=user.user_id, requester_username=user.username)

# Convert to dict
result = {
    'approval_id': approval.approval_id,
    'spec_id': approval.spec_id,
    'approver': {
        'user_id': approval.approver.user_id,
        'username': approval.approver.username
    },
    'status': approval.status.value,
    'created_at': approval.created_at
}

print(json.dumps(result))
          `
        ];

        const { promise } = runPythonSubprocess<{ approval: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_APPROVALS_REQUEST] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to request approval' };
        }

        const approval = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_APPROVALS_REQUEST success');

        // Emit event for real-time updates
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_APPROVAL_STATUS_CHANGED, { specId, approval });
        }

        return { success: true, data: approval };
      } catch (error) {
        console.error('[COLLABORATION_APPROVALS_REQUEST] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Approve a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_APPROVALS_APPROVE,
    async (
      _,
      specId: string,
      approverId: string,
      approverUsername: string,
      reason?: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_APPROVALS_APPROVE called for spec:', specId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from colaboration.models import CollaborationUser
from colaboration.approvals import ApprovalManager
from colaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(project.path)})
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
          `
        ];

        const { promise } = runPythonSubprocess<{ approval: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_APPROVALS_APPROVE] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to approve spec' };
        }

        const approval = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_APPROVALS_APPROVE success');

        // Emit event for real-time updates
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_APPROVAL_STATUS_CHANGED, { specId, approval });
        }

        return { success: true, data: approval };
      } catch (error) {
        console.error('[COLLABORATION_APPROVALS_APPROVE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Reject a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_APPROVALS_REJECT,
    async (
      _,
      specId: string,
      approverId: string,
      approverUsername: string,
      reason?: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_APPROVALS_REJECT called for spec:', specId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory
from colaboration.models import CollaborationUser
from colaboration.approvals import ApprovalManager
from colaboration.permissions import PermissionChecker

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(project.path)})
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
          `
        ];

        const { promise } = runPythonSubprocess<{ approval: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_APPROVALS_REJECT] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to reject spec' };
        }

        const approval = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_APPROVALS_REJECT success');

        // Emit event for real-time updates
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_APPROVAL_STATUS_CHANGED, { specId, approval });
        }

        return { success: true, data: approval };
      } catch (error) {
        console.error('[COLLABORATION_APPROVALS_REJECT] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  // ========================================
  // Notification Handlers
  // ========================================

  /**
   * Get notifications for a user
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_NOTIFICATIONS_GET,
    async (_, userId: string): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_NOTIFICATIONS_GET called for user:', userId);

        // Get first project for context
        const projects = projectStore.getProjects();
        const project = projects[0];

        if (!project) {
          return { success: false, error: 'No projects found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

user_id = ${JSON.stringify(userId)}

# Collect notifications from all projects
all_notifications = []

# For now, return empty list - notification retrieval would need project context
# This would be enhanced to query across all project Graphiti instances

result = []

print(json.dumps(result))
          `
        ];

        const { promise } = runPythonSubprocess<{ notifications: unknown[] }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_NOTIFICATIONS_GET] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to get notifications' };
        }

        const notifications = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_NOTIFICATIONS_GET returning', notifications.length, 'notifications');

        return { success: true, data: notifications };
      } catch (error) {
        console.error('[COLLABORATION_NOTIFICATIONS_GET] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Mark notification as read
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_NOTIFICATIONS_MARK_READ,
    async (
      _,
      notificationId: string
    ): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_NOTIFICATIONS_MARK_READ called for notification:', notificationId);

        const projects = projectStore.getProjects();
        const project = projects[0];

        if (!project) {
          return { success: false, error: 'No projects found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

notification_id = ${JSON.stringify(notificationId)}

# Mark notification as read
# This would be implemented in NotificationManager
# For now, return success

result = { 'marked': True }

print(json.dumps(result))
          `
        ];

        const { promise } = runPythonSubprocess<{ result: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_NOTIFICATIONS_MARK_READ] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to mark notification as read' };
        }

        console.warn('[IPC] COLLABORATION_NOTIFICATIONS_MARK_READ success');

        return { success: true };
      } catch (error) {
        console.error('[COLLABORATION_NOTIFICATIONS_MARK_READ] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Mark all notifications as read
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_NOTIFICATIONS_MARK_ALL_READ,
    async (_, userId: string): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_NOTIFICATIONS_MARK_ALL_READ called for user:', userId);

        const projects = projectStore.getProjects();
        const project = projects[0];

        if (!project) {
          return { success: false, error: 'No projects found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

user_id = ${JSON.stringify(userId)}

# Mark all notifications as read
# This would be implemented in NotificationManager
# For now, return success

result = { 'marked': True }

print(json.dumps(result))
          `
        ];

        const { promise } = runPythonSubprocess<{ result: unknown }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_NOTIFICATIONS_MARK_ALL_READ] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to mark all notifications as read' };
        }

        console.warn('[IPC] COLLABORATION_NOTIFICATIONS_MARK_ALL_READ success');

        return { success: true };
      } catch (error) {
        console.error('[COLLABORATION_NOTIFICATIONS_MARK_ALL_READ] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  // ========================================
  // Change History Handlers
  // ========================================

  /**
   * Get change history for a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_CHANGE_HISTORY_GET,
    async (_, specId: string): Promise<IPCResult> => {
      try {
        console.warn('[IPC] COLLABORATION_CHANGE_HISTORY_GET called for spec:', specId);

        // Find the task and project using the shared helper
        const { task, project } = await findTaskAndProject(specId);

        if (!task || !project) {
          return { success: false, error: 'Task or project not found' };
        }

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

spec_id = ${JSON.stringify(specId)}
project_dir = Path(${JSON.stringify(project.path)})

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
          `
        ];

        const { promise } = runPythonSubprocess<{ changes: unknown[] }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          console.error('[COLLABORATION_CHANGE_HISTORY_GET] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to get change history' };
        }

        const changes = JSON.parse(result.stdout.trim());
        console.warn('[IPC] COLLABORATION_CHANGE_HISTORY_GET returning', changes.length, 'changes');

        return { success: true, data: changes };
      } catch (error) {
        console.error('[COLLABORATION_CHANGE_HISTORY_GET] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  console.warn('[IPC] Collaboration handlers registered successfully');
}
