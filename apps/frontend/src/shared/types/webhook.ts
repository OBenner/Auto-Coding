/**
 * Webhook system types for Auto Code UI
 *
 * Types for webhook configuration, delivery tracking, and event management.
 */

/**
 * Webhook event types for agent lifecycle events
 */
export type WebhookEventType =
  | 'spec_created'
  | 'spec_updated'
  | 'build_started'
  | 'build_completed'
  | 'build_failed'
  | 'qa_passed'
  | 'qa_failed'
  | 'merged'
  | 'pr_created'
  | '*'; // Wildcard for all events

/**
 * Webhook delivery status
 */
export type WebhookDeliveryStatus =
  | 'pending'
  | 'sending'
  | 'success'
  | 'failed'
  | 'permanent_failure'
  | 'timeout';

/**
 * Webhook payload template types
 */
export type WebhookTemplate = 'generic' | 'slack' | 'discord' | 'teams' | 'jira';

/**
 * Configuration for a webhook endpoint
 */
export interface WebhookConfig {
  webhook_id: string;
  name: string;
  url: string;
  secret?: string; // For signature verification (HMAC-SHA256)
  events: WebhookEventType[];
  template: WebhookTemplate;
  enabled: boolean;
  headers: Record<string, string>; // Custom HTTP headers
  retry_config: WebhookRetryConfig;
  created_at: string;
  updated_at: string;
}

/**
 * Retry configuration for webhook delivery
 */
export interface WebhookRetryConfig {
  max_retries: number;
  initial_delay: number; // seconds
  max_delay: number; // seconds
  backoff_multiplier: number;
}

/**
 * Record of a webhook delivery attempt
 */
export interface WebhookDelivery {
  delivery_id: string;
  webhook_id: string;
  event: string;
  status: WebhookDeliveryStatus;
  attempt_number: number;
  response_status_code?: number;
  response_body?: string;
  error_message?: string;
  duration_ms?: number;
  next_retry_at?: string;
  created_at: string;
  completed_at?: string;
  payload: Record<string, unknown>;
}

/**
 * Webhook delivery statistics
 */
export interface WebhookDeliveryStats {
  total: number;
  success: number;
  failed: number;
  pending: number;
  success_rate: number; // percentage
  avg_duration_ms: number;
}

/**
 * Test webhook result
 */
export interface WebhookTestResult {
  success: boolean;
  message: string;
  webhook_id?: string;
  status?: WebhookDeliveryStatus;
  response_code?: number;
  error?: string;
}

/**
 * Webhook event type metadata
 */
export interface WebhookEventTypeMeta {
  value: string;
  label: string;
  description: string;
  category: 'spec' | 'build' | 'qa' | 'git';
}

/**
 * Webhook template metadata
 */
export interface WebhookTemplateMeta {
  value: WebhookTemplate;
  label: string;
  description: string;
  icon?: string; // Icon name for UI
}
