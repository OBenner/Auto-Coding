/**
 * Auth Store
 *
 * Manages authentication state and token verification for the web frontend.
 * Follows patterns from desktop app stores (settings-store.ts, claude-profile-store.ts).
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiClient } from '../api/client';

// ============================================
// TYPES
// ============================================

export interface AuthUser {
  id?: string;
  email?: string;
  name?: string;
}

export interface AuthState {
  // State
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isVerifying: boolean;
  error: string | null;

  // Actions
  setToken: (token: string | null) => void;
  setUser: (user: AuthUser | null) => void;
  setAuthenticated: (isAuthenticated: boolean) => void;
  setLoading: (loading: boolean) => void;
  setVerifying: (verifying: boolean) => void;
  setError: (error: string | null) => void;

  // Async actions
  verifyToken: (token?: string) => Promise<boolean>;
  checkAuthStatus: () => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
}

// ============================================
// STORE
// ============================================

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      isVerifying: false,
      error: null,

      // Simple setters
      setToken: (token) => set({ token }),

      setUser: (user) => set({ user }),

      setAuthenticated: (isAuthenticated) => set({ isAuthenticated }),

      setLoading: (isLoading) => set({ isLoading }),

      setVerifying: (isVerifying) => set({ isVerifying }),

      setError: (error) => set({ error }),

      clearError: () => set({ error: null }),

      // Verify authentication token
      verifyToken: async (token?: string): Promise<boolean> => {
        const tokenToVerify = token || get().token;

        if (!tokenToVerify) {
          set({
            isAuthenticated: false,
            user: null,
            error: 'No token provided'
          });
          return false;
        }

        set({ isVerifying: true, error: null });

        try {
          const result = await apiClient.verifyAuth(tokenToVerify);

          if (result.valid) {
            set({
              token: tokenToVerify,
              isAuthenticated: true,
              isVerifying: false,
              error: null
            });
            return true;
          }

          // Token invalid
          set({
            token: null,
            user: null,
            isAuthenticated: false,
            isVerifying: false,
            error: 'Invalid or expired token'
          });
          return false;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to verify token';
          set({
            token: null,
            user: null,
            isAuthenticated: false,
            isVerifying: false,
            error: errorMessage
          });
          return false;
        }
      },

      // Check authentication status with backend
      checkAuthStatus: async (): Promise<boolean> => {
        set({ isLoading: true, error: null });

        try {
          const result = await apiClient.getAuthStatus();

          // Backend returns { status: "ok" } or similar
          const isOk = result.status === 'ok' || result.status === 'authenticated';

          set({
            isAuthenticated: isOk,
            isLoading: false,
            error: null
          });

          return isOk;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to check auth status';
          set({
            isAuthenticated: false,
            isLoading: false,
            error: errorMessage
          });
          return false;
        }
      },

      // Logout - clear all auth state
      logout: () => {
        set({
          token: null,
          user: null,
          isAuthenticated: false,
          error: null
        });
      }
    }),
    {
      name: 'auto-claude-auth', // localStorage key
      partialize: (state) => ({
        // Only persist token and user, not loading/error states
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Initialize auth state on app startup
 * Verifies stored token if present
 */
export async function initializeAuth(): Promise<void> {
  const store = useAuthStore.getState();

  // If we have a stored token, verify it
  if (store.token) {
    await store.verifyToken();
  } else {
    // No token - check if backend has session-based auth
    await store.checkAuthStatus();
  }
}

/**
 * Set authentication token and verify it
 */
export async function setAuthToken(token: string): Promise<boolean> {
  const store = useAuthStore.getState();
  return await store.verifyToken(token);
}

/**
 * Get current authentication token
 */
export function getAuthToken(): string | null {
  return useAuthStore.getState().token;
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return useAuthStore.getState().isAuthenticated;
}
