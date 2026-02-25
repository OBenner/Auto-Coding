import { useState } from 'react';
import { Loader2, RefreshCw, History } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { ScrollArea } from '../ui/scroll-area';
import { MergeHistoryItem } from './MergeHistoryItem';
import type { MergeOperationRecord } from '../../../shared/types/merge-analytics';

interface MergeHistoryListProps {
  operations: MergeOperationRecord[];
  isLoading: boolean;
  selectedOperationId: string | null;
  onSelectOperation: (operation: MergeOperationRecord) => void;
  onRefresh: () => void;
  statusFilter: 'all' | 'success' | 'failed';
  onStatusFilterChange: (status: 'all' | 'success' | 'failed') => void;
}

export function MergeHistoryList({
  operations,
  isLoading,
  selectedOperationId,
  onSelectOperation,
  onRefresh,
  statusFilter,
  onStatusFilterChange
}: MergeHistoryListProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredOperations = operations.filter((operation) => {
    // Apply search filter
    const matchesSearch =
      operation.operation_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      operation.tasks_merged.some((task) =>
        task.toLowerCase().includes(searchQuery.toLowerCase())
      ) ||
      (operation.error?.toLowerCase().includes(searchQuery.toLowerCase()));

    // Apply status filter
    let matchesStatus = true;
    if (statusFilter === 'success') {
      matchesStatus = operation.success;
    } else if (statusFilter === 'failed') {
      matchesStatus = !operation.success;
    }

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
            <History className="h-4 w-4" />
            Merge History
          </h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            disabled={isLoading}
            className="h-7 px-2"
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        <Input
          placeholder="Search by operation ID, task, or error..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="h-8 text-sm"
        />

        <div className="flex gap-1">
          {(['all', 'success', 'failed'] as const).map((status) => (
            <Button
              key={status}
              variant={statusFilter === status ? 'default' : 'ghost'}
              size="sm"
              onClick={() => onStatusFilterChange(status)}
              className="h-7 text-xs capitalize"
            >
              {status}
            </Button>
          ))}
        </div>
      </div>

      {/* List */}
      <ScrollArea className="flex-1">
        {isLoading && operations.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : filteredOperations.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            {searchQuery || statusFilter !== 'all'
              ? 'No matching merge operations'
              : 'No merge operations recorded yet'}
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {filteredOperations.map((operation) => (
              <MergeHistoryItem
                key={operation.operation_id}
                operation={operation}
                isSelected={operation.operation_id === selectedOperationId}
                onClick={() => onSelectOperation(operation)}
              />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
