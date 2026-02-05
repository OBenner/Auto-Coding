# Dark Mode Support

**Status**: Implemented
**Version**: 2.9.0
**Last Updated**: 2026-02-05

## Overview

Dark mode is a theme option that changes the Auto Claude interface from light backgrounds to dark backgrounds. This feature helps reduce eye strain during extended use and provides a better experience in low-light environments.

## Key Benefits

| Benefit | Description |
|---------|-------------|
| **Reduced Eye Strain** | Dark backgrounds reduce screen brightness, making it easier on the eyes during long coding sessions |
| **Better Night Experience** | Ideal for late-night work without harsh bright screens |
| **Energy Savings** | On OLED/AMOLED screens, dark mode can reduce battery consumption |
| **Modern UI Standard** | Matches user expectations for modern developer tools |

## How It Works

### Architecture

Dark mode is implemented using CSS custom properties (CSS variables) and a theme context provider:

1. **Theme Provider**: React context manages current theme state
2. **CSS Variables**: Color values defined as variables that change based on theme
3. **Local Storage**: Theme preference persisted across sessions
4. **Toggle Component**: Settings panel includes theme switcher

### Key Components

- `ThemeContext` - Global theme state management
- `ThemeToggle` - UI control for switching themes
- `theme.css` - CSS variable definitions for both themes

## Getting Started

### Prerequisites

- Auto Claude desktop app version 2.9.0 or later
- No additional configuration required

### Basic Usage

1. Open Auto Claude desktop application
2. Navigate to Settings (⚙️ icon in sidebar)
3. Find "Appearance" section
4. Click the theme toggle switch
5. Interface immediately switches between light/dark mode

### Configuration

Theme preference is automatically saved and requires no manual configuration.

## Use Cases

### Use Case 1: Late Night Coding

**Scenario**: Developer working on a project at 11 PM

**Steps**:
1. Enable dark mode via settings
2. Continue working with reduced screen brightness
3. Experience less eye strain

### Use Case 2: Presentation Mode

**Scenario**: Demonstrating Auto Claude in a dark conference room

**Steps**:
1. Switch to dark mode for better visibility
2. Present without bright screen glare
3. Audience can see screen more clearly

## Advanced Features

### Keyboard Shortcut (Future)

Currently not implemented, but planned keyboard shortcut: `Ctrl/Cmd + Shift + T` to toggle theme.

## Limitations & Constraints

- Only two themes available (light and dark)
- No custom color schemes
- Does not automatically sync with system theme
- Some third-party components may not fully support dark mode

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Theme doesn't persist | Check browser local storage permissions |
| Some elements still light in dark mode | Report bug with screenshot |
| Toggle button not responding | Refresh application |

## Technical Details

### Dependencies

- React Context API (built-in)
- CSS Custom Properties (native browser support)
- Local Storage API (native browser support)

### Theme Variables

```css
/* Light theme */
--bg-primary: #ffffff;
--text-primary: #1a1a1a;

/* Dark theme */
--bg-primary: #1a1a1a;
--text-primary: #e5e5e5;
```

### Performance

- Theme switch: < 100ms
- No performance impact on rendering
- Minimal memory overhead

## Related Features

- **Settings Panel** - Where theme toggle is located
- **User Preferences** - Part of broader preference system

## Roadmap

**Planned Enhancements**:
- System theme detection
- Custom theme colors
- Scheduled theme switching
- Per-workspace theme preferences

## Support

For issues or questions:
- GitHub Issues: [Auto Claude Issues](https://github.com/AndyMik90/Auto-Claude/issues)
- Discussions: [GitHub Discussions](https://github.com/AndyMik90/Auto-Claude/discussions)
