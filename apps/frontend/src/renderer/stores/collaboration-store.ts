import { create } from 'zustand';
import type {
  Comment,
  Suggestion,
  Presence,
  Version,
  CommentStatus,
  SuggestionStatus,
  PresenceType,
  WebSocketConnectionState
} from '../../shared/types';
import { debugLog } from '../../shared/utils/debug-logger';

interface CollaborationState {
  // Data organized by spec_id
  commentsBySpec: Record<string, Comment[]>;
  suggestionsBySpec: Record<string, Suggestion[]>;
  presencesBySpec: Record<string, Presence[]>;
  versionsBySpec: Record<string, Version[]>;

  // WebSocket connection state
  connectionState: WebSocketConnectionState;
  currentSpecId: string | null;
  error: string | null;
  isLoading: boolean;

  // Actions - Comments
  setComments: (specId: string, comments: Comment[]) => void;
  addComment: (specId: string, comment: Comment) => void;
  updateComment: (specId: string, commentId: string, updates: Partial<Comment>) => void;
  deleteComment: (specId: string, commentId: string) => void;
  resolveComment: (specId: string, commentId: string, resolvedBy: string) => void;

  // Actions - Suggestions
  setSuggestions: (specId: string, suggestions: Suggestion[]) => void;
  addSuggestion: (specId: string, suggestion: Suggestion) => void;
  updateSuggestion: (specId: string, suggestionId: string, updates: Partial<Suggestion>) => void;
  acceptSuggestion: (specId: string, suggestionId: string, reviewedBy: string, reviewComment?: string) => void;
  rejectSuggestion: (specId: string, suggestionId: string, reviewedBy: string, reviewComment?: string) => void;
  deleteSuggestion: (specId: string, suggestionId: string) => void;

  // Actions - Presence
  setPresences: (specId: string, presences: Presence[]) => void;
  updatePresence: (specId: string, presence: Presence) => void;
  removePresence: (specId: string, userId: string) => void;
  clearPresences: (specId: string) => void;

  // Actions - Versions
  setVersions: (specId: string, versions: Version[]) => void;
  addVersion: (specId: string, version: Version) => void;
  approveVersion: (specId: string, versionId: string, approvedBy: string) => void;

  // Actions - WebSocket
  setConnectionState: (state: WebSocketConnectionState) => void;
  setCurrentSpec: (specId: string | null) => void;
  setError: (error: string | null) => void;
  setLoading: (loading: boolean) => void;

  // Actions - Bulk operations
  clearSpecData: (specId: string) => void;
  clearAllData: () => void;

  // Selectors
  getComments: (specId: string) => Comment[];
  getSuggestions: (specId: string) => Suggestion[];
  getPresences: (specId: string) => Presence[];
  getVersions: (specId: string) => Version[];
  getActiveUsers: (specId: string) => Presence[];
  getUnresolvedComments: (specId: string) => Comment[];
  getPendingSuggestions: (specId: string) => Suggestion[];
}

/**
 * Helper to find comment index by id in an array
 * Returns -1 if not found
 */
function findCommentIndex(comments: Comment[], commentId: string): number {
  return comments.findIndex((c) => c.id === commentId);
}

/**
 * Helper to find suggestion index by id in an array
 * Returns -1 if not found
 */
function findSuggestionIndex(suggestions: Suggestion[], suggestionId: string): number {
  return suggestions.findIndex((s) => s.id === suggestionId);
}

/**
 * Helper to find presence index by user_id in an array
 * Returns -1 if not found
 */
function findPresenceIndex(presences: Presence[], userId: string): number {
  return presences.findIndex((p) => p.user_id === userId);
}

/**
 * Check if presence is stale (no recent activity)
 */
function isPresenceStale(presence: Presence, timeoutSeconds: number = 60): boolean {
  const elapsed = (Date.now() - presence.last_seen.getTime()) / 1000;
  return elapsed > timeoutSeconds;
}

