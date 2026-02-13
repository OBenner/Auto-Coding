/**
 * Settings Page
 *
 * Main settings page with tabs for different configuration sections.
 * Includes General, API Configuration, Authentication, Appearance, and Advanced settings.
 * All UI text uses i18n translation keys following project standards.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GitHubConnect } from '../components/GitHubConnect';
import { useSettingsStore } from '../store/settings-store';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select } from '../components/ui/select';
import { Checkbox } from '../components/ui/checkbox';

type SettingsTab = 'general' | 'api' | 'authentication' | 'appearance' | 'advanced' | 'git';

export function Settings() {
  const { t } = useTranslation(['settings', 'common']);
  const { settings, updateSettings, resetSettings } = useSettingsStore();
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const [hasChanges, setHasChanges] = useState(false);

  const tabs: { id: SettingsTab; labelKey: string; icon: string }[] = [
    { id: 'general', labelKey: 'sections.general', icon: '⚙️' },
    { id: 'api', labelKey: 'sections.api', icon: '🔌' },
    { id: 'authentication', labelKey: 'sections.authentication', icon: '🔐' },
    { id: 'appearance', labelKey: 'sections.appearance', icon: '🎨' },
    { id: 'advanced', labelKey: 'sections.advanced', icon: '🔧' },
    { id: 'git', labelKey: 'sections.git', icon: '🔗' },
  ];

  const handleSettingChange = (key: keyof typeof settings, value: any) => {
    updateSettings({ [key]: value });
    setHasChanges(true);
  };

  const handleSave = () => {
    // Settings are auto-saved via persist middleware
    setHasChanges(false);
    // TODO: Show success toast
  };

  const handleReset = () => {
    if (confirm(t('settings:messages.resetConfirm'))) {
      resetSettings();
      setHasChanges(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{t('settings:title')}</h1>
              <p className="text-gray-600 mt-1">
                {t('settings:sections.general')}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {hasChanges && (
                <Button
                  variant="outline"
                  onClick={handleReset}
                  className="text-sm"
                >
                  {t('settings:buttons.reset')}
                </Button>
              )}
              <Button
                onClick={handleSave}
                disabled={!hasChanges}
                className="text-sm"
              >
                {t('settings:buttons.save')}
              </Button>
            </div>
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
                  <span className="text-sm">{t(`settings:${tab.labelKey}`)}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Main Content */}
          <div className="md:col-span-3">
            {/* General Settings */}
            {activeTab === 'general' && (
              <div className="space-y-6">
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    {t('settings:sections.general')}
                  </h2>
                  <p className="text-gray-600 text-sm mb-6">
                    {t('settings:general.languageDescription')}
                  </p>

                  {/* Language Selection */}
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="language">{t('settings:general.language')}</Label>
                      <Select
                        id="language"
                        value={settings.language}
                        onChange={(e) => handleSettingChange('language', e.target.value)}
                        className="mt-2"
                      >
                        <option value="en">{t('settings:general.languageOptions.english')}</option>
                        <option value="fr">{t('settings:general.languageOptions.french')}</option>
                      </Select>
                    </div>

                    {/* Theme Selection */}
                    <div>
                      <Label htmlFor="theme">{t('settings:general.theme')}</Label>
                      <Select
                        id="theme"
                        value={settings.theme}
                        onChange={(e) => handleSettingChange('theme', e.target.value as 'light' | 'dark' | 'system')}
                        className="mt-2"
                      >
                        <option value="light">{t('settings:general.themeOptions.light')}</option>
                        <option value="dark">{t('settings:general.themeOptions.dark')}</option>
                        <option value="system">{t('settings:general.themeOptions.system')}</option>
                      </Select>
                    </div>

                    {/* Notifications */}
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="notifications"
                        checked={settings.notifications}
                        onCheckedChange={(checked) =>
                          handleSettingChange('notifications', checked)
                        }
                      />
                      <Label htmlFor="notifications" className="cursor-pointer">
                        {t('settings:general.notifications')}
                      </Label>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* API Configuration */}
            {activeTab === 'api' && (
              <div className="space-y-6">
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    {t('settings:api.title')}
                  </h2>
                  <p className="text-gray-600 text-sm mb-6">
                    {t('settings:api.description')}
                  </p>

                  <div className="space-y-4">
                    {/* API URL */}
                    <div>
                      <Label htmlFor="apiUrl">{t('settings:api.apiUrl')}</Label>
                      <Input
                        id="apiUrl"
                        type="url"
                        value={settings.apiUrl}
                        onChange={(e) => handleSettingChange('apiUrl', e.target.value)}
                        placeholder={t('settings:api.apiUrlPlaceholder')}
                        className="mt-2"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {t('settings:api.apiUrlDescription')}
                      </p>
                    </div>

                    {/* WebSocket URL */}
                    <div>
                      <Label htmlFor="wsUrl">{t('settings:api.wsUrl')}</Label>
                      <Input
                        id="wsUrl"
                        type="text"
                        value={settings.wsUrl}
                        onChange={(e) => handleSettingChange('wsUrl', e.target.value)}
                        placeholder={t('settings:api.wsUrlPlaceholder')}
                        className="mt-2"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {t('settings:api.wsUrlDescription')}
                      </p>
                    </div>

                    {/* Request Timeout */}
                    <div>
                      <Label htmlFor="timeout">{t('settings:api.timeout')}</Label>
                      <Input
                        id="timeout"
                        type="number"
                        value={settings.timeout}
                        onChange={(e) => handleSettingChange('timeout', parseInt(e.target.value) || 30)}
                        min="5"
                        max="120"
                        className="mt-2"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {t('settings:api.timeoutDescription')}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Authentication */}
            {activeTab === 'authentication' && (
              <div className="space-y-6">
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    {t('settings:authentication.title')}
                  </h2>
                  <p className="text-gray-600 text-sm mb-6">
                    {t('settings:authentication.description')}
                  </p>

                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-700">
                      Authentication is managed through the web backend. Please use the
                      authentication flow in the main application.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Appearance */}
            {activeTab === 'appearance' && (
              <div className="space-y-6">
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    {t('settings:appearance.title')}
                  </h2>
                  <p className="text-gray-600 text-sm mb-6">
                    {t('settings:appearance.description')}
                  </p>

                  <div className="space-y-4">
                    {/* Compact Mode */}
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="compactMode"
                        checked={settings.compactMode}
                        onCheckedChange={(checked) =>
                          handleSettingChange('compactMode', checked)
                        }
                      />
                      <Label htmlFor="compactMode" className="cursor-pointer">
                        {t('settings:appearance.compactMode')}
                      </Label>
                    </div>
                    <p className="text-xs text-gray-500 ml-6">
                      {t('settings:appearance.compactModeDescription')}
                    </p>

                    {/* Animations */}
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="animations"
                        checked={settings.animations}
                        onCheckedChange={(checked) =>
                          handleSettingChange('animations', checked)
                        }
                      />
                      <Label htmlFor="animations" className="cursor-pointer">
                        {t('settings:appearance.animations')}
                      </Label>
                    </div>
                    <p className="text-xs text-gray-500 ml-6">
                      {t('settings:appearance.animationsDescription')}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Advanced Settings */}
            {activeTab === 'advanced' && (
              <div className="space-y-6">
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    {t('settings:advanced.title')}
                  </h2>
                  <p className="text-gray-600 text-sm mb-6">
                    {t('settings:advanced.description')}
                  </p>

                  <div className="space-y-4">
                    {/* Debug Mode */}
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="debugMode"
                        checked={settings.debugMode}
                        onCheckedChange={(checked) =>
                          handleSettingChange('debugMode', checked)
                        }
                      />
                      <Label htmlFor="debugMode" className="cursor-pointer">
                        {t('settings:advanced.debugMode')}
                      </Label>
                    </div>
                    <p className="text-xs text-gray-500 ml-6">
                      {t('settings:advanced.debugModeDescription')}
                    </p>

                    {/* Auto-Reconnect */}
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="autoReconnect"
                        checked={settings.autoReconnect}
                        onCheckedChange={(checked) =>
                          handleSettingChange('autoReconnect', checked)
                        }
                      />
                      <Label htmlFor="autoReconnect" className="cursor-pointer">
                        {t('settings:advanced.autoReconnect')}
                      </Label>
                    </div>
                    <p className="text-xs text-gray-500 ml-6">
                      {t('settings:advanced.autoReconnectDescription')}
                    </p>

                    {/* Cache Enabled */}
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="cacheEnabled"
                        checked={settings.cacheEnabled}
                        onCheckedChange={(checked) =>
                          handleSettingChange('cacheEnabled', checked)
                        }
                      />
                      <Label htmlFor="cacheEnabled" className="cursor-pointer">
                        {t('settings:advanced.cacheEnabled')}
                      </Label>
                    </div>
                    <p className="text-xs text-gray-500 ml-6">
                      {t('settings:advanced.cacheEnabledDescription')}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Git Connections */}
            {activeTab === 'git' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    {t('settings:sections.git')}
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
          </div>
        </div>
      </div>
    </div>
  );
}
