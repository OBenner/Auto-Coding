/**
 * @vitest-environment jsdom
 */
/**
 * Tests for CommandPalette component - search, selection, keyboard hints
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'quickActions:searchPlaceholder': 'Search commands...',
        'quickActions:recent': 'Recent',
        'quickActions:navigate': 'Navigate',
        'quickActions:select': 'Select',
        'quickActions:close': 'Close',
        'quickActions:noCommandsFound': 'No commands found',
      };
      return translations[key] || key;
    },
  }),
}));

// Mock lucide-react
vi.mock('lucide-react', () => {
  const icon = (props: any) => <span data-testid={`icon-${props.className || ''}`} />;
  return {
    Search: icon,
    Clock: icon,
  };
});

// Mock UI components
vi.mock('../ui/dialog', () => ({
  Dialog: ({ children, open }: any) => open ? <div data-testid="command-dialog">{children}</div> : null,
  DialogContent: ({ children, className }: any) => <div className={className}>{children}</div>,
}));

vi.mock('../../lib/utils', () => ({
  cn: (...classes: any[]) => classes.filter(Boolean).join(' '),
}));

import { CommandPalette } from '../CommandPalette';
import type { CommandAction, CommandGroup } from '../CommandPalette';

describe('CommandPalette', () => {
  const mockOnOpenChange = vi.fn();

  const createCommand = (overrides: Partial<CommandAction> = {}): CommandAction => ({
    id: 'cmd-1',
    label: 'Test Command',
    onSelect: vi.fn(),
    ...overrides,
  });

  const sampleCommands: CommandAction[] = [
    createCommand({ id: 'new-task', label: 'New Task', description: 'Create a new task', keywords: ['create', 'add'] }),
    createCommand({ id: 'settings', label: 'Open Settings', description: 'Open app settings', shortcut: '⌘,' }),
    createCommand({ id: 'terminal', label: 'New Terminal', description: 'Open a terminal', keywords: ['shell', 'console'] }),
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should not render when closed', () => {
      render(
        <CommandPalette open={false} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      expect(screen.queryByTestId('command-dialog')).not.toBeInTheDocument();
    });

    it('should render when open', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      expect(screen.getByTestId('command-dialog')).toBeInTheDocument();
    });

    it('should render search input with placeholder', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      expect(screen.getByPlaceholderText('Search commands...')).toBeInTheDocument();
    });

    it('should render custom placeholder', () => {
      render(
        <CommandPalette
          open={true}
          onOpenChange={mockOnOpenChange}
          commands={sampleCommands}
          placeholder="Type to search..."
        />
      );

      expect(screen.getByPlaceholderText('Type to search...')).toBeInTheDocument();
    });

    it('should render all commands', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      expect(screen.getByText('New Task')).toBeInTheDocument();
      expect(screen.getByText('Open Settings')).toBeInTheDocument();
      expect(screen.getByText('New Terminal')).toBeInTheDocument();
    });

    it('should render command descriptions', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      expect(screen.getByText('Create a new task')).toBeInTheDocument();
      expect(screen.getByText('Open app settings')).toBeInTheDocument();
    });

    it('should render keyboard shortcut hints', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      expect(screen.getByText('⌘,')).toBeInTheDocument();
    });

    it('should render keyboard navigation hints in footer', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      expect(screen.getByText('Navigate')).toBeInTheDocument();
      expect(screen.getByText('Select')).toBeInTheDocument();
      expect(screen.getByText('Close')).toBeInTheDocument();
    });
  });

  describe('search filtering', () => {
    it('should filter commands by label', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      const input = screen.getByPlaceholderText('Search commands...');
      fireEvent.change(input, { target: { value: 'terminal' } });

      expect(screen.getByText('New Terminal')).toBeInTheDocument();
      expect(screen.queryByText('New Task')).not.toBeInTheDocument();
      expect(screen.queryByText('Open Settings')).not.toBeInTheDocument();
    });

    it('should filter commands by description', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      const input = screen.getByPlaceholderText('Search commands...');
      fireEvent.change(input, { target: { value: 'app settings' } });

      expect(screen.getByText('Open Settings')).toBeInTheDocument();
      expect(screen.queryByText('New Task')).not.toBeInTheDocument();
    });

    it('should filter commands by keywords', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      const input = screen.getByPlaceholderText('Search commands...');
      fireEvent.change(input, { target: { value: 'shell' } });

      expect(screen.getByText('New Terminal')).toBeInTheDocument();
      expect(screen.queryByText('New Task')).not.toBeInTheDocument();
    });

    it('should be case insensitive', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      const input = screen.getByPlaceholderText('Search commands...');
      fireEvent.change(input, { target: { value: 'NEW TASK' } });

      expect(screen.getByText('New Task')).toBeInTheDocument();
    });

    it('should show empty message when no commands match', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={sampleCommands} />
      );

      const input = screen.getByPlaceholderText('Search commands...');
      fireEvent.change(input, { target: { value: 'xyznonexistent' } });

      expect(screen.getByText('No commands found')).toBeInTheDocument();
    });

    it('should show custom empty message', () => {
      render(
        <CommandPalette
          open={true}
          onOpenChange={mockOnOpenChange}
          commands={sampleCommands}
          emptyMessage="Nothing here!"
        />
      );

      const input = screen.getByPlaceholderText('Search commands...');
      fireEvent.change(input, { target: { value: 'xyznonexistent' } });

      expect(screen.getByText('Nothing here!')).toBeInTheDocument();
    });
  });

  describe('command selection', () => {
    it('should call onSelect and close when command is clicked', () => {
      const onSelect = vi.fn();
      const commands = [createCommand({ id: 'test', label: 'Click Me', onSelect })];

      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={commands} />
      );

      fireEvent.click(screen.getByText('Click Me'));

      expect(onSelect).toHaveBeenCalled();
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  describe('command groups', () => {
    it('should render grouped commands with headers', () => {
      const groups: CommandGroup[] = [
        {
          id: 'navigation',
          label: 'Navigation',
          commands: [createCommand({ id: 'nav-1', label: 'Go to Dashboard' })],
        },
        {
          id: 'actions',
          label: 'Actions',
          commands: [createCommand({ id: 'act-1', label: 'Create File' })],
        },
      ];

      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commandGroups={groups} />
      );

      expect(screen.getByText('Navigation')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
      expect(screen.getByText('Go to Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Create File')).toBeInTheDocument();
    });

    it('should filter within groups', () => {
      const groups: CommandGroup[] = [
        {
          id: 'navigation',
          label: 'Navigation',
          commands: [
            createCommand({ id: 'nav-1', label: 'Go to Dashboard' }),
            createCommand({ id: 'nav-2', label: 'Go to Settings' }),
          ],
        },
        {
          id: 'actions',
          label: 'Actions',
          commands: [createCommand({ id: 'act-1', label: 'Create File' })],
        },
      ];

      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commandGroups={groups} />
      );

      const input = screen.getByPlaceholderText('Search commands...');
      fireEvent.change(input, { target: { value: 'dashboard' } });

      expect(screen.getByText('Go to Dashboard')).toBeInTheDocument();
      expect(screen.queryByText('Go to Settings')).not.toBeInTheDocument();
      expect(screen.queryByText('Create File')).not.toBeInTheDocument();
      // Actions group should be hidden (no matching commands)
      expect(screen.queryByText('Actions')).not.toBeInTheDocument();
    });
  });

  describe('recent commands', () => {
    it('should show recent commands section when no search', () => {
      render(
        <CommandPalette
          open={true}
          onOpenChange={mockOnOpenChange}
          commands={sampleCommands}
          recentCommands={['new-task', 'settings']}
        />
      );

      expect(screen.getByText('Recent')).toBeInTheDocument();
    });

    it('should hide recent commands section when searching', () => {
      render(
        <CommandPalette
          open={true}
          onOpenChange={mockOnOpenChange}
          commands={sampleCommands}
          recentCommands={['new-task']}
        />
      );

      const input = screen.getByPlaceholderText('Search commands...');
      fireEvent.change(input, { target: { value: 'term' } });

      expect(screen.queryByText('Recent')).not.toBeInTheDocument();
    });

    it('should not show recent section when no recent commands', () => {
      render(
        <CommandPalette
          open={true}
          onOpenChange={mockOnOpenChange}
          commands={sampleCommands}
          recentCommands={[]}
        />
      );

      expect(screen.queryByText('Recent')).not.toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty message with no commands', () => {
      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={[]} />
      );

      expect(screen.getByText('No commands found')).toBeInTheDocument();
    });
  });

  describe('icon rendering', () => {
    it('should render command icons when provided', () => {
      const commands = [
        createCommand({
          id: 'with-icon',
          label: 'With Icon',
          icon: <span data-testid="custom-icon">icon</span>,
        }),
      ];

      render(
        <CommandPalette open={true} onOpenChange={mockOnOpenChange} commands={commands} />
      );

      expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    });
  });
});
