/**
 * Test setup file for Vitest
 */
import { vi, beforeEach, afterEach } from 'vitest';
import { mkdirSync, mkdtempSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import path from 'path';

// Mock localStorage for tests that need it
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    })
  };
})();

// Make localStorage available globally
Object.defineProperty(global, 'localStorage', {
  value: localStorageMock
});

// Mock scrollIntoView for Radix Select in jsdom
if (typeof HTMLElement !== 'undefined' && !HTMLElement.prototype.scrollIntoView) {
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    value: vi.fn(),
    writable: true
  });
}

// Keep Radix/browser events inside jsdom's Event hierarchy on Node versions
// that expose their own global CustomEvent constructor.
if (typeof window !== 'undefined' && typeof window.CustomEvent === 'function') {
  Object.defineProperty(globalThis, 'CustomEvent', {
    value: window.CustomEvent,
    configurable: true,
    writable: true
  });
}

// Mock requestAnimationFrame/cancelAnimationFrame for jsdom
// Required by useXterm.ts which uses requestAnimationFrame for initial fit
if (typeof global.requestAnimationFrame === 'undefined') {
  global.requestAnimationFrame = vi.fn((callback: FrameRequestCallback) => {
    return setTimeout(() => callback(Date.now()), 0) as unknown as number;
  });
  global.cancelAnimationFrame = vi.fn((id: number) => {
    clearTimeout(id);
  });
}

// Base directory scoped to this worker process so parallel vitest workers
// never touch each other's files. mkdtemp creates an unpredictable 0700
// directory, so no other local user can pre-create or tamper with it.
const WORKER_DATA_DIR = mkdtempSync(path.join(tmpdir(), 'auto-code-ui-tests-'));

// Test data directory for isolated file operations - reassigned to a unique
// directory before each test, and only that directory is ever cleaned up
export let TEST_DATA_DIR = WORKER_DATA_DIR;

// Create fresh test directory before each test
beforeEach(() => {
  // Clear localStorage
  localStorageMock.clear();

  // Unique subdirectory per test; never delete the shared parent
  const testId = `test-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  TEST_DATA_DIR = path.join(WORKER_DATA_DIR, testId);
  mkdirSync(path.join(TEST_DATA_DIR, 'store'), { recursive: true });
});

// Clean up this test's directory after each test
afterEach(() => {
  vi.clearAllMocks();
  vi.resetModules();
  rmSync(TEST_DATA_DIR, { recursive: true, force: true });
});

// Mock window.electronAPI for renderer tests
if (typeof window !== 'undefined') {
  (window as unknown as { electronAPI: unknown }).electronAPI = {
    addProject: vi.fn(),
    removeProject: vi.fn(),
    getProjects: vi.fn(),
    updateProjectSettings: vi.fn(),
    getTasks: vi.fn(),
    createTask: vi.fn(),
    startTask: vi.fn(),
    stopTask: vi.fn(),
    submitReview: vi.fn(),
    onTaskProgress: vi.fn(() => vi.fn()),
    onTaskError: vi.fn(() => vi.fn()),
    onTaskLog: vi.fn(() => vi.fn()),
    onTaskStatusChange: vi.fn(() => vi.fn()),
    getSpecContent: vi.fn().mockResolvedValue({ success: true, data: null }),
    getTokenStats: vi.fn().mockResolvedValue({ success: true, data: null }),
    getCostReport: vi.fn().mockResolvedValue({ success: false, error: 'not available' }),
    getImplementationPlan: vi.fn().mockResolvedValue({ success: true, data: null }),
    getGenericEditArtifactManifest: vi.fn().mockResolvedValue({ success: true, data: null }),
    getQAReport: vi.fn().mockResolvedValue({ success: true, data: null }),
    getQAEscalation: vi.fn().mockResolvedValue({ success: true, data: null }),
    getVerificationReport: vi.fn().mockResolvedValue({ success: true, data: null }),
    getSettings: vi.fn(),
    saveSettings: vi.fn(),
    selectDirectory: vi.fn(),
    getAppVersion: vi.fn(),
    // Tab state persistence (IPC-based)
    getTabState: vi.fn().mockResolvedValue({
      success: true,
      data: { openProjectIds: [], activeProjectId: null, tabOrder: [] }
    }),
    saveTabState: vi.fn().mockResolvedValue({ success: true }),
    // Profile-related API methods (API Profile feature)
    getAPIProfiles: vi.fn(),
    saveAPIProfile: vi.fn(),
    updateAPIProfile: vi.fn(),
    deleteAPIProfile: vi.fn(),
    setActiveAPIProfile: vi.fn(),
    testConnection: vi.fn()
  };
}

// Sanitize a value for safe logging - strips control characters and truncates
function sanitizeForLog(value: unknown): string {
  return String(value).replace(/\p{Cc}/gu, '').slice(0, 500);
}

// Suppress console errors in tests unless explicitly testing error scenarios
const originalConsoleError = console.error;
console.error = (...args: unknown[]) => {
  const message = sanitizeForLog(args[0] ?? '');
  if (message.includes('[TEST]')) {
    // Join into single sanitized string to prevent log injection
    originalConsoleError(args.map(sanitizeForLog).join(' '));
  }
};
