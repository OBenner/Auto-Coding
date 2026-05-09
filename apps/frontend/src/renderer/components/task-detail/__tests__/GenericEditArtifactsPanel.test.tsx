/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  GENERIC_EDIT_TEST_ARTIFACT_PATHS,
  createGenericEditArtifactManifest,
} from '../../../../__tests__/fixtures/generic-edit';
import { GenericEditArtifactsPanel } from '../GenericEditArtifactsPanel';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, values?: Record<string, unknown>) => {
      const normalizedKey = key.replace(/^tasks:/, '');
      const interpolation = (name: string, fallback: string | number) => {
        const value = values?.[name];
        return typeof value === 'string' || typeof value === 'number' ? String(value) : String(fallback);
      };
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
        'overview.genericEditArtifactsPresent': `${interpolation('present', 0)}/${interpolation('total', 0)} present`,
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
        'overview.genericEditNextIteration': `Next iteration ${interpolation('iteration', '')}`,
        'overview.genericEditResumeInputs': 'Resume inputs',
        'overview.genericEditMcpSupport': 'MCP support',
        'overview.genericEditMcpTools': `${interpolation('count', 0)} MCP tools`,
        'overview.genericEditMcpAvailable': 'Available',
        'overview.genericEditMcpUnavailable': 'Unavailable',
        'overview.genericEditMcpActionRequired': 'Action required',
        'overview.genericEditMcpServer': 'MCP server',
        'overview.genericEditMcpServerStatus': 'Server status',
        'overview.genericEditMcpPermissionPolicy': 'Permission policy',
        'overview.genericEditMcpAllowedPermissions': 'Allowed permissions',
        'overview.genericEditMcpToolPolicies': 'Tool policies',
        'overview.genericEditMcpBridgePlan': 'Bridge plan',
        'overview.genericEditMcpRecommendedRuntimePath': 'Recommended path',
        'overview.genericEditMcpNativeRequired': 'Native required',
        'overview.genericEditMcpLocalBridgeRequired': 'Local bridge required',
        'overview.genericEditMcpExternalBridgeRequired': 'External bridge required',
        'overview.genericEditMcpUnsupported': 'Unsupported',
        'overview.genericEditMcpBridged': 'Bridged',
        'overview.genericEditMcpExternalBridged': 'External bridged',
        'overview.genericEditMcpSessionReuse': 'Session reuse',
        'overview.genericEditMcpOpenSessions': `${interpolation('count', 0)} open MCP session`,
      };
      return translations[normalizedKey] || translations[key] || key;
    },
  }),
}));

function createManifest() {
  return createGenericEditArtifactManifest();
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
    expect(screen.getByText(GENERIC_EDIT_TEST_ARTIFACT_PATHS.checkpoint)).toBeInTheDocument();
    expect(screen.getByText('Resume inputs')).toBeInTheDocument();
    expect(screen.getByText('trace_artifact')).toBeInTheDocument();
    expect(screen.getByText(GENERIC_EDIT_TEST_ARTIFACT_PATHS.trace)).toBeInTheDocument();
    expect(screen.getByText('event_artifact')).toBeInTheDocument();
    expect(screen.getByText(GENERIC_EDIT_TEST_ARTIFACT_PATHS.events)).toBeInTheDocument();
    expect(screen.getByText('mutation_snapshot_artifact')).toBeInTheDocument();
    expect(screen.getByText(GENERIC_EDIT_TEST_ARTIFACT_PATHS.mutationSnapshots)).toBeInTheDocument();
    expect(screen.getByText('MCP support')).toBeInTheDocument();
    expect(screen.getByText('local_bridge')).toBeInTheDocument();
    expect(screen.getByText('2 MCP tools')).toBeInTheDocument();
    expect(screen.getByText('External MCP tools are bridged through generic_edit.')).toBeInTheDocument();
    expect(screen.getByText('Available')).toBeInTheDocument();
    expect(screen.getAllByText('context7')).toHaveLength(2);
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.getAllByText('linear')).toHaveLength(2);
    expect(screen.getByText('MCP server')).toBeInTheDocument();
    expect(screen.getByText('auto-claude')).toBeInTheDocument();
    expect(screen.getByText('Server status')).toBeInTheDocument();
    expect(screen.getByText('Context7')).toBeInTheDocument();
    expect(screen.getByText('external_bridge')).toBeInTheDocument();
    expect(screen.getByText('Available through Auto Code external MCP client bridge.')).toBeInTheDocument();
    expect(screen.getByText('Permission policy')).toBeInTheDocument();
    expect(screen.getByText('allowlist')).toBeInTheDocument();
    expect(screen.getByText('Allowed permissions')).toBeInTheDocument();
    expect(screen.getAllByText('mcp:context7:read')).toHaveLength(2);
    expect(screen.getByText('Tool policies')).toBeInTheDocument();
    expect(screen.getByText('read')).toBeInTheDocument();
    expect(screen.getByText('Action required')).toBeInTheDocument();
    expect(screen.getByText('configure_external_mcp_client')).toBeInTheDocument();
    expect(screen.getByText('Bridge plan')).toBeInTheDocument();
    expect(screen.getByText('partial')).toBeInTheDocument();
    expect(screen.getByText('Recommended path')).toBeInTheDocument();
    expect(screen.getByText('external_mcp_client')).toBeInTheDocument();
    expect(screen.getByText('Native required')).toBeInTheDocument();
    expect(screen.getByText('graphiti')).toBeInTheDocument();
    expect(screen.getByText('Local bridge required')).toBeInTheDocument();
    expect(screen.getAllByText('linear')).toHaveLength(2);
    expect(screen.getByText('External bridge required')).toBeInTheDocument();
    expect(screen.getAllByText('puppeteer')).toHaveLength(2);
    expect(screen.getByText('Unsupported')).toBeInTheDocument();
    expect(screen.getByText('unknown-docs')).toBeInTheDocument();
    expect(screen.getByText('Bridged')).toBeInTheDocument();
    expect(screen.getByText('External bridged')).toBeInTheDocument();
    expect(screen.getAllByText('puppeteer')).toHaveLength(2);
    expect(screen.getAllByText('mcp__context7__resolve-library-id')).toHaveLength(2);
    expect(screen.getByText('Session reuse')).toBeInTheDocument();
    expect(screen.getByText('per_runtime_bridge')).toBeInTheDocument();
    expect(screen.getByText('1 open MCP session')).toBeInTheDocument();
    expect(screen.getByText('my-docs')).toBeInTheDocument();
    expect(screen.getByText('http')).toBeInTheDocument();
  });

  it('opens an inline preview for present artifacts with paths', async () => {
    const readFile = vi.fn().mockResolvedValue({ success: true, data: '{"ok": true}' });
    Object.defineProperty(globalThis, 'electronAPI', {
      value: { readFile },
      configurable: true,
    });

    render(<GenericEditArtifactsPanel manifest={createManifest()} />);

    fireEvent.click(screen.getByLabelText('View artifact'));

    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith(GENERIC_EDIT_TEST_ARTIFACT_PATHS.result);
    });
    expect(await screen.findByText('Artifact preview')).toBeInTheDocument();
    expect(screen.getByText('{"ok": true}')).toBeInTheDocument();
  });
});
