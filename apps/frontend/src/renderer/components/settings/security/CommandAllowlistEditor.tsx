/**
 * CommandAllowlistEditor - Visual editor for command allowlist
 *
 * Allows users to view, add, remove, and toggle commands in the security
 * allowlist. Commands can be allowed or blocked, with optional labels for grouping.
 *
 * Features:
 * - Toggle commands as allowed/blocked
 * - Add custom commands to allowlist
 * - Remove commands from allowlist
 * - View command metadata (label, added date)
 * - Filter by status (all, allowed, blocked)
 */
import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Terminal,
  Plus,
  Trash2,
  Search,
  AlertCircle,
  Info,
  Check,
  X,
  Clock,
  Tag
} from 'lucide-react';
import { cn } from '../../../lib/utils';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Checkbox } from '../../ui/checkbox';
import { Label } from '../../ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '../../ui/dialog';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '../../ui/tooltip';
import type { CommandAllowlistEntry } from '../../../../shared/types';

interface CommandAllowlistEditorProps {
  /** Current allowlist entries */
  allowlist: CommandAllowlistEntry[];
  /** Callback when allowlist changes */
  onChange: (allowlist: CommandAllowlistEntry[]) => void;
  /** Whether changes are being saved */
  isLoading?: boolean;
  /** Whether the component is read-only */
  readOnly?: boolean;
}

/**
 * Filter options for command list
 */
type FilterType = 'all' | 'allowed' | 'blocked';

/**
 * CommandAllowlistEditor Component
 */
