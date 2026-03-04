import { useMemo } from 'react';
import { Cpu, Lock } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { parseModelId, getAgentLabel } from './model-utils';

/**
 * Agent groupings for organized display
 */
interface AgentGroup {
  title: string;
  agents: string[];
}

const AGENT_GROUPS: AgentGroup[] = [
  {
    title: 'Spec Creation',
    agents: [
      'spec_gatherer',
      'spec_researcher',
      'spec_writer',
      'spec_critic',
      'spec_discovery',
      'spec_context',
      'spec_validation',
      'spec_compaction',
    ],
  },
  {
    title: 'Build',
    agents: ['planner', 'coder'],
  },
  {
    title: 'Quality Assurance',
    agents: ['qa_reviewer', 'qa_fixer'],
  },
  {
    title: 'Utility',
    agents: ['insights', 'merge_resolver', 'commit_message'],
  },
  {
    title: 'Pull Request',
    agents: ['pr_reviewer', 'pr_orchestrator_parallel', 'pr_followup_parallel'],
  },
  {
    title: 'Analysis',
    agents: ['analysis', 'batch_analysis', 'batch_validation'],
  },
  {
    title: 'Roadmap & Ideation',
    agents: ['roadmap_discovery', 'competitor_analysis', 'ideation'],
  },
];

interface AgentModelDisplayProps {
  /**
   * Map of agent type to model ID
   * e.g., { "coder": "claude-sonnet-4-5-20250929", "planner": "opus" }
   */
  agentModels?: Record<string, string>;
  /**
   * Map of locked agent types to their locked model IDs
   * e.g., { "coder": "claude-opus-4-5-20251101" }
   */
  lockedModels?: Record<string, string>;
}

/**
 * AgentModelDisplay Component
 *
 * Displays the current model configuration for each agent type.
 * Shows agent groups with their assigned models and lock status.
 */
export function AgentModelDisplay({ agentModels = {}, lockedModels = {} }: AgentModelDisplayProps) {
  // Group agents by category
  const agentGroups = useMemo(() => {
    return AGENT_GROUPS.map((group) => ({
      ...group,
      agents: group.agents
        .map((agentType) => ({
          type: agentType,
          label: getAgentLabel(agentType),
          modelId: agentModels[agentType] || 'sonnet', // Default to sonnet
          isLocked: !!lockedModels[agentType],
        }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    }));
  }, [agentModels, lockedModels]);

  // Empty state - show before card rendering when no config available
  if (Object.keys(agentModels).length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Cpu className="h-12 w-12 mb-3 opacity-50" />
        <p className="text-sm font-medium">No agent model configuration available</p>
        <p className="text-xs">Agent models will be configured based on your profile settings</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {agentGroups.map((group) => (
        <div key={group.title}>
          <h3 className="text-sm font-semibold text-foreground mb-3">{group.title}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {group.agents.map((agent) => {
              const modelInfo = parseModelId(agent.modelId);

              return (
                <Card key={agent.type} className="bg-muted/30 border-border/50">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Cpu className="h-3.5 w-3.5 text-accent" />
                        {agent.label}
                      </CardTitle>
                      {agent.isLocked && (
                        <span title="Model locked">
                          <Lock className="h-3.5 w-3.5 text-muted-foreground" />
                        </span>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="space-y-2">
                      {/* Model Tier */}
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Model</p>
                        <p className="text-sm font-semibold text-foreground">{modelInfo.name}</p>
                      </div>

                      {/* Version Badge */}
                      {modelInfo.version && (
                        <div>
                          <Badge variant="outline" className="text-xs">
                            v{modelInfo.version}
                          </Badge>
                        </div>
                      )}

                      {/* Model ID (truncated) */}
                      <p className="text-[10px] text-muted-foreground truncate" title={agent.modelId}>
                        {agent.modelId}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
