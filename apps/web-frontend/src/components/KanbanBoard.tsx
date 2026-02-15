/**
 * KanbanBoard Component (Web Version)
 *
 * A drag-and-drop Kanban board for visualizing and managing tasks.
 * Adapted from the Electron frontend with simplified features for web.
 */

import {
	closestCorners,
	DndContext,
	type DragEndEvent,
	type DragOverEvent,
	DragOverlay,
	type DragStartEvent,
	KeyboardSensor,
	PointerSensor,
	useDroppable,
	useSensor,
	useSensors,
} from "@dnd-kit/core";
import {
	SortableContext,
	sortableKeyboardCoordinates,
	verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import {
	CheckCircle2,
	Eye,
	Inbox,
	Loader2,
	Plus,
	RefreshCw,
} from "lucide-react";
import { memo, useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "../lib/utils";
import { TASK_STATUS_COLUMNS, TASK_STATUS_LABELS } from "../shared/constants";
import type { Task, TaskStatus } from "../shared/types";
import { SortableTaskCard } from "./SortableTaskCard";
import { TaskCard } from "./TaskCard";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";

// Type guard for valid drop column targets
const VALID_DROP_COLUMNS = new Set<string>(TASK_STATUS_COLUMNS);
function isValidDropColumn(
	id: string,
): id is (typeof TASK_STATUS_COLUMNS)[number] {
	return VALID_DROP_COLUMNS.has(id);
}

/**
 * Get the visual column for a task status.
 * pr_created tasks are displayed in the 'done' column.
 * error tasks are displayed in the 'human_review' column.
 */
function getVisualColumn(
	status: TaskStatus,
): (typeof TASK_STATUS_COLUMNS)[number] {
	if (status === "pr_created") return "done";
	if (status === "error") return "human_review";
	return status as (typeof TASK_STATUS_COLUMNS)[number];
}

interface KanbanBoardProps {
	tasks: Task[];
	onTaskClick: (task: Task) => void;
	onNewTaskClick?: () => void;
	onRefresh?: () => void;
	isRefreshing?: boolean;
	onStatusChange?: (taskId: string, newStatus: TaskStatus) => void;
}

interface DroppableColumnProps {
	status: TaskStatus;
	tasks: Task[];
	onTaskClick: (task: Task) => void;
	isOver: boolean;
	onAddClick?: () => void;
	isLoading?: boolean;
}

// Empty state content for each column
const getEmptyStateContent = (
	status: TaskStatus,
): { icon: React.ReactNode; message: string; subtext?: string } => {
	switch (status) {
		case "backlog":
			return {
				icon: <Inbox className="h-6 w-6 text-gray-400" />,
				message: "No tasks in backlog",
				subtext: "Create a task to get started",
			};
		case "queue":
			return {
				icon: <Loader2 className="h-6 w-6 text-gray-400" />,
				message: "Queue is empty",
				subtext: "Drag tasks here to queue them",
			};
		case "in_progress":
			return {
				icon: <Loader2 className="h-6 w-6 text-gray-400" />,
				message: "No tasks in progress",
				subtext: "Tasks will appear here when running",
			};
		case "ai_review":
			return {
				icon: <Eye className="h-6 w-6 text-gray-400" />,
				message: "No AI review needed",
				subtext: "Tasks pending AI review appear here",
			};
		case "human_review":
			return {
				icon: <Eye className="h-6 w-6 text-gray-400" />,
				message: "No human review needed",
				subtext: "Tasks ready for your review appear here",
			};
		case "done":
			return {
				icon: <CheckCircle2 className="h-6 w-6 text-gray-400" />,
				message: "No completed tasks",
				subtext: "Completed tasks will appear here",
			};
		default:
			return {
				icon: <Inbox className="h-6 w-6 text-gray-400" />,
				message: "No tasks",
			};
	}
};

// Column color mapping
const getColumnBorderColor = (status: TaskStatus): string => {
	switch (status) {
		case "backlog":
			return "border-t-gray-400";
		case "queue":
			return "border-t-cyan-500";
		case "in_progress":
			return "border-t-blue-500";
		case "ai_review":
			return "border-t-purple-500";
		case "human_review":
			return "border-t-amber-500";
		case "done":
			return "border-t-green-500";
		default:
			return "border-t-gray-400";
	}
};

/**
 * DroppableColumn - A single column in the Kanban board
 */
const DroppableColumn = memo(function DroppableColumn({
	status,
	tasks,
	onTaskClick,
	isOver,
	onAddClick,
	isLoading,
}: DroppableColumnProps) {
	const { setNodeRef } = useDroppable({
		id: status,
	});

	const taskIds = useMemo(() => tasks.map((t) => t.id), [tasks]);
	const emptyState = getEmptyStateContent(status);

	return (
		<div
			ref={setNodeRef}
			className={cn(
				"flex flex-col min-w-[280px] max-w-[320px] rounded-lg border bg-gray-50 transition-all duration-200",
				getColumnBorderColor(status),
				"border-t-4",
				isOver && "ring-2 ring-blue-500 ring-opacity-50 bg-blue-50",
			)}
		>
			{/* Column header */}
			<div className="flex items-center justify-between p-4 border-b border-gray-200">
				<div className="flex items-center gap-2">
					<h2 className="font-semibold text-sm text-gray-900">
						{TASK_STATUS_LABELS[status] || status}
					</h2>
					<span className="inline-flex items-center justify-center h-5 min-w-[20px] px-1.5 text-xs font-medium rounded-full bg-gray-200 text-gray-700">
						{tasks.length}
					</span>
				</div>
				{status === "backlog" && onAddClick && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7 hover:bg-gray-200"
						onClick={onAddClick}
						aria-label="Add new task"
					>
						<Plus className="h-4 w-4" />
					</Button>
				)}
			</div>

			{/* Task list */}
			<div className="flex-1 min-h-0 overflow-hidden">
				<ScrollArea className="h-full p-3">
					<SortableContext
						items={taskIds}
						strategy={verticalListSortingStrategy}
					>
						<div className="space-y-3 min-h-[100px]">
							{isLoading ? (
								<div className="flex items-center justify-center py-8">
									<Loader2 className="h-6 w-6 animate-spin text-gray-400" />
								</div>
							) : tasks.length === 0 ? (
								<div
									className={cn(
										"flex flex-col items-center justify-center py-8 text-center",
										isOver && "bg-blue-100/50 rounded-lg",
									)}
								>
									{isOver ? (
										<>
											<div className="h-8 w-8 rounded-full bg-blue-200 flex items-center justify-center mb-2">
												<Plus className="h-4 w-4 text-blue-600" />
											</div>
											<span className="text-sm font-medium text-blue-600">
												Drop here
											</span>
										</>
									) : (
										<>
											{emptyState.icon}
											<span className="mt-2 text-sm font-medium text-gray-500">
												{emptyState.message}
											</span>
											{emptyState.subtext && (
												<span className="mt-0.5 text-xs text-gray-400">
													{emptyState.subtext}
												</span>
											)}
										</>
									)}
								</div>
							) : (
								tasks.map((task) => (
									<SortableTaskCard
										key={task.id}
										task={task}
										onClick={() => onTaskClick(task)}
									/>
								))
							)}
						</div>
					</SortableContext>
				</ScrollArea>
			</div>
		</div>
	);
});

/**
 * KanbanBoard - Main component for the Kanban view
 */
export function KanbanBoard({
	tasks,
	onTaskClick,
	onNewTaskClick,
	onRefresh,
	isRefreshing,
	onStatusChange,
}: KanbanBoardProps) {
	useTranslation(["common"]);
	const [activeTask, setActiveTask] = useState<Task | null>(null);
	const [overColumnId, setOverColumnId] = useState<string | null>(null);

	const sensors = useSensors(
		useSensor(PointerSensor, {
			activationConstraint: {
				distance: 8, // 8px movement required before drag starts
			},
		}),
		useSensor(KeyboardSensor, {
			coordinateGetter: sortableKeyboardCoordinates,
		}),
	);

	// Group tasks by status column
	const tasksByStatus = useMemo(() => {
		const grouped: Record<(typeof TASK_STATUS_COLUMNS)[number], Task[]> = {
			backlog: [],
			queue: [],
			in_progress: [],
			ai_review: [],
			human_review: [],
			done: [],
		};

		for (const task of tasks) {
			const targetColumn = getVisualColumn(task.status);
			if (grouped[targetColumn]) {
				grouped[targetColumn].push(task);
			}
		}

		// Sort tasks within each column by updatedAt (newest first)
		for (const status of Object.keys(grouped) as Array<keyof typeof grouped>) {
			grouped[status].sort((a, b) => {
				const dateA = new Date(a.updatedAt).getTime();
				const dateB = new Date(b.updatedAt).getTime();
				return dateB - dateA;
			});
		}

		return grouped;
	}, [tasks]);

	const handleDragStart = useCallback(
		(event: DragStartEvent) => {
			const { active } = event;
			const task = tasks.find((t) => t.id === active.id);
			if (task) {
				setActiveTask(task);
			}
		},
		[tasks],
	);

	const handleDragOver = useCallback(
		(event: DragOverEvent) => {
			const { over } = event;

			if (!over) {
				setOverColumnId(null);
				return;
			}

			const overId = over.id as string;

			// Check if over a column
			if (isValidDropColumn(overId)) {
				setOverColumnId(overId);
				return;
			}

			// Check if over a task - get its column
			const overTask = tasks.find((t) => t.id === overId);
			if (overTask) {
				setOverColumnId(getVisualColumn(overTask.status));
			}
		},
		[tasks],
	);

	const handleDragEnd = useCallback(
		(event: DragEndEvent) => {
			const { active, over } = event;
			setActiveTask(null);
			setOverColumnId(null);

			if (!over || !onStatusChange) return;

			const activeTaskId = active.id as string;
			const overId = over.id as string;

			// Get the task being dragged
			const task = tasks.find((t) => t.id === activeTaskId);
			if (!task) return;

			let newStatus: TaskStatus | null = null;

			// Check if dropped on a column
			if (isValidDropColumn(overId)) {
				newStatus = overId;
			} else {
				// Check if dropped on another task
				const overTask = tasks.find((t) => t.id === overId);
				if (overTask) {
					const taskVisualColumn = getVisualColumn(task.status);
					const overTaskVisualColumn = getVisualColumn(overTask.status);

					// If different columns, change status
					if (taskVisualColumn !== overTaskVisualColumn) {
						newStatus = overTask.status;
					}
				}
			}

			// Only trigger status change if it's actually different
			if (newStatus && newStatus !== task.status) {
				onStatusChange(activeTaskId, newStatus);
			}
		},
		[tasks, onStatusChange],
	);

	return (
		<div className="flex h-full flex-col">
			{/* Header */}
			{onRefresh && (
				<div className="flex items-center justify-end px-6 pt-4 pb-2">
					<Button
						variant="outline"
						size="sm"
						onClick={onRefresh}
						disabled={isRefreshing}
						className="gap-2"
					>
						<RefreshCw
							className={cn("h-4 w-4", isRefreshing && "animate-spin")}
						/>
						{isRefreshing ? "Refreshing..." : "Refresh"}
					</Button>
				</div>
			)}

			{/* Kanban columns */}
			<DndContext
				sensors={sensors}
				collisionDetection={closestCorners}
				onDragStart={handleDragStart}
				onDragOver={handleDragOver}
				onDragEnd={handleDragEnd}
			>
				<div className="flex flex-1 gap-4 overflow-x-auto p-6">
					{TASK_STATUS_COLUMNS.map((status) => (
						<DroppableColumn
							key={status}
							status={status}
							tasks={tasksByStatus[status]}
							onTaskClick={onTaskClick}
							isOver={overColumnId === status}
							onAddClick={status === "backlog" ? onNewTaskClick : undefined}
							isLoading={isRefreshing}
						/>
					))}
				</div>

				{/* Drag overlay - shows the card being dragged */}
				<DragOverlay>
					{activeTask ? (
						<div className="opacity-90 shadow-lg">
							<TaskCard task={activeTask} onClick={() => undefined} />
						</div>
					) : null}
				</DragOverlay>
			</DndContext>
		</div>
	);
}
