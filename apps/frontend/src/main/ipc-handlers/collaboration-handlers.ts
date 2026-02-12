/**
 * IPC Handlers for Real-time Collaboration
 *
 * This module handles IPC communication for collaborative spec editing features:
 * - WebSocket connection management
 * - Comment threading
 * - Suggestion mode
 * - Presence indicators
 * - Version history
 */

import { ipcMain, BrowserWindow } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type {
  IPCResult,
  Comment,
  Suggestion,
  Presence,
  Version,
  SpecCollaborationState
} from '../../shared/types';

// In-memory store for active collaboration sessions
// In production, this would connect to the WebSocket server
const collaborationSessions = new Map<string, SpecCollaborationState>();

/**
 * Validates a spec ID to ensure it's safe
 */
function validateSpecId(specId: string): { valid: true; id: string } | { valid: false; error: string } {
  if (!specId || typeof specId !== 'string') {
    return { valid: false, error: 'Invalid spec ID' };
  }

  // Basic validation: should be alphanumeric with dashes
  if (!/^[a-zA-Z0-9-]+$/.test(specId)) {
    return { valid: false, error: 'Spec ID contains invalid characters' };
  }

  return { valid: true, id: specId };
}

/**
 * Get or create a collaboration session for a spec
 */
function getCollaborationSession(specId: string): SpecCollaborationState {
  if (!collaborationSessions.has(specId)) {
    collaborationSessions.set(specId, {
      spec_id: specId,
      comments: [],
      suggestions: [],
      presences: [],
      versions: [],
      is_connected: false,
      error: null
    });
  }
  return collaborationSessions.get(specId)!;
}

/**
 * Register all collaboration-related IPC handlers
 *
 * @param getMainWindow - Function to get the main BrowserWindow for sending events
 */
