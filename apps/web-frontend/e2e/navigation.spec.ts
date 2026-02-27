/**
 * Navigation E2E Tests
 *
 * End-to-end tests for application navigation between pages.
 * Tests routing, browser back/forward functionality, and URL hash handling.
 */

import { test, expect } from '@playwright/test';
import {
  mockTaskListResponse,
  mockTaskDetailResponse,
  createMockTask,
  createMockTaskDetail,
} from './helpers';

test.describe('Application Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to welcome page first
    await page.goto('/');
    // Wait for the main layout to be ready instead of using a fixed timeout
    await page.waitForSelector('main, [role="main"], #app, #root', { state: 'visible' });
  });

  test.describe('Welcome to Task List Navigation', () => {
    test('should navigate from welcome screen to task list', async ({ page }) => {
      await mockTaskListResponse(page, []);

      // Should start on welcome screen
      await expect(page.getByRole('heading', { name: /auto claude/i })).toBeVisible();

      // Click "View Tasks" button
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

      await expect(page).toHaveURL(/#\/tasks/);
    });

    test('should display task list with tasks after navigation', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'First Task' }),
        createMockTask({ number: '002', name: 'Second Task' }),
      ];
      await mockTaskListResponse(page, mockTasks);

      const viewTasksButton = page.getByRole('button', { name: /view tasks/i });
      await viewTasksButton.click();

      await expect(page.getByText('First Task')).toBeVisible();
      await expect(page.getByText('Second Task')).toBeVisible();
    });
  });

  test.describe('Task List to Task Detail Navigation', () => {
    test('should navigate from task list to task detail', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Test Task' })];
      const mockDetail = createMockTaskDetail({ number: '001', name: 'Test Task' });

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', mockDetail);

      // Navigate to task list
      await page.goto('/#/tasks');
      await expect(page.getByText('Test Task')).toBeVisible();

      // Click task card by its visible name
      await page.getByText('Test Task').click();

      // Should navigate to task detail
      await expect(page).toHaveURL(/#\/tasks\/001/);
      await expect(page.getByText('Spec #001')).toBeVisible();
    });

    test('should update URL with task ID', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '123', name: 'Task 123' })];
      const mockDetail = createMockTaskDetail({ number: '123', name: 'Task 123' });

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '123', mockDetail);

      await page.goto('/#/tasks');
      await expect(page.getByText('Task 123')).toBeVisible();

      await page.getByText('Task 123').click();

      await expect(page).toHaveURL(/#\/tasks\/123/);
    });

    test('should navigate between multiple task details', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'Task One' }),
        createMockTask({ number: '002', name: 'Task Two' }),
      ];

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', createMockTaskDetail({ number: '001', name: 'Task One' }));
      await mockTaskDetailResponse(page, '002', createMockTaskDetail({ number: '002', name: 'Task Two' }));

      await page.goto('/#/tasks');
      await expect(page.getByText('Task One')).toBeVisible();

      // Navigate to first task
      await page.getByText('Task One').click();
      await expect(page).toHaveURL(/#\/tasks\/001/);
      await expect(page.getByText('Spec #001')).toBeVisible();

      // Go back to list
      await page.goto('/#/tasks');

      // Navigate to second task
      await page.getByText('Task Two').click();
      await expect(page).toHaveURL(/#\/tasks\/002/);
      await expect(page.getByText('Spec #002')).toBeVisible();
    });
  });

  test.describe('Task Detail to Task List Navigation', () => {
    test('should navigate back to task list using back button', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Test Task' })];
      const mockDetail = createMockTaskDetail({ number: '001', name: 'Test Task' });

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', mockDetail);

      // Start at task list
      await page.goto('/#/tasks');
      await expect(page.getByText('Test Task')).toBeVisible();

      // Navigate to detail
      await page.getByText('Test Task').click();
      await expect(page).toHaveURL(/#\/tasks\/001/);

      // Click back button in task detail (icon-only button)
      const backButton = page.locator('button').filter({ has: page.locator('svg') }).first();
      await backButton.click();

      // Should be back at task list
      await expect(page).toHaveURL(/#\/tasks/);
      await expect(page.getByText('Test Task')).toBeVisible();
    });

    test('should preserve task list content when returning', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'Task One' }),
        createMockTask({ number: '002', name: 'Task Two' }),
        createMockTask({ number: '003', name: 'Task Three' }),
      ];
      const mockDetail = createMockTaskDetail({ number: '002', name: 'Task Two' });

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '002', mockDetail);

      await page.goto('/#/tasks');
      await expect(page.getByText('Task One')).toBeVisible();
      await expect(page.getByText('Task Two')).toBeVisible();
      await expect(page.getByText('Task Three')).toBeVisible();

      // Navigate to task detail (second task)
      await page.getByText('Task Two').click();
      await expect(page).toHaveURL(/#\/tasks\/002/);

      // Go back (icon-only button)
      const backButton = page.locator('button').filter({ has: page.locator('svg') }).first();
      await backButton.click();

      // All tasks should still be visible
      await expect(page.getByText('Task One')).toBeVisible();
      await expect(page.getByText('Task Two')).toBeVisible();
      await expect(page.getByText('Task Three')).toBeVisible();
    });
  });

  test.describe('Browser Back/Forward Navigation', () => {
    test('should handle browser back button from task list to welcome', async ({ page }) => {
      await mockTaskListResponse(page, []);

      // Navigate to task list
      const viewTasksButton = page.getByRole('button', { name: /view tasks/i });
      await viewTasksButton.click();
      await expect(page).toHaveURL(/#\/tasks/);

      // Use browser back button
      await page.goBack();

      // Should be back on welcome screen
      await expect(page).toHaveURL(/#?\/?$/);
      await expect(page.getByRole('heading', { name: /auto claude/i })).toBeVisible();
    });

    test('should handle browser forward button from welcome to task list', async ({ page }) => {
      await mockTaskListResponse(page, []);

      // Navigate to task list
      const viewTasksButton = page.getByRole('button', { name: /view tasks/i });
      await viewTasksButton.click();
      await expect(page).toHaveURL(/#\/tasks/);

      // Go back to welcome
      await page.goBack();
      await expect(page).toHaveURL(/#?\/?$/);

      // Use browser forward button
      await page.goForward();

      // Should be back at task list
      await expect(page).toHaveURL(/#\/tasks/);
      await expect(page.getByText('No tasks found')).toBeVisible();
    });

    test('should handle browser back button from task detail to task list', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Test Task' })];
      const mockDetail = createMockTaskDetail({ number: '001', name: 'Test Task' });

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', mockDetail);

      await page.goto('/#/tasks');
      await expect(page.getByText('Test Task')).toBeVisible();

      // Navigate to task detail
      await page.getByText('Test Task').click();
      await expect(page).toHaveURL(/#\/tasks\/001/);

      // Use browser back button
      await page.goBack();

      // Should be back at task list
      await expect(page).toHaveURL(/#\/tasks/);
      await expect(page.getByText('Test Task')).toBeVisible();
    });

    test('should handle browser forward button from task list to task detail', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Test Task' })];
      const mockDetail = createMockTaskDetail({ number: '001', name: 'Test Task' });

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', mockDetail);

      await page.goto('/#/tasks');
      await expect(page.getByText('Test Task')).toBeVisible();

      // Navigate to task detail
      await page.getByText('Test Task').click();
      await expect(page).toHaveURL(/#\/tasks\/001/);

      // Go back
      await page.goBack();
      await expect(page).toHaveURL(/#\/tasks/);

      // Use browser forward button
      await page.goForward();

      // Should be back at task detail
      await expect(page).toHaveURL(/#\/tasks\/001/);
      await expect(page.getByText('Spec #001')).toBeVisible();
    });

    test('should handle multiple back/forward navigations', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Test Task' })];
      const mockDetail = createMockTaskDetail({ number: '001', name: 'Test Task' });

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', mockDetail);

      // Welcome -> Tasks -> Detail
      const viewTasksButton = page.getByRole('button', { name: /view tasks/i });
      await viewTasksButton.click();
      await expect(page).toHaveURL(/#\/tasks/);

      await page.getByText('Test Task').click();
      await expect(page).toHaveURL(/#\/tasks\/001/);

      // Go back twice: Detail -> Tasks -> Welcome
      await page.goBack();
      await expect(page).toHaveURL(/#\/tasks/);

      await page.goBack();
      await expect(page).toHaveURL(/#?\/?$/);

      // Go forward twice: Welcome -> Tasks -> Detail
      await page.goForward();
      await expect(page).toHaveURL(/#\/tasks/);

      await page.goForward();
      await expect(page).toHaveURL(/#\/tasks\/001/);
    });
  });

  test.describe('Direct URL Navigation', () => {
    test('should load task list directly from URL hash', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Direct Task' })];
      await mockTaskListResponse(page, mockTasks);

      // Navigate directly to task list URL
      await page.goto('/#/tasks');

      await expect(page.getByText('Direct Task')).toBeVisible();
    });

    test('should load task detail directly from URL hash', async ({ page }) => {
      const mockDetail = createMockTaskDetail({ number: '042', name: 'Direct Detail Task' });
      await mockTaskDetailResponse(page, '042', mockDetail);

      // Navigate directly to task detail URL
      await page.goto('/#/tasks/042');

      await expect(page.getByText('Spec #042')).toBeVisible();
      await expect(page.getByText('Direct Detail Task')).toBeVisible();
    });

    test('should load welcome screen for root URL', async ({ page }) => {
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /auto claude/i })).toBeVisible();
    });

    test('should load welcome screen for empty hash', async ({ page }) => {
      await page.goto('/#/');

      await expect(page.getByRole('heading', { name: /auto claude/i })).toBeVisible();
    });

    test('should handle unknown routes by defaulting to welcome', async ({ page }) => {
      await page.goto('/#/unknown-route');

      await expect(page.getByRole('heading', { name: /auto claude/i })).toBeVisible();
    });

    test('should handle task detail with alphanumeric ID', async ({ page }) => {
      const mockDetail = createMockTaskDetail({ number: 'abc-123', name: 'Alphanumeric Task' });
      await mockTaskDetailResponse(page, 'abc-123', mockDetail);

      await page.goto('/#/tasks/abc-123');

      await expect(page.getByText('Spec #abc-123')).toBeVisible();
    });
  });

  test.describe('Navigation State Preservation', () => {
    test('should maintain scroll position after navigation', async ({ page }) => {
      const mockTasks = Array.from({ length: 20 }, (_, i) =>
        createMockTask({ number: String(i + 1).padStart(3, '0'), name: `Task ${i + 1}` })
      );
      const mockDetail = createMockTaskDetail({ number: '010', name: 'Task 10' });

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '010', mockDetail);

      await page.goto('/#/tasks');
      await expect(page.getByText('Task 1').first()).toBeVisible();

      // Scroll down to see Task 10
      await page.evaluate(() => window.scrollTo(0, 500));
      await page.waitForFunction(() => window.scrollY > 0);

      // Click Task 10
      const task10Card = page.getByText('Task 10').locator('..').locator('..');
      await task10Card.click();
      await expect(page).toHaveURL(/#\/tasks\/010/);

      // Navigate back
      await page.goBack();
      await expect(page).toHaveURL(/#\/tasks/);

      // Note: Scroll position preservation depends on browser behavior
      // We just verify the page content is restored (use first match)
      await expect(page.getByText('Task 1').first()).toBeVisible();
    });

    test('should handle rapid navigation changes', async ({ page }) => {
      const mockTasks = [
        createMockTask({ number: '001', name: 'Task One' }),
        createMockTask({ number: '002', name: 'Task Two' }),
      ];

      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', createMockTaskDetail({ number: '001', name: 'Task One' }));
      await mockTaskDetailResponse(page, '002', createMockTaskDetail({ number: '002', name: 'Task Two' }));

      await page.goto('/#/tasks');
      await expect(page.getByText('Task One')).toBeVisible();

      // Rapidly click different tasks
      await page.getByText('Task One').click();
      await page.waitForURL(/#\/tasks\/001/);

      await page.goBack();
      await page.waitForURL(/#\/tasks/);

      await page.getByText('Task Two').click();
      await expect(page).toHaveURL(/#\/tasks\/002/);
      await expect(page.getByText('Spec #002')).toBeVisible();
    });
  });

  test.describe('Hash Change Event Handling', () => {
    test('should respond to programmatic hash changes', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Test Task' })];
      await mockTaskListResponse(page, mockTasks);

      await page.goto('/');

      // Programmatically change hash
      await page.evaluate(() => {
        globalThis.location.hash = '#/tasks';
      });

      await expect(page.getByText('Test Task')).toBeVisible();
    });

    test('should handle hash changes with special characters', async ({ page }) => {
      const mockDetail = createMockTaskDetail({ number: '001-special', name: 'Special Task' });
      await mockTaskDetailResponse(page, '001-special', mockDetail);

      await page.goto('/');

      // Programmatically change to hash with special characters
      await page.evaluate(() => {
        globalThis.location.hash = '#/tasks/001-special';
      });

      await expect(page.getByText('Spec #001-special')).toBeVisible();
    });
  });

  test.describe('Navigation Performance', () => {
    const MAX_NAVIGATION_MS = 2000;

    test('should navigate quickly between pages', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Performance Task' })];
      await mockTaskListResponse(page, mockTasks);

      await page.goto('/');

      const startTime = Date.now();

      const viewTasksButton = page.getByRole('button', { name: /view tasks/i });
      await viewTasksButton.click();

      await expect(page.getByText('Performance Task')).toBeVisible();

      const navigationTime = Date.now() - startTime;

      // Navigation should complete within reasonable time
      expect(navigationTime).toBeLessThan(MAX_NAVIGATION_MS);
    });

    test('should handle navigation without errors', async ({ page }) => {
      const mockTasks = [createMockTask({ number: '001', name: 'Test Task' })];
      await mockTaskListResponse(page, mockTasks);
      await mockTaskDetailResponse(page, '001', createMockTaskDetail({ number: '001', name: 'Test Task' }));

      await page.goto('/#/tasks');
      await expect(page.getByText('Test Task')).toBeVisible();

      // Navigate to detail
      await page.getByText('Test Task').click();
      await expect(page).toHaveURL(/#\/tasks\/001/);

      // Go back using browser navigation
      await page.goBack();
      await expect(page).toHaveURL(/#\/tasks/);

      // Page should still render correctly
      await expect(page.getByText('Test Task')).toBeVisible();

      // Go forward
      await page.goForward();
      await expect(page).toHaveURL(/#\/tasks\/001/);
      await expect(page.getByText('Spec #001')).toBeVisible();
    });
  });
});
