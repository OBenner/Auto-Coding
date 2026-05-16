/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from 'vitest';

import {
  buildProviderResumePolicyDiagnosticRows,
  buildProviderTransactionBatchDiagnosticRows
} from './ProviderSettingsSection';

const translate = (key: string) =>
  ({
    'settings:aiProvider.connectionTest.resumePolicy': 'Resume policy',
    'settings:aiProvider.connectionTest.resumeStrategy': 'Resume strategy',
    'settings:aiProvider.connectionTest.resumeCanResume': 'Can resume',
    'settings:aiProvider.connectionTest.resumeFinishBlocked': 'Finish blocked',
    'settings:aiProvider.connectionTest.resumeNextIteration': 'Next iteration',
    'settings:aiProvider.connectionTest.resumeRequiredActions': 'Required recovery actions',
    'settings:aiProvider.connectionTest.resumeRequiredArtifacts': 'Required resume artifacts',
    'settings:aiProvider.connectionTest.resumeUnresolvedFailures': 'Unresolved partial failures',
    'settings:aiProvider.connectionTest.resumeUnresolvedGroups': 'Unresolved transaction groups',
    'settings:aiProvider.connectionTest.resumeOpenBatches': 'Open transaction batches',
    'settings:aiProvider.connectionTest.batchContract': 'Batch contract',
    'settings:aiProvider.connectionTest.batchBoundaryGuard': 'Batch boundary guard',
    'settings:aiProvider.connectionTest.batchCount': 'Transaction batches',
    'settings:aiProvider.connectionTest.batchBoundaryErrors': 'Batch boundary errors',
    'settings:aiProvider.connectionTest.batchOpenBatches': 'Open batches',
    'settings:aiProvider.runtimeDiagnosticValues.batchBoundaryGuarded': 'Boundary guarded',
    'settings:aiProvider.runtimeDiagnosticValues.batchBoundaryViolation': 'Batch boundary violation',
    'settings:aiProvider.runtimeDiagnosticValues.inspectDiff': 'Inspect diff',
    'settings:aiProvider.runtimeDiagnosticValues.preExecutionBlocked': 'Pre-execution blocked',
    'settings:aiProvider.runtimeDiagnosticValues.ready': 'Ready',
    'settings:aiProvider.runtimeDiagnosticValues.recoverPartialFailure': 'Recover partial failure',
    'settings:aiProvider.runtimeDiagnosticValues.yes': 'Yes',
  })[key] ?? key;

describe('buildProviderResumePolicyDiagnosticRows', () => {
  it('includes resume gates and iteration metadata from provider diagnostics', () => {
    expect(
      buildProviderResumePolicyDiagnosticRows(translate, {
        status: 'ready',
        strategy: 'recover_partial_failure',
        canResume: true,
        finishBlocked: true,
        nextIteration: 4,
        requiredResolutionActionKinds: ['inspect_diff'],
        requiredArtifacts: ['trace_artifact'],
        unresolvedPartialFailureIds: ['json_actions-1'],
        unresolvedTransactionGroupIds: ['transaction-group-1'],
        openTransactionBatchIds: ['batch-1'],
      })
    ).toEqual([
      { labelKey: 'settings:aiProvider.connectionTest.resumePolicy', value: 'Ready' },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeStrategy',
        value: 'Recover partial failure',
      },
      { labelKey: 'settings:aiProvider.connectionTest.resumeCanResume', value: 'Yes' },
      { labelKey: 'settings:aiProvider.connectionTest.resumeFinishBlocked', value: 'Yes' },
      { labelKey: 'settings:aiProvider.connectionTest.resumeNextIteration', value: '4' },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeRequiredActions',
        value: 'Inspect diff',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeRequiredArtifacts',
        value: 'trace artifact',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeUnresolvedFailures',
        value: 'json actions-1',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeUnresolvedGroups',
        value: 'transaction-group-1',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.resumeOpenBatches',
        value: 'batch-1',
      },
    ]);
  });
});

describe('buildProviderTransactionBatchDiagnosticRows', () => {
  it('includes batch-boundary guard and reason metadata from provider diagnostics', () => {
    expect(
      buildProviderTransactionBatchDiagnosticRows(translate, {
        status: 'boundary_guarded',
        batchBoundaryGuard: 'pre_execution_blocked',
        transactionBatchCount: 0,
        openTransactionBatchIds: ['batch-1'],
        boundaryErrorCount: 1,
        boundaryErrorReasons: ['batch_boundary_violation'],
      })
    ).toEqual([
      {
        labelKey: 'settings:aiProvider.connectionTest.batchContract',
        value: 'Boundary guarded',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchBoundaryGuard',
        value: 'Pre-execution blocked',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchCount',
        value: '0',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchBoundaryErrors',
        value: 'Batch boundary violation',
      },
      {
        labelKey: 'settings:aiProvider.connectionTest.batchOpenBatches',
        value: 'batch-1',
      },
    ]);
  });
});
