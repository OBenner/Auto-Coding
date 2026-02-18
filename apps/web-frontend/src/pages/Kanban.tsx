/**
 * Kanban Page
 *
 * Displays tasks in a Kanban board view with drag-and-drop functionality.
 */

import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "../api/client";
import type { TaskSummary } from "../api/types";
import { KanbanBoard } from "../components/KanbanBoard";
import { PageErrorState, PageLoadingState } from "../components/PageStates";
import { Button } from "../components/ui/button";
import type { Task, TaskStatus } from "../shared/types";

interface KanbanPageProps {
	onTaskClick: (taskId: string) => void;
	onCreateTask?: () => void;
}

export function Kanban({ onTaskClick, onCreateTask }: KanbanPageProps) {
	const [tasks, setTasks] = useState<Task[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [isRefreshing, setIsRefreshing] = useState(false);

	/**
	 * Convert API TaskSummary to frontend Task type with status mapping
	 */
	const convertTaskSummary = useCallback((summary: TaskSummary): Task => {
		// Map API status to kanban status
		let status: TaskStatus = "backlog";
		const apiStatus = summary.status?.toLowerCase() || "";

		if (apiStatus.includes("done") || apiStatus.includes("complete")) {
			status = "done";
		} else if (
			apiStatus.includes("progress") ||
			apiStatus.includes("running")
		) {
			status = "in_progress";
		} else if (apiStatus.includes("review")) {
			status = "human_review";
		} else if (apiStatus.includes("queue")) {
			status = "queue";
		}

		return {
			id: summary.number,
			specId: summary.number,
			title: summary.name,
			description: summary.status || "No description",
			status,
			subtasks: [],
			createdAt: new Date(),
			updatedAt: new Date(),
			metadata: {},
		};
	}, []);

	/**
	 * Fetch tasks from the API
	 */
	const fetchTasks = useCallback(
		async (showRefreshIndicator = false) => {
			try {
				if (showRefreshIndicator) {
					setIsRefreshing(true);
				} else {
					setIsLoading(true);
				}
				setError(null);

				const response = await apiClient.listTasks();
				const convertedTasks = response.tasks.map((t) => convertTaskSummary(t));
				setTasks(convertedTasks);
			} catch (err) {
				const message =
					err instanceof Error ? err.message : "Failed to load tasks";
				setError(message);
			} finally {
				setIsLoading(false);
				setIsRefreshing(false);
			}
		},
		[convertTaskSummary],
	);

	// Initial load
	useEffect(() => {
		fetchTasks();
	}, [fetchTasks]);

	// Handle refresh button click
	const handleRefresh = useCallback(() => {
		fetchTasks(true);
	}, [fetchTasks]);

	// Handle task card click
	const handleTaskClick = useCallback(
		(task: Task) => {
			onTaskClick(task.id);
		},
		[onTaskClick],
	);

	// Handle status change from drag-and-drop
	const handleStatusChange = useCallback(
		(taskId: string, newStatus: TaskStatus) => {
			// Optimistic update - update local state immediately
			setTasks((prevTasks) =>
				prevTasks.map((task) =>
					task.id === taskId ? { ...task, status: newStatus } : task,
				),
			);

			// In a real implementation, this would make an API call to persist the change
			// For now, we just update the local state
		},
		[],
	);

	if (isLoading) return <PageLoadingState />;
	if (error) return <PageErrorState error={error} onRetry={handleRefresh} />;

	// Kanban view
	return (
		<div className="min-h-screen bg-gray-100">
			<div className="h-screen flex flex-col">
				{/* Header */}
				<div className="bg-white border-b border-gray-200 px-6 py-4">
					<div className="flex items-center justify-between">
						<div>
							<h1 className="text-2xl font-bold text-gray-900">Kanban Board</h1>
							<p className="text-sm text-gray-600 mt-1">
								{tasks.length} {tasks.length === 1 ? "task" : "tasks"} total
							</p>
						</div>
						<div className="flex gap-2">
							<Button
								onClick={handleRefresh}
								disabled={isRefreshing}
								variant="outline"
							>
								<RefreshCw
									className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`}
								/>
								Refresh
							</Button>
							{onCreateTask && (
								<Button
									onClick={onCreateTask}
									className="bg-gradient-to-br from-blue-500 to-purple-600 hover:opacity-90"
								>
									Create Task
								</Button>
							)}
						</div>
					</div>
				</div>

				{/* Kanban Board */}
				<div className="flex-1 overflow-hidden">
					<KanbanBoard
						tasks={tasks}
						onTaskClick={handleTaskClick}
						onNewTaskClick={onCreateTask}
						onRefresh={handleRefresh}
						isRefreshing={isRefreshing}
						onStatusChange={handleStatusChange}
					/>
				</div>
			</div>
		</div>
	);
}
