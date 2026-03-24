import { useState, useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'motion/react';
import {
  Plus,
  Settings,
  LayoutGrid,
  Terminal,
  Map as MapIcon,
  BookOpen,
  Lightbulb,
  AlertCircle,
  Download,
  RefreshCw,
  Github,
  GitlabIcon,
  GitPullRequest,
  GitMerge,
  FileText,
  Sparkles,
  GitBranch,
  HelpCircle,
  Wrench,
  PanelLeft,
  PanelLeftClose,
  Puzzle,
  BarChart3,
  Webhook,
  TrendingUp,
  Play,
  Calendar,
  Activity,
  Database,
  MessageSquare,
  Code,
  Brain
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from './ui/dialog';
import { cn } from '../lib/utils';
import {
  useProjectStore,
  removeProject,
  initializeProject
} from '../stores/project-store';
import { useSettingsStore, saveSettings } from '../stores/settings-store';
import { useShallow } from 'zustand/react/shallow';
import { AddProjectModal } from './AddProjectModal';
import { GitSetupModal } from './GitSetupModal';
import { RateLimitIndicator } from './RateLimitIndicator';
import { ClaudeCodeStatusBadge } from './ClaudeCodeStatusBadge';
import { useAuthFailureStore } from '../stores/auth-failure-store';
import { UpdateBanner } from './UpdateBanner';
import { SessionContextIndicator } from './SessionContextIndicator';
import { NavIndicator } from './NavIndicator';
import type { Project, AutoBuildVersionInfo, GitStatus, ProjectEnvConfig } from '../../shared/types';

export type SidebarView = 'kanban' | 'terminals' | 'roadmap' | 'context' | 'ideation' | 'webhooks' | 'github-issues' | 'gitlab-issues' | 'github-prs' | 'gitlab-merge-requests' | 'changelog' | 'insights' | 'worktrees' | 'agent-tools' | 'plugins' | 'analytics' | 'productivity' | 'merge-analytics' | 'sessions' | 'scheduler' | 'feedback' | 'patterns' | 'model-usage' | 'agent-inspector';

interface SidebarProps {
  onSettingsClick: () => void;
  onNewTaskClick: () => void;
  activeView?: SidebarView;
  onViewChange?: (view: SidebarView) => void;
}

interface NavItem {
  id: SidebarView;
  labelKey: string;
  icon: React.ElementType;
  shortcut?: string;
}

// Base nav items always shown
const baseNavItems: NavItem[] = [
  { id: 'kanban', labelKey: 'navigation:items.kanban', icon: LayoutGrid, shortcut: 'K' },
  { id: 'terminals', labelKey: 'navigation:items.terminals', icon: Terminal, shortcut: 'A' },
  { id: 'insights', labelKey: 'navigation:items.insights', icon: Sparkles, shortcut: 'N' },
  { id: 'roadmap', labelKey: 'navigation:items.roadmap', icon: MapIcon, shortcut: 'D' },
  { id: 'ideation', labelKey: 'navigation:items.ideation', icon: Lightbulb, shortcut: 'I' },
  { id: 'changelog', labelKey: 'navigation:items.changelog', icon: FileText, shortcut: 'L' },
  { id: 'scheduler', labelKey: 'navigation:items.scheduler', icon: Calendar, shortcut: 'S' },
  { id: 'context', labelKey: 'navigation:items.context', icon: BookOpen, shortcut: 'C' },
  { id: 'webhooks', labelKey: 'navigation:items.webhooks', icon: Webhook },
  { id: 'analytics', labelKey: 'navigation:items.analytics', icon: BarChart3, shortcut: 'Y' },
  { id: 'productivity', labelKey: 'navigation:items.productivity', icon: TrendingUp, shortcut: 'P' },
  { id: 'patterns', labelKey: 'navigation:items.patterns', icon: Code, shortcut: 'Z' },
  { id: 'agent-tools', labelKey: 'navigation:items.agentTools', icon: Wrench, shortcut: 'M' },
  { id: 'plugins', labelKey: 'navigation:items.plugins', icon: Puzzle, shortcut: 'U' },
  { id: 'worktrees', labelKey: 'navigation:items.worktrees', icon: GitBranch, shortcut: 'W' },
  { id: 'merge-analytics', labelKey: 'navigation:items.mergeAnalytics', icon: Activity, shortcut: 'T' },
  { id: 'sessions', labelKey: 'navigation:items.sessions', icon: Play },
  { id: 'agent-inspector', labelKey: 'navigation:items.agentInspector', icon: Brain },
  { id: 'feedback', labelKey: 'navigation:items.feedback', icon: MessageSquare, shortcut: 'F' },
  { id: 'model-usage', labelKey: 'navigation:items.modelUsage', icon: Database, shortcut: 'O' }
];

// GitHub nav items shown when GitHub is enabled
const githubNavItems: NavItem[] = [
  { id: 'github-issues', labelKey: 'navigation:items.githubIssues', icon: Github, shortcut: 'G' },
  { id: 'github-prs', labelKey: 'navigation:items.githubPRs', icon: GitPullRequest, shortcut: 'H' }
];

// GitLab nav items shown when GitLab is enabled
const gitlabNavItems: NavItem[] = [
  { id: 'gitlab-issues', labelKey: 'navigation:items.gitlabIssues', icon: GitlabIcon, shortcut: 'B' },
  { id: 'gitlab-merge-requests', labelKey: 'navigation:items.gitlabMRs', icon: GitMerge, shortcut: 'R' }
];

export function Sidebar({
  onSettingsClick,
  onNewTaskClick,
  activeView = 'kanban',
  onViewChange
}: SidebarProps) {
  const { t } = useTranslation(['navigation', 'dialogs', 'common']);
  const projects = useProjectStore(useShallow((state) => state.projects));
  const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
  const settings = useSettingsStore(useShallow((state) => state.settings));
  const hasPendingAuthFailure = useAuthFailureStore((state) => state.hasPendingAuthFailure);

  const [showAddProjectModal, setShowAddProjectModal] = useState(false);
  const [showInitDialog, setShowInitDialog] = useState(false);
  const [showGitSetupModal, setShowGitSetupModal] = useState(false);
  const [gitStatus, setGitStatus] = useState<GitStatus | null>(null);
  const [pendingProject, setPendingProject] = useState<Project | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const [envConfig, setEnvConfig] = useState<ProjectEnvConfig | null>(null);
  const [indicatorPosition, setIndicatorPosition] = useState<{
    top: number;
    height: number;
    opacity: number;
  }>({ top: 0, height: 0, opacity: 0 });

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  // Sidebar collapsed state from settings
  const isCollapsed = settings.sidebarCollapsed ?? false;

  // Refs for position tracking (used for animated indicator)
  const navContainerRef = useRef<HTMLDivElement>(null);
  const navItemRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  const toggleSidebar = () => {
    saveSettings({ sidebarCollapsed: !isCollapsed });
  };

  // Load env config when project changes to check GitHub/GitLab enabled state
  useEffect(() => {
    const loadEnvConfig = async () => {
      if (selectedProject?.autoBuildPath) {
        try {
          const result = await window.electronAPI.getProjectEnv(selectedProject.id);
          if (result.success && result.data) {
            setEnvConfig(result.data);
          } else {
            setEnvConfig(null);
          }
        } catch {
          setEnvConfig(null);
        }
      } else {
        setEnvConfig(null);
      }
    };
    loadEnvConfig();
  }, [selectedProject?.id, selectedProject?.autoBuildPath]);

  // Compute visible nav items based on GitHub/GitLab enabled state
  const visibleNavItems = useMemo(() => {
    const items = [...baseNavItems];

    if (envConfig?.githubEnabled) {
      items.push(...githubNavItems);
    }

    if (envConfig?.gitlabEnabled) {
      items.push(...gitlabNavItems);
    }

    return items;
  }, [envConfig?.githubEnabled, envConfig?.gitlabEnabled]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement ||
        (e.target as HTMLElement)?.isContentEditable
      ) {
        return;
      }

      // Only handle shortcuts when a project is selected
      if (!selectedProjectId) return;

      // Check for modifier keys - we want plain key presses only
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key.toUpperCase();

      // Find matching nav item from visible items only
      const matchedItem = visibleNavItems.find((item) => item.shortcut === key);

      if (matchedItem) {
        e.preventDefault();
        onViewChange?.(matchedItem.id);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedProjectId, onViewChange, visibleNavItems]);

  // Track position changes using ResizeObserver for smooth indicator animations
  useEffect(() => {
    const container = navContainerRef.current;
    const activeItem = navItemRefs.current.get(activeView);

    if (!container || !activeItem) {
      setIndicatorPosition((prev) => ({ ...prev, opacity: 0 }));
      return;
    }

    const updatePosition = () => {
      const containerEl = navContainerRef.current;
      const activeEl = navItemRefs.current.get(activeView);

      if (!containerEl || !activeEl) {
        setIndicatorPosition((prev) => ({ ...prev, opacity: 0 }));
        return;
      }

      const containerRect = containerEl.getBoundingClientRect();
      const itemRect = activeEl.getBoundingClientRect();

      const top = itemRect.top - containerRect.top;
      const height = itemRect.height;

      setIndicatorPosition({ top, height, opacity: 1 });
    };

    // Initial measurement
    updatePosition();

    const handleScroll = () => {
      requestAnimationFrame(updatePosition);
    };

    // Observe layout changes if ResizeObserver is available
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserverRef.current = new ResizeObserver(() => {
        requestAnimationFrame(updatePosition);
      });

      resizeObserverRef.current.observe(container);
      navItemRefs.current.forEach((item) => {
        resizeObserverRef.current?.observe(item);
      });
    }

    // Also update on scroll of the scrollable area
    container.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = null;
      container.removeEventListener('scroll', handleScroll);
    };
  }, [activeView, visibleNavItems, isCollapsed]);

  // Check git status when project changes
  useEffect(() => {
    const checkGit = async () => {
      if (selectedProject) {
        try {
          const result = await window.electronAPI.checkGitStatus(selectedProject.path);
          if (result.success && result.data) {
            setGitStatus(result.data);
            // Show git setup modal if project is not a git repo or has no commits
            if (!result.data.isGitRepo || !result.data.hasCommits) {
              setShowGitSetupModal(true);
            }
          }
        } catch (error) {
          console.error('Failed to check git status:', error);
        }
      } else {
        setGitStatus(null);
      }
    };
    checkGit();
  }, [selectedProject]);

  const handleProjectAdded = (project: Project, needsInit: boolean) => {
    if (needsInit) {
      setPendingProject(project);
      setShowInitDialog(true);
    }
  };

  const handleInitialize = async () => {
    if (!pendingProject) return;

    const projectId = pendingProject.id;
    setIsInitializing(true);
    try {
      const result = await initializeProject(projectId);
      if (result?.success) {
        // Clear pendingProject FIRST before closing dialog
        // This prevents onOpenChange from triggering skip logic
        setPendingProject(null);
        setShowInitDialog(false);
      }
    } finally {
      setIsInitializing(false);
    }
  };

  const handleSkipInit = () => {
    setShowInitDialog(false);
    setPendingProject(null);
  };

  const handleGitInitialized = async () => {
    // Refresh git status after initialization
    if (selectedProject) {
      try {
        const result = await window.electronAPI.checkGitStatus(selectedProject.path);
        if (result.success && result.data) {
          setGitStatus(result.data);
        }
      } catch (error) {
        console.error('Failed to refresh git status:', error);
      }
    }
  };

  const _handleRemoveProject = async (projectId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    await removeProject(projectId);
  };


  const handleNavClick = (view: SidebarView) => {
    onViewChange?.(view);
  };

  const renderNavItem = (item: NavItem) => {
    const isActive = activeView === item.id;
    const Icon = item.icon;

    const button = (
      <motion.button
        key={item.id}
        ref={(el) => {
          if (el) {
            navItemRefs.current.set(item.id, el);
          } else {
            navItemRefs.current.delete(item.id);
          }
        }}
        onClick={() => handleNavClick(item.id)}
        disabled={!selectedProjectId}
        aria-keyshortcuts={item.shortcut}
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -10 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className={cn(
          'flex w-full items-center rounded-lg text-sm transition-all duration-200',
          'hover:bg-accent hover:text-accent-foreground',
          'disabled:pointer-events-none disabled:opacity-50',
          isActive && 'bg-accent text-accent-foreground',
          isCollapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2.5'
        )}
      >
        <Icon className="h-4 w-4 shrink-0" />
        {!isCollapsed && (
          <>
            <span className="flex-1 text-left">{t(item.labelKey)}</span>
            {item.shortcut && (
              <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded-md border border-border bg-secondary px-1.5 font-mono text-[10px] font-medium text-muted-foreground sm:flex">
                {item.shortcut}
              </kbd>
            )}
          </>
        )}
      </motion.button>
    );

    // Wrap in tooltip when collapsed
    if (isCollapsed) {
      return (
        <Tooltip key={item.id}>
          <TooltipTrigger asChild>{button}</TooltipTrigger>
          <TooltipContent side="right">
            <span>{t(item.labelKey)}</span>
            {item.shortcut && (
              <kbd className="ml-2 rounded border border-border bg-secondary px-1 font-mono text-[10px]">
                {item.shortcut}
              </kbd>
            )}
          </TooltipContent>
        </Tooltip>
      );
    }

    return button;
  };

  return (
    <TooltipProvider>
      <div className={cn(
        "flex h-full flex-col bg-sidebar border-r border-border transition-all duration-300",
        isCollapsed ? "w-16" : "w-64"
      )}>
        {/* Header with drag area - extra top padding for macOS traffic lights */}
        <div className={cn(
          "electron-drag flex h-14 items-center pt-6 transition-all duration-300",
          isCollapsed ? "justify-center px-2" : "px-4"
        )}>
          {!isCollapsed && (
            <span className="electron-no-drag text-lg font-bold text-primary">Auto Code</span>
          )}
        </div>

        <Separator className="mt-2" />

        {/* Toggle button */}
        <div className={cn(
          "flex py-2 transition-all duration-300",
          isCollapsed ? "justify-center px-2" : "justify-end px-3"
        )}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={toggleSidebar}
                aria-label={isCollapsed ? t('actions.expandSidebar') : t('actions.collapseSidebar')}
              >
                {isCollapsed ? (
                  <PanelLeft className="h-4 w-4" />
                ) : (
                  <PanelLeftClose className="h-4 w-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              {isCollapsed ? t('actions.expandSidebar') : t('actions.collapseSidebar')}
            </TooltipContent>
          </Tooltip>
        </div>

        <Separator />

        {/* Navigation */}
        <ScrollArea className="flex-1">
          <div className={cn("py-4 transition-all duration-300", isCollapsed ? "px-2" : "px-3")}>
            {/* Project Section */}
            <div>
              {!isCollapsed && (
                <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {t('sections.project')}
                </h3>
              )}
              {/* relative wrapper starts here so NavIndicator top:0 aligns with nav top */}
              <div className="relative">
                {/* Animated indicator for active nav item */}
                {selectedProjectId && (
                  <NavIndicator
                    activeView={activeView}
                    containerRef={navContainerRef}
                    itemRefs={navItemRefs}
                    position={indicatorPosition}
                  />
                )}
                <nav ref={navContainerRef} className="space-y-1">
                  <AnimatePresence mode="popLayout">
                    {visibleNavItems.map((item) => renderNavItem(item))}
                  </AnimatePresence>
                </nav>
              </div>
            </div>
          </div>
        </ScrollArea>

        <Separator />

        {/* Rate Limit Indicator - shows when Claude is rate limited */}
        <RateLimitIndicator />

        {/* Update Banner - shows when app update is available */}
        <UpdateBanner />

        {/* Bottom section with Settings, Help, and New Task */}
        <div className={cn("space-y-3 transition-all duration-300", isCollapsed ? "p-2" : "p-4")}>
          {/* Claude Code Status Badge */}
          {!isCollapsed && <ClaudeCodeStatusBadge />}

          {/* Session Context Indicator */}
          {!isCollapsed && <SessionContextIndicator projectId={selectedProjectId ?? undefined} taskId={selectedProject?.autoBuildPath ?? undefined} />}

          {/* Settings and Help row */}
          <div className={cn(
            "flex items-center",
            isCollapsed ? "flex-col gap-1" : "gap-2"
          )}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size={isCollapsed ? "icon" : "sm"}
                  className={cn(isCollapsed ? "relative" : "relative flex-1 justify-start gap-2")}
                  onClick={onSettingsClick}
                  aria-label={isCollapsed ? t('actions.settings') : undefined}
                >
                  <Settings className="h-4 w-4" />
                  {!isCollapsed && t('actions.settings')}
                  {hasPendingAuthFailure && (
                    <span
                      className="absolute top-1 right-1 h-2 w-2 rounded-full bg-destructive"
                      aria-label={t('common:auth.failure.badgeTooltip')}
                    />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side={isCollapsed ? "right" : "top"}>
                {hasPendingAuthFailure
                  ? t('common:auth.failure.badgeTooltip')
                  : t('tooltips.settings')}
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => window.open('https://github.com/OBenner/Auto-Coding/issues', '_blank')}
                  aria-label={t('tooltips.help')}
                >
                  <HelpCircle className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side={isCollapsed ? "right" : "top"}>{t('tooltips.help')}</TooltipContent>
            </Tooltip>
          </div>

          {/* New Task button */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                className="w-full"
                size={isCollapsed ? "icon" : "default"}
                onClick={onNewTaskClick}
                disabled={!selectedProjectId || !selectedProject?.autoBuildPath}
              >
                <Plus className={isCollapsed ? "h-4 w-4" : "mr-2 h-4 w-4"} />
                {!isCollapsed && t('actions.newTask')}
              </Button>
            </TooltipTrigger>
            {isCollapsed && (
              <TooltipContent side="right">{t('actions.newTask')}</TooltipContent>
            )}
          </Tooltip>
          {!isCollapsed && selectedProject && !selectedProject.autoBuildPath && (
            <p className="mt-2 text-xs text-muted-foreground text-center">
              {t('messages.initializeToCreateTasks')}
            </p>
          )}
        </div>
      </div>

      {/* Initialize Auto Code Dialog */}
      <Dialog open={showInitDialog} onOpenChange={(open) => {
        // Only allow closing if user manually closes (not during initialization)
        if (!open && !isInitializing) {
          handleSkipInit();
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Download className="h-5 w-5" />
              {t('dialogs:initialize.title')}
            </DialogTitle>
            <DialogDescription>
              {t('dialogs:initialize.description')}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="rounded-lg bg-muted p-4 text-sm">
              <p className="font-medium mb-2">{t('dialogs:initialize.willDo')}</p>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                <li>{t('dialogs:initialize.createFolder')}</li>
                <li>{t('dialogs:initialize.copyFramework')}</li>
                <li>{t('dialogs:initialize.setupSpecs')}</li>
              </ul>
            </div>
            {!settings.autoBuildPath && (
              <div className="mt-4 rounded-lg border border-warning/50 bg-warning/10 p-4 text-sm">
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-warning mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-warning">{t('dialogs:initialize.sourcePathNotConfigured')}</p>
                    <p className="text-muted-foreground mt-1">
                      {t('dialogs:initialize.sourcePathNotConfiguredDescription')}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleSkipInit} disabled={isInitializing}>
              {t('common:buttons.skip')}
            </Button>
            <Button
              onClick={handleInitialize}
              disabled={isInitializing || !settings.autoBuildPath}
            >
              {isInitializing ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  {t('common:labels.initializing')}
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  {t('common:buttons.initialize')}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Project Modal */}
      <AddProjectModal
        open={showAddProjectModal}
        onOpenChange={setShowAddProjectModal}
        onProjectAdded={handleProjectAdded}
      />

      {/* Git Setup Modal */}
      <GitSetupModal
        open={showGitSetupModal}
        onOpenChange={setShowGitSetupModal}
        project={selectedProject || null}
        gitStatus={gitStatus}
        onGitInitialized={handleGitInitialized}
      />
    </TooltipProvider>
  );
}
