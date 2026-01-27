/**
 * Toast hook for displaying notifications
 * Simplified version for web (full implementation would use a toast library)
 */

export interface ToastProps {
  title?: string;
  description?: string;
  variant?: 'default' | 'destructive';
  duration?: number;
}

export function useToast() {
  const toast = (props: ToastProps) => {
    // For now, use console logging
    // In a real implementation, this would use a toast library like react-hot-toast or sonner
    console.log('[Toast]', props);
  };

  return { toast };
}
