/**
 * CollaborativeSpecEditor - Real-time collaborative markdown editor for specs
 *
 * Provides a collaborative editing experience for spec.md files with:
 * - WebSocket-based real-time synchronization
 * - Presence indicators for active users
 * - Markdown syntax highlighting
 * - Connection status display
 * - Auto-save with debouncing
 *
 * Features:
 * - Connects to WebSocket server on mount
 * - Sends content updates via CRDT merge
 * - Receives real-time updates from other users
 * - Shows presence of other users viewing/editing
 * - Displays connection status with visual feedback
 *
 * @example
 * ```tsx
 * <CollaborativeSpecEditor
 *   specId="143-collaborative-spec-editing-review"
 *   initialContent="# Spec Content"
 *   onContentChange={(content) => console.log('Content changed:', content)}
 * />
 * ```
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FileCode,
  Loader2,
  Wifi,
  WifiOff,
  AlertCircle,
  Users,
} from 'lucide-react';
import CodeMirror from '@uiw/react-codemirror';
import { markdown } from '@codemirror/lang-markdown';
import { useCollaborationStore } from '../../stores/collaboration-store';
import { createCollaborationAPI } from '../../../preload/api/collaboration-api';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';

/**
 * Props for the CollaborativeSpecEditor component
 */
interface CollaborativeSpecEditorProps {
  /** Unique identifier for the spec (e.g., "143-collaborative-spec-editing-review") */
  specId: string;
  /** Initial markdown content */
  initialContent: string;
  /** Callback when content changes */
  onContentChange?: (content: string) => void;
  /** Whether the editor is read-only */
  readOnly?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Debounce delay for content updates (ms)
 * Reduces WebSocket traffic during active typing
 */
const CONTENT_UPDATE_DEBOUNCE_MS = 500;

/**
 * Presence update interval (ms)
 * Frequency of broadcasting user presence
 */
const PRESENCE_UPDATE_INTERVAL_MS = 30000;

export function CollaborativeSpecEditor({
  specId,
  initialContent,
  onContentChange,
  readOnly = false,
  className,
}: CollaborativeSpecEditorProps) {
  const { t } = useTranslation(['collaboration', 'common']);

  // Collaboration store state
  const connectionState = useCollaborationStore((state) => state.connectionState);
  const currentSpecId = useCollaborationStore((state) => state.currentSpecId);
  const error = useCollaborationStore((state) => state.error);
  const presences = useCollaborationStore((state) => state.getPresences(specId));
  const setContent = useCollaborationStore((state) => state.setCurrentSpec);
  const setError = useCollaborationStore((state) => state.setError);
  const setLoading = useCollaborationStore((state) => state.setLoading);
  const setConnectionState = useCollaborationStore((state) => state.setConnectionState);

  // Local component state
  const [content, setContentState] = useState(initialContent);
  const [isConnecting, setIsConnecting] = useState(false);
  const [activeUsers, setActiveUsers] = useState(0);

  // Refs for timers and API
  const collaborationAPI = useMemo(() => createCollaborationAPI(), []);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const presenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const currentUserIdRef = useRef<string>('user-' + Math.random().toString(36).substr(2, 9));

  // Detect dark mode from DOM
  const isDarkMode = useMemo(() => {
    if (typeof document !== 'undefined') {
      return document.documentElement.classList.contains('dark');
    }
    return false;
  }, []);

  /**
   * Connect to WebSocket server for real-time collaboration
   */
  const connectToCollaborationServer = useCallback(async () => {
    if (isConnecting || connectionState === 'connected') {
      return;
    }

    setIsConnecting(true);
    setLoading(true);
    setError(null);

    try {
      const result = await collaborationAPI.connect(specId);

      if (result.success && result.data?.connected) {
        setConnectionState('connected');
        setContent(specId);
        // Load initial collaboration state
        await loadCollaborationState();
      } else {
        setConnectionState('error');
        setError(result.error || t('collaboration:errors.connectionFailed'));
      }
    } catch (err) {
      setConnectionState('error');
      setError(err instanceof Error ? err.message : t('collaboration:errors.unknown'));
    } finally {
      setIsConnecting(false);
      setLoading(false);
    }
  }, [
    specId,
    isConnecting,
    connectionState,
    collaborationAPI,
    setConnectionState,
    setContent,
    setLoading,
    setError,
    t,
  ]);

  /**
   * Load collaboration state (comments, suggestions, presence, versions)
   */
  const loadCollaborationState = useCallback(async () => {
    try {
      const stateResult = await collaborationAPI.getState(specId);
      if (stateResult.success && stateResult.data) {
        const state = stateResult.data;
        // Store will be populated by IPC events
        // Presence count is updated from the store
      }
    } catch (err) {
      // Non-fatal: log but don't show error to user
      console.error('[CollaborativeSpecEditor] Failed to load state:', err);
    }
  }, [specId, collaborationAPI]);

  /**
   * Disconnect from WebSocket server
   */
  const disconnectFromServer = useCallback(async () => {
    try {
      await collaborationAPI.disconnect(specId);
      setConnectionState('disconnected');
      setContent(null);
    } catch (err) {
      console.error('[CollaborativeSpecEditor] Disconnect error:', err);
    }
  }, [specId, collaborationAPI, setConnectionState, setContent]);

  /**
   * Send content update via WebSocket (debounced)
   */
  const sendContentUpdate = useCallback(
    (newContent: string) => {
      // Clear existing timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Set new timer
      debounceTimerRef.current = setTimeout(async () => {
        try {
          await collaborationAPI.updateContent(specId, newContent);
        } catch (err) {
          console.error('[CollaborativeSpecEditor] Failed to send content update:', err);
        }
      }, CONTENT_UPDATE_DEBOUNCE_MS);
    },
    [specId, collaborationAPI]
  );

  /**
   * Send presence update
   */
  const sendPresenceUpdate = useCallback(
    async (presenceType: 'viewing' | 'editing' | 'idle', cursorPosition: number | null) => {
      try {
        await collaborationAPI.updatePresence(
          specId,
          currentUserIdRef.current,
          'Current User', // TODO: Get from auth/user store
          presenceType,
          null, // section_id - can be enhanced to track current section
          cursorPosition
        );
      } catch (err) {
        console.error('[CollaborativeSpecEditor] Failed to send presence update:', err);
      }
    },
    [specId, collaborationAPI]
  );

  /**
   * Handle content change in editor
   */
  const handleContentChange = useCallback(
    (value: string) => {
      setContentState(value);
      onContentChange?.(value);

      // Send update to server (debounced)
      sendContentUpdate(value);

      // Mark as editing presence
      sendPresenceUpdate('editing', null);
    },
    [onContentChange, sendContentUpdate, sendPresenceUpdate]
  );

  /**
   * Handle manual reconnect
   */
  const handleReconnect = useCallback(() => {
    connectToCollaborationServer();
  }, [connectToCollaborationServer]);

  // Connect to server on mount
  useEffect(() => {
    connectToCollaborationServer();

    return () => {
      // Cleanup: disconnect on unmount
      disconnectFromServer();
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      if (presenceTimerRef.current) {
        clearInterval(presenceTimerRef.current);
      }
    };
  }, [connectToCollaborationServer, disconnectFromServer]);

  // Update active users count when presence changes
  useEffect(() => {
    // Filter out current user and idle users
    const activePresences = presences.filter(
      (p) => p.user_id !== currentUserIdRef.current && p.presence_type !== 'idle'
    );
    setActiveUsers(activePresences.length);
  }, [presences]);

  // Set up periodic presence updates
  useEffect(() => {
    if (connectionState !== 'connected') {
      return;
    }

    // Send initial presence
    sendPresenceUpdate('viewing', null);

    // Set up interval for periodic updates
    presenceTimerRef.current = setInterval(() => {
      sendPresenceUpdate('viewing', null);
    }, PRESENCE_UPDATE_INTERVAL_MS);

    return () => {
      if (presenceTimerRef.current) {
        clearInterval(presenceTimerRef.current);
      }
    };
  }, [connectionState, sendPresenceUpdate]);

  // Connection status badge component
  const ConnectionStatus = () => {
    switch (connectionState) {
      case 'connected':
        return (
          <Badge variant="outline" className="gap-1.5 border-green-500/50 text-green-500">
            <Wifi className="h-3 w-3" aria-hidden="true" />
            {t('collaboration:status.connected')}
          </Badge>
        );
      case 'connecting':
        return (
          <Badge variant="outline" className="gap-1.5 border-yellow-500/50 text-yellow-500">
            <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
            {t('collaboration:status.connecting')}
          </Badge>
        );
      case 'disconnected':
        return (
          <Badge variant="outline" className="gap-1.5 border-muted-foreground/50 text-muted-foreground">
            <WifiOff className="h-3 w-3" aria-hidden="true" />
            {t('collaboration:status.disconnected')}
          </Badge>
        );
      case 'error':
        return (
          <Badge variant="outline" className="gap-1.5 border-destructive/50 text-destructive">
            <AlertCircle className="h-3 w-3" aria-hidden="true" />
            {t('collaboration:status.error')}
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <FileCode className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">{t('collaboration:title')}</h2>
        </div>

        <div className="flex items-center gap-3">
          {/* Active users */}
          {activeUsers > 0 && (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Users className="h-4 w-4" aria-hidden="true" />
              <span>{activeUsers}</span>
            </div>
          )}

          {/* Connection status */}
          <ConnectionStatus />

          {/* Reconnect button (only show when disconnected/error) */}
          {connectionState === 'disconnected' || connectionState === 'error' ? (
            <Button variant="outline" size="sm" onClick={handleReconnect}>
              {t('collaboration:actions.reconnect')}
            </Button>
          ) : null}
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="px-4 py-2 bg-destructive/10 border-b border-destructive/20 flex items-center gap-2 shrink-0">
          <AlertCircle className="h-4 w-4 text-destructive shrink-0" />
          <p className="text-sm text-destructive flex-1">{error}</p>
        </div>
      )}

      {/* Editor */}
      <div className="flex-1 min-h-0 overflow-auto">
        {isConnecting ? (
          <div className="flex flex-col items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-primary mb-2" />
            <p className="text-sm text-muted-foreground">
              {t('collaboration:connecting')}
            </p>
          </div>
        ) : (
          <div className="h-full">
            <CodeMirror
              value={content}
              height="100%"
              extensions={[markdown()]}
              onChange={handleContentChange}
              readOnly={readOnly}
              theme={isDarkMode ? 'dark' : 'light'}
              className="text-sm"
            />
          </div>
        )}
      </div>

      {/* Footer with stats */}
      <div className="px-4 py-2 border-t border-border bg-card/50 shrink-0">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{specId}</span>
          <span>
            {content.length} {t('collaboration:characters')}
          </span>
        </div>
      </div>
    </div>
  );
}
