/**
 * @vitest-environment jsdom
 */
/**
 * Tests for Button component
 */

import { describe, it, expect, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { createRef } from 'react';
import { Button } from '../button';

describe('Button', () => {
  describe('basic rendering', () => {
    it('should render button element by default', () => {
      render(<Button>Click me</Button>);

      const button = screen.getByRole('button', { name: 'Click me' });
      expect(button).toBeInTheDocument();
      expect(button.tagName).toBe('BUTTON');
    });

    it('should render with children content', () => {
      render(<Button>Test Content</Button>);

      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    it('should apply default variant and size classes', () => {
      render(<Button>Default Button</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('inline-flex', 'items-center', 'justify-center');
    });
  });

  describe('variants', () => {
    it('should apply default variant classes', () => {
      render(<Button variant="default">Default</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-primary', 'text-primary-foreground');
    });

    it('should apply destructive variant classes', () => {
      render(<Button variant="destructive">Delete</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-destructive', 'text-destructive-foreground');
    });

    it('should apply outline variant classes', () => {
      render(<Button variant="outline">Outline</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('border', 'border-border', 'bg-transparent');
    });

    it('should apply secondary variant classes', () => {
      render(<Button variant="secondary">Secondary</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-secondary', 'text-secondary-foreground');
    });

    it('should apply ghost variant classes', () => {
      render(<Button variant="ghost">Ghost</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('hover:bg-accent', 'hover:text-accent-foreground');
    });

    it('should apply link variant classes', () => {
      render(<Button variant="link">Link</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('text-primary', 'underline-offset-4');
    });

    it('should apply success variant classes', () => {
      render(<Button variant="success">Success</Button>);

      const button = screen.getByRole('button');
      expect(button.className).toContain('bg-[var(--success)]');
    });

    it('should apply warning variant classes', () => {
      render(<Button variant="warning">Warning</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-warning', 'text-warning-foreground');
    });

    it('should apply info variant classes', () => {
      render(<Button variant="info">Info</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-info', 'text-info-foreground');
    });
  });

  describe('sizes', () => {
    it('should apply default size classes', () => {
      render(<Button size="default">Default Size</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-10', 'px-4', 'py-2', 'text-sm', 'rounded-lg');
    });

    it('should apply small size classes', () => {
      render(<Button size="sm">Small</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-8', 'px-3', 'text-xs', 'rounded-md');
    });

    it('should apply large size classes', () => {
      render(<Button size="lg">Large</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-12', 'px-6', 'text-base', 'rounded-lg');
    });

    it('should apply icon size classes', () => {
      render(<Button size="icon" aria-label="Icon button">🔍</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-10', 'w-10', 'rounded-lg');
    });
  });

  describe('disabled state', () => {
    it('should render as disabled when disabled prop is true', () => {
      render(<Button disabled>Disabled Button</Button>);

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should apply disabled classes', () => {
      render(<Button disabled>Disabled</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('disabled:pointer-events-none', 'disabled:opacity-50');
    });

    it('should not trigger onClick when disabled', () => {
      const handleClick = vi.fn();

      render(<Button disabled onClick={handleClick}>Click</Button>);

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  describe('custom className', () => {
    it('should merge custom className with default classes', () => {
      render(<Button className="custom-class">Custom</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('custom-class');
      expect(button).toHaveClass('inline-flex'); // Should still have default classes
    });

    it('should allow overriding styles with custom className', () => {
      render(<Button className="bg-red-500">Custom Background</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-red-500');
    });
  });

  describe('click handling', () => {
    it('should trigger onClick when clicked', () => {
      const handleClick = vi.fn();

      render(<Button onClick={handleClick}>Click me</Button>);

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should pass event to onClick handler', () => {
      const handleClick = vi.fn();

      render(<Button onClick={handleClick}>Click</Button>);

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(handleClick).toHaveBeenCalledWith(expect.any(Object));
    });
  });

  describe('ref forwarding', () => {
    it('should forward ref to button element', () => {
      const ref = createRef<HTMLButtonElement>();

      render(<Button ref={ref}>Button with ref</Button>);

      expect(ref.current).toBeInstanceOf(HTMLButtonElement);
      expect(ref.current?.textContent).toBe('Button with ref');
    });

    it('should allow calling focus on ref', () => {
      const ref = createRef<HTMLButtonElement>();

      render(<Button ref={ref}>Focusable</Button>);

      ref.current?.focus();
      expect(ref.current).toHaveFocus();
    });
  });

  describe('HTML button attributes', () => {
    it('should support type attribute', () => {
      render(<Button type="submit">Submit</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('type', 'submit');
    });

    it('should support aria-label attribute', () => {
      render(<Button aria-label="Close dialog">×</Button>);

      const button = screen.getByRole('button', { name: 'Close dialog' });
      expect(button).toHaveAttribute('aria-label', 'Close dialog');
    });

    it('should support data attributes', () => {
      render(<Button data-testid="custom-button">Test</Button>);

      const button = screen.getByTestId('custom-button');
      expect(button).toBeInTheDocument();
    });

    it('should support name attribute', () => {
      render(<Button name="action-button">Action</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('name', 'action-button');
    });
  });

  describe('asChild prop', () => {
    it('should render as Slot component when asChild is true', () => {
      render(
        <Button asChild>
          <a href="/link">Link Button</a>
        </Button>
      );

      // When asChild is true, it should render the child (anchor) instead of button
      const link = screen.getByRole('link', { name: 'Link Button' });
      expect(link).toBeInTheDocument();
      expect(link.tagName).toBe('A');
    });

    it('should apply button classes to child element when asChild is true', () => {
      render(
        <Button asChild variant="destructive">
          <a href="/delete">Delete Link</a>
        </Button>
      );

      const link = screen.getByRole('link');
      expect(link).toHaveClass('bg-destructive', 'text-destructive-foreground');
    });
  });

  describe('accessibility', () => {
    it('should have button role by default', () => {
      render(<Button>Accessible Button</Button>);

      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('should have focus-visible outline', () => {
      render(<Button>Focus me</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('focus-visible:outline-none', 'focus-visible:ring-2');
    });

    it('should be focusable', () => {
      render(<Button>Focusable Button</Button>);

      const button = screen.getByRole('button');
      button.focus();
      expect(button).toHaveFocus();
    });
  });

  describe('combined props', () => {
    it('should handle multiple props together', () => {
      const handleClick = vi.fn();

      render(
        <Button
          variant="destructive"
          size="lg"
          disabled={false}
          className="extra-class"
          onClick={handleClick}
          aria-label="Delete item"
        >
          Delete
        </Button>
      );

      const button = screen.getByRole('button', { name: 'Delete item' });
      expect(button).toBeInTheDocument();
      expect(button).toHaveClass('bg-destructive', 'h-12', 'px-6', 'extra-class');
      expect(button).not.toBeDisabled();
    });

    it('should handle variant and size combinations', () => {
      const variants = ['default', 'destructive', 'outline', 'secondary', 'ghost'] as const;
      const sizes = ['default', 'sm', 'lg'] as const;

      variants.forEach((variant) => {
        sizes.forEach((size) => {
          const { unmount } = render(
            <Button variant={variant} size={size}>
              {variant}-{size}
            </Button>
          );

          const button = screen.getByRole('button');
          expect(button).toBeInTheDocument();

          unmount();
        });
      });
    });
  });
});
