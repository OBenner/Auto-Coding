export type ProviderSmokeRuntime = 'analysis_only' | 'generic_edit' | 'mini_pipeline';

type RuntimeEnv = Record<string, string | undefined>;

function normalizeRuntimeMode(value: string | undefined): string {
  return value?.trim().toLowerCase().replaceAll('-', '_') ?? '';
}

function normalizeExplicitSmokeRuntime(value: string | undefined): ProviderSmokeRuntime | null {
  const normalized = normalizeRuntimeMode(value);
  if (normalized === 'mini_pipeline') {
    return 'mini_pipeline';
  }
  if (normalized === 'generic_edit') {
    return 'generic_edit';
  }
  if (normalized === 'analysis_only') {
    return 'analysis_only';
  }
  return null;
}

export function resolveProviderSmokeRuntime(
  env: RuntimeEnv,
  explicitRuntime?: string
): ProviderSmokeRuntime {
  const explicit = normalizeExplicitSmokeRuntime(explicitRuntime);
  if (explicit) {
    return explicit;
  }

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
