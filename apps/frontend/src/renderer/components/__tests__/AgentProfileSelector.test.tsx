/**
 * @vitest-environment jsdom
 */
/**
 * Tests for AgentProfileSelector component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AgentProfileSelector } from '../AgentProfileSelector';
import type { ModelType, ThinkingLevel } from '../../../shared/types';
import type { PhaseModelConfig, PhaseThinkingConfig } from '../../../shared/types/settings';

// Mock i18n translation function
vi.mock('react-i18next', () => ({
  useTranslation: vi.fn(() => ({
    t: (key: string, params?: Record<string, unknown>) => {
      // For translation keys, return test values
      const translations: Record<string, string> = {
        'agentProfile.label': 'Agent Profile',
        'agentProfile.customConfiguration': 'Custom Configuration',
        'agentProfile.customDescription': 'Manual settings',
        'agentProfile.custom': 'Custom',
        'agentProfile.phaseConfiguration': 'Phase Configuration',
        'agentProfile.clickToCustomize': 'Click to customize',
        'agentProfile.model': 'Model',
        'agentProfile.thinking': 'Thinking',
        'agentProfile.selectModel': 'Select model',
        'agentProfile.selectThinkingLevel': 'Select thinking level',
        'agentProfile.phases.spec.label': 'Spec',
        'agentProfile.phases.spec.description': 'Specification phase',
        'agentProfile.phases.planning.label': 'Planning',
        'agentProfile.phases.planning.description': 'Planning phase',
        'agentProfile.phases.coding.label': 'Coding',
        'agentProfile.phases.coding.description': 'Implementation phase',
        'agentProfile.phases.qa.label': 'QA',
        'agentProfile.phases.qa.description': 'Quality assurance phase'
      };
      if (params && Object.keys(params).length > 0) {
        return translations[key] || key;
      }
      return translations[key] || key;
    }
  }))
}));

describe('AgentProfileSelector', () => {
  const mockOnProfileChange = vi.fn();
  const mockOnModelChange = vi.fn();
  const mockOnThinkingLevelChange = vi.fn();
  const mockOnPhaseModelsChange = vi.fn();
  const mockOnPhaseThinkingChange = vi.fn();

  const defaultProps = {
    profileId: 'auto',
    model: 'opus' as ModelType,
    thinkingLevel: 'high' as ThinkingLevel,
    onProfileChange: mockOnProfileChange,
    onModelChange: mockOnModelChange,
    onThinkingLevelChange: mockOnThinkingLevelChange,
    disabled: false
  };

  const defaultPhaseModels: PhaseModelConfig = {
    spec: 'opus',
    planning: 'opus',
    coding: 'opus',
    qa: 'opus'
  };

  const defaultPhaseThinking: PhaseThinkingConfig = {
    spec: 'ultrathink',
    planning: 'high',
    coding: 'low',
    qa: 'low'
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Profile selection', () => {
    it('should render with auto profile selected by default', () => {
      render(<AgentProfileSelector {...defaultProps} />);

      expect(screen.getByLabelText('Agent Profile')).toBeInTheDocument();
      expect(screen.getByText('Auto (Optimized)')).toBeInTheDocument();
    });

    it('should display correct profile icon and label', () => {
      render(<AgentProfileSelector {...defaultProps} />);

      // Auto profile should show Sparkles icon and label
      expect(screen.getByText('Auto (Optimized)')).toBeInTheDocument();
    });

    it('should call onProfileChange when selecting a different profile', async () => {
      render(<AgentProfileSelector {...defaultProps} />);

      // Open the select dropdown
      const trigger = screen.getByRole('combobox', { name: /agent profile/i });
      fireEvent.click(trigger);

      // Wait for options to appear
      await waitFor(() => {
        expect(screen.getByRole('option', { name: /complex tasks/i })).toBeInTheDocument();
      });

      // Click on "Complex Tasks" option
      fireEvent.click(screen.getByRole('option', { name: /complex tasks/i }));

      expect(mockOnProfileChange).toHaveBeenCalledWith('complex', 'opus', 'ultrathink');
    });

    it('should show all preset profiles in dropdown', async () => {
      render(<AgentProfileSelector {...defaultProps} />);

      // Open the select dropdown
      const trigger = screen.getByRole('combobox', { name: /agent profile/i });
      fireEvent.click(trigger);

      // Wait for options and verify all profiles are present
      await waitFor(() => {
        expect(screen.getByRole('option', { name: /auto.*optimized/i })).toBeInTheDocument();
        expect(screen.getByRole('option', { name: /complex tasks/i })).toBeInTheDocument();
        expect(screen.getByRole('option', { name: /balanced/i })).toBeInTheDocument();
        expect(screen.getByRole('option', { name: /quick edits/i })).toBeInTheDocument();
        expect(screen.getByRole('option', { name: /custom/i })).toBeInTheDocument();
      });
    });
  });

  describe('Custom profile mode', () => {
    it('should show custom configuration when custom profile is selected', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="custom"
        />
      );

      expect(screen.getByText('Custom Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText('Model')).toBeInTheDocument();
      expect(screen.getByLabelText('Thinking')).toBeInTheDocument();
    });

    it('should not show phase configuration in custom mode', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="custom"
        />
      );

      expect(screen.queryByText('Phase Configuration')).not.toBeInTheDocument();
    });

    it('should call onModelChange when model is changed in custom mode', async () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="custom"
          model="opus"
        />
      );

      // Open model select
      const modelTrigger = screen.getAllByRole('combobox')[1]; // Second combobox is the model selector
      fireEvent.click(modelTrigger);

      // Wait for options and select sonnet
      await waitFor(() => {
        expect(screen.getByRole('option', { name: /sonnet.*balanced/i })).toBeInTheDocument();
      });
      fireEvent.click(screen.getByRole('option', { name: /sonnet.*balanced/i }));

      expect(mockOnModelChange).toHaveBeenCalledWith('sonnet');
    });

    it('should call onThinkingLevelChange when thinking level is changed in custom mode', async () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="custom"
          thinkingLevel="medium"
        />
      );

      // Open thinking level select (third combobox)
      const thinkingTrigger = screen.getAllByRole('combobox')[2];
      fireEvent.click(thinkingTrigger);

      // Wait for options and select high
      await waitFor(() => {
        expect(screen.getByRole('option', { name: /high.*deep thinking/i })).toBeInTheDocument();
      });
      fireEvent.click(screen.getByRole('option', { name: /high.*deep thinking/i }));

      expect(mockOnThinkingLevelChange).toHaveBeenCalledWith('high');
    });

    it('should preserve current model and thinking level when switching to custom', async () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="auto"
          model="sonnet"
          thinkingLevel="medium"
        />
      );

      // Open profile select
      const trigger = screen.getByRole('combobox', { name: /agent profile/i });
      fireEvent.click(trigger);

      // Select custom
      await waitFor(() => {
        expect(screen.getByRole('option', { name: /custom/i })).toBeInTheDocument();
      });
      fireEvent.click(screen.getByRole('option', { name: /custom/i }));

      expect(mockOnProfileChange).toHaveBeenCalledWith('custom', 'sonnet', 'medium');
    });

    it('should use default values when switching to custom with empty model/thinking', async () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="auto"
          model=""
          thinkingLevel=""
        />
      );

      // Open profile select
      const trigger = screen.getByRole('combobox', { name: /agent profile/i });
      fireEvent.click(trigger);

      // Select custom
      await waitFor(() => {
        expect(screen.getByRole('option', { name: /custom/i })).toBeInTheDocument();
      });
      fireEvent.click(screen.getByRole('option', { name: /custom/i }));

      expect(mockOnProfileChange).toHaveBeenCalledWith('custom', 'sonnet', 'medium');
    });
  });

  describe('Phase configuration', () => {
    it('should show phase configuration for preset profiles', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="auto"
          phaseModels={defaultPhaseModels}
          phaseThinking={defaultPhaseThinking}
        />
      );

      expect(screen.getByText('Phase Configuration')).toBeInTheDocument();
      expect(screen.getByText('Click to customize')).toBeInTheDocument();
    });

    it('should expand phase details when header is clicked', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="auto"
          phaseModels={defaultPhaseModels}
          phaseThinking={defaultPhaseThinking}
        />
      );

      // Initially collapsed - detailed descriptions should not be visible
      expect(screen.queryByText('Specification phase')).not.toBeInTheDocument();
      expect(screen.queryByText('Planning phase')).not.toBeInTheDocument();

      // Click header to expand
      const headerButton = screen.getByRole('button', { name: /phase configuration/i });
      fireEvent.click(headerButton);

      // Details should be visible
      expect(screen.getByText('Specification phase')).toBeInTheDocument();
      expect(screen.getByText('Planning phase')).toBeInTheDocument();
      expect(screen.getByText('Implementation phase')).toBeInTheDocument();
      expect(screen.getByText('Quality assurance phase')).toBeInTheDocument();
    });

    it('should collapse phase details when header is clicked again', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="auto"
          phaseModels={defaultPhaseModels}
          phaseThinking={defaultPhaseThinking}
        />
      );

      const headerButton = screen.getByRole('button', { name: /phase configuration/i });

      // Expand
      fireEvent.click(headerButton);
      expect(screen.getByText('Specification phase')).toBeInTheDocument();

      // Collapse
      fireEvent.click(headerButton);
      expect(screen.queryByText('Specification phase')).not.toBeInTheDocument();
    });

    it('should call onPhaseModelsChange when phase model is changed', async () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="auto"
          phaseModels={defaultPhaseModels}
          phaseThinking={defaultPhaseThinking}
          onPhaseModelsChange={mockOnPhaseModelsChange}
        />
      );

      // Expand phase details
      const headerButton = screen.getByRole('button', { name: /phase configuration/i });
      fireEvent.click(headerButton);

      // Get all comboboxes - after expanding, there should be 9 total:
      // 1 main profile selector + 4 phase model selects + 4 phase thinking selects
      const allComboboxes = screen.getAllByRole('combobox');
      // The first phase model select should be index 1 (after main profile selector)
      const firstPhaseModelSelect = allComboboxes[1];
      fireEvent.click(firstPhaseModelSelect);

      // Select haiku (different from current opus, and won't match other profiles)
      await waitFor(() => {
        expect(screen.getByRole('option', { name: /haiku.*fast/i })).toBeInTheDocument();
      });
      fireEvent.click(screen.getByRole('option', { name: /haiku.*fast/i }));

      expect(mockOnPhaseModelsChange).toHaveBeenCalledWith({
        spec: 'haiku',
        planning: 'opus',
        coding: 'opus',
        qa: 'opus'
      });
    });

    it('should call onPhaseThinkingChange when phase thinking level is changed', async () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="auto"
          phaseModels={defaultPhaseModels}
          phaseThinking={defaultPhaseThinking}
          onPhaseThinkingChange={mockOnPhaseThinkingChange}
        />
      );

      // Expand phase details
      const headerButton = screen.getByRole('button', { name: /phase configuration/i });
      fireEvent.click(headerButton);

      // Get all comboboxes - there should be 9 total:
      // 1 main profile selector + 4 phase model selects + 4 phase thinking selects
      const allComboboxes = screen.getAllByRole('combobox');
      // The first phase thinking select should be index 2 (after main profile and first model select)
      const firstPhaseThinkingSelect = allComboboxes[2];
      fireEvent.click(firstPhaseThinkingSelect);

      // Select low (different from current ultrathink)
      await waitFor(() => {
        expect(screen.getByRole('option', { name: /^low/i })).toBeInTheDocument();
      });
      fireEvent.click(screen.getByRole('option', { name: /^low/i }));

      expect(mockOnPhaseThinkingChange).toHaveBeenCalledWith({
        spec: 'low',
        planning: 'high',
        coding: 'low',
        qa: 'low'
      });
    });

    it('should use default phase configs when none provided', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="balanced"
        />
      );

      expect(screen.getByText('Phase Configuration')).toBeInTheDocument();
    });

    it('should initialize phase configs when selecting preset profile', async () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="custom"
          onPhaseModelsChange={mockOnPhaseModelsChange}
          onPhaseThinkingChange={mockOnPhaseThinkingChange}
        />
      );

      // Open profile select
      const trigger = screen.getByRole('combobox', { name: /agent profile/i });
      fireEvent.click(trigger);

      // Select balanced profile
      await waitFor(() => {
        expect(screen.getByRole('option', { name: /balanced/i })).toBeInTheDocument();
      });
      fireEvent.click(screen.getByRole('option', { name: /balanced/i }));

      // Should call phase change callbacks with balanced profile defaults
      expect(mockOnPhaseModelsChange).toHaveBeenCalledWith({
        spec: 'sonnet',
        planning: 'sonnet',
        coding: 'sonnet',
        qa: 'sonnet'
      });
      expect(mockOnPhaseThinkingChange).toHaveBeenCalledWith({
        spec: 'medium',
        planning: 'medium',
        coding: 'medium',
        qa: 'medium'
      });
    });
  });

  describe('Disabled state', () => {
    it('should disable all controls when disabled prop is true', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          disabled={true}
        />
      );

      const selects = screen.getAllByRole('combobox');
      selects.forEach(select => {
        expect(select).toBeDisabled();
      });
    });

    it('should disable phase configuration header when disabled', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="auto"
          phaseModels={defaultPhaseModels}
          disabled={true}
        />
      );

      const headerButton = screen.getByRole('button', { name: /phase configuration/i });
      expect(headerButton).toBeDisabled();
    });

    it('should disable custom mode controls when disabled', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="custom"
          disabled={true}
        />
      );

      const selects = screen.getAllByRole('combobox');
      selects.forEach(select => {
        expect(select).toBeDisabled();
      });
    });
  });

  describe('Profile display', () => {
    it('should display correct description for each profile', () => {
      const { rerender } = render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="auto"
        />
      );
      expect(screen.getByText(/uses opus across all phases with optimized thinking levels/i)).toBeInTheDocument();

      rerender(
        <AgentProfileSelector
          {...defaultProps}
          profileId="complex"
        />
      );
      expect(screen.getByText(/for intricate, multi-step implementations requiring deep analysis/i)).toBeInTheDocument();

      rerender(
        <AgentProfileSelector
          {...defaultProps}
          profileId="balanced"
        />
      );
      expect(screen.getByText(/good balance of speed and quality for most tasks/i)).toBeInTheDocument();

      rerender(
        <AgentProfileSelector
          {...defaultProps}
          profileId="quick"
        />
      );
      expect(screen.getByText(/fast iterations for simple changes and quick fixes/i)).toBeInTheDocument();

      rerender(
        <AgentProfileSelector
          {...defaultProps}
          profileId="custom"
        />
      );
      expect(screen.getByText('Manual settings')).toBeInTheDocument();
    });

    it('should fallback to auto profile display when profileId not found', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="non-existent-profile"
        />
      );

      expect(screen.getByText('Auto (Optimized)')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper labels for all form controls', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="custom"
        />
      );

      expect(screen.getByLabelText('Agent Profile')).toBeInTheDocument();
      expect(screen.getByLabelText('Model')).toBeInTheDocument();
      expect(screen.getByLabelText('Thinking')).toBeInTheDocument();
    });

    it('should support keyboard navigation', () => {
      render(<AgentProfileSelector {...defaultProps} />);

      const trigger = screen.getByRole('combobox', { name: /agent profile/i });

      // Focus the trigger
      trigger.focus();
      expect(trigger).toHaveFocus();

      // Space to open (test the interaction)
      fireEvent.keyDown(trigger, { key: ' ', code: 'Space' });
    });

    it('should have accessible phase configuration toggle button', () => {
      render(
        <AgentProfileSelector
          {...defaultProps}
          profileId="auto"
          phaseModels={defaultPhaseModels}
        />
      );

      const toggleButton = screen.getByRole('button', { name: /phase configuration/i });
      expect(toggleButton).toHaveAttribute('type', 'button');

      // Should be keyboard accessible (focusable)
      toggleButton.focus();
      expect(toggleButton).toHaveFocus();

      // Click to expand
      fireEvent.click(toggleButton);
      expect(screen.getByText('Specification phase')).toBeInTheDocument();
    });
  });
});
