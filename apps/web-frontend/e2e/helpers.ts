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
