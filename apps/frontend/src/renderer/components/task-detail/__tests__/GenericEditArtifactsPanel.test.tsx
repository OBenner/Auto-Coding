/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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
    mcp_support: null,
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
  });
});
