/**
 * Shared utilities for model usage components.
 *
 * Extracted to avoid code duplication across ModelUsageCard,
 * AgentModelDisplay, and ModelChangeConfirmationDialog.
 */

/**
 * Parse model ID to get display name and version.
 * Handles tier shorthands ("opus", "sonnet", "haiku"), full Claude model IDs
 * ("claude-sonnet-4-5-20250929"), and non-Claude model IDs gracefully.
 */
export function parseModelId(modelId: string): { name: string; version: string } {
  const tierNames: Record<string, string> = {
    opus: 'Opus',
    sonnet: 'Sonnet',
    haiku: 'Haiku',
  };

  // Handle tier shorthands
  if (modelId in tierNames) {
    return { name: tierNames[modelId], version: 'Default' };
  }

  // Parse full Claude model ID: "claude-sonnet-4-5-20250929"
  // Pattern: claude-<tier>-<major>-<minor>-<date>
  const claudeMatch = modelId.match(/^claude-(\w+)-(\d+)-(\d+)-(\d+)$/);
  if (claudeMatch) {
    const [, tier, major, minor] = claudeMatch;
    return {
      name: tierNames[tier] || tier.charAt(0).toUpperCase() + tier.slice(1),
      version: `${major}.${minor}`,
    };
  }

  // Fallback for non-Claude or unrecognized model IDs
  // Return the full ID as the name with no version
  return {
    name: modelId,
    version: '',
  };
}

/**
 * Format an agent type string for display.
 * Converts snake_case to Title Case: "spec_gatherer" -> "Spec Gatherer"
 */
export function getAgentLabel(agentType: string): string {
  return agentType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Format a number with locale-specific thousands separators.
 */
export function formatNumber(num: number): string {
  return num.toLocaleString();
}

/**
 * Format a monetary amount as USD currency string.
 */
export function formatCurrency(amount: number): string {
  return `$${amount.toFixed(2)}`;
}
