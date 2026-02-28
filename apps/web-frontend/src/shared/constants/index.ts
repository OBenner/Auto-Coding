/**
 * Shared constants for web frontend
 * Adapted from Electron frontend constants
 */

// ============================================
// Task Status (Kanban columns)
// ============================================

export const TASK_STATUS_COLUMNS = [
	"backlog",
	"queue",
	"in_progress",
	"ai_review",
	"human_review",
	"done",
] as const;

export type TaskStatus =
	| (typeof TASK_STATUS_COLUMNS)[number]
	| "pr_created"
	| "error";

export const TASK_STATUS_LABELS: Record<string, string> = {
	backlog: "Backlog",
	queue: "Queue",
	in_progress: "In Progress",
	ai_review: "AI Review",
	human_review: "Human Review",
	done: "Done",
	pr_created: "PR Created",
	error: "Error",
};

// ============================================
// Execution Phases
// ============================================

export const EXECUTION_PHASE_LABELS: Record<string, string> = {
	idle: "Idle",
	planning: "Planning",
	coding: "Coding",
	qa_review: "AI Review",
	qa_fixing: "Fixing Issues",
	complete: "Complete",
	failed: "Failed",
};

export const EXECUTION_PHASE_BADGE_COLORS: Record<string, string> = {
	idle: "bg-muted/50 text-muted-foreground border-muted",
	planning: "bg-amber-500/10 text-amber-500 border-amber-500/30",
	coding: "bg-info/10 text-info border-info/30",
	qa_review: "bg-purple-500/10 text-purple-400 border-purple-500/30",
	qa_fixing: "bg-warning/10 text-warning border-warning/30",
	complete: "bg-success/10 text-success border-success/30",
	failed: "bg-destructive/10 text-destructive border-destructive/30",
};

// ============================================
// Task Categories
// ============================================

export type TaskCategory =
	| "feature"
	| "bug_fix"
	| "refactoring"
	| "documentation"
	| "security"
	| "performance"
	| "ui_ux"
	| "infrastructure"
	| "testing";

export const TASK_CATEGORY_LABELS: Record<TaskCategory, string> = {
	feature: "Feature",
	bug_fix: "Bug Fix",
	refactoring: "Refactoring",
	documentation: "Docs",
	security: "Security",
	performance: "Performance",
	ui_ux: "UI/UX",
	infrastructure: "Infrastructure",
	testing: "Testing",
};

export const TASK_CATEGORY_COLORS: Record<TaskCategory, string> = {
	feature: "bg-primary/10 text-primary border-primary/30",
	bug_fix: "bg-destructive/10 text-destructive border-destructive/30",
	refactoring: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
	documentation: "bg-amber-500/10 text-amber-500 border-amber-500/30",
	security: "bg-red-500/10 text-red-400 border-red-500/30",
	performance: "bg-purple-500/10 text-purple-400 border-purple-500/30",
	ui_ux: "bg-info/10 text-info border-info/30",
	infrastructure: "bg-slate-500/10 text-slate-400 border-slate-500/30",
	testing: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
};

// ============================================
// Task Complexity
// ============================================

export const TASK_COMPLEXITY_LABELS: Record<string, string> = {
	trivial: "Trivial",
	small: "Small",
	medium: "Medium",
	large: "Large",
	complex: "Complex",
};

export const TASK_COMPLEXITY_COLORS: Record<string, string> = {
	trivial: "bg-success/10 text-success",
	small: "bg-info/10 text-info",
	medium: "bg-warning/10 text-warning",
	large: "bg-orange-500/10 text-orange-400",
	complex: "bg-destructive/10 text-destructive",
};

// ============================================
// Task Impact
// ============================================

export const TASK_IMPACT_LABELS: Record<string, string> = {
	low: "Low Impact",
	medium: "Medium Impact",
	high: "High Impact",
	critical: "Critical Impact",
};

export const TASK_IMPACT_COLORS: Record<string, string> = {
	low: "bg-muted text-muted-foreground",
	medium: "bg-info/10 text-info",
	high: "bg-warning/10 text-warning",
	critical: "bg-destructive/10 text-destructive",
};

// ============================================
// Task Priority
// ============================================

export const TASK_PRIORITY_LABELS: Record<string, string> = {
	low: "Low",
	medium: "Medium",
	high: "High",
	urgent: "Urgent",
};

export const TASK_PRIORITY_COLORS: Record<string, string> = {
	low: "bg-muted text-muted-foreground",
	medium: "bg-info/10 text-info",
	high: "bg-warning/10 text-warning",
	urgent: "bg-destructive/10 text-destructive",
};

// ============================================
// JSON Error Markers
// ============================================

export const JSON_ERROR_PREFIX = "__JSON_ERROR__:";
export const JSON_ERROR_TITLE_SUFFIX = "__JSON_ERROR_SUFFIX__";
