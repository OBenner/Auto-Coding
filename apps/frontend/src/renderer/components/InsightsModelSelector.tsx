import { useState, useMemo, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Brain, Scale, Zap, Sparkles, Sliders, Check } from 'lucide-react';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel
} from './ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from './ui/select';
import { DEFAULT_AGENT_PROFILES, AVAILABLE_MODELS } from '../../shared/constants';
import { getModelsForProvider } from '../../shared/constants/api-profiles';
import { INSIGHTS_TO_API_PROVIDER, getInsightsProviderOptions } from '../../shared/constants/insights-providers';
import type { InsightsModelConfig, InsightsProvider, ModelType } from '../../shared/types';
import { CustomModelModal } from './CustomModelModal';

interface InsightsModelSelectorProps {
  currentConfig?: InsightsModelConfig;
  onConfigChange: (config: InsightsModelConfig) => void;
  disabled?: boolean;
}

const iconMap: Record<string, React.ElementType> = {
  Brain,
  Scale,
  Zap,
  Sparkles
};

/**
 * Get provider-specific model label for a model tier
 */
function getModelLabelForProvider(modelTier: ModelType, providerId: InsightsProvider): string {
  const apiProviderId = INSIGHTS_TO_API_PROVIDER[providerId];

  // LiteLLM doesn't have predefined models, use generic labels
  if (providerId === 'litellm') {
    return AVAILABLE_MODELS.find(m => m.value === modelTier)?.label || modelTier;
  }

  // Get provider-specific model label
  const models = getModelsForProvider(apiProviderId);
  const model = models.find(m => m.tier === modelTier);

  if (model) {
    return model.name;
  }

  // Fallback to generic label
  return AVAILABLE_MODELS.find(m => m.value === modelTier)?.label || modelTier;
}

export function InsightsModelSelector({
  currentConfig,
  onConfigChange,
  disabled
}: InsightsModelSelectorProps) {
  const { t } = useTranslation(['dialogs', 'common']);
  const [showCustomModal, setShowCustomModal] = useState(false);

  // Provider state - sync with currentConfig to avoid stale state
  const [selectedProvider, setSelectedProvider] = useState<InsightsProvider>(
    currentConfig?.provider || 'claude'
  );

  // Sync selectedProvider when currentConfig changes externally
  useEffect(() => {
    const configProvider = currentConfig?.provider || 'claude';
    setSelectedProvider(configProvider);
  }, [currentConfig?.provider]);

  // Build provider options with i18n
  const insightsProviders = useMemo(() => getInsightsProviderOptions(t), [t]);

  // Default to 'balanced' if no config, or if 'auto' profile was selected (not applicable for insights)
  const rawProfileId = currentConfig?.profileId || 'balanced';
  const selectedProfileId = rawProfileId === 'auto' ? 'balanced' : rawProfileId;
  const profile = DEFAULT_AGENT_PROFILES.find(p => p.id === selectedProfileId);

  // Get the appropriate icon
  const Icon = selectedProfileId === 'custom'
    ? Sliders
    : (profile?.icon ? iconMap[profile.icon] : Scale);

  // Get provider-specific model label for current profile
  const providerModelLabel = useMemo(() => {
    if (profile && profile.model) {
      return getModelLabelForProvider(profile.model as ModelType, selectedProvider);
    }
    return null;
  }, [profile, selectedProvider]);

  const handleSelectProfile = (profileId: string) => {
    if (profileId === 'custom') {
      setShowCustomModal(true);
      return;
    }

    const selected = DEFAULT_AGENT_PROFILES.find(p => p.id === profileId);
    if (selected) {
      onConfigChange({
        profileId: selected.id,
        model: selected.model,
        thinkingLevel: selected.thinkingLevel,
        provider: selectedProvider
      });
    }
  };

  const handleProviderChange = (providerId: InsightsProvider) => {
    setSelectedProvider(providerId);
    // When provider changes, update the current config with the new provider
    if (currentConfig) {
      onConfigChange({
        ...currentConfig,
        provider: providerId
      });
    }
  };

  const handleCustomSave = (config: InsightsModelConfig) => {
    // Ensure provider is included when saving custom config
    onConfigChange({
      ...config,
      provider: config.provider || selectedProvider
    });
    setShowCustomModal(false);
  };

  // Build display text for current selection
  const getDisplayText = () => {
    if (selectedProfileId === 'custom' && currentConfig) {
      const modelLabel = getModelLabelForProvider(currentConfig.model, currentConfig.provider);
      const providerLabel = insightsProviders.find(p => p.id === currentConfig.provider)?.label || currentConfig.provider;
      return `${providerLabel}: ${modelLabel} + ${currentConfig.thinkingLevel}`;
    }
    const providerLabel = insightsProviders.find(p => p.id === selectedProvider)?.label || selectedProvider;
    const modelLabel = providerModelLabel || profile?.name || 'Balanced';
    return `${providerLabel} - ${profile?.name || modelLabel}`;
  };

  return (
    <div className="flex items-center gap-2">
      {/* Provider Selector */}
      <Select value={selectedProvider} onValueChange={(value) => handleProviderChange(value as InsightsProvider)} disabled={disabled}>
        <SelectTrigger className="h-8 w-[140px]">
          <SelectValue placeholder={t('dialogs:customModel.provider')} />
        </SelectTrigger>
        <SelectContent align="end">
          {insightsProviders.map((provider) => (
            <SelectItem key={provider.id} value={provider.id}>
              <div className="flex flex-col">
                <span className="font-medium">{provider.label}</span>
                <span className="text-xs text-muted-foreground">{provider.description}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Profile Selector */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-2 px-2"
            disabled={disabled}
            title={`Model: ${getDisplayText()}`}
          >
            <Icon className="h-4 w-4" />
            <span className="hidden text-xs text-muted-foreground sm:inline">
              {getDisplayText()}
            </span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-64">
          <DropdownMenuLabel>{t('dialogs:customModel.agentProfile')}</DropdownMenuLabel>
          {DEFAULT_AGENT_PROFILES.filter(p => !p.isAutoProfile).map((p) => {
            const ProfileIcon = iconMap[p.icon || 'Brain'];
            const isSelected = selectedProfileId === p.id;
            const modelLabel = getModelLabelForProvider(p.model as ModelType, selectedProvider);
            return (
              <DropdownMenuItem
                key={p.id}
                onClick={() => handleSelectProfile(p.id)}
                className="flex cursor-pointer items-center gap-2"
              >
                <ProfileIcon className="h-4 w-4 shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="font-medium">{p.name}</div>
                  <div className="truncate text-xs text-muted-foreground">
                    {modelLabel} + {p.thinkingLevel}
                  </div>
                </div>
                {isSelected && (
                  <Check className="h-4 w-4 shrink-0 text-primary" />
                )}
              </DropdownMenuItem>
            );
          })}
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => handleSelectProfile('custom')}
            className="flex cursor-pointer items-center gap-2"
          >
            <Sliders className="h-4 w-4 shrink-0" />
            <div className="flex-1">
              <div className="font-medium">{t('dialogs:customModel.custom')}</div>
              <div className="text-xs text-muted-foreground">
                {t('dialogs:customModel.customDesc')}
              </div>
            </div>
            {selectedProfileId === 'custom' && (
              <Check className="h-4 w-4 shrink-0 text-primary" />
            )}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <CustomModelModal
        open={showCustomModal}
        currentConfig={currentConfig}
        onSave={handleCustomSave}
        onClose={() => setShowCustomModal(false)}
      />
    </div>
  );
}
