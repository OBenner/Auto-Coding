# Adding Translations and New Languages

This guide explains how to add translations for new user-facing text and how to add entirely new languages to the Auto Code frontend.

## Table of Contents

- [Overview](#overview)
- [Internationalization architecture](#internationalization-architecture)
- [Adding translation keys](#adding-translation-keys)
- [Adding a new language](#adding-a-new-language)
- [Translation best practices](#translation-best-practices)
- [Testing translations](#testing-translations)
- [Common pitfalls](#common-pitfalls)

## Overview

Auto Code uses **react-i18next** for internationalization (i18n). All user-facing text in the frontend must use translation keys, not hardcoded strings.

**Current supported languages:**
- English (en) - default, fallback language
- French (fr)

**Translation namespaces:**
- `common.json` - Shared labels, buttons, common terms
- `navigation.json` - Sidebar navigation items, sections
- `settings.json` - Settings page content
- `dialogs.json` - Dialog boxes and modals
- `tasks.json` - Task/spec related content
- `errors.json` - Error messages with structured error information
- `onboarding.json` - Onboarding wizard content
- `welcome.json` - Welcome screen content
- `agent.json` - Agent-related UI text
- `changelog.json` - Changelog and version history
- `context.json` - Context management UI
- `gitlab.json` - GitLab integration text
- `plugins.json` - Plugin management
- `taskReview.json` - Task review features
- `templates.json` - Template management
- `terminal.json` - Terminal UI text

## Internationalization architecture

### File structure

Translation files are organized by language and namespace:

```
apps/frontend/src/shared/i18n/
├── index.ts              # i18n configuration
├── formatters.ts         # Custom formatters (dates, numbers, etc.)
└── locales/
    ├── en/              # English translations
    │   ├── common.json
    │   ├── navigation.json
    │   ├── settings.json
    │   └── ...
    └── fr/              # French translations
        ├── common.json
        ├── navigation.json
        ├── settings.json
        └── ...
```

### Configuration

The main i18n configuration is in `apps/frontend/src/shared/i18n/index.ts`:

```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Import translations for each language
import enCommon from './locales/en/common.json';
import enNavigation from './locales/en/navigation.json';
// ... more imports

import frCommon from './locales/fr/common.json';
import frNavigation from './locales/fr/navigation.json';
// ... more imports

export const resources = {
  en: {
    common: enCommon,
    navigation: enNavigation,
    // ... all namespaces for English
  },
  fr: {
    common: frCommon,
    navigation: frNavigation,
    // ... all namespaces for French
  }
} as const;

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en',              // Default language
    fallbackLng: 'en',      // Fallback to English if translation missing
    defaultNS: 'common',    // Default namespace
    ns: ['common', 'navigation', 'settings', 'tasks', ...],
    interpolation: {
      escapeValue: false    // React already escapes values
    },
    react: {
      useSuspense: false    // Disable suspense for Electron compatibility
    }
  });
```

## Adding translation keys

### When to add translation keys

Add translation keys for ALL user-facing text:

**✅ Needs translation:**
- Button labels: "Save", "Cancel", "Submit"
- Error messages: "Failed to load data"
- Form labels and placeholders
- Navigation items
- Success/error toasts
- Dialog titles and content
- Tooltips and aria-labels

**❌ Does NOT need translation:**
- Internal logs
- API endpoint paths
- Technical constants
- Variable names
- Comments

### Step 1: Add keys to English translation file

Add the key to the appropriate namespace file in `locales/en/`:

```json
{
  "buttons": {
    "save": "Save",
    "cancel": "Cancel"
  },
  "myNewFeature": {
    "title": "My New Feature",
    "description": "This feature does something amazing"
  }
}
```

**Key naming conventions:**
- Use `camelCase` for keys
- Group related keys under nested objects
- Use descriptive names that indicate context
- Include the namespace in the key path when using it: `namespace:section.key`

### Step 2: Add keys to all other language files

Add the same key structure to ALL language files (at minimum: English and French):

**English (`locales/en/common.json`):**
```json
{
  "myFeature": {
    "saveButton": "Save Changes",
    "cancelButton": "Cancel"
  }
}
```

**French (`locales/fr/common.json`):**
```json
{
  "myFeature": {
    "saveButton": "Enregistrer les modifications",
    "cancelButton": "Annuler"
  }
}
```

**⚠️ CRITICAL:** The key structure (nested objects, key names) must be IDENTICAL across all language files. Only the translated text values differ.

### Step 3: Use the translation key in components

Import the `useTranslation` hook and use the translation key:

```typescript
import { useTranslation } from 'react-i18next';

export function MyComponent() {
  const { t } = useTranslation(['common', 'navigation']);

  return (
    <div>
      <h1>{t('common:myFeature.title')}</h1>
      <p>{t('common:myFeature.description')}</p>
      <button>{t('common:buttons.save')}</button>
      <button>{t('common:buttons.cancel')}</button>
    </div>
  );
}
```

**Usage patterns:**
- Specify namespaces in `useTranslation()`: `useTranslation(['common', 'navigation'])`
- Use `namespace:section.key` format for keys
- Use the default namespace if you specified `defaultNS` in `useTranslation()`

### Step 4: Handle interpolation (dynamic values)

For text with dynamic values, use interpolation:

**Translation file:**
```json
{
  "errors": {
    "loadFailed": "Failed to load {{resource}}: {{error}}"
  }
}
```

**Component usage:**
```typescript
const { t } = useTranslation(['errors']);

const errorMessage = t('errors:loadFailed', {
  resource: 'user data',
  error: 'Network timeout'
});
// Result: "Failed to load user data: Network timeout"
```

**Interpolation guidelines:**
- Use `{{variableName}}` syntax in translation files
- Pass variables as an object in the second argument
- Use descriptive variable names (not `var1`, `var2`)
- For pluralization, use `_plural` suffix keys (react-i18next handles this automatically)

### Step 5: Handle pluralization

For text that changes based on count, use pluralization:

**Translation file:**
```json
{
  "items": {
    "count": "{{count}} item",
    "count_plural": "{{count}} items"
  }
}
```

**Component usage:**
```typescript
const { t } = useTranslation(['items']);

t('items:count', { count: 1 });  // "1 item"
t('items:count', { count: 5 });  // "5 items"
```

## Adding a new language

### Prerequisites

Before adding a new language, ensure you have:
- Native or fluent speaker of the target language
- Understanding of the UI context for accurate translations
- Time to translate all namespaces (15+ JSON files)

### Step 1: Create language directory

Create a new directory under `locales/` using the [ISO 639-1 language code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes):

```bash
cd apps/frontend/src/shared/i18n/locales
mkdir es  # For Spanish (es)
mkdir de  # For German (de)
mkdir ja  # For Japanese (ja)
```

### Step 2: Create namespace files

Create ALL namespace JSON files in the new language directory:

```bash
cd apps/frontend/src/shared/i18n/locales/es

# Copy English as a template
cp ../en/*.json .

# Or create files manually
touch common.json
touch navigation.json
touch settings.json
touch tasks.json
# ... create all 15 namespace files
```

**Required namespace files:**
- `common.json`
- `navigation.json`
- `settings.json`
- `tasks.json`
- `welcome.json`
- `onboarding.json`
- `dialogs.json`
- `errors.json`
- `agent.json`
- `changelog.json`
- `context.json`
- `gitlab.json`
- `plugins.json`
- `taskReview.json`
- `templates.json`
- `terminal.json`

### Step 3: Translate all namespaces

Translate each namespace file from English to the target language:

**English (`locales/en/common.json`):**
```json
{
  "buttons": {
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete"
  }
}
```

**Spanish (`locales/es/common.json`):**
```json
{
  "buttons": {
    "save": "Guardar",
    "cancel": "Cancelar",
    "delete": "Eliminar"
  }
}
```

**Translation guidelines:**
- Keep the exact same JSON structure (keys, nesting)
- Translate only the values, not the keys
- Preserve interpolation placeholders: `{{variable}}`
- Preserve pluralization keys: `_plural`
- Maintain consistent tone and terminology
- Test UI context: some translations may be shorter/longer than English
- Use formal or informal tone consistently with the language's conventions

### Step 4: Import translations in index.ts

Add imports for the new language in `apps/frontend/src/shared/i18n/index.ts`:

```typescript
// Import Spanish translation resources
import esCommon from './locales/es/common.json';
import esNavigation from './locales/es/navigation.json';
import esSettings from './locales/es/settings.json';
import esTasks from './locales/es/tasks.json';
// ... import all 15 namespace files
```

### Step 5: Add language to resources object

Add the new language to the `resources` object in `index.ts`:

```typescript
export const resources = {
  en: {
    common: enCommon,
    navigation: enNavigation,
    // ... all English namespaces
  },
  fr: {
    common: frCommon,
    navigation: frNavigation,
    // ... all French namespaces
  },
  es: {  // NEW: Spanish
    common: esCommon,
    navigation: esNavigation,
    settings: esSettings,
    tasks: esTasks,
    // ... all Spanish namespaces
  }
} as const;
```

### Step 6: Add language to namespace list

Add the new language code to the `ns` array in `index.ts`:

```typescript
i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en',
    fallbackLng: 'en',
    defaultNS: 'common',
    ns: [
      'common',
      'navigation',
      'settings',
      'tasks',
      'welcome',
      'onboarding',
      'dialogs',
      'errors',
      'agent',
      'changelog',
      'context',
      'gitlab',
      'plugins',
      'taskReview',
      'templates',
      'terminal'
      // No need to add language codes here - this lists namespaces
    ],
    // ... rest of config
  });
```

### Step 7: Test the new language

Start the application and switch to the new language:

```bash
cd apps/frontend
npm run dev
```

Use the **Settings** page to change the language and verify:
- All UI text is translated
- No English fallback text appears (unless intended)
- No missing translation errors in the console
- Text fits properly in UI elements (no truncation or overflow)

## Translation best practices

### Consistency

- Use consistent terminology across namespaces
- Create a glossary for domain-specific terms
- Reuse existing translation keys when possible
- Document new terms in team wiki/glossary

### Context

- Consider the UI context when translating
- Buttons should be short and action-oriented
- Error messages should be clear and helpful
- Tooltips should provide additional context, not repeat labels

### Interpolation

- Use meaningful variable names: `{{userName}}` not `{{var1}}`
- Provide context in variable names: `{{maxFileSize}}` not `{{limit}}`
- Keep interpolated values outside the translated string when possible

**Good:**
```json
{
  "fileSizeError": "File size ({{size}}) exceeds maximum ({{maxSize}})"
}
```

**Avoid:**
```json
{
  "fileSizeError": "{{value}} is too big"
}
```

### Pluralization

- Use `_plural` suffix for plural forms
- Some languages have multiple plural forms (e.g., Slavic languages)
- Test pluralization with different count values

### Accessibility

- Translate aria-labels for screen readers
- Provide context for icon-only buttons
- Keep translations concise for mobile UI
- Test with screen reader tools

## Testing translations

### Manual testing

1. **Switch languages in Settings**
   - Navigate to Settings → Language
   - Select each supported language
   - Verify all UI text updates correctly

2. **Check for missing translations**
   - Open browser DevTools Console
   - Look for missing translation warnings
   - Fix any keys that show English fallback in non-English languages

3. **Test text overflow**
   - Switch to each language
   - Navigate through all major UI sections
   - Check for truncated text or broken layouts
   - Adjust UI if needed (some languages require 30% more space)

### Automated testing

Consider adding automated tests for critical translations:

```typescript
import { renderHook } from '@testing-library/react';
import { useTranslation } from 'react-i18next';

describe('Translation tests', () => {
  test('all required keys exist in English', () => {
    const { result } = renderHook(() => useTranslation(['common']));
    expect(result.current.t('common:buttons.save')).toBe('Save');
  });

  test('translation works for all languages', () => {
    const languages = ['en', 'fr', 'es'];
    languages.forEach(lang => {
      // Change language and test key
      i18n.changeLanguage(lang);
      const { result } = renderHook(() => useTranslation(['common']));
      expect(result.current.exists('common:buttons.save')).toBe(true);
    });
  });
});
```

## Common pitfalls

### ❌ Hardcoded strings in components

**Wrong:**
```typescript
<button>Submit</button>
```

**Correct:**
```typescript
<button>{t('common:buttons.submit')}</button>
```

### ❌ Missing translation in one language

**Wrong:**
```json
// English
{ "save": "Save" }

// French (missing key)
{ }
```

**Correct:**
```json
// English
{ "save": "Save" }

// French
{ "save": "Enregistrer" }
```

### ❌ Inconsistent key structure

**Wrong:**
```json
// English
{ "buttons": { "save": "Save" } }

// French (different structure)
{ "saveButton": "Enregistrer" }
```

**Correct:**
```json
// English
{ "buttons": { "save": "Save" } }

// French (same structure)
{ "buttons": { "save": "Enregistrer" } }
```

### ❌ Forgetting to import new namespace

**Wrong:**
```typescript
// Added keys to errors.json but didn't import namespace
const { t } = useTranslation(['common']);
t('errors:loadFailed');  // Will show key name, not translation
```

**Correct:**
```typescript
const { t } = useTranslation(['common', 'errors']);
t('errors:loadFailed');  // Works correctly
```

### ❌ Breaking interpolation syntax

**Wrong:**
```json
{ "greeting": "Hello {name}" }  // Must use {{name}}
```

**Correct:**
```json
{ "greeting": "Hello {{name}}" }
```

## References

- [react-i18next documentation](https://react.i18next.com/)
- [i18next documentation](https://www.i18next.com/)
- [CLAUDE.md](../CLAUDE.md) - Frontend i18n guidelines
- [STYLE_GUIDE.md](STYLE_GUIDE.md) - Documentation style conventions

---

**Need help?** Open an issue or consult the team for translation assistance.
