/**
 * IDEPage
 *
 * Full-featured web-based IDE with a resizable 3-panel layout:
 *   - Left panel:  FileExplorer
 *   - Center panel: CodeEditor
 *   - Right panel: Terminal / AgentOutput tabs
 *
 * Panel sizes and the last-opened file/directory are persisted in
 * localStorage so the session is restored on the next visit.
 */

import { Code2, Terminal as TerminalIcon, Bot } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
	Panel,
	Group as PanelGroup,
	Separator as PanelResizeHandle,
	type PanelImperativeHandle as ImperativePanelHandle,
} from "react-resizable-panels";
import { AgentOutput, type LogLine } from "../components/AgentOutput";
import { CodeEditor } from "../components/CodeEditor";
import { FileExplorer, type FileNode } from "../components/FileExplorer";
import TerminalComponent from "../components/Terminal";
import { cn } from "../lib/utils";
import { useSettingsStore } from "../store/settings-store";

// ─── localStorage keys ────────────────────────────────────────────────────────
const LS_LAST_FILE = "ide_last_file";
const LS_LAST_DIR = "ide_last_dir";
const LS_PANEL_SIZES = "ide_panel_sizes";

// ─── Panel size defaults ──────────────────────────────────────────────────────
const DEFAULT_SIZES = {
	explorer: 20,
	editor: 50,
	right: 30,
};

type RightTab = "terminal" | "agent";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function loadPanelSizes(): typeof DEFAULT_SIZES {
	try {
		const raw = localStorage.getItem(LS_PANEL_SIZES);
		if (raw) {
			const parsed = JSON.parse(raw) as typeof DEFAULT_SIZES;
			// Basic sanity check
			if (
				typeof parsed.explorer === "number" &&
				typeof parsed.editor === "number" &&
				typeof parsed.right === "number"
			) {
				return parsed;
			}
		}
	} catch {
		// Ignore parse errors
	}
	return { ...DEFAULT_SIZES };
}

function savePanelSizes(sizes: typeof DEFAULT_SIZES): void {
	try {
		localStorage.setItem(LS_PANEL_SIZES, JSON.stringify(sizes));
	} catch {
		// Ignore storage errors
	}
}

function loadLastSession(): { filePath: string | null; rootDir: string | null } {
	try {
		return {
			filePath: localStorage.getItem(LS_LAST_FILE),
			rootDir: localStorage.getItem(LS_LAST_DIR),
		};
	} catch {
		return { filePath: null, rootDir: null };
	}
}

function saveLastSession(filePath: string | null, rootDir: string | null): void {
	try {
		if (filePath) {
			localStorage.setItem(LS_LAST_FILE, filePath);
		} else {
			localStorage.removeItem(LS_LAST_FILE);
		}
		if (rootDir) {
			localStorage.setItem(LS_LAST_DIR, rootDir);
		} else {
			localStorage.removeItem(LS_LAST_DIR);
		}
	} catch {
		// Ignore storage errors
	}
}

// ─── Component ────────────────────────────────────────────────────────────────

