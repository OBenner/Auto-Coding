/**
 * Roadmap Page
 *
 * Displays the product roadmap in a timeline view.
 * Shows planned features organized by phase/timeline.
 */

import {
	Calendar,
	CheckCircle2,
	Circle,
	Clock,
	Map,
	Plus,
	RefreshCw,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { PageErrorState, PageLoadingState } from "../components/PageStates";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { ScrollArea } from "../components/ui/scroll-area";

/**
 * Roadmap feature type
 */
interface RoadmapFeature {
	id: string;
	title: string;
	description: string;
	status: "planned" | "in_progress" | "completed";
	priority: "low" | "medium" | "high";
}

/**
 * Roadmap phase type
 */
interface RoadmapPhase {
	id: string;
	name: string;
	description: string;
	features: RoadmapFeature[];
}

/**
 * Roadmap data type
 */
interface RoadmapData {
	phases: RoadmapPhase[];
	lastUpdated: Date;
}

interface RoadmapProps {
	onGoToTask?: (specId: string) => void;
}

/**
 * Status icon component
 */
function StatusIcon({ status }: { status: RoadmapFeature["status"] }) {
	switch (status) {
		case "completed":
			return <CheckCircle2 className="h-4 w-4 text-green-500" />;
		case "in_progress":
			return <Clock className="h-4 w-4 text-blue-500 animate-pulse" />;
		default:
			return <Circle className="h-4 w-4 text-gray-400" />;
	}
}

/**
 * Priority badge component
 */
function PriorityBadge({ priority }: { priority: RoadmapFeature["priority"] }) {
	const colors = {
		high: "bg-red-100 text-red-700 border-red-200",
		medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
		low: "bg-gray-100 text-gray-700 border-gray-200",
	};

	return (
		<span
			className={`text-xs px-2 py-0.5 rounded-full border ${colors[priority]}`}
		>
			{priority}
		</span>
	);
}

/**
 * Feature card component
 */
function FeatureCard({ feature }: { feature: RoadmapFeature }) {
	return (
		<div className="p-3 bg-white rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all">
			<div className="flex items-start gap-3">
				<StatusIcon status={feature.status} />
				<div className="flex-1 min-w-0">
					<div className="flex items-center justify-between gap-2">
						<h4 className="font-medium text-gray-900 truncate">
							{feature.title}
						</h4>
						<PriorityBadge priority={feature.priority} />
					</div>
					<p className="text-sm text-gray-600 mt-1 line-clamp-2">
						{feature.description}
					</p>
				</div>
			</div>
		</div>
	);
}

/**
 * Timeline phase component
 */
function TimelinePhase({
	phase,
	isLast,
}: {
	phase: RoadmapPhase;
	isLast: boolean;
}) {
	const completedCount = phase.features.filter(
		(f) => f.status === "completed",
	).length;
	const totalCount = phase.features.length;
	const progressPercent =
		totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

	return (
		<div className="relative flex gap-4">
			{/* Timeline connector */}
			<div className="flex flex-col items-center">
				<div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold text-sm shadow-md">
					{phase.id}
				</div>
				{!isLast && <div className="w-0.5 h-full bg-gray-200 mt-2" />}
			</div>

			{/* Phase content */}
			<div className="flex-1 pb-8">
				<div className="mb-4">
					<h3 className="text-lg font-semibold text-gray-900">{phase.name}</h3>
					<p className="text-sm text-gray-600">{phase.description}</p>

					{/* Progress bar */}
					<div className="mt-2 flex items-center gap-2">
						<div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
							<div
								className="h-full bg-gradient-to-r from-blue-500 to-purple-600 transition-all duration-300"
								style={{ width: `${progressPercent}%` }}
							/>
						</div>
						<span className="text-xs text-gray-500 whitespace-nowrap">
							{completedCount}/{totalCount} done
						</span>
					</div>
				</div>

				{/* Features */}
				<div className="space-y-2">
					{phase.features.map((feature) => (
						<FeatureCard key={feature.id} feature={feature} />
					))}
				</div>
			</div>
		</div>
	);
}

/**
 * Empty state component
 */
function EmptyState({ onGenerate }: { onGenerate: () => void }) {
	return (
		<div className="flex items-center justify-center min-h-[400px]">
			<div className="text-center max-w-md">
				<div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mx-auto mb-4">
					<Map className="h-8 w-8 text-white" />
				</div>
				<h2 className="text-xl font-semibold text-gray-900 mb-2">
					No Roadmap Yet
				</h2>
				<p className="text-gray-600 mb-6">
					Generate a product roadmap to plan and track your features across
					different phases.
				</p>
				<Button
					onClick={onGenerate}
					className="bg-gradient-to-br from-blue-500 to-purple-600 hover:opacity-90"
				>
					<Plus className="h-4 w-4 mr-2" />
					Generate Roadmap
				</Button>
			</div>
		</div>
	);
}

export function Roadmap({ onGoToTask }: RoadmapProps) {
	const [roadmap, setRoadmap] = useState<RoadmapData | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [isRefreshing, setIsRefreshing] = useState(false);

	/**
	 * Fetch roadmap data - currently using placeholder data
	 * TODO: Connect to roadmap API when available
	 */
	const fetchRoadmap = useCallback(async (showRefreshIndicator = false) => {
		try {
			if (showRefreshIndicator) {
				setIsRefreshing(true);
			} else {
				setIsLoading(true);
			}
			setError(null);

			// Simulate API delay
			await new Promise((resolve) => setTimeout(resolve, 500));

			// Placeholder roadmap data for demonstration
			// Replace with actual API call when backend endpoint is available
			const placeholderRoadmap: RoadmapData = {
				phases: [
					{
						id: "1",
						name: "Foundation",
						description: "Core infrastructure and essential features",
						features: [
							{
								id: "f1",
								title: "Task Management System",
								description:
									"Create, view, and manage tasks with status tracking",
								status: "completed",
								priority: "high",
							},
							{
								id: "f2",
								title: "Agent Execution Pipeline",
								description:
									"Run AI agents with planner, coder, and QA reviewer",
								status: "completed",
								priority: "high",
							},
							{
								id: "f3",
								title: "WebSocket Real-time Updates",
								description: "Live progress updates during agent execution",
								status: "in_progress",
								priority: "high",
							},
						],
					},
					{
						id: "2",
						name: "Enhanced Experience",
						description: "Improved user interface and productivity features",
						features: [
							{
								id: "f4",
								title: "Kanban Board View",
								description: "Drag-and-drop task organization",
								status: "completed",
								priority: "medium",
							},
							{
								id: "f5",
								title: "Terminal Integration",
								description: "Embedded terminal for command execution",
								status: "in_progress",
								priority: "medium",
							},
							{
								id: "f6",
								title: "Dark Mode Support",
								description: "System-aware dark/light theme switching",
								status: "planned",
								priority: "low",
							},
						],
					},
					{
						id: "3",
						name: "Advanced Features",
						description: "Power user features and integrations",
						features: [
							{
								id: "f7",
								title: "GitHub Integration",
								description: "Sync with GitHub issues and pull requests",
								status: "planned",
								priority: "high",
							},
							{
								id: "f8",
								title: "Team Collaboration",
								description: "Share projects and collaborate with team members",
								status: "planned",
								priority: "medium",
							},
							{
								id: "f9",
								title: "Custom Agent Templates",
								description: "Create and share custom agent configurations",
								status: "planned",
								priority: "low",
							},
						],
					},
				],
				lastUpdated: new Date(),
			};

			setRoadmap(placeholderRoadmap);
		} catch (err) {
			const message =
				err instanceof Error ? err.message : "Failed to load roadmap";
			setError(message);
		} finally {
			setIsLoading(false);
			setIsRefreshing(false);
		}
	}, []);

	// Initial load
	useEffect(() => {
		fetchRoadmap();
	}, [fetchRoadmap]);

	// Handle refresh button click
	const handleRefresh = useCallback(() => {
		fetchRoadmap(true);
	}, [fetchRoadmap]);

	// Handle generate roadmap (placeholder)
	const handleGenerate = useCallback(() => {
		// TODO: Implement roadmap generation
		fetchRoadmap();
	}, [fetchRoadmap]);

	if (isLoading) return <PageLoadingState />;
	if (error) return <PageErrorState error={error} onRetry={handleRefresh} />;

	// Empty state
	if (!roadmap || roadmap.phases.length === 0) {
		return (
			<div className="min-h-screen bg-gray-50">
				<div className="max-w-4xl mx-auto p-6">
					<div className="flex items-center justify-between mb-6">
						<h1 className="text-3xl font-bold text-gray-900">Roadmap</h1>
						<Button
							onClick={handleRefresh}
							disabled={isRefreshing}
							variant="outline"
						>
							<RefreshCw
								className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`}
							/>
							Refresh
						</Button>
					</div>
					<EmptyState onGenerate={handleGenerate} />
				</div>
			</div>
		);
	}

	// Calculate overall stats
	const totalFeatures = roadmap.phases.reduce(
		(sum, phase) => sum + phase.features.length,
		0,
	);
	const completedFeatures = roadmap.phases.reduce(
		(sum, phase) =>
			sum + phase.features.filter((f) => f.status === "completed").length,
		0,
	);
	const inProgressFeatures = roadmap.phases.reduce(
		(sum, phase) =>
			sum + phase.features.filter((f) => f.status === "in_progress").length,
		0,
	);

	// Main roadmap view
	return (
		<div className="min-h-screen bg-gray-50">
			<div className="max-w-4xl mx-auto p-6">
				{/* Header */}
				<div className="flex items-center justify-between mb-6">
					<div>
						<h1 className="text-3xl font-bold text-gray-900">Roadmap</h1>
						<p className="text-sm text-gray-600 mt-1">
							Product development timeline
						</p>
					</div>
					<div className="flex gap-2">
						<Button
							onClick={handleRefresh}
							disabled={isRefreshing}
							variant="outline"
						>
							<RefreshCw
								className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`}
							/>
							Refresh
						</Button>
					</div>
				</div>

				{/* Stats Cards */}
				<div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
					<Card className="p-4">
						<div className="flex items-center gap-3">
							<div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
								<Calendar className="h-5 w-5 text-gray-600" />
							</div>
							<div>
								<p className="text-2xl font-bold text-gray-900">
									{roadmap.phases.length}
								</p>
								<p className="text-sm text-gray-600">Phases</p>
							</div>
						</div>
					</Card>

					<Card className="p-4">
						<div className="flex items-center gap-3">
							<div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
								<CheckCircle2 className="h-5 w-5 text-green-600" />
							</div>
							<div>
								<p className="text-2xl font-bold text-gray-900">
									{completedFeatures}/{totalFeatures}
								</p>
								<p className="text-sm text-gray-600">Completed</p>
							</div>
						</div>
					</Card>

					<Card className="p-4">
						<div className="flex items-center gap-3">
							<div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
								<Clock className="h-5 w-5 text-blue-600" />
							</div>
							<div>
								<p className="text-2xl font-bold text-gray-900">
									{inProgressFeatures}
								</p>
								<p className="text-sm text-gray-600">In Progress</p>
							</div>
						</div>
					</Card>
				</div>

				{/* Timeline */}
				<Card className="p-6">
					<ScrollArea className="h-[calc(100vh-400px)]">
						<div className="space-y-0">
							{roadmap.phases.map((phase, index) => (
								<TimelinePhase
									key={phase.id}
									phase={phase}
									isLast={index === roadmap.phases.length - 1}
								/>
							))}
						</div>
					</ScrollArea>
				</Card>
			</div>
		</div>
	);
}
