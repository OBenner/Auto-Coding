/**
 * Vitest Test Setup
 *
 * Configures test environment with:
 * - @testing-library/jest-dom matchers
 * - Mock implementations for browser APIs
 * - i18n setup for component testing
 */

import "@testing-library/jest-dom";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Cleanup after each test case
afterEach(() => {
	cleanup();
});

// Mock localStorage
const localStorageMock = {
	getItem: vi.fn(),
	setItem: vi.fn(),
	removeItem: vi.fn(),
	clear: vi.fn(),
};
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Mock WebSocket
class MockWebSocket {
	url: string;
	readyState: number = 0;
	onopen: ((ev: Event) => void) | null = null;
	onmessage: ((ev: MessageEvent) => void) | null = null;
	onerror: ((ev: Event) => void) | null = null;
	onclose: ((ev: CloseEvent) => void) | null = null;

	static CONNECTING = 0;
	static OPEN = 1;
	static CLOSING = 2;
	static CLOSED = 3;

	constructor(url: string) {
		this.url = url;
		this.readyState = MockWebSocket.CONNECTING;
	}

	send(_data: string): void {
		// Mock implementation
	}

	close(): void {
		this.readyState = MockWebSocket.CLOSED;
	}
}

vi.stubGlobal("WebSocket", MockWebSocket);

// Mock ResizeObserver
class MockResizeObserver {
	observe(): void {}
	unobserve(): void {}
	disconnect(): void {}
}

vi.stubGlobal("ResizeObserver", MockResizeObserver);

// Mock matchMedia
Object.defineProperty(window, "matchMedia", {
	writable: true,
	value: vi.fn().mockImplementation((query: string) => ({
		matches: false,
		media: query,
		onchange: null,
		addListener: vi.fn(),
		removeListener: vi.fn(),
		addEventListener: vi.fn(),
		removeEventListener: vi.fn(),
		dispatchEvent: vi.fn(),
	})),
});

// Mock scrollTo
Object.defineProperty(window, "scrollTo", {
	writable: true,
	value: vi.fn(),
});

// Mock i18next
vi.mock("react-i18next", () => ({
	useTranslation: () => ({
		t: (key: string) => key,
		i18n: {
			language: "en",
			changeLanguage: vi.fn(),
		},
	}),
	Trans: ({ children }: { children: React.ReactNode }) => children,
	initReactI18next: {
		type: "3rdParty",
		init: vi.fn(),
	},
}));

// Mock xterm.js for Terminal component tests
vi.mock("@xterm/xterm", () => ({
	Terminal: vi.fn().mockImplementation(() => ({
		open: vi.fn(),
		write: vi.fn(),
		writeln: vi.fn(),
		clear: vi.fn(),
		focus: vi.fn(),
		dispose: vi.fn(),
		loadAddon: vi.fn(),
		onData: vi.fn(),
		onResize: vi.fn(),
	})),
}));

vi.mock("@xterm/addon-fit", () => ({
	FitAddon: vi.fn().mockImplementation(() => ({
		fit: vi.fn(),
		dispose: vi.fn(),
	})),
}));