export function IDEPage() {
	const { settings } = useSettingsStore();
	const apiUrl = settings.apiUrl;

	// Restore last session from localStorage
	const [session] = useState(() => loadLastSession());
	const initialSizes = loadPanelSizes();

	// State
	const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);
	const [fileContent, setFileContent] = useState<string>("");
	const [rootDir, setRootDir] = useState<string | null>(session.rootDir);
	const [activeRightTab, setActiveRightTab] = useState<RightTab>("terminal");
	const [agentLogs] = useState<LogLine[]>([]);
	const [terminalSessionId] = useState(() => `ide-terminal-${Date.now()}`);
	const [isFetchingFile, setIsFetchingFile] = useState(false);
	const [fetchError, setFetchError] = useState<string | null>(null);

	// Track current panel sizes for persistence
	const currentSizesRef = useRef<typeof DEFAULT_SIZES>({ ...initialSizes });
	const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	// ImperativePanelHandles (for potential future collapse controls)
	const explorerPanelRef = useRef<ImperativePanelHandle>(null);

	// Restore last opened file on mount
	useEffect(() => {
		if (session.filePath && !selectedFile) {
			const fakeFn: FileNode = {
				path: session.filePath,
				name: session.filePath.split("/").pop() ?? session.filePath,
				isDirectory: false,
			};
			setSelectedFile(fakeFn);
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	// Fetch file content when selectedFile changes
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
				const data = await res.json() as { content: string };
				return data.content;
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

	// Persist last opened file/dir
	useEffect(() => {
		saveLastSession(selectedFile?.path ?? null, rootDir);
	}, [selectedFile, rootDir]);

	// Handle file selection from explorer
	const handleFileSelect = useCallback((file: FileNode) => {
		if (!file.isDirectory) {
			setSelectedFile(file);
		} else {
			// Track current root directory when user navigates
			setRootDir(file.path);
		}
	}, []);

	// Handle file save
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

	// Debounced panel-size persistence
	const handlePanelResize = useCallback(
		(panel: keyof typeof DEFAULT_SIZES, size: number) => {
			currentSizesRef.current[panel] = size;

			if (saveTimerRef.current) {
				clearTimeout(saveTimerRef.current);
			}
			saveTimerRef.current = setTimeout(() => {
				savePanelSizes({ ...currentSizesRef.current });
			}, 500);
		},
		[],
	);

	// ── Render ──────────────────────────────────────────────────────────────────
	return (
		<div className="h-screen w-full flex flex-col bg-background overflow-hidden">
			{/* IDE header bar */}
			<div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-card shrink-0">
				<Code2 className="h-5 w-5 text-primary" />
				<span className="font-semibold text-sm">IDE</span>
				{selectedFile && (
					<>
						<span className="text-muted-foreground text-sm">/</span>
						<span className="text-sm font-mono text-foreground truncate max-w-xs">
							{selectedFile.name}
						</span>
					</>
				)}
			</div>

			{/* Resizable 3-panel body */}
			<PanelGroup
				orientation="horizontal"
				className="flex-1 overflow-hidden"
			>
				{/* ── Panel 1: File Explorer ──────────────────────────────────── */}
				<Panel
					panelRef={explorerPanelRef}
					defaultSize={initialSizes.explorer}
					minSize={10}
					maxSize={40}
					onResize={(size) => handlePanelResize("explorer", size)}
					className="flex flex-col overflow-hidden"
				>
					<div className="text-xs font-semibold uppercase tracking-wider px-3 py-2 text-muted-foreground border-b border-border shrink-0">
						Explorer
					</div>
					<div className="flex-1 overflow-hidden">
						<FileExplorer
							rootPath={rootDir ?? undefined}
							onFileSelect={handleFileSelect}
							apiUrl={apiUrl}
							className="h-full"
						/>
					</div>
				</Panel>

				<PanelResizeHandle className="w-1 bg-border hover:bg-primary/40 transition-colors cursor-col-resize" />

				{/* ── Panel 2: Code Editor ─────────────────────────────────────── */}
				<Panel
					defaultSize={initialSizes.editor}
					minSize={20}
					onResize={(size) => handlePanelResize("editor", size)}
					className="flex flex-col overflow-hidden"
				>
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
							<p className="text-sm">Select a file from the explorer to start editing</p>
						</div>
					)}
				</Panel>

				<PanelResizeHandle className="w-1 bg-border hover:bg-primary/40 transition-colors cursor-col-resize" />

				{/* ── Panel 3: Terminal / Agent Output ─────────────────────────── */}
				<Panel
					defaultSize={initialSizes.right}
					minSize={15}
					onResize={(size) => handlePanelResize("right", size)}
					className="flex flex-col overflow-hidden"
				>
					{/* Tab bar */}
					<div className="flex items-center border-b border-border shrink-0">
						<button
							type="button"
							onClick={() => setActiveRightTab("terminal")}
							className={cn(
								"flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors",
								activeRightTab === "terminal"
									? "text-foreground border-b-2 border-primary"
									: "text-muted-foreground hover:text-foreground",
							)}
						>
							<TerminalIcon className="h-3.5 w-3.5" />
							Terminal
						</button>
						<button
							type="button"
							onClick={() => setActiveRightTab("agent")}
							className={cn(
								"flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors",
								activeRightTab === "agent"
									? "text-foreground border-b-2 border-primary"
									: "text-muted-foreground hover:text-foreground",
							)}
						>
							<Bot className="h-3.5 w-3.5" />
							Agent Output
						</button>
					</div>

					{/* Tab content */}
					<div className="flex-1 overflow-hidden">
						{activeRightTab === "terminal" ? (
							<TerminalComponent
								id={terminalSessionId}
								sessionId={terminalSessionId}
								cwd={rootDir ?? undefined}
								isActive
								title="Terminal"
							/>
						) : (
							<AgentOutput
								id="ide-agent-output"
								logs={agentLogs}
								isActive
								title="Agent Output"
							/>
						)}
					</div>
				</Panel>
			</PanelGroup>
		</div>
	);
}

export default IDEPage;
