// Primitives (U0.5)
export { Badge } from './primitives/Badge';
export type { BadgeProps } from './primitives/Badge';
export { Button } from './primitives/Button';
export type { ButtonProps } from './primitives/Button';
export { Input } from './primitives/Input';
export type { InputProps } from './primitives/Input';
export { Kbd } from './primitives/Kbd';
export type { KbdProps } from './primitives/Kbd';
export { ThemeProvider, useTheme } from './theme/ThemeProvider';
export type { Theme, ResolvedTheme, ThemeProviderProps } from './theme/ThemeProvider';
export { AppShell } from './shell/AppShell';
export type { AppShellProps } from './shell/AppShell';
export { Sidebar } from './shell/Sidebar';
export type { SidebarProps } from './shell/Sidebar';
export type { SidebarSection, SidebarItem } from './shell/nav-config';

// Data layer (ports & adapters) + Kanban pilot (U1)
export {
  AutoCodeClientProvider,
  useAutoCodeClient,
  useTasks,
  useTask,
} from './client/AutoCodeClient';
export type {
  AutoCodeClient,
  AutoCodeClientProviderProps,
  UseTasksResult,
  UseTaskResult,
} from './client/AutoCodeClient';
export type {
  UiTask,
  UiTaskBadge,
  UiTaskDetail,
  UiTaskProgress,
  UiSubtask,
  UiSubtaskStatus,
  UiMetaRow,
  UiMetaSection,
  UiRelease,
  UiReleaseEntry,
  UiReleaseSection,
  UiReleaseSectionKind,
  UiReleaseType,
  CreateTaskInput,
  TaskStatus,
  BadgeTone,
} from './client/types';
export { KanbanBoard, DEFAULT_KANBAN_COLUMNS } from './screens/KanbanBoard';
export type { KanbanBoardProps, KanbanColumn } from './screens/KanbanBoard';
// Canonical screens (U2)
export { TaskDetail } from './screens/TaskDetail';
export type { TaskDetailProps, TaskDetailTabId } from './screens/TaskDetail';
// Board chrome (U3)
export { BoardToolbar } from './screens/BoardToolbar';
export type {
  BoardToolbarProps,
  BoardToolbarFilter,
  BoardToolbarView,
} from './screens/BoardToolbar';
export { BoardView, buildBoardViewLabels } from './screens/BoardView';
export type {
  BoardViewProps,
  BoardViewLabels,
  Translate,
} from './screens/BoardView';
// Board data states (U4)
export { BoardSkeleton } from './screens/BoardSkeleton';
export type { BoardSkeletonProps } from './screens/BoardSkeleton';
export { filterUiTasks } from './client/filtering';
export type { UiTaskFilter } from './client/filtering';
export { useBoardFilter, FILTER_IDS } from './client/useBoardFilter';
export type { UseBoardFilterResult, FilterId } from './client/useBoardFilter';
// Changelog browser (U5 B1 pilot)
export { ChangelogView } from './screens/ChangelogView';
export type { ChangelogViewProps, ChangelogViewStateLabels } from './screens/ChangelogView';
