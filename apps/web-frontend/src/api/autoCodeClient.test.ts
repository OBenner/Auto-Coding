import { describe, expect, it } from "vitest";
import {
	createRestAutoCodeClient,
	mapStatus,
	mapTaskDetailToUiTaskDetail,
	mapTaskSummaryToUiTask,
	parseProgress,
} from "./autoCodeClient";
import type { TaskDetail, TaskSummary } from "./types";

const summary = (overrides: Partial<TaskSummary> = {}): TaskSummary => ({
	number: "001",
	name: "user-auth",
	folder: "001-user-auth",
	status: "in_progress",
	progress: "2/4",
	has_build: true,
	...overrides,
});

describe("mapStatus", () => {
	it("maps the backend statuses onto the shared closed set", () => {
		expect(mapStatus("complete")).toBe("done");
		expect(mapStatus("in_progress")).toBe("running");
		expect(mapStatus("initialized")).toBe("draft");
		expect(mapStatus("pending")).toBe("draft");
		expect(mapStatus("anything-else")).toBe("draft");
	});

	it("strips the '(has build)' decoration before matching", () => {
		expect(mapStatus("complete (has build)")).toBe("done");
		expect(mapStatus("in_progress (has build)")).toBe("running");
	});

	it("maps the review family onto the review column", () => {
		expect(mapStatus("review")).toBe("review");
		expect(mapStatus("ai_review")).toBe("review");
		expect(mapStatus("human_review (has build)")).toBe("review");
	});
});

describe("parseProgress", () => {
	it("parses done/total into a percentage", () => {
		expect(parseProgress("2/4")).toBe(50);
		expect(parseProgress("3 / 7")).toBe(43);
	});

	it("returns undefined for unknown or degenerate values", () => {
		expect(parseProgress("")).toBeUndefined();
		expect(parseProgress("n/a")).toBeUndefined();
		expect(parseProgress("0/0")).toBeUndefined();
	});
});

describe("mapTaskSummaryToUiTask", () => {
	it("uses the folder as the canonical id and maps fields", () => {
		expect(mapTaskSummaryToUiTask(summary())).toEqual({
			id: "001-user-auth",
			title: "user-auth",
			status: "running",
			progress: 50,
		});
	});
});

describe("createRestAutoCodeClient", () => {
	it("lists tasks through the injected source", async () => {
		const client = createRestAutoCodeClient({
			listTasks: async () => ({
				tasks: [summary(), summary({ folder: "002-x", status: "complete" })],
				total: 2,
			}),
			getTask: async () => detail(),
		});

		const tasks = await client.listTasks();
		expect(tasks.map((task) => task.id)).toEqual(["001-user-auth", "002-x"]);
		expect(tasks[1].status).toBe("done");
	});
});

const detail = (overrides: Partial<TaskDetail> = {}): TaskDetail => ({
	number: "001",
	name: "user-auth",
	folder: "001-user-auth",
	status: "in_progress (has build)",
	progress: {
		completed: 2,
		in_progress: 1,
		pending: 1,
		failed: 1,
		total: 5,
		percentage: 40,
	},
	has_build: true,
	spec_content: "# Spec body",
	...overrides,
});

describe("mapTaskDetailToUiTaskDetail", () => {
	it("maps detail fields incl. breakdown and decorated status", () => {
		expect(mapTaskDetailToUiTaskDetail(detail())).toEqual({
			id: "001-user-auth",
			title: "user-auth",
			status: "running",
			specContent: "# Spec body",
			progressBreakdown: {
				completed: 2,
				inProgress: 1,
				pending: 1,
				failed: 1,
				total: 5,
			},
		});
	});

	it("omits optional fields when absent", () => {
		const ui = mapTaskDetailToUiTaskDetail(
			detail({ spec_content: undefined, progress: undefined as never }),
		);
		expect(ui.specContent).toBeUndefined();
		expect(ui.progressBreakdown).toBeUndefined();
	});
});

describe("createRestAutoCodeClient.getTask", () => {
	it("fetches and maps detail through the injected source", async () => {
		const client = createRestAutoCodeClient({
			listTasks: async () => ({ tasks: [], total: 0 }),
			getTask: async (id) => detail({ folder: id }),
		});
		const ui = await client.getTask?.("002-x");
		expect(ui?.id).toBe("002-x");
		expect(ui?.status).toBe("running");
	});
});

describe("status chips (opt-in)", () => {
	it("renders no chip without the option", () => {
		expect(mapTaskSummaryToUiTask(summary()).statusChip).toBeUndefined();
	});

	it("labels the chip via the callback with the normalized status", () => {
		const ui = mapTaskSummaryToUiTask(summary({ status: "complete (has build)" }), {
			statusChipLabel: (normalized) =>
				normalized === "complete" ? "Complete" : undefined,
		});
		expect(ui.statusChip).toEqual({ label: "Complete", tone: "good" });
	});

	it("falls back to the raw normalized status when unmapped", () => {
		const ui = mapTaskSummaryToUiTask(summary({ status: "initialized" }), {
			statusChipLabel: () => undefined,
		});
		expect(ui.statusChip).toEqual({ label: "initialized", tone: "neutral" });
	});
});

