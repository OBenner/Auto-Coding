/**
 * DependencyConnector component
 *
 * SVG-based component that renders dependency relationships between phases
 * and subtasks using bezier curves with directional arrow markers.
 */

import { memo } from 'react';
import { calculateAllDependencyPaths } from './utils/timeline-layout';
import type {
  TimelinePhase,
  TimelineSubtask,
  PhaseLayout,
  SubtaskLayout,
  TimelineConfig,
  TimelineViewState,
  TimelineDependency,
} from './types';

interface DependencyConnectorProps {
  /** Timeline phases */
  phases: TimelinePhase[];
  /** Timeline subtasks */
  subtasks: TimelineSubtask[];
  /** Calculated phase layouts */
  phaseLayouts: Map<string, PhaseLayout>;
  /** Calculated subtask layouts */
  subtaskLayouts: Map<string, SubtaskLayout>;
  /** Timeline configuration */
  config: TimelineConfig;
  /** Current view state (for zoom/pan) */
  viewState: TimelineViewState;
  /** Additional CSS classes */
  className?: string;
}

// Hardcoded colors for dependency lines (extracted from Tailwind classes)
const DEPENDENCY_COLORS = {
  planner: '#f59e0b', // amber-500
  coder: '#3b82f6',   // blue-500 (info)
  qa: '#a855f7',      // purple-500
  inactive: '#9ca3af', // gray-400
};

/**
 * Get agent type and color for a dependency based on its target
 */
function getDependencyInfo(
  dep: TimelineDependency,
  phases: TimelinePhase[],
  subtasks: TimelineSubtask[]
): { color: string; agentType: string } {
  let agentType: string = 'inactive';

  if (dep.type === 'phase') {
    const targetPhase = phases.find(p => `phase-${p.phase}` === dep.toId);
    agentType = targetPhase?.agentType || 'inactive';
  } else {
    const targetSubtask = subtasks.find(s => s.id === dep.toId);
    if (targetSubtask) {
      const targetPhase = phases.find(p => `phase-${p.phase}` === targetSubtask.phaseId);
      agentType = targetPhase?.agentType || 'inactive';
    }
  }

  const color = DEPENDENCY_COLORS[agentType as keyof typeof DEPENDENCY_COLORS] || DEPENDENCY_COLORS.inactive;
  return { color, agentType };
}

/**
 * Renders dependency connections as SVG bezier curves with arrow markers
 * Integrates with BuildTimeline's SVG overlay layer for visual relationship display
 */
export const DependencyConnector = memo(function DependencyConnector({
  phases,
  subtasks,
  phaseLayouts,
  subtaskLayouts,
  config,
  viewState,
  className,
}: DependencyConnectorProps) {
  // Calculate all dependency paths
  const dependencyPaths = calculateAllDependencyPaths(
    phases,
    subtasks,
    phaseLayouts,
    subtaskLayouts,
    config,
    viewState
  );

  // If no dependencies, don't render anything
  if (dependencyPaths.length === 0) {
    return null;
  }

  return (
    <svg
      className={className}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none', // Allow clicks to pass through to elements below
        overflow: 'visible',
      }}
    >
      {/* Define arrow markers for dependency direction indicators */}
      <defs>
        {/* Planner arrow marker */}
        <marker
          id="arrow-planner"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path
            d="M 0 0 L 10 5 L 0 10 z"
            fill={DEPENDENCY_COLORS.planner}
          />
        </marker>

        {/* Coder arrow marker */}
        <marker
          id="arrow-coder"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path
            d="M 0 0 L 10 5 L 0 10 z"
            fill={DEPENDENCY_COLORS.coder}
          />
        </marker>

        {/* QA arrow marker */}
        <marker
          id="arrow-qa"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path
            d="M 0 0 L 10 5 L 0 10 z"
            fill={DEPENDENCY_COLORS.qa}
          />
        </marker>

        {/* Inactive/default arrow marker */}
        <marker
          id="arrow-inactive"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path
            d="M 0 0 L 10 5 L 0 10 z"
            fill={DEPENDENCY_COLORS.inactive}
          />
        </marker>
      </defs>

      {/* Render dependency paths as bezier curves */}
      {dependencyPaths.map((dep, index) => {
        // Skip if no path calculated
        if (!dep.path) return null;

        const { color, agentType } = getDependencyInfo(dep, phases, subtasks);
        const markerId = `arrow-${agentType}`;

        return (
          <path
            key={`${dep.fromId}-${dep.toId}-${dep.type}-${index}`}
            d={dep.path}
            fill="none"
            stroke={color}
            strokeWidth="2"
            strokeOpacity="0.6"
            markerEnd={`url(#${markerId})`}
            className="dependency-line"
            style={{
              transition: 'stroke-opacity 0.2s ease',
            }}
          />
        );
      })}
    </svg>
  );
});
