/**
 * Files Page - Displays file explorer for browsing project files
 * Integrates CodeEditor for viewing/editing selected files.
 */

import { ArrowLeft, Code2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { CodeEditor } from "../components/CodeEditor";
import { FileExplorer, type FileNode } from "../components/FileExplorer";
import { Button } from "../components/ui/button";

interface FilesPageProps {
	onBack?: () => void;
}

export function FilesPage({ onBack }: FilesPageProps) {
	const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

	const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);
	const [fileContent, setFileContent] = useState<string>("");
	const [isFetchingFile, setIsFetchingFile] = useState(false);
	const [fetchError, setFetchError] = useState<string | null>(null);

	// Fetch file content whenever the selected file changes
	useEffect(() => {
		if (!selectedFile || selectedFile.isDirectory) {
			setFileContent("");
			setFetchError(null);
			return;
		}

		let cancelled = false;
		setIsFetchingFile(true);
		setFetchError(null);

		const token = (() => {
			try {
				return localStorage.getItem("auth_token") ?? "";
			} catch {
				return "";
			}
		})();

		fetch(`${apiUrl}/api/files/content?path=${encodeURIComponent(selectedFile.path)}`, {
			headers: token ? { Authorization: `Bearer ${token}` } : {},
		})
			.then(async (res) => {
				if (!res.ok) {
					throw new Error(`Failed to load file: ${res.statusText}`);
				}
				return res.text();
			})
			.then((text) => {
				if (!cancelled) {
					setFileContent(text);
				}
			})
			.catch((err: unknown) => {
				if (!cancelled) {
					setFetchError(err instanceof Error ? err.message : "Failed to load file");
					setFileContent("");
				}
			})
			.finally(() => {
				if (!cancelled) {
					setIsFetchingFile(false);
				}
			});

		return () => {
			cancelled = true;
		};
	}, [selectedFile, apiUrl]);

	const handleFileSelect = useCallback((file: FileNode) => {
		if (!file.isDirectory) {
			setSelectedFile(file);
		}
	}, []);

	const handleSave = useCallback(
		async (content: string, filePath?: string) => {
			const path = filePath ?? selectedFile?.path;
			if (!path) return;

			const token = (() => {
				try {
					return localStorage.getItem("auth_token") ?? "";
				} catch {
					return "";
				}
			})();

			await fetch(`${apiUrl}/api/files/content`, {
				method: "PUT",
				headers: {
					"Content-Type": "application/json",
					...(token ? { Authorization: `Bearer ${token}` } : {}),
				},
				body: JSON.stringify({ path, content }),
			});
		},
		[selectedFile, apiUrl],
	);

	const handleBack = useCallback(() => {
		if (onBack) {
			onBack();
		} else {
			window.location.href = "/";
		}
	}, [onBack]);

	return (
		<div className="min-h-screen bg-background flex flex-col">
			{/* Header */}
			<header className="border-b bg-card">
				<div className="container mx-auto px-4 py-4 flex items-center gap-4">
					<Button
						variant="ghost"
						size="icon"
						onClick={handleBack}
						className="h-8 w-8"
					>
						<ArrowLeft className="h-4 w-4" />
					</Button>
					<div>
						<h1 className="text-xl font-semibold">File Explorer</h1>
						<p className="text-sm text-muted-foreground">
							Browse and explore project files
						</p>
					</div>
					{selectedFile && (
						<span className="ml-2 text-sm font-mono text-muted-foreground truncate max-w-xs">
							{selectedFile.path}
						</span>
					)}
				</div>
			</header>

			{/* Main Content */}
			<main className="flex-1 container mx-auto px-4 py-6">
				<div className="flex gap-4 h-[calc(100vh-180px)]">
					{/* File explorer panel */}
					<div className="w-64 shrink-0 bg-card rounded-lg border shadow-sm overflow-hidden">
						<FileExplorer
							rootPath="/"
							apiUrl={apiUrl}
							onFileSelect={handleFileSelect}
							className="h-full"
						/>
					</div>

					{/* Editor panel */}
					<div className="flex-1 bg-card rounded-lg border shadow-sm overflow-hidden">
						{fetchError ? (
							<div className="flex items-center justify-center h-full text-destructive text-sm p-4">
								{fetchError}
							</div>
						) : isFetchingFile ? (
							<div className="flex items-center justify-center h-full text-muted-foreground text-sm">
								Loading…
							</div>
						) : selectedFile ? (
							<CodeEditor
								filePath={selectedFile.path}
								content={fileContent}
								onSave={handleSave}
								isActive
								className="h-full"
							/>
						) : (
							<div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
								<Code2 className="h-12 w-12 opacity-20" />
								<p className="text-sm">Select a file from the explorer to view or edit it</p>
							</div>
						)}
					</div>
				</div>
			</main>
		</div>
	);
}

export default FilesPage;
