/**
 * AsyncButton - Button wrapper with automatic async state management
 *
 * Automatically handles loading states for async onClick handlers.
 * Provides a useAsync hook for custom async action management.
 *
 * Examples:
 * ```tsx
 * // Simple async button
 * <AsyncButton onClick={async () => await saveData()}>Save</AsyncButton>
 *
 * // With loading text
 * <AsyncButton onClick={handleSubmit} loadingText="Submitting...">
 *   Submit
 * </AsyncButton>
 *
 * // With custom hook
 * const { execute, isLoading, error } = useAsync(saveData);
 * <Button loading={isLoading} onClick={execute}>Save</Button>
 * ```
 */
import { useState, useCallback } from 'react';
import { Button, type ButtonProps } from './button';

/**
 * Options for useAsync hook
 */
export interface UseAsyncOptions<T = void> {
  /** Called when async operation succeeds */
  onSuccess?: (result: T) => void;
  /** Called when async operation fails */
  onError?: (error: Error) => void;
  /** Called when async operation completes (success or failure) */
  onComplete?: () => void;
}

/**
 * Return type for useAsync hook
 */
export interface UseAsyncReturn<T = void> {
  /** Execute the async function */
  execute: (...args: any[]) => Promise<T | void>;
  /** Whether the async operation is in progress */
  isLoading: boolean;
  /** Error from the last failed operation */
  error: Error | null;
  /** Clear the error state */
  clearError: () => void;
}

/**
 * Hook to manage async operations with loading and error states
 *
 * @param asyncFn - The async function to execute
 * @param options - Optional callbacks for success, error, and completion
 * @returns Object with execute function, loading state, and error state
 *
 * @example
 * ```tsx
 * const { execute, isLoading, error } = useAsync(
 *   async (id: string) => await deleteItem(id),
 *   {
 *     onSuccess: () => toast({ title: 'Deleted successfully' }),
 *     onError: (err) => toast({ title: 'Delete failed', variant: 'destructive' })
 *   }
 * );
 *
 * <Button loading={isLoading} onClick={() => execute(itemId)}>
 *   Delete
 * </Button>
 * ```
 */
export function useAsync<T = void>(
  asyncFn: (...args: any[]) => Promise<T>,
  options?: UseAsyncOptions<T>
): UseAsyncReturn<T> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(
    async (...args: any[]): Promise<T | void> => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await asyncFn(...args);
        options?.onSuccess?.(result);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        options?.onError?.(error);
      } finally {
        setIsLoading(false);
        options?.onComplete?.();
      }
    },
    [asyncFn, options]
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return { execute, isLoading, error, clearError };
}

/**
 * AsyncButton component props
 */
export interface AsyncButtonProps extends Omit<ButtonProps, 'onClick' | 'loading'> {
  /** Async onClick handler - loading state managed automatically */
  onClick: (...args: any[]) => Promise<void>;
  /** Text to show while loading (optional) */
  loadingText?: string;
  /** Called when async operation succeeds */
  onSuccess?: () => void;
  /** Called when async operation fails */
  onError?: (error: Error) => void;
}

/**
 * Button component with automatic async state management
 *
 * Wraps the Button component and automatically handles loading states
 * for async onClick handlers. No manual loading state management needed.
 *
 * @example
 * ```tsx
 * <AsyncButton
 *   onClick={async () => await saveSettings()}
 *   loadingText="Saving..."
 *   onSuccess={() => toast({ title: 'Saved!' })}
 *   onError={(err) => toast({ title: err.message, variant: 'destructive' })}
 * >
 *   Save Settings
 * </AsyncButton>
 * ```
 */
export function AsyncButton({
  onClick,
  loadingText,
  onSuccess,
  onError,
  children,
  disabled,
  ...props
}: AsyncButtonProps) {
  const { execute, isLoading } = useAsync(onClick, {
    onSuccess,
    onError,
  });

  const handleClick = useCallback(
    async (event: React.MouseEvent<HTMLButtonElement>) => {
      // Prevent default to avoid form submission if inside a form
      event.preventDefault();
      await execute();
    },
    [execute]
  );

  return (
    <Button
      {...props}
      loading={isLoading}
      loadingText={loadingText}
      disabled={disabled || isLoading}
      onClick={handleClick}
    >
      {children}
    </Button>
  );
}
