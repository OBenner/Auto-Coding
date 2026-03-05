/**
 * Timeline layout utility functions
 *
 * Calculates positions, dimensions, and paths for timeline visualization.
 * Handles phase swim lanes, subtask blocks, and dependency connectors.
 */

import type {
  TimelinePhase,
  TimelineSubtask,
  PhaseLayout,
  SubtaskLayout,
  TimelineViewState,
  TimelineConfig,
  TimelineDependency,
} from '../types';

/**
 * Generate phase ID from phase number
 * @param phaseNumber Phase number
 * @returns Phase ID string
 */
export function getPhaseId(phaseNumber: number): string {
  return `phase-${phaseNumber}`;
}

/**
 * Calculate phase layout for a swim lane
 * @param phaseIndex Index of the phase (0-based)
 * @param config Timeline configuration
 * @param zoom Current zoom level
 * @returns Phase layout with position and dimensions
 */
export function calculatePhaseLayout(
  phaseIndex: number,
  config: TimelineConfig,
  zoom: number
): PhaseLayout {
  const { phaseHeight, subtaskHeight, subtaskSpacing } = config;

  // Calculate Y position with zoom applied
  const y = phaseIndex * (phaseHeight * zoom);

  // Calculate height with subtask vertical padding
  const verticalPadding = 20;
  const height = (subtaskHeight + verticalPadding * 2) * zoom;

  // Width will be determined by content (subtasks)
  const width = 0;
  const totalWidth = 0;

  return {
    y,
    height,
    width,
    totalWidth,
  };
}

/**
 * Calculate subtask layout within a phase
 * @param subtaskIndex Index of the subtask within its phase (0-based)
 * @param phaseLayout Layout of the parent phase
 * @param config Timeline configuration
 * @param zoom Current zoom level
 * @returns Subtask layout with position and dimensions
 */
export function calculateSubtaskLayout(
  subtaskIndex: number,
  phaseLayout: PhaseLayout,
  config: TimelineConfig,
  zoom: number
): SubtaskLayout {
  const { minSubtaskWidth, subtaskHeight, subtaskSpacing } = config;

  // Calculate X position (horizontal layout)
  const x = subtaskIndex * ((minSubtaskWidth + subtaskSpacing) * zoom);

  // Calculate Y position (centered vertically in phase)
  const verticalPadding = 20 * zoom;
  const y = verticalPadding;

  // Calculate dimensions with zoom
  const width = minSubtaskWidth * zoom;
  const height = subtaskHeight * zoom;

  // Set z-index (subtasks render above phase background)
  const zIndex = 10;

  return {
    x,
    y,
    width,
    height,
    zIndex,
  };
}

/**
 * Calculate layouts for all phases in timeline
 * @param phases Timeline phases
 * @param viewState Current view state (zoom level)
 * @param config Timeline configuration
 * @returns Map of phase ID to calculated layout
 */
export function calculateAllPhaseLayouts(
  phases: TimelinePhase[],
  viewState: TimelineViewState,
  config: TimelineConfig
): Map<string, PhaseLayout> {
  const layouts = new Map<string, PhaseLayout>();

  phases.forEach((phase, index) => {
    const layout = calculatePhaseLayout(index, config, viewState.zoom);
    const phaseId = getPhaseId(phase.phase);
    layouts.set(phaseId, layout);
  });

  return layouts;
}

/**
 * Calculate layouts for all subtasks in timeline
 * @param subtasks Timeline subtasks grouped by phase
 * @param phaseLayouts Map of phase ID to phase layout
 * @param viewState Current view state (zoom level)
 * @param config Timeline configuration
 * @returns Map of subtask ID to calculated layout
 */
export function calculateAllSubtaskLayouts(
  subtasksByPhase: Map<string, TimelineSubtask[]>,
  phaseLayouts: Map<string, PhaseLayout>,
  viewState: TimelineViewState,
  config: TimelineConfig
): Map<string, SubtaskLayout> {
  const layouts = new Map<string, SubtaskLayout>();

  subtasksByPhase.forEach((subtasks, phaseId) => {
    const phaseLayout = phaseLayouts.get(phaseId);
    if (!phaseLayout) return;

    subtasks.forEach((subtask, index) => {
      const layout = calculateSubtaskLayout(index, phaseLayout, config, viewState.zoom);
      layouts.set(subtask.id, layout);
    });
  });

  return layouts;
}

/**
 * Calculate total timeline width based on all subtasks
 * @param subtasks All timeline subtasks
 * @param config Timeline configuration
 * @param zoom Current zoom level
 * @returns Total width in pixels
 */
