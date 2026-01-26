import { useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Save, FileCode, Loader2, AlertCircle, RotateCcw } from 'lucide-react';
import CodeMirror from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { markdown } from '@codemirror/lang-markdown';
import { json } from '@codemirror/lang-json';
import { css } from '@codemirror/lang-css';
import { html } from '@codemirror/lang-html';
import { Button } from './ui/button';
import { useCodeEditorStore } from '../stores/code-editor-store';

// Map file extensions to CodeMirror language extensions
function getLanguageExtension(extension: string | null) {
  if (!extension) return [];

  const ext = extension.toLowerCase();

  switch (ext) {
    case '.js':
    case '.jsx':
      return [javascript({ jsx: true })];
    case '.ts':
    case '.tsx':
      return [javascript({ jsx: true, typescript: true })];
    case '.py':
    case '.pyw':
      return [python()];
    case '.md':
    case '.mdx':
    case '.markdown':
      return [markdown()];
    case '.json':
    case '.jsonc':
      return [json()];
    case '.css':
    case '.scss':
    case '.sass':
    case '.less':
      return [css()];
    case '.html':
    case '.htm':
    case '.vue':
    case '.svelte':
      return [html()];
    default:
      return [];
  }
}

export function CodeEditorPanel() {
  const { t } = useTranslation(['common']);
  const {
    currentFile,
    content,
    isDirty,
    isLoading,
    isSaving,
    error,
    saveFile,
    setContent,
    closeFile,
    discardChanges,
    getFileName,
    getFileExtension,
  } = useCodeEditorStore();

  const fileName = getFileName();
  const fileExtension = getFileExtension();

  // Get language extensions based on file type
  const languageExtensions = useMemo(
    () => getLanguageExtension(fileExtension),
    [fileExtension]
  );

  // Detect dark mode from DOM
  const isDarkMode = useMemo(() => {
    if (typeof document !== 'undefined') {
      return document.documentElement.classList.contains('dark');
    }
    return false;
  }, []);

  // Handle save with Ctrl/Cmd+S
  const handleSave = useCallback(async () => {
    if (!isDirty || isSaving) return;
    await saveFile();
  }, [isDirty, isSaving, saveFile]);

  // Keyboard shortcut handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+S or Cmd+S
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSave]);

  // Handle content change
  const handleContentChange = useCallback(
    (value: string) => {
      setContent(value);
    },
    [setContent]
  );

  // No file open state
  if (!currentFile) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-card/50 text-muted-foreground p-8">
        <FileCode className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-sm text-center">
          Select a file from the file tree to open it in the editor
        </p>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-card/50">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="mt-2 text-sm text-muted-foreground">{t('common:labels.loading')}</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex-1 flex flex-col bg-card/50">
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-card/80 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <FileCode className="h-4 w-4 text-primary shrink-0" />
            <span className="text-sm font-medium truncate" title={currentFile}>
              {fileName}
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 shrink-0"
            onClick={closeFile}
            aria-label={t('common:buttons.close')}
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
        </div>

        {/* Error content */}
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <AlertCircle className="h-10 w-10 text-destructive mb-4" />
          <p className="text-sm text-destructive text-center max-w-md">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-card/50 min-w-0">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-card/80 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <FileCode className="h-4 w-4 text-primary shrink-0" />
          <span className="text-sm font-medium truncate" title={currentFile}>
            {fileName}
          </span>
          {/* Dirty indicator */}
          {isDirty && (
            <span
              className="h-2 w-2 rounded-full bg-amber-500 shrink-0"
              title="Unsaved changes"
              aria-label="Unsaved changes"
            />
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {/* Discard changes button */}
          {isDirty && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={discardChanges}
              disabled={isSaving}
              aria-label="Discard changes"
              title="Discard changes"
            >
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
          )}

          {/* Save button */}
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={handleSave}
            disabled={!isDirty || isSaving}
            aria-label={t('common:buttons.save')}
            title={`${t('common:buttons.save')} (Ctrl+S)`}
          >
            {isSaving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <Save className="h-3.5 w-3.5" aria-hidden="true" />
            )}
          </Button>

          {/* Close button */}
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={closeFile}
            aria-label={t('common:buttons.close')}
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 overflow-hidden">
        <CodeMirror
          value={content}
          onChange={handleContentChange}
          extensions={languageExtensions}
          theme={isDarkMode ? 'dark' : 'light'}
          className="h-full w-full text-sm"
          basicSetup={{
            lineNumbers: true,
            highlightActiveLineGutter: true,
            highlightSpecialChars: true,
            history: true,
            foldGutter: true,
            drawSelection: true,
            dropCursor: true,
            allowMultipleSelections: true,
            indentOnInput: true,
            syntaxHighlighting: true,
            bracketMatching: true,
            closeBrackets: true,
            autocompletion: true,
            rectangularSelection: true,
            crosshairCursor: false,
            highlightActiveLine: true,
            highlightSelectionMatches: true,
            closeBracketsKeymap: true,
            defaultKeymap: true,
            searchKeymap: true,
            historyKeymap: true,
            foldKeymap: true,
            completionKeymap: true,
            lintKeymap: true,
          }}
          style={{
            height: '100%',
            width: '100%',
          }}
        />
      </div>
    </div>
  );
}
