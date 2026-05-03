import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Terminal, Loader2, Check, AlertTriangle, X, RefreshCw, Download, Info, ExternalLink } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import type { ClaudeCodeVersionInfo } from '../../../shared/types/cli';

interface ClaudeCodeStepProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
  runtime?: 'claude' | 'codex';
}

type DetectionStatus = 'loading' | 'installed' | 'outdated' | 'not-found' | 'error';

/**
 * Claude Code CLI installation step for the onboarding wizard.
 *
 * Checks if Claude Code CLI is installed, shows version information,
 * and provides one-click installation/update functionality.
 */
export function ClaudeCodeStep({ onNext, onBack, onSkip, runtime = 'claude' }: ClaudeCodeStepProps) {
  const { t } = useTranslation('onboarding');
  const cliKeys = runtime === 'codex' ? 'codexCli' : 'claudeCode';
  const [status, setStatus] = useState<DetectionStatus>('loading');
  const [versionInfo, setVersionInfo] = useState<ClaudeCodeVersionInfo | null>(null);
  const [isInstalling, setIsInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [installSuccess, setInstallSuccess] = useState(false);

  // Check Claude Code version on mount
  const checkVersion = useCallback(async () => {
    setStatus('loading');
    setError(null);
    setInstallSuccess(false);

    try {
      const checkVersionApi = runtime === 'codex'
        ? window.electronAPI?.checkCodexCodeVersion
        : window.electronAPI?.checkClaudeCodeVersion;

      if (!checkVersionApi) {
        console.warn('[ClaudeCodeStep] Version check API not available');
        setStatus('error');
        setError(t(`${cliKeys}.errors.versionCheckApiMissing`));
        return;
      }

      const result = await checkVersionApi();

      if (result.success && result.data) {
        setVersionInfo(result.data);

        if (!result.data.installed) {
          setStatus('not-found');
        } else if (result.data.isOutdated) {
          setStatus('outdated');
        } else {
          setStatus('installed');
        }
      } else {
        setStatus('error');
        setError(result.error || t(`${cliKeys}.errors.versionCheckFailed`));
      }
    } catch (err) {
      console.error('Failed to check Claude Code version:', err);
      setStatus('error');
      setError(err instanceof Error ? err.message : t(`${cliKeys}.errors.unknownError`));
    }
  }, [cliKeys, runtime, t]);

  useEffect(() => {
    checkVersion();
  }, [checkVersion]);

  // Handle install/update button click
  const handleInstall = async () => {
    setIsInstalling(true);
    setError(null);

    try {
      if (!window.electronAPI?.installClaudeCode) {
        setError(t('claudeCode.errors.installApiMissing'));
        return;
      }

      const result = await window.electronAPI.installClaudeCode();

      if (result.success) {
        setInstallSuccess(true);
        // Re-check version after a short delay to give user time to complete installation
        setTimeout(() => {
          checkVersion();
        }, 5000);
      } else {
        setError(result.error || t('claudeCode.errors.installFailed'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('claudeCode.errors.unknownError'));
    } finally {
      setIsInstalling(false);
    }
  };

  // Get status icon
  const getStatusIcon = () => {
    switch (status) {
      case 'loading':
        return <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />;
      case 'installed':
        return <Check className="h-6 w-6 text-green-500" />;
      case 'outdated':
        return <AlertTriangle className="h-6 w-6 text-yellow-500" />;
      case 'not-found':
        return <X className="h-6 w-6 text-destructive" />;
      case 'error':
        return <AlertTriangle className="h-6 w-6 text-destructive" />;
    }
  };

  // Get status text
  const getStatusText = () => {
    switch (status) {
      case 'loading':
        return t(`${cliKeys}.detecting`);
      case 'installed':
        return t(`${cliKeys}.status.installed`);
      case 'outdated':
        return t(`${cliKeys}.status.outdated`);
      case 'not-found':
        return t(`${cliKeys}.status.notFound`);
      case 'error':
        return error || t(`${cliKeys}.errors.statusCheckFailed`);
    }
  };

  // Get status color class
  const getStatusColorClass = () => {
    switch (status) {
      case 'installed':
        return 'text-green-500';
      case 'outdated':
        return 'text-yellow-500';
      case 'not-found':
      case 'error':
        return 'text-destructive';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <div className="flex h-full flex-col items-center justify-center px-8 py-6">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Terminal className="h-7 w-7" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">
            {t(`${cliKeys}.title`)}
          </h1>
          <p className="mt-2 text-muted-foreground">
            {t(`${cliKeys}.description`)}
          </p>
        </div>

        {/* Main content */}
        <div className="space-y-6">
          {/* Info card */}
          <Card className="border border-info/30 bg-info/10">
            <CardContent className="p-5">
              <div className="flex items-start gap-4">
                <Info className="h-5 w-5 text-info shrink-0 mt-0.5" />
                <div className="flex-1 space-y-3">
                  <p className="text-sm font-medium text-foreground">
                    {t(`${cliKeys}.info.title`)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {t(`${cliKeys}.info.description`)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Status card */}
          <Card className={`border ${status === 'installed' ? 'border-green-500/30 bg-green-500/5' : status === 'outdated' ? 'border-yellow-500/30 bg-yellow-500/5' : status === 'not-found' || status === 'error' ? 'border-destructive/30 bg-destructive/5' : 'border-border'}`}>
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {getStatusIcon()}
                  <div>
                    <p className={`text-sm font-medium ${getStatusColorClass()}`}>
                      {getStatusText()}
                    </p>
                    {versionInfo && status !== 'loading' && (
                      <div className="mt-1 text-xs text-muted-foreground space-y-0.5">
                        {versionInfo.installed && (
                          <p>
                            {t(`${cliKeys}.version.current`)}: <span className="font-mono">{versionInfo.installed}</span>
                          </p>
                        )}
                        {versionInfo.latest && versionInfo.latest !== 'unknown' && (
                          <p>
                            {t(`${cliKeys}.version.latest`)}: <span className="font-mono">{versionInfo.latest}</span>
                          </p>
                        )}
                        {versionInfo.path && (
                          <p className="truncate max-w-md" title={versionInfo.path}>
                            {t(`${cliKeys}.version.path`)}: <span className="font-mono">{versionInfo.path}</span>
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Refresh button */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={checkVersion}
                  disabled={status === 'loading' || isInstalling}
                >
                  <RefreshCw className={`h-4 w-4 ${status === 'loading' ? 'animate-spin' : ''}`} />
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Error message */}
          {error && status !== 'loading' && (
            <Card className="border border-destructive/30 bg-destructive/10">
              <CardContent className="p-4">
                <p className="text-sm text-destructive">{error}</p>
              </CardContent>
            </Card>
          )}

          {/* Install success message */}
          {installSuccess && (
            <Card className="border border-green-500/30 bg-green-500/10">
              <CardContent className="p-4">
                <p className="text-sm text-green-700 dark:text-green-400">
                  {t('claudeCode.install.success', 'Installation command sent to terminal. Please complete the installation there.')}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  {t('claudeCode.install.instructions', 'The installer will open in your terminal. Follow the prompts to complete installation.')}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Install/Update button */}
          {runtime === 'claude' && (status === 'not-found' || status === 'outdated') && !installSuccess && (
            <div className="flex justify-center">
              <Button
                onClick={handleInstall}
                disabled={isInstalling}
                size="lg"
                className="gap-2"
              >
                {isInstalling ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t('claudeCode.install.inProgress')}
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4" />
                    {status === 'outdated'
                      ? t('claudeCode.install.updating')
                      : t('claudeCode.install.button')
                    }
                  </>
                )}
              </Button>
            </div>
          )}

          {/* Documentation link */}
          <div className="flex justify-center">
            <Button
              variant="link"
              size="sm"
              className="text-muted-foreground gap-1"
              onClick={() => window.electronAPI?.openExternal?.(
                runtime === 'codex' ? 'https://developers.openai.com/codex' : 'https://claude.ai/code'
              )}
            >
              {t(`${cliKeys}.learnMore`)}
              <ExternalLink className="h-3 w-3" />
            </Button>
          </div>
        </div>

        {/* Navigation buttons */}
        <div className="flex justify-between mt-8 pt-6 border-t border-border">
          <Button variant="outline" onClick={onBack}>
            {t('common:buttons.back')}
          </Button>

          <div className="flex gap-3">
            <Button variant="ghost" onClick={onSkip}>
              {t('common:buttons.skip')}
            </Button>
            <Button
              onClick={onNext}
              disabled={status === 'loading'}
            >
              {status === 'installed'
                ? t('common:buttons.continue')
                : t('common:buttons.continueAnyway')
              }
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
