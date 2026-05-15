export type ProviderSmokeRuntime = 'analysis_only' | 'generic_edit';

type RuntimeEnv = Record<string, string | undefined>;

function normalizeRuntimeMode(value: string | undefined): string {
  return value?.trim().toLowerCase().replaceAll('-', '_') ?? '';
}

export function resolveProviderSmokeRuntime(env: RuntimeEnv): ProviderSmokeRuntime {
  const coderRuntime = normalizeRuntimeMode(env.AGENT_RUNTIME_MODE_CODER);
  if (coderRuntime === 'generic_edit') {
    return 'generic_edit';
  }

  const globalRuntime = normalizeRuntimeMode(
    env.AUTO_CODE_RUNTIME_MODE ?? env.AUTO_CLAUDE_RUNTIME_MODE
  );
  if (globalRuntime === 'generic_edit') {
    return 'generic_edit';
  }

  return 'analysis_only';
}
