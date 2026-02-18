/**
 * Changelog Page
 *
 * Displays the project changelog with version history and release notes.
 * Shows completed features and tasks organized by release version.
 */

import {
	Calendar,
	CheckCircle2,
	Clock,
	FileText,
	GitCommit,
	RefreshCw,
	Tag,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { PageErrorState, PageLoadingState } from "../components/PageStates";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { ScrollArea } from "../components/ui/scroll-area";

/**
 * Change type for a single changelog item
 */
type ChangeType = "feature" | "fix" | "improvement" | "breaking";

/**
 * Single change entry in a release
 */
interface ChangeEntry {
	id: string;
	type: ChangeType;
	description: string;
	taskId?: string;
}

/**
 * Release version with changes
 */
interface ReleaseEntry {
	version: string;
	date: string;
	title?: string;
	changes: ChangeEntry[];
}

/**
 * Full changelog data structure
 */
interface ChangelogData {
	releases: ReleaseEntry[];
	lastUpdated: Date;
}

/**
 * Get badge variant and label for change type
 */
function getChangeTypeInfo(type: ChangeType): {
	variant: "default" | "secondary" | "destructive" | "outline";
	label: string;
	color: string;
} {
	switch (type) {
		case "feature":
			return {
				variant: "default",
				label: "Feature",
				color: "bg-green-100 text-green-700 border-green-200",
			};
		case "fix":
			return {
				variant: "secondary",
				label: "Fix",
				color: "bg-blue-100 text-blue-700 border-blue-200",
			};
		case "improvement":
			return {
				variant: "outline",
				label: "Improvement",
				color: "bg-purple-100 text-purple-700 border-purple-200",
			};
		case "breaking":
			return {
				variant: "destructive",
				label: "Breaking",
				color: "bg-red-100 text-red-700 border-red-200",
			};
	}
}

/**
 * Change type badge component
 */
function ChangeTypeBadge({ type }: { type: ChangeType }) {
	const info = getChangeTypeInfo(type);

	return (
		<span className={`text-xs px-2 py-0.5 rounded-full border ${info.color}`}>
			{info.label}
		</span>
	);
}

/**
 * Single change entry component
 */
function ChangeItem({ change }: { change: ChangeEntry }) {
	return (
		<div className="flex items-start gap-3 py-2">
			<div className="mt-0.5">
				<ChangeTypeBadge type={change.type} />
			</div>
			<div className="flex-1 min-w-0">
				<p className="text-sm text-gray-700">{change.description}</p>
				{change.taskId && (
					<span className="text-xs text-gray-500 font-mono">
						#{change.taskId}
					</span>
				)}
			</div>
		</div>
	);
}

/**
 * Release card component
 */
function ReleaseCard({ release }: { release: ReleaseEntry }) {
	const releaseDate = new Date(release.date).toLocaleDateString("en-US", {
		year: "numeric",
		month: "long",
		day: "numeric",
	});

	const featureCount = release.changes.filter(
		(c) => c.type === "feature",
	).length;
	const fixCount = release.changes.filter((c) => c.type === "fix").length;
	const improvementCount = release.changes.filter(
		(c) => c.type === "improvement",
	).length;
	const breakingCount = release.changes.filter(
		(c) => c.type === "breaking",
	).length;

	return (
		<Card className="p-6 mb-4">
			<div className="flex items-start justify-between mb-4">
				<div className="flex items-center gap-3">
					<div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
						<Tag className="h-5 w-5 text-white" />
					</div>
					<div>
						<div className="flex items-center gap-2">
							<h3 className="text-lg font-semibold text-gray-900">
								v{release.version}
							</h3>
							{breakingCount > 0 && (
								<Badge variant="destructive" className="text-xs">
									Breaking Changes
								</Badge>
							)}
						</div>
						{release.title && (
							<p className="text-sm text-gray-600">{release.title}</p>
						)}
					</div>
				</div>
				<div className="flex items-center gap-2 text-sm text-gray-500">
					<Calendar className="h-4 w-4" />
					{releaseDate}
				</div>
			</div>

			{/* Change stats */}
			<div className="flex gap-4 mb-4 text-xs">
				{featureCount > 0 && (
					<div className="flex items-center gap-1.5">
						<CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
						<span className="text-gray-600">
							{featureCount} feature{featureCount !== 1 ? "s" : ""}
						</span>
					</div>
				)}
				{fixCount > 0 && (
					<div className="flex items-center gap-1.5">
						<GitCommit className="h-3.5 w-3.5 text-blue-500" />
						<span className="text-gray-600">
							{fixCount} fix{fixCount !== 1 ? "es" : ""}
						</span>
					</div>
				)}
				{improvementCount > 0 && (
					<div className="flex items-center gap-1.5">
						<Clock className="h-3.5 w-3.5 text-purple-500" />
						<span className="text-gray-600">
							{improvementCount} improvement{improvementCount !== 1 ? "s" : ""}
						</span>
					</div>
				)}
			</div>

			{/* Changes list */}
			<div className="border-t border-gray-100 pt-4">
				<div className="space-y-1">
					{release.changes.map((change) => (
						<ChangeItem key={change.id} change={change} />
					))}
				</div>
			</div>
		</Card>
	);
}

/**
 * Empty state component
 */
function EmptyState() {
	return (
		<div className="flex items-center justify-center min-h-[400px]">
			<div className="text-center max-w-md">
				<div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mx-auto mb-4">
					<FileText className="h-8 w-8 text-white" />
				</div>
				<h2 className="text-xl font-semibold text-gray-900 mb-2">
					No Changelog Entries
				</h2>
				<p className="text-gray-600">
					Complete tasks and generate changelogs to see your release history
					here.
				</p>
			</div>
		</div>
	);
}

export function Changelog() {
	const [changelog, setChangelog] = useState<ChangelogData | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [isRefreshing, setIsRefreshing] = useState(false);

	/**
	 * Fetch changelog data
	 * TODO: Connect to changelog API when available
	 */
	const fetchChangelog = useCallback(async (showRefreshIndicator = false) => {
		try {
			if (showRefreshIndicator) {
				setIsRefreshing(true);
			} else {
				setIsLoading(true);
			}
			setError(null);

			// Simulate API delay
			await new Promise((resolve) => setTimeout(resolve, 500));

			// Placeholder changelog data for demonstration
			// Replace with actual API call when backend endpoint is available
			const placeholderChangelog: ChangelogData = {
				releases: [
					{
						version: "2.0.0",
						date: "2025-02-10",
						title: "Web Frontend Launch",
						changes: [
							{
								id: "c1",
								type: "feature",
								description:
									"Web-based frontend for browser access without desktop app",
								taskId: "141",
							},
							{
								id: "c2",
								type: "feature",
								description:
									"Real-time WebSocket updates for agent execution progress",
							},
							{
								id: "c3",
								type: "feature",
								description: "Kanban board for visual task management",
							},
							{
								id: "c4",
								type: "breaking",
								description: "API endpoints restructured for web compatibility",
							},
						],
					},
					{
						version: "1.5.0",
						date: "2025-01-28",
						title: "Enhanced Agent System",
						changes: [
							{
								id: "c5",
								type: "feature",
								description: "Multi-agent parallel execution support",
							},
							{
								id: "c6",
								type: "improvement",
								description: "Improved error handling in QA reviewer agent",
							},
							{
								id: "c7",
								type: "fix",
								description: "Fixed memory leak in long-running sessions",
							},
						],
					},
					{
						version: "1.4.2",
						date: "2025-01-15",
						title: "Bug Fixes",
						changes: [
							{
								id: "c8",
								type: "fix",
								description: "Fixed task status not updating in real-time",
							},
							{
								id: "c9",
								type: "fix",
								description: "Resolved Git worktree cleanup issues",
							},
							{
								id: "c10",
								type: "improvement",
								description: "Better error messages for failed builds",
							},
						],
					},
					{
						version: "1.4.0",
						date: "2025-01-05",
						title: "Roadmap & Planning",
						changes: [
							{
								id: "c11",
								type: "feature",
								description: "Product roadmap visualization",
							},
							{
								id: "c12",
								type: "feature",
								description: "Sprint planning integration",
							},
							{
								id: "c13",
								type: "improvement",
								description: "Faster spec creation workflow",
							},
						],
					},
				],
				lastUpdated: new Date(),
			};

			setChangelog(placeholderChangelog);
		} catch (err) {
			const message =
				err instanceof Error ? err.message : "Failed to load changelog";
			setError(message);
		} finally {
			setIsLoading(false);
			setIsRefreshing(false);
		}
	}, []);

	// Initial load
	useEffect(() => {
		fetchChangelog();
	}, [fetchChangelog]);

	// Handle refresh button click
	const handleRefresh = useCallback(() => {
		fetchChangelog(true);
	}, [fetchChangelog]);

	if (isLoading) return <PageLoadingState />;
	if (error) return <PageErrorState error={error} onRetry={handleRefresh} />;

	// Empty state
	if (!changelog || changelog.releases.length === 0) {
		return (
			<div className="min-h-screen bg-gray-50">
				<div className="max-w-4xl mx-auto p-6">
					<div className="flex items-center justify-between mb-6">
						<h1 className="text-3xl font-bold text-gray-900">Changelog</h1>
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
					<EmptyState />
				</div>
			</div>
		);
	}

	// Calculate stats
	const totalReleases = changelog.releases.length;
	const totalChanges = changelog.releases.reduce(
		(sum, release) => sum + release.changes.length,
		0,
	);
	const latestVersion = changelog.releases[0]?.version || "0.0.0";

	// Main changelog view
	return (
		<div className="min-h-screen bg-gray-50">
			<div className="max-w-4xl mx-auto p-6">
				{/* Header */}
				<div className="flex items-center justify-between mb-6">
					<div>
						<h1 className="text-3xl font-bold text-gray-900">Changelog</h1>
						<p className="text-sm text-gray-600 mt-1">
							Version history and release notes
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
							<div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
								<Tag className="h-5 w-5 text-white" />
							</div>
							<div>
								<p className="text-2xl font-bold text-gray-900">
									v{latestVersion}
								</p>
								<p className="text-sm text-gray-600">Latest Version</p>
							</div>
						</div>
					</Card>

					<Card className="p-4">
						<div className="flex items-center gap-3">
							<div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
								<FileText className="h-5 w-5 text-green-600" />
							</div>
							<div>
								<p className="text-2xl font-bold text-gray-900">
									{totalReleases}
								</p>
								<p className="text-sm text-gray-600">Releases</p>
							</div>
						</div>
					</Card>

					<Card className="p-4">
						<div className="flex items-center gap-3">
							<div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
								<CheckCircle2 className="h-5 w-5 text-purple-600" />
							</div>
							<div>
								<p className="text-2xl font-bold text-gray-900">
									{totalChanges}
								</p>
								<p className="text-sm text-gray-600">Total Changes</p>
							</div>
						</div>
					</Card>
				</div>

				{/* Releases List */}
				<ScrollArea className="h-[calc(100vh-400px)]">
					{changelog.releases.map((release) => (
						<ReleaseCard key={release.version} release={release} />
					))}
				</ScrollArea>
			</div>
		</div>
	);
}
