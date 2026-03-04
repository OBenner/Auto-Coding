import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary component to gracefully handle render errors.
 * Prevents the entire page from crashing when a component fails.
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error to console for debugging
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorBoundaryContent
          error={this.state.error}
          onReset={this.handleReset}
        />
      );
    }

    return this.props.children;
  }
}

/**
 * Inner component that uses hooks for i18n
 * Separated from the class component to allow hook usage
 */
function ErrorBoundaryContent({
  error,
  onReset
}: {
  error: Error | null;
  onReset: () => void;
}) {
  const { t } = useTranslation(['errors', 'common']);

  return (
    <Card className="border-destructive m-4">
      <CardContent className="pt-6">
        <div className="flex flex-col items-center gap-4 text-center">
          <AlertTriangle className="h-10 w-10 text-destructive" />
          <div className="space-y-2">
            <h3 className="font-semibold text-lg">
              {t('errors:errorBoundary.title')}
            </h3>
            <p className="text-sm text-muted-foreground">
              {t('errors:errorBoundary.description')}
            </p>
            {error && (
              <p className="text-xs text-muted-foreground font-mono bg-muted p-2 rounded max-w-md overflow-auto">
                {error.message}
              </p>
            )}
          </div>
          <Button onClick={onReset} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            {t('errors:errorBoundary.tryAgain')}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
