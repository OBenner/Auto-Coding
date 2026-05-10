import { afterEach, describe, expect, it } from 'vitest';
import { mkdir, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import {
  GENERIC_EDIT_TEST_ARTIFACT_PATHS,
  createGenericEditArtifactManifest,
} from '../../../__tests__/fixtures/generic-edit';
import type { Project, Task } from '../../../shared/types';
import { readGenericEditArtifactManifest } from './spec-file-readers';

const tempRoots: string[] = [];
let tempProjectCounter = 0;

async function createTempProject(): Promise<string> {
  tempProjectCounter += 1;
  const tempRoot = path.join(
    process.cwd(),
    '.vitest-tmp',
    `generic-edit-manifest-${Date.now()}-${tempProjectCounter}`
  );
  await mkdir(tempRoot, { recursive: true });
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

    const manifestPayload = createGenericEditArtifactManifest();
    await writeManifest(projectPath, task.specId, {
      ...manifestPayload,
      counts: {
        ...manifestPayload.counts,
        iteration_count: 1,
        action_count: 2,
        failed_action_count: 0,
        event_count: 4,
        transaction_count: 1,
        mutation_snapshot_count: 1,
        recovery_attempt_count: 0,
        failed_recovery_attempt_count: 0,
        native_tool_fallback_count: 1,
      },
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
      recovery_summary: manifestPayload.recovery_summary
        ? {
            ...manifestPayload.recovery_summary,
            warning_count: 0,
            warnings: [],
          }
        : null,
      native_tool_fallbacks: [
        {
          provider: 'openai',
          from_loop: 'native_tool_calls',
          to_loop: 'json_actions',
          reason: 'native_tool_request_failed',
          message: 'provider rejected tool calls',
          tool_schema_count: 6,
        },
      ],
    });

    const manifest = await readGenericEditArtifactManifest(project, task);

    expect(manifest?.artifact_type).toBe('generic_edit_artifact_manifest');
    expect(manifest?.provider).toBe('openai');
    expect(manifest?.flags.resumable).toBe(true);
    expect(manifest?.counts.mutation_snapshot_count).toBe(1);
    expect(manifest?.counts.native_tool_fallback_count).toBe(1);
    expect(manifest?.native_tool_fallbacks).toEqual([
      {
        provider: 'openai',
        from_loop: 'native_tool_calls',
        to_loop: 'json_actions',
        reason: 'native_tool_request_failed',
        message: 'provider rejected tool calls',
        tool_schema_count: 6,
      },
    ]);
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
    expect(manifest?.resume_action).toEqual({
      runtime: 'generic_edit',
      checkpoint_path: GENERIC_EDIT_TEST_ARTIFACT_PATHS.checkpoint,
      strategy: 'recover_partial_failure',
      next_iteration: 3,
    });
    expect(manifest?.resume_inputs).toEqual({
      trace_artifact: GENERIC_EDIT_TEST_ARTIFACT_PATHS.trace,
      event_artifact: GENERIC_EDIT_TEST_ARTIFACT_PATHS.events,
      recovery_plan_artifact: GENERIC_EDIT_TEST_ARTIFACT_PATHS.recovery,
      mutation_snapshot_artifact: GENERIC_EDIT_TEST_ARTIFACT_PATHS.mutationSnapshots,
    });
    expect(manifest?.mcp_support).toEqual(manifestPayload.mcp_support);
  });

  it('drops malformed optional mcp support without rejecting the manifest', async () => {
    const projectPath = await createTempProject();
    const project = createProject(projectPath);
    const task = createTask();

    const manifestPayload = createGenericEditArtifactManifest();
    await writeManifest(projectPath, task.specId, {
      ...manifestPayload,
      subtask_id: null,
      status: 'success',
      stop_reason: 'finish',
      entrypoints: {
        result: GENERIC_EDIT_TEST_ARTIFACT_PATHS.result,
      },
      flags: {
        recoverable: false,
        resumable: false,
        resumed: false,
        recovery_required: false,
        recovery_resolved: false,
        has_recovery_plan: false,
        has_mutation_snapshots: false,
        has_transaction_groups: false,
      },
      counts: {
        iteration_count: 1,
        action_count: 1,
        failed_action_count: 0,
        event_count: 1,
        transaction_count: 0,
        transaction_group_count: 0,
        mutation_snapshot_count: 0,
        recovery_attempt_count: 0,
        failed_recovery_attempt_count: 0,
      },
      artifacts: [
        {
          name: 'generic_edit_result',
          kind: 'result',
          path: GENERIC_EDIT_TEST_ARTIFACT_PATHS.result,
          active: true,
          required: true,
          present: true,
        },
      ],
      recent_events: [],
      recovery_summary: null,
      recovery_actions: [],
      mcp_support: {
        strategy: 'local_bridge',
        tool_count: 'two',
      },
      resume_action: null,
      resume_inputs: {},
      resume: null,
    });

    const manifest = await readGenericEditArtifactManifest(project, task);

    expect(manifest).not.toBeNull();
    expect(manifest?.mcp_support).toBeNull();
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
