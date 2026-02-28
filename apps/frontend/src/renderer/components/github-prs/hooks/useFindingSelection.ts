/**
 * Custom hook for managing finding selection state and actions
 */

import { useCallback } from 'react';
import type { PRReviewFinding } from './useGitHubPRs';
import type { SeverityGroup } from '../constants/severity-config';

interface UseFindingSelectionProps {
  findings: PRReviewFinding[];
  selectedIds: Set<string>;
  onSelectionChange: (selectedIds: Set<string>) => void;
  groupedFindings: Record<SeverityGroup, PRReviewFinding[]>;
}

export function useFindingSelection({
  findings,
  selectedIds,
  onSelectionChange,
  groupedFindings,
}: UseFindingSelectionProps) {
  // Toggle individual finding selection
  const toggleFinding = useCallback((id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    onSelectionChange(next);
  }, [selectedIds, onSelectionChange]);

  // Select all findings (preserve selections for IDs not in active findings list)
  const selectAll = useCallback(() => {
    const activeIds = new Set(findings.map(f => f.id));
    const preserved = new Set<string>();
    for (const id of selectedIds) {
      if (!activeIds.has(id)) {
        preserved.add(id);
      }
    }
    const next = new Set([...preserved, ...findings.map(f => f.id)]);
    onSelectionChange(next);
  }, [findings, selectedIds, onSelectionChange]);

  // Clear all selections
  const selectNone = useCallback(() => {
    onSelectionChange(new Set());
  }, [onSelectionChange]);

  // Select only critical and high severity findings (preserve selections for IDs not in active findings list)
  const selectImportant = useCallback(() => {
    const activeIds = new Set(findings.map(f => f.id));
    const preserved = new Set<string>();
    for (const id of selectedIds) {
      if (!activeIds.has(id)) {
        preserved.add(id);
      }
    }
    const important = [...groupedFindings.critical, ...groupedFindings.high];
    const next = new Set([...preserved, ...important.map(f => f.id)]);
    onSelectionChange(next);
  }, [findings, groupedFindings, selectedIds, onSelectionChange]);

  // Toggle entire severity group selection
  const toggleSeverityGroup = useCallback((severity: SeverityGroup) => {
    const groupFindings = groupedFindings[severity];
    const allSelected = groupFindings.every(f => selectedIds.has(f.id));

    const next = new Set(selectedIds);
    if (allSelected) {
      // Deselect all in group
      for (const f of groupFindings) {
        next.delete(f.id);
      }
    } else {
      // Select all in group
      for (const f of groupFindings) {
        next.add(f.id);
      }
    }
    onSelectionChange(next);
  }, [groupedFindings, selectedIds, onSelectionChange]);

  // Check if all findings in a group are selected
  const isGroupFullySelected = useCallback((severity: SeverityGroup) => {
    const groupFindings = groupedFindings[severity];
    return groupFindings.length > 0 && groupFindings.every(f => selectedIds.has(f.id));
  }, [groupedFindings, selectedIds]);

  // Check if some (but not all) findings in a group are selected
  const isGroupPartiallySelected = useCallback((severity: SeverityGroup) => {
    const groupFindings = groupedFindings[severity];
    const selectedCount = groupFindings.filter(f => selectedIds.has(f.id)).length;
    return selectedCount > 0 && selectedCount < groupFindings.length;
  }, [groupedFindings, selectedIds]);

  return {
    toggleFinding,
    selectAll,
    selectNone,
    selectImportant,
    toggleSeverityGroup,
    isGroupFullySelected,
    isGroupPartiallySelected,
  };
}
