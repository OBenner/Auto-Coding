/**
 * TaskList Page
 *
 * Displays all tasks from the backend in a grid layout.
 * Allows navigation to individual task details.
 */

import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { apiClient } from "../api/client";
import type { TaskSummary } from "../api/types";
import { PageErrorState, PageLoadingState } from "../components/PageStates";
import { TaskCard } from "../components/TaskCard";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import type { Task } from "../shared/types";

interface TaskListProps {
	onTaskClick: (taskId: string) => void;
	onCreateTask?: () => void;
}

export function TaskList({ onTaskClick, onCreateTask }: TaskListProps) {
	const { t } = useTranslation(["common"]);
	const [tasks, setTasks] = useState<Task[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [isRefreshing, setIsRefreshing] = useState(false);

	/**
	 * Convert API TaskSummary to frontend Task type
	 */
	const convertTaskSummary = useCallback((summary: TaskSummary): Task => {
		return {
			id: summary.number,
			specId: summary.number,
			title: summary.name,
			description: `Status: ${summary.status}`,
			status: "backlog", // Default status - will be updated with real data in future
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
				const convertedTasks = response.tasks.map(convertTaskSummary);
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

	if (isLoading) return <PageLoadingState />;
	if (error) return <PageErrorState error={error} onRetry={handleRefresh} />;

	// Empty state
	if (tasks.length === 0) {
		return (
			<div className="min-h-screen bg-gray-50">
				<div className="max-w-7xl mx-auto p-6">
					<div className="flex items-center justify-between mb-6">
						<h1 className="text-3xl font-bold text-gray-900">
							{t("common:tasks")}
						</h1>
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
					</div>

					<div className="flex items-center justify-center min-h-[400px]">
						<div className="text-center">
							<p className="text-lg text-gray-600 mb-2">No tasks found</p>
							<p className="text-sm text-gray-500">
								Tasks will appear here once you create specs
							</p>
						</div>
					</div>
				</div>
			</div>
		);
	}

	// Task list view
	return (
		<div className="min-h-screen bg-gray-50">
			<div className="max-w-7xl mx-auto p-6">
				{/* Header */}
				<div className="flex items-center justify-between mb-6">
					<div>
						<h1 className="text-3xl font-bold text-gray-900">
							{t("common:tasks")}
						</h1>
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

				{/* Task Grid */}
				<ScrollArea className="h-[calc(100vh-200px)]">
					<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
						{tasks.map((task) => (
							<TaskCard
								key={task.id}
								task={task}
								onClick={() => handleTaskClick(task)}
							/>
						))}
					</div>
				</ScrollArea>
			</div>
		</div>
	);
}
