import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Import English translation resources
import enCommon from './locales/en/common.json';
import enNavigation from './locales/en/navigation.json';
import enSettings from './locales/en/settings.json';
import enSecurity from './locales/en/security.json';
import enTasks from './locales/en/tasks.json';
import enWelcome from './locales/en/welcome.json';
import enOnboarding from './locales/en/onboarding.json';
import enDialogs from './locales/en/dialogs.json';
import enGithub from './locales/en/github.json';
import enGitlab from './locales/en/gitlab.json';
import enTaskReview from './locales/en/taskReview.json';
import enTerminal from './locales/en/terminal.json';
import enErrors from './locales/en/errors.json';
import enAnalytics from './locales/en/analytics.json';
import enModelUsage from './locales/en/model-usage.json';
import enCodeReview from './locales/en/codeReview.json';
import enQuality from './locales/en/quality.json';
import enAgentInspector from './locales/en/agent-inspector.json';
import enTimeline from './locales/en/timeline.json';
import enKanban from './locales/en/kanban.json';
import enChangelog from './locales/en/changelog.json';

// Import French translation resources
import frCommon from './locales/fr/common.json';
import frNavigation from './locales/fr/navigation.json';
import frSettings from './locales/fr/settings.json';
import frSecurity from './locales/fr/security.json';
import frTasks from './locales/fr/tasks.json';
import frWelcome from './locales/fr/welcome.json';
import frOnboarding from './locales/fr/onboarding.json';
import frDialogs from './locales/fr/dialogs.json';
import frGithub from './locales/fr/github.json';
import frGitlab from './locales/fr/gitlab.json';
import frTaskReview from './locales/fr/taskReview.json';
import frTerminal from './locales/fr/terminal.json';
import frErrors from './locales/fr/errors.json';
import frAnalytics from './locales/fr/analytics.json';
import frModelUsage from './locales/fr/model-usage.json';
import frCodeReview from './locales/fr/codeReview.json';
import frQuality from './locales/fr/quality.json';
import frAgentInspector from './locales/fr/agent-inspector.json';
import frTimeline from './locales/fr/timeline.json';
import frKanban from './locales/fr/kanban.json';
import frChangelog from './locales/fr/changelog.json';

export const defaultNS = 'common';

export const resources = {
  en: {
    common: enCommon,
    navigation: enNavigation,
    settings: enSettings,
    security: enSecurity,
    tasks: enTasks,
    welcome: enWelcome,
    onboarding: enOnboarding,
    dialogs: enDialogs,
    github: enGithub,
    gitlab: enGitlab,
    taskReview: enTaskReview,
    terminal: enTerminal,
    errors: enErrors,
    analytics: enAnalytics,
    'model-usage': enModelUsage,
    codeReview: enCodeReview,
    quality: enQuality,
    'agent-inspector': enAgentInspector,
    timeline: enTimeline,
    kanban: enKanban,
    changelog: enChangelog
  },
  fr: {
    common: frCommon,
    navigation: frNavigation,
    settings: frSettings,
    security: frSecurity,
    tasks: frTasks,
    welcome: frWelcome,
    onboarding: frOnboarding,
    dialogs: frDialogs,
    github: frGithub,
    gitlab: frGitlab,
    taskReview: frTaskReview,
    terminal: frTerminal,
    errors: frErrors,
    analytics: frAnalytics,
    'model-usage': frModelUsage,
    codeReview: frCodeReview,
    quality: frQuality,
    'agent-inspector': frAgentInspector,
    timeline: frTimeline,
    kanban: frKanban,
    changelog: frChangelog
  }
} as const;

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en', // Default language (will be overridden by settings)
    fallbackLng: 'en',
    defaultNS,
    ns: ['common', 'navigation', 'settings', 'security', 'tasks', 'welcome', 'onboarding', 'dialogs', 'github', 'gitlab', 'taskReview', 'terminal', 'errors', 'analytics', 'model-usage', 'codeReview', 'quality', 'agent-inspector', 'timeline', 'kanban', 'changelog'],
    interpolation: {
      escapeValue: false // React already escapes values
    },
    react: {
      useSuspense: false // Disable suspense for Electron compatibility
    }
  });

export default i18n;
