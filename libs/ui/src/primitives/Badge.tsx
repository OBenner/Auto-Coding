import type { ReactNode } from 'react';
import type { BadgeTone } from '../client/types';
import './Badge.css';

export interface BadgeProps {
  /** Semantic color; defaults to neutral. */
  tone?: BadgeTone;
  /** 'sm' for dense card chips, 'md' for detail/label badges. */
  size?: 'sm' | 'md';
  children: ReactNode;
}

/**
 * Tonal pill used across the board and detail screens (status chips, outcome
 * badges). The tone colors are shared design tokens; `size` preserves the two
 * historical sizings (dense card chip vs. detail badge).
 */
export function Badge({
  tone = 'neutral',
  size = 'md',
  children,
}: Readonly<BadgeProps>) {
  return (
    <span className={`ac-badge ac-badge--${size} ac-badge--${tone}`}>
      {children}
    </span>
  );
}
