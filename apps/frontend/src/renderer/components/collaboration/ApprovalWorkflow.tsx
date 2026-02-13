/**
 * ApprovalWorkflow - Spec Review and Approval Management
 *
 * Manages the approval workflow for specs before builds can start.
 * Displays approval status, allows requesting approval, and enables
 * admins to approve or reject specs with optional feedback.
 *
 * Features:
 * - Display current approval status with visual indicators
 * - Request approval from team admins
 * - Approve or reject specs with reasons (admin only)
 * - Approval history showing who reviewed and when
 * - Integration with permission system for access control
 *
 * @example
 * ```tsx
 * <ApprovalWorkflow
 *   specId="001-feature"
 *   currentUserId="user-123"
 *   userRole="admin"
 *   onApprovalRequested={(approval) => console.log('Requested:', approval)}
 *   onApprovalApproved={(approval) => console.log('Approved:', approval)}
 *   onApprovalRejected={(approval) => console.log('Rejected:', approval)}
 * />
 * ```
 */
import { useState, useEffect } from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  AlertCircle,
  Send,
  Loader2,
  ChevronDown,
  ChevronUp,
  FileText,
  Calendar
} from 'lucide-react';
import { Card, CardContent, CardHeader } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Textarea } from '../ui/textarea';
import { cn } from '../../lib/utils';
import type { Approval, ApprovalStatus, CollaborationUser } from '../../../shared/types';

/**
 * Props for ApprovalWorkflow
 */
interface ApprovalWorkflowProps {
  /** Spec ID to manage approvals for */
  specId: string;
  /** Current user's ID for permission checks */
  currentUserId: string;
  /** Current user's role (admin can approve/reject) */
  userRole: 'read' | 'write' | 'admin';
  /** Callback when approval is requested */
  onApprovalRequested?: (approval: Approval) => void;
  /** Callback when approval is granted */
  onApprovalApproved?: (approval: Approval) => void;
  /** Callback when approval is rejected */
  onApprovalRejected?: (approval: Approval) => void;
  /** Optional CSS class name */
  className?: string;
}

/**
 * Approval status with display info
 */
interface StatusInfo {
  status: ApprovalStatus;
  label: string;
  description: string;
  icon: React.ReactNode;
  colorClass: string;
  bgColorClass: string;
}

/**
 * Get approval status display information
 */
