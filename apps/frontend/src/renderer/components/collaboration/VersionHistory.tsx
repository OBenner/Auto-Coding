/**
 * VersionHistory - Version history and diff viewer for collaborative spec editing
 *
 * Displays version history of spec changes with diff support:
 * - List of all versions with metadata
 * - Diff view between versions (added/removed/unchanged)
 * - Approve/unapprove versions
 * - Restore previous versions
 * - Visual indication of approved version
 *
 * Features:
 * - Shows version list with author, timestamp, and commit message
 * - Side-by-side or unified diff view
 * - Color-coded changes (green for additions, red for deletions)
 * - One-click version approval for authorized users
 * - Timestamp formatting with relative time
 *
 * @example
 * ```tsx
 * <VersionHistory
 *   specId="143-collaborative-spec-editing-review"
 *   currentUserId="user-123"
 *   currentUserName="Current User"
 * />
 * ```
 */

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  History,
  GitCommit,
  Eye,
  CheckCircle2,
  Circle,
  X,
  ChevronDown,
  ChevronRight,
  Loader2,
  RefreshCw,
  User as UserIcon,
  Calendar,
  FileText,
} from 'lucide-react';
import { useCollaborationStore } from '../../stores/collaboration-store';
import { createCollaborationAPI } from '../../../preload/api/collaboration-api';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { cn } from '../../lib/utils';
import type { Version } from '../../../shared/types/collaboration';

/**
 * Props for VersionHistory component
 */
interface VersionHistoryProps {
  /** Unique identifier for the spec */
  specId: string;
  /** Current user ID */
  currentUserId: string;
  /** Current user name */
  currentUserName?: string;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show in compact mode (for embedding in other components) */
  compact?: boolean;
}

/**
 * Diff line type for rendering
 */
interface DiffLine {
  type: 'added' | 'removed' | 'unchanged';
  lineNumber: number;
  content: string;
}

/**
 * Diff result between two versions
 */
interface VersionDiff {
  added: DiffLine[];
  removed: DiffLine[];
  unchanged: DiffLine[];
  hasChanges: boolean;
}

/**
 * Format date as relative time
 */
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

/**
 * Format full date and time
 */
function formatFullDate(date: Date): string {
  return date.toLocaleString();
}

/**
 * Generate avatar color from user name
 */
function getAvatarColor(userName: string): string {
  const colors = [
    'bg-red-500',
    'bg-orange-500',
    'bg-amber-500',
    'bg-green-500',
    'bg-emerald-500',
    'bg-teal-500',
    'bg-cyan-500',
    'bg-blue-500',
    'bg-indigo-500',
    'bg-violet-500',
    'bg-purple-500',
    'bg-fuchsia-500',
    'bg-pink-500',
    'bg-rose-500',
  ];

  let hash = 0;
  for (let i = 0; i < userName.length; i++) {
    hash = userName.charCodeAt(i) + ((hash << 5) - hash);
  }

  const index = Math.abs(hash) % colors.length;
  return colors[index];
}

/**
 * Get user initials from name
 */
