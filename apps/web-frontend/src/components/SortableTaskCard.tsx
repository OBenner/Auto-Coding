/**
 * SortableTaskCard Component
 *
 * A wrapper around TaskCard that enables drag-and-drop functionality
 * using @dnd-kit/sortable.
 */

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Task, TaskStatus } from "../shared/types";
import { TaskCard } from "./TaskCard";

interface SortableTaskCardProps {
	task: Task;
	onClick: () => void;
	onStatusChange?: (newStatus: TaskStatus) => unknown;
	isSelectable?: boolean;
	isSelected?: boolean;
	onToggleSelect?: () => void;
}

export function SortableTaskCard({
	task,
	onClick,
	onStatusChange,
	isSelectable,
	isSelected,
	onToggleSelect,
}: SortableTaskCardProps) {
	const {
		attributes,
		listeners,
		setNodeRef,
		transform,
		transition,
		isDragging,
	} = useSortable({ id: task.id });

	const style = {
		transform: CSS.Transform.toString(transform),
		transition,
		opacity: isDragging ? 0.5 : 1,
	};

	return (
		<div ref={setNodeRef} style={style} {...attributes} {...listeners}>
			<TaskCard
				task={task}
				onClick={onClick}
				onStatusChange={onStatusChange}
				isSelectable={isSelectable}
				isSelected={isSelected}
				onToggleSelect={onToggleSelect}
			/>
		</div>
	);
}