export function registerCollaborationHandlers(getMainWindow: () => BrowserWindow | null): void {
  // ============================================
  // WebSocket Connection Management
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_CONNECT,
    async (_, specId: string): Promise<IPCResult<{ connected: boolean }>> => {
      try {
        const validation = validateSpecId(specId);
        if (!validation.valid) {
          return { success: false, error: validation.error };
        }

        const session = getCollaborationSession(validation.id);
        session.is_connected = true;
        session.error = null;

        // Notify renderer process
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_CONNECTED, {
            spec_id: validation.id
          });
        }

        // TODO: Connect to actual WebSocket server when backend is implemented
        return { success: true, data: { connected: true } };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to connect to collaboration server'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_DISCONNECT,
    async (_, specId: string): Promise<IPCResult<void>> => {
      try {
        const validation = validateSpecId(specId);
        if (!validation.valid) {
          return { success: false, error: validation.error };
        }

        const session = getCollaborationSession(validation.id);
        session.is_connected = false;

        // Notify renderer process
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_DISCONNECTED, {
            spec_id: validation.id
          });
        }

        // TODO: Disconnect from actual WebSocket server when backend is implemented
        return { success: true, data: undefined };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to disconnect from collaboration server'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_GET_STATE,
    async (_, specId: string): Promise<IPCResult<SpecCollaborationState>> => {
      try {
        const validation = validateSpecId(specId);
        if (!validation.valid) {
          return { success: false, error: validation.error };
        }

        const session = getCollaborationSession(validation.id);
        return { success: true, data: session };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get collaboration state'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_UPDATE_CONTENT,
    async (_, specId: string, content: string): Promise<IPCResult<void>> => {
      try {
        const validation = validateSpecId(specId);
        if (!validation.valid) {
          return { success: false, error: validation.error };
        }

        // TODO: Send content update to WebSocket server via CRDT when backend is implemented
        // For now, just acknowledge success

        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_CONTENT_UPDATED, {
            spec_id: validation.id,
            content
          });
        }

        return { success: true, data: undefined };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to update content'
        };
      }
    }
  );

  // ============================================
  // Comment Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENTS_GET,
    async (_, specId: string): Promise<IPCResult<Comment[]>> => {
      try {
        const validation = validateSpecId(specId);
        if (!validation.valid) {
          return { success: false, error: validation.error };
        }

        const session = getCollaborationSession(validation.id);
        return { success: true, data: session.comments };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get comments'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENT_ADD,
    async (
      _,
      specId: string,
      sectionId: string | null,
      author: string,
      authorName: string,
      content: string,
      parentId: string | null
    ): Promise<IPCResult<Comment>> => {
      try {
        const validation = validateSpecId(specId);
        if (!validation.valid) {
          return { success: false, error: validation.error };
        }

        const session = getCollaborationSession(validation.id);
        const newComment: Comment = {
          id: `comment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          spec_id: validation.id,
          section_id: sectionId,
          author,
          author_name: authorName,
          content,
          parent_id: parentId,
          status: 'active',
          created_at: new Date(),
          updated_at: null,
          resolved_by: null,
          resolved_at: null
        };

        session.comments.push(newComment);

        // Notify renderer process
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_COMMENT_ADDED, newComment);
        }

        return { success: true, data: newComment };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to add comment'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENT_UPDATE,
    async (_, commentId: string, content: string): Promise<IPCResult<Comment>> => {
      try {
        // Find comment across all sessions
        for (const session of collaborationSessions.values()) {
          const comment = session.comments.find(c => c.id === commentId);
          if (comment) {
            comment.content = content;
            comment.updated_at = new Date();
            return { success: true, data: comment };
          }
        }

        return { success: false, error: 'Comment not found' };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to update comment'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENT_DELETE,
    async (_, commentId: string): Promise<IPCResult<void>> => {
      try {
        // Find and remove comment across all sessions
        for (const session of collaborationSessions.values()) {
          const index = session.comments.findIndex(c => c.id === commentId);
          if (index !== -1) {
            session.comments.splice(index, 1);
            return { success: true, data: undefined };
          }
        }

        return { success: false, error: 'Comment not found' };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to delete comment'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_COMMENT_RESOLVE,
    async (_, commentId: string, resolvedBy: string): Promise<IPCResult<Comment>> => {
      try {
        // Find comment across all sessions
        for (const session of collaborationSessions.values()) {
          const comment = session.comments.find(c => c.id === commentId);
          if (comment) {
            comment.status = 'resolved';
            comment.resolved_by = resolvedBy;
            comment.resolved_at = new Date();
            return { success: true, data: comment };
          }
        }

        return { success: false, error: 'Comment not found' };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to resolve comment'
        };
      }
    }
  );

  // ============================================
  // Suggestion Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_SUGGESTIONS_GET,
    async (_, specId: string): Promise<IPCResult<Suggestion[]>> => {
      try {
        const validation = validateSpecId(specId);
        if (!validation.valid) {
          return { success: false, error: validation.error };
        }

        const session = getCollaborationSession(validation.id);
        return { success: true, data: session.suggestions };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get suggestions'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_SUGGESTION_ADD,
    async (
      _,
      specId: string,
      sectionId: string | null,
      author: string,
      authorName: string,
      originalText: string,
      suggestedText: string,
      reason: string | null
    ): Promise<IPCResult<Suggestion>> => {
      try {
        const validation = validateSpecId(specId);
        if (!validation.valid) {
          return { success: false, error: validation.error };
        }

        const session = getCollaborationSession(validation.id);
        const newSuggestion: Suggestion = {
          id: `suggestion-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          spec_id: validation.id,
          section_id: sectionId,
          author,
          author_name: authorName,
          original_text: originalText,
          suggested_text: suggestedText,
          reason,
          status: 'pending',
          created_at: new Date(),
          reviewed_by: null,
          reviewed_at: null,
          review_comment: null
        };

        session.suggestions.push(newSuggestion);

        // Notify renderer process
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_SUGGESTION_ADDED, newSuggestion);
        }

        return { success: true, data: newSuggestion };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to add suggestion'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_SUGGESTION_ACCEPT,
    async (_, suggestionId: string, reviewedBy: string): Promise<IPCResult<Suggestion>> => {
      try {
        // Find suggestion across all sessions
        for (const session of collaborationSessions.values()) {
          const suggestion = session.suggestions.find(s => s.id === suggestionId);
          if (suggestion) {
            suggestion.status = 'accepted';
            suggestion.reviewed_by = reviewedBy;
            suggestion.reviewed_at = new Date();
            return { success: true, data: suggestion };
          }
        }

        return { success: false, error: 'Suggestion not found' };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to accept suggestion'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_SUGGESTION_REJECT,
    async (
      _,
      suggestionId: string,
      reviewedBy: string,
      reviewComment: string | null
    ): Promise<IPCResult<Suggestion>> => {
      try {
        // Find suggestion across all sessions
        for (const session of collaborationSessions.values()) {
          const suggestion = session.suggestions.find(s => s.id === suggestionId);
          if (suggestion) {
            suggestion.status = 'rejected';
            suggestion.reviewed_by = reviewedBy;
            suggestion.reviewed_at = new Date();
            suggestion.review_comment = reviewComment;
            return { success: true, data: suggestion };
          }
        }

        return { success: false, error: 'Suggestion not found' };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to reject suggestion'
        };
      }
    }
  );

  // ============================================
  // Presence Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_PRESENCE_GET,
    async (_, specId: string): Promise<IPCResult<Presence[]>> => {
      try {
        const validation = validateSpecId(specId);
        if (!validation.valid) {
          return { success: false, error: validation.error };
        }

        const session = getCollaborationSession(validation.id);
        return { success: true, data: session.presences };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get presence'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_PRESENCE_UPDATE,
    async (
      _,
      specId: string,
      userId: string,
      userName: string,
      presenceType: 'viewing' | 'editing' | 'idle',
      sectionId: string | null,
      cursorPosition: number | null
    ): Promise<IPCResult<Presence>> => {
      try {
        const validation = validateSpecId(specId);
        if (!validation.valid) {
          return { success: false, error: validation.error };
        }

        const session = getCollaborationSession(validation.id);

        // Update existing presence or add new one
        const existingIndex = session.presences.findIndex(p => p.user_id === userId);
        const presenceData: Presence = {
          spec_id: validation.id,
          user_id: userId,
          user_name: userName,
          presence_type: presenceType,
          section_id: sectionId,
          cursor_position: cursorPosition,
          last_seen: new Date()
        };

        if (existingIndex !== -1) {
          session.presences[existingIndex] = presenceData;
        } else {
          session.presences.push(presenceData);
        }

        // Notify renderer process
        const mainWindow = getMainWindow();
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.COLLABORATION_PRESENCE_UPDATED, presenceData);
        }

        return { success: true, data: presenceData };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to update presence'
        };
      }
    }
  );

  // ============================================
  // Version History Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_VERSIONS_GET,
    async (_, specId: string): Promise<IPCResult<Version[]>> => {
      try {
        const validation = validateSpecId(specId);
        if (!validation.valid) {
          return { success: false, error: validation.error };
        }

        const session = getCollaborationSession(validation.id);
        return { success: true, data: session.versions };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get versions'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_VERSION_DIFF,
    async (_, versionId: string): Promise<IPCResult<string>> => {
      try {
        // Find version across all sessions
        for (const session of collaborationSessions.values()) {
          const version = session.versions.find(v => v.id === versionId);
          if (version) {
            // TODO: Implement actual diff logic when backend is ready
            // For now, return the content as-is
            return { success: true, data: version.content };
          }
        }

        return { success: false, error: 'Version not found' };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get version diff'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.COLLABORATION_VERSION_APPROVE,
    async (_, versionId: string, approvedBy: string): Promise<IPCResult<Version>> => {
      try {
        // Find version across all sessions
        for (const session of collaborationSessions.values()) {
          const version = session.versions.find(v => v.id === versionId);
          if (version) {
            version.is_approved = true;
            version.approved_by = approvedBy;
            version.approved_at = new Date();
            return { success: true, data: version };
          }
        }

        return { success: false, error: 'Version not found' };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to approve version'
        };
      }
    }
  );
}