function getStatusInfo(status: ApprovalStatus): StatusInfo {
  const statusMap: Record<ApprovalStatus, StatusInfo> = {
    pending: {
      status: 'pending',
      label: 'Pending Approval',
      description: 'Waiting for admin review',
      icon: <Clock className="h-5 w-5" />,
      colorClass: 'text-warning',
      bgColorClass: 'bg-warning/10 border-warning/20'
    },
    approved: {
      status: 'approved',
      label: 'Approved',
      description: 'Build can start',
      icon: <CheckCircle2 className="h-5 w-5" />,
      colorClass: 'text-success',
      bgColorClass: 'bg-success/10 border-success/20'
    },
    rejected: {
      status: 'rejected',
      label: 'Rejected',
      description: 'Needs revision',
      icon: <XCircle className="h-5 w-5" />,
      colorClass: 'text-destructive',
      bgColorClass: 'bg-destructive/10 border-destructive/20'
    }
  };

  return statusMap[status];
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

/**
 * Approval History Item Component
 */
interface ApprovalHistoryItemProps {
  approval: Approval;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

function ApprovalHistoryItem({ approval, isExpanded, onToggleExpand }: ApprovalHistoryItemProps) {
  const statusInfo = getStatusInfo(approval.status);

  return (
    <div className="border-b border-border last:border-0 pb-3 last:pb-0">
      <div
        className="flex items-start justify-between gap-3 cursor-pointer hover:bg-muted/50 rounded-lg p-2 -mx-2 transition-colors"
        onClick={onToggleExpand}
      >
        <div className="flex items-start gap-3 flex-1">
          {/* Status Icon */}
          <div className={cn('mt-0.5', statusInfo.colorClass)}>
            {statusInfo.icon}
          </div>

          {/* User Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-medium text-foreground">
                {approval.approver.username}
              </p>
              <Badge
                variant="outline"
                className={cn('text-xs', statusInfo.bgColorClass, statusInfo.colorClass)}
              >
                {statusInfo.label}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {formatTimestamp(approval.created_at)}
            </p>
          </div>
        </div>

        {/* Expand Icon */}
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 shrink-0">
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="mt-3 pl-9 space-y-2">
          {approval.reason && (
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <FileText className="h-3 w-3" />
                <span className="font-medium">Reason:</span>
              </div>
              <p className="text-sm text-foreground bg-muted/50 rounded-md p-2">
                {approval.reason}
              </p>
            </div>
          )}
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              <span>Created: {new Date(approval.created_at).toLocaleString()}</span>
            </div>
            {approval.reviewed_at && (
              <div className="flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" />
                <span>Reviewed: {new Date(approval.reviewed_at).toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Approval Action Form Component
 */
interface ApprovalActionFormProps {
  action: 'approve' | 'reject';
  onSubmit: (reason: string) => void;
  onCancel: () => void;
}

function ApprovalActionForm({ action, onSubmit, onCancel }: ApprovalActionFormProps) {
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isApprove = action === 'approve';
  const statusInfo = getStatusInfo(isApprove ? 'approved' : 'rejected');

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await onSubmit(reason);
      setReason('');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className={cn('border-2', statusInfo.bgColorClass)}>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          {statusInfo.icon}
          <h4 className="text-sm font-semibold text-foreground">
            {isApprove ? 'Approve Spec' : 'Reject Spec'}
          </h4>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <label className="text-sm font-medium text-foreground mb-2 block">
            Reason {isApprove ? '(optional)' : '(required)'}
          </label>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={isApprove ? 'Why are you approving this spec?' : 'Why does this spec need revision?'}
            className="min-h-[100px] text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={!isApprove && !reason.trim()}
            className={cn('gap-1', statusInfo.colorClass, isApprove && 'bg-success text-success hover:bg-success/90')}
          >
            {isSubmitting ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <CheckCircle2 className="h-3 w-3" />
            )}
            {isApprove ? 'Approve' : 'Reject'}
          </Button>
          <Button size="sm" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * ApprovalWorkflow Component
 */
export function ApprovalWorkflow({
  specId,
  currentUserId,
  userRole,
  onApprovalRequested,
  onApprovalApproved,
  onApprovalRejected,
  className
}: ApprovalWorkflowProps) {
  const [currentApproval, setCurrentApproval] = useState<Approval | null>(null);
  const [approvalHistory, setApprovalHistory] = useState<Approval[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<boolean>(false);

  const [showActionForm, setShowActionForm] = useState<'approve' | 'reject' | null>(null);
  const [expandedHistoryId, setExpandedHistoryId] = useState<string | null>(null);

  const isAdmin = userRole === 'admin';
  const status = currentApproval?.status || 'pending';
  const statusInfo = getStatusInfo(status);

  // Load approval status when component mounts
  useEffect(() => {
    loadApprovalStatus();
  }, [specId]);

  const loadApprovalStatus = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual IPC call once handler is implemented
      // const result = await window.electronAPI.collaborationApprovalsGet({ specId });
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to load approval status');
      // }
      // setCurrentApproval(result.data.current);
      // setApprovalHistory(result.data.history || []);

      // Placeholder: Mock data until IPC is connected
      setCurrentApproval(null);
      setApprovalHistory([]);
    } catch (err) {
      console.error('Failed to load approval status:', err);
      setError(err instanceof Error ? err.message : 'Failed to load approval status');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRequestApproval = async () => {
    setActionInProgress(true);
    setError(null);

    try {
      // TODO: Replace with actual IPC call
      // const result = await window.electronAPI.collaborationApprovalsRequest({ specId });
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to request approval');
      // }
      // const newApproval: Approval = result.data;
      // setCurrentApproval(newApproval);
      // setApprovalHistory(prev => [newApproval, ...prev]);
      // onApprovalRequested?.(newApproval);

      // Placeholder: Mock request
      console.log('Requesting approval for spec:', specId);
    } catch (err) {
      console.error('Failed to request approval:', err);
      setError(err instanceof Error ? err.message : 'Failed to request approval');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleApprove = async (reason: string) => {
    setActionInProgress(true);
    setError(null);

    try {
      // TODO: Replace with actual IPC call
      // const result = await window.electronAPI.collaborationApprovalsApprove({
      //   specId,
      //   reason: reason || undefined
      // });
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to approve spec');
      // }
      // const approvedApproval: Approval = result.data;
      // setCurrentApproval(approvedApproval);
      // setApprovalHistory(prev => [approvedApproval, ...prev]);
      // setShowActionForm(null);
      // onApprovalApproved?.(approvedApproval);

      // Placeholder: Mock approve
      console.log('Approving spec:', specId, 'with reason:', reason);
      setShowActionForm(null);
    } catch (err) {
      console.error('Failed to approve spec:', err);
      setError(err instanceof Error ? err.message : 'Failed to approve spec');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleReject = async (reason: string) => {
    setActionInProgress(true);
    setError(null);

    try {
      // TODO: Replace with actual IPC call
      // const result = await window.electronAPI.collaborationApprovalsReject({
      //   specId,
      //   reason
      // });
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to reject spec');
      // }
      // const rejectedApproval: Approval = result.data;
      // setCurrentApproval(rejectedApproval);
      // setApprovalHistory(prev => [rejectedApproval, ...prev]);
      // setShowActionForm(null);
      // onApprovalRejected?.(rejectedApproval);

      // Placeholder: Mock reject
      console.log('Rejecting spec:', specId, 'with reason:', reason);
      setShowActionForm(null);
    } catch (err) {
      console.error('Failed to reject spec:', err);
      setError(err instanceof Error ? err.message : 'Failed to reject spec');
    } finally {
      setActionInProgress(false);
    }
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            Approval Workflow
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Spec must be approved before builds can start
          </p>
        </div>
        {currentApproval && (
          <Badge
            variant="outline"
            className={cn('text-sm', statusInfo.bgColorClass, statusInfo.colorClass)}
          >
            {statusInfo.icon}
            <span className="ml-1">{statusInfo.label}</span>
          </Badge>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-center gap-3 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Loading approval status...</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="p-4">
            <div className="flex items-start gap-3 text-destructive">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Approval Error</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Status & Actions */}
      {!isLoading && !error && (
        <>
          {/* Current Status Card */}
          <Card className={cn('border-2', statusInfo.bgColorClass)}>
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className={cn('mt-0.5', statusInfo.colorClass)}>
                    {statusInfo.icon}
                  </div>
                  <div>
                    <h4 className="text-base font-semibold text-foreground">
                      {statusInfo.label}
                    </h4>
                    <p className="text-sm text-muted-foreground mt-0.5">
                      {statusInfo.description}
                    </p>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Action Buttons */}
              {!showActionForm && !actionInProgress && (
                <div className="flex items-center gap-2 flex-wrap">
                  {status === 'pending' && !isAdmin && (
                    <Button
                      size="sm"
                      onClick={handleRequestApproval}
                      disabled={actionInProgress}
                      className="gap-1"
                    >
                      <Send className="h-3 w-3" />
                      Request Approval
                    </Button>
                  )}
                  {status === 'pending' && isAdmin && (
                    <>
                      <Button
                        size="sm"
                        onClick={() => setShowActionForm('approve')}
                        disabled={actionInProgress}
                        className="gap-1 bg-success text-success hover:bg-success/90"
                      >
                        <CheckCircle2 className="h-3 w-3" />
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setShowActionForm('reject')}
                        disabled={actionInProgress}
                        className="gap-1 text-destructive hover:bg-destructive/10"
                      >
                        <XCircle className="h-3 w-3" />
                        Reject
                      </Button>
                    </>
                  )}
                </div>
              )}

              {/* Action Form */}
              {showActionForm && (
                <ApprovalActionForm
                  action={showActionForm}
                  onSubmit={showActionForm === 'approve' ? handleApprove : handleReject}
                  onCancel={() => setShowActionForm(null)}
                />
              )}

              {/* Loading Indicator */}
              {actionInProgress && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Processing...</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Approval History */}
          {approvalHistory.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Approval History
                </h4>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {approvalHistory.map((approval) => (
                    <ApprovalHistoryItem
                      key={approval.approval_id}
                      approval={approval}
                      isExpanded={expandedHistoryId === approval.approval_id}
                      onToggleExpand={() =>
                        setExpandedHistoryId(
                          expandedHistoryId === approval.approval_id
                            ? null
                            : approval.approval_id
                        )
                      }
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
