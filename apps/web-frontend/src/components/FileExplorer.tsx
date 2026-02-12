/**
 * FileExplorer Component (Web Version)
 * A file tree explorer with expandable folders and file type icons.
 * Adapted from Electron frontend FileTree component.
 */

import {
	AlertCircle,
	ChevronDown,
	ChevronRight,
	File,
	FileCode,
	FileImage,
	FileJson,
	FileText,
	Folder,
	FolderOpen,
	Loader2,
	RefreshCw,
} from "lucide-react";
import { useCallback, useState } from "react";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";

/**
 * FileNode represents a file or directory in the tree
 */
export interface FileNode {
	path: string;
	name: string;
	isDirectory: boolean;
	children?: FileNode[];
}

interface FileExplorerProps {
	/** Root path to display (for API calls) */
	rootPath?: string;
	/** Initial file tree data (optional, can be loaded via API) */
	initialFiles?: FileNode[];
	/** Callback when a file is selected */
	onFileSelect?: (file: FileNode) => void;
	/** Custom class name */
	className?: string;
	/** API URL for fetching files */
	apiUrl?: string;
}

interface FileTreeItemProps {
	node: FileNode;
	depth: number;
	expandedPaths: Set<string>;
	loadingPaths: Set<string>;
	onToggle: (node: FileNode) => void;
	onSelect?: (node: FileNode) => void;
}

/**
 * Get appropriate icon based on file extension
 */
function getFileIcon(name: string): React.ReactNode {
	const ext = name.split(".").pop()?.toLowerCase();

	switch (ext) {
		case "ts":
		case "tsx":
		case "js":
		case "jsx":
		case "py":
		case "rb":
		case "go":
		case "rs":
		case "java":
		case "c":
		case "cpp":
		case "h":
		case "cs":
		case "php":
		case "swift":
		case "kt":
			return <FileCode className="h-4 w-4 text-blue-400" />;
		case "json":
		case "yaml":
		case "yml":
		case "toml":
			return <FileJson className="h-4 w-4 text-yellow-400" />;
		case "md":
		case "txt":
		case "rst":
			return <FileText className="h-4 w-4 text-gray-400" />;
		case "png":
		case "jpg":
		case "jpeg":
		case "gif":
		case "svg":
		case "webp":
		case "ico":
			return <FileImage className="h-4 w-4 text-purple-400" />;
		case "css":
		case "scss":
		case "sass":
		case "less":
			return <FileCode className="h-4 w-4 text-pink-400" />;
		case "html":
		case "htm":
			return <FileCode className="h-4 w-4 text-orange-400" />;
		default:
			return <File className="h-4 w-4 text-gray-400" />;
	}
}

/**
 * Individual file/folder item in the tree
 */
function FileTreeItem({
	node,
	depth,
	expandedPaths,
	loadingPaths,
	onToggle,
	onSelect,
}: FileTreeItemProps) {
	const isExpanded = expandedPaths.has(node.path);
	const isLoading = loadingPaths.has(node.path);

	const handleClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			if (node.isDirectory) {
				onToggle(node);
			} else {
				onSelect?.(node);
			}
		},
		[node, onToggle, onSelect],
	);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				if (node.isDirectory) {
					onToggle(node);
				} else {
					onSelect?.(node);
				}
			}
		},
		[node, onToggle, onSelect],
	);

	return (
		<>
			<div
				role="treeitem"
				tabIndex={0}
				className={cn(
					"flex items-center gap-1 py-1 px-2 rounded cursor-pointer select-none",
					"hover:bg-accent/50 transition-colors",
					"focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
				)}
				style={{ paddingLeft: `${depth * 12 + 8}px` }}
				onClick={handleClick}
				onKeyDown={handleKeyDown}
				aria-expanded={node.isDirectory ? isExpanded : undefined}
			>
				{/* Expand/collapse chevron for directories */}
				{node.isDirectory ? (
					<button
						type="button"
						className="flex items-center justify-center w-4 h-4 hover:bg-accent rounded"
						onClick={(e) => {
							e.stopPropagation();
							onToggle(node);
						}}
						aria-label={isExpanded ? "Collapse folder" : "Expand folder"}
						tabIndex={-1}
					>
						{isLoading ? (
							<Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
						) : isExpanded ? (
							<ChevronDown className="h-3 w-3 text-muted-foreground" />
						) : (
							<ChevronRight className="h-3 w-3 text-muted-foreground" />
						)}
					</button>
				) : (
					<span className="w-4" />
				)}

				{/* Icon */}
				{node.isDirectory ? (
					<Folder
						className={cn(
							"h-4 w-4",
							isExpanded ? "text-blue-400" : "text-yellow-400",
						)}
					/>
				) : (
					getFileIcon(node.name)
				)}

				{/* Name */}
				<span className="text-xs truncate flex-1 text-foreground">
					{node.name}
				</span>
			</div>

			{/* Render children if expanded */}
			{node.isDirectory && isExpanded && node.children && (
				<div role="group">
					{node.children.map((child) => (
						<FileTreeItem
							key={child.path}
							node={child}
							depth={depth + 1}
							expandedPaths={expandedPaths}
							loadingPaths={loadingPaths}
							onToggle={onToggle}
							onSelect={onSelect}
						/>
					))}
				</div>
			)}
		</>
	);
}

