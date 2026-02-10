import { useEffect, useRef, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import { Clock, MemoryStick, Terminal, AlertCircle, X, Loader2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/alert-dialog';
import type { BackgroundTask, BackgroundTaskStatus } from '../../shared/types';

interface TaskProgressProps {
  taskId: string;
  onClose?: () => void;
}

/**
 * TaskProgress - Real-time output display for long-running background tasks
 *
 * Displays:
 * - Real-time command output via xterm.js terminal
 * - Task status badge (pending/running/completed/failed/cancelled)
 * - Task metadata (command, timeout, memory usage)
 * - Progress updates via IPC events
 *
 * Pattern: Follows Terminal.tsx for xterm initialization and output streaming
 */
export function TaskProgress({ taskId, onClose }: TaskProgressProps) {
  const { t } = useTranslation(['tasks', 'common']);

  // Refs for xterm terminal
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);

  // Task state
  const [task, setTask] = useState<BackgroundTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Cancel dialog state
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);

  // Track if component is mounted (prevent state updates after unmount)
  const isMountedRef = useRef(true);

  /**
   * Initialize xterm.js terminal for output display
   * Pattern: Follows useXterm.ts initialization
   */
  useEffect(() => {
    if (!terminalRef.current || xtermRef.current) return;

    const xterm = new XTerm({
      cursorBlink: false,
      cursorStyle: 'block',
      fontSize: 13,
      fontFamily: 'var(--font-mono), "JetBrains Mono", Menlo, Monaco, "Courier New", monospace',
      lineHeight: 1.2,
      letterSpacing: 0,
      theme: {
        background: '#0B0B0F',
        foreground: '#E8E6E3',
        cursor: '#D6D876',
        cursorAccent: '#0B0B0F',
        selectionBackground: '#D6D87640',
        selectionForeground: '#E8E6E3',
        black: '#1A1A1F',
        red: '#FF6B6B',
        green: '#87D687',
        yellow: '#D6D876',
        blue: '#6BB3FF',
        magenta: '#C792EA',
        cyan: '#89DDFF',
        white: '#E8E6E3',
        brightBlack: '#4A4A50',
        brightRed: '#FF8A8A',
        brightGreen: '#A5E6A5',
        brightYellow: '#E8E87A',
        brightBlue: '#8AC4FF',
        brightMagenta: '#DEB3FF',
        brightCyan: '#A6E8FF',
        brightWhite: '#FFFFFF',
      },
      allowProposedApi: true,
      scrollback: 10000,
      // Read-only terminal (no user input)
      disableStdin: true,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon((_event, uri) => {
      window.electronAPI?.openExternal?.(uri).catch((err) => {
        console.error('[TaskProgress] Failed to open URL:', uri, err);
      });
    });

    xterm.loadAddon(fitAddon);
    xterm.loadAddon(webLinksAddon);
    xterm.open(terminalRef.current);

    // Fit terminal to container
    setTimeout(() => {
      fitAddon.fit();
    }, 100);

    xtermRef.current = xterm;
    fitAddonRef.current = fitAddon;

    // Cleanup on unmount
    return () => {
      xterm.dispose();
      xtermRef.current = null;
      fitAddonRef.current = null;
    };
  }, []);

  /**
   * Fetch initial task status
   */
  const fetchTaskStatus = useCallback(async () => {
    try {
      const result = await window.electronAPI.backgroundTaskGetStatus(taskId);
      if (result.success && result.data && isMountedRef.current) {
        setTask(result.data);
        setLoading(false);

        // Display existing output in terminal
        if (xtermRef.current && result.data.output) {
          xtermRef.current.clear();
          xtermRef.current.write(result.data.output);
        }
      } else if (isMountedRef.current) {
        setError(result.error || 'Failed to fetch task status');
        setLoading(false);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      }
    }
  }, [taskId]);

  /**
   * Handle real-time progress updates via IPC
   */
  useEffect(() => {
    const handleProgress = (progressTaskId: string, output: string) => {
      if (progressTaskId === taskId && xtermRef.current && isMountedRef.current) {
        xtermRef.current.write(output);
        // Update task state with new output
        setTask((prev: BackgroundTask | null) => prev ? { ...prev, output: prev.output + output } : null);
      }
    };

    const handleComplete = async (completeTaskId: string) => {
      if (completeTaskId === taskId && isMountedRef.current) {
        // Refresh task status to get final state
        await fetchTaskStatus();
      }
    };

    const handleError = (errorTaskId: string, errorMessage: string) => {
      if (errorTaskId === taskId && isMountedRef.current) {
        setError(errorMessage);
        // Refresh task status
        fetchTaskStatus();
      }
    };

    // Register IPC event listeners
    window.electronAPI.onBackgroundTaskProgress?.(handleProgress);
    window.electronAPI.onBackgroundTaskComplete?.(handleComplete);
    window.electronAPI.onBackgroundTaskError?.(handleError);

    // Initial fetch
    fetchTaskStatus();

    return () => {
      isMountedRef.current = false;
      // Cleanup listeners (if API provides unregister methods)
      // Note: Electron API may need to provide cleanup methods
    };
  }, [taskId, fetchTaskStatus]);

  /**
   * Handle window resize - refit terminal
   */
  useEffect(() => {
    const handleResize = () => {
      if (fitAddonRef.current) {
        setTimeout(() => {
          fitAddonRef.current?.fit();
        }, 100);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  /**
   * Get status badge color
   */
  const getStatusBadgeColor = (status: BackgroundTaskStatus): string => {
    switch (status) {
      case 'running':
        return 'bg-blue-500/10 text-blue-500';
      case 'completed':
        return 'bg-green-500/10 text-green-500';
      case 'failed':
        return 'bg-red-500/10 text-red-500';
      case 'cancelled':
        return 'bg-yellow-500/10 text-yellow-500';
      case 'pending':
      default:
        return 'bg-gray-500/10 text-gray-500';
    }
  };

  /**
   * Get status label
   */
  const getStatusLabel = (status: BackgroundTaskStatus): string => {
    switch (status) {
      case 'running':
        return t('tasks:labels.running');
      case 'completed':
        return t('tasks:status.complete');
      case 'failed':
        return 'Failed';
      case 'cancelled':
        return 'Cancelled';
      case 'pending':
      default:
        return t('tasks:labels.pending');
    }
  };

  /**
   * Format duration in human-readable format
   */
  const formatDuration = (startedAt: string | null, completedAt: string | null): string => {
    if (!startedAt) return '--';

    const start = new Date(startedAt).getTime();
    const end = completedAt ? new Date(completedAt).getTime() : Date.now();
    const durationMs = end - start;

    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  /**
   * Format memory usage
   */
  const formatMemory = (mb: number): string => {
    if (mb >= 1024) {
      return `${(mb / 1024).toFixed(2)} GB`;
    }
    return `${mb.toFixed(2)} MB`;
  };

  /**
   * Handle task cancellation
   */
  const handleCancel = async () => {
    if (!task || isCancelling) return;

    setIsCancelling(true);

    try {
      const result = await window.electronAPI.backgroundTaskCancel(taskId);
      if (result.success) {
        // Refresh task status to show cancelled state
        await fetchTaskStatus();
      } else {
        setError(result.error || 'Failed to cancel task');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      if (isMountedRef.current) {
        setIsCancelling(false);
        setShowCancelDialog(false);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-sm text-muted-foreground">{t('common:loading')}...</div>
      </div>
    );
  }

  if (error && !task) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2">
        <AlertCircle className="w-8 h-8 text-destructive" />
        <div className="text-sm text-destructive">{error}</div>
        {onClose && (
          <button
            onClick={onClose}
            className="mt-4 px-4 py-2 text-sm bg-secondary hover:bg-secondary/80 rounded"
          >
            {t('common:close')}
          </button>
        )}
      </div>
    );
  }

  if (!task) {
    return null;
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header with status and metadata */}
      <div className="flex-shrink-0 border-b border-border p-4 space-y-3">
        {/* Status Badge and Command */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Terminal className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              <code className="text-sm font-mono text-foreground truncate">
                {task.command}
              </code>
            </div>
            <div className="text-xs text-muted-foreground truncate">
              {task.workingDir}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={`px-2 py-0.5 text-xs rounded-full ${getStatusBadgeColor(task.status)}`}>
              {getStatusLabel(task.status)}
            </span>
            {/* Cancel button - only show for running tasks */}
            {task.status === 'running' && (
              <button
                onClick={() => setShowCancelDialog(true)}
                disabled={isCancelling}
                className="p-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded transition-colors"
                title={t('common:buttons.cancel')}
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          {/* Duration */}
          <div className="flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Duration:</span>
            <span className="text-foreground font-medium">
              {formatDuration(task.startedAt, task.completedAt)}
            </span>
          </div>

          {/* Memory Usage */}
          {task.memoryStats && (
            <div className="flex items-center gap-2">
              <MemoryStick className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">Memory:</span>
              <span className="text-foreground font-medium">
                {task.memoryStats.percent.toFixed(1)}% ({formatMemory(task.memoryStats.usedMb)})
              </span>
            </div>
          )}

          {/* Exit Code (if completed/failed) */}
          {task.exitCode !== null && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Exit Code:</span>
              <span className={`font-medium ${task.exitCode === 0 ? 'text-green-500' : 'text-red-500'}`}>
                {task.exitCode}
              </span>
            </div>
          )}

          {/* Timeout */}
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Timeout:</span>
            <span className="text-foreground font-medium">
              {task.timeout >= 3600 ? `${(task.timeout / 3600).toFixed(1)}h` : `${task.timeout}s`}
            </span>
          </div>
        </div>

        {/* Error Message */}
        {task.error && (
          <div className="flex items-start gap-2 p-2 bg-destructive/10 border border-destructive/20 rounded">
            <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
            <div className="text-xs text-destructive">{task.error}</div>
          </div>
        )}
      </div>

      {/* Terminal Output */}
      <div className="flex-1 min-h-0 relative">
        <div
          ref={terminalRef}
          className="absolute inset-0 w-full h-full"
          data-testid="task-progress-terminal"
        />
      </div>

      {/* Cancel Confirmation Dialog */}
      <AlertDialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <X className="h-5 w-5 text-destructive" />
              Cancel Task
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="text-sm text-muted-foreground space-y-3">
                <p>
                  Are you sure you want to cancel this running task?
                </p>
                <p className="text-destructive">
                  This will terminate the process immediately. Any unsaved progress will be lost.
                </p>
                <div className="bg-muted/50 rounded-lg p-3 text-sm">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <Terminal className="w-3.5 h-3.5 text-muted-foreground" />
                      <code className="text-xs font-mono text-foreground">
                        {task.command}
                      </code>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Duration: {formatDuration(task.startedAt, task.completedAt)}
                    </div>
                  </div>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isCancelling}>
              {t('common:buttons.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                handleCancel();
              }}
              disabled={isCancelling}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isCancelling ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Cancelling...
                </>
              ) : (
                <>
                  <X className="mr-2 h-4 w-4" />
                  Cancel Task
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
