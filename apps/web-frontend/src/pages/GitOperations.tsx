/**
 * GitOperations Page
 *
 * Displays git worktrees and branch information for the project.
 * Allows management of isolated workspaces created by Auto Code tasks.
 */

import {
	AlertCircle,
	ChevronRight,
	FileCode,
	FolderGit,
	FolderOpen,
	GitBranch,
	GitMerge,
	GitPullRequest,
	Loader2,
	Minus,
	Plus,
	RefreshCw,
	Trash2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../components/ui/card";
import { ScrollArea } from "../components/ui/scroll-area";

/**
 * Worktree item representing an isolated workspace
 */
interface WorktreeItem {
	id: string;
	specName: string;
	branch: string;
	baseBranch: string;
	path: string;
	filesChanged: number;
	commitCount: number;
	additions: number;
	deletions: number;
	taskTitle?: string;
}

/**
 * Mock worktree data for demonstration
 * In production, this would come from the backend API
 */
const MOCK_WORKTREES: WorktreeItem[] = [];

export function GitOperations() {
	const { t } = useTranslation(["common"]);
	const [worktrees, setWorktrees] = useState<WorktreeItem[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [isRefreshing, setIsRefreshing] = useState(false);

	/**
	 * Fetch worktrees from the API
	 * Currently returns mock data - will be replaced with actual API call
	 */
	const fetchWorktrees = useCallback(
		async (showRefreshIndicator = false) => {
			try {
				if (showRefreshIndicator) {
					setIsRefreshing(true);
				} else {
					setIsLoading(true);
				}
				setError(null);

				// Simulate API call delay
				await new Promise((resolve) => setTimeout(resolve, 500));

				// TODO: Replace with actual API call when backend endpoint is available
				// const response = await apiClient.listWorktrees();
				setWorktrees(MOCK_WORKTREES);
			} catch (err) {
				const message =
					err instanceof Error ? err.message : "Failed to load worktrees";
				setError(message);
			} finally {
				setIsLoading(false);
				setIsRefreshing(false);
			}
		},
		[],
	);

	// Initial load
	useEffect(() => {
		fetchWorktrees();
	}, [fetchWorktrees]);

	// Handle refresh button click
	const handleRefresh = useCallback(() => {
		fetchWorktrees(true);
	}, [fetchWorktrees]);

	// Copy path to clipboard
	const handleCopyPath = useCallback((path: string) => {
		navigator.clipboard.writeText(path);
	}, []);

	// Loading state
	if (isLoading) {
		return (
			<div className="min-h-screen bg-gray-50 flex items-center justify-center">
				<div className="text-center">
					<Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
					<p className="text-gray-600">{t("common:loading")}</p>
				</div>
			</div>
		);
	}

	// Error state
	if (error) {
		return (
			<div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
				<div className="text-center max-w-md">
					<AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
					<h2 className="text-xl font-semibold text-gray-900 mb-2">
						{t("common:error")}
					</h2>
					<p className="text-gray-600 mb-4">{error}</p>
					<Button onClick={handleRefresh}>
						<RefreshCw className="h-4 w-4 mr-2" />
						Try Again
					</Button>
				</div>
			</div>
		);
	}

	return (
		<div className="min-h-screen bg-gray-50">
			<div className="max-w-6xl mx-auto p-6">
				{/* Header */}
				<div className="flex items-center justify-between mb-6">
					<div>
						<h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
							<GitBranch className="h-8 w-8 text-blue-600" />
							Git Operations
						</h1>
						<p className="text-sm text-gray-600 mt-1">
							Manage isolated workspaces for your Auto Code tasks
						</p>
					</div>
					<div className="flex items-center gap-3">
						<a
							href="/"
							className="text-blue-600 hover:text-blue-700 font-medium text-sm"
						>
							← Back to Home
						</a>
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

				{/* Empty state */}
				{worktrees.length === 0 && (
					<div className="flex flex-col items-center justify-center min-h-[400px] text-center">
						<div className="rounded-full bg-gray-100 p-6 mb-4">
							<GitBranch className="h-12 w-12 text-gray-400" />
						</div>
						<h3 className="text-xl font-semibold text-gray-900 mb-2">
							No Worktrees
						</h3>
						<p className="text-gray-600 max-w-md mb-6">
							Worktrees are created automatically when Auto Code builds
							features. Start a new task to create an isolated workspace.
						</p>
						<div className="flex gap-3">
							<Button
								variant="outline"
								onClick={() => (window.location.href = "/tasks")}
							>
								View Tasks
							</Button>
							<Button
								className="bg-gradient-to-br from-blue-500 to-purple-600 hover:opacity-90"
								onClick={() => (window.location.href = "/tasks/create")}
							>
								Create Task
							</Button>
						</div>
					</div>
				)}

				{/* Worktrees list */}
				{worktrees.length > 0 && (
					<ScrollArea className="h-[calc(100vh-200px)]">
						<div className="space-y-4">
							{worktrees.map((worktree) => (
								<Card key={worktree.id} className="overflow-hidden">
									<CardHeader className="pb-3">
										<div className="flex items-start justify-between">
											<div className="flex-1 min-w-0">
												<CardTitle className="text-base flex items-center gap-2">
													<FolderGit className="h-4 w-4 text-blue-600 shrink-0" />
													<span className="truncate">{worktree.branch}</span>
												</CardTitle>
												{worktree.taskTitle && (
													<p className="text-sm text-gray-500 mt-1 truncate">
														{worktree.taskTitle}
													</p>
												)}
											</div>
											<Badge variant="outline" className="shrink-0 ml-2">
												{worktree.specName}
											</Badge>
										</div>
									</CardHeader>
									<CardContent className="pt-0">
										{/* Stats */}
										<div className="flex flex-wrap gap-4 text-sm mb-4">
											<div className="flex items-center gap-1.5 text-gray-600">
												<FileCode className="h-3.5 w-3.5" />
												<span>{worktree.filesChanged} files changed</span>
											</div>
											<div className="flex items-center gap-1.5 text-gray-600">
												<ChevronRight className="h-3.5 w-3.5" />
												<span>{worktree.commitCount} commits ahead</span>
											</div>
											<div className="flex items-center gap-1.5 text-green-600">
												<Plus className="h-3.5 w-3.5" />
												<span>{worktree.additions}</span>
											</div>
											<div className="flex items-center gap-1.5 text-red-600">
												<Minus className="h-3.5 w-3.5" />
												<span>{worktree.deletions}</span>
											</div>
										</div>

										{/* Branch info */}
										<div className="flex items-center gap-2 text-xs text-gray-600 mb-4 bg-gray-50 rounded-md p-2">
											<span className="font-mono">{worktree.baseBranch}</span>
											<ChevronRight className="h-3 w-3" />
											<span className="font-mono text-blue-600">
												{worktree.branch}
											</span>
										</div>

										{/* Actions */}
										<div className="flex flex-wrap gap-2">
											<Button variant="default" size="sm" disabled>
												<GitMerge className="h-3.5 w-3.5 mr-1.5" />
												Merge to {worktree.baseBranch}
											</Button>
											<Button variant="outline" size="sm" disabled>
												<GitPullRequest className="h-3.5 w-3.5 mr-1.5" />
												Create PR
											</Button>
											<Button
												variant="outline"
												size="sm"
												onClick={() => handleCopyPath(worktree.path)}
											>
												<FolderOpen className="h-3.5 w-3.5 mr-1.5" />
												Copy Path
											</Button>
											<Button
												variant="outline"
												size="sm"
												className="text-red-600 hover:text-red-700 hover:bg-red-50"
												disabled
											>
												<Trash2 className="h-3.5 w-3.5 mr-1.5" />
												Delete
											</Button>
										</div>
									</CardContent>
								</Card>
							))}
						</div>
					</ScrollArea>
				)}

				{/* Info section */}
				<div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
					<h4 className="font-medium text-blue-900 mb-2 flex items-center gap-2">
						<GitBranch className="h-4 w-4" />
						About Git Worktrees
					</h4>
					<p className="text-sm text-blue-700">
						Auto Code uses git worktrees to create isolated workspaces for each
						task. This allows multiple features to be developed in parallel
						without conflicts. When a task is complete, you can merge the
						changes back to your main branch or create a pull request.
					</p>
				</div>
			</div>
		</div>
	);
}
