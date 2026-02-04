/**
 * Unit tests for Content Security Policy (CSP) enforcement
 * Verifies that CSP headers are properly injected via session.defaultSession.webRequest
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { session } from "electron";
import { CSP_CONFIG, CSP_DIRECTIVES, validateCSP } from "../security/csp-config";

// Mock electron modules before any imports
vi.mock("electron", () => {
  // Capture the onHeadersReceived callback for testing
  let capturedCallback: ((details: unknown, callback: unknown) => void) | null = null;

  const mockWebRequest = {
    onHeadersReceived: vi.fn((callback: (details: unknown, callbackFn: unknown) => void) => {
      capturedCallback = callback;
    }),
  };

  const mockSession = {
    defaultSession: {
      webRequest: mockWebRequest,
      clearCache: vi.fn(() => Promise.resolve()),
      clearStorageData: vi.fn(() => Promise.resolve()),
    },
  };

  // Expose a way to get the captured callback for testing
  (mockSession.defaultSession.webRequest as any).getCapturedCallback = () => capturedCallback;
  (mockSession.defaultSession.webRequest as any).resetCapturedCallback = () => {
    capturedCallback = null;
  };

  class MockBrowserWindow {
    webContents = {
      send: vi.fn(),
      openDevTools: vi.fn(),
      setWindowOpenHandler: vi.fn(),
      on: vi.fn(),
      once: vi.fn(),
      isDestroyed: vi.fn(() => false),
    };

    constructor(options: unknown) {}

    loadURL = vi.fn(() => Promise.resolve());
    loadFile = vi.fn(() => Promise.resolve());
    show = vi.fn();
    on = vi.fn();
    isDestroyed = vi.fn(() => false);
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
      getName: vi.fn(() => "Auto Claude"),
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
    session: mockSession,
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
      avatarUrl: null,
    })),
  })),
}));

describe("CSP Configuration", () => {
  it("should export a valid CSP_CONFIG string", () => {
    expect(typeof CSP_CONFIG).toBe("string");
    expect(CSP_CONFIG.length).toBeGreaterThan(0);
  });

  it("should contain all required CSP directives", () => {
    const requiredDirectives = [
      "default-src",
      "script-src",
      "style-src",
      "img-src",
      "connect-src",
      "font-src",
      "object-src",
      "base-uri",
      "form-action",
      "frame-ancestors"
    ];

    requiredDirectives.forEach(directive => {
      expect(CSP_CONFIG).toContain(directive);
    });
  });

  it("should have 'self' in default-src directive", () => {
    expect(CSP_DIRECTIVES['default-src']).toContain("'self'");
  });

  it("should have strict script-src directive (no unsafe-inline or unsafe-eval)", () => {
    expect(CSP_DIRECTIVES['script-src']).toBe("'self'");
    expect(CSP_DIRECTIVES['script-src']).not.toContain("'unsafe-inline'");
    expect(CSP_DIRECTIVES['script-src']).not.toContain("'unsafe-eval'");
  });

  it("should allow Google Fonts in font-src directive", () => {
    expect(CSP_DIRECTIVES['font-src']).toContain("https://fonts.gstatic.com");
  });

  it("should allow Sentry in connect-src directive", () => {
    expect(CSP_DIRECTIVES['connect-src']).toContain("https://*.ingest.us.sentry.io");
  });

  it("should disallow plugins via object-src directive", () => {
    expect(CSP_DIRECTIVES['object-src']).toBe("'none'");
  });

  it("should disallow framing via frame-ancestors directive", () => {
    expect(CSP_DIRECTIVES['frame-ancestors']).toBe("'none'");
  });

  it("should validate CSP using validateCSP helper", () => {
    expect(validateCSP(CSP_CONFIG)).toBe(true);
  });

  it("should detect invalid CSP strings", () => {
    const invalidCSP = "default-src 'self'"; // Missing other required directives
    expect(validateCSP(invalidCSP)).toBe(false);
  });
});

describe("CSP Enforcement via session.defaultSession.webRequest", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset captured callback
    const webRequest = (session.defaultSession.webRequest as any);
    if (webRequest.resetCapturedCallback) {
      webRequest.resetCapturedCallback();
    }
  });

  it("should register onHeadersReceived callback during app initialization", async () => {
    // Import index.ts to trigger app initialization
    await import("../index");

    // Verify that onHeadersReceived was called
    expect(session.defaultSession.webRequest.onHeadersReceived).toHaveBeenCalled();
    expect(session.defaultSession.webRequest.onHeadersReceived).toHaveBeenCalledWith(
      expect.any(Function)
    );
  });

  it("should inject CSP header into response headers", async () => {
    // Import index.ts to trigger app initialization
    await import("../index");

    // Get the captured callback
    const webRequest = session.defaultSession.webRequest as any;
    const callback = webRequest.getCapturedCallback?.();

    expect(callback).toBeDefined();

    if (callback) {
      // Simulate a request with response headers
      const mockDetails = {
        responseHeaders: {
          'content-type': ['text/html'],
        },
      };

      let capturedResult: any = null;
      const mockCallback = (result: any) => {
        capturedResult = result;
      };

      // Call the onHeadersReceived callback
      callback(mockDetails, mockCallback);

      // Verify CSP header was injected
      expect(capturedResult).toBeDefined();
      expect(capturedResult.responseHeaders).toBeDefined();
      expect(capturedResult.responseHeaders['Content-Security-Policy']).toBeDefined();
      expect(capturedResult.responseHeaders['Content-Security-Policy']).toEqual([CSP_CONFIG]);
    }
  });

  it("should preserve existing response headers when injecting CSP", async () => {
    // Import index.ts to trigger app initialization
    await import("../index");

    // Get the captured callback
    const webRequest = session.defaultSession.webRequest as any;
    const callback = webRequest.getCapturedCallback?.();

    expect(callback).toBeDefined();

    if (callback) {
      // Simulate a request with multiple response headers
      const mockDetails = {
        responseHeaders: {
          'content-type': ['text/html'],
          'cache-control': ['no-cache'],
          'x-custom-header': ['custom-value'],
        },
      };

      let capturedResult: any = null;
      const mockCallback = (result: any) => {
        capturedResult = result;
      };

      // Call the onHeadersReceived callback
      callback(mockDetails, mockCallback);

      // Verify all original headers are preserved
      expect(capturedResult.responseHeaders['content-type']).toEqual(['text/html']);
      expect(capturedResult.responseHeaders['cache-control']).toEqual(['no-cache']);
      expect(capturedResult.responseHeaders['x-custom-header']).toEqual(['custom-value']);

      // Verify CSP header was added
      expect(capturedResult.responseHeaders['Content-Security-Policy']).toEqual([CSP_CONFIG]);
    }
  });

  it("should handle requests with no existing response headers", async () => {
    // Import index.ts to trigger app initialization
    await import("../index");

    // Get the captured callback
    const webRequest = session.defaultSession.webRequest as any;
    const callback = webRequest.getCapturedCallback?.();

    expect(callback).toBeDefined();

    if (callback) {
      // Simulate a request with no response headers
      const mockDetails = {
        responseHeaders: {},
      };

      let capturedResult: any = null;
      const mockCallback = (result: any) => {
        capturedResult = result;
      };

      // Call the onHeadersReceived callback
      callback(mockDetails, mockCallback);

      // Verify CSP header was injected
      expect(capturedResult).toBeDefined();
      expect(capturedResult.responseHeaders).toBeDefined();
      expect(capturedResult.responseHeaders['Content-Security-Policy']).toEqual([CSP_CONFIG]);
    }
  });

  it("should inject complete CSP policy with all directives", async () => {
    // Import index.ts to trigger app initialization
    await import("../index");

    // Get the captured callback
    const webRequest = session.defaultSession.webRequest as any;
    const callback = webRequest.getCapturedCallback?.();

    expect(callback).toBeDefined();

    if (callback) {
      const mockDetails = {
        responseHeaders: {},
      };

      let capturedResult: any = null;
      const mockCallback = (result: any) => {
        capturedResult = result;
      };

      // Call the onHeadersReceived callback
      callback(mockDetails, mockCallback);

      // Verify the injected CSP contains all required directives
      const injectedCSP = capturedResult.responseHeaders['Content-Security-Policy'][0];
      expect(validateCSP(injectedCSP)).toBe(true);

      // Verify specific security-critical directives
      expect(injectedCSP).toContain("script-src 'self'");
      expect(injectedCSP).toContain("object-src 'none'");
      expect(injectedCSP).toContain("frame-ancestors 'none'");
    }
  });
});
