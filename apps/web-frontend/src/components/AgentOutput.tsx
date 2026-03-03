/**
 * AgentOutput Component
 *
 * Displays real-time agent output/logs from WebSocket events.
 * Follows the same pattern as Terminal.tsx for consistency.
 */

import {
	forwardRef,
	useCallback,
	useEffect,
	useImperativeHandle,
	useRef,
	useState,
} from "react";
import {
	Terminal as TerminalIcon,
	X,
	Maximize2,
	Minimize2,
} from "lucide-react";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";

export interface LogLine {
	timestamp: string;
	level: "debug" | "info" | "warning" | "error";
	message: string;
}

export interface AgentOutputProps {
	id: string;
	specId?: string;
	logs: LogLine[];
	isActive?: boolean;
	isExpanded?: boolean;
	onClose?: () => void;
	onActivate?: () => void;
	onToggleExpand?: () => void;
	title?: string;
	maxHeight?: string;
	maxLines?: number;
}

export interface AgentOutputHandle {
	scrollToBottom: () => void;
	clear: () => void;
}

/**
 * Get color class for log level
 */
function getLevelColor(level: LogLine["level"]): string {
	switch (level) {
		case "debug":
			return "text-gray-500";
		case "info":
			return "text-blue-400";
		case "warning":
			return "text-yellow-400";
		case "error":
			return "text-red-400";
		default:
			return "text-green-400";
	}
}

/**
 * AgentOutput component for displaying live agent logs
 */
export const AgentOutput = forwardRef<AgentOutputHandle, AgentOutputProps>(
	function AgentOutput(
		{
			id,
			specId,
			logs = [],
			isActive = false,
			isExpanded = true,
			onClose,
			onActivate,
			onToggleExpand,
			title = "Agent Output",
			maxHeight = "400px",
			maxLines = 1000,
		},
		ref,
	) {
		const outputRef = useRef<HTMLDivElement>(null);
		const scrollRef = useRef<HTMLDivElement>(null);
		const [isFollowing, setIsFollowing] = useState(true);

		// Truncate logs to maxLines
		const visibleLogs =
			logs.length > maxLines ? logs.slice(-maxLines) : logs;

		/**
		 * Check if user has scrolled near the bottom
		 */
		const checkIsAtBottom = useCallback(() => {
			if (!scrollRef.current) return true;
			const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
			return scrollHeight - scrollTop - clientHeight < 50;
		}, []);

		/**
		 * Auto-scroll to bottom when new logs arrive (only if following)
		 */
		useEffect(() => {
			if (scrollRef.current && visibleLogs.length > 0 && isFollowing) {
				scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
			}
		}, [visibleLogs, isFollowing]);

		/**
		 * Track user scroll to pause/resume auto-follow
		 */
		const handleScroll = useCallback(() => {
			setIsFollowing(checkIsAtBottom());
		}, [checkIsAtBottom]);

		/**
		 * Focus when active
		 */
		useEffect(() => {
			if (isActive && outputRef.current) {
				outputRef.current.focus();
			}
		}, [isActive]);

		/**
		 * Expose handle methods via ref
		 */
		useImperativeHandle(ref, () => ({
			scrollToBottom: () => {
				if (scrollRef.current) {
					scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
					setIsFollowing(true);
				}
			},
			clear: () => {
				// Parent controls logs array - this is a no-op signal
			},
		}));

		const handleClick = () => {
			onActivate?.();
		};

		return (
			<div
				ref={outputRef}
				tabIndex={-1}
				className={cn(
					"flex flex-col bg-black text-green-400 font-mono text-sm border rounded-lg overflow-hidden",
					isActive && "ring-2 ring-primary",
				)}
				onClick={handleClick}
			>
				{/* Header */}
				<div className="flex items-center justify-between bg-gray-800 px-3 py-2 border-b border-gray-700">
					<div className="flex items-center gap-2">
						<TerminalIcon className="h-4 w-4" />
						<span className="text-xs text-gray-300">{title}</span>
						{specId && (
							<span className="text-xs text-gray-500">({specId})</span>
						)}
					</div>
					<div className="flex items-center gap-1">
						{onToggleExpand && (
							<Button
								variant="ghost"
								size="icon"
								className="h-6 w-6 text-gray-400 hover:text-white"
								onClick={(e) => {
									e.stopPropagation();
									onToggleExpand();
								}}
							>
								{isExpanded ? (
									<Minimize2 className="h-3 w-3" />
								) : (
									<Maximize2 className="h-3 w-3" />
								)}
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

				{/* Log Content */}
				{isExpanded && (
					<div
						ref={scrollRef}
						className="overflow-auto p-4"
						style={{ maxHeight }}
						role="log"
						aria-live="polite"
						aria-label={title}
						onScroll={handleScroll}
					>
						{visibleLogs.length === 0 ? (
							<div className="text-gray-500 text-sm">
								Waiting for agent output...
							</div>
						) : (
							<div className="space-y-1">
								{visibleLogs.map((log, index) => (
									<div
										key={`${log.timestamp}-${index}`}
										className={cn(
											"whitespace-pre-wrap break-words",
											getLevelColor(log.level),
										)}
									>
										<span className="text-gray-600 text-xs">
											[{new Date(log.timestamp).toLocaleTimeString()}]
										</span>{" "}
										<span
											className={cn(
												"text-xs uppercase",
												getLevelColor(log.level),
											)}
										>
											[{log.level}]
										</span>{" "}
										<span>{log.message}</span>
									</div>
								))}
							</div>
						)}
					</div>
				)}

				{/* Footer */}
				<div className="px-4 py-2 bg-gray-900 border-t border-gray-700">
					<div className="flex items-center justify-between text-xs text-gray-500">
						<div className="flex items-center gap-2">
							<span>Lines: {logs.length}</span>
							{specId && <span>Spec: {specId}</span>}
						</div>
						<span className="opacity-50">Real-time output via WebSocket</span>
					</div>
				</div>
			</div>
		);
	},
);
