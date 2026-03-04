/**
 * Spec Store
 *
 * Manages spec/task state with CRUD operations for the web frontend.
 * Follows patterns from desktop app stores (task-store.ts, project-store.ts).
 */

import { create } from 'zustand';
import { apiClient } from '../api/client';
import type { SpecSummary, SpecDetail } from '../api/types';

// ============================================
// TYPES
// ============================================

export interface SpecState {
  // State
  specs: SpecSummary[];
  selectedSpecId: string | null;
  currentSpec: SpecDetail | null;
  isLoading: boolean;
  isLoadingDetail: boolean;
  error: string | null;
  detailError: string | null;

  // Actions
  setSpecs: (specs: SpecSummary[]) => void;
  setSelectedSpecId: (specId: string | null) => void;
  setCurrentSpec: (spec: SpecDetail | null) => void;
  setLoading: (loading: boolean) => void;
  setLoadingDetail: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setDetailError: (error: string | null) => void;

  // CRUD operations
  fetchSpecs: () => Promise<boolean>;
  fetchSpec: (specId: string) => Promise<boolean>;
  refreshSpecs: () => Promise<boolean>;
  clearSelectedSpec: () => void;
  clearError: () => void;

  // Selectors
  getSelectedSpec: () => SpecSummary | undefined;
  getSpecById: (specId: string) => SpecSummary | undefined;
}

// ============================================
// STORE
// ============================================

export const useSpecStore = create<SpecState>((set, get) => ({
  // Initial state
  specs: [],
  selectedSpecId: null,
  currentSpec: null,
  isLoading: false,
  isLoadingDetail: false,
  error: null,
  detailError: null,

  // Simple setters
  setSpecs: (specs) => set({ specs }),

  setSelectedSpecId: (selectedSpecId) => set({ selectedSpecId }),

  setCurrentSpec: (currentSpec) => set({ currentSpec }),

  setLoading: (isLoading) => set({ isLoading }),

  setLoadingDetail: (isLoadingDetail) => set({ isLoadingDetail }),

  setError: (error) => set({ error }),

  setDetailError: (detailError) => set({ detailError }),

  clearError: () => set({ error: null, detailError: null }),

  // Fetch all specs from API
  fetchSpecs: async (): Promise<boolean> => {
    set({ isLoading: true, error: null });

    try {
      const result = await apiClient.listSpecs();

      if (result.specs) {
        set({
          specs: result.specs,
          isLoading: false,
          error: null
        });
        return true;
      }

      // No specs returned
      set({
        specs: [],
        isLoading: false,
        error: null
      });
      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch specs';
      set({
        isLoading: false,
        error: errorMessage
      });
      return false;
    }
  },

  // Fetch detailed spec information
  fetchSpec: async (specId: string): Promise<boolean> => {
    set({ isLoadingDetail: true, detailError: null });

    try {
      const spec = await apiClient.getSpec(specId);

      set({
        currentSpec: spec,
        selectedSpecId: specId,
        isLoadingDetail: false,
        detailError: null
      });
      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch spec details';
      set({
        currentSpec: null,
        isLoadingDetail: false,
        detailError: errorMessage
      });
      return false;
    }
  },

  // Refresh spec list (force reload)
  refreshSpecs: async (): Promise<boolean> => {
    return get().fetchSpecs();
  },

  // Clear selected spec
  clearSelectedSpec: () => {
    set({
      selectedSpecId: null,
      currentSpec: null,
      detailError: null
    });
  },

  // Selectors
  getSelectedSpec: () => {
    const state = get();
    return state.specs.find((s) => s.number === state.selectedSpecId);
  },

  getSpecById: (specId: string) => {
    const state = get();
    return state.specs.find((s) => s.number === specId);
  }
}));

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Initialize spec store on app startup
 * Loads the initial list of specs
 */
export async function initializeSpecs(): Promise<void> {
  const store = useSpecStore.getState();
  await store.fetchSpecs();
}

/**
 * Load a specific spec by ID
 */
export async function loadSpec(specId: string): Promise<boolean> {
  const store = useSpecStore.getState();
  return await store.fetchSpec(specId);
}

/**
 * Refresh the spec list
 */
export async function refreshSpecs(): Promise<boolean> {
  const store = useSpecStore.getState();
  return await store.refreshSpecs();
}

/**
 * Get all specs
 */
export function getSpecs(): SpecSummary[] {
  return useSpecStore.getState().specs;
}

/**
 * Get selected spec
 */
export function getSelectedSpec(): SpecSummary | undefined {
  return useSpecStore.getState().getSelectedSpec();
}

/**
 * Get current spec detail
 */
export function getCurrentSpec(): SpecDetail | null {
  return useSpecStore.getState().currentSpec;
}

/**
 * Select a spec by ID
 */
export function selectSpec(specId: string | null): void {
  useSpecStore.getState().setSelectedSpecId(specId);
}

/**
 * Clear selected spec
 */
export function clearSelectedSpec(): void {
  useSpecStore.getState().clearSelectedSpec();
}
