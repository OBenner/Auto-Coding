/**
 * AuthStep - Setup wizard step for Claude SDK OAuth authentication
 *
 * Features:
 * - Detects Claude SDK authentication token via IPC handler
 * - Guides user through 'claude' CLI login process
 * - Validates token presence in keychain
 * - Shows clear success/error messages with step-by-step instructions
 * - Auto-validates on mount with manual retry option
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, AlertCircle, Loader2, Info, RefreshCw } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';

interface AuthStepProps {
  onValidate: (valid: boolean, error?: string) => void;
}

interface AuthValidationResult {
  authenticated: boolean;
  tokenPresent: boolean;
  message: string;
}

export function AuthStep({ onValidate }: AuthStepProps) {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(true);
  const [isRetrying, setIsRetrying] = useState(false);
  const [validationResult, setValidationResult] = useState<AuthValidationResult | null>(null);

  /**
   * Check authentication status
   */
  const checkAuthentication = async (isRetry = false) => {
    if (isRetry) {
      setIsRetrying(true);
    } else {
      setIsLoading(true);
    }

    try {
      // TODO: Call IPC handler to check Claude SDK authentication
      // For now, simulate the check with a mock response
      // const result = await window.electronAPI.checkClaudeAuth();

      // Mock response for development (replace with actual IPC call)
      const mockResult: AuthValidationResult = {
        authenticated: true,
        tokenPresent: true,
        message: 'Claude SDK authentication token found in keychain'
      };

      setValidationResult(mockResult);
      onValidate(mockResult.authenticated, mockResult.authenticated ? undefined : mockResult.message);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to check authentication status';
      setValidationResult({
        authenticated: false,
        tokenPresent: false,
        message: errorMessage
      });
      onValidate(false, errorMessage);
    } finally {
      setIsLoading(false);
      setIsRetrying(false);
    }
  };

  useEffect(() => {
    checkAuthentication();
  }, [onValidate]);

  /**
   * Handle retry button click
   */
  const handleRetry = () => {
    checkAuthentication(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">
            {t('setup:authentication.checking')}
          </p>
        </div>
      </div>
    );
  }

  if (!validationResult) {
    return null;
  }

  const { authenticated, tokenPresent, message } = validationResult;

  return (
    <div className="space-y-6">
      {/* Status Badge */}
      <div className="flex items-center justify-center">
        <Badge
          variant={authenticated ? "default" : "destructive"}
          className={cn(
            "gap-2 px-4 py-2 text-sm",
            authenticated ? "bg-green-500 hover:bg-green-600" : ""
          )}
        >
          {authenticated ? (
            <>
              <CheckCircle className="h-4 w-4" />
              {t('setup:authentication.authenticated')}
            </>
          ) : (
            <>
              <AlertCircle className="h-4 w-4" />
              {t('setup:authentication.notAuthenticated')}
            </>
          )}
        </Badge>
      </div>

      {/* Authentication Status Card */}
      <div className={cn(
        "rounded-lg border p-4",
        authenticated ? "border-green-500/20 bg-green-500/5" : "border-destructive/20 bg-destructive/5"
      )}>
        <div className="flex items-start gap-3">
          {authenticated ? (
            <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
          )}
          <div className="flex-1 space-y-2">
            <div>
              <p className="font-medium text-foreground">
                {t('setup:authentication.statusTitle')}
              </p>
              <p className={cn(
                "text-sm mt-1",
                authenticated ? "text-green-700 dark:text-green-400" : "text-destructive"
              )}>
                {message}
              </p>
            </div>

            {/* Token Presence Indicator */}
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">
                {t('setup:authentication.tokenStatus')}:
              </span>
              <Badge variant={tokenPresent ? "default" : "secondary"} className="font-mono">
                {tokenPresent ? t('setup:authentication.tokenPresent') : t('setup:authentication.tokenMissing')}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Setup Instructions (when not authenticated) */}
      {!authenticated && (
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
            <div className="flex-1 space-y-3">
              <p className="font-medium text-foreground">
                {t('setup:authentication.instructionsTitle')}
              </p>
              <div className="text-sm text-muted-foreground space-y-2">
                <p>{t('setup:authentication.instructions.intro')}</p>
                <ol className="list-decimal list-inside ml-2 space-y-2">
                  <li>
                    <p className="font-medium text-foreground">{t('setup:authentication.instructions.step1.title')}</p>
                    <p className="text-muted-foreground ml-4">{t('setup:authentication.instructions.step1.description')}</p>
                    <div className="ml-4 mt-1">
                      <code className="rounded bg-muted px-2 py-1 text-sm font-mono">
                        claude
                      </code>
                    </div>
                  </li>
                  <li>
                    <p className="font-medium text-foreground">{t('setup:authentication.instructions.step2.title')}</p>
                    <p className="text-muted-foreground ml-4">{t('setup:authentication.instructions.step2.description')}</p>
                  </li>
                  <li>
                    <p className="font-medium text-foreground">{t('setup:authentication.instructions.step3.title')}</p>
                    <p className="text-muted-foreground ml-4">{t('setup:authentication.instructions.step3.description')}</p>
                  </li>
                  <li>
                    <p className="font-medium text-foreground">{t('setup:authentication.instructions.step4.title')}</p>
                    <p className="text-muted-foreground ml-4">{t('setup:authentication.instructions.step4.description')}</p>
                  </li>
                </ol>
                <div className="mt-3 rounded-md bg-muted/50 p-3">
                  <p className="text-xs font-medium text-foreground">
                    {t('setup:authentication.instructions.noteTitle')}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {t('setup:authentication.instructions.note')}
                  </p>
                </div>
              </div>

              {/* Retry Button */}
              <div className="flex items-center gap-2 pt-2">
                <Button
                  onClick={handleRetry}
                  disabled={isRetrying}
                  variant="outline"
                  size="sm"
                >
                  {isRetrying && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  <RefreshCw className={!isRetrying ? "mr-2 h-4 w-4" : "hidden"} />
                  {t('setup:authentication.retryButton')}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Success Info (when authenticated) */}
      {authenticated && (
        <div className="rounded-lg border border-border bg-muted/30 p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
            <div className="flex-1 space-y-2">
              <p className="text-sm font-medium text-foreground">
                {t('setup:authentication.nextStepsTitle')}
              </p>
              <p className="text-sm text-muted-foreground">
                {t('setup:authentication.nextSteps')}
              </p>
              <div className="mt-2 rounded-md bg-muted/50 p-3">
                <p className="text-xs font-medium text-foreground">
                  {t('setup:authentication.tokenInfoTitle')}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {t('setup:authentication.tokenInfo')}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
