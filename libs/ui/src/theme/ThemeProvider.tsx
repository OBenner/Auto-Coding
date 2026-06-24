import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { ReactNode } from 'react';

export type Theme = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

interface ThemeContextValue {
  /** The user's selection (may be "system"). */
  theme: Theme;
  /** The concrete theme applied to the DOM ("light" | "dark"). */
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function readStoredTheme(storageKey: string, fallback: Theme): Theme {
  if (typeof localStorage === 'undefined') return fallback;
  const stored = localStorage.getItem(storageKey);
  return stored === 'light' || stored === 'dark' || stored === 'system'
    ? stored
    : fallback;
}

export interface ThemeProviderProps {
  children: ReactNode;
  /** Theme used before any user override is stored. Defaults to "system". */
  defaultTheme?: Theme;
  /** localStorage key for persisting the override. */
  storageKey?: string;
}

/**
 * Applies the Auto Code design tokens' theme by setting `data-theme` on
 * `<html>`. Resolves "system" from `prefers-color-scheme` and reacts to OS
 * changes; the user's override persists in localStorage (works in both the
 * Electron renderer and the web app).
 */
export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'auto-code-theme',
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(() =>
    readStoredTheme(storageKey, defaultTheme)
  );
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(getSystemTheme);

  // Track OS preference so "system" stays in sync without a reload.
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setSystemTheme(query.matches ? 'dark' : 'light');
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  const resolvedTheme: ResolvedTheme = theme === 'system' ? systemTheme : theme;

  // Apply to <html data-theme="…"> so the token overrides take effect.
  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.documentElement.setAttribute('data-theme', resolvedTheme);
  }, [resolvedTheme]);

  const setTheme = useCallback(
    (next: Theme) => {
      setThemeState(next);
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(storageKey, next);
      }
    },
    [storageKey]
  );

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme }),
    [theme, resolvedTheme, setTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return ctx;
}
