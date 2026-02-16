import { useState } from 'react';
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
import type { InsightsModelConfig, InsightsProvider } from '../../shared/types';
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

// Provider options for Insights mode
const INSIGHTS_PROVIDERS: Array<{ id: InsightsProvider; label: string; description: string }> = [
  { id: 'claude', label: 'Claude (Anthropic)', description: 'Official Anthropic Claude models' },
  { id: 'litellm', label: 'LiteLLM', description: '100+ models via LiteLLM' },
  { id: 'openrouter', label: 'OpenRouter', description: '400+ models via OpenRouter' }
];

export function InsightsModelSelector({
  currentConfig,
  onConfigChange,
  disabled
}: InsightsModelSelectorProps) {
  const [showCustomModal, setShowCustomModal] = useState(false);

  // Provider state (default to 'claude' for backward compatibility)
  const [selectedProvider, setSelectedProvider] = useState<InsightsProvider>(
    currentConfig?.provider || 'claude'
  );

  // Default to 'balanced' if no config, or if 'auto' profile was selected (not applicable for insights)
  const rawProfileId = currentConfig?.profileId || 'balanced';
  const selectedProfileId = rawProfileId === 'auto' ? 'balanced' : rawProfileId;
  const profile = DEFAULT_AGENT_PROFILES.find(p => p.id === selectedProfileId);

  // Get the appropriate icon
  const Icon = selectedProfileId === 'custom'
    ? Sliders
    : (profile?.icon ? iconMap[profile.icon] : Scale);

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
      const modelLabel = AVAILABLE_MODELS.find(m => m.value === currentConfig.model)?.label || currentConfig.model;
      const providerLabel = INSIGHTS_PROVIDERS.find(p => p.id === currentConfig.provider)?.label || currentConfig.provider;
      return `${providerLabel}: ${modelLabel} + ${currentConfig.thinkingLevel}`;
    }
    const providerLabel = INSIGHTS_PROVIDERS.find(p => p.id === selectedProvider)?.label || selectedProvider;
    return `${providerLabel} - ${profile?.name || 'Balanced'}`;
  };

  return (
    <div className="flex items-center gap-2">
      {/* Provider Selector */}
      <Select value={selectedProvider} onValueChange={(value) => handleProviderChange(value as InsightsProvider)} disabled={disabled}>
        <SelectTrigger className="h-8 w-[140px]">
          <SelectValue placeholder="Provider" />
        </SelectTrigger>
        <SelectContent align="end">
          {INSIGHTS_PROVIDERS.map((provider) => (
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
          <DropdownMenuLabel>Agent Profile</DropdownMenuLabel>
          {DEFAULT_AGENT_PROFILES.filter(p => !p.isAutoProfile).map((p) => {
            const ProfileIcon = iconMap[p.icon || 'Brain'];
            const isSelected = selectedProfileId === p.id;
            const modelLabel = AVAILABLE_MODELS.find(m => m.value === p.model)?.label;
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
              <div className="font-medium">Custom...</div>
              <div className="text-xs text-muted-foreground">
                Choose model & thinking level
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
