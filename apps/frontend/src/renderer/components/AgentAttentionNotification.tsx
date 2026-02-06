import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useToast } from "../hooks/use-toast";
import type { ExecutionProgressData } from "../../main/agent";

/**
 * Agent Attention Notification Component
 * Shows toast notifications when agent requires attention (completion or failure)
 */
export function AgentAttentionNotification() {
  const { t } = useTranslation(["tasks", "common"]);
  const { toast } = useToast();

  useEffect(() => {
    // Listen for execution progress events
    const handleExecutionProgress = (
      taskId: string,
      progress: ExecutionProgressData
    ) => {
      // Only show notifications for terminal phases that require attention
      if (progress.phase === "complete") {
        toast({
          title: t("tasks:notifications.taskComplete", "Task Complete"),
          description: t(
            "tasks:notifications.taskCompleteDescription",
            "Your task has finished successfully and is ready for review."
          ),
          variant: "default",
          duration: 5000,
        });
      } else if (progress.phase === "failed") {
        toast({
          title: t("tasks:notifications.taskFailed", "Task Failed"),
          description: t(
            "tasks:notifications.taskFailedDescription",
            "Your task encountered an issue and requires your attention."
          ),
          variant: "destructive",
          duration: 7000,
        });
      }
    };

    // Register IPC listener using the correct API pattern
    const cleanup = window.electronAPI.onTaskExecutionProgress(handleExecutionProgress);

    // Cleanup
    return cleanup;
  }, [t, toast]);

  // This component doesn't render anything visible - it only manages toast notifications
  return null;
}
