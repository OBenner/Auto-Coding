/**
 * TaskList Component Unit Tests
 *
 * Tests the TaskList page component's rendering, state management,
 * and interaction with the API client.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react';
import { TaskList } from './TaskList';
import { apiClient } from '../api/client';
import type { TaskSummary } from '../api/types';

// Mock the API client
vi.mock('../api/client', () => ({
  apiClient: {
    listTasks: vi.fn(),
  },
}));

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'common:loading': 'Loading...',
        'common:error': 'Error',
        'common:tasks': 'Tasks',
      };
      return translations[key] || key;
    },
  }),
}));

describe('TaskList', () => {
  const mockOnTaskClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  const createMockTaskSummary = (overrides: Partial<TaskSummary> = {}): TaskSummary => ({
    number: '001',
    name: 'Test Task',
    folder: '001-test-task',
    status: 'backlog',
    progress: '0',
    has_build: false,
    ...overrides,
  });

  describe('Loading State', () => {
    it('should display loading spinner and message while fetching tasks', async () => {
      // Mock API call that never resolves to keep loading state
      const neverResolvingPromise = new Promise(() => {});
      vi.mocked(apiClient.listTasks).mockReturnValue(neverResolvingPromise as any);

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      // Check for loading spinner (by className since it's a styled div)
      const loadingContainer = screen.getByText('Loading...').parentElement;
      expect(loadingContainer).toBeInTheDocument();

      // Check for loading text
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should display error message when API call fails', async () => {
      const errorMessage = 'Failed to load tasks';
      vi.mocked(apiClient.listTasks).mockRejectedValue(new Error(errorMessage));

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      // Wait for error to be displayed
      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument();
      });

      expect(screen.getByText(errorMessage)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('should retry fetching tasks when "Try Again" button is clicked', async () => {
      // First call fails
      vi.mocked(apiClient.listTasks).mockRejectedValueOnce(new Error('Network error'));

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      // Wait for error state
      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument();
      });

      // Mock successful response for retry
      const mockTasks = [createMockTaskSummary()];
      vi.mocked(apiClient.listTasks).mockResolvedValueOnce({
        tasks: mockTasks,
        total: mockTasks.length,
      });

      // Click "Try Again"
      const retryButton = screen.getByRole('button', { name: /try again/i });
      fireEvent.click(retryButton);

      // Wait for tasks to load
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      expect(apiClient.listTasks).toHaveBeenCalledTimes(2);
    });
  });

  describe('Empty State', () => {
    it('should display empty state when no tasks are returned', async () => {
      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: [],
        total: 0,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('No tasks found')).toBeInTheDocument();
      });

      expect(screen.getByText('Tasks will appear here once you create specs')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });
  });

  describe('Task List Rendering', () => {
    it('should display tasks when API returns data', async () => {
      const mockTasks = [
        createMockTaskSummary({ number: '001', name: 'First Task' }),
        createMockTaskSummary({ number: '002', name: 'Second Task' }),
        createMockTaskSummary({ number: '003', name: 'Third Task' }),
      ];

      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: mockTasks,
        total: mockTasks.length,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      // Wait for tasks to load
      await waitFor(() => {
        expect(screen.getByText('First Task')).toBeInTheDocument();
      });

      expect(screen.getByText('Second Task')).toBeInTheDocument();
      expect(screen.getByText('Third Task')).toBeInTheDocument();
      expect(screen.getByText('3 tasks total')).toBeInTheDocument();
    });

    it('should display correct singular/plural task count', async () => {
      // Test singular
      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: [createMockTaskSummary()],
        total: 1,
      });

      const { unmount } = render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('1 task total')).toBeInTheDocument();
      });

      // Clean up first render
      unmount();

      // Test plural - need a fresh component to trigger new API call
      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: [createMockTaskSummary(), createMockTaskSummary({ number: '002' })],
        total: 2,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('2 tasks total')).toBeInTheDocument();
      });
    });

    it('should render tasks in a grid layout', async () => {
      const mockTasks = [
        createMockTaskSummary({ number: '001', name: 'First Task' }),
        createMockTaskSummary({ number: '002', name: 'Second Task' }),
      ];

      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: mockTasks,
        total: mockTasks.length,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      // Wait for tasks to load
      await waitFor(() => {
        expect(screen.getByText('First Task')).toBeInTheDocument();
      });

      // Check that grid container exists
      const gridContainer = screen.getByText('First Task').closest('.grid');
      expect(gridContainer).toBeInTheDocument();
      expect(gridContainer).toHaveClass('grid');
    });
  });

  describe('Task Click Handling', () => {
    it('should call onTaskClick with correct task ID when a task is clicked', async () => {
      const mockTasks = [createMockTaskSummary({ number: '001', name: 'Clickable Task' })];

      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: mockTasks,
        total: mockTasks.length,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('Clickable Task')).toBeInTheDocument();
      });

      // Click the task card (click on the card itself)
      const taskCard = screen.getByText('Clickable Task').closest('[class*="cursor-pointer"]');
      if (taskCard) {
        fireEvent.click(taskCard);
      }

      expect(mockOnTaskClick).toHaveBeenCalledWith('001');
      expect(mockOnTaskClick).toHaveBeenCalledTimes(1);
    });

    it('should handle clicks on multiple tasks independently', async () => {
      const mockTasks = [
        createMockTaskSummary({ number: '001', name: 'Task One' }),
        createMockTaskSummary({ number: '002', name: 'Task Two' }),
      ];

      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: mockTasks,
        total: mockTasks.length,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('Task One')).toBeInTheDocument();
      });

      // Click first task
      const taskOne = screen.getByText('Task One').closest('[class*="cursor-pointer"]');
      if (taskOne) {
        fireEvent.click(taskOne);
      }

      expect(mockOnTaskClick).toHaveBeenCalledWith('001');

      // Click second task
      const taskTwo = screen.getByText('Task Two').closest('[class*="cursor-pointer"]');
      if (taskTwo) {
        fireEvent.click(taskTwo);
      }

      expect(mockOnTaskClick).toHaveBeenCalledWith('002');
      expect(mockOnTaskClick).toHaveBeenCalledTimes(2);
    });
  });

  describe('Refresh Functionality', () => {
    it('should display refresh button in task list view', async () => {
      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: [createMockTaskSummary()],
        total: 1,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
      });
    });

    it('should reload tasks when refresh button is clicked', async () => {
      // Initial load
      vi.mocked(apiClient.listTasks).mockResolvedValueOnce({
        tasks: [createMockTaskSummary({ name: 'Original Task' })],
        total: 1,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('Original Task')).toBeInTheDocument();
      });

      // Mock refreshed data
      vi.mocked(apiClient.listTasks).mockResolvedValueOnce({
        tasks: [
          createMockTaskSummary({ name: 'Original Task' }),
          createMockTaskSummary({ number: '002', name: 'New Task' }),
        ],
        total: 2,
      });

      // Click refresh
      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      fireEvent.click(refreshButton);

      // Wait for new task to appear
      await waitFor(() => {
        expect(screen.getByText('New Task')).toBeInTheDocument();
      });

      expect(apiClient.listTasks).toHaveBeenCalledTimes(2);
    });

    it('should disable refresh button while refreshing', async () => {
      // Create a promise we can control
      let resolveRefresh: (value: any) => void;
      const refreshPromise = new Promise((resolve) => {
        resolveRefresh = resolve;
      });

      // Initial load
      vi.mocked(apiClient.listTasks).mockResolvedValueOnce({
        tasks: [createMockTaskSummary()],
        total: 1,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Setup delayed refresh
      vi.mocked(apiClient.listTasks).mockReturnValueOnce(refreshPromise as any);

      // Click refresh
      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      fireEvent.click(refreshButton);

      // Button should be disabled while refreshing
      await waitFor(() => {
        expect(refreshButton).toBeDisabled();
      });

      // Resolve the refresh
      resolveRefresh!({
        tasks: [createMockTaskSummary()],
        total: 1,
      });

      // Button should be enabled again
      await waitFor(() => {
        expect(refreshButton).not.toBeDisabled();
      });
    });
  });

  describe('Task Conversion', () => {
    it('should correctly convert TaskSummary to Task type', async () => {
      const mockTaskSummary = createMockTaskSummary({
        number: '042',
        name: 'Test Conversion Task',
        status: 'in_progress',
      });

      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: [mockTaskSummary],
        total: 1,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('Test Conversion Task')).toBeInTheDocument();
      });

      // Task should display status in description
      expect(screen.getByText(/Status: in_progress/)).toBeInTheDocument();
    });

    it('should handle tasks with special characters in name', async () => {
      const mockTasks = [
        createMockTaskSummary({ name: 'Task with "quotes"' }),
        createMockTaskSummary({ number: '002', name: "Task with 'apostrophes'" }),
        createMockTaskSummary({ number: '003', name: 'Task with <html> tags' }),
      ];

      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: mockTasks,
        total: mockTasks.length,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('Task with "quotes"')).toBeInTheDocument();
      });

      expect(screen.getByText("Task with 'apostrophes'")).toBeInTheDocument();
      expect(screen.getByText('Task with <html> tags')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle API returning undefined error', async () => {
      vi.mocked(apiClient.listTasks).mockRejectedValue(new Error('Network failure'));

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load tasks')).toBeInTheDocument();
      });
    });

    it('should fetch tasks only once on initial mount', async () => {
      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: [],
        total: 0,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('No tasks found')).toBeInTheDocument();
      });

      expect(apiClient.listTasks).toHaveBeenCalledTimes(1);
    });

    it('should handle rapid refresh clicks gracefully', async () => {
      vi.mocked(apiClient.listTasks).mockResolvedValue({
        tasks: [createMockTaskSummary()],
        total: 1,
      });

      render(<TaskList onTaskClick={mockOnTaskClick} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      const refreshButton = screen.getByRole('button', { name: /refresh/i });

      // Click multiple times rapidly
      fireEvent.click(refreshButton);
      fireEvent.click(refreshButton);
      fireEvent.click(refreshButton);

      // Should still work correctly without errors
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });
    });
  });
});
