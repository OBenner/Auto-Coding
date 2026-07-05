/**
 * Task detail on the shared design system (U2).
 *
 * Renders `libs/ui`'s TaskDetail through the REST AutoCodeClient adapter —
 * mounted at /tasks-next/:id, reached from the /kanban-next pilot board.
 * Status labels are injected from i18n; the rest of the screen uses the
 * shared defaults.
 */

import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { AutoCodeClientProvider, TaskDetail, useTask } from "@auto-code/ui";
import type { TaskStatus } from "@auto-code/ui";
import { createRestAutoCodeClient } from "../api/autoCodeClient";
import { apiClient } from "../api/client";

function DetailBody({ id }: Readonly<{ id: string }>) {
	const { t } = useTranslation(["tasks"]);
	const navigate = useNavigate();
	const { task, loading, error, reload } = useTask(id);

	const statusLabels = useMemo<Partial<Record<TaskStatus, string>>>(
		() => ({
			draft: t("tasks:kanbanPilot.columns.draft"),
			running: t("tasks:kanbanPilot.columns.running"),
			review: t("tasks:kanbanPilot.columns.review"),
			done: t("tasks:kanbanPilot.columns.done"),
		}),
		[t],
	);

	return (
		<TaskDetail
			task={task}
			loading={loading}
			error={error}
			onBack={() => navigate("/kanban-next")}
			onRetry={reload}
			statusLabels={statusLabels}
		/>
	);
}

export function TaskDetailNext() {
	const { id } = useParams<{ id: string }>();
	const client = useMemo(() => createRestAutoCodeClient(apiClient), []);

	if (!id) {
		return <Navigate to="/kanban-next" replace />;
	}
	return (
		<AutoCodeClientProvider client={client}>
			<DetailBody id={id} />
		</AutoCodeClientProvider>
	);
}
