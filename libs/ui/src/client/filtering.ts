import type { TaskStatus, UiTask } from './types';

export interface UiTaskFilter {
  /** Case-insensitive substring match against id, title, and description. */
  query?: string;
  /** Keep only tasks in this status column. */
  status?: TaskStatus;
}

/**
 * Client-side board filtering shared by the pilots (search box + filter
 * chips). Pure and transport-agnostic: adapters keep delivering the full
 * task list; the board narrows what it renders.
 */
export function filterUiTasks(
  tasks: readonly UiTask[],
  filter: UiTaskFilter,
): UiTask[] {
  const query = filter.query?.trim().toLowerCase() ?? '';
  return tasks.filter((task) => {
    if (filter.status != null && task.status !== filter.status) return false;
    if (query === '') return true;
    return [task.id, task.title, task.description ?? ''].some((field) =>
      field.toLowerCase().includes(query),
    );
  });
}
