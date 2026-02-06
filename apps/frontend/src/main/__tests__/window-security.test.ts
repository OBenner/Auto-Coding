/**
 * Unit tests for BrowserWindow security configuration
 * Verifies that renderer process runs with proper sandbox and security settings
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserWindow } from "electron";

// Mock electron modules before any imports
vi.mock("electron", () => {
  let capturedOptions: unknown = null;

  class MockBrowserWindow {
    webContents = {
      send: vi.fn(),
      openDevTools: vi.fn(),
      setWindowOpenHandler: vi.fn(),
      on: vi.fn(),
      once: vi.fn(),
      isDestroyed: vi.fn(() => false),
    };

    constructor(options: unknown) {
      // Capture the options for verification
      capturedOptions = options;
    }

    loadURL = vi.fn(() => Promise.resolve());
    loadFile = vi.fn(() => Promise.resolve());
    show = vi.fn();
    on = vi.fn();
    isDestroyed = vi.fn(() => false);

    // Static method to retrieve captured options
    static getCapturedOptions(): unknown {
      return capturedOptions;
    }

    static resetCapturedOptions(): void {
      capturedOptions = null;
    }
  }

  // Mock process.resourcesPath for icon loading
  if (!process.resourcesPath) {
    process.resourcesPath = "/tmp/test/resources";
  }

  return {
    app: {
      getPath: vi.fn(() => "/tmp/test"),
      getAppPath: vi.fn(() => "/tmp/test"),
      getVersion: vi.fn(() => "0.1.0"),
      isPackaged: false,
      on: vi.fn(),
      whenReady: vi.fn(() => Promise.resolve()),
      quit: vi.fn(),
      setName: vi.fn(),
      getName: vi.fn(() => "Auto Code"),
      dock: {
        setIcon: vi.fn(),
      },
      commandLine: {
        appendSwitch: vi.fn(),
      },
    },
    BrowserWindow: MockBrowserWindow,
    ipcMain: {
      handle: vi.fn(),
      on: vi.fn(),
      removeHandler: vi.fn(),
    },
    shell: {
      openExternal: vi.fn(),
    },
    nativeImage: {
      createFromPath: vi.fn(() => ({ isEmpty: vi.fn(() => false) })),
    },
    session: {
      defaultSession: {
        clearCache: vi.fn(() => Promise.resolve()),
        clearStorageData: vi.fn(() => Promise.resolve()),
      },
    },
    screen: {
      getPrimaryDisplay: vi.fn(() => ({
        workAreaSize: { width: 1920, height: 1080 },
      })),
    },
  };
});

// Mock @electron-toolkit/utils
vi.mock("@electron-toolkit/utils", () => ({
  is: {
    dev: false,
    windows: process.platform === "win32",
    macos: process.platform === "darwin",
    linux: process.platform === "linux",
  },
  electronApp: {
    setAppUserModelId: vi.fn(),
  },
  optimizer: {
    watchWindowShortcuts: vi.fn(),
  },
}));

// Mock electron-log
vi.mock("electron-log/main.js", () => ({
  default: {
    initialize: vi.fn(),
    transports: {
      file: {
        maxSize: 10 * 1024 * 1024,
        format: "",
        fileName: "main.log",
        level: "info",
        getFile: vi.fn(() => ({ path: "/tmp/test.log" })),
      },
      console: {
        level: "warn",
        format: "",
      },
    },
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock other dependencies to prevent side effects
vi.mock("../ipc-setup", () => ({
  setupIpcHandlers: vi.fn(),
}));

vi.mock("../agent", () => ({
  AgentManager: class MockAgentManager {
    on = vi.fn();
    configure = vi.fn();
  },
}));

vi.mock("../terminal-manager", () => ({
  TerminalManager: class MockTerminalManager {
    killAll = vi.fn();
  },
}));

vi.mock("../python-env-manager", () => ({
  pythonEnvManager: {
    on: vi.fn(),
    initialize: vi.fn(() => Promise.resolve()),
  },
}));

vi.mock("../claude-profile/usage-monitor", () => ({
  getUsageMonitor: vi.fn(() => ({
    on: vi.fn(),
    start: vi.fn(),
  })),
}));

vi.mock("../ipc-handlers/terminal-handlers", () => ({
  initializeUsageMonitorForwarding: vi.fn(),
}));

vi.mock("../app-updater", () => ({
  initializeAppUpdater: vi.fn(),
  stopPeriodicUpdates: vi.fn(),
}));

vi.mock("../settings-utils", () => ({
  readSettingsFile: vi.fn(() => ({
    sentryEnabled: false,
    telemetryEnabled: false,
  })),
}));

vi.mock("../app-logger", () => ({
  setupErrorLogging: vi.fn(),
}));

vi.mock("../sentry", () => ({
  initSentryMain: vi.fn(),
}));

vi.mock("../cli-tool-manager", () => ({
  preWarmToolCache: vi.fn(() => Promise.resolve()),
}));

vi.mock("../claude-profile-manager", () => ({
  initializeClaudeProfileManager: vi.fn(() => Promise.resolve()),
  getClaudeProfileManager: vi.fn(() => ({
    on: vi.fn(),
    getMigratedProfileIds: vi.fn(() => []),
    getActiveProfile: vi.fn(() => ({
      id: 'default',
      name: 'Default',
      isDefault: true,
    })),
  })),
}));

vi.mock("../notification-service", () => ({
  notificationService: {
    initialize: vi.fn(),
  },
}));

describe("BrowserWindow Security Configuration", () => {
  beforeEach(() => {
    // Reset captured options before each test
    (BrowserWindow as unknown as { resetCapturedOptions: () => void }).resetCapturedOptions();
    vi.clearAllMocks();
    vi.resetModules(); // Reset module cache to allow fresh imports
  });

  it("should create BrowserWindow with sandbox enabled", async () => {
    // Dynamically import the main module to trigger window creation
    // This must happen after all mocks are set up
    await import("../index");

    // Wait a bit for app.whenReady() to resolve and createWindow() to be called
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Get the captured options from BrowserWindow constructor
    const capturedOptions = (
      BrowserWindow as unknown as { getCapturedOptions: () => Record<string, unknown> }
    ).getCapturedOptions() as { webPreferences?: Record<string, unknown> } | null;

    // Verify options were captured
    expect(capturedOptions).not.toBeNull();
    expect(capturedOptions).toBeDefined();
    expect(capturedOptions?.webPreferences).toBeDefined();

    // Verify security settings
    const webPreferences = capturedOptions?.webPreferences;
    expect(webPreferences?.sandbox).toBe(true);
    expect(webPreferences?.contextIsolation).toBe(true);
    expect(webPreferences?.nodeIntegration).toBe(false);
  });

  it("should have preload script configured", async () => {
    await import("../index");

    // Wait for window creation
    await new Promise((resolve) => setTimeout(resolve, 100));

    const capturedOptions = (
      BrowserWindow as unknown as { getCapturedOptions: () => Record<string, unknown> }
    ).getCapturedOptions() as { webPreferences?: Record<string, unknown> } | null;

    expect(capturedOptions).not.toBeNull();
    expect(capturedOptions?.webPreferences).toBeDefined();
    expect(capturedOptions?.webPreferences?.preload).toBeDefined();
    expect(typeof capturedOptions?.webPreferences?.preload).toBe("string");
    expect(capturedOptions?.webPreferences?.preload).toContain("preload");
  });

  it("should have all critical security settings in webPreferences", async () => {
    await import("../index");

    // Wait for window creation
    await new Promise((resolve) => setTimeout(resolve, 100));

    const capturedOptions = (
      BrowserWindow as unknown as { getCapturedOptions: () => Record<string, unknown> }
    ).getCapturedOptions() as { webPreferences?: Record<string, unknown> } | null;

    expect(capturedOptions).not.toBeNull();
    const webPreferences = capturedOptions?.webPreferences;

    // Verify all security-related settings are present and correct
    expect(webPreferences).toMatchObject({
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
    });
  });
});
