/**
 * @vitest-environment jsdom
 */
/**
 * Tests for Input component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Input } from '../input';
import { createRef } from 'react';

describe('Input', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('basic rendering', () => {
    it('should render an input element', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toBeInTheDocument();
      expect(input.tagName).toBe('INPUT');
    });

    it('should have correct display name', () => {
      expect(Input.displayName).toBe('Input');
    });

    it('should render with default type text', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      // When type is not explicitly set, browsers default to 'text' but may not show the attribute
      const typeAttr = input.getAttribute('type');
      expect(typeAttr === 'text' || typeAttr === null).toBe(true);
    });

    it('should apply base CSS classes', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('flex', 'h-10', 'w-full', 'rounded-lg');
      expect(input).toHaveClass('border', 'border-border', 'bg-card');
      expect(input).toHaveClass('px-3', 'py-2', 'text-sm', 'text-foreground');
    });
  });

  describe('input types', () => {
    it('should render with type password', () => {
      const { container } = render(<Input type="password" />);
      const input = container.querySelector('input[type="password"]');
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute('type', 'password');
    });

    it('should render with type email', () => {
      render(<Input type="email" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('type', 'email');
    });

    it('should render with type number', () => {
      render(<Input type="number" />);
      const input = screen.getByRole('spinbutton');
      expect(input).toHaveAttribute('type', 'number');
    });

    it('should render with type search', () => {
      render(<Input type="search" />);
      const input = screen.getByRole('searchbox');
      expect(input).toHaveAttribute('type', 'search');
    });

    it('should render with type tel', () => {
      render(<Input type="tel" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('type', 'tel');
    });

    it('should render with type url', () => {
      render(<Input type="url" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('type', 'url');
    });
  });

  describe('props pass-through', () => {
    it('should forward placeholder prop', () => {
      render(<Input placeholder="Enter your name" />);
      const input = screen.getByPlaceholderText('Enter your name');
      expect(input).toBeInTheDocument();
    });

    it('should forward value prop', () => {
      render(<Input value="test value" readOnly />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('test value');
    });

    it('should forward name prop', () => {
      render(<Input name="username" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('name', 'username');
    });

    it('should forward id prop', () => {
      render(<Input id="user-input" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('id', 'user-input');
    });

    it('should forward aria-label prop', () => {
      render(<Input aria-label="Username input" />);
      const input = screen.getByLabelText('Username input');
      expect(input).toBeInTheDocument();
    });

    it('should forward aria-describedby prop', () => {
      render(<Input aria-describedby="helper-text" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-describedby', 'helper-text');
    });

    it('should forward required prop', () => {
      render(<Input required />);
      const input = screen.getByRole('textbox');
      expect(input).toBeRequired();
    });

    it('should forward readOnly prop', () => {
      render(<Input readOnly />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('readOnly');
    });

    it('should forward maxLength prop', () => {
      render(<Input maxLength={10} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('maxLength', '10');
    });

    it('should forward autoFocus prop', () => {
      render(<Input autoFocus />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveFocus();
    });

    it('should forward autoComplete prop', () => {
      render(<Input autoComplete="email" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('autoComplete', 'email');
    });
  });

  describe('disabled state', () => {
    it('should render as disabled when disabled prop is true', () => {
      render(<Input disabled />);
      const input = screen.getByRole('textbox');
      expect(input).toBeDisabled();
    });

    it('should apply disabled styling classes', () => {
      render(<Input disabled />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('disabled:cursor-not-allowed', 'disabled:opacity-50');
    });

    it('should have disabled attribute preventing user input', () => {
      render(<Input disabled defaultValue="" />);
      const input = screen.getByRole('textbox');

      // Verify the disabled attribute is present
      expect(input).toHaveAttribute('disabled');
      // Browser will prevent input when disabled attribute is present
      expect(input).toBeDisabled();
    });
  });

  describe('className merging', () => {
    it('should merge custom className with base classes', () => {
      render(<Input className="custom-class" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('custom-class');
      expect(input).toHaveClass('flex', 'h-10', 'w-full'); // Base classes still present
    });

    it('should allow overriding base classes with custom className', () => {
      render(<Input className="h-12 w-1/2" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('h-12', 'w-1/2');
    });

    it('should handle multiple custom classes', () => {
      render(<Input className="custom-1 custom-2 custom-3" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('custom-1', 'custom-2', 'custom-3');
    });
  });

  describe('ref forwarding', () => {
    it('should forward ref to input element', () => {
      const ref = createRef<HTMLInputElement>();
      render(<Input ref={ref} />);

      expect(ref.current).toBeInstanceOf(HTMLInputElement);
      expect(ref.current?.tagName).toBe('INPUT');
    });

    it('should allow calling focus() via ref', () => {
      const ref = createRef<HTMLInputElement>();
      render(<Input ref={ref} />);

      ref.current?.focus();
      expect(ref.current).toHaveFocus();
    });

    it('should allow calling blur() via ref', () => {
      const ref = createRef<HTMLInputElement>();
      render(<Input ref={ref} autoFocus />);

      expect(ref.current).toHaveFocus();
      ref.current?.blur();
      expect(ref.current).not.toHaveFocus();
    });

    it('should allow accessing value via ref', () => {
      const ref = createRef<HTMLInputElement>();
      render(<Input ref={ref} defaultValue="test" />);

      expect(ref.current?.value).toBe('test');
    });
  });

  describe('user interactions', () => {
    it('should accept user input', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');

      fireEvent.change(input, { target: { value: 'Hello World' } });
      expect(input).toHaveValue('Hello World');
    });

    it('should call onChange handler when user types', () => {
      const handleChange = vi.fn();
      render(<Input onChange={handleChange} />);
      const input = screen.getByRole('textbox');

      fireEvent.change(input, { target: { value: 'test' } });
      expect(handleChange).toHaveBeenCalled();
      expect(handleChange).toHaveBeenCalledTimes(1);
    });

    it('should call onFocus handler when focused', () => {
      const handleFocus = vi.fn();
      render(<Input onFocus={handleFocus} />);
      const input = screen.getByRole('textbox');

      fireEvent.focus(input);
      expect(handleFocus).toHaveBeenCalledTimes(1);
    });

    it('should call onBlur handler when blurred', () => {
      const handleBlur = vi.fn();
      render(<Input onBlur={handleBlur} autoFocus />);
      const input = screen.getByRole('textbox');

      fireEvent.blur(input);
      expect(handleBlur).toHaveBeenCalledTimes(1);
    });

    it('should call onKeyDown handler on key press', () => {
      const handleKeyDown = vi.fn();
      render(<Input onKeyDown={handleKeyDown} />);
      const input = screen.getByRole('textbox');

      fireEvent.keyDown(input, { key: 'a' });
      expect(handleKeyDown).toHaveBeenCalled();
    });

    it('should clear input when user clears it', () => {
      render(<Input defaultValue="initial value" />);
      const input = screen.getByRole('textbox');

      expect(input).toHaveValue('initial value');
      fireEvent.change(input, { target: { value: '' } });
      expect(input).toHaveValue('');
    });
  });

  describe('styling classes', () => {
    it('should apply focus-visible styles', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass(
        'focus-visible:outline-none',
        'focus-visible:ring-2',
        'focus-visible:ring-ring',
        'focus-visible:border-primary'
      );
    });

    it('should apply transition classes', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('transition-colors', 'duration-200');
    });

    it('should apply placeholder styles', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('placeholder:text-muted-foreground');
    });

    it('should apply file input styles', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass(
        'file:border-0',
        'file:bg-transparent',
        'file:text-sm',
        'file:font-medium'
      );
    });
  });

  describe('controlled vs uncontrolled', () => {
    it('should work as uncontrolled component with defaultValue', () => {
      render(<Input defaultValue="uncontrolled" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('uncontrolled');
    });

    it('should work as controlled component with value', () => {
      const { rerender } = render(<Input value="controlled" readOnly />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('controlled');

      rerender(<Input value="updated" readOnly />);
      expect(input).toHaveValue('updated');
    });

    it('should not update when value prop is controlled without onChange', () => {
      render(<Input value="controlled" onChange={() => {}} />);
      const input = screen.getByRole('textbox');

      fireEvent.change(input, { target: { value: 'controlledx' } });
      expect(input).toHaveValue('controlled'); // Value should not change
    });
  });

  describe('edge cases', () => {
    it('should handle empty string value', () => {
      render(<Input value="" readOnly />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('');
    });

    it('should handle undefined className', () => {
      render(<Input className={undefined} />);
      const input = screen.getByRole('textbox');
      expect(input).toBeInTheDocument();
    });

    it('should handle multiple event handlers', () => {
      const onChange1 = vi.fn();
      const onChange2 = vi.fn();

      const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        onChange1(e);
        onChange2(e);
      };

      render(<Input onChange={handleChange} />);
      const input = screen.getByRole('textbox');

      fireEvent.change(input, { target: { value: 'a' } });
      expect(onChange1).toHaveBeenCalled();
      expect(onChange2).toHaveBeenCalled();
    });

    it('should render without crashing when no props provided', () => {
      expect(() => render(<Input />)).not.toThrow();
    });
  });
});
