/**
 * Task List E2E Tests
 *
 * End-to-end tests for the TaskList page and navigation flows.
 * Tests user interactions with the task list, including viewing tasks,
 * navigation to task details, error handling, and refresh functionality.
 */

import { test, expect, type Page } from '@playwright/test';

/**
 * Helper: Mock API response for task list
 */
async function mockTaskListResponse(page: Page, tasks: any[] = [], delay = 0) {
  await page.route('**/api/tasks', async (route) => {
    if (delay > 0) {
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        tasks,
        total: tasks.length,
      }),
    });
  });
}

/**
 * Helper: Mock API error response for task list
 */
async function mockTaskListError(page: Page, statusCode = 500, errorMessage = 'Internal Server Error') {
  await page.route('**/api/tasks', async (route) => {
    await route.fulfill({
      status: statusCode,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: errorMessage,
      }),
    });
  });
}

/**
 * Helper: Mock API response for task detail
 */
async function mockTaskDetailResponse(page: Page, taskId: string, taskDetail: any, delay = 0) {
  await page.route(`**/api/tasks/${taskId}`, async (route) => {
    if (delay > 0) {
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(taskDetail),
    });
  });
}

/**
 * Helper: Create mock task summary
 */
function createMockTask(overrides: any = {}) {
  return {
    number: '001',
    name: 'Test Task',
    folder: '001-test-task',
    status: 'backlog',
    progress: '0',
    has_build: false,
    ...overrides,
  };
}

/**
 * Helper: Create mock task detail
 */
function createMockTaskDetail(overrides: any = {}) {
  return {
    number: '001',
    name: 'Test Task',
    folder: '001-test-task',
    status: 'backlog',
    has_build: false,
    spec_content: '# Test Specification\n\nThis is a test spec.',
    progress: {
      percentage: 0,
      completed: 0,
      in_progress: 0,
      pending: 5,
      failed: 0,
    },
    ...overrides,
  };
}

