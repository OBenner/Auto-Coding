/**
 * Session Replay Types
 *
 * Types for session recording, playback, and learning features.
 */

/**
 * Session metadata captured during task execution
 */
export interface SessionMetadata {
  /** Unique session identifier */
  session_id: string;
  /** When the session started */
  started_at: string;
  /** When the session completed (null if in progress) */
  completed_at: string | null;
  /** Session duration in seconds */
  duration_seconds: number | null;
  /** List of subtasks worked on in this session */
  subtasks: string[];
  /** Session number (1-based) */
  session_number: number;
}

/**
 * Filter state for session list
 */
export interface SessionFilterState {
  /** Search query for filtering sessions */
  searchQuery: string;
  /** Filter by session status (completed, in-progress) */
  status: SessionStatusFilter[];
}

/**
 * Session status filter options
 */
export type SessionStatusFilter = 'completed' | 'in-progress';

/**
 * Subtask transition between sessions
 */
export interface SubtaskTransition {
  /** Source subtask */
  from_subtask: string | null;
  /** Target subtask */
  to_subtask: string;
  /** When the transition occurred */
  timestamp: string;
  /** Session number */
  session: number;
}

/**
 * Bookmark for interesting moments in session
 */
export interface Bookmark {
  /** Unique bookmark identifier */
  id: string;
  /** When the bookmark was created */
  timestamp: string;
  /** Timestamp of the log entry this bookmark references */
  entry_timestamp: string;
  /** Phase where bookmark was created */
  phase: string;
  /** Bookmark label/title */
  label: string;
  /** Optional notes about the bookmark */
  note: string | null;
  /** Session identifier */
  session: string;
  /** Subtask ID where bookmark was created */
  subtask_id: string;
}

/**
 * Decision point with agent reasoning
 */
export interface DecisionPoint {
  /** Unique identifier */
  id: string;
  /** Timestamp of decision */
  timestamp: string;
  /** Phase where decision was made */
  phase: string;
  /** Subtask context */
  subtask: string;
  /** Decision reasoning */
  reasoning: string;
  /** Options considered */
  options_considered: string[];
  /** Chosen approach */
  chosen_approach: string;
  /** Expected outcome */
  expected_outcome: string;
}
