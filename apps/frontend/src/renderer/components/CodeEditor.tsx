import { useEffect, useRef, useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useVirtualizer } from '@tanstack/react-virtual';
import {
  FolderTree,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Folder,
  File,
  FileCode,
  FileJson,
  FileText,
  FileImage,
  Loader2,
  AlertCircle,
  FolderOpen,
} from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';
import { CodeEditorPanel } from './CodeEditorPanel';
import { useCodeEditorStore } from '../stores/code-editor-store';
import { useFileExplorerStore } from '../stores/file-explorer-store';
import { useVirtualizedTree, type FlattenedNode } from '../hooks/useVirtualizedTree';
import { cn } from '../lib/utils';

interface CodeEditorProps {
  projectPath: string;
}

// Estimated height of each tree item in pixels
const ITEM_HEIGHT = 28;
// Number of items to render outside the visible area for smoother scrolling
const OVERSCAN = 10;

// Get appropriate icon based on file extension
function getFileIcon(name: string): React.ReactNode {
  const ext = name.split('.').pop()?.toLowerCase();

  switch (ext) {
    case 'ts':
    case 'tsx':
    case 'js':
    case 'jsx':
    case 'py':
    case 'rb':
    case 'go':
    case 'rs':
    case 'java':
    case 'c':
    case 'cpp':
    case 'h':
    case 'cs':
    case 'php':
    case 'swift':
    case 'kt':
      return <FileCode className="h-4 w-4 text-info" />;
    case 'json':
    case 'yaml':
    case 'yml':
    case 'toml':
      return <FileJson className="h-4 w-4 text-warning" />;
    case 'md':
    case 'txt':
    case 'rst':
      return <FileText className="h-4 w-4 text-muted-foreground" />;
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
    case 'svg':
    case 'webp':
    case 'ico':
      return <FileImage className="h-4 w-4 text-purple-400" />;
    case 'css':
    case 'scss':
    case 'sass':
    case 'less':
      return <FileCode className="h-4 w-4 text-pink-400" />;
    case 'html':
    case 'htm':
      return <FileCode className="h-4 w-4 text-orange-400" />;
    default:
      return <File className="h-4 w-4 text-muted-foreground" />;
  }
}

// Internal file tree item component with file selection support
interface CodeEditorFileTreeItemProps {
  item: FlattenedNode;
  isSelected: boolean;
  onToggle: () => void;
  onFileSelect: (path: string) => void;
}

function CodeEditorFileTreeItem({
  item,
  isSelected,
  onToggle,
  onFileSelect,
}: CodeEditorFileTreeItemProps) {
  const { node, depth, isExpanded, isLoading } = item;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (node.isDirectory) {
      onToggle();
    } else {
      onFileSelect(node.path);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      e.stopPropagation();
      if (node.isDirectory) {
        onToggle();
      } else {
        onFileSelect(node.path);
      }
    }
  };

  return (
    <div
      role="treeitem"
      tabIndex={0}
      className={cn(
        'flex items-center gap-1 py-1 px-2 rounded cursor-pointer select-none',
        'hover:bg-accent/50 transition-colors',
        'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1',
        isSelected && !node.isDirectory && 'bg-primary/20 hover:bg-primary/30'
      )}
      style={{ paddingLeft: `${depth * 12 + 8}px` }}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      aria-selected={isSelected && !node.isDirectory}
    >
      {/* Expand/collapse chevron for directories */}
      {node.isDirectory ? (
        <button
          type="button"
          className="flex items-center justify-center w-4 h-4 hover:bg-accent rounded"
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
          }}
          aria-expanded={isExpanded}
          tabIndex={-1}
        >
          {isLoading ? (
            <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" aria-hidden="true" />
          ) : isExpanded ? (
            <ChevronDown className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
          ) : (
            <ChevronRight className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
          )}
        </button>
      ) : (
        <span className="w-4" aria-hidden="true" />
      )}

      {/* Icon */}
      {node.isDirectory ? (
        <Folder
          className={cn('h-4 w-4', isExpanded ? 'text-primary' : 'text-warning')}
        />
      ) : (
        getFileIcon(node.name)
      )}

      {/* Name */}
      <span className="text-xs truncate flex-1 text-foreground">{node.name}</span>
    </div>
  );
}

// Internal file tree component with selection support
interface CodeEditorFileTreeProps {
  rootPath: string;
  selectedFile: string | null;
  onFileSelect: (path: string) => void;
}

