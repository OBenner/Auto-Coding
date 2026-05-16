/**
 * InstallPluginDialog - Dialog for installing new plugins
 *
 * Allows users to install plugins from:
 * - Local directory (for development)
 * - Remote URL (zip file or git repository)
 * - Zip file (for distribution)
 * - Marketplace (future feature)
 *
 * Features:
 * - Radio button selection for installation source type
 * - File/directory picker integration
 * - URL input for remote plugins
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
import { Loader2, FolderOpen, FileArchive, Globe, Link } from 'lucide-react';
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
  /** Project path used as the plugin CLI working directory */
  projectPath: string;
  /** Optional callback when plugin is successfully installed */
  onPluginInstalled?: () => void;
}

export function InstallPluginDialog({
  open,
  onOpenChange,
  projectPath,
  onPluginInstalled
}: InstallPluginDialogProps) {
  const { t } = useTranslation(['plugins', 'common']);
  const { toast } = useToast();

  // Form state
  const [sourceType, setSourceType] = useState<'directory' | 'zip' | 'marketplace' | 'remote'>('directory');
  const [selectedPath, setSelectedPath] = useState<string>('');
  const [marketplaceId, setMarketplaceId] = useState<string>('');
  const [remoteUrl, setRemoteUrl] = useState<string>('');

  // UI state
  const [isInstalling, setIsInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (open) {
      setSourceType('directory');
      setSelectedPath('');
      setMarketplaceId('');
      setRemoteUrl('');
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
    if (sourceType === 'remote' && !remoteUrl) {
      setError(t('plugins:install.enterUrl', 'Please enter a plugin URL'));
      return;
    }

    setIsInstalling(true);
    setError(null);

    try {
      // Build installation source
      const source: PluginInstallSource = {
        type: sourceType,
        ...(sourceType === 'directory' || sourceType === 'zip' ? { path: selectedPath } : {}),
        ...(sourceType === 'marketplace' ? { marketplace_id: marketplaceId } : {}),
        ...(sourceType === 'remote' ? { url: remoteUrl } : {})
      };

      // Call IPC to install plugin
      const result = await window.electronAPI.installPlugin(source, projectPath);

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
    (sourceType === 'marketplace' && marketplaceId.trim()) ||
    (sourceType === 'remote' && remoteUrl.trim());

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-foreground">
            {t('plugins:install.title', 'Install Plugin')}
          </DialogTitle>
          <DialogDescription>
            {t('plugins:install.description', 'Install a plugin from a local directory, remote URL, zip file, or marketplace.')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Installation Source Type */}
          <div className="space-y-3">
            <Label>{t('plugins:install.sourceType', 'Installation Source')}</Label>
            <RadioGroup
              value={sourceType}
              onValueChange={(value) => {
                setSourceType(value as 'directory' | 'zip' | 'marketplace' | 'remote');
                setSelectedPath('');
                setMarketplaceId('');
                setRemoteUrl('');
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

              {/* Remote URL */}
              <div className="flex items-start gap-3 rounded-lg border border-border p-3 hover:bg-accent/50 transition-colors">
                <RadioGroupItem value="remote" id="source-remote" className="mt-1" />
                <Label
                  htmlFor="source-remote"
                  className="flex-1 cursor-pointer"
                >
                  <div className="flex items-center gap-2 font-medium mb-1">
                    <Link className="h-4 w-4" />
                    {t('plugins:install.fromUrl', 'From URL')}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t('plugins:install.urlDescription', 'Install from a remote plugin URL (zip file or git repository)')}
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

          {/* Remote URL Input */}
          {sourceType === 'remote' && (
            <div className="space-y-2">
              <Label htmlFor="plugin-url">
                {t('plugins:install.pluginUrl', 'Plugin URL')}
              </Label>
              <input
                id="plugin-url"
                type="text"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="https://example.com/plugin.zip"
                value={remoteUrl}
                onChange={(e) => {
                  setRemoteUrl(e.target.value);
                  setError(null);
                }}
                disabled={isInstalling}
              />
              <p className="text-xs text-muted-foreground">
                {t('plugins:install.urlHelp', 'Enter the URL to a plugin zip file or git repository')}
              </p>
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
