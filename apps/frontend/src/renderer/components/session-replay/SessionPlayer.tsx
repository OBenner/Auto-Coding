/**
 * SessionPlayer Component
 *
 * Main component for playing back recorded sessions with playback controls.
 * Provides timeline navigation, speed control, and entry display.
 */

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Square,
  Settings2,
  Bookmark,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from '../ui/dropdown-menu';
import { cn } from '../../lib/utils';
import type { SessionMetadata } from '../../../shared/types';

// Mock LogEntry type based on backend model
interface LogEntry {
  timestamp: string;
  type: string;
  content: string;
  phase: string;
  tool_name: string | null;
  tool_input: string | null;
  subtask_id: string | null;
  session: number | null;
  detail: string | null;
  subphase: string | null;
  collapsed: boolean | null;
  is_decision_point: boolean | null;
  reasoning: string | null;
  alternatives: string[] | null;
  decision: string | null;
}

interface SessionPlayerProps {
  /** Session to play back */
  session: SessionMetadata;
  /** Timeline entries for the session */
  entries: LogEntry[];
  /** Callback when playback state changes */
  onPlaybackChange?: (isPlaying: boolean) => void;
  /** Callback when current entry changes */
  onEntryChange?: (entry: LogEntry | null) => void;
  /** Callback when speed changes */
  onSpeedChange?: (speed: number) => void;
  /** Callback when bookmark is added */
  onAddBookmark?: (entry: LogEntry) => void;
}

/** Playback speed options */
const SPEED_OPTIONS = [0.5, 1, 1.5, 2] as const;
type PlaybackSpeed = (typeof SPEED_OPTIONS)[number];

/**
 * Format speed value for display
 */