export function CommandAllowlistEditor({
  allowlist,
  onChange,
  isLoading = false,
  readOnly = false
}: CommandAllowlistEditorProps) {
  const { t } = useTranslation('security');
  const { t: tCommon } = useTranslation('common');

  // State for filters and search
  const [filter, setFilter] = useState<FilterType>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // State for add command dialog
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [newCommand, setNewCommand] = useState('');
  const [newCommandLabel, setNewCommandLabel] = useState('');
  const [newCommandAllowed, setNewCommandAllowed] = useState(true);

  // State for command to remove (for confirmation)
  const [commandToRemove, setCommandToRemove] = useState<string | null>(null);

  /**
   * Filter and search commands
   */
  const filteredCommands = useMemo(() => {
    return allowlist.filter((entry) => {
      // Apply status filter
      if (filter === 'allowed' && !entry.allowed) return false;
      if (filter === 'blocked' && entry.allowed) return false;

      // Apply search query
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          entry.command.toLowerCase().includes(query) ||
          entry.label?.toLowerCase().includes(query)
        );
      }

      return true;
    });
  }, [allowlist, filter, searchQuery]);

  /**
   * Get statistics about the allowlist
   */
  const stats = useMemo(() => {
    const total = allowlist.length;
    const allowed = allowlist.filter((c) => c.allowed).length;
    const blocked = total - allowed;
    return { total, allowed, blocked };
  }, [allowlist]);

  /**
   * Toggle command allowed/blocked status
   */
  const handleToggleCommand = useCallback((command: string, checked: boolean) => {
    if (readOnly || isLoading) return;

    const updatedAllowlist = allowlist.map((entry) =>
      entry.command === command ? { ...entry, allowed: checked } : entry
    );
    onChange(updatedAllowlist);
  }, [allowlist, onChange, readOnly, isLoading]);

  /**
   * Add new command to allowlist
   */
  const handleAddCommand = useCallback(() => {
    if (!newCommand.trim() || readOnly || isLoading) return;

    // Check if command already exists
    if (allowlist.some((entry) => entry.command === newCommand.trim())) {
      setIsAddDialogOpen(false);
      setNewCommand('');
      setNewCommandLabel('');
      return;
    }

    const newEntry: CommandAllowlistEntry = {
      command: newCommand.trim(),
      allowed: newCommandAllowed,
      label: newCommandLabel.trim() || undefined,
      addedAt: Date.now()
    };

    onChange([...allowlist, newEntry]);
    setIsAddDialogOpen(false);
    setNewCommand('');
    setNewCommandLabel('');
    setNewCommandAllowed(true);
  }, [newCommand, newCommandLabel, newCommandAllowed, allowlist, onChange, readOnly, isLoading]);

  /**
   * Remove command from allowlist (after confirmation)
   */
  const handleRemoveCommand = useCallback(() => {
    if (!commandToRemove || readOnly || isLoading) return;

    const updatedAllowlist = allowlist.filter((entry) => entry.command !== commandToRemove);
    onChange(updatedAllowlist);
    setCommandToRemove(null);
  }, [commandToRemove, allowlist, onChange, readOnly, isLoading]);

  /**
   * Format timestamp for display
   */
  const formatDate = useCallback((timestamp?: number): string => {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }, []);

  return (
    <div className="space-y-4">
      {/* Header with stats */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            {t('allowlist.title')}
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            {t('allowlist.description')}
          </p>
        </div>

        {/* Stats badges */}
        <div className="flex items-center gap-2">
          <div className="text-xs text-muted-foreground">
            {t('allowlist.stats.total', { count: stats.total })}
          </div>
          <div className="h-4 w-px bg-border" />
          <div className="text-xs text-green-600">
            {t('allowlist.stats.allowed', { count: stats.allowed })}
          </div>
          <div className="h-4 w-px bg-border" />
          <div className="text-xs text-red-600">
            {t('allowlist.stats.blocked', { count: stats.blocked })}
          </div>
        </div>
      </div>

      {/* Search and filters */}
      <div className="flex items-center gap-3">
        {/* Search input */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('allowlist.searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9"
            disabled={readOnly || isLoading}
          />
        </div>

        {/* Filter buttons */}
        <div className="flex items-center gap-1">
          {(['all', 'allowed', 'blocked'] as FilterType[]).map((filterType) => (
            <Button
              key={filterType}
              variant={filter === filterType ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setFilter(filterType)}
              disabled={readOnly || isLoading}
              className="h-9"
            >
              {t(`allowlist.filters.${filterType}`)}
            </Button>
          ))}
        </div>

        {/* Add command button */}
        {!readOnly && (
          <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="h-9 gap-1.5" disabled={isLoading}>
                <Plus className="h-4 w-4" />
                {t('allowlist.addButton')}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t('allowlist.addDialog.title')}</DialogTitle>
                <DialogDescription>
                  {t('allowlist.addDialog.description')}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 py-4">
                {/* Command input */}
                <div className="space-y-2">
                  <Label htmlFor="command-name">{t('allowlist.addDialog.commandLabel')}</Label>
                  <Input
                    id="command-name"
                    placeholder={t('allowlist.addDialog.commandPlaceholder')}
                    value={newCommand}
                    onChange={(e) => setNewCommand(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleAddCommand();
                      }
                    }}
                  />
                </div>

                {/* Optional label */}
                <div className="space-y-2">
                  <Label htmlFor="command-label">{t('allowlist.addDialog.labelLabel')}</Label>
                  <Input
                    id="command-label"
                    placeholder={t('allowlist.addDialog.labelPlaceholder')}
                    value={newCommandLabel}
                    onChange={(e) => setNewCommandLabel(e.target.value)}
                  />
                </div>

                {/* Allowed toggle */}
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>{t('allowlist.addDialog.allowedLabel')}</Label>
                    <p className="text-xs text-muted-foreground">
                      {t('allowlist.addDialog.allowedHint')}
                    </p>
                  </div>
                  <Checkbox
                    checked={newCommandAllowed}
                    onCheckedChange={(checked) =>
                      setNewCommandAllowed(checked === true)
                    }
                  />
                </div>
              </div>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setIsAddDialogOpen(false)}
                  disabled={isLoading}
                >
                  {tCommon('cancel')}
                </Button>
                <Button
                  onClick={handleAddCommand}
                  disabled={!newCommand.trim() || isLoading}
                >
                  {tCommon('add')}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Command list */}
      <div className={cn(
        "border rounded-lg divide-y",
        isLoading && "opacity-50 pointer-events-none"
      )}>
        {filteredCommands.length === 0 ? (
          <div className="py-12 px-4 text-center">
            <Terminal className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              {searchQuery || filter !== 'all'
                ? t('allowlist.noMatching')
                : t('allowlist.empty')}
            </p>
          </div>
        ) : (
          filteredCommands.map((entry) => (
            <div
              key={entry.command}
              className="flex items-center gap-3 p-3 hover:bg-muted/30 transition-colors"
            >
              {/* Terminal icon */}
              <div className="shrink-0">
                <Terminal className="h-4 w-4 text-muted-foreground" />
              </div>

              {/* Command name */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono font-medium text-foreground">
                    {entry.command}
                  </span>

                  {/* Label badge */}
                  {entry.label && (
                    <span className="text-[10px] text-muted-foreground px-1.5 py-0.5 bg-muted rounded flex items-center gap-1">
                      <Tag className="h-2.5 w-2.5" />
                      {entry.label}
                    </span>
                  )}
                </div>

                {/* Added date */}
                {entry.addedAt && (
                  <div className="flex items-center gap-1 mt-0.5">
                    <Clock className="h-3 w-3 text-muted-foreground/70" />
                    <span className="text-[10px] text-muted-foreground">
                      {t('allowlist.addedOn', { date: formatDate(entry.addedAt) })}
                    </span>
                  </div>
                )}
              </div>

              {/* Status indicator */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className={cn(
                    "flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium",
                    entry.allowed
                      ? "bg-green-500/10 text-green-600"
                      : "bg-red-500/10 text-red-600"
                  )}>
                    {entry.allowed ? (
                      <>
                        <Check className="h-3 w-3" />
                        {t('allowlist.status.allowed')}
                      </>
                    ) : (
                      <>
                        <X className="h-3 w-3" />
                        {t('allowlist.status.blocked')}
                      </>
                    )}
                  </div>
                </TooltipTrigger>
                <TooltipContent side="top">
                  {entry.allowed
                    ? t('allowlist.status.allowedHint')
                    : t('allowlist.status.blockedHint')}
                </TooltipContent>
              </Tooltip>

              {/* Actions */}
              {!readOnly && (
                <div className="flex items-center gap-1 shrink-0">
                  {/* Toggle allowed/blocked */}
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handleToggleCommand(entry.command, !entry.allowed)}
                        disabled={isLoading}
                      >
                        {entry.allowed ? (
                          <X className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <Check className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="top">
                      {entry.allowed
                        ? t('allowlist.actions.block')
                        : t('allowlist.actions.allow')}
                    </TooltipContent>
                  </Tooltip>

                  {/* Remove */}
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:text-destructive"
                        onClick={() => setCommandToRemove(entry.command)}
                        disabled={isLoading}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="top">
                      {t('allowlist.actions.remove')}
                    </TooltipContent>
                  </Tooltip>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Remove confirmation dialog */}
      <Dialog
        open={commandToRemove !== null}
        onOpenChange={(open) => !open && setCommandToRemove(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('allowlist.removeDialog.title')}</DialogTitle>
            <DialogDescription>
              {t('allowlist.removeDialog.description', { command: commandToRemove })}
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <div className="flex items-start gap-3 p-3 bg-destructive/10 rounded-lg border border-destructive/20">
              <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">
                  {t('allowlist.removeDialog.warning')}
                </p>
                <p className="text-xs text-muted-foreground">
                  {t('allowlist.removeDialog.warningHint')}
                </p>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCommandToRemove(null)}
              disabled={isLoading}
            >
              {tCommon('cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleRemoveCommand}
              disabled={isLoading}
            >
              {tCommon('remove')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Info tip */}
      <div className="rounded-lg bg-info/10 border border-info/30 p-3">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-info shrink-0 mt-0.5" />
          <div className="text-xs text-muted-foreground space-y-1">
            <p className="font-medium text-foreground">{t('allowlist.tipTitle')}</p>
            <p>{t('allowlist.tipDescription')}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
