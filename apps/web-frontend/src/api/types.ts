/**
 * API Type Definitions
 *
 * TypeScript types matching the backend Pydantic models.
 * These types ensure type safety when communicating with the Auto Code web backend.
 */

// ============================================
// TASK/SPEC TYPES
// ============================================

export interface TaskStatus {
  status: string;
  progress: string;
  has_build: boolean;
}

export interface TaskSummary {
  number: string;
  name: string;
  folder: string;
  status: string;
  progress: string;
  has_build: boolean;
}

export interface TaskProgressDetail {
  completed: number;
  in_progress: number;
  pending: number;
  failed: number;
  total: number;
  percentage: number;
}

export interface TaskDetail {
  number: string;
  name: string;
  folder: string;
  status: string;
  progress: TaskProgressDetail;
  has_build: boolean;
  spec_content?: string;
}

export interface TaskListResponse {
  tasks: TaskSummary[];
  total: number;
}

// Spec types (aliases for task types)
export type SpecStatus = TaskStatus;
export type SpecSummary = TaskSummary;
export type SpecProgressDetail = TaskProgressDetail;
export type SpecDetail = TaskDetail;

export interface SpecListResponse {
  specs: SpecSummary[];
  total: number;
}

// ============================================
// AGENT TYPES
// ============================================

export type AgentType = "planner" | "coder" | "qa_reviewer" | "qa_fixer";

export interface AgentRunRequest {
  spec_id: string;
  agent_type: AgentType;
  model?: string;
  verbose?: boolean;
}

export interface AgentRunResponse {
  task_id: string;
  spec_id: string;
  agent_type: string;
  status: "started" | "error";
  message: string;
}

export interface AgentStatusResponse {
  task_id: string;
  status: "running" | "completed" | "failed" | "not_found";
  result?: Record<string, unknown>;
  error?: string;
}

export interface AgentCancelResponse {
  task_id: string;
  cancelled: boolean;
  message: string;
}

// ============================================
// WEBSOCKET EVENT TYPES
// ============================================

export type ExecutionPhase =
  | "idle"
  | "planning"
  | "coding"
  | "qa_review"
  | "qa_fixing"
  | "complete"
  | "failed";

export type IdeationPhase =
  | "idle"
  | "analyzing"
  | "discovering"
  | "generating"
  | "finalizing"
  | "complete"
  | "error";

export type RoadmapPhase =
  | "idle"
  | "analyzing"
  | "discovering"
  | "generating"
  | "complete"
  | "error";

export interface ProgressData {
  completed: number;
  total: number;
  percentage: number;
}

export interface ExecutionProgressData {
  phase: ExecutionPhase;
  phase_progress: number;
  overall_progress: number;
  message?: string;
  current_subtask?: string;
}

export interface IdeationProgressData {
  phase: IdeationPhase;
  progress: number;
  message?: string;
  completed_types: number;
  total_types: number;
}

export interface RoadmapProgressData {
  phase: RoadmapPhase;
  progress: number;
  message?: string;
}

export type EventType = "execution" | "ideation" | "roadmap" | "log" | "error" | "pair_suggestion" | "pair_session" | "pair_voice" | "pair_action";

export interface BaseAgentEvent {
  event_type: EventType;
  timestamp: string;
  spec_id: string;
  data?: unknown;
}

export interface ExecutionEvent extends BaseAgentEvent {
  event_type: "execution";
  data: ExecutionProgressData;
}

export interface IdeationEvent extends BaseAgentEvent {
  event_type: "ideation";
  data: IdeationProgressData;
}

export interface RoadmapEvent extends BaseAgentEvent {
  event_type: "roadmap";
  data: RoadmapProgressData;
}

export interface LogEvent extends BaseAgentEvent {
  event_type: "log";
  log_line: string;
  level: "debug" | "info" | "warning" | "error";
}

export interface ErrorEvent extends BaseAgentEvent {
  event_type: "error";
  error_message: string;
  error_type?: string;
  traceback?: string;
}

export interface SuggestionData {
  suggestion: string;
  context?: string;
  confidence?: number;
}

export interface SuggestionEvent extends BaseAgentEvent {
  event_type: "pair_suggestion";
  data: SuggestionData;
}

export type AgentEvent =
  | ExecutionEvent
  | IdeationEvent
  | RoadmapEvent
  | LogEvent
  | ErrorEvent
  | SuggestionEvent;

export interface PhaseEvent {
  phase: string;
  message?: string;
  subtask?: string;
  progress?: number;
}

// ============================================
// WEBSOCKET MESSAGE TYPES
// ============================================

export type WebSocketAction = "subscribe" | "unsubscribe" | "ping";

export interface WebSocketMessage {
  action: WebSocketAction;
  spec_id?: string;
}

// ============================================
// API ERROR TYPES
// ============================================

export interface ApiError {
  detail: string;
  status?: number;
}

// ============================================
// CONFIGURATION TYPES
// ============================================

export interface ApiConfig {
  baseUrl: string;
  wsUrl: string;
  timeout?: number;
  debug?: boolean;
}
