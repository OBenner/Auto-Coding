/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import type { GenericEditArtifactManifest } from '../../../../shared/types';
import { GenericEditArtifactsPanel } from '../GenericEditArtifactsPanel';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, values?: Record<string, unknown>) => {
      const normalizedKey = key.replace(/^tasks:/, '');
      const translations: Record<string, string> = {
        'overview.genericEditArtifacts': 'Generic Edit Artifacts',
        'overview.genericEditProvider': 'Provider',
        'overview.genericEditStopReason': 'Stop reason',
        'overview.genericEditIterations': 'Iterations',
        'overview.genericEditActions': 'Actions',
        'overview.genericEditEvents': 'Events',
        'overview.genericEditTransactions': 'Transactions',
        'overview.genericEditRecoveryAttempts': 'Recovery attempts',
        'overview.genericEditMutationSnapshots': 'Mutation snapshots',
        'overview.genericEditTransactionGroups': 'Transaction groups',
        'overview.genericEditResumable': 'Resumable',
        'overview.genericEditRecoverable': 'Recoverable',
        'overview.genericEditRecoveryPlan': 'Recovery plan',
        'overview.genericEditArtifactsPresent': `${values?.present ?? 0}/${values?.total ?? 0} present`,
        'overview.genericEditActiveArtifacts': 'Active artifacts',
        'overview.genericEditMissingArtifact': 'Missing',
        'overview.genericEditViewArtifact': 'View artifact',
        'overview.genericEditArtifactPreview': 'Artifact preview',
        'overview.genericEditRecentEvents': 'Recent events',
        'overview.genericEditEventOk': 'OK',
        'overview.genericEditEventFailed': 'Failed',
        'overview.genericEditRecoveryStatus': 'Recovery status',
        'overview.genericEditFinishBlocked': 'Finish blocked',
        'overview.genericEditRecoveryWarnings': 'Warnings',
        'overview.genericEditRecoveryActions': 'Recovery actions',
        'overview.genericEditRequiredAction': 'Required',
        'overview.genericEditResolutionStrategies': 'Resolution strategies',
        'overview.genericEditRecommendedVerificationTools': 'Verification tools',
        'overview.genericEditResumeEntrypoint': 'Resume entrypoint',
        'overview.genericEditResumeStrategy': 'Resume strategy',
        'overview.genericEditNextIteration': `Next iteration ${values?.iteration ?? ''}`,
        'overview.genericEditMcpSupport': 'MCP support',
        'overview.genericEditMcpTools': `${values?.count ?? 0} MCP tools`,
        'overview.genericEditMcpAvailable': 'Available',
        'overview.genericEditMcpUnavailable': 'Unavailable',
        'overview.genericEditMcpActionRequired': 'Action required',
      };
      return translations[normalizedKey] || translations[key] || key;
    },
  }),
}));

function createManifest(): GenericEditArtifactManifest {
  return {
    artifact_type: 'generic_edit_artifact_manifest',
    schema_version: 1,
    timestamp: '2026-05-09T10:00:00Z',
    provider: 'openai',
    subtask_id: 'subtask-1',
    status: 'error',
    stop_reason: 'max_iterations',
    entrypoints: {
      result: '/tmp/result.json',
      summary: '/tmp/summary.md',
      events: '/tmp/events.jsonl',
      session_state: '/tmp/session.json',
      trace: '/tmp/trace.json',
    },
    flags: {
      recoverable: true,
      resumable: true,
      resumed: false,
      recovery_required: false,
      recovery_resolved: false,
      has_recovery_plan: true,
      has_mutation_snapshots: true,
      has_transaction_groups: true,
    },
    counts: {
      iteration_count: 2,
      action_count: 5,
      failed_action_count: 1,
      event_count: 9,
      transaction_count: 3,
      transaction_group_count: 1,
      mutation_snapshot_count: 2,
      recovery_attempt_count: 1,
      failed_recovery_attempt_count: 0,
    },
    artifacts: [
      {
        name: 'generic_edit_result',
        kind: 'result',
        path: '/tmp/result.json',
        active: true,
        required: true,
        present: true,
      },
      {
        name: 'generic_edit_recovery_plan',
        kind: 'recovery_plan',
        path: '/tmp/recovery.json',
        active: true,
        required: false,
        present: false,
      },
    ],
    recent_events: [
      {
        sequence: 8,
        event_type: 'action_result',
        tool: 'read_file',
        ok: false,
        message: 'File not found',
        transaction_id: 'json_actions-2',
      },
    ],
    recovery_summary: {
      version: 1,
      status: 'requires_resolution',
      finish_blocked: true,
      unresolved_transaction_group_count: 1,
      unresolved_transaction_group_ids: ['transaction-group-1'],
      warning_count: 1,
      warnings: ['Run focused verification before finish.'],
      resolution_strategies: ['rollback_transaction', 'repair_mutation'],
      recommended_verification_tools: ['git_diff', 'run_command'],
    },
    recovery_actions: [
      {
        id: 'inspect-json_actions-1-1',
        kind: 'inspect_diff',
        tool: 'git_diff',
        transaction_id: 'json_actions-1',
        transaction_group_id: 'transaction-group-1',
        paths: ['partial.txt'],
        required_before_finish: true,
      },
      {
        id: 'rollback-json_actions-1',
        kind: 'rollback_transaction',
        tool: 'rollback_transaction',
        transaction_id: 'json_actions-1',
        transaction_group_id: 'transaction-group-1',
        rollback_operation_id: 'rollback-json_actions-1',
        mutation_snapshot_ids: ['mutation-1'],
        required_before_finish: true,
      },
    ],
    resume_action: {
      runtime: 'generic_edit',
      checkpoint_path: '/tmp/recovery-checkpoint.json',
      strategy: 'recover_partial_failure',
      next_iteration: 3,
    },
    resume_inputs: {
      trace_artifact: '/tmp/trace.json',
      event_artifact: '/tmp/events.jsonl',
      recovery_plan_artifact: '/tmp/recovery.json',
      mutation_snapshot_artifact: '/tmp/mutation-snapshots.json',
    },
    mcp_support: {
      strategy: 'local_bridge',
      reason: 'External MCP tools are bridged through generic_edit.',
      tool_count: 2,
      available_servers: ['context7'],
      unavailable_servers: ['linear'],
      bridge_plan: {
        status: 'partial',
        action_required: 'configure_external_mcp_client',
      },
      bridge: {
        tools: ['mcp__context7__resolve-library-id', 'mcp__context7__get-library-docs'],
      },
    },
    resume: null,
  };
}

