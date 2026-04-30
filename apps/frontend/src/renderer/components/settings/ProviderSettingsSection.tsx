import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Switch } from '../ui/switch';
import { SettingsSection } from './SettingsSection';
import type {
  AgentRuntimeMode,
  AIEngineProvider,
  AIProviderConfig,
  ProviderConfigValidation
} from '../../../shared/types/settings';

type ProviderSettingsSectionProps = Record<string, never>;

const USE_GLOBAL_RUNTIME_MODE = '__global__';

const PROVIDER_OPTIONS: Array<{
  value: AIEngineProvider;
  labelKey: string;
  descriptionKey: string;
}> = [
  { value: 'claude', labelKey: 'settings:aiProvider.providers.claude.name', descriptionKey: 'settings:aiProvider.providers.claude.description' },
  { value: 'openai', labelKey: 'settings:aiProvider.providers.openai.name', descriptionKey: 'settings:aiProvider.providers.openai.description' },
  { value: 'google', labelKey: 'settings:aiProvider.providers.google.name', descriptionKey: 'settings:aiProvider.providers.google.description' },
  { value: 'litellm', labelKey: 'settings:aiProvider.providers.litellm.name', descriptionKey: 'settings:aiProvider.providers.litellm.description' },
  { value: 'openrouter', labelKey: 'settings:aiProvider.providers.openrouter.name', descriptionKey: 'settings:aiProvider.providers.openrouter.description' },
  { value: 'zhipuai', labelKey: 'settings:aiProvider.providers.zhipuai.name', descriptionKey: 'settings:aiProvider.providers.zhipuai.description' },
  { value: 'ollama', labelKey: 'settings:aiProvider.providers.ollama.name', descriptionKey: 'settings:aiProvider.providers.ollama.description' },
];

const RUNTIME_MODE_OPTIONS: Array<{
  value: AgentRuntimeMode;
  labelKey: string;
  descriptionKey: string;
}> = [
  { value: 'full_autonomous', labelKey: 'settings:aiProvider.runtimeModes.fullAutonomous.name', descriptionKey: 'settings:aiProvider.runtimeModes.fullAutonomous.description' },
  { value: 'generic_edit', labelKey: 'settings:aiProvider.runtimeModes.genericEdit.name', descriptionKey: 'settings:aiProvider.runtimeModes.genericEdit.description' },
  { value: 'patch_proposal', labelKey: 'settings:aiProvider.runtimeModes.patchProposal.name', descriptionKey: 'settings:aiProvider.runtimeModes.patchProposal.description' },
  { value: 'analysis_only', labelKey: 'settings:aiProvider.runtimeModes.analysisOnly.name', descriptionKey: 'settings:aiProvider.runtimeModes.analysisOnly.description' },
];

function ProviderField({
  id,
  label,
  description,
  value,
  onChange,
  type = 'text',
  placeholder
}: {
  id: string;
  label: string;
  description: string;
  value: string;
  onChange: (value: string) => void;
  type?: 'text' | 'password';
  placeholder?: string;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-sm font-medium text-foreground">
        {label}
      </Label>
      <Input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="max-w-xl"
      />
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  );
}

/**
 * Provider settings component for configuring AI providers and runtime modes.
 */
