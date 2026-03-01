import { useTranslation } from 'react-i18next';
import { useState, useEffect } from 'react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { SettingsSection } from './SettingsSection';
import type { AIEngineProvider } from '../../../shared/types/settings';

type ProviderType = AIEngineProvider;

type ProviderSettingsSectionProps = Record<string, never>;

interface ProviderApiKeyFieldsProps {
  selectedProvider: ProviderType;
  openaiApiKey: string;
  googleApiKey: string;
  openrouterApiKey: string;
  zhipuaiApiKey: string;
  onOpenaiChange: (v: string) => void;
  onGoogleChange: (v: string) => void;
  onOpenrouterChange: (v: string) => void;
  onZhipuaiChange: (v: string) => void;
}

function ProviderApiKeyFields({
  selectedProvider,
  openaiApiKey, googleApiKey, openrouterApiKey, zhipuaiApiKey,
  onOpenaiChange, onGoogleChange, onOpenrouterChange, onZhipuaiChange,
}: ProviderApiKeyFieldsProps) {
  const { t } = useTranslation(['settings']);
  return (
    <>
      {selectedProvider === 'litellm' && (
        <>
          <div className="space-y-2">
            <Label htmlFor="openaiApiKey" className="text-sm font-medium text-foreground">
              {t('settings:aiProvider.apiKeys.openai.label')}
            </Label>
            <Input
              id="openaiApiKey"
              type="password"
              placeholder={t('settings:aiProvider.apiKeys.openai.placeholder')}
              value={openaiApiKey}
              onChange={(e) => onOpenaiChange(e.target.value)}
              className="max-w-md"
            />
            <p className="text-xs text-muted-foreground">
              {t('settings:aiProvider.apiKeys.openai.description')}
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="googleApiKey" className="text-sm font-medium text-foreground">
              {t('settings:aiProvider.apiKeys.google.label')}
            </Label>
            <Input
              id="googleApiKey"
              type="password"
              placeholder={t('settings:aiProvider.apiKeys.google.placeholder')}
              value={googleApiKey}
              onChange={(e) => onGoogleChange(e.target.value)}
              className="max-w-md"
            />
            <p className="text-xs text-muted-foreground">
              {t('settings:aiProvider.apiKeys.google.description')}
            </p>
          </div>
        </>
      )}
      {selectedProvider === 'openrouter' && (
        <div className="space-y-2">
          <Label htmlFor="openrouterApiKey" className="text-sm font-medium text-foreground">
            {t('settings:aiProvider.apiKeys.openrouter.label')}
          </Label>
          <Input
            id="openrouterApiKey"
            type="password"
            placeholder={t('settings:aiProvider.apiKeys.openrouter.placeholder')}
            value={openrouterApiKey}
            onChange={(e) => onOpenrouterChange(e.target.value)}
            className="max-w-md"
          />
          <p className="text-xs text-muted-foreground">
            {t('settings:aiProvider.apiKeys.openrouter.description')}
          </p>
        </div>
      )}
      {selectedProvider === 'zhipuai' && (
        <div className="space-y-2">
          <Label htmlFor="zhipuaiApiKey" className="text-sm font-medium text-foreground">
            {t('settings:aiProvider.apiKeys.zhipuai.label')}
          </Label>
          <Input
            id="zhipuaiApiKey"
            type="password"
            placeholder={t('settings:aiProvider.apiKeys.zhipuai.placeholder')}
            value={zhipuaiApiKey}
            onChange={(e) => onZhipuaiChange(e.target.value)}
            className="max-w-md"
          />
          <p className="text-xs text-muted-foreground">
            {t('settings:aiProvider.apiKeys.zhipuai.description')}
          </p>
        </div>
      )}
    </>
  );
}

interface PerAgentModelFieldsProps {
  plannerModel: string;
  coderModel: string;
  qaModel: string;
  onPlannerChange: (v: string) => void;
  onCoderChange: (v: string) => void;
  onQaChange: (v: string) => void;
}

