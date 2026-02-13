/**
 * Sidebar Component (Web Version)
 * Adapted from Electron frontend - simplified for web
 * Enhanced with responsive design for mobile devices
 */

import { useState, useEffect } from 'react';
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
  PanelLeftClose,
  X
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
  /** Whether sidebar is open on mobile (overlay mode) */
  isMobileOpen?: boolean;
  /** Callback when mobile sidebar should close */
  onMobileClose?: () => void;
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
  onViewChange,
  isMobileOpen = false,
  onMobileClose
}: SidebarProps) {
  const { t } = useTranslation(['navigation', 'common']);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile screen size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed);
  };

  const handleViewChange = (view: SidebarView) => {
    onViewChange?.(view);
    // Close mobile sidebar after selecting a view
    if (isMobile && onMobileClose) {
      onMobileClose();
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobile && isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <div
        className={cn(
          'flex h-full flex-col border-r bg-background transition-all duration-200',
          // Desktop: always visible, width changes based on collapse
          'lg:relative lg:z-0',
          isCollapsed ? 'lg:w-16' : 'lg:w-64',
          // Mobile: fixed overlay, only visible when open
          isMobile
            ? isMobileOpen
              ? 'fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-200'
              : 'fixed inset-y-0 left-0 z-50 w-64 -translate-x-full transform transition-transform duration-200'
            : 'relative'
        )}
      >
      {/* Header */}
      <div className="flex h-14 items-center justify-between border-b px-4">
        {!isCollapsed && (
          <h2 className="text-lg font-semibold">{t('common:appName')}</h2>
        )}
        <div className="flex items-center gap-1">
          {/* Mobile close button */}
          {isMobile && onMobileClose && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onMobileClose}
              className="h-8 w-8 lg:hidden"
              aria-label="Close sidebar"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
          {/* Desktop collapse button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="hidden h-8 w-8 lg:flex"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <PanelLeft className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </Button>
        </div>
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
                        // Touch-friendly minimum size (44x44px) on mobile
                        isMobile ? 'min-h-[44px]' : isCollapsed ? 'h-10 w-10' : 'h-10',
                        'justify-start',
                        isActive && 'bg-accent text-accent-foreground'
                      )}
                      onClick={() => handleViewChange(item.id)}
                    >
                      <Icon className={cn('h-5 w-5 flex-shrink-0', !isCollapsed && 'mr-2')} />
                      {!isCollapsed && <span className="truncate">{item.label}</span>}
                      {!isCollapsed && item.shortcut && (
                        <kbd className="ml-auto hidden text-xs text-muted-foreground sm:inline-block">
                          {item.shortcut}
                        </kbd>
                      )}
                    </Button>
                  </TooltipTrigger>
                  {isCollapsed && !isMobile && (
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
                className={cn(
                  'w-full',
                  // Touch-friendly minimum size (44x44px) on mobile
                  isMobile ? 'min-h-[44px]' : isCollapsed ? 'h-10 w-10' : 'h-10',
                  'justify-start'
                )}
                onClick={() => {
                  onNewTaskClick();
                  // Close mobile sidebar after clicking new task
                  if (isMobile && onMobileClose) {
                    onMobileClose();
                  }
                }}
              >
                <Plus className={cn('h-5 w-5 flex-shrink-0', !isCollapsed && 'mr-2')} />
                {!isCollapsed && <span className="truncate">{t('common:actions.newTask', { defaultValue: 'New Task' })}</span>}
              </Button>
            </TooltipTrigger>
            {isCollapsed && !isMobile && (
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
                className={cn(
                  'w-full',
                  // Touch-friendly minimum size (44x44px) on mobile
                  isMobile ? 'min-h-[44px]' : isCollapsed ? 'h-10 w-10' : 'h-10',
                  'justify-start'
                )}
                onClick={() => {
                  onSettingsClick();
                  // Close mobile sidebar after clicking settings
                  if (isMobile && onMobileClose) {
                    onMobileClose();
                  }
                }}
              >
                <Settings className={cn('h-5 w-5 flex-shrink-0', !isCollapsed && 'mr-2')} />
                {!isCollapsed && <span className="truncate">{t('common:actions.settings', { defaultValue: 'Settings' })}</span>}
              </Button>
            </TooltipTrigger>
            {isCollapsed && !isMobile && (
              <TooltipContent side="right">
                <p>{t('common:actions.settings', { defaultValue: 'Settings' })}</p>
              </TooltipContent>
            )}
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
    </>
  );
}
