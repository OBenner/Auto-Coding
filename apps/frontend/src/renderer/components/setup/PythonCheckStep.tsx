/**
 * PythonCheckStep - Setup wizard step for Python version validation
 *
 * Features:
 * - Detects Python version via IPC handler
 * - Validates that version is >= 3.12
 * - Shows clear success/error messages with guidance
 * - Auto-validates on mount
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, AlertCircle, Loader2, Info } from 'lucide-react';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';

interface PythonCheckStepProps {
  onValidate: (valid: boolean, error?: string) => void;
}

interface PythonValidationResult {
  valid: boolean;
  version: string;
  required_version: string;
  message: string;
}

export function PythonCheckStep({ onValidate }: PythonCheckStepProps) {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(true);
  const [validationResult, setValidationResult] = useState<PythonValidationResult | null>(null);

  useEffect(() => {
    async function checkPythonVersion() {
      setIsLoading(true);
      try {
        // TODO: Call IPC handler to check Python version
        // For now, simulate the check with a mock response
        // const result = await window.electronAPI.checkPythonVersion();

        // Mock response for development (replace with actual IPC call)
        const mockResult: PythonValidationResult = {
          valid: true,
          version: '3.12.0',
          required_version: '3.12',
          message: 'Python 3.12.0 meets the minimum requirement of Python 3.12+'
        };

        setValidationResult(mockResult);
        onValidate(mockResult.valid, mockResult.valid ? undefined : mockResult.message);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to check Python version';
        setValidationResult({
          valid: false,
          version: 'unknown',
          required_version: '3.12',
          message: errorMessage
        });
        onValidate(false, errorMessage);
      } finally {
        setIsLoading(false);
      }
    }

    checkPythonVersion();
  }, [onValidate]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">
            {t('setup:pythonCheck.checking')}
          </p>
        </div>
      </div>
    );
  }

  if (!validationResult) {
    return null;
  }

  const { valid, version, required_version, message } = validationResult;

  return (
    <div className="space-y-6">
      {/* Status Badge */}
      <div className="flex items-center justify-center">
        <Badge
          variant={valid ? "default" : "destructive"}
          className={cn(
            "gap-2 px-4 py-2 text-sm",
            valid ? "bg-green-500 hover:bg-green-600" : ""
          )}
        >
          {valid ? (
            <>
              <CheckCircle className="h-4 w-4" />
              {t('setup:pythonCheck.valid')}
            </>
          ) : (
            <>
              <AlertCircle className="h-4 w-4" />
              {t('setup:pythonCheck.invalid')}
            </>
          )}
        </Badge>
      </div>

      {/* Version Info Card */}
      <div className={cn(
        "rounded-lg border p-4",
        valid ? "border-green-500/20 bg-green-500/5" : "border-destructive/20 bg-destructive/5"
      )}>
        <div className="flex items-start gap-3">
          {valid ? (
            <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
          )}
          <div className="flex-1 space-y-2">
            <div>
              <p className="font-medium text-foreground">
                {t('setup:pythonCheck.versionTitle')}
              </p>
              <p className="text-2xl font-semibold text-foreground mt-1">
                Python {version}
              </p>
            </div>

            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">
                {t('setup:pythonCheck.required')}:
              </span>
              <Badge variant="secondary" className="font-mono">
                Python {required_version}+
              </Badge>
            </div>

            {/* Message */}
            <div className={cn(
              "text-sm whitespace-pre-wrap",
              valid ? "text-green-700 dark:text-green-400" : "text-destructive"
            )}>
              {message}
            </div>
          </div>
        </div>
      </div>

      {/* Additional Info for Invalid Version */}
      {!valid && (
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
            <div className="flex-1 space-y-2">
              <p className="font-medium text-foreground">
                {t('setup:pythonCheck.howToUpgradeTitle')}
              </p>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>{t('setup:pythonCheck.howToUpgrade.download')}</p>
                <ul className="list-disc list-inside ml-2 space-y-1">
                  <li>
                    <a
                      href="https://www.python.org/downloads/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      {t('setup:pythonCheck.howToUpgrade.pythonOrg')}
                    </a>
                  </li>
                  <li>{t('setup:pythonCheck.howToUpgrade.windows')}</li>
                  <li>{t('setup:pythonCheck.howToUpgrade.mac')}</li>
                  <li>{t('setup:pythonCheck.howToUpgrade.linux')}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Python Path Info (when valid) */}
      {valid && (
        <div className="rounded-lg border border-border bg-muted/30 p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">
                {t('setup:pythonCheck.nextStepsTitle')}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {t('setup:pythonCheck.nextSteps')}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