function PerAgentModelFields({
  plannerModel, coderModel, qaModel,
  onPlannerChange, onCoderChange, onQaChange,
}: PerAgentModelFieldsProps) {
  const { t } = useTranslation(['settings']);
  return (
    <div className="space-y-4 pt-4 border-t border-border">
      <div>
        <h3 className="text-sm font-medium text-foreground mb-1">
          {t('settings:aiProvider.models.title')}
        </h3>
        <p className="text-xs text-muted-foreground">
          {t('settings:aiProvider.models.description')}
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="plannerModel" className="text-sm font-medium text-foreground">
          {t('settings:aiProvider.models.planner.label')}
        </Label>
        <Input
          id="plannerModel"
          type="text"
          placeholder={t('settings:aiProvider.models.planner.placeholder')}
          value={plannerModel}
          onChange={(e) => onPlannerChange(e.target.value)}
          className="max-w-md"
        />
        <p className="text-xs text-muted-foreground">
          {t('settings:aiProvider.models.planner.description')}
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="coderModel" className="text-sm font-medium text-foreground">
          {t('settings:aiProvider.models.coder.label')}
        </Label>
        <Input
          id="coderModel"
          type="text"
          placeholder={t('settings:aiProvider.models.coder.placeholder')}
          value={coderModel}
          onChange={(e) => onCoderChange(e.target.value)}
          className="max-w-md"
        />
        <p className="text-xs text-muted-foreground">
          {t('settings:aiProvider.models.coder.description')}
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="qaModel" className="text-sm font-medium text-foreground">
          {t('settings:aiProvider.models.qa.label')}
        </Label>
        <Input
          id="qaModel"
          type="text"
          placeholder={t('settings:aiProvider.models.qa.placeholder')}
          value={qaModel}
          onChange={(e) => onQaChange(e.target.value)}
          className="max-w-md"
        />
        <p className="text-xs text-muted-foreground">
          {t('settings:aiProvider.models.qa.description')}
        </p>
      </div>
    </div>
  );
}

/**
 * Provider settings component for configuring AI providers
 */