function CodeEditorFileTree({
  rootPath,
  selectedFile,
  onFileSelect,
}: CodeEditorFileTreeProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const { loadDirectory, isLoadingDir, error } = useFileExplorerStore();

  const { flattenedNodes, count, handleToggle, isRootLoading, hasRootFiles } =
    useVirtualizedTree(rootPath);

  const loading = isLoadingDir(rootPath);

  // Load root directory on mount
  useEffect(() => {
    if (!hasRootFiles && !loading) {
      loadDirectory(rootPath);
    }
  }, [rootPath, hasRootFiles, loading, loadDirectory]);

  // Set up the virtualizer
  const rowVirtualizer = useVirtualizer({
    count,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ITEM_HEIGHT,
    overscan: OVERSCAN,
  });

  // Create toggle handler for each item
  const createToggleHandler = useCallback(
    (index: number) => {
      return () => {
        const item = flattenedNodes[index];
        if (item) {
          handleToggle(item.node);
        }
      };
    },
    [flattenedNodes, handleToggle]
  );

  if (isRootLoading && !hasRootFiles) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
        <AlertCircle className="h-5 w-5 text-destructive mb-2" />
        <p className="text-xs text-destructive">{error}</p>
      </div>
    );
  }

  if (!hasRootFiles || count === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
        <FolderOpen className="h-6 w-6 text-muted-foreground mb-2" />
        <p className="text-xs text-muted-foreground">No files found</p>
      </div>
    );
  }

  return (
    <div ref={parentRef} className="h-full overflow-auto py-1">
      {/* The large inner element to hold all of the items */}
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {/* Only the visible items in the virtualizer */}
        {rowVirtualizer.getVirtualItems().map((virtualItem) => {
          const item = flattenedNodes[virtualItem.index];
          if (!item) return null;

          return (
            <div
              key={item.key}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualItem.size}px`,
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              <CodeEditorFileTreeItem
                item={item}
                isSelected={selectedFile === item.node.path}
                onToggle={createToggleHandler(virtualItem.index)}
                onFileSelect={onFileSelect}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function CodeEditor({ projectPath }: CodeEditorProps) {
  const { t } = useTranslation(['common', 'dialogs']);

  // Code editor store state
  const currentFile = useCodeEditorStore((state) => state.currentFile);
  const isDirty = useCodeEditorStore((state) => state.isDirty);
  const openFile = useCodeEditorStore((state) => state.openFile);
  const saveFile = useCodeEditorStore((state) => state.saveFile);
  const discardChanges = useCodeEditorStore((state) => state.discardChanges);

  // File explorer store actions
  const clearCache = useFileExplorerStore((state) => state.clearCache);
  const loadDirectory = useFileExplorerStore((state) => state.loadDirectory);

  // Pending file selection (when unsaved changes dialog is open)
  const [pendingFile, setPendingFile] = useState<string | null>(null);
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false);
  const [isSavingBeforeSwitch, setIsSavingBeforeSwitch] = useState(false);

  // Handle file selection with unsaved changes check
  const handleFileSelect = useCallback(
    (filePath: string) => {
      // If selecting the same file, do nothing
      if (filePath === currentFile) {
        return;
      }

      // If there are unsaved changes, show the dialog
      if (isDirty) {
        setPendingFile(filePath);
        setShowUnsavedDialog(true);
        return;
      }

      // Otherwise, open the file directly
      openFile(filePath);
    },
    [currentFile, isDirty, openFile]
  );

  // Handle save and switch
  const handleSaveAndSwitch = useCallback(async () => {
    if (!pendingFile) return;

    setIsSavingBeforeSwitch(true);
    const success = await saveFile();
    setIsSavingBeforeSwitch(false);

    if (success) {
      setShowUnsavedDialog(false);
      openFile(pendingFile);
      setPendingFile(null);
    }
  }, [pendingFile, saveFile, openFile]);

  // Handle discard and switch
  const handleDiscardAndSwitch = useCallback(() => {
    if (!pendingFile) return;

    discardChanges();
    setShowUnsavedDialog(false);
    openFile(pendingFile);
    setPendingFile(null);
  }, [pendingFile, discardChanges, openFile]);

  // Handle cancel
  const handleCancelSwitch = useCallback(() => {
    setShowUnsavedDialog(false);
    setPendingFile(null);
  }, []);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    clearCache();
    loadDirectory(projectPath);
  }, [clearCache, loadDirectory, projectPath]);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <FolderTree className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">{t('common:codeEditor.title')}</h2>
        </div>
      </div>

      {/* Main content - two pane layout */}
      <div className="flex flex-1 min-h-0">
        {/* Left pane - File tree */}
        <div className="w-64 flex flex-col border-r border-border shrink-0">
          {/* File tree header */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-card/50 shrink-0">
            <span className="text-xs font-medium text-muted-foreground">
              {t('common:codeEditor.files')}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={handleRefresh}
              aria-label={t('common:buttons.refresh')}
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
          </div>

          {/* File tree */}
          <ScrollArea className="flex-1">
            <CodeEditorFileTree
              rootPath={projectPath}
              selectedFile={currentFile}
              onFileSelect={handleFileSelect}
            />
          </ScrollArea>
        </div>

        {/* Right pane - Editor */}
        <div className="flex-1 flex flex-col min-w-0">
          <CodeEditorPanel />
        </div>
      </div>

      {/* Unsaved changes dialog */}
      <AlertDialog open={showUnsavedDialog} onOpenChange={setShowUnsavedDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('dialogs:codeEditor.unsavedChangesTitle')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('dialogs:codeEditor.unsavedChangesDescription')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancelSwitch} disabled={isSavingBeforeSwitch}>
              {t('common:buttons.cancel')}
            </AlertDialogCancel>
            <Button
              variant="destructive"
              onClick={handleDiscardAndSwitch}
              disabled={isSavingBeforeSwitch}
            >
              {t('dialogs:codeEditor.discardChanges')}
            </Button>
            <AlertDialogAction onClick={handleSaveAndSwitch} disabled={isSavingBeforeSwitch}>
              {isSavingBeforeSwitch ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {t('common:labels.saving')}
                </>
              ) : (
                t('dialogs:codeEditor.saveAndSwitch')
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
