/**
 * Terminal Component (Web Version)
 * Adapted from Electron frontend - simplified stub for web
 * Note: Full terminal functionality requires backend PTY support
 */

import { useEffect, useRef, useState } from 'react';
import { Terminal as XtermIcon, X } from 'lucide-react';
import { cn } from '../lib/utils';
import { Button } from './ui/button';

export interface TerminalProps {
  id: string;
  cwd?: string;
  projectPath?: string;
  isActive?: boolean;
  onClose?: () => void;
  onActivate?: () => void;
  title?: string;
}

/**
 * Terminal component for web
 * This is a simplified version without full PTY support
 * Full implementation would require backend WebSocket connection for terminal I/O
 */
export function Terminal({
  id,
  cwd,
  isActive = false,
  onClose,
  onActivate,
  title = 'Terminal'
}: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const [output] = useState<string[]>([
    'Terminal (Web Preview)',
    `ID: ${id}`,
    `Working Directory: ${cwd || 'N/A'}`,
    '',
    'Note: Full terminal functionality requires backend PTY support via WebSocket.',
    'This is a placeholder component for the web interface.',
    ''
  ]);

  useEffect(() => {
    if (isActive && terminalRef.current) {
      terminalRef.current.focus();
    }
  }, [isActive]);

  const handleClick = () => {
    onActivate?.();
  };

  return (
    <div
      className={cn(
        'flex flex-col h-full bg-black text-green-400 font-mono text-sm border rounded-lg overflow-hidden',
        isActive && 'ring-2 ring-primary'
      )}
      onClick={handleClick}
    >
      {/* Terminal Header */}
      <div className="flex items-center justify-between bg-gray-800 px-3 py-2 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <XtermIcon className="h-4 w-4" />
          <span className="text-xs text-gray-300">{title}</span>
        </div>
        {onClose && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-gray-400 hover:text-white"
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Terminal Content */}
      <div
        ref={terminalRef}
        className="flex-1 p-4 overflow-auto"
        tabIndex={0}
      >
        {output.map((line, index) => (
          <div key={index} className="whitespace-pre-wrap">
            {line || '\u00A0'}
          </div>
        ))}
      </div>

      {/* Terminal Input (Placeholder) */}
      <div className="px-4 py-2 bg-gray-900 border-t border-gray-700">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>$</span>
          <span className="opacity-50">Terminal input requires backend connection</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Handle interface for external control (matching Electron version signature)
 */
export interface TerminalHandle {
  fit: () => void;
}
