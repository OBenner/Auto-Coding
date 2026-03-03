import { RefreshCw, FileText, Download } from 'lucide-react';
import { Button } from '../ui/button';

interface DashboardActionsProps {
  onRefresh: () => void;
  onExportJson: () => void;
  onExportCsv: () => void;
  isRefreshing?: boolean;
  isExporting?: boolean;
}

export function DashboardActions({
  onRefresh,
  onExportJson,
  onExportCsv,
  isRefreshing = false,
  isExporting = false,
}: Readonly<DashboardActionsProps>) {
  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={onRefresh}
        disabled={isRefreshing}
      >
        <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
        Refresh
      </Button>

      <Button
        variant="outline"
        size="sm"
        onClick={onExportJson}
        disabled={isExporting}
      >
        <FileText className="h-4 w-4 mr-2" />
        Export JSON
      </Button>

      <Button
        variant="outline"
        size="sm"
        onClick={onExportCsv}
        disabled={isExporting}
      >
        <Download className="h-4 w-4 mr-2" />
        Export CSV
      </Button>
    </>
  );
}
