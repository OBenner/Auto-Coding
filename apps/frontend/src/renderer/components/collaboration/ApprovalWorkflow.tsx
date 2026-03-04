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
import { useTranslation } from 'react-i18next';
import {
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
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
import {
  CollaborationLoadingState,
  CollaborationErrorState,
  CollaborationSectionHeader,
  formatTimestamp,
} from './shared';

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
function getStatusInfo(status: ApprovalStatus, t: (key: string, params?: any) => string): StatusInfo {
  const statusMap: Record<ApprovalStatus, StatusInfo> = {
    pending: {
      status: 'pending',
      label: t('collaboration:approvals.status.pending'),
      description: t('collaboration:approvals.statusDescription.pending'),
      icon: <Clock className="h-5 w-5" />,
      colorClass: 'text-warning',
      bgColorClass: 'bg-warning/10 border-warning/20'
    },
    approved: {
      status: 'approved',
      label: t('collaboration:approvals.status.approved'),
      description: t('collaboration:approvals.statusDescription.approved'),
      icon: <CheckCircle2 className="h-5 w-5" />,
      colorClass: 'text-success',
      bgColorClass: 'bg-success/10 border-success/20'
    },
    rejected: {
      status: 'rejected',
      label: t('collaboration:approvals.status.rejected'),
      description: t('collaboration:approvals.statusDescription.rejected'),
      icon: <XCircle className="h-5 w-5" />,
      colorClass: 'text-destructive',
      bgColorClass: 'bg-destructive/10 border-destructive/20'
    }
  };

  return statusMap[status];
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
  const { t } = useTranslation(['collaboration', 'common']);
  const statusInfo = getStatusInfo(approval.status, t);

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
              {formatTimestamp(approval.created_at, t)}
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
                <span className="font-medium">{t('collaboration:common.reason')}</span>
              </div>
              <p className="text-sm text-foreground bg-muted/50 rounded-md p-2">
                {approval.reason}
              </p>
            </div>
          )}
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              <span>{t('collaboration:approvals.created')} {new Date(approval.created_at).toLocaleString()}</span>
            </div>
            {approval.reviewed_at && (
              <div className="flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" />
                <span>{t('collaboration:approvals.reviewed')} {new Date(approval.reviewed_at).toLocaleString()}</span>
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
  const { t } = useTranslation(['collaboration', 'common']);

  const isApprove = action === 'approve';
  const statusInfo = getStatusInfo(isApprove ? 'approved' : 'rejected', t);

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
            {isApprove ? t('collaboration:approvals.approveSpec') : t('collaboration:approvals.rejectSpec')}
          </h4>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <label className="text-sm font-medium text-foreground mb-2 block">
            {t('collaboration:common.reason')} {isApprove ? t('collaboration:approvals.reasonOptional') : t('collaboration:approvals.reasonRequired')}
          </label>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={isApprove ? t('collaboration:approvals.approvePlaceholder') : t('collaboration:approvals.rejectPlaceholder')}
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
            {isApprove ? t('collaboration:approvals.approve') : t('collaboration:approvals.reject')}
          </Button>
          <Button size="sm" variant="outline" onClick={onCancel}>
            {t('collaboration:approvals.cancel')}
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
  const { t } = useTranslation(['collaboration', 'common']);

  const isAdmin = userRole === 'admin';
  const status = currentApproval?.status || 'pending';
  const statusInfo = getStatusInfo(status, t);

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
    // TODO: Replace with actual IPC call
    // const result = await window.electronAPI.collaborationApprovalsRequest({ specId });
    // if (!result.success) {
    //   throw new Error(result.error || 'Failed to request approval');
    // }
    // const newApproval: Approval = result.data;
    // setCurrentApproval(newApproval);
    // setApprovalHistory(prev => [newApproval, ...prev]);
    // onApprovalRequested?.(newApproval);
    setActionInProgress(false);
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

      // Placeholder: No-op until IPC handler is connected
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

      // Placeholder: No-op until IPC handler is connected
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
      <CollaborationSectionHeader
        icon={<ShieldCheck className="h-5 w-5 text-primary" />}
        title={t('collaboration:approvals.title')}
        description={t('collaboration:approvals.description')}
        badge={currentApproval ? (
          <Badge
            variant="outline"
            className={cn('text-sm', statusInfo.bgColorClass, statusInfo.colorClass)}
          >
            {statusInfo.icon}
            <span className="ml-1">{statusInfo.label}</span>
          </Badge>
        ) : undefined}
      />

      {/* Loading State */}
      {isLoading && (
        <CollaborationLoadingState message={t('collaboration:approvals.loading')} />
      )}

      {/* Error State */}
      {error && (
        <CollaborationErrorState title={t('collaboration:approvals.error')} detail={error} />
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
                      {t('collaboration:approvals.requestApproval')}
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
                        {t('collaboration:approvals.approve')}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setShowActionForm('reject')}
                        disabled={actionInProgress}
                        className="gap-1 text-destructive hover:bg-destructive/10"
                      >
                        <XCircle className="h-3 w-3" />
                        {t('collaboration:approvals.reject')}
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
                  <span>{t('collaboration:approvals.processing')}</span>
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
                  {t('collaboration:approvals.history')}
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
