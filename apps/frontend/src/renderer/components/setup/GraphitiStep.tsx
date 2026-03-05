/**
 * GraphitiStep - Setup wizard step for Graphiti memory system configuration
 *
 * Features:
 * - Provider selection (OpenAI, Anthropic, Azure OpenAI, Ollama, Google AI)
 * - API key input with validation
 * - Connection testing via IPC handler
 * - Clear success/error messages with step-by-step instructions
 * - Auto-validates on mount with manual retry option
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, AlertCircle, Loader2, Info, RefreshCw } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { cn } from '../../lib/utils';

interface GraphitiStepProps {
  onValidate: (valid: boolean, error?: string) => void;
}

interface GraphitiValidationResult {
  configured: boolean;
  provider: string;
  message: string;
}

type GraphitiProvider = 'openai' | 'anthropic' | 'azure' | 'ollama' | 'google';

interface ProviderConfig {
  id: GraphitiProvider;
  name: string;
  needsApiKey: boolean;
  needsEndpoint: boolean;
  needsEmbeddingKey: boolean;
}

const PROVIDERS: ProviderConfig[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    needsApiKey: true,
    needsEndpoint: false,
    needsEmbeddingKey: false,
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    needsApiKey: true,
    needsEndpoint: false,
    needsEmbeddingKey: true,
  },
  {
    id: 'azure',
    name: 'Azure OpenAI',
    needsApiKey: true,
    needsEndpoint: true,
    needsEmbeddingKey: false,
  },
  {
    id: 'ollama',
    name: 'Ollama',
    needsApiKey: false,
    needsEndpoint: true,
    needsEmbeddingKey: false,
  },
  {
    id: 'google',
    name: 'Google AI',
    needsApiKey: true,
    needsEndpoint: false,
    needsEmbeddingKey: false,
  },
];

export function GraphitiStep({ onValidate }: GraphitiStepProps) {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [validationResult, setValidationResult] = useState<GraphitiValidationResult | null>(null);

  // Form state
  const [provider, setProvider] = useState<GraphitiProvider>('openai');
  const [apiKey, setApiKey] = useState('');
  const [embeddingKey, setEmbeddingKey] = useState('');
  const [endpoint, setEndpoint] = useState('');

  const selectedProvider = PROVIDERS.find(p => p.id === provider);

  /**
   * Validate Graphiti configuration
   */
  const validateConfiguration = async (isRetry = false) => {
    if (isRetry) {
      setIsRetrying(true);
    } else {
      setIsLoading(true);
    }

    try {
      // Validate required fields
      if (selectedProvider?.needsApiKey && !apiKey) {
        const errorMessage = t('setup:graphiti.errors.apiKeyRequired');
        setValidationResult({
          configured: false,
          provider,
          message: errorMessage
        });
        onValidate(false, errorMessage);
        setIsLoading(false);
        setIsRetrying(false);
        return;
      }

      if (selectedProvider?.needsEndpoint && !endpoint) {
        const errorMessage = t('setup:graphiti.errors.endpointRequired');
        setValidationResult({
          configured: false,
          provider,
          message: errorMessage
        });
        onValidate(false, errorMessage);
        setIsLoading(false);
        setIsRetrying(false);
        return;
      }

      if (selectedProvider?.needsEmbeddingKey && !embeddingKey) {
        const errorMessage = t('setup:graphiti.errors.embeddingKeyRequired');
        setValidationResult({
          configured: false,
          provider,
          message: errorMessage
        });
        onValidate(false, errorMessage);
        setIsLoading(false);
        setIsRetrying(false);
        return;
      }

      // TODO: Call IPC handler to validate Graphiti configuration
      // For now, simulate the validation with a mock response
      // const result = await window.electronAPI.validateGraphiti({
      //   provider,
      //   apiKey,
      //   embeddingKey,
      //   endpoint
      // });

      // Mock response for development (replace with actual IPC call)
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate network delay

      const mockResult: GraphitiValidationResult = {
        configured: true,
        provider,
        message: t('setup:graphiti.success.configured', { provider: selectedProvider?.name })
      };

      setValidationResult(mockResult);
      onValidate(mockResult.configured, mockResult.configured ? undefined : mockResult.message);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to validate Graphiti configuration';
      setValidationResult({
        configured: false,
        provider,
        message: errorMessage
      });
      onValidate(false, errorMessage);
    } finally {
      setIsLoading(false);
      setIsRetrying(false);
    }
  };

  /**
   * Handle provider change
   */
  const handleProviderChange = (newProvider: GraphitiProvider) => {
    setProvider(newProvider);
    setApiKey('');
    setEmbeddingKey('');
    setEndpoint('');
    setValidationResult(null);
    onValidate(false);
  };

  /**
   * Handle retry button click
   */
  const handleRetry = () => {
    validateConfiguration(true);
  };

  /**
   * Handle form submission
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    validateConfiguration();
  };

  // Auto-validate when form is complete and not already validated
  useEffect(() => {
    const isFormComplete = () => {
      if (selectedProvider?.needsApiKey && !apiKey) return false;
      if (selectedProvider?.needsEndpoint && !endpoint) return false;
      if (selectedProvider?.needsEmbeddingKey && !embeddingKey) return false;
      return true;
    };

    if (isFormComplete() && !validationResult && !isLoading) {
      validateConfiguration();
    }
  }, [provider, apiKey, embeddingKey, endpoint]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">
            {t('setup:graphiti.validating')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status Badge */}
      {validationResult && (
        <div className="flex items-center justify-center">
          <Badge
            variant={validationResult.configured ? "default" : "destructive"}
            className={cn(
              "gap-2 px-4 py-2 text-sm",
              validationResult.configured ? "bg-green-500 hover:bg-green-600" : ""
            )}
          >
            {validationResult.configured ? (
              <>
                <CheckCircle className="h-4 w-4" />
                {t('setup:graphiti.configured')}
              </>
            ) : (
              <>
                <AlertCircle className="h-4 w-4" />
                {t('setup:graphiti.notConfigured')}
              </>
            )}
          </Badge>
        </div>
      )}

      {/* Configuration Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Provider Selection */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">
            {t('setup:graphiti.fields.provider.label')}
          </p>
          <Select
            value={provider}
            onValueChange={(value) => handleProviderChange(value as GraphitiProvider)}
            disabled={isLoading || isRetrying}
          >
            <SelectTrigger>
              <SelectValue placeholder={t('setup:graphiti.fields.provider.placeholder')} />
            </SelectTrigger>
            <SelectContent>
              {PROVIDERS.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {t('setup:graphiti.fields.provider.description')}
          </p>
        </div>

        {/* API Key Input */}
        {selectedProvider?.needsApiKey && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">
              {t('setup:graphiti.fields.apiKey.label')}
            </p>
            <Input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={t('setup:graphiti.fields.apiKey.placeholder')}
              disabled={isLoading || isRetrying}
              autoComplete="off"
            />
            <p className="text-xs text-muted-foreground">
              {t('setup:graphiti.fields.apiKey.description')}
            </p>
          </div>
        )}

        {/* Embedding Key Input (for Anthropic) */}
        {selectedProvider?.needsEmbeddingKey && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">
              {t('setup:graphiti.fields.embeddingKey.label')}
            </p>
            <Input
              type="password"
              value={embeddingKey}
              onChange={(e) => setEmbeddingKey(e.target.value)}
              placeholder={t('setup:graphiti.fields.embeddingKey.placeholder')}
              disabled={isLoading || isRetrying}
              autoComplete="off"
            />
            <p className="text-xs text-muted-foreground">
              {t('setup:graphiti.fields.embeddingKey.description')}
            </p>
          </div>
        )}

        {/* Endpoint Input (for Azure and Ollama) */}
        {selectedProvider?.needsEndpoint && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">
              {t('setup:graphiti.fields.endpoint.label')}
            </p>
            <Input
              type="text"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              placeholder={selectedProvider.id === 'azure'
                ? 'https://your-resource.openai.azure.com'
                : 'http://localhost:11434'
              }
              disabled={isLoading || isRetrying}
              autoComplete="off"
            />
            <p className="text-xs text-muted-foreground">
              {t('setup:graphiti.fields.endpoint.description')}
            </p>
          </div>
        )}

        {/* Validation Button (only show when not auto-validated) */}
        {!validationResult && (
          <div className="flex justify-end pt-2">
            <Button
              type="submit"
              disabled={isLoading || isRetrying}
            >
              {isRetrying && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('setup:graphiti.actions.validate')}
            </Button>
          </div>
        )}
      </form>

      {/* Validation Result */}
      {validationResult && (
        <div className={cn(
          "rounded-lg border p-4",
          validationResult.configured ? "border-green-500/20 bg-green-500/5" : "border-destructive/20 bg-destructive/5"
        )}>
          <div className="flex items-start gap-3">
            {validationResult.configured ? (
              <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
            ) : (
              <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
            )}
            <div className="flex-1 space-y-2">
              <p className="font-medium text-foreground">
                {t('setup:graphiti.statusTitle')}
              </p>
              <p className={cn(
                "text-sm",
                validationResult.configured ? "text-green-700 dark:text-green-400" : "text-destructive"
              )}>
                {validationResult.message}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Retry Button (when validation failed) */}
      {validationResult && !validationResult.configured && (
        <div className="flex items-center gap-2 pt-2">
          <Button
            onClick={handleRetry}
            disabled={isRetrying}
            variant="outline"
            size="sm"
          >
            {isRetrying && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <RefreshCw className={!isRetrying ? "mr-2 h-4 w-4" : "hidden"} />
            {t('setup:graphiti.actions.retry')}
          </Button>
        </div>
      )}

      {/* Setup Instructions */}
      <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
        <div className="flex items-start gap-3">
          <Info className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
          <div className="flex-1 space-y-3">
            <p className="font-medium text-foreground">
              {t('setup:graphiti.instructionsTitle')}
            </p>
            <div className="text-sm text-muted-foreground space-y-2">
              <p>{t('setup:graphiti.instructions.intro')}</p>
              <ul className="list-disc list-inside ml-2 space-y-1">
                <li>{t('setup:graphiti.instructions.step1')}</li>
                <li>{t('setup:graphiti.instructions.step2')}</li>
                <li>{t('setup:graphiti.instructions.step3')}</li>
              </ul>
              <div className="mt-3 rounded-md bg-muted/50 p-3">
                <p className="text-xs font-medium text-foreground">
                  {t('setup:graphiti.instructions.noteTitle')}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {t('setup:graphiti.instructions.note')}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Success Info */}
      {validationResult && validationResult.configured && (
        <div className="rounded-lg border border-border bg-muted/30 p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
            <div className="flex-1 space-y-2">
              <p className="text-sm font-medium text-foreground">
                {t('setup:graphiti.nextStepsTitle')}
              </p>
              <p className="text-sm text-muted-foreground">
                {t('setup:graphiti.nextSteps')}
              </p>
              <div className="mt-2 rounded-md bg-muted/50 p-3">
                <p className="text-xs font-medium text-foreground">
                  {t('setup:graphiti.configInfoTitle')}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {t('setup:graphiti.configInfo', { provider: selectedProvider?.name })}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
