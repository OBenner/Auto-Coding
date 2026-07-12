import type { Preview } from '@storybook/react-vite';
import '../src/tokens/tokens.css';

const preview: Preview = {
  globalTypes: {
    theme: {
      description: 'Design-token color theme',
      toolbar: {
        title: 'Theme',
        icon: 'mirror',
        items: ['light', 'dark'],
        dynamicTitle: true,
      },
    },
  },
  initialGlobals: {
    theme: 'light',
  },
  decorators: [
    (Story, context) => {
      // Same mechanism as ThemeProvider: tokens.css keys dark overrides
      // off <html data-theme="dark">.
      document.documentElement.setAttribute('data-theme', context.globals.theme);
      return (
        <div
          style={{
            background: 'var(--bg)',
            color: 'var(--ink)',
            padding: 16,
            minHeight: '100vh',
            boxSizing: 'border-box',
          }}
        >
          <Story />
        </div>
      );
    },
  ],
};

export default preview;