export function calculateTimelineWidth(
  subtasks: TimelineSubtask[],
  config: TimelineConfig,
  zoom: number
): number {
  if (subtasks.length === 0) return 0;

  const { minSubtaskWidth, subtaskSpacing } = config;
  const maxSubtasksPerPhase = Math.max(
    ...Array.from(
      new Set(subtasks.map((st) => st.phaseId))
    ).map((phaseId) =>
      subtasks.filter((st) => st.phaseId === phaseId).length
    )
  );

  return (
    maxSubtasksPerPhase * ((minSubtaskWidth + subtaskSpacing) * zoom) +
    subtaskSpacing * zoom
  );
}

/**
 * Calculate total timeline height based on phases
 * @param phaseCount Number of phases
 * @param config Timeline configuration
 * @param zoom Current zoom level
 * @returns Total height in pixels
 */
export function calculateTimelineHeight(
  phaseCount: number,
  config: TimelineConfig,
  zoom: number
): number {
  const { phaseHeight } = config;
  return phaseCount * (phaseHeight * zoom);
}

/**
 * Clamp zoom level to min/max bounds
 * @param zoom Desired zoom level
 * @param config Timeline configuration
 * @returns Clamped zoom level
 */
export function clampZoom(zoom: number, config: TimelineConfig): number {
  return Math.max(config.minZoom, Math.min(config.maxZoom, zoom));
}

/**
 * Calculate zoom level centered on a point
 * @param currentZoom Current zoom level
 * @param delta Zoom delta (positive = zoom in, negative = zoom out)
 * @param centerX X coordinate of zoom center point
 * @param centerY Y coordinate of zoom center point
 * @param config Timeline configuration
 * @returns New zoom level
 */
export function calculateZoom(
  currentZoom: number,
  delta: number,
  centerX: number,
  centerY: number,
  config: TimelineConfig
): number {
  const zoomStep = 0.1;
  const newZoom = clampZoom(currentZoom + delta * zoomStep, config);
  return newZoom;
}

/**
 * Apply zoom transformation to a coordinate
 * @param coordinate Original coordinate
 * @param zoom Zoom level
 * @returns Transformed coordinate
 */
export function applyZoom(coordinate: number, zoom: number): number {
  return coordinate * zoom;
}

/**
 * Calculate scroll position after zoom (to maintain focus point)
 * @param scrollX Current scroll X
 * @param scrollY Current scroll Y
 * @param oldZoom Old zoom level
 * @param newZoom New zoom level
 * @param focusX Focus point X (relative to viewport)
 * @param focusY Focus point Y (relative to viewport)
 * @returns New scroll position
 */
export function calculateScrollAfterZoom(
  scrollX: number,
  scrollY: number,
  oldZoom: number,
  newZoom: number,
  focusX: number,
  focusY: number
): { scrollX: number; scrollY: number } {
  const zoomRatio = newZoom / oldZoom;

  return {
    scrollX: scrollX * zoomRatio + focusX * (1 - zoomRatio),
    scrollY: scrollY * zoomRatio + focusY * (1 - zoomRatio),
  };
}

/**
 * Convert screen coordinates to timeline coordinates
 * @param screenX Screen X coordinate
 * @param screenY Screen Y coordinate
 * @param scrollX Current scroll X
 * @param scrollY Current scroll Y
 * @param zoom Current zoom level
 * @returns Timeline coordinates
 */
export function screenToTimeline(
  screenX: number,
  screenY: number,
  scrollX: number,
  scrollY: number,
  zoom: number
): { x: number; y: number } {
  return {
    x: (screenX + scrollX) / zoom,
    y: (screenY + scrollY) / zoom,
  };
}

/**
 * Convert timeline coordinates to screen coordinates
 * @param timelineX Timeline X coordinate
 * @param timelineY Timeline Y coordinate
 * @param scrollX Current scroll X
 * @param scrollY Current scroll Y
 * @param zoom Current zoom level
 * @returns Screen coordinates
 */
export function timelineToScreen(
  timelineX: number,
  timelineY: number,
  scrollX: number,
  scrollY: number,
  zoom: number
): { x: number; y: number } {
  return {
    x: timelineX * zoom - scrollX,
    y: timelineY * zoom - scrollY,
  };
}

/**
 * Calculate bezier curve path for dependency connector
 * @param fromX Source X coordinate
 * @param fromY Source Y coordinate
 * @param toX Target X coordinate
 * @param toY Target Y coordinate
 * @param curvature Curve curvature (0-1, default 0.5)
 * @returns SVG path string for bezier curve
 */
