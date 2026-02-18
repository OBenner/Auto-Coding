/**
 * WebSocket Client
 *
 * WebSocket client for real-time agent progress updates from the Auto Code web backend.
 * Provides event-driven API for subscribing to agent execution events.
 */

import type {
	AgentEvent,
	ErrorEvent,
	ExecutionEvent,
	IdeationEvent,
	LogEvent,
	RoadmapEvent,
	WebSocketAction,
	WebSocketMessage,
} from "./types";

/**
 * WebSocket connection state
 */
export type ConnectionState =
	| "connecting"
	| "connected"
	| "disconnected"
	| "error";

/**
 * Event handler type for WebSocket events
 */
export type EventHandler<T = AgentEvent> = (event: T) => void;

/**
 * WebSocket client configuration
 */
export interface WebSocketConfig {
	url: string;
	reconnect?: boolean;
	reconnectDelay?: number;
	maxReconnectAttempts?: number;
	pingInterval?: number;
	debug?: boolean;
}

/**
 * Default WebSocket configuration
 */
const DEFAULT_WS_CONFIG: Required<WebSocketConfig> = {
	url: import.meta.env.VITE_WS_URL || "ws://localhost:8000",
	reconnect: true,
	reconnectDelay: 3000, // 3 seconds
	maxReconnectAttempts: 10,
	pingInterval: 30000, // 30 seconds
	debug: import.meta.env.VITE_DEBUG === "true",
};

/**
 * WebSocket Client for real-time agent events
 */
export class WebSocketClient {
	private config: Required<WebSocketConfig>;
	private ws: WebSocket | null = null;
	private state: ConnectionState = "disconnected";
	private reconnectAttempts = 0;
	private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	private pingTimer: ReturnType<typeof setInterval> | null = null;
	private subscriptions = new Set<string>();

	// Event handlers
	private eventHandlers = new Map<string, Set<EventHandler>>();
	private stateHandlers = new Set<(state: ConnectionState) => void>();

	constructor(config: Partial<WebSocketConfig> = {}) {
		this.config = { ...DEFAULT_WS_CONFIG, ...config };
		this.log("WebSocketClient initialized", this.config);
	}

	/**
	 * Sanitize a value for safe logging (strips control characters, truncates).
	 */
	private static sanitize(value: unknown): string {
		return String(value).replace(/\p{Cc}/gu, "").slice(0, 200);
	}

	/**
	 * Internal logging helper - sanitizes all values to prevent log injection
	 */
	private log(message: string, ...args: unknown[]): void {
		if (this.config.debug) {
			const safeMsg = WebSocketClient.sanitize(message);
			const sanitizedArgs = args.map((a) => WebSocketClient.sanitize(a));
			console.log("[WebSocketClient]", safeMsg, sanitizedArgs.join(" "));
		}
	}

	/**
	 * Update connection state and notify handlers
	 */
	private setState(state: ConnectionState): void {
		if (this.state === state) return;

		this.state = state;
		this.log(`State changed: ${state}`);

		for (const handler of this.stateHandlers) {
			try {
				handler(state);
			} catch (error) {
				console.error("Error in state handler:", error);
			}
		}
	}

	/**
	 * Connect to WebSocket server
	 */
	connect(): void {
		if (this.ws?.readyState === WebSocket.OPEN) {
			this.log("Already connected");
			return;
		}

		if (this.ws?.readyState === WebSocket.CONNECTING) {
			this.log("Already connecting");
			return;
		}

		try {
			this.setState("connecting");
			this.log(`Connecting to ${this.config.url}/ws/agent-events`);

			this.ws = new WebSocket(`${this.config.url}/ws/agent-events`);

			this.ws.onopen = () => {
				this.log("Connected");
				this.setState("connected");
				this.reconnectAttempts = 0;

				// Start ping interval
				this.startPing();

				// Re-subscribe to previous subscriptions
				for (const specId of this.subscriptions) {
					this.subscribe(specId);
				}
			};

			this.ws.onmessage = (event) => {
				try {
					const data = JSON.parse(event.data) as AgentEvent;
					this.handleEvent(data);
				} catch (error) {
					console.error("Error parsing WebSocket message:", error);
				}
			};

			this.ws.onerror = (error) => {
				console.error("WebSocket error:", error);
				this.setState("error");
			};

			this.ws.onclose = () => {
				this.log("Connection closed");
				this.setState("disconnected");
				this.stopPing();

				// Attempt reconnect if enabled
				if (
					this.config.reconnect &&
					this.reconnectAttempts < this.config.maxReconnectAttempts
				) {
					this.scheduleReconnect();
				}
			};
		} catch (error) {
			console.error("Error connecting to WebSocket:", error);
			this.setState("error");
		}
	}

	/**
	 * Disconnect from WebSocket server
	 */
	disconnect(): void {
		this.log("Disconnecting");
		this.config.reconnect = false; // Disable auto-reconnect
		this.clearReconnectTimer();
		this.stopPing();

		if (this.ws) {
			this.ws.close();
			this.ws = null;
		}

		this.setState("disconnected");
	}

