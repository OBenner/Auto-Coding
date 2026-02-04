import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { SettingsSection } from './SettingsSection';

type ProviderType = 'claude' | 'litellm' | 'openrouter';

interface ProviderSettingsSectionProps {
  // Future: add settings state and onChange handler
}

/**
 * Provider settings component for configuring AI providers
 */
export function ProviderSettingsSection(props: ProviderSettingsSectionProps) {
  const { t } = useTranslation('settings');
  const [selectedProvider, setSelectedProvider] = useState<ProviderType>('claude');

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
      </div>
    </SettingsSection>
  );
}
