import { Bot, Plus, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { cn } from '../../lib/utils';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Switch } from '../ui/switch';
import { Button } from '../ui/button';
import { SettingsSection } from './SettingsSection';
import type {
  AppSettings,
  AgentVerbosityLevel,
  AgentRiskTolerance,
  AgentProjectType
} from '../../../shared/types';

interface AgentPreferencesProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

const VERBOSITY_LEVELS: Array<{ value: AgentVerbosityLevel; label: string; descriptionKey: string }> = [
  { value: 'minimal', label: 'Minimal', descriptionKey: 'verbosity.minimal' },
  { value: 'concise', label: 'Concise', descriptionKey: 'verbosity.concise' },
  { value: 'normal', label: 'Normal', descriptionKey: 'verbosity.normal' },
  { value: 'detailed', label: 'Detailed', descriptionKey: 'verbosity.detailed' },
  { value: 'verbose', label: 'Verbose', descriptionKey: 'verbosity.verbose' }
];

const RISK_TOLERANCE_LEVELS: Array<{ value: AgentRiskTolerance; label: string; descriptionKey: string }> = [
  { value: 'cautious', label: 'Cautious', descriptionKey: 'riskTolerance.cautious' },
  { value: 'balanced', label: 'Balanced', descriptionKey: 'riskTolerance.balanced' },
  { value: 'aggressive', label: 'Aggressive', descriptionKey: 'riskTolerance.aggressive' }
];

const PROJECT_TYPES: Array<{ value: AgentProjectType; label: string; descriptionKey: string }> = [
  { value: 'greenfield', label: 'Greenfield', descriptionKey: 'projectType.greenfield' },
  { value: 'established', label: 'Established', descriptionKey: 'projectType.established' },
  { value: 'legacy', label: 'Legacy', descriptionKey: 'projectType.legacy' }
];

/**
 * Agent Preferences settings component
 * Provides UI for configuring adaptive agent behavior preferences
 */
