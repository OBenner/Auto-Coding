/**
 * PluginManager - Main plugin management interface
 *
 * Displays all installed plugins, allows enabling/disabling/uninstalling plugins,
 * and provides a button to install new plugins.
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Puzzle, Plus, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { useToast } from '../../hooks/use-toast';
import { PluginCard } from './PluginCard';
import { InstallPluginDialog } from './InstallPluginDialog';
import type { PluginInfo } from '../../../main/plugins/types';

export function PluginManager() {
  const { t } = useTranslation(['plugins', 'common']);
  const { toast } = useToast();

  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [operatingPluginName, setOperatingPluginName] = useState<string | null>(null);
  const [isInstallDialogOpen, setIsInstallDialogOpen] = useState(false);

  // Load plugins on mount
  useEffect(() => {
    loadPlugins();
  }, []);

  /**
   * Load all installed plugins
   */
  const loadPlugins = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await window.electronAPI.listPlugins({});

      if (result.success && result.data) {
        setPlugins(result.data);
      } else {
        setError(result.error || t('plugins:toast.loadError'));
        toast({
          variant: 'destructive',
          title: t('plugins:toast.loadError'),
          description: result.error,
        });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(errorMessage);
      toast({
        variant: 'destructive',
        title: t('plugins:toast.loadError'),
        description: errorMessage,
      });
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Enable a plugin
   */
  const handleEnable = async (pluginName: string) => {
    setOperatingPluginName(pluginName);
    try {
      const result = await window.electronAPI.enablePlugin(pluginName);

      if (result.success) {
        toast({
          title: t('plugins:toast.enableSuccess'),
          description: `${pluginName} ${t('plugins:status.enabled').toLowerCase()}`,
        });
        await loadPlugins(); // Reload to get updated status
      } else {
        toast({
          variant: 'destructive',
          title: t('plugins:toast.enableError'),
          description: result.error || t('common:errors.unknown'),
        });
      }
    } catch (err) {
      toast({
        variant: 'destructive',
        title: t('plugins:toast.enableError'),
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setOperatingPluginName(null);
    }
  };

  /**
   * Disable a plugin
   */
  const handleDisable = async (pluginName: string) => {
    setOperatingPluginName(pluginName);
    try {
      const result = await window.electronAPI.disablePlugin(pluginName);

      if (result.success) {
        toast({
          title: t('plugins:toast.disableSuccess'),
          description: `${pluginName} ${t('plugins:status.disabled').toLowerCase()}`,
        });
        await loadPlugins(); // Reload to get updated status
      } else {
        toast({
          variant: 'destructive',
          title: t('plugins:toast.disableError'),
          description: result.error || t('common:errors.unknown'),
        });
      }
    } catch (err) {
      toast({
        variant: 'destructive',
        title: t('plugins:toast.disableError'),
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setOperatingPluginName(null);
    }
  };

  /**
   * Uninstall a plugin
   */
  const handleUninstall = async (pluginName: string) => {
    setOperatingPluginName(pluginName);
    try {
      const result = await window.electronAPI.uninstallPlugin(pluginName);

      if (result.success) {
        toast({
          title: t('plugins:toast.uninstallSuccess'),
          description: `${pluginName}`,
        });
        await loadPlugins(); // Reload to remove uninstalled plugin
      } else {
        toast({
          variant: 'destructive',
          title: t('plugins:toast.uninstallError'),
          description: result.error || t('common:errors.unknown'),
        });
      }
    } catch (err) {
      toast({
        variant: 'destructive',
        title: t('plugins:toast.uninstallError'),
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setOperatingPluginName(null);
    }
  };

  /**
   * Open install plugin dialog
   */
  const handleInstall = () => {
    setIsInstallDialogOpen(true);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
        <p className="text-sm text-muted-foreground">{t('common:loading', 'Loading...')}</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-12 px-4">
        <AlertCircle className="h-12 w-12 text-destructive mb-4" />
        <h3 className="text-lg font-semibold mb-2">{t('plugins:toast.loadError')}</h3>
        <p className="text-sm text-muted-foreground text-center max-w-md mb-4">{error}</p>
        <Button onClick={loadPlugins} variant="outline">
          {t('common:buttons.retry', 'Retry')}
        </Button>
      </div>
    );
  }

  // Empty state
  if (plugins.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-12 px-4">
        <Puzzle className="h-16 w-16 text-muted-foreground mb-4" />
        <h3 className="text-xl font-semibold mb-2">{t('plugins:empty.title')}</h3>
        <p className="text-sm text-muted-foreground text-center max-w-md mb-6">
          {t('plugins:empty.description')}
        </p>
        <Button onClick={handleInstall} size="lg" className="gap-2">
          <Plus className="h-5 w-5" />
          {t('plugins:empty.action')}
        </Button>
      </div>
    );
  }

  // Plugin list
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-border">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-3">
            <Puzzle className="h-7 w-7" />
            {t('plugins:title')}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {t('plugins:description')}
          </p>
        </div>
        <Button onClick={handleInstall} className="gap-2">
          <Plus className="h-4 w-4" />
          {t('plugins:actions.install')}
        </Button>
      </div>

      {/* Plugin cards */}
      <ScrollArea className="flex-1">
        <div className="p-6 grid gap-4 grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
          {plugins.map((plugin) => (
            <PluginCard
              key={plugin.metadata.name}
              plugin={plugin}
              onEnable={handleEnable}
              onDisable={handleDisable}
              onUninstall={handleUninstall}
              isLoading={operatingPluginName === plugin.metadata.name}
            />
          ))}
        </div>
      </ScrollArea>

      {/* Install Plugin Dialog */}
      <InstallPluginDialog
        open={isInstallDialogOpen}
        onOpenChange={setIsInstallDialogOpen}
        onPluginInstalled={loadPlugins}
      />
    </div>
  );
}