test.describe('Task List Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to welcome page first
    await page.goto('http://localhost:3000');
    // Wait for initial loading to complete
    await page.waitForTimeout(600);
  });

  test.describe('Navigation', () => {
    test('should navigate to task list from welcome screen', async ({ page }) => {
      await mockTaskListResponse(page, []);

      // Click "View Tasks" button on welcome screen
      const viewTasksButton = page.getByRole('button', { name: /view tasks/i });
      await viewTasksButton.click();

      // Should navigate to tasks page
      await expect(page).toHaveURL(/#\/tasks/);
      await expect(page.getByText('No tasks found')).toBeVisible();
    });

    test('should update URL hash when navigating to tasks', async ({ page }) => {
      await mockTaskListResponse(page, []);

      const viewTasksButton = page.getByRole('button', { name: /view tasks/i });
      await viewTasksButton.click();

      expect(page.url()).toContain('#/tasks');
    });
  });

  test.describe('Loading State', () => {
    test('should display loading spinner while fetching tasks', async ({ page }) => {
      // Mock with a delay to keep loading state visible
      await mockTaskListResponse(page, [], 1000);

      await page.goto('http://localhost:3000#/tasks');

      // Should show loading state
      await expect(page.getByText('Loading...')).toBeVisible();

      // Wait for loading to complete
      await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 2000 });
    });
  });

  test.describe('Empty State', () => {
    test('should display empty state when no tasks exist', async ({ page }) => {
      await mockTaskListResponse(page, []);

      await page.goto('http://localhost:3000#/tasks');

      await expect(page.getByText('No tasks found')).toBeVisible();
      await expect(page.getByText('Tasks will appear here once you create specs')).toBeVisible();
    });

    test('should show refresh button in empty state', async ({ page }) => {
      await mockTaskListResponse(page, []);

      await page.goto('http://localhost:3000#/tasks');

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

      await page.goto('http://localhost:3000#/tasks');

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

      await page.goto('http://localhost:3000#/tasks');

      await expect(page.getByText('3 tasks total')).toBeVisible();
    });

    test('should display singular task count for one task', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Single Task' })];

      await mockTaskListResponse(page, mockTasks);

      await page.goto('http://localhost:3000#/tasks');

      await expect(page.getByText('1 task total')).toBeVisible();
    });

    test('should display task status in description', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'Test Task', status: 'in_progress' }),
      ];

      await mockTaskListResponse(page, mockTasks);

      await page.goto('http://localhost:3000#/tasks');

      await expect(page.getByText('Test Task')).toBeVisible();
      await expect(page.getByText(/Status: in_progress/)).toBeVisible();
    });

    test('should render tasks in grid layout', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'Task 1' }),
        createMockTask({ number: '002', name: 'Task 2' }),
      ];

      await mockTaskListResponse(page, mockTasks);

      await page.goto('http://localhost:3000#/tasks');

      await expect(page.getByText('Task 1')).toBeVisible();

      // Check that the grid container exists
      const gridContainer = page.locator('.grid').first();
      await expect(gridContainer).toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('should display error message when API fails', async ({ page }) => {
      await mockTaskListError(page, 500, 'Failed to load tasks');

      await page.goto('http://localhost:3000#/tasks');

      await expect(page.getByText('Error')).toBeVisible();
      await expect(page.getByText('Failed to load tasks')).toBeVisible();
    });

    test('should show "Try Again" button on error', async ({ page }) => {
      await mockTaskListError(page, 500, 'Network error');

      await page.goto('http://localhost:3000#/tasks');

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

      await page.goto('http://localhost:3000#/tasks');

      // Wait for error state
      await expect(page.getByText('Network error')).toBeVisible();

      // Click "Try Again"
      const tryAgainButton = page.getByRole('button', { name: /try again/i });
      await tryAgainButton.click();

      // Should show recovered task
      await expect(page.getByText('Recovered Task')).toBeVisible();
    });
  });

  test.describe('Task Click Navigation', () => {
    test('should navigate to task detail when task card is clicked', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Clickable Task' })];
      const mockDetail = createMockTaskDetail({ number: '001', name: 'Clickable Task' });

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', mockDetail);

      await page.goto('http://localhost:3000#/tasks');

      // Wait for task to be visible
      await expect(page.getByText('Clickable Task')).toBeVisible();

      // Click the task card
      const taskCard = page.locator('[class*="cursor-pointer"]').first();
      await taskCard.click();

      // Should navigate to task detail page
      await expect(page).toHaveURL(/#\/tasks\/001/);
      await expect(page.getByText('Spec #001')).toBeVisible();
    });

    test('should handle clicks on multiple tasks independently', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'Task One' }),
        createMockTask({ number: '002', name: 'Task Two' }),
      ];

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', createMockTaskDetail({ number: '001', name: 'Task One' }));
      await mockTaskDetailResponse(page, '002', createMockTaskDetail({ number: '002', name: 'Task Two' }));

      await page.goto('http://localhost:3000#/tasks');

      await expect(page.getByText('Task One')).toBeVisible();

      // Click first task
      const taskOne = page.locator('[class*="cursor-pointer"]').first();
      await taskOne.click();

      await expect(page).toHaveURL(/#\/tasks\/001/);

      // Go back to task list
      await page.goto('http://localhost:3000#/tasks');

      // Click second task
      const taskTwo = page.locator('[class*="cursor-pointer"]').nth(1);
      await taskTwo.click();

      await expect(page).toHaveURL(/#\/tasks\/002/);
    });
  });

  test.describe('Refresh Functionality', () => {
    test('should display refresh button in header', async ({ page }) => {
      await mockTaskListResponse(page, [createMockTask()]);

      await page.goto('http://localhost:3000#/tasks');

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

      await page.goto('http://localhost:3000#/tasks');

      // Wait for task list to finish loading
      await expect(page.getByText('Original Task')).toBeVisible();

      // Verify task count (check for "task" text which is part of "1 task total")
      const taskCountText = page.getByText(/\d+ tasks? total/);
      await expect(taskCountText).toBeVisible();

      // Click refresh
      const refreshButton = page.getByRole('button', { name: /refresh/i });
      await refreshButton.click();

      // Wait for new task to appear
      await expect(page.getByText('New Task')).toBeVisible();
      await expect(page.getByText('2 tasks total')).toBeVisible();
    });

    test('should disable refresh button while refreshing', async ({ page }) => {
      let firstCall = true;
      await page.route('**/api/tasks', async (route) => {
        if (firstCall) {
          firstCall = false;
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              tasks: [createMockTask()],
              total: 1,
            }),
          });
        } else {
          // Add delay for second call
          await new Promise((resolve) => setTimeout(resolve, 500));
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              tasks: [createMockTask()],
              total: 1,
            }),
          });
        }
      });

      await page.goto('http://localhost:3000#/tasks');

      await expect(page.getByText('Test Task')).toBeVisible();

      const refreshButton = page.getByRole('button', { name: /refresh/i });

      // Click refresh
      await refreshButton.click();

      // Button should be disabled while refreshing
      await expect(refreshButton).toBeDisabled();

      // Wait for refresh to complete
      await page.waitForTimeout(600);

      // Button should be enabled again
      await expect(refreshButton).not.toBeDisabled();
    });

    test('should show spinning icon while refreshing', async ({ page }) => {
      let firstCall = true;
      await page.route('**/api/tasks', async (route) => {
        if (firstCall) {
          firstCall = false;
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              tasks: [createMockTask()],
              total: 1,
            }),
          });
        } else {
          await new Promise((resolve) => setTimeout(resolve, 500));
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              tasks: [createMockTask()],
              total: 1,
            }),
          });
        }
      });

      await page.goto('http://localhost:3000#/tasks');

      await expect(page.getByText('Test Task')).toBeVisible();

      const refreshButton = page.getByRole('button', { name: /refresh/i });
      await refreshButton.click();

      // Check for spinning animation class
      const refreshIcon = refreshButton.locator('svg').first();
      await expect(refreshIcon).toHaveClass(/animate-spin/);
    });
  });

  test.describe('Browser Navigation', () => {
    test('should handle browser back button from task detail to task list', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Navigation Test' })];
      const mockDetail = createMockTaskDetail({ number: '001', name: 'Navigation Test' });

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', mockDetail);

      await page.goto('http://localhost:3000#/tasks');
      await expect(page.getByText('Navigation Test')).toBeVisible();

      // Navigate to task detail
      const taskCard = page.locator('[class*="cursor-pointer"]').first();
      await taskCard.click();

      await expect(page).toHaveURL(/#\/tasks\/001/);

      // Use browser back button
      await page.goBack();

      // Should be back on task list
      await expect(page).toHaveURL(/#\/tasks/);
      await expect(page.getByText('Navigation Test')).toBeVisible();
    });

    test('should preserve task list state after returning from detail page', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'Task 1' }),
        createMockTask({ number: '002', name: 'Task 2' }),
      ];
      const mockDetail = createMockTaskDetail({ number: '001', name: 'Task 1' });

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', mockDetail);

      await page.goto('http://localhost:3000#/tasks');

      // Verify both tasks are visible
      await expect(page.getByText('Task 1')).toBeVisible();
      await expect(page.getByText('Task 2')).toBeVisible();

      // Navigate to detail
      const taskCard = page.locator('[class*="cursor-pointer"]').first();
      await taskCard.click();

      await expect(page).toHaveURL(/#\/tasks\/001/);

      // Go back
      await page.goBack();

      // Both tasks should still be visible (no re-fetch needed)
      await expect(page.getByText('Task 1')).toBeVisible();
      await expect(page.getByText('Task 2')).toBeVisible();
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

      await page.goto('http://localhost:3000#/tasks');

      await expect(page.getByText('Task with "quotes"')).toBeVisible();
      await expect(page.getByText("Task with 'apostrophes'")).toBeVisible();
      await expect(page.getByText('Task with <html> tags')).toBeVisible();
    });

    test('should handle very long task names gracefully', async ({ page }) => {
      const longName = 'This is a very long task name that should be truncated or wrapped appropriately to fit within the card layout without breaking the UI';
      const mockTasks = [createMockTask({ number: '001', name: longName })];

      await mockTaskListResponse(page, mockTasks);

      await page.goto('http://localhost:3000#/tasks');

      // Task should be visible (even if truncated)
      await expect(page.getByText(longName, { exact: false })).toBeVisible();
    });

    test('should display page title', async ({ page }) => {
      await mockTaskListResponse(page, []);

      await page.goto('http://localhost:3000#/tasks');

      await expect(page.getByRole('heading', { name: /tasks/i })).toBeVisible();
    });
  });
});