	/**
	 * Schedule a reconnection attempt
	 */
	private scheduleReconnect(): void {
		this.clearReconnectTimer();

		this.reconnectAttempts++;
		const delay = this.config.reconnectDelay * this.reconnectAttempts;

		this.log(
			`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`,
		);

		this.reconnectTimer = setTimeout(() => {
			this.connect();
		}, delay);
	}

	/**
	 * Clear reconnect timer
	 */
	private clearReconnectTimer(): void {
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
	}

	/**
	 * Start ping interval to keep connection alive
	 */
	private startPing(): void {
		this.stopPing();

		this.pingTimer = setInterval(() => {
			this.send({ action: "ping" });
		}, this.config.pingInterval);
	}

	/**
	 * Stop ping interval
	 */
	private stopPing(): void {
		if (this.pingTimer) {
			clearInterval(this.pingTimer);
			this.pingTimer = null;
		}
	}

	/**
	 * Send a WebSocket message
	 */
	private send(message: WebSocketMessage): void {
		if (this.ws?.readyState !== WebSocket.OPEN) {
			console.warn("Cannot send message: WebSocket not connected");
			return;
		}

		try {
			this.ws.send(JSON.stringify(message));
			this.log("Sent message:", message);
		} catch (error) {
			console.error("Error sending WebSocket message:", error);
		}
	}

	/**
	 * Subscribe to events for a specific spec
	 */
	subscribe(specId: string): void {
		this.subscriptions.add(specId);
		this.send({ action: "subscribe", spec_id: specId });
		this.log(`Subscribed to spec: ${specId}`);
	}

	/**
	 * Unsubscribe from events for a specific spec
	 */
	unsubscribe(specId: string): void {
		this.subscriptions.delete(specId);
		this.send({ action: "unsubscribe", spec_id: specId });
		this.log(`Unsubscribed from spec: ${specId}`);
	}

	/**
	 * Handle incoming WebSocket event
	 */
	private handleEvent(event: AgentEvent): void {
		this.log("Received event:", event);

		// Emit to specific event type handlers
		const typeHandlers = this.eventHandlers.get(event.event_type);
		if (typeHandlers) {
			for (const handler of typeHandlers) {
				try {
					handler(event);
				} catch (error) {
					const safeType = WebSocketClient.sanitize(event.event_type);
					console.error(
						"Error in event handler for type:",
						safeType,
						error,
					);
				}
			}
		}

		// Emit to wildcard handlers
		const wildcardHandlers = this.eventHandlers.get("*");
		if (wildcardHandlers) {
			for (const handler of wildcardHandlers) {
				try {
					handler(event);
				} catch (error) {
					console.error("Error in wildcard event handler:", error);
				}
			}
		}
	}

	/**
	 * Register an event handler
	 */
	on(eventType: "execution", handler: EventHandler<ExecutionEvent>): void;
	on(eventType: "ideation", handler: EventHandler<IdeationEvent>): void;
	on(eventType: "roadmap", handler: EventHandler<RoadmapEvent>): void;
	on(eventType: "log", handler: EventHandler<LogEvent>): void;
	on(eventType: "error", handler: EventHandler<ErrorEvent>): void;
	on(eventType: "*", handler: EventHandler<AgentEvent>): void;
	// biome-ignore lint/suspicious/noExplicitAny: Implementation signature needs to accept all overloads
	on(eventType: string, handler: EventHandler<any>): void {
		if (!this.eventHandlers.has(eventType)) {
			this.eventHandlers.set(eventType, new Set());
		}
		this.eventHandlers.get(eventType)!.add(handler);
		this.log(`Registered handler for: ${eventType}`);
	}

	/**
	 * Unregister an event handler
	 */
	off(eventType: string, handler: EventHandler): void {
		const handlers = this.eventHandlers.get(eventType);
		if (handlers) {
			handlers.delete(handler);
			this.log(`Unregistered handler for: ${eventType}`);
		}
	}

	/**
	 * Register a state change handler
	 */
	onStateChange(handler: (state: ConnectionState) => void): void {
		this.stateHandlers.add(handler);
	}

	/**
	 * Unregister a state change handler
	 */
	offStateChange(handler: (state: ConnectionState) => void): void {
		this.stateHandlers.delete(handler);
	}

	/**
	 * Get current connection state
	 */
	getState(): ConnectionState {
		return this.state;
	}

	/**
	 * Check if connected
	 */
	isConnected(): boolean {
		return this.state === "connected" && this.ws?.readyState === WebSocket.OPEN;
	}

	/**
	 * Get list of active subscriptions
	 */
	getSubscriptions(): string[] {
		return Array.from(this.subscriptions);
	}

	/**
	 * Update WebSocket configuration
	 */
	updateConfig(config: Partial<WebSocketConfig>): void {
		this.config = { ...this.config, ...config };
		this.log("Config updated", this.config);
	}

	/**
	 * Get current configuration
	 */
	getConfig(): Readonly<Required<WebSocketConfig>> {
		return { ...this.config };
	}
}

/**
 * Default WebSocket client instance
 * Use this for most cases unless you need custom configuration
 */
export const wsClient = new WebSocketClient();

/**
 * Create a new WebSocket client with custom configuration
 */
export function createWebSocketClient(
	config: Partial<WebSocketConfig> = {},
): WebSocketClient {
	return new WebSocketClient(config);
}
