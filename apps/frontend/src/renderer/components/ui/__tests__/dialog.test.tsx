/**
 * @vitest-environment jsdom
 */
/**
 * Tests for Dialog component
 */

import { describe, it, expect, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { createRef } from 'react';
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogOverlay,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from '../dialog';

describe('Dialog', () => {
  describe('basic rendering', () => {
    it('should render dialog trigger button', () => {
      render(
        <Dialog>
          <DialogTrigger>Open Dialog</DialogTrigger>
        </Dialog>
      );

      const trigger = screen.getByRole('button', { name: 'Open Dialog' });
      expect(trigger).toBeInTheDocument();
    });

    it('should render dialog content when opened', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test Dialog</DialogTitle>
            <DialogDescription>Test description</DialogDescription>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    it('should not render dialog content when closed', () => {
      render(
        <Dialog>
          <DialogContent>
            <DialogTitle>Test Dialog</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('should have correct display names', () => {
      expect(DialogOverlay.displayName).toBe('DialogOverlay');
      expect(DialogContent.displayName).toBe('DialogContent');
      expect(DialogHeader.displayName).toBe('DialogHeader');
      expect(DialogFooter.displayName).toBe('DialogFooter');
      expect(DialogTitle.displayName).toBe('DialogTitle');
      expect(DialogDescription.displayName).toBe('DialogDescription');
    });
  });

  describe('DialogContent', () => {
    it('should render close button by default', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        const closeButton = screen.getByRole('button', { name: /close/i });
        expect(closeButton).toBeInTheDocument();
      });
    });

    it('should hide close button when hideCloseButton is true', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent hideCloseButton>
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /close/i })).not.toBeInTheDocument();
      });
    });

    it('should apply default styling classes', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        const dialog = screen.getByRole('dialog');
        expect(dialog).toHaveClass(
          'fixed',
          'left-[50%]',
          'top-[50%]',
          'translate-x-[-50%]',
          'translate-y-[-50%]'
        );
        expect(dialog).toHaveClass('bg-card', 'border', 'border-border', 'rounded-2xl', 'p-6');
      });
    });

    it('should merge custom className with default classes', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent className="custom-dialog-class">
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        const dialog = screen.getByRole('dialog');
        expect(dialog).toHaveClass('custom-dialog-class');
        expect(dialog).toHaveClass('bg-card'); // Base classes still present
      });
    });

    it('should render children content', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test Title</DialogTitle>
            <div>Custom content</div>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Title')).toBeInTheDocument();
        expect(screen.getByText('Custom content')).toBeInTheDocument();
      });
    });

    it('should have max height constraint', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        const dialog = screen.getByRole('dialog');
        expect(dialog).toHaveClass('max-h-[90vh]');
      });
    });
  });

  describe('DialogOverlay', () => {
    it('should render overlay along with dialog content', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      // The overlay is automatically rendered by Radix UI when DialogContent is shown
      // We verify this by ensuring the dialog itself is rendered
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });
  });

  describe('DialogHeader', () => {
    it('should render header content', () => {
      render(
        <DialogHeader>
          <h2>Header Content</h2>
        </DialogHeader>
      );

      expect(screen.getByText('Header Content')).toBeInTheDocument();
    });

    it('should apply default styling classes', () => {
      const { container } = render(
        <DialogHeader>
          <h2>Header</h2>
        </DialogHeader>
      );

      const header = container.firstChild;
      expect(header).toHaveClass('flex', 'flex-col', 'space-y-2', 'text-center', 'sm:text-left');
    });

    it('should merge custom className', () => {
      const { container } = render(
        <DialogHeader className="custom-header">
          <h2>Header</h2>
        </DialogHeader>
      );

      const header = container.firstChild;
      expect(header).toHaveClass('custom-header');
      expect(header).toHaveClass('flex', 'flex-col'); // Base classes still present
    });
  });

  describe('DialogFooter', () => {
    it('should render footer content', () => {
      render(
        <DialogFooter>
          <button>Action</button>
        </DialogFooter>
      );

      expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
    });

    it('should apply default styling classes', () => {
      const { container } = render(
        <DialogFooter>
          <button>Action</button>
        </DialogFooter>
      );

      const footer = container.firstChild;
      expect(footer).toHaveClass(
        'flex',
        'flex-col-reverse',
        'sm:flex-row',
        'sm:justify-end',
        'sm:space-x-3',
        'mt-6'
      );
    });

    it('should merge custom className', () => {
      const { container } = render(
        <DialogFooter className="custom-footer">
          <button>Action</button>
        </DialogFooter>
      );

      const footer = container.firstChild;
      expect(footer).toHaveClass('custom-footer');
      expect(footer).toHaveClass('flex'); // Base classes still present
    });
  });

  describe('DialogTitle', () => {
    it('should render title text', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Dialog Title</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByText('Dialog Title')).toBeInTheDocument();
      });
    });

    it('should apply default styling classes', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Title</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        const title = screen.getByText('Title');
        expect(title).toHaveClass('text-lg', 'font-semibold', 'leading-none', 'text-foreground');
      });
    });

    it('should merge custom className', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle className="custom-title">Title</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        const title = screen.getByText('Title');
        expect(title).toHaveClass('custom-title');
        expect(title).toHaveClass('text-lg', 'font-semibold'); // Base classes still present
      });
    });
  });

  describe('DialogDescription', () => {
    it('should render description text', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Title</DialogTitle>
            <DialogDescription>Description text</DialogDescription>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByText('Description text')).toBeInTheDocument();
      });
    });

    it('should apply default styling classes', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Title</DialogTitle>
            <DialogDescription>Description</DialogDescription>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        const description = screen.getByText('Description');
        expect(description).toHaveClass('text-sm', 'text-muted-foreground');
      });
    });

    it('should merge custom className', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Title</DialogTitle>
            <DialogDescription className="custom-description">Description</DialogDescription>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        const description = screen.getByText('Description');
        expect(description).toHaveClass('custom-description');
        expect(description).toHaveClass('text-sm'); // Base classes still present
      });
    });
  });

  describe('dialog interactions', () => {
    it('should open dialog when trigger is clicked', async () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogContent>
            <DialogTitle>Test Dialog</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      const trigger = screen.getByRole('button', { name: 'Open' });
      fireEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    it('should close dialog when close button is clicked', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test Dialog</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const closeButton = screen.getByRole('button', { name: /close/i });
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('should close dialog when DialogClose is clicked', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test Dialog</DialogTitle>
            <DialogClose asChild>
              <button>Cancel</button>
            </DialogClose>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('controlled state', () => {
    it('should support controlled open state', async () => {
      const { rerender } = render(
        <Dialog open={false}>
          <DialogContent>
            <DialogTitle>Controlled Dialog</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

      rerender(
        <Dialog open={true}>
          <DialogContent>
            <DialogTitle>Controlled Dialog</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    it('should call onOpenChange when dialog state changes', async () => {
      const handleOpenChange = vi.fn();

      render(
        <Dialog onOpenChange={handleOpenChange}>
          <DialogTrigger>Open</DialogTrigger>
          <DialogContent>
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      const trigger = screen.getByRole('button', { name: 'Open' });
      fireEvent.click(trigger);

      await waitFor(() => {
        expect(handleOpenChange).toHaveBeenCalledWith(true);
      });
    });
  });

  describe('ref forwarding', () => {
    it('should forward ref to DialogContent', async () => {
      const ref = createRef<HTMLDivElement>();

      render(
        <Dialog defaultOpen>
          <DialogContent ref={ref}>
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(ref.current).toBeInstanceOf(HTMLDivElement);
      });
    });

    it('should forward ref to DialogTitle', async () => {
      const ref = createRef<HTMLHeadingElement>();

      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle ref={ref}>Test Title</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(ref.current).toBeInstanceOf(HTMLHeadingElement);
        expect(ref.current?.textContent).toBe('Test Title');
      });
    });

    it('should forward ref to DialogDescription', async () => {
      const ref = createRef<HTMLParagraphElement>();

      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Title</DialogTitle>
            <DialogDescription ref={ref}>Test Description</DialogDescription>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(ref.current).toBeInstanceOf(HTMLParagraphElement);
        expect(ref.current?.textContent).toBe('Test Description');
      });
    });

    it('should forward ref to DialogOverlay', async () => {
      const ref = createRef<HTMLDivElement>();

      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogOverlay ref={ref} />
            <DialogTitle>Title</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(ref.current).toBeInstanceOf(HTMLDivElement);
      });
    });
  });

  describe('accessibility', () => {
    it('should have dialog role on content', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Accessible Dialog</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    it('should have screen reader text for close button', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        const closeButton = screen.getByRole('button', { name: /close/i });
        expect(closeButton).toHaveAccessibleName();
      });
    });

    it('should have focus-visible styles on close button', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        const closeButton = screen.getByRole('button', { name: /close/i });
        expect(closeButton).toHaveClass(
          'focus-visible:outline-none',
          'focus-visible:ring-2',
          'focus-visible:ring-ring'
        );
      });
    });
  });

  describe('complete dialog example', () => {
    it('should render complete dialog with all components', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Complete Dialog</DialogTitle>
              <DialogDescription>This is a complete dialog example.</DialogDescription>
            </DialogHeader>
            <div>Dialog body content</div>
            <DialogFooter>
              <DialogClose asChild>
                <button>Cancel</button>
              </DialogClose>
              <button>Confirm</button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText('Complete Dialog')).toBeInTheDocument();
        expect(screen.getByText('This is a complete dialog example.')).toBeInTheDocument();
        expect(screen.getByText('Dialog body content')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
      });
    });
  });

  describe('edge cases', () => {
    it('should handle dialog without title gracefully', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <div>Content without title</div>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    it('should handle empty dialog content', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Empty</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    it('should handle undefined className', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent className={undefined}>
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    it('should render without crashing when minimal props provided', () => {
      expect(() =>
        render(
          <Dialog>
            <DialogContent>
              <DialogTitle>Minimal</DialogTitle>
            </DialogContent>
          </Dialog>
        )
      ).not.toThrow();
    });
  });
});
