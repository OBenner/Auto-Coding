/**
 * Kanban pilot on the shared design system (U1).
 *
 * Renders `libs/ui`'s KanbanBoard through the REST AutoCodeClient adapter —
 * the first screen served by the shared UI in the web target. Mounted at
 * /kanban-next alongside the legacy /kanban until the migration completes.
 */

import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
	AutoCodeClientProvider,
	BoardToolbar,
	KanbanBoard,
	filterUiTasks,
	useTasks,
} from "@auto-code/ui";
import type { KanbanColumn, TaskStatus, UiTask } from "@auto-code/ui";
import { createRestAutoCodeClient } from "../api/autoCodeClient";
import { apiClient } from "../api/client";

// Status behind each toolbar filter chip; "all" clears the narrowing.
const FILTER_STATUS: Record<string, TaskStatus | undefined> = {
	all: undefined,
	running: "running",
	review: "review",
};

function PilotBoard() {
	const { t } = useTranslation(["tasks"]);
	const navigate = useNavigate();
	const { tasks, loading, error, reload } = useTasks();
	const [query, setQuery] = useState("");
	const [filterId, setFilterId] = useState("all");

	const columns = useMemo<KanbanColumn[]>(
		() => [
			{ status: "draft", label: t("tasks:kanbanPilot.columns.draft") },
			{ status: "running", label: t("tasks:kanbanPilot.columns.running") },
			{ status: "review", label: t("tasks:kanbanPilot.columns.review") },
			{ status: "done", label: t("tasks:kanbanPilot.columns.done") },
		],
		[t],
	);

	const visibleTasks = useMemo(
		() => filterUiTasks(tasks, { query, status: FILTER_STATUS[filterId] }),
		[tasks, query, filterId],
	);

	const handleSelect = (task: UiTask) => {
		navigate(`/tasks-next/${task.id}`);
	};

	return (
		<div style={{ padding: "1rem", height: "100%", overflow: "auto" }}>
			<h1>{t("tasks:kanbanPilot.title")}</h1>
			<BoardToolbar
				searchValue={query}
				searchPlaceholder={t("tasks:kanbanPilot.toolbar.searchPlaceholder")}
				onSearchChange={setQuery}
				filters={[
					{ id: "all", label: t("tasks:kanbanPilot.toolbar.filters.all") },
					{
						id: "running",
						label: t("tasks:kanbanPilot.toolbar.filters.running"),
					},
					{
						id: "review",
						label: t("tasks:kanbanPilot.toolbar.filters.review"),
					},
				]}
				activeFilterId={filterId}
				onSelectFilter={setFilterId}
				views={[
					{ id: "board", label: t("tasks:kanbanPilot.toolbar.views.board") },
					{
						id: "table",
						label: t("tasks:kanbanPilot.toolbar.views.table"),
						disabled: true,
					},
					{
						id: "timeline",
						label: t("tasks:kanbanPilot.toolbar.views.timeline"),
						disabled: true,
					},
				]}
				activeViewId="board"
			/>
			{loading && <p>{t("tasks:kanbanPilot.loading")}</p>}
			{error && (
				<p role="alert">
					{t("tasks:kanbanPilot.error")}{" "}
					<button type="button" onClick={reload}>
						{t("tasks:kanbanPilot.retry")}
					</button>
				</p>
			)}
			{!loading && !error && (
				<KanbanBoard
					tasks={visibleTasks}
					columns={columns}
					onSelectTask={handleSelect}
				/>
			)}
		</div>
	);
}

/** Normalized backend statuses that get a localized chip label. */
type ChippedStatus = "complete" | "in_progress" | "pending" | "initialized";

const CHIP_LABEL_KEYS: Record<ChippedStatus, string> = {
	complete: "tasks:status.complete",
	in_progress: "tasks:status.in_progress",
	pending: "tasks:status.pending",
	initialized: "tasks:status.initialized",
};

export function KanbanPilot() {
	const { t } = useTranslation(["tasks"]);
	// Keep the client identity stable across locale switches (useTasks
	// refetches whenever the injected client changes): read translations
	// through a ref, as in the Electron pilot. Chip labels are baked in at
	// map time either way, so they pick up a new locale on the next fetch.
	const tRef = useRef(t);
	tRef.current = t;
	const client = useMemo(
		() =>
			createRestAutoCodeClient(apiClient, {
				statusChipLabel: (normalized) =>
					Object.hasOwn(CHIP_LABEL_KEYS, normalized)
						? tRef.current(CHIP_LABEL_KEYS[normalized as ChippedStatus])
						: undefined,
			}),
		[],
	);
	return (
		<AutoCodeClientProvider client={client}>
			<PilotBoard />
		</AutoCodeClientProvider>
	);
}
