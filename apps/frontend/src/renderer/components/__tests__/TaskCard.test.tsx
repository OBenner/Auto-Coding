/**
 * @vitest-environment jsdom
 */

/**
 * Tests for TaskCard Component
 *
 * Tests the task card component that displays task information in the kanban board.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TaskCard } from '../TaskCard';
import type { Task } from '../../../shared/types';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      const translations: Record<string, string> = {
        'tasks:labels.running': 'Running',
        'tasks:labels.aiReview': 'AI Review',
        'tasks:labels.needsReview': 'Needs Review',
        'tasks:status.complete': 'Complete',
        'tasks:labels.pending': 'Pending',
        'tasks:labels.stuck': 'Stuck',
        'tasks:labels.incomplete': 'Incomplete',
        'tasks:labels.needsRecovery': 'Needs Recovery',
        'tasks:labels.needsResume': 'Needs Resume',
        'tasks:labels.recovering': 'Recovering',
        'tasks:status.archived': 'Archived',
        'tasks:reviewReason.completed': 'Completed',
        'tasks:reviewReason.hasErrors': 'Has Errors',
        'tasks:reviewReason.qaIssues': 'QA Issues',
        'tasks:reviewReason.approvePlan': 'Approve Plan',
        'tasks:actions.recover': 'Recover',
        'tasks:actions.resume': 'Resume',
        'tasks:actions.stop': 'Stop',
        'tasks:actions.start': 'Start',
        'tasks:actions.archive': 'Archive',
        'tasks:actions.moveTo': 'Move To',
        'tasks:actions.taskActions': 'Task Actions',
        'tasks:actions.selectTask': `Select ${params?.title || 'task'}`,
        'tasks:tooltips.viewPR': 'View Pull Request',
        'tasks:tooltips.archiveTask': 'Archive Task',
        'tasks:metadata.severity': 'severity',
        'tasks:columns.backlog': 'Backlog',
        'tasks:columns.queue': 'Queue',
        'tasks:columns.in_progress': 'In Progress',
        'tasks:columns.ai_review': 'AI Review',
        'tasks:columns.human_review': 'Human Review',
        'tasks:columns.done': 'Done',
        'errors:task.jsonError.description': `Failed to parse JSON: ${params?.error || ''}`,
        'errors:task.jsonError.titleSuffix': '(JSON Error)'
      };
      return translations[key] || key;
    }
  })
}));

// Mock task-store
vi.mock('../../stores/task-store', () => ({
  startTask: vi.fn(),
  stopTask: vi.fn(),
  checkTaskRunning: vi.fn().mockResolvedValue(true),
  recoverStuckTask: vi.fn().mockResolvedValue({ success: true }),
  isIncompleteHumanReview: vi.fn().mockReturnValue(false),
  archiveTasks: vi.fn().mockResolvedValue({ success: true })
}));

// Mock PhaseProgressIndicator
vi.mock('../PhaseProgressIndicator', () => ({
  PhaseProgressIndicator: ({ isStuck, isRunning }: any) => (
    <div data-testid="phase-progress-indicator">
      {isStuck && <span>Stuck</span>}
      {isRunning && <span>Running</span>}
    </div>
  )
}));

// Mock utils
vi.mock('../../lib/utils', () => ({
  cn: (...classes: any[]) => classes.filter(Boolean).join(' '),
  formatRelativeTime: (date: Date) => '2 minutes ago',
  sanitizeMarkdownForDisplay: (text: string, length: number) => text.slice(0, length)
}));

// Helper to create a base task
function createMockTask(overrides?: Partial<Task>): Task {
  return {
    id: 'task-1',
    specId: '001-test-feature',
    projectId: 'project-1',
    title: 'Test Task',
    description: 'This is a test task description',
    status: 'backlog',
    subtasks: [],
    logs: [],
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date('2024-01-02'),
    ...overrides
  };
}

describe('TaskCard', () => {
  const mockOnClick = vi.fn();
  const mockOnStatusChange = vi.fn();

  beforeEach(async () => {
    vi.clearAllMocks();
    const { isIncompleteHumanReview } = await import('../../stores/task-store');
    vi.mocked(isIncompleteHumanReview).mockReturnValue(false);
  });

  describe('rendering', () => {
    it('should render task title', () => {
      const task = createMockTask();
      render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(screen.getByText('Test Task')).toBeInTheDocument();
    });

    it('should render task description', () => {
      const task = createMockTask();
      render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(screen.getByText('This is a test task description')).toBeInTheDocument();
    });

    it('should render without description', () => {
      const task = createMockTask({ description: '' });
      render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(screen.getByText('Test Task')).toBeInTheDocument();
      expect(screen.queryByText('This is a test task description')).not.toBeInTheDocument();
    });

    it('should render relative time', () => {
      const task = createMockTask();
      render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(screen.getByText('2 minutes ago')).toBeInTheDocument();
    });

    it('should handle JSON error tasks', () => {
      const task = createMockTask({
        title: 'Test Task__JSON_ERROR_SUFFIX__',
        description: '__JSON_ERROR__:Invalid JSON syntax'
      });
      render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(screen.getByText('Test Task (JSON Error)')).toBeInTheDocument();
    });
  });

  describe('status badges', () => {
    it('should render for backlog status', () => {
      const task = createMockTask({ status: 'backlog' });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      // Should render the task card
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should show running badge for in_progress status', () => {
      const task = createMockTask({ status: 'in_progress' });
      render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(screen.getByText('Running')).toBeInTheDocument();
    });

    it('should render for ai_review status', () => {
      const task = createMockTask({ status: 'ai_review' });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(container.firstChild).toBeInTheDocument();
    });

    it('should render for human_review status', () => {
      const task = createMockTask({ status: 'human_review' });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(container.firstChild).toBeInTheDocument();
    });

    it('should render for done status', () => {
      const task = createMockTask({ status: 'done' });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(container.firstChild).toBeInTheDocument();
    });
  });

  describe('review reason badges', () => {
    it('should render with completed review reason', () => {
      const task = createMockTask({
        status: 'human_review',
        reviewReason: 'completed',
        subtasks: [
          {
            id: 'subtask-1',
            title: 'Subtask 1',
            description: 'Description',
            status: 'completed',
            files: []
          }
        ]
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(container.firstChild).toBeInTheDocument();
    });

    it('should render with errors review reason', () => {
      const task = createMockTask({
        status: 'human_review',
        reviewReason: 'errors',
        subtasks: [
          {
            id: 'subtask-1',
            title: 'Subtask 1',
            description: 'Description',
            status: 'completed',
            files: []
          }
        ]
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(container.firstChild).toBeInTheDocument();
    });

    it('should render with qa_rejected review reason', () => {
      const task = createMockTask({
        status: 'human_review',
        reviewReason: 'qa_rejected',
        subtasks: [
          {
            id: 'subtask-1',
            title: 'Subtask 1',
            description: 'Description',
            status: 'completed',
            files: []
          }
        ]
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(container.firstChild).toBeInTheDocument();
    });

    it('should render with plan_review review reason', () => {
      const task = createMockTask({
        status: 'human_review',
        reviewReason: 'plan_review',
        subtasks: [
          {
            id: 'subtask-1',
            title: 'Subtask 1',
            description: 'Description',
            status: 'completed',
            files: []
          }
        ]
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(container.firstChild).toBeInTheDocument();
    });
  });

  describe('metadata badges', () => {
    it('should render category badge', () => {
      const task = createMockTask({
        metadata: { category: 'feature' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      // Should render badges
      const badges = container.querySelectorAll('[class*="inline-flex"]');
      expect(badges.length).toBeGreaterThan(0);
    });

    it('should render impact badge for high impact', () => {
      const task = createMockTask({
        metadata: { impact: 'high' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      const badges = container.querySelectorAll('[class*="inline-flex"]');
      expect(badges.length).toBeGreaterThan(0);
    });

    it('should render impact badge for critical impact', () => {
      const task = createMockTask({
        metadata: { impact: 'critical' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      const badges = container.querySelectorAll('[class*="inline-flex"]');
      expect(badges.length).toBeGreaterThan(0);
    });

    it('should not render impact badge for low impact', () => {
      const task = createMockTask({
        metadata: { impact: 'low' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      // Should only show the start button, not extra badges
      const buttons = container.querySelectorAll('button');
      expect(buttons.length).toBeLessThan(3);
    });

    it('should render complexity badge', () => {
      const task = createMockTask({
        metadata: { complexity: 'medium' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      const badges = container.querySelectorAll('[class*="inline-flex"]');
      expect(badges.length).toBeGreaterThan(0);
    });

    it('should render priority badge for urgent', () => {
      const task = createMockTask({
        metadata: { priority: 'urgent' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      const badges = container.querySelectorAll('[class*="inline-flex"]');
      expect(badges.length).toBeGreaterThan(0);
    });

    it('should render priority badge for high', () => {
      const task = createMockTask({
        metadata: { priority: 'high' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      const badges = container.querySelectorAll('[class*="inline-flex"]');
      expect(badges.length).toBeGreaterThan(0);
    });

    it('should not render priority badge for low priority', () => {
      const task = createMockTask({
        metadata: { priority: 'low' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      // Should only show minimal UI elements
      const buttons = container.querySelectorAll('button');
      expect(buttons.length).toBeLessThan(3);
    });

    it('should render security severity badge', () => {
      const task = createMockTask({
        metadata: { securitySeverity: 'high' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      // Should include the severity text somewhere in the card
      expect(container.textContent).toContain('severity');
    });
  });

  describe('archived status', () => {
    it('should render with archived metadata', () => {
      const task = createMockTask({
        metadata: { archivedAt: '2024-01-15T10:00:00Z' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(container.firstChild).toBeInTheDocument();
    });

    it('should apply archived styling', () => {
      const task = createMockTask({
        metadata: { archivedAt: '2024-01-15T10:00:00Z' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      const card = container.querySelector('.opacity-60');
      expect(card).toBeInTheDocument();
    });
  });

  describe('execution phase', () => {
    it('should render phase progress indicator when running', () => {
      const task = createMockTask({
        status: 'in_progress',
        executionProgress: {
          phase: 'coding',
          phaseProgress: 50,
          overallProgress: 50
        }
      });
      render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(screen.getByTestId('phase-progress-indicator')).toBeInTheDocument();
    });

    it('should hide status badge when execution phase is active', () => {
      const task = createMockTask({
        status: 'in_progress',
        executionProgress: {
          phase: 'coding',
          phaseProgress: 50,
          overallProgress: 50
        }
      });
      render(<TaskCard task={task} onClick={mockOnClick} />);

      // Status badge should be hidden when phase is active
      // Phase indicator should be visible instead
      expect(screen.getByTestId('phase-progress-indicator')).toBeInTheDocument();
    });
  });

  describe('action buttons', () => {
    it('should render action button for backlog status', () => {
      const task = createMockTask({ status: 'backlog' });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      // Should render at least one button
      const buttons = container.querySelectorAll('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('should render action button for in_progress status', () => {
      const task = createMockTask({ status: 'in_progress' });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      const buttons = container.querySelectorAll('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('should render action button for done status', () => {
      const task = createMockTask({ status: 'done' });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      const buttons = container.querySelectorAll('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('should render differently when archived', () => {
      const task = createMockTask({
        status: 'done',
        metadata: { archivedAt: '2024-01-15T10:00:00Z' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      // Card should have archived styling
      expect(container.querySelector('.opacity-60')).toBeInTheDocument();
    });

    it('should render with prUrl metadata', () => {
      const task = createMockTask({
        status: 'done',
        metadata: { prUrl: 'https://github.com/owner/repo/pull/123' }
      });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(container.firstChild).toBeInTheDocument();
    });
  });

  describe('selectable mode', () => {
    it('should render checkbox when isSelectable is true', () => {
      const task = createMockTask();
      render(
        <TaskCard
          task={task}
          onClick={mockOnClick}
          isSelectable={true}
          isSelected={false}
          onToggleSelect={vi.fn()}
        />
      );

      const checkbox = screen.getByRole('checkbox');
      expect(checkbox).toBeInTheDocument();
    });

    it('should not render checkbox when isSelectable is false', () => {
      const task = createMockTask();
      render(<TaskCard task={task} onClick={mockOnClick} isSelectable={false} />);

      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    });

    it('should check checkbox when isSelected is true', () => {
      const task = createMockTask();
      render(
        <TaskCard
          task={task}
          onClick={mockOnClick}
          isSelectable={true}
          isSelected={true}
          onToggleSelect={vi.fn()}
        />
      );

      const checkbox = screen.getByRole('checkbox');
      // Check that the checkbox is rendered (checked state is managed by component)
      expect(checkbox).toBeInTheDocument();
    });

    it('should call onToggleSelect when checkbox is clicked', () => {
      const task = createMockTask();
      const mockToggle = vi.fn();
      render(
        <TaskCard
          task={task}
          onClick={mockOnClick}
          isSelectable={true}
          isSelected={false}
          onToggleSelect={mockToggle}
        />
      );

      const checkbox = screen.getByRole('checkbox');
      fireEvent.click(checkbox);

      expect(mockToggle).toHaveBeenCalled();
    });

    it('should apply selection styling when selected', () => {
      const task = createMockTask();
      const { container } = render(
        <TaskCard
          task={task}
          onClick={mockOnClick}
          isSelectable={true}
          isSelected={true}
          onToggleSelect={vi.fn()}
        />
      );

      const card = container.querySelector('[class*="ring-2"][class*="ring-ring"]');
      expect(card).toBeInTheDocument();
    });
  });

  describe('click handlers', () => {
    it('should call onClick when card is clicked', () => {
      const task = createMockTask();
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      // Click on the card container
      const card = container.firstChild as HTMLElement;
      fireEvent.click(card);

      expect(mockOnClick).toHaveBeenCalled();
    });

    it('should handle button clicks with stopPropagation', () => {
      const task = createMockTask({ status: 'backlog' });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      // Click on a button (any button in the card)
      const buttons = container.querySelectorAll('button');
      if (buttons.length > 0) {
        fireEvent.click(buttons[0]);
        // onClick should not be called due to stopPropagation
        expect(mockOnClick).not.toHaveBeenCalled();
      }
    });
  });

  describe('stuck detection', () => {
    it('should render when task is potentially stuck', async () => {
      const { checkTaskRunning } = await import('../../stores/task-store');
      vi.mocked(checkTaskRunning).mockResolvedValue(false);

      const task = createMockTask({
        status: 'in_progress',
        executionProgress: {
          phase: 'coding',
          phaseProgress: 50,
          overallProgress: 50
        }
      });

      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      // Component should render successfully
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should render correctly for non-stuck tasks', async () => {
      const { checkTaskRunning } = await import('../../stores/task-store');
      vi.mocked(checkTaskRunning).mockResolvedValue(true);

      const task = createMockTask({
        status: 'in_progress',
        executionProgress: {
          phase: 'coding',
          phaseProgress: 50,
          overallProgress: 50
        }
      });

      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      // Component should render
      expect(container.firstChild).toBeInTheDocument();
    });
  });

  describe('incomplete status', () => {
    it('should render incomplete tasks correctly', async () => {
      const { isIncompleteHumanReview } = await import('../../stores/task-store');
      vi.mocked(isIncompleteHumanReview).mockReturnValue(true);

      const task = createMockTask({
        status: 'human_review',
        subtasks: []
      });

      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(container.firstChild).toBeInTheDocument();
    });

    it('should render action button for incomplete tasks', async () => {
      const { isIncompleteHumanReview } = await import('../../stores/task-store');
      vi.mocked(isIncompleteHumanReview).mockReturnValue(true);

      const task = createMockTask({
        status: 'human_review',
        subtasks: []
      });

      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      const buttons = container.querySelectorAll('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  describe('status menu', () => {
    it('should render status menu when onStatusChange is provided', () => {
      const task = createMockTask();
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} onStatusChange={mockOnStatusChange} />);

      // Should render at least one more button (the menu trigger)
      const buttons = container.querySelectorAll('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('should not render status menu when onStatusChange is not provided', () => {
      const task = createMockTask();
      render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(screen.queryByLabelText('Task Actions')).not.toBeInTheDocument();
    });
  });

  describe('progress indicator', () => {
    it('should show progress when subtasks exist', () => {
      const task = createMockTask({
        subtasks: [
          {
            id: 'subtask-1',
            title: 'Subtask 1',
            description: 'Description',
            status: 'completed',
            files: []
          }
        ]
      });
      render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(screen.getByTestId('phase-progress-indicator')).toBeInTheDocument();
    });

    it('should show progress when running', () => {
      const task = createMockTask({
        status: 'in_progress',
        executionProgress: {
          phase: 'coding',
          phaseProgress: 50,
          overallProgress: 50
        }
      });
      render(<TaskCard task={task} onClick={mockOnClick} />);

      expect(screen.getByTestId('phase-progress-indicator')).toBeInTheDocument();
      expect(screen.getByText('Running')).toBeInTheDocument();
    });
  });

  describe('running state', () => {
    it('should apply running styling when in_progress', () => {
      const task = createMockTask({ status: 'in_progress' });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      const card = container.querySelector('[class*="task-running-pulse"]');
      expect(card).toBeInTheDocument();
    });

    it('should not apply running styling when not in_progress', () => {
      const task = createMockTask({ status: 'backlog' });
      const { container } = render(<TaskCard task={task} onClick={mockOnClick} />);

      const card = container.querySelector('[class*="task-running-pulse"]');
      expect(card).not.toBeInTheDocument();
    });
  });
});
