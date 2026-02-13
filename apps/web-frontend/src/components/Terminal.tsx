/**
 * Terminal Component (Web Version with xterm.js)
 * Connects to backend PTY via WebSocket for full terminal functionality
 */

import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import { Loader2, X, Terminal as XtermIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "@xterm/xterm/css/xterm.css";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";

export interface TerminalProps {
	id?: string;
	cwd?: string;
	projectPath?: string;
	isActive?: boolean;
	onClose?: () => void;
	onActivate?: () => void;
	title?: string;
	sessionId?: string;
	token?: string;
	wsUrl?: string;
}

// Terminal message types from backend protocol
interface TerminalInputMessage {
	type: "input" | "resize" | "ping";
	data?: string;
	rows?: number;
	cols?: number;
}

interface TerminalOutputMessage {
	type: "output" | "error" | "status" | "pong";
	data?: string;
	message?: string;
	status?: string;
	session_id?: string;
	timestamp?: string;
}

/**
 * Terminal component for web
 * Uses xterm.js for terminal rendering and WebSocket for PTY I/O
 */
export function TerminalComponent({
	id = "default",
	cwd,
	isActive = false,
	onClose,
	onActivate,
	title = "Terminal",
	sessionId = "default",
	token = "",
	wsUrl = import.meta.env.VITE_WS_URL || "ws://localhost:8000",
}: TerminalProps) {
	const terminalRef = useRef<HTMLDivElement>(null);
	const xtermRef = useRef<Terminal | null>(null);
	const fitAddonRef = useRef<FitAddon | null>(null);
	const wsRef = useRef<WebSocket | null>(null);
	const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
		null,
	);
	const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

	const [connectionStatus, setConnectionStatus] = useState<
		"disconnected" | "connecting" | "connected" | "error"
	>("disconnected");
	const [error, setError] = useState<string | null>(null);

	// Get auth token from localStorage if not provided
	const authToken = useMemo(() => {
		if (token) return token;
		try {
			return localStorage.getItem("auth_token") || "";
		} catch {
			return "";
		}
	}, [token]);

	/**
	 * Initialize xterm.js instance
	 */
	useEffect(() => {
		if (!terminalRef.current) return;

		const terminal = new Terminal({
			cursorBlink: true,
			fontSize: 14,
			fontFamily: 'Menlo, Monaco, "Courier New", monospace',
			theme: {
				background: "#0d1117",
				foreground: "#c9d1d9",
				cursor: "#58a6ff",
				black: "#484f58",
				red: "#ff7b72",
				green: "#3fb950",
				yellow: "#d29922",
				blue: "#58a6ff",
				magenta: "#bc8cff",
				cyan: "#39c5cf",
				white: "#b1bac4",
				brightBlack: "#6e7681",
				brightRed: "#ffa198",
				brightGreen: "#56d364",
				brightYellow: "#e3b341",
				brightBlue: "#79c0ff",
				brightMagenta: "#d2a8ff",
				brightCyan: "#56d4dd",
				brightWhite: "#f0f6fc",
			},
			allowProposedApi: true,
		});

		const fitAddon = new FitAddon();
		terminal.loadAddon(fitAddon);

		terminal.open(terminalRef.current);
		fitAddon.fit();

		xtermRef.current = terminal;
		fitAddonRef.current = fitAddon;

		// Welcome message
		terminal.writeln("\x1b[1;36mAuto Code Terminal\x1b[0m");
		terminal.writeln("Connecting to backend...");

		// Focus terminal when activated
		if (isActive) {
			terminal.focus();
		}

		return () => {
			fitAddon.dispose();
			terminal.dispose();
			xtermRef.current = null;
			fitAddonRef.current = null;
		};
	}, [isActive]);

	/**
	 * Connect to WebSocket terminal endpoint
	 */
	useEffect(() => {
		if (!authToken) {
			setError("No authentication token available");
			xtermRef.current?.writeln(
				"\r\n\x1b[31mError: Authentication required. Please login.\x1b[0m",
			);
			return;
		}

		setConnectionStatus("connecting");
		setError(null);

		// Build WebSocket URL with auth token and session_id
		const url = `${wsUrl}/ws/terminal?token=${encodeURIComponent(authToken)}&session_id=${sessionId}`;

		const ws = new WebSocket(url);
		wsRef.current = ws;

		ws.onopen = () => {
			setConnectionStatus("connected");
			xtermRef.current?.clear();
			xtermRef.current?.writeln(
				"\x1b[1;32m✓ Connected to terminal backend\x1b[0m",
			);

			if (cwd) {
				xtermRef.current?.writeln(`Working directory: ${cwd}`);
			}
			xtermRef.current?.writeln("");

			// Start ping interval to keep connection alive
			pingIntervalRef.current = setInterval(() => {
				if (ws.readyState === WebSocket.OPEN) {
					ws.send(JSON.stringify({ type: "ping" }));
				}
			}, 30000);
		};

		ws.onmessage = (event) => {
			try {
				const message: TerminalOutputMessage = JSON.parse(event.data);

				switch (message.type) {
					case "output":
						if (message.data) {
							xtermRef.current?.write(message.data);
						}
						break;

					case "error":
						setConnectionStatus("error");
						setError(message.message || "Unknown error");
						xtermRef.current?.writeln(
							`\r\n\x1b[31mError: ${message.message}\x1b[0m`,
						);
						break;

					case "status":
						if (message.status === "connected") {
							xtermRef.current?.writeln(
								`\x1b[1;32m✓ Session ${message.session_id} ready\x1b[0m\r\n`,
							);
						} else if (message.status === "closed") {
							setConnectionStatus("disconnected");
							xtermRef.current?.writeln("\r\n\x1b[33mSession closed\x1b[0m");
						}
						break;

					case "pong":
						// Ping response - connection alive
						break;
				}
			} catch (err) {
				console.error("Error parsing WebSocket message:", err);
			}
		};

		ws.onerror = (event) => {
			setConnectionStatus("error");
			setError("WebSocket connection failed");
			console.error("WebSocket error:", event);
		};

		ws.onclose = () => {
			setConnectionStatus("disconnected");
			if (pingIntervalRef.current) {
				clearInterval(pingIntervalRef.current);
				pingIntervalRef.current = null;
			}

			// Attempt to reconnect if not intentionally closed
			if (reconnectTimeoutRef.current === null) {
				xtermRef.current?.writeln(
					"\r\n\x1b[33mConnection lost. Reconnecting...\x1b[0m",
				);
				reconnectTimeoutRef.current = setTimeout(() => {
					reconnectTimeoutRef.current = null;
				}, 3000);
			}
		};

		return () => {
			// Cleanup on unmount
			if (pingIntervalRef.current) {
				clearInterval(pingIntervalRef.current);
			}
			if (reconnectTimeoutRef.current) {
				clearTimeout(reconnectTimeoutRef.current);
			}
			ws.close();
			wsRef.current = null;
		};
	}, [authToken, wsUrl, sessionId, cwd]);

	/**
	 * Handle user input from xterm.js
	 */
	useEffect(() => {
		const xterm = xtermRef.current;
		if (!xterm) return;

		const handleData = (data: string) => {
			const ws = wsRef.current;
			if (ws?.readyState === WebSocket.OPEN) {
				const message: TerminalInputMessage = { type: "input", data };
				ws.send(JSON.stringify(message));
			}
		};

		const handleResize = () => {
			const fitAddon = fitAddonRef.current;
			if (fitAddon) {
				fitAddon.fit();
			}
		};

		xterm.onData(handleData);
		xterm.onResize(({ cols, rows }) => {
			const ws = wsRef.current;
			if (ws?.readyState === WebSocket.OPEN) {
				const message: TerminalInputMessage = { type: "resize", cols, rows };
				ws.send(JSON.stringify(message));
			}
		});

		// Handle window resize
		window.addEventListener("resize", handleResize);

		return () => {
			xterm.onData(() => {});
			xterm.onResize(() => {});
			window.removeEventListener("resize", handleResize);
		};
	}, []);

	/**
	 * Focus terminal when active
	 */
	useEffect(() => {
		if (isActive && xtermRef.current) {
			xtermRef.current.focus();
		}
	}, [isActive]);

	/**
	 * Fit terminal on mount and container resize
	 */
	useEffect(() => {
		const fitAddon = fitAddonRef.current;
		if (!fitAddon) return;

		// Small delay to ensure container is rendered
		const timeout = setTimeout(() => {
			fitAddon.fit();
		}, 100);

		return () => clearTimeout(timeout);
	}, [connectionStatus]);

	const handleClick = useCallback(() => {
		onActivate?.();
		xtermRef.current?.focus();
	}, [onActivate]);

	const handleReconnect = useCallback(() => {
		// Force reconnect by closing current connection
		if (wsRef.current) {
			wsRef.current.close();
			wsRef.current = null;
		}
	}, []);

	const getStatusIndicator = useCallback(() => {
		switch (connectionStatus) {
			case "connected":
				return (
					<span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
				);
			case "connecting":
				return <Loader2 className="h-4 w-4 animate-spin text-yellow-500" />;
			case "error":
				return <span className="w-2 h-2 bg-red-500 rounded-full" />;
			default:
				return <span className="w-2 h-2 bg-gray-500 rounded-full" />;
		}
	}, [connectionStatus]);

	return (
		<div
			className={cn(
				"flex flex-col h-full bg-[#0d1117] border rounded-lg overflow-hidden",
				isActive && "ring-2 ring-primary",
			)}
			onClick={handleClick}
		>
			{/* Terminal Header */}
			<div className="flex items-center justify-between bg-[#161b22] px-3 py-2 border-b border-gray-700">
				<div className="flex items-center gap-2">
					<XtermIcon className="h-4 w-4 text-gray-400" />
					<span className="text-xs text-gray-300">{title}</span>
					{getStatusIndicator()}
					<span className="text-xs text-gray-500 ml-2">
						{connectionStatus === "connected" && "Connected"}
						{connectionStatus === "connecting" && "Connecting..."}
						{connectionStatus === "disconnected" && "Disconnected"}
						{connectionStatus === "error" && "Connection Error"}
					</span>
				</div>
				<div className="flex items-center gap-2">
					{connectionStatus === "error" && (
						<Button
							variant="ghost"
							size="sm"
							className="h-6 px-2 text-xs text-yellow-400 hover:text-yellow-300"
							onClick={handleReconnect}
						>
							Reconnect
						</Button>
					)}
					{onClose && (
						<Button
							variant="ghost"
							size="icon"
							className="h-6 w-6 text-gray-400 hover:text-white"
							onClick={(e) => {
								e.stopPropagation();
								onClose();
							}}
						>
							<X className="h-4 w-4" />
						</Button>
					)}
				</div>
			</div>

			{/* Terminal Content */}
			<div
				ref={terminalRef}
				className="flex-1 overflow-hidden"
				style={{ minHeight: 0 }}
			/>

			{/* Error Overlay */}
			{error && (
				<div className="absolute inset-0 bg-black/80 flex items-center justify-center z-10">
					<div className="bg-red-900/90 border border-red-500 rounded-lg p-6 max-w-md">
						<h3 className="text-lg font-semibold text-red-200 mb-2">
							Connection Error
						</h3>
						<p className="text-sm text-red-100 mb-4">{error}</p>
						<Button
							variant="outline"
							size="sm"
							className="text-red-200 border-red-500 hover:bg-red-800"
							onClick={handleReconnect}
						>
							Try Reconnecting
						</Button>
					</div>
				</div>
			)}
		</div>
	);
}

/**
 * Handle interface for external control (matching Electron version signature)
 */
export interface TerminalHandle {
	fit: () => void;
}

// Default export
export default TerminalComponent;
