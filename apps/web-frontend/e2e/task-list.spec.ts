/**
 * Task List E2E Tests
 *
 * End-to-end tests for the TaskList page and navigation flows.
 * Tests user interactions with the task list, including viewing tasks,
 * navigation to task details, error handling, and refresh functionality.
 */

import { test, expect } from '@playwright/test';
import {
  mockTaskListResponse,
  mockTaskListError,
  createMockTask,
  setupDelayedRefreshRoute,
} from './helpers';

test.describe('Task List Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to welcome page first
    await page.goto('/');
    // Wait for the main layout to be ready instead of using a fixed timeout
    await page.waitForSelector('main, [role="main"], #app, #root', { state: 'visible' });
  });

  test.describe('Loading State', () => {
    test('should display loading spinner while fetching tasks', async ({ page }) => {
      // Mock with a delay to keep loading state visible
      await mockTaskListResponse(page, [], 1000);

      await page.goto('/#/tasks');

      // Should show loading state
      await expect(page.getByText('Loading...')).toBeVisible();

      // Wait for loading to complete
      await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 2000 });
    });
  });

  test.describe('Empty State', () => {
    test('should display empty state when no tasks exist', async ({ page }) => {
      await mockTaskListResponse(page, []);

      await page.goto('/#/tasks');

      await expect(page.getByText('No tasks found')).toBeVisible();
      await expect(page.getByText('Tasks will appear here once you create specs')).toBeVisible();
    });

    test('should show refresh button in empty state', async ({ page }) => {
      await mockTaskListResponse(page, []);

      await page.goto('/#/tasks');

      await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
    });
  });

  test.describe('Task List Rendering', () => {
    test('should display tasks when API returns data', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'First Task' }),
        createMockTask({ number: '002', name: 'Second Task' }),
        createMockTask({ number: '003', name: 'Third Task' }),
      ];

      await mockTaskListResponse(page, mockTasks);

      await page.goto('/#/tasks');

      // Wait for tasks to load
      await expect(page.getByText('First Task')).toBeVisible();
      await expect(page.getByText('Second Task')).toBeVisible();
      await expect(page.getByText('Third Task')).toBeVisible();
    });

    test('should display correct task count', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'Task 1' }),
        createMockTask({ number: '002', name: 'Task 2' }),
        createMockTask({ number: '003', name: 'Task 3' }),
      ];

      await mockTaskListResponse(page, mockTasks);

      await page.goto('/#/tasks');

      await expect(page.getByText('3 tasks total')).toBeVisible();
    });

    test('should display singular task count for one task', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Single Task' })];

      await mockTaskListResponse(page, mockTasks);

      await page.goto('/#/tasks');

      await expect(page.getByText('1 task total')).toBeVisible();
    });

    test('should display task status in description', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'Test Task', status: 'in_progress' }),
      ];

      await mockTaskListResponse(page, mockTasks);

      await page.goto('/#/tasks');

      await expect(page.getByText('Test Task')).toBeVisible();
      await expect(page.getByText(/Status: in_progress/)).toBeVisible();
    });

    test('should render tasks in grid layout', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'Task 1' }),
        createMockTask({ number: '002', name: 'Task 2' }),
      ];

      await mockTaskListResponse(page, mockTasks);

      await page.goto('/#/tasks');

      await expect(page.getByText('Task 1')).toBeVisible();

      // Check that the grid container exists
      const gridContainer = page.locator('.grid').first();
      await expect(gridContainer).toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('should display error message when API fails', async ({ page }) => {
      await mockTaskListError(page, 500, 'Failed to load tasks');

      await page.goto('/#/tasks');

      await expect(page.getByText('Error')).toBeVisible();
      await expect(page.getByText('Failed to load tasks')).toBeVisible();
    });

    test('should show "Try Again" button on error', async ({ page }) => {
      await mockTaskListError(page, 500, 'Network error');

      await page.goto('/#/tasks');

      await expect(page.getByRole('button', { name: /try again/i })).toBeVisible();
    });

    test('should retry fetching tasks when "Try Again" is clicked', async ({ page }) => {
      // First call fails
      let requestCount = 0;
      await page.route('**/api/tasks', async (route) => {
        requestCount++;
        if (requestCount === 1) {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Network error' }),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              tasks: [createMockTask({ name: 'Recovered Task' })],
              total: 1,
            }),
          });
        }
      });

      await page.goto('/#/tasks');

      // Wait for error state
      await expect(page.getByText('Network error')).toBeVisible();

      // Click "Try Again"
      const tryAgainButton = page.getByRole('button', { name: /try again/i });
      await tryAgainButton.click();

      // Should show recovered task
      await expect(page.getByText('Recovered Task')).toBeVisible();
    });
  });

  test.describe('Refresh Functionality', () => {
    test('should display refresh button in header', async ({ page }) => {
      await mockTaskListResponse(page, [createMockTask()]);

      await page.goto('/#/tasks');

      await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
    });

    test('should reload tasks when refresh button is clicked', async ({ page }) => {
      let requestCount = 0;
      await page.route('**/api/tasks', async (route) => {
        requestCount++;
        if (requestCount === 1) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              tasks: [createMockTask({ name: 'Original Task' })],
              total: 1,
            }),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              tasks: [
                createMockTask({ name: 'Original Task' }),
                createMockTask({ number: '002', name: 'New Task' }),
              ],
              total: 2,
            }),
          });
        }
      });

      await page.goto('/#/tasks');

      // Wait for task list to finish loading
      await expect(page.getByText('Original Task')).toBeVisible();

      // Verify task count (check for "task" text which is part of "1 task total")
      // Regex /\d+ tasks? total/ is safe: no nested quantifiers or ambiguous alternations,
      // so there is no risk of catastrophic backtracking.
      const taskCountText = page.getByText(/\d+ tasks? total/);
      await expect(taskCountText).toBeVisible();

      // Click refresh
      const refreshButton = page.getByRole('button', { name: /refresh/i });
      await refreshButton.click();

      // Wait for new task to appear
      await expect(page.getByText('New Task')).toBeVisible();
      await expect(page.getByText('2 tasks total')).toBeVisible();
    });

    test('should show loading state while refreshing', async ({ page }) => {
      await setupDelayedRefreshRoute(page, 500);

      await page.goto('/#/tasks');

      await expect(page.getByText('Test Task')).toBeVisible();

      const refreshButton = page.getByRole('button', { name: /refresh/i });

      // Click refresh
      await refreshButton.click();

      // Button should be disabled while refreshing
      await expect(refreshButton).toBeDisabled();

      // Check for spinning animation class
      const refreshIcon = refreshButton.locator('svg').first();
      await expect(refreshIcon).toHaveClass(/animate-spin/);

      // Wait for refresh to complete
      await page.waitForTimeout(600);

      // Button should be enabled again
      await expect(refreshButton).not.toBeDisabled();
    });
  });

  test.describe('Special Cases', () => {
    test('should handle tasks with special characters in name', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'Task with "quotes"' }),
        createMockTask({ number: '002', name: "Task with 'apostrophes'" }),
        createMockTask({ number: '003', name: 'Task with <html> tags' }),
      ];

      await mockTaskListResponse(page, mockTasks);

      await page.goto('/#/tasks');

      await expect(page.getByText('Task with "quotes"')).toBeVisible();
      await expect(page.getByText("Task with 'apostrophes'")).toBeVisible();
      await expect(page.getByText('Task with <html> tags')).toBeVisible();
    });

    test('should handle very long task names gracefully', async ({ page }) => {
      const longName = 'This is a very long task name that should be truncated or wrapped appropriately to fit within the card layout without breaking the UI';
      const mockTasks = [createMockTask({ number: '001', name: longName })];

      await mockTaskListResponse(page, mockTasks);

      await page.goto('/#/tasks');

      // Task should be visible (even if truncated)
      await expect(page.getByText(longName, { exact: false })).toBeVisible();
    });

    test('should display page title', async ({ page }) => {
      await mockTaskListResponse(page, []);

      await page.goto('/#/tasks');

      await expect(page.getByRole('heading', { name: /tasks/i })).toBeVisible();
    });
  });
});
