/**
 * Settings Page
 *
 * Main settings page with tabs for different configuration sections.
 * Currently includes Git OAuth settings.
 */

import { useState } from 'react';
import { GitHubConnect } from '../components/GitHubConnect';

type SettingsTab = 'git' | 'account' | 'usage';

export function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('git');

  const tabs: { id: SettingsTab; label: string; icon: string }[] = [
    { id: 'git', label: 'Git Connections', icon: '🔗' },
    { id: 'account', label: 'Account', icon: '👤' },
    { id: 'usage', label: 'Usage & Billing', icon: '📊' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
              <p className="text-gray-600 mt-1">
                Manage your account and preferences
              </p>
            </div>
            <a
              href="/"
              className="text-blue-600 hover:text-blue-700 font-medium text-sm"
            >
              ← Back to Home
            </a>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Sidebar Navigation */}
          <div className="md:col-span-1">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <span className="text-xl">{tab.icon}</span>
                  <span className="text-sm">{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Main Content */}
          <div className="md:col-span-3">
            {activeTab === 'git' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    Git Connections
                  </h2>
                  <p className="text-gray-600 text-sm mb-6">
                    Connect your GitHub or GitLab account to access repositories
                  </p>
                </div>

                {/* GitHub Connection */}
                <GitHubConnect />

                {/* GitLab Connection (Placeholder) */}
                <div className="bg-white rounded-lg shadow-md p-6 opacity-60">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-orange-500 rounded-lg flex items-center justify-center">
                      <svg className="w-7 h-7 text-white" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M23.955 13.587l-1.342-4.135-2.664-8.189a.455.455 0 00-.867 0L16.418 9.45H7.582L4.918 1.263a.455.455 0 00-.867 0L1.387 9.452.045 13.587a.924.924 0 00.331 1.023l11.359 8.251a.455.455 0 00.53 0l11.359-8.251a.924.924 0 00.331-1.023z"/>
                      </svg>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900">GitLab</h3>
                      <p className="text-sm text-gray-600">
                        GitLab integration coming soon
                      </p>
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                      <span className="w-2 h-2 rounded-full bg-gray-400"></span>
                      Coming Soon
                    </span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'account' && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Account Settings
                </h2>
                <p className="text-gray-600">
                  Account settings coming soon...
                </p>
              </div>
            )}

            {activeTab === 'usage' && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Usage & Billing
                </h2>
                <p className="text-gray-600">
                  Usage and billing information coming soon...
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
