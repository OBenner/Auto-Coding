import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import type { UiTask } from './types';

/**
 * The data port the shared UI depends on. Each app provides a concrete adapter
 * (Electron → IPC, web → REST/WS) so `libs/ui` stays transport-agnostic — this
 * is the "ports and adapters" seam introduced at the Kanban pilot (U1).
 */
export interface AutoCodeClient {
  /** Fetch the current task/spec list for the active workspace. */
  listTasks(): Promise<UiTask[]>;
  /**
   * Optional realtime subscription. Returns an unsubscribe function; when
   * provided, useTasks() refreshes from the pushed snapshots.
   */
  subscribeTasks?(onChange: (tasks: UiTask[]) => void): () => void;
}

const AutoCodeClientContext = createContext<AutoCodeClient | null>(null);

export interface AutoCodeClientProviderProps {
  client: AutoCodeClient;
  children: ReactNode;
}

export function AutoCodeClientProvider({
  client,
  children,
}: AutoCodeClientProviderProps) {
  return (
    <AutoCodeClientContext.Provider value={client}>
      {children}
    </AutoCodeClientContext.Provider>
  );
}

export function useAutoCodeClient(): AutoCodeClient {
  const client = useContext(AutoCodeClientContext);
  if (!client) {
    throw new Error('useAutoCodeClient must be used within an AutoCodeClientProvider');
  }
  return client;
}

export interface UseTasksResult {
  tasks: UiTask[];
  loading: boolean;
  error: Error | null;
  reload: () => void;
}

/**
 * Loads tasks from the injected AutoCodeClient and, when the adapter supports
 * it, keeps them live via subscribeTasks. Presentational components (e.g.
 * KanbanBoard) receive the result as props.
 */
export function useTasks(): UseTasksResult {
  const client = useAutoCodeClient();
  const [tasks, setTasks] = useState<UiTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    client
      .listTasks()
      .then((next) => {
        if (active) setTasks(next);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err : new Error(String(err)));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    const unsubscribe = client.subscribeTasks?.((next) => {
      if (active) setTasks(next);
    });

    return () => {
      active = false;
      unsubscribe?.();
    };
  }, [client, reloadKey]);

  return { tasks, loading, error, reload };
}
