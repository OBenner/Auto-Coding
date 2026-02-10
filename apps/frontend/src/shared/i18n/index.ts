import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { debugWarn } from '../utils/debug-logger';

// Import English translation resources
import enCommon from './locales/en/common.json';
import enNavigation from './locales/en/navigation.json';
import enSettings from './locales/en/settings.json';
import enTasks from './locales/en/tasks.json';
import enWelcome from './locales/en/welcome.json';
import enOnboarding from './locales/en/onboarding.json';
import enDialogs from './locales/en/dialogs.json';
import enGitlab from './locales/en/gitlab.json';
import enTaskReview from './locales/en/taskReview.json';
import enTerminal from './locales/en/terminal.json';
import enErrors from './locales/en/errors.json';
import enPlugins from './locales/en/plugins.json';
import enTemplates from './locales/en/templates.json';
import enAgent from './locales/en/agent.json';
import enChangelog from './locales/en/changelog.json';
import enContext from './locales/en/context.json';

// Import French translation resources
import frCommon from './locales/fr/common.json';
import frNavigation from './locales/fr/navigation.json';
import frSettings from './locales/fr/settings.json';
import frTasks from './locales/fr/tasks.json';
import frWelcome from './locales/fr/welcome.json';
import frOnboarding from './locales/fr/onboarding.json';
import frDialogs from './locales/fr/dialogs.json';
import frGitlab from './locales/fr/gitlab.json';
import frTaskReview from './locales/fr/taskReview.json';
import frTerminal from './locales/fr/terminal.json';
import frErrors from './locales/fr/errors.json';
import frPlugins from './locales/fr/plugins.json';
import frTemplates from './locales/fr/templates.json';
import frAgent from './locales/fr/agent.json';
import frChangelog from './locales/fr/changelog.json';
import frContext from './locales/fr/context.json';

// TODO: Spanish and German translations are incomplete (2000+ missing keys each)
// Uncomment imports and add to resources when translations are complete
// // Import Spanish translation resources
// import esCommon from './locales/es/common.json';
// import esNavigation from './locales/es/navigation.json';
// import esSettings from './locales/es/settings.json';
// import esTasks from './locales/es/tasks.json';
// import esWelcome from './locales/es/welcome.json';
// import esOnboarding from './locales/es/onboarding.json';
// import esDialogs from './locales/es/dialogs.json';
// import esGitlab from './locales/es/gitlab.json';
// import esTaskReview from './locales/es/taskReview.json';
// import esTerminal from './locales/es/terminal.json';
// import esErrors from './locales/es/errors.json';
// import esPlugins from './locales/es/plugins.json';
// import esTemplates from './locales/es/templates.json';
//
// // Import German translation resources
// import deCommon from './locales/de/common.json';
// import deNavigation from './locales/de/navigation.json';
// import deSettings from './locales/de/settings.json';
// import deTasks from './locales/de/tasks.json';
// import deWelcome from './locales/de/welcome.json';
// import deOnboarding from './locales/de/onboarding.json';
// import deDialogs from './locales/de/dialogs.json';
// import deGitlab from './locales/de/gitlab.json';
// import deTaskReview from './locales/de/taskReview.json';
// import deTerminal from './locales/de/terminal.json';
// import deErrors from './locales/de/errors.json';
// import dePlugins from './locales/de/plugins.json';
// import deTemplates from './locales/de/templates.json';

export const defaultNS = 'common';

export const resources = {
  en: {
    common: enCommon,
    navigation: enNavigation,
    settings: enSettings,
    tasks: enTasks,
    welcome: enWelcome,
    onboarding: enOnboarding,
    dialogs: enDialogs,
    gitlab: enGitlab,
    taskReview: enTaskReview,
    terminal: enTerminal,
    errors: enErrors,
    plugins: enPlugins,
    templates: enTemplates,
    agent: enAgent,
    changelog: enChangelog,
    context: enContext
  },
  fr: {
    common: frCommon,
    navigation: frNavigation,
    settings: frSettings,
    tasks: frTasks,
    welcome: frWelcome,
    onboarding: frOnboarding,
    dialogs: frDialogs,
    gitlab: frGitlab,
    taskReview: frTaskReview,
    terminal: frTerminal,
    errors: frErrors,
    plugins: frPlugins,
    templates: frTemplates,
    agent: frAgent,
    changelog: frChangelog,
    context: frContext
  }
  // TODO: Uncomment when Spanish and German translations are complete
  // es: {
  //   common: esCommon,
  //   navigation: esNavigation,
  //   settings: esSettings,
  //   tasks: esTasks,
  //   welcome: esWelcome,
  //   onboarding: esOnboarding,
  //   dialogs: esDialogs,
  //   gitlab: esGitlab,
  //   taskReview: esTaskReview,
  //   terminal: esTerminal,
  //   errors: esErrors,
  //   plugins: esPlugins,
  //   templates: esTemplates
  // },
  // de: {
  //   common: deCommon,
  //   navigation: deNavigation,
  //   settings: deSettings,
  //   tasks: deTasks,
  //   welcome: deWelcome,
  //   onboarding: deOnboarding,
  //   dialogs: deDialogs,
  //   gitlab: deGitlab,
  //   taskReview: deTaskReview,
  //   terminal: deTerminal,
  //   errors: deErrors,
  //   plugins: dePlugins,
  //   templates: deTemplates
  // }
} as const;

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en', // Default language (will be overridden by settings)
    fallbackLng: 'en',
    defaultNS,
    ns: ['common', 'navigation', 'settings', 'tasks', 'welcome', 'onboarding', 'dialogs', 'gitlab', 'taskReview', 'terminal', 'errors', 'plugins', 'templates', 'agent', 'changelog', 'context'],
    interpolation: {
      escapeValue: false // React already escapes values
    },
    react: {
      useSuspense: false // Disable suspense for Electron compatibility
    },
    missingKeyHandler: (lngs: string[], ns: string, key: string, fallbackValue: string) => {
      debugWarn(`[i18n] Missing translation key: "${ns}:${key}" for languages: ${lngs.join(', ')}`);
    }
  });

export default i18n;
