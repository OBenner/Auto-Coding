/**
 * EnvConfigStep - Setup wizard step for .env file creation
 *
 * Features:
 * - Displays summary of configuration from previous steps
 * - Shows configured settings (Python, auth, Graphiti)
 * - Creates .env file with user's configuration
 * - Shows success message after creation
 * - Allows retry if creation fails
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, AlertCircle, Loader2, Info, FileText, Save, RefreshCw } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';

interface EnvConfigStepProps {
  onValidate: (valid: boolean, error?: string) => void;
}

interface EnvConfigSummary {
  pythonVersion: string;
  pythonValid: boolean;
  claudeAuthConfigured: boolean;
  graphitiEnabled: boolean;
  graphitiProvider: string;
  graphitiConfigured: boolean;
}

interface EnvCreationResult {
  success: boolean;
  envPath: string;
  message: string;
  createdNew: boolean;
}

export function EnvConfigStep({ onValidate }: EnvConfigStepProps) {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [configSummary, setConfigSummary] = useState<EnvConfigSummary | null>(null);
  const [creationResult, setCreationResult] = useState<EnvCreationResult | null>(null);

  /**
   * Load configuration summary from previous steps
   */
  useEffect(() => {
    async function loadConfigSummary() {
      setIsLoading(true);
      try {
        // TODO: Call IPC handler to get configuration summary
        // For now, simulate the summary with mock data
        // const summary = await window.electronAPI.getSetupConfigSummary();

        // Mock response for development (replace with actual IPC call)
        await new Promise(resolve => setTimeout(resolve, 800)); // Simulate delay

        const mockSummary: EnvConfigSummary = {
          pythonVersion: '3.12.0',
          pythonValid: true,
          claudeAuthConfigured: true,
          graphitiEnabled: true,
          graphitiProvider: 'openai',
          graphitiConfigured: true,
        };

        setConfigSummary(mockSummary);

        // Don't validate yet - wait for user to create .env file
        onValidate(false, 'Please create .env file to continue');
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to load configuration summary';
        setConfigSummary({
          pythonVersion: 'unknown',
          pythonValid: false,
          claudeAuthConfigured: false,
          graphitiEnabled: false,
          graphitiProvider: 'none',
          graphitiConfigured: false,
        });
        onValidate(false, errorMessage);
      } finally {
        setIsLoading(false);
      }
    }

    loadConfigSummary();
  }, [onValidate]);

  /**
   * Create .env file with configured settings
   */
  const createEnvFile = async (isRetry = false) => {
    if (isRetry) {
      setIsRetrying(true);
    } else {
      setIsCreating(true);
    }

    try {
      // TODO: Call IPC handler to create .env file
      // For now, simulate the creation with a mock response
      // const result = await window.electronAPI.createSetupEnvFile();

      // Mock response for development (replace with actual IPC call)
      await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate network delay

      const mockResult: EnvCreationResult = {
        success: true,
        envPath: 'apps/backend/.env',
        message: 'Successfully created .env file with your configuration',
        createdNew: true,
      };

      setCreationResult(mockResult);

      if (mockResult.success) {
        onValidate(true);
      } else {
        onValidate(false, mockResult.message);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create .env file';
      setCreationResult({
        success: false,
        envPath: '',
        message: errorMessage,
        createdNew: false,
      });
      onValidate(false, errorMessage);
    } finally {
      setIsCreating(false);
      setIsRetrying(false);
    }
  };

  /**
   * Handle retry button click
   */
  const handleRetry = () => {
    setCreationResult(null);
    createEnvFile(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">
            {t('setup:envConfig.loading')}
          </p>
        </div>
      </div>
    );
  }

  if (!configSummary) {
    return null;
  }

  const { pythonVersion, pythonValid, claudeAuthConfigured, graphitiEnabled, graphitiProvider, graphitiConfigured } = configSummary;

  return (
    <div className="space-y-6">
      {/* Configuration Summary Header */}
      <div className="rounded-lg border border-border bg-muted/30 p-4">
        <div className="flex items-start gap-3">
          <FileText className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-foreground">
              {t('setup:envConfig.summaryTitle')}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              {t('setup:envConfig.summaryDescription')}
            </p>
          </div>
        </div>
      </div>

      {/* Python Configuration */}
      <div className={cn(
        "rounded-lg border p-4",
        pythonValid ? "border-green-500/20 bg-green-500/5" : "border-destructive/20 bg-destructive/5"
      )}>
        <div className="flex items-start gap-3">
          {pythonValid ? (
            <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
          )}
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between">
              <p className="font-medium text-foreground">
                {t('setup:envConfig.python.title')}
              </p>
              <Badge variant={pythonValid ? "default" : "secondary"} className="font-mono text-xs">
                Python {pythonVersion}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {pythonValid
                ? t('setup:envConfig.python.valid')
                : t('setup:envConfig.python.invalid')
              }
            </p>
          </div>
        </div>
      </div>

      {/* Claude SDK Authentication */}
      <div className={cn(
        "rounded-lg border p-4",
        claudeAuthConfigured ? "border-green-500/20 bg-green-500/5" : "border-destructive/20 bg-destructive/5"
      )}>
        <div className="flex items-start gap-3">
          {claudeAuthConfigured ? (
            <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
          )}
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between">
              <p className="font-medium text-foreground">
                {t('setup:envConfig.authentication.title')}
              </p>
              <Badge variant={claudeAuthConfigured ? "default" : "secondary"}>
                {claudeAuthConfigured
                  ? t('setup:envConfig.authentication.configured')
                  : t('setup:envConfig.authentication.notConfigured')
                }
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {claudeAuthConfigured
                ? t('setup:envConfig.authentication.valid')
                : t('setup:envConfig.authentication.invalid')
              }
            </p>
          </div>
        </div>
      </div>

      {/* Graphiti Memory System */}
      <div className={cn(
        "rounded-lg border p-4",
        graphitiConfigured ? "border-green-500/20 bg-green-500/5" : "border-destructive/20 bg-destructive/5"
      )}>
        <div className="flex items-start gap-3">
          {graphitiConfigured ? (
            <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
          )}
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between">
              <p className="font-medium text-foreground">
                {t('setup:envConfig.graphiti.title')}
              </p>
              <div className="flex items-center gap-2">
                <Badge variant={graphitiEnabled ? "default" : "secondary"} className="font-mono text-xs">
                  {graphitiProvider}
                </Badge>
                <Badge variant={graphitiConfigured ? "default" : "secondary"}>
                  {graphitiEnabled
                    ? t('setup:envConfig.graphiti.enabled')
                    : t('setup:envConfig.graphiti.disabled')
                  }
                </Badge>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              {graphitiConfigured
                ? t('setup:envConfig.graphiti.valid', { provider: graphitiProvider })
                : t('setup:envConfig.graphiti.invalid')
              }
            </p>
          </div>
        </div>
      </div>

      {/* Creation Status */}
      {creationResult && (
        <div className={cn(
          "rounded-lg border p-4",
          creationResult.success ? "border-green-500/20 bg-green-500/5" : "border-destructive/20 bg-destructive/5"
        )}>
          <div className="flex items-start gap-3">
            {creationResult.success ? (
              <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
            ) : (
              <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
            )}
            <div className="flex-1 space-y-2">
              <p className="font-medium text-foreground">
                {creationResult.success
                  ? t('setup:envConfig.successTitle')
                  : t('setup:envConfig.errorTitle')
                }
              </p>
              <p className={cn(
                "text-sm",
                creationResult.success ? "text-green-700 dark:text-green-400" : "text-destructive"
              )}>
                {creationResult.message}
              </p>
              {creationResult.success && creationResult.envPath && (
                <div className="mt-2 rounded-md bg-muted/50 p-3">
                  <p className="text-xs font-medium text-foreground">
                    {t('setup:envConfig.fileLocation')}
                  </p>
                  <p className="text-xs font-mono text-muted-foreground mt-1">
                    {creationResult.envPath}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-end gap-2 pt-2">
        {creationResult && !creationResult.success && (
          <Button
            onClick={handleRetry}
            disabled={isRetrying}
            variant="outline"
          >
            {isRetrying && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <RefreshCw className={!isRetrying ? "mr-2 h-4 w-4" : "hidden"} />
            {t('setup:envConfig.actions.retry')}
          </Button>
        )}

        {!creationResult?.success && (
          <Button
            onClick={() => createEnvFile()}
            disabled={isCreating || isRetrying}
          >
            {isCreating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <Save className={!isCreating ? "mr-2 h-4 w-4" : "hidden"} />
            {t('setup:envConfig.actions.create')}
          </Button>
        )}
      </div>

      {/* Information Card */}
      {!creationResult?.success && (
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
            <div className="flex-1 space-y-2">
              <p className="font-medium text-foreground">
                {t('setup:envConfig.infoTitle')}
              </p>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>{t('setup:envConfig.info.intro')}</p>
                <ul className="list-disc list-inside ml-2 space-y-1">
                  <li>{t('setup:envConfig.info.step1')}</li>
                  <li>{t('setup:envConfig.info.step2')}</li>
                  <li>{t('setup:envConfig.info.step3')}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Success Info */}
      {creationResult && creationResult.success && (
        <div className="rounded-lg border border-border bg-muted/30 p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
            <div className="flex-1 space-y-2">
              <p className="text-sm font-medium text-foreground">
                {t('setup:envConfig.nextStepsTitle')}
              </p>
              <p className="text-sm text-muted-foreground">
                {t('setup:envConfig.nextSteps')}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
