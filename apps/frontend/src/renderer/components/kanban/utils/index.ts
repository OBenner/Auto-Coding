import type { Task } from '../../../../../shared/types';

export function filterTasksBySearch(tasks: Task[], searchQuery: string): Task[] {
  if (!searchQuery) {
    return tasks;
  }

  const query = searchQuery.toLowerCase();
  return tasks.filter(task =>
    task.title.toLowerCase().includes(query) ||
    task.description.toLowerCase().includes(query)
  );
}