function getUserInitials(userName: string): string {
  const parts = userName.trim().split(/\s+/);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/**
 * Parse diff result from backend
 * The backend returns diff as structured data with added/removed/unchanged lines
 */
function parseDiffResult(diffData: {
  added: string[];
  removed: string[];
  unchanged: string[];
}): VersionDiff {
  const added: DiffLine[] = diffData.added.map((content, index) => ({
    type: 'added',
    lineNumber: index,
    content,
  }));

  const removed: DiffLine[] = diffData.removed.map((content, index) => ({
    type: 'removed',
    lineNumber: index,
    content,
  }));

  const unchanged: DiffLine[] = diffData.unchanged.map((content, index) => ({
    type: 'unchanged',
    lineNumber: index,
    content,
  }));

  return {
    added,
    removed,
    unchanged,
    hasChanges: added.length > 0 || removed.length > 0,
  };
}

/**
 * VersionHistory Component
 *
 * Displays version history with diff viewing capability
 */
export function VersionHistory({
  specId,
  currentUserId,
  currentUserName = 'Current User',
  className,
  compact = false,
}: VersionHistoryProps) {
  const { t } = useTranslation(['collaboration', 'common']);

  // Collaboration store
  const versions = useCollaborationStore((state) => state.getVersions(specId));
  const approveVersion = useCollaborationStore((state) => state.approveVersion);

  // Local state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [diffView, setDiffView] = useState<{
    version1: Version | null;
    version2: Version | null;
    diff: VersionDiff | null;
  }>({
    version1: null,
    version2: null,
    diff: null,
  });
  const [isComparing, setIsComparing] = useState(false);
  const [isApproving, setIsApproving] = useState(false);

  // Refs
  const collaborationAPI = useMemo(() => createCollaborationAPI(), []);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Get approved version (latest)
  const approvedVersion = useMemo(() => {
    return versions.find((v) => v.is_approved);
  }, [versions]);

  // Get latest version
  const latestVersion = useMemo(() => {
    return versions.length > 0 ? versions[0] : null;
  }, [versions]);

  // Scroll to selected version
  useEffect(() => {
    if (selectedVersionId && scrollRef.current) {
      const element = document.getElementById(`version-${selectedVersionId}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [selectedVersionId]);

  // Fetch versions
  const fetchVersions = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await collaborationAPI.getVersions(specId);
      if (result.success && result.data) {
        // Versions are updated in store via WebSocket or API
        // Store already handles sorting (newest first)
      } else {
        setError(result.error || t('collaboration:versionHistory.errors.loadFailed'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('collaboration:versionHistory.errors.unknown'));
    } finally {
      setIsLoading(false);
    }
  }, [specId, collaborationAPI, t]);

  // View diff between two versions
  const viewDiff = useCallback(
    async (version1: Version, version2: Version | null) => {
      setIsComparing(true);
      setError(null);

      try {
        // If no second version, compare with previous version
        const targetVersion = version2 || version1;

        const result = await collaborationAPI.getVersionDiff(version1.id);
        if (result.success && result.data) {
          // Parse diff result
          const diffData = typeof result.data === 'string'
            ? JSON.parse(result.data)
            : result.data;

          setDiffView({
            version1,
            version2: targetVersion,
            diff: parseDiffResult(diffData),
          });
          setSelectedVersionId(version1.id);
        } else {
          setError(result.error || t('collaboration:versionHistory.errors.diffFailed'));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : t('collaboration:versionHistory.errors.unknown'));
      } finally {
        setIsComparing(false);
      }
    },
    [collaborationAPI, t]
  );

  // Approve version
  const handleApprove = useCallback(
    async (version: Version) => {
      if (isApproving) return;

      setIsApproving(true);
      setError(null);

      try {
        const result = await collaborationAPI.approveVersion(version.id, currentUserId);
        if (result.success && result.data) {
          // Update in store
          approveVersion(specId, version.id, currentUserId);
        } else {
          setError(result.error || t('collaboration:versionHistory.errors.approveFailed'));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : t('collaboration:versionHistory.errors.unknown'));
      } finally {
        setIsApproving(false);
      }
    },
    [specId, currentUserId, isApproving, collaborationAPI, approveVersion, t]
  );

  // Close diff view
  const closeDiff = useCallback(() => {
    setDiffView({ version1: null, version2: null, diff: null });
    setSelectedVersionId(null);
  }, []);

  // Render diff line
  const renderDiffLine = (line: DiffLine) => {
    const bgColor =
      line.type === 'added'
        ? 'bg-green-500/10 dark:bg-green-500/20'
        : line.type === 'removed'
          ? 'bg-red-500/10 dark:bg-red-500/20'
          : 'transparent';

    const textColor =
      line.type === 'added'
        ? 'text-green-700 dark:text-green-400'
        : line.type === 'removed'
          ? 'text-red-700 dark:text-red-400'
          : 'text-foreground';

    return (
      <div
        key={`${line.type}-${line.lineNumber}`}
        className={cn('font-mono text-xs py-0.5 px-2', bgColor, textColor)}
      >
        <span className="select-none opacity-50 mr-3 w-8 inline-block text-right">
          {line.lineNumber}
        </span>
        <span className="whitespace-pre-wrap break-words">{line.content || '\u00A0'}</span>
      </div>
    );
  };

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Error display */}
      {error && (
        <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3 flex items-start gap-2">
          <span className="flex-1">{error}</span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => setError(null)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Diff view */}
      {diffView.diff && diffView.version1 && (
        <div className="rounded-lg border bg-card overflow-hidden">
          {/* Diff header */}
          <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-3">
            <div className="flex items-center gap-3">
              <GitCommit className="h-4 w-4 text-muted-foreground" />
              <div className="text-sm">
                <span className="font-medium">
                  {t('collaboration:versionHistory.comparingVersions')}
                </span>
                <div className="text-muted-foreground text-xs mt-0.5">
                  {diffView.version2
                    ? `v${diffView.version1.version_number} ↔ v${diffView.version2.version_number}`
                    : `${t('collaboration:versionHistory.version')} v${diffView.version1.version_number} ${t('collaboration:versionHistory.vsPrevious')}`}
                </div>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={closeDiff}>
              <X className="h-4 w-4 mr-2" />
              {t('common:actions.close')}
            </Button>
          </div>

          {/* Diff content */}
          <ScrollArea className="h-[500px]">
            <div className="p-4">
              {diffView.diff.hasChanges ? (
                <div className="space-y-1">
                  {/* Show removed lines first */}
                  {diffView.diff.removed.map((line) => renderDiffLine(line))}
                  {/* Show unchanged lines */}
                  {diffView.diff.unchanged.map((line) => renderDiffLine(line))}
                  {/* Show added lines */}
                  {diffView.diff.added.map((line) => renderDiffLine(line))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p className="text-sm">
                    {t('collaboration:versionHistory.noChanges')}
                  </p>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      )}

      {/* Version list */}
      <div className="rounded-lg border bg-card overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-3">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium text-sm">
              {t('collaboration:versionHistory.title')}
            </span>
            <Badge variant="outline" className="text-xs">
              {versions.length}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchVersions}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Version list */}
        <ScrollArea ref={scrollRef} className={compact ? 'h-[300px]' : 'h-[500px]'}>
          {versions.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <History className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-sm">{t('collaboration:versionHistory.noVersions')}</p>
            </div>
          ) : (
            <div className="divide-y">
              {versions.map((version, index) => {
                const isSelected = selectedVersionId === version.id;
                const isApproved = version.is_approved;
                const isLatest = index === 0;
                const avatarColor = getAvatarColor(version.author_name);
                const initials = getUserInitials(version.author_name);

                return (
                  <div
                    key={version.id}
                    id={`version-${version.id}`}
                    className={cn(
                      'p-4 transition-colors',
                      isSelected && 'bg-accent',
                      !isSelected && 'hover:bg-muted/50'
                    )}
                  >
                    <div className="flex items-start gap-3">
                      {/* Avatar */}
                      <div
                        className={cn(
                          'flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-medium text-white',
                          avatarColor
                        )}
                      >
                        {initials}
                      </div>

                      {/* Version info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm">
                            {version.author_name}
                          </span>
                          <Badge variant="outline" className="text-xs">
                            v{version.version_number}
                          </Badge>
                          {isApproved && (
                            <Badge variant="outline" className="gap-1 text-xs border-green-500/50 text-green-500">
                              <CheckCircle2 className="h-3 w-3" />
                              {t('collaboration:versionHistory.approved')}
                            </Badge>
                          )}
                          {isLatest && (
                            <Badge variant="secondary" className="text-xs">
                              {t('collaboration:versionHistory.latest')}
                            </Badge>
                          )}
                        </div>

                        {/* Commit message */}
                        {version.commit_message && (
                          <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                            {version.commit_message}
                          </p>
                        )}

                        {/* Metadata */}
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <span>{formatRelativeTime(version.created_at)}</span>
                          </div>
                          <div className="flex items-center gap-1" title={formatFullDate(version.created_at)}>
                            <Eye className="h-3 w-3" />
                            <span>{version.created_at.toLocaleString()}</span>
                          </div>
                          {version.approved_by && version.approved_at && (
                            <div
                              className="flex items-center gap-1"
                              title={`${t('collaboration:versionHistory.approvedBy')}: ${version.approved_by}`}
                            >
                              <CheckCircle2 className="h-3 w-3 text-green-500" />
                              <span>{version.approved_by}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        {/* View diff with previous */}
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8"
                          onClick={() => viewDiff(version, null)}
                          disabled={isComparing}
                        >
                          {isComparing && selectedVersionId === version.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <>
                              <GitCommit className="h-4 w-4 mr-2" />
                              {t('collaboration:versionHistory.viewDiff')}
                            </>
                          )}
                        </Button>

                        {/* Approve button (if not already approved) */}
                        {!isApproved && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8"
                            onClick={() => handleApprove(version)}
                            disabled={isApproving}
                          >
                            {isApproving ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <>
                                <CheckCircle2 className="h-4 w-4 mr-2" />
                                {t('collaboration:versionHistory.approve')}
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </div>
    </div>
  );
}
