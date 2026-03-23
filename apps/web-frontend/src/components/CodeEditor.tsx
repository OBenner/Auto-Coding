/**
 * CodeEditor Component (Web Version with Monaco Editor)
 * Full-featured code editor with language detection, Ctrl+S save, and unsaved indicator.
 * Uses @monaco-editor/react for Monaco integration.
 */

import Editor, { type Monaco, type OnMount } from "@monaco-editor/react";
import { AlertCircle, Circle, Loader2, Save } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";

export interface CodeEditorProps {
	/** File path being edited */
	filePath?: string;
	/** Initial file content */
	content?: string;
	/** Language override (auto-detected from filePath if not provided) */
	language?: string;
	/** Whether editor is read-only */
	readOnly?: boolean;
	/** Callback when content is saved (Ctrl+S or save button) */
	onSave?: (content: string, filePath?: string) => void | Promise<void>;
	/** Callback when content changes */
	onChange?: (content: string) => void;
	/** Custom class name */
	className?: string;
	/** Whether this editor pane is currently active */
	isActive?: boolean;
}

/**
 * Map file extensions to Monaco language identifiers
 */
function detectLanguage(filePath?: string): string {
	if (!filePath) return "plaintext";

	const ext = filePath.split(".").pop()?.toLowerCase();

	switch (ext) {
		case "ts":
			return "typescript";
		case "tsx":
			return "typescript";
		case "js":
			return "javascript";
		case "jsx":
			return "javascript";
		case "py":
			return "python";
		case "rb":
			return "ruby";
		case "go":
			return "go";
		case "rs":
			return "rust";
		case "java":
			return "java";
		case "c":
		case "h":
			return "c";
		case "cpp":
		case "cc":
		case "cxx":
		case "hpp":
			return "cpp";
		case "cs":
			return "csharp";
		case "php":
			return "php";
		case "swift":
			return "swift";
		case "kt":
		case "kts":
			return "kotlin";
		case "json":
			return "json";
		case "yaml":
		case "yml":
			return "yaml";
		case "toml":
			return "ini";
		case "md":
		case "mdx":
			return "markdown";
		case "html":
		case "htm":
			return "html";
		case "css":
			return "css";
		case "scss":
		case "sass":
			return "scss";
		case "less":
			return "less";
		case "xml":
			return "xml";
		case "sh":
		case "bash":
		case "zsh":
			return "shell";
		case "sql":
			return "sql";
		case "dockerfile":
			return "dockerfile";
		case "graphql":
		case "gql":
			return "graphql";
		default:
			// Check for extensionless files by filename
			const filename = filePath.split("/").pop()?.split("\\").pop()?.toLowerCase();
			if (filename === "dockerfile") return "dockerfile";
			if (filename === "makefile") return "makefile";
			return "plaintext";
	}
}

/**
 * Get a human-readable label for the language
 */
function getLanguageLabel(language: string): string {
	const labels: Record<string, string> = {
		typescript: "TypeScript",
		javascript: "JavaScript",
		python: "Python",
		ruby: "Ruby",
		go: "Go",
		rust: "Rust",
		java: "Java",
		c: "C",
		cpp: "C++",
		csharp: "C#",
		php: "PHP",
		swift: "Swift",
		kotlin: "Kotlin",
		json: "JSON",
		yaml: "YAML",
		ini: "TOML/INI",
		markdown: "Markdown",
		html: "HTML",
		css: "CSS",
		scss: "SCSS",
		less: "LESS",
		xml: "XML",
		shell: "Shell",
		sql: "SQL",
		dockerfile: "Dockerfile",
		graphql: "GraphQL",
		plaintext: "Plain Text",
	};
	return labels[language] ?? language;
}

/**
 * CodeEditor component using Monaco Editor
 * Supports language detection, Ctrl+S save, and unsaved changes indicator
 */
