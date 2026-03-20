/**
 * TestRunStep - Setup wizard step for running hello-world test verification
 *
 * Features:
 * - Runs hello-world test spec via IPC handler
 * - Displays real-time test progress and output
 * - Shows test result with success/failure status
 * - Provides clear error messages and next steps
 * - Auto-runs test on mount with manual retry option
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, AlertCircle, Loader2, Info, RefreshCw, Terminal } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';

interface TestRunStepProps {
  onValidate: (valid: boolean, error?: string) => void;
}

interface TestOutput {
  timestamp: string;
  message: string;
  level: 'info' | 'error' | 'success';
}

interface TestResult {
  success: boolean;
  output: TestOutput[];
  duration: string;
  message: string;
  error?: string;
}

export function TestRunStep({ onValidate }: TestRunStepProps) {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(true);
  const [isRetrying, setIsRetrying] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  /**
   * Run hello-world test
   */
  const runTest = async (isRetry = false) => {
    if (isRetry) {
      setIsRetrying(true);
    } else {
      setIsLoading(true);
    }

    try {
      // TODO: Call IPC handler to run hello-world test
      // const result = await window.electronAPI.runHelloWorldTest();

      // Mock response for development (replace with actual IPC call)
      const mockResult: TestResult = {
        success: true,
        output: [
          { timestamp: '00:00:00', message: 'Starting hello-world test...', level: 'info' },
          { timestamp: '00:00:01', message: 'Checking Python environment...', level: 'info' },
          { timestamp: '00:00:02', message: '✓ Python 3.12.0 detected', level: 'success' },
          { timestamp: '00:00:03', message: 'Checking Claude SDK authentication...', level: 'info' },
          { timestamp: '00:00:04', message: '✓ Authentication token valid', level: 'success' },
          { timestamp: '00:00:05', message: 'Running test spec...', level: 'info' },
          { timestamp: '00:00:06', message: '✓ Test spec completed successfully', level: 'success' },
          { timestamp: '00:00:06', message: 'All checks passed!', level: 'success' },
        ],
        duration: '6s',
        message: 'Hello-world test completed successfully. Your Auto Code setup is working correctly.'
      };

      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 2000));

      setTestResult(mockResult);
      onValidate(mockResult.success, mockResult.success ? undefined : mockResult.error);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to run test';
      setTestResult({
        success: false,
        output: [
          { timestamp: '00:00:00', message: 'Starting hello-world test...', level: 'info' },
          { timestamp: '00:00:01', message: '✗ Test failed: ' + errorMessage, level: 'error' },
        ],
        duration: '1s',
        message: 'Test failed',
        error: errorMessage
      });
      onValidate(false, errorMessage);
    } finally {
      setIsLoading(false);
      setIsRetrying(false);
    }
  };

  useEffect(() => {
    runTest();
  }, [onValidate]);

  /**
   * Handle retry button click
   */
  const handleRetry = () => {
    setTestResult(null);
    runTest(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">
            {t('setup:testRun.running')}
          </p>
        </div>
      </div>
    );
  }

  if (!testResult) {
    return null;
  }

  const { success, output, duration, message, error } = testResult;

  return (
    <div className="space-y-6">
      {/* Status Badge */}
      <div className="flex items-center justify-center">
        <Badge
          variant={success ? "default" : "destructive"}
          className={cn(
            "gap-2 px-4 py-2 text-sm",
            success ? "bg-green-500 hover:bg-green-600" : ""
          )}
        >
          {success ? (
            <>
              <CheckCircle className="h-4 w-4" />
              {t('setup:testRun.success')}
            </>
          ) : (
            <>
              <AlertCircle className="h-4 w-4" />
              {t('setup:testRun.failed')}
            </>
          )}
        </Badge>
      </div>

      {/* Test Result Card */}
      <div className={cn(
        "rounded-lg border p-4",
        success ? "border-green-500/20 bg-green-500/5" : "border-destructive/20 bg-destructive/5"
      )}>
        <div className="flex items-start gap-3">
          {success ? (
            <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
          )}
          <div className="flex-1 space-y-2">
            <div>
              <p className="font-medium text-foreground">
                {t('setup:testRun.resultTitle')}
              </p>
              <p className={cn(
                "text-sm mt-1",
                success ? "text-green-700 dark:text-green-400" : "text-destructive"
              )}>
                {message}
              </p>
            </div>

            {/* Duration */}
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">
                {t('setup:testRun.duration')}:
              </span>
              <Badge variant="secondary" className="font-mono">
                {duration}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Test Output */}
      <div className="rounded-lg border border-border bg-muted/30 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Terminal className="h-4 w-4 text-muted-foreground" />
          <p className="text-sm font-medium text-foreground">
            {t('setup:testRun.outputTitle')}
          </p>
        </div>
        <div className="space-y-1">
          {output.map((line, index) => (
            <div
              key={index}
              className={cn(
                "font-mono text-xs",
                line.level === 'error' && "text-destructive",
                line.level === 'success' && "text-green-600 dark:text-green-400",
                line.level === 'info' && "text-muted-foreground"
              )}
            >
              <span className="text-muted-foreground/70">[{line.timestamp}]</span>{' '}
              {line.message}
            </div>
          ))}
        </div>
      </div>

      {/* Error Details (if failed) */}
      {!success && error && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
            <div className="flex-1 space-y-2">
              <p className="font-medium text-foreground">
                {t('setup:testRun.errorTitle')}
              </p>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {error}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Next Steps (when successful) */}
      {success && (
        <div className="rounded-lg border border-border bg-muted/30 p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
            <div className="flex-1 space-y-2">
              <p className="text-sm font-medium text-foreground">
                {t('setup:testRun.nextStepsTitle')}
              </p>
              <p className="text-sm text-muted-foreground">
                {t('setup:testRun.nextSteps')}
              </p>
              <ul className="list-disc list-inside ml-2 space-y-1 text-sm text-muted-foreground">
                <li>{t('setup:testRun.nextSteps.createSpec')}</li>
                <li>{t('setup:testRun.nextSteps.runBuild')}</li>
                <li>{t('setup:testRun.nextSteps.exploreFeatures')}</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Retry Button (when failed) */}
      {!success && (
        <div className="flex items-center gap-2 pt-2">
          <Button
            onClick={handleRetry}
            disabled={isRetrying}
            variant="outline"
            size="sm"
          >
            {isRetrying && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <RefreshCw className={!isRetrying ? "mr-2 h-4 w-4" : "hidden"} />
            {t('setup:testRun.retryButton')}
          </Button>
        </div>
      )}
    </div>
  );
}
