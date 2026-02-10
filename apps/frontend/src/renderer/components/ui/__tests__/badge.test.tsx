/**
 * @vitest-environment jsdom
 */
/**
 * Tests for Badge component
 */

import { describe, it, expect } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '../badge';

describe('Badge', () => {
  describe('rendering', () => {
    it('should render with default variant', () => {
      render(<Badge>Default Badge</Badge>);

      const badge = screen.getByText('Default Badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-primary', 'text-primary-foreground', 'border-transparent');
    });

    it('should render children content correctly', () => {
      render(<Badge>Test Content</Badge>);

      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    it('should render with custom className', () => {
      render(<Badge className="custom-class">Badge</Badge>);

      const badge = screen.getByText('Badge');
      expect(badge).toHaveClass('custom-class');
    });
  });

  describe('variant styles', () => {
    it('should render with secondary variant', () => {
      render(<Badge variant="secondary">Secondary</Badge>);

      const badge = screen.getByText('Secondary');
      expect(badge).toHaveClass('bg-secondary', 'text-secondary-foreground', 'border-transparent');
    });

    it('should render with destructive variant', () => {
      render(<Badge variant="destructive">Destructive</Badge>);

      const badge = screen.getByText('Destructive');
      expect(badge).toHaveClass('bg-destructive', 'text-destructive-foreground', 'border-transparent');
    });

    it('should render with outline variant', () => {
      render(<Badge variant="outline">Outline</Badge>);

      const badge = screen.getByText('Outline');
      expect(badge).toHaveClass('text-foreground');
    });

    it('should render with success variant', () => {
      render(<Badge variant="success">Success</Badge>);

      const badge = screen.getByText('Success');
      expect(badge).toHaveClass('bg-success/10', 'text-success', 'border-transparent');
    });

    it('should render with warning variant', () => {
      render(<Badge variant="warning">Warning</Badge>);

      const badge = screen.getByText('Warning');
      expect(badge).toHaveClass('bg-warning/10', 'text-warning', 'border-transparent');
    });

    it('should render with info variant', () => {
      render(<Badge variant="info">Info</Badge>);

      const badge = screen.getByText('Info');
      expect(badge).toHaveClass('bg-info/10', 'text-info', 'border-transparent');
    });

    it('should render with purple variant', () => {
      render(<Badge variant="purple">Purple</Badge>);

      const badge = screen.getByText('Purple');
      expect(badge).toHaveClass('bg-purple-500/10', 'text-purple-400', 'border-transparent');
    });

    it('should render with muted variant', () => {
      render(<Badge variant="muted">Muted</Badge>);

      const badge = screen.getByText('Muted');
      expect(badge).toHaveClass('bg-muted', 'text-muted-foreground', 'border-transparent');
    });
  });

  describe('HTML attributes', () => {
    it('should apply aria-label attribute', () => {
      render(<Badge aria-label="Status badge">Active</Badge>);

      const badge = screen.getByLabelText('Status badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent('Active');
    });

    it('should apply role attribute', () => {
      render(<Badge role="status">Loading</Badge>);

      const badge = screen.getByRole('status');
      expect(badge).toBeInTheDocument();
    });

    it('should apply data attributes', () => {
      render(<Badge data-testid="custom-badge" data-status="active">Badge</Badge>);

      const badge = screen.getByTestId('custom-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute('data-status', 'active');
    });

    it('should apply id attribute', () => {
      render(<Badge id="unique-badge">Badge</Badge>);

      const badge = document.getElementById('unique-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent('Badge');
    });
  });

  describe('base classes', () => {
    it('should always have base badge classes', () => {
      render(<Badge>Base Classes</Badge>);

      const badge = screen.getByText('Base Classes');
      expect(badge).toHaveClass('inline-flex');
      expect(badge).toHaveClass('items-center');
      expect(badge).toHaveClass('rounded-md');
      expect(badge).toHaveClass('border');
      expect(badge).toHaveClass('px-2.5');
      expect(badge).toHaveClass('py-0.5');
      expect(badge).toHaveClass('text-xs');
      expect(badge).toHaveClass('font-semibold');
      expect(badge).toHaveClass('transition-colors');
    });

    it('should have focus styles', () => {
      render(<Badge>Focus Styles</Badge>);

      const badge = screen.getByText('Focus Styles');
      expect(badge).toHaveClass('focus:outline-none');
      expect(badge).toHaveClass('focus:ring-2');
      expect(badge).toHaveClass('focus:ring-ring');
      expect(badge).toHaveClass('focus:ring-offset-2');
    });
  });

  describe('custom className merging', () => {
    it('should merge custom className with variant classes', () => {
      render(
        <Badge variant="success" className="ml-2 text-sm">
          Custom Classes
        </Badge>
      );

      const badge = screen.getByText('Custom Classes');
      // Should have both variant classes and custom classes
      expect(badge).toHaveClass('bg-success/10', 'text-success');
      expect(badge).toHaveClass('ml-2', 'text-sm');
    });
  });

  describe('complex content', () => {
    it('should render with multiple children elements', () => {
      render(
        <Badge>
          <span>Icon</span>
          <span>Label</span>
        </Badge>
      );

      expect(screen.getByText('Icon')).toBeInTheDocument();
      expect(screen.getByText('Label')).toBeInTheDocument();
    });

    it('should render with numeric content', () => {
      render(<Badge>{42}</Badge>);

      expect(screen.getByText('42')).toBeInTheDocument();
    });

    it('should render empty badge', () => {
      const { container } = render(<Badge />);

      const badge = container.querySelector('.inline-flex');
      expect(badge).toBeInTheDocument();
      expect(badge).toBeEmptyDOMElement();
    });
  });
});
