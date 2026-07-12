import type { ButtonHTMLAttributes } from 'react';
import './Button.css';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** 'primary' for the main call-to-action; 'default' for everything else. */
  variant?: 'default' | 'primary';
}

/**
 * Standard action button from the `.lazyweb` design language (header
 * actions like "Import spec" / "+ New spec"). Defaults to type="button";
 * remaining button attributes are forwarded.
 */
export function Button({
  variant = 'default',
  className,
  children,
  ...rest
}: Readonly<ButtonProps>) {
  const classes = `ac-button${
    variant === 'primary' ? ' ac-button--primary' : ''
  }${className ? ` ${className}` : ''}`;
  return (
    <button type="button" className={classes} {...rest}>
      {children}
    </button>
  );
}
