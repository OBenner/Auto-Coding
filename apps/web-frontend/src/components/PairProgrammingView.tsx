/**
 * PairProgrammingView Component
 *
 * Interactive panel for AI pair programming mode.
 * Displays real-time suggestions, session controls, and collaboration interface.
 */

import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Play,
  Square,
  RefreshCw,
  Code2,
  MessageSquare,
  Lightbulb,
  Settings,
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { cn } from '../lib/utils';

interface PairProgrammingViewProps {
  className?: string;
}

type SessionStatus = 'idle' | 'active' | 'paused' | 'error';

export function PairProgrammingView({ className }: PairProgrammingViewProps) {
  const { t } = useTranslation(['common']);
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>('idle');
  const [isStarting, setIsStarting] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  /**
   * Start a new pair programming session
   */
  const handleStartSession = useCallback(async () => {
    try {
      setIsStarting(true);
      // TODO: Call API to start pair programming session
      // const response = await apiClient.startPairSession();

      // Simulate session start for now
      await new Promise(resolve => setTimeout(resolve, 500));
      setSessionStatus('active');
      setSuggestions([
        'Ready to pair program!',
        'Start editing files to receive AI suggestions.',
      ]);
    } catch (error) {
      setSessionStatus('error');
      console.error('Failed to start pair programming session:', error);
    } finally {
      setIsStarting(false);
    }
  }, []);

  /**
   * Stop the current pair programming session
   */
  const handleStopSession = useCallback(async () => {
    try {
      // TODO: Call API to stop pair programming session
      // await apiClient.stopPairSession();

      setSessionStatus('idle');
      setSuggestions([]);
    } catch (error) {
      console.error('Failed to stop pair programming session:', error);
    }
  }, []);

  /**
   * Refresh suggestions manually
   */
  const handleRefresh = useCallback(() => {
    // TODO: Implement refresh logic
    console.log('Refreshing suggestions...');
  }, []);

  const isActive = sessionStatus === 'active';
  const isIdle = sessionStatus === 'idle';

  return (
    <div className={cn('min-h-screen bg-gray-50', className)}>
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl flex items-center justify-center">
              <Code2 className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                AI Pair Programming
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Real-time AI collaboration and suggestions
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={handleRefresh}
              disabled={!isActive}
              variant="outline"
              size="icon"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button
              onClick={handleRefresh}
              disabled={!isActive}
              variant="outline"
              size="icon"
            >
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="grid gap-6">
          {/* Session Control Card */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Session Status</p>
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-sm',
                        isActive && 'bg-green-50 text-green-700 border-green-200',
                        isIdle && 'bg-gray-50 text-gray-700 border-gray-200',
                        sessionStatus === 'error' && 'bg-red-50 text-red-700 border-red-200'
                      )}
                    >
                      {sessionStatus === 'active' && 'Active'}
                      {sessionStatus === 'idle' && 'Idle'}
                      {sessionStatus === 'paused' && 'Paused'}
                      {sessionStatus === 'error' && 'Error'}
                    </Badge>
                  </div>
                  {isActive && (
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                      <span>Listening for changes...</span>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {isIdle && (
                    <Button
                      onClick={handleStartSession}
                      disabled={isStarting}
                      className="gap-2"
                    >
                      <Play className="h-4 w-4" />
                      {isStarting ? 'Starting...' : 'Start Session'}
                    </Button>
                  )}
                  {isActive && (
                    <Button
                      onClick={handleStopSession}
                      variant="destructive"
                      className="gap-2"
                    >
                      <Square className="h-4 w-4" />
                      Stop Session
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* AI Suggestions Panel */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-2 mb-4">
                  <Lightbulb className="h-5 w-5 text-yellow-500" />
                  <h3 className="text-lg font-semibold">AI Suggestions</h3>
                </div>
                <Separator className="mb-4" />
                <ScrollArea className="h-[400px] w-full">
                  {suggestions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center p-6">
                      <Lightbulb className="h-12 w-12 text-gray-300 mb-3" />
                      <p className="text-gray-500 text-sm">
                        {isIdle
                          ? 'Start a session to receive AI suggestions'
                          : 'No suggestions yet. Start editing to see recommendations.'}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {suggestions.map((suggestion, index) => (
                        <div
                          key={index}
                          className="p-3 bg-blue-50 border border-blue-100 rounded-lg"
                        >
                          <p className="text-sm text-gray-700">{suggestion}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Conversation Panel */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-2 mb-4">
                  <MessageSquare className="h-5 w-5 text-blue-500" />
                  <h3 className="text-lg font-semibold">Conversation</h3>
                </div>
                <Separator className="mb-4" />
                <ScrollArea className="h-[400px] w-full">
                  <div className="flex flex-col items-center justify-center h-full text-center p-6">
                    <MessageSquare className="h-12 w-12 text-gray-300 mb-3" />
                    <p className="text-gray-500 text-sm">
                      Chat with AI about your code
                    </p>
                    <p className="text-gray-400 text-xs mt-2">
                      Coming soon: Voice and text interaction
                    </p>
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Features Info Card */}
          <Card>
            <CardContent className="pt-6">
              <h3 className="text-lg font-semibold mb-4">Features</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-purple-50 rounded-lg border border-purple-100">
                  <div className="text-2xl mb-2">💡</div>
                  <h4 className="font-semibold text-gray-900 mb-1">
                    Real-time Suggestions
                  </h4>
                  <p className="text-sm text-gray-600">
                    Get AI suggestions as you code
                  </p>
                </div>
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <div className="text-2xl mb-2">🗣️</div>
                  <h4 className="font-semibold text-gray-900 mb-1">
                    Voice Interaction
                  </h4>
                  <p className="text-sm text-gray-600">
                    Hands-free pair programming
                  </p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg border border-green-100">
                  <div className="text-2xl mb-2">🔄</div>
                  <h4 className="font-semibold text-gray-900 mb-1">
                    Seamless Switching
                  </h4>
                  <p className="text-sm text-gray-600">
                    Toggle between autonomous and pair modes
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
