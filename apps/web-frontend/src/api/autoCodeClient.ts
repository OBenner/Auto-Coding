/**
 * REST adapter for the shared UI's AutoCodeClient port (U1).
 *
 * `libs/ui` is transport-agnostic: its screens consume tasks through the
 * injected AutoCodeClient. This adapter maps the web backend's task/spec
 * listing (`GET /api/tasks`) into the shared `UiTask` shape.
 */

import type {
	AutoCodeClient,
	TaskStatus,
	UiTask,
	UiTaskDetail,
} from "@auto-code/ui";
import type { TaskDetail, TaskListResponse, TaskSummary } from "./types";

/** The slice of ApiClient this adapter needs (keeps it unit-testable). */
export interface TasksSource {
	listTasks(): Promise<TaskListResponse>;
	getTask(taskId: string): Promise<TaskDetail>;
}

/** Map the backend's free-form spec status onto the shared closed set. */
export function mapStatus(status: string): TaskStatus {
	// list_specs suffixes built specs with " (has build)" — strip decorations
	// before matching, or "in_progress (has build)" would land in Draft.
	// Plain string ops, no regex: Sonar S8786 flags `\s*(...)$` backtracking.
	let normalized = (status ?? "").trim();
	const suffix = "(has build)";
	if (normalized.toLowerCase().endsWith(suffix)) {
		normalized = normalized.slice(0, -suffix.length).trimEnd();
	}
	switch (normalized) {
		case "complete":
			return "done";
		case "in_progress":
			return "running";
		// The web backend doesn't emit review states yet; map the family
		// defensively so future statuses land in the Review column.
		case "review":
		case "ai_review":
		case "human_review":
			return "review";
		default:
			// initialized / pending / anything unknown starts in Draft.
			return "draft";
	}
}

/** Parse the "3/7" progress string into 0-100, or undefined when unknown. */
export function parseProgress(progress: string): number | undefined {
	const match = /^(\d+)\s*\/\s*(\d+)$/.exec(progress ?? "");
	if (!match) return undefined;
	const done = Number(match[1]);
	const total = Number(match[2]);
	if (!Number.isFinite(done) || !Number.isFinite(total) || total <= 0) {
		return undefined;
	}
	return Math.round((done / total) * 100);
}

export function mapTaskSummaryToUiTask(task: TaskSummary): UiTask {
	return {
		// The folder name is the canonical spec id (works with /tasks/:id too).
		id: task.folder,
		title: task.name,
		status: mapStatus(task.status),
		progress: parseProgress(task.progress),
	};
}

export function mapTaskDetailToUiTaskDetail(detail: TaskDetail): UiTaskDetail {
	const breakdown = detail.progress;
	return {
		id: detail.folder,
		title: detail.name,
		status: mapStatus(detail.status),
		specContent: detail.spec_content ?? undefined,
		progressBreakdown:
			breakdown != null
				? {
						completed: breakdown.completed,
						inProgress: breakdown.in_progress,
						pending: breakdown.pending,
						failed: breakdown.failed,
						total: breakdown.total,
					}
				: undefined,
	};
}

/** REST-backed AutoCodeClient over the existing ApiClient. */
export function createRestAutoCodeClient(source: TasksSource): AutoCodeClient {
	return {
		async listTasks(): Promise<UiTask[]> {
			const response = await source.listTasks();
			return (response.tasks ?? []).map(mapTaskSummaryToUiTask);
		},
		async getTask(id: string): Promise<UiTaskDetail> {
			const detail = await source.getTask(id);
			return mapTaskDetailToUiTaskDetail(detail);
		},
	};
}