export function ProviderSettingsSection(_props: ProviderSettingsSectionProps) {
  const { t } = useTranslation(['settings', 'common']);
  const [selectedProvider, setSelectedProvider] = useState<ProviderType>('claude');
  const [openaiApiKey, setOpenaiApiKey] = useState('');
  const [googleApiKey, setGoogleApiKey] = useState('');
  const [openrouterApiKey, setOpenrouterApiKey] = useState('');
  const [zhipuaiApiKey, setZhipuaiApiKey] = useState('');

  // Model selection per agent type
  const [plannerModel, setPlannerModel] = useState('');
  const [coderModel, setCoderModel] = useState('');
  const [qaModel, setQaModel] = useState('');

  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Load existing config on mount
  useEffect(() => {
    (async () => {
      try {
        const result = await window.electronAPI?.getProviderConfig?.();
        if (result?.success && result.data) {
          const data = result.data;
          if (data.provider) setSelectedProvider(data.provider);
          if (data.openaiApiKey) setOpenaiApiKey(data.openaiApiKey);
          if (data.googleApiKey) setGoogleApiKey(data.googleApiKey);
          if (data.openrouterApiKey) setOpenrouterApiKey(data.openrouterApiKey);
          if (data.zhipuaiApiKey) setZhipuaiApiKey(data.zhipuaiApiKey);
          if (data.plannerModel) setPlannerModel(data.plannerModel);
          if (data.coderModel) setCoderModel(data.coderModel);
          if (data.qaModel) setQaModel(data.qaModel);
        }
      } catch {
        // Ignore errors loading config on mount
      }
    })();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaveStatus('idle');
    try {
      const config: Partial<import('../../../shared/types/settings').AIProviderConfig> = {
        provider: selectedProvider,
        openaiApiKey: openaiApiKey || undefined,
        googleApiKey: googleApiKey || undefined,
        openrouterApiKey: openrouterApiKey || undefined,
        zhipuaiApiKey: zhipuaiApiKey || undefined,
        plannerModel: plannerModel || undefined,
        coderModel: coderModel || undefined,
        qaModel: qaModel || undefined,
      };
      const result = await window.electronAPI?.updateProviderConfig?.(config);
      setSaveStatus(result?.success ? 'success' : 'error');
    } catch {
      setSaveStatus('error');
    } finally {
      setSaving(false);
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
          <p className="text-sm text-muted-foreground">
            {t('settings:aiProvider.hints.claudeDefault')}
          </p>
          <Select
            value={selectedProvider}
            onValueChange={(value) => setSelectedProvider(value as ProviderType)}
          >
            <SelectTrigger id="aiProvider" className="w-full max-w-md">
              <SelectValue placeholder={t('settings:aiProvider.selectProvider')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="claude">
                <div className="flex flex-col items-start">
                  <span className="font-medium">{t('settings:aiProvider.providers.claude.name')}</span>
                  <span className="text-xs text-muted-foreground">
                    {t('settings:aiProvider.providers.claude.description')}
                  </span>
                </div>
              </SelectItem>
              <SelectItem value="litellm">
                <div className="flex flex-col items-start">
                  <span className="font-medium">{t('settings:aiProvider.providers.litellm.name')}</span>
                  <span className="text-xs text-muted-foreground">
                    {t('settings:aiProvider.providers.litellm.description')}
                  </span>
                </div>
              </SelectItem>
              <SelectItem value="openrouter">
                <div className="flex flex-col items-start">
                  <span className="font-medium">{t('settings:aiProvider.providers.openrouter.name')}</span>
                  <span className="text-xs text-muted-foreground">
                    {t('settings:aiProvider.providers.openrouter.description')}
                  </span>
                </div>
              </SelectItem>
              <SelectItem value="zhipuai">
                <div className="flex flex-col items-start">
                  <span className="font-medium">{t('settings:aiProvider.providers.zhipuai.name')}</span>
                  <span className="text-xs text-muted-foreground">
                    {t('settings:aiProvider.providers.zhipuai.description')}
                  </span>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {t('settings:aiProvider.hints.envOverride')}
          </p>
        </div>

        {/* API Key Configuration - conditionally shown based on provider */}
        {selectedProvider !== 'claude' && (
          <div className="space-y-4 pt-4 border-t border-border">
            <div>
              <h3 className="text-sm font-medium text-foreground mb-3">
                {t('settings:aiProvider.apiKeys.title')}
              </h3>
            </div>
            <ProviderApiKeyFields
              selectedProvider={selectedProvider}
              openaiApiKey={openaiApiKey}
              googleApiKey={googleApiKey}
              openrouterApiKey={openrouterApiKey}
              zhipuaiApiKey={zhipuaiApiKey}
              onOpenaiChange={setOpenaiApiKey}
              onGoogleChange={setGoogleApiKey}
              onOpenrouterChange={setOpenrouterApiKey}
              onZhipuaiChange={setZhipuaiApiKey}
            />
            <PerAgentModelFields
              plannerModel={plannerModel}
              coderModel={coderModel}
              qaModel={qaModel}
              onPlannerChange={setPlannerModel}
              onCoderChange={setCoderModel}
              onQaChange={setQaModel}
            />
          </div>
        )}

        {/* Save button - always visible */}
        <div className="pt-2">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? t('common:buttons.saving', 'Saving...') : t('common:actions.save')}
          </Button>
          {saveStatus === 'success' && (
            <span className="ml-2 text-sm text-success">{t('common:status.saved', 'Saved')}</span>
          )}
          {saveStatus === 'error' && (
            <span className="ml-2 text-sm text-destructive">{t('common:status.error', 'Error saving')}</span>
          )}
        </div>
      </div>
    </SettingsSection>
  );
}