/**
 * Sample data for demonstration when no API is available
 */
const SAMPLE_FILES: FileNode[] = [
	{
		path: "/src",
		name: "src",
		isDirectory: true,
		children: [
			{
				path: "/src/components",
				name: "components",
				isDirectory: true,
				children: [
					{
						path: "/src/components/Button.tsx",
						name: "Button.tsx",
						isDirectory: false,
					},
					{
						path: "/src/components/Card.tsx",
						name: "Card.tsx",
						isDirectory: false,
					},
					{
						path: "/src/components/Input.tsx",
						name: "Input.tsx",
						isDirectory: false,
					},
				],
			},
			{
				path: "/src/pages",
				name: "pages",
				isDirectory: true,
				children: [
					{ path: "/src/pages/Home.tsx", name: "Home.tsx", isDirectory: false },
					{
						path: "/src/pages/About.tsx",
						name: "About.tsx",
						isDirectory: false,
					},
					{
						path: "/src/pages/Settings.tsx",
						name: "Settings.tsx",
						isDirectory: false,
					},
				],
			},
			{
				path: "/src/lib",
				name: "lib",
				isDirectory: true,
				children: [
					{ path: "/src/lib/utils.ts", name: "utils.ts", isDirectory: false },
					{ path: "/src/lib/api.ts", name: "api.ts", isDirectory: false },
				],
			},
			{ path: "/src/App.tsx", name: "App.tsx", isDirectory: false },
			{ path: "/src/main.tsx", name: "main.tsx", isDirectory: false },
			{ path: "/src/index.css", name: "index.css", isDirectory: false },
		],
	},
	{
		path: "/public",
		name: "public",
		isDirectory: true,
		children: [
			{ path: "/public/favicon.ico", name: "favicon.ico", isDirectory: false },
			{ path: "/public/logo.svg", name: "logo.svg", isDirectory: false },
		],
	},
	{ path: "/package.json", name: "package.json", isDirectory: false },
	{ path: "/tsconfig.json", name: "tsconfig.json", isDirectory: false },
	{ path: "/README.md", name: "README.md", isDirectory: false },
	{ path: "/.gitignore", name: ".gitignore", isDirectory: false },
];

/**
 * FileExplorer component - displays a navigable file tree
 */
