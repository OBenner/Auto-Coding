/**
 * InstallPluginDialog - Dialog for installing new plugins
 *
 * Allows users to install plugins from:
 * - Local directory (for development)
 * - Zip file (for distribution)
 * - Marketplace (future feature)
 *
 * Features:
 * - Radio button selection for installation source type
 * - File/directory picker integration
 * - Installation progress and error handling
 * - Success toast notifications
 *
 * @example
 * ```tsx
 * <InstallPluginDialog
 *   open={isDialogOpen}
 *   onOpenChange={setIsDialogOpen}
 *   onPluginInstalled={() => loadPlugins()}
 * />
 * ```
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, FolderOpen, FileArchive, Globe } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';
import { useToast } from '../../hooks/use-toast';
import type { PluginInstallSource } from '../../../main/plugins/types';

/**
 * Props for the InstallPluginDialog component
 */
interface InstallPluginDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when the dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Optional callback when plugin is successfully installed */
  onPluginInstalled?: () => void;
}

export function InstallPluginDialog({
  open,
  onOpenChange,
  onPluginInstalled
}: InstallPluginDialogProps) {
  const { t } = useTranslation(['plugins', 'common']);
  const { toast } = useToast();

  // Form state
  const [sourceType, setSourceType] = useState<'directory' | 'zip' | 'marketplace'>('directory');
  const [selectedPath, setSelectedPath] = useState<string>('');
  const [marketplaceId, setMarketplaceId] = useState<string>('');

  // UI state
  const [isInstalling, setIsInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (open) {
      setSourceType('directory');
      setSelectedPath('');
      setMarketplaceId('');
      setError(null);
      setIsInstalling(false);
    }
  }, [open]);

  /**
   * Open file picker for directory selection
   */
  const handleSelectDirectory = async () => {
    try {
      const result = await window.electronAPI.selectDirectory();
      if (result) {
        setSelectedPath(result);
        setError(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  /**
   * Open file picker for zip file selection
   */
  const handleSelectZip = async () => {
    try {
      // Use the Electron dialog API to select a zip file
      // Note: We'll need to add a selectFile API to electronAPI
      // For now, we'll show a message that this feature is coming soon
      toast({
        title: t('common:comingSoon', 'Coming Soon'),
        description: t('plugins:install.zipNotYetSupported', 'Zip file installation will be supported in a future update.'),
      });
      setError(t('plugins:install.zipNotYetSupported', 'Zip file installation will be supported in a future update.'));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  /**
   * Install the plugin
   */
  const handleInstall = async () => {
    // Validate based on source type
    if (sourceType === 'directory' && !selectedPath) {
      setError(t('plugins:install.selectDirectory', 'Please select a plugin directory'));
      return;
    }
    if (sourceType === 'zip' && !selectedPath) {
      setError(t('plugins:install.selectZip', 'Please select a plugin zip file'));
      return;
    }
    if (sourceType === 'marketplace' && !marketplaceId) {
      setError(t('plugins:install.enterMarketplaceId', 'Please enter a marketplace plugin ID'));
      return;
    }

    setIsInstalling(true);
    setError(null);

    try {
      // Build installation source
      const source: PluginInstallSource = {
        type: sourceType,
        ...(sourceType === 'directory' || sourceType === 'zip' ? { path: selectedPath } : {}),
        ...(sourceType === 'marketplace' ? { marketplace_id: marketplaceId } : {})
      };

      // Call IPC to install plugin
      const result = await window.electronAPI.installPlugin(source);

      if (result.success && result.data?.plugin) {
        toast({
          title: t('plugins:toast.installSuccess', 'Plugin installed successfully'),
          description: `${result.data.plugin.name} v${result.data.plugin.version}`,
        });
        onOpenChange(false);
        onPluginInstalled?.();
      } else {
        setError(result.error || t('plugins:toast.installError', 'Failed to install plugin'));
        toast({
          variant: 'destructive',
          title: t('plugins:toast.installError'),
          description: result.error || t('common:errors.unknown'),
        });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(errorMessage);
      toast({
        variant: 'destructive',
        title: t('plugins:toast.installError'),
        description: errorMessage,
      });
    } finally {
      setIsInstalling(false);
    }
  };

  const handleClose = () => {
    if (!isInstalling) {
      onOpenChange(false);
    }
  };

  // Form validation
  const isValid =
    (sourceType === 'directory' && selectedPath) ||
    (sourceType === 'zip' && selectedPath) ||
    (sourceType === 'marketplace' && marketplaceId.trim());

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-foreground">
            {t('plugins:install.title', 'Install Plugin')}
          </DialogTitle>
          <DialogDescription>
            {t('plugins:install.description', 'Install a plugin from a local directory, zip file, or marketplace.')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Installation Source Type */}
          <div className="space-y-3">
            <Label>{t('plugins:install.sourceType', 'Installation Source')}</Label>
            <RadioGroup
              value={sourceType}
              onValueChange={(value) => {
                setSourceType(value as 'directory' | 'zip' | 'marketplace');
                setSelectedPath('');
                setMarketplaceId('');
                setError(null);
              }}
              className="grid grid-cols-1 gap-3"
            >
              {/* Directory */}
              <div className="flex items-start gap-3 rounded-lg border border-border p-3 hover:bg-accent/50 transition-colors">
                <RadioGroupItem value="directory" id="source-directory" className="mt-1" />
                <Label
                  htmlFor="source-directory"
                  className="flex-1 cursor-pointer"
                >
                  <div className="flex items-center gap-2 font-medium mb-1">
                    <FolderOpen className="h-4 w-4" />
                    {t('plugins:install.fromDirectory', 'From Directory')}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t('plugins:install.directoryDescription', 'Install from a local plugin directory (for development)')}
                  </p>
                </Label>
              </div>

              {/* Zip File */}
              <div className="flex items-start gap-3 rounded-lg border border-border p-3 hover:bg-accent/50 transition-colors opacity-50">
                <RadioGroupItem value="zip" id="source-zip" className="mt-1" disabled />
                <Label
                  htmlFor="source-zip"
                  className="flex-1"
                >
                  <div className="flex items-center gap-2 font-medium mb-1">
                    <FileArchive className="h-4 w-4" />
                    {t('plugins:install.fromZip', 'From Zip File')}
                    <span className="text-xs text-muted-foreground font-normal">
                      ({t('common:comingSoon', 'Coming Soon')})
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t('plugins:install.zipDescription', 'Install from a packaged plugin zip file')}
                  </p>
                </Label>
              </div>

              {/* Marketplace */}
              <div className="flex items-start gap-3 rounded-lg border border-border p-3 hover:bg-accent/50 transition-colors opacity-50">
                <RadioGroupItem value="marketplace" id="source-marketplace" className="mt-1" disabled />
                <Label
                  htmlFor="source-marketplace"
                  className="flex-1"
                >
                  <div className="flex items-center gap-2 font-medium mb-1">
                    <Globe className="h-4 w-4" />
                    {t('plugins:install.fromMarketplace', 'From Marketplace')}
                    <span className="text-xs text-muted-foreground font-normal">
                      ({t('common:comingSoon', 'Coming Soon')})
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t('plugins:install.marketplaceDescription', 'Install from the Auto Code plugin marketplace')}
                  </p>
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Directory/Zip File Selection */}
          {(sourceType === 'directory' || sourceType === 'zip') && (
            <div className="space-y-2">
              <Label htmlFor="plugin-path">
                {sourceType === 'directory'
                  ? t('plugins:install.pluginDirectory', 'Plugin Directory')
                  : t('plugins:install.pluginZipFile', 'Plugin Zip File')}
              </Label>
              <div className="flex gap-2">
                <div className="flex-1 px-3 py-2 rounded-md border border-input bg-background text-sm text-muted-foreground truncate">
                  {selectedPath || t('plugins:install.noPathSelected', 'No path selected')}
                </div>
                <Button
                  type="button"
                  variant="outline"
                  onClick={sourceType === 'directory' ? handleSelectDirectory : handleSelectZip}
                  disabled={isInstalling}
                >
                  {t('plugins:install.browse', 'Browse')}
                </Button>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="rounded-lg bg-destructive/10 border border-destructive/30 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isInstalling}>
            {t('common:cancel', 'Cancel')}
          </Button>
          <Button
            onClick={handleInstall}
            disabled={isInstalling || !isValid}
          >
            {isInstalling ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('plugins:install.installing', 'Installing...')}
              </>
            ) : (
              t('plugins:install.install', 'Install')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
