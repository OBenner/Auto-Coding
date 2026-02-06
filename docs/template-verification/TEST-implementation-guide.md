# Implementation Guide: Dark Mode Support

## Overview

This guide explains how dark mode was implemented in Auto Code, covering the theme system architecture, CSS variable strategy, and state management approach.

## Architecture

### High-Level Design

```
┌─────────────────┐
│  ThemeProvider  │ ← Manages global theme state
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼─────┐
│ CSS  │  │ Theme  │
│ Vars │  │ Toggle │
└──────┘  └────────┘
```

### Technology Choices

- **React Context API**: For global theme state without prop drilling
- **CSS Custom Properties**: Native browser support, no CSS-in-JS overhead
- **Local Storage**: Simple persistence without database

## Implementation Details

### Component: ThemeProvider

**Location**: `src/context/ThemeContext.tsx`

**Purpose**: Manages theme state and provides theme switching functionality

**Code**:
```typescript
import React, { createContext, useState, useEffect } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

export const ThemeContext = createContext<ThemeContextType>({
  theme: 'light',
  toggleTheme: () => {},
});

export const ThemeProvider: React.FC = ({ children }) => {
  const [theme, setTheme] = useState<Theme>('light');

  useEffect(() => {
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') as Theme;
    if (savedTheme) setTheme(savedTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
```

### Component: ThemeToggle

**Location**: `src/components/ThemeToggle.tsx`

**Purpose**: UI control for switching themes

**Code**:
```typescript
import React, { useContext } from 'react';
import { ThemeContext } from '../context/ThemeContext';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useContext(ThemeContext);

  return (
    <button
      onClick={toggleTheme}
      className="theme-toggle"
      aria-label="Toggle theme"
    >
      {theme === 'light' ? '🌙' : '☀️'}
    </button>
  );
};
```

### Styling: CSS Variables

**Location**: `src/styles/theme.css`

**Purpose**: Define color schemes for both themes

**Code**:
```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f5;
  --text-primary: #1a1a1a;
  --text-secondary: #666666;
  --border-color: #e0e0e0;
}

[data-theme='dark'] {
  --bg-primary: #1a1a1a;
  --bg-secondary: #2a2a2a;
  --text-primary: #e5e5e5;
  --text-secondary: #a0a0a0;
  --border-color: #404040;
}

/* Apply variables to components */
body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
  transition: background-color 0.3s ease, color 0.3s ease;
}
```

## Integration Points

### Internal Dependencies

- **App.tsx**: Wrap app with ThemeProvider
- **Settings.tsx**: Include ThemeToggle component
- **All CSS files**: Use CSS variables instead of hardcoded colors

### Integration Example

```typescript
// src/App.tsx
import { ThemeProvider } from './context/ThemeContext';

function App() {
  return (
    <ThemeProvider>
      <Router>
        <Layout />
      </Router>
    </ThemeProvider>
  );
}
```

## Testing

### Unit Tests

```bash
npm test -- ThemeContext.test.tsx
```

**Test Cases**:
- Theme defaults to 'light'
- toggleTheme switches between themes
- Theme persists to localStorage
- Theme loads from localStorage on mount

### Manual Testing

**Checklist**:
- [ ] Theme toggle appears in settings
- [ ] Clicking toggle changes theme immediately
- [ ] Theme persists after app restart
- [ ] All components render correctly in both themes
- [ ] Smooth transition animation between themes

## Common Pitfalls

### Pitfall 1: CSS Specificity Issues

**Problem**: Some components override theme variables with hardcoded colors

**Solution**: Audit all CSS for hardcoded color values, replace with variables

**Example**:
```css
/* ❌ Wrong */
.button {
  background: #ffffff;
}

/* ✅ Correct */
.button {
  background: var(--bg-primary);
}
```

### Pitfall 2: Flash of Wrong Theme

**Problem**: App briefly shows light theme before switching to saved dark theme

**Solution**: Check localStorage synchronously before first render

## Performance Considerations

- CSS variable changes trigger repaints but are optimized by browsers
- Use CSS transitions for smooth theme switching
- localStorage operations are synchronous but fast

## Debugging

### Check Current Theme

```javascript
// In browser console
localStorage.getItem('theme')
document.documentElement.getAttribute('data-theme')
```

### Inspect CSS Variables

```javascript
// Check computed values
getComputedStyle(document.documentElement)
  .getPropertyValue('--bg-primary')
```

## Related Documentation

- [React Context API](https://react.dev/reference/react/useContext)
- [CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/--*)
- [Local Storage API](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)
