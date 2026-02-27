/**
 * Shared E2E Test Helpers
 *
 * Common mock factories and API route helpers shared across E2E test specs.
 */

import { type Page } from '@playwright/test';

export async function mockTaskListResponse(page: Page, tasks: any[] = [], delay = 0) {
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

export async function mockTaskListError(
  page: Page,
  statusCode = 500,
  errorMessage = 'Internal Server Error'
) {
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

export async function mockTaskDetailResponse(
  page: Page,
  taskId: string,
  taskDetail: any,
  delay = 0
) {
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

export function createMockTask(overrides: any = {}) {
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
 * Navigate directly to a task detail page.
 * Sets up route mocks, navigates to the task list, then clicks the task.
 */
export async function navigateToTaskDetail(
  page: Page,
  taskNum: string,
  taskName: string
): Promise<void> {
  await mockTaskListResponse(page, [createMockTask({ number: taskNum, name: taskName })]);
  await mockTaskDetailResponse(page, taskNum, createMockTaskDetail({ number: taskNum, name: taskName }));
  await page.goto('/#/tasks');
  await page.getByText(taskName).click();
}

/**
 * Set up route mocks for a two-task list and navigate to it.
 * Tasks are "Task One" (#001) and "Task Two" (#002).
 */
export async function setupTwoTaskNavigation(page: Page): Promise<void> {
  const tasks = [
    createMockTask({ number: '001', name: 'Task One' }),
    createMockTask({ number: '002', name: 'Task Two' }),
  ];
  await mockTaskListResponse(page, tasks);
  await mockTaskDetailResponse(page, '001', createMockTaskDetail({ number: '001', name: 'Task One' }));
  await mockTaskDetailResponse(page, '002', createMockTaskDetail({ number: '002', name: 'Task Two' }));
  await page.goto('/#/tasks');
}

/**
 * Set up a two-phase route: first request returns firstBody (with firstStatus),
 * subsequent requests return secondBody with status 200.
 */
export async function setupTwoPhaseRoute(
  page: Page,
  firstBody: Record<string, unknown>,
  secondBody: Record<string, unknown>,
  firstStatus = 200
): Promise<void> {
  let requestCount = 0;
  await page.route('**/api/tasks', async (route) => {
    requestCount++;
    if (requestCount === 1) {
      await route.fulfill({
        status: firstStatus,
        contentType: 'application/json',
        body: JSON.stringify(firstBody),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(secondBody),
      });
    }
  });
}

/**
 * Set up a delayed refresh route for testing button/spinner state during refresh.
 * First request responds immediately; subsequent requests are delayed by delayMs.
 */
export async function setupDelayedRefreshRoute(page: Page, delayMs = 500): Promise<void> {
  let firstCall = true;
  await page.route('**/api/tasks', async (route) => {
    if (firstCall) {
      firstCall = false;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ tasks: [createMockTask()], total: 1 }),
      });
    } else {
      await new Promise<void>((resolve) => setTimeout(resolve, delayMs));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ tasks: [createMockTask()], total: 1 }),
      });
    }
  });
}

export function createMockTaskDetail(overrides: any = {}) {
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
