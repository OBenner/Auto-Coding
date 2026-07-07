/**
 * Kanban pilot on the shared design system (U1).
 *
 * Renders `libs/ui`'s KanbanBoard through the REST AutoCodeClient adapter —
 * the first screen served by the shared UI in the web target. Mounted at
 * /kanban-next alongside the legacy /kanban until the migration completes.
 */

import type { KanbanColumn, UiTask } from "@auto-code/ui";
import {
	AutoCodeClientProvider,
	BoardToolbar,
	KanbanBoard,
	useBoardFilter,
	useTasks,
} from "@auto-code/ui";
import { useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { createRestAutoCodeClient } from "../api/autoCodeClient";
import { apiClient } from "../api/client";

function PilotBoard() {
	const { t } = useTranslation(["tasks"]);
	const navigate = useNavigate();
	const { tasks, loading, error, reload } = useTasks();
	const { query, setQuery, filterId, setFilterId, filtering, visibleTasks } =
		useBoardFilter(tasks);

	const columns = useMemo<KanbanColumn[]>(
		() => [
			{ status: "draft", label: t("tasks:kanbanPilot.columns.draft") },
			{ status: "running", label: t("tasks:kanbanPilot.columns.running") },
			{ status: "review", label: t("tasks:kanbanPilot.columns.review") },
			{ status: "done", label: t("tasks:kanbanPilot.columns.done") },
		],
		[t],
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
				searchLabel={t("tasks:kanbanPilot.toolbar.searchLabel")}
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
				filtersLabel={t("tasks:kanbanPilot.toolbar.filtersLabel")}
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
				viewsLabel={t("tasks:kanbanPilot.toolbar.viewsLabel")}
				activeViewId="board"
			/>
			{/* Always mounted so screen readers announce narrowing (WCAG 4.1.3);
			    <output> carries an implicit status role. */}
			<output
				style={{ display: "block", minHeight: "1.2em", color: "var(--muted)" }}
			>
				{filtering
					? visibleTasks.length === 0
						? t("tasks:kanbanPilot.toolbar.noMatches")
						: t("tasks:kanbanPilot.toolbar.matchCount", {
								count: visibleTasks.length,
							})
					: ""}
			</output>
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