export const useCollaborationStore = create<CollaborationState>((set, get) => ({
  // Initial state
  commentsBySpec: {},
  suggestionsBySpec: {},
  presencesBySpec: {},
  versionsBySpec: {},
  connectionState: 'disconnected',
  currentSpecId: null,
  error: null,
  isLoading: false,

  // Comment actions
  setComments: (specId, comments) =>
    set((state) => ({
      commentsBySpec: {
        ...state.commentsBySpec,
        [specId]: comments
      }
    })),

  addComment: (specId, comment) =>
    set((state) => {
      const existingComments = state.commentsBySpec[specId] || [];
      return {
        commentsBySpec: {
          ...state.commentsBySpec,
          [specId]: [...existingComments, comment]
        }
      };
    }),

  updateComment: (specId, commentId, updates) =>
    set((state) => {
      const comments = state.commentsBySpec[specId] || [];
      const index = findCommentIndex(comments, commentId);
      if (index === -1) {
        debugLog('[updateComment] Comment not found:', { specId, commentId });
        return state;
      }

      const updatedComments = [...comments];
      updatedComments[index] = {
        ...updatedComments[index],
        ...updates,
        updated_at: updates.updated_at !== undefined ? updates.updated_at : new Date()
      };

      return {
        commentsBySpec: {
          ...state.commentsBySpec,
          [specId]: updatedComments
        }
      };
    }),

  deleteComment: (specId, commentId) =>
    set((state) => {
      const comments = state.commentsBySpec[specId] || [];
      return {
        commentsBySpec: {
          ...state.commentsBySpec,
          [specId]: comments.filter((c) => c.id !== commentId)
        }
      };
    }),

  resolveComment: (specId, commentId, resolvedBy) =>
    set((state) => {
      const comments = state.commentsBySpec[specId] || [];
      const index = findCommentIndex(comments, commentId);
      if (index === -1) return state;

      const updatedComments = [...comments];
      updatedComments[index] = {
        ...updatedComments[index],
        status: 'resolved' as CommentStatus,
        resolved_by: resolvedBy,
        resolved_at: new Date()
      };

      return {
        commentsBySpec: {
          ...state.commentsBySpec,
          [specId]: updatedComments
        }
      };
    }),

  // Suggestion actions
  setSuggestions: (specId, suggestions) =>
    set((state) => ({
      suggestionsBySpec: {
        ...state.suggestionsBySpec,
        [specId]: suggestions
      }
    })),

  addSuggestion: (specId, suggestion) =>
    set((state) => {
      const existingSuggestions = state.suggestionsBySpec[specId] || [];
      return {
        suggestionsBySpec: {
          ...state.suggestionsBySpec,
          [specId]: [...existingSuggestions, suggestion]
        }
      };
    }),

  updateSuggestion: (specId, suggestionId, updates) =>
    set((state) => {
      const suggestions = state.suggestionsBySpec[specId] || [];
      const index = findSuggestionIndex(suggestions, suggestionId);
      if (index === -1) {
        debugLog('[updateSuggestion] Suggestion not found:', { specId, suggestionId });
        return state;
      }

      const updatedSuggestions = [...suggestions];
      updatedSuggestions[index] = { ...updatedSuggestions[index], ...updates };

      return {
        suggestionsBySpec: {
          ...state.suggestionsBySpec,
          [specId]: updatedSuggestions
        }
      };
    }),

  acceptSuggestion: (specId, suggestionId, reviewedBy, reviewComment) =>
    set((state) => {
      const suggestions = state.suggestionsBySpec[specId] || [];
      const index = findSuggestionIndex(suggestions, suggestionId);
      if (index === -1) return state;

      const updatedSuggestions = [...suggestions];
      updatedSuggestions[index] = {
        ...updatedSuggestions[index],
        status: 'accepted' as SuggestionStatus,
        reviewed_by: reviewedBy,
        reviewed_at: new Date(),
        review_comment: reviewComment || null
      };

      return {
        suggestionsBySpec: {
          ...state.suggestionsBySpec,
          [specId]: updatedSuggestions
        }
      };
    }),

  rejectSuggestion: (specId, suggestionId, reviewedBy, reviewComment) =>
    set((state) => {
      const suggestions = state.suggestionsBySpec[specId] || [];
      const index = findSuggestionIndex(suggestions, suggestionId);
      if (index === -1) return state;

      const updatedSuggestions = [...suggestions];
      updatedSuggestions[index] = {
        ...updatedSuggestions[index],
        status: 'rejected' as SuggestionStatus,
        reviewed_by: reviewedBy,
        reviewed_at: new Date(),
        review_comment: reviewComment || null
      };

      return {
        suggestionsBySpec: {
          ...state.suggestionsBySpec,
          [specId]: updatedSuggestions
        }
      };
    }),

  deleteSuggestion: (specId, suggestionId) =>
    set((state) => {
      const suggestions = state.suggestionsBySpec[specId] || [];
      return {
        suggestionsBySpec: {
          ...state.suggestionsBySpec,
          [specId]: suggestions.filter((s) => s.id !== suggestionId)
        }
      };
    }),

  // Presence actions
  setPresences: (specId, presences) =>
    set((state) => ({
      presencesBySpec: {
        ...state.presencesBySpec,
        [specId]: presences.filter((p) => !isPresenceStale(p))
      }
    })),

  updatePresence: (specId, presence) =>
    set((state) => {
      const presences = state.presencesBySpec[specId] || [];
      const index = findPresenceIndex(presences, presence.user_id);

      let updatedPresences: Presence[];
      if (index === -1) {
        // Add new presence
        updatedPresences = [...presences, presence];
      } else {
        // Update existing presence
        updatedPresences = [...presences];
        updatedPresences[index] = presence;
      }

      // Remove stale presences
      updatedPresences = updatedPresences.filter((p) => !isPresenceStale(p));

      return {
        presencesBySpec: {
          ...state.presencesBySpec,
          [specId]: updatedPresences
        }
      };
    }),

  removePresence: (specId, userId) =>
    set((state) => {
      const presences = state.presencesBySpec[specId] || [];
      return {
        presencesBySpec: {
          ...state.presencesBySpec,
          [specId]: presences.filter((p) => p.user_id !== userId)
        }
      };
    }),

  clearPresences: (specId) =>
    set((state) => ({
      presencesBySpec: {
        ...state.presencesBySpec,
        [specId]: []
      }
    })),

  // Version actions
  setVersions: (specId, versions) =>
    set((state) => ({
      versionsBySpec: {
        ...state.versionsBySpec,
        [specId]: versions.sort((a, b) => b.version_number - a.version_number) // Newest first
      }
    })),

  addVersion: (specId, version) =>
    set((state) => {
      const existingVersions = state.versionsBySpec[specId] || [];
      const updatedVersions = [...existingVersions, version]
        .sort((a, b) => b.version_number - a.version_number); // Newest first

      return {
        versionsBySpec: {
          ...state.versionsBySpec,
          [specId]: updatedVersions
        }
      };
    }),

  approveVersion: (specId, versionId, approvedBy) =>
    set((state) => {
      const versions = state.versionsBySpec[specId] || [];
      const index = versions.findIndex((v) => v.id === versionId);
      if (index === -1) return state;

      const updatedVersions = [...versions];
      updatedVersions[index] = {
        ...updatedVersions[index],
        is_approved: true,
        approved_by: approvedBy,
        approved_at: new Date()
      };

      return {
        versionsBySpec: {
          ...state.versionsBySpec,
          [specId]: updatedVersions
        }
      };
    }),

  // WebSocket connection actions
  setConnectionState: (connectionState) => set({ connectionState }),

  setCurrentSpec: (specId) => set({ currentSpecId: specId }),

  setError: (error) => set({ error }),

  setLoading: (isLoading) => set({ isLoading }),

  // Bulk operations
  clearSpecData: (specId) =>
    set((state) => ({
      commentsBySpec: Object.fromEntries(
        Object.entries(state.commentsBySpec).filter(([key]) => key !== specId)
      ),
      suggestionsBySpec: Object.fromEntries(
        Object.entries(state.suggestionsBySpec).filter(([key]) => key !== specId)
      ),
      presencesBySpec: Object.fromEntries(
        Object.entries(state.presencesBySpec).filter(([key]) => key !== specId)
      ),
      versionsBySpec: Object.fromEntries(
        Object.entries(state.versionsBySpec).filter(([key]) => key !== specId)
      )
    })),

  clearAllData: () => ({
    commentsBySpec: {},
    suggestionsBySpec: {},
    presencesBySpec: {},
    versionsBySpec: {},
    connectionState: 'disconnected',
    currentSpecId: null,
    error: null
  }),

  // Selectors
  getComments: (specId) => {
    const state = get();
    return state.commentsBySpec[specId] || [];
  },

  getSuggestions: (specId) => {
    const state = get();
    return state.suggestionsBySpec[specId] || [];
  },

  getPresences: (specId) => {
    const state = get();
    return state.presencesBySpec[specId] || [];
  },

  getVersions: (specId) => {
    const state = get();
    return state.versionsBySpec[specId] || [];
  },

  getActiveUsers: (specId) => {
    const state = get();
    const presences = state.presencesBySpec[specId] || [];
    // Filter out idle users and stale presences
    return presences.filter(
      (p) => p.presence_type !== 'idle' && !isPresenceStale(p)
    );
  },

  getUnresolvedComments: (specId) => {
    const state = get();
    const comments = state.commentsBySpec[specId] || [];
    return comments.filter((c) => c.status === 'active');
  },

  getPendingSuggestions: (specId) => {
    const state = get();
    const suggestions = state.suggestionsBySpec[specId] || [];
    return suggestions.filter((s) => s.status === 'pending');
  }
}));
