import { afterEach, describe, expect, it } from 'vitest';
import { mkdtemp, mkdir, rm, writeFile } from 'fs/promises';
import os from 'os';
import path from 'path';
import type { Project, Task } from '../../../shared/types';
import { readGenericEditArtifactManifest } from './spec-file-readers';

const tempRoots: string[] = [];

async function createTempProject(): Promise<string> {
  const tempRoot = await mkdtemp(path.join(os.tmpdir(), 'generic-edit-manifest-'));
  tempRoots.push(tempRoot);
  return tempRoot;
}

function createProject(projectPath: string): Project {
  return {
    id: 'project-1',
    name: 'Project',
    path: projectPath,
    autoBuildPath: '.auto-claude',
    settings: {
      model: 'sonnet',
      memoryBackend: 'file',
      linearSync: false,
      notifications: {
        onTaskComplete: true,
        onTaskFailed: true,
        onReviewNeeded: true,
        sound: false,
      },
      graphitiMcpEnabled: true,
    },
    createdAt: new Date('2026-01-01T00:00:00Z'),
    updatedAt: new Date('2026-01-01T00:00:00Z'),
  };
}

function createTask(specId = '001-generic-edit'): Task {
  return {
    id: 'task-1',
    specId,
    projectId: 'project-1',
    title: 'Generic edit',
    description: 'Exercise artifact manifest',
    status: 'human_review',
    subtasks: [],
    logs: [],
    createdAt: new Date('2026-01-01T00:00:00Z'),
    updatedAt: new Date('2026-01-01T00:00:00Z'),
  };
}

async function writeManifest(projectPath: string, specId: string, manifest: unknown): Promise<void> {
  const artifactDir = path.join(projectPath, '.auto-claude', 'specs', specId, 'artifacts');
  await mkdir(artifactDir, { recursive: true });
  await writeFile(
    path.join(artifactDir, 'generic_edit_artifact_manifest.json'),
    JSON.stringify(manifest, null, 2),
    'utf-8'
  );
}

afterEach(async () => {
  await Promise.all(tempRoots.splice(0).map((tempRoot) => rm(tempRoot, { recursive: true, force: true })));
});

describe('readGenericEditArtifactManifest', () => {
  it('reads and normalizes the generic edit artifact manifest', async () => {
    const projectPath = await createTempProject();
    const project = createProject(projectPath);
    const task = createTask();

    await writeManifest(projectPath, task.specId, {
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
        iteration_count: 1,
        action_count: 2,
        failed_action_count: 0,
        event_count: 4,
        transaction_count: 1,
        transaction_group_count: 1,
        mutation_snapshot_count: 1,
        recovery_attempt_count: 0,
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
          sequence: 4,
          event_type: 'transaction',
          transaction_id: 'json_actions-1',
          status: 'partial_failure',
          failed_action_count: 1,
          recovery_required: true,
        },
      ],
      recovery_summary: {
        version: 1,
        status: 'requires_resolution',
        finish_blocked: true,
        unresolved_transaction_group_count: 1,
        unresolved_transaction_group_ids: ['transaction-group-1'],
        warning_count: 0,
        warnings: [],
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
      mcp_support: { enabled: true },
      resume: null,
    });

    const manifest = await readGenericEditArtifactManifest(project, task);

    expect(manifest?.artifact_type).toBe('generic_edit_artifact_manifest');
    expect(manifest?.provider).toBe('openai');
    expect(manifest?.flags.resumable).toBe(true);
    expect(manifest?.counts.mutation_snapshot_count).toBe(1);
    expect(manifest?.artifacts).toHaveLength(2);
    expect(manifest?.artifacts[1]).toMatchObject({
      name: 'generic_edit_recovery_plan',
      active: true,
      present: false,
    });
    expect(manifest?.recent_events).toEqual([
      {
        sequence: 4,
        event_type: 'transaction',
        transaction_id: 'json_actions-1',
        status: 'partial_failure',
        failed_action_count: 1,
        recovery_required: true,
      },
    ]);
    expect(manifest?.recovery_summary).toMatchObject({
      status: 'requires_resolution',
      finish_blocked: true,
      unresolved_transaction_group_ids: ['transaction-group-1'],
      resolution_strategies: ['rollback_transaction', 'repair_mutation'],
    });
    expect(manifest?.recovery_actions).toEqual([
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
    ]);
  });

  it('returns null when the manifest has not been written yet', async () => {
    const projectPath = await createTempProject();

    await expect(
      readGenericEditArtifactManifest(createProject(projectPath), createTask())
    ).resolves.toBeNull();
  });

  it('returns null for a different manifest type or schema version', async () => {
    const projectPath = await createTempProject();
    const project = createProject(projectPath);
    const task = createTask();

    await writeManifest(projectPath, task.specId, {
      artifact_type: 'other_manifest',
      schema_version: 99,
    });

    await expect(readGenericEditArtifactManifest(project, task)).resolves.toBeNull();
  });
});