describe('GenericEditArtifactsPanel', () => {
  it('renders runtime status, recovery flags, and active artifact presence', () => {
    render(<GenericEditArtifactsPanel manifest={createManifest()} />);

    expect(screen.getByText('Generic Edit Artifacts')).toBeInTheDocument();
    expect(screen.getByText('openai')).toBeInTheDocument();
    expect(screen.getByText('max_iterations')).toBeInTheDocument();
    expect(screen.getByText('Resumable')).toBeInTheDocument();
    expect(screen.getByText('Recoverable')).toBeInTheDocument();
    expect(screen.getByText('Recovery plan')).toBeInTheDocument();
    expect(screen.getByText('1/2 present')).toBeInTheDocument();
    expect(screen.getByText('generic_edit_recovery_plan')).toBeInTheDocument();
    expect(screen.getByText('Missing')).toBeInTheDocument();
    expect(screen.getByText('Recent events')).toBeInTheDocument();
    expect(screen.getByText('read_file')).toBeInTheDocument();
    expect(screen.getByText(/File not found/)).toBeInTheDocument();
    expect(screen.getByText('Recovery status')).toBeInTheDocument();
    expect(screen.getByText('requires_resolution')).toBeInTheDocument();
    expect(screen.getByText('Finish blocked')).toBeInTheDocument();
    expect(screen.getByText('Warnings')).toBeInTheDocument();
    expect(screen.getByText('Run focused verification before finish.')).toBeInTheDocument();
    expect(screen.getByText('Resolution strategies')).toBeInTheDocument();
    expect(screen.getByText('repair_mutation')).toBeInTheDocument();
    expect(screen.getByText('Verification tools')).toBeInTheDocument();
    expect(screen.getByText('run_command')).toBeInTheDocument();
    expect(screen.getByText('Recovery actions')).toBeInTheDocument();
    expect(screen.getByText('inspect_diff')).toBeInTheDocument();
    expect(screen.getAllByText('rollback_transaction')).toHaveLength(2);
    expect(screen.getByText(/partial.txt/)).toBeInTheDocument();
    expect(screen.getAllByText('Required')).toHaveLength(2);
    expect(screen.getByText('Resume entrypoint')).toBeInTheDocument();
    expect(screen.getByText('Resume strategy')).toBeInTheDocument();
    expect(screen.getByText('recover_partial_failure')).toBeInTheDocument();
    expect(screen.getByText('Next iteration 3')).toBeInTheDocument();
    expect(screen.getByText('/tmp/recovery-checkpoint.json')).toBeInTheDocument();
    expect(screen.getByText('MCP support')).toBeInTheDocument();
    expect(screen.getByText('local_bridge')).toBeInTheDocument();
    expect(screen.getByText('2 MCP tools')).toBeInTheDocument();
    expect(screen.getByText('External MCP tools are bridged through generic_edit.')).toBeInTheDocument();
    expect(screen.getByText('Available')).toBeInTheDocument();
    expect(screen.getByText('context7')).toBeInTheDocument();
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.getByText('linear')).toBeInTheDocument();
    expect(screen.getByText('Action required')).toBeInTheDocument();
    expect(screen.getByText('configure_external_mcp_client')).toBeInTheDocument();
    expect(screen.getByText('mcp__context7__resolve-library-id')).toBeInTheDocument();
  });

  it('opens an inline preview for present artifacts with paths', async () => {
    const readFile = vi.fn().mockResolvedValue({ success: true, data: '{"ok": true}' });
    Object.defineProperty(window, 'electronAPI', {
      value: { readFile },
      configurable: true,
    });

    render(<GenericEditArtifactsPanel manifest={createManifest()} />);

    fireEvent.click(screen.getByLabelText('View artifact'));

    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('/tmp/result.json');
    });
    expect(await screen.findByText('Artifact preview')).toBeInTheDocument();
    expect(screen.getByText('{"ok": true}')).toBeInTheDocument();
  });
});
