/**
 * PluginManager - Main plugin management interface
 *
 * Displays all installed plugins, allows enabling/disabling/uninstalling plugins,
 * and provides a button to install new plugins.
 */
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Activity, FileText, Puzzle, Plus, Loader2, AlertCircle, ShieldCheck } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '../ui/alert-dialog';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '../ui/dialog';
import { useToast } from '../../hooks/use-toast';
import { PluginCard } from './PluginCard';
import { InstallPluginDialog } from './InstallPluginDialog';
import type {
  PluginContextPreview,
  PluginInfo,
  PluginPermissionDiff,
  PluginTraceResult
} from '../../../main/plugins/types';

interface PluginManagerProps {
  readonly projectPath: string;
}

interface PermissionReviewState {
  pluginName: string;
  diff: PluginPermissionDiff;
  enableAfterConfirm: boolean;
}

interface TraceViewState {
  pluginName: string;
  result: PluginTraceResult;
}

interface PreviewViewState {
  pluginName: string;
  result: PluginContextPreview;
}

export function PluginManager({ projectPath }: PluginManagerProps) {
  const { t } = useTranslation(['plugins', 'common']);
  const { toast } = useToast();

  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [operatingPluginName, setOperatingPluginName] = useState<string | null>(null);
  const [isInstallDialogOpen, setIsInstallDialogOpen] = useState(false);
  const [permissionReview, setPermissionReview] = useState<PermissionReviewState | null>(null);
  const [traceView, setTraceView] = useState<TraceViewState | null>(null);
  const [previewView, setPreviewView] = useState<PreviewViewState | null>(null);

  /**
   * Load all installed plugins
   */
  const loadPlugins = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await globalThis.electronAPI.listPlugins({ projectPath });

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
  }, [projectPath, t, toast]);

  // Load plugins on mount and when switching projects
  useEffect(() => {
    loadPlugins();
  }, [loadPlugins]);

  const translatePermission = (permission: string) =>
    t(`plugins:permissions.${permission}`, { defaultValue: permission });

  const translateCapability = (capability: string) =>
    t(`plugins:capabilities.${capability}`, { defaultValue: capability });

  const translatePluginType = (pluginType: string) =>
    t(`plugins:types.${pluginType}`, { defaultValue: pluginType });

  const openPermissionReview = async (
    pluginName: string,
    enableAfterConfirm: boolean
  ) => {
    setOperatingPluginName(pluginName);
    try {
      const result = await globalThis.electronAPI.getPluginPermissionDiff(
        pluginName,
        projectPath
      );

      if (result.success && result.data) {
        setPermissionReview({
          pluginName,
          diff: result.data,
          enableAfterConfirm
        });
      } else {
        toast({
          variant: 'destructive',
          title: t('plugins:toast.permissionDiffError'),
          description: result.error || t('common:errors.unknown'),
        });
      }
    } catch (err) {
      toast({
        variant: 'destructive',
        title: t('plugins:toast.permissionDiffError'),
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setOperatingPluginName(null);
    }
  };

  /**
   * Enable a plugin after showing the permission diff
   */
  const handleEnable = (pluginName: string) => {
    void openPermissionReview(pluginName, true);
  };

  const handleInspectPermissions = (pluginName: string) => {
    void openPermissionReview(pluginName, false);
  };

  const handleConfirmEnable = async () => {
    const review = permissionReview;
    if (!review) {
      return;
    }

    setPermissionReview(null);
    setOperatingPluginName(review.pluginName);
    try {
      const result = await globalThis.electronAPI.enablePlugin(review.pluginName, projectPath);

      if (result.success) {
        toast({
          title: t('plugins:toast.enableSuccess'),
          description: t('plugins:toast.enableStatusMessage', { plugin: review.pluginName }),
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
      const result = await globalThis.electronAPI.disablePlugin(pluginName, projectPath);

      if (result.success) {
        toast({
          title: t('plugins:toast.disableSuccess'),
          description: t('plugins:toast.disableStatusMessage', { plugin: pluginName }),
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
      const result = await globalThis.electronAPI.uninstallPlugin(pluginName, projectPath);

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

  const handleViewTraces = async (pluginName: string) => {
    setOperatingPluginName(pluginName);
    try {
      const result = await globalThis.electronAPI.getPluginTraces(projectPath, {
        pluginName,
        limit: 20
      });

      if (result.success && result.data) {
        setTraceView({ pluginName, result: result.data });
      } else {
        toast({
          variant: 'destructive',
          title: t('plugins:toast.tracesError'),
          description: result.error || t('common:errors.unknown'),
        });
      }
    } catch (err) {
      toast({
        variant: 'destructive',
        title: t('plugins:toast.tracesError'),
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setOperatingPluginName(null);
    }
  };

  const handlePreviewContext = async (pluginName: string) => {
    setOperatingPluginName(pluginName);
    try {
      const result = await globalThis.electronAPI.previewPluginContext(projectPath, {
        agentType: 'coder',
        task: pluginName
      });

      if (result.success && result.data) {
        setPreviewView({ pluginName, result: result.data });
      } else {
        toast({
          variant: 'destructive',
          title: t('plugins:toast.previewError'),
          description: result.error || t('common:errors.unknown'),
        });
      }
    } catch (err) {
      toast({
        variant: 'destructive',
        title: t('plugins:toast.previewError'),
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
        <InstallPluginDialog
          open={isInstallDialogOpen}
          onOpenChange={setIsInstallDialogOpen}
          projectPath={projectPath}
          onPluginInstalled={loadPlugins}
        />
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
              onInspectPermissions={handleInspectPermissions}
              onViewTraces={handleViewTraces}
              onPreviewContext={handlePreviewContext}
              isLoading={operatingPluginName === plugin.metadata.name}
            />
          ))}
        </div>
      </ScrollArea>

      {/* Install Plugin Dialog */}
      <InstallPluginDialog
        open={isInstallDialogOpen}
        onOpenChange={setIsInstallDialogOpen}
        projectPath={projectPath}
        onPluginInstalled={loadPlugins}
      />

      <AlertDialog
        open={permissionReview !== null}
        onOpenChange={(open) => {
          if (!open) {
            setPermissionReview(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" />
              {t('plugins:permissionReview.title')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('plugins:permissionReview.description', {
                plugin: permissionReview?.pluginName ?? ''
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>

          {permissionReview && (
            <div className="space-y-4 py-2">
              <div>
                <p className="text-sm font-medium mb-2">
                  {t('plugins:permissionReview.requiredPermissions')}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {permissionReview.diff.required_permissions.length > 0 ? (
                    permissionReview.diff.required_permissions.map((permission) => (
                      <Badge key={permission} variant="outline" className="text-xs">
                        {translatePermission(permission)}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      {t('plugins:permissionReview.none')}
                    </span>
                  )}
                </div>
              </div>

              <div>
                <p className="text-sm font-medium mb-2">
                  {t('plugins:permissionReview.addedPermissions')}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {permissionReview.diff.added_permissions.length > 0 ? (
                    permissionReview.diff.added_permissions.map((permission) => (
                      <Badge key={permission} variant="secondary" className="text-xs">
                        {translatePermission(permission)}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      {t('plugins:permissionReview.noNewPermissions')}
                    </span>
                  )}
                </div>
              </div>

              <div>
                <p className="text-sm font-medium mb-2">
                  {t('plugins:permissionReview.addedCapabilities')}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {permissionReview.diff.added_capabilities.length > 0 ? (
                    permissionReview.diff.added_capabilities.map((capability) => (
                      <Badge key={capability} variant="outline" className="text-xs">
                        {translateCapability(capability)}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      {t('plugins:permissionReview.noNewCapabilities')}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          <AlertDialogFooter>
            <AlertDialogCancel>{t('common:buttons.cancel')}</AlertDialogCancel>
            {permissionReview?.enableAfterConfirm && (
              <AlertDialogAction onClick={handleConfirmEnable}>
                {t('plugins:actions.confirmEnable')}
              </AlertDialogAction>
            )}
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog
        open={traceView !== null}
        onOpenChange={(open) => {
          if (!open) {
            setTraceView(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-[720px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              {t('plugins:traces.title')}
            </DialogTitle>
            <DialogDescription>
              {t('plugins:traces.description', { plugin: traceView?.pluginName ?? '' })}
            </DialogDescription>
          </DialogHeader>

          <ScrollArea className="max-h-[420px] pr-3">
            {traceView && traceView.result.traces.length > 0 ? (
              <div className="space-y-3">
                {traceView.result.traces.map((trace, index) => (
                  <div
                    key={`${trace.source ?? traceView.pluginName}-${index}`}
                    className="rounded-md border border-border bg-muted/30 p-3"
                  >
                    <div className="flex flex-wrap items-center gap-2 mb-2 text-xs text-muted-foreground">
                      {trace.event && <Badge variant="secondary">{String(trace.event)}</Badge>}
                      {trace.source && (
                        <span>
                          {t('plugins:traces.source', { source: String(trace.source) })}
                        </span>
                      )}
                    </div>
                    <pre className="whitespace-pre-wrap break-words text-xs">
                      {JSON.stringify(trace, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t('plugins:traces.empty')}</p>
            )}
          </ScrollArea>

          <DialogFooter>
            <Button variant="outline" onClick={() => setTraceView(null)}>
              {t('common:buttons.close')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={previewView !== null}
        onOpenChange={(open) => {
          if (!open) {
            setPreviewView(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-[720px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {t('plugins:contextPreview.title')}
            </DialogTitle>
            <DialogDescription>
              {t('plugins:contextPreview.description', {
                plugin: previewView?.pluginName ?? '',
                agent: previewView?.result.agent_type ?? 'coder'
              })}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium mb-2">
                {t('plugins:contextPreview.runtimePlugins')}
              </p>
              {previewView && previewView.result.runtime_plugins.length > 0 ? (
                <div className="space-y-2">
                  {previewView.result.runtime_plugins.map((plugin) => (
                    <div
                      key={plugin.plugin_name}
                      className="rounded-md border border-border bg-muted/20 p-3"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium">{plugin.plugin_name}</span>
                        <Badge variant="outline" className="text-xs">
                          {translatePluginType(plugin.plugin_type)}
                        </Badge>
                        <Badge
                          variant={plugin.contributed ? 'secondary' : 'outline'}
                          className="text-xs"
                        >
                          {plugin.contributed
                            ? t('plugins:contextPreview.contributed')
                            : t('plugins:contextPreview.noPromptContribution')}
                        </Badge>
                      </div>
                      {plugin.capabilities.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {plugin.capabilities.map((capability) => (
                            <Badge key={capability} variant="outline" className="text-xs">
                              {translateCapability(capability)}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t('plugins:contextPreview.noRuntimePlugins')}
                </p>
              )}
            </div>

            <div>
              <p className="text-sm font-medium mb-2">
                {t('plugins:contextPreview.contributions')}
              </p>
              {previewView && previewView.result.contributions.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {previewView.result.contributions.map((contribution) => (
                    <Badge key={contribution.plugin_name} variant="outline">
                      {contribution.plugin_name}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t('plugins:contextPreview.noContributions')}
                </p>
              )}
            </div>

            <ScrollArea className="max-h-[360px] rounded-md border border-border bg-muted/30 p-3">
              <pre className="whitespace-pre-wrap break-words text-xs">
                {previewView?.result.preview || t('plugins:contextPreview.empty')}
              </pre>
            </ScrollArea>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setPreviewView(null)}>
              {t('common:buttons.close')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
