/**
 * Insights Page
 *
 * AI-powered insights chat interface for asking questions about
 * codebases and getting AI-assisted suggestions.
 */

import {
	AlertCircle,
	Bot,
	CheckCircle2,
	FileText,
	FolderSearch,
	Loader2,
	MessageSquare,
	MoreVertical,
	PanelLeft,
	PanelLeftClose,
	Plus,
	Search,
	Send,
	Sparkles,
	Trash2,
	User,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { ScrollArea } from "../components/ui/scroll-area";
import { Textarea } from "../components/ui/textarea";
import { cn } from "../lib/utils";

// Types
interface ChatMessage {
	id: string;
	role: "user" | "assistant";
	content: string;
	timestamp: Date;
	toolsUsed?: Array<{
		name: string;
		input?: string;
		timestamp: Date;
	}>;
	suggestedTask?: {
		title: string;
		description: string;
		metadata?: {
			category?: string;
			complexity?: string;
		};
	};
}

interface ChatSession {
	id: string;
	title: string;
	messages: ChatMessage[];
	createdAt: Date;
	updatedAt: Date;
}

type StatusPhase = "idle" | "thinking" | "streaming" | "error";

// createSafeLink - factory function that creates a SafeLink component
const createSafeLink = () => {
	return function SafeLink({
		href,
		children,
		...props
	}: React.AnchorHTMLAttributes<HTMLAnchorElement>) {
		// Validate URL - only allow http, https, and relative links
		const isValidUrl =
			href &&
			(href.startsWith("http://") ||
				href.startsWith("https://") ||
				href.startsWith("/") ||
				href.startsWith("#"));

		if (!isValidUrl) {
			// For invalid or potentially malicious URLs, render as plain text
			return <span className="text-gray-500">{children}</span>;
		}

		// External links get security attributes and accessibility indicator
		const isExternal =
			href?.startsWith("http://") || href?.startsWith("https://");

		return (
			<a
				href={href}
				{...props}
				{...(isExternal && {
					target: "_blank",
					rel: "noopener noreferrer",
				})}
				className="text-blue-600 hover:underline"
			>
				{children}
				{isExternal && <span className="sr-only"> (opens in new window)</span>}
			</a>
		);
	};
};

// Chat History Sidebar Component
interface ChatHistorySidebarProps {
	sessions: ChatSession[];
	currentSessionId: string | null;
	onNewSession: () => void;
	onSelectSession: (sessionId: string) => void;
	onDeleteSession: (sessionId: string) => void;
}

function ChatHistorySidebar({
	sessions,
	currentSessionId,
	onNewSession,
	onSelectSession,
	onDeleteSession,
}: ChatHistorySidebarProps) {
	return (
		<div className="w-64 border-r border-gray-200 bg-gray-50 flex flex-col">
			<div className="p-4 border-b border-gray-200">
				<Button onClick={onNewSession} className="w-full" variant="outline">
					<Plus className="h-4 w-4 mr-2" />
					New Chat
				</Button>
			</div>
			<ScrollArea className="flex-1">
				<div className="p-2 space-y-1">
					{sessions.length === 0 ? (
						<p className="text-sm text-gray-500 p-3 text-center">
							No chat history
						</p>
					) : (
						sessions.map((session) => (
							<div
								key={session.id}
								className={cn(
									"group flex items-center justify-between p-3 rounded-lg transition-colors",
									currentSessionId === session.id
										? "bg-blue-50 border border-blue-200"
										: "hover:bg-gray-100",
								)}
							>
								<button
									type="button"
									className="flex-1 min-w-0 text-left"
									onClick={() => onSelectSession(session.id)}
								>
									<p className="text-sm font-medium text-gray-900 truncate">
										{session.title}
									</p>
									<p className="text-xs text-gray-500">
										{session.messages.length} messages
									</p>
								</button>
								<DropdownMenu>
									<DropdownMenuTrigger asChild>
										<Button
											variant="ghost"
											size="sm"
											className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100"
											onClick={(e) => e.stopPropagation()}
										>
											<MoreVertical className="h-4 w-4" />
										</Button>
									</DropdownMenuTrigger>
									<DropdownMenuContent align="end">
										<DropdownMenuItem
											onClick={(e) => {
												e.stopPropagation();
												onDeleteSession(session.id);
											}}
											className="text-red-600"
										>
											<Trash2 className="h-4 w-4 mr-2" />
											Delete
										</DropdownMenuItem>
									</DropdownMenuContent>
								</DropdownMenu>
							</div>
						))
					)}
				</div>
			</ScrollArea>
		</div>
	);
}

// Tool usage history component
interface ToolUsageHistoryProps {
	tools: Array<{
		name: string;
		input?: string;
		timestamp: Date;
	}>;
}

function ToolUsageHistory({ tools }: ToolUsageHistoryProps) {
	const [expanded, setExpanded] = useState(false);

	if (tools.length === 0) return null;

	// Group tools by name for summary
	const toolCounts = tools.reduce(
		(acc, tool) => {
			acc[tool.name] = (acc[tool.name] || 0) + 1;
			return acc;
		},
		{} as Record<string, number>,
	);

	const getToolIcon = (toolName: string) => {
		switch (toolName) {
			case "Read":
				return FileText;
			case "Glob":
				return FolderSearch;
			case "Grep":
				return Search;
			default:
				return FileText;
		}
	};

	const getToolColor = (toolName: string) => {
		switch (toolName) {
			case "Read":
				return "text-blue-500";
			case "Glob":
				return "text-amber-500";
			case "Grep":
				return "text-green-500";
			default:
				return "text-gray-500";
		}
	};

	return (
		<div className="mt-2">
			<button
				type="button"
				onClick={() => setExpanded(!expanded)}
				className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700 transition-colors"
			>
				<span className="flex items-center gap-1">
					{Object.entries(toolCounts).map(([name, count]) => {
						const Icon = getToolIcon(name);
						return (
							<span
								key={name}
								className={cn("flex items-center gap-0.5", getToolColor(name))}
							>
								<Icon className="h-3 w-3" />
								<span>{count}</span>
							</span>
						);
					})}
				</span>
				<span>
					{tools.length} tool{tools.length !== 1 ? "s" : ""} used
				</span>
				<span className="text-[10px]">{expanded ? "▲" : "▼"}</span>
			</button>

			{expanded && (
				<div className="mt-2 space-y-1 rounded-md border border-gray-200 bg-gray-50 p-2">
					{tools.map((tool, index) => {
						const Icon = getToolIcon(tool.name);
						return (
							<div
								key={`${tool.name}-${index}`}
								className="flex items-center gap-2 text-xs"
							>
								<Icon
									className={cn("h-3 w-3 shrink-0", getToolColor(tool.name))}
								/>
								<span className="font-medium">{tool.name}</span>
								{tool.input && (
									<span className="text-gray-500 truncate max-w-[250px]">
										{tool.input}
									</span>
								)}
							</div>
						);
					})}
				</div>
			)}
		</div>
	);
}

// Tool indicator component
interface ToolIndicatorProps {
	name: string;
	input?: string;
}

function ToolIndicator({ name, input }: ToolIndicatorProps) {
	const getToolInfo = (toolName: string) => {
		switch (toolName) {
			case "Read":
				return {
					icon: FileText,
					label: "Reading file",
					color: "text-blue-500 bg-blue-50",
				};
			case "Glob":
				return {
					icon: FolderSearch,
					label: "Searching files",
					color: "text-amber-500 bg-amber-50",
				};
			case "Grep":
				return {
					icon: Search,
					label: "Searching code",
					color: "text-green-500 bg-green-50",
				};
			default:
				return {
					icon: Loader2,
					label: toolName,
					color: "text-blue-600 bg-blue-50",
				};
		}
	};

	const { icon: Icon, label, color } = getToolInfo(name);

	return (
		<div
			className={cn(
				"mt-2 inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm",
				color,
			)}
		>
			<Icon className="h-4 w-4 animate-pulse" />
			<span className="font-medium">{label}</span>
			{input && (
				<span className="text-gray-500 truncate max-w-[300px]">{input}</span>
			)}
		</div>
	);
}

// Message bubble component
interface MessageBubbleProps {
	message: ChatMessage;
	markdownComponents: Components;
	onCreateTask: () => void;
	isCreatingTask: boolean;
	taskCreated: boolean;
}

function MessageBubble({
	message,
	markdownComponents,
	onCreateTask,
	isCreatingTask,
	taskCreated,
}: MessageBubbleProps) {
	const isUser = message.role === "user";

	return (
		<div className="flex gap-3">
			<div
				className={cn(
					"flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
					isUser ? "bg-gray-100" : "bg-blue-50",
				)}
			>
				{isUser ? (
					<User className="h-4 w-4 text-gray-600" />
				) : (
					<Bot className="h-4 w-4 text-blue-600" />
				)}
			</div>
			<div className="flex-1 space-y-2">
				<div className="text-sm font-medium text-gray-900">
					{isUser ? "You" : "Assistant"}
				</div>
				<div className="prose prose-sm max-w-none">
					<ReactMarkdown
						remarkPlugins={[remarkGfm]}
						components={markdownComponents}
					>
						{message.content}
					</ReactMarkdown>
				</div>

				{/* Tool usage history for assistant messages */}
				{!isUser && message.toolsUsed && message.toolsUsed.length > 0 && (
					<ToolUsageHistory tools={message.toolsUsed} />
				)}

				{/* Task suggestion card */}
				{message.suggestedTask && (
					<Card className="mt-3 border-blue-200 bg-blue-50">
						<CardContent className="p-4">
							<div className="mb-2 flex items-center gap-2">
								<Sparkles className="h-4 w-4 text-blue-600" />
								<span className="text-sm font-medium text-blue-600">
									Suggested Task
								</span>
							</div>
							<h4 className="mb-2 font-medium text-gray-900">
								{message.suggestedTask.title}
							</h4>
							<p className="mb-3 text-sm text-gray-600">
								{message.suggestedTask.description}
							</p>
							{message.suggestedTask.metadata && (
								<div className="mb-3 flex flex-wrap gap-2">
									{message.suggestedTask.metadata.category && (
										<Badge variant="outline" className="text-xs">
											{message.suggestedTask.metadata.category}
										</Badge>
									)}
									{message.suggestedTask.metadata.complexity && (
										<Badge variant="outline" className="text-xs">
											{message.suggestedTask.metadata.complexity}
										</Badge>
									)}
								</div>
							)}
							<Button
								size="sm"
								onClick={onCreateTask}
								disabled={isCreatingTask || taskCreated}
							>
								{isCreatingTask ? (
									<>
										<Loader2 className="mr-2 h-4 w-4 animate-spin" />
										Creating...
									</>
								) : taskCreated ? (
									<>
										<CheckCircle2 className="mr-2 h-4 w-4" />
										Task Created
									</>
								) : (
									<>
										<Plus className="mr-2 h-4 w-4" />
										Create Task
									</>
								)}
							</Button>
						</CardContent>
					</Card>
				)}
			</div>
		</div>
	);
}

// Main Insights component
export function Insights() {
	// Markdown components for safe link handling
	const markdownComponents = useMemo(
		() => ({
			a: createSafeLink(),
		}),
		[],
	);

	// State
	const [sessions, setSessions] = useState<ChatSession[]>([]);
	const [currentSession, setCurrentSession] = useState<ChatSession | null>(
		null,
	);
	const [inputValue, setInputValue] = useState("");
	const [statusPhase, setStatusPhase] = useState<StatusPhase>("idle");
	const [statusError, setStatusError] = useState<string | null>(null);
	const [streamingContent, setStreamingContent] = useState("");
	const [currentTool, setCurrentTool] = useState<{
		name: string;
		input?: string;
	} | null>(null);
	const [creatingTask, setCreatingTask] = useState<string | null>(null);
	const [taskCreated, setTaskCreated] = useState<Set<string>>(new Set());
	const [showSidebar, setShowSidebar] = useState(true);

	const messagesEndRef = useRef<HTMLDivElement>(null);
	const textareaRef = useRef<HTMLTextAreaElement>(null);

	// Auto-scroll to bottom when messages change
	const messagesLength = currentSession?.messages?.length ?? 0;
	const hasStreamingContent = Boolean(streamingContent);
	// biome-ignore lint/correctness/useExhaustiveDependencies: intentionally trigger scroll on message/content changes
	useEffect(() => {
		messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [messagesLength, hasStreamingContent]);

	// Focus textarea on mount
	useEffect(() => {
		textareaRef.current?.focus();
	}, []);

	// Create a new session
	const handleNewSession = () => {
		const newSession: ChatSession = {
			id: `session-${Date.now()}`,
			title: "New Chat",
			messages: [],
			createdAt: new Date(),
			updatedAt: new Date(),
		};
		setSessions((prev) => [newSession, ...prev]);
		setCurrentSession(newSession);
		setTaskCreated(new Set());
		textareaRef.current?.focus();
	};

	// Select a session
	const handleSelectSession = (sessionId: string) => {
		const session = sessions.find((s) => s.id === sessionId);
		if (session) {
			setCurrentSession(session);
			setTaskCreated(new Set());
		}
	};

	// Delete a session
	const handleDeleteSession = (sessionId: string) => {
		setSessions((prev) => prev.filter((s) => s.id !== sessionId));
		if (currentSession?.id === sessionId) {
			setCurrentSession(sessions.length > 1 ? sessions[0] : null);
		}
	};

	// Send a message
	const handleSend = async () => {
		const message = inputValue.trim();
		if (!message || statusPhase === "thinking" || statusPhase === "streaming")
			return;

		// Create session if none exists
		let session = currentSession;
		let isNewSession = false;
		if (!session) {
			session = {
				id: `session-${Date.now()}`,
				title: message.slice(0, 50) + (message.length > 50 ? "..." : ""),
				messages: [],
				createdAt: new Date(),
				updatedAt: new Date(),
			};
			isNewSession = true;
			setCurrentSession(session);
		}

		// Add user message
		const userMessage: ChatMessage = {
			id: `msg-${Date.now()}`,
			role: "user",
			content: message,
			timestamp: new Date(),
		};

		const sessionId = session.id;
		const updatedSession = {
			...session,
			messages: [...session.messages, userMessage],
			updatedAt: new Date(),
		};
		setCurrentSession(updatedSession);
		setSessions((prev) => {
			if (isNewSession) {
				return [updatedSession, ...prev];
			}
			return prev.map((s) => (s.id === sessionId ? updatedSession : s));
		});

		setInputValue("");
		setStatusPhase("thinking");
		setStatusError(null);

		// Simulate AI response (replace with actual API call)
		try {
			await simulateAIResponse(message, updatedSession);
		} catch (error) {
			setStatusPhase("error");
			setStatusError(
				error instanceof Error ? error.message : "An error occurred",
			);
		}
	};

	// Simulate AI response (placeholder for actual API integration)
	const simulateAIResponse = async (
		userMessage: string,
		session: ChatSession,
	) => {
		// Simulate thinking delay
		await new Promise((resolve) => setTimeout(resolve, 1000));

		// Simulate tool usage
		setCurrentTool({ name: "Grep", input: "searching codebase..." });
		await new Promise((resolve) => setTimeout(resolve, 800));
		setCurrentTool({ name: "Read", input: "reading files..." });
		await new Promise((resolve) => setTimeout(resolve, 600));
		setCurrentTool(null);

		// Simulate streaming response
		setStatusPhase("streaming");
		const response = `Thank you for your question about "${userMessage.slice(0, 30)}..."

This is a demo response. In production, this will connect to the Auto Code backend API to provide AI-powered insights about your codebase.

**Features available:**
- Ask questions about code architecture
- Get suggestions for improvements
- Identify potential security concerns
- Generate implementation plans

Would you like me to help with anything specific?`;

		// Stream the response character by character
		let streamedContent = "";
		for (const char of response) {
			streamedContent += char;
			setStreamingContent(streamedContent);
			await new Promise((resolve) => setTimeout(resolve, 10));
		}

		// Add assistant message
		const assistantMessage: ChatMessage = {
			id: `msg-${Date.now()}`,
			role: "assistant",
			content: response,
			timestamp: new Date(),
			toolsUsed: [
				{ name: "Grep", input: "searching codebase...", timestamp: new Date() },
				{ name: "Read", input: "reading files...", timestamp: new Date() },
			],
		};

		const finalSession = {
			...session,
			messages: [...session.messages, assistantMessage],
			updatedAt: new Date(),
		};
		setCurrentSession(finalSession);
		setSessions((prev) =>
			prev.map((s) => (s.id === session.id ? finalSession : s)),
		);

		setStreamingContent("");
		setStatusPhase("idle");
	};

	// Handle keyboard shortcuts
	const handleKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			handleSend();
		}
	};

	// Handle task creation (placeholder)
	const handleCreateTask = async (message: ChatMessage) => {
		if (!message.suggestedTask) return;

		setCreatingTask(message.id);
		try {
			// Simulate API call
			await new Promise((resolve) => setTimeout(resolve, 1000));
			setTaskCreated((prev) => new Set(prev).add(message.id));
		} finally {
			setCreatingTask(null);
		}
	};

	const isLoading = statusPhase === "thinking" || statusPhase === "streaming";
	const messages = currentSession?.messages || [];

	return (
		<div className="min-h-screen bg-gray-50 flex flex-col">
			{/* Header */}
			<div className="bg-white border-b border-gray-200">
				<div className="px-4 py-4">
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-4">
							<a
								href="/"
								className="text-blue-600 hover:text-blue-700 font-medium text-sm"
							>
								← Back to Home
							</a>
							<div className="h-6 w-px bg-gray-200" />
							<div className="flex items-center gap-3">
								<div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
									<Sparkles className="h-5 w-5 text-white" />
								</div>
								<div>
									<h1 className="text-xl font-bold text-gray-900">Insights</h1>
									<p className="text-sm text-gray-600">
										Ask questions about your codebase
									</p>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			{/* Main Content */}
			<div className="flex flex-1 overflow-hidden">
				{/* Chat History Sidebar */}
				{showSidebar && (
					<ChatHistorySidebar
						sessions={sessions}
						currentSessionId={currentSession?.id || null}
						onNewSession={handleNewSession}
						onSelectSession={handleSelectSession}
						onDeleteSession={handleDeleteSession}
					/>
				)}

				{/* Main Chat Area */}
				<div className="flex flex-1 flex-col bg-white">
					{/* Chat Header */}
					<div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
						<div className="flex items-center gap-2">
							<Button
								variant="ghost"
								size="sm"
								className="h-8 w-8 p-0"
								onClick={() => setShowSidebar(!showSidebar)}
								title={showSidebar ? "Hide sidebar" : "Show sidebar"}
							>
								{showSidebar ? (
									<PanelLeftClose className="h-4 w-4" />
								) : (
									<PanelLeft className="h-4 w-4" />
								)}
							</Button>
							<span className="text-sm text-gray-600">
								{currentSession?.title || "No conversation selected"}
							</span>
						</div>
						<Button variant="outline" size="sm" onClick={handleNewSession}>
							<Plus className="mr-2 h-4 w-4" />
							New Chat
						</Button>
					</div>

					{/* Messages */}
					<ScrollArea className="flex-1 px-6 py-4">
						{messages.length === 0 && !streamingContent ? (
							<div className="flex h-full flex-col items-center justify-center text-center py-12">
								<div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gray-100">
									<MessageSquare className="h-8 w-8 text-gray-400" />
								</div>
								<h3 className="mb-2 text-lg font-medium text-gray-900">
									Start a Conversation
								</h3>
								<p className="max-w-md text-sm text-gray-600">
									Ask questions about your codebase, get suggestions for
									improvements, or discuss features you'd like to implement.
								</p>
								<div className="mt-6 flex flex-wrap justify-center gap-2">
									{[
										"What is the architecture of this project?",
										"Suggest improvements for code quality",
										"What features could I add next?",
										"Are there any security concerns?",
									].map((suggestion) => (
										<Button
											key={suggestion}
											variant="outline"
											size="sm"
											className="text-xs"
											onClick={() => {
												setInputValue(suggestion);
												textareaRef.current?.focus();
											}}
										>
											{suggestion}
										</Button>
									))}
								</div>
							</div>
						) : (
							<div className="space-y-6">
								{messages.map((message) => (
									<MessageBubble
										key={message.id}
										message={message}
										markdownComponents={markdownComponents}
										onCreateTask={() => handleCreateTask(message)}
										isCreatingTask={creatingTask === message.id}
										taskCreated={taskCreated.has(message.id)}
									/>
								))}

								{/* Streaming message */}
								{(streamingContent || currentTool) && (
									<div className="flex gap-3">
										<div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50">
											<Bot className="h-4 w-4 text-blue-600" />
										</div>
										<div className="flex-1">
											<div className="mb-1 text-sm font-medium text-gray-900">
												Assistant
											</div>
											{streamingContent && (
												<div className="prose prose-sm max-w-none">
													<ReactMarkdown
														remarkPlugins={[remarkGfm]}
														components={markdownComponents}
													>
														{streamingContent}
													</ReactMarkdown>
												</div>
											)}
											{/* Tool usage indicator */}
											{currentTool && (
												<ToolIndicator
													name={currentTool.name}
													input={currentTool.input}
												/>
											)}
										</div>
									</div>
								)}

								{/* Thinking indicator */}
								{statusPhase === "thinking" &&
									!streamingContent &&
									!currentTool && (
										<div className="flex gap-3">
											<div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50">
												<Bot className="h-4 w-4 text-blue-600" />
											</div>
											<div className="flex items-center gap-2 text-sm text-gray-500">
												<Loader2 className="h-4 w-4 animate-spin" />
												Thinking...
											</div>
										</div>
									)}

								{/* Error message */}
								{statusPhase === "error" && statusError && (
									<div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
										<AlertCircle className="h-4 w-4 shrink-0" />
										{statusError}
									</div>
								)}

								<div ref={messagesEndRef} />
							</div>
						)}
					</ScrollArea>

					{/* Input */}
					<div className="border-t border-gray-200 p-4">
						<div className="flex gap-2">
							<Textarea
								ref={textareaRef}
								value={inputValue}
								onChange={(e) => setInputValue(e.target.value)}
								onKeyDown={handleKeyDown}
								placeholder="Ask about your codebase..."
								className="min-h-[80px] resize-none"
								disabled={isLoading}
							/>
							<Button
								onClick={handleSend}
								disabled={!inputValue.trim() || isLoading}
								className="self-end"
							>
								{isLoading ? (
									<Loader2 className="h-4 w-4 animate-spin" />
								) : (
									<Send className="h-4 w-4" />
								)}
							</Button>
						</div>
						<p className="mt-2 text-xs text-gray-500">
							Press Enter to send, Shift+Enter for new line
						</p>
					</div>
				</div>
			</div>
		</div>
	);
}