export function AgentPreferences({ settings, onSettingsChange }: AgentPreferencesProps) {
  const { t } = useTranslation('settings');
  const [newInstruction, setNewInstruction] = useState('');

  const agentVerbosity = settings.agentVerbosity ?? 'normal';
  const agentRiskTolerance = settings.agentRiskTolerance ?? 'balanced';
  const agentProjectType = settings.agentProjectType ?? 'established';
  const agentCodingStyle = settings.agentCodingStyle ?? {};
  const agentUserInstructions = settings.agentUserInstructions ?? [];

  const handleVerbosityChange = (value: AgentVerbosityLevel) => {
    onSettingsChange({ ...settings, agentVerbosity: value });
  };

  const handleRiskToleranceChange = (value: AgentRiskTolerance) => {
    onSettingsChange({ ...settings, agentRiskTolerance: value });
  };

  const handleProjectTypeChange = (value: AgentProjectType) => {
    onSettingsChange({ ...settings, agentProjectType: value });
  };

  const handleAddInstruction = () => {
    if (newInstruction.trim()) {
      const updatedInstructions = [...agentUserInstructions, newInstruction.trim()];
      onSettingsChange({ ...settings, agentUserInstructions: updatedInstructions });
      setNewInstruction('');
    }
  };

  const handleRemoveInstruction = (index: number) => {
    const updatedInstructions = agentUserInstructions.filter((_, i) => i !== index);
    onSettingsChange({ ...settings, agentUserInstructions: updatedInstructions });
  };

  return (
    <SettingsSection
      title={t('agentPreferences.title')}
      description={t('agentPreferences.description')}
    >
      <div className="space-y-6">
        {/* Verbosity Level */}
        <div className="space-y-3">
          <Label className="text-sm font-medium text-foreground">
            {t('agentPreferences.verbosity.label')}
          </Label>
          <p className="text-sm text-muted-foreground">
            {t('agentPreferences.verbosity.description')}
          </p>
          <div
            className="grid grid-cols-2 sm:grid-cols-5 gap-2 max-w-2xl pt-1"
            role="radiogroup"
            aria-label={t('agentPreferences.verbosity.label')}
          >
            {VERBOSITY_LEVELS.map((level, idx) => {
              const isSelected = agentVerbosity === level.value;
              return (
                <button
                  type="button"
                  key={level.value}
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => handleVerbosityChange(level.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                      e.preventDefault();
                      const direction = e.key === 'ArrowRight' ? 1 : -1;
                      const newIndex = (idx + direction + VERBOSITY_LEVELS.length) % VERBOSITY_LEVELS.length;
                      handleVerbosityChange(VERBOSITY_LEVELS[newIndex].value);
                    }
                  }}
                  className={cn(
                    'flex flex-col items-center gap-2 p-3 rounded-lg border-2 transition-all',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                    isSelected
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50 hover:bg-accent/50'
                  )}
                >
                  <div className="text-center">
                    <div className="text-sm font-medium">{level.label}</div>
                    <div className="text-xs text-muted-foreground">
                      {t(`agentPreferences.${level.descriptionKey}`)}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Risk Tolerance */}
        <div className="space-y-3">
          <Label className="text-sm font-medium text-foreground">
            {t('agentPreferences.riskTolerance.label')}
          </Label>
          <p className="text-sm text-muted-foreground">
            {t('agentPreferences.riskTolerance.description')}
          </p>
          <div
            className="grid grid-cols-3 gap-3 max-w-md pt-1"
            role="radiogroup"
            aria-label={t('agentPreferences.riskTolerance.label')}
          >
            {RISK_TOLERANCE_LEVELS.map((level, idx) => {
              const isSelected = agentRiskTolerance === level.value;
              return (
                <button
                  type="button"
                  key={level.value}
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => handleRiskToleranceChange(level.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                      e.preventDefault();
                      const direction = e.key === 'ArrowRight' ? 1 : -1;
                      const newIndex = (idx + direction + RISK_TOLERANCE_LEVELS.length) % RISK_TOLERANCE_LEVELS.length;
                      handleRiskToleranceChange(RISK_TOLERANCE_LEVELS[newIndex].value);
                    }
                  }}
                  className={cn(
                    'flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                    isSelected
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50 hover:bg-accent/50'
                  )}
                >
                  <Bot className="h-4 w-4" />
                  <div className="text-center">
                    <div className="text-sm font-medium">{level.label}</div>
                    <div className="text-xs text-muted-foreground">
                      {t(`agentPreferences.${level.descriptionKey}`)}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Project Type */}
        <div className="space-y-3">
          <Label className="text-sm font-medium text-foreground">
            {t('agentPreferences.projectType.label')}
          </Label>
          <p className="text-sm text-muted-foreground">
            {t('agentPreferences.projectType.description')}
          </p>
          <div
            className="grid grid-cols-3 gap-3 max-w-md pt-1"
            role="radiogroup"
            aria-label={t('agentPreferences.projectType.label')}
          >
            {PROJECT_TYPES.map((type, idx) => {
              const isSelected = agentProjectType === type.value;
              return (
                <button
                  type="button"
                  key={type.value}
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => handleProjectTypeChange(type.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                      e.preventDefault();
                      const direction = e.key === 'ArrowRight' ? 1 : -1;
                      const newIndex = (idx + direction + PROJECT_TYPES.length) % PROJECT_TYPES.length;
                      handleProjectTypeChange(PROJECT_TYPES[newIndex].value);
                    }
                  }}
                  className={cn(
                    'flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                    isSelected
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50 hover:bg-accent/50'
                  )}
                >
                  <div className="text-center">
                    <div className="text-sm font-medium">{type.label}</div>
                    <div className="text-xs text-muted-foreground">
                      {t(`agentPreferences.${type.descriptionKey}`)}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Coding Style Preferences */}
        <div className="space-y-4 pt-4 border-t border-border">
          <div className="space-y-1">
            <Label className="text-sm font-medium text-foreground">
              {t('agentPreferences.codingStyle.label')}
            </Label>
            <p className="text-sm text-muted-foreground">
              {t('agentPreferences.codingStyle.description')}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 max-w-md">
            {/* Indentation */}
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                {t('agentPreferences.codingStyle.indentation')}
              </Label>
              <Select
                value={agentCodingStyle.indentation ?? 'auto'}
                onValueChange={(value) => {
                  onSettingsChange({
                    ...settings,
                    agentCodingStyle: { ...agentCodingStyle, indentation: value as 'spaces' | 'tabs' | 'auto' }
                  });
                }}
              >
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">{t('agentPreferences.codingStyle.auto')}</SelectItem>
                  <SelectItem value="spaces">{t('agentPreferences.codingStyle.spaces')}</SelectItem>
                  <SelectItem value="tabs">{t('agentPreferences.codingStyle.tabs')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Quote Style */}
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                {t('agentPreferences.codingStyle.quoteStyle')}
              </Label>
              <Select
                value={agentCodingStyle.quoteStyle ?? 'auto'}
                onValueChange={(value) => {
                  onSettingsChange({
                    ...settings,
                    agentCodingStyle: { ...agentCodingStyle, quoteStyle: value as 'single' | 'double' | 'auto' }
                  });
                }}
              >
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">{t('agentPreferences.codingStyle.auto')}</SelectItem>
                  <SelectItem value="single">{t('agentPreferences.codingStyle.single')}</SelectItem>
                  <SelectItem value="double">{t('agentPreferences.codingStyle.double')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Naming Convention */}
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                {t('agentPreferences.codingStyle.namingConvention')}
              </Label>
              <Select
                value={agentCodingStyle.namingConvention ?? 'auto'}
                onValueChange={(value) => {
                  onSettingsChange({
                    ...settings,
                    agentCodingStyle: { ...agentCodingStyle, namingConvention: value as 'snake_case' | 'camelCase' | 'PascalCase' | 'auto' }
                  });
                }}
              >
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">{t('agentPreferences.codingStyle.auto')}</SelectItem>
                  <SelectItem value="snake_case">snake_case</SelectItem>
                  <SelectItem value="camelCase">camelCase</SelectItem>
                  <SelectItem value="PascalCase">PascalCase</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Comment Density */}
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                {t('agentPreferences.codingStyle.commentDensity')}
              </Label>
              <Select
                value={agentCodingStyle.commentDensity ?? 'normal'}
                onValueChange={(value) => {
                  onSettingsChange({
                    ...settings,
                    agentCodingStyle: { ...agentCodingStyle, commentDensity: value as 'minimal' | 'normal' | 'verbose' }
                  });
                }}
              >
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="minimal">{t('agentPreferences.codingStyle.minimal')}</SelectItem>
                  <SelectItem value="normal">{t('agentPreferences.codingStyle.normalComments')}</SelectItem>
                  <SelectItem value="verbose">{t('agentPreferences.codingStyle.verbose')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Type Hints */}
          <div className="flex items-center justify-between max-w-md">
            <div className="space-y-1">
              <Label className="text-sm font-medium text-foreground">
                {t('agentPreferences.codingStyle.typeHints')}
              </Label>
              <p className="text-sm text-muted-foreground">
                {t('agentPreferences.codingStyle.typeHintsDescription')}
              </p>
            </div>
            <Switch
              checked={agentCodingStyle.typeHints ?? true}
              onCheckedChange={(checked) => {
                onSettingsChange({
                  ...settings,
                  agentCodingStyle: { ...agentCodingStyle, typeHints: checked }
                });
              }}
            />
          </div>
        </div>

        {/* User Instructions */}
        <div className="space-y-4 pt-4 border-t border-border">
          <div className="space-y-1">
            <Label className="text-sm font-medium text-foreground">
              {t('agentPreferences.userInstructions.label')}
            </Label>
            <p className="text-sm text-muted-foreground">
              {t('agentPreferences.userInstructions.description')}
            </p>
          </div>

          {/* Add Instruction Input */}
          <div className="flex gap-2 max-w-md">
            <Input
              placeholder={t('agentPreferences.userInstructions.placeholder')}
              value={newInstruction}
              onChange={(e) => setNewInstruction(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleAddInstruction();
                }
              }}
              className="flex-1"
            />
            <Button
              type="button"
              onClick={handleAddInstruction}
              disabled={!newInstruction.trim()}
              size="icon"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          {/* Instructions List */}
          {agentUserInstructions.length > 0 && (
            <div className="space-y-2 max-w-md">
              {agentUserInstructions.map((instruction, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 p-2 rounded-lg bg-muted/50 border border-border"
                >
                  <span className="flex-1 text-sm">{instruction}</span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveInstruction(index)}
                    className="h-6 w-6 shrink-0"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </SettingsSection>
  );
}
