/**
 * Tool Selector Component
 *
 * Allows users to select tools and MCP servers for custom agent templates.
 * Displays base tools (Read, Write, Edit, etc.) and MCP server options
 * in an organized, accessible interface following the pattern from AgentTools.tsx.
 */

import { useState, useMemo, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import { ScrollArea } from '../ui/scroll-area';
import { cn } from '../../lib/utils';
import {
  Search,
  Brain,
  Code,
  FileText,
  Terminal,
  Globe,
  Monitor,
  ClipboardList,
  CheckCircle2
} from 'lucide-react';

// Base tool definitions (from backend BASE_READ_TOOLS, BASE_WRITE_TOOLS, WEB_TOOLS)
interface BaseTool {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  category: 'read' | 'write' | 'web';
}

const BASE_TOOLS: BaseTool[] = [
  {
    id: 'Read',
    name: 'read',
    description: 'Read file contents',
    icon: FileText,
    category: 'read'
  },
  {
    id: 'Glob',
    name: 'glob',
    description: 'Find files by pattern',
    icon: FileText,
    category: 'read'
  },
  {
    id: 'Grep',
    name: 'grep',
    description: 'Search file contents',
    icon: FileText,
    category: 'read'
  },
  {
    id: 'Write',
    name: 'write',
    description: 'Create new files',
    icon: Code,
    category: 'write'
  },
  {
    id: 'Edit',
    name: 'edit',
    description: 'Modify existing files',
    icon: Code,
    category: 'write'
  },
  {
    id: 'Bash',
    name: 'bash',
    description: 'Execute commands',
    icon: Terminal,
    category: 'write'
  },
  {
    id: 'WebFetch',
    name: 'webFetch',
    description: 'Fetch web pages',
    icon: Globe,
    category: 'web'
  },
  {
    id: 'WebSearch',
    name: 'webSearch',
    description: 'Search the web',
    icon: Search,
    category: 'web'
  }
];

// MCP server definitions (from AgentTools.tsx MCP_SERVERS)
interface McpServer {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  required?: boolean;  // Auto-Code MCP is always required
}

const MCP_SERVERS: McpServer[] = [
  {
    id: 'context7',
    name: 'context7',
    description: 'Documentation lookup for libraries and frameworks',
    icon: Search
  },
  {
    id: 'graphiti',
    name: 'graphiti',
    description: 'Knowledge graph for cross-session context',
    icon: Brain
  },
  {
    id: 'linear',
    name: 'linear',
    description: 'Project management via Linear API',
    icon: ClipboardList
  },
  {
    id: 'electron',
    name: 'electron',
    description: 'Desktop app automation via Chrome DevTools',
    icon: Monitor
  },
  {
    id: 'puppeteer',
    name: 'puppeteer',
    description: 'Web browser automation',
    icon: Globe
  },
  {
    id: 'auto-claude',
    name: 'autoClaude',
    description: 'Build progress tracking and session management',
    icon: CheckCircle2,
    required: true  // Always required
  }
];

export interface ToolSelection {
  baseTools: string[];
  mcpServers: string[];
}

interface ToolSelectorProps {
  value?: ToolSelection;
  onChange: (selection: ToolSelection) => void;
  disabled?: boolean;
  error?: string;
}

/**
 * ToolSelector Component
 *
 * Provides tool and MCP server selection UI for custom agent templates.
 * Follows the design patterns from AgentTools.tsx for consistency.
 */
export function ToolSelector({
  value,
  onChange,
  disabled = false,
  error
}: ToolSelectorProps) {
  const { t } = useTranslation('templates');

  // Initialize selections from props
  const [selectedTools, setSelectedTools] = useState<string[]>(
    value?.baseTools || []
  );
  const [selectedMcpServers, setSelectedMcpServers] = useState<string[]>(
    value?.mcpServers || ['auto-claude']  // Auto-Code MCP always included
  );

  // Sync from value prop
  useEffect(() => {
    if (value) {
      setSelectedTools(value.baseTools);
      setSelectedMcpServers(value.mcpServers);
    }
  }, [value]);

  // Group tools by category
  const toolsByCategory = useMemo(() => {
    const grouped = {
      read: BASE_TOOLS.filter(t => t.category === 'read'),
      write: BASE_TOOLS.filter(t => t.category === 'write'),
      web: BASE_TOOLS.filter(t => t.category === 'web')
    };
    return grouped;
  }, []);

  // Handle base tool toggle
  const handleToolToggle = (toolId: string) => {
    const newTools = selectedTools.includes(toolId)
      ? selectedTools.filter(t => t !== toolId)
      : [...selectedTools, toolId];

    setSelectedTools(newTools);
    onChange({
      baseTools: newTools,
      mcpServers: selectedMcpServers
    });
  };

  // Handle MCP server toggle
  const handleMcpToggle = (mcpId: string) => {
    // Auto-Code MCP cannot be deselected
    if (mcpId === 'auto-claude') {
      return;
    }

    const newMcps = selectedMcpServers.includes(mcpId)
      ? selectedMcpServers.filter(m => m !== mcpId)
      : [...selectedMcpServers, mcpId];

    // Always ensure auto-claude is included
    const finalMcps = newMcps.includes('auto-claude')
      ? newMcps
      : [...newMcps, 'auto-claude'];

    setSelectedMcpServers(finalMcps);
    onChange({
      baseTools: selectedTools,
      mcpServers: finalMcps
    });
  };

  // Select/deselect all tools
  const handleSelectAllTools = () => {
    const allTools = BASE_TOOLS.map(t => t.id);
    setSelectedTools(allTools);
    onChange({
      baseTools: allTools,
      mcpServers: selectedMcpServers
    });
  };

  const handleDeselectAllTools = () => {
    setSelectedTools([]);
    onChange({
      baseTools: [],
      mcpServers: selectedMcpServers
    });
  };

  // Select/deselect all MCP servers (except required ones)
  const handleSelectAllMcps = () => {
    const allMcps = MCP_SERVERS.map(m => m.id);
    setSelectedMcpServers(allMcps);
    onChange({
      baseTools: selectedTools,
      mcpServers: allMcps
    });
  };

  const handleDeselectAllMcps = () => {
    // Keep only required MCP servers
    const requiredMcps = MCP_SERVERS.filter(m => m.required).map(m => m.id);
    setSelectedMcpServers(requiredMcps);
    onChange({
      baseTools: selectedTools,
      mcpServers: requiredMcps
    });
  };

  // Check if a tool is selected
  const isToolSelected = (toolId: string) => selectedTools.includes(toolId);

  // Check if an MCP server is selected
  const isMcpSelected = (mcpId: string) => selectedMcpServers.includes(mcpId);

  // Check if MCP server is required (cannot be deselected)
  const isMcpRequired = (mcpId: string) => MCP_SERVERS.find(m => m.id === mcpId)?.required;

  // Category labels
  const categoryLabels = {
    read: 'File Reading',
    write: 'File Writing',
    web: 'Web Access'
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-1">
          {t('toolSelector.title')}
        </h3>
        <p className="text-xs text-muted-foreground">
          {t('toolSelector.description')}
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
          <p className="text-xs text-destructive">{error}</p>
        </div>
      )}

      {/* Base Tools Section */}
      <ScrollArea className="h-auto max-h-96">
        <div className="space-y-4 pr-4">
          <div className="space-y-3">
            {/* Section Header with Select All/Deselect All */}
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {t('toolSelector.baseTools')}
              </h4>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSelectAllTools}
                  disabled={disabled}
                  className="text-xs text-primary hover:text-primary/80 transition-colors disabled:opacity-50"
                >
                  {t('toolSelector.selectAll')}
                </button>
                <span className="text-xs text-muted-foreground">|</span>
                <button
                  type="button"
                  onClick={handleDeselectAllTools}
                  disabled={disabled}
                  className="text-xs text-primary hover:text-primary/80 transition-colors disabled:opacity-50"
                >
                  {t('toolSelector.deselectAll')}
                </button>
              </div>
            </div>

            {/* Tools grouped by category */}
            {Object.entries(toolsByCategory).map(([category, tools]) => (
              <div key={category} className="space-y-2">
                <h5 className="text-xs font-medium text-muted-foreground mb-2">
                  {categoryLabels[category as keyof typeof categoryLabels]}
                </h5>
                <div className="grid grid-cols-1 gap-2">
                  {tools.map((tool) => {
                    const ToolIcon = tool.icon;
                    const isSelected = isToolSelected(tool.id);

                    return (
                      <div
                        key={tool.id}
                        className={cn(
                          "flex items-start gap-3 p-3 rounded-lg border transition-colors",
                          isSelected
                            ? "border-primary bg-primary/5"
                            : "border-border hover:bg-muted/50",
                          disabled && "opacity-50 cursor-not-allowed"
                        )}
                      >
                        <Checkbox
                          id={`tool-${tool.id}`}
                          checked={isSelected}
                          onCheckedChange={() => !disabled && handleToolToggle(tool.id)}
                          disabled={disabled}
                          className="mt-0.5"
                        />
                        <Label
                          htmlFor={`tool-${tool.id}`}
                          className={cn(
                            "flex-1 cursor-pointer text-sm",
                            disabled && "cursor-not-allowed"
                          )}
                        >
                          <div className="flex items-center gap-2 mb-0.5">
                            <ToolIcon className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="font-medium text-foreground">
                              {t(`toolSelector.tools.${tool.name}`)}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {tool.description}
                          </p>
                        </Label>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* MCP Servers Section */}
          <div className="space-y-3 pt-4 border-t border-border">
            {/* Section Header with Select All/Deselect All */}
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {t('toolSelector.mcpServers')}
              </h4>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSelectAllMcps}
                  disabled={disabled}
                  className="text-xs text-primary hover:text-primary/80 transition-colors disabled:opacity-50"
                >
                  {t('toolSelector.selectAll')}
                </button>
                <span className="text-xs text-muted-foreground">|</span>
                <button
                  type="button"
                  onClick={handleDeselectAllMcps}
                  disabled={disabled}
                  className="text-xs text-primary hover:text-primary/80 transition-colors disabled:opacity-50"
                >
                  {t('toolSelector.deselectAll')}
                </button>
              </div>
            </div>

            {/* MCP Server List */}
            <div className="grid grid-cols-1 gap-2">
              {MCP_SERVERS.map((server) => {
                const ServerIcon = server.icon;
                const isSelected = isMcpSelected(server.id);
                const isRequired = isMcpRequired(server.id);

                return (
                  <div
                    key={server.id}
                    className={cn(
                      "flex items-start gap-3 p-3 rounded-lg border transition-colors",
                      isSelected
                        ? "border-primary bg-primary/5"
                        : "border-border hover:bg-muted/50",
                      isRequired && "opacity-75",  // Slight dim for required items
                      disabled && "opacity-50 cursor-not-allowed"
                    )}
                  >
                    <Checkbox
                      id={`mcp-${server.id}`}
                      checked={isSelected}
                      onCheckedChange={() => !disabled && handleMcpToggle(server.id)}
                      disabled={disabled || isRequired}
                      className="mt-0.5"
                    />
                    <Label
                      htmlFor={`mcp-${server.id}`}
                      className={cn(
                        "flex-1 cursor-pointer text-sm",
                        (disabled || isRequired) && "cursor-not-allowed"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-0.5">
                        <ServerIcon className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="font-medium text-foreground">
                          {t(`toolSelector.mcp.${server.name}`)}
                        </span>
                        {isRequired && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-secondary text-secondary-foreground rounded">
                            Required
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {server.description}
                        {isRequired && (
                          <span className="ml-1">
                            ({t('toolSelector.autoClaudeRequired')})
                          </span>
                        )}
                      </p>
                    </Label>
                  </div>
                );
              })}
            </div>

            {/* Required MCP Info */}
            <div className="rounded-md bg-muted/50 border border-border p-3 mt-2">
              <p className="text-xs text-muted-foreground">
                {t('toolSelector.autoClaudeRequired')}
              </p>
            </div>
          </div>
        </div>
      </ScrollArea>

      {/* Selection Summary */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border">
        <span>
          {selectedTools.length} {selectedTools.length === 1 ? 'tool' : 'tools'} selected
        </span>
        <span>|</span>
        <span>
          {selectedMcpServers.length} {selectedMcpServers.length === 1 ? 'MCP server' : 'MCP servers'} enabled
        </span>
      </div>
    </div>
  );
}
