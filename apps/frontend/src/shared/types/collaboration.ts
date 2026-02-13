/**
 * Collaboration types for real-time spec editing
 * Types for comments, suggestions, presence, and version history
 */

/**
 * Status of a comment
 */
export type CommentStatus = 'active' | 'resolved' | 'archived';

/**
 * Status of a suggestion
 */
export type SuggestionStatus = 'pending' | 'accepted' | 'rejected';

/**
 * Type of user presence
 */
export type PresenceType = 'viewing' | 'editing' | 'idle';

/**
 * A comment on a spec section for threaded discussions
 */
export interface Comment {
  id: string;
  spec_id: string;
  section_id: string | null;
  author: string;
  author_name: string;
  content: string;
  parent_id: string | null;
  status: CommentStatus;
  created_at: Date;
  updated_at: Date | null;
  resolved_by: string | null;
  resolved_at: Date | null;
}

/**
 * A suggested change to a spec without direct editing
 */
export interface Suggestion {
  id: string;
  spec_id: string;
  section_id: string | null;
  author: string;
  author_name: string;
  original_text: string;
  suggested_text: string;
  reason: string | null;
  status: SuggestionStatus;
  created_at: Date;
  reviewed_by: string | null;
  reviewed_at: Date | null;
  review_comment: string | null;
}

/**
 * Real-time presence indicator for users viewing/editing a spec
 */
export interface Presence {
  spec_id: string;
  user_id: string;
  user_name: string;
  presence_type: PresenceType;
  section_id: string | null;
  cursor_position: number | null;
  last_seen: Date;
}

/**
 * A version of a spec for change tracking and history
 */
export interface Version {
  id: string;
  spec_id: string;
  version_number: number;
  author: string;
  author_name: string;
  content: string;
  commit_message: string | null;
  previous_version_id: string | null;
  created_at: Date;
  is_approved: boolean;
  approved_by: string | null;
  approved_at: Date | null;
}

/**
 * WebSocket connection state
 */
export type WebSocketConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

/**
 * Collaboration state for a spec
 */
export interface SpecCollaborationState {
  spec_id: string;
  comments: Comment[];
  suggestions: Suggestion[];
  presences: Presence[];
  versions: Version[];
  is_connected: boolean;
  error: string | null;
}
