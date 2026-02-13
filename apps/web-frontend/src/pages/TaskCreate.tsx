/**
 * TaskCreate Page
 *
 * A page-based wizard for creating new tasks/specs.
 * Simplified version of the desktop TaskCreationWizard for the web interface.
 */

import {
	ArrowLeft,
	Brain,
	ChevronDown,
	ChevronUp,
	Code,
	Info,
	Loader2,
	Search,
	Wrench,
} from "lucide-react";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/client";
import type { AgentType } from "../api/types";
import { Button } from "../components/ui/button";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../components/ui/card";
import { Label } from "../components/ui/label";
import { ScrollArea } from "../components/ui/scroll-area";
import { Separator } from "../components/ui/separator";

interface TaskCreateProps {
	onCreateSuccess?: (taskId: string) => void;
}

export function TaskCreate({ onCreateSuccess }: TaskCreateProps) {
	const { t } = useTranslation(["common", "tasks"]);
	const navigate = useNavigate();

	// Form state
	const [name, setName] = useState("");
	const [description, setDescription] = useState("");
	const [isCreating, setIsCreating] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [showAgentInfo, setShowAgentInfo] = useState(false);

	// Agent types information
	const agentTypes: Array<{
		type: AgentType;
		label: string;
		description: string;
		icon: React.ReactNode;
	}> = [
		{
			type: "planner",
			label: "Planner",
			description: "Creates implementation plan with subtasks",
			icon: <Brain className="h-5 w-5" />,
		},
		{
			type: "coder",
			label: "Coder",
			description: "Implements individual subtasks",
			icon: <Code className="h-5 w-5" />,
		},
		{
			type: "qa_reviewer",
			label: "QA Reviewer",
			description: "Validates acceptance criteria",
			icon: <Search className="h-5 w-5" />,
		},
		{
			type: "qa_fixer",
			label: "QA Fixer",
			description: "Fixes QA-reported issues",
			icon: <Wrench className="h-5 w-5" />,
		},
	];

	/**
	 * Handle form submission
	 */
	const handleSubmit = useCallback(
		async (e: React.FormEvent<HTMLFormElement>) => {
			e.preventDefault();

			if (!description.trim()) {
				setError("Task description is required");
				return;
			}

			setIsCreating(true);
			setError(null);

			try {
				const response = await apiClient.createTask({
					name: name.trim() || "Untitled Task",
					description: description.trim(),
				});

				if (response.spec_id) {
					// Call success callback or navigate to task detail
					if (onCreateSuccess) {
						onCreateSuccess(response.spec_id);
					} else {
						navigate(`/tasks/${response.spec_id}`);
					}
				} else {
					setError("Failed to create task: No spec ID returned");
				}
			} catch (err) {
				const message =
					err instanceof Error ? err.message : "Failed to create task";
				setError(message);
			} finally {
				setIsCreating(false);
			}
		},
		[name, description, onCreateSuccess, navigate],
	);

	/**
	 * Handle back navigation
	 */
	const handleBack = useCallback(() => {
		navigate("/tasks");
	}, [navigate]);

	return (
		<div className="min-h-screen bg-gray-50">
			<div className="max-w-4xl mx-auto p-6">
				{/* Header */}
				<div className="flex items-center gap-4 mb-6">
					<Button
						onClick={handleBack}
						variant="outline"
						size="icon"
						disabled={isCreating}
					>
						<ArrowLeft className="h-4 w-4" />
					</Button>
					<div>
						<h1 className="text-3xl font-bold text-gray-900">
							Create New Task
						</h1>
						<p className="text-sm text-gray-600 mt-1">
							Describe what you want to build
						</p>
					</div>
				</div>

				<form onSubmit={handleSubmit} className="space-y-6">
					{/* Info Banner */}
					<div className="flex items-start gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
						<Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
						<div className="flex-1 min-w-0">
							<h4 className="text-sm font-medium text-gray-900 mb-1">
								How It Works
							</h4>
							<p className="text-sm text-gray-600">
								Describe your task in detail. The AI will create a specification
								and break it down into subtasks, then implement them using
								coordinated agents.
							</p>
						</div>
					</div>

					{/* Main Form Card */}
					<Card>
						<CardContent className="space-y-6 pt-6">
							{/* Task Name (Optional) */}
							<div className="space-y-2">
								<Label
									htmlFor="task-name"
									className="text-sm font-medium text-gray-900"
								>
									Task Name{" "}
									<span className="text-gray-400 font-normal">(optional)</span>
								</Label>
								<input
									id="task-name"
									type="text"
									value={name}
									onChange={(e) => setName(e.target.value)}
									placeholder="e.g., Add User Authentication"
									disabled={isCreating}
									className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
								/>
								<p className="text-xs text-gray-500">
									A short title for your task. If left blank, will be
									auto-generated.
								</p>
							</div>

							<Separator />

							{/* Task Description (Required) */}
							<div className="space-y-2">
								<Label
									htmlFor="task-description"
									className="text-sm font-medium text-gray-900"
								>
									Task Description <span className="text-red-500">*</span>
								</Label>
								<textarea
									id="task-description"
									value={description}
									onChange={(e) => setDescription(e.target.value)}
									placeholder="Describe what you want to build in detail. Include requirements, features, and any specific constraints..."
									disabled={isCreating}
									rows={12}
									className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:bg-gray-100 disabled:cursor-not-allowed font-mono text-sm"
								/>
								<p className="text-xs text-gray-500">
									Be specific and detailed. The more context you provide, the
									better the AI can understand and implement your task.
								</p>
							</div>

							{/* Error Message */}
							{error && (
								<div className="p-3 bg-red-50 border border-red-200 rounded-lg">
									<p className="text-sm text-red-700">{error}</p>
								</div>
							)}
						</CardContent>
					</Card>

					{/* Agent Process Info */}
					<Card>
						<CardHeader>
							<button
								type="button"
								onClick={() => setShowAgentInfo(!showAgentInfo)}
								className="flex items-center justify-between w-full text-left"
							>
								<CardTitle className="text-lg font-semibold">
									Agent Workflow
								</CardTitle>
								{showAgentInfo ? (
									<ChevronUp className="h-5 w-5 text-gray-500" />
								) : (
									<ChevronDown className="h-5 w-5 text-gray-500" />
								)}
							</button>
						</CardHeader>
						{showAgentInfo && (
							<CardContent>
								<ScrollArea className="h-[300px] pr-4">
									<div className="space-y-4">
										{agentTypes.map((agent) => (
											<div
												key={agent.type}
												className="flex items-start gap-3 p-3 border rounded-lg bg-gray-50"
											>
												<div className="flex-shrink-0 mt-0.5 text-blue-600">
													{agent.icon}
												</div>
												<div className="flex-1 min-w-0">
													<h4 className="font-semibold text-sm text-gray-900 mb-1">
														{agent.label}
													</h4>
													<p className="text-sm text-gray-600">
														{agent.description}
													</p>
												</div>
											</div>
										))}
									</div>
								</ScrollArea>
							</CardContent>
						)}
					</Card>

					{/* Action Buttons */}
					<div className="flex items-center justify-between">
						<Button
							type="button"
							onClick={handleBack}
							variant="outline"
							disabled={isCreating}
						>
							Cancel
						</Button>
						<Button
							type="submit"
							disabled={isCreating || !description.trim()}
							className="min-w-[150px]"
						>
							{isCreating ? (
								<>
									<Loader2 className="mr-2 h-4 w-4 animate-spin" />
									Creating...
								</>
							) : (
								<>
									<Brain className="mr-2 h-4 w-4" />
									Create Task
								</>
							)}
						</Button>
					</div>
				</form>
			</div>
		</div>
	);
}
