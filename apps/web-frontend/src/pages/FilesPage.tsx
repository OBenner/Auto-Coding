/**
 * Files Page - Displays file explorer for browsing project files
 */

import { ArrowLeft } from "lucide-react";
import { useCallback } from "react";
import { FileExplorer, type FileNode } from "../components/FileExplorer";
import { Button } from "../components/ui/button";

interface FilesPageProps {
	onBack?: () => void;
}

export function FilesPage({ onBack }: FilesPageProps) {
	const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

	const handleFileSelect = useCallback((file: FileNode) => {
		// For now, just log the selected file
		// In future, this could open a file viewer or editor
		alert(`Selected file: ${file.name}\nPath: ${file.path}`);
	}, []);

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
				</div>
			</header>

			{/* Main Content */}
			<main className="flex-1 container mx-auto px-4 py-6">
				<div className="bg-card rounded-lg border shadow-sm h-[calc(100vh-180px)]">
					<FileExplorer
						rootPath="/"
						apiUrl={apiUrl}
						onFileSelect={handleFileSelect}
						className="h-full"
					/>
				</div>
			</main>
		</div>
	);
}

export default FilesPage;
