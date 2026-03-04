/**
 * Terminal Component Tests
 *
 * Tests for the Terminal component which uses xterm.js for rendering
 * and WebSocket for PTY communication.
 */

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TerminalComponent } from "../Terminal";

// Track WebSocket instances created during tests
let wsInstances: MockWebSocketInstance[] = [];

interface MockWebSocketInstance {
	url: string;
	readyState: number;
	onopen: ((ev: Event) => void) | null;
	onmessage: ((ev: MessageEvent) => void) | null;
	onerror: ((ev: Event) => void) | null;
	onclose: ((ev: CloseEvent) => void) | null;
	send: (data: string) => void;
	close: () => void;
}

// Create a fresh mock WebSocket for each test
function createMockWebSocket() {
	wsInstances = [];

	const MockWS = vi.fn().mockImplementation((url: string) => {
		const instance: MockWebSocketInstance = {
			url,
			readyState: 0,
			onopen: null,
			onmessage: null,
			onerror: null,
			onclose: null,
			send: vi.fn(),
			close: vi.fn(),
		};
		wsInstances.push(instance);
		return instance;
	});

	// Add static constants
	MockWS.CONNECTING = 0;
	MockWS.OPEN = 1;
	MockWS.CLOSING = 2;
	MockWS.CLOSED = 3;

	vi.stubGlobal("WebSocket", MockWS);
	return MockWS;
}

describe("TerminalComponent", () => {
	let MockWebSocket: ReturnType<typeof createMockWebSocket>;

	beforeEach(() => {
		vi.clearAllMocks();
		MockWebSocket = createMockWebSocket();
		// Reset localStorage mock
		vi.mocked(localStorage.getItem).mockReturnValue("test-token");
	});

	describe("Rendering", () => {
		it("renders terminal container", () => {
			render(<TerminalComponent />);

			// Should have terminal header
			expect(screen.getByText("Terminal")).toBeInTheDocument();
		});

		it("displays custom title when provided", () => {
			render(<TerminalComponent title="Custom Terminal" />);

			expect(screen.getByText("Custom Terminal")).toBeInTheDocument();
		});

		it("shows connecting status initially", () => {
			render(<TerminalComponent />);

			expect(screen.getByText("Connecting...")).toBeInTheDocument();
		});

		it("shows close button when onClose is provided", () => {
			const onClose = vi.fn();
			render(<TerminalComponent onClose={onClose} />);

			// Find the close button by looking for the X icon
			const buttons = screen.getAllByRole("button");
			const closeButton = buttons.find((btn) =>
				btn.querySelector("svg.lucide-x"),
			);
			expect(closeButton).toBeInTheDocument();
		});

		it("does not show close button when onClose is not provided", () => {
			render(<TerminalComponent />);

			// Look for buttons with X icon - there should be none
			const buttons = screen.queryAllByRole("button");
			const closeButton = buttons.find((btn) =>
				btn.querySelector("svg.lucide-x"),
			);
			expect(closeButton).toBeUndefined();
		});
	});

	describe("Connection Status", () => {
		it("shows error state when no auth token available", () => {
			vi.mocked(localStorage.getItem).mockReturnValue(null);

			render(<TerminalComponent />);

			// Without a token, it should show an error
			expect(screen.getByText("Connection Error")).toBeInTheDocument();
		});

		it("uses provided token over localStorage", () => {
			render(<TerminalComponent token="provided-token" wsUrl="ws://test" />);

			// Check that WebSocket was called with the provided token
			expect(MockWebSocket).toHaveBeenCalledWith(
				expect.stringContaining("token=provided-token"),
			);
		});

		it("builds correct WebSocket URL with session ID", () => {
			render(
				<TerminalComponent
					token="test-token"
					wsUrl="ws://localhost:8000"
					sessionId="my-session"
				/>,
			);

			expect(MockWebSocket).toHaveBeenCalledWith(
				"ws://localhost:8000/ws/terminal?token=test-token&session_id=my-session",
			);
		});
	});

	describe("Interactions", () => {
		it("calls onClose when close button is clicked", () => {
			const onClose = vi.fn();
			render(<TerminalComponent onClose={onClose} />);

			// Find and click close button (the X icon button)
			const buttons = screen.getAllByRole("button");
			const closeButton = buttons.find((btn) =>
				btn.querySelector("svg.lucide-x"),
			);

			if (closeButton) {
				fireEvent.click(closeButton);
				expect(onClose).toHaveBeenCalledTimes(1);
			}
		});

		it("calls onActivate when terminal is clicked", () => {
			const onActivate = vi.fn();
			const { container } = render(<TerminalComponent onActivate={onActivate} />);

			// Click on the terminal container
			const terminalContainer = container.querySelector(
				".flex.flex-col.h-full",
			);
			if (terminalContainer) {
				fireEvent.click(terminalContainer);
				expect(onActivate).toHaveBeenCalledTimes(1);
			}
		});

		it("applies active ring styling when isActive is true", () => {
			const { container } = render(<TerminalComponent isActive={true} />);

			const terminalContainer = container.querySelector(".ring-2");
			expect(terminalContainer).toBeInTheDocument();
		});
	});

	describe("WebSocket Messages", () => {
		it("handles connection open event", async () => {
			render(<TerminalComponent token="test-token" />);

			// Get the WebSocket instance and trigger open
			const wsInstance = wsInstances[0];
			expect(wsInstance).toBeDefined();

			// Simulate open event - wrap in act to handle state updates
			await act(async () => {
				wsInstance.readyState = 1;
				if (wsInstance.onopen) {
					wsInstance.onopen(new Event("open"));
				}
			});

			await waitFor(() => {
				expect(screen.getByText("Connected")).toBeInTheDocument();
			});
		});

		it("handles error status messages", async () => {
			render(<TerminalComponent token="test-token" />);

			const wsInstance = wsInstances[0];
			expect(wsInstance).toBeDefined();

			// Simulate open - wrap in act to handle state updates
			await act(async () => {
				wsInstance.readyState = 1;
				if (wsInstance.onopen) {
					wsInstance.onopen(new Event("open"));
				}
			});

			// Simulate error message - wrap in act to handle state updates
			await act(async () => {
				if (wsInstance.onmessage) {
					const errorMessage = {
						type: "error",
						message: "Test error message",
					};
					wsInstance.onmessage(
						new MessageEvent("message", {
							data: JSON.stringify(errorMessage),
						}),
					);
				}
			});

			await waitFor(() => {
				// Multiple "Connection Error" elements - one in header, one in overlay
				const errors = screen.getAllByText("Connection Error");
				expect(errors.length).toBeGreaterThan(0);
			});
		});
	});

	describe("Reconnection", () => {
		it("shows reconnect button on error state", async () => {
			vi.mocked(localStorage.getItem).mockReturnValue(null);

			render(<TerminalComponent />);

			await waitFor(() => {
				expect(
					screen.getByRole("button", { name: /reconnect/i }),
				).toBeInTheDocument();
			});
		});
	});

	describe("Props", () => {
		it("uses default values when props not provided", () => {
			render(<TerminalComponent />);

			expect(screen.getByText("Terminal")).toBeInTheDocument();
		});

		it("uses default wsUrl from environment when not provided", () => {
			render(<TerminalComponent token="test-token" />);

			// Should use default URL
			expect(MockWebSocket).toHaveBeenCalledWith(
				expect.stringContaining("ws://localhost:8000"),
			);
		});
	});
});
