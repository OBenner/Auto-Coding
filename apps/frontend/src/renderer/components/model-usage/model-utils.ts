/**
 * Shared utilities for model usage components.
 *
 * Extracted to avoid code duplication across ModelUsageCard,
 * AgentModelDisplay, and ModelChangeConfirmationDialog.
 */

/**
 * Parse model ID to get display name and version.
 * Handles both tier shorthands ("opus", "sonnet", "haiku") and full model IDs
 * ("claude-sonnet-4-5-20250929").
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

  // Parse full model ID: "claude-sonnet-4-5-20250929"
  const parts = modelId.split('-');
  const tier = parts[1] || 'unknown';
  const version = parts.slice(2).join('.').substring(0, 3); // e.g., "4.5"

  return {
    name: tierNames[tier] || tier.charAt(0).toUpperCase() + tier.slice(1),
    version: version || 'latest',
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
