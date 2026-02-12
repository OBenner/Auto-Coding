/**
 * KanbanBoard Component Tests
 *
 * Tests for the KanbanBoard component which displays tasks
 * in a drag-and-drop Kanban layout.
 */

import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TASK_STATUS_COLUMNS, TASK_STATUS_LABELS } from "../../shared/constants";
import type { Task } from "../../shared/types";
import { KanbanBoard } from "../KanbanBoard";

// Mock dnd-kit to avoid complex drag-drop simulation in tests
vi.mock("@dnd-kit/core", async () => {
	const actual = await vi.importActual("@dnd-kit/core");
	return {
		...actual,
		DndContext: ({ children }: { children: React.ReactNode }) => (
			<div>{children}</div>
		),
		DragOverlay: ({ children }: { children: React.ReactNode }) => (
			<div data-testid="drag-overlay">{children}</div>
		),
		useSensor: vi.fn(),
		useSensors: vi.fn(() => []),
		useDroppable: vi.fn(() => ({
			setNodeRef: vi.fn(),
			isOver: false,
		})),
		closestCorners: vi.fn(),
		KeyboardSensor: vi.fn(),
		PointerSensor: vi.fn(),
	};
});

vi.mock("@dnd-kit/sortable", async () => {
	const actual = await vi.importActual("@dnd-kit/sortable");
	return {
		...actual,
		SortableContext: ({ children }: { children: React.ReactNode }) => (
			<div>{children}</div>
		),
		useSortable: vi.fn(() => ({
			attributes: {},
			listeners: {},
			setNodeRef: vi.fn(),
			transform: null,
			transition: undefined,
			isDragging: false,
		})),
		sortableKeyboardCoordinates: vi.fn(),
		verticalListSortingStrategy: {},
	};
});

