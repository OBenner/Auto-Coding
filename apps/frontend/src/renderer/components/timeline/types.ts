/**
 * Timeline-specific types for visual build timeline component
 *
 * Timeline visualization showing agent phases, subtasks, and their relationships
 * with real-time progress updates, zoom/pan controls, and export functionality.
 */

import type {
  ImplementationPlan,
  Phase,
  PlanSubtask,
  ExecutionProgress,
  SubtaskStatus,
  ExecutionPhase,
} from '../../../shared/types';

/**
 * Timeline phase data with layout and rendering information
 */
export interface TimelinePhase extends Phase {
  /** Display index in timeline (0-based) */
  displayIndex: number;
  /** Phase agent type for color-coding */
  agentType: TimelineAgentType;
  /** Calculated layout for this phase */
  layout: PhaseLayout;
  /** Current execution progress for this phase */
  progress?: PhaseProgressData;
}

/**
 * Agent type for color-coding phases
 */
export type TimelineAgentType = 'planner' | 'coder' | 'qa';

/**
 * Timeline subtask with position and time tracking
 */
export interface TimelineSubtask extends PlanSubtask {
  /** Phase this subtask belongs to */
  phaseId: string;
  /** Display position within phase (0-based) */
  displayIndex: number;
  /** Calculated layout for this subtask */
  layout: SubtaskLayout;
  /** Estimated time in seconds (from plan) */
  estimatedTime?: number;
  /** Actual elapsed time in seconds */
  actualTime?: number;
  /** Files associated with this subtask */
  files?: string[];
  /** Subtask dependencies (other subtask IDs) */
  dependsOn?: string[];
}

/**
 * Layout dimensions and position for a phase swim lane
 */
export interface PhaseLayout {
  /** Y position in pixels */
  y: number;
  /** Height in pixels */
  height: number;
  /** Width in pixels (entire phase width) */
  width: number;
  /** Total width including subtasks */
  totalWidth: number;
}

/**
 * Layout dimensions and position for a subtask block
 */
export interface SubtaskLayout {
  /** X position relative to phase start (pixels) */
  x: number;
  /** Y position relative to phase start (pixels) */
  y: number;
  /** Width in pixels */
  width: number;
  /** Height in pixels */
  height: number;
  /** Z-index for rendering order */
  zIndex: number;
}

/**
 * Progress data for a phase
 */
export interface PhaseProgressData {
  /** Current phase execution status */
  status: ExecutionPhase;
  /** Progress percentage (0-100) */
  progress: number;
  /** Currently executing subtask ID */
  currentSubtaskId?: string;
  /** Number of completed subtasks */
  completedCount: number;
  /** Total number of subtasks */
  totalCount: number;
}

/**
 * Timeline view state for zoom and pan
 */
export interface TimelineViewState {
  /** Zoom level (0.5 = 50%, 1 = 100%, 2 = 200%) */
  zoom: number;
  /** Horizontal scroll position (pixels) */
  scrollX: number;
  /** Vertical scroll position (pixels) */
  scrollY: number;
  /** Whether user is currently dragging */
  isDragging: boolean;
  /** Drag start position */
  dragStart?: { x: number; y: number };
}

/**
 * Timeline data combined from implementation plan and execution progress
 */
export interface TimelineData {
  /** Implementation plan phases and subtasks */
  phases: TimelinePhase[];
  /** Flattened list of all subtasks with dependencies */
  subtasks: TimelineSubtask[];
  /** Current execution progress */
  executionProgress?: ExecutionProgress;
  /** Timeline metadata */
  metadata: TimelineMetadata;
}

/**
 * Timeline metadata and statistics
 */
export interface TimelineMetadata {
  /** Total estimated time for all subtasks (seconds) */
  totalEstimatedTime: number;
  /** Total actual elapsed time (seconds) */
  totalActualTime: number;
  /** Number of completed subtasks */
  completedSubtasks: number;
  /** Total number of subtasks */
  totalSubtasks: number;
  /** Overall progress percentage (0-100) */
  overallProgress: number;
  /** Timeline created at timestamp */
  createdAt: Date;
  /** Timeline last updated timestamp */
  updatedAt: Date;
}

/**
 * Dependency connection between subtasks or phases
 */
export interface TimelineDependency {
  /** Source subtask/phase ID */
  fromId: string;
  /** Target subtask/phase ID */
  toId: string;
  /** Type of dependency */
  type: 'phase' | 'subtask';
  /** SVG path for rendering the connection */
  path?: string;
  /** Connection line color */
  color?: string;
}

/**
 * Export options for timeline snapshot
 */