export function CodeEditor({
	filePath,
	content = "",
	language,
	readOnly = false,
	onSave,
	onChange,
	className,
	isActive = false,
}: CodeEditorProps) {
	const [currentContent, setCurrentContent] = useState<string>(content);
	const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
	const [isSaving, setIsSaving] = useState(false);
	const [saveError, setSaveError] = useState<string | null>(null);
	const editorRef = useRef<Parameters<OnMount>[0] | null>(null);
	const monacoRef = useRef<Monaco | null>(null);

	const detectedLanguage = language ?? detectLanguage(filePath);

	// Sync content prop changes (e.g. new file loaded)
	useEffect(() => {
		setCurrentContent(content);
		setHasUnsavedChanges(false);
		setSaveError(null);
	}, [content, filePath]);

	/**
	 * Handle save action – called by Ctrl+S or save button
	 */
	const handleSave = useCallback(async () => {
		if (!onSave || isSaving) return;
		setIsSaving(true);
		setSaveError(null);
		try {
			await onSave(currentContent, filePath);
			setHasUnsavedChanges(false);
		} catch (err) {
			const message = err instanceof Error ? err.message : "Save failed";
			setSaveError(message);
		} finally {
			setIsSaving(false);
		}
	}, [onSave, isSaving, currentContent, filePath]);

	/**
	 * Register Ctrl+S keybinding once the editor mounts
	 */
	const handleEditorMount: OnMount = useCallback(
		(editor, monaco) => {
			editorRef.current = editor;
			monacoRef.current = monaco;

			// Ctrl+S / Cmd+S → save
			editor.addCommand(
				monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
				() => {
					handleSave();
				},
			);
		},
		[handleSave],
	);

	/**
	 * Track content changes and propagate to parent
	 */
	const handleChange = useCallback(
		(value: string | undefined) => {
			const newContent = value ?? "";
			setCurrentContent(newContent);
			setHasUnsavedChanges(newContent !== content);
			onChange?.(newContent);
		},
		[content, onChange],
	);

	const fileName = filePath
		? filePath.split("/").pop()?.split("\\").pop() ?? filePath
		: "Untitled";

	return (
		<div
			className={cn(
				"flex flex-col h-full bg-background border rounded-md overflow-hidden",
				isActive && "ring-2 ring-primary ring-offset-1",
				className,
			)}
		>
			{/* Editor toolbar */}
			<div className="flex items-center justify-between px-3 py-1.5 border-b bg-muted/30 shrink-0">
				<div className="flex items-center gap-2 min-w-0">
					{/* Unsaved indicator dot */}
					{hasUnsavedChanges && (
						<Circle
							className="h-2 w-2 fill-current text-orange-400 shrink-0"
							aria-label="Unsaved changes"
						/>
					)}
					{/* File name */}
					<span
						className={cn(
							"text-sm font-medium truncate",
							hasUnsavedChanges ? "text-orange-400" : "text-foreground",
						)}
						title={filePath}
					>
						{fileName}
					</span>
					{/* Language badge */}
					<span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded shrink-0">
						{getLanguageLabel(detectedLanguage)}
					</span>
					{/* Read-only badge */}
					{readOnly && (
						<span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded shrink-0">
							Read-only
						</span>
					)}
				</div>

				<div className="flex items-center gap-2 shrink-0">
					{/* Save error */}
					{saveError && (
						<span
							className="flex items-center gap-1 text-xs text-destructive"
							title={saveError}
						>
							<AlertCircle className="h-3 w-3" />
							Save failed
						</span>
					)}

					{/* Save button */}
					{!readOnly && onSave && (
						<Button
							variant="ghost"
							size="sm"
							className="h-6 px-2 text-xs"
							onClick={handleSave}
							disabled={isSaving || !hasUnsavedChanges}
							title="Save (Ctrl+S)"
						>
							{isSaving ? (
								<Loader2 className="h-3 w-3 animate-spin" />
							) : (
								<Save className="h-3 w-3" />
							)}
							<span className="ml-1">Save</span>
						</Button>
					)}
				</div>
			</div>

			{/* Monaco Editor */}
			<div className="flex-1 overflow-hidden">
				<Editor
					height="100%"
					language={detectedLanguage}
					value={currentContent}
					theme="vs-dark"
					options={{
						readOnly,
						fontSize: 14,
						fontFamily: 'Menlo, Monaco, "Courier New", monospace',
						minimap: { enabled: true },
						scrollBeyondLastLine: false,
						wordWrap: "off",
						lineNumbers: "on",
						renderLineHighlight: "line",
						tabSize: 2,
						insertSpaces: true,
						automaticLayout: true,
						bracketPairColorization: { enabled: true },
						formatOnPaste: false,
						formatOnType: false,
						suggestOnTriggerCharacters: true,
						quickSuggestions: {
							other: true,
							comments: false,
							strings: false,
						},
						padding: { top: 8, bottom: 8 },
					}}
					onMount={handleEditorMount}
					onChange={handleChange}
					loading={
						<div className="flex items-center justify-center h-full">
							<Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
						</div>
					}
				/>
			</div>
		</div>
	);
}

export default CodeEditor;
