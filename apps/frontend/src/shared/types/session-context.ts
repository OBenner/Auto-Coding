/**
 * Session context types for conversation history tracking
 */

/**
 * A single round of conversation (user message + assistant response)
 */
export interface ConversationRound {
  /** Sequential round number within session */
  round_number: number;
  /** When this round started (ISO timestamp) */
  timestamp: string;
  /** Execution phase (planning, coding, validation) */
  phase: string;
  /** The prompt/query sent to the agent */
  user_message: string;
  /** The complete text response from the agent */
  assistant_response: string;
  /** List of tools called during this round */
  tool_calls: Array<{ name: string; input: Record<string, unknown> }>;
  /** List of file paths referenced in this round */
  code_references: string[];
  /** Number of input tokens used */
  input_tokens: number;
  /** Number of output tokens used */
  output_tokens: number;
}

/**
 * Complete conversation history for a session
 */
export interface ConversationHistory {
  /** Unique session identifier */
  session_id: string;
  /** Optional subtask identifier */
  subtask_id: string | null;
  /** When the session started (ISO timestamp) */
  session_start: string;
  /** All conversation rounds in this session */
  rounds: ConversationRound[];
  /** Total input tokens across all rounds */
  total_input_tokens: number;
  /** Total output tokens across all rounds */
  total_output_tokens: number;
  /** All unique file paths referenced in the session */
  all_code_references: string[];
}

/**
 * High-level session context summary
 */
export interface SessionContextSummary {
  /** Unique session identifier */
  session_id: string;
  /** Optional subtask identifier */
  subtask_id: string | null;
  /** When the session started (ISO timestamp) */
  session_start: string;
  /** Total number of conversation rounds */
  total_rounds: number;
  /** Total input tokens */
  total_input_tokens: number;
  /** Total output tokens */
  total_output_tokens: number;
  /** Code references from this session */
  code_references: string[];
}

/**
 * Optimized context window for task execution
 */
export interface OptimizedContext {
  /** Most recent conversation rounds (for continuity) */
  recent_rounds: ConversationRound[];
  /** Top relevant rounds from history (for context) */
  relevant_rounds: ConversationRound[];
  /** All code references from selected rounds */
  code_references: string[];
  /** Number of recent rounds included */
  total_recent: number;
  /** Number of relevant rounds included */
  total_relevant: number;
  /** Total rounds in optimized context */
  total_rounds: number;
  /** Query used for relevance matching */
  query: string;
}