export interface TimelineExportOptions {
  /** Export format */
  format: 'png' | 'svg';
  /** Scale factor for high-DPI displays (default: 2) */
  scale?: number;
  /** Background color (default: transparent) */
  backgroundColor?: string;
  /** Include expanded subtask details */
  includeDetails?: boolean;
  /** Filename for exported image */
  filename?: string;
}

/**
 * Timeline event types for real-time updates
 */
export type TimelineEventType =
  | 'subtask_started'
  | 'subtask_completed'
  | 'subtask_failed'
  | 'phase_started'
  | 'phase_completed'
  | 'phase_failed'
  | 'timeline_updated';

/**
 * Timeline event for real-time updates
 */
export interface TimelineEvent {
  /** Event type */
  type: TimelineEventType;
  /** Subtask ID (if applicable) */
  subtaskId?: string;
  /** Phase ID (if applicable) */
  phaseId?: string;
  /** Previous status */
  previousStatus?: SubtaskStatus;
  /** New status */
  newStatus?: SubtaskStatus;
  /** Event timestamp */
  timestamp: Date;
}

/**
 * Animation state for timeline components
 */
export interface TimelineAnimationState {
  /** Whether animations are currently enabled */
  isEnabled: boolean;
  /** Whether timeline is currently visible (IntersectionObserver) */
  isVisible: boolean;
}

/**
 * Timeline configuration options
 */
export interface TimelineConfig {
  /** Default zoom level */
  defaultZoom: number;
  /** Minimum zoom level */
  minZoom: number;
  /** Maximum zoom level */
  maxZoom: number;
  /** Phase swim lane height (pixels) */
  phaseHeight: number;
  /** Subtask block height (pixels) */
  subtaskHeight: number;
  /** Subtask block minimum width (pixels) */
  minSubtaskWidth: number;
  /** Horizontal spacing between subtasks (pixels) */
  subtaskSpacing: number;
  /** Whether animations are enabled */
  enableAnimations: boolean;
  /** Whether to show dependency lines */
  showDependencies: boolean;
  /** Whether to show time estimates */
  showTimeEstimates: boolean;
}

/**
 * Phase color scheme for timeline rendering
 */
export interface PhaseColorScheme {
  /** Primary color (e.g., for subtask blocks) */
  primary: string;
  /** Background color (e.g., for swim lanes) */
  background: string;
  /** Border color */
  border: string;
  /** Text color */
  text: string;
}

/**
 * Color schemes for different agent types
 */
export type TimelineColorScheme = Record<TimelineAgentType, PhaseColorScheme> & {
  /** Colors for inactive/pending states */
  inactive: PhaseColorScheme;
  /** Colors for error states */
  error: PhaseColorScheme;
};

/**
 * Default timeline configuration
 */
export const DEFAULT_TIMELINE_CONFIG: TimelineConfig = {
  defaultZoom: 1,
  minZoom: 0.5,
  maxZoom: 2,
  phaseHeight: 120,
  subtaskHeight: 60,
  minSubtaskWidth: 150,
  subtaskSpacing: 8,
  enableAnimations: true,
  showDependencies: true,
  showTimeEstimates: true,
};

/**
 * Default color scheme for timeline phases
 * Matches PhaseProgressIndicator colors for consistency
 */
export const DEFAULT_TIMELINE_COLORS: TimelineColorScheme = {
  planner: {
    primary: 'bg-amber-500',
    background: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-600 dark:text-amber-400',
  },
  coder: {
    primary: 'bg-info',
    background: 'bg-info/10',
    border: 'border-info/30',
    text: 'text-info',
  },
  qa: {
    primary: 'bg-purple-500',
    background: 'bg-purple-500/10',
    border: 'border-purple-500/30',
    text: 'text-purple-600 dark:text-purple-400',
  },
  inactive: {
    primary: 'bg-muted-foreground',
    background: 'bg-muted',
    border: 'border-border',
    text: 'text-muted-foreground',
  },
  error: {
    primary: 'bg-destructive',
    background: 'bg-destructive/10',
    border: 'border-destructive/30',
    text: 'text-destructive',
  },
};

/**
 * Props for timeline components
 */
export interface TimelineComponentProps {
  /** Timeline data */
  timelineData: TimelineData;
  /** View state */
  viewState: TimelineViewState;
  /** Timeline configuration */
  config?: TimelineConfig;
  /** Color scheme */
  colors?: TimelineColorScheme;
  /** Animation state */
  animationState?: TimelineAnimationState;
  /** Event handlers */
  onSubtaskClick?: (subtask: TimelineSubtask) => void;
  onPhaseClick?: (phase: TimelinePhase) => void;
  onZoomChange?: (zoom: number) => void;
  onScrollChange?: (scrollX: number, scrollY: number) => void;
  onExport?: (options: TimelineExportOptions) => void;
}