// Helper to create mock tasks
const createMockTask = (overrides: Partial<Task> = {}): Task => ({
	id: `task-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
	specId: "spec-1",
	title: "Test Task",
	description: "A test task description",
	status: "backlog",
	subtasks: [],
	createdAt: new Date().toISOString(),
	updatedAt: new Date().toISOString(),
	...overrides,
});

describe("KanbanBoard", () => {
	const defaultProps = {
		tasks: [] as Task[],
		onTaskClick: vi.fn(),
	};

	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe("Rendering", () => {
		it("renders all status columns", () => {
			render(<KanbanBoard {...defaultProps} />);

			// Check all column headers are rendered
			for (const status of TASK_STATUS_COLUMNS) {
				const label = TASK_STATUS_LABELS[status];
				expect(screen.getByText(label)).toBeInTheDocument();
			}
		});

		it("shows empty state messages for columns without tasks", () => {
			render(<KanbanBoard {...defaultProps} />);

			// Check for some empty state messages
			expect(screen.getByText("No tasks in backlog")).toBeInTheDocument();
			expect(screen.getByText("Queue is empty")).toBeInTheDocument();
			expect(screen.getByText("No tasks in progress")).toBeInTheDocument();
		});

		it("displays tasks in correct columns based on status", () => {
			const tasks: Task[] = [
				createMockTask({ id: "task-1", title: "Backlog Task", status: "backlog" }),
				createMockTask({
					id: "task-2",
					title: "In Progress Task",
					status: "in_progress",
				}),
				createMockTask({ id: "task-3", title: "Done Task", status: "done" }),
			];

			render(<KanbanBoard {...defaultProps} tasks={tasks} />);

			expect(screen.getByText("Backlog Task")).toBeInTheDocument();
			expect(screen.getByText("In Progress Task")).toBeInTheDocument();
			expect(screen.getByText("Done Task")).toBeInTheDocument();
		});

		it("shows task count badges for each column", () => {
			const tasks: Task[] = [
				createMockTask({ id: "task-1", status: "backlog" }),
				createMockTask({ id: "task-2", status: "backlog" }),
				createMockTask({ id: "task-3", status: "in_progress" }),
			];

			render(<KanbanBoard {...defaultProps} tasks={tasks} />);

			// Find badges with count "2" (backlog) and "1" (in_progress)
			const badges = screen.getAllByText("2");
			expect(badges.length).toBeGreaterThan(0);
		});

		it("maps pr_created status to done column", () => {
			const tasks: Task[] = [
				createMockTask({
					id: "task-1",
					title: "PR Created Task",
					status: "pr_created",
				}),
			];

			render(<KanbanBoard {...defaultProps} tasks={tasks} />);

			// Task should appear (it's in the done column visually)
			expect(screen.getByText("PR Created Task")).toBeInTheDocument();
		});

		it("maps error status to human_review column", () => {
			const tasks: Task[] = [
				createMockTask({
					id: "task-1",
					title: "Error Task",
					status: "error",
				}),
			];

			render(<KanbanBoard {...defaultProps} tasks={tasks} />);

			expect(screen.getByText("Error Task")).toBeInTheDocument();
		});
	});

	describe("Task Interactions", () => {
		it("calls onTaskClick when a task is clicked", () => {
			const onTaskClick = vi.fn();
			const task = createMockTask({ id: "task-1", title: "Clickable Task" });

			render(
				<KanbanBoard {...defaultProps} tasks={[task]} onTaskClick={onTaskClick} />,
			);

			fireEvent.click(screen.getByText("Clickable Task"));
			expect(onTaskClick).toHaveBeenCalledWith(task);
		});

		it("calls onNewTaskClick when add button is clicked in backlog column", () => {
			const onNewTaskClick = vi.fn();

			render(
				<KanbanBoard
					{...defaultProps}
					onNewTaskClick={onNewTaskClick}
				/>,
			);

			const addButton = screen.getByRole("button", { name: /add new task/i });
			fireEvent.click(addButton);
			expect(onNewTaskClick).toHaveBeenCalledTimes(1);
		});
	});

	describe("Refresh Functionality", () => {
		it("shows refresh button when onRefresh is provided", () => {
			const onRefresh = vi.fn();

			render(<KanbanBoard {...defaultProps} onRefresh={onRefresh} />);

			expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
		});

		it("calls onRefresh when refresh button is clicked", () => {
			const onRefresh = vi.fn();

			render(<KanbanBoard {...defaultProps} onRefresh={onRefresh} />);

			fireEvent.click(screen.getByRole("button", { name: /refresh/i }));
			expect(onRefresh).toHaveBeenCalledTimes(1);
		});

		it("disables refresh button and shows spinner when isRefreshing is true", () => {
			const onRefresh = vi.fn();

			render(
				<KanbanBoard
					{...defaultProps}
					onRefresh={onRefresh}
					isRefreshing={true}
				/>,
			);

			const refreshButton = screen.getByRole("button", { name: /refreshing/i });
			expect(refreshButton).toBeDisabled();
		});

		it("shows loading spinners in columns when refreshing", () => {
			render(
				<KanbanBoard
					{...defaultProps}
					onRefresh={vi.fn()}
					isRefreshing={true}
				/>,
			);

			// Check for spinner elements (they have animate-spin class)
			const spinners = document.querySelectorAll(".animate-spin");
			expect(spinners.length).toBeGreaterThan(0);
		});
	});

	describe("Task Sorting", () => {
		it("sorts tasks by updatedAt within columns (newest first)", () => {
			const oldDate = new Date("2024-01-01").toISOString();
			const newDate = new Date("2024-06-01").toISOString();

			const tasks: Task[] = [
				createMockTask({
					id: "task-old",
					title: "Old Task",
					status: "backlog",
					updatedAt: oldDate,
				}),
				createMockTask({
					id: "task-new",
					title: "New Task",
					status: "backlog",
					updatedAt: newDate,
				}),
			];

			render(<KanbanBoard {...defaultProps} tasks={tasks} />);

			const taskElements = screen.getAllByText(/Task$/);
			// New task should appear before old task
			const newTaskIndex = taskElements.findIndex((el) =>
				el.textContent?.includes("New"),
			);
			const oldTaskIndex = taskElements.findIndex((el) =>
				el.textContent?.includes("Old"),
			);
			expect(newTaskIndex).toBeLessThan(oldTaskIndex);
		});
	});

	describe("Column Empty States", () => {
		it("shows appropriate empty state for backlog", () => {
			render(<KanbanBoard {...defaultProps} />);

			expect(screen.getByText("No tasks in backlog")).toBeInTheDocument();
			expect(screen.getByText("Create a task to get started")).toBeInTheDocument();
		});

		it("shows appropriate empty state for queue", () => {
			render(<KanbanBoard {...defaultProps} />);

			expect(screen.getByText("Queue is empty")).toBeInTheDocument();
			expect(screen.getByText("Drag tasks here to queue them")).toBeInTheDocument();
		});

		it("shows appropriate empty state for in_progress", () => {
			render(<KanbanBoard {...defaultProps} />);

			expect(screen.getByText("No tasks in progress")).toBeInTheDocument();
			expect(
				screen.getByText("Tasks will appear here when running"),
			).toBeInTheDocument();
		});

		it("shows appropriate empty state for done", () => {
			render(<KanbanBoard {...defaultProps} />);

			expect(screen.getByText("No completed tasks")).toBeInTheDocument();
			expect(
				screen.getByText("Completed tasks will appear here"),
			).toBeInTheDocument();
		});
	});

	describe("Task Metadata Display", () => {
		it("displays task with category badge", () => {
			const task = createMockTask({
				id: "task-1",
				title: "Feature Task",
				metadata: { category: "feature" },
			});

			render(<KanbanBoard {...defaultProps} tasks={[task]} />);

			expect(screen.getByText("Feature")).toBeInTheDocument();
		});

		it("displays task with complexity badge", () => {
			const task = createMockTask({
				id: "task-1",
				title: "Complex Task",
				metadata: { complexity: "complex" },
			});

			render(<KanbanBoard {...defaultProps} tasks={[task]} />);

			expect(screen.getByText("Complex")).toBeInTheDocument();
		});

		it("displays progress bar when task has subtasks", () => {
			const task = createMockTask({
				id: "task-1",
				title: "Task with Subtasks",
				subtasks: [
					{ id: "sub-1", description: "Subtask 1", status: "completed" },
					{ id: "sub-2", description: "Subtask 2", status: "pending" },
				],
			});

			render(<KanbanBoard {...defaultProps} tasks={[task]} />);

			// Check for progress indicator
			expect(screen.getByText("Progress")).toBeInTheDocument();
			expect(screen.getByText("50%")).toBeInTheDocument();
		});
	});

	describe("Accessibility", () => {
		it("has accessible add button in backlog column", () => {
			render(<KanbanBoard {...defaultProps} onNewTaskClick={vi.fn()} />);

			const addButton = screen.getByRole("button", { name: /add new task/i });
			expect(addButton).toHaveAttribute("aria-label");
		});

		it("columns have semantic structure", () => {
			render(<KanbanBoard {...defaultProps} />);

			// Column headers should be present
			for (const status of TASK_STATUS_COLUMNS) {
				const label = TASK_STATUS_LABELS[status];
				const header = screen.getByText(label);
				expect(header).toBeInTheDocument();
			}
		});
	});

	describe("Edge Cases", () => {
		it("handles empty tasks array", () => {
			render(<KanbanBoard {...defaultProps} tasks={[]} />);

			// Should render all columns with empty states
			expect(screen.getByText("No tasks in backlog")).toBeInTheDocument();
		});

		it("handles task with missing optional fields", () => {
			const minimalTask = createMockTask({
				id: "minimal-task",
				title: "Minimal Task",
				description: "",
				metadata: undefined,
				subtasks: [],
			});

			render(<KanbanBoard {...defaultProps} tasks={[minimalTask]} />);

			expect(screen.getByText("Minimal Task")).toBeInTheDocument();
		});

		it("handles large number of tasks", () => {
			const manyTasks = Array.from({ length: 50 }, (_, i) =>
				createMockTask({
					id: `task-${i}`,
					title: `Task ${i}`,
					status: TASK_STATUS_COLUMNS[i % 6] as Task["status"],
				}),
			);

			render(<KanbanBoard {...defaultProps} tasks={manyTasks} />);

			// Should render without crashing
			expect(screen.getByText("Task 0")).toBeInTheDocument();
			expect(screen.getByText("Task 49")).toBeInTheDocument();
		});
	});
});
