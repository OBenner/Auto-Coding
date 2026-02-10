/**
 * KeyboardShortcutsSettings - Manage customizable keyboard shortcuts
 *
 * Allows users to view and customize keyboard shortcuts for common actions.
 * Shortcuts are stored in localStorage and persist across sessions.
 */
import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Keyboard,
  RotateCcw,
  Save,
  Loader2,
  Info
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { cn } from '../../lib/utils';
import { SettingsSection } from './SettingsSection';
import { useKeyboardShortcutsStore, formatKeyCombination, parseKeyboardEvent } from '../../stores/keyboard-shortcuts-store';
import type { KeyboardShortcutAction } from '../../../shared/types/settings';
import { DEFAULT_KEYBOARD_SHORTCUTS } from '../../../shared/types/settings';
import { useToast } from '../../hooks/use-toast';

interface KeyboardShortcutsSettingsProps {
  isOpen: boolean;
}

/**
 * Keyboard shortcut definition with metadata
 */
interface ShortcutDefinition {
  action: KeyboardShortcutAction;
  label: string;
  description: string;
}

/**
 * Keyboard shortcuts settings component
 */
export function KeyboardShortcutsSettings({ isOpen }: KeyboardShortcutsSettingsProps) {
  const { t } = useTranslation('settings');
  const { toast } = useToast();

  const { shortcuts, updateShortcut, resetToDefaults, saveShortcuts, loadShortcuts } = useKeyboardShortcutsStore();

  const [isRecording, setIsRecording] = useState<KeyboardShortcutAction | null>(null);
  const [recordedKeys, setRecordedKeys] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Define available shortcuts
  const shortcutDefinitions: ShortcutDefinition[] = [
    {
      action: 'commandPalette',
      label: t('keyboardShortcuts.actions.commandPalette.label'),
      description: t('keyboardShortcuts.actions.commandPalette.description')
    },
    {
      action: 'quickActions',
      label: t('keyboardShortcuts.actions.quickActions.label'),
      description: t('keyboardShortcuts.actions.quickActions.description')
    },
    {
      action: 'createTask',
      label: t('keyboardShortcuts.actions.createTask.label'),
      description: t('keyboardShortcuts.actions.createTask.description')
    },
    {
      action: 'batchQA',
      label: t('keyboardShortcuts.actions.batchQA.label'),
      description: t('keyboardShortcuts.actions.batchQA.description')
    },
    {
      action: 'batchStatusUpdate',
      label: t('keyboardShortcuts.actions.batchStatusUpdate.label'),
      description: t('keyboardShortcuts.actions.batchStatusUpdate.description')
    }
  ];

  // Load shortcuts when section opens
  useEffect(() => {
    if (isOpen) {
      loadShortcuts();
    }
  }, [isOpen, loadShortcuts]);

  // Track changes
  useEffect(() => {
    const hasChanged = Object.entries(shortcuts).some(
      ([action, keyCombo]) => keyCombo !== DEFAULT_KEYBOARD_SHORTCUTS[action as keyof typeof DEFAULT_KEYBOARD_SHORTCUTS]
    );
    setHasChanges(hasChanged);
  }, [shortcuts]);

  // Handle keyboard recording
  const handleStartRecording = (action: KeyboardShortcutAction) => {
    setIsRecording(action);
    setRecordedKeys('');
  };

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (isRecording === null) return;

    event.preventDefault();
    event.stopPropagation();

    const parsed = parseKeyboardEvent(event);
    setRecordedKeys(formatKeyCombination(parsed));

    // Auto-save on first key press
    if (parsed && isRecording && parsed !== shortcuts[isRecording]) {
      updateShortcut(isRecording, parsed);
      setIsRecording(null);
      setRecordedKeys('');
      setHasChanges(true);
    }
  }, [isRecording, shortcuts, updateShortcut]);

  const handleCancelRecording = () => {
    setIsRecording(null);
    setRecordedKeys('');
  };

  // Register keyboard listener when recording
  useEffect(() => {
    if (isRecording !== null) {
      window.addEventListener('keydown', handleKeyDown, { capture: true });
      return () => {
        window.removeEventListener('keydown', handleKeyDown, { capture: true });
      };
    }
  }, [isRecording, handleKeyDown]);

  // Handle reset to defaults
  const handleResetToDefaults = () => {
    resetToDefaults();
    setHasChanges(false);
    toast({
      title: t('keyboardShortcuts.toast.resetTitle'),
      description: t('keyboardShortcuts.toast.resetDescription')
    });
  };

  // Handle save
  const handleSave = () => {
    setIsSaving(true);
    const success = saveShortcuts();
    setIsSaving(false);

    if (success) {
      setHasChanges(false);
      toast({
        title: t('keyboardShortcuts.toast.savedTitle'),
        description: t('keyboardShortcuts.toast.savedDescription')
      });
    } else {
      toast({
        variant: 'destructive',
        title: t('keyboardShortcuts.toast.saveFailedTitle'),
        description: t('keyboardShortcuts.toast.saveFailedDescription')
      });
    }
  };

  return (
    <SettingsSection
      title={t('keyboardShortcuts.title')}
      description={t('keyboardShortcuts.description')}
    >
      <div className="space-y-6">
        {/* Info banner */}
        <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/30 border border-border">
          <Info className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
          <div className="text-sm text-muted-foreground">
            {t('keyboardShortcuts.infoBanner')}
          </div>
        </div>

        {/* Shortcuts list */}
        <div className="space-y-3">
          {shortcutDefinitions.map((definition) => {
            const currentShortcut = shortcuts[definition.action as keyof typeof shortcuts];
            const isCurrentlyRecording = isRecording === definition.action;

            return (
              <div
                key={definition.action}
                className={cn(
                  "flex items-center justify-between p-4 rounded-lg border transition-colors",
                  isCurrentlyRecording
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-accent/50"
                )}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Label className="text-sm font-medium">{definition.label}</Label>
                  </div>
                  <p className="text-xs text-muted-foreground">{definition.description}</p>
                </div>

                <div className="flex items-center gap-3">
                  {isCurrentlyRecording ? (
                    <div className="flex items-center gap-2">
                      <kbd className="px-3 py-1.5 text-sm font-mono rounded border border-primary bg-primary/10 text-primary min-w-[120px] text-center">
                        {recordedKeys || t('keyboardShortcuts.recording.pressKeys')}
                      </kbd>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleCancelRecording}
                        className="h-8 text-xs"
                      >
                        {t('keyboardShortcuts.recording.cancel')}
                      </Button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <kbd className="px-3 py-1.5 text-sm font-mono rounded border border-border bg-muted min-w-[120px] text-center">
                        {formatKeyCombination(currentShortcut)}
                      </kbd>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleStartRecording(definition.action)}
                        disabled={isRecording !== null}
                        className="h-8 text-xs"
                      >
                        {t('keyboardShortcuts.actions.change')}
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-border">
          <Button
            variant="outline"
            onClick={handleResetToDefaults}
            disabled={!hasChanges || isSaving}
            className="gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            {t('keyboardShortcuts.actions.resetToDefaults')}
          </Button>

          {hasChanges && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                {t('keyboardShortcuts.unsavedChanges')}
              </span>
              <Button
                onClick={handleSave}
                disabled={isSaving}
                className="gap-2"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t('keyboardShortcuts.actions.saving')}
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    {t('keyboardShortcuts.actions.save')}
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      </div>
    </SettingsSection>
  );
}