export function calculateBezierPath(
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
  curvature: number = 0.5
): string {
  // Calculate control points for smooth bezier curve
  const dx = toX - fromX;
  const dy = toY - fromY;

  // Control points offset based on distance
  const controlOffsetX = Math.abs(dx) * curvature;
  const controlOffsetY = Math.abs(dy) * curvature;

  // Determine direction for control points
  const cp1x = fromX + controlOffsetX;
  const cp1y = fromY;
  const cp2x = toX - controlOffsetX;
  const cp2y = toY;

  // Generate SVG path command
  return `M ${fromX} ${fromY} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${toX} ${toY}`;
}

/**
 * Calculate dependency connector path between phases
 * @param fromPhase Source phase
 * @param toPhase Target phase
 * @param fromLayout Source phase layout
 * @param toLayout Target phase layout
 * @param config Timeline configuration
 * @param zoom Current zoom level
 * @returns SVG path string or null if phases are invalid
 */
export function calculatePhaseDependencyPath(
  fromPhase: TimelinePhase,
  toPhase: TimelinePhase,
  fromLayout: PhaseLayout,
  toLayout: PhaseLayout,
  config: TimelineConfig,
  zoom: number
): string | null {
  // Calculate connection points (right side of source, left side of target)
  const fromX = fromLayout.totalWidth + (config.subtaskSpacing * zoom) / 2;
  const fromY = fromLayout.y + fromLayout.height / 2;
  const toX = 0;
  const toY = toLayout.y + toLayout.height / 2;

  return calculateBezierPath(fromX, fromY, toX, toY);
}

/**
 * Calculate dependency connector path between subtasks
 * @param fromSubtask Source subtask
 * @param toSubtask Target subtask
 * @param fromLayout Source subtask layout
 * @param toLayout Target subtask layout
 * @param config Timeline configuration
 * @param zoom Current zoom level
 * @returns SVG path string or null if subtasks are invalid
 */
export function calculateSubtaskDependencyPath(
  fromSubtask: TimelineSubtask,
  toSubtask: TimelineSubtask,
  fromLayout: SubtaskLayout,
  toLayout: SubtaskLayout,
  config: TimelineConfig,
  zoom: number
): string | null {
  // Calculate connection points (right side of source, left side of target)
  const fromX = fromLayout.x + fromLayout.width;
  const fromY = fromLayout.y + fromLayout.height / 2;
  const toX = toLayout.x;
  const toY = toLayout.y + toLayout.height / 2;

  return calculateBezierPath(fromX, fromY, toX, toY);
}

/**
 * Calculate all dependency paths for timeline
 * @param phases Timeline phases
 * @param subtasks Timeline subtasks
 * @param phaseLayouts Map of phase ID to layout
 * @param subtaskLayouts Map of subtask ID to layout
 * @param config Timeline configuration
 * @param viewState Current view state
 * @returns Array of dependency objects with paths
 */
export function calculateAllDependencyPaths(
  phases: TimelinePhase[],
  subtasks: TimelineSubtask[],
  phaseLayouts: Map<string, PhaseLayout>,
  subtaskLayouts: Map<string, SubtaskLayout>,
  config: TimelineConfig,
  viewState: TimelineViewState
): TimelineDependency[] {
  const dependencies: TimelineDependency[] = [];

  // Calculate phase dependencies
  phases.forEach((phase) => {
    const phaseId = getPhaseId(phase.phase);
    const phaseLayout = phaseLayouts.get(phaseId);
    if (!phaseLayout) return;

    phase.depends_on?.forEach((depPhaseNumber) => {
      const depPhase = phases.find((p) => p.phase === depPhaseNumber);
      const depPhaseId = depPhase ? getPhaseId(depPhase.phase) : null;
      const depLayout = depPhaseId ? phaseLayouts.get(depPhaseId) : null;

      if (depPhase && depPhaseId && depLayout) {
        const path = calculatePhaseDependencyPath(
          depPhase,
          phase,
          depLayout,
          phaseLayout,
          config,
          viewState.zoom
        );

        if (path) {
          dependencies.push({
            fromId: depPhaseId,
            toId: phaseId,
            type: 'phase',
            path,
          });
        }
      }
    });
  });

  // Calculate subtask dependencies
  subtasks.forEach((subtask) => {
    const subtaskLayout = subtaskLayouts.get(subtask.id);
    if (!subtaskLayout) return;

    subtask.dependsOn?.forEach((depId) => {
      const depSubtask = subtasks.find((st) => st.id === depId);
      const depLayout = depSubtask ? subtaskLayouts.get(depSubtask.id) : null;

      if (depSubtask && depLayout) {
        const path = calculateSubtaskDependencyPath(
          depSubtask,
          subtask,
          depLayout,
          subtaskLayout,
          config,
          viewState.zoom
        );

        if (path) {
          dependencies.push({
            fromId: depSubtask.id,
            toId: subtask.id,
            type: 'subtask',
            path,
          });
        }
      }
    });
  });

  return dependencies;
}

