/**
 * TaskDetail Page
 *
 * Displays detailed information about a single task/spec.
 * Shows spec content, progress, and subtasks.
 */

import {
	AlertCircle,
	ArrowLeft,
	Brain,
	CheckCircle2,
	Circle,
	Code,
	Loader2,
	Play,
	RefreshCw,
	Search,
	Square,
	Wrench,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { apiClient } from "../api/client";
import type {
	AgentStatusResponse,
	AgentType,
	TaskDetail as TaskDetailType,
} from "../api/types";
import { useTaskSubscription } from "../hooks/useWebSocketTaskIntegration";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../components/ui/card";
import { ScrollArea } from "../components/ui/scroll-area";
import { Separator } from "../components/ui/separator";
import { BuildProgress } from "../components/BuildProgress";

interface TaskDetailProps {
	taskId: string;
	onBack: () => void;
}

export function TaskDetail({ taskId, onBack }: TaskDetailProps) {
	const { t } = useTranslation(["common", "tasks"]);
	const [task, setTask] = useState<TaskDetailType | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [isRefreshing, setIsRefreshing] = useState(false);

	// Subscribe to WebSocket events for this task
	useTaskSubscription(taskId);

	// Agent control state
	const [agentStatus, setAgentStatus] = useState<AgentStatusResponse | null>(
		null,
	);
	const [isStartingAgent, setIsStartingAgent] = useState(false);
	const [isCancellingAgent, setIsCancellingAgent] = useState(false);
	const [selectedAgentType, setSelectedAgentType] = useState<AgentType | null>(
		null,
	);

	/**
	 * Agent type configuration
	 */
	const agentTypes: Array<{
		type: AgentType;
		label: string;
		description: string;
		icon: React.ReactNode;
	}> = [
		{
			type: "planner",
			label: "Planner",
			description: "Create implementation plan with subtasks",
			icon: <Brain className="h-4 w-4" />,
		},
		{
			type: "coder",
			label: "Coder",
			description: "Implement individual subtasks",
			icon: <Code className="h-4 w-4" />,
		},
		{
			type: "qa_reviewer",
			label: "QA Reviewer",
			description: "Validate acceptance criteria",
			icon: <Search className="h-4 w-4" />,
		},
		{
			type: "qa_fixer",
			label: "QA Fixer",
			description: "Fix QA-reported issues",
			icon: <Wrench className="h-4 w-4" />,
		},
	];

	/**
	 * Fetch task details from the API
	 */
	const fetchTaskDetail = useCallback(
		async (showRefreshIndicator = false) => {
			try {
				if (showRefreshIndicator) {
					setIsRefreshing(true);
				} else {
					setIsLoading(true);
				}
				setError(null);

				const taskDetail = await apiClient.getTask(taskId);
				setTask(taskDetail);
			} catch (err) {
				const message =
					err instanceof Error ? err.message : "Failed to load task details";
				setError(message);
			} finally {
				setIsLoading(false);
				setIsRefreshing(false);
			}
		},
		[taskId],
	);

	// Initial load
	useEffect(() => {
		fetchTaskDetail();
	}, [fetchTaskDetail]);

	// Handle refresh button click
	const handleRefresh = useCallback(() => {
		fetchTaskDetail(true);
	}, [fetchTaskDetail]);

	/**
	 * Start an agent
	 */
	const handleStartAgent = useCallback(
		async (agentType: AgentType) => {
			try {
				setIsStartingAgent(true);
				setError(null);
				setSelectedAgentType(agentType);

				const response = await apiClient.runAgent({
					spec_id: taskId,
					agent_type: agentType,
				});

				if (response.status === "started") {
					// Poll for status
					pollAgentStatus(response.task_id);
				} else {
					setError(response.message || "Failed to start agent");
				}
			} catch (err) {
				const message =
					err instanceof Error ? err.message : "Failed to start agent";
				setError(message);
			} finally {
				setIsStartingAgent(false);
			}
		},
		[taskId],
	);

	/**
	 * Poll agent status
	 */
	const pollAgentStatus = useCallback(async (agentTaskId: string) => {
		const poll = async () => {
			try {
				const status = await apiClient.getAgentStatus(agentTaskId);
				setAgentStatus(status);

				// Continue polling if still running
				if (status.status === "running") {
					setTimeout(() => poll(), 2000); // Poll every 2 seconds
				}
			} catch (err) {
				console.error("Failed to poll agent status:", err);
			}
		};

		poll();
	}, []);

	/**
	 * Cancel running agent
	 */
	const handleCancelAgent = useCallback(async () => {
		if (!agentStatus || agentStatus.status !== "running") {
			return;
		}

		try {
			setIsCancellingAgent(true);
			const response = await apiClient.cancelAgent(agentStatus.task_id);

			if (response.cancelled) {
				setAgentStatus(null);
				setSelectedAgentType(null);
			} else {
				setError(response.message || "Failed to cancel agent");
			}
		} catch (err) {
			const message =
				err instanceof Error ? err.message : "Failed to cancel agent";
			setError(message);
		} finally {
			setIsCancellingAgent(false);
		}
	}, [agentStatus]);

	// Loading state
	if (isLoading) {
		return (
			<div className="min-h-screen bg-gray-50 flex items-center justify-center">
				<div className="text-center">
					<div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
					<p className="text-gray-600">{t("common:loading")}</p>
				</div>
			</div>
		);
	}

	// Error state
	if (error || !task) {
		return (
			<div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
				<div className="text-center max-w-md">
					<AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
					<h2 className="text-xl font-semibold text-gray-900 mb-2">
						{t("common:error")}
					</h2>
					<p className="text-gray-600 mb-4">{error || "Task not found"}</p>
					<div className="flex gap-2 justify-center">
						<Button onClick={onBack} variant="outline">
							<ArrowLeft className="h-4 w-4 mr-2" />
							{t("common:buttons.back")}
						</Button>
						<Button onClick={handleRefresh}>
							<RefreshCw className="h-4 w-4 mr-2" />
							{t("common:buttons.retry")}
						</Button>
					</div>
				</div>
			</div>
		);
	}

	// Task detail view
	return (
		<div className="min-h-screen bg-gray-50">
			<div className="max-w-5xl mx-auto p-6">
				{/* Header */}
				<div className="flex items-center justify-between mb-6">
					<div className="flex items-center gap-4">
						<Button onClick={onBack} variant="outline" size="icon">
							<ArrowLeft className="h-4 w-4" />
						</Button>
						<div>
							<h1 className="text-3xl font-bold text-gray-900">{task.name}</h1>
							<p className="text-sm text-gray-600 mt-1">
								Spec #{task.number}
							</p>
						</div>
					</div>
					<Button
						onClick={handleRefresh}
						disabled={isRefreshing}
						variant="outline"
					>
						<RefreshCw
							className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`}
						/>
						{t("common:buttons.refresh")}
					</Button>
				</div>

				<div className="grid gap-6">
					{/* Status and Progress Card */}
					<Card>
						<CardContent className="space-y-4 pt-6">
							<h3 className="text-lg font-semibold mb-4">
								{t("common:labels.status")}
							</h3>
							<div className="flex items-center gap-4">
								<div>
									<p className="text-sm text-gray-600 mb-1">
										{t("tasks:labels.status")}
									</p>
									<Badge variant="outline" className="text-sm">
										{task.status}
									</Badge>
								</div>
								{task.has_build && (
									<div>
										<p className="text-sm text-gray-600 mb-1">Build</p>
										<Badge
											variant="outline"
											className="text-sm bg-green-50 text-green-700 border-green-200"
										>
											Active
										</Badge>
									</div>
								)}
							</div>

							<Separator />

							{/* Progress Bar */}
							<div className="space-y-2">
								<div className="flex items-center justify-between text-sm">
									<span className="text-gray-600">Overall Progress</span>
									<span className="font-semibold">
										{task.progress.percentage}%
									</span>
								</div>
								<div className="h-3 bg-gray-200 rounded-full overflow-hidden">
									<div
										className="h-full bg-blue-600 transition-all duration-300"
										style={{ width: `${task.progress.percentage}%` }}
									/>
								</div>
								<div className="grid grid-cols-4 gap-2 text-xs text-gray-600">
									<div className="flex items-center gap-1">
										<CheckCircle2 className="h-3 w-3 text-green-600" />
										<span>{task.progress.completed} completed</span>
									</div>
									<div className="flex items-center gap-1">
										<Loader2 className="h-3 w-3 text-blue-600" />
										<span>{task.progress.in_progress} in progress</span>
									</div>
									<div className="flex items-center gap-1">
										<Circle className="h-3 w-3 text-gray-400" />
										<span>{task.progress.pending} pending</span>
									</div>
									<div className="flex items-center gap-1">
										<AlertCircle className="h-3 w-3 text-red-600" />
										<span>{task.progress.failed} failed</span>
									</div>
								</div>
							</div>
						</CardContent>
					</Card>

					{/* Build Progress Card */}
					<BuildProgress
						taskId={task.number}
						progress={task.progress}
					/>

					{/* Agent Controls Card */}
					<Card>
						<CardHeader>
							<CardTitle className="text-lg font-semibold">
								Agent Controls
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-4">
							{agentStatus && agentStatus.status === "running" ? (
								// Agent Running State
								<div className="space-y-4">
									<div className="flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg">
										<div className="flex items-center gap-3">
											<Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
											<div>
												<p className="font-semibold text-blue-900">
													{selectedAgentType === "planner" && "Planner Agent"}
													{selectedAgentType === "coder" && "Coder Agent"}
													{selectedAgentType === "qa_reviewer" &&
														"QA Reviewer Agent"}
													{selectedAgentType === "qa_fixer" && "QA Fixer Agent"}
												</p>
												<p className="text-sm text-blue-700">Running...</p>
											</div>
										</div>
										<Button
											onClick={handleCancelAgent}
											disabled={isCancellingAgent}
											variant="destructive"
											size="sm"
										>
											<Square className="h-4 w-4 mr-2" />
											{isCancellingAgent ? "Cancelling..." : "Cancel"}
										</Button>
									</div>
									<div className="text-xs text-gray-500">
										Task ID: {agentStatus.task_id}
									</div>
								</div>
							) : (
								// Agent Selection Grid
								<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
									{agentTypes.map((agentType) => (
										<div
											key={agentType.type}
											className="p-4 border rounded-lg hover:bg-gray-50 transition-colors"
										>
											<div className="flex items-center gap-2 mb-2">
												{agentType.icon}
												<h4 className="font-semibold text-sm">
													{agentType.label}
												</h4>
											</div>
											<p className="text-xs text-gray-600 mb-3">
												{agentType.description}
											</p>
											<Button
												onClick={() => handleStartAgent(agentType.type)}
												disabled={
													isStartingAgent || agentStatus?.status === "running"
												}
												variant="outline"
												size="sm"
												className="w-full"
											>
												<Play className="h-3 w-3 mr-1" />
												{isStartingAgent && selectedAgentType === agentType.type
													? "Starting..."
													: "Start"}
											</Button>
										</div>
									))}
								</div>
							)}
						</CardContent>
					</Card>

					{/* Spec Content Card */}
					{task.spec_content && (
						<Card>
							<CardContent className="pt-6">
								<h3 className="text-lg font-semibold mb-4">
									{t("common:specs")}
								</h3>
								<ScrollArea className="h-[400px] w-full rounded-md border p-4">
									<pre className="text-sm font-mono whitespace-pre-wrap">
										{task.spec_content}
									</pre>
								</ScrollArea>
							</CardContent>
						</Card>
					)}

					{/* Folder Location Card */}
					<Card>
						<CardContent className="pt-6">
							<h3 className="text-lg font-semibold mb-4">
								{t("common:labels.location", "Location")}
							</h3>
							<div className="flex items-center gap-2">
								<code className="text-sm bg-gray-100 px-3 py-1 rounded">
									{task.folder}
								</code>
							</div>
						</CardContent>
					</Card>
				</div>
			</div>
		</div>
	);
}
