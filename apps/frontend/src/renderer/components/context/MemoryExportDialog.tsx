/**
 * MemoryExportDialog - Dialog for exporting memory data
 *
 * Allows users to export their Graphiti memory graph in various formats
 * (JSON, CSV) with options to filter by type and date range.
 *
 * Features:
 * - Multiple export formats (JSON, CSV)
 * - Filter by memory type
 * - Date range filtering
 * - Export to file with progress indication
 *
 * @example
 * ```tsx
 * <MemoryExportDialog
 *   projectId="my-project"
 *   memories={recentMemories}
 *   open={isExportDialogOpen}
 *   onOpenChange={setIsExportDialogOpen}
 * />
 * ```
 */
import { useState, useEffect, useMemo } from 'react';
import { Loader2, Download, FileJson, FileText } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '../ui/select';
import { Checkbox } from '../ui/checkbox';
import { Badge } from '../ui/badge';
import type { MemoryEpisode, MemoryType } from '../../../shared/types';

/**
 * Props for the MemoryExportDialog component
 */
interface MemoryExportDialogProps {
  /** Project ID for memory export */
  projectId: string;
  /** Available memories to export */
  memories: MemoryEpisode[];
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when the dialog open state changes */
  onOpenChange: (open: boolean) => void;
}

type ExportFormat = 'json' | 'csv';

// Memory type options for filtering
const MEMORY_TYPE_OPTIONS: { value: MemoryType | 'all'; label: string }[] = [
  { value: 'all', label: 'All Types' },
  { value: 'session_insight', label: 'Session Insights' },
  { value: 'codebase_discovery', label: 'Codebase Discoveries' },
  { value: 'codebase_map', label: 'Codebase Maps' },
  { value: 'pattern', label: 'Patterns' },
  { value: 'gotcha', label: 'Gotchas' },
  { value: 'task_outcome', label: 'Task Outcomes' },
  { value: 'pr_review', label: 'PR Reviews' },
  { value: 'pr_finding', label: 'PR Findings' },
  { value: 'pr_pattern', label: 'PR Patterns' },
  { value: 'pr_gotcha', label: 'PR Gotchas' }
];

export function MemoryExportDialog({
  projectId,
  memories,
  open,
  onOpenChange
}: MemoryExportDialogProps) {
  // Form state
  const [format, setFormat] = useState<ExportFormat>('json');
  const [selectedType, setSelectedType] = useState<MemoryType | 'all'>('all');
  const [includeMetadata, setIncludeMetadata] = useState(true);

  // UI state
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (open) {
      setFormat('json');
      setSelectedType('all');
      setIncludeMetadata(true);
      setError(null);
    }
  }, [open]);

  // Filter memories based on selected type
  const filteredMemories = useMemo(() => {
    if (selectedType === 'all') {
      return memories;
    }
    return memories.filter(memory => memory.type === selectedType);
  }, [memories, selectedType]);

  // Convert memories to CSV format
  const convertToCSV = (data: MemoryEpisode[]): string => {
    if (data.length === 0) {
      return 'No data to export';
    }

    const headers = includeMetadata
      ? ['ID', 'Type', 'Timestamp', 'Content', 'Session Number', 'Score', 'PR Number', 'Repo', 'Verdict']
      : ['Type', 'Timestamp', 'Content'];

    const rows = data.map(memory => {
      const basicRow = [
        memory.type,
        new Date(memory.timestamp).toISOString(),
        `"${memory.content.replace(/"/g, '""')}"`
      ];

      if (includeMetadata) {
        return [
          memory.id,
          ...basicRow,
          memory.session_number?.toString() || '',
          memory.score?.toString() || '',
          memory.prNumber?.toString() || '',
          memory.repo || '',
          memory.verdict || ''
        ];
      }

      return basicRow;
    });

    return [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
  };

  const handleExport = async () => {
    if (filteredMemories.length === 0) {
      setError('No memories to export with the selected filters');
      return;
    }

    setIsExporting(true);
    setError(null);

    try {
      let content: string;
      let filename: string;

      if (format === 'json') {
        // Export as JSON
        const exportData = {
          projectId,
          exportDate: new Date().toISOString(),
          totalMemories: filteredMemories.length,
          filters: {
            type: selectedType,
            includeMetadata
          },
          memories: includeMetadata
            ? filteredMemories
            : filteredMemories.map(({ type, timestamp, content }) => ({
                type,
                timestamp,
                content
              }))
        };
        content = JSON.stringify(exportData, null, 2);
        filename = `memory-export-${projectId}-${Date.now()}.json`;
      } else {
        // Export as CSV
        content = convertToCSV(filteredMemories);
        filename = `memory-export-${projectId}-${Date.now()}.csv`;
      }

      // Create download link
      const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);

      // Success - close dialog
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export memories');
    } finally {
      setIsExporting(false);
    }
  };

  const handleClose = () => {
    if (!isExporting) {
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-foreground flex items-center gap-2">
            <Download className="h-5 w-5" />
            Export Memory Data
          </DialogTitle>
          <DialogDescription>
            Export your memory graph in various formats for backup or analysis.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Export Format */}
          <div className="space-y-2">
            <Label htmlFor="export-format" className="text-sm font-medium text-foreground">
              Export Format
            </Label>
            <Select
              value={format}
              onValueChange={(value) => setFormat(value as ExportFormat)}
              disabled={isExporting}
            >
              <SelectTrigger id="export-format">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="json">
                  <div className="flex items-center gap-2">
                    <FileJson className="h-4 w-4" />
                    <span>JSON (Structured Data)</span>
                  </div>
                </SelectItem>
                <SelectItem value="csv">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    <span>CSV (Spreadsheet)</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Memory Type Filter */}
          <div className="space-y-2">
            <Label htmlFor="memory-type" className="text-sm font-medium text-foreground">
              Memory Type
            </Label>
            <Select
              value={selectedType}
              onValueChange={(value) => setSelectedType(value as MemoryType | 'all')}
              disabled={isExporting}
            >
              <SelectTrigger id="memory-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MEMORY_TYPE_OPTIONS.map(({ value, label }) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Include Metadata */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="include-metadata"
              checked={includeMetadata}
              onCheckedChange={(checked) => setIncludeMetadata(checked as boolean)}
              disabled={isExporting}
            />
            <Label
              htmlFor="include-metadata"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
            >
              Include metadata (IDs, scores, session numbers)
            </Label>
          </div>

          {/* Export Preview */}
          <div className="rounded-lg border border-border bg-muted/30 p-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Memories to export:</span>
              <Badge variant="outline" className="font-mono">
                {filteredMemories.length}
              </Badge>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-lg bg-destructive/10 border border-destructive/30 p-3 text-sm text-destructive" role="alert">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isExporting}>
            Cancel
          </Button>
          <Button
            onClick={handleExport}
            disabled={isExporting || filteredMemories.length === 0}
          >
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Export
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
