/**
 * GitHub OAuth Connection Component
 *
 * Provides UI for connecting GitHub account via OAuth flow.
 * Redirects to backend OAuth endpoint for authorization.
 */

import { useState, useEffect } from 'react';
import { Button } from './ui/button';

interface GitHubUser {
  id: number;
  login: string;
  email: string | null;
  name: string | null;
}

interface ConnectionStatus {
  connected: boolean;
  provider?: string;
  user?: GitHubUser;
}

export function GitHubConnect() {
  const [status, setStatus] = useState<ConnectionStatus>({ connected: false });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Check if we just returned from OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const callbackStatus = urlParams.get('status');
    const callbackError = urlParams.get('error');

    if (callbackStatus === 'success') {
      setSuccess('GitHub account connected successfully!');
      setStatus({ connected: true });
      // Clean up URL parameters
      window.history.replaceState({}, '', window.location.pathname);
    } else if (callbackError) {
      setError(decodeURIComponent(callbackError));
      // Clean up URL parameters
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const handleConnect = () => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    // Redirect to backend OAuth endpoint
    // The backend will handle the OAuth flow and redirect back to this page
    const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    window.location.href = `${backendUrl}/api/git/github/authorize`;
  };

  const handleDisconnect = () => {
    // TODO: Implement disconnect functionality
    setStatus({ connected: false });
    setSuccess('GitHub account disconnected');
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <div className="w-12 h-12 bg-gray-900 rounded-lg flex items-center justify-center">
          <svg className="w-7 h-7 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
          </svg>
        </div>
        <div className="flex-1">
          <h2 className="text-xl font-semibold text-gray-900">GitHub</h2>
          <p className="text-sm text-gray-600">
            Connect your GitHub account to access repositories
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
            status.connected
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-700'
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              status.connected ? 'bg-green-500' : 'bg-gray-400'
            }`}></span>
            {status.connected ? 'Connected' : 'Not Connected'}
          </span>
        </div>
      </div>

      {/* Success Message */}
      {success && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-600">{success}</p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Connection Status */}
      {status.connected && status.user ? (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center">
              <span className="text-sm font-semibold text-gray-700">
                {status.user.login.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                {status.user.name || status.user.login}
              </p>
              <p className="text-xs text-gray-600">
                @{status.user.login}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="mb-6">
          <p className="text-sm text-gray-600">
            Connecting your GitHub account allows Auto Claude to access your repositories and create builds.
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        {status.connected ? (
          <>
            <Button
              variant="outline"
              onClick={handleDisconnect}
              className="flex-1"
            >
              Disconnect
            </Button>
            <Button
              onClick={() => setSuccess('Connection refreshed!')}
              className="flex-1"
            >
              Refresh Connection
            </Button>
          </>
        ) : (
          <Button
            onClick={handleConnect}
            disabled={isLoading}
            className="w-full"
          >
            {isLoading ? 'Connecting...' : 'Connect GitHub Account'}
          </Button>
        )}
      </div>

      {/* Permissions Info */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h3 className="text-sm font-medium text-gray-900 mb-2">
          Requested Permissions
        </h3>
        <ul className="space-y-1.5">
          <li className="flex items-center gap-2 text-xs text-gray-600">
            <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Read repository information and metadata
          </li>
          <li className="flex items-center gap-2 text-xs text-gray-600">
            <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Read and write repository contents
          </li>
          <li className="flex items-center gap-2 text-xs text-gray-600">
            <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Create and manage pull requests
          </li>
        </ul>
      </div>
    </div>
  );
}
