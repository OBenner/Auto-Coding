import { describe, expect, it } from "vitest";
import {
	createRestAutoCodeClient,
	mapStatus,
	mapTaskSummaryToUiTask,
	parseProgress,
} from "./autoCodeClient";
import type { TaskSummary } from "./types";

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
		});

		const tasks = await client.listTasks();
		expect(tasks.map((task) => task.id)).toEqual(["001-user-auth", "002-x"]);
		expect(tasks[1].status).toBe("done");
	});
});
