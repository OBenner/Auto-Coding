import {
  Brain,
  AlertTriangle,
  CheckCircle2,
  Info,
  Target,
  TrendingUp,
  Layers,
  GitBranch,
} from 'lucide-react';
import type { DecisionType, ConfidenceLevel } from '../types';

export interface DecisionTypeMeta {
  label: string;
  icon: typeof Brain;
  color: string;
}

export interface ConfidenceMeta {
  label: string;
  color: string;
  icon: typeof CheckCircle2;
}

const DEFAULT_TYPE_META: DecisionTypeMeta = {
  label: 'Other',
  icon: Info,
  color: 'text-gray-500 bg-gray-500/10 border-gray-500/30'
};

const DEFAULT_CONFIDENCE_META: ConfidenceMeta = {
  label: 'Medium',
  color: 'text-amber-500 bg-amber-500/10 border-amber-500/30',
  icon: Info
};

export const DECISION_TYPE_META: Record<DecisionType, DecisionTypeMeta> = {
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

export const CONFIDENCE_META: Record<ConfidenceLevel, ConfidenceMeta> = {
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

/** Safe lookup with fallback for unknown decision types */
export function getDecisionTypeMeta(type: string): DecisionTypeMeta {
  return DECISION_TYPE_META[type as DecisionType] ?? DEFAULT_TYPE_META;
}

/** Safe lookup with fallback for unknown confidence levels */
export function getConfidenceMeta(level: string): ConfidenceMeta {
  return CONFIDENCE_META[level as ConfidenceLevel] ?? DEFAULT_CONFIDENCE_META;
}
