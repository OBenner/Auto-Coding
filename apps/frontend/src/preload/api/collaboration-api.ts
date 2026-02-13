import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type {
  IPCResult,
  Comment,
  Suggestion,
  Presence,
  Version,
  SpecCollaborationState
} from '../../shared/types';

export interface CollaborationAPI {
  // WebSocket Connection Management
  connect: (specId: string) => Promise<IPCResult<{ connected: boolean }>>;
  disconnect: (specId: string) => Promise<IPCResult<void>>;
  getState: (specId: string) => Promise<IPCResult<SpecCollaborationState>>;
  updateContent: (specId: string, content: string) => Promise<IPCResult<void>>;

  // Comment Operations
  getComments: (specId: string) => Promise<IPCResult<Comment[]>>;
  addComment: (
    specId: string,
    sectionId: string | null,
    author: string,
    authorName: string,
    content: string,
    parentId: string | null
  ) => Promise<IPCResult<Comment>>;
  updateComment: (commentId: string, content: string) => Promise<IPCResult<Comment>>;
  deleteComment: (commentId: string) => Promise<IPCResult<void>>;
  resolveComment: (commentId: string, resolvedBy: string) => Promise<IPCResult<Comment>>;

  // Suggestion Operations
  getSuggestions: (specId: string) => Promise<IPCResult<Suggestion[]>>;
  addSuggestion: (
    specId: string,
    sectionId: string | null,
    author: string,
    authorName: string,
    originalText: string,
    suggestedText: string,
    reason: string | null
  ) => Promise<IPCResult<Suggestion>>;
  acceptSuggestion: (suggestionId: string, reviewedBy: string) => Promise<IPCResult<Suggestion>>;
  rejectSuggestion: (
    suggestionId: string,
    reviewedBy: string,
    reviewComment: string | null
  ) => Promise<IPCResult<Suggestion>>;

  // Presence Operations
  getPresence: (specId: string) => Promise<IPCResult<Presence[]>>;
  updatePresence: (
    specId: string,
    userId: string,
    userName: string,
    presenceType: 'viewing' | 'editing' | 'idle',
    sectionId: string | null,
    cursorPosition: number | null
  ) => Promise<IPCResult<Presence>>;

  // Version History Operations
  getVersions: (specId: string) => Promise<IPCResult<Version[]>>;
  getVersionDiff: (versionId: string) => Promise<IPCResult<string>>;
  approveVersion: (versionId: string, approvedBy: string) => Promise<IPCResult<Version>>;
}

export const createCollaborationAPI = (): CollaborationAPI => ({
  // WebSocket Connection Management
  connect: (specId: string): Promise<IPCResult<{ connected: boolean }>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_CONNECT, specId),

  disconnect: (specId: string): Promise<IPCResult<void>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_DISCONNECT, specId),

  getState: (specId: string): Promise<IPCResult<SpecCollaborationState>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_GET_STATE, specId),

  updateContent: (specId: string, content: string): Promise<IPCResult<void>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_UPDATE_CONTENT, specId, content),

  // Comment Operations
  getComments: (specId: string): Promise<IPCResult<Comment[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_COMMENTS_GET, specId),

  addComment: (
    specId: string,
    sectionId: string | null,
    author: string,
    authorName: string,
    content: string,
    parentId: string | null
  ): Promise<IPCResult<Comment>> =>
    ipcRenderer.invoke(
      IPC_CHANNELS.COLLABORATION_COMMENT_ADD,
      specId,
      sectionId,
      author,
      authorName,
      content,
      parentId
    ),

  updateComment: (commentId: string, content: string): Promise<IPCResult<Comment>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_COMMENT_UPDATE, commentId, content),

  deleteComment: (commentId: string): Promise<IPCResult<void>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_COMMENT_DELETE, commentId),

  resolveComment: (commentId: string, resolvedBy: string): Promise<IPCResult<Comment>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_COMMENT_RESOLVE, commentId, resolvedBy),

  // Suggestion Operations
  getSuggestions: (specId: string): Promise<IPCResult<Suggestion[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_SUGGESTIONS_GET, specId),

  addSuggestion: (
    specId: string,
    sectionId: string | null,
    author: string,
    authorName: string,
    originalText: string,
    suggestedText: string,
    reason: string | null
  ): Promise<IPCResult<Suggestion>> =>
    ipcRenderer.invoke(
      IPC_CHANNELS.COLLABORATION_SUGGESTION_ADD,
      specId,
      sectionId,
      author,
      authorName,
      originalText,
      suggestedText,
      reason
    ),

  acceptSuggestion: (suggestionId: string, reviewedBy: string): Promise<IPCResult<Suggestion>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_SUGGESTION_ACCEPT, suggestionId, reviewedBy),

  rejectSuggestion: (
    suggestionId: string,
    reviewedBy: string,
    reviewComment: string | null
  ): Promise<IPCResult<Suggestion>> =>
    ipcRenderer.invoke(
      IPC_CHANNELS.COLLABORATION_SUGGESTION_REJECT,
      suggestionId,
      reviewedBy,
      reviewComment
    ),

  // Presence Operations
  getPresence: (specId: string): Promise<IPCResult<Presence[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_PRESENCE_GET, specId),

  updatePresence: (
    specId: string,
    userId: string,
    userName: string,
    presenceType: 'viewing' | 'editing' | 'idle',
    sectionId: string | null,
    cursorPosition: number | null
  ): Promise<IPCResult<Presence>> =>
    ipcRenderer.invoke(
      IPC_CHANNELS.COLLABORATION_PRESENCE_UPDATE,
      specId,
      userId,
      userName,
      presenceType,
      sectionId,
      cursorPosition
    ),

  // Version History Operations
  getVersions: (specId: string): Promise<IPCResult<Version[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_VERSIONS_GET, specId),

  getVersionDiff: (versionId: string): Promise<IPCResult<string>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_VERSION_DIFF, versionId),

  approveVersion: (versionId: string, approvedBy: string): Promise<IPCResult<Version>> =>
    ipcRenderer.invoke(IPC_CHANNELS.COLLABORATION_VERSION_APPROVE, versionId, approvedBy)
});