/**
 * Check if a point is within a subtask's bounds
 * @param point X, Y coordinates to check
 * @param subtask Subtask with layout
 * @param subtaskLayout Calculated subtask layout
 * @param scrollX Current scroll X
 * @param scrollY Current scroll Y
 * @param zoom Current zoom level
 * @returns True if point is within subtask bounds
 */
export function isPointInSubtask(
  point: { x: number; y: number },
  subtask: TimelineSubtask,
  subtaskLayout: SubtaskLayout,
  scrollX: number,
  scrollY: number,
  zoom: number
): boolean {
  const screen = timelineToScreen(
    subtaskLayout.x,
    subtaskLayout.y,
    scrollX,
    scrollY,
    zoom
  );

  const width = subtaskLayout.width * zoom;
  const height = subtaskLayout.height * zoom;

  return (
    point.x >= screen.x &&
    point.x <= screen.x + width &&
    point.y >= screen.y &&
    point.y <= screen.y + height
  );
}

/**
 * Check if a point is within a phase's bounds
 * @param point X, Y coordinates to check
 * @param phase Phase with layout
 * @param phaseLayout Calculated phase layout
 * @param scrollX Current scroll X
 * @param scrollY Current scroll Y
 * @param zoom Current zoom level
 * @returns True if point is within phase bounds
 */
export function isPointInPhase(
  point: { x: number; y: number },
  phase: TimelinePhase,
  phaseLayout: PhaseLayout,
  scrollX: number,
  scrollY: number,
  zoom: number
): boolean {
  const screen = timelineToScreen(
    0,
    phaseLayout.y,
    scrollX,
    scrollY,
    zoom
  );

  const width = phaseLayout.totalWidth * zoom;
  const height = phaseLayout.height * zoom;

  return (
    point.x >= screen.x &&
    point.x <= screen.x + width &&
    point.y >= screen.y &&
    point.y <= screen.y + height
  );
}

/**
 * Find subtask at a given point
 * @param point X, Y coordinates
 * @param subtasks Timeline subtasks
 * @param subtaskLayouts Map of subtask ID to layout
 * @param scrollX Current scroll X
 * @param scrollY Current scroll Y
 * @param zoom Current zoom level
 * @returns Subtask at point or undefined
 */
export function findSubtaskAtPoint(
  point: { x: number; y: number },
  subtasks: TimelineSubtask[],
  subtaskLayouts: Map<string, SubtaskLayout>,
  scrollX: number,
  scrollY: number,
  zoom: number
): TimelineSubtask | undefined {
  // Search in reverse order (topmost first)
  for (let i = subtasks.length - 1; i >= 0; i--) {
    const subtask = subtasks[i];
    const layout = subtaskLayouts.get(subtask.id);

    if (layout && isPointInSubtask(point, subtask, layout, scrollX, scrollY, zoom)) {
      return subtask;
    }
  }

  return undefined;
}

/**
 * Find phase at a given point
 * @param point X, Y coordinates
 * @param phases Timeline phases
 * @param phaseLayouts Map of phase ID to layout
 * @param scrollX Current scroll X
 * @param scrollY Current scroll Y
 * @param zoom Current zoom level
 * @returns Phase at point or undefined
 */
export function findPhaseAtPoint(
  point: { x: number; y: number },
  phases: TimelinePhase[],
  phaseLayouts: Map<string, PhaseLayout>,
  scrollX: number,
  scrollY: number,
  zoom: number
): TimelinePhase | undefined {
  // Search in reverse order (topmost first)
  for (let i = phases.length - 1; i >= 0; i--) {
    const phase = phases[i];
    const phaseId = getPhaseId(phase.phase);
    const layout = phaseLayouts.get(phaseId);

    if (layout && isPointInPhase(point, phase, layout, scrollX, scrollY, zoom)) {
      return phase;
    }
  }

  return undefined;
}
