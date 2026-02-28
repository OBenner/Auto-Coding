import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { SettingsSection } from './SettingsSection';
import type { AIEngineProvider } from '../../../shared/types/settings';

type ProviderType = AIEngineProvider;

type ProviderSettingsSectionProps = Record<string, never>;

/**
 * Provider settings component for configuring AI providers
 */
export function ProviderSettingsSection(props: ProviderSettingsSectionProps) {
  const { t } = useTranslation(['settings', 'common']);
  const [selectedProvider, setSelectedProvider] = useState<ProviderType>('claude');
  const [openaiApiKey, setOpenaiApiKey] = useState('');
  const [googleApiKey, setGoogleApiKey] = useState('');
  const [openrouterApiKey, setOpenrouterApiKey] = useState('');

  // Model selection per agent type
  const [plannerModel, setPlannerModel] = useState('');
  const [coderModel, setCoderModel] = useState('');
  const [qaModel, setQaModel] = useState('');

  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const handleSave = async () => {
    setSaving(true);
    setSaveStatus('idle');
    try {
      const config: Partial<import('../../../shared/types/settings').AIProviderConfig> = {
        provider: selectedProvider,
        openaiApiKey: openaiApiKey || undefined,
        googleApiKey: googleApiKey || undefined,
        openrouterApiKey: openrouterApiKey || undefined,
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
      title={t('aiProvider.title')}
      description={t('aiProvider.description')}
    >
      <div className="space-y-6">
        <div className="space-y-3">
          <Label htmlFor="aiProvider" className="text-sm font-medium text-foreground">
            {t('aiProvider.label')}
          </Label>
          <p className="text-sm text-muted-foreground">
            {t('aiProvider.hints.claudeDefault')}
          </p>
          <Select
            value={selectedProvider}
            onValueChange={(value) => setSelectedProvider(value as ProviderType)}
          >
            <SelectTrigger id="aiProvider" className="w-full max-w-md">
              <SelectValue placeholder={t('aiProvider.selectProvider')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="claude">
                <div className="flex flex-col items-start">
                  <span className="font-medium">{t('aiProvider.providers.claude.name')}</span>
                  <span className="text-xs text-muted-foreground">
                    {t('aiProvider.providers.claude.description')}
                  </span>
                </div>
              </SelectItem>
              <SelectItem value="litellm">
                <div className="flex flex-col items-start">
                  <span className="font-medium">{t('aiProvider.providers.litellm.name')}</span>
                  <span className="text-xs text-muted-foreground">
                    {t('aiProvider.providers.litellm.description')}
                  </span>
                </div>
              </SelectItem>
              <SelectItem value="openrouter">
                <div className="flex flex-col items-start">
                  <span className="font-medium">{t('aiProvider.providers.openrouter.name')}</span>
                  <span className="text-xs text-muted-foreground">
                    {t('aiProvider.providers.openrouter.description')}
                  </span>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {t('aiProvider.hints.envOverride')}
          </p>
        </div>

        {/* API Key Configuration - conditionally shown based on provider */}
        {selectedProvider !== 'claude' && (
          <div className="space-y-4 pt-4 border-t border-border">
            <div>
              <h3 className="text-sm font-medium text-foreground mb-3">
                {t('aiProvider.apiKeys.title')}
              </h3>
            </div>

            {/* LiteLLM provider shows OpenAI and Google keys */}
            {selectedProvider === 'litellm' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="openaiApiKey" className="text-sm font-medium text-foreground">
                    {t('aiProvider.apiKeys.openai.label')}
                  </Label>
                  <Input
                    id="openaiApiKey"
                    type="password"
                    placeholder={t('aiProvider.apiKeys.openai.placeholder')}
                    value={openaiApiKey}
                    onChange={(e) => setOpenaiApiKey(e.target.value)}
                    className="max-w-md"
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('aiProvider.apiKeys.openai.description')}
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="googleApiKey" className="text-sm font-medium text-foreground">
                    {t('aiProvider.apiKeys.google.label')}
                  </Label>
                  <Input
                    id="googleApiKey"
                    type="password"
                    placeholder={t('aiProvider.apiKeys.google.placeholder')}
                    value={googleApiKey}
                    onChange={(e) => setGoogleApiKey(e.target.value)}
                    className="max-w-md"
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('aiProvider.apiKeys.google.description')}
                  </p>
                </div>
              </>
            )}

            {/* OpenRouter provider shows OpenRouter key */}
            {selectedProvider === 'openrouter' && (
              <div className="space-y-2">
                <Label htmlFor="openrouterApiKey" className="text-sm font-medium text-foreground">
                  {t('aiProvider.apiKeys.openrouter.label')}
                </Label>
                <Input
                  id="openrouterApiKey"
                  type="password"
                  placeholder={t('aiProvider.apiKeys.openrouter.placeholder')}
                  value={openrouterApiKey}
                  onChange={(e) => setOpenrouterApiKey(e.target.value)}
                  className="max-w-md"
                />
                <p className="text-xs text-muted-foreground">
                  {t('aiProvider.apiKeys.openrouter.description')}
                </p>
              </div>
            )}

            {/* Model Selection per Agent Type */}
            <div className="space-y-4 pt-4 border-t border-border">
              <div>
                <h3 className="text-sm font-medium text-foreground mb-1">
                  {t('aiProvider.models.title')}
                </h3>
                <p className="text-xs text-muted-foreground">
                  {t('aiProvider.models.description')}
                </p>
              </div>

              {/* Planner Model */}
              <div className="space-y-2">
                <Label htmlFor="plannerModel" className="text-sm font-medium text-foreground">
                  {t('aiProvider.models.planner.label')}
                </Label>
                <Input
                  id="plannerModel"
                  type="text"
                  placeholder={t('aiProvider.models.planner.placeholder')}
                  value={plannerModel}
                  onChange={(e) => setPlannerModel(e.target.value)}
                  className="max-w-md"
                />
                <p className="text-xs text-muted-foreground">
                  {t('aiProvider.models.planner.description')}
                </p>
              </div>

              {/* Coder Model */}
              <div className="space-y-2">
                <Label htmlFor="coderModel" className="text-sm font-medium text-foreground">
                  {t('aiProvider.models.coder.label')}
                </Label>
                <Input
                  id="coderModel"
                  type="text"
                  placeholder={t('aiProvider.models.coder.placeholder')}
                  value={coderModel}
                  onChange={(e) => setCoderModel(e.target.value)}
                  className="max-w-md"
                />
                <p className="text-xs text-muted-foreground">
                  {t('aiProvider.models.coder.description')}
                </p>
              </div>

              {/* QA Model */}
              <div className="space-y-2">
                <Label htmlFor="qaModel" className="text-sm font-medium text-foreground">
                  {t('aiProvider.models.qa.label')}
                </Label>
                <Input
                  id="qaModel"
                  type="text"
                  placeholder={t('aiProvider.models.qa.placeholder')}
                  value={qaModel}
                  onChange={(e) => setQaModel(e.target.value)}
                  className="max-w-md"
                />
                <p className="text-xs text-muted-foreground">
                  {t('aiProvider.models.qa.description')}
                </p>
              </div>
            </div>

            {/* Save button */}
            <div className="pt-2">
              <Button onClick={handleSave}>
                {t('common:actions.save')}
              </Button>
            </div>
          </div>
        )}
      </div>
    </SettingsSection>
  );
}
