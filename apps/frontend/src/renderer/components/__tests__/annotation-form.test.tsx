/**
 * Tests for AnnotationForm component
 *
 * Tests the annotation form dialog including:
 * - Form validation (description min length)
 * - Severity selector functionality
 * - Submit/cancel button states
 * - Character counter updates
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AnnotationForm } from '../annotations/AnnotationForm';
import type { AnnotationFormData, AnnotationCoordinates } from '../../../shared/types/annotation';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string) => defaultValue || key
  })
}));

// Mock UI components
vi.mock('../ui/dialog', () => ({
  Dialog: ({ children, open, onOpenChange }: any) => (
    open ? <div data-testid="dialog">{children}</div> : null
  ),
  DialogContent: ({ children }: any) => <div>{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <h2>{children}</h2>,
  DialogDescription: ({ children }: any) => <p>{children}</p>,
  DialogFooter: ({ children }: any) => <div className="flex gap-2">{children}</div>
}));

vi.mock('../ui/button', () => ({
  Button: ({ children, onClick, disabled, ...props }: any) => (
    <button
      onClick={onClick}
      disabled={disabled}
      data-testid={props.variant === 'outline' ? 'cancel-button' : 'submit-button'}
    >
      {children}
    </button>
  )
}));

vi.mock('../ui/textarea', () => ({
  Textarea: ({ value, onChange, disabled, placeholder, ...props }: any) => (
    <textarea
      value={value}
      onChange={(e) => onChange?.(e)}
      disabled={disabled}
      placeholder={placeholder}
      data-testid="description-textarea"
      {...props}
    />
  )
}));

vi.mock('../ui/label', () => ({
  Label: ({ children }: any) => <label>{children}</label>
}));

vi.mock('../ui/select', () => ({
  Select: ({ value, onValueChange, disabled, children }: any) => (
    <div data-testid="severity-select">
      <span data-selected-severity={value}></span>
      {children}
    </div>
  ),
  SelectTrigger: ({ children }: any) => <button>{children}</button>,
  SelectValue: ({ children }: any) => <span>{children}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value, onClick }: any) => (
    <button onClick={() => onClick?.(value)}>{children}</button>
  )
}));

describe('AnnotationForm', () => {
  const mockCoordinates: AnnotationCoordinates = {
    x: 100,
    y: 200,
    width: 300,
    height: 400
  };

  const mockScreenshot = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should render dialog with title and description', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByText('Add Annotation Details')).toBeInTheDocument();
      expect(screen.getByText('Describe the issue and set its severity level.')).toBeInTheDocument();
    });

    it('should display screenshot preview', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const screenshot = screen.getByAltText('Screenshot of annotated area');
      expect(screenshot).toBeInTheDocument();
      expect(screenshot).toHaveAttribute('src', mockScreenshot);
    });

    it('should display selection dimensions', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByText('300 × 400')).toBeInTheDocument();
    });

    it('should render description textarea', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveAttribute('placeholder');
    });

    it('should render severity selector', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByTestId('severity-select')).toBeInTheDocument();
    });

    it('should render submit and cancel buttons', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByTestId('submit-button')).toBeInTheDocument();
      expect(screen.getByTestId('cancel-button')).toBeInTheDocument();
    });

    it('should show required indicator for description field', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      // Description label should have asterisk
      expect(screen.getByText(/\*/)).toBeInTheDocument();
    });
  });

  describe('form validation', () => {
    it('should disable submit button when description is empty', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const submitButton = screen.getByTestId('submit-button');
      expect(submitButton).toBeDisabled();
    });

    it('should disable submit button when description is too short', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'Short' } });

      const submitButton = screen.getByTestId('submit-button');
      expect(submitButton).toBeDisabled();
    });

    it('should enable submit button when description meets minimum length', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'This is a valid description that is long enough' } });

      const submitButton = screen.getByTestId('submit-button');
      expect(submitButton).not.toBeDisabled();
    });

    it('should show character count', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'Testing' } });

      expect(screen.getByText(/7 \/ 10/)).toBeInTheDocument();
    });

    it('should show error message when description is too short and has content', async () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'Short' } });

      // Should show "Too short" warning
      await waitFor(() => {
        expect(screen.getByText('Too short')).toBeInTheDocument();
      });
    });
  });

  describe('severity selection', () => {
    it('should have medium severity selected by default', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const severitySelect = screen.getByTestId('severity-select');
      expect(severitySelect.querySelector('[data-selected-severity="medium"]')).toBeInTheDocument();
    });

    it('should display severity labels', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByText(/Low - Minor visual/)).toBeInTheDocument();
      expect(screen.getByText(/Medium - Noticeable/)).toBeInTheDocument();
      expect(screen.getByText(/High - Significant/)).toBeInTheDocument();
      expect(screen.getByText(/Critical - Blocking/)).toBeInTheDocument();
    });
  });

  describe('form submission', () => {
    it('should call onSubmit with form data when submit is clicked', async () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'This is a valid annotation description' } });

      const submitButton = screen.getByTestId('submit-button');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledTimes(1);
        expect(mockOnSubmit).toHaveBeenCalledWith({
          description: 'This is a valid annotation description',
          severity: 'medium'
        });
      });
    });

    it('should not call onSubmit when description is too short', async () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'Short' } });

      const submitButton = screen.getByTestId('submit-button');
      fireEvent.click(submitButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it('should show loading state during submission', async () => {
      const slowSubmit = vi.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));

      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={slowSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'Valid description for testing' } });

      const submitButton = screen.getByTestId('submit-button');
      fireEvent.click(submitButton);

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText('Submitting...')).toBeInTheDocument();
      });
    });
  });

  describe('cancel', () => {
    it('should call onCancel when cancel button is clicked', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const cancelButton = screen.getByTestId('cancel-button');
      fireEvent.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalledTimes(1);
    });

    it('should disable cancel button during submission', async () => {
      const slowSubmit = vi.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));

      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={slowSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'Valid description' } });

      const submitButton = screen.getByTestId('submit-button');
      fireEvent.click(submitButton);

      await waitFor(() => {
        const cancelButton = screen.getByTestId('cancel-button');
        expect(cancelButton).toBeDisabled();
      });
    });
  });

  describe('error handling', () => {
    it('should display error message when submission fails', async () => {
      const failingSubmit = vi.fn(() => Promise.reject(new Error('Network error')));

      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={failingSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'Valid description for testing' } });

      const submitButton = screen.getByTestId('submit-button');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument();
      });
    });
  });

  describe('form reset', () => {
    it('should reset form when coordinates change', () => {
      const { rerender } = render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'Previous annotation description' } });

      // Rerender with new coordinates
      rerender(
        <AnnotationForm
          coordinates={{ ...mockCoordinates, x: 50 }}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      expect(textarea).toHaveValue('');
    });
  });

  describe('accessibility', () => {
    it('should have aria-invalid on textarea when description is too short', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'Short' } });

      expect(textarea).toHaveAttribute('aria-invalid', 'true');
    });

    it('should not have aria-invalid when description is valid', () => {
      render(
        <AnnotationForm
          coordinates={mockCoordinates}
          screenshot={mockScreenshot}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      );

      const textarea = screen.getByTestId('description-textarea');
      fireEvent.change(textarea, { target: { value: 'This is a valid description' } });

      expect(textarea).not.toHaveAttribute('aria-invalid');
    });
  });
});
