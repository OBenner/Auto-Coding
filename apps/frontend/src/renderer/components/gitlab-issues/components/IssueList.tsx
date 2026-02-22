import { AlertCircle } from 'lucide-react';
import { ScrollArea } from '../../ui/scroll-area';
import { IssueListItem } from './IssueListItem';
import { EmptyState } from './EmptyStates';
import { IssueListSkeleton } from '../../skeletons/IssueListSkeleton';
import type { IssueListProps } from '../types';

export function IssueList({
  issues,
  selectedIssueIid,
  isLoading,
  error,
  onSelectIssue,
  onInvestigate,
  onQuickCreate
}: IssueListProps) {
  if (error) {
    return (
      <div className="p-4 bg-destructive/10 border-b border-destructive/30">
        <div className="flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <ScrollArea className="flex-1">
        <div className="p-2">
          <IssueListSkeleton count={5} />
        </div>
      </ScrollArea>
    );
  }

  if (issues.length === 0) {
    return <EmptyState message="No issues found" />;
  }

  return (
    <ScrollArea className="flex-1">
      <div className="p-2 space-y-1">
        {issues.map((issue) => (
          <IssueListItem
            key={issue.id}
            issue={issue}
            isSelected={selectedIssueIid === issue.iid}
            onClick={() => onSelectIssue(issue.iid)}
            onInvestigate={() => onInvestigate(issue)}
            onQuickCreate={() => onQuickCreate?.(issue)}
          />
        ))}
      </div>
    </ScrollArea>
  );
}