function formatSpeed(speed: PlaybackSpeed): string {
  return `${speed}x`;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Get phase badge color
 */
function getPhaseBadgeColor(phase: string): string {
  const phaseColors: Record<string, string> = {
    planning: 'bg-blue-500/20 text-blue-400',
    coding: 'bg-purple-500/20 text-purple-400',
    validation: 'bg-green-500/20 text-green-400',
  };
  return phaseColors[phase] || 'bg-gray-500/20 text-gray-400';
}

/**
 * Main SessionPlayer component
 */
export function SessionPlayer({
  session,
  entries,
  onPlaybackChange,
  onEntryChange,
  onSpeedChange,
  onAddBookmark,
}: SessionPlayerProps) {
  const { t } = useTranslation('session-replay');

  // Playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentEntryIndex, setCurrentEntryIndex] = useState<number | null>(null);
  const [speed, setSpeed] = useState<PlaybackSpeed>(1);

  // Refs for playback interval and timing
  const playbackIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const currentStartTimeRef = useRef<number | null>(null);

  // Computed values
  const currentEntry = useMemo(() => {
    if (currentEntryIndex === null || currentEntryIndex < 0 || currentEntryIndex >= entries.length) {
      return null;
    }
    return entries[currentEntryIndex];
  }, [currentEntryIndex, entries]);

  const canPlay = entries.length > 0;
  const canGoBack = currentEntryIndex !== null && currentEntryIndex > 0;
  const canGoForward =
    currentEntryIndex !== null && currentEntryIndex < entries.length - 1;
  const isAtStart = currentEntryIndex === null || currentEntryIndex === 0;
  const isAtEnd = currentEntryIndex === entries.length - 1;

  // Notify parent of state changes
  useEffect(() => {
    onPlaybackChange?.(isPlaying);
  }, [isPlaying, onPlaybackChange]);

  useEffect(() => {
    onEntryChange?.(currentEntry);
  }, [currentEntry, onEntryChange]);

  useEffect(() => {
    onSpeedChange?.(speed);
  }, [speed, onSpeedChange]);

  // Cleanup playback interval on unmount
  useEffect(() => {
    return () => {
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current);
      }
    };
  }, []);

  // Start playback
  const startPlayback = useCallback(() => {
    if (!canPlay) return;

    // Clear any existing interval before creating a new one
    if (playbackIntervalRef.current) {
      clearInterval(playbackIntervalRef.current);
      playbackIntervalRef.current = null;
    }

    // Start at beginning if not at end
    if (isAtEnd) {
      setCurrentEntryIndex(0);
    } else if (currentEntryIndex === null) {
      setCurrentEntryIndex(0);
    }

    setIsPlaying(true);

    // Calculate delay based on speed (base delay: 2 seconds per entry)
    const baseDelay = 2000;
    const delay = baseDelay / speed;

    playbackIntervalRef.current = setInterval(() => {
      setCurrentEntryIndex((prevIndex) => {
        if (prevIndex === null) return 0;
        const nextIndex = prevIndex + 1;
        if (nextIndex >= entries.length) {
          // End of entries, stop playback
          setIsPlaying(false);
          if (playbackIntervalRef.current) {
            clearInterval(playbackIntervalRef.current);
            playbackIntervalRef.current = null;
          }
          return prevIndex;
        }
        return nextIndex;
      });
    }, delay);
  }, [canPlay, isAtEnd, currentEntryIndex, speed, entries.length]);

  // Pause playback
  const pausePlayback = useCallback(() => {
    setIsPlaying(false);
    if (playbackIntervalRef.current) {
      clearInterval(playbackIntervalRef.current);
      playbackIntervalRef.current = null;
    }
  }, []);

  // Stop playback and reset to start
  const stopPlayback = useCallback(() => {
    pausePlayback();
    setCurrentEntryIndex(null);
  }, [pausePlayback]);

  // Go to previous entry
  const goPrevious = useCallback(() => {
    if (!canGoBack) return;
    pausePlayback();
    setCurrentEntryIndex((prevIndex) => (prevIndex !== null ? prevIndex - 1 : null));
  }, [canGoBack, pausePlayback]);

  // Go to next entry
  const goNext = useCallback(() => {
    if (!canGoForward) return;
    pausePlayback();
    setCurrentEntryIndex((prevIndex) => (prevIndex !== null ? prevIndex + 1 : null));
  }, [canGoForward, pausePlayback]);

  // Handle speed change
  const handleSpeedChange = useCallback(
    (newSpeed: PlaybackSpeed) => {
      setSpeed(newSpeed);
      // Restart playback if playing to apply new speed
      if (isPlaying) {
        pausePlayback();
        startPlayback();
      }
    },
    [isPlaying, pausePlayback, startPlayback]
  );

  // Handle add bookmark
  const handleAddBookmark = useCallback(() => {
    if (currentEntry && onAddBookmark) {
      onAddBookmark(currentEntry);
    }
  }, [currentEntry, onAddBookmark]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in input, textarea, select, or contentEditable elements
      const target = e.target as HTMLElement;
      if (target.closest('input, textarea, select, [contenteditable="true"]')) {
        return;
      }

      switch (e.key) {
        case ' ':
          e.preventDefault();
          if (isPlaying) {
            pausePlayback();
          } else {
            startPlayback();
          }
          break;
        case 'ArrowLeft':
          if (e.shiftKey) {
            // Shift+Left: Go to start
            stopPlayback();
          } else {
            goPrevious();
          }
          break;
        case 'ArrowRight':
          if (e.shiftKey) {
            // Shift+Right: Go to end
            pausePlayback();
            setCurrentEntryIndex(entries.length - 1);
          } else {
            goNext();
          }
          break;
        case 'Escape':
          stopPlayback();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isPlaying, startPlayback, pausePlayback, goPrevious, goNext, stopPlayback, entries.length]);

  return (
    <div className="flex flex-col h-full">
      {/* Playback Controls Header */}
      <div className="px-4 py-3 border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center gap-3">
          {/* Session Title */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-medium truncate">
                {t('sessionPlayer.title')} #{session.session_number}
              </h2>
              {session.completed_at ? (
                <Badge variant="success" className="gap-1">
                  <span className="text-xs">{t('sessionList.statusCompleted')}</span>
                </Badge>
              ) : (
                <Badge variant="warning" className="gap-1">
                  <span className="text-xs">{t('sessionList.statusInProgress')}</span>
                </Badge>
              )}
            </div>
            {currentEntry && (
              <div className="text-xs text-muted-foreground mt-1">
                {t('sessionPlayer.phase')}: {currentEntry.phase}
                {' • '}
                {t('sessionPlayer.timestamp')}: {formatTimestamp(currentEntry.timestamp)}
              </div>
            )}
          </div>

          <Separator orientation="vertical" className="h-6 mx-1" />

          {/* Playback Controls */}
          <div className="flex items-center gap-1">
            {/* Stop Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={stopPlayback}
              disabled={!canPlay && currentEntryIndex === null}
              className="h-8 w-8 p-0"
              aria-label={t('sessionPlayer.stop')}
            >
              <Square className="h-4 w-4" />
            </Button>

            {/* Previous Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={goPrevious}
              disabled={!canGoBack}
              className="h-8 w-8 p-0"
              aria-label={t('sessionPlayer.previous')}
            >
              <SkipBack className="h-4 w-4" />
            </Button>

            {/* Play/Pause Button */}
            <Button
              variant="default"
              size="sm"
              onClick={isPlaying ? pausePlayback : startPlayback}
              disabled={!canPlay}
              className="h-8 w-8 p-0"
              aria-label={isPlaying ? t('sessionPlayer.pause') : t('sessionPlayer.play')}
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
            </Button>

            {/* Next Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={goNext}
              disabled={!canGoForward}
              className="h-8 w-8 p-0"
              aria-label={t('sessionPlayer.next')}
            >
              <SkipForward className="h-4 w-4" />
            </Button>
          </div>

          <Separator orientation="vertical" className="h-6 mx-1" />

          {/* Speed Control */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1"
                aria-label={t('sessionPlayer.speed')}
              >
                <Settings2 className="h-3.5 w-3.5" />
                <span className="text-xs">{formatSpeed(speed)}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[120px] p-1">
              <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                {t('sessionPlayer.speed')}
              </div>
              <DropdownMenuRadioGroup value={String(speed)} onValueChange={(value) => handleSpeedChange(parseFloat(value) as PlaybackSpeed)}>
                {SPEED_OPTIONS.map((speedOption) => (
                  <DropdownMenuRadioItem
                    key={speedOption}
                    value={String(speedOption)}
                    className="cursor-pointer"
                  >
                    {t(`sessionPlayer.speed${speedOption}x`)}
                  </DropdownMenuRadioItem>
                ))}
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Bookmark Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleAddBookmark}
            disabled={!currentEntry}
            className="h-8 w-8 p-0"
            aria-label={t('sessionPlayer.addBookmark')}
          >
            <Bookmark className="h-4 w-4" />
          </Button>
        </div>

        {/* Progress Bar */}
        {entries.length > 0 && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
              <span>
                {currentEntryIndex !== null ? currentEntryIndex + 1 : 0} / {entries.length}{' '}
                {t('sessionPlayer.entries')}
              </span>
              <span>
                {currentEntryIndex !== null
                  ? Math.round((currentEntryIndex / entries.length) * 100)
                  : 0}
                %
              </span>
            </div>
            <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-200 ease-in-out"
                style={{
                  width: `${
                    currentEntryIndex !== null
                      ? (currentEntryIndex / entries.length) * 100
                      : 0
                  }%`,
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Entry Display Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
        {!currentEntry ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
            <Play className="h-12 w-12 mb-3 opacity-50" />
            <div className="text-sm mb-1">{t('sessionPlayer.title')}</div>
            <div className="text-xs">
              Press <kbd className="px-1.5 py-0.5 bg-secondary rounded text-xs">Space</kbd> to
              start playback
            </div>
            {entries.length > 0 && (
              <div className="text-xs mt-2">
                {entries.length} {t('sessionPlayer.entries')} available
              </div>
            )}
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-4">
            {/* Entry Header */}
            <div className="flex items-start gap-3">
              <Badge className={cn('gap-1 shrink-0', getPhaseBadgeColor(currentEntry.phase))}>
                <span className="text-xs uppercase">{currentEntry.phase}</span>
              </Badge>
              <div className="flex-1 min-w-0">
                <div className="text-xs text-muted-foreground mb-1">
                  {formatTimestamp(currentEntry.timestamp)}
                  {currentEntry.subphase && ` • ${currentEntry.subphase}`}
                  {currentEntry.subtask_id && ` • ${currentEntry.subtask_id}`}
                </div>
                <div className="text-sm">{currentEntry.content}</div>
              </div>
            </div>

            {/* Tool Information */}
            {currentEntry.tool_name && (
              <div className="pl-4 border-l-2 border-primary/30">
                <div className="text-xs text-muted-foreground mb-1">
                  {t('sessionPlayer.tool')}: {currentEntry.tool_name}
                </div>
                {currentEntry.tool_input && (
                  <pre className="text-xs bg-secondary/50 rounded p-2 overflow-x-auto">
                    {currentEntry.tool_input}
                  </pre>
                )}
              </div>
            )}

            {/* Decision Point Information */}
            {currentEntry.is_decision_point && (
              <div className="border border-primary/30 rounded-lg p-3 bg-primary/5">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="outline" className="gap-1">
                    <span className="text-xs">{t('sessionPlayer.decision')}</span>
                  </Badge>
                </div>
                {currentEntry.reasoning && (
                  <div className="mb-2">
                    <div className="text-xs font-medium mb-1">{t('sessionPlayer.reasoning')}:</div>
                    <div className="text-sm text-muted-foreground">{currentEntry.reasoning}</div>
                  </div>
                )}
                {currentEntry.alternatives && currentEntry.alternatives.length > 0 && (
                  <div className="mb-2">
                    <div className="text-xs font-medium mb-1">
                      {t('sessionPlayer.options')}:
                    </div>
                    <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                      {currentEntry.alternatives.map((alt, idx) => (
                        <li key={idx}>{alt}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {currentEntry.decision && (
                  <div>
                    <div className="text-xs font-medium mb-1">{t('sessionPlayer.chosen')}:</div>
                    <div className="text-sm">{currentEntry.decision}</div>
                  </div>
                )}
              </div>
            )}

            {/* Detail/Expanded Content */}
            {currentEntry.detail && (
              <details className="group">
                <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground list-none flex items-center gap-1">
                  <span className="transform group-open:rotate-90 transition-transform">▶</span>
                  Show details
                </summary>
                <pre className="mt-2 text-xs bg-secondary/50 rounded p-3 overflow-x-auto">
                  {currentEntry.detail}
                </pre>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