export function FileExplorer({
	rootPath = "/",
	initialFiles,
	onFileSelect,
	className,
	apiUrl,
}: FileExplorerProps) {
	const [files, setFiles] = useState<FileNode[]>(initialFiles || SAMPLE_FILES);
	const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
	const [loadingPaths, setLoadingPaths] = useState<Set<string>>(new Set());
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	/**
	 * Fetch directory contents from API
	 */
	const fetchDirectory = useCallback(
		async (path: string): Promise<FileNode[] | null> => {
			if (!apiUrl) {
				// Use sample data for directories without API
				return null;
			}

			try {
				const token = localStorage.getItem("auth_token") || "";
				const response = await fetch(
					`${apiUrl}/api/files?path=${encodeURIComponent(path)}`,
					{
						headers: {
							Authorization: `Bearer ${token}`,
						},
					},
				);

				if (!response.ok) {
					throw new Error("Failed to fetch directory contents");
				}

				const data = await response.json();
				return data.files || [];
			} catch (err) {
				console.error("Error fetching directory:", err);
				return null;
			}
		},
		[apiUrl],
	);

	/**
	 * Refresh the file tree from the API
	 */
	const handleRefresh = useCallback(async () => {
		setIsLoading(true);
		setError(null);

		try {
			const newFiles = await fetchDirectory(rootPath);
			if (newFiles) {
				setFiles(newFiles);
			}
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to refresh files");
		} finally {
			setIsLoading(false);
		}
	}, [rootPath, fetchDirectory]);

	/**
	 * Toggle folder expansion
	 */
	const handleToggle = useCallback(
		async (node: FileNode) => {
			if (!node.isDirectory) return;

			const newExpanded = new Set(expandedPaths);

			if (expandedPaths.has(node.path)) {
				// Collapse
				newExpanded.delete(node.path);
			} else {
				// Expand
				newExpanded.add(node.path);

				// Fetch children if not already loaded and API is available
				if (!node.children && apiUrl) {
					setLoadingPaths((prev) => new Set(prev).add(node.path));

					const children = await fetchDirectory(node.path);

					if (children) {
						// Update the tree with new children
						setFiles((prevFiles) => {
							const updateNode = (nodes: FileNode[]): FileNode[] => {
								return nodes.map((n) => {
									if (n.path === node.path) {
										return { ...n, children };
									}
									if (n.children) {
										return { ...n, children: updateNode(n.children) };
									}
									return n;
								});
							};
							return updateNode(prevFiles);
						});
					}

					setLoadingPaths((prev) => {
						const newSet = new Set(prev);
						newSet.delete(node.path);
						return newSet;
					});
				}
			}

			setExpandedPaths(newExpanded);
		},
		[expandedPaths, apiUrl, fetchDirectory],
	);

	/**
	 * Handle file selection
	 */
	const handleSelect = useCallback(
		(node: FileNode) => {
			if (!node.isDirectory) {
				onFileSelect?.(node);
			}
		},
		[onFileSelect],
	);

	// Loading state
	if (isLoading && files.length === 0) {
		return (
			<div
				className={cn(
					"flex items-center justify-center py-8",
					className,
				)}
			>
				<Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
			</div>
		);
	}

	// Error state
	if (error) {
		return (
			<div
				className={cn(
					"flex flex-col items-center justify-center py-8 px-4 text-center",
					className,
				)}
			>
				<AlertCircle className="h-5 w-5 text-destructive mb-2" />
				<p className="text-xs text-destructive">{error}</p>
				<Button
					variant="outline"
					size="sm"
					className="mt-4"
					onClick={handleRefresh}
				>
					<RefreshCw className="h-4 w-4 mr-2" />
					Retry
				</Button>
			</div>
		);
	}

	// Empty state
	if (files.length === 0) {
		return (
			<div
				className={cn(
					"flex flex-col items-center justify-center py-8 px-4 text-center",
					className,
				)}
			>
				<FolderOpen className="h-6 w-6 text-muted-foreground mb-2" />
				<p className="text-xs text-muted-foreground">No files found</p>
			</div>
		);
	}

	return (
		<div className={cn("flex flex-col h-full", className)}>
			{/* Header */}
			<div className="flex items-center justify-between px-3 py-2 border-b">
				<div className="flex items-center gap-2">
					<Folder className="h-4 w-4 text-muted-foreground" />
					<span className="text-sm font-medium">Files</span>
				</div>
				<Button
					variant="ghost"
					size="icon"
					className="h-6 w-6"
					onClick={handleRefresh}
					disabled={isLoading}
				>
					<RefreshCw
						className={cn("h-4 w-4", isLoading && "animate-spin")}
					/>
				</Button>
			</div>

			{/* File Tree */}
			<ScrollArea className="flex-1">
				<div className="py-2" role="tree">
					{files.map((file) => (
						<FileTreeItem
							key={file.path}
							node={file}
							depth={0}
							expandedPaths={expandedPaths}
							loadingPaths={loadingPaths}
							onToggle={handleToggle}
							onSelect={handleSelect}
						/>
					))}
				</div>
			</ScrollArea>
		</div>
	);
}

export default FileExplorer;
