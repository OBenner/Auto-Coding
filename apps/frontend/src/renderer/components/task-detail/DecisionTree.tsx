import { useState, useMemo } from 'react';
import {
  Brain,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Info,
  Target,
  TrendingUp,
  Layers,
  GitBranch,
  Lightbulb,
  Network
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { DecisionPoint, DecisionType, ConfidenceLevel } from '../../../shared/types';

interface DecisionTreeProps {
  decisions: DecisionPoint[];
  className?: string;
  groupBy?: 'phase' | 'type' | 'confidence';
}

// Decision type metadata
const DECISION_TYPE_META: Record<DecisionType, { label: string; icon: typeof Brain; color: string }> = {
  approach: {
    label: 'Approach',
    icon: Target,
    color: 'text-blue-500 bg-blue-500/10 border-blue-500/30'
  },
  implementation: {
    label: 'Implementation',
    icon: Layers,
    color: 'text-purple-500 bg-purple-500/10 border-purple-500/30'
  },
  tool_selection: {
    label: 'Tool Selection',
    icon: Brain,
    color: 'text-cyan-500 bg-cyan-500/10 border-cyan-500/30'
  },
  file_modification: {
    label: 'File Change',
    icon: GitBranch,
    color: 'text-amber-500 bg-amber-500/10 border-amber-500/30'
  },
  error_recovery: {
    label: 'Error Recovery',
    icon: AlertTriangle,
    color: 'text-orange-500 bg-orange-500/10 border-orange-500/30'
  },
  architecture: {
    label: 'Architecture',
    icon: Layers,
    color: 'text-indigo-500 bg-indigo-500/10 border-indigo-500/30'
  },
  optimization: {
    label: 'Optimization',
    icon: TrendingUp,
    color: 'text-green-500 bg-green-500/10 border-green-500/30'
  },
  other: {
    label: 'Other',
    icon: Info,
    color: 'text-gray-500 bg-gray-500/10 border-gray-500/30'
  }
};

// Confidence level metadata
const CONFIDENCE_META: Record<ConfidenceLevel, { label: string; color: string; icon: typeof CheckCircle2 }> = {
  very_low: {
    label: 'Very Low',
    color: 'text-red-500 bg-red-500/10 border-red-500/30',
    icon: AlertTriangle
  },
  low: {
    label: 'Low',
    color: 'text-orange-500 bg-orange-500/10 border-orange-500/30',
    icon: AlertTriangle
  },
  medium: {
    label: 'Medium',
    color: 'text-amber-500 bg-amber-500/10 border-amber-500/30',
    icon: Info
  },
  high: {
    label: 'High',
    color: 'text-green-500 bg-green-500/10 border-green-500/30',
    icon: CheckCircle2
  },
  very_high: {
    label: 'Very High',
    color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30',
    icon: CheckCircle2
  }
};

// Tree node structure
interface TreeNode {
  id: string;
  label: string;
  icon?: typeof Brain;
  color?: string;
  decision?: DecisionPoint;
  children: TreeNode[];
  count?: number;
  averageConfidence?: number;
}

export function DecisionTree({ decisions, className, groupBy = 'phase' }: DecisionTreeProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set(['root']));

  // Build tree structure based on groupBy parameter
  const treeRoot = useMemo(() => {
    if (decisions.length === 0) {
      return null;
    }

    const root: TreeNode = {
      id: 'root',
      label: 'All Decisions',
      icon: Network,
      color: 'text-primary bg-primary/10 border-primary/30',
      children: [],
      count: decisions.length,
      averageConfidence: decisions.reduce((sum, d) => sum + d.confidence, 0) / decisions.length
    };

    if (groupBy === 'phase') {
      // Group by phase
      const phaseGroups = new Map<string, DecisionPoint[]>();

      decisions.forEach(decision => {
        const phase = decision.phase || 'Unknown';
        if (!phaseGroups.has(phase)) {
          phaseGroups.set(phase, []);
        }
        phaseGroups.get(phase)!.push(decision);
      });

      phaseGroups.forEach((phaseDecisions, phase) => {
        const phaseNode: TreeNode = {
          id: `phase-${phase}`,
          label: phase,
          icon: Layers,
          color: 'text-info bg-info/10 border-info/30',
          children: [],
          count: phaseDecisions.length,
          averageConfidence: phaseDecisions.reduce((sum, d) => sum + d.confidence, 0) / phaseDecisions.length
        };

        // Group by subtask within phase
        const subtaskGroups = new Map<string, DecisionPoint[]>();
        const noSubtask: DecisionPoint[] = [];

        phaseDecisions.forEach(decision => {
          if (decision.subtask_id) {
            if (!subtaskGroups.has(decision.subtask_id)) {
              subtaskGroups.set(decision.subtask_id, []);
            }
            subtaskGroups.get(decision.subtask_id)!.push(decision);
          } else {
            noSubtask.push(decision);
          }
        });

        // Add subtask nodes
        subtaskGroups.forEach((subtaskDecisions, subtaskId) => {
          const subtaskNode: TreeNode = {
            id: `subtask-${subtaskId}`,
            label: subtaskId,
            icon: Target,
            color: 'text-purple-500 bg-purple-500/10 border-purple-500/30',
            children: subtaskDecisions.map((d, idx) => createDecisionNode(d, `${subtaskId}-${idx}`)),
            count: subtaskDecisions.length,
            averageConfidence: subtaskDecisions.reduce((sum, d) => sum + d.confidence, 0) / subtaskDecisions.length
          };
          phaseNode.children.push(subtaskNode);
        });

        // Add decisions without subtask
        noSubtask.forEach((decision, idx) => {
          phaseNode.children.push(createDecisionNode(decision, `${phase}-${idx}`));
        });

        root.children.push(phaseNode);
      });
    } else if (groupBy === 'type') {
      // Group by decision type
      const typeGroups = new Map<DecisionType, DecisionPoint[]>();

      decisions.forEach(decision => {
        if (!typeGroups.has(decision.decision_type)) {
          typeGroups.set(decision.decision_type, []);
        }
        typeGroups.get(decision.decision_type)!.push(decision);
      });

      typeGroups.forEach((typeDecisions, type) => {
        const typeMeta = DECISION_TYPE_META[type];
        const typeNode: TreeNode = {
          id: `type-${type}`,
          label: typeMeta.label,
          icon: typeMeta.icon,
          color: typeMeta.color,
          children: typeDecisions.map((d, idx) => createDecisionNode(d, `${type}-${idx}`)),
          count: typeDecisions.length,
          averageConfidence: typeDecisions.reduce((sum, d) => sum + d.confidence, 0) / typeDecisions.length
        };
        root.children.push(typeNode);
      });
    } else if (groupBy === 'confidence') {
      // Group by confidence level
      const confidenceGroups = new Map<ConfidenceLevel, DecisionPoint[]>();

      decisions.forEach(decision => {
        if (!confidenceGroups.has(decision.confidence_level)) {
          confidenceGroups.set(decision.confidence_level, []);
        }
        confidenceGroups.get(decision.confidence_level)!.push(decision);
      });

      // Sort by confidence (high to low)
      const sortedLevels: ConfidenceLevel[] = ['very_high', 'high', 'medium', 'low', 'very_low'];

      sortedLevels.forEach(level => {
        if (confidenceGroups.has(level)) {
          const levelDecisions = confidenceGroups.get(level)!;
          const confidenceMeta = CONFIDENCE_META[level];
          const levelNode: TreeNode = {
            id: `confidence-${level}`,
            label: confidenceMeta.label,
            icon: confidenceMeta.icon,
            color: confidenceMeta.color,
            children: levelDecisions.map((d, idx) => createDecisionNode(d, `${level}-${idx}`)),
            count: levelDecisions.length,
            averageConfidence: levelDecisions.reduce((sum, d) => sum + d.confidence, 0) / levelDecisions.length
          };
          root.children.push(levelNode);
        }
      });
    }

    return root;
  }, [decisions, groupBy]);

  const toggleNode = (nodeId: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  if (!treeRoot || decisions.length === 0) {
    return (
      <div className={cn('flex items-center justify-center py-8 text-muted-foreground', className)}>
        <Network className="mr-2 h-5 w-5" />
        <span>No decisions to display</span>
      </div>
    );
  }

  return (
    <div className={cn('space-y-1', className)}>
      <TreeNodeComponent
        node={treeRoot}
        isExpanded={expandedNodes.has(treeRoot.id)}
        onToggle={() => toggleNode(treeRoot.id)}
        depth={0}
        expandedNodes={expandedNodes}
        onToggleNode={toggleNode}
      />
    </div>
  );
}

// Helper to create a decision node
function createDecisionNode(decision: DecisionPoint, id: string): TreeNode {
  const typeMeta = DECISION_TYPE_META[decision.decision_type];
  return {
    id,
    label: decision.chosen_approach,
    icon: typeMeta.icon,
    color: typeMeta.color,
    decision,
    children: []
  };
}

// Tree node component
interface TreeNodeComponentProps {
  node: TreeNode;
  isExpanded: boolean;
  onToggle: () => void;
  depth: number;
  expandedNodes: Set<string>;
  onToggleNode: (nodeId: string) => void;
}

function TreeNodeComponent({
  node,
  isExpanded,
  onToggle,
  depth,
  expandedNodes,
  onToggleNode
}: TreeNodeComponentProps) {
  const hasChildren = node.children.length > 0;
  const Icon = node.icon || Info;
  const isDecisionNode = !!node.decision;

  return (
    <div className="relative">
      {/* Tree connector lines */}
      {depth > 0 && (
        <div
          className="absolute left-0 top-0 bottom-0 w-px bg-border"
          style={{ left: `${(depth - 1) * 24 + 12}px` }}
        />
      )}

      {depth > 0 && (
        <div
          className="absolute top-6 left-0 h-px bg-border"
          style={{
            left: `${(depth - 1) * 24 + 12}px`,
            width: '12px'
          }}
        />
      )}

      {/* Node content */}
      <button
        onClick={onToggle}
        className={cn(
          'w-full flex items-center gap-2 py-2 px-3 rounded-md hover:bg-accent/50 transition-colors text-left',
          isDecisionNode && 'hover:bg-accent/30'
        )}
        style={{ paddingLeft: `${depth * 24 + 12}px` }}
      >
        {/* Expand/collapse icon (only for nodes with children) */}
        {hasChildren ? (
          <div className="flex-shrink-0">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        ) : (
          <div className="w-4 flex-shrink-0" />
        )}

        {/* Node icon */}
        <div className="flex-shrink-0">
          <div className={cn('rounded p-1.5 border', node.color)}>
            <Icon className="h-3.5 w-3.5" />
          </div>
        </div>

        {/* Node label */}
        <div className="flex-1 min-w-0">
          <span className={cn(
            'text-sm',
            isDecisionNode ? 'font-normal' : 'font-medium'
          )}>
            {node.label}
          </span>
        </div>

        {/* Node metadata */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Decision-specific badges */}
          {isDecisionNode && node.decision && (
            <>
              {/* Confidence badge */}
              <ConfidenceBadge decision={node.decision} />

              {/* Review required badge */}
              {node.decision.requires_review && (
                <Badge variant="outline" className="text-xs text-amber-500 bg-amber-500/10 border-amber-500/30">
                  <AlertTriangle className="mr-1 h-3 w-3" />
                  Review
                </Badge>
              )}
            </>
          )}

          {/* Group node badges */}
          {!isDecisionNode && (
            <>
              {/* Count badge */}
              {node.count !== undefined && (
                <Badge variant="outline" className="text-xs">
                  {node.count} {node.count === 1 ? 'decision' : 'decisions'}
                </Badge>
              )}

              {/* Average confidence badge */}
              {node.averageConfidence !== undefined && (
                <Badge variant="outline" className="text-xs">
                  Avg: {Math.round(node.averageConfidence * 100)}%
                </Badge>
              )}
            </>
          )}

          {/* Timestamp for decision nodes */}
          {isDecisionNode && node.decision && (
            <span className="text-xs text-muted-foreground">
              {new Date(node.decision.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>
      </button>

      {/* Decision details (for leaf nodes) */}
      {isExpanded && isDecisionNode && node.decision && (
        <DecisionDetails decision={node.decision} depth={depth} />
      )}

      {/* Children nodes */}
      {isExpanded && hasChildren && (
        <div className="space-y-1 mt-1">
          {node.children.map(child => (
            <TreeNodeComponent
              key={child.id}
              node={child}
              isExpanded={expandedNodes.has(child.id)}
              onToggle={() => onToggleNode(child.id)}
              depth={depth + 1}
              expandedNodes={expandedNodes}
              onToggleNode={onToggleNode}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Confidence badge component
function ConfidenceBadge({ decision }: { decision: DecisionPoint }) {
  const confidenceMeta = CONFIDENCE_META[decision.confidence_level];
  const ConfidenceIcon = confidenceMeta.icon;

  return (
    <Badge variant="outline" className={cn('text-xs', confidenceMeta.color)}>
      <ConfidenceIcon className="mr-1 h-3 w-3" />
      {Math.round(decision.confidence * 100)}%
    </Badge>
  );
}

// Decision details component
function DecisionDetails({ decision, depth }: { decision: DecisionPoint; depth: number }) {
  return (
    <div
      className="py-2 px-3 border-l-2 border-primary/30 bg-accent/20 space-y-2 text-sm"
      style={{ marginLeft: `${depth * 24 + 12}px` }}
    >
      {/* Context */}
      {decision.context && (
        <div>
          <span className="text-xs font-semibold text-muted-foreground uppercase">Context:</span>
          <p className="text-xs text-foreground mt-0.5">{decision.context}</p>
        </div>
      )}

      {/* Reasoning */}
      {decision.reasoning && (
        <div>
          <span className="text-xs font-semibold text-muted-foreground uppercase flex items-center">
            <Lightbulb className="mr-1 h-3 w-3 text-amber-500" />
            Reasoning:
          </span>
          <p className="text-xs text-foreground mt-0.5">{decision.reasoning}</p>
        </div>
      )}

      {/* Alternatives count */}
      {decision.alternatives && decision.alternatives.length > 0 && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <GitBranch className="h-3 w-3" />
          <span>{decision.alternatives.length} alternative{decision.alternatives.length !== 1 ? 's' : ''} considered</span>
        </div>
      )}

      {/* Impact */}
      {decision.impact && (
        <div className="flex items-center gap-1 text-xs">
          <TrendingUp className="h-3 w-3 text-green-500" />
          <span className="text-muted-foreground">Impact:</span>
          <span className="text-foreground">{decision.impact}</span>
        </div>
      )}

      {/* Dependencies */}
      {decision.dependencies && decision.dependencies.length > 0 && (
        <div>
          <span className="text-xs font-semibold text-muted-foreground uppercase">Dependencies:</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {decision.dependencies.map((dep, idx) => (
              <Badge key={idx} variant="outline" className="text-xs">
                {dep}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
