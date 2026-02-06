/**
 * Sidebar Component (Web Version)
 * Adapted from Electron frontend - simplified for web
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Plus,
  Settings,
  LayoutGrid,
  Terminal,
  Map,
  BookOpen,
  Lightbulb,
  FileText,
  Sparkles,
  GitBranch,
  Wrench,
  PanelLeft,
  PanelLeftClose
} from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from './ui/tooltip';
import { cn } from '../lib/utils';

export type SidebarView = 'kanban' | 'terminals' | 'roadmap' | 'context' | 'ideation' | 'changelog' | 'insights' | 'worktrees' | 'agent-tools';

interface SidebarProps {
  onSettingsClick: () => void;
  onNewTaskClick: () => void;
  activeView?: SidebarView;
  onViewChange?: (view: SidebarView) => void;
}

interface NavItem {
  id: SidebarView;
  label: string;
  icon: React.ElementType;
  shortcut?: string;
}

// Base nav items always shown
const baseNavItems: NavItem[] = [
  { id: 'kanban', label: 'Kanban', icon: LayoutGrid, shortcut: 'K' },
  { id: 'terminals', label: 'Terminals', icon: Terminal, shortcut: 'A' },
  { id: 'insights', label: 'Insights', icon: Sparkles, shortcut: 'N' },
  { id: 'roadmap', label: 'Roadmap', icon: Map, shortcut: 'D' },
  { id: 'ideation', label: 'Ideation', icon: Lightbulb, shortcut: 'I' },
  { id: 'changelog', label: 'Changelog', icon: FileText, shortcut: 'L' },
  { id: 'context', label: 'Context', icon: BookOpen, shortcut: 'C' },
  { id: 'agent-tools', label: 'Agent Tools', icon: Wrench, shortcut: 'M' },
  { id: 'worktrees', label: 'Worktrees', icon: GitBranch, shortcut: 'W' }
];

export function Sidebar({
  onSettingsClick,
  onNewTaskClick,
  activeView = 'kanban',
  onViewChange
}: SidebarProps) {
  const { t } = useTranslation(['navigation', 'common']);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed);
  };

  const handleViewChange = (view: SidebarView) => {
    onViewChange?.(view);
  };

  return (
    <div
      className={cn(
        'flex h-full flex-col border-r bg-background transition-all duration-200',
        isCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Header */}
      <div className="flex h-14 items-center justify-between border-b px-4">
        {!isCollapsed && (
          <h2 className="text-lg font-semibold">Auto Code</h2>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="h-8 w-8"
        >
          {isCollapsed ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1 px-2 py-4">
        <TooltipProvider>
          <div className="space-y-1">
            {baseNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeView === item.id;

              return (
                <Tooltip key={item.id} delayDuration={0}>
                  <TooltipTrigger asChild>
                    <Button
                      variant={isActive ? 'secondary' : 'ghost'}
                      size={isCollapsed ? 'icon' : 'default'}
                      className={cn(
                        'w-full',
                        isCollapsed ? 'h-10 w-10' : 'justify-start',
                        isActive && 'bg-accent text-accent-foreground'
                      )}
                      onClick={() => handleViewChange(item.id)}
                    >
                      <Icon className={cn('h-5 w-5', !isCollapsed && 'mr-2')} />
                      {!isCollapsed && <span>{item.label}</span>}
                      {!isCollapsed && item.shortcut && (
                        <kbd className="ml-auto hidden text-xs text-muted-foreground sm:inline-block">
                          {item.shortcut}
                        </kbd>
                      )}
                    </Button>
                  </TooltipTrigger>
                  {isCollapsed && (
                    <TooltipContent side="right">
                      <p>{item.label}</p>
                      {item.shortcut && (
                        <kbd className="ml-2 text-xs">{item.shortcut}</kbd>
                      )}
                    </TooltipContent>
                  )}
                </Tooltip>
              );
            })}
          </div>
        </TooltipProvider>
      </ScrollArea>

      <Separator />

      {/* Footer Actions */}
      <div className="p-2 space-y-1">
        <TooltipProvider>
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <Button
                variant="default"
                size={isCollapsed ? 'icon' : 'default'}
                className={cn('w-full', isCollapsed ? 'h-10 w-10' : 'justify-start')}
                onClick={onNewTaskClick}
              >
                <Plus className={cn('h-5 w-5', !isCollapsed && 'mr-2')} />
                {!isCollapsed && <span>{t('common:actions.newTask', { defaultValue: 'New Task' })}</span>}
              </Button>
            </TooltipTrigger>
            {isCollapsed && (
              <TooltipContent side="right">
                <p>{t('common:actions.newTask', { defaultValue: 'New Task' })}</p>
              </TooltipContent>
            )}
          </Tooltip>

          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size={isCollapsed ? 'icon' : 'default'}
                className={cn('w-full', isCollapsed ? 'h-10 w-10' : 'justify-start')}
                onClick={onSettingsClick}
              >
                <Settings className={cn('h-5 w-5', !isCollapsed && 'mr-2')} />
                {!isCollapsed && <span>{t('common:actions.settings', { defaultValue: 'Settings' })}</span>}
              </Button>
            </TooltipTrigger>
            {isCollapsed && (
              <TooltipContent side="right">
                <p>{t('common:actions.settings', { defaultValue: 'Settings' })}</p>
              </TooltipContent>
            )}
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
}
