import type { HTMLAttributes } from 'react';
import type { BadgeTone } from '../client/types';
import './Badge.css';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  /** Semantic color; defaults to neutral. */
  tone?: BadgeTone;
  /** 'sm' for dense card chips, 'md' for detail/label badges. */
  size?: 'sm' | 'md';
}

/**
 * Tonal pill used across the board and detail screens (status chips, outcome
 * badges). The tone colors are shared design tokens; `size` preserves the two
 * historical sizings (dense card chip vs. detail badge). Remaining span
 * attributes (className, aria-*, data-*, handlers) are forwarded.
 */
export function Badge({
  tone = 'neutral',
  size = 'md',
  className,
  children,
  ...rest
}: Readonly<BadgeProps>) {
  const classes = `ac-badge ac-badge--${size} ac-badge--${tone}${
    className ? ` ${className}` : ''
  }`;
  return (
    <span className={classes} {...rest}>
      {children}
    </span>
  );
}
