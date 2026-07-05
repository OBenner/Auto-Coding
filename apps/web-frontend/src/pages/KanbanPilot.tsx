/**
 * Kanban pilot on the shared design system (U1).
 *
 * Renders `libs/ui`'s KanbanBoard through the REST AutoCodeClient adapter —
 * the first screen served by the shared UI in the web target. Mounted at
 * /kanban-next alongside the legacy /kanban until the migration completes.
 */

import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
	AutoCodeClientProvider,
	KanbanBoard,
	useTasks,
} from "@auto-code/ui";
import type { KanbanColumn, UiTask } from "@auto-code/ui";
import { createRestAutoCodeClient } from "../api/autoCodeClient";
import { apiClient } from "../api/client";

function PilotBoard() {
	const { t } = useTranslation(["tasks"]);
	const navigate = useNavigate();
	const { tasks, loading, error, reload } = useTasks();

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
					tasks={tasks}
					columns={columns}
					onSelectTask={handleSelect}
				/>
			)}
		</div>
	);
}

export function KanbanPilot() {
	const client = useMemo(() => createRestAutoCodeClient(apiClient), []);
	return (
		<AutoCodeClientProvider client={client}>
			<PilotBoard />
		</AutoCodeClientProvider>
	);
}