export function ProviderSettingsSection(_props: ProviderSettingsSectionProps) {
  const { t } = useTranslation(['settings', 'common']);
  const [config, setConfig] = useState<AIProviderConfig>({
    provider: 'claude',
    runtimeMode: 'full_autonomous'
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [validationStatus, setValidationStatus] = useState<ProviderConfigValidation | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await window.electronAPI?.getProviderConfig?.();
        if (!cancelled && result?.success && result.data) {
          setConfig({
            ...result.data,
            provider: result.data.provider ?? 'claude',
            runtimeMode: result.data.runtimeMode ?? 'full_autonomous'
          });
        }
      } catch {
        if (!cancelled) {
          setSaveStatus('error');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedProvider = useMemo(
    () => PROVIDER_OPTIONS.find((provider) => provider.value === config.provider) ?? PROVIDER_OPTIONS[0],
    [config.provider]
  );

  const activeRuntimeMode = config.runtimeMode ?? 'full_autonomous';
  const runtimeFallbackEnabled = config.runtimeFallbackEnabled ?? false;
  const nonClaudeFullAutonomous = config.provider !== 'claude' && activeRuntimeMode === 'full_autonomous';
  let compatibilityMessageKey = 'settings:aiProvider.compatibility.claudeFirst';
  if (nonClaudeFullAutonomous) {
    compatibilityMessageKey = runtimeFallbackEnabled
      ? 'settings:aiProvider.compatibility.fallbackActive'
      : 'settings:aiProvider.compatibility.nonClaudeFullAutonomous';
  }

  const updateConfig = (updates: Partial<AIProviderConfig>) => {
    setConfig((current) => ({ ...current, ...updates }));
    setSaveStatus('idle');
    setValidationStatus(null);
  };

  const handleProviderChange = (provider: AIEngineProvider) => {
    updateConfig({
      provider,
      runtimeMode: provider === 'claude' ? 'full_autonomous' : config.runtimeMode
    });
  };

  const handleRuntimeOverrideChange = (
    key: 'plannerRuntimeMode' | 'coderRuntimeMode' | 'qaReviewerRuntimeMode' | 'qaFixerRuntimeMode',
    value: string
  ) => {
    updateConfig({
      [key]: value === USE_GLOBAL_RUNTIME_MODE ? '' : value
    } as Partial<AIProviderConfig>);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveStatus('idle');
    try {
      const result = await window.electronAPI?.updateProviderConfig?.(config);
      setSaveStatus(result?.success ? 'success' : 'error');
    } catch {
      setSaveStatus('error');
    } finally {
      setSaving(false);
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    setSaveStatus('idle');
    setValidationStatus(null);
    try {
      const saveResult = await window.electronAPI?.updateProviderConfig?.(config);
      if (!saveResult?.success) {
        setSaveStatus('error');
        return;
      }
      const validationResult = await window.electronAPI?.validateProviderConfig?.();
      setValidationStatus(
        validationResult?.success ? validationResult.data ?? null : null
      );
      setSaveStatus(validationResult?.success ? 'success' : 'error');
    } catch {
      setSaveStatus('error');
    } finally {
      setValidating(false);
    }
  };

  const renderRuntimeSelect = (
    id: string,
    value: AgentRuntimeMode | '' | undefined,
    onChange: (value: string) => void,
    includeGlobal: boolean
  ) => (
    <Select value={value || USE_GLOBAL_RUNTIME_MODE} onValueChange={onChange}>
      <SelectTrigger id={id} className="w-full max-w-xl">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {includeGlobal && (
          <SelectItem value={USE_GLOBAL_RUNTIME_MODE}>
            {t('settings:aiProvider.runtimeModes.useGlobal')}
          </SelectItem>
        )}
        {RUNTIME_MODE_OPTIONS.map((mode) => (
          <SelectItem key={mode.value} value={mode.value}>
            <div className="flex flex-col items-start">
              <span className="font-medium">{t(mode.labelKey)}</span>
              <span className="text-xs text-muted-foreground">{t(mode.descriptionKey)}</span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );

  const renderProviderConfiguration = () => {
    switch (config.provider) {
      case 'openai':
        return (
          <>
            <ProviderField
              id="openaiApiKey"
              label={t('settings:aiProvider.apiKeys.openai.label')}
              description={t('settings:aiProvider.apiKeys.openai.description')}
              placeholder={t('settings:aiProvider.apiKeys.openai.placeholder')}
              type="password"
              value={config.openaiApiKey ?? ''}
              onChange={(openaiApiKey) => updateConfig({ openaiApiKey })}
            />
            <ProviderField
              id="openaiModel"
              label={t('settings:aiProvider.providerModels.openai.label')}
              description={t('settings:aiProvider.providerModels.openai.description')}
              placeholder={t('settings:aiProvider.providerModels.openai.placeholder')}
              value={config.openaiModel ?? ''}
              onChange={(openaiModel) => updateConfig({ openaiModel })}
            />
            <ProviderField
              id="openaiBaseUrl"
              label={t('settings:aiProvider.baseUrls.openai.label')}
              description={t('settings:aiProvider.baseUrls.openai.description')}
              placeholder={t('settings:aiProvider.baseUrls.openai.placeholder')}
              value={config.openaiBaseUrl ?? ''}
              onChange={(openaiBaseUrl) => updateConfig({ openaiBaseUrl })}
            />
          </>
        );
      case 'google':
        return (
          <>
            <ProviderField
              id="googleApiKey"
              label={t('settings:aiProvider.apiKeys.google.label')}
              description={t('settings:aiProvider.apiKeys.google.description')}
              placeholder={t('settings:aiProvider.apiKeys.google.placeholder')}
              type="password"
              value={config.googleApiKey ?? ''}
              onChange={(googleApiKey) => updateConfig({ googleApiKey })}
            />
            <ProviderField
              id="googleModel"
              label={t('settings:aiProvider.providerModels.google.label')}
              description={t('settings:aiProvider.providerModels.google.description')}
              placeholder={t('settings:aiProvider.providerModels.google.placeholder')}
              value={config.googleModel ?? ''}
              onChange={(googleModel) => updateConfig({ googleModel })}
            />
          </>
        );
      case 'litellm':
        return (
          <>
            <ProviderField
              id="litellmModel"
              label={t('settings:aiProvider.providerModels.litellm.label')}
              description={t('settings:aiProvider.providerModels.litellm.description')}
              placeholder={t('settings:aiProvider.providerModels.litellm.placeholder')}
              value={config.litellmModel ?? ''}
              onChange={(litellmModel) => updateConfig({ litellmModel })}
            />
            <ProviderField
              id="litellmApiBase"
              label={t('settings:aiProvider.baseUrls.litellm.label')}
              description={t('settings:aiProvider.baseUrls.litellm.description')}
              placeholder={t('settings:aiProvider.baseUrls.litellm.placeholder')}
              value={config.litellmApiBase ?? ''}
              onChange={(litellmApiBase) => updateConfig({ litellmApiBase })}
            />
            <ProviderField
              id="litellmApiKey"
              label={t('settings:aiProvider.apiKeys.litellm.label')}
              description={t('settings:aiProvider.apiKeys.litellm.description')}
              placeholder={t('settings:aiProvider.apiKeys.litellm.placeholder')}
              type="password"
              value={config.litellmApiKey ?? ''}
              onChange={(litellmApiKey) => updateConfig({ litellmApiKey })}
            />
          </>
        );
      case 'openrouter':
        return (
          <>
            <ProviderField
              id="openrouterApiKey"
              label={t('settings:aiProvider.apiKeys.openrouter.label')}
              description={t('settings:aiProvider.apiKeys.openrouter.description')}
              placeholder={t('settings:aiProvider.apiKeys.openrouter.placeholder')}
              type="password"
              value={config.openrouterApiKey ?? ''}
              onChange={(openrouterApiKey) => updateConfig({ openrouterApiKey })}
            />
            <ProviderField
              id="openrouterModel"
              label={t('settings:aiProvider.providerModels.openrouter.label')}
              description={t('settings:aiProvider.providerModels.openrouter.description')}
              placeholder={t('settings:aiProvider.providerModels.openrouter.placeholder')}
              value={config.openrouterModel ?? ''}
              onChange={(openrouterModel) => updateConfig({ openrouterModel })}
            />
            <ProviderField
              id="openrouterBaseUrl"
              label={t('settings:aiProvider.baseUrls.openrouter.label')}
              description={t('settings:aiProvider.baseUrls.openrouter.description')}
              placeholder={t('settings:aiProvider.baseUrls.openrouter.placeholder')}
              value={config.openrouterBaseUrl ?? ''}
              onChange={(openrouterBaseUrl) => updateConfig({ openrouterBaseUrl })}
            />
          </>
        );
      case 'zhipuai':
        return (
          <>
            <ProviderField
              id="zhipuaiApiKey"
              label={t('settings:aiProvider.apiKeys.zhipuai.label')}
              description={t('settings:aiProvider.apiKeys.zhipuai.description')}
              placeholder={t('settings:aiProvider.apiKeys.zhipuai.placeholder')}
              type="password"
              value={config.zhipuaiApiKey ?? ''}
              onChange={(zhipuaiApiKey) => updateConfig({ zhipuaiApiKey })}
            />
            <ProviderField
              id="zhipuaiModel"
              label={t('settings:aiProvider.providerModels.zhipuai.label')}
              description={t('settings:aiProvider.providerModels.zhipuai.description')}
              placeholder={t('settings:aiProvider.providerModels.zhipuai.placeholder')}
              value={config.zhipuaiModel ?? ''}
              onChange={(zhipuaiModel) => updateConfig({ zhipuaiModel })}
            />
          </>
        );
      case 'ollama':
        return (
          <>
            <ProviderField
              id="ollamaModel"
              label={t('settings:aiProvider.providerModels.ollama.label')}
              description={t('settings:aiProvider.providerModels.ollama.description')}
              placeholder={t('settings:aiProvider.providerModels.ollama.placeholder')}
              value={config.ollamaModel ?? ''}
              onChange={(ollamaModel) => updateConfig({ ollamaModel })}
            />
            <ProviderField
              id="ollamaBaseUrl"
              label={t('settings:aiProvider.baseUrls.ollama.label')}
              description={t('settings:aiProvider.baseUrls.ollama.description')}
              placeholder={t('settings:aiProvider.baseUrls.ollama.placeholder')}
              value={config.ollamaBaseUrl ?? ''}
              onChange={(ollamaBaseUrl) => updateConfig({ ollamaBaseUrl })}
            />
          </>
        );
      default:
        return (
          <ProviderField
            id="claudeModel"
            label={t('settings:aiProvider.providerModels.claude.label')}
            description={t('settings:aiProvider.providerModels.claude.description')}
            placeholder={t('settings:aiProvider.providerModels.claude.placeholder')}
            value={config.claudeModel ?? ''}
            onChange={(claudeModel) => updateConfig({ claudeModel })}
          />
        );
    }
  };

  return (
    <SettingsSection
      title={t('settings:aiProvider.title')}
      description={t('settings:aiProvider.description')}
    >
      <div className="space-y-6">
        <div className="space-y-3">
          <Label htmlFor="aiProvider" className="text-sm font-medium text-foreground">
            {t('settings:aiProvider.label')}
          </Label>
          <Select
            value={config.provider}
            onValueChange={(value) => handleProviderChange(value as AIEngineProvider)}
            disabled={loading}
          >
            <SelectTrigger id="aiProvider" className="w-full max-w-xl">
              <SelectValue placeholder={t('settings:aiProvider.selectProvider')} />
            </SelectTrigger>
            <SelectContent>
              {PROVIDER_OPTIONS.map((provider) => (
                <SelectItem key={provider.value} value={provider.value}>
                  <div className="flex flex-col items-start">
                    <span className="font-medium">{t(provider.labelKey)}</span>
                    <span className="text-xs text-muted-foreground">{t(provider.descriptionKey)}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {t('settings:aiProvider.hints.envOverride')}
          </p>
        </div>

        <div className="rounded-md border border-border bg-muted/30 p-4">
          <div className="flex items-start gap-3">
            {nonClaudeFullAutonomous ? (
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            ) : (
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            )}
            <div className="space-y-1">
              <h3 className="text-sm font-medium text-foreground">
                {t(selectedProvider.labelKey)}
              </h3>
              <p className="text-xs text-muted-foreground">
                {t(compatibilityMessageKey)}
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-4 border-t border-border pt-4">
          <div>
            <h3 className="text-sm font-medium text-foreground">
              {t('settings:aiProvider.runtime.title')}
            </h3>
            <p className="text-xs text-muted-foreground">
              {t('settings:aiProvider.runtime.description')}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="runtimeMode" className="text-sm font-medium text-foreground">
              {t('settings:aiProvider.runtime.globalLabel')}
            </Label>
            {renderRuntimeSelect(
              'runtimeMode',
              activeRuntimeMode,
              (runtimeMode) => updateConfig({ runtimeMode: runtimeMode as AgentRuntimeMode }),
              false
            )}
          </div>

          <div className="flex max-w-xl items-start gap-3 rounded-md border border-border bg-background p-3">
            <Switch
              id="runtimeFallbackEnabled"
              checked={runtimeFallbackEnabled}
              onCheckedChange={(runtimeFallbackEnabled) =>
                updateConfig({ runtimeFallbackEnabled })
              }
              disabled={loading}
            />
            <div className="space-y-1">
              <Label htmlFor="runtimeFallbackEnabled" className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.runtime.fallbackLabel')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('settings:aiProvider.runtime.fallbackDescription')}
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="plannerRuntimeMode" className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.runtime.plannerLabel')}
              </Label>
              {renderRuntimeSelect(
                'plannerRuntimeMode',
                config.plannerRuntimeMode,
                (value) => handleRuntimeOverrideChange('plannerRuntimeMode', value),
                true
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="coderRuntimeMode" className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.runtime.coderLabel')}
              </Label>
              {renderRuntimeSelect(
                'coderRuntimeMode',
                config.coderRuntimeMode,
                (value) => handleRuntimeOverrideChange('coderRuntimeMode', value),
                true
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="qaReviewerRuntimeMode" className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.runtime.qaReviewerLabel')}
              </Label>
              {renderRuntimeSelect(
                'qaReviewerRuntimeMode',
                config.qaReviewerRuntimeMode,
                (value) => handleRuntimeOverrideChange('qaReviewerRuntimeMode', value),
                true
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="qaFixerRuntimeMode" className="text-sm font-medium text-foreground">
                {t('settings:aiProvider.runtime.qaFixerLabel')}
              </Label>
              {renderRuntimeSelect(
                'qaFixerRuntimeMode',
                config.qaFixerRuntimeMode,
                (value) => handleRuntimeOverrideChange('qaFixerRuntimeMode', value),
                true
              )}
            </div>
          </div>
        </div>

        <div className="space-y-4 border-t border-border pt-4">
          <div>
            <h3 className="text-sm font-medium text-foreground">
              {t('settings:aiProvider.configuration.title')}
            </h3>
            <p className="text-xs text-muted-foreground">
              {t('settings:aiProvider.configuration.description')}
            </p>
          </div>
          {renderProviderConfiguration()}
        </div>

        <div className="space-y-4 border-t border-border pt-4">
          <div>
            <h3 className="text-sm font-medium text-foreground">
              {t('settings:aiProvider.models.title')}
            </h3>
            <p className="text-xs text-muted-foreground">
              {t('settings:aiProvider.models.description')}
            </p>
          </div>
          <ProviderField
            id="plannerModel"
            label={t('settings:aiProvider.models.planner.label')}
            description={t('settings:aiProvider.models.planner.description')}
            placeholder={t('settings:aiProvider.models.planner.placeholder')}
            value={config.plannerModel ?? ''}
            onChange={(plannerModel) => updateConfig({ plannerModel })}
          />
          <ProviderField
            id="coderModel"
            label={t('settings:aiProvider.models.coder.label')}
            description={t('settings:aiProvider.models.coder.description')}
            placeholder={t('settings:aiProvider.models.coder.placeholder')}
            value={config.coderModel ?? ''}
            onChange={(coderModel) => updateConfig({ coderModel })}
          />
          <ProviderField
            id="qaModel"
            label={t('settings:aiProvider.models.qa.label')}
            description={t('settings:aiProvider.models.qa.description')}
            placeholder={t('settings:aiProvider.models.qa.placeholder')}
            value={config.qaModel ?? ''}
            onChange={(qaModel) => updateConfig({ qaModel })}
          />
        </div>

        <div className="flex items-center gap-3 pt-2">
          <Button onClick={handleSave} disabled={saving || loading}>
            {saving ? t('common:buttons.saving') : t('common:buttons.save')}
          </Button>
          <Button
            variant="outline"
            onClick={handleValidate}
            disabled={saving || validating || loading}
          >
            {validating
              ? t('settings:aiProvider.validation.validating')
              : t('settings:aiProvider.validation.action')}
          </Button>
          {saveStatus === 'success' && (
            <span className="inline-flex items-center gap-1.5 text-sm text-success">
              <CheckCircle2 className="h-4 w-4" />
              {t('common:labels.success')}
            </span>
          )}
          {saveStatus === 'error' && (
            <span className="inline-flex items-center gap-1.5 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4" />
              {t('common:labels.error')}
            </span>
          )}
        </div>
        {validationStatus && (
          <div className="max-w-xl rounded-md border border-border bg-muted/30 p-3 text-sm">
            {validationStatus.isValid ? (
              <div className="flex items-center gap-2 text-success">
                <CheckCircle2 className="h-4 w-4" />
                {t('settings:aiProvider.validation.valid')}
              </div>
            ) : (
              <div className="space-y-2 text-destructive">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  {t('settings:aiProvider.validation.invalid')}
                </div>
                <ul className="list-disc space-y-1 pl-5">
                  {validationStatus.errors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              </div>
            )}
            {validationStatus.availableProviders.length > 0 && (
              <p className="mt-2 text-xs text-muted-foreground">
                {t('settings:aiProvider.validation.availableProviders', {
                  providers: validationStatus.availableProviders.join(', ')
                })}
              </p>
            )}
          </div>
        )}
      </div>
    </SettingsSection>
  );
}
