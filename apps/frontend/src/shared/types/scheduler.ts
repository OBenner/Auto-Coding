/**
 * Scheduler-related types
 */

/**
 * Priority levels for scheduled builds
 */
export type SchedulePriority = 'critical' | 'high' | 'normal' | 'low' | 'background';

/**
 * Status of a scheduled build
 */
export type BuildStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'retrying';

/**
 * Scheduled build configuration
 */
export interface ScheduledBuild {
  id: string;
  spec_id: string;
  spec_name: string;
  scheduled_time: string | null;  // ISO datetime string or null for immediate
  priority: SchedulePriority;
  status: BuildStatus;
  dependencies: string[];  // List of spec IDs
  created_at: string;  // ISO datetime string
  updated_at: string;  // ISO datetime string
  started_at: string | null;
  completed_at: string | null;
  retry_count: number;
  max_retries: number;
  error_message: string | null;
  notification_config: Record<string, unknown>;
  metadata: Record<string, unknown>;

  // Computed properties
  duration_seconds?: number | null;
}

/**
 * Scheduler status summary
 * Note: Uses camelCase since this is constructed by the frontend handler,
 * unlike ScheduledBuild which uses snake_case to match Python backend JSON.
 */
export interface SchedulerStatus {
  schedulerRunning: boolean;
  totalBuilds: number;
  byStatus: Record<BuildStatus, number>;
  builds: ScheduledBuild[];
  nextBuild: ScheduledBuild | null;
}

/**
 * Schedule build options
 */
export interface ScheduleBuildOptions {
  taskId: string;
  scheduledTime?: string;  // ISO format or natural language like "tonight 10pm"
  priority?: SchedulePriority;
  dependencies?: string[];  // Task IDs that must complete first
}

/**
 * Calendar event for scheduled builds
 */
export interface CalendarEvent {
  id: string;
  taskId: string;
  title: string;
  start: Date;
  end: Date | null;
  status: BuildStatus;
  priority: SchedulePriority;
  allDay?: boolean;
}

/**
 * Queue item with dependency info
 */
export interface QueueItem extends ScheduledBuild {
  blocking_tasks: string[];  // Tasks this build is blocking
  blocked_by: string[];  // Tasks blocking this build
  estimated_wait_minutes?: number;
}

/**
 * Scheduler configuration
 */
export interface SchedulerConfig {
  enabled: boolean;
  max_parallel_builds: number;
  default_priority: SchedulePriority;
  notification_enabled: boolean;
  auto_retry_enabled: boolean;
  max_retries: number;
  working_hours?: {
    start: string;  // HH:MM format
    end: string;    // HH:MM format
    days: number[]; // 0-6 (Sunday-Saturday)
  };
}
