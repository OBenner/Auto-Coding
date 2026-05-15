import { describe, expect, it } from 'vitest';

import { resolveProviderSmokeRuntime } from './provider-smoke-runtime';

describe('resolveProviderSmokeRuntime', () => {
  it('defaults to analysis_only when no edit runtime is configured', () => {
    expect(resolveProviderSmokeRuntime({})).toBe('analysis_only');
    expect(resolveProviderSmokeRuntime({ AUTO_CODE_RUNTIME_MODE: 'full_autonomous' })).toBe(
      'analysis_only'
    );
  });

  it('uses generic_edit for the global or coder runtime edit surface', () => {
    expect(resolveProviderSmokeRuntime({ AUTO_CODE_RUNTIME_MODE: 'generic_edit' })).toBe(
      'generic_edit'
    );
    expect(resolveProviderSmokeRuntime({ AGENT_RUNTIME_MODE_CODER: 'generic-edit' })).toBe(
      'generic_edit'
    );
  });

  it('prefers the coder runtime override over the global runtime', () => {
    expect(
      resolveProviderSmokeRuntime({
        AUTO_CODE_RUNTIME_MODE: 'analysis_only',
        AGENT_RUNTIME_MODE_CODER: 'generic_edit',
      })
    ).toBe('generic_edit');
  });
});
