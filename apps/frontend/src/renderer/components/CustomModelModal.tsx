import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription
} from './ui/dialog';
import { Button } from './ui/button';
import { Label } from './ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from './ui/select';
import { AVAILABLE_MODELS, THINKING_LEVELS } from '../../shared/constants';
import { getModelsForProvider } from '../../shared/constants/api-profiles';
import type { InsightsModelConfig, InsightsProvider } from '../../shared/types';
import type { ModelType, ThinkingLevel } from '../../shared/types';

interface CustomModelModalProps {
  currentConfig?: InsightsModelConfig;
  onSave: (config: InsightsModelConfig) => void;
  onClose: () => void;
  open?: boolean;
}

// Map Insights provider IDs to API provider IDs
const INSIGHTS_TO_API_PROVIDER: Record<InsightsProvider, string> = {
  claude: 'anthropic',
  litellm: 'litellm',
  openrouter: 'openrouter',
  openai: 'openai'
};

export function CustomModelModal({ currentConfig, onSave, onClose, open = true }: CustomModelModalProps) {
  const { t } = useTranslation(['dialogs', 'common']);
  const [model, setModel] = useState<ModelType>(
    currentConfig?.model || 'sonnet'
  );
  const [thinkingLevel, setThinkingLevel] = useState<ThinkingLevel>(
    currentConfig?.thinkingLevel || 'medium'
  );
  const [provider, setProvider] = useState<InsightsProvider>(
    currentConfig?.provider || 'claude'
  );

  // Build provider options with i18n
  const insightsProviders = useMemo(() => [
    { id: 'claude' as InsightsProvider, label: t('dialogs:customModel.providers.claude'), description: t('dialogs:customModel.providers.claudeDesc') },
    { id: 'openai' as InsightsProvider, label: t('dialogs:customModel.providers.openai'), description: t('dialogs:customModel.providers.openaiDesc') },
    { id: 'litellm' as InsightsProvider, label: t('dialogs:customModel.providers.litellm'), description: t('dialogs:customModel.providers.litellmDesc') },
    { id: 'openrouter' as InsightsProvider, label: t('dialogs:customModel.providers.openrouter'), description: t('dialogs:customModel.providers.openrouterDesc') }
  ], [t]);

  // Sync internal state when modal opens or config changes
  useEffect(() => {
    if (open) {
      setModel(currentConfig?.model || 'sonnet');
      setThinkingLevel(currentConfig?.thinkingLevel || 'medium');
      setProvider(currentConfig?.provider || 'claude');
    }
  }, [open, currentConfig]);

  // Get available models for the selected provider
  const availableModels = useMemo(() => {
    if (provider === 'litellm') {
      // LiteLLM supports all tiers, use generic labels
      return AVAILABLE_MODELS;
    }

    // Get provider-specific models
    const apiProviderId = INSIGHTS_TO_API_PROVIDER[provider];
    const models = getModelsForProvider(apiProviderId);

    // Filter to only models with known tiers (opus, sonnet, haiku)
    const tieredModels = models.filter(m => m.tier === 'opus' || m.tier === 'sonnet' || m.tier === 'haiku');

    // Map to the format expected by the select component
    return tieredModels.map(m => ({
      value: m.tier as ModelType,
      label: m.name,
      description: m.description
    }));
  }, [provider]);

  const handleSave = () => {
    onSave({
      profileId: 'custom',
      model,
      thinkingLevel,
      provider
    });
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t('dialogs:customModel.title')}</DialogTitle>
          <DialogDescription>
            {t('dialogs:customModel.description')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="provider-select">{t('dialogs:customModel.provider')}</Label>
            <Select value={provider} onValueChange={(v) => setProvider(v as InsightsProvider)}>
              <SelectTrigger id="provider-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {insightsProviders.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    <div className="flex flex-col">
                      <span className="font-medium">{p.label}</span>
                      <span className="text-xs text-muted-foreground">{p.description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="model-select">{t('dialogs:customModel.model')}</Label>
            <Select value={model} onValueChange={(v) => setModel(v as ModelType)}>
              <SelectTrigger id="model-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {availableModels.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    <div className="flex flex-col">
                      <span className="font-medium">{m.label}</span>
                      {m.description && (
                        <span className="text-xs text-muted-foreground">{m.description}</span>
                      )}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="thinking-select">{t('dialogs:customModel.thinkingLevel')}</Label>
            <Select value={thinkingLevel} onValueChange={(v) => setThinkingLevel(v as ThinkingLevel)}>
              <SelectTrigger id="thinking-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {THINKING_LEVELS.map((level) => (
                  <SelectItem key={level.value} value={level.value}>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{level.label}</span>
                      <span className="text-xs text-muted-foreground">
                        {level.description}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t('dialogs:customModel.cancel')}
          </Button>
          <Button onClick={handleSave}>
            {t('dialogs:customModel.apply')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
