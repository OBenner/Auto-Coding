/**
 * TaskDetail Component Unit Tests
 *
 * Tests the TaskDetail page component's rendering, state management,
 * and interaction with the API client.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { TaskDetail } from './TaskDetail';
import { apiClient } from '../api/client';
import type { TaskDetail as TaskDetailType } from '../api/types';

// Mock the API client
vi.mock('../api/client', () => ({
  apiClient: {
    getTask: vi.fn(),
  },
}));

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'common:loading': 'Loading...',
        'common:error': 'Error',
      };
      return translations[key] || key;
    },
  }),
}));

describe('TaskDetail', () => {
  const mockOnBack = vi.fn();
  const testTaskId = '001';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  const createMockTaskDetail = (overrides: Partial<TaskDetailType> = {}): TaskDetailType => ({
    number: '001',
    name: 'Test Task',
    folder: '001-test-task',
    status: 'in_progress',
    progress: {
      completed: 5,
      in_progress: 2,
      pending: 3,
      failed: 0,
      total: 10,
      percentage: 50,
    },
    has_build: true,
    spec_content: '# Test Spec\n\nThis is a test specification.',
    ...overrides,
  });

  describe('Loading State', () => {
    it('should display loading spinner and message while fetching task details', async () => {
      // Mock API call that never resolves to keep loading state
      const neverResolvingPromise = new Promise(() => {});
      vi.mocked(apiClient.getTask).mockReturnValue(neverResolvingPromise as any);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      // Check for loading spinner (by className since it's a styled div)
      const loadingContainer = screen.getByText('Loading...').parentElement;
      expect(loadingContainer).toBeInTheDocument();

      // Check for loading text
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should display error message when API call fails', async () => {
      const errorMessage = 'Failed to load task details';
      vi.mocked(apiClient.getTask).mockRejectedValue(new Error(errorMessage));

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      // Wait for error to be displayed
      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument();
      });

      expect(screen.getByText(errorMessage)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /back to tasks/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('should retry fetching task when "Try Again" button is clicked', async () => {
      // First call fails
      vi.mocked(apiClient.getTask).mockRejectedValueOnce(new Error('Network error'));

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      // Wait for error state
      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument();
      });

      // Mock successful response for retry
      const mockTask = createMockTaskDetail();
      vi.mocked(apiClient.getTask).mockResolvedValueOnce(mockTask);

      // Click "Try Again"
      const retryButton = screen.getByRole('button', { name: /try again/i });
      fireEvent.click(retryButton);

      // Wait for task to load
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      expect(apiClient.getTask).toHaveBeenCalledTimes(2);
      expect(apiClient.getTask).toHaveBeenCalledWith(testTaskId);
    });

    it('should call onBack when "Back to Tasks" button is clicked in error state', async () => {
      vi.mocked(apiClient.getTask).mockRejectedValue(new Error('Failed to load'));

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument();
      });

      const backButton = screen.getByRole('button', { name: /back to tasks/i });
      fireEvent.click(backButton);

      expect(mockOnBack).toHaveBeenCalledTimes(1);
    });

    it('should display "Task not found" when task is null', async () => {
      vi.mocked(apiClient.getTask).mockResolvedValue(null as any);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Task not found')).toBeInTheDocument();
      });
    });
  });

  describe('Task Detail Rendering', () => {
    it('should display task details when API returns data', async () => {
      const mockTask = createMockTaskDetail({
        number: '042',
        name: 'Feature Implementation',
      });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      // Wait for task to load
      await waitFor(() => {
        expect(screen.getByText('Feature Implementation')).toBeInTheDocument();
      });

      expect(screen.getByText('Spec #042')).toBeInTheDocument();
    });

    it('should display task status and progress information', async () => {
      const mockTask = createMockTaskDetail({
        status: 'in_progress',
        progress: {
          completed: 7,
          in_progress: 2,
          pending: 1,
          failed: 0,
          total: 10,
          percentage: 70,
        },
      });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Check status badge
      expect(screen.getByText('in_progress')).toBeInTheDocument();

      // Check progress stats
      expect(screen.getByText('70%')).toBeInTheDocument();
      expect(screen.getByText('7 completed')).toBeInTheDocument();
      expect(screen.getByText('2 in progress')).toBeInTheDocument();
      expect(screen.getByText('1 pending')).toBeInTheDocument();
      expect(screen.getByText('0 failed')).toBeInTheDocument();
    });

    it('should display build badge when task has an active build', async () => {
      const mockTask = createMockTaskDetail({ has_build: true });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      expect(screen.getByText('Active')).toBeInTheDocument();
    });

    it('should not display build badge when task has no build', async () => {
      const mockTask = createMockTaskDetail({ has_build: false });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      expect(screen.queryByText('Active')).not.toBeInTheDocument();
    });

    it('should display spec content when available', async () => {
      const specContent = '# Authentication Feature\n\nImplement OAuth 2.0 login.';
      const mockTask = createMockTaskDetail({ spec_content: specContent });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Check for spec content using regex to handle multiline text
      expect(screen.getByText(/# Authentication Feature/)).toBeInTheDocument();
      expect(screen.getByText(/Implement OAuth 2.0 login/)).toBeInTheDocument();
      expect(screen.getByText('Specification')).toBeInTheDocument();
    });

    it('should not display spec content section when not available', async () => {
      const mockTask = createMockTaskDetail({ spec_content: undefined });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      expect(screen.queryByText('Specification')).not.toBeInTheDocument();
    });
  });

  describe('Back Navigation', () => {
    it('should call onBack when back button is clicked', async () => {
      const mockTask = createMockTaskDetail();
      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Find the back button (icon button in header)
      const backButtons = screen.getAllByRole('button');
      const backButton = backButtons.find(btn => btn.querySelector('svg'));

      if (backButton) {
        fireEvent.click(backButton);
      }

      expect(mockOnBack).toHaveBeenCalledTimes(1);
    });
  });

  describe('Refresh Functionality', () => {
    it('should display refresh button', async () => {
      const mockTask = createMockTaskDetail();
      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
      });
    });

    it('should reload task data when refresh button is clicked', async () => {
      // Initial load
      const initialTask = createMockTaskDetail({
        progress: {
          completed: 5,
          in_progress: 2,
          pending: 3,
          failed: 0,
          total: 10,
          percentage: 50,
        },
      });

      vi.mocked(apiClient.getTask).mockResolvedValueOnce(initialTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('50%')).toBeInTheDocument();
      });

      // Mock refreshed data with updated progress
      const refreshedTask = createMockTaskDetail({
        progress: {
          completed: 8,
          in_progress: 1,
          pending: 1,
          failed: 0,
          total: 10,
          percentage: 80,
        },
      });

      vi.mocked(apiClient.getTask).mockResolvedValueOnce(refreshedTask);

      // Click refresh
      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      fireEvent.click(refreshButton);

      // Wait for updated progress
      await waitFor(() => {
        expect(screen.getByText('80%')).toBeInTheDocument();
      });

      expect(screen.getByText('8 completed')).toBeInTheDocument();
      expect(apiClient.getTask).toHaveBeenCalledTimes(2);
    });

    it('should disable refresh button while refreshing', async () => {
      // Create a promise we can control
      let resolveRefresh: (value: any) => void;
      const refreshPromise = new Promise((resolve) => {
        resolveRefresh = resolve;
      });

      // Initial load
      vi.mocked(apiClient.getTask).mockResolvedValueOnce(createMockTaskDetail());

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Setup delayed refresh
      vi.mocked(apiClient.getTask).mockReturnValueOnce(refreshPromise as any);

      // Click refresh
      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      fireEvent.click(refreshButton);

      // Button should be disabled while refreshing
      await waitFor(() => {
        expect(refreshButton).toBeDisabled();
      });

      // Resolve the refresh
      resolveRefresh!(createMockTaskDetail());

      // Button should be enabled again
      await waitFor(() => {
        expect(refreshButton).not.toBeDisabled();
      });
    });

    it('should show spinning icon while refreshing', async () => {
      // Create a promise we can control
      let resolveRefresh: (value: any) => void;
      const refreshPromise = new Promise((resolve) => {
        resolveRefresh = resolve;
      });

      // Initial load
      vi.mocked(apiClient.getTask).mockResolvedValueOnce(createMockTaskDetail());

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Setup delayed refresh
      vi.mocked(apiClient.getTask).mockReturnValueOnce(refreshPromise as any);

      // Click refresh
      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      fireEvent.click(refreshButton);

      // Check for spinning animation class
      await waitFor(() => {
        const icon = refreshButton.querySelector('.animate-spin');
        expect(icon).toBeInTheDocument();
      });

      // Resolve the refresh
      resolveRefresh!(createMockTaskDetail());

      // Icon should stop spinning
      await waitFor(() => {
        const icon = refreshButton.querySelector('.animate-spin');
        expect(icon).not.toBeInTheDocument();
      });
    });
  });

  describe('Progress Bar Rendering', () => {
    it('should render progress bar with correct width', async () => {
      const mockTask = createMockTaskDetail({
        progress: {
          completed: 6,
          in_progress: 0,
          pending: 4,
          failed: 0,
          total: 10,
          percentage: 60,
        },
      });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('60%')).toBeInTheDocument();
      });

      // Find progress bar by looking for bg-blue-600 class
      const progressBar = document.querySelector('.bg-blue-600');
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveStyle({ width: '60%' });
    });

    it('should handle 0% progress', async () => {
      const mockTask = createMockTaskDetail({
        progress: {
          completed: 0,
          in_progress: 0,
          pending: 10,
          failed: 0,
          total: 10,
          percentage: 0,
        },
      });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('0%')).toBeInTheDocument();
      });

      const progressBar = document.querySelector('.bg-blue-600');
      expect(progressBar).toHaveStyle({ width: '0%' });
    });

    it('should handle 100% progress', async () => {
      const mockTask = createMockTaskDetail({
        progress: {
          completed: 10,
          in_progress: 0,
          pending: 0,
          failed: 0,
          total: 10,
          percentage: 100,
        },
      });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('100%')).toBeInTheDocument();
      });

      const progressBar = document.querySelector('.bg-blue-600');
      expect(progressBar).toHaveStyle({ width: '100%' });
    });
  });

  describe('Edge Cases', () => {
    it('should handle API returning undefined error', async () => {
      vi.mocked(apiClient.getTask).mockRejectedValue('Network failure');

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load task details')).toBeInTheDocument();
      });
    });

    it('should fetch task only once on initial mount', async () => {
      vi.mocked(apiClient.getTask).mockResolvedValue(createMockTaskDetail());

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      expect(apiClient.getTask).toHaveBeenCalledTimes(1);
      expect(apiClient.getTask).toHaveBeenCalledWith(testTaskId);
    });

    it('should handle rapid refresh clicks gracefully', async () => {
      vi.mocked(apiClient.getTask).mockResolvedValue(createMockTaskDetail());

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

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

    it('should handle tasks with special characters in name', async () => {
      const mockTask = createMockTaskDetail({
        name: 'Task with "quotes" and <html> tags',
      });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Task with "quotes" and <html> tags')).toBeInTheDocument();
      });
    });

    it('should handle empty spec content', async () => {
      const mockTask = createMockTaskDetail({ spec_content: '' });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Empty content should still show the section but with empty pre
      expect(screen.queryByText('Specification')).not.toBeInTheDocument();
    });

    it('should handle failed subtasks in progress', async () => {
      const mockTask = createMockTaskDetail({
        progress: {
          completed: 5,
          in_progress: 2,
          pending: 1,
          failed: 2,
          total: 10,
          percentage: 50,
        },
      });

      vi.mocked(apiClient.getTask).mockResolvedValue(mockTask);

      render(<TaskDetail taskId={testTaskId} onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      expect(screen.getByText('2 failed')).toBeInTheDocument();
    });
  });

  describe('Different Task IDs', () => {
    it('should fetch correct task when taskId changes', async () => {
      vi.mocked(apiClient.getTask).mockResolvedValue(createMockTaskDetail({ number: '001' }));

      const { rerender } = render(<TaskDetail taskId="001" onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Spec #001')).toBeInTheDocument();
      });

      expect(apiClient.getTask).toHaveBeenCalledWith('001');

      // Change taskId
      vi.mocked(apiClient.getTask).mockResolvedValue(createMockTaskDetail({ number: '002' }));

      rerender(<TaskDetail taskId="002" onBack={mockOnBack} />);

      await waitFor(() => {
        expect(screen.getByText('Spec #002')).toBeInTheDocument();
      });

      expect(apiClient.getTask).toHaveBeenCalledWith('002');
    });
  });
});
