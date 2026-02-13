/**
 * AI Decision Explainability types
 */

/**
 * Types of decisions made by AI agents
 */
export type DecisionType =
  | 'approach'           // Overall approach to solving a problem
  | 'implementation'     // Specific implementation choice
  | 'tool_selection'     // Which tool to use
  | 'file_modification'  // How to modify files
  | 'error_recovery'     // How to recover from errors
  | 'architecture'       // Architectural decisions
  | 'optimization'       // Performance/quality optimizations
  | 'other';             // Other decision types

/**
 * Confidence levels for decisions
 */
export type ConfidenceLevel =
  | 'very_low'   // < 40%
  | 'low'        // 40-60%
  | 'medium'     // 60-80%
  | 'high'       // 80-95%
  | 'very_high'; // > 95%

/**
 * An alternative approach that was considered but not chosen
 */
export interface Alternative {
  description: string;           // Description of the alternative
  reasoning: string;             // Why this alternative was considered
  rejected_reason: string;       // Why it was not chosen
  confidence_impact?: string;    // How this would affect confidence
  tradeoffs?: string[];          // Known tradeoffs of this approach
}

/**
 * A decision point made by the AI agent
 */
export interface DecisionPoint {
  timestamp: string;             // When the decision was made
  decision_type: DecisionType;   // Type of decision
  context: string;               // What problem/situation led to this decision
  chosen_approach: string;       // The approach that was chosen
  reasoning: string;             // Why this approach was chosen
  confidence: number;            // Confidence score (0.0 - 1.0)
  confidence_level: ConfidenceLevel; // Human-readable confidence level
  phase: string;                 // Which phase this decision was made in
  subtask_id?: string;           // Associated subtask if applicable
  session?: number;              // Session number
  alternatives?: Alternative[];  // Alternatives considered
  requires_review?: boolean;     // Flag for uncertain decisions
  reasoning_chain?: string[];    // Step-by-step reasoning
  impact?: string;               // Expected impact of this decision
  reversible?: boolean;          // Whether this decision can be easily reversed
  dependencies?: string[];       // What this decision depends on
  metadata?: Record<string, any>; // Additional metadata
}

/**
 * Summary statistics for decisions
 */
export interface DecisionStats {
  total: number;
  by_type: Record<DecisionType, number>;
  by_confidence: Record<ConfidenceLevel, number>;
  needs_review: number;
  average_confidence: number;
}

/**
 * Filter options for decision queries
 */
export interface DecisionFilter {
  decision_type?: DecisionType;
  min_confidence?: number;
  max_confidence?: number;
  requires_review?: boolean;
  phase?: string;
  subtask_id?: string;
}
